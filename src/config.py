"""
설정 관리 모듈 (Singleton 패턴 적용)

봇의 전역 설정을 관리하는 Singleton 클래스입니다.
환경 변수 로드, 길드별 설정 저장/조회 기능을 제공합니다.
"""
import os
import json
from typing import Dict, Optional, Any
from dotenv import load_dotenv


class Config:
    """
    봇 설정을 관리하는 Singleton 클래스
    """
    _instance: Optional['Config'] = None
    
    # 상수 정의
    SETTINGS_FILE = "guild_settings.json"
    
    # 기본 Google Cloud TTS 설정
    DEFAULT_GC_VOICE = "ko-KR-Neural2-A"
    DEFAULT_GC_SPEED = 1.0
    DEFAULT_GC_PITCH = 0.0
    
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
        
        # Google Cloud 인증 정보 (환경 변수에서 로드)
        self.google_cloud_credentials_json = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON")
        
        # 길드별 설정 저장소
        # 구조: {guild_id: {channel_id, engine, gc_voice, gc_speed, gc_pitch}}
        self.guild_settings: Dict[int, Dict[str, Any]] = {}
        
        # 저장된 설정 로드
        self._load_settings()
        
        self._initialized = True
    
    def _load_settings(self):
        """
        JSON 파일에서 길드 설정을 로드합니다.
        기존 형식(단순 int)과 새 형식(dict) 모두 지원합니다.
        """
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 데이터 형식에 따라 처리
                    for guild_id_str, value in data.items():
                        guild_id = int(guild_id_str)
                        
                        # 기존 형식 (단순 int: channel_id)
                        if isinstance(value, int):
                            self.guild_settings[guild_id] = {
                                "channel_id": value,
                                "engine": "gtts",  # 기본값
                                "gc_voice": self.DEFAULT_GC_VOICE,
                                "gc_speed": self.DEFAULT_GC_SPEED,
                                "gc_pitch": self.DEFAULT_GC_PITCH
                            }
                        # 새 형식 (dict)
                        elif isinstance(value, dict):
                            # 기본값 설정
                            self.guild_settings[guild_id] = {
                                "channel_id": value.get("channel_id"),
                                "engine": value.get("engine", "gtts"),
                                "gc_voice": value.get("gc_voice", self.DEFAULT_GC_VOICE),
                                "gc_speed": value.get("gc_speed", self.DEFAULT_GC_SPEED),
                                "gc_pitch": value.get("gc_pitch", self.DEFAULT_GC_PITCH)
                            }
            except Exception as e:
                print(f"설정 파일 로드 중 오류 발생: {e}")
                self.guild_settings = {}
    
    def _save_settings(self):
        """
        현재 길드 설정을 JSON 파일에 저장합니다.
        """
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.guild_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"설정 파일 저장 중 오류 발생: {e}")
    
    def set_guild_settings(self, guild_id: int, channel_id: int, engine: str = "gtts"):
        """
        길드의 TTS 설정을 저장합니다.
        
        Args:
            guild_id: 길드 ID
            channel_id: TTS를 사용할 채널 ID
            engine: TTS 엔진 ("gtts" 또는 "gctts")
        """
        # 기존 설정이 있으면 유지, 없으면 기본값 사용
        if guild_id in self.guild_settings:
            self.guild_settings[guild_id]["channel_id"] = channel_id
            self.guild_settings[guild_id]["engine"] = engine
        else:
            self.guild_settings[guild_id] = {
                "channel_id": channel_id,
                "engine": engine,
                "gc_voice": self.DEFAULT_GC_VOICE,
                "gc_speed": self.DEFAULT_GC_SPEED,
                "gc_pitch": self.DEFAULT_GC_PITCH
            }
        
        # 파일에 저장
        self._save_settings()
    
    def remove_guild_settings(self, guild_id: int):
        """
        길드의 TTS 설정을 제거합니다.
        
        Args:
            guild_id: 길드 ID
        """
        if guild_id in self.guild_settings:
            del self.guild_settings[guild_id]
            # 파일에 저장
            self._save_settings()
    
    def get_guild_channel(self, guild_id: int) -> Optional[int]:
        """
        길드의 TTS 채널 ID를 조회합니다.
        
        Args:
            guild_id: 길드 ID
            
        Returns:
            채널 ID 또는 None
        """
        settings = self.guild_settings.get(guild_id)
        if settings:
            return settings.get("channel_id")
        return None
    
    def get_guild_engine(self, guild_id: int) -> str:
        """
        길드의 TTS 엔진 타입을 조회합니다.
        
        Args:
            guild_id: 길드 ID
            
        Returns:
            엔진 타입 ("gtts" 또는 "gctts"), 기본값 "gtts"
        """
        settings = self.guild_settings.get(guild_id)
        if settings:
            return settings.get("engine", "gtts")
        return "gtts"
    
    def set_gc_voice(self, guild_id: int, voice_name: str):
        """
        길드의 Google Cloud TTS 음성을 설정합니다.
        
        Args:
            guild_id: 길드 ID
            voice_name: 음성 이름 (예: ko-KR-Neural2-A)
        """
        if guild_id in self.guild_settings:
            self.guild_settings[guild_id]["gc_voice"] = voice_name
            self._save_settings()
    
    def set_gc_speed(self, guild_id: int, speed: float):
        """
        길드의 Google Cloud TTS 속도를 설정합니다.
        
        Args:
            guild_id: 길드 ID
            speed: 속도 (0.25 ~ 4.0)
        """
        if guild_id in self.guild_settings:
            self.guild_settings[guild_id]["gc_speed"] = speed
            self._save_settings()
    
    def set_gc_pitch(self, guild_id: int, pitch: float):
        """
        길드의 Google Cloud TTS 피치를 설정합니다.
        
        Args:
            guild_id: 길드 ID
            pitch: 피치 (-20.0 ~ 20.0)
        """
        if guild_id in self.guild_settings:
            self.guild_settings[guild_id]["gc_pitch"] = pitch
            self._save_settings()
    
    def get_gc_settings(self, guild_id: int) -> Dict[str, Any]:
        """
        길드의 Google Cloud TTS 설정을 조회합니다.
        
        Args:
            guild_id: 길드 ID
            
        Returns:
            {voice, speed, pitch} 딕셔너리
        """
        settings = self.guild_settings.get(guild_id, {})
        return {
            "voice": settings.get("gc_voice", self.DEFAULT_GC_VOICE),
            "speed": settings.get("gc_speed", self.DEFAULT_GC_SPEED),
            "pitch": settings.get("gc_pitch", self.DEFAULT_GC_PITCH)
        }
