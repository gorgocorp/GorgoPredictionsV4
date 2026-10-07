-- Registro de picks del modelo, parlays sugeridos, proyecciones y apuestas del usuario.
--
-- Una fila de `picks` por pierna evaluada y partido. Cada corrida actualiza la fila mientras el
-- partido no haya empezado; al empezar queda congelada con la última probabilidad y el último
-- momio previos al partido (lo que había disponible al decidir la apuesta).

CREATE TABLE picks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fixture_id INTEGER NOT NULL REFERENCES fixtures (id),
    market TEXT NOT NULL
        CHECK (market IN ('1x2', 'dc', 'total', 'team_total', 'btts', 'score', 'cards', 'team_cards', 'player')),
    side TEXT NOT NULL,
    line NUMERIC(6, 1),
    team TEXT CHECK (team IN ('home', 'away')),
    stat TEXT,
    player_id INTEGER REFERENCES players (id),
    description TEXT NOT NULL,
    p_model NUMERIC(6, 4) NOT NULL CHECK (p_model > 0 AND p_model < 1),
    odd NUMERIC(10, 3) CHECK (odd > 1),
    bookmaker TEXT,
    p_market NUMERIC(6, 4),
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
    -- Props: 'questionable' si la API lo marca en duda; 'starter'/'bench' con alineación publicada.
    player_status TEXT,
    CONSTRAINT picks_side_valid CHECK (
        side IN ('home', 'draw', 'away', '1x', '12', 'x2', 'over', 'under', 'yes', 'no')
        OR (market = 'score' AND side ~ '^\d+-\d+$')
    ),
    CONSTRAINT picks_leg_unique UNIQUE NULLS NOT DISTINCT (fixture_id, market, side, line, team, stat, player_id)
);

CREATE INDEX picks_unsettled_idx ON picks (fixture_id) WHERE result IS NULL;

-- Parlays sugeridos por día, modo y número de piernas. Se reemplazan en cada corrida
-- hasta que empieza el partido de alguna de sus piernas.
CREATE TABLE parlays (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_date DATE NOT NULL,
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
    CONSTRAINT parlays_slot_unique UNIQUE (match_date, mode, n_legs)
);

-- Cada pierna guarda una copia de lo que se predijo al registrar el parlay: el parlay se congela
-- al empezar su primer partido, pero las piernas de partidos posteriores siguen cambiando en picks.
CREATE TABLE parlay_legs (
    parlay_id BIGINT NOT NULL REFERENCES parlays (id) ON DELETE CASCADE,
    pick_id BIGINT NOT NULL REFERENCES picks (id),
    position SMALLINT NOT NULL,
    description TEXT NOT NULL,
    p_model NUMERIC(6, 4) NOT NULL,
    odd NUMERIC(10, 3),
    PRIMARY KEY (parlay_id, pick_id)
);

-- Proyección del modelo por partido (misma regla que picks: se congela al empezar el partido).
CREATE TABLE fixture_projections (
    fixture_id INTEGER PRIMARY KEY REFERENCES fixtures (id),
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
    home_missing NUMERIC(5, 3) NOT NULL DEFAULT 0, -- fracción del ataque que falta por bajas
    away_missing NUMERIC(5, 3) NOT NULL DEFAULT 0,
    lineups BOOLEAN NOT NULL DEFAULT false,        -- ¿se usaron alineaciones confirmadas?
    model_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL
);

-- Apuestas reales del usuario ("Mis apuestas"), con los momios de su casa (p. ej. Caliente,
-- que no está en la API). Se registran sólo antes del primer partido para que el registro sea
-- honesto, y se liquidan solas con los resultados de sus piernas.
CREATE TABLE user_bets (
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

CREATE TABLE user_bet_legs (
    bet_id BIGINT NOT NULL REFERENCES user_bets (id) ON DELETE CASCADE,
    position SMALLINT NOT NULL,
    pick_id BIGINT NOT NULL REFERENCES picks (id),
    -- Copia de lo que dijo el modelo al registrar (la pierna puede seguir cambiando en picks).
    description TEXT NOT NULL,
    p_model NUMERIC(6, 4) NOT NULL,
    odd NUMERIC(10, 3) NOT NULL CHECK (odd > 1),            -- momio de la casa para la pierna
    PRIMARY KEY (bet_id, position),
    UNIQUE (bet_id, pick_id)
);

CREATE INDEX user_bets_unsettled_idx ON user_bets (id) WHERE result IS NULL;
