"""
Google Cloud TTS 음성 설정 명령어

Google Cloud TTS의 음성 종류를 변경합니다.
"""
import discord
from discord import app_commands
from src.config import Config


def register_gcvoice_command(bot):
    """
    봇에 Google Cloud TTS 음성 설정 명령어를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    config = Config()
    
    @bot.tree.command(name="gcvoice", description="Google Cloud TTS 음성을 변경합니다.")
    @app_commands.choices(voice=[
        app_commands.Choice(name="여성 음성 1 (Neural2-A)", value="ko-KR-Neural2-A"),
        app_commands.Choice(name="여성 음성 2 (Neural2-B)", value="ko-KR-Neural2-B"),
        app_commands.Choice(name="남성 음성 1 (Neural2-C)", value="ko-KR-Neural2-C"),
    ])
    async def gcvoice(interaction: discord.Interaction, voice: app_commands.Choice[str]):
        """
        Google Cloud TTS 음성을 변경하는 명령어 핸들러
        
        Args:
            interaction: Discord 인터랙션 객체
            voice: 선택한 음성
        """
        guild_id = interaction.guild_id
        
        # 서버 설정 확인
        if guild_id not in config.guild_settings:
            await interaction.response.send_message(
                "❌ 먼저 `/setup` 명령어로 TTS를 설정해주세요."
            )
            return
        
        # Google Cloud TTS 엔진 확인
        if config.get_guild_engine(guild_id) != "gctts":
            await interaction.response.send_message(
                "❌ 이 명령어는 Google Cloud TTS 엔진을 사용하는 서버에서만 사용할 수 있습니다.\n"
                "`/setup` 명령어에서 'Google Cloud TTS'를 선택해주세요."
            )
            return
        
        # 음성 설정 저장
        config.set_gc_voice(guild_id, voice.value)
        
        await interaction.response.send_message(
            f"✅ Google Cloud TTS 음성이 변경되었습니다!\n"
            f"- 새 음성: **{voice.name}**"
        )
