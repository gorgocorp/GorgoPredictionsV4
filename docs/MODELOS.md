# Cambios a los modelos

Registro de los cambios intencionales al cálculo de probabilidades. Cada uno sube `MODEL_VERSION` de su deporte
(`app/sports/<deporte>/engine/tracking.py`), que se guarda en cada pick, parlay y proyección para separar el
rendimiento de cada versión. `v1` es el motor copiado de los proyectos anteriores (paridad del 6-oct-2026).

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
