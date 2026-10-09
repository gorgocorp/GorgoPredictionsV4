import type { ReactNode } from "react";

/**
 * Lo que una cuenta free no ve. La API no manda esos datos: lo difuminado es relleno genérico con la forma de la
 * pantalla real, para que se entienda qué incluye la suscripción.
 */

export const SUBSCRIBE_HINT = "Para activar tu suscripción, contacta al administrador.";

export function Paywall({ title, children, placeholder }: { title: string; children: ReactNode; placeholder: ReactNode }) {
  return (
    <div className="locked">
      <div className="locked-content" aria-hidden="true">
        {placeholder}
      </div>
      <div className="locked-overlay">
        <div className="card locked-card" role="note" aria-label={title}>
          <span className="locked-icon" aria-hidden="true">
            🔒
          </span>
          <h3>{title}</h3>
          <div className="muted small">{children}</div>
          <p className="muted xs" style={{ margin: 0 }}>
            {SUBSCRIBE_HINT}
          </p>
        </div>
      </div>
    </div>
  );
}

/** Proyección del modelo de un partido, bloqueada: una barra genérica difuminada y el aviso. */
export function LockedProjection({ outcomes }: { outcomes: 2 | 3 }) {
  return (
    <div className="locked-projection">
      <div className={`winbar ${outcomes === 3 ? "winbar-3" : ""} locked-content`} aria-hidden="true">
        {(outcomes === 3 ? [45, 27, 28] : [55, 45]).map((w, i) => (
          <span key={i} style={{ width: `${w}%` }} />
        ))}
      </div>
      <span className="xs muted">
        <span aria-hidden="true">🔒</span> Probabilidades del modelo con suscripción
      </span>
    </div>
  );
}

const FAKE_LEGS = ["Pierna del modelo", "Pierna con valor", "Pierna del modelo", "Pierna de jugador"];

/** Relleno: tarjetas de parlay y filas de piernas sin datos reales. */
export function ParlaysPlaceholder() {
  return (
    <>
      <div className="parlay-list">
        {[4, 5, 6].map((n) => (
          <div key={n} className="card parlay-card">
            <div className="parlay-head">
              <h3>{n} piernas</h3>
            </div>
            <div className="parlay-stats">
              {["Prob. modelo", "Momio justo", "Casa"].map((label) => (
                <div key={label} className="stat">
                  <span className="stat-label">{label}</span>
                  <span className="stat-value">00.0</span>
                </div>
              ))}
            </div>
            <ol className="leg-list">
              {FAKE_LEGS.slice(0, 3).map((text, i) => (
                <li key={i} className="leg-item">
                  <span>
                    <span className="muted xs">Equipo A vs Equipo B</span>
                    <br />
                    {text}
                  </span>
                  <span className="leg-meta num">00%</span>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>
      <div className="card table-wrap" style={{ marginTop: "var(--space-4)" }}>
        <table className="data">
          <tbody>
            {FAKE_LEGS.map((text, i) => (
              <tr key={i}>
                <td>Equipo A vs Equipo B</td>
                <td>{text}</td>
                <td className="num">00%</td>
                <td className="num">0.00</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
