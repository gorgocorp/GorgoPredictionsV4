"""Cliente HTTP mínimo para las APIs de api-sports (API-Basketball v1 y API-Football v3).

La misma llave sirve para las dos; cada API tiene su propia cuota y sus propios encabezados de límite,
así que se usa una instancia por API.
"""

import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_api_key


class ApiSportsError(Exception):
    pass


@dataclass
class RateLimit:
    day_limit: int | None = None
    day_remaining: int | None = None
    minute_limit: int | None = None
    minute_remaining: int | None = None


def _int_header(headers: httpx.Headers, name: str) -> int | None:
    value = headers.get(name)
    return int(value) if value and value.isdigit() else None


class ApiSportsClient:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 30.0):
        self._http = httpx.Client(
            base_url=base_url,
            headers={"x-apisports-key": api_key or get_api_key()},
            timeout=timeout,
        )
        self.rate_limit = RateLimit()
        self.requests_made = 0

    def get_page(self, path: str, **params: Any) -> dict:
        """Hace GET y devuelve el cuerpo completo (con `paging`).

        API-SPORTS responde 200 incluso con errores; vienen en el campo `errors`
        (lista vacía o diccionario {campo: mensaje}).
        """
        if self.rate_limit.minute_remaining == 0:
            time.sleep(60)
        if self.rate_limit.day_remaining == 0:
            raise ApiSportsError("Se agotó la cuota diaria de la API (se renueva a las 00:00 UTC)")

        self.requests_made += 1
        resp = self._http.get(path, params={k: v for k, v in params.items() if v is not None})
        self._update_rate_limit(resp.headers)
        resp.raise_for_status()

        body = resp.json()
        errors = body.get("errors")
        if errors:
            raise ApiSportsError(f"{path} {params}: {errors}")
        return body

    def get(self, path: str, **params: Any) -> list | dict:
        return self.get_page(path, **params)["response"]

    def get_all(self, path: str, **params: Any) -> list:
        """Recorre todas las páginas de un endpoint paginado (p. ej. /odds de API-Football, 10 por página)."""
        out: list = []
        page = 1
        while True:
            body = self.get_page(path, page=page, **params)
            out.extend(body["response"])
            paging = body.get("paging") or {}
            if page >= int(paging.get("total") or 1):
                return out
            page += 1

    def _update_rate_limit(self, headers: httpx.Headers) -> None:
        self.rate_limit = RateLimit(
            day_limit=_int_header(headers, "x-ratelimit-requests-limit"),
            day_remaining=_int_header(headers, "x-ratelimit-requests-remaining"),
            minute_limit=_int_header(headers, "X-RateLimit-Limit"),
            minute_remaining=_int_header(headers, "X-RateLimit-Remaining"),
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
