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

def parse_ip(ip_str):
    """
    이닝 문자열 파싱 (예: "14 1/3" -> 14.333, "5" -> 5.0)
    """
    try:
        ip_str = ip_str.strip()
        if ' ' in ip_str:
            # "14 2/3" 형태
            whole, frac = ip_str.split(' ')
            if '/' in frac:
                num, den = map(int, frac.split('/'))
                return float(whole) + (num / den)
        elif '/' in ip_str:
            # "2/3" 형태 (정수부 없음)
            num, den = map(int, ip_str.split('/'))
            return num / den
        
        # 정수 형태 ("14")
        return float(ip_str) if ip_str else 0.0
    except:
        return 0.0

def sync_pitcher_details():
    print("⚾ KBO 투수 상세 기록 수집 시작 (Basic/Career)...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 1. 수집 대상: 포지션이 '투수'인 선수들
    cur.execute("""
        SELECT id, name FROM sl_players 
        WHERE biometrics->>'position' LIKE '%투수%'
    """)
    targets = cur.fetchall()
    
    print(f"🎯 수집 대상: 총 {len(targets)}명")

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    success_count = 0

    try:
        for p_id, p_name in targets:
            print(f"\n👤 {p_name} (ID: {p_id}) 수집 중...")

            # =========================================================
            # 1. 통산 기록 (Total.aspx)
            # =========================================================
            total_url = f"https://www.koreabaseball.com/Record/Player/PitcherDetail/Total.aspx?playerId={p_id}"
            driver.get(total_url)
            time.sleep(1.5)

            try:
                # 테이블 찾기 (summary="통산기록" 또는 헤더 텍스트로 식별)
                tables = driver.find_elements(By.TAG_NAME, "table")
                career_table = None
                
                for tbl in tables:
                    # 투수는 ERA(평균자책점)가 핵심 키워드
                    if "통산기록" in tbl.get_attribute("summary") or ("ERA" in tbl.text and "승" in tbl.text):
                        career_table = tbl
                        break
                
                if not career_table:
                    print(f"  ⚠️ 통산 기록 테이블 미발견 (신인/기록 없음)")
                    continue

                rows = career_table.find_elements(By.CSS_SELECTOR, "tbody tr")
                
                saved_seasons = 0
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    # 헤더: 연도, 팀명, ERA, G, CG, SHO, W, L, SV, HLD, WPCT, TBF, IP, H, HR, BB, HBP, SO, R, ER
                    if len(cols) < 20: continue

                    year_text = cols[0].text.strip()
                    if not year_text.isdigit(): continue
                    
                    year = int(year_text)
                    team_name = cols[1].text.strip()
                    
                    # 시즌 ID 확보
                    cur.execute("SELECT id FROM sl_seasons WHERE league_id=200 AND year=%s", (year,))
                    s_row = cur.fetchone()
                    if not s_row:
                        cur.execute("INSERT INTO sl_seasons (league_id, year, is_current) VALUES (200, %s, false) RETURNING id", (year,))
                        season_id = cur.fetchone()[0]
                    else:
                        season_id = s_row[0]

                    team_id = get_team_id(cur, team_name)
                    
                    try:
                        # 데이터 파싱
                        # [2]ERA [3]G [4]CG [5]SHO [6]W [7]L [8]SV [9]HLD [10]WPCT [11]TBF [12]IP [13]H [14]HR [15]BB [16]HBP [17]SO [18]R [19]ER
                        ip_val = parse_ip(cols[12].text.strip())
                        
                        stats = {
                            "ERA": cols[2].text.strip(),
                            "G": int(cols[3].text.strip()),
                            "CG": int(cols[4].text.strip()),  # 완투
                            "SHO": int(cols[5].text.strip()), # 완봉
                            "W": int(cols[6].text.strip()),   # 승
                            "L": int(cols[7].text.strip()),   # 패
                            "SV": int(cols[8].text.strip()),  # 세이브
                            "HLD": int(cols[9].text.strip()), # 홀드
                            "WPCT": cols[10].text.strip(),    # 승률
                            "TBF": int(cols[11].text.strip()),# 타자수
                            "IP": f"{ip_val:.1f}",            # 이닝 (실수형 문자열로 저장 권장)
                            "H": int(cols[13].text.strip()),  # 피안타
                            "HR": int(cols[14].text.strip()), # 피홈런
                            "BB": int(cols[15].text.strip()), # 볼넷
                            "HBP": int(cols[16].text.strip()),# 사구
                            "SO": int(cols[17].text.strip()), # 삼진
                            "R": int(cols[18].text.strip()),  # 실점
                            "ER": int(cols[19].text.strip())  # 자책점
                        }

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
                success_count += 1
                print(f"  ✅ 통산 {saved_seasons}개 시즌 저장 완료")

            except Exception as e:
                print(f"  ❌ 통산 기록 처리 에러: {e}")
                conn.rollback()

            # =========================================================
            # 2. 기본 기록 (Basic1.aspx) - 세부 스탯 (NP, QS, WHIP 등)
            # =========================================================
            basic_url = f"https://www.koreabaseball.com/Record/Player/PitcherDetail/Basic1.aspx?playerId={p_id}"
            driver.get(basic_url)
            time.sleep(1)

            try:
                # 현재 시즌 연도 확인
                year_select = Select(driver.find_element(By.ID, "cphContents_cphContents_cphContents_ddlSeason_ddlSeason"))
                curr_year = int(year_select.first_selected_option.text)
                
                cur.execute("SELECT id FROM sl_seasons WHERE league_id=200 AND year=%s", (curr_year,))
                s_row = cur.fetchone()
                if not s_row: continue
                season_id = s_row[0]

                # 테이블 파싱 (보통 2개)
                tables = driver.find_elements(By.TAG_NAME, "table")
                main_table = None
                detail_table = None
                
                # 테이블 구분 (헤더 텍스트 기준)
                for tbl in tables:
                    txt = tbl.text
                    if "투구수" in txt or "NP" in txt: # 1번 테이블
                        main_table = tbl
                    if "WHIP" in txt or "QS" in txt:   # 2번 테이블
                        detail_table = tbl

                detailed_stats = {}

                # Table 1: ..., TBF, NP, IP, H, 2B, 3B, HR
                if main_table:
                    row1 = main_table.find_elements(By.CSS_SELECTOR, "tbody tr")[0]
                    cols1 = row1.find_elements(By.TAG_NAME, "td")
                    # TBF(10), NP(11) ... 2B(14), 3B(15) 인덱스 확인 필요
                    # KBO 사이트 구조상 NP는 보통 IP 앞쪽에 위치
                    try:
                        # 전체 텍스트에서 콤마 제거 후 숫자 추출 시도
                        np_text = cols1[11].text.strip().replace(',', '')
                        detailed_stats["NP"] = int(np_text) # 투구수
                    except: pass

                # Table 2: SAC, SF, BB, IBB, SO, WP, BK, R, ER, BSV, WHIP, AVG, QS
                if detail_table:
                    row2 = detail_table.find_elements(By.CSS_SELECTOR, "tbody tr")[0]
                    cols2 = row2.find_elements(By.TAG_NAME, "td")
                    
                    try:
                        # [5]WP(폭투) [6]BK(보크) [10]WHIP [12]QS
                        if len(cols2) >= 13:
                            detailed_stats["WP"] = int(cols2[5].text.strip())
                            detailed_stats["BK"] = int(cols2[6].text.strip())
                            detailed_stats["WHIP"] = cols2[10].text.strip()
                            detailed_stats["QS"] = int(cols2[12].text.strip())
                    except: pass

                if detailed_stats:
                    sql = """
                        UPDATE sl_player_season_stats
                        SET stats = stats || %s::jsonb, updated_at = NOW()
                        WHERE player_id = %s AND season_id = %s
                    """
                    cur.execute(sql, (json.dumps(detailed_stats), p_id, season_id))
                    conn.commit()
                    # print(f"  ✅ {curr_year} 세부 스탯 보강 완료")

            except Exception:
                pass

    except Exception as e:
        print(f"❌ 전체 프로세스 에러: {e}")
    
    finally:
        driver.quit()
        cur.close()
        conn.close()
        print(f"🎉 총 {success_count}명의 투수 기록 저장 완료.")

if __name__ == "__main__":
    sync_pitcher_details()