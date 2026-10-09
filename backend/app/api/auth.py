"""Entrar, salir, quién soy y cambiar la contraseña (/api/auth).

También define las dependencias con las que las demás rutas piden sesión (`current_viewer`), plan completo
(`full_viewer`) o administrador (`admin_viewer`). La sesión viaja en una cookie httpOnly con SameSite=Lax: otra
página no puede leerla ni mandarla en un POST, y la interfaz y la API son el mismo sitio.
"""

import threading
import time
from collections import deque
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.config import COOKIE_SECURE, LOCAL_TZ
from app.core.accounts import (
    SESSION_DAYS,
    AccountError,
    Viewer,
    authenticate,
    create_session,
    delete_session,
    session_viewer,
    set_password,
)
from app.db import connect

COOKIE = "gorgo_session"

router = APIRouter(prefix="/api/auth", tags=["Cuentas"])


def _now() -> datetime:
    return datetime.now(LOCAL_TZ)


def current_viewer(request: Request) -> Viewer:
    token = request.cookies.get(COOKIE)
    if token:
        with connect() as conn:
            viewer = session_viewer(conn, token, _now())
        if viewer:
            return viewer
    raise HTTPException(status_code=401, detail="Inicia sesión para continuar.")


def full_viewer(viewer: Viewer = Depends(current_viewer)) -> Viewer:
    if not viewer.full:
        raise HTTPException(status_code=403, detail="Disponible con suscripción.")
    return viewer


def admin_viewer(viewer: Viewer = Depends(current_viewer)) -> Viewer:
    if not viewer.is_admin:
        raise HTTPException(status_code=403, detail="Sólo el administrador puede hacer esto.")
    return viewer


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE, token, max_age=SESSION_DAYS * 86_400, httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/"
    )


# Intentos fallidos por usuario (en memoria: un solo proceso web). Tras MAX_FAILURES en WINDOW segundos se espera
# a que el más viejo salga de la ventana.
MAX_FAILURES = 5
WINDOW = 15 * 60
_failures: dict[str, deque[float]] = {}
_failures_lock = threading.Lock()


def _blocked(key: str) -> bool:
    with _failures_lock:
        attempts = _failures.get(key)
        if attempts is None:
            return False
        cutoff = time.monotonic() - WINDOW
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        if not attempts:
            del _failures[key]
            return False
        return len(attempts) >= MAX_FAILURES


def _record_failure(key: str) -> None:
    with _failures_lock:
        _failures.setdefault(key, deque()).append(time.monotonic())


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginIn, response: Response) -> dict:
    key = body.username.strip().lower()
    if _blocked(key):
        raise HTTPException(status_code=429, detail="Demasiados intentos fallidos. Espera 15 minutos y vuelve a intentar.")
    now = _now()
    with connect() as conn:
        user = authenticate(conn, body.username, body.password)
        if user is None:
            _record_failure(key)
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
        token = create_session(conn, user["id"], now)
        viewer = session_viewer(conn, token, now)
    with _failures_lock:
        _failures.pop(key, None)
    _set_cookie(response, token)
    return viewer.to_json()


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(COOKIE)
    if token:
        with connect() as conn:
            delete_session(conn, token)
    response.delete_cookie(COOKIE, path="/", secure=COOKIE_SECURE, httponly=True, samesite="lax")
    return {"ok": True}


@router.get("/me")
def me(viewer: Viewer = Depends(current_viewer)) -> dict:
    return viewer.to_json()


class PasswordChange(BaseModel):
    current: str
    new: str


@router.post("/password")
def change_password(body: PasswordChange, response: Response, viewer: Viewer = Depends(current_viewer)) -> dict:
    """Cambia la contraseña propia: cierra las demás sesiones y deja abierta la de este navegador."""
    with connect() as conn:
        if authenticate(conn, viewer.username, body.current) is None:
            raise HTTPException(status_code=422, detail="La contraseña actual no es correcta.")
        try:
            set_password(conn, viewer.id, body.new)
        except AccountError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        token = create_session(conn, viewer.id, _now())
    _set_cookie(response, token)
    return {"ok": True}
