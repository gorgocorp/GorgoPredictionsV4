"""Orden y aislamiento de los pasos de la sincronización de fútbol (sin red ni base: todo sustituido)."""

from contextlib import nullcontext
from unittest import mock

import psycopg
import pytest

from app.sports.futbol import ops


def _fail(*_args):
    raise psycopg.errors.ForeignKeyViolation('Key (team_id)=(22722) is not present in table "teams".')


@pytest.fixture
def jobs(monkeypatch):
    calls = []
    monkeypatch.setattr(ops, "connect", lambda: nullcontext(object()))
    monkeypatch.setattr(ops.jobs, "client", lambda: nullcontext(mock.MagicMock(requests_made=0)))
    monkeypatch.setattr(ops.jobs, "ensure_leagues", lambda conn, api: None)
    monkeypatch.setattr(ops.jobs, "current_seasons", lambda conn: {})
    for name in ("ingest_details", "ingest_lineups", "ingest_injuries", "ingest_odds"):
        monkeypatch.setattr(ops.jobs, name, lambda conn, api, *args, name=name: calls.append(name))
    return calls


def test_sync_gets_injuries_and_odds_even_if_details_fail(jobs, monkeypatch):
    monkeypatch.setattr(ops.jobs, "ingest_details", _fail)
    with pytest.raises(RuntimeError, match=r"detalle \(ForeignKeyViolation\)"):
        ops.sync()
    assert jobs == ["ingest_injuries", "ingest_odds"]


def test_pregame_gets_injuries_and_odds_even_if_lineups_fail(jobs, monkeypatch):
    monkeypatch.setattr(ops.jobs, "ingest_lineups", _fail)
    with pytest.raises(RuntimeError, match="alineaciones"):
        ops.pregame_sync(ops.timedelta(minutes=90))
    assert jobs == ["ingest_injuries", "ingest_odds"]


def test_sync_without_failures_does_not_raise(jobs):
    ops.sync()
    assert jobs == ["ingest_details", "ingest_injuries", "ingest_odds"]
