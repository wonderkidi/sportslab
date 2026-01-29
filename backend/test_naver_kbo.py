import requests
import json

def test_naver_kbo():
    year = 2024
    month = 5
    url = "https://api-gw.sports.naver.com/schedule/games"
    params = {
        "fields": "basic,status,team,score",
        "upperCategoryId": "kbaseball",
        "categoryId": "kbo",
        "fromDate": f"{year}-{month:02d}-01",
        "toDate": f"{year}-{month:02d}-31",
        "size": 200
    }
    
    try:
        res = requests.get(url, params=params)
        print(f"Status: {res.status_code}")
        data = res.json()
        games = data.get('result', {}).get('games', [])
        print(f"Found {len(games)} games for {year}-{month}")
        if games:
            print("First game sample keys:", games[0].keys())
            print("Home Team ID:", games[0].get('homeTeamId'))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_naver_kbo()
