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
        
        voice_client = message.guild.voice_client
        user_voice_channel = message.author.voice.channel
        
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


async def play_tts_loop(
    guild_id: int, 
    voice_client: discord.VoiceClient, 
    config: Config
) -> None:
    """
    TTS 재생 루프 - 최적화 버전
    
    현재 재생 중에 다음 TTS를 미리 생성하여 대기 시간 최소화
    """
    is_playing[guild_id] = True
    queue = tts_queues[guild_id]
    tts_engine = get_tts_engine(guild_id, config)
    
    # 준비된 오디오 저장: (text, filename)
    prepared: Optional[Tuple[str, str]] = None
    prepare_task: Optional[asyncio.Task] = None
    
    async def prepare_next() -> Optional[Tuple[str, str]]:
        """다음 메시지를 미리 준비합니다."""
        try:
            text = await asyncio.wait_for(queue.get(), timeout=0.1)
            filename = await generate_tts(tts_engine, text)
            if filename:
                return (text, filename)
        except asyncio.TimeoutError:
            pass
        except Exception:
            pass
        return None
    
    try:
        while True:
            # 연결 확인
            if not voice_client.is_connected():
                break
            
            # 준비된 오디오가 있으면 사용
            if prepared:
                text, filename = prepared
                prepared = None
            else:
                # 큐에서 가져와서 생성
                try:
                    text = await asyncio.wait_for(queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    # 큐가 비어있으면 종료
                    break
                
                filename = await generate_tts(tts_engine, text)
                if not filename:
                    continue
            
            # 재생하는 동안 다음 메시지 미리 준비 시작
            prepare_task = asyncio.create_task(prepare_next())
            
            try:
                # 음성 재생
                source = discord.FFmpegPCMAudio(filename)
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                
                def after_callback(error: Optional[Exception]) -> None:
                    if not future.done():
                        loop.call_soon_threadsafe(future.set_result, None)
                    if error:
                        logger.error(f"Player error: {error}")
                
                voice_client.play(source, after=after_callback)
                await future
                
            except Exception as e:
                logger.error(f"TTS 재생 오류: {e}")
            finally:
                # 파일 삭제
                try:
                    os.remove(filename)
                except OSError:
                    pass
            
            # 미리 준비된 오디오 가져오기
            if prepare_task:
                try:
                    prepared = await prepare_task
                except Exception:
                    prepared = None
                prepare_task = None
    
    finally:
        # 정리: 남은 준비된 오디오 파일 삭제
        if prepared:
            try:
                os.remove(prepared[1])
            except OSError:
                pass
        
        # prepare_task가 아직 실행 중이면 취소
        if prepare_task and not prepare_task.done():
            prepare_task.cancel()
            try:
                result = await prepare_task
                if result:
                    try:
                        os.remove(result[1])
                    except OSError:
                        pass
            except asyncio.CancelledError:
                pass
        
        is_playing[guild_id] = False
