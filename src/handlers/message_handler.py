"""
메시지 이벤트 핸들러

메시지를 TTS로 변환하여 재생하는 기능을 처리합니다.
"""
import discord
import asyncio
import tempfile
import os
import logging
from typing import Dict, Optional, Tuple
from src.config import Config
from src.tts import EdgeTTSEngine
from src.utils.text_preprocessor import preprocess_text

# 로깅 설정
logger = logging.getLogger(__name__)

# 상수 정의
MAX_MESSAGE_LENGTH = 200

# TTS 큐 및 재생 상태 관리
tts_queues: Dict[int, asyncio.Queue] = {}
is_playing: Dict[int, bool] = {}
tts_engines: Dict[int, EdgeTTSEngine] = {}
audio_queues: Dict[int, asyncio.Queue] = {}

# 음성 채널 연결 경쟁 조건 방지용 Lock
connect_locks: Dict[int, asyncio.Lock] = {}


def invalidate_engine_cache(guild_id: int) -> None:
    """특정 길드의 TTS 엔진 캐시를 무효화합니다."""
    if guild_id in tts_engines:
        del tts_engines[guild_id]


def get_tts_engine(guild_id: int, config: Config) -> EdgeTTSEngine:
    """길드에 맞는 TTS 엔진을 가져옵니다."""
    if guild_id not in tts_engines:
        voice = config.get_voice(guild_id)
        speed = config.get_speed(guild_id)
        pitch = config.get_pitch(guild_id)
        tts_engines[guild_id] = EdgeTTSEngine(voice=voice, rate=speed, pitch=pitch)
    return tts_engines[guild_id]


async def generate_tts(tts_engine: EdgeTTSEngine, text: str) -> Optional[str]:
    """TTS를 생성하고 파일 경로를 반환합니다."""
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
        filename = tmp_file.name
    
    try:
        await tts_engine.generate(text, filename)
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return filename
        else:
            try:
                os.remove(filename)
            except OSError:
                pass
            return None
    except Exception as e:
        logger.error(f"TTS 생성 오류: {e}")
        try:
            os.remove(filename)
        except OSError:
            pass
        return None


def register_message_handler(bot) -> None:
    """봇에 메시지 이벤트 핸들러를 등록합니다."""
    config = Config()
    
    @bot.event
    async def on_message(message: discord.Message) -> None:
        """메시지 수신 이벤트 핸들러"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        guild_id = message.guild.id
        settings = config.get_guild_settings(guild_id)
        
        if not settings or message.channel.id != settings['channel_id']:
            return
        
        if not message.author.voice:
            embed = discord.Embed(
                title="🎤 음성 채널 필요",
                description="TTS를 사용하려면 음성 채널에 먼저 접속해주세요.",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed, delete_after=5)
            return
        
        user_voice_channel = message.author.voice.channel
        
        # 길드별 Lock으로 동시 connect 방지
        if guild_id not in connect_locks:
            connect_locks[guild_id] = asyncio.Lock()
        
        async with connect_locks[guild_id]:
            voice_client = message.guild.voice_client
            if not voice_client:
                try:
                    voice_client = await user_voice_channel.connect()
                except Exception as e:
                    logger.error(f"음성 채널 접속 오류: {e}")
                    return
            elif voice_client.channel != user_voice_channel:
                embed = discord.Embed(
                    title="🚫 다른 채널 사용 중",
                    description=f"봇이 이미 **{voice_client.channel.name}** 채널에 있습니다.",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed, delete_after=5)
                return
        
        # 텍스트 전처리
        text = message.content[:MAX_MESSAGE_LENGTH]
        
        # reply 인용인 경우, 인용된 메시지는 무시하고 본문만 읽음
        # (message.reference가 있어도 message.content는 본문만 포함)
        
        if config.get_read_username(guild_id):
            text = f"{message.author.display_name} 님, {text}"
        
        processed_text = preprocess_text(text)
        
        if not processed_text:
            return
        
        # 큐 초기화
        if guild_id not in tts_queues:
            tts_queues[guild_id] = asyncio.Queue()
        
        # 메시지를 큐에 추가
        await tts_queues[guild_id].put(processed_text)
        
        # 재생 루프가 실행 중이 아니면 시작
        if not is_playing.get(guild_id, False):
            bot.loop.create_task(play_tts_loop(guild_id, voice_client, config))


async def stream_and_play(
    tts_engine: EdgeTTSEngine,
    text: str,
    voice_client: discord.VoiceClient
) -> None:
    """
    TTS 스트리밍을 FFmpeg 파이프로 전달하여 즉시 재생합니다.
    
    edge-tts stream() → os.pipe → FFmpegPCMAudio(pipe=True)
    첫 청크 수신 즉시 재생이 시작되어 지연이 최소화됩니다.
    """
    read_fd, write_fd = os.pipe()
    read_pipe = os.fdopen(read_fd, 'rb')
    write_pipe = os.fdopen(write_fd, 'wb')
    
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    def after_callback(error: Optional[Exception]) -> None:
        """재생 완료 콜백"""
        if not future.done():
            loop.call_soon_threadsafe(future.set_result, None)
        if error:
            logger.error(f"Player error: {error}")
    
    # TTS 스트리밍 → 파이프 기록 태스크
    feed_task = asyncio.create_task(
        tts_engine.stream_to_pipe(text, write_pipe)
    )
    
    try:
        # FFmpeg가 파이프에서 읽어 PCM 변환 후 재생
        source = discord.FFmpegPCMAudio(read_pipe, pipe=True)
        voice_client.play(source, after=after_callback)
        await future
    except Exception as e:
        logger.error(f"TTS 재생 오류: {e}")
    finally:
        # 스트리밍 태스크 완료 대기
        if not feed_task.done():
            feed_task.cancel()
            try:
                await feed_task
            except asyncio.CancelledError:
                pass
        read_pipe.close()


async def play_from_file(
    voice_client: discord.VoiceClient,
    filename: str
) -> None:
    """미리 생성된 파일을 재생합니다."""
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    def after_callback(error: Optional[Exception]) -> None:
        """재생 완료 콜백"""
        if not future.done():
            loop.call_soon_threadsafe(future.set_result, None)
        if error:
            logger.error(f"Player error: {error}")
    
    try:
        source = discord.FFmpegPCMAudio(filename)
        voice_client.play(source, after=after_callback)
        await future
    except Exception as e:
        logger.error(f"TTS 파일 재생 오류: {e}")
    finally:
        try:
            os.remove(filename)
        except OSError:
            pass


async def play_tts_loop(
    guild_id: int, 
    voice_client: discord.VoiceClient, 
    config: Config
) -> None:
    """
    TTS 재생 루프 - 스트리밍 + prefetch 병행 방식
    
    현재 메시지: 스트리밍으로 즉시 재생
    다음 메시지: 재생 중에 파일로 미리 생성 (prefetch)
    """
    is_playing[guild_id] = True
    queue = tts_queues[guild_id]
    prefetch_result: Optional[str] = None
    prefetch_task: Optional[asyncio.Task] = None
    
    async def prefetch_next() -> Optional[str]:
        """다음 메시지를 파일로 미리 생성합니다."""
        try:
            text = await asyncio.wait_for(queue.get(), timeout=0.1)
            engine = get_tts_engine(guild_id, config)
            return await generate_tts(engine, text)
        except asyncio.TimeoutError:
            return None
        except Exception:
            return None
    
    try:
        while True:
            # 연결 확인
            if not voice_client.is_connected():
                break
            
            # prefetch된 파일이 있으면 파일 방식으로 즉시 재생
            if prefetch_result:
                filename = prefetch_result
                prefetch_result = None
                
                # 파일 재생 중에 다음 prefetch 시작
                prefetch_task = asyncio.create_task(prefetch_next())
                await play_from_file(voice_client, filename)
                
                # prefetch 결과 확인
                try:
                    prefetch_result = await prefetch_task
                except Exception:
                    prefetch_result = None
                prefetch_task = None
                continue
            
            # 큐에서 텍스트 가져오기
            try:
                text = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                break
            
            # 매 iteration마다 최신 엔진 조회
            tts_engine = get_tts_engine(guild_id, config)
            
            # 스트리밍 재생 + prefetch 동시 시작
            prefetch_task = asyncio.create_task(prefetch_next())
            await stream_and_play(tts_engine, text, voice_client)
            
            # prefetch 결과 확인
            try:
                prefetch_result = await prefetch_task
            except Exception:
                prefetch_result = None
            prefetch_task = None
    
    finally:
        # 미사용 prefetch 파일 정리
        if prefetch_result:
            try:
                os.remove(prefetch_result)
            except OSError:
                pass
        
        if prefetch_task and not prefetch_task.done():
            prefetch_task.cancel()
            try:
                result = await prefetch_task
                if result:
                    try:
                        os.remove(result)
                    except OSError:
                        pass
            except asyncio.CancelledError:
                pass
        
        is_playing[guild_id] = False

