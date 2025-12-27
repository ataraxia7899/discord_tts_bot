"""
gTTS(Google Text-to-Speech) 엔진 구현체

무료로 사용 가능한 Google TTS 서비스를 사용합니다.
"""
from gtts import gTTS
import asyncio
import os
import logging
from .base import TTSEngine

# 로깅 설정
logger = logging.getLogger(__name__)


class GoogleTTSEngine(TTSEngine):
    """
    gTTS(Google Text-to-Speech)를 사용하는 엔진
    
    무료로 사용 가능하며, 한국어 음성을 제공합니다.
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
            # 한국어(ko)로 음성 생성, slow=False로 빠른 속도 사용
            tts = gTTS(text=text, lang='ko', slow=False)
            tts.save(filename)
        except Exception as e:
            logger.error(f"Google TTS 생성 오류: {e}")
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
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._generate_sync, text, filename)
