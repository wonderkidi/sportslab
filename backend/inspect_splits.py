import requests
import json

# NBA / Trae Young ID
TEST_SPORT = "basketball"
TEST_LEAGUE = "nba"
PLAYER_ID = "4277905" # Trae Young (만약 이 선수가 없으면 다른 ID로 자동 교체됨)

def inspect_web_v2_structure():
    print("🕵️‍♂️ [Web V2 API 구조 정밀 분석] 시작...")
    
    # 1. 선수 ID 자동 확보 (혹시 모를 오류 방지)
    try:
        teams_url = f"http://site.api.espn.com/apis/site/v2/sports/{TEST_SPORT}/{TEST_LEAGUE}/teams"
        res = requests.get(teams_url, params={'limit': 1})
        team_id = res.json()['sports'][0]['leagues'][0]['teams'][0]['team']['id']
        roster_url = f"{teams_url}/{team_id}"
        r_res = requests.get(roster_url, params={'enable': 'roster'})
        athlete = r_res.json()['team']['athletes'][0]
        pid = athlete['id']
        pname = athlete['fullName']
        print(f"👤 분석 대상: {pname} (ID: {pid})")
    except:
        pid = PLAYER_ID
        print(f"👤 분석 대상: ID {pid} (Fallback)")

    # 2. Web V2 API 호출
    # 헤더 필수
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # URL 1: 기본 프로필
    url_profile = f"https://site.web.api.espn.com/apis/site/v2/sports/{TEST_SPORT}/{TEST_LEAGUE}/athletes/{pid}"
    print(f"\n🌐 [1] 기본 프로필 호출: {url_profile}")
    
    res = requests.get(url_profile, headers=headers)
    
    if res.status_code == 200:
        data = res.json()
        athlete = data.get('athlete', {})
        print(f"   🔑 Athlete Keys: {list(athlete.keys())}")
        
        # stats 체크
        if 'stats' in athlete:
            print(f"   ✅ 'stats' 필드 존재함! 개수: {len(athlete['stats'])}")
            if len(athlete['stats']) > 0:
                 print(json.dumps(athlete['stats'][0], indent=4, ensure_ascii=False)[:300])
        else:
            print("   ❌ 'stats' 필드가 없습니다.")
            
        # statistics 체크
        if 'statistics' in athlete:
             print(f"   ✅ 'statistics' 필드 존재함!")
        
        # 혹시 'career' 같은게 있는지?
        if 'career' in athlete:
             print(f"   ✅ 'career' 필드 존재함!")

    else:
        print(f"❌ 호출 실패: {res.status_code}")
        
    # URL 2: params 추가해보기
    print(f"\n🌐 [2] 파라미터 추가 호출 (enable=stats)")
    res2 = requests.get(url_profile, params={'enable': 'stats'}, headers=headers)
    if res2.status_code == 200:
         data2 = res2.json()
         athlete2 = data2.get('athlete', {})
         if 'stats' in athlete2:
             print(f"   ✅ enable=stats로 'stats' 발견! 개수: {len(athlete2['stats'])}")
         else:
             print("   ❌ 여전히 'stats'가 없습니다.")

if __name__ == "__main__":
    inspect_web_v2_structure()