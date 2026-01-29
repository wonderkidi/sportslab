import subprocess
import sys
import time
import os

def run_script(script_name):
    print(f"\n" + "="*60)
    print(f"🚀 Running: {script_name}")
    print("="*60)
    
    start_time = time.time()
    try:
        # 윈도우 환경을 고려하여 python 대신 sys.executable 사용
        result = subprocess.run([sys.executable, script_name], capture_output=False, text=True)
        
        duration = time.time() - start_time
        if result.returncode == 0:
            print(f"✅ Finished: {script_name} ({duration:.1f}s)")
        else:
            print(f"❌ Failed: {script_name} with exit code {result.returncode}")
    except Exception as e:
        print(f"💥 Exception while running {script_name}: {e}")

def main():
    print("🏁 SportsLab Data Sync Master")
    print(f"Current Directory: {os.getcwd()}")
    
    # 순차적으로 실행할 스크립트 목록
    # 1. 기초 정보 및 경기 결과 (빠름)
    core_scripts = [
        "espn_league_list.py",   # 리그 정보 (ID mapping 등)
        "update_results.py",     # ESPN 주요 리그 결과 (MLB, NBA, EPL 등)
        "KBO_game.py",           # KBO 경기 결과 (Naver)
        "KLEAGUE_game.py"        # K-League 경기 결과 (Naver)
    ]
    
    # 2. 선수 및 스쿼드 정보 (상대적으로 느림)
    squad_scripts = [
        "espn_player_squads.py", # ESPN 주요 리그 스쿼드
        "KBO_player.py",         # KBO 선수 정보 및 스쿼드 (Selenium)
        "KLEAGUE_player.py"      # K-League 선수 정보 (Lineup Harvesting)
    ]
    
    # 3. 상세 정보 (매우 느림 - 필요시 활성화)
    detail_scripts = [
        # "KBO_batter_stats.py", # KBO 타자 상세
        # "KBO_pitcher_stats.py" # KBO 투수 상세
    ]

    print("\n--- Phase 1: Core Data (Leagues & Games) ---")
    for script in core_scripts:
        run_script(script)

    print("\n--- Phase 2: Squad Data (Players & Rosters) ---")
    for script in squad_scripts:
        run_script(script)

    # print("\n--- Phase 3: Detailed Stats (Optional) ---")
    # for script in detail_scripts:
    #     run_script(script)

    print("\n" + "="*60)
    print("🎉 All synchronization tasks completed!")
    print("="*60)

if __name__ == "__main__":
    main()
