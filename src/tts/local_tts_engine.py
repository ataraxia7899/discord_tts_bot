"""
Local TTS 엔진 구현체 (Strategy 패턴)

pyttsx3를 사용한 로컬 음성 합성 기능을 제공합니다.
"""
import pyttsx3
import asyncio
from .base import TTSEngine


class LocalTTSEngine(TTSEngine):
    """
    pyttsx3를 사용하는 로컬 TTS 엔진 구현체
    """
    
    def __init__(self, rate: int = 200):
        """
        Local TTS 엔진을 초기화합니다.
        
        Args:
            rate: 음성 속도 (기본값: 200)
        """
        self.rate = rate
    
    def _generate_sync(self, text: str, filename: str):
        """
        동기 방식으로 TTS를 생성합니다.
        
        pyttsx3는 동기 라이브러리이므로 별도 메서드로 분리했습니다.
        
        Args:
            text: 변환할 텍스트
            filename: 저장할 파일명
        """
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
            engine.save_to_file(text, filename)
            engine.runAndWait()
        except Exception as e:
            print(f"Local TTS Error: {e}")
            raise
    
    async def generate(self, text: str, filename: str):
        """
        Local TTS를 사용하여 텍스트를 음성 파일로 변환합니다.
        
        동기 함수를 별도 스레드에서 실행하여 봇이 멈추지 않도록 합니다.
        
        Args:
            text: 변환할 텍스트
            filename: 저장할 파일명
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._generate_sync, text, filename)
