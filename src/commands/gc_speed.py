"""
Google Cloud TTS 속도 설정 명령어

Google Cloud TTS의 말하기 속도를 변경합니다.
"""
import discord
from discord import app_commands
from src.config import Config


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
        
        Args:
            interaction: Discord 인터랙션 객체
            speed: 속도 값 (0.25 ~ 4.0)
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
        
        # 속도 유효성 검사
        if speed < 0.25 or speed > 4.0:
            await interaction.response.send_message(
                "❌ 속도는 0.25 ~ 4.0 사이의 값이어야 합니다.\n"
                "- 0.25 = 매우 느림\n"
                "- 1.0 = 보통\n"
                "- 2.0 = 빠름\n"
                "- 4.0 = 매우 빠름"
            )
            return
        
        # 속도 설정 저장
        config.set_gc_speed(guild_id, speed)
        
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
        
        await interaction.response.send_message(
            f"✅ Google Cloud TTS 속도가 변경되었습니다!\n"
            f"- 새 속도: **{speed}** ({speed_desc})"
        )
