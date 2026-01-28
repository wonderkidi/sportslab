import os
from pathlib import Path

import requests
import psycopg2
import re
import json

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

def sync_teams_only(sport, league):
    print(f"🚀 [{league}] 팀 정보 수집 시작...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return

    # ESPN API 호출 (팀 목록만 조회)
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
    params = {'limit': 1000} # 모든 팀 다 가져오기
    
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        
        # 데이터 파싱
        try:
            teams = data['sports'][0]['leagues'][0]['teams']
        except (KeyError, IndexError):
            print(f"⚠️ [{league}] 팀 데이터를 찾을 수 없습니다. (시즌 비활성 등)")
            teams = []

        count = 0
        for team_entry in teams:
            t = team_entry['team']
            
            team_id = int(t['id'])
            team_name = t['displayName']
            team_code = t.get('abbreviation')
            
            # 로고 URL 안전하게 가져오기
            logo_url = None
            if 'logos' in t and len(t['logos']) > 0:
                logo_url = t['logos'][0]['href']

            # DB 저장 (sl_teams)
            sql = """
                INSERT INTO sl_teams (id, name, code, logo_url)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE 
                SET name = EXCLUDED.name, 
                    code = EXCLUDED.code,
                    logo_url = EXCLUDED.logo_url;
            """
            cur.execute(sql, (team_id, team_name, team_code, logo_url))
            count += 1
            
        conn.commit()
        print(f"✅ [{league}] {count}개 팀 저장 완료!")

    except Exception as e:
        conn.rollback()
        print(f"❌ [{league}] 에러 발생: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("🏟️ 전 세계 주요 리그 팀 정보 업데이트 중...\n")
    
    for sport, league in TARGET_LEAGUES:
        sync_teams_only(sport, league)
        
    print("\n✨ 모든 작업이 완료되었습니다.")