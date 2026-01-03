"""
설정 관리 모듈 (Singleton 패턴 적용)

봇의 전역 설정을 관리하는 Singleton 클래스입니다.
환경 변수 로드, 길드별 설정 저장/조회 기능을 제공합니다.
"""
import os
import json
import logging
from typing import Dict, Optional, Any
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)


class Config:
    """
    봇 설정을 관리하는 Singleton 클래스
    """
    _instance: Optional['Config'] = None
    
    # 상수 정의
    SETTINGS_FILE = "guild_settings.json"
    DEFAULT_VOICE = "ko-KR-SunHiNeural"
    DEFAULT_SPEED = "+0%"
    DEFAULT_PITCH = "+0Hz"
    
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
        
        # 토큰 검증
        if not self.discord_token:
            raise ValueError(
                "DISCORD_BOT_TOKEN 환경 변수가 설정되지 않았습니다. "
                ".env 파일에 DISCORD_BOT_TOKEN=your_token 형식으로 추가해주세요."
            )
        
        # 길드별 설정 저장소: {guild_id: {'channel_id': int, 'voice': str, ...}}
        self.guild_settings: Dict[int, Dict[str, Any]] = {}
        
        # 저장된 설정 로드
        self._load_settings()
        
        self._initialized = True
    
    def _load_settings(self):
        """JSON 파일에서 길드 설정을 로드합니다."""
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 문자열 키를 정수로 변환
                    self.guild_settings = {int(k): v for k, v in data.items()}
            except Exception as e:
                logger.error(f"설정 파일 로드 중 오류 발생: {e}")
                self.guild_settings = {}
    
    def _save_settings(self):
        """현재 길드 설정을 JSON 파일에 저장합니다."""
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.guild_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"설정 파일 저장 중 오류 발생: {e}")
    
    def set_guild_settings(self, guild_id: int, channel_id: int) -> None:
        """
        길드의 TTS 설정을 저장합니다.
        
        Args:
            guild_id: 길드 ID
            channel_id: TTS를 사용할 채널 ID
        """
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = {}
        
        self.guild_settings[guild_id]['channel_id'] = channel_id
        self._save_settings()
    
    def remove_guild_settings(self, guild_id: int) -> None:
        """길드의 TTS 설정을 제거합니다."""
        if guild_id in self.guild_settings:
            del self.guild_settings[guild_id]
            self._save_settings()
    
    def get_guild_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """길드의 TTS 설정을 조회합니다."""
        return self.guild_settings.get(guild_id)
    
    # 음성 설정
    def set_voice(self, guild_id: int, voice: str) -> None:
        """길드의 TTS 음성을 설정합니다."""
        if guild_id in self.guild_settings:
            self.guild_settings[guild_id]['voice'] = voice
            self._save_settings()
    
    def get_voice(self, guild_id: int) -> str:
        """길드의 TTS 음성을 반환합니다."""
        settings = self.guild_settings.get(guild_id, {})
        return settings.get('voice', self.DEFAULT_VOICE)
    
    # 속도 설정
    def set_speed(self, guild_id: int, speed: str) -> None:
        """길드의 TTS 속도를 설정합니다."""
        if guild_id in self.guild_settings:
            self.guild_settings[guild_id]['speed'] = speed
            self._save_settings()
    
    def get_speed(self, guild_id: int) -> str:
        """길드의 TTS 속도를 반환합니다."""
        settings = self.guild_settings.get(guild_id, {})
        return settings.get('speed', self.DEFAULT_SPEED)
    
    # 작성자 이름 읽기 설정
    def set_read_username(self, guild_id: int, enabled: bool) -> None:
        """길드의 작성자 이름 읽기 설정을 변경합니다."""
        if guild_id in self.guild_settings:
            self.guild_settings[guild_id]['read_username'] = enabled
            self._save_settings()
    
    def get_read_username(self, guild_id: int) -> bool:
        """길드의 작성자 이름 읽기 설정을 반환합니다."""
        settings = self.guild_settings.get(guild_id, {})
        return settings.get('read_username', False)  # 기본값: 꺼짐
    
    # 피치 설정
    def set_pitch(self, guild_id: int, pitch: str) -> None:
        """길드의 TTS 피치를 설정합니다."""
        if guild_id in self.guild_settings:
            self.guild_settings[guild_id]['pitch'] = pitch
            self._save_settings()
    
    def get_pitch(self, guild_id: int) -> str:
        """길드의 TTS 피치를 반환합니다."""
        settings = self.guild_settings.get(guild_id, {})
        return settings.get('pitch', self.DEFAULT_PITCH)

