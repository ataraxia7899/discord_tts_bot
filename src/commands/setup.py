"""
설정 명령어 핸들러 (Command 패턴)

TTS 봇의 설정 관련 명령어를 처리합니다.
"""
import discord
from discord import app_commands
from src.config import Config


def register_setup_commands(bot):
    """
    봇에 설정 관련 명령어를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    config = Config()
    
    @bot.tree.command(name="setup", description="TTS 엔진 및 채널을 설정합니다.")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="활성화 (Google TTS)", value="enable_gtts"),
            app_commands.Choice(name="활성화 (Google Cloud TTS)", value="enable_gctts"),
            app_commands.Choice(name="비활성화", value="disable")
        ]
    )
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
        
        # Google Cloud TTS 활성화 - 환경 변수 확인
        if action.value == "enable_gctts":
            if not config.google_cloud_credentials_json:
                await interaction.response.send_message(
                    "❌ Google Cloud TTS를 사용하려면 `.env` 파일에 "
                    "`GOOGLE_CLOUD_CREDENTIALS_JSON` 환경 변수를 설정해야 합니다.\n"
                    "자세한 내용은 README를 참조하세요."
                )
                return
            
            # Google Cloud TTS로 설정
            config.set_guild_settings(
                interaction.guild_id,
                interaction.channel_id,
                engine="gctts"
            )
            
            gc_settings = config.get_gc_settings(interaction.guild_id)
            
            await interaction.response.send_message(
                f"✅ 설정 완료!\n"
                f"- 대상 채널: **{interaction.channel.name}**\n"
                f"- TTS 엔진: **Google Cloud TTS**\n"
                f"- 음성: **{gc_settings['voice']}**\n"
                f"- 속도: **{gc_settings['speed']}**\n"
                f"- 피치: **{gc_settings['pitch']}**\n\n"
                f"음성 변경: `/gcvoice` | 속도 조절: `/gcspeed` | 피치 조절: `/gcpitch`"
            )
        
        else:  # enable_gtts
            # Google TTS (gTTS)로 설정
            config.set_guild_settings(
                interaction.guild_id,
                interaction.channel_id,
                engine="gtts"
            )
            
            await interaction.response.send_message(
                f"✅ 설정 완료!\n"
                f"- 대상 채널: **{interaction.channel.name}**\n"
                f"- TTS 엔진: **Google TTS (gTTS)**"
            )
