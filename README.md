# Discord TTS Bot

텍스트를 음성으로 변환하여 Discord 음성 채널에서 재생하는 봇입니다.

## 주요 기능

- **텍스트 음성 변환**: 채널에 작성된 메시지를 음성으로 변환하여 재생
- **Edge TTS**: 고품질 무료 클라우드 TTS (Microsoft)
- **한국어 초성 약어 변환**: `ㄱㅅ` → "감사", `ㅈㅅ` → "죄송" 등 자동 변환
- **반복 문자 단축**: `ㅋㅋㅋㅋㅋ` → `크크크`로 자연스럽게 읽기
- **다양한 텍스트 처리**: 이미지/링크, 이모지, 스포일러 태그, 멘션, 숫자 등
- **설정 영구 저장**: 서버별 설정이 JSON 파일에 저장되어 봇 재시작 후에도 유지
- **자동 음성 채널 관리**: 모두 나가면 자동 퇴장

## 기술 스택

- **Python 3.10+**
- **discord.py 2.3+**: Discord 봇 API
- **edge-tts 6.1+**: Microsoft Edge TTS 엔진
- **python-dotenv 1.0+**: 환경 변수 관리

## 프로젝트 구조

```
discord_tts_bot/
├── bot.py                 # 메인 진입점
├── Dockerfile             # Docker 컨테이너 설정
├── requirements.txt       # 의존성 목록
├── guild_settings.json    # 서버별 설정 저장 (자동 생성)
├── .env                   # 환경 변수 (비공개)
└── src/
    ├── config.py          # 설정 관리 (Singleton)
    ├── tts/               # TTS 엔진 (Strategy)
    │   ├── __init__.py
    │   ├── base.py
    │   └── edge_tts_engine.py
    ├── commands/          # 명령어 핸들러 (Command)
    │   ├── __init__.py
    │   └── setup.py
    ├── handlers/          # 이벤트 핸들러
    │   ├── __init__.py
    │   ├── message_handler.py
    │   └── voice_handler.py
    └── utils/             # 유틸리티
        ├── __init__.py
        └── text_preprocessor.py
```

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/ataraxia7899/discord_tts_bot.git
cd discord_tts_bot
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 아래 내용을 추가:

```env
DISCORD_BOT_TOKEN="your_discord_bot_token_here"
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 봇 실행

```bash
python bot.py
```

## 사용 방법

### 명령어

| 명령어 | 설명 |
|--------|------|
| `/setup` | TTS 활성화/비활성화 (토글) |
| `/voice` | 음성 변경 (선희, 인준, 현수) |
| `/speed` | 말하기 속도 변경 (-50% ~ +100%) |
| `/pitch` | 음높이 변경 (-50Hz ~ +50Hz) |
| `/status` | 현재 설정 확인 |
| `/leave` | 음성 채널에서 나가기 |
| `/readname` | 작성자 이름 읽기 켜기/끄기 |
| `/clear` | TTS 대기열 비우기 |
| `/help` | 명령어 도움말 |

### 한국어 초성 약어 변환

| 초성 | 변환 결과 |
|------|----------|
| `ㄱㅅ` | 감사 |
| `ㅈㅅ` | 죄송 |
| `ㅋㅋ` | 크크 |
| `ㅎㅎ` | 하하 |
| `ㄱㄱ` | 고고 |
| `ㄴㄴ` | 노노 |

### 텍스트 처리 예시

| 입력 | 변환 결과 |
|------|----------|
| `ㅋㅋㅋㅋㅋㅋ` | 크크크 |
| `https://example.com` | 링크 |
| `https://example.com/image.jpg` | 이미지 |
| `||스포일러||` | 스포일러 |
| `<:pepe:123456>` | pepe |
| `@사용자` | 사용자 |
| `#채널` | 채널 |

## 환경 변수

| 변수명 | 필수 | 설명 |
|--------|------|------|
| `DISCORD_BOT_TOKEN` | ✅ | Discord 봇 토큰 |

## 라이선스

MIT License