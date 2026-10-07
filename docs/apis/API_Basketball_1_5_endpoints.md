# API-BASKETBALL 1.5.2 — inventario extraído de la documentación

**18 rutas GET: 17 operaciones de datos y /status en autenticación.**

Fuente: texto de `https://api-sports.io/documentation/basketball/v1` (Redocly), pegado por el usuario en el chat. Extracción: 5 de octubre de 2026.
No hubo navegación web, descarga del YAML ni consultas con una API key. Este documento no es una especificación OpenAPI oficial.
Los ejemplos son estáticos y se preservan como aparecen, sin actualizar fechas, valores ni inconsistencias.
En el texto pegado, la mayoría de los objetos de respuesta venían **colapsados** (`{}`): sus campos internos no se pueden documentar desde esta fuente.

## Conexión

```text
Base: https://v1.basketball.api-sports.io
Método: GET (único método aceptado)
Cabecera de autenticación: x-apisports-key: TU_API_KEY
```

La API sólo acepta peticiones GET y sólo la cabecera `x-apisports-key`. Peticiones no-GET o cabeceras extra devuelven error.
El documento advierte que algunos frameworks (JS, NodeJS) agregan cabeceras automáticamente y hay que quitarlas.

Cabeceras de respuesta documentadas:

| Cabecera | Significado |
|---|---|
| `x-ratelimit-requests-limit` | Solicitudes asignadas por día según la suscripción |
| `x-ratelimit-requests-remaining` | Solicitudes restantes del día |
| `X-RateLimit-Limit` | Máximo de llamadas por minuto |
| `X-RateLimit-Remaining` | Llamadas restantes en el minuto |

`/status` no consume la cuota diaria, según el documento. Los valores del ejemplo no identifican el plan del usuario.

## Versión y changelog

El encabezado dice **1.5.2**, pero el changelog lista **(1.5.6)** con estos cambios:

- `leagues`: se agrega el campo `coverage`.
- `games`: se agregan `games/statistics/teams`, `games/statistics/players` y el campo `venue`.
- Se agrega el endpoint `players`.

No se resolvió la discrepancia de versión; se conserva tal cual.

## Diferencias clave frente a API-NBA 2.2.5

| Aspecto | API-NBA 2.2.5 | API-BASKETBALL 1.5.x |
|---|---|---|
| Base | `https://v2.nba.api-sports.io` | `https://v1.basketball.api-sports.io` |
| Formato de `season` | integer `YYYY` | string de 4 a 9 caracteres: `YYYY` o `YYYY-YYYY` |
| Ligas | 6 claves de texto (`standard`, `vegas`…) | `id` numérico por liga/copa (ej. NBA = 12 en los ejemplos) |
| Estados de partido | Códigos numéricos 1–6 | Códigos de texto (`NS`, `Q1`, `FT`, `AOT`…) |
| Zona horaria | No documentada | Parámetro `timezone` + endpoint `/timezone` |
| H2H | Parámetro `h2h` en `/games` | Ruta `/games/h2h` (el ejemplo PHP usa `/games`) |
| Estadísticas de partido | `/games/statistics` (por equipo) | `/games/statistics/teams` y `/games/statistics/players` |
| Estadísticas de equipo | `/teams/statistics` | `/statistics` |
| Cuotas | No documentadas | `/odds`, `/bookmakers`, `/bets` |
| Países | No documentados | `/countries` |
| Partidos en vivo | Parámetro `live=all` | No hay parámetro `live` documentado |

## Rutas y parámetros

Un asterisco (*) indica que el parámetro está marcado `required` en la tabla original.
No sustituye requisitos generales del texto (“requiere al menos un parámetro”). Se contabilizan 62 entradas de parámetros de consulta entre las rutas.

| # | Ruta | Función | Parámetros |
|---:|---|---|---|
| 1 | `/status` | Consulta cuenta, suscripción y consumo. No descuenta cuota diaria. | Sin parámetros de consulta documentados |
| 2 | `/timezone` | Lista las zonas horarias válidas para `/games` y `/games/h2h`. | Sin parámetros de consulta documentados |
| 3 | `/seasons` | Lista las temporadas válidas como filtro en otros endpoints. | Sin parámetros de consulta documentados |
| 4 | `/countries` | Lista países; `id`, `name` y `code` sirven como filtros en otros endpoints. | `id`, `name`, `code`, `search` |
| 5 | `/leagues` | Lista ligas y copas, con su `coverage` por temporada. | `id`, `name`, `country_id`, `country`, `type`, `season`, `search`, `code` |
| 6 | `/teams` | Consulta datos de equipos. Requiere al menos un parámetro. | `id`, `name`, `country_id`, `country`, `league`, `season`, `search` |
| 7 | `/statistics` | Estadísticas de un equipo en una liga y temporada, con fecha límite opcional. | `league`*, `season`*, `team`*, `date` |
| 8 | `/players` | Consulta datos de jugadores. Requiere al menos un parámetro. | `id`, `team`, `season`, `search` |
| 9 | `/standings` | Clasificación de una liga/temporada, con filtros de equipo, fase o grupo. | `league`*, `season`*, `team`, `stage`, `group` |
| 10 | `/standings/stages` | Lista las fases (`stage`) disponibles para `/standings`. | `league`*, `season`* |
| 11 | `/standings/groups` | Lista los grupos (`group`) disponibles para `/standings`. | `league`*, `season`* |
| 12 | `/games` | Consulta partidos. Requiere al menos un parámetro. | `id`, `date`, `league`, `season`, `team`, `timezone` |
| 13 | `/games/statistics/teams` | Estadísticas de equipos de uno o varios partidos (máx. 20). | `id`, `ids` |
| 14 | `/games/statistics/players` | Estadísticas de jugadores por partido(s), o de un jugador en una temporada. | `id`, `ids`, `player`, `season` |
| 15 | `/games/h2h` | Enfrentamientos directos entre dos equipos. | `h2h`*, `date`, `league`, `season`, `timezone` |
| 16 | `/odds` | Cuotas pre-partido por liga, temporada, partido, casa o mercado. | `league`, `season`, `game`, `bookmaker`, `bet` |
| 17 | `/bookmakers` | Lista casas de apuestas; su `id` filtra `/odds`. | `id`, `search` |
| 18 | `/bets` | Lista mercados de apuesta; su `id` filtra `/odds`. | `id`, `search` |

## Frecuencias de actualización documentadas

| Ruta | Frecuencia |
|---|---|
| `/games` | Cada 15 segundos |
| `/games/statistics/teams` | Cada 30–120 segundos |
| `/games/statistics/players` | Cada 30–120 segundos |
| `/standings` | Cada hora |
| `/odds` | Una vez al día. Cuotas pre-partido de 1 a 7 días antes del juego; se guarda historial de 7 días |

Las demás rutas no indican frecuencia.

## Estados de partido (`/games`)

| Código | Significado | Grupo |
|---|---|---|
| `NS` | Not Started | Programado |
| `Q1` | Quarter 1 | En juego |
| `Q2` | Quarter 2 | En juego |
| `Q3` | Quarter 3 | En juego |
| `Q4` | Quarter 4 | En juego |
| `OT` | Over Time | En juego |
| `BT` | Break Time | En juego |
| `HT` | Halftime | En juego |
| `FT` | Game Finished | Terminado |
| `AOT` | After Over Time | Terminado |
| `POST` | Game Postponed | — |
| `CANC` | Game Cancelled | — |
| `SUSP` | Game Suspended | — |
| `AWD` | Game Awarded | — |
| `ABD` | Game Abandoned | — |

## Qué no documenta este archivo

No hay parámetro `live` ni ruta de partidos en vivo; el estado se lee del partido.
No hay paginación por `page`, ni filtros `from`, `to`, `last` o `next`.
No hay rutas de predicciones, lesiones, play-by-play ni alineaciones.
No existe `/teams/statistics`: la ruta de estadísticas de equipo es `/statistics`.
No se presenta catálogo de `stage` ni `group`; hay que consultarlos con `/standings/stages` y `/standings/groups`.
El contenido de `coverage` (leagues) y `venue` (games), mencionados en el changelog, no aparece porque las muestras venían colapsadas.

## Granularidad y diferencias de parámetros

| Ruta | Qué identifica `id` | Otros identificadores |
|---|---|---|
| `/countries` | País | `code`: código de 2 caracteres |
| `/leagues` | Liga/copa | `country_id`: país; `code`: código de país |
| `/teams` | Equipo | `league`: id de liga; `country_id`: país |
| `/statistics` | No tiene `id` | `team`, `league` y `season` obligatorios |
| `/players` | Jugador | `team`: equipo |
| `/standings` | No tiene `id` | `team`: equipo; `league` y `season` obligatorios |
| `/games` | Partido | `team`: equipo; `league`: liga |
| `/games/statistics/teams` | Partido (string) | `ids`: hasta 20 partidos, formato `id-id-id` |
| `/games/statistics/players` | Partido (string) | `ids`: hasta 20 partidos; `player` + `season`: temporada de un jugador |
| `/games/h2h` | No tiene `id` | `h2h`: dos ids de equipo `id-id` |
| `/odds` | No tiene `id` | `game`: partido; `bookmaker`; `bet` |
| `/bookmakers` | Casa de apuestas | — |
| `/bets` | Mercado de apuesta | — |

Los IDs de ligas, equipos y jugadores son únicos y se conservan entre temporadas (y entre ligas/copas, para equipos y jugadores), según las fichas respectivas.
El `coverage` de cada liga refleja lo disponible al momento de la llamada; puede variar por temporada y `true` no garantiza 100% de datos.

## Inconsistencias del documento original

Se conservan sin corregir:

- Versión 1.5.2 en el encabezado vs. 1.5.6 en el changelog.
- `/games/h2h` se documenta como ruta, pero el ejemplo PHP llama a `/games` con `h2h=132-134`, y la respuesta dice `"get": "games"`.
- Las respuestas de `/games/statistics/teams` y `/games/statistics/players` dicen `"get": "games"`.
- `/bets`: la muestra dice `"results": 7` pero lista 19 objetos.
- `/standings/groups` declara respuestas 200 y 201.
- Los ejemplos PHP de `/standings/stages` y `/standings/groups` no envían `league` ni `season`, aunque son obligatorios.
- `/odds`: el ejemplo PHP usa `bet=1, bookmaker=6, league=12, season=2019-2020`; la respuesta muestra `bet=2, game=1912`.
- `/seasons` mezcla strings (`"2015-2016"`) e integers (`2017`) en el mismo arreglo.
- `/statistics` devuelve `response` como objeto (no arreglo) con `"results": 5`.
- El código de país de ejemplo es `EN`.

## Widgets y recursos complementarios

El texto incluye la documentación general de widgets API-SPORTS: `games`, `game`, `team`, `player`, `standings`, `league`, `leagues` y `h2h`.
También enumera widgets de Formula 1 (`races`, `race`, `driver`) y MMA (`fights`, `fight`, `fighter`): no se cuentan como funciones de basketball.
Se configuran con `<api-sports-widget data-type="config" data-key="..." data-sport="...">`.
Describe idiomas en/fr/es/it (`data-lang`), traducciones personalizadas (`data-custom-lang`), temas white/grey/dark/blue y CSS personalizado (`data-theme`),
destinos modal o selector CSS (`data-target-game`, `data-target-standings`, `data-target-team`, `data-target-player`, `data-target-league`), y depuración con `data-show-errors`.
Los widgets consumen la cuota de la cuenta y exponen la API key en el front; se recomienda restringir dominios/IP en el dashboard y usar caché (el ejemplo baja de 115 200 a 1 440 solicitudes/día con caché de 60 s).
Las imágenes y logos no descuentan la cuota diaria, pero tienen límites propios por segundo/minuto; el documento recomienda guardarlas del lado propio (ej. BunnyCDN) y advierte sobre derechos de terceros.
Las menciones de BunnyCDN, Aiven y Firebase son integraciones sugeridas, no rutas de API-BASKETBALL.

## Fichas por endpoint

### GET /status

Consulta cuenta, suscripción y consumo de solicitudes. La llamada no descuenta cuota diaria.

Fuente: sección Authentication › API-SPORTS Account.

**Descripción original:** You can also consult all this information directly through the API by calling the endpoint status. This call does not count against the daily quota.

Sin parámetros de consulta documentados.

**Notas:**

Está documentado en autenticación, fuera del grupo Endpoints.

Los valores Free, 100 y fechas del ejemplo no describen la suscripción del usuario.

**Campos observados en el ejemplo** (no son un esquema oficial):

| Ruta del campo | Tipos observados |
|---|---|
| `response` | object |
| `response.account` | object |
| `response.account.firstname` | string |
| `response.account.lastname` | string |
| `response.account.email` | string |
| `response.subscription` | object |
| `response.subscription.plan` | string |
| `response.subscription.end` | string |
| `response.subscription.active` | boolean |
| `response.requests` | object |
| `response.requests.current` | integer |
| `response.requests.limit_day` | integer |

**Ejemplo JSON original:**

```json
{
  "get": "status",
  "parameters": [],
  "errors": [],
  "results": 1,
  "response": {
    "account": {
      "firstname": "xxxx",
      "lastname": "XXXXXX",
      "email": "xxx@xxx.com"
    },
    "subscription": {
      "plan": "Free",
      "end": "2020-04-10T23:24:27+00:00",
      "active": true
    },
    "requests": {
      "current": 12,
      "limit_day": 100
    }
  }
}
```

### GET /timezone

Lista las zonas horarias disponibles para usar en el endpoint de partidos.

Fuente: sección Endpoints › Timezone.

**Descripción original:** Get the list of available timezone to be used in the games endpoint. This endpoint does not require any parameters.

Sin parámetros de consulta documentados.

**Notas:**

La muestra declara 425 resultados pero sólo enseña 5.

**Campos observados en el ejemplo:**

| Ruta del campo | Tipos observados |
|---|---|
| `response` | array |
| `response[]` | string |

**Ejemplo JSON original:**

```json
{
  "get": "timezone",
  "parameters": [],
  "errors": [],
  "results": 425,
  "response": [
    "Africa/Abidjan",
    "Africa/Accra",
    "Africa/Addis_Ababa",
    "Africa/Algiers",
    "Africa/Asmara"
  ]
}
```

### GET /seasons

Lista las temporadas válidas como filtro en otros endpoints.

Fuente: sección Endpoints › Seasons.

**Descripción original:** All seasons can be used in other endpoints as filters. This endpoint does not require any parameters.

Sin parámetros de consulta documentados.

**Notas:**

Las temporadas pueden ser `YYYY` (competiciones de un año) o `YYYY-YYYY` (competiciones que cruzan año, como la NBA).

La muestra mezcla strings e integers; es un ejemplo estático, no la cobertura actual.

**Campos observados en el ejemplo:**

| Ruta del campo | Tipos observados |
|---|---|
| `response` | array |
| `response[]` | string, integer |

**Ejemplo JSON original:**

```json
{
  "get": "seasons",
  "parameters": [],
  "errors": [],
  "results": 8,
  "response": [
    "2015-2016",
    "2016-2017",
    2017,
    "2017-2018",
    2018,
    "2018-2019",
    2019,
    "2019-2020"
  ]
}
```

### GET /countries

Lista los países disponibles.

Fuente: sección Endpoints › Countries.

**Descripción original:** Get the list of available countries. The id name and code fields can be used in other endpoints as filters. All the parameters of this endpoint can be used together.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `id` | No | integer The id of the country |
| `name` | No | string Example: name=USA The name of the country |
| `code` | No | string = 2 characters Example: code=EN The code of the country |
| `search` | No | string >= 3 characters Example: search=USA |

**Notas:**

Todos los parámetros se pueden combinar.

El objeto de la respuesta venía colapsado; no se conocen sus campos.

**Ejemplo JSON original:**

```json
{
  "get": "countries",
  "parameters": {
    "search": "usa"
  },
  "errors": [],
  "results": 1,
  "response": [
    {}
  ]
}
```

### GET /leagues

Lista ligas y copas disponibles, con su cobertura.

Fuente: sección Endpoints › Leagues.

**Descripción original:** Get the list of available leagues and cups. The league id are unique in the API and leagues keep it across all seasons. This endpoint also returns the coverage of each competition, which makes it possible to know what is available for leagues or cups. The values returned by the coverage indicate the data available at the moment you call the API, so for a competition that has not yet started, it is normal to have all the features set to False. This will be updated once the competition has started. The coverage of a competition can vary from season to season and values set to True do not guarantee 100% data availability. You can find all the leagues ids on our Dashboard. Most of the parameters of this endpoint can be used together.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `id` | No | integer The id of the league |
| `name` | No | string Example: name=NBA The name of the league |
| `country_id` | No | integer The id of the country |
| `country` | No | string Example: country=USA The name of the country |
| `type` | No | string Enum: "league" "cup" Example: type=league The type of the league |
| `season` | No | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2021-2022 The season of the league |
| `search` | No | string >= 3 characters Example: search=NBA The name of the league |
| `code` | No | string = 2 characters Example: code=FR The code of the country |

**Notas:**

“La mayoría” de los parámetros se pueden combinar; no se especifica cuáles no.

En los ejemplos de toda la documentación, la NBA usa `league=12`.

Los IDs de liga se consultan también en el dashboard.

El objeto de la respuesta (incluido `coverage`) venía colapsado.

**Ejemplo JSON original:**

```json
{
  "get": "leagues",
  "parameters": {
    "id": "12",
    "season": "2023-2024"
  },
  "errors": [],
  "results": 1,
  "response": [
    {}
  ]
}
```

### GET /teams

Consulta datos de equipos.

Fuente: sección Endpoints › Teams › teams.

**Descripción original:** Get data about teams. The team id are unique in the API and teams keep it among all the leagues/cups in which they participate. You can find all the teams ids on our Dashboard. This endpoint requires at least one parameter.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `id` | No | integer The id of the team |
| `name` | No | string Example: name=Denver Nuggets The name of the team |
| `country_id` | No | integer The id of the country |
| `country` | No | string The name of the country |
| `league` | No | integer The id of the league |
| `season` | No | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2021-2022 The season of the league |
| `search` | No | string >= 3 characters Example: search=Denver The name of the team |

**Notas:**

Requiere al menos un parámetro.

El ejemplo PHP usa `id=139`; la respuesta de muestra usa `name=Denver Nuggets`.

El objeto de la respuesta venía colapsado.

**Ejemplo JSON original:**

```json
{
  "get": "teams",
  "parameters": {
    "name": "Denver Nuggets"
  },
  "errors": [],
  "results": 1,
  "response": [
    {}
  ]
}
```

### GET /statistics

Estadísticas de un equipo en una liga y temporada.

Fuente: sección Endpoints › Teams › statistics.

**Descripción original:** No incluye texto descriptivo; sólo la tabla de parámetros.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2021-2022 The season of the league |
| `team` | Sí | integer The id of the team |
| `date` | No | string YYYY-MM-DD Example: date=2021-05-12 A Limit Date |

**Notas:**

`date` funciona como fecha límite: estadísticas acumuladas hasta ese día (interpretación del texto “A Limit Date”, no verificada).

`response` es un objeto, no un arreglo. Sus cinco sub-objetos venían colapsados.

El ejemplo PHP usa `season=2019-2020, team=139, league=12`.

**Campos observados en el ejemplo:**

| Ruta del campo | Tipos observados |
|---|---|
| `response` | object |
| `response.league` | object |
| `response.country` | object |
| `response.team` | object |
| `response.games` | object |
| `response.points` | object |

**Ejemplo JSON original:**

```json
{
  "get": "statistics",
  "parameters": {
    "league": "12",
    "season": "2019-2020",
    "team": "139"
  },
  "errors": [],
  "results": 5,
  "response": {
    "league": {},
    "country": {},
    "team": {},
    "games": {},
    "points": {}
  }
}
```

### GET /players

Consulta datos de jugadores.

Fuente: sección Endpoints › Players.

**Descripción original:** Get data about players. The players id are unique in the API and players keep it among all the leagues/cups in which they participate. This endpoint requires at least one parameter.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `id` | No | integer The id of the player |
| `team` | No | integer The id of the team |
| `season` | No | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2023-2024 A valid season |
| `search` | No | string >= 3 characters Example: search=Malith The name of the player |

**Notas:**

Requiere al menos un parámetro.

No hay parámetros `name` ni `country` (a diferencia de API-NBA).

La muestra devuelve 16 jugadores para `team=1, season=2023-2024`; los objetos venían colapsados.

**Ejemplo JSON original:**

```json
{
  "get": "players",
  "parameters": {
    "team": "1",
    "season": "2023-2024"
  },
  "errors": [],
  "results": 16,
  "response": [
    {}, {}, {}, {}, {}, {}, {}, {},
    {}, {}, {}, {}, {}, {}, {}, {}
  ]
}
```

### GET /standings

Clasificación de una liga y temporada.

Fuente: sección Endpoints › Standings › standings.

**Descripción original:** Get the standings for a league. Return a table of one or more rankings according to the league / cup. Some competitions have several rankings in a year, regular season, pre season etc… To know the list of available stages or groups you have to use the endpoint standings/stages or standings/groups. Standings are updated every hours.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2021-2022 The season of the league |
| `team` | No | integer The id of the team |
| `stage` | No | string Example: stage=NBA - Regular Season A valid stage |
| `group` | No | string Example: group=Eastern Conference A valid group |

**Notas:**

`league` y `season` son obligatorios.

Se actualiza cada hora.

`response` es un arreglo de arreglos (una tabla por ranking); el contenido venía colapsado.

**Ejemplo JSON original:**

```json
{
  "get": "standings",
  "parameters": {
    "league": "12",
    "season": "2019-2020",
    "team": "137"
  },
  "errors": [],
  "results": 1,
  "response": [
    []
  ]
}
```

### GET /standings/stages

Lista las fases disponibles de una liga para usar en `/standings`.

Fuente: sección Endpoints › Standings › standings/stages.

**Descripción original:** Get the list of available stages for a league to be used in the standings endpoint.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2021-2022 The season of the league |

**Campos observados en el ejemplo:**

| Ruta del campo | Tipos observados |
|---|---|
| `response` | array |
| `response[]` | string |

**Ejemplo JSON original:**

```json
{
  "get": "standings/stages",
  "parameters": {
    "league": "12",
    "season": "2019-2020"
  },
  "errors": [],
  "results": 1,
  "response": [
    "NBA - Regular Season"
  ]
}
```

### GET /standings/groups

Lista los grupos disponibles de una liga para usar en `/standings`.

Fuente: sección Endpoints › Standings › standings/groups.

**Descripción original:** Get the list of available groups for a league to be used in the standings endpoint.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2021-2022 The season of the league |

**Notas:**

Para la NBA, los grupos mezclan conferencias (`Western Conference`, `Eastern Conference`) y divisiones (`Atlantic`, `Southeast`, …).

Declara respuestas 200 OK y 201 Created.

**Campos observados en el ejemplo:**

| Ruta del campo | Tipos observados |
|---|---|
| `response` | array |
| `response[]` | string |

**Ejemplo JSON original:**

```json
{
  "get": "standings/groups",
  "parameters": {
    "league": "12",
    "season": "2019-2020"
  },
  "errors": [],
  "results": 8,
  "response": [
    "Western Conference",
    "Eastern Conference",
    "Atlantic",
    "Southeast",
    "Central",
    "Northwest",
    "Pacific",
    "Southwest"
  ]
}
```

### GET /games

Consulta partidos.

Fuente: sección Endpoints › Games › games.

**Descripción original:** For all requests to games you can add the query parameter timezone to your request in order to retrieve the list of games in the time zone of your choice like “Europe/London“. To know the list of available time zones you have to use the endpoint timezone. Games are updated every 15 seconds. This endpoint requires at least one parameter.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `id` | No | integer The id of the game |
| `date` | No | string YYYY-MM-DD Example: date=2019-11-23 A valid date |
| `league` | No | integer The id of the league |
| `season` | No | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2021-2022 The season of the league |
| `team` | No | integer The id of the team |
| `timezone` | No | string Example: timezone=Europe/London A valid timezone |

**Notas:**

Requiere al menos un parámetro.

Se actualiza cada 15 segundos.

Los estados están en la sección “Estados de partido”.

No hay parámetros `live`, `status`, `ids`, `from`, `to`, `last`, `next` ni `page`.

El objeto de la respuesta venía colapsado; el changelog indica que incluye `venue`.

**Ejemplo JSON original:**

```json
{
  "get": "games",
  "parameters": {
    "league": "12",
    "date": "2019-11-23",
    "team": "134",
    "timezone": "europe/london",
    "season": "2019-2020"
  },
  "errors": [],
  "results": 1,
  "response": [
    {}
  ]
}
```

### GET /games/statistics/teams

Estadísticas de equipos de uno o varios partidos.

Fuente: sección Endpoints › Games › teams statistics.

**Descripción original:** Get teams statistics from one or several games ids. Statistics are updated every 30-120 seconds. This endpoint need at least one parameter.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `id` | No | string The id of the game |
| `ids` | No | string Maximum of 20 games ids Value: "id-id-id" One or more games ids |

**Notas:**

Requiere al menos un parámetro.

`ids` acepta hasta 20 partidos separados por guion.

`id` es string aquí (integer en `/games`).

La respuesta dice `"get": "games"`. La muestra trae 2 objetos (uno por equipo, presumiblemente), colapsados.

**Ejemplo JSON original:**

```json
{
  "get": "games",
  "parameters": {
    "id": "391053"
  },
  "errors": [],
  "results": 2,
  "response": [
    {},
    {}
  ]
}
```

### GET /games/statistics/players

Estadísticas de jugadores por partido(s), o de un jugador en una temporada.

Fuente: sección Endpoints › Games › players statistics.

**Descripción original:** Get players statistics from one or several games ids. Also possible to get all statistics from a player id and a season. Statistics are updated every 30-120 seconds. This endpoint need at least one parameter.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `id` | No | string The id of the game |
| `ids` | No | string Maximum of 20 games ids Value: "id-id-id" One or more games ids |
| `player` | No | integer The id of the player |
| `season` | No | string A valid season |

**Notas:**

Requiere al menos un parámetro.

`id` identifica el partido, no al jugador; el jugador va en `player`.

La combinación `player` + `season` devuelve todas las estadísticas del jugador en la temporada.

La respuesta dice `"get": "games"`. La muestra trae 18 objetos colapsados.

**Ejemplo JSON original:**

```json
{
  "get": "games",
  "parameters": {
    "id": "391053"
  },
  "errors": [],
  "results": 18,
  "response": [
    {}, {}, {}, {}, {}, {}, {}, {}, {},
    {}, {}, {}, {}, {}, {}, {}, {}, {}
  ]
}
```

### GET /games/h2h

Enfrentamientos directos entre dos equipos.

Fuente: sección Endpoints › Games › h2h.

**Descripción original:** Get heads to heads between two teams.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `h2h` | Sí | string id-id Example: h2h=132-134 The ids of the teams |
| `date` | No | string YYYY-MM-DD Example: date=2019-12-05 A valid date |
| `league` | No | integer The id of the league |
| `season` | No | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2021-2022 The season of the league |
| `timezone` | No | string Example: timezone=Europe/London A valid timezone |

**Notas:**

`h2h` recibe dos IDs de equipo separados por guion.

La ruta documentada es `/games/h2h`, pero el ejemplo PHP llama a `/games?h2h=132-134`. No se verificó cuál responde.

**Ejemplo JSON original:**

```json
{
  "get": "games",
  "parameters": {
    "league": "12",
    "h2h": "132-134",
    "season": "2019-2020"
  },
  "errors": [],
  "results": 4,
  "response": [
    {}
  ]
}
```

### GET /odds

Cuotas pre-partido de partidos o ligas.

Fuente: sección Endpoints › Odds › odds.

**Descripción original:** Get odds from games or leagues. We provide pre-match odds between 1 and 7 days before the game. We keep a 7-day history (The availability of odds may vary according to the leagues, seasons, games and bookmakers). Odds are updated once a day.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `league` | No | integer The id of the league |
| `season` | No | string [ 4 .. 9 ] characters YYYY or YYYY-YYYY Example: season=2021-2022 The season of the league |
| `game` | No | integer The id of the game |
| `bookmaker` | No | integer The id of the bookmaker |
| `bet` | No | integer The id of the bet |

**Notas:**

Sólo cuotas pre-partido, de 1 a 7 días antes; no hay cuotas en vivo documentadas.

Historial de 7 días; se actualiza una vez al día.

No indica si requiere al menos un parámetro.

**Ejemplo JSON original:**

```json
{
  "get": "odds",
  "parameters": {
    "bet": "2",
    "game": "1912"
  },
  "errors": [],
  "results": 1,
  "response": [
    {}
  ]
}
```

### GET /bookmakers

Lista las casas de apuestas disponibles.

Fuente: sección Endpoints › Odds › bookmakers.

**Descripción original:** Get all available bookmakers. All bookmakers id can be used in endpoint odds as filters.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `id` | No | integer The id of the bookmaker |
| `search` | No | string >= 3 characters Example: search=Bwin The name of the bookmaker |

**Notas:**

La muestra trae 15 casas, colapsadas.

**Ejemplo JSON original:**

```json
{
  "get": "bookmakers",
  "parameters": [],
  "errors": [],
  "results": 15,
  "response": [
    {}, {}, {}, {}, {}, {}, {}, {},
    {}, {}, {}, {}, {}, {}, {}
  ]
}
```

### GET /bets

Lista los mercados de apuesta disponibles.

Fuente: sección Endpoints › Odds › bets.

**Descripción original:** Get all available bets. All bets id can be used in endpoint odds as filters.

| Parámetro | Required en tabla | Especificación original |
|---|---|---|
| `id` | No | integer The id of the bet |
| `search` | No | string >= 3 characters Example: search=under The name of the bet |

**Notas:**

La muestra declara `"results": 7` pero lista 19 objetos colapsados.

**Ejemplo JSON original:**

```json
{
  "get": "bets",
  "parameters": {
    "search": "under"
  },
  "errors": [],
  "results": 7,
  "response": [
    {}, {}, {}, {}, {}, {}, {}, {}, {}, {},
    {}, {}, {}, {}, {}, {}, {}, {}, {}
  ]
}
```
