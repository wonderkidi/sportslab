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

TARGET_LEAGUES = [
    ("basketball", "nba"),
    ("soccer", "eng.1"),
    ("baseball", "mlb"),
    ("football", "nfl"),
    ("hockey", "nhl"),
    ("soccer", "esp.1"),
    ("soccer", "ger.1"),
    ("soccer", "ita.1"),
    ("soccer", "uefa.champions"),
    ("soccer", "kor.1"),
    ("soccer", "jpn.1"),
    ("soccer", "usa.1")
]

# 수집할 시즌 리스트
TARGET_YEARS = [2025, 2024, 2023, 2022, 2021, 2020]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_season_exists(cur, league_id, year):
    if not year: return None
    
    cur.execute("SELECT id FROM sl_seasons WHERE league_id = %s AND year = %s", (league_id, year))
    row = cur.fetchone()
    if row: return row[0]
    
    try:
        cur.execute("""
            INSERT INTO sl_seasons (league_id, year, is_current)
            VALUES (%s, %s, false)
            ON CONFLICT (league_id, year) DO NOTHING
            RETURNING id;
        """, (league_id, year))
        new_row = cur.fetchone()
        if new_row: return new_row[0]
        
        cur.execute("SELECT id FROM sl_seasons WHERE league_id = %s AND year = %s", (league_id, year))
        row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        return None

def sync_player_season_stats(sport, league):
    print(f"🚀 [{league}] 선수 시즌 스탯 동기화 시작 (구조 수정됨)...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. 리그 ID 조회
    try:
        cur.execute("SELECT id FROM sl_leagues WHERE slug = %s", (league,))
        row = cur.fetchone()
        if not row:
            print(f"⚠️ [{league}] 리그 정보 없음.")
            return
        league_db_id = row[0]
    except Exception as e:
        print(f"❌ DB 에러: {e}")
        return

    # 2. 팀 목록 가져오기
    teams_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
    print(f"📡 [API CALL] Teams: {teams_url}")
    
    try:
        res = requests.get(teams_url, params={'limit': 1000})
        teams = res.json().get('sports', [])[0].get('leagues', [])[0].get('teams', [])
    except Exception:
        print(f"❌ API 호출 실패 ({teams_url})")
        return

    total_updated = 0
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for t in teams:
        team_id = int(t['team']['id'])
        team_name = t['team']['displayName']
        print(f"\n📂 [{team_name}] 처리 중...")

        roster_url = f"{teams_url}/{team_id}"
        
        try:
            r_res = requests.get(roster_url, params={'enable': 'roster'})
            athletes = r_res.json().get('team', {}).get('athletes', [])
        except:
            continue

        player_count_in_team = 0
        for p in athletes:
            player_id = int(p['id'])
            player_name = p.get('fullName', 'Unknown')
            
            splits_base_url = f"https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{player_id}/splits"
            
            saved_seasons_count = 0
            
            for year in TARGET_YEARS:
                full_url = f"{splits_base_url}?season={year}"
                # print(f"    📡 [GET] {full_url}")

                try:
                    s_res = requests.get(splits_base_url, params={'season': year}, headers=headers)
                    if s_res.status_code != 200: continue
                    
                    data = s_res.json()
                    
                    # [수정됨] 1. Labels는 최상위에 위치
                    labels = data.get('names', []) or data.get('labels', [])
                    
                    # [수정됨] 2. splitCategories 안에서 'split' 카테고리 찾기
                    split_categories = data.get('splitCategories', [])
                    general_split_category = next((cat for cat in split_categories if cat.get('name') == 'split'), None)
                    
                    if not general_split_category: 
                        # 카테고리가 없으면 데이터가 없는 것
                        continue

                    splits_list = general_split_category.get('splits', [])
                    
                    # [수정됨] 3. 'Total' (All Splits) 항목만 찾기
                    # DB Unique Constraint (Player, Season, Team) 때문에 하나만 저장해야 함.
                    # 'All Splits'가 시즌 전체 합계/평균입니다.
                    total_split = next((s for s in splits_list if s.get('abbreviation') == 'Total'), None)
                    
                    if not total_split: continue
                    
                    # 데이터 확보 완료
                    stats_values = total_split.get('stats', [])
                    if not stats_values: continue
                    
                    # 시즌 ID 확보
                    season_db_id = ensure_season_exists(cur, league_db_id, year)
                    if not season_db_id: continue
                    
                    save_data = {
                        "labels": labels,
                        "values": stats_values,
                        "type": "Regular Season", # Total은 보통 정규시즌 성적
                        "raw": total_split
                    }
                    
                    stat_team_id = team_id 

                    sql = """
                        INSERT INTO sl_player_season_stats 
                        (player_id, season_id, team_id, stats)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (player_id, season_id, team_id) 
                        DO UPDATE SET 
                            stats = EXCLUDED.stats,
                            updated_at = NOW();
                    """
                    cur.execute(sql, (player_id, season_db_id, stat_team_id, json.dumps(save_data)))
                    total_updated += 1
                    saved_seasons_count += 1
                    print(f"      ✅ OK ({year}): {full_url}")

                except Exception as e:
                    # print(f"      ❌ Err ({year}): {e}")
                    continue

            if saved_seasons_count > 0:
                # print(f"    ✨ {player_name}: {saved_seasons_count}개 시즌 저장됨")
                player_count_in_team += 1
            
            conn.commit()
            time.sleep(0.05) 
        
        if player_count_in_team == 0:
             print(f"    ⚠️ {team_name}: 저장된 데이터 없음")

    cur.close()
    conn.close()
    print(f"✅ [{league}] 총 {total_updated}건의 시즌 스탯 저장 완료.")

if __name__ == "__main__":
    for sport, league in TARGET_LEAGUES:
        sync_player_season_stats(sport, league)