import requests

def test_all_leagues():
    target_leagues = [
        # --- ⚾ 야구 (Baseball) ---
        ("baseball", "mlb"),              # 미국 MLB
        ("baseball", "college-baseball"), # 미국 대학야구 (NCAA)

        # --- 🏀 농구 (Basketball) ---
        ("basketball", "nba"),                      # 미국 NBA
        ("basketball", "wnba"),                     # 미국 WNBA
        ("basketball", "mens-college-basketball"),  # 미국 대학농구 (NCAA 남자)
        ("basketball", "womens-college-basketball"),# 미국 대학농구 (NCAA 여자)

        # --- 🏈 미식축구 (Football) ---
        ("football", "nfl"),              # 미국 NFL
        ("football", "college-football"), # 미국 대학풋볼 (NCAA)
        ("football", "cfl"),              # 캐나다 CFL
        ("football", "ufl"),              # 미국 UFL (통합 리그)

        # --- 🏒 하키 (Hockey) ---
        ("hockey", "nhl"),                # 북미 NHL

        # --- ⚽ 축구 (Soccer) - 유럽 5대 리그 ---
        ("soccer", "eng.1"),              # 잉글랜드 프리미어리그 (EPL)
        ("soccer", "esp.1"),              # 스페인 라리가
        ("soccer", "ger.1"),              # 독일 분데스리가
        ("soccer", "ita.1"),              # 이탈리아 세리에 A
        ("soccer", "fra.1"),              # 프랑스 리그 1

        # --- ⚽ 축구 (Soccer) - 유럽 대항전 & 컵 ---
        ("soccer", "uefa.champions"),     # UEFA 챔피언스리그 (UCL)
        ("soccer", "uefa.europa"),        # UEFA 유로파리그 (UEL)
        ("soccer", "eng.fa"),             # 잉글랜드 FA컵
        ("soccer", "eng.league_cup"),     # 잉글랜드 카라바오컵

        # --- ⚽ 축구 (Soccer) - 아시아 & 미주 & 기타 ---
        ("soccer", "jpn.1"),              # 일본 J리그 1
        ("soccer", "usa.1"),              # 미국 MLS
        ("soccer", "bra.1"),              # 브라질 세리에 A
        ("soccer", "arg.1"),              # 아르헨티나 프리메라
        ("soccer", "ned.1"),              # 네덜란드 에레디비시

        # --- ⚽ 축구 (Soccer) - 국가대표 ---
        ("soccer", "fifa.friendly"),      # A매치 (국가대표 친선)
        ("soccer", "uefa.nations"),       # UEFA 네이션스리그
        ("soccer", "fifa.world"),         # 월드컵 (대회 기간 중 활성화)

        # --- 🥊 격투기 (Combat Sports) ---
        ("mma", "ufc"),                   # UFC

        # --- 🏎️ 레이싱 (Racing) ---
        ("racing", "f1"),                 # 포뮬러 1 (F1)

        # --- ⛳ 골프 (Golf) ---
        ("golf", "pga"),                  # PGA 투어
        ("golf", "lpga"),                 # LPGA 투어
        ("golf", "eur"),                  # DP 월드투어 (유러피언 투어)
        ("golf", "liv"),                  # LIV 골프

        # --- 🎾 테니스 (Tennis) ---
        ("tennis", "atp"),                # 남자 프로 테니스 (ATP)
        ("tennis", "wta")                 # 여자 프로 테니스 (WTA)
    ]

    print(f"{'SPORT':<12} {'LEAGUE':<15} {'STATUS':<10} {'INFO'}")
    print("-" * 60)

    for sport, league in target_leagues:
        url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                # 리그 이름과 현재 시즌 정보 가져오기
                league_name = data['leagues'][0]['name']
                event_count = len(data.get('events', []))
                print(f"{sport:<12} {league:<15} ✅ OK       {league_name} ({event_count} games)")
            else:
                print(f"{sport:<12} {league:<15} ❌ {res.status_code}")
        except Exception as e:
            print(f"{sport:<12} {league:<15} ❌ Error")

if __name__ == "__main__":
    test_all_leagues()