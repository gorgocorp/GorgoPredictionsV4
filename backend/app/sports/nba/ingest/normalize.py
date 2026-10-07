"""Convierte respuestas de API-Basketball en filas para la base de datos.

Funciones puras: sin red ni base de datos, para poder probarlas aisladas.
"""

import html
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from app.sports.nba.config import NBA_FRANCHISE_IDS

EASTERN = ZoneInfo("America/New_York")


class InvalidRecord(ValueError):
    pass


def parse_minutes(value: str | None) -> int | None:
    """'39:12' -> 2352 segundos. También acepta '25' (sólo minutos)."""
    if not value:
        return None
    parts = value.strip().split(":")
    try:
        if len(parts) == 1:
            return int(parts[0]) * 60
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        pass
    raise InvalidRecord(f"minutos con formato inesperado: {value!r}")


def derive_fg2_made(points: int | None, fg3_made: int | None, ft_made: int | None) -> int | None:
    """Dobles anotados reconstruidos desde los puntos: (pts - 3·triples - libres) / 2."""
    if points is None:
        return None
    rest = points - 3 * (fg3_made or 0) - (ft_made or 0)
    if rest < 0 or rest % 2:
        return None
    return rest // 2


def _parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value)
    if ts.tzinfo is None:
        raise InvalidRecord(f"fecha sin zona horaria: {value!r}")
    return ts


def team_row(raw: dict[str, Any], fetched_at: datetime) -> dict[str, Any]:
    team_id = raw.get("id")
    if not isinstance(team_id, int) or team_id <= 0:
        raise InvalidRecord(f"id de equipo inválido: {team_id!r}")
    name = (raw.get("name") or "").strip()
    if not name:
        raise InvalidRecord(f"equipo {team_id} sin nombre")
    return {"id": team_id, "name": name, "logo": raw.get("logo"), "raw_payload": raw, "fetched_at": fetched_at}


def is_franchise_game(raw: dict[str, Any]) -> bool:
    teams = raw.get("teams") or {}
    home = (teams.get("home") or {}).get("id")
    away = (teams.get("away") or {}).get("id")
    return home in NBA_FRANCHISE_IDS and away in NBA_FRANCHISE_IDS


def game_row(raw: dict[str, Any], fetched_at: datetime) -> dict[str, Any]:
    game_id = raw.get("id")
    if not isinstance(game_id, int) or game_id <= 0:
        raise InvalidRecord(f"id de partido inválido: {game_id!r}")
    starts_at = _parse_ts(raw["date"])
    home, away = raw["teams"]["home"], raw["teams"]["away"]
    if home["id"] == away["id"]:
        raise InvalidRecord(f"partido {game_id} con el mismo equipo en ambos lados")

    row = {
        "id": game_id,
        "season": raw["league"]["season"],
        "starts_at": starts_at,
        "game_date": starts_at.astimezone(EASTERN).date(),
        "status": raw["status"]["short"],
        "home_team_id": home["id"],
        "away_team_id": away["id"],
        "venue": raw.get("venue"),
        "raw_payload": raw,
        "fetched_at": fetched_at,
    }
    for side in ("home", "away"):
        scores = raw["scores"][side]
        row[f"{side}_q1"] = scores.get("quarter_1")
        row[f"{side}_q2"] = scores.get("quarter_2")
        row[f"{side}_q3"] = scores.get("quarter_3")
        row[f"{side}_q4"] = scores.get("quarter_4")
        row[f"{side}_ot"] = scores.get("over_time")
        row[f"{side}_total"] = scores.get("total")
    return row


def _made_att(raw: dict[str, Any], key: str) -> tuple[int | None, int | None]:
    block = raw.get(key) or {}
    return block.get("total"), block.get("attempts")


def player_rows(raw: dict[str, Any], fetched_at: datetime) -> tuple[dict[str, Any], dict[str, Any]]:
    """Devuelve (fila de jugador, fila de estadísticas del partido)."""
    player = raw.get("player") or {}
    player_id = player.get("id")
    if not isinstance(player_id, int) or player_id <= 0:
        raise InvalidRecord(f"id de jugador inválido: {player_id!r}")
    name = html.unescape(player.get("name") or "").strip()  # la API manda "Day&apos;Ron"
    if not name:
        raise InvalidRecord(f"jugador {player_id} sin nombre")

    fg2_made, fg2_att = _made_att(raw, "field_goals")
    fg3_made, fg3_att = _made_att(raw, "threepoint_goals")
    ft_made, ft_att = _made_att(raw, "freethrows_goals")
    points = raw.get("points")

    stats = {
        "game_id": raw["game"]["id"],
        "player_id": player_id,
        "team_id": raw["team"]["id"],
        "is_starter": raw.get("type") == "starters",
        "seconds_played": parse_minutes(raw.get("minutes")),
        "points": points,
        "rebounds": (raw.get("rebounds") or {}).get("total"),
        "assists": raw.get("assists"),
        "fg2_made": fg2_made,
        "fg2_attempts": fg2_att,
        "fg3_made": fg3_made,
        "fg3_attempts": fg3_att,
        "ft_made": ft_made,
        "ft_attempts": ft_att,
        "fg2_made_derived": derive_fg2_made(points, fg3_made, ft_made),
        "raw_payload": raw,
        "fetched_at": fetched_at,
    }
    return {"id": player_id, "name": name, "fetched_at": fetched_at}, stats


def team_stats_row(raw: dict[str, Any], fetched_at: datetime) -> dict[str, Any]:
    fg2_made, fg2_att = _made_att(raw, "field_goals")
    fg3_made, fg3_att = _made_att(raw, "threepoint_goals")
    ft_made, ft_att = _made_att(raw, "freethrows_goals")
    return {
        "game_id": raw["game"]["id"],
        "team_id": raw["team"]["id"],
        "fg2_made": fg2_made,
        "fg2_attempts": fg2_att,
        "fg3_made": fg3_made,
        "fg3_attempts": fg3_att,
        "ft_made": ft_made,
        "ft_attempts": ft_att,
        "rebounds": (raw.get("rebounds") or {}).get("total"),
        "assists": raw.get("assists"),
        "steals": raw.get("steals"),
        "blocks": raw.get("blocks"),
        "turnovers": raw.get("turnovers"),
        "raw_payload": raw,
        "fetched_at": fetched_at,
    }


def odds_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Aplana {game, bookmakers[].bets[].values[]} en una fila por selección.

    Descarta momios no numéricos o <= 1 y duplicados exactos dentro del mismo partido.
    """
    game_id = raw["game"]["id"]
    rows: dict[tuple, dict[str, Any]] = {}
    for bookmaker in raw.get("bookmakers") or []:
        for bet in bookmaker.get("bets") or []:
            for value in bet.get("values") or []:
                selection = str(value.get("value") or "").strip()
                try:
                    odd = Decimal(str(value.get("odd")))
                except InvalidOperation:
                    continue
                if not selection or not odd.is_finite() or odd <= 1:
                    continue
                key = (game_id, bookmaker["id"], bet["id"], selection)
                rows[key] = {
                    "game_id": game_id,
                    "bookmaker_id": bookmaker["id"],
                    "bookmaker_name": bookmaker.get("name"),
                    "bet_id": bet["id"],
                    "bet_name": bet.get("name"),
                    "selection": selection,
                    "odd": odd,
                }
    return list(rows.values())
