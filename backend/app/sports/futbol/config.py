"""Configuración de fútbol (API-Football v3)."""

API_BASE_URL = "https://v3.football.api-sports.io"

# Competiciones del proyecto (IDs de API-Football, verificados con /leagues el 6-oct-2026).
# El nombre corto es el que se muestra en la interfaz.
LEAGUES: dict[int, str] = {
    262: "Liga MX",
    39: "Premier League",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    88: "Eredivisie",
    61: "Ligue 1",
    2: "Champions League",
    3: "Europa League",
    71: "Brasileirão",
    128: "Liga Argentina",
    40: "Championship",
    13: "Libertadores",
    94: "Primeira Liga",
    169: "Superliga China",
}

# Copas internacionales: mezclan equipos de varias ligas.
CUPS = frozenset({2, 3, 13})
