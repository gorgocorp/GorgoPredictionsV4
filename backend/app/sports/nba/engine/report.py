"""Formato de texto de los picks del día."""

from datetime import date

from app.sports.nba.engine.odds import american
from app.core.parlay import MODES, PARLAY_SIZES, Candidate, Parlay, build_parlay
from app.sports.nba.engine.picks import GameCard

SUSPICIOUS_EDGE = 0.10  # ventaja tan grande suele ser noticia (lesión) que el modelo no ve


def _short(matchup: str) -> str:
    away, home = matchup.split(" @ ")
    return f"{away.split()[-1]} @ {home.split()[-1]}"


def _pct(p: float | None) -> str:
    return f"{p:.0%}" if p is not None else "—"


def _odd(o: float | None) -> str:
    return f"{o:.2f} ({american(o)})" if o else "—"


def _hits(c: Candidate) -> str:
    return "  ".join(f"{h}/{n}" for h, n in c.hits) if c.hits else ""


def _flag(c: Candidate) -> str:
    return " (!)" if c.edge is not None and c.edge > SUSPICIOUS_EDGE else ""


def format_legs(cards: list[GameCard], top: int, min_prob: float) -> list[str]:
    legs = [c for card in cards for c in card.candidates if c.p_model >= min_prob]
    legs.sort(key=lambda c: (c.ev is not None, c.ev if c.ev is not None else c.p_model), reverse=True)
    priced = [c for c in legs if c.odd][:top]
    # Sin momio sólo interesan las que pagarían algo: momio justo >= 1.15 (prob. <= 87%).
    max_p = 1 / MODES["prob"][1].min_odd
    unpriced = sorted((c for c in legs if not c.odd and c.p_model <= max_p), key=lambda c: c.p_model, reverse=True)[:top]

    lines = []
    if priced:
        lines.append(f"Piernas con momio (ordenadas por valor esperado):")
        lines.append(f"  {'Partido':<22}{'Pierna':<42}{'Modelo':>7}{'Mercado':>8}  {'Momio casa':<15}{'EV':>7}  Últ.10/25")
        for c in priced:
            lines.append(
                f"  {_short(c.matchup):<22}{c.description[:41]:<42}{_pct(c.p_model):>7}{_pct(c.p_market):>8}  "
                f"{_odd(c.odd):<15}{c.ev:>+7.1%}  {_hits(c)}{_flag(c)}"
            )
        lines.append("")
    if unpriced:
        lines.append("Props sin momio de la casa (compáralos con tu casa: conviene si te pagan más que el momio justo):")
        lines.append(f"  {'Partido':<22}{'Pierna':<42}{'Modelo':>7}  {'Momio justo':<15}Últ.10/25")
        for c in unpriced:
            lines.append(f"  {_short(c.matchup):<22}{c.description[:41]:<42}{_pct(c.p_model):>7}  {_odd(c.fair_odd):<15}{_hits(c)}")
        lines.append("")
    return lines


def format_parlay(parlay: Parlay) -> list[str]:
    odd = parlay.odd
    head = f"prob. {parlay.probability:.1%} | momio justo {_odd(parlay.fair_odd)}"
    if odd:
        head += f" | momio casa {_odd(odd)} | EV {parlay.ev:+.1%}"
    lines = [f"    {head}"]
    for c in parlay.legs:
        price = f"@ {c.odd:.2f}" if c.odd else "(sin momio)"
        lines.append(f"      - {_short(c.matchup):<20} {c.description:<42} {_pct(c.p_model):>4} {price}{_flag(c)}")
    return lines


def format_day(day: date, bookmaker: str, cards: list[GameCard], top: int = 25) -> str:
    lines = [f"NBA — picks para {day:%Y-%m-%d} (precios de: {bookmaker})", ""]
    if not cards:
        return "\n".join(lines + ["No hay partidos ese día."])

    lines.append("Proyecciones del modelo:")
    for card in cards:
        p = card.prediction
        away, home = card.matchup.split(" @ ")
        lines.append(
            f"  {card.matchup:<48} {away.split()[-1]} {p.away_points:5.1f} - {p.home_points:5.1f} {home.split()[-1]}"
            f"  | total {p.total:5.1f} | gana local {p.p_home_win():.0%}{'' if card.has_odds else '  (sin momios)'}"
        )
    lines.append("")
    lines += format_legs(cards, top, min_prob=0.55)

    candidates = [c for card in cards for c in card.candidates]
    for mode, (title, filters) in MODES.items():
        lines.append(f"PARLAYS — {title}")
        built = False
        for n in PARLAY_SIZES:
            parlay = build_parlay(candidates, n, mode, filters)
            if parlay is None:
                continue
            built = True
            lines.append(f"  [{n} piernas]")
            lines += format_parlay(parlay)
        if not built:
            lines.append("  No hay suficientes piernas que cumplan los filtros (se necesita al menos una por partido en 2 partidos).")
        lines.append("")

    lines.append("Notas:")
    lines.append("  - Una pierna por partido: piernas del mismo partido están correlacionadas.")
    lines.append("  - El modelo no sabe de lesiones ni descansos anunciados. (!) = ventaja > 10 pts sobre el mercado: revisa noticias.")
    lines.append("  - Backtest 2025-26: los parlays cortos (2–3 piernas) de props acertaron 5–6 pts menos de lo predicho")
    lines.append("    (sesgo de selección); los de ganadores, algo más. Toma la probabilidad de los parlays cortos con ese margen.")
    return "\n".join(lines)
