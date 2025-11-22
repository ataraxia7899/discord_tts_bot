# Discord TTS Bot (Google Cloud Edition)

> [!IMPORTANT]
> **Google Cloud 호스팅 전용 브랜치**
> 
> 이 버전은 Google Cloud 환경에서의 호환성을 위해 **Google TTS (gTTS)** 만을 사용하도록 수정되었습니다.
> Edge TTS나 pyttsx3 등 다른 엔진은 Google Cloud 환경에서 불안정하거나 작동하지 않아 제거되었습니다.

Discord 음성 채널에서 텍스트를 음성으로 변환하여 재생하는 봇입니다. 안정적인 gTTS 엔진을 사용하여 텍스트를 한국어 음성으로 변환합니다.

## 주요 기능

- **텍스트 음성 변환**: 채널에 작성된 메시지를 음성으로 변환하여 재생
- **Google TTS (gTTS)**: Google의 안정적인 텍스트 음성 변환 엔진 사용
- **설정 영구 저장**: 서버별 설정이 JSON 파일에 저장되어 봇 재시작 후에도 유지
- **비활성화 옵션**: 원하지 않는 서버에서 TTS 기능을 쉽게 비활성화
- **자동 음성 채널 관리**: 사용자가 있을 때만 채널에 머무르고, 모두 나가면 자동 퇴장
- **길드별 설정**: 각 서버마다 독립적인 설정 관리

## 기술 스택

- **Python 3.8+**
- **discord.py 2.3+**: Discord 봇 API
- **gTTS 2.3+**: Google Text-to-Speech 라이브러리
- **python-dotenv 1.0+**: 환경 변수 관리

## 프로젝트 구조

```
discord_tts_bot/
├── .env                     # 환경 변수 (토큰 저장)
├── .gitignore               # Git 제외 파일 목록
├── guild_settings.json      # 서버별 TTS 설정 (자동 생성)
├── requirements.txt         # Python 패키지 의존성
├── bot.py                   # 메인 봇 실행 파일
├── README.md               # 프로젝트 설명서 (현재 파일)
└── src/                    # 소스 코드 모듈
    ├── __init__.py
    ├── config.py           # 설정 관리 (Singleton)
    ├── tts/                # TTS 엔진 모듈
    │   ├── __init__.py
    │   ├── base.py         # TTS 엔진 인터페이스
    │   └── local_tts_engine.py # gTTS 구현체
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
Discord 서버에서 `/setup` 명령어를 실행하여 TTS를 사용할 채널을 설정합니다:
- **활성화**: 명령어를 실행한 채널이 TTS 채널로 설정됩니다.
- **비활성화**: 해당 서버의 TTS 설정이 제거됩니다.

> **참고**: 설정은 자동으로 `guild_settings.json` 파일에 저장되므로 봇을 재시작해도 유지됩니다.

### 3. TTS 사용
1. 음성 채널에 입장합니다
2. 설정한 텍스트 채널에 메시지를 작성합니다
3. 봇이 자동으로 음성 채널에 입장하여 메시지를 음성으로 재생합니다

### 4. 자동 퇴장
- 음성 채널에서 모든 사용자가 나가면 봇도 자동으로 퇴장합니다
- TTS 큐는 자동으로 초기화됩니다

## 명령어

| 명령어 | 설명 | 옵션 |
|--------|------|------|
| `/setup` | TTS 채널 설정 또는 비활성화 | 활성화 / 비활성화 |

## 환경 변수

| 변수명 | 설명 | 필수 여부 |
|--------|------|-----------|
| `DISCORD_BOT_TOKEN` | Discord 봇 토큰 | 필수 |

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