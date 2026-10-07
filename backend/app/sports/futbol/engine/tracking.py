"""Partes de fútbol del registro de picks: proyecciones, liquidación y filtros de rendimiento.

Lo común (guardar piernas, armar y congelar parlays, liquidar parlays y apuestas, rendimiento) está en
app/core/tracking.py.
"""

from datetime import date, datetime, timedelta

import psycopg
from psycopg.types.json import Jsonb

from app.sports.futbol.engine.evidence import CANCELLED, player_value
from app.sports.futbol.engine.legs import LegSpec, settle

# Cambiar cuando los modelos cambien de forma relevante, para separar su rendimiento.
MODEL_VERSION = "v1"

# Qué piernas se guardan: prácticamente todas las evaluadas, también las poco probables, para
# que el usuario pueda registrar en "Mis apuestas" cualquier pierna que apueste en su casa.
STORE_RANGE_PRICED = (0.02, 0.97)  # arriba de 97% el momio no paga nada (≤ 1.03)
STORE_RANGE_UNPRICED = (0.05, 0.97)
# Si un partido terminó y la API nunca publicó estadísticas, las piernas que las necesitan se anulan.
STATS_GRACE = timedelta(days=2)


UPSERT_PROJECTION = """
INSERT INTO futbol.fixture_projections (fixture_id, home_goals, away_goals, p_home, p_draw, p_away, p_over25, p_btts,
                                        top_scores, home_cards, away_cards, lineups,
                                        model_version, evaluated_at)
VALUES (%(fixture_id)s, %(home_goals)s, %(away_goals)s, %(p_home)s, %(p_draw)s, %(p_away)s, %(p_over25)s, %(p_btts)s,
        %(top_scores)s, %(home_cards)s, %(away_cards)s, %(lineups)s,
        %(version)s, %(now)s)
ON CONFLICT (fixture_id) DO UPDATE SET
    home_goals = EXCLUDED.home_goals,
    away_goals = EXCLUDED.away_goals,
    p_home = EXCLUDED.p_home,
    p_draw = EXCLUDED.p_draw,
    p_away = EXCLUDED.p_away,
    p_over25 = EXCLUDED.p_over25,
    p_btts = EXCLUDED.p_btts,
    top_scores = EXCLUDED.top_scores,
    home_cards = EXCLUDED.home_cards,
    away_cards = EXCLUDED.away_cards,
    lineups = EXCLUDED.lineups,
    model_version = EXCLUDED.model_version,
    evaluated_at = EXCLUDED.evaluated_at
"""


def save_projections(conn: psycopg.Connection, cards: list, now: datetime) -> None:
    """Proyección de cada partido (misma regla que picks: deja de cambiar al empezar el partido)."""
    with conn.cursor() as cur:
        cur.executemany(UPSERT_PROJECTION, [
            {
                "fixture_id": card.fixture_id,
                "home_goals": round(card.prediction.home_goals, 2),
                "away_goals": round(card.prediction.away_goals, 2),
                "p_home": round(card.prediction.p_home(), 4),
                "p_draw": round(card.prediction.p_draw(), 4),
                "p_away": round(card.prediction.p_away(), 4),
                "p_over25": round(card.prediction.p_total_over(2.5), 4),
                "p_btts": round(card.prediction.p_btts(), 4),
                "top_scores": Jsonb([[s, round(p, 4)] for s, p in card.prediction.top_scores(5)]),
                "home_cards": round(card.cards.home, 2) if card.cards else None,
                "away_cards": round(card.cards.away, 2) if card.cards else None,
                "lineups": card.lineups,
                "version": MODEL_VERSION,
                "now": now,
            }
            for card in cards
        ])


def models_day(today: date, day: date) -> date:
    """Fecha de corte de los modelos para predecir `day` viendo desde `today`.

    Hoy se predice con lo terminado antes de hoy. De mañana en adelante se usa la misma fecha de
    corte (mañana): entre hoy y esos días no hay partidos terminados que se conozcan todavía.
    """
    return day if day <= today else today + timedelta(days=1)


# Datos reales de cada pierna: marcador a 90', tarjetas por equipo y estadística del jugador.
OUTCOME_COLUMNS = """
       f.status, f.starts_at, f.ft_home, f.ft_away,
       hs.yellow + COALESCE(hs.red, 0) AS home_cards, aws.yellow + COALESCE(aws.red, 0) AS away_cards,
       ps.minutes, ps.goals, ps.assists, ps.shots_total, ps.shots_on, ps.yellow, ps.red,
       EXISTS (SELECT 1 FROM futbol.fixture_player_stats x WHERE x.fixture_id = f.id) AS fixture_has_players
"""
OUTCOME_JOINS = """
JOIN core.matches m ON m.id = k.match_id
JOIN futbol.fixtures f ON f.id = m.external_id
LEFT JOIN futbol.fixture_team_stats hs ON hs.fixture_id = f.id AND hs.team_id = f.home_team_id
LEFT JOIN futbol.fixture_team_stats aws ON aws.fixture_id = f.id AND aws.team_id = f.away_team_id
LEFT JOIN futbol.fixture_player_stats ps ON ps.fixture_id = f.id AND ps.player_id = k.player_id
"""


def pick_result(r: dict, now: datetime) -> str | None:
    """Resultado de una pierna a partir de los datos reales; None si todavía falta información."""
    if r["status"] in CANCELLED:
        return "void"
    if r["ft_home"] is None or r["ft_away"] is None:
        return None
    spec = LegSpec(r["market"], r["side"], r["line"], r["team"], r["stat"], r["player_id"])
    late = now - r["starts_at"] > STATS_GRACE
    if spec.market in ("cards", "team_cards"):
        outcome = settle(spec, r["ft_home"], r["ft_away"], r["home_cards"], r["away_cards"])
        if outcome is None:
            return "void" if late else None
        return "won" if outcome else "lost"
    if spec.market != "player":
        return "won" if settle(spec, r["ft_home"], r["ft_away"]) else "lost"
    if r["minutes"] is not None:
        if r["minutes"] == 0:
            return "void"  # no jugó: las casas anulan la apuesta
        return "won" if settle(spec, r["ft_home"], r["ft_away"], player_value=player_value(r)) else "lost"
    if r["fixture_has_players"]:
        return "void"  # hay estadísticas del partido pero no del jugador: no fue convocado
    return "void" if late else None


def performance_filters(league: int | None = None, **_) -> tuple[str, str, dict]:
    """Rendimiento de una liga (los parlays mezclan ligas: se cuentan todos)."""
    if league is None:
        return "", "", {}
    return "AND m.competition_id = %(league)s", "", {"league": int(league)}
