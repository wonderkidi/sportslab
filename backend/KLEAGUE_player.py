import os
import psycopg2
import json
import time
import re
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
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

# 포지션별 URL (감독/코치 제외)
POSITIONS = {
    'GK': 'gk',
    'DF': 'df',
    'MF': 'mf',
    'FW': 'fw'
}

def get_team_id_by_name(cur, team_name):
    if not team_name: return None
    name_map = {
        '전북': '전북 현대', '울산': '울산 HD', '포항': '포항 스틸러스', '제주': '제주 유나이티드',
        '서울': 'FC 서울', '강원': '강원 FC', '광주': '광주 FC', '인천': '인천 유나이티드',
        '수원': '수원 삼성', '수원FC': '수원 FC', '대구': '대구 FC', '대전': '대전 하나 시티즌',
        '김천': '김천 상무', '성남': '성남 FC', '부산': '부산 아이파크', '전남': '전남 드래곤즈',
        '경남': '경남 FC', '안양': 'FC 안양', '부천': '부천 FC 1995', '충남아산': '충남 아산',
        '김포': '김포 FC', '안산': '안산 그리너스', '서울E': '서울 이랜드', '천안': '천안 시티 FC',
        '충북청주': '충북 청주 FC'
    }
    search_name = name_map.get(team_name, team_name)
    cur.execute("SELECT id FROM sl_teams WHERE name LIKE %s LIMIT 1", (f"%{search_name}%",))
    row = cur.fetchone()
    return row[0] if row else None

def parse_number(text):
    if not text: return 0
    text = str(text).strip()
    if text == '-' or text == '': return 0
    return int(re.sub(r'[^\d]', '', text))

def scrape_kleague_players():
    print("⚽ K-League 포지션별 선수 전체 수집 시작...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # [수정] 0. 리그 기초 데이터 생성 (FK 에러 방지)
    try:
        print("  🔧 리그 기초 데이터 확인 중...")
        # 1. 종목 (Soccer)
        cur.execute("INSERT INTO sl_sports (name, slug) VALUES ('Soccer', 'soccer') ON CONFLICT (name) DO NOTHING")
        cur.execute("SELECT id FROM sl_sports WHERE name='Soccer'")
        sport_row = cur.fetchone()
        sport_id = sport_row[0] if sport_row else 1 

        # 2. 리그 (K League 1 - ID 300)
        # ID 300번이 없으면 생성
        cur.execute("""
            INSERT INTO sl_leagues (id, sport_id, name, slug, country, type)
            VALUES (300, %s, 'K League 1', 'k-league', 'South Korea', 'League')
            ON CONFLICT (id) DO NOTHING
        """, (sport_id,))
        
        conn.commit() # 기초 데이터 커밋
        print("  ✅ 리그 기초 데이터(ID: 300) 준비 완료")
        
    except Exception as e:
        print(f"  ⚠️ 초기 설정 중 경고: {e}")
        conn.rollback()

    # Selenium 설정
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    total_saved = 0

    try:
        # 1. 포지션별 순회
        for pos_name, pos_code in POSITIONS.items():
            print(f"\n📂 포지션: {pos_name} 수집 시작...")
            page = 1
            
            while True:
                # 목록 URL 접속
                list_url = f"https://www.kleague.com/player.do?page={page}&type=all&leagueId=&teamId=&pos={pos_code}"
                driver.get(list_url)
                time.sleep(1)

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                player_boxes = soup.select(".cont-box.f-wrap.left.player-hover")
                
                if not player_boxes:
                    print(f"  ✅ {pos_name} 수집 완료 (총 {page-1}페이지)")
                    break
                
                print(f"  📄 {page}페이지: {len(player_boxes)}명 발견.")
                
                player_ids = []
                for box in player_boxes:
                    try:
                        onclick = box.get('onclick') 
                        pid = re.search(r"onPlayerClicked\((\d+)\)", onclick).group(1)
                        player_ids.append(pid)
                    except:
                        continue

                # 2. 상세 페이지 순회
                for pid in player_ids:
                    try:
                        detail_url = f"https://www.kleague.com/record/playerDetail.do?playerId={pid}"
                        driver.get(detail_url)
                        
                        detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
                        
                        # --- A. 기본 정보 파싱 ---
                        info_table = detail_soup.select_one(".cont-box.right table.style2 tbody")
                        info_map = {}
                        if info_table:
                            for tr in info_table.find_all("tr"):
                                ths = tr.find_all("th")
                                tds = tr.find_all("td")
                                for i, th in enumerate(ths):
                                    key = th.text.strip()
                                    val = tds[i].text.strip() if i < len(tds) else ""
                                    info_map[key] = val
                        
                        name = info_map.get("이름", "")
                        en_name_full = info_map.get("영문명", "")
                        team_name = info_map.get("소속구단", "")
                        position = info_map.get("포지션", pos_name) 
                        back_no = parse_number(info_map.get("배번", ""))
                        nation = info_map.get("국적", "South Korea")
                        height = parse_number(info_map.get("키", ""))
                        weight = parse_number(info_map.get("몸무게", ""))
                        
                        birth_str = info_map.get("생년월일", "")
                        birth_date = birth_str.replace('/', '-') if birth_str else None
                        
                        photo_img = detail_soup.select_one(".img-box img")
                        photo_url = photo_img['src'] if photo_img else None
                        
                        # biometrics JSON 구성
                        biometrics = {
                            "position": position,
                            "back_no": back_no,
                            "en_name": en_name_full,
                            "team_name_raw": team_name
                        }

                        # 선수 DB 저장 (lastname에 영문명 저장)
                        cur.execute("""
                            INSERT INTO sl_players 
                            (id, name, lastname, photo_url, birth_date, height_cm, weight_kg, nationality, biometrics, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                            ON CONFLICT (id) DO UPDATE 
                            SET name = EXCLUDED.name,
                                lastname = EXCLUDED.lastname,
                                photo_url = EXCLUDED.photo_url,
                                birth_date = EXCLUDED.birth_date,
                                height_cm = EXCLUDED.height_cm,
                                weight_kg = EXCLUDED.weight_kg,
                                nationality = EXCLUDED.nationality,
                                biometrics = sl_players.biometrics || EXCLUDED.biometrics,
                                updated_at = NOW();
                        """, (pid, name, en_name_full, photo_url, birth_date, height, weight, nation, json.dumps(biometrics)))

                        # --- B. 시즌별 기록 파싱 ---
                        season_section = None
                        titles = detail_soup.select("h3.tit-box.style2")
                        for title in titles:
                            if "시즌별" in title.text:
                                season_section = title.find_next("div", class_="table-wrap")
                                break
                        
                        if season_section:
                            season_rows = season_section.select("table tbody tr")
                            for s_row in season_rows:
                                cols = s_row.find_all("td")
                                if len(cols) < 17: continue
                                
                                year_txt = cols[0].text.strip()
                                if not year_txt.isdigit(): continue
                                year = int(year_txt)
                                s_team_name = cols[1].text.strip()
                                
                                stats = {
                                    "K1": {"apps": parse_number(cols[2].text), "goals": parse_number(cols[3].text), "assists": parse_number(cols[4].text)},
                                    "K2": {"apps": parse_number(cols[5].text), "goals": parse_number(cols[6].text), "assists": parse_number(cols[7].text)},
                                    "Total": {"apps": parse_number(cols[14].text), "goals": parse_number(cols[15].text), "assists": parse_number(cols[16].text)}
                                }
                                
                                # 시즌 ID 조회 (300번 리그에 대해)
                                cur.execute("SELECT id FROM sl_seasons WHERE league_id = 300 AND year = %s", (year,))
                                sid_row = cur.fetchone()
                                if not sid_row:
                                    # 시즌 생성
                                    cur.execute("INSERT INTO sl_seasons (league_id, year) VALUES (300, %s) RETURNING id", (year,))
                                    season_id = cur.fetchone()[0]
                                else:
                                    season_id = sid_row[0]
                                    
                                team_id = get_team_id_by_name(cur, s_team_name)
                                if team_id:
                                    cur.execute("""
                                        INSERT INTO sl_player_season_stats
                                        (player_id, season_id, team_id, stats, updated_at)
                                        VALUES (%s, %s, %s, %s, NOW())
                                        ON CONFLICT (player_id, season_id, team_id)
                                        DO UPDATE SET stats = EXCLUDED.stats, updated_at = NOW();
                                    """, (pid, season_id, team_id, json.dumps(stats)))

                        # 현재 스쿼드 정보
                        curr_team_id = get_team_id_by_name(cur, team_name)
                        if curr_team_id:
                            # 2024 시즌 기준
                            cur.execute("SELECT id FROM sl_seasons WHERE league_id = 300 AND year = 2024")
                            sid_row = cur.fetchone()
                            if not sid_row:
                                cur.execute("INSERT INTO sl_seasons (league_id, year, is_current) VALUES (300, 2024, true) RETURNING id")
                                curr_sid = cur.fetchone()
                            else:
                                curr_sid = sid_row
                                
                            if curr_sid:
                                cur.execute("""
                                    INSERT INTO sl_player_squads 
                                    (player_id, team_id, season_id, position, jersey_number, is_active)
                                    VALUES (%s, %s, %s, %s, %s, true)
                                    ON CONFLICT (player_id, team_id, season_id) 
                                    DO UPDATE SET position = EXCLUDED.position, jersey_number = EXCLUDED.jersey_number, is_active = true;
                                """, (pid, curr_team_id, curr_sid[0], position, back_no))
                        
                        total_saved += 1
                        
                    except Exception as e:
                        conn.rollback()
                        print(f"    ⚠️ ID {pid} 처리 실패: {e}")
                        continue

                conn.commit()
                page += 1

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        driver.quit()
        cur.close()
        conn.close()
        print(f"🎉 총 {total_saved}명 선수 정보 수집 완료.")

if __name__ == "__main__":
    scrape_kleague_players()