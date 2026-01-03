# 멀티스테이지 빌드로 이미지 크기 최적화
FROM python:3.10-slim AS builder

WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# 실행 이미지
FROM python:3.10-slim

# FFmpeg 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 빌더에서 설치된 패키지 복사
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 애플리케이션 코드 복사
COPY . .

# 비루트 사용자로 실행 (보안)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 실행 명령
CMD ["python", "bot.py"]
