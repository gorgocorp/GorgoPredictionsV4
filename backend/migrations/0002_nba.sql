-- NBA (API-Basketball, league=12): esquema final de GorgoNBAParlays (sus migraciones 0001–0009) en el
-- esquema `nba`, salvo lo que pasó a `core` (ingest_runs, picks, parlays y apuestas).
-- Los IDs de equipos, jugadores y partidos son los de API-Basketball, estables entre temporadas según su
-- documentación.

-- Fechas de fase por temporada, en hora del Este (ET). Las fechas vienen del calendario oficial y se
-- verificaron contra la densidad de partidos en los datos. Cada temporada nueva se registra con una migración.
CREATE TABLE nba.seasons (
    season TEXT PRIMARY KEY CHECK (season ~ '^\d{4}-\d{4}$'),
    regular_start DATE NOT NULL,
    regular_end DATE,
    playin_start DATE,
    playoffs_start DATE
);

INSERT INTO nba.seasons (season, regular_start, regular_end, playin_start, playoffs_start) VALUES
    ('2024-2025', '2024-10-22', '2025-04-13', '2025-04-15', '2025-04-19'),
    ('2025-2026', '2025-10-21', '2026-04-12', '2026-04-14', '2026-04-18'),
    ('2026-2027', '2026-10-20', NULL, NULL, NULL);

CREATE TABLE nba.teams (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    logo TEXT,
    raw_payload JSONB NOT NULL CHECK (jsonb_typeof(raw_payload) = 'object'),
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE nba.players (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    position TEXT,
    country TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE nba.games (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    season TEXT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    -- Fecha del partido en hora del Este: un juego de 10 pm ET cae al día siguiente en UTC.
    game_date DATE NOT NULL,
    status TEXT NOT NULL,
    home_team_id INTEGER NOT NULL REFERENCES nba.teams (id),
    away_team_id INTEGER NOT NULL REFERENCES nba.teams (id),
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

CREATE INDEX games_season_date_idx ON nba.games (season, game_date);
CREATE INDEX games_home_team_idx ON nba.games (home_team_id, game_date);
CREATE INDEX games_away_team_idx ON nba.games (away_team_id, game_date);

-- Una fila por jugador y partido.
-- Ojo: en la API `field_goals` son sólo tiros de 2; aquí se guardan como fg2_*.
-- En ~12% de las filas la API trae fg2 en 0/0 aunque hubo dobles; `fg2_made_derived`
-- los reconstruye desde los puntos (los intentos no se pueden recuperar).
CREATE TABLE nba.player_game_stats (
    game_id INTEGER NOT NULL REFERENCES nba.games (id),
    player_id INTEGER NOT NULL REFERENCES nba.players (id),
    team_id INTEGER NOT NULL REFERENCES nba.teams (id),
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

CREATE INDEX player_game_stats_player_idx ON nba.player_game_stats (player_id);
CREATE INDEX player_game_stats_team_idx ON nba.player_game_stats (team_id, game_id);

-- Una fila por equipo y partido. Aquí sí hay robos, bloqueos y pérdidas.
CREATE TABLE nba.team_game_stats (
    game_id INTEGER NOT NULL REFERENCES nba.games (id),
    team_id INTEGER NOT NULL REFERENCES nba.teams (id),
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
CREATE TABLE nba.odds_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES nba.games (id),
    bookmaker_id INTEGER NOT NULL,
    bookmaker_name TEXT,
    bet_id INTEGER NOT NULL,
    bet_name TEXT,
    selection TEXT NOT NULL,
    odd NUMERIC(10, 3) NOT NULL CHECK (odd > 1),
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    first_run_id BIGINT NOT NULL REFERENCES core.ingest_runs (id),
    last_run_id BIGINT NOT NULL REFERENCES core.ingest_runs (id),
    CONSTRAINT odds_history_seen_order CHECK (last_seen_at >= first_seen_at),
    CONSTRAINT odds_history_observation_unique
        UNIQUE (game_id, bookmaker_id, bet_id, selection, first_seen_at)
);

CREATE INDEX odds_history_game_idx ON nba.odds_history (game_id, bet_id);

-- Proyección del modelo por partido (misma regla que picks: se congela al empezar el partido).
CREATE TABLE nba.game_projections (
    game_id INTEGER PRIMARY KEY REFERENCES nba.games (id),
    home_points NUMERIC(6, 2) NOT NULL,
    away_points NUMERIC(6, 2) NOT NULL,
    p_home_win NUMERIC(6, 4) NOT NULL CHECK (p_home_win > 0 AND p_home_win < 1),
    model_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL,
    -- Puntos por partido que se esperan perdidos por bajas en cada equipo (ya aplicados a la proyección).
    home_missing_pts NUMERIC(6, 2) NOT NULL DEFAULT 0,
    away_missing_pts NUMERIC(6, 2) NOT NULL DEFAULT 0,
    -- Ajuste por cambios de plantel entre temporadas (pts por partido netos perdidos, ya ponderados por el
    -- peso de la temporada anterior; negativo = el equipo ganó producción) y su detalle.
    home_roster_pts NUMERIC(6, 2) NOT NULL DEFAULT 0,
    away_roster_pts NUMERIC(6, 2) NOT NULL DEFAULT 0,
    roster_detail JSONB
);

-- Disponibilidad de jugadores: reporte oficial de lesiones de la NBA + correcciones manuales.

-- Cada reporte oficial descargado (la NBA publica uno cada 15 minutos en temporada).
CREATE TABLE nba.injury_reports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_at TIMESTAMPTZ NOT NULL UNIQUE,
    url TEXT NOT NULL,
    entries INTEGER NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL
);

-- Equipos incluidos en cada reporte y si ya entregaron su lista ("NOT YET SUBMITTED" = no).
CREATE TABLE nba.injury_report_teams (
    report_id BIGINT NOT NULL REFERENCES nba.injury_reports (id) ON DELETE CASCADE,
    game_date DATE NOT NULL,
    team_id INTEGER NOT NULL REFERENCES nba.teams (id),
    submitted BOOLEAN NOT NULL,
    PRIMARY KEY (report_id, game_date, team_id)
);

-- Jugadores con designación en un reporte. Los que no aparecen están disponibles.
CREATE TABLE nba.injury_entries (
    report_id BIGINT NOT NULL REFERENCES nba.injury_reports (id) ON DELETE CASCADE,
    game_date DATE NOT NULL,
    team_id INTEGER NOT NULL REFERENCES nba.teams (id),
    player_name TEXT NOT NULL,
    player_id INTEGER REFERENCES nba.players (id),
    status TEXT NOT NULL CHECK (status IN ('out', 'doubtful', 'questionable', 'probable', 'available')),
    reason TEXT,
    PRIMARY KEY (report_id, game_date, team_id, player_name)
);

-- Correcciones manuales desde la interfaz: mandan sobre el reporte.
CREATE TABLE nba.availability_overrides (
    game_date DATE NOT NULL,
    player_id INTEGER NOT NULL REFERENCES nba.players (id),
    status TEXT NOT NULL CHECK (status IN ('out', 'available')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (game_date, player_id)
);

-- Partidos con su fase (pretemporada, regular, play-in, playoffs) calculada desde `seasons`.
CREATE VIEW nba.v_games AS
SELECT
    g.*,
    CASE
        WHEN g.game_date < s.regular_start THEN 'preseason'
        WHEN s.playoffs_start IS NOT NULL AND g.game_date >= s.playoffs_start THEN 'playoffs'
        WHEN s.playin_start IS NOT NULL AND g.game_date >= s.playin_start THEN 'playin'
        ELSE 'regular'
    END AS phase,
    g.status IN ('FT', 'AOT') AS is_finished
FROM nba.games g
LEFT JOIN nba.seasons s ON s.season = g.season;

-- Último momio conocido de cada selección.
CREATE VIEW nba.v_odds_latest AS
SELECT DISTINCT ON (game_id, bookmaker_id, bet_id, selection) *
FROM nba.odds_history
ORDER BY game_id, bookmaker_id, bet_id, selection, last_seen_at DESC;

-- Último reporte que incluye cada fecha de partido.
CREATE VIEW nba.v_latest_injury_report AS
SELECT DISTINCT ON (t.game_date) t.game_date, r.id AS report_id, r.report_at
FROM nba.injury_report_teams t
JOIN nba.injury_reports r ON r.id = t.report_id
ORDER BY t.game_date, r.report_at DESC;

-- Estado efectivo por jugador y fecha: corrección manual si existe; si no, el último reporte.
CREATE VIEW nba.v_player_availability AS
WITH report AS (
    SELECT e.game_date, e.player_id, e.team_id, e.status, e.reason, l.report_at
    FROM nba.injury_entries e
    JOIN nba.v_latest_injury_report l ON l.report_id = e.report_id AND l.game_date = e.game_date
    WHERE e.player_id IS NOT NULL
)
SELECT
    COALESCE(m.game_date, r.game_date) AS game_date,
    COALESCE(m.player_id, r.player_id) AS player_id,
    COALESCE(m.status, r.status) AS status,
    r.status AS report_status,
    r.reason,
    r.report_at,
    m.status IS NOT NULL AS manual
FROM report r
FULL OUTER JOIN nba.availability_overrides m ON m.game_date = r.game_date AND m.player_id = r.player_id;
