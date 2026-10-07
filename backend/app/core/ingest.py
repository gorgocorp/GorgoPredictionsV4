"""Piezas comunes de la ingesta: registro de cada corrida, upsert por lote e historial de momios.

Las descargas ocurren fuera de las transacciones; cada lote se guarda en una transacción corta.
"""

import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from app.apisports import ApiSportsClient

log = logging.getLogger(__name__)

JSON_COLUMNS = {"raw_payload", "coverage"}
# Tablas con updated_at: un upsert que actualiza la fila también lo renueva.
TOUCH_UPDATED_AT = {
    ("nba", "teams"), ("nba", "players"), ("nba", "games"),
    ("futbol", "leagues"), ("futbol", "teams"), ("futbol", "players"), ("futbol", "fixtures"),
}


@dataclass
class RunStats:
    id: int
    received: int = 0
    written: int = 0
    skipped: int = 0


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def ingest_run(conn: psycopg.Connection, api: ApiSportsClient, sport: str, job: str, **params: Any) -> Iterator[RunStats]:
    """Registra la corrida en core.ingest_runs y la cierra como success o failed (con el error)."""
    requests_before = api.requests_made
    with conn.transaction():
        run_id = conn.execute(
            "INSERT INTO core.ingest_runs (sport, job, params) VALUES (%s, %s, %s) RETURNING id",
            (sport, job, Jsonb(params)),
        ).fetchone()["id"]
    stats = RunStats(id=run_id)
    try:
        yield stats
    except Exception as exc:
        conn.rollback()
        _finish_run(conn, stats, "failed", api.requests_made - requests_before, f"{type(exc).__name__}: {exc}")
        raise
    _finish_run(conn, stats, "success", api.requests_made - requests_before, None)
    log.info("%s %s %s: recibidos=%d escritos=%d omitidos=%d", sport, job, params, stats.received, stats.written, stats.skipped)


def _finish_run(conn: psycopg.Connection, stats: RunStats, status: str, requests: int, error: str | None) -> None:
    with conn.transaction():
        conn.execute(
            """
            UPDATE core.ingest_runs
            SET status = %s, requests_made = %s, rows_received = %s, rows_written = %s,
                rows_skipped = %s, error = %s, finished_at = now()
            WHERE id = %s
            """,
            (status, requests, stats.received, stats.written, stats.skipped, error, stats.id),
        )


def upsert(
    conn: psycopg.Connection,
    table: tuple[str, str],
    rows: Sequence[dict[str, Any]],
    key: Sequence[str],
    do_nothing: bool = False,
) -> int:
    """INSERT … ON CONFLICT por lote en `table` = (esquema, tabla). Devuelve las filas enviadas."""
    if not rows:
        return 0
    # Último valor por llave: executemany no admite la misma llave dos veces en un lote con DO UPDATE.
    unique = list({tuple(r[k] for k in key): r for r in rows}.values())
    cols = list(unique[0].keys())
    updates = [sql.SQL("{c} = EXCLUDED.{c}").format(c=sql.Identifier(c)) for c in cols if c not in key]
    if table in TOUCH_UPDATED_AT and "updated_at" not in cols:
        updates.append(sql.SQL("updated_at = now()"))
    action = sql.SQL("DO NOTHING") if do_nothing else sql.SQL("DO UPDATE SET {}").format(sql.SQL(", ").join(updates))
    query = sql.SQL("INSERT INTO {t} ({cols}) VALUES ({vals}) ON CONFLICT ({key}) {action}").format(
        t=sql.Identifier(*table),
        cols=sql.SQL(", ").join(map(sql.Identifier, cols)),
        vals=sql.SQL(", ").join(sql.Placeholder(c) for c in cols),
        key=sql.SQL(", ").join(map(sql.Identifier, key)),
        action=action,
    )
    adapted = [{k: Jsonb(v) if k in JSON_COLUMNS and v is not None else v for k, v in r.items()} for r in unique]
    with conn.cursor() as cur:
        cur.executemany(query, adapted)
    return len(unique)


def store_odds(
    conn: psycopg.Connection, schema: str, match_col: str, run_id: int, rows: list[dict[str, Any]], seen_at: datetime
) -> int:
    """Historial de momios de un deporte: una observación nueva si el momio cambió; si no, extiende last_seen_at.

    `match_col` es la columna del partido en `<schema>.odds_history` (game_id / fixture_id).
    """
    if not rows:
        return 0
    table, latest_view, match = sql.Identifier(schema, "odds_history"), sql.Identifier(schema, "v_odds_latest"), sql.Identifier(match_col)
    match_ids = sorted({r[match_col] for r in rows})
    latest = {
        (r[match_col], r["bookmaker_id"], r["bet_id"], r["selection"]): (r["id"], r["odd"])
        for r in conn.execute(
            sql.SQL("SELECT id, {m}, bookmaker_id, bet_id, selection, odd FROM {v} WHERE {m} = ANY(%s)").format(m=match, v=latest_view),
            (match_ids,),
        )
    }
    unchanged, changed = [], []
    for r in rows:
        prev = latest.get((r[match_col], r["bookmaker_id"], r["bet_id"], r["selection"]))
        if prev and prev[1] == r["odd"]:
            unchanged.append({"id": prev[0], "seen_at": seen_at, "run_id": run_id})
        else:
            changed.append({**r, "seen_at": seen_at, "run_id": run_id})

    with conn.cursor() as cur:
        if unchanged:
            cur.executemany(
                sql.SQL("UPDATE {} SET last_seen_at = %(seen_at)s, last_run_id = %(run_id)s WHERE id = %(id)s").format(table),
                unchanged,
            )
        if changed:
            cur.executemany(
                sql.SQL(
                    """
                    INSERT INTO {t} ({m}, bookmaker_id, bookmaker_name, bet_id, bet_name, selection, odd,
                                     first_seen_at, last_seen_at, first_run_id, last_run_id)
                    VALUES ({mp}, %(bookmaker_id)s, %(bookmaker_name)s, %(bet_id)s, %(bet_name)s, %(selection)s,
                            %(odd)s, %(seen_at)s, %(seen_at)s, %(run_id)s, %(run_id)s)
                    ON CONFLICT ({m}, bookmaker_id, bet_id, selection, first_seen_at) DO NOTHING
                    """
                ).format(t=table, m=match, mp=sql.Placeholder(match_col)),
                changed,
            )
    return len(changed)
