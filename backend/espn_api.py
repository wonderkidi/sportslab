#

# 각 종목별 클래스를 따로 불러와야 합니다.
from espn_api.football import League as FootballLeague
from espn_api.baseball import League as BaseballLeague
from espn_api.basketball import League as BasketballLeague
from espn_api.hockey import League as HockeyLeague
from espn_api.wnba import League as WNBALeague

def connect_espn_fantasy():
    # 주의: 실제 데이터를 가져오려면 본인의 판타지 리그 ID(league_id)가 필요합니다.
    # 비공개 리그인 경우 swid와 espn_s2 쿠키값도 필요합니다.
    
    league_id = 12345678  # 예시 ID
    year = 2024

    try:
        # 1. NFL (미식축구)
        nfl = FootballLeague(league_id=league_id, year=year)
        print("NFL 연결 성공")

        # 2. NBA (농구)
        nba = BasketballLeague(league_id=league_id, year=year)
        print("NBA 연결 성공")

        # 3. MLB (야구)
        mlb = BaseballLeague(league_id=league_id, year=year)
        print("MLB 연결 성공")
        
        # 4. NHL (하키)
        nhl = HockeyLeague(league_id=league_id, year=year)
        print("NHL 연결 성공")

    except Exception as e:
        print(f"연결 실패 (ID가 유효하지 않음): {e}")

if __name__ == "__main__":
    connect_espn_fantasy()