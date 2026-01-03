# Discord TTS Bot (Koyeb 버전)

텍스트를 음성으로 변환하여 Discord 음성 채널에서 재생하는 봇입니다.

> [!IMPORTANT]
> **Koyeb 호스팅 전용 브랜치**
> 
> 이 버전은 Koyeb 환경에서의 호환성을 위해 **Edge TTS, Google Cloud TTS**를 지원합니다.

## 주요 기능

- **텍스트 음성 변환**: 채널에 작성된 메시지를 음성으로 변환하여 재생
- **다중 TTS 엔진 지원**:
  - **Edge TTS**: 고품질 무료 클라우드 TTS (Microsoft)
  - **Google Cloud TTS**: 최고품질 Neural2 음성, 속도/피치 조정 가능
- **한국어 초성 약어 변환**: `ㄱㅅ` → "감사", `ㅈㅅ` → "죄송" 등 자동 변환
- **반복 문자 단축**: `ㅋㅋㅋㅋㅋ` → `크크크`로 자연스럽게 읽기
- **다양한 텍스트 처리**: 이미지/링크, 이모지, 스포일러, 멘션, 코드블록, 숫자 등
- **설정 영구 저장**: 서버별 설정이 JSON 파일에 저장되어 봇 재시작 후에도 유지
- **자동 음성 채널 관리**: 모두 나가면 자동 퇴장

## 기술 스택

- **Python 3.10+**
- **discord.py 2.3+**: Discord 봇 API
- **edge-tts 6.1+**: Microsoft Edge TTS 엔진
- **google-cloud-texttospeech 2.14+**: Google Cloud TTS 엔진
- **Flask 2.3+**: Health Check 서버
- **python-dotenv 1.0+**: 환경 변수 관리

## 사용 방법

### 명령어

| 명령어 | 설명 |
|--------|------|
| `/setup` | TTS 활성화/비활성화 및 엔진 선택 |
| `/status` | 현재 설정 확인 |
| `/leave` | 음성 채널에서 나가기 |
| `/readname` | 작성자 이름 읽기 켜기/끄기 |
| `/clear` | TTS 대기열 비우기 |
| `/help` | 명령어 도움말 |

### Edge TTS 설정

| 명령어 | 설명 |
|--------|------|
| `/voice` | 음성 변경 (선희, 인준, 현수) |

### Google Cloud TTS 설정

| 명령어 | 설명 |
|--------|------|
| `/gcvoice` | 음성 종류 변경 (Neural2-A, B, C 등) |
| `/gcspeed` | 말하기 속도 변경 (0.25 ~ 4.0) |
| `/gcpitch` | 피치 변경 (-20.0 ~ 20.0) |

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
| `@everyone` | 에브리원 |
| `@here` | 히어 |
| ` ```code``` ` | 코드 |

## 환경 변수

| 변수명 | 필수 | 설명 |
|--------|------|------|
| `DISCORD_BOT_TOKEN` | ✅ | Discord 봇 토큰 |
| `GOOGLE_CLOUD_CREDENTIALS_JSON` | ⚠️ | Google Cloud TTS 사용 시 필요 |

## 라이선스

MIT License
