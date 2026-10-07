# API-FOOTBALL — campos verificados con consultas reales

Complemento de `API_FOOTBALL_3_9_3_endpoints.md`. Verificado el 6 de octubre de 2026 con la cuenta del
proyecto: plan **Pro** (7,500 solicitudes/día, 300/minuto; `/status` no gasta cuota), vigente hasta el
20-oct-2026. Las respuestas crudas se guardan en `data/samples/` (no versionado).

## Competiciones (`/leagues?current=true`, una llamada para todas)

| ID | Competición | País | Temporada en curso |
|---:|---|---|---|
| 262 | Liga MX | México | 2026 (Apertura 2026 + Clausura 2027) |
| 39 | Premier League | Inglaterra | 2026 (2026-27) |
| 40 | Championship | Inglaterra | 2026 |
| 140 | La Liga | España | 2026 |
| 135 | Serie A | Italia | 2026 |
| 78 | Bundesliga | Alemania | 2026 |
| 88 | Eredivisie | Países Bajos | 2026 |
| 61 | Ligue 1 | Francia | 2026 |
| 94 | Primeira Liga | Portugal | 2026 |
| 2 | UEFA Champions League | World | 2026 |
| 3 | UEFA Europa League | World | 2026 |
| 13 | CONMEBOL Libertadores | World | 2026 (año calendario) |
| 71 | Brasileirão Série A | Brasil | 2026 (año calendario) |
| 128 | Liga Profesional Argentina | Argentina | 2026 (año calendario) |
| 169 | Super League | China | 2026 (año calendario) |

- La temporada es el **año de inicio** (2026 = 2026-27 en Europa). Liga MX 2026 trae sólo "Apertura - N"
  hasta ahora; la liguilla y el Clausura se agregan cuando se conocen.
- **La API llama "Serie A" a Italia (135) y a Brasil (71).** El proyecto usa nombres cortos propios.
- `coverage.injuries=false` en Liga MX, Argentina, Libertadores, Portugal y China: ahí `/injuries` casi
  no trae nada. `coverage.odds=false` en Champions y Europa League, pero sí hay momios (no confiar en `coverage.odds`).

## GET /fixtures

`league` + `season` devuelve la temporada completa en una llamada (380 partidos de la Premier).
`ids` (hasta 20, separados por `-`) devuelve además **eventos, alineaciones, estadísticas de equipo y de
jugadores** de cada partido: es la forma barata de cargar el detalle (20 partidos por solicitud).

```json
{
  "fixture": {"id": 1557367, "referee": "Thomas Bramall, England", "date": "2026-08-21T19:00:00+00:00",
              "venue": {"id": 494, "name": "Emirates Stadium", "city": "London"},
              "status": {"long": "Match Finished", "short": "FT", "elapsed": 90, "extra": 5}},
  "league": {"id": 39, "season": 2026, "round": "Regular Season - 1"},
  "teams": {"home": {"id": 42, "name": "Arsenal", "logo": "...", "winner": true},
            "away": {"id": 1346, "name": "Coventry", "logo": "...", "winner": false}},
  "goals": {"home": 3, "away": 0},
  "score": {"halftime": {"home": 2, "away": 0}, "fulltime": {"home": 3, "away": 0},
            "extratime": {"home": null, "away": null}, "penalty": {"home": null, "away": null}}
}
```

- `score.fulltime` es el marcador de **90 minutos**: con él se liquidan las apuestas. `goals` incluye el
  tiempo extra. Terminados: `FT`, `AET`, `PEN`. Anulados: `PST`, `CANC`, `ABD`, `AWD`, `WO`.
- `referee` viene como "Nombre, País" (a veces sin país) y suele publicarse antes del partido.
- La fecha local (centro de México) se calcula desde `fixture.date` (UTC).

### Estadísticas de equipo (`statistics[]`)

`Shots on Goal`, `Shots off Goal`, `Total Shots`, `Blocked Shots`, `Shots insidebox`, `Shots outsidebox`,
`Fouls`, `Corner Kicks`, `Offsides`, `Ball Possession` ("54%"), `Yellow Cards`, `Red Cards`,
`Goalkeeper Saves`, `Total passes`, `Passes accurate`, `Passes %`, **`expected_goals`** ("0.82") y
`goals_prevented`. Los conteos en 0 vienen `null`.

Cobertura de xG por liga (temporadas 2024–2026): ~100% en las ligas europeas y Championship; 75–90% en
China y Libertadores; Liga MX 0% en 2024, 62% en 2025, 76% en 2026; Argentina 37–100%; Champions y
Europa League ~70% (6% en lo que va de 2026). El modelo usa goles cuando falta el xG.

### Estadísticas por jugador (`players[].players[]`)

Nombre **completo** ("Zion Suzuki"); las alineaciones traen la forma corta ("Z. Suzuki"). Un suplente que
no entró viene con `games.minutes: null`. Los conteos en 0 vienen `null`.

```json
{"player": {"id": 199578, "name": "Zion Suzuki"},
 "statistics": [{"games": {"minutes": 90, "position": "G", "rating": "7.2", "substitute": false},
                 "shots": {"total": null, "on": null}, "goals": {"total": null, "assists": 0, "saves": 5},
                 "cards": {"yellow": 0, "red": 0}, "fouls": {"committed": null}, "penalty": {"scored": 0}}]}
```

### Eventos y alineaciones

- Eventos: `Goal` (`Normal Goal`, `Own Goal`, `Penalty`, `Missed Penalty`), `Card` (`Yellow Card`,
  `Red Card`), `subst`, `Var`.
- Alineaciones: `formation`, `startXI[]` y `substitutes[]` con `id`, `name` corto, `pos` (G/D/M/F) y `grid`.
  Según la documentación aparecen 20–40 minutos antes del partido.

## GET /injuries

`ids` (hasta 20 partidos) o `league` + `season` (temporada completa en una llamada). Tipos:
`Missing Fixture` (no juega) y `Questionable` (en duda). Cada baja llega **duplicada** en la respuesta.
En partidos futuros aparece pocas horas o días antes. Motivos frecuentes: lesiones, `Red Card`,
`Yellow Cards` (suspensión), `Inactive`.

## GET /odds

`league` + `season`, 10 partidos por página. Momios de 1 a 14 días antes. Casas en el catálogo:
`/odds/bookmakers` (Bet365 = 8, Pinnacle = 4, Betano = 32, 1xBet = 11…). **Caliente no está.**
Una muestra (Arsenal vs Leeds, 4 días antes) traía 9 casas; Bet365 con 70 mercados.

Mercados que usa el motor (`/odds/bets`, ids estables):

| id | Nombre | Selecciones |
|---:|---|---|
| 1 | Match Winner | `Home`, `Draw`, `Away` |
| 12 | Double Chance | `Home/Draw`, `Home/Away`, `Draw/Away` |
| 5 | Goals Over/Under | `Over 2.5`, `Under 2.5` (algunas casas también .25/.75 y enteros) |
| 16 / 17 | Total - Home / Total - Away | `Over 1.5`… |
| 8 | Both Teams Score | `Yes`, `No` |
| 10 | Exact Score | `2:1` |
| 80 | Cards Over/Under | `Over 4.5`… (pocas casas, cerca del partido) |
| 82 / 83 | Home / Away Team Total Cards | `Over 1.5`… |
| 92, 231, 218 | Anytime Goal Scorer (general, local, visitante) | nombre completo del jugador ("Viktor Gyokeres") |
| 95, 237, 236 | To Score Two or More Goals | nombre |
| 257–259 | Player to Score or Assist | nombre |
| 102, 251 | Player to be booked | nombre |
| 242, 264, 265 | Player Shots On Target / Shots | sólo si traen línea (`Nombre - Over 1.5`) |

- **No usar 269, 270, 275, 276** (remates por equipo de Bet365): en la muestra traían los precios de
  "gol de cabeza".
- Los demás ~60 mercados (córners, mitades, minutos, etc.) no se guardan.
