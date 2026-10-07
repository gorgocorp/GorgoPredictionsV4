Copias textuales de las migraciones de los proyectos anteriores, que definen el esquema de origen de
`import-legacy` en `tests/integration/test_legacy_import.py`:

- `nba/`: GorgoNBAParlays @ `6d16326` (`backend/migrations/0001`–`0009`)
- `futbol/`: GorgoPredictionsV3 @ `0791500` (`backend/migrations/0001`–`0004`)

No se editan: si un proyecto anterior cambiara su esquema antes del corte, se vuelven a copiar.
