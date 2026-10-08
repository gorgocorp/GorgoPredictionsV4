"""Convierte respuestas de API-Football en filas para la base de datos.

Funciones puras: sin red ni base de datos, para poder probarlas aisladas.
"""

import html
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.config import LOCAL_TZ
from app.sports.futbol.config import LEAGUES

log = logging.getLogger(__name__)


class InvalidRecord(ValueError):
    pass


def _parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value)
    if ts.tzinfo is None:
        raise InvalidRecord(f"fecha sin zona horaria: {value!r}")
    return ts


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _clean_name(value: str | None) -> str:
    return html.unescape(value or "").strip()


def league_row(raw: dict[str, Any], fetched_at: datetime) -> dict[str, Any]:
    """Fila de `leagues` desde un elemento de /leagues (con su temporada en curso)."""
    league = raw["league"]
    seasons = raw.get("seasons") or []
    current = next((s for s in seasons if s.get("current")), seasons[-1] if seasons else {})
    return {
        "id": league["id"],
        # Nombre corto propio: la API llama "Serie A" tanto a Italia como a Brasil.
        "name": LEAGUES.get(league["id"], league["name"]),
        "country": (raw.get("country") or {}).get("name"),
        "type": league.get("type"),
        "logo": league.get("logo"),
        "current_season": current.get("year"),
        "season_start": _date(current.get("start")),
        "season_end": _date(current.get("end")),
        "coverage": current.get("coverage"),
        "fetched_at": fetched_at,
    }


def team_rows(raw: dict[str, Any], fetched_at: datetime) -> list[dict[str, Any]]:
    """Los dos equipos de un partido."""
    rows = []
    for side in ("home", "away"):
        team = (raw.get("teams") or {}).get(side) or {}
        team_id, name = team.get("id"), _clean_name(team.get("name"))
        if not isinstance(team_id, int) or team_id <= 0 or not name:
            raise InvalidRecord(f"equipo inválido en el partido {raw.get('fixture', {}).get('id')}: {team!r}")
        rows.append({"id": team_id, "name": name, "logo": team.get("logo"), "fetched_at": fetched_at})
    return rows


def fixture_row(raw: dict[str, Any], fetched_at: datetime) -> dict[str, Any]:
    fixture = raw.get("fixture") or {}
    fixture_id = fixture.get("id")
    if not isinstance(fixture_id, int) or fixture_id <= 0:
        raise InvalidRecord(f"id de partido inválido: {fixture_id!r}")
    starts_at = _parse_ts(fixture["date"])
    home, away = raw["teams"]["home"], raw["teams"]["away"]
    if home["id"] == away["id"]:
        raise InvalidRecord(f"partido {fixture_id} con el mismo equipo en ambos lados")
    score = raw.get("score") or {}
    goals = raw.get("goals") or {}
    fulltime = score.get("fulltime") or {}
    halftime = score.get("halftime") or {}
    penalty = score.get("penalty") or {}
    status = fixture["status"]["short"]
    # En FT el marcador de 90' es el final; en AET/PEN viene en score.fulltime.
    ft_home, ft_away = fulltime.get("home"), fulltime.get("away")
    if status == "FT" and ft_home is None:
        ft_home, ft_away = goals.get("home"), goals.get("away")
    venue = fixture.get("venue") or {}
    league = raw["league"]
    return {
        "id": fixture_id,
        "league_id": league["id"],
        "season": league["season"],
        "round": league.get("round"),
        "starts_at": starts_at,
        "match_date": starts_at.astimezone(LOCAL_TZ).date(),
        "status": status,
        "elapsed": fixture["status"].get("elapsed"),
        "home_team_id": home["id"],
        "away_team_id": away["id"],
        "ft_home": ft_home,
        "ft_away": ft_away,
        "ht_home": halftime.get("home"),
        "ht_away": halftime.get("away"),
        "goals_home": goals.get("home"),
        "goals_away": goals.get("away"),
        "pen_home": penalty.get("home"),
        "pen_away": penalty.get("away"),
        "referee": _clean_name(fixture.get("referee")) or None,
        "venue": venue.get("name"),
        "venue_city": venue.get("city"),
        "raw_payload": {k: v for k, v in raw.items() if k not in ("events", "lineups", "statistics", "players")},
        "fetched_at": fetched_at,
    }


def _fixture_teams(raw: dict[str, Any]) -> set[int]:
    return {raw["teams"]["home"]["id"], raw["teams"]["away"]["id"]}


def _block_team(raw: dict[str, Any], block: dict[str, Any], what: str) -> int | None:
    """Equipo de un bloque de estadísticas o alineación; None (se descarta) si no es uno de los dos del partido."""
    team_id = (block.get("team") or {}).get("id")
    if team_id in _fixture_teams(raw):
        return team_id
    log.warning("partido %s: %s del equipo %s descartadas (no es de este partido)", raw["fixture"]["id"], what, team_id)
    return None


def _team_by_players(raw: dict[str, Any], player_ids: set[int], free: set[int]) -> int | None:
    """Equipo del partido en el que las alineaciones y los eventos ponen a todos estos jugadores.

    Sólo responde si todos los que aparecen ahí son del mismo equipo y ese equipo está en `free`.
    """
    teams = _fixture_teams(raw)
    found = set()
    for block in raw.get("lineups") or []:
        team_id = (block.get("team") or {}).get("id")
        if team_id in teams and any(
            (item.get("player") or {}).get("id") in player_ids
            for key in ("startXI", "substitutes")
            for item in block.get(key) or []
        ):
            found.add(team_id)
    for e in raw.get("events") or []:
        team_id = (e.get("team") or {}).get("id")
        if team_id in teams and (e.get("player") or {}).get("id") in player_ids:
            found.add(team_id)
    return found.pop() if len(found) == 1 and found <= free else None


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.rstrip("%").strip()
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        out = Decimal(str(value))
    except InvalidOperation:
        return None
    return out if out.is_finite() else None


TEAM_STAT_FIELDS = {
    "Shots on Goal": "shots_on",
    "Total Shots": "shots_total",
    "Corner Kicks": "corners",
    "Fouls": "fouls",
    "Offsides": "offsides",
    "Yellow Cards": "yellow",
    "Red Cards": "red",
    "Goalkeeper Saves": "saves",
    "Ball Possession": "possession",
}


def team_stats_rows(raw: dict[str, Any], fetched_at: datetime) -> list[dict[str, Any]]:
    """Estadísticas de equipo de un partido. Conteos NULL = 0 (la API omite los ceros)."""
    fixture_id = raw["fixture"]["id"]
    rows = []
    for block in raw.get("statistics") or []:
        values = {s.get("type"): s.get("value") for s in block.get("statistics") or []}
        if not values:
            continue
        team_id = _block_team(raw, block, "estadísticas de equipo")
        if team_id is None:
            continue
        row = {"fixture_id": fixture_id, "team_id": team_id}
        for api_name, col in TEAM_STAT_FIELDS.items():
            value = _int(values.get(api_name))
            row[col] = value if value is not None or col == "possession" else 0
        row["xg"] = _decimal(values.get("expected_goals"))
        row["raw_payload"] = block
        row["fetched_at"] = fetched_at
        rows.append(row)
    return rows


def player_stats_rows(
    raw: dict[str, Any], fetched_at: datetime
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(jugadores, estadísticas por jugador) de un partido.

    Un suplente que no entró viene con minutes NULL: se guarda con 0 minutos y conteos NULL.

    A veces el bloque de un equipo llega con otro ID y sin nombre (partido 1492399: Chapecoense, 132, llegó
    como 22722, que no es ninguno de los dos). Se asigna al equipo del partido sin bloque propio si las
    alineaciones y los eventos ponen ahí a sus jugadores; si no hay esa evidencia, el bloque se descarta.
    """
    fixture_id = raw["fixture"]["id"]
    blocks = raw.get("players") or []
    teams = _fixture_teams(raw)
    free = teams - {(block.get("team") or {}).get("id") for block in blocks}
    players, stats = [], []
    for block in blocks:
        team_id = (block.get("team") or {}).get("id")
        if team_id not in teams:
            ids = {(item.get("player") or {}).get("id") for item in block.get("players") or []}
            found = _team_by_players(raw, {i for i in ids if isinstance(i, int) and i > 0}, free)
            if found is None:
                log.warning("partido %s: estadísticas de jugadores del equipo %s descartadas (no es de este partido)", fixture_id, team_id)
                continue
            log.warning("partido %s: estadísticas de jugadores con equipo %s asignadas a %s (alineaciones y eventos)", fixture_id, team_id, found)
            team_id = found
            free.discard(found)
        for item in block.get("players") or []:
            player = item.get("player") or {}
            player_id = player.get("id")
            name = _clean_name(player.get("name"))
            if not isinstance(player_id, int) or player_id <= 0 or not name:
                continue
            s = (item.get("statistics") or [{}])[0]
            games = s.get("games") or {}
            minutes = _int(games.get("minutes")) or 0
            played = minutes > 0

            def count(value: Any) -> int | None:
                v = _int(value)
                return (v or 0) if played else v

            goals = s.get("goals") or {}
            shots = s.get("shots") or {}
            cards = s.get("cards") or {}
            fouls = s.get("fouls") or {}
            penalty = s.get("penalty") or {}
            players.append({"id": player_id, "name": name, "photo": player.get("photo"), "fetched_at": fetched_at})
            stats.append(
                {
                    "fixture_id": fixture_id,
                    "player_id": player_id,
                    "team_id": team_id,
                    "minutes": minutes,
                    "position": games.get("position"),
                    "is_substitute": games.get("substitute"),
                    "rating": _decimal(games.get("rating")),
                    "goals": count(goals.get("total")),
                    "assists": count(goals.get("assists")),
                    "shots_total": count(shots.get("total")),
                    "shots_on": count(shots.get("on")),
                    "yellow": count(cards.get("yellow")),
                    "red": count(cards.get("red")),
                    "fouls_committed": count(fouls.get("committed")),
                    "key_passes": count((s.get("passes") or {}).get("key")),
                    "penalty_scored": count(penalty.get("scored")),
                    "penalty_missed": count(penalty.get("missed")),
                    "raw_payload": item,
                    "fetched_at": fetched_at,
                }
            )
    return players, stats


def event_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    fixture_id = raw["fixture"]["id"]
    rows = []
    for seq, e in enumerate(raw.get("events") or [], 1):
        time = e.get("time") or {}
        player = e.get("player") or {}
        rows.append(
            {
                "fixture_id": fixture_id,
                "seq": seq,
                "minute": time.get("elapsed"),
                "extra": time.get("extra"),
                "team_id": (e.get("team") or {}).get("id"),
                "player_id": player.get("id"),
                "player_name": _clean_name(player.get("name")) or None,
                "assist_id": (e.get("assist") or {}).get("id"),
                "type": e.get("type") or "?",
                "detail": e.get("detail"),
                "comments": e.get("comments"),
            }
        )
    return rows


def lineup_rows(
    raw: dict[str, Any], fetched_at: datetime
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(jugadores con nombre corto, filas de alineación) de un partido."""
    fixture_id = raw["fixture"]["id"]
    players, rows = [], []
    for block in raw.get("lineups") or []:
        team_id = _block_team(raw, block, "alineaciones")
        if team_id is None:
            continue
        for key, starter in (("startXI", True), ("substitutes", False)):
            for item in block.get(key) or []:
                p = item.get("player") or {}
                if not isinstance(p.get("id"), int) or p["id"] <= 0 or not _clean_name(p.get("name")):
                    continue
                players.append({"id": p["id"], "name": _clean_name(p["name"]), "photo": None, "fetched_at": fetched_at})
                rows.append(
                    {
                        "fixture_id": fixture_id,
                        "team_id": team_id,
                        "player_id": p["id"],
                        "is_starter": starter,
                        "position": p.get("pos"),
                        "grid": p.get("grid"),
                        "formation": block.get("formation"),
                        "fetched_at": fetched_at,
                    }
                )
    return players, rows


INJURY_STATUS = {"Missing Fixture": "out", "Questionable": "questionable"}


def injury_rows(raw: dict[str, Any], fetched_at: datetime) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """(jugador, fila de baja) de un elemento de /injuries; None si el tipo no se reconoce."""
    player = raw.get("player") or {}
    status = INJURY_STATUS.get(player.get("type"))
    name = _clean_name(player.get("name"))
    if status is None or not isinstance(player.get("id"), int) or player["id"] <= 0 or not name:
        return None
    return (
        {"id": player["id"], "name": name, "photo": player.get("photo"), "fetched_at": fetched_at},
        {
            "fixture_id": raw["fixture"]["id"],
            "player_id": player["id"],
            "team_id": raw["team"]["id"],
            "status": status,
            "reason": player.get("reason"),
            "fetched_at": fetched_at,
        },
    )


def odds_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Aplana {fixture, bookmakers[].bets[].values[]} en una fila por selección.

    Descarta momios no numéricos o <= 1 y duplicados exactos dentro del mismo partido.
    """
    fixture_id = raw["fixture"]["id"]
    rows: dict[tuple, dict[str, Any]] = {}
    for bookmaker in raw.get("bookmakers") or []:
        for bet in bookmaker.get("bets") or []:
            for value in bet.get("values") or []:
                selection = _clean_name(str(value.get("value") or ""))
                odd = _decimal(value.get("odd"))
                if not selection or odd is None or odd <= 1:
                    continue
                key = (fixture_id, bookmaker["id"], bet["id"], selection)
                rows[key] = {
                    "fixture_id": fixture_id,
                    "bookmaker_id": bookmaker["id"],
                    "bookmaker_name": bookmaker.get("name"),
                    "bet_id": bet["id"],
                    "bet_name": bet.get("name"),
                    "selection": selection,
                    "odd": odd,
                }
    return list(rows.values())
