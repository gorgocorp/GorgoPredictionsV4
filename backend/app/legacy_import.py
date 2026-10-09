"""Importa el historial de los proyectos anteriores: GorgoNBAParlays (NBA) y GorgoPredictionsV3 (fútbol).

No modifica nada de esos proyectos. Cada base se lee en una sola transacción de sólo lectura con
aislamiento REPEATABLE READ (una foto consistente aunque su scheduler siga escribiendo) y todo se escribe
en V4 en una sola transacción: si algo falla, no queda nada a medias.

- Tablas de cada deporte (esquemas nba y futbol): se copian tal cual, con los IDs de su proveedor.
- core: las ingestas, picks, parlays y apuestas de los dos proyectos se renumeran porque sus IDs chocan
  entre sí; la correspondencia queda en core.legacy_ids. Las marcas de tiempo se conservan: son la
  evidencia de que cada pick y cada apuesta se registró antes del partido.
- Antes de escribir se comprueba que las tablas y columnas de origen sean las esperadas (que nada se
  quede fuera). Al final se comparan conteos y huellas de los valores contra la foto de origen; si algo
  no cuadra, se revierte todo.
"""

import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import ROOT_DIR
from app.sports.futbol.matches import sync_matches as sync_futbol_matches
from app.sports.nba.matches import sync_matches as sync_nba_matches


class LegacyImportError(RuntimeError):
    pass


@dataclass(frozen=True)
class Source:
    sport: str
    project: str
    url_var: str  # URL directa de la base anterior (opcional)
    env_var: str  # ruta al .env del proyecto anterior, del que se toma DATABASE_URL
    match_table: str  # tabla de partidos del deporte
    match_col: str  # columna del partido en picks
    day_col: str  # columna del día en parlays
    tables: tuple[str, ...]  # se copian tal cual, en orden de llaves foráneas
    special: tuple[str, ...]  # se copian con un paso propio (ver _import_sport)
    sync_matches: Callable[[psycopg.Connection], int]


NBA = Source(
    sport="nba",
    project="GorgoNBAParlays",
    url_var="LEGACY_NBA_DATABASE_URL",
    env_var="LEGACY_NBA_ENV",
    match_table="games",
    match_col="game_id",
    day_col="game_date",
    tables=(
        "teams", "players", "games", "player_game_stats", "team_game_stats", "game_projections",
        "injury_reports", "injury_report_teams", "injury_entries", "availability_overrides",
    ),
    special=("seasons", "odds_history"),
    sync_matches=sync_nba_matches,
)

FUTBOL = Source(
    sport="futbol",
    project="GorgoPredictionsV3",
    url_var="LEGACY_FUTBOL_DATABASE_URL",
    env_var="LEGACY_FUTBOL_ENV",
    match_table="fixtures",
    match_col="fixture_id",
    day_col="match_date",
    tables=(
        "leagues", "teams", "players", "fixtures", "fixture_team_stats", "fixture_player_stats",
        "fixture_events", "fixture_lineups", "injuries", "availability_overrides", "fixture_projections",
    ),
    special=("odds_history",),
    sync_matches=sync_futbol_matches,
)

SOURCES = (NBA, FUTBOL)

# Tablas de los proyectos anteriores que pasan a core, y las que no se importan.
TO_CORE = ("ingest_runs", "picks", "parlays", "parlay_legs", "user_bets", "user_bet_legs")
IGNORED = ("schema_migrations",)

# Columnas de las tablas que pasan a core, tal como están en los proyectos anteriores
# (además de su id y de la columna del partido o del día, que cambian de nombre).
RUN_COLUMNS = (
    "job", "params", "status", "requests_made", "rows_received", "rows_written", "rows_skipped",
    "error", "started_at", "finished_at",
)
PICK_COLUMNS = (
    "market", "side", "line", "team", "stat", "player_id", "description", "p_model", "odd", "bookmaker",
    "p_market", "model_version", "first_evaluated_at", "evaluated_at", "result", "settled_at",
    "hits_10", "games_10", "hits_25", "games_25", "player_status", "book_odds",
)
PARLAY_COLUMNS = (
    "mode", "n_legs", "probability", "odd", "bookmaker", "model_version", "evaluated_at", "result",
    "settled_odd", "settled_at",
)
LEG_COLUMNS = ("position", "description", "p_model", "odd")
BET_COLUMNS = (
    "bookmaker", "stake", "odd", "model_probability", "note", "created_at", "first_start", "result",
    "settled_odd", "payout", "settled_at",
)

# Tablas temporales (se borran al terminar cada deporte) con los tipos de las tablas de origen.
STAGE_DDL = {
    "stage_runs": """
        legacy_id BIGINT PRIMARY KEY, job TEXT NOT NULL, params JSONB NOT NULL, status TEXT NOT NULL,
        requests_made INTEGER NOT NULL, rows_received INTEGER NOT NULL, rows_written INTEGER NOT NULL,
        rows_skipped INTEGER NOT NULL, error TEXT, started_at TIMESTAMPTZ NOT NULL, finished_at TIMESTAMPTZ,
        id BIGINT""",
    "stage_picks": """
        legacy_id BIGINT PRIMARY KEY, external_id INTEGER NOT NULL, market TEXT, side TEXT, line NUMERIC(6, 1),
        team TEXT, stat TEXT, player_id INTEGER, description TEXT, p_model NUMERIC(6, 4), odd NUMERIC(10, 3),
        bookmaker TEXT, p_market NUMERIC(6, 4), model_version TEXT, first_evaluated_at TIMESTAMPTZ,
        evaluated_at TIMESTAMPTZ, result TEXT, settled_at TIMESTAMPTZ, hits_10 SMALLINT, games_10 SMALLINT,
        hits_25 SMALLINT, games_25 SMALLINT, player_status TEXT, book_odds JSONB, id BIGINT""",
    "stage_parlays": """
        legacy_id BIGINT PRIMARY KEY, day DATE NOT NULL, mode TEXT, n_legs SMALLINT, probability NUMERIC(8, 6),
        odd NUMERIC(12, 3), bookmaker TEXT, model_version TEXT, evaluated_at TIMESTAMPTZ, result TEXT,
        settled_odd NUMERIC(12, 3), settled_at TIMESTAMPTZ, id BIGINT""",
    "stage_parlay_legs": """
        parlay_id BIGINT NOT NULL, pick_id BIGINT NOT NULL, position SMALLINT, description TEXT,
        p_model NUMERIC(6, 4), odd NUMERIC(10, 3)""",
    "stage_bets": """
        legacy_id BIGINT PRIMARY KEY, bookmaker TEXT, stake NUMERIC(12, 2), odd NUMERIC(10, 3),
        model_probability NUMERIC(8, 6), note TEXT, created_at TIMESTAMPTZ, first_start TIMESTAMPTZ, result TEXT,
        settled_odd NUMERIC(10, 3), payout NUMERIC(12, 2), settled_at TIMESTAMPTZ, id BIGINT""",
    "stage_bet_legs": """
        bet_id BIGINT NOT NULL, position SMALLINT, pick_id BIGINT NOT NULL, description TEXT,
        p_model NUMERIC(6, 4), odd NUMERIC(10, 3)""",
}


@dataclass
class SportReport:
    sport: str
    project: str
    database: str
    snapshot_at: datetime
    # (tabla, filas en origen, filas en V4)
    tables: list[tuple[str, int, int]] = field(default_factory=list)
    # (control, origen, V4); un control que no cuadra revierte toda la importación
    checks: list[tuple[str, object, object]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- conexión a los proyectos anteriores


def legacy_url(source: Source) -> str:
    """URL de la base anterior: la directa si está en el .env de V4; si no, DATABASE_URL de su propio .env."""
    url = os.getenv(source.url_var, "").strip()
    if url:
        return url
    env_path = os.getenv(source.env_var, "").strip()
    if not env_path:
        raise LegacyImportError(f"Falta {source.url_var} o {source.env_var} en el .env de V4")
    path = Path(env_path)
    if not path.is_absolute():
        path = (ROOT_DIR / path).resolve()
    if not path.is_file():
        raise LegacyImportError(f"No existe {path} ({source.env_var})")
    url = (dotenv_values(path).get("DATABASE_URL") or "").strip()
    if not url:
        raise LegacyImportError(f"{path} no tiene DATABASE_URL")
    return url


@contextmanager
def _snapshot(url: str) -> Iterator[psycopg.Connection]:
    """Conexión a una base anterior dentro de una transacción de sólo lectura (foto consistente)."""
    with psycopg.connect(url, row_factory=dict_row, options="-c TimeZone=UTC") as src:
        src.read_only = True
        src.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        with src.transaction():
            if src.execute("SHOW transaction_read_only").fetchone()["transaction_read_only"] != "on":
                raise LegacyImportError("La conexión a la base anterior no quedó en sólo lectura; no se importa nada")
            yield src


# ---------------------------------------------------------------- utilidades


def _columns(conn: psycopg.Connection, schema: str, table: str) -> list[str]:
    return [
        r["column_name"]
        for r in conn.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
    ]


def _names(columns) -> sql.Composable:
    return sql.SQL(", ").join(map(sql.Identifier, columns))


def _prefixed(alias: str, columns) -> sql.Composable:
    return sql.SQL(", ").join(sql.Identifier(alias, c) for c in columns)


def _count(conn: psycopg.Connection, table: sql.Composable, where: sql.Composable = sql.SQL(""), params=None) -> int:
    return conn.execute(sql.SQL("SELECT count(*) AS n FROM {} {}").format(table, where), params).fetchone()["n"]


def _copy(src_cur: psycopg.Cursor, dst_cur: psycopg.Cursor, select: sql.Composable, target: sql.Composable) -> None:
    """Pasa filas de la base anterior a V4 con COPY (formato de texto), sin cargarlas en memoria."""
    with src_cur.copy(sql.SQL("COPY ({}) TO STDOUT").format(select)) as copy_out:
        with dst_cur.copy(sql.SQL("COPY {} FROM STDIN").format(target)) as copy_in:
            for block in copy_out:
                copy_in.write(block)


def _stage(dst: psycopg.Connection, name: str) -> None:
    dst.execute(sql.SQL("CREATE TEMP TABLE {} ({}) ON COMMIT DROP").format(sql.Identifier(name), sql.SQL(STAGE_DDL[name])))


def _renumber(dst: psycopg.Connection, stage: str, target: tuple[str, str]) -> None:
    """IDs nuevos para las filas de `stage`: consecutivos, en el orden de los anteriores, después del máximo de `target`."""
    dst.execute(
        sql.SQL(
            """
            UPDATE {stage} s SET id = n.id
            FROM (SELECT legacy_id, (SELECT COALESCE(max(id), 0) FROM {target}) + row_number() OVER (ORDER BY legacy_id) AS id
                  FROM {stage}) n
            WHERE n.legacy_id = s.legacy_id
            """
        ).format(stage=sql.Identifier(stage), target=sql.Identifier(*target))
    )


def _map_ids(dst: psycopg.Connection, sport: str, entity: str, stage: str) -> None:
    dst.execute(
        sql.SQL("INSERT INTO core.legacy_ids (sport, entity, legacy_id, id) SELECT %s, %s, legacy_id, id FROM {}").format(
            sql.Identifier(stage)
        ),
        (sport, entity),
    )


def _insert(dst: psycopg.Connection, query: sql.Composable, params, expected: int, what: str) -> int:
    """Ejecuta un INSERT … SELECT y exige que escriba todas las filas preparadas."""
    written = dst.execute(query, params).rowcount
    if written != expected:
        raise LegacyImportError(f"{what}: se prepararon {expected} filas y se escribieron {written}")
    return written


def _fingerprint(conn: psycopg.Connection, rows: sql.Composable, params=None) -> tuple[int, int]:
    """(filas, huella) de una consulta que devuelve una columna de texto `t` por fila.

    La huella suma los primeros 48 bits del md5 de cada fila: no depende del orden y cambia si cambia
    cualquier valor.
    """
    r = conn.execute(
        sql.SQL(
            "SELECT count(*) AS n, COALESCE(sum(('x' || substr(md5(t), 1, 12))::bit(48)::bigint), 0) AS h FROM ({}) q"
        ).format(rows),
        params,
    ).fetchone()
    return r["n"], int(r["h"])


def _row_text(alias: str, columns) -> sql.Composable:
    return sql.SQL("row({})::text").format(_prefixed(alias, columns))


# ---------------------------------------------------------------- comprobaciones previas


def _check_destination(dst: psycopg.Connection) -> None:
    exists = dst.execute("SELECT to_regclass('core.legacy_ids') IS NOT NULL AS ok").fetchone()["ok"]
    if not exists:
        raise LegacyImportError("La base de V4 no tiene el esquema: corre `migrate` primero")


def _check_source(src: psycopg.Connection, dst: psycopg.Connection, source: Source) -> None:
    """Que la base anterior tenga exactamente las tablas y columnas esperadas: nada se queda fuera."""
    if src.execute("SELECT to_regnamespace('core') IS NOT NULL AS v4").fetchone()["v4"]:
        raise LegacyImportError(f"La base de {source.project} parece ser la de V4: revisa {source.url_var} / {source.env_var}")
    legacy = {
        r["table_name"]
        for r in src.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
    }
    expected = set(source.tables) | set(source.special) | set(TO_CORE)
    missing = expected - legacy
    unexpected = legacy - expected - set(IGNORED)
    if missing or unexpected:
        raise LegacyImportError(
            f"{source.project}: tablas distintas a las esperadas "
            f"(faltan: {sorted(missing) or 'ninguna'}; sin destino en V4: {sorted(unexpected) or 'ninguna'})"
        )
    for table in source.tables + source.special:
        old, new = set(_columns(src, "public", table)), set(_columns(dst, source.sport, table))
        if old != new:
            raise LegacyImportError(
                f"{source.project}.{table}: columnas distintas en V4 "
                f"(sólo en origen: {sorted(old - new) or 'ninguna'}; sólo en V4: {sorted(new - old) or 'ninguna'})"
            )
    core_columns = {
        "ingest_runs": {"id", *RUN_COLUMNS},
        "picks": {"id", source.match_col, *PICK_COLUMNS},
        "parlays": {"id", source.day_col, *PARLAY_COLUMNS},
        "parlay_legs": {"parlay_id", "pick_id", *LEG_COLUMNS},
        "user_bets": {"id", *BET_COLUMNS},
        "user_bet_legs": {"bet_id", "pick_id", *LEG_COLUMNS},
    }
    for table, expected_columns in core_columns.items():
        old = set(_columns(src, "public", table))
        if old != expected_columns:
            raise LegacyImportError(
                f"{source.project}.{table}: columnas distintas a las esperadas "
                f"(de más: {sorted(old - expected_columns) or 'ninguna'}; faltan: {sorted(expected_columns - old) or 'ninguna'})"
            )


# Tablas de V4 que no son datos importados: nba.seasons trae sus filas de referencia desde la migración, y las
# cuentas y sus sesiones no vienen de los proyectos anteriores (--replace no las borra).
NOT_IMPORTED = {("nba", "seasons"), ("core", "users"), ("core", "sessions")}


def _data_tables(dst: psycopg.Connection) -> list[tuple[str, str]]:
    """Tablas de datos de V4 (las que llena la importación)."""
    return [
        (r["table_schema"], r["table_name"])
        for r in dst.execute(
            """
            SELECT table_schema, table_name FROM information_schema.tables
            WHERE table_schema IN ('core', 'nba', 'futbol') AND table_type = 'BASE TABLE'
            ORDER BY table_schema, table_name
            """
        )
        if (r["table_schema"], r["table_name"]) not in NOT_IMPORTED
    ]


def existing_rows(dst: psycopg.Connection) -> dict[str, int]:
    """Tablas de V4 que ya tienen datos, con su número de filas."""
    counts = {}
    for schema, table in _data_tables(dst):
        n = _count(dst, sql.Identifier(schema, table))
        if n:
            counts[f"{schema}.{table}"] = n
    return counts


# ---------------------------------------------------------------- importación


def _import_sport(src: psycopg.Connection, dst: psycopg.Connection, source: Source) -> SportReport:
    s = source.sport
    report = SportReport(
        sport=s,
        project=source.project,
        database=src.info.dbname,
        snapshot_at=src.execute("SELECT now() AS t").fetchone()["t"],
    )
    _check_source(src, dst, source)

    with src.cursor() as scur, dst.cursor() as dcur:
        # Ingestas → core.ingest_runs (renumeradas: odds_history las referencia).
        _stage(dst, "stage_runs")
        _copy(
            scur, dcur,
            sql.SQL("SELECT id, {} FROM ingest_runs").format(_names(RUN_COLUMNS)),
            sql.SQL("stage_runs (legacy_id, {})").format(_names(RUN_COLUMNS)),
        )
        staged = _count(dst, sql.Identifier("stage_runs"))
        _renumber(dst, "stage_runs", ("core", "ingest_runs"))
        _insert(
            dst,
            sql.SQL(
                "INSERT INTO core.ingest_runs (id, sport, {cols}) OVERRIDING SYSTEM VALUE "
                "SELECT id, %s, {cols} FROM stage_runs ORDER BY legacy_id"
            ).format(cols=_names(RUN_COLUMNS)),
            (s,), staged, "ingest_runs",
        )
        _map_ids(dst, s, "ingest_run", "stage_runs")

        # Tablas del deporte, tal cual.
        for table in source.tables:
            columns = _columns(dst, s, table)
            _copy(
                scur, dcur,
                sql.SQL("SELECT {} FROM {}").format(_names(columns), sql.Identifier("public", table)),
                sql.SQL("{} ({})").format(sql.Identifier(s, table), _names(columns)),
            )

        # Temporadas NBA: la migración ya trae las conocidas; mandan las de la base anterior.
        if "seasons" in source.special:
            columns = _columns(dst, "nba", "seasons")
            dst.execute("CREATE TEMP TABLE stage_seasons (LIKE nba.seasons) ON COMMIT DROP")
            _copy(
                scur, dcur,
                sql.SQL("SELECT {} FROM seasons").format(_names(columns)),
                sql.SQL("stage_seasons ({})").format(_names(columns)),
            )
            dst.execute(
                sql.SQL(
                    "INSERT INTO nba.seasons ({cols}) SELECT {cols} FROM stage_seasons "
                    "ON CONFLICT (season) DO UPDATE SET {sets}"
                ).format(
                    cols=_names(columns),
                    sets=sql.SQL(", ").join(
                        sql.SQL("{0} = EXCLUDED.{0}").format(sql.Identifier(c)) for c in columns if c != "season"
                    ),
                )
            )

        # Momios: mismas filas e IDs, con los IDs nuevos de sus ingestas.
        columns = _columns(dst, s, "odds_history")
        dst.execute(sql.SQL("CREATE TEMP TABLE stage_odds (LIKE {}) ON COMMIT DROP").format(sql.Identifier(s, "odds_history")))
        _copy(
            scur, dcur,
            sql.SQL("SELECT {} FROM odds_history").format(_names(columns)),
            sql.SQL("stage_odds ({})").format(_names(columns)),
        )
        remapped = {"first_run_id": sql.SQL("fr.id"), "last_run_id": sql.SQL("lr.id")}
        _insert(
            dst,
            sql.SQL(
                """
                INSERT INTO {table} ({cols}) OVERRIDING SYSTEM VALUE
                SELECT {values}
                FROM stage_odds o
                JOIN core.legacy_ids fr ON fr.sport = %(sport)s AND fr.entity = 'ingest_run' AND fr.legacy_id = o.first_run_id
                JOIN core.legacy_ids lr ON lr.sport = %(sport)s AND lr.entity = 'ingest_run' AND lr.legacy_id = o.last_run_id
                """
            ).format(
                table=sql.Identifier(s, "odds_history"),
                cols=_names(columns),
                values=sql.SQL(", ").join(remapped.get(c, sql.Identifier("o", c)) for c in columns),
            ),
            {"sport": s}, _count(dst, sql.Identifier("stage_odds")), "odds_history",
        )

        # Registro común de partidos.
        source.sync_matches(dst)

        # Picks → core.picks, con el partido de core.matches.
        _stage(dst, "stage_picks")
        _copy(
            scur, dcur,
            sql.SQL("SELECT id, {}, {} FROM picks").format(sql.Identifier(source.match_col), _names(PICK_COLUMNS)),
            sql.SQL("stage_picks (legacy_id, external_id, {})").format(_names(PICK_COLUMNS)),
        )
        _renumber(dst, "stage_picks", ("core", "picks"))
        _insert(
            dst,
            sql.SQL(
                """
                INSERT INTO core.picks (id, sport, match_id, {cols}) OVERRIDING SYSTEM VALUE
                SELECT p.id, %(sport)s, m.id, {values}
                FROM stage_picks p
                JOIN core.matches m ON m.sport = %(sport)s AND m.external_id = p.external_id
                ORDER BY p.legacy_id
                """
            ).format(cols=_names(PICK_COLUMNS), values=_prefixed("p", PICK_COLUMNS)),
            {"sport": s}, _count(dst, sql.Identifier("stage_picks")), "picks",
        )
        _map_ids(dst, s, "pick", "stage_picks")

        # Parlays sugeridos y sus piernas.
        _stage(dst, "stage_parlays")
        _copy(
            scur, dcur,
            sql.SQL("SELECT id, {}, {} FROM parlays").format(sql.Identifier(source.day_col), _names(PARLAY_COLUMNS)),
            sql.SQL("stage_parlays (legacy_id, day, {})").format(_names(PARLAY_COLUMNS)),
        )
        _renumber(dst, "stage_parlays", ("core", "parlays"))
        _insert(
            dst,
            sql.SQL(
                "INSERT INTO core.parlays (id, sport, day, {cols}) OVERRIDING SYSTEM VALUE "
                "SELECT id, %s, day, {cols} FROM stage_parlays ORDER BY legacy_id"
            ).format(cols=_names(PARLAY_COLUMNS)),
            (s,), _count(dst, sql.Identifier("stage_parlays")), "parlays",
        )
        _map_ids(dst, s, "parlay", "stage_parlays")

        _stage(dst, "stage_parlay_legs")
        _copy(
            scur, dcur,
            sql.SQL("SELECT parlay_id, pick_id, {} FROM parlay_legs").format(_names(LEG_COLUMNS)),
            sql.SQL("stage_parlay_legs (parlay_id, pick_id, {})").format(_names(LEG_COLUMNS)),
        )
        _insert(
            dst,
            sql.SQL(
                """
                INSERT INTO core.parlay_legs (parlay_id, pick_id, {cols})
                SELECT pa.id, pk.id, {values}
                FROM stage_parlay_legs l
                JOIN stage_parlays pa ON pa.legacy_id = l.parlay_id
                JOIN stage_picks pk ON pk.legacy_id = l.pick_id
                """
            ).format(cols=_names(LEG_COLUMNS), values=_prefixed("l", LEG_COLUMNS)),
            None, _count(dst, sql.Identifier("stage_parlay_legs")), "parlay_legs",
        )

        # Tus apuestas y sus piernas: en V4 son del dueño (el primer administrador).
        _stage(dst, "stage_bets")
        _copy(
            scur, dcur,
            sql.SQL("SELECT id, {} FROM user_bets").format(_names(BET_COLUMNS)),
            sql.SQL("stage_bets (legacy_id, {})").format(_names(BET_COLUMNS)),
        )
        _renumber(dst, "stage_bets", ("core", "user_bets"))
        _insert(
            dst,
            sql.SQL(
                "INSERT INTO core.user_bets (id, user_id, {cols}) OVERRIDING SYSTEM VALUE "
                "SELECT id, (SELECT id FROM core.users WHERE role = 'admin' ORDER BY id LIMIT 1), {cols} "
                "FROM stage_bets ORDER BY legacy_id"
            ).format(cols=_names(BET_COLUMNS)),
            None, _count(dst, sql.Identifier("stage_bets")), "user_bets",
        )
        _map_ids(dst, s, "user_bet", "stage_bets")

        _stage(dst, "stage_bet_legs")
        _copy(
            scur, dcur,
            sql.SQL("SELECT bet_id, pick_id, {} FROM user_bet_legs").format(_names(LEG_COLUMNS)),
            sql.SQL("stage_bet_legs (bet_id, pick_id, {})").format(_names(LEG_COLUMNS)),
        )
        _insert(
            dst,
            sql.SQL(
                """
                INSERT INTO core.user_bet_legs (bet_id, pick_id, {cols})
                SELECT b.id, pk.id, {values}
                FROM stage_bet_legs l
                JOIN stage_bets b ON b.legacy_id = l.bet_id
                JOIN stage_picks pk ON pk.legacy_id = l.pick_id
                """
            ).format(cols=_names(LEG_COLUMNS), values=_prefixed("l", LEG_COLUMNS)),
            None, _count(dst, sql.Identifier("stage_bet_legs")), "user_bet_legs",
        )

    _verify(src, dst, source, report)

    for stage in ("stage_runs", "stage_seasons", "stage_odds", *[n for n in STAGE_DDL if n != "stage_runs"]):
        dst.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(stage)))
    return report


# ---------------------------------------------------------------- verificación


def _verify(src: psycopg.Connection, dst: psycopg.Connection, source: Source, report: SportReport) -> None:
    """Compara conteos y huellas de valores entre la foto de origen y lo escrito en V4."""
    s = source.sport
    sport_param = {"sport": s}

    # Tablas copiadas tal cual (y las especiales): mismas filas y mismos valores.
    for table in source.tables + source.special:
        columns = _columns(dst, s, table)
        if table == "odds_history":
            # Los IDs de ingesta cambiaron: se compara con los anteriores, vía core.legacy_ids.
            keep = [c for c in columns if c not in ("first_run_id", "last_run_id")]
            old = _fingerprint(
                src,
                sql.SQL("SELECT row({}, x.first_run_id, x.last_run_id)::text AS t FROM odds_history x").format(_prefixed("x", keep)),
            )
            new = _fingerprint(
                dst,
                sql.SQL(
                    """
                    SELECT row({cols}, fr.legacy_id, lr.legacy_id)::text AS t
                    FROM {table} x
                    JOIN core.legacy_ids fr ON fr.sport = %(sport)s AND fr.entity = 'ingest_run' AND fr.id = x.first_run_id
                    JOIN core.legacy_ids lr ON lr.sport = %(sport)s AND lr.entity = 'ingest_run' AND lr.id = x.last_run_id
                    """
                ).format(cols=_prefixed("x", keep), table=sql.Identifier(s, table)),
                sport_param,
            )
        elif table == "seasons":
            # V4 puede tener temporadas de más (de su migración); se comparan las de origen.
            old = _fingerprint(src, sql.SQL("SELECT {} AS t FROM seasons x").format(_row_text("x", columns)))
            seasons = [r["season"] for r in src.execute("SELECT season FROM seasons")]
            new = _fingerprint(
                dst,
                sql.SQL("SELECT {} AS t FROM nba.seasons x WHERE x.season = ANY(%(seasons)s)").format(_row_text("x", columns)),
                {"seasons": seasons},
            )
        else:
            old = _fingerprint(src, sql.SQL("SELECT {} AS t FROM {} x").format(_row_text("x", columns), sql.Identifier("public", table)))
            new = _fingerprint(dst, sql.SQL("SELECT {} AS t FROM {} x").format(_row_text("x", columns), sql.Identifier(s, table)))
        report.tables.append((table, old[0], new[0]))
        report.checks.append((f"{table}: valores", old, new))

    # core: mismas filas y valores, comparando con los IDs anteriores.
    core_pairs = {
        "ingest_runs": (
            sql.SQL("SELECT row(x.id, {})::text AS t FROM ingest_runs x").format(_prefixed("x", RUN_COLUMNS)),
            sql.SQL(
                "SELECT row(li.legacy_id, {})::text AS t FROM core.ingest_runs x "
                "JOIN core.legacy_ids li ON li.sport = %(sport)s AND li.entity = 'ingest_run' AND li.id = x.id"
            ).format(_prefixed("x", RUN_COLUMNS)),
        ),
        "picks": (
            sql.SQL("SELECT row(x.id, x.{}, {})::text AS t FROM picks x").format(
                sql.Identifier(source.match_col), _prefixed("x", PICK_COLUMNS)
            ),
            sql.SQL(
                "SELECT row(li.legacy_id, m.external_id, {})::text AS t FROM core.picks x "
                "JOIN core.matches m ON m.id = x.match_id "
                "JOIN core.legacy_ids li ON li.sport = %(sport)s AND li.entity = 'pick' AND li.id = x.id"
            ).format(_prefixed("x", PICK_COLUMNS)),
        ),
        "parlays": (
            sql.SQL("SELECT row(x.id, x.{}, {})::text AS t FROM parlays x").format(
                sql.Identifier(source.day_col), _prefixed("x", PARLAY_COLUMNS)
            ),
            sql.SQL(
                "SELECT row(li.legacy_id, x.day, {})::text AS t FROM core.parlays x "
                "JOIN core.legacy_ids li ON li.sport = %(sport)s AND li.entity = 'parlay' AND li.id = x.id"
            ).format(_prefixed("x", PARLAY_COLUMNS)),
        ),
        "parlay_legs": (
            sql.SQL("SELECT row(x.parlay_id, x.pick_id, {})::text AS t FROM parlay_legs x").format(_prefixed("x", LEG_COLUMNS)),
            sql.SQL(
                "SELECT row(pa.legacy_id, pk.legacy_id, {})::text AS t FROM core.parlay_legs x "
                "JOIN core.legacy_ids pa ON pa.sport = %(sport)s AND pa.entity = 'parlay' AND pa.id = x.parlay_id "
                "JOIN core.legacy_ids pk ON pk.sport = %(sport)s AND pk.entity = 'pick' AND pk.id = x.pick_id"
            ).format(_prefixed("x", LEG_COLUMNS)),
        ),
        "user_bets": (
            sql.SQL("SELECT row(x.id, {})::text AS t FROM user_bets x").format(_prefixed("x", BET_COLUMNS)),
            sql.SQL(
                "SELECT row(li.legacy_id, {})::text AS t FROM core.user_bets x "
                "JOIN core.legacy_ids li ON li.sport = %(sport)s AND li.entity = 'user_bet' AND li.id = x.id"
            ).format(_prefixed("x", BET_COLUMNS)),
        ),
        "user_bet_legs": (
            sql.SQL("SELECT row(x.bet_id, x.pick_id, {})::text AS t FROM user_bet_legs x").format(_prefixed("x", LEG_COLUMNS)),
            sql.SQL(
                "SELECT row(b.legacy_id, pk.legacy_id, {})::text AS t FROM core.user_bet_legs x "
                "JOIN core.legacy_ids b ON b.sport = %(sport)s AND b.entity = 'user_bet' AND b.id = x.bet_id "
                "JOIN core.legacy_ids pk ON pk.sport = %(sport)s AND pk.entity = 'pick' AND pk.id = x.pick_id"
            ).format(_prefixed("x", LEG_COLUMNS)),
        ),
    }
    for table, (old_q, new_q) in core_pairs.items():
        old, new = _fingerprint(src, old_q), _fingerprint(dst, new_q, sport_param)
        report.tables.append((f"{table} (a core)", old[0], new[0]))
        report.checks.append((f"{table}: valores", old, new))

    # Cada partido del deporte quedó en el registro común.
    games = _count(src, sql.Identifier("public", source.match_table))
    matches = _count(dst, sql.SQL("core.matches"), sql.SQL("WHERE sport = %(sport)s"), sport_param)
    report.checks.append(("partidos en core.matches", games, matches))

    # Resúmenes legibles (los mismos datos que cubren las huellas).
    report.checks.append((
        "picks por resultado",
        _by_result(src, sql.SQL("SELECT result FROM picks")),
        _by_result(dst, sql.SQL("SELECT result FROM core.picks WHERE sport = %(sport)s"), sport_param),
    ))
    report.checks.append((
        "parlays por resultado",
        _by_result(src, sql.SQL("SELECT result FROM parlays")),
        _by_result(dst, sql.SQL("SELECT result FROM core.parlays WHERE sport = %(sport)s"), sport_param),
    ))
    report.checks.append((
        "apuestas: monto y pago",
        _bet_totals(src, sql.SQL("SELECT stake, payout FROM user_bets")),
        _bet_totals(
            dst,
            sql.SQL(
                "SELECT b.stake, b.payout FROM core.user_bets b "
                "JOIN core.legacy_ids li ON li.sport = %(sport)s AND li.entity = 'user_bet' AND li.id = b.id"
            ),
            sport_param,
        ),
    ))

    bad = [(name, old, new) for name, old, new in report.checks if old != new]
    if bad:
        detail = "; ".join(f"{name}: origen {old} vs V4 {new}" for name, old, new in bad)
        raise LegacyImportError(f"{source.project}: la importación no cuadra, no se guardó nada ({detail})")

    if s == "nba":
        differ = dst.execute(
            """
            SELECT count(*) AS n FROM core.matches m JOIN nba.games g ON g.id = m.external_id
            WHERE m.sport = 'nba' AND m.local_date <> g.game_date
            """
        ).fetchone()["n"]
        report.notes.append(f"Partidos con día local distinto a su fecha en hora del Este: {differ}")
    running = _count(dst, sql.SQL("core.ingest_runs"), sql.SQL("WHERE sport = %(sport)s AND status = 'running'"), sport_param)
    if running:
        report.notes.append(f"Ingestas que estaban en curso en el origen al tomar la foto: {running} (se importaron tal cual)")


def _by_result(conn: psycopg.Connection, rows: sql.Composable, params=None) -> dict[str, int]:
    return {
        r["result"]: r["n"]
        for r in conn.execute(
            sql.SQL("SELECT COALESCE(result, 'pendiente') AS result, count(*) AS n FROM ({}) q GROUP BY 1 ORDER BY 1").format(rows),
            params,
        )
    }


def _bet_totals(conn: psycopg.Connection, rows: sql.Composable, params=None) -> tuple[int, str, str]:
    r = conn.execute(
        sql.SQL("SELECT count(*) AS n, COALESCE(sum(stake), 0) AS stake, COALESCE(sum(payout), 0) AS payout FROM ({}) q").format(rows),
        params,
    ).fetchone()
    return r["n"], f"{r['stake']:.2f}", f"{r['payout']:.2f}"


def _reset_identities(dst: psycopg.Connection) -> None:
    """Deja cada secuencia de identidad después del ID más alto (las filas importadas traen sus IDs)."""
    for r in dst.execute(
        """
        SELECT table_schema, table_name, column_name FROM information_schema.columns
        WHERE table_schema IN ('core', 'nba', 'futbol') AND is_identity = 'YES'
        """
    ).fetchall():
        table = sql.Identifier(r["table_schema"], r["table_name"])
        column = sql.Identifier(r["column_name"])
        dst.execute(
            sql.SQL("SELECT setval(pg_get_serial_sequence(%s, %s), COALESCE(max({col}), 1), max({col}) IS NOT NULL) FROM {table}").format(
                col=column, table=table
            ),
            (f"{r['table_schema']}.{r['table_name']}", r["column_name"]),
        )


def run_import(dst: psycopg.Connection, replace: bool = False) -> list[SportReport]:
    """Importa los dos proyectos anteriores en una sola transacción de V4.

    Si V4 ya tiene datos, sólo continúa con `replace=True`: borra todo lo de V4 (salvo las temporadas NBA
    de referencia) y lo vuelve a importar. Pensado para ensayos antes del corte y para la importación final.
    """
    _check_destination(dst)
    urls = [(source, legacy_url(source)) for source in SOURCES]
    existing = existing_rows(dst)
    if existing and not replace:
        listed = ", ".join(f"{t} ({n})" for t, n in existing.items())
        raise LegacyImportError(f"V4 ya tiene datos: {listed}. Usa --replace para borrarlos y volver a importar.")

    dst.execute("SET TIME ZONE 'UTC'")
    started = datetime.now(timezone.utc)
    t0 = time.monotonic()
    reports: list[SportReport] = []
    with dst.transaction():
        if existing:
            dst.execute(
                sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
                    sql.SQL(", ").join(sql.Identifier(*t) for t in _data_tables(dst))
                )
            )
        for source, url in urls:
            with _snapshot(url) as src:
                reports.append(_import_sport(src, dst, source))
        _reset_identities(dst)
        finished = datetime.now(timezone.utc)
        for report in reports:
            dst.execute(
                """
                INSERT INTO core.ingest_runs (sport, job, params, status, rows_received, rows_written, started_at, finished_at)
                VALUES (%s, 'import-legacy', %s, 'success', %s, %s, %s, %s)
                """,
                (
                    report.sport,
                    Jsonb({
                        "project": report.project,
                        "database": report.database,
                        "snapshot_at": report.snapshot_at.isoformat(),
                        "replaced": bool(existing),
                        "seconds": round(time.monotonic() - t0, 1),
                    }),
                    sum(old for _, old, _ in report.tables),
                    sum(new for _, _, new in report.tables),
                    started,
                    finished,
                ),
            )
    return reports


def format_report(reports: list[SportReport]) -> str:
    lines = []
    for r in reports:
        lines.append(f"{r.project} -> V4 ({r.sport})   base {r.database}, foto de {r.snapshot_at:%Y-%m-%d %H:%M:%S} UTC")
        lines.append(f"  {'Tabla':<30}{'Origen':>12}{'V4':>12}")
        for table, old, new in r.tables:
            mark = "" if old == new else "  <- distinto"
            lines.append(f"  {table:<30}{old:>12,}{new:>12,}{mark}")
        lines.append("  Controles (origen = V4):")
        for name, old, new in r.checks:
            if name.endswith(": valores"):
                continue  # las huellas ya se reflejan en la tabla de arriba; sólo se listan si fallan
            lines.append(f"    {name}: {new}" if old == new else f"    {name}: origen {old} vs V4 {new}  <- distinto")
        ok_values = sum(1 for name, old, new in r.checks if name.endswith(": valores") and old == new)
        lines.append(f"    huellas de valores iguales: {ok_values} de {sum(1 for n, _, _ in r.checks if n.endswith(': valores'))} tablas")
        for note in r.notes:
            lines.append(f"  Nota: {note}")
        lines.append("")
    return "\n".join(lines)
