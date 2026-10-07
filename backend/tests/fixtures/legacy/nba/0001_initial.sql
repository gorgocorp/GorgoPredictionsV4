-- Esquema inicial. Fuente única: API-Basketball (league=12, NBA).
-- Los IDs de equipos, jugadores y partidos son los IDs del proveedor, estables entre
-- temporadas según su documentación. Si se agrega otro proveedor, se necesitará una
-- tabla de correspondencias en lugar de reutilizar estas llaves.

-- Registro de cada ejecución de ingesta.
CREATE TABLE ingest_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job TEXT NOT NULL,
    params JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'success', 'failed')),
    requests_made INTEGER NOT NULL DEFAULT 0,
    rows_received INTEGER NOT NULL DEFAULT 0,
    rows_written INTEGER NOT NULL DEFAULT 0,
    rows_skipped INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

-- Fechas de fase por temporada, en hora del Este (ET). Las fechas vienen del
-- calendario oficial y se verificaron contra la densidad de partidos en los datos.
CREATE TABLE seasons (
    season TEXT PRIMARY KEY CHECK (season ~ '^\d{4}-\d{4}$'),
    regular_start DATE NOT NULL,
    regular_end DATE,
    playin_start DATE,
    playoffs_start DATE
);

INSERT INTO seasons (season, regular_start, regular_end, playin_start, playoffs_start) VALUES
    ('2024-2025', '2024-10-22', '2025-04-13', '2025-04-15', '2025-04-19'),
    ('2025-2026', '2025-10-21', '2026-04-12', '2026-04-14', '2026-04-18'),
    ('2026-2027', '2026-10-20', NULL, NULL, NULL);

CREATE TABLE teams (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    logo TEXT,
    raw_payload JSONB NOT NULL CHECK (jsonb_typeof(raw_payload) = 'object'),
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE players (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    position TEXT,
    country TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE games (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    season TEXT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    -- Fecha del partido en hora del Este: un juego de 10 pm ET cae al día siguiente en UTC.
    game_date DATE NOT NULL,
    status TEXT NOT NULL,
    home_team_id INTEGER NOT NULL REFERENCES teams (id),
    away_team_id INTEGER NOT NULL REFERENCES teams (id),
    home_q1 SMALLINT, home_q2 SMALLINT, home_q3 SMALLINT, home_q4 SMALLINT,
    home_ot SMALLINT, home_total SMALLINT,
    away_q1 SMALLINT, away_q2 SMALLINT, away_q3 SMALLINT, away_q4 SMALLINT,
    away_ot SMALLINT, away_total SMALLINT,
    venue TEXT,
    raw_payload JSONB NOT NULL CHECK (jsonb_typeof(raw_payload) = 'object'),
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT games_distinct_teams CHECK (home_team_id <> away_team_id)
);

CREATE INDEX games_season_date_idx ON games (season, game_date);
CREATE INDEX games_home_team_idx ON games (home_team_id, game_date);
CREATE INDEX games_away_team_idx ON games (away_team_id, game_date);

-- Una fila por jugador y partido.
-- Ojo: en la API `field_goals` son sólo tiros de 2; aquí se guardan como fg2_*.
-- En ~12% de las filas la API trae fg2 en 0/0 aunque hubo dobles; `fg2_made_derived`
-- los reconstruye desde los puntos (los intentos no se pueden recuperar).
CREATE TABLE player_game_stats (
    game_id INTEGER NOT NULL REFERENCES games (id),
    player_id INTEGER NOT NULL REFERENCES players (id),
    team_id INTEGER NOT NULL REFERENCES teams (id),
    is_starter BOOLEAN NOT NULL,
    seconds_played INTEGER,
    points SMALLINT,
    rebounds SMALLINT,
    assists SMALLINT,
    fg2_made SMALLINT,
    fg2_attempts SMALLINT,
    fg3_made SMALLINT,
    fg3_attempts SMALLINT,
    ft_made SMALLINT,
    ft_attempts SMALLINT,
    fg2_made_derived SMALLINT,
    raw_payload JSONB NOT NULL CHECK (jsonb_typeof(raw_payload) = 'object'),
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (game_id, player_id)
);

CREATE INDEX player_game_stats_player_idx ON player_game_stats (player_id);
CREATE INDEX player_game_stats_team_idx ON player_game_stats (team_id, game_id);

-- Una fila por equipo y partido. Aquí sí hay robos, bloqueos y pérdidas.
CREATE TABLE team_game_stats (
    game_id INTEGER NOT NULL REFERENCES games (id),
    team_id INTEGER NOT NULL REFERENCES teams (id),
    fg2_made SMALLINT,
    fg2_attempts SMALLINT,
    fg3_made SMALLINT,
    fg3_attempts SMALLINT,
    ft_made SMALLINT,
    ft_attempts SMALLINT,
    rebounds SMALLINT,
    assists SMALLINT,
    steals SMALLINT,
    blocks SMALLINT,
    turnovers SMALLINT,
    raw_payload JSONB NOT NULL CHECK (jsonb_typeof(raw_payload) = 'object'),
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (game_id, team_id)
);

-- Historial de momios sin sobrescribir: una fila por cada valor distinto observado.
-- Si en la siguiente recolección el momio no cambió, sólo se actualiza last_seen_at;
-- si cambió, se inserta una fila nueva. Así se sabe qué momio existía antes de cada partido.
CREATE TABLE odds_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games (id),
    bookmaker_id INTEGER NOT NULL,
    bookmaker_name TEXT,
    bet_id INTEGER NOT NULL,
    bet_name TEXT,
    selection TEXT NOT NULL,
    odd NUMERIC(10, 3) NOT NULL CHECK (odd > 1),
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    first_run_id BIGINT NOT NULL REFERENCES ingest_runs (id),
    last_run_id BIGINT NOT NULL REFERENCES ingest_runs (id),
    CONSTRAINT odds_history_seen_order CHECK (last_seen_at >= first_seen_at),
    CONSTRAINT odds_history_observation_unique
        UNIQUE (game_id, bookmaker_id, bet_id, selection, first_seen_at)
);

CREATE INDEX odds_history_game_idx ON odds_history (game_id, bet_id);

-- Partidos con su fase (pretemporada, regular, play-in, playoffs) calculada desde `seasons`.
CREATE VIEW v_games AS
SELECT
    g.*,
    CASE
        WHEN g.game_date < s.regular_start THEN 'preseason'
        WHEN s.playoffs_start IS NOT NULL AND g.game_date >= s.playoffs_start THEN 'playoffs'
        WHEN s.playin_start IS NOT NULL AND g.game_date >= s.playin_start THEN 'playin'
        ELSE 'regular'
    END AS phase,
    g.status IN ('FT', 'AOT') AS is_finished
FROM games g
LEFT JOIN seasons s ON s.season = g.season;

-- Último momio conocido de cada selección.
CREATE VIEW v_odds_latest AS
SELECT DISTINCT ON (game_id, bookmaker_id, bet_id, selection) *
FROM odds_history
ORDER BY game_id, bookmaker_id, bet_id, selection, last_seen_at DESC;
