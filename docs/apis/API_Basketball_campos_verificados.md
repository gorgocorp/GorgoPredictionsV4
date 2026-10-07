# API-BASKETBALL — campos verificados con consultas reales (NBA)

Complemento de `API_Basketball_1_5_endpoints.md`, cuyas muestras venían colapsadas.
Verificado el 5 de octubre de 2026 con la cuenta del proyecto (plan **Pro**: 7,500 solicitudes/día, 300/minuto).
Las respuestas crudas se guardan en `data/samples/` (no versionado).

## Liga

- NBA: `league=12`, país USA (`country.id=5`).
- Formato de temporada: `YYYY-YYYY` (ej. `2025-2026`).
- Temporadas recientes: `2023-2024`, `2024-2025`, `2025-2026`, `2026-2027`.
- `coverage` de 2024-25 a 2026-27: `games.statistics.teams=true`, `games.statistics.players=true`, `standings=true`, `players=true`, **`odds=false`**.
  Pese a `odds=false`, `/odds` sí devuelve cuotas para partidos próximos (ver abajo). No confiar en `coverage.odds`.

## GET /games

Una sola llamada `league=12&season=2025-2026` devuelve la temporada completa (1,384 partidos).
`stage` y `week` vienen `null`: no distinguen pretemporada, temporada regular ni playoffs.

```json
{
  "id": 519490,
  "date": "2026-10-06T02:00:00+00:00",
  "time": "02:00",
  "timestamp": 1791252000,
  "timezone": "UTC",
  "stage": null,
  "week": null,
  "venue": "Golden",
  "status": {"long": "Not Started", "short": "NS", "timer": null},
  "league": {"id": 12, "name": "NBA", "type": "League", "season": "2026-2027", "logo": "..."},
  "country": {"id": 5, "name": "USA", "code": "US", "flag": "..."},
  "teams": {
    "home": {"id": 157, "name": "Sacramento Kings", "logo": "..."},
    "away": {"id": 145, "name": "Los Angeles Lakers", "logo": "..."}
  },
  "scores": {
    "home": {"quarter_1": null, "quarter_2": null, "quarter_3": null, "quarter_4": null, "over_time": null, "total": null},
    "away": {"quarter_1": null, "quarter_2": null, "quarter_3": null, "quarter_4": null, "over_time": null, "total": null}
  }
}
```

Los lados son `home` / `away` (no `visitors` como en API-NBA). Partidos terminados: `FT` o `AOT`.

## GET /games/statistics/players

Una fila por jugador y partido. `ids` acepta hasta 20 partidos por llamada (452 filas en una prueba).
`player` + `season` devuelve la temporada de un jugador.

```json
{
  "game": {"id": 500996},
  "team": {"id": 158},
  "player": {"id": 999, "name": "Vassell Devin"},
  "type": "starters",
  "minutes": "39:12",
  "field_goals": {"total": 3, "attempts": 3, "percentage": null},
  "threepoint_goals": {"total": 2, "attempts": 5, "percentage": null},
  "freethrows_goals": {"total": 0, "attempts": 0, "percentage": null},
  "rebounds": {"total": 7},
  "assists": 2,
  "points": 12
}
```

Hallazgos (muestra de 20 partidos aleatorios de 2025-26):

- **`field_goals` = sólo tiros de 2 puntos**, no incluye triples. `points = 2·fg + 3·tp + ft` cuadra en 399 de 452 filas;
  la fórmula “FG incluye triples” sólo cuadra cuando no hubo triples.
- En ~12% de las filas `field_goals` viene `0/0` aunque el jugador sí anotó de 2 (ej. 40 puntos con 6 triples y 4 libres).
  `points` sí es confiable: la suma de puntos de jugadores coincidió con el marcador en 40 de 40 casos.
  Los dobles anotados se pueden reconstruir como `(points - 3·tp - ft) / 2`; los intentos no.
- `type`: `starters` o `bench`. `minutes` en formato `MM:SS`.
- **No hay** robos, bloqueos, pérdidas ni rebotes ofensivos/defensivos por jugador.
- Formato de nombre inconsistente: `"Vassell Devin"` (apellido nombre) o `"A. Bailey"` (inicial).

## GET /games/statistics/teams

Una fila por equipo. Sí trae robos, bloqueos y pérdidas a nivel equipo. Aquí también `field_goals` son tiros de 2.

```json
{
  "game": {"id": 500996},
  "team": {"id": 158},
  "field_goals": {"total": 21, "attempts": 49, "percentage": 43},
  "threepoint_goals": {"total": 12, "attempts": 37, "percentage": 32},
  "freethrows_goals": {"total": 12, "attempts": 19, "percentage": 63},
  "rebounds": {"total": 47, "offence": null, "defense": null},
  "assists": 18, "steals": 6, "blocks": 7, "turnovers": 12, "personal_fouls": null
}
```

## GET /players

```json
{"id": 623, "name": "Braun Christian", "number": null, "country": "USA", "position": "Guard", "age": 22}
```

## GET /odds

- Sólo devuelve partidos dentro de la ventana de 1–7 días antes del juego. `league=12&season=2025-2026` (temporada terminada) devolvió 0.
- Estructura: `{league, country, game, bookmakers: [{id, name, bets: [{id, name, values: [{value, odd}]}]}]}`.
- `odd` es string en formato **decimal** (ej. `"1.43"`).
- En un partido de pretemporada: 9 casas (Marathon Bet, 1xBet, Betano, WilliamHill, Bet365, Betfair, BetVictor, Pinnacle, SBO) y 75 mercados distintos.

Mercados de partido más frecuentes: `Home/Away` (ganador, id 2), `Over/Under` (id 4), `Asian Handicap` (id 3),
y sus variantes por mitad y cuarto, totales por equipo (`Home Team Total Goals (Including OT)`), `Odd/Even`.

Formato de `values`:

| Mercado | Ejemplo de `value` |
|---|---|
| `Home/Away` | `Home`, `Away` |
| `Over/Under` | `Over 226.5`, `Under 226.5` (varias líneas por casa) |
| `Asian Handicap` | `Away +4.5`, `Home +5.5` — **el número es siempre el handicap del local** (ver abajo) |

**Asian Handicap: convención de signo.** El número de la selección es el handicap del equipo local,
aunque la selección sea `Away`. En un partido con los Lakers (visitante) favoritos, a 1.46:

| Selección API | Significa | Momio Pinnacle |
|---|---|---|
| `Home +5.5` | Kings (local) +5.5 | 1.96 |
| `Away +5.5` | Lakers (visitante) **−5.5** | 1.83 |
| `Away -3.5` | Lakers **+3.5** | 1.25 (1xBet) |
| `Home -3.5` | Kings −3.5 | 3.70 (1xBet) |

`Home +X` y `Away +X` son los dos lados de la misma línea.

Props de jugador encontradas (pocas casas, sólo Betano y Bet365 en la muestra):

| Mercado | Ejemplo de `value` | Significado |
|---|---|---|
| `Player Points Milestones` | `Anthony Edwards - 20` | 20 o más puntos |
| `Player Points and Assists` | `LaMelo Ball - Over 17.5` | puntos + asistencias |

Los nombres de jugador en odds (`"Anthony Edwards"`) no coinciden con el formato de estadísticas (`"Edwards Anthony"`, `"A. Edwards"`):
hay que normalizarlos para emparejarlos.

## GET /bets y /bookmakers

- `/bets`: 245 mercados, catálogo compartido entre deportes (incluye “Stolen Bases”, “Tackles”). Algunos `name` son `null`.
- `/bookmakers`: 34 casas; una tiene `name` `null`.
