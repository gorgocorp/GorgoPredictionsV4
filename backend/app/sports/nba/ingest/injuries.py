"""Reporte oficial de lesiones de la NBA (PDF público en su CDN).

URL: https://ak-static.cms.nba.com/referee/injury/Injury-Report_<fecha>_<hora>.pdf, hora del Este.
- Desde enero de 2026: cada 15 minutos, "_05_30PM".
- Antes: cada hora, "_05PM".
No se publica en pretemporada. No consume cuota de API-Basketball.

El PDF trae el texto pegado si se lee como texto plano, así que se lee por posición de cada
palabra: las columnas salen del encabezado y cada palabra se asigna a la columna donde empieza.
El motivo de la lesión ocupa varias líneas centradas verticalmente alrededor de la fila del
jugador; cada línea de motivo se asigna a la fila de jugador más cercana.
"""

import io
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import psycopg

from app.sports.nba.engine.odds import match_full_name, match_player

log = logging.getLogger(__name__)

BASE_URL = "https://ak-static.cms.nba.com/referee/injury/"
EASTERN = ZoneInfo("America/New_York")
SEARCH_WINDOW = timedelta(hours=10)
STATUSES = {"out", "doubtful", "questionable", "probable", "available"}
COLUMNS = ("game_date", "game_time", "matchup", "team", "player", "status", "reason")
# Encabezado del PDF -> columna. "Game" aparece dos veces (Game Date, Game Time).
HEADER_WORDS = {"Matchup": "matchup", "Team": "team", "Player": "player", "Current": "status", "Reason": "reason"}
TEAM_ALIASES = {"laclippers": "losangelesclippers"}
# Las líneas de un motivo quedan a pocos puntos de su fila (las filas van cada ~22 puntos).
MAX_REASON_OFFSET = 12


@dataclass
class ReportRow:
    game_date: date
    team: str
    player: str
    status: str
    # Fragmentos del motivo con su altura en la página, para unirlos de arriba hacia abajo.
    reason_parts: list[tuple[float, str]] = field(default_factory=list)

    @property
    def reason(self) -> str:
        return " ".join(text for _, text in sorted(self.reason_parts)).strip()


@dataclass
class ParsedReport:
    rows: list[ReportRow]
    teams: list[tuple[date, str, bool]]  # (fecha, equipo, entregó su lista)


# ---------------------------------------------------------------- URLs

def report_urls(moment: datetime) -> list[str]:
    """URLs posibles para un instante (hora del Este): formato de 15 min y formato por hora."""
    et = moment.astimezone(EASTERN)
    day = et.strftime("%Y-%m-%d")
    hour12 = et.strftime("%I%p")  # "05PM"
    urls = [f"{BASE_URL}Injury-Report_{day}_{hour12[:2]}_{et:%M}{hour12[2:]}.pdf"]
    if et.minute == 0:
        urls.append(f"{BASE_URL}Injury-Report_{day}_{hour12}.pdf")
    return urls


def candidate_times(now: datetime, window: timedelta = SEARCH_WINDOW) -> Iterable[datetime]:
    """Instantes a probar, del más reciente al más antiguo, en pasos de 15 minutos."""
    et = now.astimezone(EASTERN).replace(second=0, microsecond=0)
    t = et - timedelta(minutes=et.minute % 15)
    while et - t <= window:
        yield t
        t -= timedelta(minutes=15)


def find_latest_report(http: httpx.Client, now: datetime) -> tuple[str, datetime] | None:
    for t in candidate_times(now):
        for url in report_urls(t):
            if http.head(url).status_code == 200:
                return url, t
    return None


# ---------------------------------------------------------------- lectura del PDF

def _column_bounds(words: list[dict]) -> dict[str, float] | None:
    """x inicial de cada columna a partir de las palabras del encabezado."""
    bounds: dict[str, float] = {}
    game = sorted((w for w in words if w["text"] == "Game"), key=lambda w: w["x0"])
    if len(game) >= 2:
        bounds["game_date"], bounds["game_time"] = game[0]["x0"], game[1]["x0"]
    for w in words:
        col = HEADER_WORDS.get(w["text"])
        if col and col not in bounds:
            bounds[col] = w["x0"]
    return bounds if len(bounds) == len(COLUMNS) else None


def _lines(words: list[dict], tolerance: float = 2.0) -> list[tuple[float, list[dict]]]:
    lines: list[tuple[float, list[dict]]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(lines[-1][0] - w["top"]) <= tolerance:
            lines[-1][1].append(w)
        else:
            lines.append((w["top"], [w]))
    return lines


def _cells(line: list[dict], bounds: dict[str, float]) -> dict[str, str]:
    order = sorted(bounds.items(), key=lambda kv: kv[1])
    cells: dict[str, list[str]] = {}
    for w in sorted(line, key=lambda w: w["x0"]):
        col = order[0][0]
        for name, x in order:
            if w["x0"] + 2 >= x:
                col = name
        cells.setdefault(col, []).append(w["text"])
    return {k: " ".join(v) for k, v in cells.items()}


def parse_pages(pages: list[list[dict]]) -> ParsedReport:
    """Convierte las palabras de cada página (dicts con x0, top, text) en filas del reporte."""
    rows: list[ReportRow] = []
    teams: dict[tuple[date, str], bool] = {}
    bounds = None
    game_date: date | None = None
    team: str | None = None

    for words in pages:
        bounds = _column_bounds(words) or bounds
        if bounds is None:
            continue
        lines = _lines(words)
        # El encabezado de columnas sólo está en la primera página. Se reconoce porque "Matchup" y
        # "Reason" van en la misma línea (la palabra "Team" sola también aparece en motivos como
        # "Not With Team").
        header_top = next(
            (top for top, line in lines if {"Matchup", "Reason"} <= {w["text"] for w in line}), None
        )
        page_rows: list[tuple[float, ReportRow]] = []
        reasons: list[tuple[float, str]] = []

        for top, line in lines:
            if header_top is not None and top <= header_top + 1:
                continue  # título y encabezado
            text = " ".join(w["text"] for w in line)
            if re.fullmatch(r"Page \d+ of \d+", text) or text.startswith("Injury Report:"):
                continue  # pie de página y título (las páginas 2+ no repiten el encabezado de columnas)
            cells = _cells(line, bounds)
            if set(cells) == {"reason"}:
                # Línea suelta del motivo: puede ir arriba de la fila del jugador (incluso la primera).
                reasons.append((top, cells["reason"]))
                continue
            if "game_date" in cells and re.fullmatch(r"\d{2}/\d{2}/\d{4}", cells["game_date"]):
                game_date = datetime.strptime(cells["game_date"], "%m/%d/%Y").date()
            if "team" in cells:
                team = cells["team"]
            if game_date is None or team is None:
                continue
            if "NOT YET SUBMITTED" in text:
                teams[(game_date, team)] = False
                continue
            status = cells.get("status", "").strip().lower()
            if status in STATUSES and cells.get("player"):
                teams.setdefault((game_date, team), True)
                row = ReportRow(game_date, team, cells["player"], status)
                if cells.get("reason"):
                    row.reason_parts.append((top, cells["reason"]))
                page_rows.append((top, row))

        for top, text in reasons:
            # Un motivo que empieza al final de una página continúa arriba de la siguiente, lejos
            # de cualquier fila: pertenece al último jugador de la página anterior.
            if page_rows and (top >= page_rows[0][0] or page_rows[0][0] - top <= MAX_REASON_OFFSET or not rows):
                nearest = min(page_rows, key=lambda pr: abs(pr[0] - top))[1]
                nearest.reason_parts.append((top, text))
            elif rows:
                rows[-1].reason_parts.append((float("inf"), text))
        rows.extend(r for _, r in page_rows)

    return ParsedReport(rows, [(d, t, s) for (d, t), s in teams.items()])


def parse_pdf(content: bytes) -> ParsedReport:
    import pdfplumber  # dependencia pesada: sólo se carga al leer un reporte

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return parse_pages([page.extract_words(x_tolerance=1.2) for page in pdf.pages])


# ---------------------------------------------------------------- guardado

def report_name(name: str) -> str:
    """El reporte usa "Apellido, Nombre"; se pasa a "Nombre Apellido" para emparejar."""
    if "," in name:
        last, first = name.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return name


def _team_key(name: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    return TEAM_ALIASES.get(key, key)


def ingest_injuries(conn: psycopg.Connection, now: datetime, http: httpx.Client | None = None) -> dict[str, int] | None:
    """Descarga el reporte más reciente si es nuevo. None si no hay reporte (p. ej. pretemporada)."""
    own_http = http is None
    http = http or httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0 (GorgoPredictionsV4)"})
    try:
        found = find_latest_report(http, now)
        if found is None:
            log.info("lesiones: no hay reporte oficial en las últimas %s", SEARCH_WINDOW)
            return None
        url, report_at = found
        if conn.execute("SELECT 1 FROM nba.injury_reports WHERE report_at = %s", (report_at,)).fetchone():
            log.info("lesiones: el reporte de %s ya estaba guardado", report_at.strftime("%Y-%m-%d %H:%M ET"))
            return {"entries": 0, "new": 0}
        response = http.get(url)
        response.raise_for_status()
    finally:
        if own_http:
            http.close()

    parsed = parse_pdf(response.content)
    teams = {_team_key(r["name"]): r["id"] for r in conn.execute("SELECT id, name FROM nba.teams")}
    # Candidatos por equipo: jugadores que jugaron para él en el último año.
    rosters: dict[int, dict[int, str]] = {}
    for r in conn.execute(
        """
        SELECT DISTINCT p.team_id, pl.id, pl.name
        FROM nba.player_game_stats p JOIN nba.games g ON g.id = p.game_id JOIN nba.players pl ON pl.id = p.player_id
        WHERE g.starts_at > %s
        """,
        (now - timedelta(days=400),),
    ):
        rosters.setdefault(r["team_id"], {})[r["id"]] = r["name"]

    all_players = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM nba.players")}
    entries, unmatched = [], 0
    for row in parsed.rows:
        team_id = teams.get(_team_key(row.team))
        if team_id is None:
            log.warning("lesiones: equipo desconocido en el reporte: %r", row.team)
            continue
        name = report_name(row.player)
        player_id = match_player(name, rosters.get(team_id, {}))
        if player_id is None:
            # Traspasado estando lesionado: nunca jugó con su equipo nuevo. Se busca entre todos,
            # sólo por nombre completo y si es único.
            player_id = match_full_name(name, all_players)
        unmatched += player_id is None
        entries.append((row.game_date, team_id, row.player, player_id, row.status, row.reason or None))

    with conn.transaction():
        report_id = conn.execute(
            "INSERT INTO nba.injury_reports (report_at, url, entries, fetched_at) VALUES (%s, %s, %s, now()) RETURNING id",
            (report_at, url, len(entries)),
        ).fetchone()["id"]
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO nba.injury_report_teams (report_id, game_date, team_id, submitted) VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                [(report_id, d, teams[_team_key(t)], s) for d, t, s in parsed.teams if _team_key(t) in teams],
            )
            cur.executemany(
                """
                INSERT INTO nba.injury_entries (report_id, game_date, team_id, player_name, player_id, status, reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
                """,
                [(report_id, *e) for e in entries],
            )
    log.info("lesiones: reporte %s, %d jugadores (%d sin emparejar)", report_at.strftime("%Y-%m-%d %H:%M ET"), len(entries), unmatched)
    return {"entries": len(entries), "new": 1, "unmatched": unmatched}
