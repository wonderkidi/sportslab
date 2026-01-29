import os
import requests
import psycopg2
import json
from datetime import datetime, timedelta
from pathlib import Path

# --- 환경 설정 ---
def load_env(path: Path) -> None:
    if not path.exists(): return
    for line in path.read_text(encoding="utf-8").splitlines():
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

# (Sport, ESPN_Key, Frontend_Slug)
TARGET_LEAGUES = [
    ("baseball", "mlb", "mlb"),
    ("basketball", "nba", "nba"),
    ("football", "nfl", "nfl"),
    ("hockey", "nhl", "nhl"),
    ("soccer", "eng.1", "epl"),
    ("soccer", "esp.1", "la-liga"),
    ("soccer", "ger.1", "bundesliga"),
    ("soccer", "ita.1", "serie-a"),
    ("soccer", "fra.1", "ligue-1"),
    ("soccer", "uefa.champions", "ucl"),
    ("soccer", "kor.1", "k-league"),
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def update_monitor(sport, espn_key, frontend_slug):
    print(f"📡 Updating results for {frontend_slug} ({espn_key})...")
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Scoreboard API: 최근/현재 경기 정보 조회
        url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{espn_key}/scoreboard"
        # dates 파라미터 없이 호출하면 '현재' 윈도우(오늘/어제/내일 등)를 반환함
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()

        # 1. 리그 정보 동기화
        try:
            l_data = data['leagues'][0]
            league_id = int(l_data['id'])
            league_name = l_data['name']
            
            # Frontend slug로 저장하여 매핑 유지
            sql_league = """
                INSERT INTO sl_leagues (id, name, slug, sport_id)
                VALUES (%s, %s, %s, (SELECT id FROM sl_sports WHERE name=%s LIMIT 1))
                ON CONFLICT (id) DO UPDATE 
                SET name = EXCLUDED.name, slug = EXCLUDED.slug;
            """
            # sport 이름을 sl_sports 테이블의 name과 매칭 (대소문자 주의 필요시 수정)
            # 여기서는 sport 변수("baseball") -> DB("Baseball") 매핑을 위해 title() 사용 등 고려
            # 기존 DB sport name이 "Baseball", "Soccer" 등일 수 있음.
            # safe matching: lowercase check
            cur.execute(sql_league, (league_id, league_name, frontend_slug, sport.title() if sport != 'mma' else 'MMA'))
            
            # 시즌 정보 파싱
            season_year = l_data.get('season', {}).get('year')
            season_db_id = None
            if season_year:
                cur.execute("SELECT id FROM sl_seasons WHERE league_id=%s AND year=%s", (league_id, season_year))
                row = cur.fetchone()
                if row:
                    season_db_id = row[0]
                else:
                    cur.execute("""
                        INSERT INTO sl_seasons (league_id, year, is_current)
                        VALUES (%s, %s, true) RETURNING id
                    """, (league_id, season_year))
                    season_db_id = cur.fetchone()[0]

        except (IndexError, KeyError) as e:
            print(f"⚠️ League info mismatch for {espn_key}: {e}")
            return

        # 2. 경기(Event) 루프
        events = data.get('events', [])
        updated_count = 0

        for event in events:
            try:
                game_id = int(event['id'])
                date_str = event.get('date')
                if not date_str: continue
                game_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%MZ")

                # Status
                status_obj = event.get('status', {})
                status_type = status_obj.get('type', {})
                status_name = status_type.get('name', 'STATUS_UNKNOWN')
                status_detail = status_type.get('detail', 'Unknown')

                # Competition data
                competitions = event.get('competitions', [])
                if not competitions: continue
                comp = competitions[0]
                venue = comp.get('venue', {}).get('fullName', 'Unknown Venue')

                competitors = comp.get('competitors', [])
                home_comp = next((c for c in competitors if c['homeAway'] == 'home'), None)
                away_comp = next((c for c in competitors if c['homeAway'] == 'away'), None)

                if not home_comp or not away_comp: continue

                # --- [중요] 팀 정보 즉시 동기화 (Upsert) ---
                for c_data in [home_comp, away_comp]:
                    team = c_data.get('team', {})
                    t_id = int(team.get('id', 0))
                    t_name = team.get('displayName', 'Unknown')
                    t_code = team.get('abbreviation', '')
                    t_logo = team.get('logo')

                    if t_id > 0:
                        sql_team = """
                            INSERT INTO sl_teams (id, name, code, logo_url)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE
                            SET name = EXCLUDED.name, code = EXCLUDED.code, logo_url = EXCLUDED.logo_url;
                        """
                        cur.execute(sql_team, (t_id, t_name, t_code, t_logo))

                home_id = int(home_comp['id'])
                away_id = int(away_comp['id'])
                home_score = int(home_comp.get('score', 0) or 0)
                away_score = int(away_comp.get('score', 0) or 0)

                # 게임 저장
                score_detail = {"status_detail": status_detail, "venue": venue}
                
                sql_game = """
                    INSERT INTO sl_games 
                    (id, season_id, league_id, home_team_id, away_team_id, game_date, status, home_score, away_score, score_detail)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE 
                    SET status = EXCLUDED.status,
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        score_detail = EXCLUDED.score_detail;
                """
                cur.execute(sql_game, (game_id, season_db_id, league_id, home_id, away_id, game_date, status_name, home_score, away_score, json.dumps(score_detail)))
                updated_count += 1
                
            except Exception as e:
                # print(f"Skipping event {event.get('id')}: {e}")
                continue

        conn.commit()
        print(f"✅ {frontend_slug}: Updated {updated_count} games.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating {frontend_slug}: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("🔄 Starting Live Scoreboard Update...\n")
    for sp, key, slug in TARGET_LEAGUES:
        update_monitor(sp, key, slug)
    print("\n✨ Update Complete.")
