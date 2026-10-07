# Plan de unión → GorgoPredictionsV4

> Una sola plataforma con NBA y fútbol: una base de datos, una API + web, un scheduler y un `docker compose`.
>
> Fuentes, **sólo lectura** (no se modifican sus archivos ni sus bases):
> `GorgoNBAParlays` @ `6d16326` y `GorgoPredictionsV3` @ `0791500` (6-oct-2026).
>
> **Corte hecho la noche del 6-oct-2026** (ver §10): V4 es el sistema oficial y los dos proyectos anteriores
> quedaron apagados como archivo, sin borrar nada. Lo que sigue en §1–§9 es el plan tal como se hizo.

## 1. Diagnóstico

**Son el mismo sistema con dos deportes.** V3 nació como copia del proyecto NBA ("Misma arquitectura que
GorgoNBAParlays") y después los dos siguieron creciendo en paralelo.

| Aspecto | NBA | Fútbol (V3) |
|---|---|---|
| Backend | Python 3.13 · FastAPI · psycopg 3 · numpy/pandas (+ pdfplumber) | igual |
| Base | PostgreSQL 17 en Docker · puerto 5433 · BD `gorgo` | igual · 5434 · BD `gorgo_futbol` |
| Web | React 18 · Vite · TypeScript · TanStack Query · React Router · puerto 8100 | igual · 8200 |
| Fuente | API-Basketball v1 (`league=12`) | API-Football v3 (15 competiciones) |
| Llave api-sports | la **misma** llave en los dos `.env` | |
| Plan de la API | Pro, vence 6-nov-2026 | Pro, vence **20-oct-2026** |
| Estado hoy | web + scheduler + db corriendo | web + scheduler + db corriendo |

- **25 archivos idénticos** byte por byte: `db.py`, los Dockerfile, los 3 documentos de reglas
  (`docs/guidelines/*`, `docs/database/psycopg.md`), `test_bets.py`, `Toast`, `States`, `books.ts`,
  `oddsInput.ts`, `store.ts`, `main.tsx`…
- **Núcleo casi idéntico** (cambia `game_id` ↔ `fixture_id` y los JOIN): `parlay.py` (18 líneas distintas),
  `bets.py` (25), `evidence.summarize` (igual), `report.py` (42), `tracking.py` (~70 % igual), el scheduler y las
  tablas `picks`, `parlays`, `parlay_legs`, `user_bets`, `user_bet_legs`, `odds_history`, `ingest_runs`.
- **Lo propio de cada deporte**: cliente e ingesta de la API; esquema de datos (cuartos vs. eventos, alineaciones y
  tarjetas); modelos (NBA: ratings con normal, props binomial negativa, bajas por reporte PDF, cambios de plantel,
  pretemporada · fútbol: GLM Poisson + Dixon-Coles, tarjetas con árbitro, props por 90 min); vocabulario de
  mercados (`legs.py`); textos de evidencia; piezas de interfaz (tarjeta de partido, Jornada, filtro de liga,
  plantel y bajas).
- **Choque de IDs**: los dos usan los IDs del proveedor como llave primaria, y API-Basketball y API-Football son
  espacios distintos (el equipo 132 existe en ambos y no es el mismo). La migración `0001` de NBA ya lo advierte y
  `docs/database/psycopg.md` §14–15 pide conservar el servicio de origen junto al ID externo ("Mismo ID externo
  en dos servicios → dos identidades separadas").
- Los dos **registran picks y apuestas ahora mismo**. La tarea programada `revision-debut-nba-2026`
  (21-oct, 11:00) revisa el proyecto NBA en el puerto 8100.

## 2. Decisión: núcleo común + un módulo por deporte

```
API-Basketball ──► sports/nba ────┐
                                  ├──► core: picks, parlays, boleto, liquidación, rendimiento ──► API ──► web :8300
API-Football ────► sports/futbol ─┘
                   PostgreSQL :5435 — esquemas nba · futbol · core
```

- **Un esquema por deporte (`nba`, `futbol`)** con sus tablas tal como están hoy (IDs del proveedor) y **un esquema
  `core`** con lo que cruza deportes: partidos registrados, picks, parlays, apuestas e ingestas.
- Los modelos y la ingesta se portan casi sin tocar (sólo nombres de tabla con esquema), así que se puede
  **demostrar paridad** con los proyectos actuales. Lo duplicado se escribe una sola vez.
- Descartado:
  - Dos bases detrás de una puerta común: no permite boleto mixto ni un solo "Mis apuestas", y duplica la operación.
  - Catálogo totalmente normalizado (equipos, jugadores y partidos de todos los deportes en tablas comunes):
    reescribe la ingesta y el SQL de modelos ya calibrados sin beneficio visible.

## 3. Base de datos

| Esquema | Contenido |
|---|---|
| `nba` | Esquema final de las 9 migraciones NBA, sin lo que pasa a `core`: `teams`, `players`, `games`, `player_game_stats`, `team_game_stats`, `seasons`, `odds_history`, `injury_reports`, `injury_report_teams`, `injury_entries`, `availability_overrides`, `game_projections` y sus vistas (`v_games`, `v_odds_latest`, `v_latest_injury_report`, `v_player_availability`). |
| `futbol` | Esquema final de las 4 migraciones de V3, sin lo que pasa a `core`: `leagues`, `teams`, `players`, `fixtures`, `fixture_team_stats`, `fixture_player_stats`, `fixture_events`, `fixture_lineups`, `injuries`, `availability_overrides`, `odds_history`, `fixture_projections` y sus vistas. |
| `core` | `ingest_runs` (+ `sport`), `matches`, `picks`, `parlays`, `parlay_legs`, `user_bets`, `user_bet_legs`, `legacy_ids`. |

✅ Implementado en `backend/migrations/` (`0001_core.sql`, `0002_nba.sql`, `0003_futbol.sql`, `0004_legacy_ids.sql`;
la base es nueva, así que las migraciones de cada proyecto se consolidaron). Lo esencial de `core`:

- `core.matches` (nombre de la guía `psycopg.md` §14): un partido de cualquier deporte con identidad propia y
  `UNIQUE (sport, external_id)`, donde `external_id` es `nba.games.id` o `futbol.fixtures.id`. Guarda lo que necesita
  la parte común: liga, inicio, día local, estado del proveedor y estado común (`scheduled`, `live`, `finished`,
  `cancelled`) y nombres de los equipos. Lo mantiene cada deporte con un upsert por conjunto desde sus tablas
  (`app/sports/<deporte>/matches.py`).
- `core.picks`: `sport` + `match_id` con llave foránea compuesta a `core.matches (id, sport)` (el deporte de una pierna
  es el de su partido) y `CHECK` de mercados y lados por deporte. Su `id` es global: el boleto puede mezclar NBA y
  fútbol sin choque de IDs.
- `core.parlays`: + `sport`, y `game_date` / `match_date` pasa a `day`; `UNIQUE (sport, day, mode, n_legs)`.
- `parlay_legs`, `user_bets`, `user_bet_legs`: igual que en los dos proyectos, con FK a `core.picks`.
- `core.legacy_ids`: correspondencia de IDs viejos → nuevos de lo que se renumeró al importar.

Reglas:

- `player_id` guarda el ID del proveedor de ese deporte. No puede tener FK a dos tablas: es la única relación sin
  restricción y queda documentada.
- Día: `local_date` en `LOCAL_TIMEZONE` (centro de México) para los dos deportes. NBA conserva `game_date` en hora
  del Este para las fases de `nba.seasons`. Comprobado con los datos importados: en los 3,972 partidos NBA las dos
  fechas coinciden.
- La migración de datos `0005_unescape_names` de NBA no se repite: la ingesta ya convierte las entidades HTML.
- Pruebas de integración contra PostgreSQL real (`tests/integration/test_schema.py`): mismo ID de proveedor en los dos
  deportes = dos partidos, estados por proveedor, `CHECK` por deporte, FK compuesta, boleto mixto, apuesta antes del
  partido y parlays por deporte.

## 4. Backend

✅ Implementado (6-oct-2026):

```
backend/
├── app/
│   ├── config.py           # APISPORTS_KEY, DATABASE_URL, BOOKMAKER, PRICE_BOOKMAKERS, LOCAL_TZ, SPORTS
│   ├── db.py               # idéntico en ambos proyectos
│   ├── apisports.py        # un cliente (el de V3: paginación y guardia de cuota), una instancia por API
│   ├── core/
│   │   ├── sport.py        # contrato que implementa cada deporte
│   │   ├── matches.py      # upsert de core.matches
│   │   ├── ingest.py       # registro de cada corrida, upsert por lote, historial de momios
│   │   ├── parlay.py       # Candidate(sport, external_id), build_parlay, filtros y modos (MODES)
│   │   ├── tracking.py     # registrar, congelar y liquidar picks/parlays; rendimiento
│   │   ├── bets.py         # Mis apuestas (boleto mixto)
│   │   └── evidence.py     # resumen del historial
│   ├── sports/
│   │   ├── nba/            # engine/ (history, team/player models, roster, legs, odds, picks, evidence,
│   │   │                   # tracking, backtest, report), ingest/ (jobs, normalize, injuries), ops.py, sport.py
│   │   └── futbol/         # engine/ (history, glm, dist, team/cards/player models, legs, odds, picks,
│   │                       # evidence, tracking, backtest, report), ingest/ (jobs, normalize), ops.py, sport.py
│   ├── scheduler.py        # un solo ciclo para todos los deportes
│   ├── legacy_import.py    # historial de los proyectos anteriores
│   ├── parity.py           # comparación con los proyectos anteriores
│   └── cli.py              # gorgo <comando> [--sport nba|futbol]
├── migrations/
└── tests/                  # core/, nba/, futbol/, integration/
```

- Cada deporte conserva su código casi textual (sólo imports y tablas con esquema). Para paridad exacta se
  quedaron por deporte su `odds.py` (parseo de mercados, quitar comisión y empate de nombres difieren) y su
  `report.py` (texto de la CLI); a `core` pasó sólo lo idéntico o lo que se generalizó sin cambiar resultados.
- NBA adoptó `fit_models` separado de `generate_day` (como V3) para reutilizar modelos al recalcular, pero sigue
  ajustando cada día con su propia fecha de corte, como antes; fútbol conserva su `models_day`.
- `app/api/main.py` (routers por deporte) llega en la fase 3.

Contrato de cada deporte (`app/core/sport.py`, una instancia en `app/sports/<deporte>/sport.py`): identidad y
versión del modelo, rangos de piernas que se guardan, días a registrar y anticipación de la previa; historial y
modelos (`load_history`, `has_matches`, `models_cutoff`, `fit_models`, `generate_day`, `save_projections`,
`sync_matches`); liquidación y evidencia (`outcome_columns`, `outcome_joins`, estados terminados y anulados,
`pick_result`, `leg_outcome`, `matchup`); y filtros de rendimiento. La sincronización de cada deporte vive en su
`ops.py` (`sync`, `pregame_sync`, `backfill`…).

API:

| Uso | Hoy (cada proyecto) | V4 |
|---|---|---|
| Día y piernas | `/api/days/{day}`, `/api/days/{day}/legs` | `/api/{sport}/days/{day}`, `/api/{sport}/days/{day}/legs` |
| Recalcular | `POST /api/days/{day}/refresh` | `POST /api/{sport}/days/{day}/refresh` (candado y caché por deporte) |
| Plantel y bajas | `/api/games/{id}/roster`, `/api/fixtures/{id}/roster`, `PUT /api/availability` | `/api/nba/games/{id}/roster`, `/api/futbol/fixtures/{id}/roster`, `PUT /api/{sport}/availability` |
| Jornada o rango | `/api/rounds`, `/api/slate*` (fútbol) | `/api/futbol/rounds`, `/api/futbol/slate*` |
| Estado | `/api/meta` | `/api/meta` con sincronización por deporte |
| Calendario | `/api/calendar` | `/api/calendar?sport=` |
| Mis apuestas | `/api/bets` | `/api/bets` (piernas de los dos deportes) |
| Historial | `/api/history`, `/api/history.csv` | igual + `?sport=` (y `preseason` NBA, `league` fútbol) |
| Rendimiento | `/api/performance` | `/api/performance?sport=&league=&include_preseason=` |

Scheduler y CLI:

- Un proceso. En cada ciclo, cada deporte corre aislado: si falla uno (p. ej. vence el plan de fútbol), el otro sigue
  y la interfaz muestra el fallo sólo de ese deporte.
- Próxima corrida: la regular (`SYNC_INTERVAL_HOURS`) o la previa más cercana entre los dos deportes, con la
  anticipación de cada uno.
- Un cliente api-sports por API: cada API tiene su cuota y sus encabezados de límite.
- `gorgo <comando> [--sport nba|futbol]` (sin `--sport`, todos donde aplique): `migrate`, `status` (los dos planes),
  `summary`, `backfill`, `sync`, `odds`, `injuries`, `lineups` (fútbol), `picks`, `record-picks`, `settle`,
  `performance`, `backtest`, `scheduler` e `import-legacy` (nuevo, ver §7).

Un solo `.env`:

```
APISPORTS_KEY=                 # la misma llave que usan hoy los dos proyectos
POSTGRES_DB=gorgo_v4           # + POSTGRES_USER, POSTGRES_PASSWORD
POSTGRES_HOST_PORT=5435
DATABASE_URL=postgresql://gorgo:...@localhost:5435/gorgo_v4
LOCAL_TIMEZONE=America/Mexico_City
SPORTS=nba,futbol
NBA_CURRENT_SEASON=2026-2027
SYNC_INTERVAL_HOURS=6
NBA_PREGAME_LEAD_MINUTES=60
FUTBOL_PREGAME_LEAD_MINUTES=45
FUTBOL_RECORD_DAYS=7
BOOKMAKER=Bet365
PRICE_BOOKMAKERS=Bet365,1xBet
WEB_HOST_PORT=8300
LEGACY_NBA_DATABASE_URL=       # sólo para import-legacy (lectura)
LEGACY_FUTBOL_DATABASE_URL=
```

Puertos 5435 / 8300 para que V4 corra junto a los dos proyectos actuales durante la transición.

## 5. Interfaz

✅ Implementada el 6-oct-2026 (React 18 + Vite + TypeScript estricto + TanStack Query, como los dos proyectos).

```
frontend/src/
├── App.tsx, main.tsx          # rutas con el deporte en la URL
├── components/                # comunes: Header, BetSlip, LegsTable, ParlaysSection, PreferencesPanel, SlateBody, DateBar, States, Toast
├── sports/
│   ├── nba/                   # config (mercados, estadísticas, etiquetas), api, GameCard, AvailabilityPanel, DayPage
│   └── futbol/                # config, api, GameCard, AvailabilityPanel, DayPage, RoundPage (jornada o rango de fechas)
├── pages/                     # comunes: Historial, Mis apuestas, Rendimiento
└── lib/                       # api, sports, preferences, slip, builder, parlay, books, format, oddsInput, store, sportContext, queries, backtest
```

- **Lo común una vez, lo de cada deporte en su carpeta**: `sports/<deporte>/config.ts` define lo que cambia
  (mercados, estadísticas de jugador y cómo se agrupan, "Visitante @ Local" o "Local vs Visitante", etiquetas de
  "en duda"/"titular", tareas de sincronización) y las piezas comunes (tabla de piernas, parlays sugeridos,
  personalizar, boleto, `SlateBody`) se configuran con él. Las tarjetas de partido y los paneles de bajas son de
  cada deporte (sus datos son distintos).
- **Encabezado**: "Gorgo Predictions" + control segmentado **NBA | Fútbol** (vistas hermanas → control segmentado,
  guía §7) + Día · Jornada (sólo fútbol) · Historial · Mis apuestas · Rendimiento + estado de sincronización del
  deporte (detalle de los dos al pasar el cursor) + tema. En Historial y Rendimiento el control cambia el deporte de
  la página; en las demás lleva al día de ese deporte (entre días conserva la fecha).
- **Rutas**: `/nba` y `/futbol` (Día, con `?fecha=`), `/futbol/jornada`, `/historial?deporte=` (sin él, todos),
  `/mis-apuestas`, `/rendimiento?deporte=`. `/` lleva al último deporte usado.
- **Acento por deporte** con tokens (`data-sport` en `<html>`, aplicado antes del primer pintado: naranja NBA,
  índigo fútbol, en claro y oscuro) y etiquetas de deporte con texto: el color no es la única señal.
- **Un solo boleto, mixto**: `SlipLeg` lleva `sport` y `matchId`; el aviso de "mismo partido" usa `matchId`.
  Momios escritos por casa (lo de NBA). El backend acepta hasta 20 piernas.
- **Preferencias**: por deporte (mercados, estadísticas, ligas, mínimos, tamaños, jugadores en duda) y comunes (tu
  casa y la casa para comparar). "Restablecer" ya no cambia tu casa (en los proyectos anteriores sí lo hacía).
- **Mejoras al unir**: Rendimiento "Por mercado" también para NBA (la API ya lo da igual para los dos); al marcar
  una baja o recalcular se refrescan día y jornada del deporte (antes la jornada esperaba hasta 2 minutos).
- `localStorage` no se hereda (otro puerto = otro origen) y las llaves de V4 llevan prefijo `gorgo-v4.`: no chocan
  con las de los proyectos anteriores si comparten origen en desarrollo (`localhost:5173`).

## 6. Documentación y reglas

```
CLAUDE.md                     # reglas de trabajo para el agente
README.md                     # arranque, comandos, "Cómo decide el motor" y "Datos" por deporte
docs/
├── PLAN_UNION.md             # este documento
├── ARQUITECTURA.md           # núcleo, contrato de deporte y esquemas, al implementar
├── IDEA.md                   # la de V3 + NBA
├── apis/                     # endpoints y campos verificados de API-Basketball y API-Football
├── database/psycopg.md       # idéntico en ambos → una copia
└── guidelines/               # guía maestra y catálogo UI/UX, idénticos → una copia
```

`CLAUDE.md` vuelve obligatorias las reglas de los docs:

- Leer `docs/database/psycopg.md` antes de tocar persistencia; sólo migraciones versionadas; transacciones cortas;
  restricciones reales en la base.
- No inventar campos, IDs ni endpoints: consultar `docs/apis/*_campos_verificados.md`.
- Cambios de interfaz con la checklist de aceptación de la guía maestra (§11).
- Nada de información futura en backtests ni evaluaciones.
- Reportar con ✅ 🟡 ❌ 🎨 ⚠️ (psycopg.md §17) y no declarar nada terminado sin evidencia.
- `GorgoNBAParlays` y `GorgoPredictionsV3` son de sólo lectura.

## 7. Migración de datos (sin modificar los proyectos)

Decidido el 6-oct-2026: se importa **todo** el historial. ✅ Implementado en `app/legacy_import.py`
(`import-legacy`) y ensayado con las bases reales.

- Lee las dos bases actuales (puertos 5433 y 5434) en transacciones de sólo lectura con REPEATABLE READ (una foto
  consistente aunque sus schedulers sigan escribiendo). No escribe en ellas ni toca sus archivos; la conexión sale
  del `.env` de cada proyecto, que sólo se lee.
- Antes de escribir comprueba que las tablas y columnas de origen sean exactamente las esperadas (nada se queda
  fuera). Escribe todo en V4 en una sola transacción: si algo falla, no queda nada a medias.
- Orden: `ingest_runs` → tablas de cada deporte tal cual (con sus IDs) → `odds_history` (con los IDs nuevos de sus
  ingestas) → `core.matches` → `picks` → `parlays` (+ `sport`, `day`) → `parlay_legs` → `user_bets` →
  `user_bet_legs`. Lo renumerado queda en `core.legacy_ids`.
- Se conservan todas las marcas de tiempo: son la evidencia de "registrado antes del partido" y las exige
  `CHECK (created_at < first_start)`.
- Verificación dentro de la misma transacción: conteo y huella de los valores de cada tabla (18 por deporte),
  partidos en `core.matches`, picks y parlays por resultado, monto y pago de tus apuestas. Si algo no cuadra, se
  revierte todo.
- Con datos en V4 se niega a escribir encima; `--replace` borra lo de V4 y vuelve a importar. Así se repite en el
  corte, con los schedulers viejos detenidos, para traer lo que registren mientras tanto.
- Pruebas (`tests/integration/test_legacy_import.py`, con copias de las migraciones de los dos proyectos): choque de
  IDs entre deportes, renumeración, marcas de tiempo, negativa sin `--replace`, reversión ante un fallo, origen que
  no puede escribir y rechazo de una base de V4 como origen.

Ensayo del 6-oct-2026 (foto de las 19:30 hora del centro, ~80 s, todo cuadró):

| | NBA | Fútbol |
|---|---:|---:|
| Partidos | 3,972 | 14,884 |
| Estadísticas de jugadores | 59,597 | 496,398 |
| Momios (`odds_history`) | 4,761 | 108,932 |
| Picks registrados | 8,844 | 29,854 |
| Parlays sugeridos | 16 | 69 |
| Tus apuestas (piernas) | 1 (4) | 2 (11) |
| Filas en total | 83,638 | 1,468,380 |

## 8. Fases

| Fase | Entrega | Aceptación (evidencia) |
|---|---|---|
| 0. Base ✅ | `git init`, docs consolidados, `CLAUDE.md`, `.env.example`, compose (base en 5435) | Hecho el 6-oct; `scheduler` y `web` en el compose con el perfil `servicio` (encendidos en el corte) |
| 1. Datos + núcleo ✅ | Migraciones `core`/`nba`/`futbol`; `core/*` extraído; los dos deportes portados al contrato | Hecho el 6-oct: `migrate` en base vacía; los archivos de pruebas de los dos proyectos portados (salvo `slate_range`, que vuelve con la API) + pruebas de `core`, del esquema y de integración del registro y la liquidación: 172 pruebas pasan |
| 2. CLI + scheduler ✅ | `gorgo … --sport`, scheduler único | `status` y un ciclo real del scheduler contra las dos APIs el 6-oct (sync NBA 37 solicitudes, fútbol 41; liquidación y registro de 7 días); pruebas de `next_runs` con partidos de ambos; un deporte que falla no detiene al otro |
| 3. API ✅ | Routers `/api/nba`, `/api/futbol` + rutas comunes (`meta`, `bets`, `history[.csv]`, `performance`) | Todas las rutas probadas contra la base real de V4; pruebas automáticas con base de prueba (boleto mixto por HTTP, jornada y rango, historial por deporte, CSV, rendimiento): 179 pruebas pasan |
| 4. Interfaz ✅ | Encabezado, páginas por deporte, boleto mixto, Historial y Rendimiento con filtro | Hecho el 6-oct: `npm test` 37 pruebas (las de los dos proyectos portadas + preferencias por deporte y boleto mixto), `tsc` estricto y `npm run build` sin errores; revisada en el navegador contra la base real: día de fútbol y de NBA, jornada, boleto con piernas de los dos deportes, Historial (todos/NBA), Mis apuestas, Rendimiento de los dos (580 piernas NBA liquidadas con pretemporada), claro/oscuro y móvil (375 px) sin desbordes |
| 5. Importación + paridad ✅ | `import-legacy` y `parity` | Conteos y huellas cuadran; **paridad** el 6-oct: NBA (7, 10 y 21-oct, 15,398 piernas) y fútbol (7, 10 y 18-oct, 29,742 piernas) idénticos, diferencia máxima 0; `record-picks` reprodujo lo registrado para el 7-oct (4,340 piernas y 14 parlays). Repetidas en el corte (§10) |
| 6. Corte ✅ | V4 en paralelo → detienes los schedulers viejos → importación final → V4 solo | Hecho el 6-oct a las 23:00 (§10): importación final 18/18 tablas por deporte, paridad IGUALES, primera corrida de V4 sin errores y con los mismos picks que acababan de registrar los proyectos anteriores; éstos quedaron intactos como archivo |
| 7. Después de la paridad | Vista "Hoy" con los dos deportes, parlays mixtos sugeridos, rango de fechas también para NBA, rendimiento combinado | Cada una con sus pruebas |

## 9. Riesgos y fechas

- **20-oct-2026**: vence el plan de API-Football (hay que renovarlo) y debuta la NBA (20 y 21-oct), ya con V4.
  El scheduler de V4 aísla cada deporte para que un plan vencido no tumbe al otro.
- **6-nov-2026**: vence el plan de API-Basketball.
- **Cuota**: misma llave. Desde el corte, en esta computadora sólo V4 sincroniza (~500/día NBA y ~250–400 fútbol, de
  7,500 cada uno); si un proyecto viejo volviera a prenderse con su scheduler, el consumo se duplicaría. La versión 1
  publicada en gorgopredictions.com usa la misma llave de API-Football (~3,700 solicitudes el 7-oct): cuenta para el
  límite diario de fútbol.
- **Memoria**: un proceso web con los dos historiales (el de fútbol ronda el medio millón de filas): caché por
  deporte y carga perezosa.
- **Paridad de modelos**: el riesgo principal es romper un modelo al portarlo; por eso la Fase 5 compara contra los
  proyectos actuales antes del corte.
- **"Hoy" de NBA**: pasa de hora del Este a `LOCAL_TIMEZONE`; sólo cambia entre la medianoche ET y la de CDMX.
- **Tarea programada** `revision-debut-nba-2026` (21-oct, 11:00): actualizada en el corte para revisar V4 (8300, base
  5435); tiene prohibido prender los proyectos anteriores y revisa también si venció el plan de fútbol.

## 10. El corte ✅

Hecho la noche del **6-oct-2026** por decisión del usuario, antes de lo previsto (después del 21-oct): V4 ya estaba
completo y con la paridad comprobada, y con un solo proyecto encendido es más simple de operar. No había partidos
hasta el día siguiente (fútbol desde las 16:30 y NBA desde las 17:00 del 7-oct). Pasos, todos con evidencia:

1. Comparación de liquidación pendiente: las 580 piernas NBA del 6-oct que V4 había liquidado coinciden con las del
   proyecto NBA (0 diferencias) y la apuesta #6 sale perdida en los dos.
2. Los schedulers y webs de los dos proyectos se detuvieron estando en espera (acababan de terminar su corrida: NBA
   liquidó 2,574 piernas del 6-oct y registró el 7 y el 8; fútbol registró del 7 al 12).
3. Importación final (`import-legacy --replace`, foto de las 23:04): 18 de 18 tablas por deporte con huellas iguales;
   NBA 12,262 picks, 21 parlays, 1 apuesta; fútbol 29,905 picks, 72 parlays, 2 apuestas.
4. `parity` sobre esos datos: NBA 7-oct (2,903 piernas) y 21-oct (8,557) y fútbol 7-oct (2,037) y 10-oct (17,857),
   todos IGUALES con diferencia máxima 0.
5. Se apagaron las bases anteriores y se encendió V4 (`docker compose --profile servicio up -d`). Su primera corrida
   (NBA 37 solicitudes, fútbol 42) registró exactamente los mismos picks que acababan de registrar los proyectos
   anteriores (7-oct NBA: 2,903 piernas y 4 parlays; fútbol del 7 al 12: mismas cifras), sin errores.
6. La tarea programada del 21-oct se apuntó a V4.

**Si hubiera que volver atrás**: los proyectos anteriores están intactos (`docker compose up -d` en cada carpeta). Lo
registrado en V4 desde el corte (picks, liquidaciones, tus apuestas) no estaría en ellos, y habría que apagar el
scheduler de V4 para no duplicar la cuota.

Lo que se consideró antes de decidir la fecha:

Es el momento en que V4 pasa a ser el sistema oficial: su scheduler sincroniza, registra picks y liquida, y los
schedulers de los proyectos anteriores se apagan. No cambia lo que se construye ni lo que se importa (la importación
final trae todo lo registrado hasta ese momento). Lo que sí depende de él:

- **Dónde registras tus apuestas**: hasta el corte, en los proyectos anteriores (8100 y 8200). V4 es de prueba: lo
  que se registre ahí se borra en la importación final.
- **Orden y horario**: apagar los schedulers viejos → importación final (`--replace`, ~80 s) → `parity` → arrancar
  V4 (`docker compose --profile servicio up -d --build`: scheduler y web en 8300). En ese hueco nadie congela picks,
  así que se hace en un horario sin partidos próximos (p. ej. una mañana entre semana).
- **Boleto de la vista previa**: la importación final renumera los picks. Si usaste la interfaz de V4 antes del corte
  (API local en 8301), vacía su boleto antes de registrar: una pierna guardada podría apuntar a otro pick.
- **Debut NBA (20–21 oct)**: primera evidencia real de la temporada (primer reporte de lesiones, primeros momios de
  temporada regular). Antes del corte lo maneja el proyecto NBA probado; después, código recién portado.
- **Revisión programada del 21-oct**: revisa el proyecto NBA (8100); si el corte es antes, hay que apuntarla a V4.
- **Reversible**: los proyectos anteriores quedan intactos; si V4 fallara, se vuelven a encender sus schedulers (lo
  registrado en V4 mientras tanto no estaría en ellos).
- **No depende del corte**: el vencimiento del plan de API-Football el 20-oct afecta a quien sincronice fútbol ese
  día; sin renovarlo, tampoco se puede probar la sincronización de fútbol en V4 después de esa fecha.

Recomendación: **cortar después del 21-oct** (p. ej. el 22 por la mañana), con V4 completo y la paridad comprobada.
Como la importación final trae el debut igual, no se pierde nada por esperar y no se estrena V4 en el momento más
delicado.

## 11. Decisiones

1. ✅ Historial: se importa todo (6-oct-2026).
2. ✅ Corte: primero se decidió hacerlo después del 21-oct-2026; esa misma noche el usuario decidió adelantarlo y se
   hizo el 6-oct-2026 a las 23:00, con V4 completo y la paridad comprobada (§10).
