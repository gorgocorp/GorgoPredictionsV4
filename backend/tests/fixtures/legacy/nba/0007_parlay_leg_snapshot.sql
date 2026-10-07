-- Copia de cada pierna en el momento en que se registra el parlay.
--
-- Un parlay se congela cuando empieza su primer partido, pero las piernas de partidos
-- posteriores siguen actualizándose en `picks` hasta que empieza cada uno. Para que el
-- historial muestre exactamente lo que se predijo (y el pago se calcule con esos momios),
-- cada pierna guarda su descripción, probabilidad y momio al registrarse el parlay.
ALTER TABLE parlay_legs
    ADD COLUMN description TEXT,
    ADD COLUMN p_model NUMERIC(6, 4),
    ADD COLUMN odd NUMERIC(10, 3);

UPDATE parlay_legs l
SET description = k.description, p_model = k.p_model, odd = k.odd
FROM picks k
WHERE k.id = l.pick_id;

ALTER TABLE parlay_legs
    ALTER COLUMN description SET NOT NULL,
    ALTER COLUMN p_model SET NOT NULL;
