-- Proyección del modelo por partido (misma regla que picks: se congela al empezar el partido)
-- y tasas de acierto simples de cada prop para mostrarlas junto a la probabilidad del modelo.

CREATE TABLE game_projections (
    game_id INTEGER PRIMARY KEY REFERENCES games (id),
    home_points NUMERIC(6, 2) NOT NULL,
    away_points NUMERIC(6, 2) NOT NULL,
    p_home_win NUMERIC(6, 4) NOT NULL CHECK (p_home_win > 0 AND p_home_win < 1),
    model_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL
);

-- Aciertos de "N o más" en los últimos 10 y 25 partidos jugados (sólo props "más de").
ALTER TABLE picks
    ADD COLUMN hits_10 SMALLINT,
    ADD COLUMN games_10 SMALLINT,
    ADD COLUMN hits_25 SMALLINT,
    ADD COLUMN games_25 SMALLINT;
