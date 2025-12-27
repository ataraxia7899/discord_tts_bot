"""
메시지 이벤트 핸들러

메시지를 TTS로 변환하여 재생하는 기능을 처리합니다.
Prefetch, FFmpeg 최적화, Idle Timeout 기능이 포함되어 있습니다.
"""
import discord
import asyncio
import os
import io
import tempfile
import logging
from typing import Dict, Optional, Union
from src.config import Config
from src.tts import GoogleTTSEngine, GoogleCloudTTSEngine, TTSEngine
from src.utils import preprocess_text

# 로깅 설정
logger = logging.getLogger(__name__)

# 상수 정의
MAX_MESSAGE_LENGTH = 100
IDLE_TIMEOUT_SECONDS = 2 * 60 * 60  # 2시간

# FFmpeg 옵션 - 네트워크 안정성 및 성능 최적화
FFMPEG_OPTIONS = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

# 길드별 상태 관리
tts_queues: Dict[int, asyncio.Queue] = {}
is_playing: Dict[int, bool] = {}
tts_locks: Dict[int, asyncio.Lock] = {}  # Race condition 방지
tts_engines: Dict[int, TTSEngine] = {}  # TTS 엔진 캐시 (싱글톤화)
prefetch_cache: Dict[int, Dict[str, str]] = {}  # Prefetch 결과 캐시 {guild_id: {text: filename}}
last_activity: Dict[int, float] = {}  # 마지막 활동 시간
idle_timeout_tasks: Dict[int, asyncio.Task] = {}  # Idle timeout 태스크


def get_guild_lock(guild_id: int) -> asyncio.Lock:
    """길드별 Lock을 가져오거나 생성합니다."""
    if guild_id not in tts_locks:
        tts_locks[guild_id] = asyncio.Lock()
    return tts_locks[guild_id]


def get_or_create_engine(guild_id: int, config: Config) -> TTSEngine:
    """
    길드별 TTS 엔진을 가져오거나 생성합니다. (싱글톤 패턴)
    
    Args:
        guild_id: 길드 ID
        config: Config 인스턴스
        
    Returns:
        TTSEngine 인스턴스
    """
    engine_type = config.get_guild_engine(guild_id)
    
    # 엔진 타입이 변경되었거나 없으면 새로 생성
    if guild_id in tts_engines:
        current_engine = tts_engines[guild_id]
        is_gctts = isinstance(current_engine, GoogleCloudTTSEngine)
        if (engine_type == "gctts") != is_gctts:
            # 엔진 타입 변경됨 - 재생성 필요
            del tts_engines[guild_id]
    
    if guild_id not in tts_engines:
        if engine_type == "gctts":
            try:
                gc_settings = config.get_gc_settings(guild_id)
                tts_engines[guild_id] = GoogleCloudTTSEngine(
                    voice_name=gc_settings['voice'],
                    speaking_rate=gc_settings['speed'],
                    pitch=gc_settings['pitch']
                )
            except ValueError as e:
                logger.error(f"Google Cloud TTS 엔진 초기화 오류: {e}")
                logger.info("Google TTS (gTTS)로 폴백합니다.")
                tts_engines[guild_id] = GoogleTTSEngine()
        else:
            tts_engines[guild_id] = GoogleTTSEngine()
    
    return tts_engines[guild_id]


def update_last_activity(guild_id: int):
    """마지막 활동 시간을 갱신합니다."""
    import time
    last_activity[guild_id] = time.time()


async def idle_timeout_handler(guild_id: int, voice_client: discord.VoiceClient):
    """
    Idle Timeout 핸들러
    
    2시간 동안 활동이 없으면 음성 채널에서 자동 퇴장합니다.
    
    Args:
        guild_id: 길드 ID
        voice_client: Discord 음성 클라이언트
    """
    import time
    
    while True:
        await asyncio.sleep(60)  # 1분마다 체크
        
        # 연결 상태 확인
        if not voice_client.is_connected():
            break
        
        # 마지막 활동 후 경과 시간 확인
        current_time = time.time()
        last = last_activity.get(guild_id, current_time)
        elapsed = current_time - last
        
        if elapsed >= IDLE_TIMEOUT_SECONDS:
            logger.info(f"길드 {guild_id}: {IDLE_TIMEOUT_SECONDS/3600}시간 비활동으로 인한 자동 퇴장")
            await voice_client.disconnect()
            cleanup_guild_resources(guild_id)
            break


def cleanup_guild_resources(guild_id: int):
    """길드 관련 리소스를 정리합니다."""
    # Prefetch 캐시 파일 삭제
    if guild_id in prefetch_cache:
        for filename in prefetch_cache[guild_id].values():
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except OSError:
                pass
        del prefetch_cache[guild_id]
    
    # 큐 초기화
    if guild_id in tts_queues:
        tts_queues[guild_id] = asyncio.Queue()
    
    # 엔진 캐시 정리 (선택적)
    if guild_id in tts_engines:
        del tts_engines[guild_id]
    
    # Idle timeout 태스크 취소
    if guild_id in idle_timeout_tasks:
        idle_timeout_tasks[guild_id].cancel()
        del idle_timeout_tasks[guild_id]
    
    # 활동 시간 정리
    if guild_id in last_activity:
        del last_activity[guild_id]


def invalidate_engine_cache(guild_id: int):
    """
    길드의 TTS 엔진 캐시를 무효화합니다.
    설정 변경 시 호출하여 다음 재생 시 새 설정으로 엔진을 재생성합니다.
    
    Args:
        guild_id: 길드 ID
    """
    if guild_id in tts_engines:
        del tts_engines[guild_id]
        logger.debug(f"길드 {guild_id} 엔진 캐시 무효화")


def register_message_handler(bot):
    """
    봇에 메시지 이벤트 핸들러를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    config = Config()
    
    @bot.event
    async def on_message(message):
        """
        메시지 수신 이벤트 핸들러
        
        설정된 채널에서 메시지를 받으면 TTS로 변환하여 재생합니다.
        
        Args:
            message: Discord 메시지 객체
        """
        # 봇 메시지 무시
        if message.author.bot:
            return
        
        guild_id = message.guild.id
        channel_id = config.get_guild_channel(guild_id)
        
        # 설정이 없거나 채널이 다르면 무시
        if not channel_id or message.channel.id != channel_id:
            return
        
        # 음성 채널에 없으면 무시
        if not message.author.voice:
            return
        
        voice_client = message.guild.voice_client
        user_voice_channel = message.author.voice.channel
        
        # 음성 채널 접속 로직
        if not voice_client:
            try:
                voice_client = await user_voice_channel.connect()
                
                # Idle timeout 태스크 시작
                idle_timeout_tasks[guild_id] = asyncio.create_task(
                    idle_timeout_handler(guild_id, voice_client)
                )
                
            except Exception as e:
                logger.error(f"음성 채널 접속 오류: {e}")
                return
        elif voice_client.channel != user_voice_channel:
            await message.channel.send(
                f"🚫 봇이 이미 다른 통화방(**{voice_client.channel.name}**)에 있습니다."
            )
            return
        
        # 활동 시간 갱신
        update_last_activity(guild_id)
        
        # 메시지를 큐에 추가
        text = message.content[:MAX_MESSAGE_LENGTH]
        # 텍스트 전처리 (URL 대체, 반복 문자 제한)
        text = preprocess_text(text)
        
        if guild_id not in tts_queues:
            tts_queues[guild_id] = asyncio.Queue()
        
        await tts_queues[guild_id].put(text)
        
        # Race condition 방지를 위한 Lock 사용
        lock = get_guild_lock(guild_id)
        async with lock:
            if not is_playing.get(guild_id, False):
                is_playing[guild_id] = True
                asyncio.create_task(play_tts_loop(guild_id, voice_client, config))


async def prefetch_next_tts(guild_id: int, queue: asyncio.Queue, tts_engine: TTSEngine):
    """
    다음 메시지를 미리 TTS로 생성합니다. (Prefetch)
    
    Args:
        guild_id: 길드 ID
        queue: TTS 큐
        tts_engine: TTS 엔진
    """
    try:
        # 큐가 비어있지 않으면 다음 항목을 peek (꺼내지 않고 확인)
        if not queue.empty():
            # 큐에서 다음 텍스트를 임시로 가져옴
            # 주의: asyncio.Queue는 peek을 지원하지 않으므로 _queue 직접 접근
            if queue._queue:
                next_text = queue._queue[0]
                
                # 이미 prefetch된 경우 스킵
                if guild_id in prefetch_cache and next_text in prefetch_cache[guild_id]:
                    return
                
                # Prefetch 캐시 초기화
                if guild_id not in prefetch_cache:
                    prefetch_cache[guild_id] = {}
                
                # 임시 파일로 TTS 생성
                with tempfile.NamedTemporaryFile(
                    suffix=".mp3", 
                    delete=False, 
                    prefix=f"tts_prefetch_{guild_id}_"
                ) as tmp:
                    await tts_engine.generate(next_text, tmp.name)
                    prefetch_cache[guild_id][next_text] = tmp.name
                    logger.debug(f"Prefetch 완료: {next_text[:20]}...")
                    
    except Exception as e:
        logger.error(f"Prefetch 오류: {e}")


async def play_tts_loop(guild_id: int, voice_client: discord.VoiceClient, config: Config):
    """
    TTS 재생 루프
    
    큐에 있는 메시지를 순차적으로 TTS로 변환하여 재생합니다.
    Prefetch 기능으로 다음 메시지를 미리 생성합니다.
    
    Args:
        guild_id: 길드 ID
        voice_client: Discord 음성 클라이언트
        config: Config 인스턴스
    """
    queue = tts_queues[guild_id]
    
    # TTS 엔진 가져오기 (싱글톤)
    tts_engine = get_or_create_engine(guild_id, config)
    
    try:
        while not queue.empty():
            # 연결이 끊어졌으면 종료
            if not voice_client.is_connected():
                break
            
            text = await queue.get()
            
            # 활동 시간 갱신
            update_last_activity(guild_id)
            
            # Prefetch된 파일이 있는지 확인
            prefetched_file = None
            if guild_id in prefetch_cache and text in prefetch_cache[guild_id]:
                prefetched_file = prefetch_cache[guild_id].pop(text)
            
            try:
                # Prefetch된 파일 사용 또는 새로 생성
                if prefetched_file and os.path.exists(prefetched_file):
                    filename = prefetched_file
                else:
                    # 임시 파일로 TTS 생성
                    with tempfile.NamedTemporaryFile(
                        suffix=".mp3", 
                        delete=False, 
                        prefix=f"tts_{guild_id}_"
                    ) as tmp:
                        filename = tmp.name
                    await tts_engine.generate(text, filename)
                
                # 다음 메시지 Prefetch 시작 (비동기)
                prefetch_task = asyncio.create_task(
                    prefetch_next_tts(guild_id, queue, tts_engine)
                )
                
                # 음성 재생 (FFmpeg 옵션 적용)
                source = discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS)
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                
                def after_callback(error):
                    """재생 완료 콜백"""
                    if not future.done():
                        loop.call_soon_threadsafe(future.set_result, None)
                    if error:
                        logger.error(f"Player error: {error}")
                
                voice_client.play(source, after=after_callback)
                await future
                
                # Prefetch 태스크 완료 대기
                try:
                    await asyncio.wait_for(prefetch_task, timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
            except Exception as e:
                logger.error(f"TTS 재생 오류: {e}")
            
            finally:
                # 임시 파일 삭제
                if filename and os.path.exists(filename):
                    try:
                        os.remove(filename)
                    except OSError:
                        pass
                        
    finally:
        # 재생 상태 플래그 해제 (예외 발생 시에도 안전하게 처리)
        is_playing[guild_id] = False
