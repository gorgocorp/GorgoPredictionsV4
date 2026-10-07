-- Fútbol (API-Football v3, 15 competiciones): esquema final de GorgoPredictionsV3 (sus migraciones
-- 0001–0004) en el esquema `futbol`, salvo lo que pasó a `core` (ingest_runs, picks, parlays y apuestas).
-- Los IDs de ligas, equipos, jugadores y partidos son los de API-Football, estables entre temporadas
-- según su documentación.

-- Competiciones del proyecto y su temporada en curso (la API usa el año de inicio: 2026 = 2026-27).
CREATE TABLE futbol.leagues (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    country TEXT,
    type TEXT,
    logo TEXT,
    current_season SMALLINT,
    season_start DATE,
    season_end DATE,
    coverage JSONB,
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE futbol.teams (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    logo TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Nombre completo ("Zion Suzuki") de las estadísticas por jugador; las alineaciones traen
-- la forma corta ("Z. Suzuki") y sólo se usan si el jugador todavía no existe.
CREATE TABLE futbol.players (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    photo TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE futbol.fixtures (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    league_id INTEGER NOT NULL REFERENCES futbol.leagues (id),
    season SMALLINT NOT NULL,
    round TEXT,
    starts_at TIMESTAMPTZ NOT NULL,
    -- Fecha del partido en la zona horaria local (centro de México por defecto).
    match_date DATE NOT NULL,
    status TEXT NOT NULL,
    elapsed SMALLINT,
    home_team_id INTEGER NOT NULL REFERENCES futbol.teams (id),
    away_team_id INTEGER NOT NULL REFERENCES futbol.teams (id),
    -- Marcador de los 90 minutos (más reposición): con él se liquidan las apuestas.
    ft_home SMALLINT,
    ft_away SMALLINT,
    ht_home SMALLINT,
    ht_away SMALLINT,
    -- Marcador final incluido tiempo extra (sin penales) y penales, sólo informativos.
    goals_home SMALLINT,
    goals_away SMALLINT,
    pen_home SMALLINT,
    pen_away SMALLINT,
    referee TEXT,
    venue TEXT,
    venue_city TEXT,
    raw_payload JSONB NOT NULL CHECK (jsonb_typeof(raw_payload) = 'object'),
    fetched_at TIMESTAMPTZ NOT NULL,
    -- Última descarga del detalle (estadísticas, eventos, alineaciones y jugadores).
    details_fetched_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fixtures_distinct_teams CHECK (home_team_id <> away_team_id)
);

CREATE INDEX fixtures_date_idx ON futbol.fixtures (match_date);
CREATE INDEX fixtures_league_season_idx ON futbol.fixtures (league_id, season);
CREATE INDEX fixtures_home_team_idx ON futbol.fixtures (home_team_id, starts_at);
CREATE INDEX fixtures_away_team_idx ON futbol.fixtures (away_team_id, starts_at);

-- Estadísticas de equipo por partido (/fixtures?ids=...). `xg` = expected_goals del proveedor.
CREATE TABLE futbol.fixture_team_stats (
    fixture_id INTEGER NOT NULL REFERENCES futbol.fixtures (id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES futbol.teams (id),
    shots_on SMALLINT,
    shots_total SMALLINT,
    corners SMALLINT,
    fouls SMALLINT,
    offsides SMALLINT,
    yellow SMALLINT,
    red SMALLINT,
    saves SMALLINT,
    possession SMALLINT,
    xg NUMERIC(5, 2),
    raw_payload JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (fixture_id, team_id)
);

-- Una fila por jugador convocado y partido. minutes NULL o 0 = no jugó (suplente sin entrar).
-- En la API los conteos vienen NULL cuando son 0; aquí se guardan como 0 si el jugador jugó.
CREATE TABLE futbol.fixture_player_stats (
    fixture_id INTEGER NOT NULL REFERENCES futbol.fixtures (id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES futbol.players (id),
    team_id INTEGER NOT NULL REFERENCES futbol.teams (id),
    minutes SMALLINT,
    position TEXT,
    is_substitute BOOLEAN,
    rating NUMERIC(4, 2),
    goals SMALLINT,
    assists SMALLINT,
    shots_total SMALLINT,
    shots_on SMALLINT,
    yellow SMALLINT,
    red SMALLINT,
    fouls_committed SMALLINT,
    key_passes SMALLINT,
    penalty_scored SMALLINT,
    penalty_missed SMALLINT,
    raw_payload JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (fixture_id, player_id)
);

CREATE INDEX fixture_player_stats_player_idx ON futbol.fixture_player_stats (player_id);
CREATE INDEX fixture_player_stats_team_idx ON futbol.fixture_player_stats (team_id, fixture_id);

-- Goles, tarjetas, cambios y VAR.
CREATE TABLE futbol.fixture_events (
    fixture_id INTEGER NOT NULL REFERENCES futbol.fixtures (id) ON DELETE CASCADE,
    seq SMALLINT NOT NULL,
    minute SMALLINT,
    extra SMALLINT,
    team_id INTEGER,
    player_id INTEGER,
    player_name TEXT,
    assist_id INTEGER,
    type TEXT NOT NULL,
    detail TEXT,
    comments TEXT,
    PRIMARY KEY (fixture_id, seq)
);

-- Alineaciones (disponibles 20–40 min antes del partido cuando la liga tiene cobertura).
CREATE TABLE futbol.fixture_lineups (
    fixture_id INTEGER NOT NULL REFERENCES futbol.fixtures (id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES futbol.teams (id),
    player_id INTEGER NOT NULL REFERENCES futbol.players (id),
    is_starter BOOLEAN NOT NULL,
    position TEXT,
    grid TEXT,
    formation TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (fixture_id, player_id)
);

-- Bajas por partido según /injuries: 'out' = "Missing Fixture", 'questionable' = "Questionable".
CREATE TABLE futbol.injuries (
    fixture_id INTEGER NOT NULL REFERENCES futbol.fixtures (id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES futbol.players (id),
    team_id INTEGER NOT NULL REFERENCES futbol.teams (id),
    status TEXT NOT NULL CHECK (status IN ('out', 'questionable')),
    reason TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (fixture_id, player_id)
);

-- Correcciones manuales desde la interfaz: mandan sobre la API.
CREATE TABLE futbol.availability_overrides (
    fixture_id INTEGER NOT NULL REFERENCES futbol.fixtures (id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES futbol.players (id),
    status TEXT NOT NULL CHECK (status IN ('out', 'available')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fixture_id, player_id)
);

-- Historial de momios sin sobrescribir: una fila por cada valor distinto observado.
-- Si en la siguiente recolección el momio no cambió, sólo se actualiza last_seen_at;
-- si cambió, se inserta una fila nueva. Así se sabe qué momio existía antes de cada partido.
CREATE TABLE futbol.odds_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fixture_id INTEGER NOT NULL REFERENCES futbol.fixtures (id),
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
        UNIQUE (fixture_id, bookmaker_id, bet_id, selection, first_seen_at)
);

CREATE INDEX odds_history_fixture_idx ON futbol.odds_history (fixture_id, bet_id);

-- Proyección del modelo por partido (misma regla que picks: se congela al empezar el partido).
-- El ajuste de goles por bajas se quitó en V3: en el backtest empeoraba el pronóstico.
CREATE TABLE futbol.fixture_projections (
    fixture_id INTEGER PRIMARY KEY REFERENCES futbol.fixtures (id),
    home_goals NUMERIC(5, 2) NOT NULL,            -- goles esperados (lambda) de cada lado
    away_goals NUMERIC(5, 2) NOT NULL,
    p_home NUMERIC(6, 4) NOT NULL,
    p_draw NUMERIC(6, 4) NOT NULL,
    p_away NUMERIC(6, 4) NOT NULL,
    p_over25 NUMERIC(6, 4) NOT NULL,
    p_btts NUMERIC(6, 4) NOT NULL,
    top_scores JSONB NOT NULL,                    -- [["1-0", 0.12], ...] marcadores más probables
    home_cards NUMERIC(5, 2),                     -- tarjetas esperadas de cada lado
    away_cards NUMERIC(5, 2),
    lineups BOOLEAN NOT NULL DEFAULT false,        -- ¿se usaron alineaciones confirmadas?
    model_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL
);

-- Partidos con su estado resumido. AET/PEN también terminaron (las apuestas van a 90 minutos).
CREATE VIEW futbol.v_fixtures AS
SELECT
    f.*,
    l.name AS league_name,
    f.status IN ('FT', 'AET', 'PEN') AS is_finished
FROM futbol.fixtures f
JOIN futbol.leagues l ON l.id = f.league_id;

-- Último momio conocido de cada selección.
CREATE VIEW futbol.v_odds_latest AS
SELECT DISTINCT ON (fixture_id, bookmaker_id, bet_id, selection) *
FROM futbol.odds_history
ORDER BY fixture_id, bookmaker_id, bet_id, selection, last_seen_at DESC;

-- Estado efectivo por jugador y partido: corrección manual si existe; si no, la API.
CREATE VIEW futbol.v_player_availability AS
SELECT
    COALESCE(m.fixture_id, i.fixture_id) AS fixture_id,
    COALESCE(m.player_id, i.player_id) AS player_id,
    i.team_id,
    COALESCE(m.status, i.status) AS status,
    i.status AS report_status,
    i.reason,
    i.fetched_at AS report_at,
    m.status IS NOT NULL AS manual
FROM futbol.injuries i
FULL OUTER JOIN futbol.availability_overrides m ON m.fixture_id = i.fixture_id AND m.player_id = i.player_id;
