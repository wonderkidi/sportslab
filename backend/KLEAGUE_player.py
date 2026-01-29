import os
import requests
import psycopg2
import json
import hashlib
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

KLEAGUE_TEAM_MAP = {
    '01': '울산 HD', '03': '포항 스틸러스', '04': '제주 유나이티드',
    '05': '전북 현대 모터스', '09': 'FC 서울', '10': '대전 하나 시티즌',
    '12': '수원 삼성 블루윙즈', '17': '대구 FC', '18': '인천 유나이티드',
    '21': '강원 FC', '22': '광주 FC', '29': '수원 FC', '35': '김천 상무',
    '02': '성남 FC', '06': '부산 아이파크', '07': '전남 드래곤즈', 
    '13': '강원 FC', '15': '경남 FC', '20': '안산 그리너스',
    '23': 'FC 안양', '24': '충남 아산 FC', '25': '서울 이랜드 FC',
    '26': '부천 FC 1995', '27': '김포 FC', '28': '천안 시티 FC', '30': '충북 청주 FC'
}

def get_team_id_hash(team_code):
    if not team_code: return 0
    try:
        return int(f"900{int(team_code)}")
    except:
        h = int(hashlib.md5(team_code.encode()).hexdigest()[:6], 16)
        return int(f"900{h}")

def ensure_team_exists(cur, team_code, team_name):
    if not team_code: return None
    full_name = KLEAGUE_TEAM_MAP.get(team_code, team_name)
    internal_id = get_team_id_hash(team_code)
    
    cur.execute("SELECT id FROM sl_teams WHERE id = %s", (internal_id,))
    if cur.fetchone():
        return internal_id
    
    cur.execute("""
        INSERT INTO sl_teams (id, name, created_at, updated_at) 
        VALUES (%s, %s, NOW(), NOW()) 
        ON CONFLICT (id) DO NOTHING
    """, (internal_id, full_name))
    return internal_id

def sync_kleague_players():
    print("⚽ K-League 선수 정보(Lineup Harvesting) 시작...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 1. 리그 및 시즌 확인
    cur.execute("SELECT id FROM sl_leagues WHERE slug = 'k-league'")
    league_row = cur.fetchone()
    if not league_row:
        print("❌ K-League 리그 정보를 찾을 수 없습니다.")
        return
    league_id = league_row[0]
    
    cur.execute("SELECT id FROM sl_seasons WHERE league_id = %s AND year = 2024", (league_id,))
    season_row = cur.fetchone()
    if not season_row:
        print("❌ 2024 시즌 정보를 찾을 수 없습니다.")
        return
    season_id = season_row[0]

    # 2. 최근 경기들 가져오기
    url = "https://api-gw.sports.naver.com/schedule/games"
    params = {
        "fields": "basic",
        "upperCategoryId": "kfootball",
        "categoryId": "kleague",
        "fromDate": "2024-03-01",
        "toDate": "2024-11-30",
        "size": 500
    }
    
    try:
        res = requests.get(url, params=params)
        games = res.json().get('result', {}).get('games', [])
        print(f"  🔍 총 {len(games)}개의 경기에서 라인업 추출 중...")

        total_players = 0
        processed_games = 0

        for g in games:
            game_id = g.get('gameId')
            home_code = g.get('homeTeamCode')
            away_code = g.get('awayTeamCode')
            home_name = g.get('homeTeamName')
            away_name = g.get('awayTeamName')
            
            if not game_id or not home_code or not away_code: continue

            # 팀 존재 확보
            home_id = ensure_team_exists(cur, home_code, home_name)
            away_id = ensure_team_exists(cur, away_code, away_name)

            # 라인업 API 호출
            lineup_url = f"https://api-gw.sports.naver.com/schedule/games/{game_id}/lineup"
            try:
                l_res = requests.get(lineup_url)
                if l_res.status_code != 200: continue
                
                l_data = l_res.json()
                lineup_data = l_data.get('result', {}).get('lineUpData', {}).get('lineup', {})
                
                if not lineup_data: continue

                processed_games += 1
                
                for side in ['home', 'away']:
                    side_id = home_id if side == 'home' else away_id
                    
                    players_rows = lineup_data.get(side, {}).get('players', [])
                    for row in players_rows:
                        for p in row:
                            p_id = p.get('playerId')
                            p_name = p.get('name')
                            p_pos = p.get('pos')
                            p_num = p.get('shirtNumber')
                            
                            if not p_id or not p_name: continue

                            # Photo URL placeholder for now
                            photo_url = f"https://sports-phinf.pstatic.net/player/kfootball/kleague/{p_id}.png"

                            # sl_players 저장
                            cur.execute("""
                                INSERT INTO sl_players (id, name, photo_url, created_at, updated_at)
                                VALUES (%s, %s, %s, NOW(), NOW())
                                ON CONFLICT (id) DO UPDATE 
                                SET updated_at = NOW();
                            """, (p_id, p_name, photo_url))

                            # sl_player_squads 저장
                            cur.execute("""
                                INSERT INTO sl_player_squads 
                                (player_id, team_id, season_id, position, jersey_number, is_active)
                                VALUES (%s, %s, %s, %s, %s, true)
                                ON CONFLICT (player_id, team_id, season_id) 
                                DO UPDATE SET 
                                    position = EXCLUDED.position,
                                    jersey_number = EXCLUDED.jersey_number,
                                    is_active = true;
                            """, (p_id, side_id, season_id, p_pos, int(p_num) if p_num and p_num.isdigit() else None))
                            
                            total_players += 1
                
                if processed_games % 10 == 0:
                    conn.commit()
                    print(f"    - {processed_games}개 경기 완료 (추출된 누적 선수 스쿼드: {total_players})")

            except Exception as e:
                print(f"    ⚠️ Game {game_id} 처리 중 오류: {e}")
                continue

        conn.commit()
        print(f"🎉 동기화 완료! 총 {processed_games}개 경기에서 중복 포함 {total_players}명의 스쿼드 정보 확인.")

    except Exception as e:
        print(f"❌ 프로세스 에러: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    sync_kleague_players()
