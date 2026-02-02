import os
import time
import re
import json
import psycopg2
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

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

class KBLFullScraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        # [중요] 화면을 띄워야 차단되지 않음 (Headless 주석 처리)
        # options.add_argument('--headless=new')
        
        options.add_argument('--start-maximized') 
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-blink-features=AutomationControlled') 
        options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # 봇 탐지 회피용 JS
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()

    def __del__(self):
        if hasattr(self, 'driver'): self.driver.quit()
        if hasattr(self, 'cur'): self.cur.close()
        if hasattr(self, 'conn'): self.conn.close()

    # =========================================================================
    # 1. 팀 소개 수집
    # URL: https://www.kbl.or.kr/team/intro
    # =========================================================================
    def scrape_teams(self):
        print("\n🏀 [1단계] 팀 정보 수집 시작...")
        self.driver.get("https://www.kbl.or.kr/team/intro")
        time.sleep(3) # 로딩 대기
        
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "team_list"))
            )
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            team_list = soup.select(".team_list li")
            
            print(f"  👉 총 {len(team_list)}개 구단 발견")
            
            for team in team_list:
                name = team.select_one(".name").get_text(strip=True)
                # 링크에서 구단 코드/ID 추출
                link = team.select_one("a")['href'] # 예: /team/intro/10
                team_kbl_id = link.split("/")[-1]
                
                # DB 저장 (sl_teams 테이블이 있다고 가정)
                self.save_team(team_kbl_id, name)
                
        except Exception as e:
            print(f"  ❌ 팀 수집 실패: {e}")

    def save_team(self, kbl_id, name):
        try:
            # Upsert (이미 있으면 이름만 업데이트)
            sql = """
                INSERT INTO sl_teams (name, created_at, updated_at)
                VALUES (%s, NOW(), NOW())
                ON CONFLICT (name) DO UPDATE SET updated_at = NOW()
                RETURNING id;
            """
            # 참고: 실제로는 KBL ID를 매핑하는 로직이 필요할 수 있음
            self.cur.execute(sql, (name,))
            self.conn.commit()
            print(f"    💾 저장: {name} (KBL_ID: {kbl_id})")
        except Exception:
            self.conn.rollback()

    # =========================================================================
    # 2. 선수 목록 수집 (페이징 포함)
    # URL: https://www.kbl.or.kr/player/player
    # =========================================================================
    def scrape_players(self):
        print("\n🏀 [2단계] 선수 목록 수집 시작...")
        self.driver.get("https://www.kbl.or.kr/player/player")
        time.sleep(4)
        
        try:
            # 테이블 로딩 확인
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "player_list")))
            
            # 전체 페이지 수 파악 (데스크탑 뷰 기준)
            paging_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.page.desktop select"))
            )
            total_pages = len(paging_box.find_elements(By.TAG_NAME, "option"))
            print(f"  👉 총 {total_pages} 페이지 감지됨")

            for page_num in range(1, total_pages + 1):
                print(f"  🔄 {page_num}/{total_pages} 페이지 처리 중...")
                
                try:
                    # 페이지 이동 로직
                    select_elem = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.page.desktop select"))
                    )
                    select = Select(select_elem)
                    
                    if select.first_selected_option.get_attribute("value") != str(page_num):
                        select.select_by_value(str(page_num))
                        time.sleep(2) # 데이터 로딩 대기
                        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "player_list")))
                    
                    # 파싱
                    self.parse_and_save_players()
                    
                except Exception as e:
                    print(f"    ⚠️ {page_num}페이지 에러: {e}")
                    self.driver.refresh()
                    time.sleep(3)
                    continue

        except Exception as e:
            print(f"  ❌ 선수 수집 초기화 실패: {e}")

    def parse_and_save_players(self):
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        rows = soup.select(".player_list tbody tr")
        
        count = 0
        for row in rows:
            try:
                cols = row.find_all("td")
                if len(cols) < 5: continue
                
                # 데이터 추출
                name_tag = cols[1].select_one(".player_name a")
                if not name_tag: continue
                
                name = name_tag.get_text(strip=True)
                player_id = name_tag['href'].split("/")[-1]
                
                position = cols[2].get_text(strip=True)
                height = int(re.sub(r'[^\d]', '', cols[3].get_text(strip=True) or "0"))
                team_name = cols[4].get_text(strip=True)
                
                # DB 저장
                self.save_player(player_id, name, team_name, position, height)
                count += 1
            except: continue
        print(f"    ✅ {count}명 저장 완료")

    def save_player(self, pid, name, team_name, position, height):
        try:
            # 팀 ID 조회
            self.cur.execute("SELECT id FROM sl_teams WHERE name LIKE %s LIMIT 1", (f"%{team_name}%",))
            res = self.cur.fetchone()
            # 팀이 DB에 없으면 건너뛰거나 생성 (여기선 건너뜀)
            if not res: return 
            
            biometrics = {"height_cm": height, "position": position, "kbl_id": pid}
            
            sql = """
                INSERT INTO sl_players (id, name, biometrics, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE 
                SET name = EXCLUDED.name, biometrics = sl_players.biometrics || EXCLUDED.biometrics, updated_at = NOW();
            """
            self.cur.execute(sql, (pid, name, json.dumps(biometrics)))
            self.conn.commit()
        except Exception:
            self.conn.rollback()

    # =========================================================================
    # 3. 경기 결과/일정 수집
    # URL: https://www.kbl.or.kr/match/schedule?type=SCHEDULE
    # =========================================================================
    def scrape_schedule(self):
        print("\n🏀 [3단계] 경기 일정 수집 시작...")
        self.driver.get("https://www.kbl.or.kr/match/schedule?type=SCHEDULE")
        time.sleep(5)
        
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "schedule_list"))
            )
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            days = soup.select(".schedule_list .day_list")
            print(f"  👉 캘린더 로딩 완료 ({len(days)}일치 데이터)")
            
            for day in days:
                date_str = day.select_one(".date").get_text(strip=True) # 예: 10.19 (토)
                matches = day.select("li")
                
                for match in matches:
                    home = match.select_one(".team.home .name").get_text(strip=True)
                    score_home = match.select_one(".team.home .score").get_text(strip=True)
                    
                    away = match.select_one(".team.away .name").get_text(strip=True)
                    score_away = match.select_one(".team.away .score").get_text(strip=True)
                    
                    state = match.select_one(".state").get_text(strip=True) # 종료, 예정
                    
                    print(f"    📅 [{date_str}] {home} {score_home} : {score_away} {away} ({state})")
                    # TODO: sl_matches 테이블에 INSERT 로직 추가
                    # self.save_match(...) 

        except Exception as e:
            print(f"  ❌ 일정 수집 실패: {e}")

    def run(self):
        self.scrape_teams()
        self.scrape_players()
        self.scrape_schedule()

if __name__ == "__main__":
    scraper = KBLFullScraper()
    scraper.run()