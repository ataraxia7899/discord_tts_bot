"""
텍스트 전처리 유틸리티

TTS 생성 전 텍스트를 전처리하여 읽기 적합한 형태로 변환합니다.
"""
import re

# 정규식 패턴 사전 컴파일 (성능 최적화)
URL_PATTERN = re.compile(r'https?://\S+')
REPEATED_CHAR_PATTERN = re.compile(r'(.)\1{4,}')  # 5회 이상 반복


def replace_urls(text: str) -> str:
    """
    텍스트 내의 URL을 "링크"로 대체합니다.
    
    http:// 또는 https://로 시작하는 URL을 "링크"라는 단어로 변경합니다.
    
    Args:
        text: 원본 텍스트
        
    Returns:
        URL이 "링크"로 대체된 텍스트
        
    Examples:
        >>> replace_urls("방문하세요 https://google.com")
        '방문하세요 링크'
        >>> replace_urls("http://example.com https://test.com 확인")
        '링크 링크 확인'
    """
    return URL_PATTERN.sub('링크', text)


def limit_repeated_characters(text: str, max_repeat: int = 4) -> str:
    """
    반복되는 동일한 문자를 지정된 횟수로 제한합니다.
    
    동일한 문자가 5회 이상 반복될 경우, 지정된 최대 횟수(기본 4회)까지만 남깁니다.
    
    Args:
        text: 원본 텍스트
        max_repeat: 허용할 최대 반복 횟수 (기본값: 4)
        
    Returns:
        반복 문자가 제한된 텍스트
        
    Examples:
        >>> limit_repeated_characters("ㅋㅋㅋㅋㅋ")
        'ㅋㅋㅋㅋ'
        >>> limit_repeated_characters("ㅎㅎㅎㅎㅎㅎ")
        'ㅎㅎㅎㅎ'
        >>> limit_repeated_characters("와아아아아아아")
        '와아아아아'
    """
    def replace_func(match):
        """반복된 문자를 max_repeat 횟수로 제한하는 함수"""
        char = match.group(1)
        return char * max_repeat
    
    # 동적 패턴이 필요한 경우 (max_repeat가 4가 아닐 때)
    if max_repeat != 4:
        pattern = re.compile(rf'(.)\1{{{max_repeat},}}')
        return pattern.sub(replace_func, text)
    
    return REPEATED_CHAR_PATTERN.sub(replace_func, text)


def preprocess_text(text: str) -> str:
    """
    TTS 생성을 위한 텍스트 전처리를 수행합니다.
    
    다음 처리를 순차적으로 적용합니다:
    1. URL을 "링크"로 대체
    2. 반복 문자를 4회로 제한
    
    Args:
        text: 원본 텍스트
        
    Returns:
        전처리된 텍스트
        
    Examples:
        >>> preprocess_text("ㅋㅋㅋㅋㅋ 이거 봐 https://google.com")
        'ㅋㅋㅋㅋ 이거 봐 링크'
    """
    # 1단계: URL 대체
    text = replace_urls(text)
    
    # 2단계: 반복 문자 제한
    text = limit_repeated_characters(text)
    
    return text
