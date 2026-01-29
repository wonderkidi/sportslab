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

NAVER_TEAM_MAP = {
    '두산': '두산 베어스', '롯데': '롯데 자이언츠', '삼성': '삼성 라이온즈',
    '키움': '키움 히어로즈', '한화': '한화 이글스', 'KIA': 'KIA 타이거즈',
    'KT': 'KT 위즈', 'LG': 'LG 트윈스', 'NC': 'NC 다이노스', 'SSG': 'SSG 랜더스'
}

def get_game_id_hash(naver_game_id):
    return int(hashlib.sha256(str(naver_game_id).encode('utf-8')).hexdigest()[:15], 16)

def ensure_team_exists(cur, short_name):
    if not short_name: return None
    full_name = NAVER_TEAM_MAP.get(short_name, short_name)
    
    cur.execute("SELECT id FROM sl_teams WHERE name = %s", (full_name,))
    row = cur.fetchone()
    if row: return row[0]
    
    new_id = int(hashlib.md5(full_name.encode()).hexdigest()[:8], 16)
    cur.execute("""
        INSERT INTO sl_teams (id, name, created_at, updated_at) 
        VALUES (%s, %s, NOW(), NOW()) 
        ON CONFLICT (id) DO NOTHING
    """, (new_id, full_name))
    return new_id

def sync_kbo_games(year, month):
    print(f"🗓️ {year}년 {month}월 KBO 경기 데이터 수집 중...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # 1. 리그 ID 조회 및 생성
        cur.execute("SELECT id FROM sl_leagues WHERE slug = 'kbo'")
        row = cur.fetchone()
        if row:
            league_id = row[0]
        else:
            print("⚠️ KBO 리그 정보 생성 중...")
            cur.execute("INSERT INTO sl_sports (name, slug) VALUES ('Baseball', 'baseball') ON CONFLICT (name) DO NOTHING")
            cur.execute("SELECT id FROM sl_sports WHERE slug='baseball'")
            sport_id = cur.fetchone()[0]
            
            league_id = 200
            cur.execute("""
                INSERT INTO sl_leagues (id, sport_id, name, slug, country, type)
                VALUES (%s, %s, 'KBO League', 'kbo', 'South Korea', 'League')
                ON CONFLICT (id) DO NOTHING
            """, (league_id, sport_id))

        # 2. 시즌 ID 조회 및 생성
        cur.execute("SELECT id FROM sl_seasons WHERE league_id = %s AND year = %s", (league_id, year))
        row = cur.fetchone()
        if row:
            season_id = row[0]
        else:
            cur.execute("""
                INSERT INTO sl_seasons (league_id, year, is_current)
                VALUES (%s, %s, true)
                ON CONFLICT (league_id, year) DO NOTHING
                RETURNING id
            """, (league_id, year))
            # RETURNING으로 못 가져오는 경우 대비
            if cur.rowcount == 0:
                 cur.execute("SELECT id FROM sl_seasons WHERE league_id = %s AND year = %s", (league_id, year))
            season_id = cur.fetchone()[0]

        # 3. 네이버 API 호출
        url = "https://api-gw.sports.naver.com/schedule/games"
        params = {
            "fields": "basic,status,team,score",
            "upperCategoryId": "kbaseball",
            "categoryId": "kbo",
            "fromDate": f"{year}-{month:02d}-01",
            "toDate": f"{year}-{month:02d}-31",
            "size": 200
        }

        res = requests.get(url, params=params)
        data = res.json()
        games = data.get('result', {}).get('games', [])
        
        count = 0
        for g in games:
            try:
                # [디버깅] g가 딕셔너리가 아닌 경우 건너뜀
                if not isinstance(g, dict):
                    print(f"  ⚠️ 잘못된 데이터 형식: {type(g)} -> {g}")
                    continue

                # 데이터 추출 (안전하게 .get 사용)
                game_id_str = g.get('gameId')
                game_date = g.get('gameDateTime')
                
                # statusInfo 처리 (문자열일 경우와 객체일 경우 대비)
                status_info = g.get('statusInfo')
                if isinstance(status_info, dict):
                    status_origin = status_info.get('name', '')
                else:
                    status_origin = str(status_info)

                home_name = g.get('homeTeamName')
                away_name = g.get('awayTeamName')

                # 필수 정보 없으면 스킵
                if not game_id_str or not home_name or not away_name:
                    continue

                # ID 변환
                game_db_id = get_game_id_hash(game_id_str)
                home_id = ensure_team_exists(cur, home_name)
                away_id = ensure_team_exists(cur, away_name)
                
                status_map = {
                    "종료": "STATUS_FINAL", 
                    "취소": "STATUS_CANCELLED", 
                    "예정": "STATUS_SCHEDULED",
                    "경기중": "STATUS_IN_PROGRESS"
                }
                status = status_map.get(status_origin, "STATUS_SCHEDULED")
                
                home_score = g.get('homeTeamScore') or 0
                away_score = g.get('awayTeamScore') or 0
                
                # 빈 문자열('')이 오는 경우 0으로 처리
                if home_score == '': home_score = 0
                if away_score == '': away_score = 0
                
                score_detail = json.dumps(g.get('score', {}))

                # DB 저장
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
                cur.execute(sql, (
                    game_db_id, season_id, league_id, home_id, away_id, game_date, status, home_score, away_score, score_detail
                ))
                count += 1
            
            except Exception as e:
                # 에러 발생 시 해당 데이터 출력
                print(f"  ❌ 데이터 처리 에러: {e}")
                print(f"     데이터 확인: {g}")
                continue

        conn.commit()
        print(f"🏁 {year}년 {month}월: 총 {count}경기 저장 완료.")

    except Exception as e:
        conn.rollback()
        print(f"❌ 전체 프로세스 에러: {e}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    sync_kbo_games(2024, 5)