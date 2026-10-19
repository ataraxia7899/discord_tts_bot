"""Edge TTS 생성: 요청 직렬화, 제한된 재시도 및 공통 429 대기시간."""
import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
import math
from pathlib import Path
import random

import aiohttp
import edge_tts
from edge_tts.exceptions import NoAudioReceived

from .base import TTSEngine

logger = logging.getLogger(__name__)
_generation_semaphore = asyncio.Semaphore(1)
_cooldown_until = 0.0
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2.0
MAX_RETRY_DELAY = 30.0
REQUEST_TIMEOUT = 60.0


def retry_after_seconds(value: str | None) -> float:
    """Retry-After의 초 단위 값과 HTTP-date를 모두 지원합니다."""
    if not value:
        return 0.0
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            seconds = (date - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return 0.0
    return max(0.0, seconds) if math.isfinite(seconds) else 0.0


class EdgeTTSEngine(TTSEngine):
    def __init__(self, voice: str = "ko-KR-SunHiNeural",
                 rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def generate(self, text: str, filename: str) -> None:
        """완성된 음성만 반환합니다. 실패·취소 시 부분 파일을 삭제합니다."""
        global _cooldown_until
        path = Path(filename)
        try:
            # 모든 길드의 요청을 직렬화합니다. 백오프 중에도 슬롯을 유지합니다.
            async with _generation_semaphore:
                for attempt in range(MAX_RETRIES + 1):
                    remaining = _cooldown_until - asyncio.get_running_loop().time()
                    if remaining > 0:
                        await asyncio.sleep(remaining)
                    try:
                        # Communicate는 재사용할 수 없으므로 매 시도마다 새로 만듭니다.
                        communicate = edge_tts.Communicate(
                            text, self.voice, rate=self.rate, pitch=self.pitch
                        )
                        async with asyncio.timeout(REQUEST_TIMEOUT):
                            await communicate.save(filename)
                        if not path.is_file() or path.stat().st_size == 0:
                            raise NoAudioReceived("TTS returned no audio data")
                        return
                    except (aiohttp.ClientError, TimeoutError, NoAudioReceived) as error:
                        status = getattr(error, "status", None)
                        retryable = (
                            status in (429, 500, 502, 503, 504)
                            or isinstance(error, (aiohttp.ClientConnectionError,
                                                  TimeoutError, NoAudioReceived))
                        )
                        if not retryable:
                            raise
                        delay = min(MAX_RETRY_DELAY, BASE_RETRY_DELAY * 2 ** attempt)
                        delay += random.uniform(0.0, 1.0)
                        if status == 429:
                            headers = getattr(error, "headers", None) or {}
                            delay = max(delay, retry_after_seconds(headers.get("Retry-After")))
                            # 최종 실패나 /clear 취소 뒤에도 다른 길드의 요청을 늦춥니다.
                            _cooldown_until = max(
                                _cooldown_until, asyncio.get_running_loop().time() + delay
                            )
                        if attempt == MAX_RETRIES:
                            raise
                        logger.warning(
                            "TTS 요청 실패 (%s, status=%s). %.1f초 후 재시도 %s/%s",
                            type(error).__name__, status, delay, attempt + 1, MAX_RETRIES,
                        )
                        if status != 429:
                            await asyncio.sleep(delay)
        except BaseException:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.exception("TTS 부분 파일 삭제 실패")
            raise
