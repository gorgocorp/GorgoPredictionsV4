# Psycopg 3 — Guía de integración de Python con PostgreSQL

> **Uso previsto:** documentación técnica para un proyecto online que recolecta información de fútbol y NBA, conserva históricos y produce predicciones.
>
> **Ruta sugerida en el repositorio:** `docs/database/psycopg.md`.
>
> **Alcance:** guía práctica elaborada para el proyecto; no es una copia completa ni una traducción oficial de la documentación de Psycopg.
>
> **Versión de referencia:** Psycopg 3, importado como `psycopg`. No confundir con `psycopg2`.
>
> **Fecha de elaboración:** 13 de septiembre de 2026. La búsqueda web estaba deshabilitada al elaborar esta guía: los enlaces oficiales se incluyen como referencia, pero no se consultaron en vivo ni se verificó la última versión disponible. El contenido se basa en funcionalidades conocidas hasta diciembre de 2025.
>
> **Estado de los ejemplos:** Se comprobó la sintaxis de los 17 bloques Python y se ejecutaron 27 comprobaciones locales de la función de normalización. No se ejecutaron los ejemplos de conexión ni pruebas SQL: Psycopg y PostgreSQL no estaban disponibles en el entorno de elaboración.

## Índice

1. [Qué hace Psycopg](#1-qué-hace-psycopg)
2. [Instalación y versiones](#2-instalación-y-versiones)
3. [Configuración y credenciales](#3-configuración-y-credenciales)
4. [Conexiones y consultas básicas](#4-conexiones-y-consultas-básicas)
5. [Parámetros e identificadores seguros](#5-parámetros-e-identificadores-seguros)
6. [Resultados y tipos de datos](#6-resultados-y-tipos-de-datos)
7. [Transacciones, rollback y autocommit](#7-transacciones-rollback-y-autocommit)
8. [Modelo mínimo contra duplicados](#8-modelo-mínimo-contra-duplicados)
9. [Ejemplo de validación y guardado por lote](#9-ejemplo-de-validación-y-guardado-por-lote)
10. [Reintentos y errores](#10-reintentos-y-errores)
11. [Pool de conexiones](#11-pool-de-conexiones)
12. [Programación asíncrona](#12-programación-asíncrona)
13. [Lotes grandes, COPY y lectura incremental](#13-lotes-grandes-copy-y-lectura-incremental)
14. [Reglas para fútbol, NBA, cuotas y predicciones](#14-reglas-para-fútbol-nba-cuotas-y-predicciones)
15. [Pruebas y observabilidad](#15-pruebas-y-observabilidad)
16. [Problemas frecuentes](#16-problemas-frecuentes)
17. [Instrucciones para Codex](#17-instrucciones-para-codex)
18. [Mapa de referencias oficiales](#18-mapa-de-referencias-oficiales)

---

## 1. Qué hace Psycopg

**Psycopg es el controlador que permite a Python comunicarse con PostgreSQL.** Abre conexiones, envía consultas SQL, adapta parámetros, recupera resultados y permite controlar transacciones.

```text
API externa
    ↓
Python: descargar, interpretar y validar
    ↓
Psycopg: ejecutar SQL parametrizado
    ↓
PostgreSQL: guardar y hacer cumplir restricciones
    ↓
Python: consultar datos para la aplicación y los modelos
```

Psycopg **no es** la base de datos, un recolector HTTP, un programador de tareas, un ORM, una herramienta de migraciones ni un motor de predicciones. No evita por sí solo registros duplicados ni valida que un resultado deportivo sea correcto.

### Reparto de responsabilidades propuesto

| Componente | Responsabilidad |
|---|---|
| Cliente HTTP | Consumir las APIs, controlar tiempos de espera, paginación y límites del proveedor. |
| Validación en Python | Revisar estructura, identificadores, fechas y coherencia de los datos. |
| Repositorios con Psycopg | Ejecutar consultas explícitas, transacciones y escrituras repetibles. |
| PostgreSQL | Aplicar `PRIMARY KEY`, `UNIQUE`, `NOT NULL`, `CHECK` y llaves foráneas. |
| Programador de tareas | Iniciar jobs y aplicar la política de concurrencia. |
| Migraciones | Versionar y aplicar cambios de esquema. |
| Modelos y evaluación | Calcular predicciones y medir su calidad sin utilizar información futura. |

**Propuesta inicial:** usar Psycopg directamente para los recolectores. Agregar un ORM solamente cuando haya una necesidad concreta; no mantener dos implementaciones distintas de la misma escritura.

Referencia: [documentación de Psycopg 3](https://www.psycopg.org/psycopg3/docs/).

## 2. Instalación y versiones

### Entorno virtual

```bash
python -m venv .venv
```

Activación en Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activación en Linux o macOS:

```bash
source .venv/bin/activate
```

Los ejemplos de esta guía emplean sintaxis de Python 3.10 o posterior. Esto **no establece** la matriz de compatibilidad de todas las versiones de Psycopg: comprobarla para la versión que se instale.

### Instalación sencilla para desarrollo

```bash
python -m pip install "psycopg[binary]>=3,<4"
```

La distribución binaria proporciona componentes precompilados para las plataformas soportadas. Que exista un wheel compatible depende de la combinación de versión de Python, sistema operativo y arquitectura.

Para usar también un pool:

```bash
python -m pip install "psycopg[binary]>=3,<4" "psycopg_pool>=3,<4"
```

El pool se importa desde `psycopg_pool`; no es un servicio PostgreSQL separado. Su paquete y el de Psycopg deben resolverse como dependencias compatibles; no asumir que comparten exactamente la misma numeración.

### Alternativas de instalación

| Instalación | Características |
|---|---|
| `psycopg[binary]` | Usa componentes binarios distribuidos para plataformas compatibles. Es una opción cómoda para desarrollo. |
| `psycopg[c]` | Compila la implementación C localmente; requiere herramientas de compilación, cabeceras y dependencias de PostgreSQL. |
| `psycopg` | Implementación Python que sigue necesitando una biblioteca `libpq` disponible en el sistema. |

En producción, elegir según el entorno de despliegue y la política de actualización de bibliotecas. No cambiar de variante sin probar la imagen o servidor final.

### Verificación local

```bash
python -c "import psycopg; print(psycopg.__version__)"
python -m pip check
```

Después de instalar y probar, registrar las versiones resueltas en el archivo de bloqueo del gestor de dependencias del proyecto. El rango `>=3,<4` es una restricción de versión mayor, **no un bloqueo reproducible**.

Importación de esta guía:

```python
import psycopg
```

No copiar indiscriminadamente ejemplos de `psycopg2`, como `psycopg2.extras.execute_values`: pertenecen a otra API.

Referencia: [instalación](https://www.psycopg.org/psycopg3/docs/basic/install.html).

## 3. Configuración y credenciales

Usar una variable de entorno; nunca escribir contraseñas reales en el código o en este documento.

Ejemplo de `.env.example` para desarrollo local:

```dotenv
DATABASE_URL=postgresql://sports_app:REEMPLAZAR_PASSWORD@localhost:5432/sports_db
```

Este ejemplo **no crea** la base de datos ni el usuario. Ambos deben existir y tener permisos adecuados.

Agregar al `.gitignore`:

```gitignore
.env
.env.*
!.env.example
.venv/
__pycache__/
```

**Python no carga un archivo `.env` automáticamente.** El entorno de ejecución debe exportar las variables, o el proyecto debe incorporar y configurar una herramienta que lo haga.

Definición temporal en PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://sports_app:REEMPLAZAR_PASSWORD@localhost:5432/sports_db"
```

Definición temporal en Linux o macOS:

```bash
export DATABASE_URL='postgresql://sports_app:REEMPLAZAR_PASSWORD@localhost:5432/sports_db'
```

Lectura con validación básica:

```python
import os


def require_database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("Falta configurar DATABASE_URL")
    return value
```

Las contraseñas con caracteres reservados requieren codificación apropiada al construir una URI. Otra opción es pasar los campos de conexión por separado; no concatenar una URI manualmente con datos arbitrarios.

### Seguridad de despliegue

Usar un rol de aplicación con permisos limitados y otro rol para migraciones. No ejecutar recolectores como superusuario. No imprimir la URI, contraseñas ni payloads sensibles en los logs.

Para conexiones remotas, configurar TLS según el proveedor. Cuando corresponda a la infraestructura, `sslmode=verify-full` permite verificar certificado y nombre del servidor, con la CA adecuada. `sslmode=require` por sí solo no debe tratarse como equivalente a esa verificación completa de identidad.

Referencias: [conexiones](https://www.psycopg.org/psycopg3/docs/api/connections.html) y [TLS en libpq, PostgreSQL 16](https://www.postgresql.org/docs/16/libpq-ssl.html).

## 4. Conexiones y consultas básicas

Ejemplo autocontenido, suponiendo una `DATABASE_URL` válida:

```python
import os

import psycopg
from psycopg.rows import dict_row


dsn = os.environ["DATABASE_URL"]

with psycopg.connect(
    dsn,
    connect_timeout=10,
    application_name="sports_healthcheck",
    row_factory=dict_row,
) as conn:
    row = conn.execute("SELECT 1 AS ok").fetchone()
    if row is None or row["ok"] != 1:
        raise RuntimeError("Respuesta inesperada de PostgreSQL")

# Se llega aquí después de salir correctamente del contexto de conexión.
print("Conexión comprobada")
```

`connect_timeout=10` limita la espera para establecer la conexión según las reglas de libpq. No es un límite general para cada consulta ni necesariamente para una secuencia de múltiples hosts.

### Conexión frente a cursor

| Objeto o método | Para qué sirve |
|---|---|
| `psycopg.connect(...)` | Abre una conexión a PostgreSQL. |
| `conn.cursor()` | Crea un cursor para ejecutar consultas y leer resultados. |
| `conn.execute(sql, params)` | Atajo para ejecutar y obtener un cursor. |
| `cursor.execute(...)` | Ejecuta una consulta. |
| `cursor.executemany(...)` | Ejecuta una operación para varios conjuntos de parámetros. |
| `cursor.fetchone()` | Obtiene una fila o `None`. |
| `cursor.fetchmany(n)` | Obtiene el siguiente bloque de hasta `n` filas. |
| `cursor.fetchall()` | Obtiene todas las filas restantes; cuidar el consumo de memoria. |

### Semántica de los contextos

| Contexto | Salida normal | Salida con excepción |
|---|---|---|
| `with psycopg.connect(...) as conn` | Confirma la transacción pendiente y cierra la conexión. | Revierte la transacción pendiente y cierra la conexión. |
| `with conn.cursor() as cur` | Cierra el cursor. | Cierra el cursor; no sustituye el manejo de la transacción. |
| `with conn.transaction()` | Confirma el bloque transaccional o libera su savepoint. | Revierte el bloque correspondiente. |
| `with pool.connection() as conn` | Finaliza la transacción pendiente y devuelve la conexión al pool. | Revierte la transacción pendiente y la devuelve al pool o la descarta si está rota. |

La fila relativa a `connect` asume el modo normal, sin `autocommit=True`. En autocommit no hay una transacción pendiente implícita que confirmar al salir.

**Cerrar un cursor no equivale a guardar los cambios.** Tampoco debe confundirse devolver una conexión al pool con cerrar físicamente todas sus conexiones.

Referencias: [uso básico](https://www.psycopg.org/psycopg3/docs/basic/usage.html), [conexiones](https://www.psycopg.org/psycopg3/docs/api/connections.html) y [cursores](https://www.psycopg.org/psycopg3/docs/api/cursors.html).

## 5. Parámetros e identificadores seguros

Los siguientes fragmentos que usan `conn` suponen una conexión abierta y el esquema del apartado 8.

### Valores: usar parámetros

```python
row = conn.execute(
    """
    SELECT id, provider, external_team_id, name
    FROM teams
    WHERE provider = %s AND external_team_id = %s
    """,
    ("api_football", 123),
).fetchone()
```

Reglas obligatorias:

- Usar `%s` para valores posicionales; no sustituirlo por `%d` para enteros.
- Pasar los valores como segundo argumento, no mediante f-strings, concatenación o interpolación con `%`.
- No escribir comillas alrededor del marcador: usar `name = %s`, no `name = '%s'`.
- Para un solo valor en una tupla, incluir la coma: `(123,)`.

Parámetros con nombre:

```python
row = conn.execute(
    """
    SELECT id, name
    FROM teams
    WHERE provider = %(provider)s
      AND external_team_id = %(team_id)s
    """,
    {"provider": "api_nba", "team_id": 123},
).fetchone()
```

### Nombres de tabla o columna: usar `sql.Identifier`

Los parámetros de valores no sirven para sustituir identificadores SQL ni palabras como `ASC` o `DESC`.

```python
from psycopg import sql


def list_teams(conn, sort_column: str = "name"):
    allowed_columns = {"id", "name", "external_team_id"}
    if sort_column not in allowed_columns:
        raise ValueError("Columna de ordenamiento no permitida")

    query = sql.SQL(
        "SELECT id, name FROM teams ORDER BY {} LIMIT %s"
    ).format(sql.Identifier(sort_column))

    return conn.execute(query, (50,)).fetchall()
```

La lista permitida controla qué puede elegir el usuario; `Identifier` se ocupa de representar correctamente el identificador. Para fragmentos como la dirección de ordenamiento, seleccionar únicamente constantes internas permitidas. `sql.SQL(texto_externo)` **no sanea** texto arbitrario.

### Listas de identificadores como valores

```python
rows = conn.execute(
    """
    SELECT id, name
    FROM teams
    WHERE provider = %s
      AND external_team_id = ANY(%s::bigint[])
    """,
    ("api_football", [101, 102, 103]),
).fetchall()
```

`ANY` con un arreglo tipado evita construir manualmente una lista SQL. Un arreglo vacío no selecciona ningún equipo. No usar `IN %s` esperando que una lista genere automáticamente la sintaxis de `IN (...)`.

Referencias: [parámetros de consultas](https://www.psycopg.org/psycopg3/docs/basic/params.html) y [composición SQL](https://www.psycopg.org/psycopg3/docs/api/sql.html).

## 6. Resultados y tipos de datos

Psycopg devuelve tuplas por defecto. `row_factory=dict_row` devuelve diccionarios indexados por los nombres de las columnas. En consultas con varias tablas, asignar alias únicos para no repetir claves como `id` o `name`.

```sql
SELECT
    m.id AS match_id,
    home.name AS home_name,
    away.name AS away_name
FROM matches AS m
JOIN teams AS home ON home.id = m.home_team_id
JOIN teams AS away ON away.id = m.away_team_id;
```

Esta consulta supone la tabla `matches` opcional del apartado 14.

### Correspondencias comunes

| Python | PostgreSQL habitual | Observación |
|---|---|---|
| `int` | `smallint`, `integer`, `bigint` | Elegir el tamaño del esquema según el rango requerido. |
| `str` | `text`, `varchar` | No usar nombres como sustitutos de IDs estables. |
| `bool` | `boolean` | En validaciones Python, recordar que `bool` es una subclase de `int`. |
| `Decimal` | `numeric` | Útil para importes, líneas y cuotas donde se necesita precisión decimal. |
| `float` | `real`, `double precision` | Adecuado para cálculos aproximados cuando se acepta esa semántica. |
| `datetime` con zona | `timestamptz` | Representa un instante; PostgreSQL no conserva el nombre original de la zona. |
| `datetime` sin zona | `timestamp` | Evitarlo para instantes globales de partidos o recolección. |
| `date` | `date` | Fecha sin hora. |
| `UUID` | `uuid` | Útil para identificadores de jobs o eventos propios. |
| `None` | `NULL` | No confundir ausencia, cero y dato desconocido. |
| `Jsonb(objeto)` | `jsonb` | Adaptador explícito para objetos JSON. |

### JSONB

```python
from psycopg.types.json import Jsonb

payload = {"source": "synthetic_example", "team": {"id": 123}}

row = conn.execute(
    "SELECT %s::jsonb AS payload",
    (Jsonb(payload),),
).fetchone()
```

No pasar un `dict` como valor JSON sin el adaptador correspondiente o una configuración explícita de adaptación.

`jsonb` guarda una representación estructurada, **no una copia byte por byte** de la respuesta HTTP. No preserva espacios, el orden original de las claves ni claves repetidas. Para una auditoría exacta de la respuesta original, almacenar también el cuerpo original como texto/bytes o en almacenamiento de objetos, con su hash y metadatos.

### Fechas y decimales

```python
from datetime import datetime, timezone
from decimal import Decimal

observed_at = datetime.now(timezone.utc)
decimal_odds = Decimal("1.95")
```

Crear `Decimal` desde texto cuando se necesite conservar el decimal esperado. `Decimal(1.95)` parte de un número binario aproximado. Rechazar o normalizar explícitamente `NaN` e infinitos cuando no tengan significado en el modelo de negocio.

Referencias: [adaptación de tipos](https://www.psycopg.org/psycopg3/docs/basic/adapt.html) y [row factories](https://www.psycopg.org/psycopg3/docs/api/rows.html).

## 7. Transacciones, rollback y autocommit

Una transacción permite que un conjunto de escrituras se confirme completo o no se confirme. No valida automáticamente la coherencia deportiva: eso requiere reglas adicionales.

En el modo predeterminado, Psycopg inicia una transacción cuando se ejecuta una operación, incluso un `SELECT`. Dejar una conexión abierta sin finalizarla puede producir sesiones `idle in transaction`.

### Patrón para una unidad de trabajo

```python
import os

import psycopg


def rename_team(provider: str, team_id: int, new_name: str) -> int:
    normalized_name = new_name.strip()
    if not normalized_name:
        raise ValueError("El nombre no puede quedar vacío")

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        result = conn.execute(
            """
            UPDATE teams
            SET name = %s, updated_at = clock_timestamp()
            WHERE provider = %s AND external_team_id = %s
            """,
            (normalized_name, provider, team_id),
        )
        affected = result.rowcount

    # El commit ya ocurrió al salir correctamente del contexto.
    return affected
```

Si ocurre un error SQL, no basta con capturarlo y seguir ejecutando consultas en la misma transacción fallida. Es necesario hacer rollback o dejar que el contexto correspondiente lo haga.

Capturar la excepción **fuera** del contexto que debe revertirse, salvo que se gestione deliberadamente un savepoint. Capturarla dentro y ocultarla puede cambiar qué modificaciones se confirman.

### Autocommit con transacciones explícitas

```python
import os

import psycopg

with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
    # Consulta independiente: no deja una transacción implícita abierta.
    conn.execute("SELECT 1").fetchone()

    # Agrupación explícita: estas instrucciones sí comparten una transacción.
    with conn.transaction():
        conn.execute("SET LOCAL statement_timeout = '15s'")
        conn.execute("SET LOCAL lock_timeout = '3s'")
        conn.execute(
            "UPDATE teams SET updated_at = clock_timestamp() WHERE id = %s",
            (1,),
        )
```

Los tiempos anteriores son valores ilustrativos para pruebas, no una configuración universal. Ajustarlos al tamaño de los lotes y los objetivos de latencia.

Si `conn.transaction()` se abre cuando ya existe una transacción, gestiona un savepoint; salir de él no confirma necesariamente la transacción exterior.

### Límites operativos

No mantener una transacción abierta durante una llamada HTTP, una espera de reintento o un cálculo de predicción largo. Primero descargar y validar; después abrir una transacción breve para guardar.

Una transacción por lote pequeño suele ser un punto de partida sencillo. Si un job tiene muchos lotes, **cada lote confirmado permanece guardado** aunque falle otro posterior. Para obtener publicación atómica de un conjunto completo, diseñar un staging y una fase de publicación específicos; no anunciar que todo el job fue atómico porque cada lote lo fue.

Referencia: [transacciones](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).

## 8. Modelo mínimo contra duplicados

El ejemplo representa **identidades de equipo por servicio**. No es todavía un catálogo canónico que consolide el mismo equipo entre proveedores diferentes.

Clave de negocio propuesta:

```text
(provider, external_team_id)
```

```text
("api_football", 123) ≠ ("api_nba", 123)
```

Se supone que el ID es estable y único dentro de cada servicio. Si la documentación de un proveedor define otra delimitación —por liga, temporada u otro contexto—, incorporar ese contexto a la clave. No adivinarlo.

### Migración inicial de ejemplo

Guardar este SQL en una migración versionada y ejecutarlo una vez mediante el mecanismo de migraciones del proyecto, no en cada petición o cada job.

```sql
CREATE TABLE teams (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    external_team_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    source_fetched_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT teams_provider_check
        CHECK (provider IN ('api_football', 'api_nba')),
    CONSTRAINT teams_external_id_positive
        CHECK (external_team_id > 0),
    CONSTRAINT teams_name_not_blank
        CHECK (length(btrim(name)) > 0),
    CONSTRAINT teams_payload_is_object
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    CONSTRAINT teams_provider_external_unique
        UNIQUE (provider, external_team_id),
    CONSTRAINT teams_provider_internal_unique
        UNIQUE (provider, id)
);
```

El `CHECK` de proveedores es una decisión de este esquema de ejemplo, no una limitación de Psycopg. Agregar otros servicios requerirá una migración o un catálogo de proveedores.

`UNIQUE (provider, id)` parece redundante frente a la llave primaria; aquí se incluye para que las llaves foráneas compuestas de `matches` puedan exigir que ambos equipos pertenezcan al mismo servicio que el partido. Si no se utiliza ese diseño, evaluar eliminar ese índice adicional.

No usar `CREATE TABLE IF NOT EXISTS` como sustituto de las migraciones: que una tabla exista no significa que tenga el esquema esperado.

### Por qué no basta con consultar antes de insertar

```text
Worker A: no encuentra el equipo.
Worker B: no encuentra el equipo.
Worker A: intenta insertarlo.
Worker B: también intenta insertarlo.
```

La defensa final es una restricción única en PostgreSQL. `ON CONFLICT` permite definir qué hacer cuando esa identidad ya existe.

**Identidad no es contenido:** cambiar el nombre no debe crear otro equipo. Tampoco se deben fusionar equipos diferentes sólo porque compartan nombre.

Referencias: [restricciones de PostgreSQL 16](https://www.postgresql.org/docs/16/ddl-constraints.html) e [`INSERT ... ON CONFLICT`](https://www.postgresql.org/docs/16/sql-insert.html).

## 9. Ejemplo de validación y guardado por lote

Este módulo es un ejemplo autocontenido de la **capa de persistencia**. Requiere las dependencias, la variable de entorno y la tabla del apartado anterior. No descarga datos, no implementa endpoints y no crea el esquema automáticamente.

### Contrato de entrada

Un adaptador específico del proveedor debe convertir la respuesta real a esta forma interna:

```json
{
  "external_team_id": 123,
  "name": "Equipo de ejemplo",
  "payload": {"example": true}
}
```

Estos campos internos **no se presentan como el formato real de API-FOOTBALL o API-NBA**. El mapeo debe hacerse con la documentación efectiva de cada servicio.

El ejemplo exige un nombre completo y un payload JSON por equipo. No usarlo directamente para actualizaciones parciales: primero definir qué significa un campo omitido, un `null` explícito o una orden de borrado.

### `team_repository.py`

```python
from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TypedDict

import psycopg
from psycopg.types.json import Jsonb


class NormalizedTeam(TypedDict):
    provider: str
    external_team_id: int
    name: str
    raw_payload: dict[str, Any]
    source_fetched_at: datetime


@dataclass(frozen=True)
class WriteResult:
    requested: int
    affected: int


UPSERT_TEAM_SQL = """
INSERT INTO teams (
    provider,
    external_team_id,
    name,
    raw_payload,
    source_fetched_at
)
VALUES (
    %(provider)s,
    %(external_team_id)s,
    %(name)s,
    %(raw_payload)s,
    %(source_fetched_at)s
)
ON CONFLICT (provider, external_team_id)
DO UPDATE SET
    name = EXCLUDED.name,
    raw_payload = EXCLUDED.raw_payload,
    source_fetched_at = EXCLUDED.source_fetched_at,
    updated_at = clock_timestamp()
WHERE EXCLUDED.source_fetched_at > teams.source_fetched_at
"""


def normalize_teams(
    provider: str,
    records: Iterable[Mapping[str, Any]],
    *,
    source_fetched_at: datetime,
) -> list[NormalizedTeam]:
    """Valida un lote completo antes de abrir una conexión."""
    if provider not in ("api_football", "api_nba"):
        raise ValueError("Proveedor no permitido")

    if not isinstance(source_fetched_at, datetime):
        raise ValueError("source_fetched_at debe ser datetime")
    if (
        source_fetched_at.tzinfo is None
        or source_fetched_at.utcoffset() is None
    ):
        raise ValueError("source_fetched_at debe incluir zona horaria")

    fetched_at_utc = source_fetched_at.astimezone(timezone.utc)
    normalized: dict[int, NormalizedTeam] = {}
    signatures: dict[int, tuple[str, str]] = {}

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"Registro {index}: se esperaba un objeto")

        team_id = record.get("external_team_id")
        # Rechaza bool y valores fuera del rango de BIGINT positivo.
        if type(team_id) is not int or not 0 < team_id <= 2**63 - 1:
            raise ValueError(f"Registro {index}: ID de equipo inválido")

        name = record.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Registro {index}: nombre vacío o inválido")
        name = name.strip()

        payload = record.get("payload")
        if not isinstance(payload, dict):
            raise ValueError(f"Registro {index}: payload debe ser un objeto")

        try:
            # Copia JSON independiente y rechaza NaN, infinito y objetos
            # no serializables. No conserva los bytes originales de HTTP.
            safe_payload = json.loads(json.dumps(payload, allow_nan=False))
            canonical_payload = json.dumps(
                safe_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise ValueError(f"Registro {index}: payload JSON inválido") from exc

        signature = (name, canonical_payload)
        if team_id in normalized:
            if signatures[team_id] != signature:
                raise ValueError(
                    f"Registro {index}: ID repetido con contenido contradictorio"
                )
            continue  # Duplicado idéntico dentro del mismo lote.

        normalized[team_id] = {
            "provider": provider,
            "external_team_id": team_id,
            "name": name,
            "raw_payload": safe_payload,
            "source_fetched_at": fetched_at_utc,
        }
        signatures[team_id] = signature

    # Un orden consistente de escritura puede reducir conflictos de locks.
    return [normalized[team_id] for team_id in sorted(normalized)]


def write_teams_once(
    dsn: str,
    teams: Sequence[NormalizedTeam],
) -> WriteResult:
    """Guarda un lote ya normalizado; sólo devuelve éxito tras el commit."""
    if not dsn.strip():
        raise ValueError("La conexión a PostgreSQL no está configurada")
    if not teams:
        return WriteResult(requested=0, affected=0)

    params = [
        {**team, "raw_payload": Jsonb(team["raw_payload"])}
        for team in teams
    ]

    with psycopg.connect(
        dsn,
        connect_timeout=10,
        application_name="sports_team_sync",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '15s'")
            cur.execute("SET LOCAL lock_timeout = '3s'")
            cur.executemany(UPSERT_TEAM_SQL, params)
            affected = cur.rowcount

    # Si falla el commit al salir del contexto, no se ejecuta este return.
    return WriteResult(requested=len(teams), affected=affected)


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("Falta configurar DATABASE_URL")

    # DATOS FICTICIOS: ejecutar sólo en una base de desarrollo o pruebas.
    records = [
        {
            "external_team_id": 123,
            "name": "Equipo de ejemplo",
            "payload": {"example": True},
        }
    ]

    teams = normalize_teams(
        "api_football",
        records,
        source_fetched_at=datetime.now(timezone.utc),
    )
    result = write_teams_once(dsn, teams)
    print(f"Registros únicos: {result.requested}; afectados: {result.affected}")


if __name__ == "__main__":
    main()
```

Para probarlo, copiar el bloque a `team_repository.py`, aplicar primero la migración en una base de pruebas y ejecutar:

```bash
python team_repository.py
```

### Qué garantiza y qué no

| Aspecto | Comportamiento del ejemplo |
|---|---|
| IDs repetidos entre servicios | Se mantienen separados por `provider`. |
| ID repetido dentro del lote | Si el contenido normalizado coincide, se conserva una entrada; si contradice, se rechaza todo el lote antes de escribir. |
| ID ya guardado | Se aplica un upsert sujeto a la comparación temporal. |
| Registro con marca anterior o igual | No reemplaza la fila existente. |
| Fallo durante el lote | El contexto revierte la transacción; no se confirma una fracción de ese lote. |
| Lectura HTTP | No está implementada aquí. |
| Veracidad del dato del proveedor | No queda garantizada por validarlo o guardarlo. |
| Compatibilidad con PostgreSQL real | Debe probarse en el entorno del proyecto. |

`source_fetched_at` significa **cuándo se obtuvo la respuesta**, no cuándo el proveedor actualizó el dato. Capturarlo al recibir cada respuesta y conservarlo al reintentar su persistencia. Los relojes deben estar sincronizados. Una respuesta recibida después puede contener información vieja por caché: esta regla temporal local no prueba frescura en origen.

Cuando el proveedor ofrezca una revisión, secuencia o fecha de actualización confiable, diseñar la política de reemplazo alrededor de esa evidencia. Si aparecen datos contradictorios con la misma marca, detectarlos y resolverlos explícitamente; la cláusula `WHERE` del ejemplo simplemente no los sobrescribe.

`affected` cuenta las filas afectadas por PostgreSQL; no distingue inserciones de actualizaciones ni equivale al número original recibido desde la API. Las marcas iguales o anteriores pueden producir menos filas afectadas que solicitadas. No inventar contadores de “creados” y “actualizados” a partir de una cifra que no los separa.

**La idempotencia debe definirse por efecto.** Repetir el mismo lote con la misma marca no cambia estas filas; reconsultar y usar una marca nueva puede actualizarlas. Triggers, auditorías y acciones externas pueden tener otros efectos: un upsert no garantiza que todo el sistema se ejecute exactamente una vez.

Un lote vacío es válido para esta función, pero no demuestra que el proveedor haya respondido correctamente. El recolector debe distinguir “sin resultados” de errores, filtros incorrectos o paginación incompleta.

## 10. Reintentos y errores

### Clasificación práctica

| Excepción o señal | Interpretación | Acción propuesta |
|---|---|---|
| `UniqueViolation` | Conflicto con una restricción única. | Revisar identidad y política de `ON CONFLICT`; no repetir a ciegas. |
| `ForeignKeyViolation` | Falta o no coincide una entidad relacionada. | Revisar orden de carga, proveedor y referencias. |
| `NotNullViolation`, `CheckViolation` | El dato viola el contrato de la tabla. | Rechazar o poner en cuarentena con una causa trazable. |
| `SerializationFailure` | Conflicto de serialización. | Reintentar la transacción completa con un límite. |
| `DeadlockDetected` | Interbloqueo entre transacciones. | Reintentar la transacción completa; revisar orden de escrituras. |
| `OperationalError` | Problema operativo, que puede incluir conexión o comunicación. | Inspeccionar contexto y causa; no asumir siempre un fallo temporal. |
| `QueryCanceled` | Consulta cancelada, por ejemplo por tiempo de espera. | Investigar duración, locks, cancelación y tamaño del lote. |
| `PoolTimeout` | No se obtuvo conexión del pool a tiempo. | Revisar saturación, conexiones retenidas y capacidad total. |

Las excepciones SQL específicas se encuentran en `psycopg.errors`; `PoolTimeout` pertenece a `psycopg_pool`.

### Reintento limitado de la transacción completa

El siguiente fragmento supone que se guardó el módulo del apartado 9 como `team_repository.py`:

```python
import random
import time
from collections.abc import Sequence

from psycopg.errors import DeadlockDetected, SerializationFailure

from team_repository import NormalizedTeam, WriteResult, write_teams_once


def write_teams_with_retry(
    dsn: str,
    teams: Sequence[NormalizedTeam],
    *,
    max_attempts: int = 3,
) -> WriteResult:
    if type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("max_attempts debe ser un entero positivo")

    for attempt in range(max_attempts):
        try:
            # Cada intento abre una conexión y una transacción nuevas.
            return write_teams_once(dsn, teams)
        except (SerializationFailure, DeadlockDetected):
            if attempt == max_attempts - 1:
                raise
            delay = min(0.5 * (2**attempt), 4.0)
            time.sleep(delay + random.uniform(0.0, 0.25))

    raise RuntimeError("Estado de reintento inesperado")
```

No volver a descargar datos dentro de esta función. Debe reintentarse la persistencia de un lote ya validado, no mezclar intentos con respuestas externas diferentes.

**Pérdida de conexión durante el commit:** el cliente puede desconocer si PostgreSQL confirmó. No asumir automáticamente “no se guardó” ni “sí se guardó”. Para operaciones con efectos relevantes, usar una clave idempotente de operación, consultar su estado persistido y reconciliar antes de repetir.

Un resultado incierto merece un estado distinto de `success` y `failed`. El job debe conservar suficiente información para resolverlo.

Referencia: [errores de Psycopg](https://www.psycopg.org/psycopg3/docs/api/errors.html).

## 11. Pool de conexiones

Un pool mantiene un conjunto de conexiones disponibles para reutilizarlas. Puede convenir a una aplicación web o un worker persistente. Un script corto y aislado puede usar simplemente `with psycopg.connect(...)`.

```python
import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


pool = ConnectionPool(
    conninfo=os.environ["DATABASE_URL"],
    min_size=1,
    max_size=5,
    timeout=10.0,
    kwargs={
        "connect_timeout": 10,
        "application_name": "sports_backend",
        "row_factory": dict_row,
    },
    open=False,
)

try:
    pool.open()
    pool.wait(timeout=15.0)

    with pool.connection() as conn:
        row = conn.execute("SELECT 1 AS ok").fetchone()
        if row is None or row["ok"] != 1:
            raise RuntimeError("Comprobación de conexión fallida")
finally:
    pool.close()
```

Los tamaños y tiempos de este ejemplo son ilustrativos. `timeout` del pool limita la espera para obtener una conexión; no limita cada consulta SQL.

En una aplicación web, abrir el pool al iniciar el proceso y cerrarlo al terminar. No crear uno por petición. Cada proceso trabajador debe inicializar sus propias conexiones después de crearse; no compartir conexiones heredadas entre procesos.

Presupuesto aproximado de conexiones:

```text
réplicas × procesos por réplica × max_size
+ conexiones de jobs, migraciones y administración
≤ capacidad disponible acordada para PostgreSQL
```

No compartir una misma conexión entre operaciones que necesiten transacciones independientes. Aunque una conexión síncrona pueda usarse desde varios hilos bajo las reglas del controlador, las operaciones comparten sesión y transacción y se serializan; no se convierten en consultas paralelas independientes. Los cursores no deben compartirse libremente entre hilos.

No dejar configuraciones de sesión, tablas temporales o transacciones abiertas que sorprendan al siguiente usuario del pool. Cuando una opción debe vivir sólo durante una transacción, preferir `SET LOCAL`.

Referencia: [pool de conexiones](https://www.psycopg.org/psycopg3/docs/advanced/pool.html).

## 12. Programación asíncrona

Usar la API asíncrona cuando la aplicación ya se ejecute con `asyncio` y necesite esperar operaciones de E/S sin bloquear su bucle de eventos. No es un requisito para recolectar datos ni una garantía de mayor velocidad.

```python
import asyncio
import os

import psycopg
from psycopg.rows import dict_row


async def check_database() -> None:
    async with await psycopg.AsyncConnection.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=10,
        row_factory=dict_row,
    ) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 AS ok")
            row = await cur.fetchone()
            if row is None or row["ok"] != 1:
                raise RuntimeError("Comprobación asíncrona fallida")


if __name__ == "__main__":
    asyncio.run(check_database())
```

El módulo de pooling también ofrece `AsyncConnectionPool`. No ejecutar consultas bloqueantes del controlador síncrono directamente en el bucle asíncrono de un servidor.

Varias tareas que usan una misma conexión no consiguen sesiones SQL independientes: sus operaciones comparten la conexión y su contexto transaccional. Para concurrencia independiente, obtener conexiones distintas dentro de los límites del pool.

La compatibilidad del bucle de eventos, particularmente en Windows, depende de las versiones de Python y Psycopg. Comprobar el apartado de plataforma de la documentación instalada; no copiar automáticamente cambios de política de `asyncio` sin revisar compatibilidad.

Referencia: [operación asíncrona](https://www.psycopg.org/psycopg3/docs/advanced/async.html).

## 13. Lotes grandes, COPY y lectura incremental

### Elegir el mecanismo

| Necesidad | Punto de partida |
|---|---|
| Una lectura o escritura puntual | `execute`. |
| La misma escritura para un lote moderado | `executemany`. |
| Una carga masiva | `COPY` hacia staging, seguida de validación y publicación. |
| Exportar muchos resultados sin cargar todo en el cliente | Cursor de servidor con nombre. |
| Reducir viajes de red en un caso medido | Evaluar pipeline mode y compatibilidad de versiones. |

No existe un tamaño de lote ideal para todos los casos. Medir duración, memoria, locks, límites operativos y recuperación ante errores antes de aumentarlo.

### `COPY` hacia una tabla temporal

Fragmento didáctico que requiere una conexión abierta en modo transaccional. **Sólo demuestra staging temporal; no publica equipos en la tabla definitiva.**

```python
with conn.cursor() as cur:
    cur.execute(
        """
        CREATE TEMP TABLE team_stage_demo (
            provider TEXT,
            external_team_id BIGINT,
            name TEXT
        ) ON COMMIT DROP
        """
    )

    with cur.copy(
        "COPY team_stage_demo (provider, external_team_id, name) FROM STDIN"
    ) as copy:
        copy.write_row(("api_football", 123, "Equipo de ejemplo"))
        copy.write_row(("api_nba", 123, "Otro equipo de ejemplo"))

    # Aquí se validaría staging y se haría INSERT ... SELECT ... ON CONFLICT.
    # Este fragmento no incluye esa publicación.
```

Con `write_row`, Psycopg adapta los valores. No combinar este patrón con opciones de CSV como `FORMAT CSV` esperando el mismo comportamiento; la carga de bloques CSV es otra modalidad de `COPY`.

`COPY` no proporciona directamente una cláusula `ON CONFLICT`. Para un importador real:

```text
Datos validados
→ COPY a staging
→ comprobar claves duplicadas y relaciones
→ INSERT ... SELECT ... ON CONFLICT hacia tablas definitivas
→ confirmar la transacción
```

Antes del `INSERT ... SELECT`, garantizar una sola fila por clave que deba actualizarse. Una misma instrucción `INSERT ... ON CONFLICT DO UPDATE` no debe intentar actualizar repetidamente la misma fila a partir de claves duplicadas en el conjunto de entrada.

### Cursor de servidor

```python
import os

import psycopg
from psycopg.rows import dict_row

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor(name="export_teams", row_factory=dict_row) as cur:
        cur.execute("SELECT id, name FROM teams ORDER BY id")
        for row in cur:
            print(row["id"], row["name"])
```

Un cursor de servidor permite recuperar filas por bloques. Un cursor normal con `fetchmany` no implica por sí solo que el resultado completo no se haya transferido al cliente.

El ejemplo mantiene abierta la transacción durante la iteración. Para exportaciones muy largas, evaluar paginación por clave y los requisitos de consistencia, en lugar de dejar una transacción abierta indefinidamente.

### Pipeline mode

Permite enviar operaciones con menos esperas entre cliente y servidor, cuando las versiones de Psycopg y libpq lo soportan. No significa que una sola conexión ejecute consultas en paralelo, ni sustituye las transacciones, validaciones o la recuperación de errores.

Referencias: [COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html), [tipos de cursor](https://www.psycopg.org/psycopg3/docs/advanced/cursors.html) y [pipeline mode](https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html).

## 14. Reglas para fútbol, NBA, cuotas y predicciones

Este apartado contiene **decisiones propuestas para el proyecto**, no requisitos impuestos por Psycopg ni una descripción verificada de los endpoints de cada API.

### Identidades y relaciones

Mantener IDs internos para relaciones propias y conservar los IDs externos con su servicio de origen. Para un catálogo canónico entre varios proveedores, usar una tabla de correspondencias explícita; no fusionar por coincidencia aproximada del nombre.

Extensión opcional del esquema del apartado 8:

```sql
CREATE TABLE matches (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL,
    external_match_id BIGINT NOT NULL CHECK (external_match_id > 0),
    home_team_id BIGINT NOT NULL,
    away_team_id BIGINT NOT NULL,
    starts_at TIMESTAMPTZ,

    CONSTRAINT matches_provider_external_unique
        UNIQUE (provider, external_match_id),
    CONSTRAINT matches_distinct_teams
        CHECK (home_team_id <> away_team_id),
    CONSTRAINT matches_home_team_fk
        FOREIGN KEY (provider, home_team_id)
        REFERENCES teams (provider, id),
    CONSTRAINT matches_away_team_fk
        FOREIGN KEY (provider, away_team_id)
        REFERENCES teams (provider, id)
);
```

`home_team_id` y `away_team_id` contienen **IDs internos de `teams.id`**, no IDs externos. Resolverlos mediante `(provider, external_team_id)` antes de guardar el partido.

Este esquema supone dos equipos conocidos. Para partidos con participantes por definir, se necesita una política explícita; no fabricar un “equipo desconocido” reutilizado para aparentar integridad. Una sede neutral tampoco elimina necesariamente los roles designados por el proveedor.

### Granularidad de cada registro

| Entidad | Qué debe quedar definido antes de implementar su clave |
|---|---|
| Equipo del proveedor | Servicio y alcance real de su ID externo. |
| Partido | Servicio, ID externo y alcance documentado. |
| Estadística de equipo en partido | Partido, equipo, período y tipo de estadística, según la forma elegida. |
| Cuota actual | Partido, casa, mercado, selección, período, línea y contexto de mercado necesarios para distinguirla. |
| Histórico de cuotas | Identidad de la cuota más la identidad estable de la observación o snapshot. |
| Predicción | Partido, mercado y selección, versión del modelo, corte de datos y ejecución identificable. |

La clave exacta depende del contrato de cada fuente. Por ejemplo, en cuotas una línea `2.5` y una `3.5` no deben fusionarse sólo porque compartan partido y mercado.

### Estado actual frente a histórico

Usar upsert para una fila de **estado actual** es distinto de conservar un **histórico**. No sobrescribir todas las cuotas anteriores si luego se necesita conocer qué información estaba disponible al predecir.

Una identidad de snapshot puede provenir del proveedor o de una unidad de ingesta persistida antes de reintentar. No generar un UUID nuevo en cada intento y llamarlo idempotencia: eso convertiría cada reintento en una observación nueva.

Conservar, cuando corresponda, la fecha del evento, la fecha declarada por la fuente y la fecha de recolección. No son intercambiables.

### Evitar multiplicaciones al consultar

Una restricción única evita filas duplicadas de la misma entidad, pero no evita multiplicaciones producidas por un `JOIN` mal diseñado.

Ejemplo conceptual:

```text
1 partido
× 2 filas de estadísticas de equipo
× 10 filas de cuotas
= 20 combinaciones si se unen sin respetar la granularidad
```

Antes de calcular promedios o alimentar un modelo, establecer qué representa cada fila. Agregar estadísticas y cuotas a la granularidad necesaria antes de combinarlas. No usar `SELECT DISTINCT` como remedio automático: puede esconder la causa sin corregir las métricas.

### Flujo de ingesta propuesto

```text
Crear run_id y registrar el alcance solicitado
→ descargar páginas fuera de una transacción SQL
→ comprobar respuesta, cobertura y paginación
→ normalizar y validar
→ detectar duplicados y conflictos dentro del lote
→ persistir con transacción corta
→ confirmar el commit
→ registrar resultado y métricas reales
→ habilitar datos para cálculo sólo si cumplen el contrato de calidad
```

Para evitar dos ejecuciones simultáneas del mismo trabajo, definir un control del programador o un mecanismo de exclusión en PostgreSQL. Ese mecanismo complementa las restricciones únicas; no las reemplaza.

**No entrenar ni evaluar con información futura.** Una consulta de evaluación debe poder demostrar que las cuotas, resultados y estadísticas utilizadas estaban disponibles antes del corte de cada predicción. Tener una base de datos consistente no garantiza precisión predictiva ni rentabilidad.

## 15. Pruebas y observabilidad

### Pruebas mínimas antes de producción

| Caso | Resultado esperado |
|---|---|
| Importar dos veces el mismo lote y marca | Una identidad por equipo y ningún reemplazo por marca igual. |
| Mismo ID externo en dos servicios | Dos identidades separadas. |
| Mismo ID con nombre diferente y marca posterior | Se actualiza la fila existente; no se crea otro equipo. |
| ID repetido con contenido contradictorio en el lote | El normalizador rechaza antes de escribir. |
| ID inválido, nombre vacío o fecha sin zona | Rechazo explícito. |
| Error SQL después de una escritura del lote | Rollback: ninguna escritura de ese lote queda confirmada. |
| Dos workers sobre la misma identidad | Sin duplicados; resultado acorde a la política temporal. |
| Lote anterior después de uno posterior | No reemplaza el estado más reciente según la regla elegida. |
| Pérdida de conexión durante confirmación | Resultado incierto registrado y reconciliación comprobada. |
| Partido con equipo del servicio incorrecto | Rechazo por llave foránea compuesta. |
| Consulta de entrenamiento con múltiples cuotas | Cantidades y agregaciones correctas; sin multiplicación accidental. |
| Pool saturado | Tiempo de espera finito y error observable, no bloqueo indefinido. |

Las pruebas de restricciones, transacciones, cursores, `COPY` y concurrencia deben ejecutarse contra PostgreSQL real. SQLite o mocks no reproducen suficientemente esa semántica.

Usar una base de pruebas aislada con las mismas migraciones y una versión de PostgreSQL compatible con producción. No ejecutar pruebas destructivas con credenciales del entorno productivo.

### Evidencia que debe conservar cada job

Registrar `run_id`, proveedor, recurso lógico, filtros, páginas esperadas/recibidas, fecha de inicio y fin, registros recibidos, validados, repetidos, rechazados y afectados. Registrar también duración, intentos, estado final, clase de error y SQLSTATE cuando exista.

No llamar `inserted_count` a `rowcount` si no distingue inserciones y actualizaciones. No declarar `success` antes del commit ni porque la función devolvió una estructura vacía sin excepción.

Un fallo después del commit pero antes de actualizar el registro del job también requiere reconciliación: los datos pueden estar guardados aunque el panel del job todavía no lo refleje.

Para errores, usar logs estructurados con IDs y códigos. Las excepciones pueden contener valores de datos; revisar su contenido antes de enviarlas a logs compartidos. No publicar credenciales ni respuestas completas de las APIs por defecto.

### Estado de revisión de esta guía

- **Sintaxis:** 17/17 bloques Python analizados correctamente con el parser de Python 3.13.5; esto no prueba imports ni compatibilidad con todas las versiones.
- **Validación pura:** 27/27 comprobaciones locales aprobadas sobre el normalizador del apartado 9, incluyendo duplicados, conflictos, IDs, JSON, fechas y copia del payload.
- **Integración real:** no ejecutada. No estaban instalados Psycopg ni PostgreSQL. No se han verificado conexiones, SQL, commits, reintentos contra la base, pools, async, COPY ni concurrencia.
- **Fuentes y versiones actuales:** no verificadas en vivo porque la búsqueda web estaba deshabilitada.
- **Producción:** no se ha desplegado ni auditado el repositorio del usuario.

## 16. Problemas frecuentes

| Síntoma | Causa posible | Qué revisar |
|---|---|---|
| `ModuleNotFoundError: psycopg` | Dependencia instalada en otro intérprete o entorno. | Activación del entorno y `python -m pip`. |
| Error relacionado con `libpq` | Instalación local incompleta o combinación incompatible. | Variante de instalación y dependencias del sistema. |
| Cambios que no aparecen | Falta de commit, rollback o conexión a otra base/esquema. | Contextos, destino y errores propagados. |
| `current transaction is aborted` | Se ocultó un error y se siguió usando la transacción. | Rollback o salida del contexto fallido. |
| `idle in transaction` | Se dejó una transacción abierta mientras se esperaba. | Ciclo de vida y operaciones externas dentro de la transacción. |
| Error al adaptar un diccionario | Falta un adaptador JSON adecuado. | `Jsonb` o configuración explícita de adaptación. |
| Equipos duplicados guardados | Falta la clave única correcta o se interpretan mal los IDs. | Claves, datos existentes y política de upsert. |
| Equipo repetido en resultados | `JOIN` con varias relaciones uno-a-muchos. | Granularidad y agregaciones, no sólo restricciones. |
| Se agotaron conexiones | Pools excesivos, fugas o transacciones retenidas. | Presupuesto total por proceso y réplica. |
| Error de sentencia preparada con un proxy | El proxy y el modo de pooling no manejan bien esa configuración. | Compatibilidad de versiones y `prepare_threshold`; no desactivar funciones sin diagnosticar. |
| Una fila vieja reemplaza información nueva | Política temporal insuficiente o marca mal interpretada. | Revisión del proveedor, caché y tiempos de recolección. |

Los parámetros de preparación de consultas y la compatibilidad con proxies deben verificarse contra las versiones realmente desplegadas. No asumir que todos los modos o versiones de un pooler se comportan igual.

## 17. Instrucciones para Codex

### Ubicación propuesta

Esta estructura es una propuesta, no un inventario del repositorio existente:

```text
proyecto/
├── README.md
├── AGENTS.md
├── docs/
│   └── database/
│       └── psycopg.md
├── migrations/
├── src/
│   ├── ingestion/
│   └── repositories/
└── tests/
    └── integration/
```

En `README.md`, agregar un enlace relativo:

```markdown
## Documentación técnica

- [Python y PostgreSQL con Psycopg 3](docs/database/psycopg.md)
```

### Texto de trabajo para el agente

```text
Antes de implementar o modificar persistencia en PostgreSQL, lee
`docs/database/psycopg.md` y revisa el código, las migraciones, las pruebas
y las versiones instaladas del repositorio.

Usa Psycopg 3 (`psycopg`) para los recolectores si no existe ya una decisión
arquitectónica distinta. No mezcles APIs de psycopg2 ni añadas una segunda
capa de persistencia para resolver una operación que ya existe.

Separa descarga HTTP, normalización, validación y persistencia.
Usa parámetros para valores y psycopg.sql.Identifier para identificadores
que realmente necesiten ser dinámicos, con listas de valores permitidos.

Define la identidad y granularidad de cada entidad antes de escribir SQL.
La base debe tener restricciones reales contra duplicados y relaciones
inválidas; comprobar antes de insertar no sustituye una restricción única.

Mantén transacciones cortas y declara éxito sólo después de confirmar.
No reintentes indiscriminadamente errores de datos o commits inciertos.
Diferencia estado actual, históricos y efectos externos.

No inventes campos, IDs, endpoints o cobertura de las APIs deportivas.
Consulta su documentación presente en el repositorio y conserva el origen
de cada dato. No trates los ejemplos ficticios de esta guía como datos reales.

No crees tablas desde cada job ni uses IF NOT EXISTS como migrador.
Respeta el sistema de migraciones y dependencias que ya utiliza el proyecto.

Ejecuta pruebas de integración contra PostgreSQL cuando el entorno lo permita.
Distingue claramente código escrito, prueba con mocks, prueba con PostgreSQL
y comportamiento comprobado en producción. Nunca inventes resultados.

Esta guía es una propuesta técnica. Si contradice una API instalada,
una migración real o una decisión vigente del repositorio, explica la
contradicción y actualiza la documentación con evidencia.
```

### Formato sugerido para reportar una implementación

| Estado | Significado |
|---|---|
| ✅ Correcto | Funciona, está conectado y hay evidencia de la prueba indicada. |
| 🟡 Parcial | Está incompleto o falta verificar una parte relevante. |
| ❌ Incorrecto | No funciona, falta o contradice el contrato esperado. |
| 🎨 Sólo apariencia | Existe como interfaz, documento, mock o demostración sin efecto real conectado. |
| ⚠️ Riesgo | Puede funcionar, pero presenta fragilidad, deuda o una condición no resuelta. |

Para cada cambio, reportar qué debía ocurrir, qué ocurrió realmente, qué archivos se modificaron, qué prueba se ejecutó y qué quedó sin verificar. No calificar como producción algo que sólo se comprobó con dobles de prueba.

## 18. Mapa de referencias oficiales

**Enlaces de referencia, no constancia de consulta en vivo.** Revisar su contenido y la versión instalada antes de adoptar características o ajustes sensibles a versiones.

| Tema | Referencia |
|---|---|
| Inicio de Psycopg 3 | https://www.psycopg.org/psycopg3/docs/ |
| Instalación | https://www.psycopg.org/psycopg3/docs/basic/install.html |
| Uso básico | https://www.psycopg.org/psycopg3/docs/basic/usage.html |
| Parámetros | https://www.psycopg.org/psycopg3/docs/basic/params.html |
| Transacciones | https://www.psycopg.org/psycopg3/docs/basic/transactions.html |
| Adaptación de tipos y JSON | https://www.psycopg.org/psycopg3/docs/basic/adapt.html |
| Conexiones | https://www.psycopg.org/psycopg3/docs/api/connections.html |
| Cursores | https://www.psycopg.org/psycopg3/docs/api/cursors.html |
| Row factories | https://www.psycopg.org/psycopg3/docs/api/rows.html |
| Composición SQL | https://www.psycopg.org/psycopg3/docs/api/sql.html |
| Errores | https://www.psycopg.org/psycopg3/docs/api/errors.html |
| Pool | https://www.psycopg.org/psycopg3/docs/advanced/pool.html |
| Async | https://www.psycopg.org/psycopg3/docs/advanced/async.html |
| COPY | https://www.psycopg.org/psycopg3/docs/basic/copy.html |
| Tipos de cursor | https://www.psycopg.org/psycopg3/docs/advanced/cursors.html |
| Pipeline | https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html |
| Restricciones de PostgreSQL 16 | https://www.postgresql.org/docs/16/ddl-constraints.html |
| INSERT y ON CONFLICT de PostgreSQL 16 | https://www.postgresql.org/docs/16/sql-insert.html |
| TLS de libpq, PostgreSQL 16 | https://www.postgresql.org/docs/16/libpq-ssl.html |

---

**Criterio central:** Python interpreta y valida; Psycopg ejecuta SQL; PostgreSQL protege la integridad. Ninguna de esas capas sustituye la definición correcta de identidad, temporalidad, granularidad y evidencia.
