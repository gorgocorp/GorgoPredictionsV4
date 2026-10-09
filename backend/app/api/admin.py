"""Administración de cuentas (/api/admin): sólo el administrador crea cuentas y cambia planes."""

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import admin_viewer
from app.config import LOCAL_TZ
from app.core.accounts import AccountError, Viewer, create_user, list_users, set_password, update_user
from app.db import connect

router = APIRouter(prefix="/api/admin", tags=["Administración"], dependencies=[Depends(admin_viewer)])

Role = Literal["admin", "subscriber", "free"]


class NewUser(BaseModel):
    username: str
    password: str
    role: Role = "free"
    subscription_until: date | None = None  # último día con suscripción (hora local); vacío = sin vencimiento


class UserChange(BaseModel):
    role: Role
    subscription_until: date | None = None
    active: bool


class PasswordReset(BaseModel):
    password: str


@router.get("/users")
def users() -> list[dict]:
    with connect() as conn:
        return list_users(conn, datetime.now(LOCAL_TZ))


@router.post("/users", status_code=201)
def new_user(body: NewUser) -> dict:
    with connect() as conn:
        try:
            user_id = create_user(conn, body.username, body.password, body.role, body.subscription_until)
        except AccountError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": user_id}


@router.put("/users/{user_id}")
def change_user(user_id: int, body: UserChange, viewer: Viewer = Depends(admin_viewer)) -> dict:
    if user_id == viewer.id and (body.role != "admin" or not body.active):
        raise HTTPException(status_code=409, detail="No puedes quitarte el rol de administrador ni desactivar tu propia cuenta.")
    with connect() as conn:
        try:
            update_user(conn, user_id, role=body.role, until=body.subscription_until, active=body.active)
        except AccountError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": user_id}


@router.put("/users/{user_id}/password")
def reset_password(user_id: int, body: PasswordReset) -> dict:
    """Pone una contraseña nueva (p. ej. si el usuario la olvidó) y cierra sus sesiones."""
    with connect() as conn:
        try:
            set_password(conn, user_id, body.password)
        except AccountError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": user_id}
