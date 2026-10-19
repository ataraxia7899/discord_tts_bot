"""음성 채널 자동 퇴장 시 생성·재생 작업도 함께 정리합니다."""
from src.handlers.message_handler import disconnect_playback


def register_voice_handler(bot):
    @bot.event
    async def on_voice_state_update(member, before, after):
        if member.bot:
            return
        voice_client = member.guild.voice_client
        if (voice_client and before.channel == voice_client.channel
                and len(voice_client.channel.members) == 1):
            await disconnect_playback(member.guild.id, voice_client)
