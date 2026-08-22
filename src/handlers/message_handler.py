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

            # Discord 쪽에서 강제로 연결이 끊긴 뒤 VoiceClient 객체만 남는 경우 정리
            if voice_client and not voice_client.is_connected():
                logger.warning("끊어진 음성 연결 객체를 감지하여 재연결을 준비합니다. guild_id=%s", guild_id)
                try:
                    await voice_client.disconnect(force=True)
                except Exception as e:
                    logger.warning(f"끊어진 음성 연결 정리 중 오류: {e}")
                voice_client = None
                is_playing[guild_id] = False

            if not voice_client:
                try:
                    voice_client = await user_voice_channel.connect(reconnect=True)
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
    TTS를 스트리밍하여 FFmpeg 파이프로 전달하고 즉시 재생합니다.
    """
    read_fd, write_fd = os.pipe()
    read_pipe = os.fdopen(read_fd, 'rb')
    write_pipe = os.fdopen(write_fd, 'wb')

    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def after_callback(error: Optional[Exception]) -> None:
        if not future.done():
            loop.call_soon_threadsafe(future.set_result, None)
        if error:
            logger.error(f"Player error: {error}")

    feed_task = asyncio.create_task(
        tts_engine.stream_to_pipe(text, write_pipe)
    )

    try:
        source = discord.FFmpegPCMAudio(read_pipe, pipe=True)
        voice_client.play(source, after=after_callback)
        await asyncio.wait_for(future, timeout=60)
    except asyncio.TimeoutError:
        logger.error("TTS 재생이 60초 내 완료되지 않아 중단합니다.")
        if voice_client.is_playing():
            voice_client.stop()
    except Exception as e:
        logger.error(f"TTS 재생 오류: {e}")
    finally:
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
        if not future.done():
            loop.call_soon_threadsafe(future.set_result, None)
        if error:
            logger.error(f"Player error: {error}")

    try:
        source = discord.FFmpegPCMAudio(filename)
        voice_client.play(source, after=after_callback)
        await asyncio.wait_for(future, timeout=60)
    except asyncio.TimeoutError:
        logger.error("TTS 파일 재생이 60초 내 완료되지 않아 중단합니다.")
        if voice_client.is_playing():
            voice_client.stop()
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
    """
    is_playing[guild_id] = True
    queue = tts_queues[guild_id]
    prefetch_result: Optional[str] = None
    prefetch_task: Optional[asyncio.Task] = None

    async def prefetch_next() -> Optional[str]:
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
            if not voice_client.is_connected():
                logger.warning("TTS 재생 중 음성 연결이 끊어졌습니다. guild_id=%s", guild_id)
                break

            if prefetch_result:
                filename = prefetch_result
                prefetch_result = None

                prefetch_task = asyncio.create_task(prefetch_next())
                await play_from_file(voice_client, filename)

                try:
                    prefetch_result = await prefetch_task
                except Exception:
                    prefetch_result = None
                prefetch_task = None
                continue

            try:
                text = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                break

            tts_engine = get_tts_engine(guild_id, config)

            prefetch_task = asyncio.create_task(prefetch_next())
            await stream_and_play(tts_engine, text, voice_client)

            try:
                prefetch_result = await prefetch_task
            except Exception:
                prefetch_result = None
            prefetch_task = None
    finally:
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
