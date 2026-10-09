import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { BrandMark } from "../components/Header";
import { Spinner } from "../components/States";
import { api, ApiError } from "../lib/api";
import { startSession } from "../lib/session";
import { lastSport } from "../lib/sportContext";

/** Entrar. Se muestra en cualquier ruta sin sesión; al entrar se queda en la página que se pidió. */
export function LoginPage() {
  const client = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const login = useMutation({
    mutationFn: () => api.auth.login(username.trim(), password),
    onSuccess: (viewer) => startSession(client, viewer),
  });
  const error = login.error instanceof ApiError ? login.error.message : login.error ? "No se pudo entrar. Intenta otra vez." : null;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (username.trim() && password) login.mutate();
  };

  return (
    <main className="login-page">
      <form className="card login-card" onSubmit={submit} aria-labelledby="login-title" noValidate>
        <div className="brand">
          <BrandMark sport={lastSport()} />
          <span>Gorgo Predictions</span>
        </div>
        <div>
          <h1 id="login-title">Entrar</h1>
          <p className="muted small" style={{ margin: 0 }}>
            Parlays y picks de NBA y fútbol con las probabilidades del modelo.
          </p>
        </div>
        <label className="field">
          Usuario
          <input
            className="input"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            autoFocus
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label className="field">
          Contraseña
          <span className="password-field">
            <input
              className="input"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              aria-pressed={showPassword}
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? "Ocultar" : "Mostrar"}
            </button>
          </span>
        </label>
        {error && (
          <p className="form-error small" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn btn-primary" disabled={login.isPending || !username.trim() || !password}>
          {login.isPending && <Spinner label="Entrando" />}
          {login.isPending ? "Entrando…" : "Entrar"}
        </button>
        <p className="muted xs" style={{ margin: 0 }}>
          ¿No tienes cuenta? Las cuentas las crea el administrador.
        </p>
      </form>
    </main>
  );
}
