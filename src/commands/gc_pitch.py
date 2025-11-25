"""
Google Cloud TTS 피치 설정 명령어

Google Cloud TTS의 음성 피치를 변경합니다.
"""
import discord
from discord import app_commands
from src.config import Config


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
        
        Args:
            interaction: Discord 인터랙션 객체
            pitch: 피치 값 (-20.0 ~ 20.0)
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
        
        # 피치 유효성 검사
        if pitch < -20.0 or pitch > 20.0:
            await interaction.response.send_message(
                "❌ 피치는 -20.0 ~ 20.0 사이의 값이어야 합니다.\n"
                "- -20.0 = 매우 낮음\n"
                "- 0.0 = 기본\n"
                "- 20.0 = 매우 높음"
            )
            return
        
        # 피치 설정 저장
        config.set_gc_pitch(guild_id, pitch)
        
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
        
        await interaction.response.send_message(
            f"✅ Google Cloud TTS 피치가 변경되었습니다!\n"
            f"- 새 피치: **{pitch}** ({pitch_desc})"
        )
