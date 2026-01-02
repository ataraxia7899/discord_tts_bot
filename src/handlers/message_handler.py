"""
메시지 이벤트 핸들러

메시지를 TTS로 변환하여 재생하는 기능을 처리합니다.
"""
import discord
import asyncio
import os
import logging
from typing import Dict
from src.config import Config
from src.tts import EdgeTTSEngine, GoogleCloudTTSEngine
from src.utils.text_preprocessor import preprocess_text

# 로깅 설정
logger = logging.getLogger(__name__)

# 상수 정의
MAX_MESSAGE_LENGTH = 80  # Google Cloud TTS 무료 사용량 절약용
TTS_FILENAME_FORMAT = "tts_{guild_id}.mp3"

# TTS 큐 및 재생 상태 관리
tts_queues: Dict[int, asyncio.Queue] = {}
is_playing: Dict[int, bool] = {}
tts_engines: Dict[int, object] = {}  # TTS 엔진 캐시


def invalidate_engine_cache(guild_id: int):
    """
    특정 길드의 TTS 엔진 캐시를 무효화합니다.
    설정이 변경되었을 때 호출됩니다.
    
    Args:
        guild_id: 길드 ID
    """
    if guild_id in tts_engines:
        del tts_engines[guild_id]


def get_tts_engine(guild_id: int, config: Config):
    """
    길드에 맞는 TTS 엔진을 가져옵니다.
    캐싱을 통해 엔진 재생성을 방지합니다.
    
    Args:
        guild_id: 길드 ID
        config: Config 인스턴스
        
    Returns:
        TTS 엔진 인스턴스
    """
    if guild_id not in tts_engines:
        engine_type = config.get_engine_type(guild_id)
        
        if engine_type == "gctts":
            gc_settings = config.get_gc_settings(guild_id)
            tts_engines[guild_id] = GoogleCloudTTSEngine(
                voice_name=gc_settings['voice'],
                speaking_rate=gc_settings['speed'],
                pitch=gc_settings['pitch']
            )
        else:
            tts_engines[guild_id] = EdgeTTSEngine(config.edge_voice)
    
    return tts_engines[guild_id]


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
        settings = config.get_guild_settings(guild_id)
        
        # 설정이 없거나 채널이 다르면 무시
        if not settings or message.channel.id != settings['channel_id']:
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
            except Exception as e:
                logger.error(f"음성 채널 접속 오류: {e}")
                return
        elif voice_client.channel != user_voice_channel:
            await message.channel.send(
                f"🚫 봇이 이미 다른 통화방(**{voice_client.channel.name}**)에 있습니다."
            )
            return
        
        # 메시지를 큐에 추가 (초성 약어 변환 및 URL 처리)
        text = preprocess_text(message.content[:MAX_MESSAGE_LENGTH])
        if guild_id not in tts_queues:
            tts_queues[guild_id] = asyncio.Queue()
        
        await tts_queues[guild_id].put(text)
        
        # 재생 루프 시작
        if not is_playing.get(guild_id, False):
            bot.loop.create_task(play_tts_loop(guild_id, voice_client, config))


async def play_tts_loop(guild_id, voice_client, config):
    """
    TTS 재생 루프
    
    큐에 있는 메시지를 순차적으로 TTS로 변환하여 재생합니다.
    
    Args:
        guild_id: 길드 ID
        voice_client: Discord 음성 클라이언트
        config: Config 인스턴스
    """
    is_playing[guild_id] = True
    queue = tts_queues[guild_id]
    
    # 캐싱된 TTS 엔진 가져오기
    tts_engine = get_tts_engine(guild_id, config)
    
    while not queue.empty():
        # 연결이 끊어졌으면 종료
        if not voice_client.is_connected():
            break
        
        text = await queue.get()
        filename = TTS_FILENAME_FORMAT.format(guild_id=guild_id)
        
        try:
            # TTS 생성
            await tts_engine.generate(text, filename)
            
            # 음성 재생
            source = discord.FFmpegPCMAudio(filename)
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
            
        except Exception as e:
            logger.error(f"TTS 재생 오류: {e}")
        
        finally:
            # 임시 파일 삭제
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except OSError:
                    pass
    
    is_playing[guild_id] = False
