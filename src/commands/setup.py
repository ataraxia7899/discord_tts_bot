"""
설정 명령어 핸들러 (Command 패턴)

TTS 봇의 설정 관련 명령어를 처리합니다.
"""
import discord
from discord import app_commands
from src.config import Config
from src.handlers.message_handler import invalidate_engine_cache

def register_commands(bot):
    """
    봇에 설정 관련 명령어를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    config = Config()
    
    @bot.tree.command(name="setup", description="TTS를 사용할 채널과 엔진을 설정합니다.")
    @app_commands.choices(engine=[
        app_commands.Choice(name="Edge TTS (고품질, 무료)", value="edge"),
        app_commands.Choice(name="Google Cloud TTS (최고품질, 다양한 설정)", value="gctts"),
        app_commands.Choice(name="비활성화 (TTS 사용 안 함)", value="disable")
    ])
    async def setup(interaction: discord.Interaction, engine: app_commands.Choice[str]):
        """
        TTS 설정을 저장하거나 비활성화하는 명령어 핸들러
        
        Args:
            interaction: Discord 인터랙션 객체
            engine: 선택한 TTS 엔진 또는 비활성화
        """
        guild_id = interaction.guild_id
        
        # 비활성화 선택 시
        if engine.value == "disable":
            config.remove_guild_settings(guild_id)
            invalidate_engine_cache(guild_id)
            await interaction.response.send_message(
                f"✅ TTS 설정이 비활성화되었습니다.\n- 서버: **{interaction.guild.name}**"
            )
            return
        
        # 설정 저장
        config.set_guild_settings(
            guild_id,
            interaction.channel_id,
            engine.value
        )
        invalidate_engine_cache(guild_id)
        
        # 엔진별 응답 메시지
        if engine.value == "gctts":
            gc_settings = config.get_gc_settings(guild_id)
            await interaction.response.send_message(
                f"✅ 설정 완료!\n"
                f"- 대상 채널: **{interaction.channel.name}**\n"
                f"- 엔진: **Google Cloud TTS**\n"
                f"- 음성: {gc_settings['voice']}\n"
                f"- 속도: {gc_settings['speed']}\n"
                f"- 피치: {gc_settings['pitch']}\n\n"
                f"💡 설정 변경: `/gcvoice`, `/gcspeed`, `/gcpitch`"
            )
        else:
            await interaction.response.send_message(
                f"✅ 설정 완료!\n"
                f"- 대상 채널: **{interaction.channel.name}**\n"
                f"- 엔진: **Edge TTS**"
            )
    
    # Google Cloud TTS 음성 설정 명령어
    @bot.tree.command(name="gcvoice", description="Google Cloud TTS 음성을 변경합니다.")
    @app_commands.choices(voice=[
        app_commands.Choice(name="Neural2-A (여성)", value="ko-KR-Neural2-A"),
        app_commands.Choice(name="Neural2-B (여성)", value="ko-KR-Neural2-B"),
        app_commands.Choice(name="Neural2-C (남성)", value="ko-KR-Neural2-C"),
        app_commands.Choice(name="Standard-A (여성)", value="ko-KR-Standard-A"),
        app_commands.Choice(name="Standard-B (여성)", value="ko-KR-Standard-B"),
        app_commands.Choice(name="Standard-C (남성)", value="ko-KR-Standard-C"),
        app_commands.Choice(name="Standard-D (남성)", value="ko-KR-Standard-D"),
    ])
    async def gcvoice(interaction: discord.Interaction, voice: app_commands.Choice[str]):
        """Google Cloud TTS 음성 변경 명령어"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings or settings.get('engine') != 'gctts':
            await interaction.response.send_message(
                "❌ 먼저 `/setup`에서 Google Cloud TTS를 선택해주세요.",
                ephemeral=True
            )
            return
        
        config.set_gc_voice(guild_id, voice.value)
        invalidate_engine_cache(guild_id)
        await interaction.response.send_message(
            f"✅ 음성이 **{voice.name}** ({voice.value})로 변경되었습니다."
        )
    
    # Google Cloud TTS 속도 설정 명령어
    @bot.tree.command(name="gcspeed", description="Google Cloud TTS 말하기 속도를 변경합니다.")
    @app_commands.describe(speed="말하기 속도 (0.25 ~ 4.0, 기본값: 1.0)")
    async def gcspeed(interaction: discord.Interaction, speed: float):
        """Google Cloud TTS 속도 변경 명령어"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings or settings.get('engine') != 'gctts':
            await interaction.response.send_message(
                "❌ 먼저 `/setup`에서 Google Cloud TTS를 선택해주세요.",
                ephemeral=True
            )
            return
        
        # 범위 검증
        if speed < 0.25 or speed > 4.0:
            await interaction.response.send_message(
                "❌ 속도는 0.25에서 4.0 사이여야 합니다.",
                ephemeral=True
            )
            return
        
        config.set_gc_speed(guild_id, speed)
        invalidate_engine_cache(guild_id)
        await interaction.response.send_message(
            f"✅ 말하기 속도가 **{speed}**로 변경되었습니다."
        )
    
    # Google Cloud TTS 피치 설정 명령어
    @bot.tree.command(name="gcpitch", description="Google Cloud TTS 피치를 변경합니다.")
    @app_commands.describe(pitch="피치 (-20.0 ~ 20.0, 기본값: 0.0)")
    async def gcpitch(interaction: discord.Interaction, pitch: float):
        """Google Cloud TTS 피치 변경 명령어"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings or settings.get('engine') != 'gctts':
            await interaction.response.send_message(
                "❌ 먼저 `/setup`에서 Google Cloud TTS를 선택해주세요.",
                ephemeral=True
            )
            return
        
        # 범위 검증
        if pitch < -20.0 or pitch > 20.0:
            await interaction.response.send_message(
                "❌ 피치는 -20.0에서 20.0 사이여야 합니다.",
                ephemeral=True
            )
            return
        
        config.set_gc_pitch(guild_id, pitch)
        invalidate_engine_cache(guild_id)
        await interaction.response.send_message(
            f"✅ 피치가 **{pitch}**로 변경되었습니다."
        )
