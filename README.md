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

- **Python 3.12**: 검증된 실행 환경
- **discord.py 2.7.1**: Discord 봇 API 및 음성 연결
- **edge-tts 7.3.1**: Microsoft Edge TTS 엔진
- **python-dotenv 1.2.4**: 환경 변수 관리
- **imageio-ffmpeg 0.6.0**: FFmpeg 실행 파일 제공

직접·간접 의존성은 `requirements.txt`에 검증된 버전으로 고정되어 있습니다.
버전 변경 시 아래 회귀 테스트와 실제 호스팅 음성 재생을 확인하세요.
`edge-tts` 7.3.1은 Microsoft의 Sec-MS-GEC v2 인증에 대응합니다.
7.2.8에서 HTTP 403이 발생하면 최신 `requirements.txt`로 의존성을 다시 설치한 뒤 봇을 재시작하세요.
회귀 테스트는 외부 서비스의 인증 호환성을 확인하지 않으므로, 배포 후 실제 음성 생성도 확인해야 합니다.

## 요청 제한과 실패 처리

- 봇 전체에서 음성 생성 요청은 한 번에 1개만 처리합니다.
- 서버별 대기열은 최대 20개이며, 가득 차면 새 메시지를 거절하고 안내합니다.
- HTTP 429 및 일시적인 연결 오류는 최대 3회 재시도합니다(최초 요청 포함 최대 4회).
- 기본 대기시간은 2·4·8초에 무작위 지연 0~1초를 더합니다. 429의 `Retry-After`가 더 길면 그 시간을 기다립니다.
- 429 대기시간은 모든 서버에 공유되며, `/clear`로 현재 요청을 취소해도 유지됩니다.
- 요청 1회 제한시간은 60초입니다. 음성 생성이 실패하거나 결과가 비어 있으면 FFmpeg를 실행하지 않습니다.
- 완성된 음성을 재생하는 동안 다음 메시지를 하나 미리 생성합니다. 첫 재생은 파일 생성이 끝난 뒤 시작합니다.
- `/clear`, `/leave`, TTS 비활성화 및 자동 퇴장은 미리 생성 중인 음성과 재생 작업을 함께 취소합니다.
- 설정은 같은 디렉터리의 임시 파일에 저장한 뒤 교체합니다. 저장 실패 시 기존 파일과 메모리 설정을 유지하고 오류를 안내합니다.

## 회귀 테스트

```bash
python -m unittest discover -s tests -v
```

네트워크나 Discord에 접속하지 않고 재시도, 요청 동시성, 재생 취소, 설정 파일 보존을 검증합니다.

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
