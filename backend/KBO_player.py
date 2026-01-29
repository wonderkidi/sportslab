import os
import psycopg2
import time
import re
import json
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

def sync_kbo_players_selenium():
    print("👤 KBO 선수 정보 수집 (디버깅 모드)...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

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
            print(f"  ⚾ {team_name} 수집 시작...")

            try:
                select_element = driver.find_element(By.ID, "cphContents_cphContents_cphContents_ddlTeam")
                select = Select(select_element)
                select.select_by_value(team_code)
                time.sleep(2) # 로딩 시간 넉넉히

                page = 1
                while True:
                    rows = driver.find_elements(By.CSS_SELECTOR, ".tEx tbody tr")
                    
                    # [디버깅] 행 개수 확인
                    if len(rows) == 0:
                        print(f"    ⚠️ {page}페이지: 행(tr)을 찾을 수 없습니다.")
                        break
                    
                    page_count = 0
                    
                    for i, row in enumerate(rows):
                        cols = row.find_elements(By.TAG_NAME, "td")
                        
                        # [디버깅] 컬럼 개수 확인 (헤더나 빈 행인지 체크)
                        if len(cols) < 7:
                            # print(f"    ⚠️ 행 {i}: 컬럼 부족 ({len(cols)}개) - 스킵")
                            continue

                        try:
                            # [1] 선수명 & ID
                            # 여기서 에러가 나는지 확인
                            try:
                                name_link = cols[1].find_element(By.TAG_NAME, "a")
                                player_name = name_link.text.strip()
                                href = name_link.get_attribute("href")
                            except NoSuchElementException:
                                print(f"    ❌ 행 {i}: 이름 링크(a 태그) 없음. 텍스트: {cols[1].text}")
                                continue

                            if "playerId=" in href:
                                kbo_id = int(href.split("playerId=")[1].split("&")[0])
                            else:
                                print(f"    ❌ 행 {i}: ID 파싱 실패 ({href})")
                                continue

                            # [3] 포지션
                            position = cols[3].text.strip()

                            # [4] 생년월일
                            birth_raw = cols[4].text.strip()
                            birth_date = birth_raw.replace('.', '-') if birth_raw else None
                            
                            # [5] 체격
                            hw_raw = cols[5].text.strip()
                            height, weight = None, None
                            numbers = re.findall(r'\d+', hw_raw)
                            if len(numbers) >= 2:
                                height = int(numbers[0])
                                weight = int(numbers[1])
                            
                            # [6] 출신교
                            school_info = cols[6].text.strip() or None
                            
                            photo_url = f"https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/2025/{kbo_id}.jpg"

                            biometrics = {
                                "position": position,
                                "school": school_info
                            }

                            sql = """
                                INSERT INTO sl_players 
                                (id, name, birth_date, height_cm, weight_kg, nationality, photo_url, biometrics, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, 'South Korea', %s, %s, NOW(), NOW())
                                ON CONFLICT (id) DO UPDATE 
                                SET name = EXCLUDED.name,
                                    birth_date = EXCLUDED.birth_date,
                                    height_cm = EXCLUDED.height_cm,
                                    weight_kg = EXCLUDED.weight_kg,
                                    photo_url = EXCLUDED.photo_url,
                                    biometrics = COALESCE(sl_players.biometrics, '{}'::jsonb) || EXCLUDED.biometrics,
                                    updated_at = NOW();
                            """
                            cur.execute(sql, (kbo_id, player_name, birth_date, height, weight, photo_url, json.dumps(biometrics)))
                            
                            page_count += 1
                            total_count += 1

                        except Exception as e:
                            # [디버깅] 상세 에러 출력
                            conn.rollback()
                            print(f"    ❌ 저장 실패 (행 {i}): {e}")
                            continue
                    
                    conn.commit()
                    print(f"    - {page}페이지: {page_count}명 저장 완료")
                    
                    # 다음 페이지
                    try:
                        next_page = page + 1
                        paging_area = driver.find_element(By.CLASS_NAME, "paging")
                        next_btn = paging_area.find_element(By.LINK_TEXT, str(next_page))
                        driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(2)
                        page += 1
                    except NoSuchElementException:
                        break 
                    except Exception as e:
                        print(f"    ⚠️ 페이지 이동 에러: {e}")
                        break

                print(f"    ✅ {team_name} 완료")
                driver.get(url) 
                time.sleep(1)

            except Exception as e:
                print(f"    ❌ {team_name} 팀 처리 실패: {e}")
                driver.get(url)
                time.sleep(1)

    except Exception as e:
        print(f"❌ 프로세스 에러: {e}")
    
    finally:
        driver.quit()
        cur.close()
        conn.close()
        print(f"🎉 총 {total_count}명 완료.")

if __name__ == "__main__":
    sync_kbo_players_selenium()