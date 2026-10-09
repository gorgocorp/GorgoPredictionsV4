"""Línea de comandos de GorgoPredictions V4 (NBA y fútbol).

En Docker:   docker compose run --rm app <comando>
Local:       python -m app.cli <comando>   (desde backend/)

Los comandos de datos aceptan --sport nba|futbol; sin él corren para todos los deportes donde aplica.
"""

import argparse
import getpass
import importlib
import logging
import sys
from datetime import date, datetime

from psycopg import sql

from app.config import BOOKMAKER, LOCAL_TZ, SPORTS
from app.db import connect, migrate

log = logging.getLogger("gorgo")


def _today() -> date:
    return datetime.now(LOCAL_TZ).date()


def _selected(args):
    """Deportes elegidos con --sport (todos si no se indica)."""
    from app.sports import all_sports

    sports = all_sports()
    return [sports[args.sport]] if getattr(args, "sport", None) else list(sports.values())


def _one(args):
    from app.sports import get_sport

    if not args.sport:
        raise SystemExit("Este comando necesita --sport nba o --sport futbol")
    return get_sport(args.sport)


def _ops(key: str):
    return importlib.import_module(f"app.sports.{key}.ops")


def _per_sport(args, action) -> None:
    """Corre `action(sport)` en cada deporte elegido; un fallo no detiene a los demás."""
    failed = []
    for sport in _selected(args):
        try:
            result = action(sport)
            if result:
                print(result)
        except Exception as exc:
            log.exception("%s: falló", sport.label)
            failed.append(f"{sport.label} ({type(exc).__name__}: {exc})")
    if failed:
        print("Falló: " + "; ".join(failed), file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------- base de datos


def cmd_migrate(_args) -> None:
    with connect() as conn:
        applied = migrate(conn)
    print("Migraciones aplicadas:", ", ".join(applied) if applied else "ninguna (al día)")


def cmd_summary(_args) -> None:
    """Filas por tabla de cada esquema."""
    with connect() as conn:
        tables = conn.execute(
            """
            SELECT table_schema, table_name FROM information_schema.tables
            WHERE table_schema IN ('core', 'nba', 'futbol') AND table_type = 'BASE TABLE'
            ORDER BY array_position(ARRAY['core', 'nba', 'futbol'], table_schema::text), table_name
            """
        ).fetchall()
        for t in tables:
            n = conn.execute(
                sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier(t["table_schema"], t["table_name"]))
            ).fetchone()["n"]
            print(f"  {t['table_schema'] + '.' + t['table_name']:<36}{n:>12,}")


def cmd_import_legacy(args) -> None:
    """Importa el historial de GorgoNBAParlays y GorgoPredictionsV3 (sólo los lee)."""
    from app.legacy_import import LegacyImportError, format_report, run_import

    try:
        with connect() as conn:
            reports = run_import(conn, replace=args.replace)
    except LegacyImportError as exc:
        print(f"No se importó nada: {exc}", file=sys.stderr)
        sys.exit(1)
    print(format_report(reports))
    print("Importación completa: todo cuadró con la foto de origen.")


# ---------------------------------------------------------------- cuentas


def _read_password() -> str:
    """Pide la contraseña sin mostrarla; sin consola (p. ej. un pipe), la lee de la entrada estándar."""
    if not sys.stdin.isatty():
        return sys.stdin.readline().rstrip("\r\n")
    first = getpass.getpass("Contraseña: ")
    if getpass.getpass("Repítela: ") != first:
        raise SystemExit("Las contraseñas no coinciden; no se cambió nada.")
    return first


def _warn_weak(password: str) -> None:
    from app.core.accounts import MIN_PASSWORD

    if len(password) < MIN_PASSWORD:
        print(
            f"Aviso: la contraseña tiene {len(password)} caracteres (la interfaz pide al menos {MIN_PASSWORD}). "
            "Cámbiala antes de publicar el sitio en internet.",
            file=sys.stderr,
        )


def _account(conn, username: str) -> dict:
    from app.core.accounts import find_user

    user = find_user(conn, username)
    if user is None:
        raise SystemExit(f"No existe el usuario {username}.")
    return user


def cmd_users(_args) -> None:
    from app.core.accounts import list_users

    with connect() as conn:
        rows = list_users(conn, datetime.now(LOCAL_TZ))
    for u in rows:
        until = f" hasta {u['subscription_until']}" if u["subscription_until"] else ""
        state = "" if u["active"] else " (desactivada)"
        password = "" if u["has_password"] else " (sin contraseña)"
        access = "todo" if u["full"] else "free"
        print(f"  {u['username']:<24}{u['role'] + until:<28}ve: {access:<6}{u['bets']:>4} apuestas{state}{password}")


def cmd_create_user(args) -> None:
    from app.core.accounts import AccountError, create_user

    until = date.fromisoformat(args.until) if args.until else None
    password = _read_password()
    with connect() as conn:
        try:
            create_user(conn, args.username, password, args.role, until, min_length=1)
        except AccountError as exc:
            raise SystemExit(str(exc)) from exc
    _warn_weak(password)
    print(f"Cuenta {args.username} creada ({args.role}).")


def cmd_set_password(args) -> None:
    from app.core.accounts import AccountError, set_password

    password = _read_password()
    with connect() as conn:
        user = _account(conn, args.username)
        try:
            set_password(conn, user["id"], password, min_length=1)
        except AccountError as exc:
            raise SystemExit(str(exc)) from exc
    _warn_weak(password)
    print(f"Contraseña de {user['username']} actualizada; sus sesiones abiertas se cerraron.")


def cmd_set_plan(args) -> None:
    from app.core.accounts import AccountError, update_user

    until = date.fromisoformat(args.until) if args.until else None
    with connect() as conn:
        user = _account(conn, args.username)
        try:
            update_user(conn, user["id"], role=args.role, until=until, active=not args.disable)
        except AccountError as exc:
            raise SystemExit(str(exc)) from exc
    print(f"{user['username']}: {args.role}{f' hasta {until}' if until else ''}{' (desactivada)' if args.disable else ''}.")


# ---------------------------------------------------------------- ingesta


def cmd_status(args) -> None:
    def status(sport):
        ops = _ops(sport.key)
        with ops.jobs.client() as api:
            body = api.get("/status")
        sub, req = body.get("subscription", {}), body.get("requests", {})
        return (
            f"{sport.label}: plan {sub.get('plan')} (activo: {sub.get('active')}, vence {sub.get('end')}); "
            f"{req.get('current')} / {req.get('limit_day')} solicitudes hoy (se renueva 00:00 UTC)"
        )

    _per_sport(args, status)


def cmd_backfill(args) -> None:
    sport = _one(args)
    if sport.key == "nba":
        from app.sports.nba.config import CURRENT_SEASON

        print(_ops("nba").backfill(args.season or CURRENT_SEASON))
    else:
        print(_ops("futbol").backfill(args.seasons, args.league, injuries=not args.no_injuries))


def cmd_sync(args) -> None:
    _per_sport(args, lambda sport: _ops(sport.key).sync())


def cmd_odds(args) -> None:
    _per_sport(args, lambda sport: _ops(sport.key).odds())


def cmd_injuries(args) -> None:
    _per_sport(args, lambda sport: _ops(sport.key).injuries())


def cmd_lineups(args) -> None:
    print(_ops("futbol").lineups(args.minutes))


# ---------------------------------------------------------------- picks y rendimiento


def cmd_picks(args) -> None:
    sport = _one(args)
    report = importlib.import_module(f"app.sports.{sport.key}.engine.report")
    day = date.fromisoformat(args.date) if args.date else _today()
    with connect() as conn:
        hist = sport.load_history(conn)
        cards = sport.generate_day(conn, hist, day, args.bookmaker)
    print(report.format_day(day, args.bookmaker, cards, top=args.top))


def cmd_record(args) -> None:
    from app.core.tracking import record_picks

    sport = _one(args)
    day = date.fromisoformat(args.date) if args.date else _today()
    with connect() as conn:
        counts = record_picks(conn, sport, sport.load_history(conn), day, args.bookmaker)
    print(f"{sport.label} {day}: {counts['games']} partidos sin empezar, {counts['picks']} piernas y {counts['parlays']} parlays guardados")


def cmd_settle(args) -> None:
    from app.core.tracking import settle_all

    with connect() as conn:
        counts = settle_all(conn, _selected(args))
    print(f"Liquidadas: {counts['picks']} piernas, {counts['parlays']} parlays, {counts['bets']} apuestas tuyas")


def cmd_performance(args) -> None:
    from app.core.tracking import performance_report

    sport = _one(args)
    filters = {"include_preseason": args.include_preseason} if sport.key == "nba" else {"league": args.league}
    with connect() as conn:
        print(performance_report(conn, sport, **filters))


BACKTEST_RANGES = {"nba": ("2025-10-21", "2026-06-14"), "futbol": ("2025-08-15", "2026-06-01")}


def cmd_backtest(args) -> None:
    sport = _one(args)
    backtest = importlib.import_module(f"app.sports.{sport.key}.engine.backtest")
    start, end = (date.fromisoformat(d) for d in (args.start or BACKTEST_RANGES[sport.key][0], args.end or BACKTEST_RANGES[sport.key][1]))
    with connect() as conn:
        hist = sport.load_history(conn)
    options = {"players": not args.teams_only, "every": args.every}
    if sport.key == "futbol":
        options["leagues"] = set(args.league) if args.league else None
    print(backtest.format_report(backtest.run_backtest(hist, start, end, **options)))


def cmd_parity(args) -> None:
    """Compara el motor de V4 con el del proyecto anterior para los mismos días y datos."""
    from app.parity import format_result, run_parity

    sport = _one(args)
    days = [date.fromisoformat(d) for d in args.date] if args.date else [_today()]
    results = [run_parity(sport.key, day, args.bookmaker) for day in days]
    for r in results:
        print(format_result(r))
    if not all(r.ok for r in results):
        sys.exit(1)


def cmd_scheduler(args) -> None:
    from app.scheduler import run_forever

    run_forever({sport.key: sport for sport in _selected(args)})


# ---------------------------------------------------------------- argumentos


def main() -> None:
    # En una consola de Windows con página de códigos ANSI, un carácter que no exista en ella se cambia
    # por "?" en lugar de tumbar el comando después de hacer el trabajo.
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog="gorgo", description="GorgoPredictions V4 (NBA y fútbol)")
    sub = parser.add_subparsers(dest="command", required=True)

    def with_sport(p, help_text="Sólo este deporte (por defecto, todos)"):
        p.add_argument("--sport", choices=SPORTS, help=help_text)
        return p

    sub.add_parser("migrate", help="Aplica migraciones pendientes").set_defaults(func=cmd_migrate)
    sub.add_parser("summary", help="Filas por tabla").set_defaults(func=cmd_summary)
    p = sub.add_parser("import-legacy", help="Importa el historial de los proyectos anteriores (sólo los lee)")
    p.add_argument("--replace", action="store_true", help="Borra lo que ya tenga V4 y vuelve a importar")
    p.set_defaults(func=cmd_import_legacy)

    roles = ("admin", "subscriber", "free")
    sub.add_parser("users", help="Cuentas, su plan y cuántas apuestas tienen").set_defaults(func=cmd_users)
    p = sub.add_parser("create-user", help="Crea una cuenta (pide la contraseña)")
    p.add_argument("username")
    p.add_argument("--role", choices=roles, default="free")
    p.add_argument("--until", help="Suscripción: último día con acceso, YYYY-MM-DD (por defecto, sin vencimiento)")
    p.set_defaults(func=cmd_create_user)
    p = sub.add_parser("set-password", help="Pone la contraseña de una cuenta (la pide) y cierra sus sesiones")
    p.add_argument("username")
    p.set_defaults(func=cmd_set_password)
    p = sub.add_parser("set-plan", help="Cambia el rol o la suscripción de una cuenta")
    p.add_argument("username")
    p.add_argument("role", choices=roles)
    p.add_argument("--until", help="Suscripción: último día con acceso, YYYY-MM-DD (por defecto, sin vencimiento)")
    p.add_argument("--disable", action="store_true", help="Desactiva la cuenta (no puede entrar; conserva sus apuestas)")
    p.set_defaults(func=cmd_set_plan)

    with_sport(sub.add_parser("status", help="Plan y consumo de cada API (no gasta cuota)")).set_defaults(func=cmd_status)
    with_sport(sub.add_parser("sync", help="Temporada en curso: partidos, estadísticas, bajas y momios")).set_defaults(func=cmd_sync)
    with_sport(sub.add_parser("odds", help="Momios de los próximos 7 días")).set_defaults(func=cmd_odds)
    with_sport(sub.add_parser("injuries", help="Bajas (NBA: reporte oficial; fútbol: API de los próximos 3 días)")).set_defaults(func=cmd_injuries)

    p = sub.add_parser("lineups", help="Fútbol: alineaciones de los partidos que empiezan pronto")
    p.add_argument("--minutes", type=int, default=90, help="Ventana en minutos (por defecto 90)")
    p.set_defaults(func=cmd_lineups)

    p = with_sport(sub.add_parser("backfill", help="Carga temporadas completas"), "Deporte (obligatorio)")
    p.add_argument("--season", help="NBA: temporada YYYY-YYYY (por defecto, la en curso)")
    p.add_argument("--seasons", type=int, nargs="+", default=[2024, 2025, 2026], help="Fútbol: años de temporada (2025 = 2025-26)")
    p.add_argument("--league", type=int, action="append", help="Fútbol: sólo esta competición (se puede repetir)")
    p.add_argument("--no-injuries", action="store_true", help="Fútbol: no descargar las bajas de cada temporada")
    p.set_defaults(func=cmd_backfill)

    p = with_sport(sub.add_parser("picks", help="Piernas y parlays de 2 a 8 piernas para un día (texto)"), "Deporte (obligatorio)")
    p.add_argument("--date", help="YYYY-MM-DD (hora local). Por defecto, hoy")
    p.add_argument("--bookmaker", default=BOOKMAKER, help="Casa para los precios (Bet365, 1xBet…), o 'best'")
    p.add_argument("--top", type=int, default=25, help="Piernas a listar por sección")
    p.set_defaults(func=cmd_picks)

    p = with_sport(sub.add_parser("record-picks", help="Guarda piernas y parlays de un día (partidos sin empezar)"), "Deporte (obligatorio)")
    p.add_argument("--date", help="YYYY-MM-DD (hora local). Por defecto, hoy")
    p.add_argument("--bookmaker", default=BOOKMAKER)
    p.set_defaults(func=cmd_record)

    with_sport(sub.add_parser("settle", help="Liquida piernas, parlays y tus apuestas de partidos terminados")).set_defaults(func=cmd_settle)

    p = with_sport(sub.add_parser("performance", help="Rendimiento real de los picks registrados"), "Deporte (obligatorio)")
    p.add_argument("--include-preseason", action="store_true", help="NBA: incluir la pretemporada")
    p.add_argument("--league", type=int, help="Fútbol: sólo esta competición")
    p.set_defaults(func=cmd_performance)

    p = with_sport(sub.add_parser("backtest", help="Evalúa los modelos día por día sobre un rango de fechas"), "Deporte (obligatorio)")
    p.add_argument("--start", help="YYYY-MM-DD (por defecto, el rango del README de cada deporte)")
    p.add_argument("--end", help="YYYY-MM-DD")
    p.add_argument("--teams-only", action="store_true", help="Sólo mercados de equipo (rápido)")
    p.add_argument("--every", type=int, default=1, help="Evalúa uno de cada N días")
    p.add_argument("--league", type=int, action="append", help="Fútbol: sólo esta competición (se puede repetir)")
    p.set_defaults(func=cmd_backtest)

    p = with_sport(sub.add_parser("parity", help="Compara V4 con el proyecto anterior (mismas piernas y probabilidades)"), "Deporte (obligatorio)")
    p.add_argument("--date", action="append", help="YYYY-MM-DD (se puede repetir). Por defecto, hoy")
    p.add_argument("--bookmaker", default=BOOKMAKER)
    p.set_defaults(func=cmd_parity)

    with_sport(sub.add_parser("scheduler", help="Corre sync, liquidación y registro de picks periódicamente")).set_defaults(func=cmd_scheduler)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
