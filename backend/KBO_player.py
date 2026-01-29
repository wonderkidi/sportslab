import os
import psycopg2
import time
import re
import json
import hashlib
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

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

KBO_TEAMS = [
    {'code': 'OB', 'name': '두산 베어스'},
    {'code': 'LT', 'name': '롯데 자이언츠'},
    {'code': 'SS', 'name': '삼성 라이온즈'},
    {'code': 'WO', 'name': '키움 히어로즈'},
    {'code': 'HH', 'name': '한화 이글스'},
    {'code': 'HT', 'name': 'KIA 타이거즈'},
    {'code': 'KT', 'name': 'KT 위즈'},
    {'code': 'LG', 'name': 'LG 트윈스'},
    {'code': 'NC', 'name': 'NC 다이노스'},
    {'code': 'SK', 'name': 'SSG 랜더스'}
]

def get_team_id_hash(team_code):
    # KBO_game.py와 동일한 로직
    if not team_code: return 0
    h = int(hashlib.md5(team_code.encode()).hexdigest()[:6], 16)
    return int(f"800{h}")

def sync_kbo_players_selenium():
    print("👤 KBO 선수 정보 및 스쿼드 동기화 시작...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 1. 리그 및 시즌 확인
    cur.execute("SELECT id FROM sl_leagues WHERE slug = 'kbo'")
    league_row = cur.fetchone()
    if not league_row:
        print("❌ KBO 리그 정보를 찾을 수 없습니다. KBO_game.py를 먼저 실행하세요.")
        return
    league_id = league_row[0]
    
    cur.execute("SELECT id FROM sl_seasons WHERE league_id = %s AND year = 2024", (league_id,))
    season_row = cur.fetchone()
    if not season_row:
        print("❌ 2024 시즌 정보를 찾을 수 없습니다.")
        return
    season_id = season_row[0]

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    total_count = 0
    
    try:
        url = "https://www.koreabaseball.com/Player/Search.aspx"
        driver.get(url)
        time.sleep(1)

        for team in KBO_TEAMS:
            team_code = team['code']
            team_name = team['name']
            team_id = get_team_id_hash(team_code)
            print(f"  ⚾ {team_name} (ID: {team_id}) 수집 시작...")

            try:
                select_element = driver.find_element(By.ID, "cphContents_cphContents_cphContents_ddlTeam")
                select = Select(select_element)
                select.select_by_value(team_code)
                time.sleep(2)

                page = 1
                while True:
                    rows = driver.find_elements(By.CSS_SELECTOR, ".tEx tbody tr")
                    if len(rows) == 0: break
                    
                    page_count = 0
                    for i, row in enumerate(rows):
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) < 7: continue

                        try:
                            # 선수명 & ID
                            name_link = cols[1].find_element(By.TAG_NAME, "a")
                            player_name = name_link.text.strip()
                            href = name_link.get_attribute("href")
                            
                            if "playerId=" in href:
                                kbo_id = int(href.split("playerId=")[1].split("&")[0])
                            else: continue

                            # 상세 정보
                            jersey_num_str = cols[0].text.strip()
                            jersey_number = int(jersey_num_str) if jersey_num_str.isdigit() else None
                            position = cols[3].text.strip()
                            birth_raw = cols[4].text.strip()
                            birth_date = birth_raw.replace('.', '-') if birth_raw else None
                            
                            hw_raw = cols[5].text.strip()
                            height, weight = None, None
                            numbers = re.findall(r'\d+', hw_raw)
                            if len(numbers) >= 2:
                                height = int(numbers[0])
                                weight = int(numbers[1])
                            
                            school_info = cols[6].text.strip() or None
                            # 2025 이미지는 아직 없을 수 있으니 2024로 시도
                            photo_url = f"https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/2024/{kbo_id}.jpg"

                            biometrics = {
                                "position": position,
                                "school": school_info,
                                "team": team_name
                            }

                            # sl_players 저장
                            cur.execute("""
                                INSERT INTO sl_players 
                                (id, name, birth_date, height_cm, weight_kg, nationality, photo_url, biometrics, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, 'South Korea', %s, %s, NOW(), NOW())
                                ON CONFLICT (id) DO UPDATE 
                                SET name = EXCLUDED.name,
                                    photo_url = EXCLUDED.photo_url,
                                    biometrics = COALESCE(sl_players.biometrics, '{}'::jsonb) || EXCLUDED.biometrics,
                                    updated_at = NOW();
                            """, (kbo_id, player_name, birth_date, height, weight, photo_url, json.dumps(biometrics)))

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
                            """, (kbo_id, team_id, season_id, position, jersey_number))
                            
                            page_count += 1
                            total_count += 1

                        except Exception: continue
                    
                    conn.commit()
                    print(f"    - {page}페이지: {page_count}명 완료")
                    
                    try:
                        next_page = page + 1
                        paging_area = driver.find_element(By.CLASS_NAME, "paging")
                        next_btn = paging_area.find_element(By.LINK_TEXT, str(next_page))
                        driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(2)
                        page += 1
                    except: break

                print(f"    ✅ {team_name} 완료")
                driver.get(url) 
                time.sleep(1)

            except Exception as e:
                print(f"    ❌ {team_name} 오류: {e}")
                driver.get(url)
                time.sleep(1)

    finally:
        driver.quit()
        cur.close()
        conn.close()
        print(f"🎉 총 {total_count}명의 KBO 선수/스쿼드 데이터 동기화 완료.")

if __name__ == "__main__":
    sync_kbo_players_selenium()