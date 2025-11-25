"""
Google Cloud TTS 엔진 구현체

Google Cloud Text-to-Speech API를 사용하여 고품질 Neural2 음성을 제공합니다.
환경 변수에서 JSON 키를 읽어 인증합니다.
"""
from google.cloud import texttospeech
from google.oauth2 import service_account
import asyncio
import os
import json
from .base import TTSEngine


class GoogleCloudTTSEngine(TTSEngine):
    """
    Google Cloud Text-to-Speech API를 사용하는 엔진
    
    고품질 Neural2 음성을 제공하며, 음성 종류, 속도, 피치를 세밀하게 조정할 수 있습니다.
    """
    
    def __init__(self, voice_name: str = "ko-KR-Neural2-A", 
                 speaking_rate: float = 1.0, 
                 pitch: float = 0.0):
        """
        Google Cloud TTS 엔진을 초기화합니다.
        
        Args:
            voice_name: 음성 종류 (예: ko-KR-Neural2-A, ko-KR-Neural2-B, ko-KR-Neural2-C)
            speaking_rate: 말하기 속도 (0.25 ~ 4.0, 기본값: 1.0)
            pitch: 피치 (-20.0 ~ 20.0, 기본값: 0.0)
        """
        # 환경 변수에서 Google Cloud 인증 정보 로드
        credentials_json = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON")
        
        if not credentials_json:
            raise ValueError(
                "GOOGLE_CLOUD_CREDENTIALS_JSON 환경 변수가 설정되지 않았습니다. "
                ".env 파일에 Google Cloud 서비스 계정 JSON 키를 추가해주세요."
            )
        
        try:
            # JSON 문자열을 딕셔너리로 파싱
            credentials_dict = json.loads(credentials_json)
            
            # 서비스 계정 인증 정보 생성
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict
            )
            
            # Google Cloud TTS 클라이언트 생성
            self.client = texttospeech.TextToSpeechClient(credentials=credentials)
            
        except json.JSONDecodeError as e:
            raise ValueError(
                f"GOOGLE_CLOUD_CREDENTIALS_JSON 환경 변수의 JSON 형식이 올바르지 않습니다: {e}"
            )
        except Exception as e:
            raise ValueError(
                f"Google Cloud TTS 클라이언트 초기화 중 오류 발생: {e}"
            )
        
        # 음성 설정
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name=voice_name
        )
        
        # 오디오 설정
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch
        )
    
    def _generate_sync(self, text: str, filename: str):
        """
        동기 방식으로 Google Cloud TTS를 생성합니다.
        
        Args:
            text: 변환할 텍스트
            filename: 저장할 파일명
        """
        try:
            # 입력 텍스트 설정
            input_text = texttospeech.SynthesisInput(text=text)
            
            # TTS 생성 요청
            response = self.client.synthesize_speech(
                input=input_text,
                voice=self.voice,
                audio_config=self.audio_config
            )
            
            # 오디오 파일 저장
            with open(filename, "wb") as out:
                out.write(response.audio_content)
                
        except Exception as e:
            print(f"Google Cloud TTS 생성 오류: {e}")
            raise
    
    async def generate(self, text: str, filename: str):
        """
        텍스트를 음성 파일로 변환합니다 (비동기 래퍼).
        
        동기 함수를 별도 스레드에서 실행하여 봇이 멈추지 않도록 합니다.
        
        Args:
            text: 변환할 텍스트
            filename: 저장할 파일명
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._generate_sync, text, filename)
    
    def update_voice(self, voice_name: str):
        """
        음성 종류를 변경합니다.
        
        Args:
            voice_name: 새로운 음성 종류
        """
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name=voice_name
        )
    
    def update_speed(self, speaking_rate: float):
        """
        말하기 속도를 변경합니다.
        
        Args:
            speaking_rate: 새로운 속도 (0.25 ~ 4.0)
        """
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=self.audio_config.pitch
        )
    
    def update_pitch(self, pitch: float):
        """
        피치를 변경합니다.
        
        Args:
            pitch: 새로운 피치 (-20.0 ~ 20.0)
        """
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=self.audio_config.speaking_rate,
            pitch=pitch
        )
