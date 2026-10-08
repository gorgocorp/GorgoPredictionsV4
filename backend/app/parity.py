"""Paridad con los proyectos anteriores: para un mismo día, V4 debe dar las mismas piernas y probabilidades.

Corre el motor del proyecto anterior (una copia temporal de su código, contra su base en sólo lectura) y el
de V4 (contra la base de V4), y compara partido por partido y pierna por pierna. Sirve para demostrar que
el código portado no cambió los modelos; antes del corte se corre después de `import-legacy --replace`.
No modifica nada de los proyectos anteriores.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.config import ROOT_DIR
from app.db import connect
from app.legacy_import import FUTBOL, NBA, Source, _snapshot, legacy_url

TOLERANCE = 1e-9  # el orden de las sumas cambia con el orden físico de las filas: diferencias de redondeo

# Se ejecuta con el código del proyecto anterior (paquete `app` de su copia temporal).
LEGACY_SCRIPT = r'''
import json, sys
from datetime import date
from app.db import connect
from app.engine.history import load_history
from app.engine.picks import generate_day

day, bookmaker = date.fromisoformat(sys.argv[1]), sys.argv[2]
with connect() as conn:
    hist = load_history(conn)
    cards = generate_day(conn, hist, day, bookmaker=bookmaker)
print(json.dumps([__SERIALIZE__(card) for card in cards]))
'''

SERIALIZER = r'''
def __SERIALIZE__(card):
    p = card.prediction
    if hasattr(p, "home_points"):
        projection = {"home": p.home_points, "away": p.away_points, "p_home": card.p_home_win,
                      "home_missing": card.home_missing, "away_missing": card.away_missing,
                      "home_roster": card.home_roster, "away_roster": card.away_roster}
    else:
        projection = {"home": p.home_goals, "away": p.away_goals, "p_home": p.p_home(), "p_draw": p.p_draw(),
                      "p_away": p.p_away(), "home_cards": card.cards.home if card.cards else None,
                      "away_cards": card.cards.away if card.cards else None, "lineups": card.lineups}
    match = getattr(card, "game_id", None) or getattr(card, "fixture_id")
    legs = []
    for c in card.candidates:
        s = c.spec
        legs.append({
            "key": [match, s.market, s.side, None if s.line is None else round(s.line, 1), s.team, s.stat, s.player_id],
            "description": c.description, "p_model": c.p_model, "odd": c.odd, "bookmaker": c.bookmaker,
            "p_market": c.p_market, "book_odds": c.book_odds, "hits": [list(h) for h in c.hits],
            "player_status": c.player_status,
        })
    return {"match": match, "starts_at": str(card.starts_at), "projection": projection, "legs": legs}
'''


@dataclass
class ParityResult:
    sport: str
    day: date
    matches: tuple[int, int] = (0, 0)  # (anterior, V4)
    legs: tuple[int, int] = (0, 0)
    max_diff: float = 0.0
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _legacy_backend(source: Source) -> Path:
    env_path = Path(os.getenv(source.env_var, ""))
    if not env_path.is_absolute():
        env_path = (ROOT_DIR / env_path).resolve()
    backend = env_path.parent / "backend"
    if not (backend / "app" / "engine" / "picks.py").is_file():
        raise RuntimeError(f"No encuentro el código de {source.project} en {backend}")
    return backend


def _read_only(url: str) -> str:
    """La misma conexión, con toda transacción en sólo lectura."""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}options=-c%20default_transaction_read_only%3Don"


def legacy_cards(source: Source, day: date, bookmaker: str) -> list[dict]:
    """Corre el motor del proyecto anterior sobre una copia temporal de su código (no escribe en su carpeta)."""
    env_path = _legacy_backend(source).parent / ".env"
    from dotenv import dotenv_values

    legacy_env = {k: v for k, v in dotenv_values(env_path).items() if v is not None}
    with tempfile.TemporaryDirectory(prefix=f"gorgo-parity-{source.sport}-") as tmp:
        shutil.copytree(_legacy_backend(source) / "app", Path(tmp) / "backend" / "app", ignore=shutil.ignore_patterns("__pycache__"))
        script = Path(tmp) / "backend" / "parity_run.py"
        script.write_text(SERIALIZER + LEGACY_SCRIPT, encoding="utf-8")
        env = {
            **os.environ,
            **{k: legacy_env[k] for k in ("BOOKMAKER", "PRICE_BOOKMAKERS", "NBA_CURRENT_SEASON", "LOCAL_TIMEZONE") if k in legacy_env},
            "DATABASE_URL": _read_only(legacy_url(source)),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        done = subprocess.run(
            [sys.executable, str(script), day.isoformat(), bookmaker],
            cwd=Path(tmp) / "backend", env=env, capture_output=True, text=True, encoding="utf-8",
        )
    if done.returncode != 0:
        raise RuntimeError(f"El motor de {source.project} falló:\n{done.stderr[-3000:]}")
    return json.loads(done.stdout.strip().splitlines()[-1])


def v4_cards(sport_key: str, day: date, bookmaker: str) -> list[dict]:
    from app.sports import get_sport

    sport = get_sport(sport_key)
    namespace: dict = {}
    exec(SERIALIZER, namespace)  # el mismo serializador que del lado anterior
    with connect() as conn:
        hist = sport.load_history(conn)
        cards = sport.generate_day(conn, hist, day, bookmaker)
    return json.loads(json.dumps([namespace["__SERIALIZE__"](card) for card in cards]))


def _diff(a, b) -> float | None:
    """Diferencia numérica (None si los valores no son comparables o son distintos en tipo)."""
    if a is None and b is None:
        return 0.0
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b) if not (math.isnan(a) and math.isnan(b)) else 0.0
    return None


def compare(sport: str, day: date, old: list[dict], new: list[dict]) -> ParityResult:
    result = ParityResult(sport, day, (len(old), len(new)))
    old_cards, new_cards = {c["match"]: c for c in old}, {c["match"]: c for c in new}
    if set(old_cards) != set(new_cards):
        result.problems.append(f"partidos distintos: sólo anterior {sorted(set(old_cards) - set(new_cards))}, sólo V4 {sorted(set(new_cards) - set(old_cards))}")
    old_legs, new_legs = {}, {}
    for match in set(old_cards) & set(new_cards):
        o, n = old_cards[match], new_cards[match]
        if o["starts_at"] != n["starts_at"]:
            result.problems.append(f"partido {match}: inicio {o['starts_at']} vs {n['starts_at']}")
        for name, value in o["projection"].items():
            d = _diff(value, n["projection"].get(name))
            if d is None and value != n["projection"].get(name):
                result.problems.append(f"partido {match}: proyección {name} {value} vs {n['projection'].get(name)}")
            elif d is not None:
                result.max_diff = max(result.max_diff, d)
                if d > TOLERANCE:
                    result.problems.append(f"partido {match}: proyección {name} {value} vs {n['projection'][name]}")
        old_legs.update({json.dumps(leg["key"]): leg for leg in o["legs"]})
        new_legs.update({json.dumps(leg["key"]): leg for leg in n["legs"]})
    result.legs = (len(old_legs), len(new_legs))
    only_old, only_new = set(old_legs) - set(new_legs), set(new_legs) - set(old_legs)
    if only_old or only_new:
        result.problems.append(f"piernas distintas: {len(only_old)} sólo en el anterior, {len(only_new)} sólo en V4 (p. ej. {sorted(only_old | only_new)[:3]})")
    for key in set(old_legs) & set(new_legs):
        o, n = old_legs[key], new_legs[key]
        for name in ("description", "odd", "bookmaker", "hits", "player_status"):
            if o[name] != n[name]:
                result.problems.append(f"pierna {key}: {name} {o[name]!r} vs {n[name]!r}")
        # V4 guarda más casas que los proyectos anteriores (Pinnacle): se comparan las que ellos tenían.
        old_books = o["book_odds"] or {}
        shared = {book: odd for book, odd in (n["book_odds"] or {}).items() if book in old_books}
        if old_books != shared:
            result.problems.append(f"pierna {key}: book_odds {old_books!r} vs {shared!r}")
        for name in ("p_model", "p_market"):
            d = _diff(o[name], n[name])
            if d is None:
                result.problems.append(f"pierna {key}: {name} {o[name]!r} vs {n[name]!r}")
            else:
                result.max_diff = max(result.max_diff, d)
                if d > TOLERANCE:
                    result.problems.append(f"pierna {key}: {name} {o[name]} vs {n[name]}")
    return result


def data_changed_since_import(source: Source) -> str | None:
    """Si la base anterior recibió ingestas después de la foto importada, la comparación no es justa."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT (params->>'snapshot_at')::timestamptz AS snapshot_at FROM core.ingest_runs
            WHERE job = 'import-legacy' AND sport = %s ORDER BY id DESC LIMIT 1
            """,
            (source.sport,),
        ).fetchone()
    if row is None:
        return "V4 no tiene una importación de este deporte"
    with connect() as conn:
        own = conn.execute(
            """
            SELECT count(*) AS n, max(started_at) AS last FROM core.ingest_runs
            WHERE sport = %s AND job <> 'import-legacy' AND started_at > %s
            """,
            (source.sport, row["snapshot_at"]),
        ).fetchone()
    if own["n"]:
        return f"V4 sincronizó {own['n']} veces por su cuenta después de la importación (última {own['last']:%Y-%m-%d %H:%M} UTC)"
    with _snapshot(legacy_url(source)) as src:
        newer = src.execute(
            "SELECT count(*) AS n, max(started_at) AS last FROM ingest_runs WHERE started_at > %s", (row["snapshot_at"],)
        ).fetchone()
    if newer["n"]:
        return f"{source.project} sincronizó {newer['n']} veces después de la importación (última {newer['last']:%Y-%m-%d %H:%M} UTC)"
    return None


def run_parity(sport: str, day: date, bookmaker: str) -> ParityResult:
    source = NBA if sport == "nba" else FUTBOL
    changed = data_changed_since_import(source)
    old = legacy_cards(source, day, bookmaker)
    new = v4_cards(sport, day, bookmaker)
    result = compare(sport, day, old, new)
    if changed:
        result.problems.insert(0, f"aviso: {changed}; vuelve a correr import-legacy --replace para comparar con los mismos datos")
    return result


def format_result(r: ParityResult) -> str:
    head = (
        f"{r.sport} {r.day}: partidos {r.matches[0]} / {r.matches[1]}, piernas {r.legs[0]} / {r.legs[1]} "
        f"(anterior / V4), diferencia máxima {r.max_diff:.2e}"
    )
    if r.ok:
        return f"{head}  -> IGUALES"
    lines = [f"{head}  -> DISTINTOS ({len(r.problems)})"] + [f"  - {p}" for p in r.problems[:15]]
    if len(r.problems) > 15:
        lines.append(f"  … y {len(r.problems) - 15} más")
    return "\n".join(lines)
