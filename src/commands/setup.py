"""
설정 명령어 핸들러 (Command 패턴)

TTS 봇의 설정 관련 명령어를 처리합니다.
"""
import discord
from discord import app_commands
from src.config import Config
from src.handlers.message_handler import invalidate_engine_cache

# 표시명 매핑
VOICE_NAMES = {
    "ko-KR-SunHiNeural": "선희 (여성)",
    "ko-KR-InJoonNeural": "인준 (남성)",
    "ko-KR-HyunsuNeural": "현수 (남성)",
}

SPEED_NAMES = {
    "-50%": "매우 느림",
    "-25%": "느림",
    "+0%": "보통",
    "+25%": "빠름",
    "+50%": "매우 빠름",
    "+100%": "초고속",
}

PITCH_NAMES = {
    "-50Hz": "매우 낮음",
    "-25Hz": "낮음",
    "+0Hz": "보통",
    "+25Hz": "높음",
    "+50Hz": "매우 높음",
}

# 음성 선택지
VOICE_CHOICES = [
    app_commands.Choice(name="선희 (여성, 기본)", value="ko-KR-SunHiNeural"),
    app_commands.Choice(name="인준 (남성)", value="ko-KR-InJoonNeural"),
    app_commands.Choice(name="현수 (남성)", value="ko-KR-HyunsuNeural"),
]

# 속도 선택지
SPEED_CHOICES = [
    app_commands.Choice(name="매우 느림 (-50%)", value="-50%"),
    app_commands.Choice(name="느림 (-25%)", value="-25%"),
    app_commands.Choice(name="보통 (기본)", value="+0%"),
    app_commands.Choice(name="빠름 (+25%)", value="+25%"),
    app_commands.Choice(name="매우 빠름 (+50%)", value="+50%"),
    app_commands.Choice(name="초고속 (+100%)", value="+100%"),
]

# 피치 선택지
PITCH_CHOICES = [
    app_commands.Choice(name="매우 낮음 (-50Hz)", value="-50Hz"),
    app_commands.Choice(name="낮음 (-25Hz)", value="-25Hz"),
    app_commands.Choice(name="보통 (기본)", value="+0Hz"),
    app_commands.Choice(name="높음 (+25Hz)", value="+25Hz"),
    app_commands.Choice(name="매우 높음 (+50Hz)", value="+50Hz"),
]


def get_display_name(value: str, mapping: dict) -> str:
    """기술적 값을 사용자 친화적 표시명으로 변환합니다."""
    return mapping.get(value, value)


def register_commands(bot):
    """
    봇에 설정 관련 명령어를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    config = Config()
    
    # /setup - TTS 활성화/비활성화 토글
    @bot.tree.command(name="setup", description="TTS를 활성화/비활성화합니다.")
    async def setup(interaction: discord.Interaction):
        """TTS 설정 토글"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        # 설정이 있으면 비활성화, 없으면 활성화
        if settings:
            config.remove_guild_settings(guild_id)
            invalidate_engine_cache(guild_id)
            
            embed = discord.Embed(
                title="🔇 TTS 비활성화",
                description="TTS 기능이 비활성화되었습니다.",
                color=discord.Color.red()
            )
            embed.add_field(name="서버", value=interaction.guild.name, inline=True)
            await interaction.response.send_message(embed=embed)
        else:
            config.set_guild_settings(guild_id, interaction.channel_id)
            
            embed = discord.Embed(
                title="🔊 TTS 활성화",
                description="이 채널의 메시지가 음성으로 읽힙니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="채널", value=f"#{interaction.channel.name}", inline=True)
            embed.add_field(name="음성", value=config.get_voice(guild_id), inline=True)
            embed.set_footer(text="💡 /voice, /speed, /status 명령어로 설정 변경")
            await interaction.response.send_message(embed=embed)
    
    # /voice - Edge TTS 음성 선택
    @bot.tree.command(name="voice", description="TTS 음성을 변경합니다.")
    @app_commands.choices(voice=VOICE_CHOICES)
    async def voice_cmd(
        interaction: discord.Interaction,
        voice: app_commands.Choice[str],
    ):
        """음성 변경 명령어"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings:
            embed = discord.Embed(
                title="❌ 설정 필요",
                description="먼저 `/setup` 명령어로 TTS를 활성화해주세요.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        config.set_voice(guild_id, voice.value)
        invalidate_engine_cache(guild_id)
        
        display_name = get_display_name(voice.value, VOICE_NAMES)
        embed = discord.Embed(
            title="🎤 음성 변경",
            description=f"음성이 **{display_name}**으로 변경되었습니다.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    # /speed - TTS 속도 조절
    @bot.tree.command(name="speed", description="TTS 말하기 속도를 변경합니다.")
    @app_commands.choices(speed=SPEED_CHOICES)
    async def speed_cmd(
        interaction: discord.Interaction,
        speed: app_commands.Choice[str],
    ):
        """속도 변경 명령어"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings:
            embed = discord.Embed(
                title="❌ 설정 필요",
                description="먼저 `/setup` 명령어로 TTS를 활성화해주세요.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        config.set_speed(guild_id, speed.value)
        invalidate_engine_cache(guild_id)
        
        display_name = get_display_name(speed.value, SPEED_NAMES)
        embed = discord.Embed(
            title="⚡ 속도 변경",
            description=f"말하기 속도가 **{display_name}**으로 변경되었습니다.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    # /pitch - TTS 피치 조절
    @bot.tree.command(name="pitch", description="TTS 음높이를 변경합니다.")
    @app_commands.choices(pitch=PITCH_CHOICES)
    async def pitch_cmd(
        interaction: discord.Interaction,
        pitch: app_commands.Choice[str],
    ):
        """피치 변경 명령어"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings:
            embed = discord.Embed(
                title="❌ 설정 필요",
                description="먼저 `/setup` 명령어로 TTS를 활성화해주세요.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        config.set_pitch(guild_id, pitch.value)
        invalidate_engine_cache(guild_id)
        
        display_name = get_display_name(pitch.value, PITCH_NAMES)
        embed = discord.Embed(
            title="🎵 피치 변경",
            description=f"음높이가 **{display_name}**으로 변경되었습니다.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    # /status - 현재 설정 확인
    @bot.tree.command(name="status", description="현재 TTS 설정을 확인합니다.")
    async def status(interaction: discord.Interaction):
        """상태 확인 명령어"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings:
            embed = discord.Embed(
                title="📊 TTS 상태",
                description="TTS가 비활성화되어 있습니다.",
                color=discord.Color.grey()
            )
            embed.set_footer(text="💡 /setup 명령어로 활성화하세요")
        else:
            channel = interaction.guild.get_channel(settings['channel_id'])
            channel_name = channel.name if channel else "알 수 없음"
            
            # 1회 조회로 모든 설정 가져오기
            all_settings = config.get_all_settings(guild_id)
            
            embed = discord.Embed(
                title="📊 TTS 상태",
                description="TTS가 활성화되어 있습니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="채널", value=f"#{channel_name}", inline=True)
            embed.add_field(
                name="음성", 
                value=get_display_name(all_settings['voice'], VOICE_NAMES), 
                inline=True
            )
            embed.add_field(
                name="속도", 
                value=get_display_name(all_settings['speed'], SPEED_NAMES), 
                inline=True
            )
            embed.add_field(
                name="피치", 
                value=get_display_name(all_settings['pitch'], PITCH_NAMES), 
                inline=True
            )
            embed.add_field(
                name="작성자 읽기", 
                value="켜짐" if all_settings['read_username'] else "꺼짐", 
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    # /leave - 음성 채널 나가기
    @bot.tree.command(name="leave", description="봇을 음성 채널에서 내보냅니다.")
    async def leave(interaction: discord.Interaction):
        """음성 채널 나가기 명령어"""
        voice_client = interaction.guild.voice_client
        
        if not voice_client:
            embed = discord.Embed(
                title="❌ 연결 없음",
                description="봇이 음성 채널에 연결되어 있지 않습니다.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await voice_client.disconnect()
        
        embed = discord.Embed(
            title="👋 연결 해제",
            description="음성 채널에서 나갔습니다.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    # /readname - 작성자 이름 읽기 토글
    @bot.tree.command(name="readname", description="메시지 작성자 이름 읽기를 설정합니다.")
    async def readname(interaction: discord.Interaction):
        """작성자 이름 읽기 토글"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings:
            embed = discord.Embed(
                title="❌ 설정 필요",
                description="먼저 `/setup` 명령어로 TTS를 활성화해주세요.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        current = config.get_read_username(guild_id)
        config.set_read_username(guild_id, not current)
        
        new_status = "켜짐" if not current else "꺼짐"
        embed = discord.Embed(
            title="👤 작성자 읽기",
            description=f"작성자 이름 읽기가 **{new_status}**으로 변경되었습니다.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    # /clear - TTS 대기열 비우기
    @bot.tree.command(name="clear", description="TTS 대기열을 비웁니다.")
    async def clear(interaction: discord.Interaction):
        """TTS 대기열 비우기"""
        from src.handlers.message_handler import tts_queues, audio_queues
        
        guild_id = interaction.guild_id
        cleared_count = 0
        
        # 텍스트 큐 비우기
        if guild_id in tts_queues:
            while not tts_queues[guild_id].empty():
                try:
                    tts_queues[guild_id].get_nowait()
                    cleared_count += 1
                except Exception:
                    break
        
        # 오디오 큐 비우기
        if guild_id in audio_queues:
            while not audio_queues[guild_id].empty():
                try:
                    audio_queues[guild_id].get_nowait()
                except Exception:
                    break
        
        # 현재 재생 중지
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
        
        embed = discord.Embed(
            title="🗑️ 대기열 비움",
            description=f"TTS 대기열이 비워졌습니다. ({cleared_count}개 삭제)",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    # /help - 도움말
    @bot.tree.command(name="help", description="TTS 봇 명령어 도움말을 표시합니다.")
    async def help_command(interaction: discord.Interaction):
        """도움말 명령어"""
        embed = discord.Embed(
            title="📖 TTS 봇 도움말",
            description="텍스트를 음성으로 변환하여 재생하는 봇입니다.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🔧 기본 설정",
            value=(
                "`/setup` - TTS 활성화/비활성화 (토글)\n"
                "`/status` - 현재 설정 확인\n"
                "`/leave` - 음성 채널에서 나가기"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎤 음성 설정",
            value=(
                "`/voice` - 음성 변경 (선희, 인준, 현수)\n"
                "`/speed` - 말하기 속도 변경\n"
                "`/pitch` - 음높이 변경"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ 추가 기능",
            value=(
                "`/readname` - 작성자 이름 읽기 켜기/끄기\n"
                "`/clear` - TTS 대기열 비우기"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 팁",
            value=(
                "• `ㄱㅅ` → 감사, `ㅈㅅ` → 죄송 등 초성 약어 자동 변환\n"
                "• URL은 '링크' 또는 '이미지'로 읽힘\n"
                "• `||스포일러||`는 '스포일러'로 읽힘"
            ),
            inline=False
        )
        
        embed.set_footer(text="음성 채널에 접속 후 설정된 채널에 메시지를 보내면 TTS가 재생됩니다.")
        
        await interaction.response.send_message(embed=embed)
