-- Parlays destacados (app/core/featured.py): el de la semana (se publica el lunes con partidos de lunes a domingo)
-- y el de fin de semana (se publica el jueves con partidos de viernes a domingo), de 2 a 5 piernas.
--
-- Viven en core.parlays con su propio modo y `day` = primer día de su ventana, así que se liquidan, se miden y salen
-- en el historial como los demás. A diferencia de los del día, se arman una sola vez y no se reemplazan.
ALTER TABLE core.parlays DROP CONSTRAINT parlays_mode_check;
ALTER TABLE core.parlays ADD CONSTRAINT parlays_mode_check CHECK (mode IN ('prob', 'ev', 'week', 'weekend'));

-- Probabilidad sin comisión del mercado de la pierna al registrar el parlay. Los destacados exigen que el modelo y
-- el mercado coincidan y prometen la menor de las dos; los del día no la guardan (NULL).
ALTER TABLE core.parlay_legs ADD COLUMN p_market NUMERIC(6, 4) CHECK (p_market > 0 AND p_market < 1);
