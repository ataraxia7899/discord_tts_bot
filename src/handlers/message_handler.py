"""
메시지 이벤트 핸들러

메시지를 TTS로 변환하여 재생하는 기능을 처리합니다.
"""
import discord
import asyncio
import os
from typing import Dict
from src.config import Config
from src.tts import GoogleTTSEngine

# 상수 정의
MAX_MESSAGE_LENGTH = 100
TTS_FILENAME_FORMAT = "tts_{guild_id}.mp3"

# TTS 큐 및 재생 상태 관리
tts_queues: Dict[int, asyncio.Queue] = {}
is_playing: Dict[int, bool] = {}


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
            except Exception as e:
                print(f"음성 채널 접속 오류: {e}")
                return
        elif voice_client.channel != user_voice_channel:
            await message.channel.send(
                f"🚫 봇이 이미 다른 통화방(**{voice_client.channel.name}**)에 있습니다."
            )
            return
        
        # 메시지를 큐에 추가
        text = message.content[:MAX_MESSAGE_LENGTH]
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
    
    # Google TTS 엔진 생성
    tts_engine = GoogleTTSEngine()
    
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
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            
            def after_callback(error):
                """재생 완료 콜백"""
                if not future.done():
                    future.set_result(None)
                if error:
                    print(f"Player error: {error}")
            
            voice_client.play(source, after=after_callback)
            await future
            
        except Exception as e:
            print(f"TTS 재생 오류: {e}")
        
        finally:
            # 임시 파일 삭제
            if os.path.exists(filename):
                os.remove(filename)
    
    is_playing[guild_id] = False
