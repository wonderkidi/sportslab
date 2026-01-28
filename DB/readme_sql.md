# 🏟️ Sportslab Database Schema (PostgreSQL)

이 문서는 **Sportslab** 프로젝트의 데이터베이스 설계 구조와 DDL(Data Definition Language)을 정의합니다.
PostgreSQL의 강력한 기능인 **JSONB**를 활용하여, 축구/야구 등 다양한 종목의 상이한 데이터 구조를 하나의 DB에서 유연하게 통합 관리하도록 설계되었습니다.

---

## 🛠️ 핵심 설계 전략 (Key Design Decisions)

1.  **Sport-Agnostic Structure (종목 중립적 설계)**
    * 종목마다 다른 스탯(예: 축구의 골 vs 야구의 타율)을 별도 컬럼으로 만들지 않고, `stats` 컬럼 하나에 **JSONB** 포맷으로 저장합니다.
    * 이를 통해 스키마 변경 없이 새로운 종목이나 스탯 필드를 자유롭게 추가할 수 있습니다.

2.  **API-Friendly IDs**
    * 주요 테이블(`SL_players`, `SL_teams`, `SL_games` 등)의 Primary Key는 `SERIAL(자동증가)`이 아닌 `BIGINT`를 사용합니다.
    * 이는 외부 데이터 소스(**API-SPORTS**)의 고유 ID를 그대로 사용하여, 데이터 중복 수집을 방지하고 매핑 효율을 높이기 위함입니다.

3.  **GIN Indexing for Performance**
    * JSON 데이터 내부의 특정 키(예: '홈런 개수')를 빠르게 검색할 수 있도록 `GIN Index`를 적용했습니다.

---

## 📜 DDL Script (init.sql)

아래 스크립트를 PostgreSQL 초기화 시 실행하거나, DB 툴(DBeaver, PGAdmin)에서 실행하십시오.

```sql
-- 1. 기본 설정
SET timezone = 'Asia/Seoul';
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --------------------------------------------------------
-- [Reference Tables] 기준 정보
-- --------------------------------------------------------

-- 1. 스포츠 종목 (Soccer, Baseball, Basketball ...)
CREATE TABLE SL_sports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 리그 정보 (EPL, MLB, KBO ...)
CREATE TABLE SL_leagues (
    id BIGINT PRIMARY KEY, -- API ID 매핑
    sport_id INT REFERENCES SL_sports(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    logo_url TEXT,
    type VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 시즌 정보 (연도별 리그 기간)
CREATE TABLE SL_seasons (
    id SERIAL PRIMARY KEY,
    league_id BIGINT REFERENCES SL_leagues(id) ON DELETE CASCADE,
    year INT NOT NULL,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,
    UNIQUE(league_id, year)
);

-- --------------------------------------------------------
-- [Entity Tables] 팀과 선수
-- --------------------------------------------------------

-- 4. 팀 정보
CREATE TABLE SL_teams (
    id BIGINT PRIMARY KEY, -- API ID 매핑
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10),
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
    height_cm INT,
    weight_kg INT,
    photo_url TEXT,
    biometrics JSONB DEFAULT '{}'::jsonb, -- { "batting": "Right", "throwing": "Left" }
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. 팀-시즌 매핑 (승강제/리그 이동 대비)
CREATE TABLE SL_team_season_map (
    id SERIAL PRIMARY KEY,
    team_id BIGINT REFERENCES SL_teams(id),
    season_id INT REFERENCES SL_seasons(id),
    UNIQUE(team_id, season_id)
);

-- --------------------------------------------------------
-- [Stats & History] 기록과 스탯
-- --------------------------------------------------------

-- 7. 선수 소속 이력 (Roster)
CREATE TABLE SL_player_squads (
    id SERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES SL_players(id) ON DELETE CASCADE,
    team_id BIGINT REFERENCES SL_teams(id) ON DELETE CASCADE,
    season_id INT REFERENCES SL_seasons(id) ON DELETE CASCADE,
    position VARCHAR(50),
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
    status VARCHAR(20),
    home_score INT,
    away_score INT,
    score_detail JSONB DEFAULT '{}'::jsonb, -- { "innings": [...] }
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. 선수 시즌별 스탯 (Yearly Status)
CREATE TABLE SL_player_season_stats (
    id SERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES SL_players(id) ON DELETE CASCADE,
    season_id INT REFERENCES SL_seasons(id) ON DELETE CASCADE,
    team_id BIGINT REFERENCES SL_teams(id),
    stats JSONB NOT NULL DEFAULT '{}'::jsonb, -- { "avg": 0.312, "hr": 30 }
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(player_id, season_id, team_id)
);

-- 10. 선수 경기별 상세 스탯 (Game Logs)
CREATE TABLE SL_player_game_stats (
    id SERIAL PRIMARY KEY,
    game_id BIGINT REFERENCES SL_games(id) ON DELETE CASCADE,
    player_id BIGINT REFERENCES SL_players(id) ON DELETE CASCADE,
    team_id BIGINT REFERENCES SL_teams(id),
    minutes_played INT,
    rating DECIMAL(3, 1),
    stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE(game_id, player_id)
);

-- --------------------------------------------------------
-- [Indexes] 성능 최적화
-- --------------------------------------------------------
CREATE INDEX idx_games_date ON SL_games(game_date);
CREATE INDEX idx_games_league ON SL_games(league_id);
CREATE INDEX idx_players_name ON SL_players(name);
CREATE INDEX idx_player_stats_json ON SL_player_season_stats USING gin (stats);

-- 예: 홈런(hr)이 30개 이상인 야구 선수 조회
SELECT p.name, s.stats->>'hr' as homerun
FROM SL_player_season_stats s
JOIN SL_players p ON s.player_id = p.id
WHERE (s.stats->>'hr')::int >= 30;

-- 예: 특정 시즌 타율(avg) 상위 10명
SELECT p.name, s.stats->>'avg' as average
FROM SL_player_season_stats s
JOIN SL_players p ON s.player_id = p.id
ORDER BY (s.stats->>'avg')::float DESC
LIMIT 10;