"""
환경 변수 JSON 파싱 테스트

.env 파일에서 GOOGLE_CLOUD_CREDENTIALS_JSON이 올바르게 로드되는지 확인합니다.
"""
import os
from dotenv import load_dotenv
import json

# .env 파일 로드
load_dotenv()

# 환경 변수 값 가져오기
credentials_json = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON")

print("=" * 60)
print("환경 변수 확인")
print("=" * 60)

if not credentials_json:
    print("❌ GOOGLE_CLOUD_CREDENTIALS_JSON 환경 변수가 설정되지 않았습니다.")
    print("\n.env 파일에 다음과 같이 추가했는지 확인하세요:")
    print('GOOGLE_CLOUD_CREDENTIALS_JSON={"type":"service_account",...}')
else:
    print("✅ 환경 변수가 설정되어 있습니다.")
    print(f"\n길이: {len(credentials_json)} 문자")
    print(f"\n첫 100자: {credentials_json[:100]}")
    print(f"마지막 50자: {credentials_json[-50:]}")
    
    print("\n" + "=" * 60)
    print("JSON 파싱 테스트")
    print("=" * 60)
    
    try:
        # JSON 파싱 시도
        credentials_dict = json.loads(credentials_json)
        print("✅ JSON 파싱 성공!")
        print(f"\n키 목록: {list(credentials_dict.keys())}")
        
        # 필수 필드 확인
        required_fields = ["type", "project_id", "private_key", "client_email"]
        missing_fields = [field for field in required_fields if field not in credentials_dict]
        
        if missing_fields:
            print(f"\n⚠️ 누락된 필드: {missing_fields}")
        else:
            print("\n✅ 모든 필수 필드가 존재합니다.")
            print(f"   - type: {credentials_dict.get('type')}")
            print(f"   - project_id: {credentials_dict.get('project_id')}")
            print(f"   - client_email: {credentials_dict.get('client_email')}")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패!")
        print(f"\n에러: {e}")
        print(f"위치: line {e.lineno}, column {e.colno}")
        print(f"문제 문자 위치: {e.pos}")
        
        if e.pos < len(credentials_json):
            # 문제가 있는 부분 표시
            start = max(0, e.pos - 20)
            end = min(len(credentials_json), e.pos + 20)
            problem_area = credentials_json[start:end]
            
            print(f"\n문제 영역 (위치 {start}-{end}):")
            print(f"'{problem_area}'")
            print(" " * (e.pos - start) + "^ 여기")
        
        print("\n가능한 원인:")
        print("1. 작은따옴표(')를 큰따옴표(\")로 변경했는지 확인")
        print("2. JSON이 한 줄로 작성되었는지 확인")
        print("3. 특수 문자가 올바르게 이스케이프되었는지 확인")
        
print("\n" + "=" * 60)
