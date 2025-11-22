# Discord TTS Bot

Discord 음성 채널에서 텍스트를 음성으로 변환하여 재생하는 봇입니다. Edge TTS와 Local TTS 두 가지 엔진을 지원하며, 디자인 패턴을 적용하여 유지보수성과 확장성을 높였습니다.

## 주요 기능

- **텍스트 음성 변환**: 채널에 작성된 메시지를 음성으로 변환하여 재생
- **다중 TTS 엔진 지원**:
  - **Edge TTS**: 고품질 음성 합성 (약간 느림)
  - **Local TTS**: 빠른 속도의 로컬 음성 합성 (기계음)
- **자동 음성 채널 관리**: 사용자가 있을 때만 채널에 머무르고, 모두 나가면 자동 퇴장
- **길드별 설정**: 각 서버마다 독립적인 설정 관리

## 기술 스택

- **Python 3.8+**
- **discord.py 2.3+**: Discord 봇 API
- **edge-tts 6.1+**: Microsoft Edge TTS 엔진
- **pyttsx3 2.90+**: 로컬 TTS 엔진
- **python-dotenv 1.0+**: 환경 변수 관리

## 디자인 패턴

이 프로젝트는 소프트웨어 공학 베스트 프랙티스를 적용하여 구조화되었습니다:

### Singleton 패턴
- **위치**: `src/config.py`
- **목적**: 애플리케이션 전역에서 하나의 설정 인스턴스만 존재하도록 보장
- **효과**: 일관된 설정 접근 및 메모리 효율성

### Strategy 패턴
- **위치**: `src/tts/`
- **목적**: TTS 엔진을 런타임에 동적으로 선택 가능
- **효과**: 새로운 TTS 엔진 추가가 용이하며, 기존 코드 수정 불필요

### Command 패턴
- **위치**: `src/commands/`
- **목적**: 명령어 로직을 독립적인 모듈로 분리
- **효과**: 새로운 명령어 추가 시 기존 코드에 영향 없음

## 프로젝트 구조

```
discord_tts_bot/
├── .env                     # 환경 변수 (토큰 저장)
├── .gitignore               # Git 제외 파일 목록
├── requirements.txt         # Python 패키지 의존성
├── bot.py                   # 메인 봇 실행 파일
├── README.md               # 프로젝트 설명서 (현재 파일)
└── src/                    # 소스 코드 모듈
    ├── __init__.py
    ├── config.py           # 설정 관리 (Singleton)
    ├── tts/                # TTS 엔진 모듈 (Strategy)
    │   ├── __init__.py
    │   ├── base.py         # TTS 엔진 인터페이스
    │   ├── edge_tts_engine.py  # Edge TTS 구현
    │   └── local_tts_engine.py # Local TTS 구현
    ├── commands/           # 명령어 핸들러 (Command)
    │   ├── __init__.py
    │   └── setup.py        # /setup 명령어
    └── handlers/           # 이벤트 핸들러
        ├── __init__.py
        ├── message_handler.py   # 메시지 처리
        └── voice_handler.py     # 음성 상태 처리
```

## 설치 방법

### 1. 저장소 클론
```bash
git clone <repository-url>
cd discord_tts_bot
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`.env` 파일을 생성하고 Discord 봇 토큰을 입력합니다:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

### 4. Discord 봇 생성
1. [Discord Developer Portal](https://discord.com/developers/applications)에 접속
2. "New Application" 클릭하여 새 애플리케이션 생성
3. "Bot" 메뉴에서 봇 생성 및 토큰 복사
4. "OAuth2" > "URL Generator"에서 다음 권한 선택:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Connect`, `Speak`, `Use Voice Activity`
5. 생성된 URL로 봇을 서버에 초대

## 사용 방법

### 1. 봇 실행
```bash
python bot.py
```

### 2. TTS 설정
Discord 서버에서 `/setup` 명령어를 실행하여 TTS를 사용할 채널과 엔진을 선택합니다:
- **채널**: 명령어를 실행한 채널이 TTS 채널로 설정됩니다
- **엔진 옵션**:
  - `Edge TTS (고품질, 약간 느림)`: Microsoft Edge TTS 엔진
  - `Local TTS (기계음, 속도 최우선)`: pyttsx3 로컬 엔진

### 3. TTS 사용
1. 음성 채널에 입장합니다
2. 설정한 텍스트 채널에 메시지를 작성합니다
3. 봇이 자동으로 음성 채널에 입장하여 메시지를 음성으로 재생합니다

### 4. 자동 퇴장
- 음성 채널에서 모든 사용자가 나가면 봇도 자동으로 퇴장합니다
- TTS 큐는 자동으로 초기화됩니다

## 명령어

| 명령어 | 설명 | 사용 예시 |
|--------|------|-----------|
| `/setup` | TTS 채널 및 엔진 설정 | `/setup engine:Edge TTS` |

## 환경 변수

| 변수명 | 설명 | 필수 여부 |
|--------|------|-----------|
| `DISCORD_BOT_TOKEN` | Discord 봇 토큰 | 필수 |

## 개발 가이드

### 새로운 TTS 엔진 추가
1. `src/tts/` 디렉토리에 새 파일 생성 (예: `google_tts_engine.py`)
2. `TTSEngine` 추상 클래스를 상속받아 구현:
```python
from .base import TTSEngine

class GoogleTTSEngine(TTSEngine):
    async def generate(self, text: str, filename: str):
        # Google TTS 구현
        pass
```
3. `src/tts/__init__.py`에 추가
4. `src/handlers/message_handler.py`에서 엔진 선택 로직 업데이트

### 새로운 명령어 추가
1. `src/commands/` 디렉토리에 새 파일 생성 (예: `voice.py`)
2. `register_commands` 함수 내에 명령어 정의
3. `bot.py`에서 새 명령어 등록 함수 호출

## 트러블슈팅

### FFmpeg 오류
봇 실행 시 FFmpeg 관련 오류가 발생하면:
1. [FFmpeg 다운로드](https://ffmpeg.org/download.html)
2. 시스템 PATH에 FFmpeg 추가
3. 봇 재시작

### 봇이 음성 채널에 입장하지 않음
- 봇 권한 확인: `Connect`, `Speak` 권한 필요
- 사용자가 음성 채널에 있는지 확인
- `/setup` 명령어로 올바른 채널이 설정되었는지 확인

### TTS가 재생되지 않음
- FFmpeg가 설치되어 있는지 확인
- `.env` 파일에 올바른 토큰이 설정되었는지 확인
- 봇 인텐트 설정 확인: `message_content`, `voice_states` 활성화 필요

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 기여

버그 리포트, 기능 제안, Pull Request를 환영합니다!