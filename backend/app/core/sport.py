"""Contrato que cumple cada deporte para usar la parte común: registro de picks, liquidación, tus
apuestas, historial y rendimiento.

Cada deporte lo implementa en app/sports/<deporte>/sport.py con sus propios modelos, tablas y textos.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import psycopg


@dataclass(frozen=True)
class Sport:
    key: str  # "nba" | "futbol" (core.matches.sport)
    label: str  # "NBA" | "Fútbol"
    # Cambiarla cuando los modelos cambien de forma relevante, para separar su rendimiento.
    model_version: str
    # Qué piernas se guardan, con momio y sin momio: prácticamente todas las evaluadas, también las poco
    # probables, para que el usuario pueda registrar cualquier pierna que apueste en su casa.
    store_range_priced: tuple[float, float]
    store_range_unpriced: tuple[float, float]
    record_days: int  # días con picks registrados en cada sincronización completa (hoy incluido)
    pregame_lead: timedelta  # corrida extra antes de cada horario de partidos
    # Lectura de cierre antes de cada horario de partidos (None: sin ella): sólo momios, y los picks quedan con el
    # último momio y la probabilidad del mercado previos al partido, contra los que se mide el CLV.
    closing_lead: timedelta | None

    # Historial y modelos.
    load_history: Callable[[psycopg.Connection], Any]
    has_matches: Callable[[Any, date], bool]  # (historial, día)
    models_cutoff: Callable[[date, date], date]  # (hoy, día) -> fecha de corte de los modelos para ese día
    fit_models: Callable[[Any, date], Any]
    # (conn, historial, día, casa, modelos) -> tarjetas con .external_id, .starts_at y .candidates
    generate_day: Callable[..., list]
    save_projections: Callable[[psycopg.Connection, list, datetime], None]
    sync_matches: Callable[[psycopg.Connection, list[int] | None], int]

    # Liquidación y evidencia. `outcome_joins` une core.picks (alias k) con core.matches (alias m) y con las
    # tablas del deporte; `outcome_columns` da los datos reales que usan pick_result y leg_outcome, entre
    # ellos `status` y `starts_at`.
    outcome_columns: str
    outcome_joins: str
    finished_statuses: tuple[str, ...]
    cancelled_statuses: tuple[str, ...]
    pick_result: Callable[[dict, datetime], str | None]  # won / lost / void / None (aún no)
    leg_outcome: Callable[[dict], dict]  # {"value": número o None, "text": explicación corta}
    matchup: Callable[[str, str], str]  # (local, visitante) -> "Hawks @ Celtics" / "América vs Chivas"

    # Rendimiento: filtros propios (NBA: pretemporada; fútbol: liga) -> (SQL picks, SQL parlays, params).
    # El SQL de picks puede usar k (core.picks) y m (core.matches); el de parlays, p (core.parlays).
    performance_filters: Callable[..., tuple[str, str, dict]]

    # Expresión booleana sobre m (core.matches): el partido es de pretemporada. Sólo si el deporte la tiene.
    preseason_sql: str | None = None


def minutes_env(name: str, default: str) -> timedelta | None:
    """Anticipación en minutos desde el entorno; 0 (o menos) la desactiva."""
    minutes = float(os.getenv(name, default))
    return timedelta(minutes=minutes) if minutes > 0 else None
