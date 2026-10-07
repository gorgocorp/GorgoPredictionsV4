"""Ajuste por cambios de plantel entre temporadas (traspasos, fichajes, regresos).

Al iniciar una temporada, los ratings de equipo vienen casi por completo de la temporada
anterior: no saben quién se fue ni quién llegó. Este módulo trata los cambios confirmados
como bajas permanentes (o "bajas al revés") y reutiliza el efecto medido para las bajas:

- Se fue: estaba en la rotación del equipo al cierre de la temporada anterior y en la
  temporada actual ya jugó con otro equipo.
- Llegó: en la temporada actual ya jugó con el equipo, no estaba en su rotación de cierre y
  sí era jugador de rotación la temporada anterior (en otro equipo, o en este pero lesionado
  al final). Si hoy está en el reporte de lesiones, cuenta según su probabilidad de jugar.
- Quien todavía no juega esta temporada (lesionado, retirado, sin equipo) no se toca.

Para no sumar sin límite (en la cancha caben 240 minutos), la rotación anterior y la nueva se
comparan en los mismos minutos: los de la rotación de cierre, repartidos primero entre los
mejores anotadores. Un fichaje sólo suma lo que mejora sobre el jugador que desplaza.

El ajuste se multiplica por la fracción del rating que todavía viene de la temporada
anterior, así que se desvanece solo conforme se juegan partidos nuevos.

Validado en el arranque de 2025-26 (prediciendo cada día sólo con lo sabido ese día): log loss
del ganador en las dos primeras semanas de 0.626 a 0.615; de la semana 3 en adelante, sin efecto.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.sports.nba.engine.history import History
from app.sports.nba.engine.team_model import P_MISSING, TeamModelParams

ROTATION_TEAM_GAMES = 15  # rotación de cierre: últimos 15 partidos oficiales del equipo
CALIBER_PLAYER_GAMES = 10  # "jugador de rotación": sus últimos 10 partidos oficiales
MIN_GAMES = 5
MIN_MINUTES = 20.0


Line = tuple[float, float]  # (puntos por partido, minutos por partido)


def capped_points(players: list[Line], minutes: float) -> float:
    """Puntos que produce un grupo si sólo hay `minutes` para repartir, primero a los mejores."""
    total, left = 0.0, minutes
    for pts, mins in sorted(players, key=lambda pm: -pm[0]):
        if left <= 0 or mins <= 0:
            break
        used = min(mins, left)
        total += pts * used / mins
        left -= used
    return total


@dataclass
class RosterChange:
    team_id: int
    departed: list[tuple[int, float]] = field(default_factory=list)  # (jugador, pts por partido)
    arrived: list[tuple[int, float]] = field(default_factory=list)  # (jugador, pts esperados)
    weight: float = 0.0  # fracción del rating que aún viene de temporadas anteriores
    net_lost: float = 0.0  # pts por partido netos perdidos en los mismos minutos (negativo = ganó)

    @property
    def adjustment(self) -> float:
        """Puntos netos perdidos, ponderados por el peso de la temporada anterior."""
        return self.net_lost * self.weight


def _closing_rotation(hist: History, before: pd.Timestamp) -> dict[int, dict[int, Line]]:
    """{equipo: {jugador: (pts, min)}} con la rotación de los últimos 15 partidos oficiales antes de `before`."""
    g = hist.games
    g = g[g["is_finished"] & (g["phase"] != "preseason") & (g["game_date"] < before)]
    apps = pd.concat(
        [g[["id", "home_team_id", "game_date"]].rename(columns={"id": "game_id", "home_team_id": "team_id"}),
         g[["id", "away_team_id", "game_date"]].rename(columns={"id": "game_id", "away_team_id": "team_id"})]
    )
    last = apps.sort_values("game_date").groupby("team_id").tail(ROTATION_TEAM_GAMES)[["game_id", "team_id"]]
    ps = hist.player_stats
    rows = ps[ps["minutes"] > 0].merge(last, on=["game_id", "team_id"])
    agg = rows.groupby(["team_id", "player_id"]).agg(n=("minutes", "size"), mins=("minutes", "mean"), pts=("points", "mean"))
    agg = agg[(agg["n"] >= MIN_GAMES) & (agg["mins"] >= MIN_MINUTES)]
    out: dict[int, dict[int, Line]] = {}
    for (team, pid), r in agg.iterrows():
        out.setdefault(int(team), {})[int(pid)] = (float(r["pts"]), float(r["mins"]))
    return out


def _caliber(hist: History, before: pd.Timestamp) -> dict[int, Line]:
    """{jugador: (pts, min)} de quienes eran de rotación en sus últimos 10 partidos oficiales antes de `before`."""
    ps = hist.player_stats
    played = ps[(ps["game_date"] < before) & (ps["phase"] != "preseason") & (ps["minutes"] > 0)]
    last = played.sort_values("game_date").groupby("player_id").tail(CALIBER_PLAYER_GAMES)
    agg = last.groupby("player_id").agg(n=("minutes", "size"), mins=("minutes", "mean"), pts=("points", "mean"))
    agg = agg[(agg["n"] >= MIN_GAMES) & (agg["mins"] >= MIN_MINUTES)]
    return {int(pid): (float(r["pts"]), float(r["mins"])) for pid, r in agg.iterrows()}


def _previous_season_weight(hist: History, cutoff: pd.Timestamp, season_start: pd.Timestamp, half_life: float) -> dict[int, float]:
    """Fracción del peso de cada equipo (ratings por recencia) que viene de antes de `season_start`."""
    g = hist.games
    g = g[g["is_finished"] & (g["phase"] != "preseason") & (g["game_date"] < cutoff)]
    w = 0.5 ** ((cutoff - g["game_date"]).dt.days.to_numpy(dtype=float) / half_life)
    old = (g["game_date"] < season_start).to_numpy()
    frame = pd.DataFrame(
        {"team": np.r_[g["home_team_id"], g["away_team_id"]], "w": np.r_[w, w], "old": np.r_[old, old]}
    )
    total = frame.groupby("team")["w"].sum()
    prev = frame[frame["old"]].groupby("team")["w"].sum()
    return (prev / total).fillna(0.0).to_dict()


def roster_changes(
    hist: History,
    cutoff: pd.Timestamp,
    season: str,
    availability: dict[int, str] | None = None,
    team_params: TeamModelParams = TeamModelParams(),
) -> dict[int, RosterChange]:
    """Cambios de plantel confirmados por equipo para partidos del día `cutoff` en `season`."""
    availability = availability or {}
    g = hist.games
    official = g[(g["season"] == season) & (g["phase"] != "preseason")]
    season_games = g[g["season"] == season]
    if season_games.empty:
        return {}
    # Inicio de la temporada oficial (si aún no empieza, la fecha de corte).
    season_start = official["game_date"].min() if not official.empty else cutoff
    season_start = min(season_start, cutoff)

    closing = _closing_rotation(hist, season_start)
    caliber = _caliber(hist, season_start)
    weights = _previous_season_weight(hist, cutoff, season_start, team_params.half_life_days)

    # Equipo actual de cada jugador según sus apariciones en esta temporada (incluida pretemporada).
    ps = hist.player_stats
    this_season = ps[(ps["season"] == season) & (ps["game_date"] < cutoff)]
    current = this_season.sort_values("game_date").groupby("player_id")["team_id"].last().to_dict()

    changes = {team: RosterChange(team, weight=weights.get(team, 1.0)) for team in closing}
    lines: dict[int, list[Line]] = {team: [] for team in closing}  # rotación esperada hoy
    for team, rotation in closing.items():
        for pid, (pts, mins) in rotation.items():
            if pid in current and current[pid] != team:
                changes[team].departed.append((pid, pts))
            else:
                lines[team].append((pts, mins))
    for pid, team in current.items():
        if team not in changes or pid in closing.get(team, {}) or pid not in caliber:
            continue
        pts, mins = caliber[pid]
        expected = pts * (1.0 - P_MISSING.get(availability.get(pid, "available"), 0.0))
        changes[team].arrived.append((pid, expected))
        lines[team].append((expected, mins))
    for team, change in changes.items():
        budget = sum(mins for _, mins in closing[team].values())
        change.net_lost = capped_points(list(closing[team].values()), budget) - capped_points(lines[team], budget)
    return changes
