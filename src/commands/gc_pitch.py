"""
Google Cloud TTS 피치 설정 명령어

Google Cloud TTS의 음성 피치를 변경합니다.
"""
import discord
from discord import app_commands
from src.config import Config
from src.utils import create_success_embed, create_error_embed, ERROR_SETUP_REQUIRED, ERROR_GCTTS_REQUIRED
from src.handlers.message_handler import invalidate_engine_cache


def register_gcpitch_command(bot):
    """
    봇에 Google Cloud TTS 피치 설정 명령어를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    config = Config()
    
    @bot.tree.command(name="gcpitch", description="Google Cloud TTS 피치를 변경합니다 (-20.0 ~ 20.0).")
    @app_commands.describe(pitch="음성 피치 (-20.0=매우 낮음, 0.0=기본, 20.0=매우 높음)")
    async def gcpitch(interaction: discord.Interaction, pitch: float):
        """
        Google Cloud TTS 피치를 변경하는 명령어 핸들러
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
        
        # 피치 유효성 검사
        if pitch < -20.0 or pitch > 20.0:
            embed = create_error_embed(
                "유효하지 않은 값",
                "피치는 **-20.0 ~ 20.0** 사이의 값이어야 합니다.\n\n"
                "• -20.0 = 매우 낮음\n"
                "• 0.0 = 기본\n"
                "• 20.0 = 매우 높음"
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # 피치 설정 저장
        config.set_gc_pitch(guild_id, pitch)
        invalidate_engine_cache(guild_id)
        
        # 피치 설명
        pitch_desc = "기본"
        if pitch < -10.0:
            pitch_desc = "매우 낮음"
        elif pitch < 0:
            pitch_desc = "낮음"
        elif pitch > 10.0:
            pitch_desc = "매우 높음"
        elif pitch > 0:
            pitch_desc = "높음"
        
        embed = create_success_embed(
            "피치 변경 완료",
            f"Google Cloud TTS 피치가 **{pitch}** ({pitch_desc})으로 변경되었습니다."
        )
        await interaction.response.send_message(embed=embed)
