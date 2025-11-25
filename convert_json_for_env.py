"""
Google Cloud JSON 키를 .env 파일 형식으로 변환

여러 줄로 된 JSON 파일을 한 줄로 압축하여 .env 파일에 사용할 수 있게 합니다.
"""
import json

print("=" * 60)
print("Google Cloud JSON 키 -> .env 변환기")
print("=" * 60)
print()
print("Google Cloud에서 다운로드한 JSON 키 파일 경로를 입력하세요:")
print("예: C:\\Downloads\\my-project-key.json")
print()

json_file_path = input("JSON 파일 경로: ").strip().strip('"').strip("'")

try:
    # JSON 파일 읽기
    with open(json_file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # 한 줄로 압축 (공백 제거)
    compressed_json = json.dumps(json_data, separators=(',', ':'))
    
    print("\n" + "=" * 60)
    print("✅ 변환 완료!")
    print("=" * 60)
    print()
    print("아래 내용을 .env 파일에 추가하세요:")
    print()
    print("-" * 60)
    print(f"GOOGLE_CLOUD_CREDENTIALS_JSON='{compressed_json}'")
    print("-" * 60)
    print()
    print("⚠️ 주의사항:")
    print("1. 위 한 줄 전체를 복사하여 .env 파일의 2번째 줄에 붙여넣으세요")
    print("2. 줄바꿈 없이 한 줄로 작성되어야 합니다")
    print("3. 작은따옴표(')로 감싸져 있어야 합니다")
    print()
    
    # 클립보드에 복사 시도 (pyperclip이 설치되어 있으면)
    try:
        import pyperclip
        env_line = f"GOOGLE_CLOUD_CREDENTIALS_JSON='{compressed_json}'"
        pyperclip.copy(env_line)
        print("✅ 클립보드에 복사되었습니다! Ctrl+V로 붙여넣으세요.")
    except ImportError:
        print("💡 Tip: 위 내용을 마우스로 드래그하여 복사하세요.")
    
    print()
    
except FileNotFoundError:
    print(f"\n❌ 파일을 찾을 수 없습니다: {json_file_path}")
    print("경로를 다시 확인해주세요.")
except json.JSONDecodeError as e:
    print(f"\n❌ JSON 파일 형식이 올바르지 않습니다: {e}")
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")

print()
input("Enter 키를 눌러 종료...")
