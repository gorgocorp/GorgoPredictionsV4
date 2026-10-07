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
