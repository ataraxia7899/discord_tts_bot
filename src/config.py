"""
설정 관리 모듈 (Singleton 패턴 적용)

봇의 전역 설정을 관리하는 Singleton 클래스입니다.
환경 변수 로드, 길드별 설정 저장/조회 기능을 제공합니다.
"""
import os
from typing import Dict, Optional
from dotenv import load_dotenv


class Config:
    """
    봇 설정을 관리하는 Singleton 클래스
    """
    _instance: Optional['Config'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # 이미 초기화된 경우 재초기화 방지
        if self._initialized:
            return
            
        # .env 파일에서 환경 변수 로드
        load_dotenv()
        
        # Discord 봇 토큰
        self.discord_token = os.getenv("DISCORD_BOT_TOKEN")
        
        # Edge TTS 목소리 설정
        self.edge_voice = "ko-KR-SunHiNeural"
        
        # 길드별 설정 저장소: {guild_id: {'channel_id': int, 'engine': str}}
        self.guild_settings: Dict[int, Dict[str, any]] = {}
        
        self._initialized = True
    
    def set_guild_settings(self, guild_id: int, channel_id: int, engine: str):
        """
        길드의 TTS 설정을 저장합니다.
        
        Args:
            guild_id: 길드 ID
            channel_id: TTS를 사용할 채널 ID
            engine: TTS 엔진 종류 ('edge' 또는 'local')
        """
        self.guild_settings[guild_id] = {
            'channel_id': channel_id,
            'engine': engine
        }
    
    def get_guild_settings(self, guild_id: int) -> Optional[Dict[str, any]]:
        """
        길드의 TTS 설정을 조회합니다.
        
        Args:
            guild_id: 길드 ID
            
        Returns:
            설정 딕셔너리 또는 None
        """
        return self.guild_settings.get(guild_id)
    
    def get_engine_type(self, guild_id: int) -> str:
        """
        길드의 TTS 엔진 종류를 반환합니다.
        
        Args:
            guild_id: 길드 ID
            
        Returns:
            TTS 엔진 종류 ('edge' 또는 'local', 기본값: 'edge')
        """
        settings = self.get_guild_settings(guild_id)
        return settings['engine'] if settings else 'edge'
