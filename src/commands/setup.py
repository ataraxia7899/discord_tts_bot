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
    
    @bot.tree.command(name="setup", description="TTS를 사용할 채널과 엔진을 설정합니다.")
    @app_commands.choices(engine=[
        app_commands.Choice(name="Edge TTS (고품질, 약간 느림)", value="edge"),
        app_commands.Choice(name="Local TTS (기계음, 속도 최우선)", value="local"),
        app_commands.Choice(name="비활성화 (TTS 사용 안 함)", value="disable")
    ])
    async def setup(interaction: discord.Interaction, engine: app_commands.Choice[str]):
        """
        TTS 설정을 저장하거나 비활성화하는 명령어 핸들러
        
        Args:
            interaction: Discord 인터랙션 객체
            engine: 선택한 TTS 엔진 또는 비활성화
        """
        # 비활성화 선택 시
        if engine.value == "disable":
            config.remove_guild_settings(interaction.guild_id)
            await interaction.response.send_message(
                f"✅ TTS 설정이 비활성화되었습니다.\n- 서버: **{interaction.guild.name}**"
            )
            return
        
        # 설정 저장
        config.set_guild_settings(
            interaction.guild_id,
            interaction.channel_id,
            engine.value
        )
        
        # 엔진 이름 표시
        engine_name = "Edge TTS" if engine.value == "edge" else "Local TTS"
        
        # 응답 메시지 전송
        await interaction.response.send_message(
            f"✅ 설정 완료!\n- 대상 채널: **{interaction.channel.name}**\n- 엔진: **{engine_name}**"
        )
