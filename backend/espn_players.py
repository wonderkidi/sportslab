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
    "port": os.getenv("DB_PORT", "54321"),
}

# --- 1. 도우미 함수: 단위 변환 ---
def parse_height(ht_str):
    # 예: "6' 2\"" -> 188 (cm)
    if not ht_str: return None
    try:
        match = re.match(r"(\d+)'\s*(\d+)", ht_str)
        if match:
            feet = int(match.group(1))
            inches = int(match.group(2))
            return int((feet * 30.48) + (inches * 2.54))
    except:
        pass
    return None

def parse_weight(wt_str):
    # 예: "200 lbs" -> 91 (kg)
    if not wt_str: return None
    try:
        match = re.match(r"(\d+)\s*lbs", wt_str)
        if match:
            lbs = int(match.group(1))
            return int(lbs * 0.453592)
    except:
        pass
    return None

# --- 2. 메인 로직: 데이터 수집 및 저장 ---
def sync_team_roster(sport, league):
    print(f"🚀 [{league}] 데이터 동기화 시작 (테이블: sl_*) ...")
    
    # DB 연결
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"conn :: {conn}")
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return

    # ESPN API 호출 (모든 팀 가져오기)
    teams_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
    params = {'limit': 1000}
    
    try:
        res = requests.get(teams_url, params=params)
        res.raise_for_status()
        data = res.json()
        
        # 실제 팀 리스트 경로 찾기
        teams = data.get('sports', [])[0].get('leagues', [])[0].get('teams', [])
        
        for team_entry in teams:
            t_data = team_entry['team']
            team_id = int(t_data['id'])
            team_name = t_data['displayName']
            
            print(f"  Processing Team: {team_name} (ID: {team_id})...")
            
            # [A] 팀 정보 저장 (Table: sl_teams)
            # 수정됨: teams -> sl_teams
            sql_team = """
                INSERT INTO sl_teams (id, name, code, logo_url)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE 
                SET name = EXCLUDED.name, logo_url = EXCLUDED.logo_url;
            """
            cur.execute(sql_team, (
                team_id, 
                team_name, 
                t_data.get('abbreviation'), 
                t_data.get('logos', [{}])[0].get('href')
            ))
            
            # [B] 로스터(선수단) 상세 조회
            roster_url = f"{teams_url}/{team_id}"
            r_res = requests.get(roster_url, params={'enable': 'roster'})
            r_data = r_res.json()
            athletes = r_data['team'].get('athletes', [])
            
            # [C] 선수 정보 저장 (Table: sl_players)
            for p in athletes:
                p_id = int(p['id'])
                p_name = p['fullName']
                
                # 단위 변환
                height_cm = parse_height(p.get('displayHeight'))
                weight_kg = parse_weight(p.get('displayWeight'))
                
                # 수정됨: players -> sl_players
                sql_player = """
                    INSERT INTO sl_players (id, name, height_cm, weight_kg, nationality, photo_url, biometrics)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE 
                    SET height_cm = EXCLUDED.height_cm, 
                        weight_kg = EXCLUDED.weight_kg,
                        photo_url = EXCLUDED.photo_url;
                """
                # JSONB 데이터 (추가 정보)
                biometrics = {
                    "birthCity": p.get('birthPlace', {}).get('city'),
                    "bats": p.get('bats', {}).get('abbreviation'),
                    "throws": p.get('throws', {}).get('abbreviation')
                }
                
                cur.execute(sql_player, (
                    p_id,
                    p_name,
                    height_cm,
                    weight_kg,
                    p.get('birthPlace', {}).get('country'),
                    p.get('headshot', {}).get('href'),
                    json.dumps(biometrics)
                ))
                
                # [D] 선수-팀 매핑 (Table: sl_player_squads)
                # 주의: season_id는 현재 임의로 처리하거나 sl_seasons 테이블 조회 로직이 필요함.
                # 여기서는 선수 정보(sl_players)와 팀 정보(sl_teams) 저장에 집중합니다.
            
            conn.commit() # 팀 하나 끝날 때마다 커밋
            
        print(f"✅ [{league}] 저장 완료!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 에러 발생: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # # 1. MLB (야구) 저장
    # sync_team_roster("baseball", "mlb")
    # # 2. EPL (축구) 저장
    # sync_team_roster("soccer", "eng.1")
    sync_team_roster("basketball", "nba")
    sync_team_roster("football", "nfl")
    sync_team_roster("hockey", "nhl")
    sync_team_roster("soccer", "esp.1")
    sync_team_roster("soccer", "ger.1")
    sync_team_roster("soccer", "ita.1")
    sync_team_roster("soccer", "fra.1")
    sync_team_roster("soccer", "uefa.champions")
    sync_team_roster("soccer", "uefa.europa") 
    sync_team_roster("soccer", "jpn.1")
    sync_team_roster("soccer", "usa.1")    