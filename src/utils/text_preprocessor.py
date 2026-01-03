"""
텍스트 전처리 모듈

TTS 변환 전 텍스트를 전처리하는 기능을 제공합니다.
- 한국어 초성 약어 변환
- URL/이미지 링크 처리
- Discord 이모지 처리
- 스포일러 태그 처리
- 반복 문자 단축
- 숫자 읽기 개선
"""
import re
from typing import Dict, Optional

# 정규식 패턴 (모듈 레벨에서 컴파일하여 성능 향상)
URL_PATTERN = re.compile(r'https?://\S+', re.IGNORECASE)
DISCORD_EMOJI_PATTERN = re.compile(r'<a?:(\w+):\d+>')
SPOILER_PATTERN = re.compile(r'\|\|(.+?)\|\|')
NUMBER_PATTERN = re.compile(r'\d+')
KOREAN_CONTENT_PATTERN = re.compile(r'[가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9]')

# 멘션 패턴
USER_MENTION_PATTERN = re.compile(r'<@!?(\d+)>')  # 사용자 멘션
CHANNEL_MENTION_PATTERN = re.compile(r'<#(\d+)>')  # 채널 멘션
ROLE_MENTION_PATTERN = re.compile(r'<@&(\d+)>')  # 역할 멘션

# 특수 멘션 패턴
EVERYONE_PATTERN = re.compile(r'@everyone', re.IGNORECASE)
HERE_PATTERN = re.compile(r'@here', re.IGNORECASE)

# 코드 블록 패턴
CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```')  # 멀티라인 코드 블록
INLINE_CODE_PATTERN = re.compile(r'`[^`]+`')  # 인라인 코드

# 특수문자/마크다운 패턴
MARKDOWN_PATTERN = re.compile(r'[*_~\\]')  # 마크다운 장식 문자 (백틱 제외)

# 한국어 초성 약어 사전
KOREAN_ABBREVIATIONS: Dict[str, str] = {
    # 인사/감사 표현
    'ㄱㅅ': '감사',
    'ㄱㅅㄱㅅ': '감사감사',
    
    # 사과 표현
    'ㅈㅅ': '죄송',
    'ㅁㅇ': '미안',
    
    # 긍정/동의 표현
    'ㅇㅇ': '응응',
    'ㅇㅋ': '오키',
    'ㄱㄱ': '고고',
    'ㄴㄴ': '노노',
    'ㄹㅇ': '리얼',
    'ㅇㅎ': '아하',
    'ㅎㄹ': '헐',
    'ㅂㅂㅂㄱ': '반박불가',
    
    # 감탄/반응 표현
    'ㅋㅋ': '크크',
    'ㅋㅋㅋ': '크크크',
    'ㅎㅎ': '하하',
    'ㅎㅎㅎ': '하하하',
    'ㄷㄷ': '덜덜',
    'ㅎㄷㄷ': '후덜덜',
    'ㅗㅜㅑ': '오우야',
    'ㅂㄷㅂㄷ': '부들부들',
    
    # 축약 표현
    'ㅂㅂ': '바이바이',
    'ㅂㅇ': '바이',
    'ㅎㅇ': '하이',
    'ㄹㅇㄹㅇ': '리얼리얼',
    
    # 기타 자주 쓰는 표현
    'ㅊㅋ': '축하',
    'ㅊㅊ': '축축',
    'ㄱㅊ': '괜찮아',
    'ㄱㅊㄱㅊ': '괜찮아괜찮아',
    'ㅇㄷ': '어디',
    'ㅇㄱㄹㅇ': '이거레알',
    'ㅁㅊ': '미친',
    'ㅅㄱ': '수고',
    'ㅅㅂ': '시발',
    'ㅂㅅ': '병신',
    'ㄷㅊ': '닥쳐',
    'ㅈㄴ': '존나',
    
    # 시간/대기 관련
    'ㄱㄷ': '기달',
    'ㄱㄷㄱㄷ': '기달기달',
    'ㅈㅁ': '잠만',
    
    # 감정/평가 표현
    'ㄲㅂ': '까비',
    'ㅁㄹ': '몰라',
    'ㄱㅇㄷ': '개이득',
    'ㄴㅈ': '노잼',
    'ㅇㅈ': '인정',
    
    # 게임/인터넷 용어
    'ㅌㅌ': '튀튀',
    'ㅋㅋㄹㅃㅃ': '쿠쿠루삥뽕',
    'ㅈㄹ': '지랄',
    
    # 기타 일상 표현
    'ㅎㅇㅇ': '하이요',
    'ㅁㅈㅁㅈ': '맞아맞아',
    'ㅇㅋㄷㅋ': '오키도키',
    'ㅅㄱㄹ': '수고링',
    'ㅅㄱㅇ': '수고여',
    'ㅈㅂ': '제발',
    'ㅉㅉ': '쯧쯧',
    'ㄴㄱ': '누구',
    'ㄹㅇㅋㅋ': '레알키키'
}

# 겹자음 확장 매핑
DOUBLE_CONSONANTS: Dict[str, str] = {
    'ㄲ': '크크',
    'ㄸ': '뜨',
    'ㅃ': '쁘',
    'ㅆ': '쓰',
    'ㅉ': '쯔',
}

# 이미지 확장자 목록
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')


def is_korean_jamo(char: str) -> bool:
    """문자가 한국어 자모인지 확인합니다."""
    if len(char) != 1:
        return False
    code = ord(char)
    return 0x3131 <= code <= 0x3163


def process_urls(text: str) -> str:
    """URL을 '링크' 또는 '이미지'로 변환합니다."""
    def replace_url(match):
        url = match.group(0).lower()
        if any(url.endswith(ext) for ext in IMAGE_EXTENSIONS):
            return '이미지'
        return '링크'
    return URL_PATTERN.sub(replace_url, text)


def process_discord_emoji(text: str) -> str:
    """Discord 커스텀 이모지를 이름으로 변환합니다."""
    return DISCORD_EMOJI_PATTERN.sub(r'\1', text)


def process_spoiler(text: str) -> str:
    """스포일러 태그를 '스포일러'로 변환합니다."""
    return SPOILER_PATTERN.sub('스포일러', text)


def shorten_repeated_chars(text: str, max_repeat: int = 3) -> str:
    """반복되는 문자를 최대 max_repeat개로 줄입니다."""
    result = []
    prev_char = None
    count = 0
    
    for char in text:
        if char == prev_char:
            count += 1
            if count < max_repeat:
                result.append(char)
        else:
            result.append(char)
            prev_char = char
            count = 1
    
    return ''.join(result)


def expand_double_consonants(text: str) -> str:
    """겹자음을 확장합니다."""
    for consonant, expansion in DOUBLE_CONSONANTS.items():
        text = text.replace(consonant, expansion)
    return text


def process_jamo_abbreviations(text: str) -> str:
    """초성 약어를 완성형 단어로 변환합니다."""
    result = []
    i = 0
    
    while i < len(text):
        if is_korean_jamo(text[i]):
            jamo_start = i
            jamo_end = i
            
            while jamo_end < len(text) and is_korean_jamo(text[jamo_end]):
                jamo_end += 1
            
            jamo_block = text[jamo_start:jamo_end]
            
            if jamo_block in KOREAN_ABBREVIATIONS:
                result.append(KOREAN_ABBREVIATIONS[jamo_block])
            else:
                result.append(jamo_block)
            
            i = jamo_end
        else:
            result.append(text[i])
            i += 1
    
    return ''.join(result)


def convert_numbers_to_readable(text: str) -> str:
    """숫자를 읽기 쉬운 형태로 변환합니다."""
    def replace_number(match):
        num = match.group(0)
        if len(num) <= 4:
            return num
        return ' '.join(num)
    return NUMBER_PATTERN.sub(replace_number, text)


def is_empty_message(text: str) -> bool:
    """메시지가 실질적으로 비어있는지 확인합니다."""
    stripped = text.strip()
    if not stripped:
        return True
    if KOREAN_CONTENT_PATTERN.search(stripped):
        return False
    return True


def process_mentions(text: str) -> str:
    """Discord 멘션을 처리합니다."""
    text = EVERYONE_PATTERN.sub('에브리원', text)
    text = HERE_PATTERN.sub('히어', text)
    text = USER_MENTION_PATTERN.sub('사용자', text)
    text = CHANNEL_MENTION_PATTERN.sub('채널', text)
    text = ROLE_MENTION_PATTERN.sub('역할', text)
    return text


def remove_code_blocks(text: str) -> str:
    """코드 블록을 제거합니다."""
    text = CODE_BLOCK_PATTERN.sub('코드', text)
    text = INLINE_CODE_PATTERN.sub(lambda m: m.group(0)[1:-1], text)
    return text


def remove_markdown(text: str) -> str:
    """마크다운 장식 문자를 제거합니다."""
    return MARKDOWN_PATTERN.sub('', text)


def preprocess_text(text: str) -> Optional[str]:
    """
    TTS 변환 전 텍스트를 전처리합니다.
    
    처리 순서:
    1. 스포일러 태그 처리
    2. 코드 블록 처리
    3. 멘션 처리 (사용자, 채널, 역할, @everyone, @here)
    4. URL/이미지 처리
    5. Discord 이모지 처리
    6. 마크다운 장식 문자 제거
    7. 반복 문자 단축
    8. 겹자음 변환
    9. 초성 약어 변환
    10. 숫자 읽기 개선
    11. 빈 메시지 필터링
    """
    if not text:
        return None
    
    text = process_spoiler(text)
    text = remove_code_blocks(text)
    text = process_mentions(text)
    text = process_urls(text)
    text = process_discord_emoji(text)
    text = remove_markdown(text)
    text = shorten_repeated_chars(text, max_repeat=3)
    text = expand_double_consonants(text)
    text = process_jamo_abbreviations(text)
    text = convert_numbers_to_readable(text)
    
    if is_empty_message(text):
        return None
    
    return text.strip()
