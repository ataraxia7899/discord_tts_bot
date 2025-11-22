"""
TTS 엔진 기본 인터페이스 (Strategy 패턴)

모든 TTS 엔진이 구현해야 하는 추상 클래스입니다.
"""
from abc import ABC, abstractmethod


class TTSEngine(ABC):
    """
    TTS 엔진의 기본 인터페이스
    
    모든 TTS 엔진 구현체는 이 클래스를 상속받아야 합니다.
    """
    
    @abstractmethod
    async def generate(self, text: str, filename: str):
        """
        텍스트를 음성 파일로 변환합니다.
        
        Args:
            text: 변환할 텍스트
            filename: 저장할 파일명
        """
        pass
