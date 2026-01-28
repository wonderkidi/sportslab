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

# --- 대상 리그 목록 ---
TARGET_LEAGUES = [
    ("baseball", "mlb"),
    ("soccer", "eng.1"),
    ("basketball", "nba"),
    ("football", "nfl"),
    ("hockey", "nhl"),
    ("soccer", "esp.1"),
    ("soccer", "ger.1"),
    ("soccer", "ita.1"),
    ("soccer", "fra.1"),
    ("soccer", "uefa.champions"),
    ("soccer", "uefa.europa"),
    ("soccer", "jpn.1"),
    ("soccer", "usa.1"),
    ("soccer", "kor.1"),
    ("baseball", "kbo")
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def sync_team_season_map(sport, league_slug):
    print(f"🔗 [{league_slug}] 팀-시즌 매핑 동기화 중...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. API 호출 (팀 목록 + 시즌 정보)
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league_slug}/teams"
    
    try:
        res = requests.get(url, params={'limit': 1000})
        res.raise_for_status()
        data = res.json()

        # 2. 리그 및 시즌 정보 파싱
        try:
            league_data = data['sports'][0]['leagues'][0]
            league_id = int(league_data['id'])
            season_year = league_data.get('season', {}).get('year')
        except (IndexError, KeyError):
            print(f"⚠️ [{league_slug}] 데이터 구조를 파싱할 수 없습니다.")
            return

        print(f"  - Season: {season_year}")

        # 3. [FK 방지] 시즌 ID(season_id) 찾기 (없으면 생성)
        cur.execute("SELECT id FROM sl_seasons WHERE league_id=%s AND year=%s", (league_id, season_year))
        row = cur.fetchone()

        if row:
            season_db_id = row[0]
        else:
            # 시즌이 없으면 새로 생성
            cur.execute("""
                INSERT INTO sl_seasons (league_id, year, is_current)
                VALUES (%s, %s, true) RETURNING id
            """, (league_id, season_year))
            season_db_id = cur.fetchone()[0]

        # 4. 팀 리스트 순회하며 매핑 저장
        teams = league_data.get('teams', [])
        count = 0

        for t in teams:
            team_info = t.get('team', {})
            team_id = int(team_info.get('id', 0))
            team_name = team_info.get('displayName', 'Unknown Team')
            
            if team_id == 0: continue

            # [FK 방지] 팀이 sl_teams에 없으면 최소 정보로 생성 (에러 방지)
            cur.execute("SELECT 1 FROM sl_teams WHERE id=%s", (team_id,))
            if not cur.fetchone():
                # save_teams.py를 안 돌렸거나 누락된 팀이 있을 경우 대비
                cur.execute("""
                    INSERT INTO sl_teams (id, name) VALUES (%s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (team_id, team_name))

            # 5. 매핑 저장 (sl_team_season_map)
            sql = """
                INSERT INTO sl_team_season_map (team_id, season_id)
                VALUES (%s, %s)
                ON CONFLICT (team_id, season_id) DO NOTHING;
            """
            cur.execute(sql, (team_id, season_db_id))
            count += 1

        conn.commit()
        print(f"✅ [{league_slug}] {count}개 팀 매핑 완료.")

    except Exception as e:
        conn.rollback()
        print(f"❌ 오류 발생: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("🔄 팀-시즌 매핑(sl_team_season_map) 작업을 시작합니다...\n")
    for sport, league in TARGET_LEAGUES:
        sync_team_season_map(sport, league)