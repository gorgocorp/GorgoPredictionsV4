"""Configuración común leída desde variables de entorno o el archivo .env de la raíz.

Lo propio de cada deporte (ligas, temporada en curso, IDs del proveedor) vive en app/sports/<deporte>/config.py.
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
# No sobrescribe variables ya definidas (en Docker, DATABASE_URL viene de compose).
load_dotenv(ROOT_DIR / ".env")

# Deportes de la plataforma, en el orden en que se muestran.
SPORTS = ("nba", "futbol")

# Zona horaria del usuario: define a qué "día" pertenece cada partido, de cualquier deporte.
LOCAL_TZ = ZoneInfo(os.getenv("LOCAL_TIMEZONE", "America/Mexico_City"))

# Casa de la API con la que el sistema registra y mide sus picks y parlays.
BOOKMAKER = os.getenv("BOOKMAKER", "Bet365").strip()

# Casa de referencia del mercado: cobra poca comisión y acepta a los apostadores profesionales. Su probabilidad
# sin comisión es la del mercado cuando cotiza el mercado completo, y la única contra la que se mide el CLV.
SHARP_BOOKMAKER = "Pinnacle"

# Casas de la API cuyos momios se guardan en cada pierna (la interfaz deja elegir con cuál comparar).
# Nombres como los dan /bookmakers (API-Basketball) y /odds/bookmakers (API-Football).
PRICE_BOOKMAKERS = list(
    dict.fromkeys([BOOKMAKER] + [b.strip() for b in os.getenv("PRICE_BOOKMAKERS", "Bet365,1xBet,Pinnacle").split(",") if b.strip()])
)


# Cookie de sesión sólo por HTTPS. Apagada en local (http://localhost); se prende al publicar el sitio con HTTPS.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "").strip().lower() in ("1", "true", "yes")


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta {name} en el archivo .env")
    return value


def get_api_key() -> str:
    """Llave de api-sports: la misma para API-Basketball y API-Football."""
    return _require("APISPORTS_KEY")


def get_database_url() -> str:
    return _require("DATABASE_URL")
