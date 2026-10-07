"""Scheduler único: sincroniza, liquida y registra picks de todos los deportes.

- Ciclo regular cada SYNC_INTERVAL_HOURS por deporte: sincronización completa y registro de picks de
  sus próximos `record_days` días.
- Corridas previas antes de cada horario de partidos, con la anticipación de cada deporte: sólo el
  deporte de esos partidos, con su corrida previa (fútbol: alineaciones, bajas y momios de lo que
  empieza pronto; NBA: sincronización completa) y registro de hoy y mañana.
- Cada deporte corre aislado: si uno falla (p. ej. venció su plan de la API), los demás siguen.
"""

import importlib
import logging
import os
import time
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

import psycopg

from app.config import BOOKMAKER, LOCAL_TZ
from app.core.sport import Sport
from app.db import connect, migrate

log = logging.getLogger("gorgo.scheduler")

# Se omite una previa si la corrida anterior del mismo deporte fue hace menos de MIN_GAP; los partidos
# que empiezan dentro de PREGAME_GROUP de la previa se atienden en la misma corrida.
PREGAME_LOOKAHEAD = timedelta(hours=36)
MIN_GAP = timedelta(minutes=20)
PREGAME_GROUP = timedelta(minutes=30)
# Deportes cuya próxima corrida cae a pocos minutos de otra se atienden juntos.
WAKE_TOLERANCE = timedelta(minutes=5)
EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def next_runs(
    conn: psycopg.Connection,
    now: datetime,
    last_runs: Mapping[str, datetime],
    interval: timedelta,
    leads: Mapping[str, timedelta],
) -> tuple[datetime, dict[str, str]]:
    """Próxima corrida: (cuándo, {deporte: "regular" | "previa"}) de los deportes que tocan entonces.

    Para cada deporte, la regular (cada `interval` desde su última corrida) o la previa a su siguiente
    horario de partidos si llega antes.
    """
    starts: dict[str, list[datetime]] = defaultdict(list)
    for r in conn.execute(
        """
        SELECT DISTINCT sport, starts_at FROM core.matches
        WHERE status = 'NS' AND starts_at BETWEEN %s AND %s AND sport = ANY(%s)
        ORDER BY starts_at
        """,
        (now, now + PREGAME_LOOKAHEAD, list(leads)),
    ).fetchall():
        starts[r["sport"]].append(r["starts_at"])

    plans: dict[str, tuple[datetime, str]] = {}
    for sport, lead in leads.items():
        regular = last_runs.get(sport, EPOCH) + interval
        plan = (regular, "regular")
        for start in starts.get(sport, []):
            pregame = start - lead
            if pregame <= now or pregame - last_runs.get(sport, EPOCH) < MIN_GAP:
                continue
            if pregame < regular:
                plan = (pregame, "previa")
            break
        plans[sport] = plan
    wake = min(when for when, _ in plans.values())
    return wake, {sport: kind for sport, (when, kind) in plans.items() if when <= wake + WAKE_TOLERANCE}


def _ops(sport: Sport):
    return importlib.import_module(f"app.sports.{sport.key}.ops")


def run_once(sports: Mapping[str, Sport], due: Mapping[str, str], last_full: dict[str, datetime], interval: timedelta) -> None:
    """Una corrida: sincroniza los deportes que tocan, liquida todo y registra sus picks."""
    from app.core.tracking import record_upcoming, settle_all

    started = datetime.now(timezone.utc)
    record_days: dict[str, int] = {}
    for key, kind in due.items():
        sport = sports[key]
        full = kind == "regular" or started - last_full.get(key, EPOCH) >= interval
        try:
            if full:
                _ops(sport).sync()
                last_full[key] = started
            else:
                _ops(sport).pregame_sync(sport.pregame_lead + PREGAME_GROUP)
        except Exception:
            log.exception("%s: la sincronización falló; se reintenta en la siguiente corrida", sport.label)
        record_days[key] = sport.record_days if full else 2

    try:
        with connect() as conn:
            settle_all(conn, sports.values())
    except Exception:
        log.exception("la liquidación falló; se reintenta en la siguiente corrida")

    today = datetime.now(LOCAL_TZ).date()
    for key, days in record_days.items():
        sport = sports[key]
        try:
            with connect() as conn:
                record_upcoming(conn, sport, sport.load_history(conn), today, days, BOOKMAKER)
        except Exception:
            log.exception("%s: el registro de picks falló; se reintenta en la siguiente corrida", sport.label)


def run_forever(sports: Mapping[str, Sport]) -> None:
    interval = timedelta(hours=float(os.getenv("SYNC_INTERVAL_HOURS", "6")))
    leads = {key: sport.pregame_lead for key, sport in sports.items()}
    with connect() as conn:
        migrate(conn)
    last_runs: dict[str, datetime] = {}
    last_full: dict[str, datetime] = {}
    due = {key: "regular" for key in sports}  # arranque: sincronización completa de todo
    while True:
        started = datetime.now(timezone.utc)
        run_once(sports, due, last_full, interval)
        for key in due:
            last_runs[key] = started
        try:
            with connect() as conn:
                wake, due = next_runs(conn, datetime.now(timezone.utc), last_runs, interval, leads)
        except Exception:
            log.exception("no se pudo calcular la próxima corrida; se usa el ciclo regular")
            wake, due = started + interval, {key: "regular" for key in sports}
        detail = ", ".join(f"{sports[key].label} ({kind})" for key, kind in due.items())
        log.info("siguiente corrida %s hora local: %s", wake.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M"), detail)
        time.sleep(max(60.0, (wake - datetime.now(timezone.utc)).total_seconds()))
