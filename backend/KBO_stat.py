import os
import psycopg2
import json
import time
import re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
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

# KBO 팀 코드 매핑 (기록실 드롭다운 기준)
# 두산, 롯데, 삼성, 키움, 한화, KIA, KT, LG, NC, SSG
KBO_TEAMS = ['OB', 'LT', 'SS', 'WO', 'HH', 'HT', 'KT', 'LG', 'NC', 'SK']

def sync_kbo_stats_selenium(year=2024):
    print(f"📊 {year}년 KBO 타자 스탯 크롤링 시작 (Selenium)...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 1. 시즌 ID 조회
    cur.execute("""
        SELECT s.id FROM sl_seasons s
        JOIN sl_leagues l ON s.league_id = l.id
        WHERE l.slug = 'kbo' AND s.year = %s
    """, (year,))
    row = cur.fetchone()
    if not row:
        print("⚠️ 시즌 정보가 없습니다. KBO_game.py를 먼저 실행해주세요.")
        return
    season_id = row[0]

    # 브라우저 설정
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 안티봇 우회 헤더
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    total_count = 0

    try:
        # KBO 기록실 - 타자 순위 페이지
        url = "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx"
        driver.get(url)
        time.sleep(2)

        # 2. 연도 선택
        try:
            select_year = Select(driver.find_element(By.ID, "cphContents_cphContents_cphContents_ddlSeason_ddlSeason"))
            select_year.select_by_value(str(year))
            time.sleep(1.5)
        except Exception as e:
            print(f"❌ 연도 선택 실패: {e}")
            return

        # 3. 팀별 루프 (팀을 선택해야 해당 팀 전체 선수가 나옴)
        for team_code in KBO_TEAMS:
            try:
                # 팀 선택
                select_team = Select(driver.find_element(By.ID, "cphContents_cphContents_cphContents_ddlTeam_ddlTeam"))
                select_team.select_by_value(team_code)
                time.sleep(1.5) # 로딩 대기

                # 테이블 데이터 파싱
                # KBO 기록실 테이블 클래스: tData01
                rows = driver.find_elements(By.CSS_SELECTOR, ".tData01 tbody tr")
                
                print(f"  ⚾ {team_code} 데이터 수집 중... ({len(rows)}명)")

                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 10: continue

                    try:
                        # 데이터 추출
                        # [0] 순위 [1] 선수명 [2] 팀 [3] 타율 [4] 경기수 [5] 타석 [6] 타수 [7] 득점 [8] 안타 [9] 2루타 ...
                        
                        # 선수명 & ID 추출
                        # <a href="/Record/Player/HitterDetail/Basic.aspx?playerId=67001">XX</a>
                        name_link = cols[1].find_element(By.TAG_NAME, "a")
                        player_name = name_link.text.strip()
                        href = name_link.get_attribute("href")
                        
                        if "playerId=" in href:
                            player_id = int(href.split("playerId=")[1].split("&")[0])
                        else:
                            continue # ID 없으면 저장 불가

                        # 팀 ID 조회 (DB에 있는 팀 정보와 연결)
                        cur.execute("SELECT id FROM sl_teams WHERE name LIKE %s", (f"%{cols[2].text.strip()}%",))
                        t_row = cur.fetchone()
                        team_id = t_row[0] if t_row else None

                        # 스탯 딕셔너리 생성
                        stats = {
                            "AVG": cols[3].text.strip(),
                            "G": cols[4].text.strip(),
                            "PA": cols[5].text.strip(),
                            "AB": cols[6].text.strip(),
                            "R": cols[7].text.strip(),
                            "H": cols[8].text.strip(),
                            "2B": cols[9].text.strip(),
                            "3B": cols[10].text.strip(),
                            "HR": cols[11].text.strip(),
                            "RBI": cols[12].text.strip(),
                            "SB": cols[13].text.strip(),
                            "CS": cols[14].text.strip(),
                            "BB": cols[15].text.strip(),
                            "HBP": cols[16].text.strip(),
                            "SO": cols[17].text.strip(),
                            "GDP": cols[18].text.strip(),
                            "SLG": cols[19].text.strip(),
                            "OBP": cols[20].text.strip(),
                            # OPS는 보통 이 페이지에 없으므로 계산하거나 생략 (다음 페이지에 있을수 있음)
                        }

                        # DB 저장 (Upsert)
                        # sl_player_season_stats (player_id, season_id, team_id)
                        if team_id:
                            sql = """
                                INSERT INTO sl_player_season_stats 
                                (player_id, season_id, team_id, stats, updated_at)
                                VALUES (%s, %s, %s, %s, NOW())
                                ON CONFLICT (player_id, season_id, team_id) 
                                DO UPDATE SET stats = EXCLUDED.stats, updated_at = NOW();
                            """
                            cur.execute(sql, (player_id, season_id, team_id, json.dumps(stats)))
                            total_count += 1
                        
                    except Exception as e:
                        # print(f"    ⚠️ 파싱 에러: {e}")
                        continue
                
                conn.commit()
                # print(f"    ✅ {team_code} 저장 완료")

            except Exception as e:
                print(f"    ❌ {team_code} 처리 중 에러: {e}")
                # 에러 발생 시 페이지 리셋
                driver.get(url)
                time.sleep(2)
                # 연도 재선택 필요할 수 있음

    except Exception as e:
        print(f"❌ 크롤링 치명적 오류: {e}")

    finally:
        driver.quit()
        cur.close()
        conn.close()
        print(f"🎉 총 {total_count}건의 타자 스탯 저장 완료.")

if __name__ == "__main__":
    sync_kbo_stats_selenium(2024)