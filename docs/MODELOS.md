# Cambios a los modelos

Registro de los cambios intencionales al cálculo de probabilidades. Cada uno sube `MODEL_VERSION` de su deporte
(`app/sports/<deporte>/engine/tracking.py`), que se guarda en cada pick, parlay y proyección para separar el
rendimiento de cada versión. `v1` es el motor copiado de los proyectos anteriores (paridad del 6-oct-2026).

## Fútbol v3 — titulares según la alineación y remates con bloqueados (16-oct-2026)

**Qué pasó.** En la revisión del 13-oct, las props de remates de jugador salían 8 a 10 puntos por debajo de lo real
(más de 0.5: 50.5% predicho contra 58.3% real). API-Football cambió dos cosas de sus estadísticas de jugador. No lo
hizo en una fecha: lo fue haciendo partido por partido entre enero y octubre de 2026, casi todo desde septiembre.

1. **Remates ("Total Shots" del jugador).** Antes contaba a puerta + fuera. Ahora suma también los bloqueados,
   igual que el total del equipo. Se distingue en cada (partido, equipo) con el desglose del equipo en
   `raw_payload`. Del 1-ene-2024 al 14-oct-2026, en 21,000 casos los jugadores sumaban el total menos los bloqueados
   (definición vieja) y en 587 sumaban el total exacto (nueva). En 1,632 no hubo bloqueados (las dos dan igual) y 63
   quedan cerca de una de las dos. Ejemplo viejo: un equipo con 27 remates (5 a puerta, 11 fuera, 11 bloqueados) y
   jugadores que sumaban 16. Hasta junio había pocos partidos nuevos (7 a 12 por mes); en agosto fueron 51 y desde el
   21-sep son casi todos. Conviven en la misma liga y el mismo día (Liga MX, 11-oct), y al 14-oct la Superliga China
   sigue con la vieja. Con la definición vieja, el cociente total del equipo / suma de los jugadores tiene mediana
   1.36 (media 1.43, percentil 95 de 2.0 y 99 de 2.6). Los remates a puerta siempre cuadraron.
2. **Marca de suplente (`games.substitute`).** En los partidos nuevos, la API marca `substitute = false` a todo el
   que juega, también al que entra de cambio: salen 15.6 "titulares" por equipo en lugar de 11. La alineación
   publicada (`futbol.fixture_lineups`, presente en el 100% de los partidos terminados) no cambió. Los jugadores que
   la API marca titulares y la alineación pone en la banca eran 0 a 29 por mes hasta mayo de 2026; luego 193 en
   julio, 258 en agosto, 893 en septiembre y 1,536 del 1 al 14 de octubre. Para la v2, esos suplentes "empezaban" el
   partido: subía su probabilidad de ser titular (y se volvían elegibles para props) y bajaban los "minutos como
   titular" de quien a veces entra de cambio.

Las props se liquidan con el dato de la API, que ya usa la definición nueva de remates. El modelo debe predecir esa.

**Qué cambió** (`engine/history.py`, `engine/player_model.py`):

- Suplente = marca de la API **o** banca en la alineación. En el historial cambian 6,852 filas. El conteo de
  titularidades del plantel para marcar bajas (`/fixtures/{id}/roster`) usa la misma regla.
- Para las **tasas** de remates (`shots_model`), los remates de cada jugador se escalan para que los de su equipo
  sumen el total del equipo en ese partido: factor = total del equipo / suma de los jugadores, acotado entre 1 y 3.
  Con la definición nueva el factor es 1 y nada cambia; con la vieja, los bloqueados se reparten en proporción a lo
  que remató cada jugador. Sin estadísticas del equipo, o si los jugadores no rematan o suman más que el equipo, el
  factor es 1.
- Los **resultados** (backtest y liquidación) y "veces que lo logró en sus últimos 10 y 25" siguen con el dato crudo
  de la API. En los partidos con la definición vieja ese conteo no incluye los bloqueados; deja de pesar a medida
  que esos partidos salen de la ventana.
- La escala (0.97) y la dispersión (1.1) de remates no cambian. En la rejilla (escala × 0.85 a 1.05, dispersión 1.1
  a 1.5) las mejores combinaciones empatan con la actual (log loss 0.4097 a 0.4101 contra 0.4099).
- El backtest evalúa remates sólo donde los jugadores suman el total del equipo, es decir, con resultados de la
  definición nueva. Antes de septiembre de 2026 eso deja casi únicamente partidos sin bloqueados (una muestra con
  menos remates), así que los remates del backtest se leen desde el 21-sep-2026.

**Backtest.** Emparejado: los mismos titulares, según la alineación, que jugaron. Cada día ajusta con lo anterior,
sin información futura. Se corrió sobre la base real de producción en sólo lectura. Variantes: v2; sólo el arreglo
de suplentes; v3 (suplentes + remates escalados por partido); y una alternativa descartada (suplentes + factor
constante de 1.357 donde se detecta la definición vieja). IC de 95% por bootstrap de días.

Remates, 21-sep a 14-oct-2026 (15 días; 3,297 titulares-partido con la definición nueva o sin bloqueados; escalones
"1 o más" a "4 o más"):

| | ≥1 | ≥2 | ≥3 | ≥4 | Remates por titular | Brier | Log loss |
|---|---:|---:|---:|---:|---:|---:|---:|
| Real | 58.7% | 31.4% | 14.7% | 6.9% | 1.171 | | |
| v2 | 50.5% | 21.7% | 8.6% | 3.2% | 0.857 | 0.1400 | 0.4326 |
| Sólo suplentes | 51.1% | 22.2% | 8.9% | 3.4% | 0.875 | 0.1390 | 0.4290 |
| **v3** | 59.8% | 30.5% | 14.4% | 6.5% | 1.157 | 0.1334 | 0.4099 |
| Factor constante | 59.3% | 30.1% | 14.1% | 6.3% | 1.142 | 0.1333 | 0.4098 |

- Log loss v3 − v2: **−0.0226** (IC −0.0309 a −0.0184). Sólo suplentes − v2: −0.0036 (IC −0.0060 a −0.0024).
  v3 − factor constante: +0.0001 (IC −0.0009 a +0.0010), un empate. Se eligió el escalado por partido porque no
  necesita una constante ni detectar la definición.
- Sensibilidad: del 4-sep al 14-oct, sólo partidos con la definición nueva exacta (4,544 titulares-partido): v3 − v2
  −0.0277 (IC −0.0334 a −0.0240). Del 1 al 14-oct: −0.0226 (IC −0.0317 a −0.0183).
- Por liga mejora en 11 de 14. Empeoran la Libertadores (20 titulares-partido), la Ligue 1 (164; +0.004) y la
  Superliga China (30). En China sólo se evalúan sus partidos sin bloqueados, porque sigue con la definición vieja.
- Con el código de v3, `backtest --sport futbol --start 2026-09-21 --end 2026-10-14` da en remates 10,605 piernas
  (probabilidad entre 3% y 97%): predicho medio 34.9% contra 34.9% real, y cada franja de 10 puntos queda a 2.1
  puntos o menos. El `backtest` de v2 en el mismo rango no se compara con éste: toma como titulares a los suplentes
  que entraron y evalúa también los remates con la definición vieja.

Demás props, 4-sep a 14-oct-2026 (11,379 titulares-partido, todos los partidos): ninguna cambia de forma
significativa. Goles (log loss 0.1807 → 0.1806), asistencias (0.2786 → 0.2785), gol o asistencia (0.4296 → 0.4291;
IC −0.0011 a +0.0001), remates a puerta (0.2827 → 0.2826) y tarjetas (0.4438 → 0.4437). Los minutos como titular
pasan de 80.6 a 81.4 en promedio.

**En producción** (partidos por jugar del 16 al 19-oct, 110 partidos, antes de que salgan las alineaciones):

- Los jugadores elegibles para props bajan de 2,536 a 2,120. Los 416 que salen eran suplentes que la v2 tomaba por
  titulares: su probabilidad de ser titular baja de 0.67 a 0.30.
- En los demás, la probabilidad media de remates más de 0.5 pasa de 49.1% a 56.1%, de más de 1.5 de 20.8% a 27.4% y
  de más de 2.5 de 8.2% a 12.6%.
- Remates a puerta (26.4% → 25.8%) y goles (9.7% → 9.5%) casi no cambian. Bajan un poco porque ahora la
  probabilidad de entrar de cambio pesa lo que debe mientras no hay alineación.

**Paridad.** Desde v3, `parity --sport futbol` ya no da diferencia 0 en las props de jugador (todas las
estadísticas, por la elegibilidad y los minutos) ni en los remates proyectados. Es el cambio buscado. Las piernas
de equipo siguen idénticas.

## Fútbol v2 — un árbitro, una clave (9-oct-2026)

**Qué cambió.** El modelo de tarjetas tiene un efecto por árbitro, y la clave del árbitro era su nombre sin el país
(`'Jeremy Stinat, France'` → `'jeremy stinat'`). API-Football publica a la misma persona con varios nombres, así que
el historial de cada árbitro quedaba repartido entre varias claves y, con `ridge_referee = 40`, cada pedazo quedaba
muy encogido hacia 0. Ahora `engine/referees.py` junta las variantes de cada árbitro con reglas conservadoras (ante la
duda las deja separadas) y sólo con los partidos que el modelo ya conoce en su fecha de corte. Los parámetros del
modelo no cambiaron.

**Alcance** (partidos terminados con árbitro de los últimos 760 días al 9-oct-2026, la ventana del modelo):

- La API cambió de formato a mitad de la temporada 2025-26 en casi todas las ligas: de `'J. Stinat'` a
  `'Jeremy Stinat, France'`. El historial de cada árbitro quedaba partido justo en esa frontera.
- 10,655 partidos y 1,149 claves → 675 árbitros. **369 árbitros tenían 2 a 5 claves** (267 con 2, 82 con 3, 18 con
  4, 2 con 5) y dirigieron 9,500 de esos partidos (89%). Su clave más grande sólo juntaba el 65% de sus partidos
  (mediana: 13 de 23).
- Motivos (un árbitro puede tener varios): abreviado vs completo (355), con vs sin país (108), acentos (84,
  `'Hernández'`/`'Hernandez'`, `'S. Gözübüyük'`/`'S. Gozubuyuk'`) y apellido primero (21,
  `'Hilfer, Leandro Rey, Argentina'`).

**Reglas** (detalle en el docstring de `referees.py`):

1. Se normaliza el nombre: sin país, sin acentos, en orden nombre-apellido.
2. Un nombre cubre a otro si empieza con la misma inicial y contiene sus demás palabras en orden:
   `'Adonai Escobedo Gonzalez'` cubre a `'A. Escobedo'`; `'Andre Filipe Domingues Narciso'` a `'A. Narciso'`.
3. Una forma abreviada sólo se busca en su liga (`'M. Ortiz'` es Miguel Ángel Ortiz Arias en La Liga y Marco Antonio
   Ortiz Nava en la Liga MX: la misma cadena, dos personas). En copas, y para árbitros que sólo conocemos de copas,
   en cualquier liga.
4. Si el nombre lo cubren dos árbitros posibles, no se junta con ninguno.
5. Dos variantes con partidos a un día o menos de distancia son personas distintas. En la ventana, sólo 6 de
   ~3,500 pares de partidos consecutivos de un mismo nombre completo están a 0 o 1 días.
6. Al predecir, un nombre que el modelo no ha visto se busca primero entre los conocidos que lo cubren (`'Joao
   Pinheiro'` → Joao Pedro Pinheiro) y, si no hay, entre los que él completa (`'Jeremy Stinat, France'` la primera
   vez que sale, cuando sólo se conocía `'J. Stinat'`). Con más de un candidato, o con apodos y erratas
   (`'Andrew'`/`'Andy Madley'`, `'Guiseppe Collu'`), el árbitro queda como desconocido (efecto 0), igual que antes.

**Choques.** No se usa "inicial + apellido" porque juntaría a árbitros distintos en 21 combinaciones liga/clave:
`'J. Martinez'` en La Liga (juntaría a Juan Martínez Munuera con José María Sánchez Martínez; `'J. Martinez'` dirigió
partidos a un día de los de Sánchez Martínez, así que es Martínez Munuera), `'J. Munuera'` (José Luis Munuera Montero
y Juan Martínez Munuera), `'J. Pinheiro'` (Joao Pedro Pinheiro de Portugal y Jonathan Benkenstein Pinheiro de Brasil)
y `'J. Smith'` en la Premier (dos personas: partidos a un día de distancia), entre otros. Con las reglas de
arriba quedan 14 formas abreviadas ambiguas que se dejan aparte (por ejemplo `'S. Martin'`: la API escribe tanto
`'Stephen Martin'` como `'Steve Martin'`, y no inventamos equivalencias de apodos). Las fusiones dudosas (la forma
corta toma un apellido del medio o sólo el último de un nombre con dos apellidos) se revisaron a mano.

**Backtest** (`backtest --sport futbol`, rango por defecto 15-ago-2025 a 1-jun-2026, 267 días, 4,793 partidos; cada
día ajusta con lo anterior, sin información futura; base real de producción en sólo lectura):

| Mercado | n | Log loss v1 | Log loss v2 | Brier v1 | Brier v2 |
|---|---:|---:|---:|---:|---:|
| tarjetas: total | 23,955 | 0.5652 | 0.5649 | 0.1912 | 0.1910 |
| tarjetas: equipo | 38,328 | 0.5145 | 0.5135 | 0.1705 | 0.1701 |
| jugador: tarjetas (props, usan las tarjetas esperadas del equipo) | 91,810 → 91,804 | 0.4501 | 0.4499 | 0.1391 | 0.1391 |
| goles, 1X2, ambos anotan, demás props y parlays de props | — | sin cambio | sin cambio | | |

Las líneas de tarjetas del backtest se centran en el total que predice cada modelo, así que v1 y v2 no evalúan las
mismas líneas. Por eso también se compararon emparejadas: los mismos partidos con líneas fijas (total 2.5 a 7.5, por
equipo 0.5 a 3.5) y la probabilidad del conteo exacto, con intervalo de confianza de 95% por bootstrap de días:

| Periodo | Partidos | Árbitro con efecto | Total 2.5-7.5 | Equipo 0.5-3.5 | −log P(conteo exacto) |
|---|---:|---|---|---|---|
| 15-ago-2025 a 1-jun-2026 | 4,791 | 91.7% → 97.6% | 0.5235 → 0.5219 (−0.0017, IC −0.0031 a −0.0001) | 0.5145 → 0.5135 (−0.0010, IC −0.0019 a −0.0001) | 2.2019 → 2.1990 (−0.0029, IC −0.0054 a −0.0003) |
| 2-jun a 9-oct-2026 | 1,094 | 91.3% → 94.3% | 0.5077 → 0.5059 (−0.0018, IC −0.0048 a +0.0012) | 0.5142 → 0.5130 (−0.0012, IC −0.0031 a +0.0007) | 2.1535 → 2.1511 (−0.0024, IC −0.0079 a +0.0031) |

- La mejora es chica pero consistente: en el rango principal los tres intervalos excluyen el 0; en el periodo
  posterior (más corto) va en la misma dirección sin ser concluyente. Por liga hay ruido: mejoran sobre todo
  Primeira Liga y Serie A; el Brasileirão empeora un poco (+0.0028), pero sus árbitros que más empeoran son fusiones
  correctas (`'L. Casagrande'` → Lucas Casagrande) o nombres que no cambiaron.
- Sin la regla de nombres nuevos más completos (la primera vez que sale `'Jeremy Stinat, France'` cuando sólo se
  conocía `'J. Stinat'`) la mejora era menor (−0.0014 en el total, IC hasta 0.0000).
- `ridge_referee` se mantiene en 40: con los árbitros unificados, 20 empeora (+0.0008 en el total, IC +0.0001 a
  +0.0016) y 60 queda igual que 40 (0.5218 vs 0.5219).
- Parlays simulados del backtest (pierna más probable de cada partido entre 60% y 87%, una combinación por día): con
  v2 el acierto real baja hasta 5.4 puntos según el número de piernas (2 piernas: 76.3% → 73.9% en 253 días; 3
  piernas: igual; 7 piernas: 40.1% → 34.7%). Con v1 el acierto real quedaba por encima de lo predicho y con v2 queda
  más cerca (7 piernas: predicho 36.0%). No es significativo: emparejando por día, los días que sólo acierta v1
  contra los que sólo acierta v2 dan p de McNemar de 0.18 a 1.00 para 2 a 8 piernas (y esas cifras no son
  independientes: el top N de cada día contiene al top N−1).
  Las piernas de tarjetas elegidas siguen calibradas (predicho 85.5%, real 85.3%; con v1, 85.5% y 85.6%). Hay que
  vigilarlo en Rendimiento con los parlays reales de v2.
- Con datos reales de producción (sólo lectura), en los 82 partidos por jugar del 9 al 11 de octubre con árbitro
  publicado, el árbitro tiene efecto en 77 con v2 contra 68 con v1, y ninguno lo pierde. Los 5 restantes son apodos,
  erratas y `'Ricardo, Rueben'` (apellido primero sin país, que no se distingue de "Nombre, País").

**Paridad.** Desde v2, `parity --sport futbol` ya no da diferencia 0 en las piernas de tarjetas (total y por
equipo), en las props de tarjetas de jugador ni en las tarjetas proyectadas: es el cambio buscado. El resto de las
piernas debe seguir idéntico.
