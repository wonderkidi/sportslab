import os
from pathlib import Path
import requests
import psycopg2
import json
from datetime import datetime

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

def sync_season_schedule(sport, league_slug):
    print(f"🚀 [{league_slug}] 경기 일정(Schedule) 동기화 시작...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    base_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league_slug}/teams"
    
    try:
        # 1. 리그 정보 가져오기
        res = requests.get(base_url, params={'limit': 1000})
        # 응답 코드가 200이 아니면 예외 발생
        res.raise_for_status() 
        data = res.json()
        
        # 데이터 구조 파싱 (안전하게)
        try:
            league_data = data['sports'][0]['leagues'][0]
        except (IndexError, KeyError):
            print(f"⚠️ [{league_slug}] 리그 정보를 찾을 수 없어 건너뜁니다.")
            return

        league_id = int(league_data['id'])
        league_name = league_data['name']
        season_year = league_data.get('season', {}).get('year')
        
        print(f"  - League: {league_name} (ID: {league_id}), Year: {season_year}")

        # [FK 방지 1] sl_leagues 저장
        # (이전 단계에서 slug 컬럼을 DB에 추가했다고 가정합니다)
        sql_league = """
            INSERT INTO sl_leagues (id, name, slug, sport_id)
            VALUES (%s, %s, %s, (SELECT id FROM sl_sports WHERE name=%s LIMIT 1))
            ON CONFLICT (id) DO UPDATE 
            SET name = EXCLUDED.name, slug = EXCLUDED.slug;
        """
        try:
            cur.execute(sql_league, (league_id, league_name, league_slug, sport))
        except Exception as e:
            # 혹시 DB 컬럼 문제 등이 생기면 롤백 후 로그 출력
            conn.rollback()
            print(f"⚠️ 리그 정보 저장 중 에러 (slug 컬럼 확인 필요): {e}")
            # 비상시 slug 제외하고 저장 시도 (필요시 주석 해제)
            # cur.execute("INSERT INTO sl_leagues (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING", (league_id, league_name))

        # [FK 방지 2] sl_seasons 저장
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

        # 2. 각 팀별 스케줄 순회
        teams = league_data.get('teams', [])
        total_games_processed = 0

        for t in teams:
            team_core = t.get('team', {})
            team_id = team_core.get('id')
            team_name = team_core.get('displayName', 'Unknown Team')
            
            if not team_id: continue # 팀 ID 없으면 패스

            # 팀별 스케줄 API 호출
            schedule_url = f"{base_url}/{team_id}/schedule"
            try:
                s_res = requests.get(schedule_url)
                if s_res.status_code != 200: continue
                s_data = s_res.json()
            except:
                continue
            
            events = s_data.get('events', [])
            
            for event in events:
                # [수정됨] 개별 게임 에러 처리 (하나가 망가져도 나머지는 저장)
                try:
                    game_id = int(event['id'])
                    game_date_str = event.get('date') # "2024-03-20T19:00Z"
                    
                    if not game_date_str: continue 

                    # 날짜 파싱
                    game_date = datetime.strptime(game_date_str, "%Y-%m-%dT%H:%MZ")
                    
                    # [핵심 수정] 경기 상태 파싱 (KeyError: 'status' 방지)
                    status_obj = event.get('status', {})
                    status_type = status_obj.get('type', {})
                    status = status_type.get('name', 'STATUS_UNKNOWN') # 값이 없으면 UNKNOWN
                    status_detail = status_type.get('detail', 'Unknown')
                    
                    # [핵심 수정] competitions 파싱 (IndexError 방지)
                    competitions_list = event.get('competitions', [])
                    if not competitions_list: continue # 상세 정보 없으면 패스
                    competitions = competitions_list[0]
                    
                    # 홈/어웨이 팀 찾기
                    comp_list = competitions.get('competitors', [])
                    home_team = next((c for c in comp_list if c['homeAway'] == 'home'), {})
                    away_team = next((c for c in comp_list if c['homeAway'] == 'away'), {})
                    
                    home_id = int(home_team.get('id', 0))
                    away_id = int(away_team.get('id', 0))
                    
                    # 점수 파싱 (None 처리 안전하게)
                    h_score_val = home_team.get('score', {}).get('value')
                    a_score_val = away_team.get('score', {}).get('value')
                    
                    home_score = int(h_score_val) if h_score_val is not None else None
                    away_score = int(a_score_val) if a_score_val is not None else None
                    
                    # 상세 스코어(이닝/쿼터) JSONB
                    venue_obj = competitions.get('venue', {})
                    score_detail = {
                        "status_detail": status_detail,
                        "venue": venue_obj.get('fullName', 'Unknown Venue')
                    }

                    # [INSERT] 게임 저장
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
                    cur.execute(sql_game, (
                        game_id, season_db_id, league_id, 
                        home_id, away_id, game_date, 
                        status, home_score, away_score, 
                        json.dumps(score_detail)
                    ))
                    total_games_processed += 1

                except Exception as inner_e:
                    # 특정 게임 데이터가 이상하면 로그만 찍고 넘어감 (스크립트 중단 방지)
                    # print(f"    ⚠️ Game Skipped (ID: {event.get('id')}): {inner_e}")
                    continue
            
            conn.commit() # 한 팀 처리할 때마다 커밋
            # print(f"    - {team_name}: 스케줄 처리 완료")

        print(f"✅ [{league_slug}] 총 {total_games_processed}건의 경기 정보 처리 완료.")

    except Exception as e:
        conn.rollback()
        print(f"❌ [{league_slug}] 치명적 오류 발생: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("🏟️ 경기 일정 전체 동기화 시작 (방어 로직 적용됨)...\n")
    
    for sport, league in TARGET_LEAGUES:
        sync_season_schedule(sport, league)