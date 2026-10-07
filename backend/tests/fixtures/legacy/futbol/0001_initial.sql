-- Esquema inicial. Fuente única: API-Football v3 (15 competiciones, ver app/config.py).
-- Los IDs de ligas, equipos, jugadores y partidos son los del proveedor, estables entre
-- temporadas según su documentación.

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

-- Competiciones del proyecto y su temporada en curso (la API usa el año de inicio: 2026 = 2026-27).
CREATE TABLE leagues (
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

CREATE TABLE teams (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    logo TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Nombre completo ("Zion Suzuki") de las estadísticas por jugador; las alineaciones traen
-- la forma corta ("Z. Suzuki") y sólo se usan si el jugador todavía no existe.
CREATE TABLE players (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    photo TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE fixtures (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    league_id INTEGER NOT NULL REFERENCES leagues (id),
    season SMALLINT NOT NULL,
    round TEXT,
    starts_at TIMESTAMPTZ NOT NULL,
    -- Fecha del partido en la zona horaria local (centro de México por defecto).
    match_date DATE NOT NULL,
    status TEXT NOT NULL,
    elapsed SMALLINT,
    home_team_id INTEGER NOT NULL REFERENCES teams (id),
    away_team_id INTEGER NOT NULL REFERENCES teams (id),
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

CREATE INDEX fixtures_date_idx ON fixtures (match_date);
CREATE INDEX fixtures_league_season_idx ON fixtures (league_id, season);
CREATE INDEX fixtures_home_team_idx ON fixtures (home_team_id, starts_at);
CREATE INDEX fixtures_away_team_idx ON fixtures (away_team_id, starts_at);

-- Estadísticas de equipo por partido (/fixtures?ids=...). `xg` = expected_goals del proveedor.
CREATE TABLE fixture_team_stats (
    fixture_id INTEGER NOT NULL REFERENCES fixtures (id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams (id),
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
CREATE TABLE fixture_player_stats (
    fixture_id INTEGER NOT NULL REFERENCES fixtures (id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players (id),
    team_id INTEGER NOT NULL REFERENCES teams (id),
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

CREATE INDEX fixture_player_stats_player_idx ON fixture_player_stats (player_id);
CREATE INDEX fixture_player_stats_team_idx ON fixture_player_stats (team_id, fixture_id);

-- Goles, tarjetas, cambios y VAR.
CREATE TABLE fixture_events (
    fixture_id INTEGER NOT NULL REFERENCES fixtures (id) ON DELETE CASCADE,
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
CREATE TABLE fixture_lineups (
    fixture_id INTEGER NOT NULL REFERENCES fixtures (id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams (id),
    player_id INTEGER NOT NULL REFERENCES players (id),
    is_starter BOOLEAN NOT NULL,
    position TEXT,
    grid TEXT,
    formation TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (fixture_id, player_id)
);

-- Bajas por partido según /injuries: 'out' = "Missing Fixture", 'questionable' = "Questionable".
CREATE TABLE injuries (
    fixture_id INTEGER NOT NULL REFERENCES fixtures (id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players (id),
    team_id INTEGER NOT NULL REFERENCES teams (id),
    status TEXT NOT NULL CHECK (status IN ('out', 'questionable')),
    reason TEXT,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (fixture_id, player_id)
);

-- Correcciones manuales desde la interfaz: mandan sobre la API.
CREATE TABLE availability_overrides (
    fixture_id INTEGER NOT NULL REFERENCES fixtures (id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players (id),
    status TEXT NOT NULL CHECK (status IN ('out', 'available')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fixture_id, player_id)
);

-- Historial de momios sin sobrescribir: una fila por cada valor distinto observado.
-- Si en la siguiente recolección el momio no cambió, sólo se actualiza last_seen_at;
-- si cambió, se inserta una fila nueva. Así se sabe qué momio existía antes de cada partido.
CREATE TABLE odds_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fixture_id INTEGER NOT NULL REFERENCES fixtures (id),
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
        UNIQUE (fixture_id, bookmaker_id, bet_id, selection, first_seen_at)
);

CREATE INDEX odds_history_fixture_idx ON odds_history (fixture_id, bet_id);

-- Partidos con su estado resumido. AET/PEN también terminaron (las apuestas van a 90 minutos).
CREATE VIEW v_fixtures AS
SELECT
    f.*,
    l.name AS league_name,
    f.status IN ('FT', 'AET', 'PEN') AS is_finished
FROM fixtures f
JOIN leagues l ON l.id = f.league_id;

-- Último momio conocido de cada selección.
CREATE VIEW v_odds_latest AS
SELECT DISTINCT ON (fixture_id, bookmaker_id, bet_id, selection) *
FROM odds_history
ORDER BY fixture_id, bookmaker_id, bet_id, selection, last_seen_at DESC;

-- Estado efectivo por jugador y partido: corrección manual si existe; si no, la API.
CREATE VIEW v_player_availability AS
SELECT
    COALESCE(m.fixture_id, i.fixture_id) AS fixture_id,
    COALESCE(m.player_id, i.player_id) AS player_id,
    i.team_id,
    COALESCE(m.status, i.status) AS status,
    i.status AS report_status,
    i.reason,
    i.fetched_at AS report_at,
    m.status IS NOT NULL AS manual
FROM injuries i
FULL OUTER JOIN availability_overrides m ON m.fixture_id = i.fixture_id AND m.player_id = i.player_id;
