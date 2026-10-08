-- Momio de publicación de cada pierna, para medir el CLV (valor contra el momio de cierre).
--
-- `odd`, `p_model` y `p_market` se actualizan en cada corrida hasta que empieza el partido: al empezar
-- quedan con los últimos previos al partido (el cierre). Estas columnas guardan cómo estaba la pierna la
-- primera vez que se registró con momio de BOOKMAKER y no se vuelven a escribir. Las piernas registradas
-- antes de esta migración (y las importadas de los proyectos anteriores) no las tienen.
ALTER TABLE core.picks
    ADD COLUMN first_odd NUMERIC(10, 3) CHECK (first_odd > 1),
    ADD COLUMN first_p_model NUMERIC(6, 4) CHECK (first_p_model > 0 AND first_p_model < 1),
    ADD COLUMN first_p_market NUMERIC(6, 4) CHECK (first_p_market BETWEEN 0 AND 1),
    ADD COLUMN first_priced_at TIMESTAMPTZ,
    -- Momio, probabilidad del modelo y hora van juntos; la probabilidad del mercado puede faltar (mercado
    -- sin todos sus lados cotizados).
    ADD CONSTRAINT picks_first_price_complete CHECK (
        (first_odd IS NULL) = (first_priced_at IS NULL)
        AND (first_odd IS NULL) = (first_p_model IS NULL)
        AND (first_p_market IS NULL OR first_odd IS NOT NULL)
    ),
    ADD CONSTRAINT picks_first_price_before_last CHECK (first_priced_at <= evaluated_at);
