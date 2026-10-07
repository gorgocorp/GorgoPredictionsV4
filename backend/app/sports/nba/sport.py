"""NBA en la plataforma: el contrato de app.core.sport con los modelos de GorgoNBAParlays."""

import os
from datetime import date, timedelta

from app.core.sport import Sport
from app.sports.nba.engine import tracking
from app.sports.nba.engine.evidence import CANCELLED, FINISHED, leg_outcome
from app.sports.nba.engine.history import History, load_history
from app.sports.nba.engine.picks import fit_models, generate_day
from app.sports.nba.matches import sync_matches


def matchup(home: str, away: str) -> str:
    """"Hawks @ Celtics": visitante @ local, con la última palabra del nombre de cada equipo."""
    return f"{away.split(' ')[-1]} @ {home.split(' ')[-1]}"


def has_matches(hist: History, day: date) -> bool:
    return not hist.games_on(day).empty


def models_cutoff(today: date, day: date) -> date:
    """Cada día se predice con su propia fecha de corte, como en GorgoNBAParlays (los ratings y los
    perfiles de jugador ponderan por antigüedad respecto a esa fecha)."""
    return day


SPORT = Sport(
    key="nba",
    label="NBA",
    model_version=tracking.MODEL_VERSION,
    store_range_priced=tracking.STORE_RANGE_PRICED,
    store_range_unpriced=tracking.STORE_RANGE_UNPRICED,
    record_days=2,  # hoy y mañana
    pregame_lead=timedelta(minutes=float(os.getenv("NBA_PREGAME_LEAD_MINUTES", "60"))),
    load_history=load_history,
    has_matches=has_matches,
    models_cutoff=models_cutoff,
    fit_models=fit_models,
    generate_day=generate_day,
    save_projections=tracking.save_projections,
    sync_matches=sync_matches,
    outcome_columns=tracking.OUTCOME_COLUMNS,
    outcome_joins=tracking.OUTCOME_JOINS,
    finished_statuses=FINISHED,
    cancelled_statuses=CANCELLED,
    pick_result=tracking.pick_result,
    leg_outcome=leg_outcome,
    matchup=matchup,
    performance_filters=tracking.performance_filters,
    preseason_sql="EXISTS (SELECT 1 FROM nba.v_games g WHERE g.id = m.external_id AND g.phase = 'preseason')",
)
