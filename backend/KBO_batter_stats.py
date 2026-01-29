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

def get_team_id(cur, team_name):
    if not team_name: return None
    cur.execute("SELECT id FROM sl_teams WHERE name LIKE %s LIMIT 1", (f"%{team_name}%",))
    row = cur.fetchone()
    return row[0] if row else None

def sync_batter_details():
    print("⚾ KBO 타자 상세 기록 수집 시작 (테이블 구조 수정됨)...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name FROM sl_players 
        WHERE biometrics->>'position' IN ('포수', '내야수', '외야수')
    """)
    targets = cur.fetchall()
    print(f"🎯 수집 대상: {len(targets)}명")

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument("user-agent=Mozilla/5.0")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        for p_id, p_name in targets:
            print(f"\n👤 {p_name} (ID: {p_id}) 수집 중...")

            # =========================================================
            # 1. 통산 기록 (Total.aspx)
            # =========================================================
            total_url = f"https://www.koreabaseball.com/Record/Player/HitterDetail/Total.aspx?playerId={p_id}"
            driver.get(total_url)
            time.sleep(1)

            try:
                # [수정] 클래스 이름 대신 'summary="통산기록"' 속성으로 테이블 찾기 (가장 정확)
                # 만약 summary가 없다면 테이블 텍스트로 찾음
                tables = driver.find_elements(By.TAG_NAME, "table")
                career_table = None
                
                for tbl in tables:
                    if "통산기록" in tbl.get_attribute("summary") or ("연도" in tbl.text and "타율" in tbl.text):
                        career_table = tbl
                        break
                
                if not career_table:
                    print(f"  ⚠️ 통산 기록 없음 (신인 등)")
                    continue # 통산 기록 없으면 다음 선수로

                rows = career_table.find_elements(By.CSS_SELECTOR, "tbody tr")
                
                saved_seasons = 0
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    # 헤더: 연도, 팀명, AVG, G, PA, AB, R, H, 2B, 3B, HR, TB, RBI, SB, CS, BB, HBP, SO, GDP, SLG, OBP
                    if len(cols) < 20: continue

                    year_text = cols[0].text.strip()
                    if not year_text.isdigit(): continue
                    
                    year = int(year_text)
                    team_name = cols[1].text.strip()
                    
                    # 시즌 ID
                    cur.execute("SELECT id FROM sl_seasons WHERE league_id=200 AND year=%s", (year,))
                    s_row = cur.fetchone()
                    if not s_row:
                        cur.execute("INSERT INTO sl_seasons (league_id, year, is_current) VALUES (200, %s, false) RETURNING id", (year,))
                        season_id = cur.fetchone()[0]
                    else:
                        season_id = s_row[0]

                    team_id = get_team_id(cur, team_name)
                    
                    try:
                        # 데이터 파싱 (순서 중요)
                        # [2]AVG [3]G [4]PA [5]AB [6]R [7]H [8]2B [9]3B [10]HR [11]TB [12]RBI [13]SB [14]CS [15]BB [16]HBP [17]SO [18]GDP [19]SLG [20]OBP
                        slg = cols[19].text.strip()
                        obp = cols[20].text.strip()
                        
                        stats = {
                            "AVG": cols[2].text.strip(),
                            "G": int(cols[3].text.strip()),
                            "PA": int(cols[4].text.strip()),
                            "AB": int(cols[5].text.strip()),
                            "R": int(cols[6].text.strip()),
                            "H": int(cols[7].text.strip()),
                            "2B": int(cols[8].text.strip()),
                            "3B": int(cols[9].text.strip()),
                            "HR": int(cols[10].text.strip()),
                            "TB": int(cols[11].text.strip()), # 루타
                            "RBI": int(cols[12].text.strip()),
                            "SB": int(cols[13].text.strip()),
                            "CS": int(cols[14].text.strip()),
                            "BB": int(cols[15].text.strip()),
                            "HBP": int(cols[16].text.strip()),
                            "SO": int(cols[17].text.strip()),
                            "GDP": int(cols[18].text.strip()),
                            "SLG": slg,
                            "OBP": obp
                        }
                        
                        # OPS
                        try:
                            ops = float(slg) + float(obp)
                            stats["OPS"] = f"{ops:.3f}"
                        except:
                            stats["OPS"] = "0.000"

                        # DB 저장
                        sql = """
                            INSERT INTO sl_player_season_stats 
                            (player_id, season_id, team_id, stats, updated_at)
                            VALUES (%s, %s, %s, %s, NOW())
                            ON CONFLICT (player_id, season_id, team_id) 
                            DO UPDATE SET stats = sl_player_season_stats.stats || EXCLUDED.stats, updated_at = NOW();
                        """
                        cur.execute(sql, (p_id, season_id, team_id, json.dumps(stats)))
                        saved_seasons += 1
                    
                    except Exception as e:
                        # print(f"    ❌ 파싱 에러 ({year}): {e}")
                        continue

                conn.commit()
                print(f"  ✅ 통산 {saved_seasons}개 시즌 저장 완료")

            except Exception as e:
                print(f"  ❌ 통산 기록 처리 에러: {e}")
                conn.rollback()

            # =========================================================
            # 2. 기본 기록 (Basic1.aspx) - 세부 스탯(희생타 등) 보강
            # =========================================================
            basic_url = f"https://www.koreabaseball.com/Record/Player/HitterDetail/Basic1.aspx?playerId={p_id}"
            driver.get(basic_url)
            time.sleep(1)

            try:
                # 현재 선택된 시즌 확인
                year_select = Select(driver.find_element(By.ID, "cphContents_cphContents_cphContents_ddlSeason_ddlSeason"))
                curr_year = int(year_select.first_selected_option.text)
                
                cur.execute("SELECT id FROM sl_seasons WHERE league_id=200 AND year=%s", (curr_year,))
                s_row = cur.fetchone()
                if not s_row: continue
                season_id = s_row[0]

                # 테이블 2개 찾기 (주요기록, 세부기록)
                # summary="...성적으로..." 포함된 테이블들
                tables = driver.find_elements(By.CSS_SELECTOR, "table.tbl.tt")
                
                detailed_stats = {}
                
                # 두 번째 테이블 (세부 기록: BB, IBB, HBP ... SAC, SF)
                if len(tables) > 1:
                    row2 = tables[1].find_element(By.CSS_SELECTOR, "tbody tr")
                    cols2 = row2.find_elements(By.TAG_NAME, "td")
                    # 헤더: BB, IBB, HBP, SO, GDP, SLG, OBP, E, SB%, MH, OPS, RISP, PH-BA
                    # 주의: 타자_기본기록.txt 분석 결과, IBB는 1번 인덱스에 있음
                    if len(cols2) >= 10:
                        try:
                            # 1번째: IBB (고의4구)
                            detailed_stats["IBB"] = int(cols2[1].text.strip())
                            
                            # 첫 번째 테이블의 마지막 컬럼들 확인 (SAC, SF가 여기 있을 수 있음)
                            # 분석 결과: Table 1 헤더 끝에 SAC, SF가 있음!
                            # Table 1: ..., SAC, SF
                            row1 = tables[0].find_element(By.CSS_SELECTOR, "tbody tr")
                            cols1 = row1.find_elements(By.TAG_NAME, "td")
                            
                            if len(cols1) >= 16:
                                # [14] SAC (희생번트) [15] SF (희생플라이)
                                detailed_stats["SAC"] = int(cols1[14].text.strip())
                                detailed_stats["SF"] = int(cols1[15].text.strip())
                                
                        except: 
                            pass

                if detailed_stats:
                    sql = """
                        UPDATE sl_player_season_stats
                        SET stats = stats || %s::jsonb, updated_at = NOW()
                        WHERE player_id = %s AND season_id = %s
                    """
                    cur.execute(sql, (json.dumps(detailed_stats), p_id, season_id))
                    conn.commit()
                    print(f"  ✅ {curr_year} 세부 스탯(희생타 등) 보강 완료")

            except Exception as e:
                # print(f"  ⚠️ 세부 스탯 수집 실패: {e}")
                pass

    except Exception as e:
        print(f"❌ 전체 에러: {e}")
    
    finally:
        driver.quit()
        cur.close()
        conn.close()
        print("🎉 수집 종료.")

if __name__ == "__main__":
    sync_batter_details()