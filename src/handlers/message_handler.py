"""길드별 단일 재생 작업과 크기가 제한된 TTS 대기열."""
import asyncio
from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import tempfile
from typing import Optional

import discord
import imageio_ffmpeg

from src.config import Config
from src.tts import EdgeTTSEngine
from src.utils.text_preprocessor import preprocess_text

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 200
MAX_QUEUE_SIZE = 20
FFMPEG_EXECUTABLE = imageio_ffmpeg.get_ffmpeg_exe()
PLAYBACK_TIMEOUT = 60.0


@dataclass
class PlaybackState:
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(MAX_QUEUE_SIZE))
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    worker: Optional[asyncio.Task] = None
    generation: Optional[asyncio.Task] = None


playback_states: dict[int, PlaybackState] = {}
tts_engines: dict[int, EdgeTTSEngine] = {}


def get_playback_state(guild_id: int) -> PlaybackState:
    if guild_id not in playback_states:
        playback_states[guild_id] = PlaybackState()
    return playback_states[guild_id]


def invalidate_engine_cache(guild_id: int) -> None:
    tts_engines.pop(guild_id, None)


def get_tts_engine(guild_id: int, config: Config) -> EdgeTTSEngine:
    if guild_id not in tts_engines:
        tts_engines[guild_id] = EdgeTTSEngine(
            voice=config.get_voice(guild_id), rate=config.get_speed(guild_id),
            pitch=config.get_pitch(guild_id),
        )
    return tts_engines[guild_id]


def remove_audio(filename: Optional[str]) -> None:
    if filename:
        try:
            Path(filename).unlink(missing_ok=True)
        except OSError:
            logger.exception("임시 음성 파일 삭제 실패")


async def generate_tts(tts_engine: EdgeTTSEngine, text: str) -> Optional[str]:
    descriptor, filename = tempfile.mkstemp(suffix=".mp3")
    os.close(descriptor)
    completed = False
    try:
        await tts_engine.generate(text, filename)
        if Path(filename).stat().st_size == 0:
            raise ValueError("생성된 음성 파일이 비어 있습니다.")
        completed = True
        return filename
    except Exception:
        logger.exception("TTS 생성 실패: 이 메시지는 재생하지 않습니다.")
        return None
    finally:
        if not completed:
            remove_audio(filename)


async def play_from_file(voice_client: discord.VoiceClient, filename: str) -> None:
    """생성에 성공한 파일만 재생하며 취소 시 FFmpeg를 정리합니다."""
    loop = asyncio.get_running_loop()
    finished = loop.create_future()
    source = None

    def resolve(error):
        # 완료 여부 확인과 결과 설정을 모두 이벤트 루프에서 수행합니다.
        if not finished.done():
            if error:
                finished.set_exception(error)
            else:
                finished.set_result(None)

    def after_callback(error):
        loop.call_soon_threadsafe(resolve, error)

    try:
        if not voice_client.is_connected():
            return
        if not Path(filename).is_file() or Path(filename).stat().st_size == 0:
            raise ValueError("재생할 음성 파일이 없습니다.")
        source = discord.FFmpegOpusAudio(filename, executable=FFMPEG_EXECUTABLE)
        voice_client.play(source, after=after_callback)
        await asyncio.wait_for(finished, timeout=PLAYBACK_TIMEOUT)
    except Exception:
        logger.exception("TTS 파일 재생 오류")
    finally:
        try:
            if source is not None:
                if voice_client.source is source:
                    voice_client.stop()
                await asyncio.to_thread(source.cleanup)
        finally:
            remove_audio(filename)


def start_next_generation(guild_id: int, state: PlaybackState, config: Config) -> None:
    try:
        text = state.queue.get_nowait()
    except asyncio.QueueEmpty:
        return
    state.queue.task_done()
    state.generation = asyncio.create_task(generate_tts(get_tts_engine(guild_id, config), text))


async def play_tts_loop(guild_id: int, voice_client: discord.VoiceClient,
                        config: Config, state: PlaybackState) -> None:
    filename = None
    try:
        while voice_client.is_connected():
            if state.generation is None:
                start_next_generation(guild_id, state, config)
            if state.generation is None:
                break
            filename = await state.generation
            state.generation = None
            if filename is None:
                continue
            if not voice_client.is_connected():
                break
            # 현재 음성을 재생하는 동안 다음 메시지를 하나만 미리 생성합니다.
            start_next_generation(guild_id, state, config)
            await play_from_file(voice_client, filename)
            filename = None
    except Exception:
        logger.exception("TTS 재생 작업 오류: guild_id=%s", guild_id)
    finally:
        remove_audio(filename)
        if state.generation is not None:
            state.generation.cancel()
            results = await asyncio.gather(state.generation, return_exceptions=True)
            if isinstance(results[0], str):
                remove_audio(results[0])
            state.generation = None
        state.worker = None


async def _clear_playback_locked(state: PlaybackState, voice_client) -> int:
    cleared = state.queue.qsize() + int(state.generation is not None)
    while not state.queue.empty():
        state.queue.get_nowait()
        state.queue.task_done()
    if state.worker is not None:
        state.worker.cancel()
        await asyncio.gather(state.worker, return_exceptions=True)
        state.worker = None
    if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
        voice_client.stop()
    return cleared


async def clear_playback(guild_id: int, voice_client=None) -> int:
    state = get_playback_state(guild_id)
    # 정리 완료 전 새 메시지가 이전 작업에 합류하지 못하게 합니다.
    async with state.lock:
        return await _clear_playback_locked(state, voice_client)


async def disconnect_playback(guild_id: int, voice_client) -> None:
    state = get_playback_state(guild_id)
    async with state.lock:
        await _clear_playback_locked(state, voice_client)
        await voice_client.disconnect()


def enqueue_tts(guild_id: int, text: str, voice_client, config: Config,
                state: PlaybackState) -> bool:
    """호출자는 state.lock을 보유해야 합니다. 작업 등록 전에는 yield하지 않습니다."""
    try:
        state.queue.put_nowait(text)
    except asyncio.QueueFull:
        return False
    if state.worker is None or state.worker.done():
        state.worker = asyncio.create_task(play_tts_loop(guild_id, voice_client, config, state))
    return True


def register_message_handler(bot) -> None:
    config = Config()

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        guild_id = message.guild.id
        settings = config.get_guild_settings(guild_id)
        if not settings or message.channel.id != settings['channel_id']:
            return
        if not message.author.voice:
            embed = discord.Embed(
                title="🎤 음성 채널 필요",
                description="TTS를 사용하려면 음성 채널에 먼저 접속해주세요.",
                color=discord.Color.orange(),
            )
            await message.channel.send(embed=embed, delete_after=5)
            return
        text = message.content[:MAX_MESSAGE_LENGTH]
        if config.get_read_username(guild_id):
            text = f"{message.author.display_name} 님, {text}"
        text = preprocess_text(text)
        if not text:
            return
        user_voice_channel = message.author.voice.channel
        state = get_playback_state(guild_id)
        async with state.lock:
            # /setup 비활성화나 채널 변경이 대기 중 일어난 경우 다시 확인합니다.
            settings = config.get_guild_settings(guild_id)
            if not settings or message.channel.id != settings['channel_id']:
                return
            voice_client = message.guild.voice_client
            if voice_client and not voice_client.is_connected():
                await _clear_playback_locked(state, voice_client)
                await voice_client.disconnect(force=True)
                voice_client = None
            if not voice_client:
                try:
                    voice_client = await user_voice_channel.connect(reconnect=True)
                except Exception:
                    logger.exception("음성 채널 접속 오류")
                    return
            elif voice_client.channel != user_voice_channel:
                embed = discord.Embed(
                    title="🚫 다른 채널 사용 중",
                    description=f"봇이 이미 **{voice_client.channel.name}** 채널에 있습니다.",
                    color=discord.Color.red(),
                )
                await message.channel.send(embed=embed, delete_after=5)
                return
            accepted = enqueue_tts(guild_id, text, voice_client, config, state)
        if not accepted:
            await message.channel.send(
                f"TTS 대기열이 가득 찼습니다. (최대 {MAX_QUEUE_SIZE}개) 잠시 후 다시 보내주세요.",
                delete_after=5,
            )
