-- Parlay con valor (app/core/value.py), en prueba y sólo para admin: piernas en las que el momio de la casa paga más que
-- el justo del modelo y del mercado.
--
-- Vive en core.parlays con su propio modo, así que se liquida y sale en el historial y el rendimiento como los demás.
-- Como los destacados, se publica una sola vez por día y deporte y no se reemplaza; cada pierna guarda el mercado con
-- el que se publicó (core.parlay_legs.p_market).
ALTER TABLE core.parlays DROP CONSTRAINT parlays_mode_check;
ALTER TABLE core.parlays ADD CONSTRAINT parlays_mode_check CHECK (mode IN ('prob', 'ev', 'week', 'weekend', 'value'));
