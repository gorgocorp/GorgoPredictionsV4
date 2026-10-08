Respuestas reales de API-Football recortadas para las pruebas (sólo se quitan elementos y campos que no se usan;
lo que queda es textual).

- `fixture_1492399.json`: `/fixtures?ids=1492399` (Vitória 4-0 Chapecoense, Brasileirão, 7-oct-2026), pedido el
  8-oct-2026. El bloque `players[]` de Chapecoense (132) llega con `team.id = 22722` y `team.name = null`; las
  alineaciones, los eventos y `statistics[]` sí lo traen como 132. Incluye un jugador con `id = 0`.
