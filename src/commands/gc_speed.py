"""
Google Cloud TTS 속도 설정 명령어

Google Cloud TTS의 말하기 속도를 변경합니다.
"""
import discord
from discord import app_commands
from src.config import Config
from src.utils import create_success_embed, create_error_embed, ERROR_SETUP_REQUIRED, ERROR_GCTTS_REQUIRED
from src.handlers.message_handler import invalidate_engine_cache


def register_gcspeed_command(bot):
    """
    봇에 Google Cloud TTS 속도 설정 명령어를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    config = Config()
    
    @bot.tree.command(name="gcspeed", description="Google Cloud TTS 속도를 변경합니다 (0.25 ~ 4.0).")
    @app_commands.describe(speed="말하기 속도 (0.25=매우 느림, 1.0=보통, 2.0=빠름, 4.0=매우 빠름)")
    async def gcspeed(interaction: discord.Interaction, speed: float):
        """
        Google Cloud TTS 속도를 변경하는 명령어 핸들러
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
        
        # 속도 유효성 검사
        if speed < 0.25 or speed > 4.0:
            embed = create_error_embed(
                "유효하지 않은 값",
                "속도는 **0.25 ~ 4.0** 사이의 값이어야 합니다.\n\n"
                "• 0.25 = 매우 느림\n"
                "• 1.0 = 보통\n"
                "• 2.0 = 빠름\n"
                "• 4.0 = 매우 빠름"
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # 속도 설정 저장
        config.set_gc_speed(guild_id, speed)
        invalidate_engine_cache(guild_id)
        
        # 속도 설명
        speed_desc = "보통"
        if speed < 0.75:
            speed_desc = "매우 느림"
        elif speed < 1.0:
            speed_desc = "느림"
        elif speed > 1.5:
            speed_desc = "매우 빠름"
        elif speed > 1.0:
            speed_desc = "빠름"
        
        embed = create_success_embed(
            "속도 변경 완료",
            f"Google Cloud TTS 속도가 **{speed}** ({speed_desc})으로 변경되었습니다."
        )
        await interaction.response.send_message(embed=embed)
