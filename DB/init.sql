-- 1. 기본 설정 (타임존 및 확장기능)
SET timezone = 'Asia/Seoul';
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- 고유 ID 생성을 위해 필요 시 사용

-- --------------------------------------------------------
-- [Reference Tables] 기준 정보
-- --------------------------------------------------------

-- 1. 스포츠 종목 (예: Soccer, Baseball, Basketball)
CREATE TABLE SL_sports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(50) NOT NULL, -- URL용 (예: baseball)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 리그 정보 (예: EPL, MLB, KBO)
CREATE TABLE SL_leagues (
    id BIGINT PRIMARY KEY, -- API-SPORTS의 ID와 매핑하기 위해 BIGINT 사용
    sport_id INT REFERENCES SL_sports(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    logo_url TEXT,
    type VARCHAR(20), -- League or Cup
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 시즌 정보 (연도별 리그 기간)
CREATE TABLE SL_seasons (
    id SERIAL PRIMARY KEY,
    league_id BIGINT REFERENCES SL_leagues(id) ON DELETE CASCADE,
    year INT NOT NULL, -- 2024, 2025
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE, -- 현재 진행 중인 시즌인지 여부
    UNIQUE(league_id, year) -- 같은 리그에 같은 연도 중복 방지
);

-- --------------------------------------------------------
-- [Entity Tables] 팀과 선수
-- --------------------------------------------------------

-- 4. 팀 정보
CREATE TABLE SL_teams (
    id BIGINT PRIMARY KEY, -- API ID 매핑
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10), -- 예: TOT, LAD
    logo_url TEXT,
    founded INT,
    venue_name VARCHAR(100),
    venue_capacity INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 선수 기본 정보 (변하지 않는 스펙)
CREATE TABLE SL_players (
    id BIGINT PRIMARY KEY, -- API ID 매핑
    name VARCHAR(100) NOT NULL,
    firstname VARCHAR(50),
    lastname VARCHAR(50),
    birth_date DATE,
    nationality VARCHAR(50),
    height_cm INT, -- 키 (cm)
    weight_kg INT, -- 몸무게 (kg)
    photo_url TEXT,
    
    -- [Expert Tip] 종목별 특이사항은 JSONB로 처리
    -- 예: { "batting": "Right", "throwing": "Left", "preferred_foot": "Right" }
    biometrics JSONB DEFAULT '{}'::jsonb, 
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. 팀-리그 연결 (어떤 팀이 어느 시즌에 어느 리그에 있었나)
-- 승강제가 있는 축구나, 리그 이동이 잦은 경우 필수
CREATE TABLE SL_team_season_map (
    id SERIAL PRIMARY KEY,
    team_id BIGINT REFERENCES SL_teams(id),
    season_id INT REFERENCES SL_seasons(id),
    UNIQUE(team_id, season_id)
);

-- --------------------------------------------------------
-- [Stats & History] 기록과 스탯 (핵심)
-- --------------------------------------------------------

-- 7. 선수 소속 이력 (Squad/Roster)
-- 선수가 특정 시즌에 어떤 팀, 어떤 포지션이었는지
CREATE TABLE SL_player_squads (
    id SERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES SL_players(id) ON DELETE CASCADE,
    team_id BIGINT REFERENCES SL_teams(id) ON DELETE CASCADE,
    season_id INT REFERENCES SL_seasons(id) ON DELETE CASCADE,
    
    position VARCHAR(50), -- FW, Pitcher, Guard
    jersey_number INT,
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(player_id, team_id, season_id)
);

-- 8. 경기 일정 및 결과
CREATE TABLE SL_games (
    id BIGINT PRIMARY KEY, -- API Game ID
    season_id INT REFERENCES SL_seasons(id),
    league_id BIGINT REFERENCES SL_leagues(id),
    
    home_team_id BIGINT REFERENCES SL_teams(id),
    away_team_id BIGINT REFERENCES SL_teams(id),
    
    game_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(20), -- NS(Not Started), FT(Finished), PST(Postponed)
    
    -- 간단한 스코어 저장
    home_score INT,
    away_score INT,
    
    -- [Expert Tip] 경기 세부 결과 (이닝별 점수, 연장전 등)
    -- 예: { "halftime": "1-0", "fulltime": "2-1", "innings": [...] }
    score_detail JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. 선수 시즌별 스탯 (Yearly Status) -> 질문하신 "연도별 스테이터스"
-- 매 경기 합산이 아니라, 시즌 종료 후 혹은 주기적으로 업데이트되는 요약 테이블
CREATE TABLE SL_player_season_stats (
    id SERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES SL_players(id) ON DELETE CASCADE,
    season_id INT REFERENCES SL_seasons(id) ON DELETE CASCADE,
    team_id BIGINT REFERENCES SL_teams(id),
    
    -- [Expert Tip] 종목 불문 모든 스탯을 다 넣는 마법의 컬럼
    -- 야구 예시: { "avg": 0.312, "hr": 30, "rbi": 100, "era": 2.50 }
    -- 축구 예시: { "goals": 15, "assists": 10, "yellow_cards": 2, "rating": 7.5 }
    stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(player_id, season_id, team_id)
);

-- 10. 선수 경기별 상세 스탯 (Game Logs)
-- 가장 데이터가 많이 쌓이는 테이블 (Partitioning 고려 가능)
CREATE TABLE SL_player_game_stats (
    id SERIAL PRIMARY KEY,
    game_id BIGINT REFERENCES SL_games(id) ON DELETE CASCADE,
    player_id BIGINT REFERENCES SL_players(id) ON DELETE CASCADE,
    team_id BIGINT REFERENCES SL_teams(id),
    
    minutes_played INT, -- 공통적으로 많이 쓰임
    rating DECIMAL(3, 1), -- 평점 (10.0 만점)
    
    -- 경기별 상세 스탯
    -- { "shots": 3, "pass_accuracy": 90, "tackles": 2 }
    stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    UNIQUE(game_id, player_id)
);

-- --------------------------------------------------------
-- [Indexes] 검색 성능 최적화
-- --------------------------------------------------------
CREATE INDEX idx_games_date ON SL_games(game_date); -- 날짜별 경기 조회용
CREATE INDEX idx_games_league ON SL_games(league_id); -- 리그별 조회용
CREATE INDEX idx_players_name ON SL_players(name); -- 선수 이름 검색용
CREATE INDEX idx_player_stats_json ON SL_player_season_stats USING gin (stats); -- JSON 내부 필드 검색 가속 (GIN Index)