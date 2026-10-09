# GorgoPredictions V4 — NBA y fútbol

Picks y parlays de **NBA** y **fútbol** en una sola plataforma: une
[GorgoNBAParlays](../GorgoNBAParlays) (API-Basketball) y [GorgoPredictionsV3](../GorgoPredictionsV3)
(API-Football, 15 competiciones). Plan completo, fases y decisiones: [docs/PLAN_UNION.md](docs/PLAN_UNION.md).

## Estado

| Fase | Estado |
|---|---|
| 0. Base (docs, reglas, Docker) | ✅ |
| 1. Base de datos y núcleo común; motores de NBA y fútbol portados | ✅ |
| 2. CLI y scheduler únicos | ✅ un ciclo real contra las dos APIs el 6-oct (sync, liquidación y registro) |
| 3. API (`/api/nba`, `/api/futbol` y rutas comunes) | ✅ |
| 4. Interfaz | ✅ un solo sitio para los dos deportes, con boleto mixto |
| 5. Importación del historial y paridad | ✅ importación final en el corte: 18/18 tablas por deporte, paridad idéntica |
| 6. Corte | ✅ 6-oct-2026: V4 es el sistema oficial |

Desde la noche del 6-oct-2026 V4 es el sistema oficial: sincroniza, registra picks, liquida y guarda **tus apuestas**
(interfaz en `http://localhost:8300`). Los dos proyectos anteriores quedaron apagados como archivo, sin borrar nada; no
se vuelven a prender (su scheduler duplicaría la cuota de la API).

Desde el 8-oct-2026 todo pide sesión, con tres planes: **free** (parlays gratis del día, historial y rendimiento),
**suscriptor** (todo) y **admin** (todo, recalcular, bajas y cuentas). Qué ve cada uno y cómo está hecho:
[docs/PLAN_USUARIOS.md](docs/PLAN_USUARIOS.md).

## Requisitos

- Docker Desktop
- Python 3.13 (entorno virtual en `.venv`) y Node 20 (interfaz)
- Archivo `.env` en la raíz (copiar de `.env.example`; la llave de api-sports es la misma de los proyectos anteriores)

## Arranque

```bash
docker compose up -d db                                   # PostgreSQL en localhost:5435
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
npm --prefix frontend install
```

El servicio completo (base, scheduler y web) corre en Docker: `docker compose --profile servicio up -d --build` →
interfaz y API en `http://localhost:8300`. Los contenedores se reinician solos con Docker Desktop.

La primera vez (o después de la migración `0007`), pon la contraseña del dueño: `docker compose run --rm app
set-password GorgoAdmin`. Las demás cuentas se crean en la página **Usuarios** o con `create-user`.

## Comandos

Desde `backend/` con `../.venv/Scripts/python -m app.cli <comando>` (o `docker compose run --rm app <comando>`).
Los comandos de datos aceptan `--sport nba|futbol`; sin él corren para los dos deportes donde aplica.

| Comando | Qué hace |
|---|---|
| `migrate` | Crea/actualiza el esquema |
| `summary` | Filas por tabla |
| `import-legacy [--replace]` | Historial de los dos proyectos anteriores (sólo los lee) |
| `users` | Cuentas, su plan, vencimiento y cuántas apuestas tienen |
| `create-user USUARIO [--role free\|subscriber\|admin] [--until YYYY-MM-DD]` | Crea una cuenta (pide la contraseña) |
| `set-password USUARIO` | Pone la contraseña (la pide sin mostrarla) y cierra sus sesiones |
| `set-plan USUARIO ROL [--until YYYY-MM-DD] [--disable]` | Cambia el plan, el vencimiento o desactiva la cuenta |
| `parity --sport X [--date D]…` | Compara el motor de V4 con el del proyecto anterior para los mismos días y datos |
| `status [--sport X]` | Plan y consumo de cada API (no gasta cuota) |
| `sync [--sport X]` | Temporada en curso: partidos, estadísticas, bajas y momios |
| `odds` · `injuries [--sport X]` | Sólo momios · sólo bajas (NBA: reporte oficial; fútbol: API) |
| `lineups [--minutes 90]` | Fútbol: alineaciones de lo que empieza pronto |
| `backfill --sport nba [--season YYYY-YYYY]` · `backfill --sport futbol [--seasons …] [--league ID]` | Temporadas completas |
| `picks --sport X [--date D] [--bookmaker Bet365\|1xBet\|best]` | Piernas y parlays de un día (texto) |
| `record-picks --sport X [--date D]` | Guarda piernas y parlays de un día (lo hace el scheduler) |
| `settle [--sport X]` | Liquida piernas, parlays y tus apuestas (lo hace el scheduler) |
| `performance --sport nba [--include-preseason]` · `--sport futbol [--league ID]` | Rendimiento real, con CLV |
| `backtest --sport X [--start --end --every N --teams-only]` | Evalúa los modelos día por día |
| `scheduler [--sport X]` | Sincroniza, liquida y registra picks periódicamente |

API local (desde `backend/`): `../.venv/Scripts/python -m uvicorn app.api.main:app --port 8301 --reload`;
documentación en `http://localhost:8301/api/docs`. Rutas de cada deporte en `/api/nba/*` y `/api/futbol/*`;
comunes en `/api/meta`, `/api/bets` (boleto mixto), `/api/history[.csv]?sport=` y `/api/performance?sport=`; cuentas
en `/api/auth/*` (entrar, salir, quién soy, cambiar contraseña) y `/api/admin/users` (sólo admin). Todo lo demás
responde 401 sin sesión.
Si existe `frontend/dist` (`npm --prefix frontend run build`), la misma API sirve la interfaz en `http://localhost:8301`.

Interfaz en desarrollo: `npm --prefix frontend run dev` → `http://localhost:5173` (manda `/api` a la API local del
puerto 8301).

Pruebas:

- Backend (desde `backend/`, contra PostgreSQL real): `../.venv/Scripts/python -m pytest`.
- Interfaz: `npm --prefix frontend test` (lógica de parlays, boleto, preferencias y momios) y
  `npm --prefix frontend run build` (tipos estrictos + compilación).

## Cómo está armado

```
backend/app/
├── core/            # lo común: parlays, registro y liquidación de picks, apuestas, evidencia, ingesta,
│                    # cuentas y sesiones (accounts.py) y qué ve cada plan (access.py)
├── sports/
│   ├── nba/         # modelos, ingesta (API-Basketball + reporte de lesiones) y su contrato (sport.py)
│   └── futbol/      # modelos, ingesta (API-Football) y su contrato (sport.py)
├── scheduler.py     # un solo ciclo para los dos deportes; cada deporte corre aislado
├── legacy_import.py # importación del historial de los proyectos anteriores
├── parity.py        # comparación con los proyectos anteriores
└── cli.py
```

```
frontend/src/
├── components/      # lo común: encabezado (NBA | Fútbol), boleto mixto, piernas, parlays sugeridos, personalizar
├── sports/
│   ├── nba/         # config.ts (mercados, estadísticas, etiquetas), tarjeta de partido, bajas, Día
│   └── futbol/      # config.ts, tarjeta de partido, bajas, Día y Jornada (jornada o rango de fechas)
├── pages/           # Historial, Mis apuestas, Rendimiento; Entrar, Tu cuenta y Usuarios (admin)
└── lib/             # API, preferencias por deporte, boleto, armado de parlays, formatos
```

- La interfaz es una sola: `/nba`, `/futbol`, `/futbol/jornada`, `/historial`, `/mis-apuestas`, `/rendimiento`,
  `/cuenta` y `/usuarios` (admin). Sin sesión, cualquier ruta muestra "Entrar".
  El boleto acepta piernas de los dos deportes; cada deporte guarda sus preferencias (mercados, ligas, mínimos) y
  tu casa de apuestas es común. El color de acento cambia con el deporte (naranja NBA, índigo fútbol).
- Los modelos e ingestas de cada deporte se copiaron casi textuales de su proyecto (sólo cambian los imports y los
  nombres de tabla, ahora con esquema). Cómo decide cada motor: ver "Cómo decide el motor" en el README de
  [GorgoNBAParlays](../GorgoNBAParlays/README.md) y de [GorgoPredictionsV3](../GorgoPredictionsV3/README.md).
  Lo que cambió después, con su backtest, está en [Cambios a los modelos](docs/MODELOS.md).
- Lo que estaba duplicado (armar y congelar parlays, guardar y liquidar piernas, tus apuestas, resumen de evidencia)
  vive una sola vez en `core/`, y cada deporte aporta lo suyo con el contrato `app/core/sport.py`.

### Paridad comprobada (6-oct-2026)

Con los mismos datos (`import-legacy --replace` y luego `parity`), V4 da exactamente las mismas piernas,
probabilidades, momios y proyecciones que los proyectos anteriores (diferencia máxima 0):

| Deporte | Días | Partidos | Piernas |
|---|---|---:|---:|
| NBA | 7, 10 y 21 de octubre (pretemporada, internacionales y temporada regular) | 23 | 15,398 |
| Fútbol | 7, 10 y 18 de octubre | 105 | 29,742 |

Además, `record-picks` de V4 reprodujo lo que los proyectos anteriores habían registrado para el 7-oct
(3,010 piernas y 4 parlays de NBA; 1,330 piernas y 10 parlays de fútbol, sin una sola diferencia).

Esto vale para los modelos `v1`. Desde fútbol `v2` (identidad de árbitros), las tarjetas difieren a propósito del
proyecto anterior; ver [Cambios a los modelos](docs/MODELOS.md).

## Momios de publicación, cierre y CLV

- **Casas que se guardan en cada pierna** (`PRICE_BOOKMAKERS`): Bet365 (`BOOKMAKER`: con ella el sistema registra
  y mide sus parlays), 1xBet y Pinnacle (la referencia del mercado: casi sin comisión). En Personalizar eliges con
  cuál comparar piernas y parlays; en el boleto, si apuestas en una de ellas sus momios se llenan solos (Caliente y
  las demás se escriben a mano). `parity` compara sólo las casas que guardaban los proyectos anteriores.
- **Cuándo se leen los momios** (scheduler): en el ciclo regular (`SYNC_INTERVAL_HOURS`), en la previa de cada
  horario de partidos (`NBA_PREGAME_LEAD_MINUTES`=60: sincronización completa; `FUTBOL_PREGAME_LEAD_MINUTES`=45:
  alineaciones, bajas y momios) y en la **lectura de cierre** (`NBA_CLOSING_LEAD_MINUTES`=15: sólo momios y reporte
  de lesiones; `FUTBOL_CLOSING_LEAD_MINUTES`=0, apagada: la previa de fútbol ya lee después de las alineaciones).
  Cada corrida vuelve a registrar los picks de hoy y mañana.
- **Momio de publicación**: la primera vez que una pierna se registra con momio de `BOOKMAKER`, `core.picks` guarda
  `first_odd`, `first_p_model`, `first_p_market`, `first_p_sharp` y `first_priced_at`, que ya no cambian. `odd`,
  `p_model`, `p_market` y `p_sharp` siguen actualizándose hasta que empieza el partido: quedan con los del cierre.
- **Probabilidad del mercado y de Pinnacle**: `p_market` es la de Pinnacle si cotiza el mercado completo y, si no, la
  mediana de las casas que sí (se muestra en las piernas). `p_sharp` es sólo la de Pinnacle (NULL si no cotiza el
  mercado completo): con una sola casa que pone un lado en el mínimo (1.01), el devig infla mucho los momios altos
  (p. ej. 6.7% para "más de 4.5 goles" de un equipo que Bet365 paga a 51), así que el CLV no usa esa mediana.
- **CLV** (Rendimiento y `performance`): momio de publicación × probabilidad sin comisión de Pinnacle al cierre − 1.
  Una pierna cuenta si su última evaluación fue a 90 min o menos del inicio, Pinnacle cotizaba ahí su mercado
  completo, se publicó al menos 2 h antes de esa evaluación (si no, publicación y cierre son la misma foto) y su
  momio de publicación no estaba a más de 20% del precio justo de ese momento (Pinnacle; si no lo había, el mercado):
  una diferencia así casi siempre es un dato malo. El que mide al modelo es el de las **piernas con valor al
  publicarse** (probabilidad del modelo × momio > 1) de momio menor a 10, con promedio y mediana; las de momio 10 o
  más van aparte (poco confiables) y el de todas las piernas es sólo referencia (incluye los dos lados de cada mercado
  y ronda menos la comisión de la casa). Rendimiento dice cuántas piernas con valor no cuentan y por qué.
- **Historia**: las piernas de partidos que empezaron antes del 7-oct-2026 no tienen momio de publicación; las de
  partidos pendientes lo tomaron en la primera corrida después. `p_sharp` existe desde el 8-oct-2026 (migración
  0006): las piernas publicadas antes no tienen `first_p_sharp`, así que su filtro de precio dudoso usa
  `first_p_market` y no entran en "mercado a favor", pero su CLV sí se mide contra el cierre de Pinnacle.
- Límite conocido: si una casa retira una selección, la vista `v_odds_latest` sigue dando su último momio. En los
  datos del 6 y 7-oct pasó en 51 de ~124 mil selecciones de fútbol y en ninguna de NBA.

## Base de datos

- `nba`: tablas de NBA tal como estaban en GorgoNBAParlays (IDs de API-Basketball).
- `futbol`: tablas de fútbol tal como estaban en GorgoPredictionsV3 (IDs de API-Football).
- `core`: lo que cruza deportes. `core.matches` da a cada partido una identidad común (los IDs de los dos proveedores
  chocan entre sí), y `core.picks`, `core.parlays` y `core.user_bets` se refieren a él: un boleto puede mezclar NBA y
  fútbol. `core.users` y `core.sessions` son las cuentas; cada apuesta es de una (`core.user_bets.user_id`).

### Importación del historial (`import-legacy`)

- Lee cada base anterior en una transacción de sólo lectura (foto consistente aunque su scheduler siga escribiendo)
  y escribe todo en V4 en una sola transacción: si algo falla, no queda nada a medias.
- Antes de escribir comprueba que las tablas y columnas de origen sean exactamente las esperadas; al final compara
  conteos y huellas de los valores de cada tabla contra la foto de origen.
- Las ingestas, picks, parlays y apuestas se renumeran (sus IDs chocaban entre proyectos); la correspondencia queda en
  `core.legacy_ids`. Las marcas de tiempo se conservan: son la evidencia de "registrado antes del partido".
- Con datos en V4 se niega a escribir encima; `--replace` borra lo de V4 y vuelve a importar (ensayos y corte).
- La conexión a cada base sale del `.env` de su proyecto (`LEGACY_NBA_ENV`, `LEGACY_FUTBOL_ENV`) o de una URL directa
  (`LEGACY_NBA_DATABASE_URL`, `LEGACY_FUTBOL_DATABASE_URL`).

Los archivos locales de los proyectos anteriores (muestras de la API, reportes y backtests) están copiados en
`data/nba` y `data/futbol` (no versionados).

## Documentación técnica

- [Plan de unión](docs/PLAN_UNION.md)
- [Cuentas y planes](docs/PLAN_USUARIOS.md)
- [Cambios a los modelos](docs/MODELOS.md) (versiones y sus backtests)
- [Python y PostgreSQL con Psycopg 3](docs/database/psycopg.md)
- APIs: [API-Basketball](docs/apis/API_Basketball_1_5_endpoints.md) ([campos verificados](docs/apis/API_Basketball_campos_verificados.md)),
  [API-Football](docs/apis/API_FOOTBALL_3_9_3_endpoints.md) ([campos verificados](docs/apis/API_Football_campos_verificados.md))
- Interfaz: [guía maestra UI/UX](docs/guidelines/guia_maestra_ui_ux_para_codex.md),
  [catálogo de patrones](docs/guidelines/catalogo_patrones_ui_ux_para_codex.md)
