FROM python:3.10-slim

# FFmpeg 및 필수 시스템 패키지 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출 (Health Check용)
EXPOSE 8000

# 실행 명령
CMD ["python", "bot.py"]
