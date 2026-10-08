-- Probabilidad sin comisión de Pinnacle de cada pierna: la referencia contra la que se mide el CLV.
--
-- `p_market` usa Pinnacle si cotiza el mercado completo y, si no, la mediana de las casas que sí. Cuando la única
-- casa con los dos lados pone uno en el mínimo (1.01), su devig infla mucho la probabilidad de los momios altos
-- (p. ej. 6.7% para "más de 4.5 goles" de un equipo que Bet365 paga a 51), y el CLV de esas piernas sale
-- positivo aunque el mercado no se mueva. Por eso el CLV se mide sólo contra Pinnacle.
--
-- `p_sharp` se actualiza en cada corrida, como `p_market`: al empezar el partido queda la del cierre.
-- `first_p_sharp` es la de la publicación (se guarda junto con `first_odd` y no se vuelve a escribir).
-- NULL = Pinnacle no cotizaba el mercado completo. Las piernas publicadas antes de esta migración no tienen
-- `first_p_sharp`.
ALTER TABLE core.picks
    ADD COLUMN p_sharp NUMERIC(6, 4) CHECK (p_sharp BETWEEN 0 AND 1),
    ADD COLUMN first_p_sharp NUMERIC(6, 4) CHECK (first_p_sharp BETWEEN 0 AND 1),
    ADD CONSTRAINT picks_first_sharp_needs_first_price CHECK (first_p_sharp IS NULL OR first_odd IS NOT NULL);
