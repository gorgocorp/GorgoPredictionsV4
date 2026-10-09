import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { SUBSCRIBE_HINT } from "../components/Locked";
import { Spinner } from "../components/States";
import { useToast } from "../components/Toast";
import { api, ApiError } from "../lib/api";
import { longDate } from "../lib/format";
import { PLAN_LABELS, useViewer } from "../lib/session";

const MIN_PASSWORD = 8; // igual que app/core/accounts.py

function PlanSummary() {
  const viewer = useViewer();
  const expired = viewer.role === "subscriber" && !viewer.full;
  return (
    <section className="card card-pad account-plan" aria-labelledby="plan-title">
      <h2 id="plan-title">Tu plan</h2>
      <p style={{ margin: 0 }}>
        <span className={`badge ${viewer.full ? "badge-won" : "badge-neutral"}`}>{PLAN_LABELS[viewer.plan]}</span>{" "}
        {viewer.role === "admin"
          ? "Ves todo y administras las cuentas."
          : viewer.full
            ? viewer.subscription_until
              ? `Suscripción vigente hasta el ${longDate(viewer.subscription_until).toLowerCase()}.`
              : "Suscripción sin vencimiento."
            : expired && viewer.subscription_until
              ? `Tu suscripción terminó el ${longDate(viewer.subscription_until).toLowerCase()}.`
              : "Ves los parlays gratis de cada día, el historial y el rendimiento."}
      </p>
      {!viewer.full && (
        <p className="muted small" style={{ margin: 0 }}>
          Con suscripción ves todos los parlays, todas las piernas con sus momios, las proyecciones del modelo y armas los
          tuyos con tu configuración. {SUBSCRIBE_HINT}
        </p>
      )}
    </section>
  );
}

function PasswordForm() {
  const notify = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const change = useMutation({
    mutationFn: () => api.auth.changePassword(current, next),
    onSuccess: () => {
      setCurrent("");
      setNext("");
      setRepeat("");
      notify("Contraseña cambiada. Se cerraron tus sesiones en otros dispositivos.");
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "No se pudo cambiar la contraseña"),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (next.length < MIN_PASSWORD) return setError(`La contraseña nueva debe tener al menos ${MIN_PASSWORD} caracteres.`);
    if (next !== repeat) return setError("La contraseña nueva y su confirmación no coinciden.");
    change.mutate();
  };

  return (
    <form className="card card-pad account-form" onSubmit={submit} aria-labelledby="password-title" noValidate>
      <h2 id="password-title">Cambiar contraseña</h2>
      <label className="field">
        Contraseña actual
        <input className="input" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
      </label>
      <label className="field">
        Contraseña nueva
        <input className="input" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        <span className="xs">Al menos {MIN_PASSWORD} caracteres.</span>
      </label>
      <label className="field">
        Repite la nueva
        <input className="input" type="password" autoComplete="new-password" value={repeat} onChange={(e) => setRepeat(e.target.value)} />
      </label>
      {error && (
        <p className="form-error small" role="alert">
          {error}
        </p>
      )}
      <div className="card-actions">
        <button type="submit" className="btn btn-primary" disabled={change.isPending || !current || !next || !repeat}>
          {change.isPending && <Spinner label="Guardando" />}
          Cambiar contraseña
        </button>
      </div>
    </form>
  );
}

export function AccountPage() {
  const viewer = useViewer();
  return (
    <div className="day-main account-page">
      <div>
        <h1>Tu cuenta</h1>
        <p className="muted small" style={{ margin: 0 }}>
          Usuario <strong>{viewer.username}</strong>
        </p>
      </div>
      <PlanSummary />
      <PasswordForm />
    </div>
  );
}
