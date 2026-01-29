import requests

def list_kleague_teams():
    url = "https://api-gw.sports.naver.com/schedule/games"
    params = {
        "fields": "basic,status,team,score",
        "upperCategoryId": "kfootball",
        "categoryId": "kleague",
        "fromDate": "2024-05-01",
        "toDate": "2024-06-30",
        "size": 200
    }
    res = requests.get(url, params=params)
    games = res.json().get('result', {}).get('games', [])
    teams = {}
    for g in games:
        code = g.get('homeTeamCode')
        name = g.get('homeTeamName')
        if code and name:
            teams[code] = name
            
    print("K-League Teams Found:")
    for code, name in sorted(teams.items()):
        print(f"  Code: {code}, Name: {name}")

if __name__ == "__main__":
    list_kleague_teams()
