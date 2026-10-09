"""Cuentas, contraseñas y sesiones.

- Contraseñas: scrypt (biblioteca estándar) con sal propia; los parámetros van dentro del hash, así que se pueden
  subir después sin invalidar los anteriores (`needs_rehash` lo detecta al entrar).
- Sesiones: el navegador guarda un token al azar en una cookie; la base guarda sólo su SHA-256.
- Roles y planes: ver migrations/0007_users.sql. Qué ve cada plan lo decide app/core/access.py.
"""

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import psycopg

from app.config import LOCAL_TZ

ROLES = ("admin", "subscriber", "free")
SESSION_DAYS = 30
MIN_PASSWORD = 8  # para las que se ponen desde la interfaz; la línea de comandos sólo avisa
MAX_PASSWORD = 128

# Recomendación de OWASP para scrypt (~0.5 s y 128 MiB por intento).
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**17, 8, 1
_MAXMEM = 2**28

USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")


class AccountError(ValueError):
    """Error de validación con mensaje para el usuario."""


@dataclass(frozen=True)
class Viewer:
    """Quién hace la petición y qué puede ver."""

    id: int
    username: str
    role: str
    subscription_until: date | None
    # Ve todo: admin, o suscriptor con suscripción vigente.
    full: bool

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def plan(self) -> str:
        """Plan efectivo: un suscriptor vencido está en free."""
        return self.role if self.full else "free"

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "plan": self.plan,
            "full": self.full,
            "subscription_until": self.subscription_until,
        }


def has_full_access(role: str, until: date | None, now: datetime) -> bool:
    """Admin, o suscriptor cuyo último día (hora local) no ha pasado."""
    return role == "admin" or (role == "subscriber" and (until is None or until >= now.astimezone(LOCAL_TZ).date()))


# ---------------------------------------------------------------- contraseñas


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=_MAXMEM, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), maxmem=_MAXMEM, dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def needs_rehash(stored: str) -> bool:
    return not stored.startswith(f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$")


# Para que un usuario inexistente tarde lo mismo que uno con contraseña equivocada.
_DUMMY_HASH: str | None = None


def _dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None or needs_rehash(_DUMMY_HASH):
        _DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
    return _DUMMY_HASH


def check_username(username: str) -> str:
    username = username.strip()
    if not USERNAME_RE.match(username):
        raise AccountError("El usuario lleva de 3 a 32 caracteres: letras sin acento, números, punto, guion o guion bajo.")
    return username


def check_password(password: str, min_length: int = MIN_PASSWORD) -> str:
    if len(password) < min_length:
        raise AccountError(f"La contraseña debe tener al menos {min_length} caracteres.")
    if len(password) > MAX_PASSWORD:
        raise AccountError(f"La contraseña puede tener hasta {MAX_PASSWORD} caracteres.")
    return password


def check_plan(role: str, until: date | None) -> None:
    if role not in ROLES:
        raise AccountError(f"Rol desconocido: {role}")
    if until is not None and role != "subscriber":
        raise AccountError("Sólo una suscripción lleva fecha de vencimiento.")


# ---------------------------------------------------------------- cuentas

USER_COLUMNS = "id, username, role, subscription_until, active, created_at, last_login_at"


def find_user(conn: psycopg.Connection, username: str) -> dict | None:
    return conn.execute(
        f"SELECT {USER_COLUMNS}, password_hash FROM core.users WHERE lower(username) = lower(%s)", (username.strip(),)
    ).fetchone()


def create_user(
    conn: psycopg.Connection,
    username: str,
    password: str,
    role: str = "free",
    until: date | None = None,
    min_length: int = MIN_PASSWORD,
) -> int:
    username = check_username(username)
    check_password(password, min_length)
    check_plan(role, until)
    try:
        with conn.transaction():
            return conn.execute(
                """
                INSERT INTO core.users (username, password_hash, role, subscription_until)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                (username, hash_password(password), role, until),
            ).fetchone()["id"]
    except psycopg.errors.UniqueViolation as exc:
        raise AccountError(f"Ya existe el usuario {username}.") from exc


def set_password(conn: psycopg.Connection, user_id: int, password: str, min_length: int = MIN_PASSWORD) -> None:
    """Cambia la contraseña y cierra todas las sesiones de la cuenta."""
    check_password(password, min_length)
    with conn.transaction():
        updated = conn.execute(
            "UPDATE core.users SET password_hash = %s WHERE id = %s", (hash_password(password), user_id)
        ).rowcount
        if not updated:
            raise LookupError("Usuario no encontrado")
        conn.execute("DELETE FROM core.sessions WHERE user_id = %s", (user_id,))


def update_user(
    conn: psycopg.Connection,
    user_id: int,
    *,
    role: str,
    until: date | None,
    active: bool,
) -> None:
    """Cambia plan y estado. Desactivar cierra sus sesiones."""
    check_plan(role, until)
    with conn.transaction():
        updated = conn.execute(
            "UPDATE core.users SET role = %s, subscription_until = %s, active = %s WHERE id = %s",
            (role, until, active, user_id),
        ).rowcount
        if not updated:
            raise LookupError("Usuario no encontrado")
        if not active:
            conn.execute("DELETE FROM core.sessions WHERE user_id = %s", (user_id,))


def list_users(conn: psycopg.Connection, now: datetime) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT {", ".join("u." + c for c in USER_COLUMNS.split(", "))}, u.password_hash IS NOT NULL AS has_password,
               (SELECT count(*) FROM core.user_bets b WHERE b.user_id = u.id) AS bets
        FROM core.users u ORDER BY lower(u.username)
        """
    ).fetchall()
    return [{**r, "full": has_full_access(r["role"], r["subscription_until"], now) and r["active"]} for r in rows]


def authenticate(conn: psycopg.Connection, username: str, password: str) -> dict | None:
    """La cuenta si usuario y contraseña coinciden y está activa; None si no (sin decir qué falló)."""
    user = find_user(conn, username)
    stored = user["password_hash"] if user and user["password_hash"] else None
    ok = verify_password(password, stored or _dummy_hash())
    if not (ok and stored and user["active"]):
        return None
    if needs_rehash(stored):
        with conn.transaction():
            conn.execute("UPDATE core.users SET password_hash = %s WHERE id = %s", (hash_password(password), user["id"]))
    return user


# ---------------------------------------------------------------- sesiones


def _token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def create_session(conn: psycopg.Connection, user_id: int, now: datetime) -> str:
    """Nueva sesión; devuelve el token para la cookie. De paso borra las vencidas de la cuenta."""
    token = secrets.token_urlsafe(32)
    with conn.transaction():
        conn.execute("DELETE FROM core.sessions WHERE user_id = %s AND expires_at <= %s", (user_id, now))
        conn.execute(
            "INSERT INTO core.sessions (token_hash, user_id, created_at, expires_at) VALUES (%s, %s, %s, %s)",
            (_token_hash(token), user_id, now, now + timedelta(days=SESSION_DAYS)),
        )
        conn.execute("UPDATE core.users SET last_login_at = %s WHERE id = %s", (now, user_id))
    return token


def session_viewer(conn: psycopg.Connection, token: str, now: datetime) -> Viewer | None:
    row = conn.execute(
        """
        SELECT u.id, u.username, u.role, u.subscription_until
        FROM core.sessions s JOIN core.users u ON u.id = s.user_id
        WHERE s.token_hash = %s AND s.expires_at > %s AND u.active
        """,
        (_token_hash(token), now),
    ).fetchone()
    if row is None:
        return None
    return Viewer(
        id=row["id"],
        username=row["username"],
        role=row["role"],
        subscription_until=row["subscription_until"],
        full=has_full_access(row["role"], row["subscription_until"], now),
    )


def delete_session(conn: psycopg.Connection, token: str) -> None:
    with conn.transaction():
        conn.execute("DELETE FROM core.sessions WHERE token_hash = %s", (_token_hash(token),))
