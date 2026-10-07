-- Registro de picks del modelo y su liquidación.
--
-- Una fila por pierna evaluada y partido. Cada corrida actualiza la fila mientras el
-- partido no haya empezado; al empezar queda congelada con la última probabilidad y el
-- último momio previos al partido (lo que había disponible al decidir la apuesta).

CREATE TABLE picks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games (id),
    market TEXT NOT NULL CHECK (market IN ('ml', 'spread', 'total', 'team_total', 'player')),
    side TEXT NOT NULL CHECK (side IN ('home', 'away', 'over', 'under')),
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
    CONSTRAINT picks_leg_unique UNIQUE NULLS NOT DISTINCT (game_id, market, side, line, team, stat, player_id)
);

CREATE INDEX picks_unsettled_idx ON picks (game_id) WHERE result IS NULL;

-- Parlays sugeridos por día, modo y número de piernas. Se reemplazan en cada corrida
-- hasta que empieza el partido de alguna de sus piernas.
CREATE TABLE parlays (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_date DATE NOT NULL,
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
    CONSTRAINT parlays_slot_unique UNIQUE (game_date, mode, n_legs)
);

CREATE TABLE parlay_legs (
    parlay_id BIGINT NOT NULL REFERENCES parlays (id) ON DELETE CASCADE,
    pick_id BIGINT NOT NULL REFERENCES picks (id),
    position SMALLINT NOT NULL,
    PRIMARY KEY (parlay_id, pick_id)
);
