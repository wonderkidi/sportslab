import os
import requests
import psycopg2
import hashlib
import json
from datetime import datetime
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

def get_game_id_hash(naver_game_id):
    return int(hashlib.sha256(str(naver_game_id).encode('utf-8')).hexdigest()[:15], 16)

def get_team_id_hash(team_code):
    # K-League 팀 코드를 기반으로 고유 ID 생성 (900 + numeric_code or hash)
    if not team_code: return 0
    try:
        return int(f"900{int(team_code)}")
    except:
        h = int(hashlib.md5(team_code.encode()).hexdigest()[:6], 16)
        return int(f"900{h}")

def ensure_team_exists(cur, team_code, team_name, logo_url=None):
    if not team_code: return None
    
    full_name = KLEAGUE_TEAM_MAP.get(team_code, team_name)
    internal_id = get_team_id_hash(team_code)
    
    cur.execute("SELECT id FROM sl_teams WHERE id = %s", (internal_id,))
    row = cur.fetchone()
    if row:
        if logo_url:
            cur.execute("UPDATE sl_teams SET logo_url = %s, name = %s WHERE id = %s", (logo_url, full_name, internal_id))
        return internal_id
    
    cur.execute("""
        INSERT INTO sl_teams (id, name, logo_url, created_at, updated_at) 
        VALUES (%s, %s, %s, NOW(), NOW()) 
    """, (internal_id, full_name, logo_url))
    return internal_id

def sync_kleague_games(year, month):
    print(f"⚽ {year}년 {month}월 K-League 경기 데이터 수집 중...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM sl_leagues WHERE slug = 'k-league'")
        row = cur.fetchone()
        if row: league_id = row[0]
        else:
            cur.execute("INSERT INTO sl_sports (name, slug) VALUES ('Soccer', 'soccer') ON CONFLICT (name) DO NOTHING")
            cur.execute("SELECT id FROM sl_sports WHERE slug='soccer'")
            sport_id = cur.fetchone()[0]
            league_id = 100
            cur.execute("INSERT INTO sl_leagues (id, sport_id, name, slug, country, type) VALUES (%s, %s, 'K League', 'k-league', 'South Korea', 'League') ON CONFLICT DO NOTHING", (league_id, sport_id))

        cur.execute("SELECT id FROM sl_seasons WHERE league_id = %s AND year = %s", (league_id, year))
        row = cur.fetchone()
        if row: season_id = row[0]
        else:
            cur.execute("INSERT INTO sl_seasons (league_id, year, is_current) VALUES (%s, %s, true) RETURNING id", (league_id, year))
            season_id = cur.fetchone()[0]

        url = "https://api-gw.sports.naver.com/schedule/games"
        params = {
            "fields": "basic,status,team,score",
            "upperCategoryId": "kfootball",
            "categoryId": "kleague",
            "fromDate": f"{year}-{month:02d}-01",
            "toDate": f"{year}-{month:02d}-31",
            "size": 300
        }

        res = requests.get(url, params=params)
        data = res.json()
        games = data.get('result', {}).get('games', [])
        
        count = 0
        for g in games:
            try:
                game_id_str = g.get('gameId')
                game_date = g.get('gameDateTime')
                status_info = g.get('statusInfo', {})
                status_origin = status_info.get('name', '') if isinstance(status_info, dict) else str(status_info)

                home_code = g.get('homeTeamCode')
                away_code = g.get('awayTeamCode')
                home_name = g.get('homeTeamName')
                away_name = g.get('awayTeamName')
                home_logo = g.get('homeTeamEmblemUrl')
                away_logo = g.get('awayTeamEmblemUrl')

                if not game_id_str: continue

                game_db_id = get_game_id_hash(game_id_str)
                home_id = ensure_team_exists(cur, home_code, home_name, home_logo)
                away_id = ensure_team_exists(cur, away_code, away_name, away_logo)
                
                status_map = { "종료": "STATUS_FINAL", "취소": "STATUS_CANCELLED", "예정": "STATUS_SCHEDULED", "경기중": "STATUS_IN_PROGRESS" }
                status = status_map.get(status_origin, "STATUS_SCHEDULED")
                
                home_score = g.get('homeTeamScore') or 0
                away_score = g.get('awayTeamScore') or 0
                if home_score == '': home_score = 0
                if away_score == '': away_score = 0
                
                score_detail = json.dumps(g.get('score', {}))

                sql = """
                    INSERT INTO sl_games 
                    (id, season_id, league_id, home_team_id, away_team_id, game_date, status, home_score, away_score, score_detail)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE 
                    SET status = EXCLUDED.status,
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        score_detail = EXCLUDED.score_detail;
                """
                cur.execute(sql, (game_db_id, season_id, league_id, home_id, away_id, game_date, status, home_score, away_score, score_detail))
                count += 1
            except Exception: continue

        conn.commit()
        print(f"🏁 {year}년 {month}월: 총 {count}경기 저장 완료.")
    except Exception as e:
        conn.rollback()
        print(f"❌ 에러: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    for m in range(3, 12):
        sync_kleague_games(2024, m)
