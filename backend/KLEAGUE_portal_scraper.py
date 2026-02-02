import os
import psycopg2
import json
import time
import re
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

class KLeaguePlayerClickFixScraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless') 
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()

    def __del__(self):
        if hasattr(self, 'driver'): self.driver.quit()
        if hasattr(self, 'cur'): self.cur.close()
        if hasattr(self, 'conn'): self.conn.close()

    def parse_number(self, text):
        if not text: return 0
        text = str(text).strip()
        if text == '-' or text == '': return 0
        return int(re.sub(r'[^\d]', '', text))

    def get_team_id_by_name(self, team_name):
        if not team_name: return None
        search_name = team_name.replace("FC", "").strip()
        self.cur.execute("SELECT id FROM sl_teams WHERE name LIKE %s LIMIT 1", (f"%{search_name}%",))
        row = self.cur.fetchone()
        return row[0] if row else None

    # -------------------------------------------------------------------------
    # 메뉴 스크립트 실행 (이전 로직 유지)
    # -------------------------------------------------------------------------
    def execute_menu_script(self, script_code, description):
        print(f"  ⌨️ 명령어 실행: {description} ...", end="")
        self.driver.switch_to.default_content()
        try:
            self.driver.execute_script(script_code)
            print(" 성공 (Main) ✅")
            time.sleep(2)
            return True
        except:
            pass

        frames = self.driver.find_elements(By.TAG_NAME, "frame")
        for i, frame in enumerate(frames):
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                self.driver.execute_script(script_code)
                print(f" 성공 (Frame {i}) ✅")
                time.sleep(2)
                return True
            except:
                continue
        print(" ❌ 실패")
        return False

    def navigate_to_player_list(self):
        print("🌐 [1단계] 사이트 접속...")
        self.driver.get("https://data.kleague.com/")
        time.sleep(3)

        if not self.execute_menu_script("moveMainFrame('0011')", "데이터센터 이동"): return False
        if not self.execute_menu_script("moveMainFrame('0410')", "선수 메뉴 이동"): return False

        print("  🔀 선수 목록(mainFrame) 로딩 대기...")
        try:
            self.driver.switch_to.default_content()
            WebDriverWait(self.driver, 20).until(EC.frame_to_be_available_and_switch_to_it("mainFrame"))
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "club-playerlist-box")))
            print("  ✅ 선수 목록 진입 완료!")
            return True
        except Exception as e:
            print(f"  ❌ 목록 로딩 실패: {e}")
            return False

    # -------------------------------------------------------------------------
    # 2. 수집 루프 (⚡수정된 부분: JS 코드 추출 후 직접 실행)
    # -------------------------------------------------------------------------
    def start_scraping_loop(self):
        print("🔄 [2단계] 수집 시작")
        current_index = 0
        
        while True:
            try:
                # 1. 요소 리스트 로딩 (StaleElement 방지 위해 매번 새로 찾음)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "club-playerlist-box"))
                )
                all_boxes = self.driver.find_elements(By.CLASS_NAME, "club-playerlist-box")
                
                # 2. 화면에 보이는 요소만 필터링
                visible_boxes = [box for box in all_boxes if box.is_displayed()]
                
                total_count = len(visible_boxes)
                if total_count == 0:
                    print("  ⚠️ 표시된 선수 없음 (로딩 중이거나 데이터 없음)")
                    time.sleep(2)
                    continue
                    
                if current_index >= total_count:
                    print(f"  ⏹️ 수집 종료 (총 {total_count}명)")
                    break

                # 3. 타겟 설정
                target_box = visible_boxes[current_index]
                
                # 4. [핵심 수정] onclick 속성값(JS 코드)을 문자열로 가져옴
                # 예: "javascript:moveMainFrameMcPlayer('0416','20230068','K21');"
                onclick_js = target_box.get_attribute("onclick")
                
                # 5. ID 추출 (로그용)
                match = re.search(r"moveMainFrameMcPlayer\('.+','(\d+)','(.+)'\)", onclick_js)
                p_id = match.group(1) if match else "Unknown"
                
                print(f"  👉 [{current_index+1}/{total_count}] 선수 이동 시도 (ID: {p_id})")
                
                # 6. [핵심 수정] 'javascript:' 접두어 제거 후 브라우저에서 직접 실행
                if onclick_js:
                    clean_js = onclick_js.replace("javascript:", "").strip()
                    self.driver.execute_script(clean_js)
                else:
                    print("    ❌ onclick 속성이 없습니다. 건너뜁니다.")
                    current_index += 1
                    continue
                
                # 7. 상세 페이지 파싱
                if self.parse_detail_page(p_id):
                    self.reset_to_list()
                    current_index += 1
                else:
                    self.reset_to_list()
                    current_index += 1
            
            except Exception as e:
                print(f"  ❌ 루프 에러: {e}")
                self.reset_to_list()
                current_index += 1

    # -------------------------------------------------------------------------
    # 3. 상세 파싱 (이전 로직 유지)
    # -------------------------------------------------------------------------
    def parse_detail_page(self, player_id):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "sub-team-table"))
            )
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            info_map = {}
            info_table = soup.select_one(".sub-team-table table.table tbody")
            if info_table:
                for tr in info_table.find_all("tr"):
                    tds = tr.find_all("td")
                    current_key = None
                    for td in tds:
                        if "bar_bottm_right_01" in td.get("class", []):
                            current_key = td.get_text(strip=True)
                        elif current_key:
                            info_map[current_key] = td.get_text(strip=True)
                            current_key = None
            
            name = info_map.get("이름", "").split("(")[0].strip()
            en_name = info_map.get("영문명", "")
            position = info_map.get("포지션", "")
            back_no = self.parse_number(info_map.get("배번", "0"))
            nation = info_map.get("국적", "South Korea")
            height = self.parse_number(info_map.get("키", "0"))
            weight = self.parse_number(info_map.get("몸무게", "0"))
            birth_date = info_map.get("생년월일", "").replace("/", "-")
            photo_url = f"http://portal.kleague.com//common/playerPhotoById.do?playerId={player_id}&recYn=Y&searchYear=2025"

            season_stats = []
            titles = soup.find_all("h3")
            target_table = None
            for title in titles:
                if "시즌별" in title.get_text():
                    target_table = title.find_next("table", class_="table")
                    break
            
            if target_table:
                rows = target_table.select("tbody tr")
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) < 12: continue
                    year_text = cols[0].get_text(strip=True)
                    if not year_text.isdigit(): continue
                    
                    year = int(year_text)
                    curr_team = cols[1].get_text(strip=True)
                    
                    try:
                        k1_stats = [self.parse_number(cols[2].text), self.parse_number(cols[3].text), self.parse_number(cols[4].text)]
                        k2_stats = [self.parse_number(cols[5].text), self.parse_number(cols[6].text), self.parse_number(cols[7].text)]
                        total_stats = [self.parse_number(cols[-3].text), self.parse_number(cols[-2].text), self.parse_number(cols[-1].text)]
                        
                        stat_data = {"K1": k1_stats, "K2": k2_stats, "Total": total_stats}
                        keys = ["apps", "conceded", "clean_sheet"] if position == "GK" else ["apps", "goals", "assists"]
                        
                        formatted = {k: dict(zip(keys, v)) for k, v in stat_data.items()}
                        season_stats.append({"year": year, "team": curr_team, "data": formatted})
                    except:
                        continue

            self.save_to_db(player_id, name, en_name, photo_url, birth_date, height, weight, nation, position, back_no, season_stats)
            return True

        except Exception as e:
            print(f"    ⚠️ 파싱 에러: {e}")
            return False

    def save_to_db(self, pid, name, en_name, photo_url, birth_date, height, weight, nation, position, back_no, stats_list):
        try:
            biometrics = {"position": position, "back_no": back_no, "en_name": en_name}
            sql_player = """
                INSERT INTO sl_players (id, name, lastname, photo_url, birth_date, height_cm, weight_kg, nationality, biometrics, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE 
                SET name = EXCLUDED.name, lastname = EXCLUDED.lastname, photo_url = EXCLUDED.photo_url,
                    birth_date = EXCLUDED.birth_date, height_cm = EXCLUDED.height_cm, weight_kg = EXCLUDED.weight_kg,
                    biometrics = sl_players.biometrics || EXCLUDED.biometrics, updated_at = NOW();
            """
            self.cur.execute(sql_player, (pid, name, en_name, photo_url, birth_date, height, weight, nation, json.dumps(biometrics)))

            for stat in stats_list:
                team_id = self.get_team_id_by_name(stat['team'])
                if not team_id: continue
                
                self.cur.execute("SELECT id FROM sl_seasons WHERE league_id=300 AND year=%s", (stat['year'],))
                sid_row = self.cur.fetchone()
                season_id = sid_row[0] if sid_row else self.cur.execute("INSERT INTO sl_seasons (league_id, year) VALUES (300, %s) RETURNING id", (stat['year'],)) or self.cur.fetchone()[0]

                sql_stat = """
                    INSERT INTO sl_player_season_stats (player_id, season_id, team_id, stats, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (player_id, season_id, team_id) DO UPDATE SET stats = EXCLUDED.stats, updated_at = NOW();
                """
                self.cur.execute(sql_stat, (pid, season_id, team_id, json.dumps(stat['data'])))
            self.conn.commit()
            print(f"    💾 저장 완료: {name}")
        except Exception as e:
            self.conn.rollback()
            print(f"    ⚠️ DB 저장 에러: {e}")

    def reset_to_list(self):
        # '선수' 메뉴 누르는 명령어를 직접 실행하여 목록으로 복귀
        if not self.execute_menu_script("moveMainFrame('0410')", "목록 복귀"):
            print("  ❌ 목록 복귀 실패")
        
        try:
            self.driver.switch_to.default_content()
            WebDriverWait(self.driver, 10).until(EC.frame_to_be_available_and_switch_to_it("mainFrame"))
            WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "club-playerlist-box")))
        except:
            pass

    def run(self):
        if self.navigate_to_player_list():
            self.start_scraping_loop()

if __name__ == "__main__":
    scraper = KLeaguePlayerClickFixScraper()
    scraper.run()