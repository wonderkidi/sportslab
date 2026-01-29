import requests
import json

def test_naver_players():
    # Try naive guess for player list
    url = "https://api-gw.sports.naver.com/team/kbaseball/kbo/LG/player" # LG Twins sample
    try:
        res = requests.get(url)
        print(f"LG Players Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            players = data.get('result', {}).get('players', [])
            print(f"Found {len(players)} players for LG")
            if players:
                print(json.dumps(players[0], indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_naver_players()
