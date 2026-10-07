"""Valor real de cada pierna para el historial y tus apuestas ("qué pasó en realidad").

Funciones puras (sin base de datos) para poder probarlas aisladas.
"""

from typing import Any

from app.sports.futbol.engine.player_model import STAT_LABELS

FINISHED = ("FT", "AET", "PEN")
CANCELLED = ("PST", "CANC", "ABD", "AWD", "WO")
LIVE = ("1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE")


def player_value(r: dict[str, Any]) -> float | None:
    """Valor real de la estadística de una prop (`r` trae las columnas de fixture_player_stats)."""
    stat = r["stat"]
    if stat == "goals":
        return r["goals"] or 0
    if stat == "assists":
        return r["assists"] or 0
    if stat == "ga":
        return (r["goals"] or 0) + (r["assists"] or 0)
    if stat == "shots":
        return r["shots_total"] or 0
    if stat == "shots_on":
        return r["shots_on"] or 0
    if stat == "cards":
        return (r["yellow"] or 0) + (r["red"] or 0)
    raise ValueError(f"estadística desconocida: {stat}")


def leg_outcome(r: dict[str, Any]) -> dict[str, Any]:
    """Valor real de una pierna: {"value": número o None, "text": explicación corta}.

    `r` trae: market, side, line, team, stat, status, ft_home, ft_away, home_name, away_name,
    home_cards, away_cards y, para props: minutes, goals, assists, shots_total, shots_on, yellow,
    red, fixture_has_players.
    """
    status = r["status"]
    if status in CANCELLED:
        return {"value": None, "text": "Partido pospuesto o cancelado"}
    if status not in FINISHED or r["ft_home"] is None:
        return {"value": None, "text": "Programado" if status in ("NS", "TBD") else "En juego" if status in LIVE else "Sin resultado todavía"}

    h, a = int(r["ft_home"]), int(r["ft_away"])
    home, away = r["home_name"], r["away_name"]
    market = r["market"]
    if market in ("1x2", "dc", "score"):
        return {"value": h - a, "text": f"Terminó {home} {h}-{a} {away}"}
    if market == "total":
        return {"value": h + a, "text": f"{h + a} goles ({h}-{a})"}
    if market == "team_total":
        team, goals = (home, h) if r["team"] == "home" else (away, a)
        return {"value": goals, "text": f"{team} anotó {goals}"}
    if market == "btts":
        return {"value": int(h > 0 and a > 0), "text": f"{'Anotaron' if h > 0 and a > 0 else 'No anotaron'} ambos ({h}-{a})"}
    if market in ("cards", "team_cards"):
        hc, ac = r.get("home_cards"), r.get("away_cards")
        if hc is None or ac is None:
            return {"value": None, "text": "Sin estadísticas de tarjetas todavía"}
        if market == "cards":
            return {"value": hc + ac, "text": f"{hc + ac} tarjetas ({home} {hc}, {away} {ac})"}
        team, cards = (home, hc) if r["team"] == "home" else (away, ac)
        return {"value": cards, "text": f"{team} recibió {cards} tarjetas"}
    if market == "player":
        if r.get("minutes") is None:
            return {"value": None, "text": "No jugó" if r.get("fixture_has_players") else "Sin estadísticas todavía"}
        if r["minutes"] == 0:
            return {"value": None, "text": "No jugó"}
        value = player_value(r)
        return {"value": value, "text": f"{value:g} {STAT_LABELS[r['stat']]} en {r['minutes']} min"}
    raise ValueError(f"mercado desconocido: {market}")
