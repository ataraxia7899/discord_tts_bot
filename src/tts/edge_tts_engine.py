"""
Edge TTS 엔진 구현체 (Strategy 패턴)

Edge TTS를 사용한 음성 합성 기능을 제공합니다.
"""
import os
import asyncio
import logging
from typing import BinaryIO
import edge_tts
from .base import TTSEngine

logger = logging.getLogger(__name__)


class EdgeTTSEngine(TTSEngine):
    """Edge TTS를 사용하는 TTS 엔진 구현체"""
    
    def __init__(
        self, 
        voice: str = "ko-KR-SunHiNeural", 
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ):
        """
        Edge TTS 엔진을 초기화합니다.
        
        Args:
            voice: Edge TTS 목소리 설정
            rate: 말하기 속도 (예: "+0%", "+50%", "-25%")
            pitch: 음높이 (예: "+0Hz", "+50Hz", "-50Hz")
        """
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
    
    async def generate(self, text: str, filename: str) -> None:
        """
        텍스트를 음성 파일로 변환합니다.
        
        Args:
            text: 변환할 텍스트
            filename: 저장할 파일명
        """
        communicate = edge_tts.Communicate(
            text, 
            self.voice, 
            rate=self.rate,
            pitch=self.pitch
        )
        await communicate.save(filename)
    
    async def stream_to_pipe(self, text: str, write_pipe: BinaryIO) -> None:
        """
        TTS를 스트리밍하여 파이프에 직접 기록합니다.
        
        Args:
            text: 변환할 텍스트
            write_pipe: 오디오 데이터를 기록할 파이프 (쓰기 전용)
        """
        loop = asyncio.get_running_loop()
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            pitch=self.pitch
        )
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    # blocking write를 executor에서 실행
                    await loop.run_in_executor(
                        None, 
                        lambda data=chunk["data"]: (
                            write_pipe.write(data),
                            write_pipe.flush()
                        )
                    )
        except Exception as e:
            logger.error(f"TTS 스트리밍 오류: {e}")
        finally:
            await loop.run_in_executor(None, write_pipe.close)
