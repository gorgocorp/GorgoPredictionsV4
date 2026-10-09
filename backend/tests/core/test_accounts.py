"""Contraseñas y planes (sin base de datos)."""

from datetime import date, datetime

import pytest

from app.config import LOCAL_TZ
from app.core import accounts
from app.core.accounts import (
    AccountError,
    check_password,
    check_plan,
    check_username,
    has_full_access,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_password_hash_round_trip_with_own_salt():
    stored = hash_password("bolas de prueba")
    assert stored.startswith("scrypt$") and "bolas" not in stored
    assert verify_password("bolas de prueba", stored)
    assert not verify_password("bolas de Prueba", stored)
    assert hash_password("bolas de prueba") != stored  # sal distinta en cada hash


def test_malformed_hashes_never_verify():
    for stored in ("", "scrypt$1$2", "bcrypt$x$y$z$a$b", "scrypt$16384$8$1$no-es-base64$%%%"):
        assert not verify_password("x", stored)


def test_stronger_parameters_mark_old_hashes_for_rehash(monkeypatch):
    stored = hash_password("contraseña")
    assert not needs_rehash(stored)
    monkeypatch.setattr(accounts, "SCRYPT_N", accounts.SCRYPT_N * 2)
    assert needs_rehash(stored)
    assert verify_password("contraseña", stored)  # el hash viejo sigue sirviendo con sus propios parámetros


@pytest.mark.parametrize("username", ["GorgoAdmin", "ana.lopez", "jugador_23", "a-b"])
def test_valid_usernames(username):
    assert check_username(f"  {username} ") == username


@pytest.mark.parametrize("username", ["ab", "con espacio", "peña", "x" * 33, "correo@dominio.com"])
def test_invalid_usernames(username):
    with pytest.raises(AccountError):
        check_username(username)


def test_password_length_rules():
    assert check_password("ocho1234") == "ocho1234"
    with pytest.raises(AccountError, match="al menos 8"):
        check_password("bolas")
    assert check_password("bolas", min_length=1) == "bolas"  # la línea de comandos sólo avisa
    with pytest.raises(AccountError):
        check_password("x" * 129)


def test_only_a_subscription_has_an_end_date():
    check_plan("subscriber", date(2026, 11, 8))
    check_plan("free", None)
    with pytest.raises(AccountError):
        check_plan("free", date(2026, 11, 8))
    with pytest.raises(AccountError):
        check_plan("vip", None)


def test_subscription_lasts_through_its_last_local_day():
    last_day = date(2026, 11, 8)
    # A las 23:59 del último día en hora local sigue vigente, aunque en UTC ya sea otro día.
    assert has_full_access("subscriber", last_day, datetime(2026, 11, 8, 23, 59, tzinfo=LOCAL_TZ))
    assert not has_full_access("subscriber", last_day, datetime(2026, 11, 9, 0, 0, tzinfo=LOCAL_TZ))
    assert has_full_access("subscriber", None, datetime(2030, 1, 1, tzinfo=LOCAL_TZ))
    assert has_full_access("admin", None, datetime(2030, 1, 1, tzinfo=LOCAL_TZ))
    assert not has_full_access("free", None, datetime(2026, 1, 1, tzinfo=LOCAL_TZ))
