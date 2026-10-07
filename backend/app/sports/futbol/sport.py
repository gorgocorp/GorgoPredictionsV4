"""Fútbol en la plataforma: el contrato de app.core.sport con los modelos de GorgoPredictionsV3."""

import os
from datetime import date, timedelta

from app.core.sport import Sport
from app.sports.futbol.engine import tracking
from app.sports.futbol.engine.evidence import CANCELLED, FINISHED, leg_outcome
from app.sports.futbol.engine.history import History, load_history
from app.sports.futbol.engine.picks import fit_models, generate_day
from app.sports.futbol.matches import sync_matches


def matchup(home: str, away: str) -> str:
    return f"{home} vs {away}"


def has_matches(hist: History, day: date) -> bool:
    return not hist.fixtures_on(day).empty


SPORT = Sport(
    key="futbol",
    label="Fútbol",
    model_version=tracking.MODEL_VERSION,
    store_range_priced=tracking.STORE_RANGE_PRICED,
    store_range_unpriced=tracking.STORE_RANGE_UNPRICED,
    # Hoy y los 6 días siguientes, para armar parlays de una jornada o de un fin de semana.
    record_days=int(os.getenv("FUTBOL_RECORD_DAYS", "7")),
    pregame_lead=timedelta(minutes=float(os.getenv("FUTBOL_PREGAME_LEAD_MINUTES", "45"))),
    load_history=load_history,
    has_matches=has_matches,
    models_cutoff=tracking.models_day,
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
)
