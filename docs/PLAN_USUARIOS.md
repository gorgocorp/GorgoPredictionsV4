# Cuentas y planes (free · suscriptor · admin)

Decidido el 8-oct-2026. Toda la plataforma pide sesión; sólo el administrador crea cuentas. Lo que ve cada plan lo
decide la **API**: a una cuenta free no le llegan los datos que no incluye su plan, así que no se pueden ver con las
herramientas del navegador. Lo que la interfaz muestra difuminado es relleno genérico.

## Qué ve cada plan

| | Free | Suscriptor (vigente) | Admin |
|---|---|---|---|
| Partidos, horarios, marcadores, bajas | ✅ | ✅ | ✅ |
| Parlays gratis del día (máx. probabilidad de 2 y 3 piernas, configuración estándar) | ✅ | ✅ | ✅ |
| Proyecciones del modelo de partidos sin empezar | 🔒 | ✅ | ✅ |
| Todas las piernas, parlays de 2 a 8, máximo valor, "Personalizar" | 🔒 | ✅ | ✅ |
| Jornada / varios días (fútbol) | 🔒 | ✅ | ✅ |
| Historial | ✅ (piernas de partidos sin empezar fuera de los gratis: 🔒) | ✅ | ✅ |
| Descargar CSV del historial | 🔒 | ✅ | ✅ |
| Rendimiento y CLV | ✅ | ✅ | ✅ |
| Mis apuestas (cada quien las suyas) | ✅ sólo con piernas que ve | ✅ | ✅ |
| Recalcular, marcar bajas | — | — | ✅ |
| Usuarios (crear, plan, vencimiento, contraseña, desactivar) | — | — | ✅ |

- Regla única (`app/core/access.py`): una cuenta free ve una pierna si su partido ya empezó (ya no se puede apostar:
  es evidencia) o si está en un parlay gratis. Los parlays gratis son los mismos que registra y mide el historial.
- Un suscriptor ve todo hasta el último día de su suscripción, en hora local (`subscription_until`, incluido); sin
  fecha no vence. Al vencer ve lo mismo que free, sin cambiar su rol.
- Recalcular y marcar bajas cambian los picks que todos ven y que mide el historial: sólo el admin.

## Cómo está hecho

- Migración `0007_users.sql`: `core.users` (usuario único sin importar mayúsculas, hash scrypt, rol, vencimiento,
  activa), `core.sessions` (sólo el SHA-256 del token) y `core.user_bets.user_id` (obligatorio). Crea **GorgoAdmin**
  sin contraseña y le asigna las apuestas que ya existían (las de prueba).
- Contraseñas: scrypt de la biblioteca estándar con parámetros de OWASP; nunca en el repositorio ni en la migración.
  La interfaz pide al menos 8 caracteres; la línea de comandos acepta menos pero avisa.
- Sesión: cookie `gorgo_session` httpOnly, `SameSite=Lax`, 30 días; `COOKIE_SECURE=1` al publicar con HTTPS.
  Cambiar o reponer la contraseña y desactivar la cuenta cierran sus sesiones.
- Entrar: mismo mensaje si el usuario no existe o la contraseña está mal; 5 intentos fallidos por usuario en 15
  minutos bloquean ese usuario 15 minutos (en memoria del proceso web).
- `import-legacy` asigna las apuestas importadas al primer admin, y `--replace` no borra cuentas ni sesiones.

## Comandos

```bash
../.venv/Scripts/python -m app.cli set-password GorgoAdmin         # la pide sin mostrarla
../.venv/Scripts/python -m app.cli users
../.venv/Scripts/python -m app.cli create-user ana --role subscriber --until 2026-11-08
../.venv/Scripts/python -m app.cli set-plan ana subscriber --until 2026-12-08
../.venv/Scripts/python -m app.cli set-plan ana free --disable
```

En Docker: `docker compose run --rm app set-password GorgoAdmin`. Lo mismo se hace desde la página **Usuarios**.

## Pendiente (cuando se abra a otros)

1. Publicar con HTTPS (`COOKIE_SECURE=1`) y cambiar la contraseña de GorgoAdmin por una larga.
2. Vistas por usuario: guardar en el servidor las preferencias de "Personalizar" (hoy viven en cada navegador) y
   permitir varias con nombre.
3. Registro abierto, correo para recuperar la contraseña y aviso de privacidad.
4. Pagos: que la suscripción se active y extienda sola (hoy la pone el admin con fecha de vencimiento).
5. Límite de intentos por IP y en la base (hoy por usuario y en memoria: un solo proceso web).
