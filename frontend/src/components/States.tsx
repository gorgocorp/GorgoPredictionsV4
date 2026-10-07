import type { ReactNode } from "react";
import type { Result } from "../lib/api";

export function Skeleton({ height = 16, width = "100%" }: { height?: number; width?: number | string }) {
  return <div className="skeleton" style={{ height, width }} aria-hidden="true" />;
}

export function SkeletonCards({ count, height }: { count: number; height: number }) {
  return (
    <div className="games-grid" aria-busy="true" aria-label="Cargando">
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} height={height} />
      ))}
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="card state">
      <h3>{title}</h3>
      {children && <p className="muted small">{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card state state-error" role="alert">
      <h3>No se pudo cargar</h3>
      <p className="muted small">{message}</p>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          Reintentar
        </button>
      )}
    </div>
  );
}

const RESULT_TEXT: Record<Exclude<Result, null>, { label: string; icon: string }> = {
  won: { label: "Ganada", icon: "✓" },
  lost: { label: "Perdida", icon: "✕" },
  void: { label: "Anulada", icon: "–" },
};

/** Resultado con icono y texto (no sólo color). */
export function ResultBadge({ result, pendingLabel }: { result: Result; pendingLabel?: string }) {
  if (!result) {
    return pendingLabel ? <span className="badge badge-neutral">{pendingLabel}</span> : null;
  }
  const { label, icon } = RESULT_TEXT[result];
  return (
    <span className={`badge badge-${result}`}>
      <span aria-hidden="true">{icon}</span>
      {label}
    </span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <>
      <span className="spinner" aria-hidden="true" />
      {label && <span className="visually-hidden">{label}</span>}
    </>
  );
}
