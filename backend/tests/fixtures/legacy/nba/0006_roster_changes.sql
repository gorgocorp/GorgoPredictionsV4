-- Ajuste por cambios de plantel entre temporadas (pts por partido netos perdidos, ya ponderados
-- por el peso de la temporada anterior; negativo = el equipo ganó producción) y su detalle.
ALTER TABLE game_projections
    ADD COLUMN home_roster_pts NUMERIC(6, 2) NOT NULL DEFAULT 0,
    ADD COLUMN away_roster_pts NUMERIC(6, 2) NOT NULL DEFAULT 0,
    ADD COLUMN roster_detail JSONB;
