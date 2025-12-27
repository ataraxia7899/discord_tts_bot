"""
Google Cloud TTS 음성 설정 명령어

Google Cloud TTS의 음성 종류를 변경합니다.
"""
import discord
from discord import app_commands
from src.config import Config
from src.utils import create_success_embed, create_error_embed, ERROR_SETUP_REQUIRED, ERROR_GCTTS_REQUIRED
from src.handlers.message_handler import invalidate_engine_cache


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
        """
        guild_id = interaction.guild_id
        
        # 서버 설정 확인
        if guild_id not in config.guild_settings:
            embed = create_error_embed("설정 필요", ERROR_SETUP_REQUIRED)
            await interaction.response.send_message(embed=embed)
            return
        
        # Google Cloud TTS 엔진 확인
        if config.get_guild_engine(guild_id) != "gctts":
            embed = create_error_embed("엔진 불일치", ERROR_GCTTS_REQUIRED)
            await interaction.response.send_message(embed=embed)
            return
        
        # 음성 설정 저장
        config.set_gc_voice(guild_id, voice.value)
        invalidate_engine_cache(guild_id)
        
        embed = create_success_embed(
            "음성 변경 완료",
            f"Google Cloud TTS 음성이 **{voice.name}**으로 변경되었습니다."
        )
        await interaction.response.send_message(embed=embed)
