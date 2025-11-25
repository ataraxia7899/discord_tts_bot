"""
텍스트 전처리 유틸리티

TTS 생성 전 텍스트를 전처리하여 읽기 적합한 형태로 변환합니다.
"""
import re


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
    # http:// 또는 https://로 시작하는 URL 패턴 매칭
    # URL은 공백이 나올 때까지 또는 문자열 끝까지로 간주
    url_pattern = r'https?://\S+'
    return re.sub(url_pattern, '링크', text)


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
    # 동일한 문자가 반복되는 패턴을 찾아서 max_repeat 횟수로 제한
    # (.): 임의의 한 문자를 캡처
    # \1{max_repeat,}: 캡처한 문자가 max_repeat번 이상 반복
    # 이를 캡처한 문자를 max_repeat번 반복한 것으로 대체
    pattern = rf'(.)\1{{{max_repeat},}}'
    
    def replace_func(match):
        """반복된 문자를 max_repeat 횟수로 제한하는 함수"""
        char = match.group(1)
        return char * max_repeat
    
    return re.sub(pattern, replace_func, text)


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
