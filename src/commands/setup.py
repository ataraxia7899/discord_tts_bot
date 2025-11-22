"""
설정 명령어 핸들러 (Command 패턴)

TTS 봇의 설정 관련 명령어를 처리합니다.
"""
import discord
from discord import app_commands
from src.config import Config


def register_commands(bot):
    """
    봇에 설정 관련 명령어를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    config = Config()
    
    @bot.tree.command(name="setup", description="TTS를 사용할 채널을 설정합니다.")
    @app_commands.choices(action=[
        app_commands.Choice(name="활성화 (현재 채널에서 TTS 사용)", value="enable"),
        app_commands.Choice(name="비활성화 (TTS 사용 안 함)", value="disable")
    ])
    async def setup(interaction: discord.Interaction, action: app_commands.Choice[str]):
        """
        TTS 설정을 저장하거나 비활성화하는 명령어 핸들러
        
        Args:
            interaction: Discord 인터랙션 객체
            action: 활성화 또는 비활성화 선택
        """
        # 비활성화 선택 시
        if action.value == "disable":
            config.remove_guild_settings(interaction.guild_id)
            await interaction.response.send_message(
                f"✅ TTS 설정이 비활성화되었습니다.\n- 서버: **{interaction.guild.name}**"
            )
            return
        
        # 설정 저장 (활성화)
        config.set_guild_settings(
            interaction.guild_id,
            interaction.channel_id
        )
        
        # 응답 메시지 전송
        await interaction.response.send_message(
            f"✅ 설정 완료!\n- 대상 채널: **{interaction.channel.name}**\n- TTS 엔진: **Google TTS (gTTS)**"
        )
