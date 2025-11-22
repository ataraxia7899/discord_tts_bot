"""
Local TTS 엔진 구현체 (gTTS로 대체)
기존 pyttsx3가 서버 호환성 문제가 많아, 안정적인 Google TTS로 기능을 변경했습니다.
"""
from gtts import gTTS
import asyncio
import os
from .base import TTSEngine


class GoogleTTSEngine(TTSEngine):
    """
    gTTS(Google Text-to-Speech)를 사용하는 엔진
    """
    
    def __init__(self, rate: int = 200):
        """
        Google TTS 엔진을 초기화합니다.
        
        Args:
            rate: gTTS는 속도 조절을 기본적으로 지원하지 않아 무시됩니다.
        """
        # gTTS는 속도 조절을 기본적으로 지원하지 않아 rate는 무시합니다.
        pass
    
    def _generate_sync(self, text: str, filename: str):
        """
        동기 방식으로 Google TTS를 생성합니다.
        
        Args:
            text: 변환할 텍스트
            filename: 저장할 파일명
        """
        try:
            # 한국어(ko)로 음성 생성
            tts = gTTS(text=text, lang='ko')
            tts.save(filename)
        except Exception as e:
            print(f"Google TTS 생성 오류: {e}")
            # 오류 발생 시 빈 파일이라도 생성 방지 (상위 핸들러 처리를 위해)
            if os.path.exists(filename):
                os.remove(filename)
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
