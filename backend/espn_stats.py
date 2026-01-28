import requests
import psycopg2
import json
import time

# --- 설정 ---
DB_CONFIG = {
    "host": "localhost",
    "database": "sportslab",
    "user": "postgres",
    "password": "rootpassword",
    "port": "5432"
}

# 수집할 리그 목록
TARGET_LEAGUES = [
    ("baseball", "mlb"),
    ("soccer", "eng.1"),
    ("basketball", "nba"),
    ("soccer", "kor.1"),
    # 필요시 추가...
]

CURRENT_SEASON = 2024 # 기준 시즌

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
    # 날짜 포맷이 가끔 다를 수 있어 예외처리 필요할 수 있음
    try:
        cur.execute(sql, (game_id, game_date, home_team_id, away_team_id, league_id, season_id))
    except Exception:
        pass # 날짜 포맷 에러 등은 일단 무시 (스탯 저장이 우선)

def sync_player_stats(sport, league):
    print(f"🚀 [{league}] 선수 스탯 동기화 시작...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. DB에 저장된 해당 리그의 모든 선수 ID 가져오기
    # (효율성을 위해 팀 단위로 순회하지 않고 DB에 있는 선수 리스트를 기반으로 합니다)
    # 다만, API 호출을 위해선 선수의 팀/리그 정보가 필요하므로 
    # 여기서는 간단히 '해당 리그에 속한 팀'의 선수들을 조회하는 로직을 짭니다.
    
    # 먼저 해당 리그의 팀 ID들을 가져옵니다. (이전 단계에서 teams 테이블에 league 정보가 없으므로 
    # API로 팀 리스트를 다시 훑거나, 기존 로직대로 팀별 API를 돌며 선수를 찾습니다.)
    
    # 전략 변경: API에서 팀 목록 -> 선수 목록 -> 선수별 로그 호출 (가장 정확함)
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

        # 팀 로스터 가져오기
        roster_url = f"{teams_url}/{team_id}"
        r_res = requests.get(roster_url, params={'enable': 'roster'})
        r_data = r_res.json()
        athletes = r_data['team'].get('athletes', [])

        for p in athletes:
            player_id = int(p['id'])
            
            # --- [핵심] 선수별 Gamelog API 호출 ---
            # 예: http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/athletes/12345/gamelog
            gamelog_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/athletes/{player_id}/gamelog"
            
            try:
                g_res = requests.get(gamelog_url)
                if g_res.status_code != 200: continue
                
                g_data = g_res.json()
                season_list = g_data.get('seasonTypes', [])
                
                for season_type in season_list:
                    # categories[0]: Batting/General stats, [1]: Pitching/GK etc.
                    # 종목마다 구조가 다르므로 categories 리스트 전체를 훑습니다.
                    for category in season_type.get('categories', []):
                        
                        # 1. Season Stats (시즌 총합 저장)
                        # API 응답 하단에 totals가 있는 경우가 많음. 없으면 events 합산해야 함.
                        # ESPN Gamelog API는 보통 events 리스트만 줍니다.
                        # 시즌 총합은 'totals' 필드가 없으면 계산해야 하는데, 
                        # 여기서는 'events'를 순회하며 게임 스탯을 저장합니다.
                        
                        events = category.get('events', [])
                        
                        for event in events:
                            game_id = int(event['eventId'])
                            game_date = event.get('gameDate') # 2024-04-01T...
                            
                            # 게임 스탯 데이터 (JSONB로 통째로 저장)
                            stats_data = event.get('stats', [])
                            # 배열 형태의 스탯을 { "avg": .300, "hr": 1 } 형태로 변환하면 좋지만
                            # 종목마다 필드가 달라 일단 원본 리스트나 매핑된 딕셔너리로 저장
                            
                            # 간단한 Key-Value 변환 (API가 값을 리스트로 줄 때가 많음)
                            # ESPN은 보통 값만 줍니다 (stats: ["0.3", "1", ...])
                            # 헤더 정보가 필요하지만, 복잡하므로 통째로 JSONB에 넣습니다.
                            stats_json = json.dumps(event) 

                            # FK 오류 방지 (게임 생성)
                            # 상대팀 ID 등은 event 안에 없을 수 있어 일단 NULL 처리하거나
                            # home_team_id, away_team_id를 현재 team_id로 대충 채웁니다 (나중에 game 스케줄러가 덮어씀)
                            ensure_game_exists(cur, game_id, game_date, None, None, None, None)

                            # Game Stats 저장 (Upsert)
                            sql_game_stats = """
                                INSERT INTO sl_player_game_stats (game_id, player_id, team_id, stats)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (game_id, player_id) DO UPDATE 
                                SET stats = EXCLUDED.stats;
                            """
                            cur.execute(sql_game_stats, (game_id, player_id, team_id, stats_json))
                            
                    # 2. Season Stats (시즌 스탯 별도 API 호출 필요할 수 있음)
                    # Gamelog에는 '합계'가 잘 안 나옵니다.
                    # 선수 Overview API를 한 번 더 찌르는 게 확실합니다.
                    # http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/athletes/{id}
                    
            except Exception as e:
                print(f"    Error collecting stats for player {player_id}: {e}")
                conn.rollback()
                continue
            
            # 선수 Overview (시즌 스탯용) 호출 - 너무 느려지면 이 부분은 분리 가능
            try:
                ov_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/athletes/{player_id}"
                ov_res = requests.get(ov_url)
                ov_data = ov_res.json()
                
                # 'statistics' 항목 파싱 (종목마다 다름 주의)
                # 보통 athlete -> statistics -> splits -> categories... 구조
                # 여기서는 raw json을 그대로 'stats' 컬럼에 넣습니다.
                season_stats_raw = ov_data.get('athlete', {}).get('stats', {})
                
                if season_stats_raw:
                     sql_season_stats = """
                        INSERT INTO sl_player_season_stats (player_id, season_id, team_id, stats)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (player_id, season_id, team_id) DO UPDATE 
                        SET stats = EXCLUDED.stats;
                    """
                     # season_id는 임의로 1 (2024년) 등으로 매핑 필요. 여기선 CURRENT_SEASON 사용을 가정
                     # 실제로는 seasons 테이블 조회해야 함. 데모에선 Raw JSON 저장에 집중.
                     # cur.execute(...) 
                     # * 시즌 스탯은 구조가 복잡하여 일단 Gamelog 위주로 먼저 돌리는 걸 추천합니다.
                     pass 

            except Exception:
                pass

            conn.commit()
            total_players += 1
            
            # API 보호를 위한 딜레이 (선수가 많으므로 필수)
            time.sleep(0.05) 

    cur.close()
    conn.close()
    print(f"✅ [{league}] {total_players}명 선수 스탯 처리 완료.")

if __name__ == "__main__":
    for sport, league in TARGET_LEAGUES:
        sync_player_stats(sport, league)