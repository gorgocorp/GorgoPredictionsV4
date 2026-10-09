-- Cuentas, sesiones y dueño de cada apuesta.
--
-- Roles:
--   admin       ve todo; además recalcula picks, marca bajas y administra las cuentas.
--   subscriber  ve todo hasta el último día de su suscripción, en hora local (subscription_until NULL = sin vencimiento).
--   free        ve los parlays gratis de cada día y lo que ya empezó; lo demás le llega bloqueado desde la API
--               (app/core/access.py). Un suscriptor vencido ve lo mismo que free.
--
-- Las contraseñas se guardan como hash scrypt y las sesiones como el SHA-256 del token de la cookie
-- (app/core/accounts.py): una copia de la base no sirve para entrar.

CREATE TABLE core.users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username TEXT NOT NULL CHECK (username ~ '^[A-Za-z0-9._-]{3,32}$'),
    password_hash TEXT CHECK (password_hash LIKE 'scrypt$%'),   -- NULL: no puede entrar hasta tener contraseña
    role TEXT NOT NULL DEFAULT 'free' CHECK (role IN ('admin', 'subscriber', 'free')),
    subscription_until DATE,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ,
    CONSTRAINT users_until_only_subscribers CHECK (subscription_until IS NULL OR role = 'subscriber')
);

-- "GorgoAdmin" y "gorgoadmin" son la misma cuenta.
CREATE UNIQUE INDEX users_username_unique ON core.users (lower(username));

CREATE TABLE core.sessions (
    token_hash BYTEA PRIMARY KEY CHECK (length(token_hash) = 32),
    user_id BIGINT NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT sessions_expire_after_creation CHECK (expires_at > created_at)
);

CREATE INDEX sessions_user_idx ON core.sessions (user_id);

-- Dueño de la plataforma. Su contraseña no va en el repositorio: se pone con
-- `python -m app.cli set-password GorgoAdmin`.
INSERT INTO core.users (username, role) VALUES ('GorgoAdmin', 'admin');

-- Cada apuesta es de un usuario. Las registradas antes de que hubiera cuentas (pruebas) son del dueño.
-- Una cuenta con apuestas no se borra: se desactiva.
ALTER TABLE core.user_bets ADD COLUMN user_id BIGINT REFERENCES core.users (id);
UPDATE core.user_bets SET user_id = (SELECT id FROM core.users WHERE username = 'GorgoAdmin');
ALTER TABLE core.user_bets ALTER COLUMN user_id SET NOT NULL;

CREATE INDEX user_bets_user_idx ON core.user_bets (user_id, created_at DESC);
