import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { EmptyState, ErrorState, Skeleton, Spinner } from "../components/States";
import { useToast } from "../components/Toast";
import { api, ApiError, type AdminUser, type Role } from "../lib/api";
import { dateTime, longDate, shiftDate } from "../lib/format";
import { PLAN_LABELS, useViewer } from "../lib/session";

/** Administración de cuentas: sólo el administrador crea cuentas y cambia planes (la API lo exige). */

const MIN_PASSWORD = 8; // igual que app/core/accounts.py
const ROLES: Role[] = ["free", "subscriber", "admin"];
const USERS_KEY = ["admin", "users"];

function errorText(e: unknown, fallback: string): string {
  return e instanceof ApiError ? e.message : fallback;
}

function PlanCell({ user }: { user: AdminUser }) {
  const expired = user.role === "subscriber" && !user.full && user.active;
  return (
    <>
      <span className={`badge ${user.full ? "badge-won" : "badge-neutral"}`}>{PLAN_LABELS[user.role]}</span>
      {expired && (
        <>
          {" "}
          <span className="badge badge-warn">Vencida</span>
        </>
      )}
    </>
  );
}

function NewUserForm({ today }: { today: string }) {
  const client = useQueryClient();
  const notify = useToast();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("free");
  const [until, setUntil] = useState("");
  const [error, setError] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () =>
      api.admin.createUser({ username: username.trim(), password, role, subscription_until: role === "subscriber" && until ? until : null }),
    onSuccess: () => {
      notify(`Cuenta ${username.trim()} creada (${PLAN_LABELS[role]}). Dale su usuario y contraseña.`);
      setUsername("");
      setPassword("");
      setRole("free");
      setUntil("");
      client.invalidateQueries({ queryKey: USERS_KEY });
    },
    onError: (e) => setError(errorText(e, "No se pudo crear la cuenta")),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < MIN_PASSWORD) return setError(`La contraseña debe tener al menos ${MIN_PASSWORD} caracteres.`);
    create.mutate();
  };

  return (
    <form className="card card-pad account-form" onSubmit={submit} aria-labelledby="new-user-title" noValidate>
      <h2 id="new-user-title">Nueva cuenta</h2>
      <div className="filters">
        <label className="field">
          Usuario
          <input className="input" autoComplete="off" autoCapitalize="none" spellCheck={false} value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="field">
          Contraseña inicial
          <input className="input" type="text" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <label className="field">
          Plan
          <select className="select" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {PLAN_LABELS[r]}
              </option>
            ))}
          </select>
        </label>
        {role === "subscriber" && (
          <label className="field">
            Vigente hasta (incluido)
            <input className="input num" type="date" min={today} value={until} onChange={(e) => setUntil(e.target.value)} />
          </label>
        )}
      </div>
      <p className="muted xs" style={{ margin: 0 }}>
        Usuario: 3 a 32 letras sin acento, números, punto, guion o guion bajo. Contraseña: al menos {MIN_PASSWORD} caracteres.
        {role === "subscriber" && " Sin fecha, la suscripción no vence."}
      </p>
      {error && (
        <p className="form-error small" role="alert">
          {error}
        </p>
      )}
      <div className="card-actions">
        <button type="submit" className="btn btn-primary" disabled={create.isPending || !username.trim() || !password}>
          {create.isPending && <Spinner label="Creando" />}
          Crear cuenta
        </button>
      </div>
    </form>
  );
}

function EditUser({ user, today, onClose }: { user: AdminUser; today: string; onClose: () => void }) {
  const client = useQueryClient();
  const notify = useToast();
  const viewer = useViewer();
  const panelRef = useRef<HTMLDivElement>(null);
  const [role, setRole] = useState<Role>(user.role);
  const [until, setUntil] = useState(user.subscription_until ?? "");
  const [active, setActive] = useState(user.active);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const self = user.id === viewer.id;

  useEffect(() => {
    const returnFocus = document.activeElement as HTMLElement | null;
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      returnFocus?.focus?.();
    };
  }, [onClose]);

  const done = (message: string) => {
    notify(message);
    client.invalidateQueries({ queryKey: USERS_KEY });
    onClose();
  };
  const save = useMutation({
    mutationFn: () => api.admin.updateUser(user.id, { role, subscription_until: role === "subscriber" && until ? until : null, active }),
    onSuccess: () => done(`${user.username}: cambios guardados`),
    onError: (e) => setError(errorText(e, "No se pudieron guardar los cambios")),
  });
  const reset = useMutation({
    mutationFn: () => api.admin.resetPassword(user.id, password),
    onSuccess: () => done(`${user.username}: contraseña nueva guardada; sus sesiones se cerraron`),
    onError: (e) => setError(errorText(e, "No se pudo cambiar la contraseña")),
  });

  /** Suscripción de N días a partir de hoy o, si sigue vigente, desde su último día. */
  const extend = (days: number) => {
    const from = role === "subscriber" && until && until >= today ? until : shiftDate(today, -1);
    setRole("subscriber");
    setUntil(shiftDate(from, days));
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    save.mutate();
  };

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div ref={panelRef} className="drawer" role="dialog" aria-modal="true" aria-labelledby="edit-user-title" tabIndex={-1}>
        <div className="drawer-head">
          <div>
            <h2 id="edit-user-title">{user.username}</h2>
            <p className="muted small" style={{ margin: 0 }}>
              {user.bets} {user.bets === 1 ? "apuesta" : "apuestas"} · último acceso {user.last_login_at ? dateTime(user.last_login_at) : "nunca"}
            </p>
          </div>
          <button type="button" className="btn btn-ghost btn-icon" aria-label="Cerrar" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="drawer-body">
          <form className="account-form" onSubmit={submit} aria-label="Plan y estado">
            <fieldset className="pref-group">
              <legend>Plan</legend>
              <div className="segmented" role="radiogroup" aria-label="Plan">
                {ROLES.map((r) => (
                  <button
                    key={r}
                    type="button"
                    role="radio"
                    aria-checked={role === r}
                    disabled={self && r !== "admin"}
                    onClick={() => setRole(r)}
                  >
                    {PLAN_LABELS[r]}
                  </button>
                ))}
              </div>
            </fieldset>
            {role === "subscriber" && (
              <>
                <label className="field">
                  Vigente hasta (incluido; vacío = sin vencimiento)
                  <input className="input num" type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
                </label>
                <div className="card-actions" role="group" aria-label="Extender suscripción">
                  <button type="button" className="btn btn-sm" onClick={() => extend(30)}>
                    +30 días
                  </button>
                  <button type="button" className="btn btn-sm" onClick={() => extend(7)}>
                    +7 días
                  </button>
                </div>
                {until && (
                  <p className="muted xs" style={{ margin: 0 }}>
                    {until >= today ? `Ve todo hasta el ${longDate(until).toLowerCase()}.` : "Con esa fecha ya está vencida: ve lo mismo que Gratis."}
                  </p>
                )}
              </>
            )}
            <label className="toggle">
              <input type="checkbox" checked={active} disabled={self} onChange={(e) => setActive(e.target.checked)} />
              Cuenta activa {self && <span className="muted xs">(la tuya no se puede desactivar)</span>}
            </label>
            {!active && (
              <p className="muted xs" style={{ margin: 0 }}>
                Una cuenta desactivada no puede entrar y se cierran sus sesiones; sus apuestas se conservan.
              </p>
            )}
            <div className="card-actions">
              <button type="submit" className="btn btn-primary" disabled={save.isPending}>
                {save.isPending && <Spinner label="Guardando" />}
                Guardar cambios
              </button>
            </div>
          </form>

          <form
            className="account-form"
            aria-label="Contraseña nueva"
            onSubmit={(e) => {
              e.preventDefault();
              setError(null);
              if (password.length < MIN_PASSWORD) return setError(`La contraseña debe tener al menos ${MIN_PASSWORD} caracteres.`);
              reset.mutate();
            }}
          >
            <label className="field">
              Contraseña nueva (si la olvidó)
              <input className="input" type="text" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            <div className="card-actions">
              <button type="submit" className="btn" disabled={reset.isPending || !password}>
                {reset.isPending && <Spinner label="Guardando" />}
                Poner contraseña
              </button>
            </div>
          </form>

          {error && (
            <p className="form-error small" role="alert">
              {error}
            </p>
          )}
        </div>
      </div>
    </>
  );
}

export function UsersPage() {
  const users = useQuery({ queryKey: USERS_KEY, queryFn: api.admin.users });
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta });
  const [editing, setEditing] = useState<number | null>(null);
  const close = useCallback(() => setEditing(null), []);
  const today = meta.data?.today ?? new Date().toISOString().slice(0, 10);
  const list = users.data ?? [];
  const counts = ROLES.map((r) => `${list.filter((u) => u.active && u.role === r).length} ${PLAN_LABELS[r].toLowerCase()}`);
  const editingUser = list.find((u) => u.id === editing);

  return (
    <div className="day-main">
      <div>
        <h1>Usuarios</h1>
        <p className="muted small" style={{ margin: 0 }}>
          {users.data ? `${list.length} cuentas · activas: ${counts.join(", ")}` : "Cuentas, planes y suscripciones"}
        </p>
      </div>

      <NewUserForm today={today} />

      {users.isPending ? (
        <Skeleton height={240} />
      ) : users.isError ? (
        <ErrorState message={(users.error as Error).message} onRetry={() => users.refetch()} />
      ) : list.length === 0 ? (
        <EmptyState title="Todavía no hay cuentas" />
      ) : (
        <div className="card table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">Usuario</th>
                <th scope="col">Plan</th>
                <th scope="col">Vigente hasta</th>
                <th scope="col">Estado</th>
                <th scope="col" className="r">
                  Apuestas
                </th>
                <th scope="col">Último acceso</th>
                <th scope="col">
                  <span className="visually-hidden">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {list.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.username}</strong>
                  </td>
                  <td>
                    <PlanCell user={u} />
                  </td>
                  <td className="num">{u.role === "subscriber" ? (u.subscription_until ? longDate(u.subscription_until) : "Sin vencimiento") : "—"}</td>
                  <td>
                    {!u.active ? (
                      <span className="badge badge-lost">Desactivada</span>
                    ) : !u.has_password ? (
                      <span className="badge badge-warn">Sin contraseña</span>
                    ) : (
                      <span className="muted">Activa</span>
                    )}
                  </td>
                  <td className="r num">{u.bets}</td>
                  <td className="muted">{u.last_login_at ? dateTime(u.last_login_at) : "Nunca"}</td>
                  <td className="r">
                    <button type="button" className="btn btn-sm" onClick={() => setEditing(u.id)} aria-label={`Editar ${u.username}`}>
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editingUser && <EditUser key={editingUser.id} user={editingUser} today={today} onClose={close} />}
    </div>
  );
}
