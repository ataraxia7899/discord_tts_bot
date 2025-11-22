"""
음성 상태 이벤트 핸들러

사용자의 음성 채널 입/퇴장을 처리합니다.
"""
import discord
import asyncio
from src.handlers.message_handler import tts_queues


def register_voice_handler(bot):
    """
    봇에 음성 상태 변경 이벤트 핸들러를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    
    @bot.event
    async def on_voice_state_update(member, before, after):
        """
        음성 상태 변경 이벤트 핸들러
        
        음성 채널에 봇만 남았을 때 자동으로 퇴장합니다.
        
        Args:
            member: 상태가 변경된 멤버
            before: 변경 전 음성 상태
            after: 변경 후 음성 상태
        """
        # 봇 자신의 상태 변경은 무시
        if member.bot:
            return
        
        voice_client = member.guild.voice_client
        
        # 봇이 음성 채널에 있고, 변경 전 채널이 봇이 있는 채널인 경우
        if voice_client and before.channel == voice_client.channel:
            # 봇만 남았는지 확인 (봇 자신 1명)
            if len(voice_client.channel.members) == 1:
                # 봇 퇴장
                await voice_client.disconnect()
                
                # TTS 큐 초기화
                if member.guild.id in tts_queues:
                    tts_queues[member.guild.id] = asyncio.Queue()
