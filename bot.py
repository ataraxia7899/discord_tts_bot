"""
Discord TTS Bot

텍스트를 음성으로 변환하여 재생하는 Discord 봇입니다.

디자인 패턴:
- Singleton: 설정 관리 (Config)
- Strategy: TTS 엔진 (EdgeTTSEngine, LocalTTSEngine)
- Command: 명령어 핸들러
"""
import discord
from discord.ext import commands
from src.config import Config
from src.commands import register_commands
from src.handlers import register_message_handler, register_voice_handler


class TTSBot(commands.Bot):
    """
    TTS 기능을 제공하는 Discord Bot 클래스
    """
    
    def __init__(self):
        """봇 초기화"""
        # 인텐트 설정
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(command_prefix="!", intents=intents)
    
    async def setup_hook(self):
        """봇 시작 시 실행되는 설정 훅"""
        await self.tree.sync()
        print(f"Logged in as {self.user}")


def main():
    """메인 함수"""
    # 설정 로드
    config = Config()
    
    # 봇 인스턴스 생성
    bot = TTSBot()
    
    # 명령어 및 이벤트 핸들러 등록
    register_commands(bot)
    register_message_handler(bot)
    register_voice_handler(bot)
    
    # 봇 실행
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()