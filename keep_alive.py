"""
Keep Alive 모듈

Koyeb Health Check를 통과하기 위한 간단한 Flask 웹 서버입니다.
외부에서 주기적으로 ping을 보내 인스턴스가 Sleep 상태로 전환되는 것을 방지합니다.
"""
from flask import Flask
from threading import Thread
import logging

# Flask 로깅 비활성화 (Discord 봇 로그와 분리)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)


@app.route('/')
def home():
    """Health Check 엔드포인트"""
    return "Discord TTS Bot is alive!"


@app.route('/health')
def health():
    """Health Check 엔드포인트 (대체)"""
    return {"status": "healthy"}, 200


def run():
    """Flask 서버 실행 (포트 8000)"""
    app.run(host='0.0.0.0', port=8000)


def keep_alive():
    """
    백그라운드 스레드에서 Flask 서버를 시작합니다.
    봇 시작 전에 호출하세요.
    """
    t = Thread(target=run, daemon=True)
    t.start()
    print("Keep-alive 서버가 시작되었습니다. (포트: 8000)")
