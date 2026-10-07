-- Disponibilidad de jugadores: reporte oficial de lesiones de la NBA + correcciones manuales.

-- Cada reporte oficial descargado (la NBA publica uno cada 15 minutos en temporada).
CREATE TABLE injury_reports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_at TIMESTAMPTZ NOT NULL UNIQUE,
    url TEXT NOT NULL,
    entries INTEGER NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL
);

-- Equipos incluidos en cada reporte y si ya entregaron su lista ("NOT YET SUBMITTED" = no).
CREATE TABLE injury_report_teams (
    report_id BIGINT NOT NULL REFERENCES injury_reports (id) ON DELETE CASCADE,
    game_date DATE NOT NULL,
    team_id INTEGER NOT NULL REFERENCES teams (id),
    submitted BOOLEAN NOT NULL,
    PRIMARY KEY (report_id, game_date, team_id)
);

-- Jugadores con designación en un reporte. Los que no aparecen están disponibles.
CREATE TABLE injury_entries (
    report_id BIGINT NOT NULL REFERENCES injury_reports (id) ON DELETE CASCADE,
    game_date DATE NOT NULL,
    team_id INTEGER NOT NULL REFERENCES teams (id),
    player_name TEXT NOT NULL,
    player_id INTEGER REFERENCES players (id),
    status TEXT NOT NULL CHECK (status IN ('out', 'doubtful', 'questionable', 'probable', 'available')),
    reason TEXT,
    PRIMARY KEY (report_id, game_date, team_id, player_name)
);

-- Correcciones manuales desde la interfaz: mandan sobre el reporte.
CREATE TABLE availability_overrides (
    game_date DATE NOT NULL,
    player_id INTEGER NOT NULL REFERENCES players (id),
    status TEXT NOT NULL CHECK (status IN ('out', 'available')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (game_date, player_id)
);

-- Último reporte que incluye cada fecha de partido.
CREATE VIEW v_latest_injury_report AS
SELECT DISTINCT ON (t.game_date) t.game_date, r.id AS report_id, r.report_at
FROM injury_report_teams t
JOIN injury_reports r ON r.id = t.report_id
ORDER BY t.game_date, r.report_at DESC;

-- Estado efectivo por jugador y fecha: corrección manual si existe; si no, el último reporte.
CREATE VIEW v_player_availability AS
WITH report AS (
    SELECT e.game_date, e.player_id, e.team_id, e.status, e.reason, l.report_at
    FROM injury_entries e
    JOIN v_latest_injury_report l ON l.report_id = e.report_id AND l.game_date = e.game_date
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
FULL OUTER JOIN availability_overrides m ON m.game_date = r.game_date AND m.player_id = r.player_id;

-- Estado del jugador en cada pick de prop (para marcar "en duda" en la interfaz).
ALTER TABLE picks ADD COLUMN player_status TEXT;

-- Puntos por partido que se esperan perdidos por bajas en cada equipo (ya aplicados a la proyección).
ALTER TABLE game_projections
    ADD COLUMN home_missing_pts NUMERIC(6, 2) NOT NULL DEFAULT 0,
    ADD COLUMN away_missing_pts NUMERIC(6, 2) NOT NULL DEFAULT 0;
