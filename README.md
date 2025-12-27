# Discord TTS Bot (Google Cloud Edition)

> [!IMPORTANT]
> **Google Cloud 호스팅 전용 브랜치**
> 
> 이 버전은 Google Cloud 환경에서의 호환성을 위해 **Google TTS (gTTS)** 만을 사용하도록 수정되었습니다.
> Edge TTS나 pyttsx3 등 다른 엔진은 Google Cloud 환경에서 불안정하거나 작동하지 않아 제거되었습니다.

Discord 음성 채널에서 텍스트를 음성으로 변환하여 재생하는 봇입니다. Google TTS (gTTS)와 Google Cloud TTS 두 가지 엔진을 지원합니다.

## 주요 기능

- **이중 TTS 엔진 지원**
  - **Google TTS (gTTS)**: 간단하고 안정적인 무료 TTS
  - **Google Cloud TTS**: 고품질 Neural2 음성 (API 키 필요)
- **텍스트 전처리**: URL을 "링크"로 대체, 반복 문자 자동 제한
- **설정 영구 저장**: 서버별 설정이 JSON 파일에 저장
- **세밀한 음성 조정** (Google Cloud TTS): 음성 종류, 속도, 피치 조절
- **자동 음성 채널 관리**: 사용자가 없으면 자동 퇴장
- **길드별 설정**: 각 서버마다 독립적인 TTS 엔진 및 설정 관리

## ✨ 최적화 기능

### 성능 최적화
- **TTS Prefetch**: 현재 메시지 재생 중 다음 메시지를 미리 생성하여 응답 지연 최소화
- **TTS 엔진 싱글톤화**: 엔진 인스턴스 재사용으로 초기화 시간 절약
- **Google Cloud 클라이언트 캐싱**: API 클라이언트를 한 번만 생성하여 재사용
- **정규식 패턴 캐싱**: 텍스트 전처리 성능 향상

### 안정성 개선
- **Race Condition 방지**: `asyncio.Lock`으로 동시 접근 제어
- **FFmpeg 재연결 옵션**: 네트워크 불안정 시 자동 재연결
- **예외 처리 강화**: 모든 예외 상황에서 안전한 상태 복구
- **Idle Timeout**: 2시간 비활동 시 자동 퇴장으로 리소스 절약
- **설정 즉시 반영**: `/gcvoice`, `/gcspeed`, `/gcpitch` 변경 시 즉시 적용

### UI/UX 개선
- **Discord Embed**: 모든 응답이 깔끔한 Embed 형식으로 표시
- **통일된 에러 메시지**: 일관된 사용자 경험 제공

## 기술 스택

- **Python 3.10+**
- **discord.py 2.3+**: Discord 봇 API
- **gTTS 2.3+**: Google Text-to-Speech 라이브러리
- **google-cloud-texttospeech 2.14+**: Google Cloud TTS API
- **python-dotenv 1.0+**: 환경 변수 관리

## 프로젝트 구조

```
discord_tts_bot/
├── .env                     # 환경 변수 (토큰 저장)
├── .gitignore               # Git 제외 파일 목록
├── guild_settings.json      # 서버별 TTS 설정 (자동 생성)
├── requirements.txt         # Python 패키지 의존성
├── bot.py                   # 메인 봇 실행 파일
├── README.md                # 프로젝트 설명서 (현재 파일)
└── src/                     # 소스 코드 모듈
    ├── __init__.py
    ├── config.py            # 설정 관리 (Singleton 패턴)
    ├── tts/                 # TTS 엔진 모듈 (Strategy 패턴)
    │   ├── __init__.py
    │   ├── base.py                    # TTS 엔진 인터페이스
    │   ├── google_tts_engine.py       # gTTS 구현체
    │   └── google_cloud_tts_engine.py # Google Cloud TTS 구현체
    ├── commands/            # 명령어 핸들러 (Command 패턴)
    │   ├── __init__.py
    │   ├── setup.py         # /setup 명령어
    │   ├── gc_voice.py      # /gcvoice 명령어
    │   ├── gc_speed.py      # /gcspeed 명령어
    │   └── gc_pitch.py      # /gcpitch 명령어
    ├── handlers/            # 이벤트 핸들러
    │   ├── __init__.py
    │   ├── message_handler.py   # 메시지 처리 (Prefetch, 큐 관리)
    │   └── voice_handler.py     # 음성 상태 처리
    └── utils/               # 유틸리티
        ├── __init__.py
        ├── text_preprocessor.py # 텍스트 전처리
        └── discord_utils.py     # Discord Embed, 에러 핸들러
```

## 설치 방법

### 1. 저장소 클론
```bash
git clone <repository-url>
cd discord_tts_bot
```

### 2. 가상환경 생성 (권장)
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env` 파일을 생성하고 Discord 봇 토큰을 입력합니다:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

#### Google Cloud TTS 사용 시 (선택사항)

Google Cloud TTS를 사용하려면 추가로 JSON 키를 `.env` 파일에 추가합니다:

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Text-to-Speech API 활성화
3. 서비스 계정 생성 및 JSON 키 다운로드
4. JSON 키 내용을 한 줄로 압축하여 `.env` 파일에 추가:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GOOGLE_CLOUD_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project-id",...}
```

> **참고**: JSON 키는 줄바꿈 없이 한 줄로 작성해야 합니다.

### 5. Discord 봇 생성

1. [Discord Developer Portal](https://discord.com/developers/applications)에 접속
2. "New Application" 클릭하여 새 애플리케이션 생성
3. "Bot" 메뉴에서 봇 생성 및 토큰 복사
4. "Bot" 메뉴에서 다음 Privileged Gateway Intents 활성화:
   - `MESSAGE CONTENT INTENT` ✅
   - `SERVER MEMBERS INTENT` (선택사항)
5. "OAuth2" > "URL Generator"에서 다음 권한 선택:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Connect`, `Speak`, `Use Voice Activity`
6. 생성된 URL로 봇을 서버에 초대

## 사용 방법

### 1. 봇 실행
```bash
python bot.py
```

### 2. TTS 설정

Discord 서버에서 `/setup` 명령어를 실행하여 TTS 엔진을 선택합니다:
- **Google TTS (gTTS)**: 무료, 설정 불필요
- **Google Cloud TTS**: 고품질, API 키 필요
- **비활성화**: TTS 기능 끄기

### 3. Google Cloud TTS 음성 조정 (선택사항)

Google Cloud TTS를 선택한 경우 다음 명령어로 세밀하게 조정할 수 있습니다:

- `/gcvoice`: 음성 종류 선택
  - `ko-KR-Neural2-A` (여성 1)
  - `ko-KR-Neural2-B` (여성 2)
  - `ko-KR-Neural2-C` (남성 1)
- `/gcspeed <속도>`: 말하기 속도 조절 (0.25 ~ 4.0)
- `/gcpitch <피치>`: 음성 피치 조절 (-20.0 ~ 20.0)

> **참고**: 설정 변경 시 즉시 적용됩니다. 봇 재시작이 필요 없습니다.

### 4. TTS 사용

1. 음성 채널에 입장합니다
2. 설정한 텍스트 채널에 메시지를 작성합니다
3. 봇이 자동으로 음성 채널에 입장하여 메시지를 음성으로 재생합니다

### 5. 자동 퇴장
- 음성 채널에서 모든 사용자가 나가면 봇도 자동으로 퇴장합니다
- 2시간 동안 활동이 없으면 자동으로 퇴장합니다
- TTS 큐 및 캐시는 자동으로 정리됩니다

## 명령어

| 명령어 | 설명 | 파라미터 |
|--------|------|---------|
| `/setup` | TTS 엔진 및 채널 설정 | Google TTS / Google Cloud TTS / 비활성화 |
| `/gcvoice` | Google Cloud TTS 음성 선택 | Neural2-A / B / C |
| `/gcspeed` | Google Cloud TTS 속도 조절 | 0.25 ~ 4.0 |
| `/gcpitch` | Google Cloud TTS 피치 조절 | -20.0 ~ 20.0 |

## 환경 변수

| 변수명 | 설명 | 필수 여부 |
|--------|------|-----------|
| `DISCORD_BOT_TOKEN` | Discord 봇 토큰 | 필수 |
| `GOOGLE_CLOUD_CREDENTIALS_JSON` | Google Cloud 서비스 계정 JSON 키 | Google Cloud TTS 사용 시 필수 |

## 텍스트 전처리 기능

봇은 자동으로 다음 전처리를 수행합니다:

1. **URL 대체**: `https://google.com` → `링크`
2. **반복 문자 제한**: `ㅋㅋㅋㅋㅋ` (5자) → `ㅋㅋㅋㅋ` (4자)

## 디자인 패턴

이 프로젝트는 다음 디자인 패턴을 적용하여 유지보수성과 확장성을 높였습니다:

- **Singleton**: `Config` 클래스 - 전역 설정 관리
- **Strategy**: `TTSEngine` 인터페이스 - TTS 엔진 교체 가능
- **Command**: 슬래시 명령어 핸들러 - 명령어별 독립적 처리

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

### 음성 설정이 적용되지 않음
- `/gcvoice`, `/gcspeed`, `/gcpitch` 명령어 실행 후 즉시 적용됩니다
- 적용되지 않는다면 봇을 재시작해 보세요

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.