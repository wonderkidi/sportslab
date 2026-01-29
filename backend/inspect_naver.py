import requests
import json

def inspect_raw_naver(category_id, upper_category_id):
    url = "https://api-gw.sports.naver.com/schedule/games"
    params = {
        "fields": "basic,status,team,score",
        "upperCategoryId": upper_category_id,
        "categoryId": category_id,
        "fromDate": "2024-05-25",
        "toDate": "2024-05-25",
        "size": 5
    }
    
    try:
        res = requests.get(url, params=params)
        data = res.json()
        games = data.get('result', {}).get('games', [])
        if games:
            print(f"--- Raw {category_id} Game ---")
            print(json.dumps(games[0], indent=2, ensure_ascii=False))
        else:
            print(f"No games found for {category_id}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_raw_naver("kbo", "kbaseball")
    inspect_raw_naver("kleague", "kfootball")
