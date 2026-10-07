"""Deportes de la plataforma (cada uno implementa app.core.sport.Sport en su sport.py)."""

from app.config import SPORTS
from app.core.sport import Sport


def all_sports() -> dict[str, Sport]:
    """Deportes en el orden de config.SPORTS. Se importan al pedirlos: cargan pandas, numpy y sus modelos."""
    from app.sports.futbol.sport import SPORT as FUTBOL
    from app.sports.nba.sport import SPORT as NBA

    available = {NBA.key: NBA, FUTBOL.key: FUTBOL}
    return {key: available[key] for key in SPORTS}


def get_sport(key: str) -> Sport:
    sports = all_sports()
    if key not in sports:
        raise KeyError(f"deporte desconocido: {key} (opciones: {', '.join(sports)})")
    return sports[key]
