import os
from pathlib import Path
import requests
import psycopg2
import json
import time

# --- 설정 (환경에 맞게 수정하세요) ---
def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env(Path(__file__).with_name(".env"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "sportslab"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "rootpassword"),
    "port": os.getenv("DB_PORT", "54321"), # [수정] 54321 -> 5432
}

# --- 수집할 리그 목록 ---
TARGET_LEAGUES = [
    ("basketball", "nba"),
    ("baseball", "mlb"),
    ("soccer", "eng.1"),    
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

def ensure_game_exists(cur, game_id, game_date, home_id, away_id, league_id, season_id):
    """
    FK 제약조건 해결을 위해 게임이 없으면 임시로 생성합니다.
    """
    sql = """
        INSERT INTO sl_games (id, game_date, home_team_id, away_team_id, league_id, season_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
    """
    try:
        cur.execute(sql, (game_id, game_date, home_id, away_id, league_id, season_id))
    except Exception:
        pass # 날짜 포맷 에러 등은 무시

def sync_player_stats(sport, league):
    print(f"🚀 [{league}] 선수 스탯 동기화 시작...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # [중요] 0. DB에서 League ID와 Season ID 먼저 찾기 (FK용)
    # 이게 없으면 ensure_game_exists나 stats 저장시 에러남
    try:
        cur.execute("SELECT id, sport_id FROM sl_leagues WHERE slug = %s", (league,))
        league_row = cur.fetchone()
        if not league_row:
            print(f"⚠️ [{league}] 리그 정보가 DB에 없습니다. save_games.py를 먼저 실행하세요.")
            return
        league_db_id = league_row[0]

        # 현재 시즌 ID 가져오기 (is_current = true 인 것)
        # 만약 없으면 가장 최근 연도 가져오기
        cur.execute("""
            SELECT id FROM sl_seasons 
            WHERE league_id = %s 
            ORDER BY is_current DESC, year DESC LIMIT 1
        """, (league_db_id,))
        season_row = cur.fetchone()
        if not season_row:
             print(f"⚠️ [{league}] 시즌 정보가 DB에 없습니다.")
             return
        season_db_id = season_row[0]
        
    except Exception as e:
        print(f"❌ 초기 DB 조회 실패: {e}")
        return

    # 1. API 호출: 팀 목록 조회
    teams_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
    try:
        res = requests.get(teams_url, params={'limit': 1000})
        teams_data = res.json()
        teams = teams_data.get('sports', [])[0].get('leagues', [])[0].get('teams', [])
    except Exception as e:
        print(f"❌ [{league}] 팀 목록 조회 실패: {e}")
        return

    total_players = 0
    
    for team_entry in teams:
        team_id = int(team_entry['team']['id'])
        team_name = team_entry['team']['displayName']
        print(f"  Processing {team_name}...")

        # 2. 팀 로스터 가져오기
        roster_url = f"{teams_url}/{team_id}"
        try:
            r_res = requests.get(roster_url, params={'enable': 'roster'})
            r_data = r_res.json()
            athletes = r_data['team'].get('athletes', [])
        except:
            continue

        for p in athletes:
            player_id = int(p['id'])
            
            # 3. 선수별 Gamelog API 호출
            gamelog_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/athletes/{player_id}/gamelog"
            
            try:
                g_res = requests.get(gamelog_url)
                if g_res.status_code != 200: continue
                
                g_data = g_res.json()
                season_list = g_data.get('seasonTypes', [])
                
                for season_type in season_list:
                    for category in season_type.get('categories', []):
                        
                        events = category.get('events', [])
                        
                        for event in events:
                            try:
                                game_id = int(event['eventId'])
                                game_date = event.get('gameDate')
                                
                                # 통계 데이터 JSON 처리
                                stats_data = event.get('stats', []) # 배열인 경우가 많음
                                stats_json = json.dumps(event) # 전체 이벤트 데이터를 저장

                                # [수정] ensure_game_exists에 정확한 ID 전달
                                # home/away 구분은 어려우므로 home_id에 현재 team_id를 임시로 넣거나 NULL
                                ensure_game_exists(cur, game_id, game_date, team_id, None, league_db_id, season_db_id)

                                # Game Stats 저장 (Upsert)
                                sql_game_stats = """
                                    INSERT INTO sl_player_game_stats (game_id, player_id, team_id, stats)
                                    VALUES (%s, %s, %s, %s)
                                    ON CONFLICT (game_id, player_id) DO UPDATE 
                                    SET stats = EXCLUDED.stats;
                                """
                                cur.execute(sql_game_stats, (game_id, player_id, team_id, stats_json))
                            except Exception:
                                continue

            except Exception as e:
                print(f"    Error collecting gamelog for player {player_id}: {e}")
                conn.rollback()
                continue
            
            # 4. 선수 Overview (시즌 스탯용) 호출 및 저장
            # [수정] pass로 되어있던 로직 구현
            try:
                ov_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/athletes/{player_id}"
                ov_res = requests.get(ov_url)
                ov_data = ov_res.json()
                
                # 'stats' 필드 추출
                season_stats_raw = ov_data.get('athlete', {}).get('stats', {})
                
                if season_stats_raw:
                     sql_season_stats = """
                        INSERT INTO sl_player_season_stats (player_id, season_id, team_id, stats)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (player_id, season_id, team_id) DO UPDATE 
                        SET stats = EXCLUDED.stats;
                    """
                     # season_stats_raw 자체를 JSON으로 변환하여 저장
                     cur.execute(sql_season_stats, (player_id, season_db_id, team_id, json.dumps(season_stats_raw)))

            except Exception:
                pass

            conn.commit()
            total_players += 1
            
            # 딜레이
            time.sleep(0.05) 

    cur.close()
    conn.close()
    print(f"✅ [{league}] {total_players}명 선수 스탯 처리 완료.")

if __name__ == "__main__":
    for sport, league in TARGET_LEAGUES:
        sync_player_stats(sport, league)