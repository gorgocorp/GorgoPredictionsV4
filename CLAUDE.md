# GorgoPredictions V4

Plataforma única de picks y parlays de **NBA** (API-Basketball) y **fútbol** (API-Football): une
GorgoNBAParlays y GorgoPredictionsV3. Plan, fases y decisiones: `docs/PLAN_UNION.md`.

## Reglas

- `../GorgoNBAParlays` y `../GorgoPredictionsV3` son **de sólo lectura**: no se editan sus archivos ni sus bases.
  Desde el corte (6-oct-2026) están apagados como archivo y V4 es el sistema oficial: no se prenden (su scheduler
  duplicaría la cuota y escribiría evidencia que V4 no ve). Prender sólo su base para leerla lo decide el usuario.
- Persistencia: antes de tocar SQL o migraciones, leer `docs/database/psycopg.md`. Sólo migraciones versionadas en
  `backend/migrations/` (nunca `CREATE TABLE` desde un job), parámetros para valores y `psycopg.sql.Identifier` para
  identificadores dinámicos, transacciones cortas, restricciones reales en la base.
- Esquemas: `nba` y `futbol` (tablas de cada deporte con los IDs de su proveedor, que son espacios distintos) y `core`
  (partidos registrados, picks, parlays, apuestas, ingestas). Toda consulta lleva el esquema explícito. Lo que cruza
  deportes se refiere a partidos por `core.matches.id`, nunca por el ID del proveedor solo.
- APIs: no inventar campos, IDs ni endpoints; consultar `docs/apis/*_campos_verificados.md` y los inventarios.
- Estructura: lo común vive una sola vez en `backend/app/core/`; lo de cada deporte en `backend/app/sports/<deporte>/`
  y se conecta con el contrato `app/core/sport.py`. No duplicar en un deporte lo que ya está en `core`.
- Modelos: nada de información futura en backtests ni evaluaciones. Un cambio intencional al cálculo de
  probabilidades de un deporte sube `MODEL_VERSION` de ese deporte y se documenta con su backtest. Para comprobar que
  un cambio no altera nada se usa `parity` (necesita la base del proyecto anterior prendida, en sólo lectura).
- Interfaz: `docs/guidelines/guia_maestra_ui_ux_para_codex.md` (checklist de aceptación, §11) y el catálogo de
  patrones; textos en español de México. Igual que el backend: lo común en `frontend/src/{components,pages,lib}` y
  lo de cada deporte en `frontend/src/sports/<deporte>/` (su `config.ts` configura las piezas comunes). Los tipos de
  `api.ts` reflejan lo que devuelve la API: no inventar campos.
- Reportes: ✅ Correcto · 🟡 Parcial · ❌ Incorrecto · 🎨 Sólo apariencia · ⚠️ Riesgo (psycopg.md §17). No declarar
  nada terminado sin la prueba que lo demuestre; distinguir prueba con mocks, con PostgreSQL real y en producción.

## Comandos (desde `backend/`, con el entorno virtual de la raíz)

```bash
../.venv/Scripts/python -m app.cli migrate
../.venv/Scripts/python -m app.cli summary
../.venv/Scripts/python -m app.cli import-legacy [--replace]
../.venv/Scripts/python -m app.cli parity --sport nba --date 2026-10-21
../.venv/Scripts/python -m app.cli picks --sport futbol [--date YYYY-MM-DD]
../.venv/Scripts/python -m pytest
```

Interfaz (desde la raíz): `npm --prefix frontend test` y `npm --prefix frontend run build`.

Lista completa de comandos en el README.

La base de V4 corre en Docker (`docker compose up -d db`, puerto 5435). Las pruebas de integración crean bases
`gorgo_v4_test*` en ese mismo servidor.
