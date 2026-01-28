import os
from pathlib import Path
import requests
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
    "port": os.getenv("DB_PORT", "5432"),
}


TARGET_LEAGUES = [
    # --- ⚾ 야구 (Baseball) ---
    ("baseball", "mlb"),              # 미국 MLB
    ("baseball", "college-baseball"), # 미국 대학야구 (NCAA)

    # --- 🏀 농구 (Basketball) ---
    ("basketball", "nba"),                      # 미국 NBA
    ("basketball", "wnba"),                     # 미국 WNBA
    ("basketball", "mens-college-basketball"),  # 미국 대학농구 (NCAA 남자)
    ("basketball", "womens-college-basketball"),# 미국 대학농구 (NCAA 여자)

    # --- 🏈 미식축구 (Football) ---
    ("football", "nfl"),              # 미국 NFL
    ("football", "college-football"), # 미국 대학풋볼 (NCAA)
    ("football", "cfl"),              # 캐나다 CFL
    ("football", "ufl"),              # 미국 UFL (통합 리그)

    # --- 🏒 하키 (Hockey) ---
    ("hockey", "nhl"),                # 북미 NHL

    # --- ⚽ 축구 (Soccer) - 유럽 5대 리그 ---
    ("soccer", "eng.1"),              # 잉글랜드 프리미어리그 (EPL)
    ("soccer", "esp.1"),              # 스페인 라리가
    ("soccer", "ger.1"),              # 독일 분데스리가
    ("soccer", "ita.1"),              # 이탈리아 세리에 A
    ("soccer", "fra.1"),              # 프랑스 리그 1

    # --- ⚽ 축구 (Soccer) - 유럽 대항전 & 컵 ---
    ("soccer", "uefa.champions"),     # UEFA 챔피언스리그 (UCL)
    ("soccer", "uefa.europa"),        # UEFA 유로파리그 (UEL)
    ("soccer", "eng.fa"),             # 잉글랜드 FA컵
    ("soccer", "eng.league_cup"),     # 잉글랜드 카라바오컵

    # --- ⚽ 축구 (Soccer) - 아시아 & 미주 & 기타 ---
    ("soccer", "jpn.1"),              # 일본 J리그 1
    ("soccer", "usa.1"),              # 미국 MLS
    ("soccer", "bra.1"),              # 브라질 세리에 A
    ("soccer", "arg.1"),              # 아르헨티나 프리메라
    ("soccer", "ned.1"),              # 네덜란드 에레디비시

    # --- ⚽ 축구 (Soccer) - 국가대표 ---
    ("soccer", "fifa.friendly"),      # A매치 (국가대표 친선)
    ("soccer", "uefa.nations"),       # UEFA 네이션스리그
    ("soccer", "fifa.world"),         # 월드컵 (대회 기간 중 활성화)

    # --- 🥊 격투기 (Combat Sports) ---
    ("mma", "ufc"),                   # UFC

    # --- 🏎️ 레이싱 (Racing) ---
    ("racing", "f1"),                 # 포뮬러 1 (F1)

    # --- ⛳ 골프 (Golf) ---
    ("golf", "pga"),                  # PGA 투어
    ("golf", "lpga"),                 # LPGA 투어
    ("golf", "eur"),                  # DP 월드투어 (유러피언 투어)
    ("golf", "liv"),                  # LIV 골프

    # --- 🎾 테니스 (Tennis) ---
    ("tennis", "atp"),                # 남자 프로 테니스 (ATP)
    ("tennis", "wta")                 # 여자 프로 테니스 (WTA)
]

print(f"{'SPORT':<12} {'LEAGUE':<15} {'STATUS':<10} {'INFO'}")
print("-" * 60)
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def sync_leagues():
    print("🏆 리그(Leagues) 정보 동기화 시작...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    count = 0
    
    for sport, league_slug in TARGET_LEAGUES:
        # 1. API 호출
        url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league_slug}/teams"
        
        try:
            res = requests.get(url, params={'limit': 1}) # 팀 하나만 가져와도 리그 정보는 딸려옴
            if res.status_code != 200:
                print(f"⚠️ API 호출 실패 ({league_slug}): {res.status_code}")
                continue
                
            data = res.json()
            
            # 2. 데이터 파싱
            try:
                league_data = data['sports'][0]['leagues'][0]
                league_id = int(league_data['id'])
                league_name = league_data['name']
                league_abbr = league_data.get('abbreviation')
            except (IndexError, KeyError):
                print(f"⚠️ 데이터 파싱 실패 ({league_slug})")
                continue

            # 3. Sport ID 찾기 (없으면 생성)
            # sl_sports 테이블에서 sport(slug)로 ID 조회
            cur.execute("SELECT id FROM sl_sports WHERE slug=%s", (sport,))
            sport_row = cur.fetchone()
            
            if sport_row:
                sport_db_id = sport_row[0]
            else:
                # 종목이 없으면 자동 생성 (Name은 대충 slug를 대문자로)
                print(f"  * 종목({sport})이 없어 자동 생성합니다.")
                cur.execute("""
                    INSERT INTO sl_sports (name, slug) VALUES (%s, %s)
                    ON CONFLICT (name) DO NOTHING RETURNING id;
                """, (sport.capitalize(), sport))
                
                # RETURNING으로 바로 ID를 못 받을 수도 있으니(ON CONFLICT 등) 다시 조회
                # (간단하게 다시 조회하는게 안전함)
                cur.execute("SELECT id FROM sl_sports WHERE slug=%s", (sport,))
                new_row = cur.fetchone()
                sport_db_id = new_row[0] if new_row else None

            if not sport_db_id:
                print(f"❌ 종목 ID를 찾을 수 없어 건너뜁니다: {sport}")
                continue

            # 4. League 저장 (Upsert)
            # slug 컬럼이 있는 경우와 없는 경우를 모두 대비 (최신 스키마엔 slug 추가됨)
            sql = """
                INSERT INTO sl_leagues (id, name, slug, sport_id, abbreviation)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE 
                SET name = EXCLUDED.name,
                    slug = EXCLUDED.slug,
                    sport_id = EXCLUDED.sport_id,
                    abbreviation = EXCLUDED.abbreviation;
            """
            
            # 만약 abbreviation 컬럼이 DB에 없다면 에러가 날 수 있음.
            # 방어 코드: try-except로 처리하거나, DB 스키마가 확실하다면 그대로 진행.
            # 여기선 abbreviation 컬럼이 있다고 가정 (보통 리그 정보에 포함됨)
            
            try:
                cur.execute(sql, (league_id, league_name, league_slug, sport_db_id, league_abbr))
                count += 1
                print(f"  ✅ {league_name} ({league_slug}) 저장 완료")
            except psycopg2.errors.UndefinedColumn:
                conn.rollback()
                print("⚠️ DB에 'abbreviation' 또는 'slug' 컬럼이 없습니다. 스키마 확인 필요.")
                # 비상용: 기본 컬럼만으로 재시도
                cur.execute("""
                    INSERT INTO sl_leagues (id, name, sport_id) VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name;
                """, (league_id, league_name, sport_db_id))
                count += 1

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"❌ [{league_slug}] 에러 발생: {e}")

    cur.close()
    conn.close()
    print(f"\n🎉 총 {count}개 리그 정보 동기화 완료.")

if __name__ == "__main__":
    sync_leagues()