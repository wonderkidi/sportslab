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

# --- 수집할 리그 목록 ---
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
    ("soccer", "usa.1") 
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def sync_player_squads(sport, league_slug):
    print(f"👕 [{league_slug}] 선수단(Squad/Roster) 정보 동기화 중...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. API 호출 (팀 목록)
    base_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league_slug}/teams"
    
    try:
        res = requests.get(base_url, params={'limit': 1000})
        if res.status_code != 200:
            print(f"⚠️ API 호출 실패: {res.status_code}")
            return
        data = res.json()

        # 2. 리그 및 시즌 파싱
        try:
            league_data = data['sports'][0]['leagues'][0]
            league_id = int(league_data['id'])
            season_year = league_data.get('season', {}).get('year')
        except (IndexError, KeyError):
            print(f"⚠️ [{league_slug}] 리그/시즌 정보를 찾을 수 없습니다.")
            return

        print(f"  - Season Year: {season_year}")

        # 3. DB에서 시즌 ID(season_id) 조회 (없으면 생성)
        cur.execute("SELECT id FROM sl_seasons WHERE league_id=%s AND year=%s", (league_id, season_year))
        row = cur.fetchone()
        
        if row:
            season_db_id = row[0]
        else:
            # 시즌 정보가 없으면 자동 생성
            cur.execute("""
                INSERT INTO sl_seasons (league_id, year, is_current)
                VALUES (%s, %s, true) RETURNING id
            """, (league_id, season_year))
            season_db_id = cur.fetchone()[0]

        # 4. 각 팀별 로스터 순회
        teams = league_data.get('teams', [])
        total_squad_count = 0

        for t in teams:
            team_id = int(t['team']['id'])
            team_name = t['team']['displayName']
            
            # 로스터 API 호출 (enable=roster)
            roster_url = f"{base_url}/{team_id}"
            r_res = requests.get(roster_url, params={'enable': 'roster'})
            
            if r_res.status_code != 200: continue
            
            r_data = r_res.json()
            athletes = r_data['team'].get('athletes', [])
            
            # print(f"    Processing {team_name} ({len(athletes)} players)...")

            for p in athletes:
                player_id = int(p['id'])
                player_name = p['fullName']
                
                # 포지션 (예: FW, QB, Pitcher)
                position = p.get('position', {}).get('abbreviation', 'Unknown')
                
                # 등번호 (문자열일 수 있음 "00", "10") -> 숫자로 변환
                jersey_str = p.get('jersey', '0')
                try:
                    jersey_number = int(jersey_str)
                except ValueError:
                    jersey_number = None

                # [FK 방지] 만약 sl_players 테이블에 선수가 없으면 최소 정보로 생성
                # (save_players.py를 안 돌렸을 경우를 대비)
                cur.execute("SELECT 1 FROM sl_players WHERE id=%s", (player_id,))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO sl_players (id, name) VALUES (%s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (player_id, player_name))

                # [FK 방지] 팀이 없으면 최소 정보로 생성
                cur.execute("SELECT 1 FROM sl_teams WHERE id=%s", (team_id,))
                if not cur.fetchone():
                     cur.execute("""
                        INSERT INTO sl_teams (id, name) VALUES (%s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (team_id, team_name))

                # [INSERT] Squad 정보 저장
                # ON CONFLICT: 이미 해당 시즌, 해당 팀에 등록된 선수면 정보 업데이트
                sql_squad = """
                    INSERT INTO sl_player_squads 
                    (player_id, team_id, season_id, position, jersey_number, is_active)
                    VALUES (%s, %s, %s, %s, %s, true)
                    ON CONFLICT (player_id, team_id, season_id) 
                    DO UPDATE SET 
                        position = EXCLUDED.position,
                        jersey_number = EXCLUDED.jersey_number,
                        is_active = true;
                """
                cur.execute(sql_squad, (player_id, team_id, season_db_id, position, jersey_number))
                total_squad_count += 1

            conn.commit() # 한 팀 처리 후 커밋

        print(f"✅ [{league_slug}] 총 {total_squad_count}명의 스쿼드 정보 저장 완료.")

    except Exception as e:
        conn.rollback()
        print(f"❌ [{league_slug}] 오류 발생: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("🏟️ 선수단(Squad) 테이블 채우기 시작...\n")
    for sport, league in TARGET_LEAGUES:
        sync_player_squads(sport, league)