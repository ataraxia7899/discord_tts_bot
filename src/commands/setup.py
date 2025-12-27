"""
설정 명령어 핸들러 (Command 패턴)

TTS 봇의 설정 관련 명령어를 처리합니다.
"""
import discord
from discord import app_commands
from src.config import Config
from src.utils import create_success_embed, create_error_embed
from src.handlers.message_handler import invalidate_engine_cache


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
        """
        guild_id = interaction.guild_id
        
        # 비활성화 선택 시
        if action.value == "disable":
            config.remove_guild_settings(guild_id)
            invalidate_engine_cache(guild_id)
            
            embed = create_success_embed(
                "TTS 비활성화",
                f"서버 **{interaction.guild.name}**의 TTS 설정이 비활성화되었습니다."
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # Google Cloud TTS 활성화 - 환경 변수 확인
        if action.value == "enable_gctts":
            if not config.google_cloud_credentials_json:
                embed = create_error_embed(
                    "설정 오류",
                    "Google Cloud TTS를 사용하려면 `.env` 파일에 "
                    "`GOOGLE_CLOUD_CREDENTIALS_JSON` 환경 변수를 설정해야 합니다.\n\n"
                    "자세한 내용은 README를 참조하세요."
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Google Cloud TTS로 설정
            config.set_guild_settings(guild_id, interaction.channel_id, engine="gctts")
            invalidate_engine_cache(guild_id)
            
            gc_settings = config.get_gc_settings(guild_id)
            
            embed = create_success_embed(
                "설정 완료",
                f"**{interaction.channel.name}** 채널에서 TTS가 활성화되었습니다.",
                fields=[
                    {"name": "TTS 엔진", "value": "Google Cloud TTS", "inline": True},
                    {"name": "음성", "value": gc_settings['voice'], "inline": True},
                    {"name": "속도", "value": str(gc_settings['speed']), "inline": True},
                    {"name": "피치", "value": str(gc_settings['pitch']), "inline": True},
                ]
            )
            embed.set_footer(text="음성 변경: /gcvoice | 속도: /gcspeed | 피치: /gcpitch")
            await interaction.response.send_message(embed=embed)
        
        else:  # enable_gtts
            # Google TTS (gTTS)로 설정
            config.set_guild_settings(guild_id, interaction.channel_id, engine="gtts")
            invalidate_engine_cache(guild_id)
            
            embed = create_success_embed(
                "설정 완료",
                f"**{interaction.channel.name}** 채널에서 TTS가 활성화되었습니다.",
                fields=[
                    {"name": "TTS 엔진", "value": "Google TTS (gTTS)", "inline": True},
                ]
            )
            await interaction.response.send_message(embed=embed)
