-- GorgoPredictions V4: NBA y fútbol en una sola base.
--
-- Esquemas:
--   nba     tablas de NBA (API-Basketball) tal como estaban en GorgoNBAParlays
--   futbol  tablas de fútbol (API-Football) tal como estaban en GorgoPredictionsV3
--   core    lo que cruza deportes: ingestas, partidos registrados, picks, parlays y apuestas
--
-- Los IDs de equipos, jugadores y partidos de cada deporte son los de su proveedor, y los dos
-- proveedores usan espacios distintos (el equipo 132 existe en ambos y no es el mismo). Por eso
-- core.matches da a cada partido una identidad propia y conserva (sport, external_id).

CREATE SCHEMA core;
CREATE SCHEMA nba;
CREATE SCHEMA futbol;

-- Registro de cada ejecución de ingesta.
CREATE TABLE core.ingest_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sport TEXT NOT NULL CHECK (sport IN ('nba', 'futbol')),
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

CREATE INDEX ingest_runs_job_idx ON core.ingest_runs (sport, job, started_at DESC);

-- Partidos de todos los deportes, con lo que necesita la parte común: congelar picks al empezar,
-- liquidar y mostrar historial y apuestas. Lo mantiene la ingesta de cada deporte desde sus tablas
-- (nba.games, futbol.fixtures). Un proveedor por deporte: si un deporte tuviera dos, el proveedor
-- se agrega a la llave.
CREATE TABLE core.matches (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sport TEXT NOT NULL CHECK (sport IN ('nba', 'futbol')),
    external_id INTEGER NOT NULL CHECK (external_id > 0),   -- nba.games.id / futbol.fixtures.id
    competition_id INTEGER NOT NULL,                         -- liga del proveedor (NBA = 12)
    competition TEXT NOT NULL CHECK (length(btrim(competition)) > 0),
    starts_at TIMESTAMPTZ NOT NULL,
    local_date DATE NOT NULL,                                -- día del partido en LOCAL_TIMEZONE
    status TEXT NOT NULL,                                    -- estado del proveedor (NS, FT, AOT, PEN, PST…)
    state TEXT NOT NULL CHECK (state IN ('scheduled', 'live', 'finished', 'cancelled')),
    home_name TEXT NOT NULL,
    away_name TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT matches_external_unique UNIQUE (sport, external_id),
    -- Para la llave foránea compuesta de picks: el deporte de una pierna es el de su partido.
    CONSTRAINT matches_id_sport_unique UNIQUE (id, sport)
);

CREATE INDEX matches_date_idx ON core.matches (local_date, sport);

-- Registro de picks del modelo y su liquidación.
--
-- Una fila por pierna evaluada y partido. Cada corrida actualiza la fila mientras el partido no haya
-- empezado; al empezar queda congelada con la última probabilidad y el último momio previos al partido
-- (lo que había disponible al decidir la apuesta).
CREATE TABLE core.picks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sport TEXT NOT NULL,
    match_id BIGINT NOT NULL,
    market TEXT NOT NULL,
    side TEXT NOT NULL,
    line NUMERIC(6, 1),
    team TEXT CHECK (team IN ('home', 'away')),
    stat TEXT,
    -- ID del jugador en el proveedor del deporte (nba.players / futbol.players). No puede tener llave
    -- foránea a dos tablas: lo garantiza el motor de cada deporte y lo verifica una prueba de integración.
    player_id INTEGER,
    description TEXT NOT NULL,
    p_model NUMERIC(6, 4) NOT NULL CHECK (p_model > 0 AND p_model < 1),
    odd NUMERIC(10, 3) CHECK (odd > 1),
    bookmaker TEXT,
    p_market NUMERIC(6, 4),
    -- Momios de las casas de PRICE_BOOKMAKERS: {"Bet365": 1.83, "1xBet": 1.87}. `odd` / `bookmaker` son
    -- los de BOOKMAKER, con los que el sistema registra y mide sus parlays.
    book_odds JSONB,
    model_version TEXT NOT NULL,
    first_evaluated_at TIMESTAMPTZ NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL,
    result TEXT CHECK (result IN ('won', 'lost', 'void')),
    settled_at TIMESTAMPTZ,
    -- Props: veces que lo logró en sus últimos 10 y 25 partidos jugados.
    hits_10 SMALLINT,
    games_10 SMALLINT,
    hits_25 SMALLINT,
    games_25 SMALLINT,
    -- Props: estado del jugador (NBA: designación del reporte de lesiones; fútbol: 'questionable',
    -- 'starter' o 'bench' con alineación publicada).
    player_status TEXT,
    CONSTRAINT picks_match_fk FOREIGN KEY (match_id, sport) REFERENCES core.matches (id, sport),
    CONSTRAINT picks_market_valid CHECK (
        (sport = 'nba'
            AND market IN ('ml', 'spread', 'total', 'team_total', 'player')
            AND side IN ('home', 'away', 'over', 'under'))
        OR (sport = 'futbol'
            AND market IN ('1x2', 'dc', 'total', 'team_total', 'btts', 'score', 'cards', 'team_cards', 'player')
            AND (side IN ('home', 'draw', 'away', '1x', '12', 'x2', 'over', 'under', 'yes', 'no')
                 OR (market = 'score' AND side ~ '^\d+-\d+$')))
    ),
    CONSTRAINT picks_leg_unique UNIQUE NULLS NOT DISTINCT (match_id, market, side, line, team, stat, player_id)
);

CREATE INDEX picks_unsettled_idx ON core.picks (match_id) WHERE result IS NULL;

-- Parlays sugeridos por deporte, día, modo y número de piernas. Se reemplazan en cada corrida hasta
-- que empieza el partido de alguna de sus piernas.
CREATE TABLE core.parlays (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sport TEXT NOT NULL CHECK (sport IN ('nba', 'futbol')),
    day DATE NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('prob', 'ev')),
    n_legs SMALLINT NOT NULL CHECK (n_legs BETWEEN 2 AND 8),
    probability NUMERIC(8, 6) NOT NULL,
    odd NUMERIC(12, 3),
    bookmaker TEXT,
    model_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL,
    result TEXT CHECK (result IN ('won', 'lost', 'void')),
    -- Pago real con las piernas anuladas fuera (momio 1); NULL si alguna pierna no tenía momio.
    settled_odd NUMERIC(12, 3),
    settled_at TIMESTAMPTZ,
    CONSTRAINT parlays_slot_unique UNIQUE (sport, day, mode, n_legs)
);

-- Cada pierna guarda una copia de lo que se predijo al registrar el parlay: el parlay se congela al
-- empezar su primer partido, pero las piernas de partidos posteriores siguen cambiando en picks.
CREATE TABLE core.parlay_legs (
    parlay_id BIGINT NOT NULL REFERENCES core.parlays (id) ON DELETE CASCADE,
    pick_id BIGINT NOT NULL REFERENCES core.picks (id),
    position SMALLINT NOT NULL,
    description TEXT NOT NULL,
    p_model NUMERIC(6, 4) NOT NULL,
    odd NUMERIC(10, 3),
    PRIMARY KEY (parlay_id, pick_id)
);

-- Apuestas reales del usuario ("Mis apuestas"), con los momios de su casa (p. ej. Caliente, que no
-- está en la API). Se registran sólo antes del primer partido para que el registro sea honesto, y se
-- liquidan solas con los resultados de sus piernas. Un boleto puede mezclar NBA y fútbol.
CREATE TABLE core.user_bets (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bookmaker TEXT NOT NULL CHECK (length(btrim(bookmaker)) > 0),
    stake NUMERIC(12, 2) NOT NULL CHECK (stake > 0),
    odd NUMERIC(10, 3) NOT NULL CHECK (odd > 1),            -- momio total del boleto (decimal)
    model_probability NUMERIC(8, 6) NOT NULL CHECK (model_probability > 0 AND model_probability < 1),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    first_start TIMESTAMPTZ NOT NULL,                       -- inicio del primer partido del boleto
    result TEXT CHECK (result IN ('won', 'lost', 'void')),
    settled_odd NUMERIC(10, 3),                             -- momio final sin piernas anuladas
    payout NUMERIC(12, 2),                                  -- lo que regresa la casa (0 si se pierde)
    settled_at TIMESTAMPTZ,
    CONSTRAINT user_bets_before_start CHECK (created_at < first_start)
);

CREATE TABLE core.user_bet_legs (
    bet_id BIGINT NOT NULL REFERENCES core.user_bets (id) ON DELETE CASCADE,
    position SMALLINT NOT NULL,
    pick_id BIGINT NOT NULL REFERENCES core.picks (id),
    -- Copia de lo que dijo el modelo al registrar (la pierna puede seguir cambiando en picks).
    description TEXT NOT NULL,
    p_model NUMERIC(6, 4) NOT NULL,
    odd NUMERIC(10, 3) NOT NULL CHECK (odd > 1),            -- momio de la casa para la pierna
    PRIMARY KEY (bet_id, position),
    UNIQUE (bet_id, pick_id)
);

CREATE INDEX user_bets_unsettled_idx ON core.user_bets (id) WHERE result IS NULL;
