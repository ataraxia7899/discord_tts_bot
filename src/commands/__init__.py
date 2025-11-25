"""
명령어 패키지

모든 봇 명령어를 등록합니다.
"""
from .setup import register_setup_commands
from .gc_voice import register_gcvoice_command
from .gc_speed import register_gcspeed_command
from .gc_pitch import register_gcpitch_command


def register_commands(bot):
    """
    봇에 모든 명령어를 등록합니다.
    
    Args:
        bot: Discord Bot 인스턴스
    """
    register_setup_commands(bot)
    register_gcvoice_command(bot)
    register_gcspeed_command(bot)
    register_gcpitch_command(bot)
