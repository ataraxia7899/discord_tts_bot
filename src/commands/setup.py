"""
설정 명령어 핸들러 (Command 패턴)

TTS 봇의 설정 관련 명령어를 처리합니다.
"""
import discord
from discord import app_commands
from src.config import Config
from src.handlers.message_handler import invalidate_engine_cache, tts_queues


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
            
            embed = discord.Embed(
                title="🔇 TTS 비활성화",
                description="TTS가 비활성화되었습니다.",
                color=discord.Color.grey()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # TTS 설정 저장
        channel_id = interaction.channel_id
        config.set_guild_settings(guild_id, channel_id, engine.value)
        invalidate_engine_cache(guild_id)
        
        engine_name = "Edge TTS" if engine.value == "edge" else "Google Cloud TTS"
        embed = discord.Embed(
            title="🔊 TTS 활성화",
            description=f"**{engine_name}**로 설정되었습니다.",
            color=discord.Color.green()
        )
        embed.add_field(name="채널", value=f"#{interaction.channel.name}", inline=True)
        embed.set_footer(text="💡 이 채널에 메시지를 보내면 TTS로 읽어줍니다.")
        
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
            engine = settings.get('engine', 'edge')
            engine_name = "Edge TTS" if engine == "edge" else "Google Cloud TTS"
            
            embed = discord.Embed(
                title="📊 TTS 상태",
                description="TTS가 활성화되어 있습니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="채널", value=f"#{channel_name}", inline=True)
            embed.add_field(name="엔진", value=engine_name, inline=True)
            embed.add_field(
                name="작성자 읽기", 
                value="켜짐" if config.get_read_username(guild_id) else "꺼짐", 
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
            title="👋 음성 채널 퇴장",
            description="봇이 음성 채널에서 나갔습니다.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    # /readname - 작성자 이름 읽기 토글
    @bot.tree.command(name="readname", description="메시지 작성자 이름 읽기를 켜거나 끕니다.")
    async def readname(interaction: discord.Interaction):
        """작성자 이름 읽기 토글 명령어"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings:
            embed = discord.Embed(
                title="❌ TTS 비활성화",
                description="먼저 `/setup` 명령어로 TTS를 활성화해주세요.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        current = config.get_read_username(guild_id)
        new_value = not current
        config.set_read_username(guild_id, new_value)
        
        status_text = "켜짐" if new_value else "꺼짐"
        embed = discord.Embed(
            title="👤 작성자 이름 읽기",
            description=f"작성자 이름 읽기가 **{status_text}** 상태로 변경되었습니다.",
            color=discord.Color.green() if new_value else discord.Color.grey()
        )
        await interaction.response.send_message(embed=embed)
    
    # /clear - TTS 대기열 비우기
    @bot.tree.command(name="clear", description="TTS 대기열을 비웁니다.")
    async def clear(interaction: discord.Interaction):
        """TTS 대기열 비우기"""
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
                "`/setup` - TTS 활성화/비활성화 (엔진 선택)\n"
                "`/status` - 현재 설정 확인\n"
                "`/leave` - 음성 채널에서 나가기"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎤 음성 설정 (Edge TTS)",
            value="`/voice` - 음성 변경",
            inline=False
        )
        
        embed.add_field(
            name="☁️ 음성 설정 (Google Cloud TTS)",
            value=(
                "`/gcvoice` - 음성 변경\n"
                "`/gcspeed` - 말하기 속도 변경\n"
                "`/gcpitch` - 음높이 변경"
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
    
    # Edge TTS 음성 변경 명령어
    @bot.tree.command(name="voice", description="Edge TTS 음성을 변경합니다.")
    @app_commands.choices(voice=[
        app_commands.Choice(name="선희 (여성, 기본)", value="ko-KR-SunHiNeural"),
        app_commands.Choice(name="인준 (남성)", value="ko-KR-InJoonNeural"),
        app_commands.Choice(name="현수 (남성)", value="ko-KR-HyunsuNeural"),
    ])
    async def voice(interaction: discord.Interaction, voice: app_commands.Choice[str]):
        """Edge TTS 음성 변경 명령어"""
        guild_id = interaction.guild_id
        settings = config.get_guild_settings(guild_id)
        
        if not settings:
            await interaction.response.send_message(
                "❌ 먼저 `/setup`에서 TTS를 활성화해주세요.",
                ephemeral=True
            )
            return
        
        if settings.get('engine') != 'edge':
            await interaction.response.send_message(
                "❌ 이 명령어는 Edge TTS에서만 사용 가능합니다.",
                ephemeral=True
            )
            return
        
        config.set_voice(guild_id, voice.value)
        invalidate_engine_cache(guild_id)
        
        embed = discord.Embed(
            title="🔊 음성 변경",
            description=f"음성이 **{voice.name}**으로 변경되었습니다.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    # Google Cloud TTS 음성 변경 명령어
    @bot.tree.command(name="gcvoice", description="Google Cloud TTS 음성을 변경합니다.")
    @app_commands.choices(voice=[
        app_commands.Choice(name="Neural2-A (여성)", value="ko-KR-Neural2-A"),
        app_commands.Choice(name="Neural2-B (여성)", value="ko-KR-Neural2-B"),
        app_commands.Choice(name="Neural2-C (남성)", value="ko-KR-Neural2-C"),
        app_commands.Choice(name="Wavenet-A (여성)", value="ko-KR-Wavenet-A"),
        app_commands.Choice(name="Wavenet-B (여성)", value="ko-KR-Wavenet-B"),
        app_commands.Choice(name="Wavenet-C (남성)", value="ko-KR-Wavenet-C"),
        app_commands.Choice(name="Wavenet-D (남성)", value="ko-KR-Wavenet-D"),
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
        
        embed = discord.Embed(
            title="🔊 음성 변경",
            description=f"Google Cloud TTS 음성이 **{voice.name}**으로 변경되었습니다.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    # Google Cloud TTS 속도 설정 명령어
    @bot.tree.command(name="gcspeed", description="Google Cloud TTS 말하기 속도를 변경합니다.")
    @app_commands.describe(speed="속도 (0.25 ~ 4.0, 기본값: 1.0)")
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
