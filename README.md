# Discord TTS Bot (Koyeb 버전)

텍스트를 음성으로 변환하여 Discord 음성 채널에서 재생하는 봇입니다.

> [!IMPORTANT]
> **Koyeb 호스팅 전용 브랜치**
> 
> 이 버전은 Koyeb 환경에서의 호환성을 위해 **Edge TTS, Google TTS (gTTS)** 만을 사용하도록 수정되었습니다.

## 주요 기능

- **텍스트 음성 변환**: 채널에 작성된 메시지를 음성으로 변환하여 재생
- **다중 TTS 엔진 지원**:
  - **Edge TTS**: 고품질 무료 클라우드 TTS (Microsoft)
  - **Google Cloud TTS**: 최고품질 Neural2 음성, 속도/피치 조정 가능
- **한국어 초성 약어 변환**: `ㄱㅅ` → "감사", `ㅈㅅ` → "죄송" 등 자동 변환
- **설정 영구 저장**: 서버별 설정이 JSON 파일에 저장되어 봇 재시작 후에도 유지
- **비활성화 옵션**: 원하지 않는 서버에서 TTS 기능을 쉽게 비활성화
- **자동 음성 채널 관리**: 사용자가 있을 때만 채널에 머무르고, 모두 나가면 자동 퇴장

## 기술 스택

- **Python 3.10+**
- **discord.py 2.3+**: Discord 봇 API
- **edge-tts 6.1+**: Microsoft Edge TTS 엔진
- **google-cloud-texttospeech 2.14+**: Google Cloud TTS 엔진
- **Flask 2.3+**: Health Check 서버
- **python-dotenv 1.0+**: 환경 변수 관리

## 디자인 패턴

- **Singleton**: `Config` 클래스 - 설정의 단일 인스턴스 보장
- **Strategy**: TTS 엔진 - `EdgeTTSEngine`, `GoogleCloudTTSEngine` 교체 가능
- **Command**: 슬래시 명령어 핸들러

## 프로젝트 구조

```
discord_tts_bot/
├── bot.py                 # 메인 진입점
├── keep_alive.py          # Koyeb Health Check 서버
├── Dockerfile             # Docker 컨테이너 설정
├── requirements.txt       # 의존성 목록
├── guild_settings.json    # 서버별 설정 저장 (자동 생성)
├── .env                   # 환경 변수 (비공개)
└── src/
    ├── config.py          # 설정 관리 (Singleton)
    ├── tts/               # TTS 엔진 (Strategy)
    │   ├── __init__.py
    │   ├── base.py                    # TTS 엔진 인터페이스
    │   ├── edge_tts_engine.py         # Edge TTS 구현
    │   └── google_cloud_tts_engine.py # Google Cloud TTS 구현
    ├── commands/          # 명령어 핸들러 (Command)
    │   ├── __init__.py
    │   └── setup.py       # /setup, /gcvoice, /gcspeed, /gcpitch
    ├── handlers/          # 이벤트 핸들러
    │   ├── __init__.py
    │   ├── message_handler.py
    │   └── voice_handler.py
    └── utils/             # 유틸리티
        ├── __init__.py
        └── text_preprocessor.py  # 초성 약어 변환
```

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/ataraxia7899/discord_tts_bot.git
cd discord_tts_bot
git checkout koyebVersion
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 아래 내용을 추가:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GOOGLE_CLOUD_CREDENTIALS_JSON={"type": "service_account", ...}
```

> **참고**: Google Cloud TTS를 사용하려면 [Google Cloud Console](https://console.cloud.google.com/)에서 서비스 계정 JSON 키를 발급받아야 합니다.

### 3. 의존성 설치 (로컬 테스트용)

```bash
pip install -r requirements.txt
```

### 4. 봇 실행 (로컬 테스트용)

```bash
python bot.py
```

## Koyeb 배포 방법

### 1. GitHub 연동

1. Koyeb 대시보드에서 **Create Service** 클릭
2. **GitHub** 선택 → 레포지토리 연결
3. 브랜치: `koyebVersion` 선택

### 2. 설정

- **Service Type**: Web Service
- **Builder**: Docker
- **Port**: 8000

### 3. 환경 변수 설정

Koyeb 대시보드에서 다음 환경 변수 추가:

| Key | Value |
|-----|-------|
| `DISCORD_BOT_TOKEN` | 디스코드 봇 토큰 |
| `GOOGLE_CLOUD_CREDENTIALS_JSON` | Google Cloud 서비스 계정 JSON |

### 4. UptimeRobot 설정 (Sleep 방지)

1. [UptimeRobot](https://uptimerobot.com/) 가입
2. **Add New Monitor** → **HTTP(s)**
3. URL: `https://앱이름-계정이름.koyeb.app`
4. 주기: 5분

## 사용 방법

### 기본 설정

Discord 서버에서 `/setup` 명령어를 실행하여 TTS 엔진을 선택합니다:

| 옵션 | 설명 |
|------|------|
| `Edge TTS (고품질, 무료)` | Microsoft 클라우드 TTS |
| `Google Cloud TTS (최고품질, 다양한 설정)` | Google Neural2 TTS |
| `비활성화 (TTS 사용 안 함)` | TTS 설정 제거 |

### Google Cloud TTS 설정

| 명령어 | 설명 |
|--------|------|
| `/gcvoice` | 음성 종류 변경 (Neural2-A, B, C 등) |
| `/gcspeed` | 말하기 속도 변경 (0.25 ~ 4.0) |
| `/gcpitch` | 피치 변경 (-20.0 ~ 20.0) |

### 한국어 초성 약어 변환

자주 사용되는 인터넷 초성 약어를 TTS가 읽을 수 있도록 자동 변환합니다:

| 초성 | 변환 결과 |
|------|----------|
| `ㄱㅅ` | 감사 |
| `ㅈㅅ` | 죄송 |
| `ㅋㅋ` | 크크 |
| `ㅎㅎ` | 하하 |
| `ㄱㄱ` | 고고 |
| `ㄴㄴ` | 노노 |
| `ㅇㅋ` | 오키 |
| `ㄹㅇ` | 리얼 |

> **참고**: 독립된 초성 블록만 변환됩니다. `ㅂㅈㅅㅈ`처럼 사전에 없는 긴 초성 조합은 변환되지 않습니다.

## 환경 변수

| 변수명 | 필수 | 설명 |
|--------|------|------|
| `DISCORD_BOT_TOKEN` | ✅ | Discord 봇 토큰 |
| `GOOGLE_CLOUD_CREDENTIALS_JSON` | ⚠️ | Google Cloud TTS 사용 시 필요 |

## 라이선스

MIT License