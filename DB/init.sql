create table public.sl_sports
(
    id         serial
        primary key,
    name       varchar(50) not null
        unique,
    slug       varchar(50) not null,
    created_at timestamp with time zone default now()
);

alter table public.sl_sports
    owner to hongun;

create table public.sl_leagues
(
    id         bigint       not null
        primary key,
    sport_id   integer
        references public.sl_sports
            on delete cascade,
    name       varchar(100) not null,
    country    varchar(50),
    logo_url   text,
    type       varchar(20),
    created_at timestamp with time zone default now(),
    slug       varchar(50)
);

alter table public.sl_leagues
    owner to hongun;

create table public.sl_seasons
(
    id         serial
        primary key,
    league_id  bigint
        references public.sl_leagues
            on delete cascade,
    year       integer not null,
    start_date date,
    end_date   date,
    is_current boolean default false,
    unique (league_id, year)
);

alter table public.sl_seasons
    owner to hongun;

create table public.sl_teams
(
    id             bigint       not null
        primary key,
    name           varchar(100) not null,
    code           varchar(10),
    logo_url       text,
    founded        integer,
    venue_name     varchar(100),
    venue_capacity integer,
    created_at     timestamp with time zone default now(),
    updated_at     timestamp with time zone default now()
);

alter table public.sl_teams
    owner to hongun;

create table public.sl_players
(
    id          bigint       not null
        primary key,
    name        varchar(100) not null,
    firstname   varchar(50),
    lastname    varchar(50),
    birth_date  date,
    nationality varchar(50),
    height_cm   integer,
    weight_kg   integer,
    photo_url   text,
    biometrics  jsonb                    default '{}'::jsonb,
    created_at  timestamp with time zone default now(),
    updated_at  timestamp with time zone default now()
);

alter table public.sl_players
    owner to hongun;

create index idx_players_name
    on public.sl_players (name);

create table public.sl_team_season_map
(
    id        serial
        primary key,
    team_id   bigint
        references public.sl_teams,
    season_id integer
        references public.sl_seasons,
    unique (team_id, season_id)
);

alter table public.sl_team_season_map
    owner to hongun;

create table public.sl_player_squads
(
    id            serial
        primary key,
    player_id     bigint
        references public.sl_players
            on delete cascade,
    team_id       bigint
        references public.sl_teams
            on delete cascade,
    season_id     integer
        references public.sl_seasons
            on delete cascade,
    position      varchar(50),
    jersey_number integer,
    is_active     boolean default true,
    unique (player_id, team_id, season_id)
);

alter table public.sl_player_squads
    owner to hongun;

create table public.sl_games
(
    id           bigint                   not null
        primary key,
    season_id    integer
        references public.sl_seasons,
    league_id    bigint
        references public.sl_leagues,
    home_team_id bigint
        references public.sl_teams,
    away_team_id bigint
        references public.sl_teams,
    game_date    timestamp with time zone not null,
    status       varchar(20),
    home_score   integer,
    away_score   integer,
    score_detail jsonb                    default '{}'::jsonb,
    created_at   timestamp with time zone default now()
);

alter table public.sl_games
    owner to hongun;

create index idx_games_date
    on public.sl_games (game_date);

create index idx_games_league
    on public.sl_games (league_id);

create table public.sl_player_season_stats
(
    id         serial
        primary key,
    player_id  bigint
        references public.sl_players
            on delete cascade,
    season_id  integer
        references public.sl_seasons
            on delete cascade,
    team_id    bigint
        references public.sl_teams,
    stats      jsonb                    default '{}'::jsonb not null,
    updated_at timestamp with time zone default now(),
    unique (player_id, season_id, team_id)
);

alter table public.sl_player_season_stats
    owner to hongun;

create index idx_player_stats_json
    on public.sl_player_season_stats using gin (stats);

create table public.sl_player_game_stats
(
    id             serial
        primary key,
    game_id        bigint
        references public.sl_games
            on delete cascade,
    player_id      bigint
        references public.sl_players
            on delete cascade,
    team_id        bigint
        references public.sl_teams,
    minutes_played integer,
    rating         numeric(3, 1),
    stats          jsonb default '{}'::jsonb not null,
    unique (game_id, player_id)
);

alter table public.sl_player_game_stats
    owner to hongun;

