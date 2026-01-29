import os
from pathlib import Path
import requests
import psycopg2
import json
import time

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
    ("basketball", "nba"),
    ("soccer", "eng.1"),
    ("baseball", "mlb"),
    ("football", "nfl"),
    ("hockey", "nhl"),
    ("soccer", "esp.1"),
    ("soccer", "ger.1"),
    ("soccer", "ita.1"),
    ("soccer", "fra.1"),
    ("soccer", "uefa.champions"),
    ("soccer", "uefa.europa"),
    ("soccer", "usa.1")
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_game_exists(cur, game_id, game_date, league_id, season_id):
    """
    FK 제약조건 해결을 위해 게임이 없으면 임시로 생성합니다.
    """
    if not game_id: return

    # 날짜가 None이면 에러나므로 방어 로직 추가
    if not game_date:
        # 임시 날짜 생성 (시즌 ID가 있으면 좋겠지만 일단 고정값이라도 넣음)
        game_date = "1970-01-01T00:00:00Z" 

    sql = """
        INSERT INTO sl_games (id, game_date, league_id, season_id, status)
        VALUES (%s, %s, %s, %s, 'STATUS_FINAL')
        ON CONFLICT (id) DO NOTHING;
    """
    try:
        cur.execute(sql, (game_id, game_date, league_id, season_id))
    except Exception:
        pass 

def sync_player_game_stats(sport, league):
    print(f"🚀 [{league}] 선수 경기별 스탯 동기화 시작 (v3 API + Date Fix)...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. DB에서 리그 및 시즌 ID 확보
    try:
        cur.execute("SELECT id FROM sl_leagues WHERE slug = %s", (league,))
        row = cur.fetchone()
        if not row:
            print(f"⚠️ [{league}] 리그 정보 없음. (save_leagues.py 실행 필요)")
            return
        league_db_id = row[0]

        cur.execute("""
            SELECT id, year FROM sl_seasons 
            WHERE league_id = %s ORDER BY is_current DESC, year DESC LIMIT 1
        """, (league_db_id,))
        row = cur.fetchone()
        
        if not row:
             print(f"⚠️ [{league}] 시즌 정보 없음.")
             return
        
        season_db_id, season_year = row
        print(f"  ℹ️ Target Season: {season_year}")

    except Exception as e:
        print(f"❌ 초기 설정 실패: {e}")
        return

    # 2. 팀 목록 API 호출
    teams_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
    try:
        res = requests.get(teams_url, params={'limit': 1000})
        teams = res.json().get('sports', [])[0].get('leagues', [])[0].get('teams', [])
    except Exception:
        print(f"❌ API 호출 실패 ({teams_url})")
        return

    total_stats_saved = 0
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for t in teams:
        team_id = int(t['team']['id'])
        team_name = t['team']['displayName']
        print(f"  Processing Team: {team_name}...")

        # 3. 로스터 조회
        roster_url = f"{teams_url}/{team_id}"
        try:
            r_res = requests.get(roster_url, params={'enable': 'roster'})
            athletes = r_res.json().get('team', {}).get('athletes', [])
        except:
            continue

        for p in athletes:
            player_id = int(p['id'])
            
            # 4. Gamelog API v3 호출
            gamelog_url = f"https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{player_id}/gamelog"
            params = {'season': season_year}

            try:
                g_res = requests.get(gamelog_url, params=params, headers=headers)
                if g_res.status_code != 200: continue
                
                g_data = g_res.json()
                season_types = g_data.get('seasonTypes', [])
                
                for s_type in season_types:
                    categories = s_type.get('categories', [])
                    for cat in categories:
                        events = cat.get('events', [])
                        
                        for event in events:
                            game_id_str = event.get('eventId')
                            if not game_id_str: continue
                            game_id = int(game_id_str)
                            
                            # [핵심 수정] 날짜 파싱 로직 강화
                            # gameDate가 없으면 date를 찾고, 그것도 없으면 임시 날짜 사용
                            game_date = event.get('gameDate')
                            if not game_date:
                                game_date = event.get('date')
                            if not game_date:
                                # 날짜가 아예 없으면 시즌 시작일로 임시 설정 (DB 에러 방지용)
                                game_date = f"{season_year}-01-01T00:00:00Z"
                            
                            # 스탯 데이터 준비
                            stats_json = json.dumps(event)
                            minutes_played = None
                            rating = None

                            # [FK 방지] 게임 임시 생성
                            ensure_game_exists(cur, game_id, game_date, league_db_id, season_db_id)

                            # [INSERT]
                            sql = """
                                INSERT INTO sl_player_game_stats 
                                (game_id, player_id, team_id, minutes_played, rating, stats)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (game_id, player_id) DO UPDATE 
                                SET stats = EXCLUDED.stats,
                                    team_id = EXCLUDED.team_id; 
                            """
                            cur.execute(sql, (
                                game_id, 
                                player_id, 
                                team_id, 
                                minutes_played, 
                                rating, 
                                stats_json
                            ))
                            total_stats_saved += 1
            
            except Exception:
                conn.rollback()
                continue
            
            conn.commit()
            time.sleep(0.05) 

    cur.close()
    conn.close()
    print(f"✅ [{league}] 총 {total_stats_saved}건의 경기 스탯 저장 완료.")

if __name__ == "__main__":
    for sport, league in TARGET_LEAGUES:
        sync_player_game_stats(sport, league)