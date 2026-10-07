# API-FOOTBALL 3.9.3 — Inventario extraído del HTML

## Alcance

Fuente: `Pasted text(20260913-180036).txt`. Extracción local realizada el 13 de septiembre de 2026. **39 rutas GET: 38 operaciones y `/status`**. No se consultó la API ni se verificó una suscripción. El HTML **no contiene documentación de API-NBA**; esa parte sigue pendiente.

URL base: `https://v3.football.api-sports.io`. Autenticación: encabezado `x-apisports-key`.

Este documento no es el OpenAPI oficial. El JSON acompañante conserva los ejemplos de respuesta del documento, no datos actuales. Los ejemplos pueden contener erratas del original.

En la tabla, `*` significa que el parámetro está marcado como `required` en su tabla. Su ausencia no elimina requisitos condicionales; las notas los distinguen.

## Índice de endpoints

| # | Método y ruta | Función | Parámetros de consulta |
|---|---|---|---|
| 1 | `GET /status` | Consulta cuenta, suscripción activa y consumo de solicitudes. La llamada no descuenta cuota diaria. | Sin parámetros de consulta documentados. |
| 2 | `GET /timezone` | Lista las zonas horarias disponibles para consultar partidos. | Sin parámetros de consulta documentados. |
| 3 | `GET /countries` | Lista países disponibles para competiciones, con nombre, código y bandera. | `name`, `code`, `search` |
| 4 | `GET /leagues` | Lista ligas y copas, temporadas y cobertura de datos por competición y temporada. | `id`, `name`, `country`, `code`, `season`, `team`, `type`, `current`, `search`, `last` |
| 5 | `GET /leagues/seasons` | Lista los años de temporada disponibles en la API. | Sin parámetros de consulta documentados. |
| 6 | `GET /teams` | Consulta información de equipos y su estadio asociado. | `id`, `name`, `league`, `season`, `country`, `code`, `venue`, `search` |
| 7 | `GET /teams/statistics` | Estadísticas de un equipo en una competición y temporada; permite una fecha límite. | `league *`, `season *`, `team *`, `date` |
| 8 | `GET /teams/seasons` | Lista las temporadas disponibles para un equipo. | `team *` |
| 9 | `GET /teams/countries` | Lista los países disponibles para el catálogo de equipos. | Sin parámetros de consulta documentados. |
| 10 | `GET /venues` | Consulta estadios: identidad, ubicación, capacidad, superficie e imagen, según el ejemplo. | `id`, `name`, `city`, `country`, `search` |
| 11 | `GET /standings` | Consulta clasificaciones por competición o equipo, con posibles grupos o fases. | `league`, `season *`, `team` |
| 12 | `GET /fixtures/rounds` | Lista jornadas o rondas; permite incluir sus fechas y seleccionar la actual. | `league *`, `season *`, `current`, `dates`, `timezone` |
| 13 | `GET /fixtures` | Consulta partidos, calendario, estados, marcadores y datos relacionados mediante filtros. | `id`, `ids`, `live`, `date`, `league`, `season`, `team`, `last`, `next`, `from`, `to`, `round`, `status`, `venue`, `timezone` |
| 14 | `GET /fixtures/headtohead` | Consulta enfrentamientos entre dos equipos, con filtros temporales y de competición. | `h2h *`, `date`, `league`, `season`, `last`, `next`, `from`, `to`, `status`, `venue`, `timezone` |
| 15 | `GET /fixtures/statistics` | Estadísticas de equipos por partido. El parámetro half añade datos por mitades desde 2024. | `fixture *`, `team`, `type`, `half` |
| 16 | `GET /fixtures/events` | Eventos del partido: goles, tarjetas, sustituciones y VAR. | `fixture *`, `team`, `player`, `type` |
| 17 | `GET /fixtures/lineups` | Alineaciones, formación, entrenador, titulares, suplentes y posiciones en la cuadrícula. | `fixture *`, `team`, `player`, `type` |
| 18 | `GET /fixtures/players` | Estadísticas individuales de jugadores en un partido. | `fixture *`, `team` |
| 19 | `GET /injuries` | Ausencias y dudas de jugadores para partidos: lesionados, suspendidos u otros motivos. | `league`, `season`, `fixture`, `team`, `player`, `date`, `ids`, `timezone` |
| 20 | `GET /predictions` | Predicciones del proveedor y comparaciones entre equipos; no utilizan cuotas de casas de apuestas. | `fixture *` |
| 21 | `GET /coachs` | Información y trayectoria de entrenadores. La ruta se escribe coachs. | `id`, `team`, `search` |
| 22 | `GET /players/seasons` | Temporadas disponibles para estadísticas de jugadores; permite filtrar por jugador. | `player` |
| 23 | `GET /players/profiles` | Catálogo de perfiles de jugadores; admite consulta completa paginada. | `player`, `search`, `page` |
| 24 | `GET /players` | Perfiles y estadísticas por jugador, equipo, competición y temporada. | `id`, `team`, `league`, `season`, `search`, `page` |
| 25 | `GET /players/squads` | Plantilla actual de un equipo, o equipos asociados a un jugador. | `team`, `player` |
| 26 | `GET /players/teams` | Equipos y temporadas en los que jugó un jugador durante su carrera. | `player *` |
| 27 | `GET /players/topscorers` | Los 20 jugadores mejor clasificados como goleadores, con los desempates documentados. | `league *`, `season *` |
| 28 | `GET /players/topassists` | Los 20 jugadores mejor clasificados por asistencias, con los desempates documentados. | `league *`, `season *` |
| 29 | `GET /players/topyellowcards` | Los 20 jugadores con más tarjetas amarillas, con los desempates documentados. | `league *`, `season *` |
| 30 | `GET /players/topredcards` | Los 20 jugadores con más tarjetas rojas, con los desempates documentados. | `league *`, `season *` |
| 31 | `GET /transfers` | Transferencias disponibles por jugador o equipo. | `player`, `team` |
| 32 | `GET /trophies` | Trofeos disponibles por jugador o entrenador, individualmente o en lotes. | `player`, `players`, `coach`, `coachs` |
| 33 | `GET /sidelined` | Periodos de baja disponibles por jugador o entrenador, individualmente o en lotes. | `player`, `players`, `coach`, `coachs` |
| 34 | `GET /odds/live` | Cuotas en vivo de partidos próximos, en curso o recién finalizados; no conserva historial. | `fixture`, `league`, `bet` |
| 35 | `GET /odds/live/bets` | Catálogo de mercados de cuotas en vivo; IDs no compatibles con mercados prepartido. | `id`, `search` |
| 36 | `GET /odds` | Cuotas prepartido por partido, competición o fecha, con filtros de casa y mercado. | `fixture`, `league`, `season`, `date`, `timezone`, `page`, `bookmaker`, `bet` |
| 37 | `GET /odds/mapping` | Lista paginada de partidos disponibles para consultar cuotas prepartido. | `page` |
| 38 | `GET /odds/bookmakers` | Catálogo de casas de apuestas y sus IDs para cuotas prepartido. | `id`, `search` |
| 39 | `GET /odds/bets` | Catálogo de mercados prepartido; IDs no compatibles con mercados en vivo. | `id`, `search` |

## Límites y detalles de recolección

La cobertura de `/leagues` es por competición y temporada; `true` no garantiza datos para todos los partidos. Los IDs de equipos se conservan entre competiciones. La repetición de un mismo ID no crea un equipo diferente. [Fuente: Leagues](https://www.api-football.com/documentation-v3#tag/Leagues/operation/get-leagues) · [Fuente: Teams](https://www.api-football.com/documentation-v3#tag/Teams/operation/get-teams)

| Ruta paginada | Resultados por página |
|---|---|
| `/players/profiles` | 250 |
| `/players` | 20 |
| `/odds` | 10 |
| `/odds/mapping` | 100 |

`/fixtures?ids=` e `/injuries?ids=` admiten hasta 20 IDs de partidos por consulta. `/trophies` y `/sidelined` admiten lotes de hasta 20 jugadores o entrenadores en sus parámetros plurales.

Cuotas prepartido: entre 1 y 14 días antes del encuentro, 7 días de historial y actualización indicativa de 3 horas. Cuotas en vivo: sin historial; entrada de partidos de 15 a 5 minutos antes y retirada de 5 a 20 minutos después; actualización indicativa de 5 a 60 segundos. Los mercados prepartido y en vivo usan catálogos incompatibles.

## Funciones complementarias del documento

Los widgets `games`, `game`, `team`, `player`, `standings`, `league`, `leagues` y `h2h` son componentes de presentación, no rutas GET adicionales. Admiten idioma español, temas y personalización; consumen solicitudes de la cuenta. La documentación también explica imágenes y logotipos, ejemplos en varios lenguajes, caché y enlaces a integraciones con CDN/bases de datos.

## Fichas técnicas por endpoint

### 1. `GET /status`

Consulta cuenta, suscripción activa y consumo de solicitudes. La llamada no descuenta cuota diaria.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#section/Authentication/API-SPORTS-Account); comienza en la línea 95 del HTML adjunto.

No se documentan parámetros de consulta en esta sección.

**Nota:** La información procede de la sección de autenticación, no del grupo de 38 operaciones.

**Campos del primer nivel del resultado de ejemplo:** `account`, `subscription`, `requests`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

You can also consult all this information directly through the API by calling the endpoint status. This call does not count against the daily quota.

**Ejemplo original (no ejecutado):**

```text
get("https://v3.football.api-sports.io/status");
```

### 2. `GET /timezone`

Lista las zonas horarias disponibles para consultar partidos.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Timezone/operation/get-timezone); comienza en la línea 924 del HTML adjunto.

No se documentan parámetros de consulta en esta sección.

**Actualización del proveedor:** This endpoint contains all the existing timezone, it is not updated.

**Llamadas recomendadas por el proveedor:** 1 call when you need.

**Descripción original, sin etiquetas HTML:**

Get the list of available timezone to be used in the fixtures endpoint. This endpoint does not require any parameters. Update Frequency : This endpoint contains all the existing timezone, it is not updated. Recommended Calls : 1 call when you need.

**Ejemplo original (no ejecutado):**

```text
$client = new http\Client;
$request = new http\Client\Request;

$request->setRequestUrl('https://v3.football.api-sports.io/timezone');
$request->setRequestMethod('GET');
$request->setHeaders(array(
	'x-apisports-key' => 'XxXxXxXxXxXxXxXxXxXxXxXx'
));

$client->enqueue($request)->send();
$response = $client->getResponse();

echo $response->getBody();

```

### 3. `GET /countries`

Lista países disponibles para competiciones, con nombre, código y bandera.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Countries/operation/get-countries); comienza en la línea 949 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `name` | No; revisar condiciones | string The name of the country |
| `code` | No; revisar condiciones | string [ 2 .. 6 ] characters FR, GB-ENG, IT… The Alpha code of the country |
| `search` | No; revisar condiciones | string = 3 characters The name of the country |

**Actualización del proveedor:** This endpoint is updated each time a new league from a country not covered by the API is added.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Nota:** El HTML muestra search = 3 caracteres, pero un ejemplo utiliza search=engl. Se conserva la discrepancia; no se determina aquí la validación real.

**Campos del primer nivel del resultado de ejemplo:** `name`, `code`, `flag`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the list of available countries for the leagues endpoint. The name and code fields can be used in other endpoints as filters. To get the flag of a country you have to call the following url: https://media.api-sports.io/flags/{country_code}.svg Examples available in Request samples "Use Cases". All the parameters of this endpoint can be used together. Update Frequency : This endpoint is updated each time a new league from a country not covered by the API is added. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all available countries across all {seasons} and competitions
get("https://v3.football.api-sports.io/countries");

// Get all available countries from one country {name}
get("https://v3.football.api-sports.io/countries?name=england");

// Get all available countries from one country {code}
get("https://v3.football.api-sports.io/countries?code=fr");

// Allows you to search for a countries in relation to a country {name}
get("https://v3.football.api-sports.io/countries?search=engl");

```

### 4. `GET /leagues`

Lista ligas y copas, temporadas y cobertura de datos por competición y temporada.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Leagues/operation/get-leagues); comienza en la línea 978 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `id` | No; revisar condiciones | integer The id of the league |
| `name` | No; revisar condiciones | string The name of the league |
| `country` | No; revisar condiciones | string The country name of the league |
| `code` | No; revisar condiciones | string [ 2 .. 6 ] characters FR, GB-ENG, IT… The Alpha code of the country |
| `season` | No; revisar condiciones | integer = 4 characters YYYY The season of the league |
| `team` | No; revisar condiciones | integer The id of the team |
| `type` | No; revisar condiciones | string Enum: "league" "cup" The type of the league |
| `current` | No; revisar condiciones | string Return the list of active seasons or the las... Show pattern Enum: "true" "false" The state of the league |
| `search` | No; revisar condiciones | string >= 3 characters The name or the country of the league |
| `last` | No; revisar condiciones | integer <= 2 characters The X last leagues/cups added in the API |

**Actualización del proveedor:** This endpoint is updated several times a day.

**Llamadas recomendadas por el proveedor:** 1 call per hour.

**Nota:** La cobertura puede variar por temporada. True no garantiza disponibilidad completa. Antes del comienzo de una competición, False puede ser temporal.

**Nota:** El ID de la competición se conserva entre temporadas.

**Nota:** Algunos textos de patrones están truncados en el HTML. Un ejemplo contiene id=61¤t=true; se preserva como ejemplo original, no como llamada validada.

**Campos del primer nivel del resultado de ejemplo:** `league`, `country`, `seasons`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the list of available leagues and cups. The league id are unique in the API and leagues keep it across all seasons To get the logo of a competition you have to call the following url: https://media.api-sports.io/football/leagues/{league_id}.png This endpoint also returns the coverage of each competition, which makes it possible to know what is available for that league or cup. The values returned by the coverage indicate the data available at the moment you call the API, so for a competition that has not yet started, it is normal to have all the features set to False . This will be updated once the competition has started. You can find all the leagues ids on our Dashboard . Example : "coverage" : { "fixtures" : { "events" : true , "lineups" : true , "statistics_fixtures" : false , "statistics_players" : false } , "standings" : true , "players" : true , "top_scorers" : true , "top_assists" : true , "top_cards" : true , "injuries" : true , "predictions" : true , "odds" : false } In this example we can deduce that the competition does not have the following features: statistics_fixtures , statistics_players , odds because it is set to False . The coverage of a competition can vary from season to season and values set to True do not guarantee 100% data availability. Some competitions, such as the friendlies , are exceptions to the coverage indicated in the leagues endpoint, and the data available may differ depending on the match, including livescore, events, lineups, statistics and players. Competitions are automatically renewed by the API when a new season is available. There may be a delay between the announcement of the official calendar and the availability of data in the API. For Cup competitions, fixtures are automatically added when the two participating teams are known. For example if the current phase is the 8th final, the quarter final will be added once the teams playing this phase are known. Examples available in Request samples "Use Cases". Most of the parameters of this endpoint can be used together. Update Frequency : This endpoint is updated several times a day. Recommended Calls : 1 call per hour.

**Ejemplo original (no ejecutado):**

```text
// Allows to retrieve all the seasons available for a league/cup
get("https://v3.football.api-sports.io/leagues?id=39");

// Get all leagues from one league {name}
get("https://v3.football.api-sports.io/leagues?name=premier league");

// Get all leagues from one {country}
// You can find the available {country} by using the endpoint country
get("https://v3.football.api-sports.io/leagues?country=england");

// Get all leagues from one country {code} (GB, FR, IT etc..)
// You can find the available country {code} by using the endpoint country
get("https://v3.football.api-sports.io/leagues?code=gb");

// Get all leagues from one {season}
// You can find the available {season} by using the endpoint seasons
get("https://v3.football.api-sports.io/leagues?season=2019");

// Get one league from one league {id} & {season}
get("https://v3.football.api-sports.io/leagues?season=2019&id=39");

// Get all leagues in which the {team} has played at least one match
get("https://v3.football.api-sports.io/leagues?team=33");

// Allows you to search for a league in relation to a league {name} or {country}
get("https://v3.football.api-sports.io/leagues?search=premier league");
get("https://v3.football.api-sports.io/leagues?search=England");

// Get all leagues from one {type}
get("https://v3.football.api-sports.io/leagues?type=league");

// Get all leagues where the season is in progress or not
get("https://v3.football.api-sports.io/leagues?current=true");

// Get the last 99 leagues or cups added to the API
get("https://v3.football.api-sports.io/leagues?last=99");

// It’s possible to make requests by mixing the available parameters
get("https://v3.football.api-sports.io/leagues?season=2019&country=england&type=league");
get("https://v3.football.api-sports.io/leagues?team=85&season=2019");
get("https://v3.football.api-sports.io/leagues?id=61¤t=true&type=league");

```

### 5. `GET /leagues/seasons`

Lista los años de temporada disponibles en la API.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Leagues/operation/get-seasons); comienza en la línea 1074 del HTML adjunto.

No se documentan parámetros de consulta en esta sección.

**Actualización del proveedor:** This endpoint is updated each time a new league is added.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Descripción original, sin etiquetas HTML:**

Get the list of available seasons. All seasons are only 4-digit keys , so for a league whose season is 2018-2019 like the English Premier League (EPL), the 2018-2019 season in the API will be 2018 . All seasons can be used in other endpoints as filters. This endpoint does not require any parameters. Update Frequency : This endpoint is updated each time a new league is added. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
$client = new http\Client;
$request = new http\Client\Request;

$request->setRequestUrl('https://v3.football.api-sports.io/leagues/seasons');
$request->setRequestMethod('GET');
$request->setHeaders(array(
	'x-apisports-key' => 'XxXxXxXxXxXxXxXxXxXxXxXx'
));

$client->enqueue($request)->send();
$response = $client->getResponse();

echo $response->getBody();

```

### 6. `GET /teams`

Consulta información de equipos y su estadio asociado.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Teams/operation/get-teams); comienza en la línea 1101 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `id` | No; revisar condiciones | integer The id of the team |
| `name` | No; revisar condiciones | string The name of the team |
| `league` | No; revisar condiciones | integer The id of the league |
| `season` | No; revisar condiciones | integer = 4 characters YYYY The season of the league |
| `country` | No; revisar condiciones | string The country name of the team |
| `code` | No; revisar condiciones | string = 3 characters The code of the team |
| `venue` | No; revisar condiciones | integer The id of the venue |
| `search` | No; revisar condiciones | string >= 3 characters The name or the country name of the team |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Nota:** Requiere al menos un parámetro. Para obtener los equipos de una liga y temporada, el ejemplo combina league y season.

**Nota:** El ID del equipo es único y se conserva entre ligas/copas.

**Campos del primer nivel del resultado de ejemplo:** `team`, `venue`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the list of available teams. The team id are unique in the API and teams keep it among all the leagues/cups in which they participate. To get the logo of a team you have to call the following url: https://media.api-sports.io/football/teams/{team_id}.png You can find all the teams ids on our Dashboard . Examples available in Request samples "Use Cases". All the parameters of this endpoint can be used together. This endpoint requires at least one parameter. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day. Tutorials : HOW TO GET ALL TEAMS AND PLAYERS FROM A LEAGUE ID

**Ejemplo original (no ejecutado):**

```text
// Get one team from one team {id}
get("https://v3.football.api-sports.io/teams?id=33");

// Get one team from one team {name}
get("https://v3.football.api-sports.io/teams?name=manchester united");

// Get all teams from one {league} & {season}
get("https://v3.football.api-sports.io/teams?league=39&season=2019");

// Get teams from one team {country}
get("https://v3.football.api-sports.io/teams?country=england");

// Get teams from one team {code}
get("https://v3.football.api-sports.io/teams?code=FRA");

// Get teams from one venue {id}
get("https://v3.football.api-sports.io/teams?venue=789");

// Allows you to search for a team in relation to a team {name} or {country}
get("https://v3.football.api-sports.io/teams?search=manches");
get("https://v3.football.api-sports.io/teams?search=England");

```

### 7. `GET /teams/statistics`

Estadísticas de un equipo en una competición y temporada; permite una fecha límite.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Teams/operation/get-teams-statistics); comienza en la línea 1155 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | integer = 4 characters YYYY The season of the league |
| `team` | Sí | integer The id of the team |
| `date` | No; revisar condiciones | string YYYY-MM-DD The limit date |

**Actualización del proveedor:** This endpoint is updated twice a day.

**Llamadas recomendadas por el proveedor:** 1 call per day for the teams who have at least one fixture during the day otherwise 1 call per week.

**Nota:** league, season y team aparecen marcados required. date limita el cálculo desde el inicio de temporada hasta la fecha indicada.

**Nota:** Los bloques goals.for.under_over y goals.against.under_over del ejemplo son separados; no deben confundirse automáticamente con el total de goles del partido.

**Campos del primer nivel del resultado de ejemplo:** `league`, `team`, `form`, `fixtures`, `goals`, `biggest`, `clean_sheet`, `failed_to_score`, `penalty`, `lineups`, `cards`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Returns the statistics of a team in relation to a given competition and season. It is possible to add the date parameter to calculate statistics from the beginning of the season to the given date. By default the API returns the statistics of all games played by the team for the competition and the season. Update Frequency : This endpoint is updated twice a day. Recommended Calls : 1 call per day for the teams who have at least one fixture during the day otherwise 1 call per week. Here is an example of what can be achieved

**Ejemplo original (no ejecutado):**

```text
// Get all statistics for a {team} in a {league} & {season}
get("https://v3.football.api-sports.io/teams/statistics?league=39&team=33&season=2019");

//Get all statistics for a {team} in a {league} & {season} with a end {date}
get("https://v3.football.api-sports.io/teams/statistics?league=39&team=33&season=2019&date=2019-10-08");

```

### 8. `GET /teams/seasons`

Lista las temporadas disponibles para un equipo.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Teams/operation/get-teams-seasons); comienza en la línea 1178 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `team` | Sí | integer The id of the team |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Descripción original, sin etiquetas HTML:**

Get the list of seasons available for a team. Examples available in Request samples "Use Cases". This endpoint requires at least one parameter. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all seasons available for a team from one team {id}
get("https://v3.football.api-sports.io/teams/seasons?team=33");

```

### 9. `GET /teams/countries`

Lista los países disponibles para el catálogo de equipos.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Teams/operation/get-teams-countries); comienza en la línea 1194 del HTML adjunto.

No se documentan parámetros de consulta en esta sección.

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `name`, `code`, `flag`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the list of countries available for the teams endpoint. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all countries available for the teams endpoints
get("https://v3.football.api-sports.io/teams/countries");

```

### 10. `GET /venues`

Consulta estadios: identidad, ubicación, capacidad, superficie e imagen, según el ejemplo.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Venues/operation/get-venues); comienza en la línea 1205 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `id` | No; revisar condiciones | integer The id of the venue |
| `name` | No; revisar condiciones | string The name of the venue |
| `city` | No; revisar condiciones | string The city of the venue |
| `country` | No; revisar condiciones | string The country name of the venue |
| `search` | No; revisar condiciones | string >= 3 characters The name, city or the country of the venue |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Nota:** Requiere al menos un parámetro.

**Campos del primer nivel del resultado de ejemplo:** `id`, `name`, `address`, `city`, `country`, `capacity`, `surface`, `image`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the list of available venues. The venue id are unique in the API. To get the image of a venue you have to call the following url: https://media.api-sports.io/football/venues/{venue_id}.png Examples available in Request samples "Use Cases". All the parameters of this endpoint can be used together. This endpoint requires at least one parameter. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get one venue from venue {id}
get("https://v3.football.api-sports.io/venues?id=556");

// Get one venue from venue {name}
get("https://v3.football.api-sports.io/venues?name=Old Trafford");

// Get all venues from {city}
get("https://v3.football.api-sports.io/venues?city=manchester");

// Get venues from {country}
get("https://v3.football.api-sports.io/venues?country=england");

// Allows you to search for a venues in relation to a venue {name}, {city} or {country}
get("https://v3.football.api-sports.io/venues?search=trafford");
get("https://v3.football.api-sports.io/venues?search=manches");
get("https://v3.football.api-sports.io/venues?search=England");

```

### 11. `GET /standings`

Consulta clasificaciones por competición o equipo, con posibles grupos o fases.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Standings/operation/get-standings); comienza en la línea 1244 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `league` | No; revisar condiciones | integer The id of the league |
| `season` | Sí | integer = 4 characters YYYY The season of the league |
| `team` | No; revisar condiciones | integer The id of the team |

**Actualización del proveedor:** This endpoint is updated every hour.

**Llamadas recomendadas por el proveedor:** 1 call per hour for the leagues or teams who have at least one fixture in progress otherwise 1 call per day.

**Nota:** season aparece marcado required. Las consultas de ejemplo lo combinan con league o team.

**Nota:** Puede devolver varios rankings por fase, grupo, apertura o clausura.

**Campos del primer nivel del resultado de ejemplo:** `league`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the standings for a league or a team. Return a table of one or more rankings according to the league / cup. Some competitions have several rankings in a year, group phase, opening ranking, closing ranking etc… Examples available in Request samples "Use Cases". Most of the parameters of this endpoint can be used together. Update Frequency : This endpoint is updated every hour. Recommended Calls : 1 call per hour for the leagues or teams who have at least one fixture in progress otherwise 1 call per day. Tutorials : HOW TO GET STANDINGS FOR ALL CURRENT SEASONS

**Ejemplo original (no ejecutado):**

```text
// Get all Standings from one {league} & {season}
get("https://v3.football.api-sports.io/standings?league=39&season=2019");

// Get all Standings from one {league} & {season} & {team}
get("https://v3.football.api-sports.io/standings?league=39&team=33&season=2019");

// Get all Standings from one {team} & {season}
get("https://v3.football.api-sports.io/standings?team=33&season=2019");

```

### 12. `GET /fixtures/rounds`

Lista jornadas o rondas; permite incluir sus fechas y seleccionar la actual.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures-rounds); comienza en la línea 1276 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | integer = 4 characters YYYY The season of the league |
| `current` | No; revisar condiciones | boolean Enum: "true" "false" The current round only |
| `dates` | No; revisar condiciones | boolean Default: false Enum: "true" "false" Add the dates of each round in the response |
| `timezone` | No; revisar condiciones | string A valid timezone from the endpoint Timezone |

**Actualización del proveedor:** This endpoint is updated every day.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Descripción original, sin etiquetas HTML:**

Get the rounds for a league or a cup. The round can be used in endpoint fixtures as filters Examples available in Request samples "Use Cases". Update Frequency : This endpoint is updated every day. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all available rounds from one {league} & {season}
get("https://v3.football.api-sports.io/fixtures/rounds?league=39&season=2019");

// Get all available rounds from one {league} & {season} With the dates of each round
get("https://v3.football.api-sports.io/fixtures/rounds?league=39&season=2019&dates=true");

// Get current round from one {league} & {season}
get("https://v3.football.api-sports.io/fixtures/rounds?league=39&season=2019&current=true");

```

### 13. `GET /fixtures`

Consulta partidos, calendario, estados, marcadores y datos relacionados mediante filtros.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures); comienza en la línea 1302 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `id` | No; revisar condiciones | integer Value: "id" The id of the fixture |
| `ids` | No; revisar condiciones | string Maximum of 20 fixtures ids Value: "id-id-id" One or more fixture ids |
| `live` | No; revisar condiciones | string Enum: "all" "id-id" All or several leagues ids |
| `date` | No; revisar condiciones | string YYYY-MM-DD A valid date |
| `league` | No; revisar condiciones | integer The id of the league |
| `season` | No; revisar condiciones | integer = 4 characters YYYY The season of the league |
| `team` | No; revisar condiciones | integer The id of the team |
| `last` | No; revisar condiciones | integer <= 2 characters For the X last fixtures |
| `next` | No; revisar condiciones | integer <= 2 characters For the X next fixtures |
| `from` | No; revisar condiciones | string YYYY-MM-DD A valid date |
| `to` | No; revisar condiciones | string YYYY-MM-DD A valid date |
| `round` | No; revisar condiciones | string The round of the fixture |
| `status` | No; revisar condiciones | string Enum: "NS" "NS-PST-FT" One or more fixture status short |
| `venue` | No; revisar condiciones | integer The venue id of the fixture |
| `timezone` | No; revisar condiciones | string A valid timezone from the endpoint Timezone |

**Actualización del proveedor:** This endpoint is updated every 15 seconds.

**Llamadas recomendadas por el proveedor:** 1 call per minute for the leagues, teams, fixtures who have at least one fixture in progress otherwise 1 call per day.

**Nota:** ids admite como máximo 20 IDs separados por guiones.

**Nota:** Los ejemplos de id e ids incluyen eventos, alineaciones, estadísticas de equipos y estadísticas de jugadores, según disponibilidad.

**Nota:** live admite all o una lista de IDs de ligas; no se debe confundir con una lista de IDs de partidos.

**Nota:** El ID del partido no cambia. En competiciones sin livescore, un estado NS puede mantenerse hasta que el resultado final se actualice; el documento menciona demoras de hasta 48 horas.

**Nota:** La tabla de estados contiene una descripción de HT que dice Finished in the regular time, aunque el nombre es Halftime y el tipo In Play. Se conserva la inconsistencia sin convertir esa descripción en una regla de negocio.

**Campos del primer nivel del resultado de ejemplo:** `fixture`, `league`, `teams`, `goals`, `score`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

For all requests to fixtures you can add the query parameter timezone to your request in order to retrieve the list of matches in the time zone of your choice like “Europe/London“ To know the list of available time zones you have to use the endpoint timezone. Available fixtures status SHORT LONG TYPE DESCRIPTION TBD Time To Be Defined Scheduled Scheduled but date and time are not known NS Not Started Scheduled 1H First Half, Kick Off In Play First half in play HT Halftime In Play Finished in the regular time 2H Second Half, 2nd Half Started In Play Second half in play ET Extra Time In Play Extra time in play BT Break Time In Play Break during extra time P Penalty In Progress In Play Penaly played after extra time SUSP Match Suspended In Play Suspended by referee's decision, may be rescheduled another day INT Match Interrupted In Play Interrupted by referee's decision, should resume in a few minutes FT Match Finished Finished Finished in the regular time AET Match Finished Finished Finished after extra time without going to the penalty shootout PEN Match Finished Finished Finished after the penalty shootout PST Match Postponed Postponed Postponed to another day, once the new date and time is known the status will change to Not Started CANC Match Cancelled Cancelled Cancelled, match will not be played ABD Match Abandoned Abandoned Abandoned for various reasons (Bad Weather, Safety, Floodlights, Playing Staff Or Referees), Can be rescheduled or not, it depends on the competition AWD Technical Loss Not Played WO WalkOver Not Played Victory by forfeit or absence of competitor LIVE In Progress In Play Used in very rare cases. It indicates a fixture in progress but the data indicating the half-time or elapsed time are not available Fixtures with the status TBD may indicate an incorrect fixture date or time because the fixture date or time is not yet known or final. Fixtures with this status are checked and updated daily. The same applies to fixtures with the status PST , CANC . The fixtures ids are unique and specific to each fixture. In no case an ID will change. Not all competitions have livescore available and only have final result . In this case, the status remains in NS and will be updated in the minutes/hours following the match (this can take up to 48 hours, depending on the competition). Although the data is updated every 15 seconds, depending on the competition there may be a delay between reality and the availability of data in the API. Update Frequency : This endpoint is updated every 15 seconds. Recommended Calls : 1 call per minute for the leagues, teams, fixtures who have at least one fixture in progress otherwise 1 call per day. Here are several examples of what can be achieved

**Ejemplo original (no ejecutado):**

```text
// Get fixture from one fixture {id}
// In this request events, lineups, statistics fixture and players fixture are returned in the response
get("https://v3.football.api-sports.io/fixtures?id=215662");

// Get fixture from severals fixtures {ids}
// In this request events, lineups, statistics fixture and players fixture are returned in the response
get("https://v3.football.api-sports.io/fixtures?ids=215662-215663-215664-215665-215666-215667");

// Get all available fixtures in play
// In this request events are returned in the response
get("https://v3.football.api-sports.io/fixtures?live=all");

// Get all available fixtures in play filter by several {league}
// In this request events are returned in the response
get("https://v3.football.api-sports.io/fixtures?live=39-61-48");

// Get all available fixtures from one {league} & {season}
get("https://v3.football.api-sports.io/fixtures?league=39&season=2019");

// Get all available fixtures from one {date}
get("https://v3.football.api-sports.io/fixtures?date=2019-10-22");

// Get next X available fixtures
get("https://v3.football.api-sports.io/fixtures?next=15");

// Get last X available fixtures
get("https://v3.football.api-sports.io/fixtures?last=15");

// It’s possible to make requests by mixing the available parameters
get("https://v3.football.api-sports.io/fixtures?date=2020-01-30&league=61&season=2019");
get("https://v3.football.api-sports.io/fixtures?league=61&next=10");
get("https://v3.football.api-sports.io/fixtures?venue=358&next=10");
get("https://v3.football.api-sports.io/fixtures?league=61&last=10&status=ft");
get("https://v3.football.api-sports.io/fixtures?team=85&last=10&timezone=Europe/london");
get("https://v3.football.api-sports.io/fixtures?team=85&season=2019&from=2019-07-01&to=2020-10-31");
get("https://v3.football.api-sports.io/fixtures?league=61&season=2019&from=2019-07-01&to=2020-10-31&timezone=Europe/london");
get("https://v3.football.api-sports.io/fixtures?league=61&season=2019&round=Regular Season - 1");

```

### 14. `GET /fixtures/headtohead`

Consulta enfrentamientos entre dos equipos, con filtros temporales y de competición.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures-headtohead); comienza en la línea 1499 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `h2h` | Sí | string ID-ID The ids of the teams |
| `date` | No; revisar condiciones | string YYYY-MM-DD |
| `league` | No; revisar condiciones | integer The id of the league |
| `season` | No; revisar condiciones | integer = 4 characters YYYY The season of the league |
| `last` | No; revisar condiciones | integer For the X last fixtures |
| `next` | No; revisar condiciones | integer For the X next fixtures |
| `from` | No; revisar condiciones | string YYYY-MM-DD |
| `to` | No; revisar condiciones | string YYYY-MM-DD |
| `status` | No; revisar condiciones | string Enum: "NS" "NS-PST-FT" One or more fixture status short |
| `venue` | No; revisar condiciones | integer The venue id of the fixture |
| `timezone` | No; revisar condiciones | string A valid timezone from the endpoint Timezone |

**Actualización del proveedor:** This endpoint is updated every 15 seconds.

**Llamadas recomendadas por el proveedor:** 1 call per minute for the leagues, teams, fixtures who have at least one fixture in progress otherwise 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `fixture`, `league`, `teams`, `goals`, `score`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get heads to heads between two teams. Update Frequency : This endpoint is updated every 15 seconds. Recommended Calls : 1 call per minute for the leagues, teams, fixtures who have at least one fixture in progress otherwise 1 call per day. Here is an example of what can be achieved

**Ejemplo original (no ejecutado):**

```text
// Get all head to head between two {team}
get("https://v3.football.api-sports.io/fixtures/headtohead?h2h=33-34");

// It’s possible to make requests by mixing the available parameters
get("https://v3.football.api-sports.io/fixtures/headtohead?h2h=33-34");
get("https://v3.football.api-sports.io/fixtures/headtohead?h2h=33-34&status=ns");
get("https://v3.football.api-sports.io/fixtures/headtohead?h2h=33-34&from=2019-10-01&to=2019-10-31");
get("https://v3.football.api-sports.io/fixtures/headtohead?date=2019-10-22&h2h=33-34");
get("https://v3.football.api-sports.io/fixtures/headtohead?league=39&season=2019&h2h=33-34&last=5");
get("https://v3.football.api-sports.io/fixtures/headtohead?league=39&season=2019&h2h=33-34&next=10&from=2019-10-01&to=2019-10-31");
get("https://v3.football.api-sports.io/fixtures/headtohead?league=39&season=2019&h2h=33-34&last=5&timezone=Europe/London");

```

### 15. `GET /fixtures/statistics`

Estadísticas de equipos por partido. El parámetro half añade datos por mitades desde 2024.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures-statistics); comienza en la línea 1531 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `fixture` | Sí | integer The id of the fixture |
| `team` | No; revisar condiciones | integer The id of the team |
| `type` | No; revisar condiciones | string The type of statistics |
| `half` | No; revisar condiciones | boolean Default: false Enum: "true" "false" Add the halftime statistics in the response Data start from 2024 season for half parameter |

**Actualización del proveedor:** This endpoint is updated every minute.

**Llamadas recomendadas por el proveedor:** 1 call every minute for the teams or fixtures who have at least one fixture in progress otherwise 1 call per day.

**Nota:** fixture aparece marcado required. half=true añade Fulltime, First & Second Half, según el ejemplo; el documento sitúa los datos por mitades desde la temporada 2024.

**Campos del primer nivel del resultado de ejemplo:** `team`, `statistics`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the statistics for one fixture. Available statistics Shots on Goal Shots off Goal Shots insidebox Shots outsidebox Total Shots Blocked Shots Fouls Corner Kicks Offsides Ball Possession Yellow Cards Red Cards Goalkeeper Saves Total passes Passes accurate Passes % Update Frequency : This endpoint is updated every minute. Recommended Calls : 1 call every minute for the teams or fixtures who have at least one fixture in progress otherwise 1 call per day. Here is an example of what can be achieved

**Ejemplo original (no ejecutado):**

```text
// Get all available statistics from one {fixture}
get("https://v3.football.api-sports.io/fixtures/statistics?fixture=215662");

// Get all available statistics from one {fixture} with Fulltime, First & Second Half data
get("https://v3.football.api-sports.io/fixtures/statistics?fixture=215662&half=true");

// Get all available statistics from one {fixture} & {type}
get("https://v3.football.api-sports.io/fixtures/statistics?fixture=215662&type=Total Shots");

// Get all available statistics from one {fixture} & {team}
get("https://v3.football.api-sports.io/fixtures/statistics?fixture=215662&team=463");

```

### 16. `GET /fixtures/events`

Eventos del partido: goles, tarjetas, sustituciones y VAR.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures-events); comienza en la línea 1578 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `fixture` | Sí | integer The id of the fixture |
| `team` | No; revisar condiciones | integer The id of the team |
| `player` | No; revisar condiciones | integer The id of the player |
| `type` | No; revisar condiciones | string The type |

**Actualización del proveedor:** This endpoint is updated every 15 seconds.

**Llamadas recomendadas por el proveedor:** 1 call per minute for the fixtures in progress otherwise 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `time`, `team`, `player`, `assist`, `type`, `detail`, `comments`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the events from a fixture. Available events TYPE Goal Normal Goal Own Goal Penalty Missed Penalty Card Yellow Card Red card Subst Substitution [1, 2, 3...] Var Goal cancelled Penalty confirmed VAR events are available from the 2020-2021 season. Update Frequency : This endpoint is updated every 15 seconds. Recommended Calls : 1 call per minute for the fixtures in progress otherwise 1 call per day. You can also retrieve all the events of the fixtures in progress with to the endpoint fixtures?live=all Here is an example of what can be achieved

**Ejemplo original (no ejecutado):**

```text
// Get all available events from one {fixture}
get("https://v3.football.api-sports.io/fixtures/events?fixture=215662");

// Get all available events from one {fixture} & {team}
get("https://v3.football.api-sports.io/fixtures/events?fixture=215662&team=463");

// Get all available events from one {fixture} & {player}
get("https://v3.football.api-sports.io/fixtures/events?fixture=215662&player=35845");

// Get all available events from one {fixture} & {type}
get("https://v3.football.api-sports.io/fixtures/events?fixture=215662&type=card");

// It’s possible to make requests by mixing the available parameters
get("https://v3.football.api-sports.io/fixtures/events?fixture=215662&player=35845&type=card");
get("https://v3.football.api-sports.io/fixtures/events?fixture=215662&team=463&type=goal&player=35845");

```

### 17. `GET /fixtures/lineups`

Alineaciones, formación, entrenador, titulares, suplentes y posiciones en la cuadrícula.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures-lineups); comienza en la línea 1654 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `fixture` | Sí | integer The id of the fixture |
| `team` | No; revisar condiciones | integer The id of the team |
| `player` | No; revisar condiciones | integer The id of the player |
| `type` | No; revisar condiciones | string The type |

**Actualización del proveedor:** This endpoint is updated every 15 minutes.

**Llamadas recomendadas por el proveedor:** 1 call every 15 minutes for the fixtures in progress otherwise 1 call per day.

**Nota:** La ventana indicativa es de 20 a 40 minutos antes del partido cuando hay cobertura. En algunas competiciones las alineaciones sólo aparecen después.

**Campos del primer nivel del resultado de ejemplo:** `team`, `formation`, `startXI`, `substitutes`, `coach`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the lineups for a fixture. Lineups are available between 20 and 40 minutes before the fixture when the competition covers this feature. You can check this with the endpoint leagues and the coverage field. It's possible that for some competitions the lineups are not available before the fixture, in this case, they are updated and available after the match with a variable delay depending on the competition. Available datas Formation Coach Start XI Substitutes Players' positions on the grid * X = row and Y = column (X:Y) Line 1 X being the one of the goal and then for each line this number is incremented. The column Y will go from left to right, and incremented for each player of the line. * As a new feature, some irregularities may occur, do not hesitate to report them on our public Roadmap Update Frequency : This endpoint is updated every 15 minutes. Recommended Calls : 1 call every 15 minutes for the fixtures in progress otherwise 1 call per day. Here are several examples of what can be done

**Ejemplo original (no ejecutado):**

```text
// Get all available lineups from one {fixture}
get("https://v3.football.api-sports.io/fixtures/lineups?fixture=592872");

// Get all available lineups from one {fixture} & {team}
get("https://v3.football.api-sports.io/fixtures/lineups?fixture=592872&team=50");

// Get all available lineups from one {fixture} & {player}
get("https://v3.football.api-sports.io/fixtures/lineups?fixture=215662&player=35845");

// Get all available lineups from one {fixture} & {type}
get("https://v3.football.api-sports.io/fixtures/lineups?fixture=215662&type=startXI");

// It’s possible to make requests by mixing the available parameters
get("https://v3.football.api-sports.io/fixtures/lineups?fixture=215662&player=35845&type=startXI");
get("https://v3.football.api-sports.io/fixtures/lineups?fixture=215662&team=463&type=startXI&player=35845");

```

### 18. `GET /fixtures/players`

Estadísticas individuales de jugadores en un partido.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures-players); comienza en la línea 1702 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `fixture` | Sí | integer The id of the fixture |
| `team` | No; revisar condiciones | integer The id of the team |

**Actualización del proveedor:** This endpoint is updated every minute.

**Llamadas recomendadas por el proveedor:** 1 call every minute for the fixtures in progress otherwise 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `team`, `players`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the players statistics from one fixture. Update Frequency : This endpoint is updated every minute. Recommended Calls : 1 call every minute for the fixtures in progress otherwise 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all available players statistics from one {fixture}
get("https://v3.football.api-sports.io/fixtures/players?fixture=169080");

// Get all available players statistics from one {fixture} & {team}
get("https://v3.football.api-sports.io/fixtures/players?fixture=169080&team=2284");

```

### 19. `GET /injuries`

Ausencias y dudas de jugadores para partidos: lesionados, suspendidos u otros motivos.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Injuries/operation/get-injuries); comienza en la línea 1718 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `league` | No; revisar condiciones | integer The id of the league |
| `season` | No; revisar condiciones | integer = 4 characters YYYY The season of the league, required with league , team and player parameters |
| `fixture` | No; revisar condiciones | integer The id of the fixture |
| `team` | No; revisar condiciones | integer The id of the team |
| `player` | No; revisar condiciones | integer The id of the player |
| `date` | No; revisar condiciones | string YYYY-MM-DD A valid date |
| `ids` | No; revisar condiciones | string Maximum of 20 fixtures ids Value: "id-id-id" One or more fixture ids |
| `timezone` | No; revisar condiciones | string A valid timezone from the endpoint Timezone |

**Actualización del proveedor:** This endpoint is updated every 4 hours.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Nota:** Requiere al menos un parámetro. season es obligatorio cuando se utiliza league, team o player, según el texto de la tabla.

**Nota:** ids admite como máximo 20 IDs de partidos separados por guiones.

**Nota:** Missing Fixture y Questionable son estados distintos; Questionable no confirma una baja.

**Nota:** El documento indica datos desde abril de 2021.

**Campos del primer nivel del resultado de ejemplo:** `player`, `team`, `fixture`, `league`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the list of players not participating in the fixtures for various reasons such as suspended , injured for example. Being a new endpoint, the data is only available from April 2021. There are two types: Missing Fixture : The player will not play the fixture. Questionable : The information is not yet 100% sure, the player may eventually play the fixture. Examples available in Request samples "Use Cases". All the parameters of this endpoint can be used together. This endpoint requires at least one parameter. Update Frequency : This endpoint is updated every 4 hours. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all available injuries from one {league} & {season}
get("https://v3.football.api-sports.io/injuries?league=2&season=2020");

// Get all available injuries from one {fixture}
get("https://v3.football.api-sports.io/injuries?fixture=686314");

// Get all available injuries from severals fixtures {ids} 
get("https://v3.football.api-sports.io/injuries?ids=686314-686315-686316-686317-686318-686319-686320");

// Get all available injuries from one {team} & {season}
get("https://v3.football.api-sports.io/injuries?team=85&season=2020");

// Get all available injuries from one {player} & {season}
get("https://v3.football.api-sports.io/injuries?player=865&season=2020");

// Get all available injuries from one {date}
get("https://v3.football.api-sports.io/injuries?date=2021-04-07");

// It’s possible to make requests by mixing the available parameters
get("https://v3.football.api-sports.io/injuries?league=2&season=2020&team=85");
get("https://v3.football.api-sports.io/injuries?league=2&season=2020&player=865");
get("https://v3.football.api-sports.io/injuries?date=2021-04-07&timezone=Europe/London&team=85");
get("https://v3.football.api-sports.io/injuries?date=2021-04-07&league=61");

```

### 20. `GET /predictions`

Predicciones del proveedor y comparaciones entre equipos; no utilizan cuotas de casas de apuestas.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Predictions/operation/get-predictions); comienza en la línea 1771 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `fixture` | Sí | integer The id of the fixture |

**Actualización del proveedor:** This endpoint is updated every hour.

**Llamadas recomendadas por el proveedor:** 1 call per hour for the fixtures in progress otherwise 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `predictions`, `league`, `teams`, `comparison`, `h2h`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get predictions about a fixture. The predictions are made using several algorithms including the poisson distribution, comparison of team statistics, last matches, players etc… Bookmakers odds are not used to make these predictions Also provides some comparative statistics between teams Available Predictions Match winner : Id of the team that can potentially win the fixture Win or Draw : If True indicates that the designated team can win or draw Under / Over : -1.5 / -2.5 / -3.5 / -4.5 / +1.5 / +2.5 / +3.5 / +4.5 * Goals Home : -1.5 / -2.5 / -3.5 / -4.5 * Goals Away -1.5 / -2.5 / -3.5 / -4.5 * Advice (Ex : Deportivo Santani or draws and -3.5 goals) * -1.5 means that there will be a maximum of 1.5 goals in the fixture, i.e : 1 goal Update Frequency : This endpoint is updated every hour. Recommended Calls : 1 call per hour for the fixtures in progress otherwise 1 call per day. Here is an example of what can be achieved

**Ejemplo original (no ejecutado):**

```text
// Get all available predictions from one {fixture}
get("https://v3.football.api-sports.io/predictions?fixture=198772");

```

### 21. `GET /coachs`

Información y trayectoria de entrenadores. La ruta se escribe coachs.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Coachs/operation/get-coachs); comienza en la línea 1800 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `id` | No; revisar condiciones | integer The id of the coach |
| `team` | No; revisar condiciones | integer The id of the team |
| `search` | No; revisar condiciones | string >= 3 characters The name of the coach |

**Actualización del proveedor:** This endpoint is updated every day.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `id`, `name`, `firstname`, `lastname`, `age`, `birth`, `nationality`, `height`, `weight`, `photo`, `team`, `career`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get all the information about the coachs and their careers. To get the photo of a coach you have to call the following url: https://media.api-sports.io/football/coachs/{coach_id}.png Update Frequency : This endpoint is updated every day. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get coachs from one coach {id}
get("https://v3.football.api-sports.io/coachs?id=1");

// Get coachs from one {team}
get("https://v3.football.api-sports.io/coachs?team=33");

// Allows you to search for a coach in relation to a coach {name}
get("https://v3.football.api-sports.io/coachs?search=Klopp");

```

### 22. `GET /players/seasons`

Temporadas disponibles para estadísticas de jugadores; permite filtrar por jugador.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Players/operation/get-players-seasons); comienza en la línea 1821 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `player` | No; revisar condiciones | integer The id of the player |

**Actualización del proveedor:** This endpoint is updated every day.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Descripción original, sin etiquetas HTML:**

Get all available seasons for players statistics. Update Frequency : This endpoint is updated every day. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all seasons available for players endpoint
get("https://v3.football.api-sports.io/players/seasons");

// Get all seasons available for a player {id}
get("https://v3.football.api-sports.io/players/seasons?player=276");

```

### 23. `GET /players/profiles`

Catálogo de perfiles de jugadores; admite consulta completa paginada.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Players/operation/get-players-profiles); comienza en la línea 1836 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `player` | No; revisar condiciones | integer The id of the player |
| `search` | No; revisar condiciones | string >= 4 characters The lastname of the player |
| `page` | No; revisar condiciones | integer Default: 1 Use for the pagination |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per week.

**Paginación:** 250 resultados por página.

**Nota:** 250 resultados por página. player es el filtro por ID; no se llama id en esta ruta.

**Campos del primer nivel del resultado de ejemplo:** `player`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Returns the list of all available players. It is possible to call this endpoint without parameters, but you will need to use the pagination to get  all available players. To get the photo of a player you have to call the following url: https://media.api-sports.io/football/players/{player_id}.png This endpoint uses a pagination system , you can navigate between the different pages with to the page parameter. Pagination : 250 results per page. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per week.

**Ejemplo original (no ejecutado):**

```text
// Get data from one {player}
get("https://v3.football.api-sports.io/players/profiles?player=276");

// Allows you to search for a player in relation to a player {lastname}
get("https://v3.football.api-sports.io/players/profiles?search=ney");

// Get all available Players (limited to 250 results, use the pagination for next ones)
get("https://v3.football.api-sports.io/players/profiles");
get("https://v3.football.api-sports.io/players/profiles?page=2");
get("https://v3.football.api-sports.io/players/profiles?page=3");

```

### 24. `GET /players`

Perfiles y estadísticas por jugador, equipo, competición y temporada.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Players/operation/get-players); comienza en la línea 1864 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `id` | No; revisar condiciones | integer The id of the player |
| `team` | No; revisar condiciones | integer The id of the team |
| `league` | No; revisar condiciones | integer The id of the league |
| `season` | No; revisar condiciones | integer = 4 characters YYYY \| Requires the fields Id, League or Team... The season of the league |
| `search` | No; revisar condiciones | string >= 4 characters Requires the fields League or Team The name of the player |
| `page` | No; revisar condiciones | integer Default: 1 Use for the pagination |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Paginación:** 20 resultados por página.

**Nota:** 20 resultados por página. id es el filtro por ID de jugador en esta ruta.

**Nota:** Un jugador puede tener estadísticas para más de un equipo en una temporada por transferencias.

**Nota:** Las estadísticas están identificadas por equipo, liga y temporada. El ID del jugador se conserva entre equipos.

**Nota:** search indica que requiere League o Team. El texto explicativo de season está truncado en el HTML; no se reconstruye el patrón completo.

**Campos del primer nivel del resultado de ejemplo:** `player`, `statistics`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get players statistics. This endpoint returns the players for whom the profile and statistics data are available. Note that it is possible that a player has statistics for 2 teams in the same season in case of transfers. The statistics are calculated according to the team id , league id and season . You can find the available seasons by using the endpoint players/seasons . To get the squads of the teams it is better to use the endpoint players/squads . The players id are unique in the API and players keep it among all the teams they have been in. In this endpoint you have the rating field, which is the rating of the player according to a match or a season. This data is calculated according to the performance of the player in relation to the other players of the game or the season who occupy the same position (Attacker, defender, goal...) . There are different algorithms that take into account the position of the player and assign points according to his performance. To get the photo of a player you have to call the following url: https://media.api-sports.io/football/players/{player_id}.png This endpoint uses a pagination system , you can navigate between the different pages with to the page parameter. Pagination : 20 results per page. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day. Tutorials : HOW TO GET ALL TEAMS AND PLAYERS FROM A LEAGUE ID

**Ejemplo original (no ejecutado):**

```text
// Get all players statistics from one player {id} & {season}
get("https://v3.football.api-sports.io/players?id=19088&season=2018");

// Get all players statistics from one {team} & {season}
get("https://v3.football.api-sports.io/players?season=2018&team=33");
get("https://v3.football.api-sports.io/players?season=2018&team=33&page=2");

// Get all players statistics from one {league} & {season}
get("https://v3.football.api-sports.io/players?season=2018&league=61");
get("https://v3.football.api-sports.io/players?season=2018&league=61&page=4");

// Get all players statistics from one {league}, {team} & {season}
get("https://v3.football.api-sports.io/players?season=2018&league=61&team=33");
get("https://v3.football.api-sports.io/players?season=2018&league=61&team=33&page=5");

// Allows you to search for a player in relation to a player {name}
get("https://v3.football.api-sports.io/players?team=85&search=cavani");
get("https://v3.football.api-sports.io/players?league=61&search=cavani");
get("https://v3.football.api-sports.io/players?team=85&search=cavani&season=2018");

```

### 25. `GET /players/squads`

Plantilla actual de un equipo, o equipos asociados a un jugador.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Players/operation/get-players-squads); comienza en la línea 1915 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `team` | No; revisar condiciones | integer The id of the team |
| `player` | No; revisar condiciones | integer The id of the player |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per week.

**Nota:** Requiere al menos team o player. Devuelve la plantilla actual, no una plantilla histórica por season.

**Campos del primer nivel del resultado de ejemplo:** `team`, `players`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Return the current squad of a team when the team parameter is used. When the player parameter is used the endpoint returns the set of teams associated with the player. The response format is the same regardless of the parameter sent. This endpoint requires at least one parameter. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per week.

**Ejemplo original (no ejecutado):**

```text
// Get all players from one {team}
get("https://v3.football.api-sports.io/players/squads?team=33");

// Get all teams from one {player}
get("https://v3.football.api-sports.io/players/squads?player=276");

```

### 26. `GET /players/teams`

Equipos y temporadas en los que jugó un jugador durante su carrera.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Players/operation/get-players-teams); comienza en la línea 1935 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `player` | Sí | integer The id of the player |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per week.

**Campos del primer nivel del resultado de ejemplo:** `team`, `seasons`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Returns the list of teams and seasons in which the player played during his career. This endpoint requires at least one parameter. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per week.

**Ejemplo original (no ejecutado):**

```text
// Get all teams from one {player}
get("https://v3.football.api-sports.io/players/teams?player=276");

```

### 27. `GET /players/topscorers`

Los 20 jugadores mejor clasificados como goleadores, con los desempates documentados.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Players/operation/get-players-topscorers); comienza en la línea 1948 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | integer = 4 characters YYYY The season of the league |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `player`, `statistics`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the 20 best players for a league or cup. How it is calculated: 1 : The player that has scored the higher number of goals 2 : The player that has scored the fewer number of penalties 3 : The player that has delivered the higher number of goal assists 4 : The player that scored their goals in the higher number of matches 5 : The player that played the fewer minutes 6 : The player that plays for the team placed higher on the table 7 : The player that received the fewer number of red cards 8 : The player that received the fewer number of yellow cards Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
$client = new http\Client;
$request = new http\Client\Request;

$request->setRequestUrl('https://v3.football.api-sports.io/players/topscorers');
$request->setRequestMethod('GET');
$request->setQuery(new http\QueryString(array(
	'season' => '2018',
	'league' => '61'
)));

$request->setHeaders(array(
	'x-apisports-key' => 'XxXxXxXxXxXxXxXxXxXxXxXx'
));

$client->enqueue($request)->send();
$response = $client->getResponse();

echo $response->getBody();

```

### 28. `GET /players/topassists`

Los 20 jugadores mejor clasificados por asistencias, con los desempates documentados.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Players/operation/get-players-topassists); comienza en la línea 1988 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | integer = 4 characters YYYY The season of the league |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `player`, `statistics`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the 20 best players assists for a league or cup. How it is calculated: 1 : The player that has delivered the higher number of goal assists 2 : The player that has scored the higher number of goals 3 : The player that has scored the fewer number of penalties 4 : The player that assists in the higher number of matches 5 : The player that played the fewer minutes 6 : The player that received the fewer number of red cards 7 : The player that received the fewer number of yellow cards Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
$client = new http\Client;
$request = new http\Client\Request;

$request->setRequestUrl('https://v3.football.api-sports.io/players/topassists');
$request->setRequestMethod('GET');
$request->setQuery(new http\QueryString(array(
	'season' => '2020',
	'league' => '61'
)));

$request->setHeaders(array(
	'x-apisports-key' => 'XxXxXxXxXxXxXxXxXxXxXxXx'
));

$client->enqueue($request)->send();
$response = $client->getResponse();

echo $response->getBody();

```

### 29. `GET /players/topyellowcards`

Los 20 jugadores con más tarjetas amarillas, con los desempates documentados.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Players/operation/get-players-topyellowcards); comienza en la línea 2027 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | integer = 4 characters YYYY The season of the league |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `player`, `statistics`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the 20 players with the most yellow cards for a league or cup. How it is calculated: 1 : The player that received the higher number of yellow cards 2 : The player that received the higher number of red cards 3 : The player that assists in the higher number of matches 4 : The player that played the fewer minutes Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
$client = new http\Client;
$request = new http\Client\Request;

$request->setRequestUrl('https://v3.football.api-sports.io/players/topyellowcards');
$request->setRequestMethod('GET');
$request->setQuery(new http\QueryString(array(
	'season' => '2020',
	'league' => '61'
)));

$request->setHeaders(array(
	'x-apisports-key' => 'XxXxXxXxXxXxXxXxXxXxXxXx'
));

$client->enqueue($request)->send();
$response = $client->getResponse();

echo $response->getBody();

```

### 30. `GET /players/topredcards`

Los 20 jugadores con más tarjetas rojas, con los desempates documentados.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Players/operation/get-players-topredcards); comienza en la línea 2063 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `league` | Sí | integer The id of the league |
| `season` | Sí | integer = 4 characters YYYY The season of the league |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `player`, `statistics`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the 20 players with the most red cards for a league or cup. How it is calculated: 1 : The player that received the higher number of red cards 2 : The player that received the higher number of yellow cards 3 : The player that assists in the higher number of matches 4 : The player that played the fewer minutes Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
$client = new http\Client;
$request = new http\Client\Request;

$request->setRequestUrl('https://v3.football.api-sports.io/players/topredcards');
$request->setRequestMethod('GET');
$request->setQuery(new http\QueryString(array(
	'season' => '2020',
	'league' => '61'
)));

$request->setHeaders(array(
	'x-apisports-key' => 'XxXxXxXxXxXxXxXxXxXxXxXx'
));

$client->enqueue($request)->send();
$response = $client->getResponse();

echo $response->getBody();

```

### 31. `GET /transfers`

Transferencias disponibles por jugador o equipo.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Transfers/operation/get-transfers); comienza en la línea 2099 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `player` | No; revisar condiciones | integer The id of the player |
| `team` | No; revisar condiciones | integer The id of the team |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `player`, `update`, `transfers`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get all available transfers for players and teams Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all transfers from one {player}
get("https://v3.football.api-sports.io/transfers?player=35845");

// Get all transfers from one {team}
get("https://v3.football.api-sports.io/transfers?team=463");

```

### 32. `GET /trophies`

Trofeos disponibles por jugador o entrenador, individualmente o en lotes.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Trophies/operation/get-trophies); comienza en la línea 2115 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `player` | No; revisar condiciones | integer The id of the player |
| `players` | No; revisar condiciones | string Maximum of 20 players ids Value: "id-id-id" One or more players ids |
| `coach` | No; revisar condiciones | integer The id of the coach |
| `coachs` | No; revisar condiciones | string Maximum of 20 coachs ids Value: "id-id-id" One or more coachs ids |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Nota:** players y coachs admiten hasta 20 IDs por parámetro, separados por guiones.

**Campos del primer nivel del resultado de ejemplo:** `league`, `country`, `season`, `place`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get all available trophies for a player or a coach. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all trophies from one {player}
get("https://v3.football.api-sports.io/trophies?player=276");

// Get all trophies from several {player} ids
get("https://v3.football.api-sports.io/trophies?players=276-278");

// Get all trophies from one {coach}
get("https://v3.football.api-sports.io/trophies?coach=2");

// Get all trophies from several {coach} ids
get("https://v3.football.api-sports.io/trophies?coachs=2-6");

```

### 33. `GET /sidelined`

Periodos de baja disponibles por jugador o entrenador, individualmente o en lotes.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Sidelined/operation/get-sidelined); comienza en la línea 2139 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `player` | No; revisar condiciones | integer The id of the player |
| `players` | No; revisar condiciones | string Maximum of 20 players ids Value: "id-id-id" One or more players ids |
| `coach` | No; revisar condiciones | integer The id of the coach |
| `coachs` | No; revisar condiciones | string Maximum of 20 coachs ids Value: "id-id-id" One or more coachs ids |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Nota:** players y coachs admiten hasta 20 IDs por parámetro, separados por guiones.

**Campos del primer nivel del resultado de ejemplo:** `type`, `start`, `end`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get all available sidelined for a player or a coach. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all from one {player}
get("https://v3.football.api-sports.io/sidelined?player=276");

// Get all from several {player} ids
get("https://v3.football.api-sports.io/sidelined?players=276-278-279-280-281-282");

// Get all from one {coach}
get("https://v3.football.api-sports.io/sidelined?coach=2");

// Get all from several {coach} ids
get("https://v3.football.api-sports.io/sidelined?coachs=2-6-44-77-54-52");

```

### 34. `GET /odds/live`

Cuotas en vivo de partidos próximos, en curso o recién finalizados; no conserva historial.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Odds-(In-Play)/operation/get-odds-live); comienza en la línea 2163 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `fixture` | No; revisar condiciones | integer The id of the fixture |
| `league` | No; revisar condiciones | integer (In this endpoint the "season" parameter is ... Show pattern The id of the league |
| `bet` | No; revisar condiciones | integer The id of the bet |

**Actualización del proveedor:** This endpoint is updated every 5 seconds. *

**Nota:** No guarda historial. Añade partidos entre 15 y 5 minutos antes del inicio y los retira entre 5 y 20 minutos después del final.

**Nota:** Actualización indicativa de 5 segundos, con variación documentada de 5 a 60 segundos.

**Nota:** Consultar stopped, blocked, finished y suspended. El documento define finished=true tanto si no ha empezado como si ha terminado.

**Nota:** No descartar automáticamente registros con main=false o null: el documento indica que también puede corresponder a valores únicos.

**Nota:** El parámetro season no aparece en esta ruta; el texto explicativo de league está truncado en el HTML.

**Campos del primer nivel del resultado de ejemplo:** `fixture`, `league`, `teams`, `status`, `update`, `odds`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

This endpoint returns in-play odds for fixtures in progress. Fixtures are added between 15 and 5 minutes before the start of the fixture. Once the fixture is over they are removed from the endpoint between 5 and 20 minutes. No history is stored . So fixtures that are about to start, fixtures in progress and fixtures that have just ended are available in this endpoint. Update Frequency : This endpoint is updated every 5 seconds. * * This value can change in the range of 5 to 60 seconds INFORMATIONS ABOUT STATUS "status" : { "stopped" : false , // True if the fixture is stopped by the referee for X reason "blocked" : false , // True if bets on this fixture are temporarily blocked "finished" : false // True if the fixture has not started or if it is finished } , INFORMATIONS ABOUT VALUES When several identical values exist for the same bet the main field is set to True for the bet being considered, the others will have the value False . The main field will be set to True only if several identical values exist for the same bet. When a value is unique for a bet the main value will always be False or null . Example below : "id" : 36 , "name" : "Over/Under Line" , "values" : [ { "value" : "Over" , "odd" : "1.975" , "handicap" : "2" , "main" : true , // Bet to consider "suspended" : false // True if this bet is temporarily suspended } , { "value" : "Over" , "odd" : "3.45" , "handicap" : "2" , "main" : false , // Bet to no consider "suspended" : false } , ]

**Ejemplo original (no ejecutado):**

```text
// Get all available odds
get("https://v3.football.api-sports.io/odds/live");

// Get all available odds from one {fixture}
get("https://v3.football.api-sports.io/odds/live?fixture=164327");

// Get all available odds from one {league}
get("https://v3.football.api-sports.io/odds/live?league=39");

// It’s possible to make requests by mixing the available parameters
get("https://v3.football.api-sports.io/odds/live?bet=4&league=39");
get("https://v3.football.api-sports.io/odds/live?bet=4&fixture=164327");

```

### 35. `GET /odds/live/bets`

Catálogo de mercados de cuotas en vivo; IDs no compatibles con mercados prepartido.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Odds-(In-Play)/operation/get-bets); comienza en la línea 2219 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `id` | No; revisar condiciones | string The id of the bet name |
| `search` | No; revisar condiciones | string = 3 characters The name of the bet |

**Actualización del proveedor:** This endpoint is updated every 60 seconds.

**Nota:** Sus IDs no son compatibles con /odds prepartido.

**Campos del primer nivel del resultado de ejemplo:** `id`, `name`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get all available bets for in-play odds. All bets id can be used in endpoint odds/live as filters, but are not compatible with endpoint odds for pre-match odds . Update Frequency : This endpoint is updated every 60 seconds.

**Ejemplo original (no ejecutado):**

```text
// Get all available bets
get("https://v3.football.api-sports.io/odds/live/bets");

// Get bet from one {id}
get("https://v3.football.api-sports.io/odds/live/bets?id=1");

// Allows you to search for a bet in relation to a bets {name}
get("https://v3.football.api-sports.io/odds/live/bets?search=winner");

```

### 36. `GET /odds`

Cuotas prepartido por partido, competición o fecha, con filtros de casa y mercado.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Odds-(Pre-Match)/operation/get-odds); comienza en la línea 2238 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `fixture` | No; revisar condiciones | integer The id of the fixture |
| `league` | No; revisar condiciones | integer The id of the league |
| `season` | No; revisar condiciones | integer = 4 characters YYYY The season of the league |
| `date` | No; revisar condiciones | string YYYY-MM-DD A valid date |
| `timezone` | No; revisar condiciones | string A valid timezone from the endpoint Timezone |
| `page` | No; revisar condiciones | integer Default: 1 Use for the pagination |
| `bookmaker` | No; revisar condiciones | integer The id of the bookmaker |
| `bet` | No; revisar condiciones | integer The id of the bet |

**Actualización del proveedor:** This endpoint is updated every 3 hours.

**Llamadas recomendadas por el proveedor:** 1 call every 3 hours.

**Paginación:** 10 resultados por página.

**Nota:** 10 resultados por página.

**Nota:** Cuotas prepartido entre 1 y 14 días antes del partido; conserva 7 días de historial, sujeto a disponibilidad.

**Nota:** Actualización y llamadas recomendadas: cada 3 horas.

**Campos del primer nivel del resultado de ejemplo:** `league`, `fixture`, `update`, `bookmakers`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get odds from fixtures, leagues or date. This endpoint uses a pagination system , you can navigate between the different pages with to the page parameter. Pagination : 10 results per page. We provide pre-match odds between 1 and 14 days before the fixture. We keep a 7-days history (The availability of odds may vary according to the leagues, seasons, fixtures and bookmakers) Update Frequency : This endpoint is updated every 3 hours. Recommended Calls : 1 call every 3 hours.

**Ejemplo original (no ejecutado):**

```text
// Get all available odds from one {fixture}
get("https://v3.football.api-sports.io/odds?fixture=164327");

// Get all available odds from one {league} & {season}
get("https://v3.football.api-sports.io/odds?league=39&season=2019");

// Get all available odds from one {date}
get("https://v3.football.api-sports.io/odds?date=2020-05-15");

// It’s possible to make requests by mixing the available parameters
get("https://v3.football.api-sports.io/odds?bookmaker=1&bet=4&league=39&season=2019");
get("https://v3.football.api-sports.io/odds?bet=4&fixture=164327");
get("https://v3.football.api-sports.io/odds?bookmaker=1&league=39&season=2019");
get("https://v3.football.api-sports.io/odds?date=2020-05-15&page=2&bet=4");

```

### 37. `GET /odds/mapping`

Lista paginada de partidos disponibles para consultar cuotas prepartido.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Odds-(Pre-Match)/operation/get-odds-mapping); comienza en la línea 2275 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `page` | No; revisar condiciones | integer Default: 1 Use for the pagination |

**Actualización del proveedor:** This endpoint is updated every day.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Paginación:** 100 resultados por página.

**Nota:** 100 resultados por página. El único query parameter listado es page.

**Campos del primer nivel del resultado de ejemplo:** `league`, `fixture`, `update`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get the list of available fixtures id for the endpoint odds. All fixtures, leagues id and date can be used in endpoint odds as filters. This endpoint uses a pagination system , you can navigate between the different pages with to the page parameter. Pagination : 100 results per page. Update Frequency : This endpoint is updated every day. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
$client = new http\Client;
$request = new http\Client\Request;

$request->setRequestUrl('https://v3.football.api-sports.io/odds/mapping');
$request->setRequestMethod('GET');
$request->setHeaders(array(
	'x-apisports-key' => 'XxXxXxXxXxXxXxXxXxXxXxXx'
));

$client->enqueue($request)->send();
$response = $client->getResponse();

echo $response->getBody();

```

### 38. `GET /odds/bookmakers`

Catálogo de casas de apuestas y sus IDs para cuotas prepartido.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Odds-(Pre-Match)/operation/get-bookmakers); comienza en la línea 2303 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `id` | No; revisar condiciones | integer The id of the bookmaker |
| `search` | No; revisar condiciones | string = 3 characters The name of the bookmaker |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Campos del primer nivel del resultado de ejemplo:** `id`, `name`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get all available bookmakers. All bookmakers id can be used in endpoint odds as filters. Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all available bookmakers
get("https://v3.football.api-sports.io/odds/bookmakers");

// Get bookmaker from one {id}
get("https://v3.football.api-sports.io/odds/bookmakers?id=1");

// Allows you to search for a bookmaker in relation to a bookmakers {name}
get("https://v3.football.api-sports.io/odds/bookmakers?search=Betfair");

```

### 39. `GET /odds/bets`

Catálogo de mercados prepartido; IDs no compatibles con mercados en vivo.

**Fuente:** [sección original](https://www.api-football.com/documentation-v3#tag/Odds-(Pre-Match)/operation/get-bets); comienza en la línea 2323 del HTML adjunto.

| Parámetro | Marcado required | Detalle literal del proveedor |
|---|---|---|
| `id` | No; revisar condiciones | string The id of the bet name |
| `search` | No; revisar condiciones | string = 3 characters The name of the bet |

**Actualización del proveedor:** This endpoint is updated several times a week.

**Llamadas recomendadas por el proveedor:** 1 call per day.

**Nota:** Sus IDs no son compatibles con /odds/live.

**Campos del primer nivel del resultado de ejemplo:** `id`, `name`. Estos campos no constituyen un esquema exhaustivo.

**Descripción original, sin etiquetas HTML:**

Get all available bets for pre-match odds. All bets id can be used in endpoint odds as filters, but are not compatible with endpoint odds/live for in-play odds . Update Frequency : This endpoint is updated several times a week. Recommended Calls : 1 call per day.

**Ejemplo original (no ejecutado):**

```text
// Get all available bets
get("https://v3.football.api-sports.io/odds/bets");

// Get bet from one {id}
get("https://v3.football.api-sports.io/odds/bets?id=1");

// Allows you to search for a bet in relation to a bets {name}
get("https://v3.football.api-sports.io/odds/bets?search=winner");

```

## Procedencia y limitaciones

El HTML referencia `public/doc/openapi.yaml`. Resolviendo esa referencia respecto a la página, la URL es `https://www.api-football.com/public/doc/openapi.yaml`; no se descargó ni verificó en esta sesión.

Los patrones truncados del HTML no se reconstruyen. Se conservaron tanto notas como etiquetas y ejemplos del proveedor. En particular, hay discrepancias entre algunas longitudes de búsqueda y sus ejemplos, y una descripción inconsistente del estado HT; no deben convertirse automáticamente en reglas de validación.

**API-NBA:** no documentada en el archivo recibido. No se valida aquí el inventario orientativo de la respuesta anterior.

**SHA-256 de la fuente:** `357013025f93a1968a538f77ad2bfb973d5cfce214e05942a2e1fe3eb9ea6618`.
