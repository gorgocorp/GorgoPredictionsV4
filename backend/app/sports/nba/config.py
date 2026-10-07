"""Configuración de NBA (API-Basketball)."""

import os

API_BASE_URL = "https://v1.basketball.api-sports.io"

# ID de la NBA en API-Basketball (league=12 en la documentación).
NBA_LEAGUE_ID = 12

# Las 30 franquicias tienen IDs consecutivos 132–161 (Atlanta Hawks … Washington Wizards).
# Excluye equipos del All-Star (Team World 1414, Team Stars/Stripes con id 0).
NBA_FRANCHISE_IDS = frozenset(range(132, 162))

# Temporada en curso para la recolección diaria.
CURRENT_SEASON = os.getenv("NBA_CURRENT_SEASON", "2026-2027")
