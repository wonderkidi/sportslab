import os
from pathlib import Path
import psycopg2

# --- 환경 변수 로드 ---
def load_env(path: Path) -> None:
    if not path.exists(): return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

load_env(Path(__file__).with_name(".env"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "sportslab"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "rootpassword"),
    "port": os.getenv("DB_PORT", "54321"),
}

# --- 저장할 종목 리스트 (Name, Slug) ---
# ESPN API에서 사용하는 sport 파라미터 값(slug)과 매칭되어야 합니다.
SPORTS_LIST = [
    ("Baseball", "baseball"),
    ("Basketball", "basketball"),
    ("Soccer", "soccer"),
    ("Football", "football"), # 미식축구
    ("Hockey", "hockey"),
    ("MMA", "mma"),
    ("Racing", "racing"),
    ("Golf", "golf"),
    ("Tennis", "tennis"),
    ("Boxing", "boxing"),
    ("Rugby", "rugby"),
    ("Cricket", "cricket")
]

def sync_sports():
    print("🏟️ 종목(Sports) 기초 데이터 저장 중...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        count = 0
        for name, slug in SPORTS_LIST:
            # ON CONFLICT (name): 이미 'Baseball'이 있으면 아무것도 안 함(DO NOTHING)
            # 만약 slug 업데이트가 필요하면 DO UPDATE SET slug = EXCLUDED.slug 사용
            sql = """
                INSERT INTO sl_sports (name, slug)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE 
                SET slug = EXCLUDED.slug; 
            """
            cur.execute(sql, (name, slug))
            count += 1
            
        conn.commit()
        print(f"✅ 총 {count}개 종목 데이터 확인/저장 완료.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        if 'conn' in locals(): conn.rollback()
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    sync_sports()