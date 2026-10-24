import type { Leg, SlateGame, SystemParlay } from "../lib/api";
import { ACCEPT_HELP, fromSystem, type BuiltParlay } from "../lib/builder";
import type { SportConfig } from "../lib/sports";
import { ParlayCard } from "./ParlaysSection";
import { EmptyState } from "./States";

/**
 * El parlay con valor del día, en prueba (sólo le llega a admin: app/core/value.py). Se publica una vez, la víspera, y
 * ya no cambia; sus resultados y su CLV se ven en Rendimiento.
 */
export function ValueParlay({
  config,
  parlays,
  legs,
  games,
  bookmaker,
  date,
}: {
  config: SportConfig;
  /** Parlays que registró el sistema para el día. */
  parlays: SystemParlay[];
  /** Todas las piernas del día (sin los filtros de tus preferencias). */
  legs: Leg[];
  games: Map<number, SlateGame>;
  /** Casa con la que el sistema registra y mide sus parlays. */
  bookmaker: string;
  date: string;
}) {
  const byId = new Map(legs.map((l) => [l.id, l]));
  const built = parlays
    .filter((p) => p.mode === "value")
    .map((p) => fromSystem(p, byId))
    .filter((p): p is BuiltParlay => p !== null);

  return (
    <section aria-labelledby="value-parlay-title">
      <div className="section-head">
        <div>
          <h2 id="value-parlay-title">
            Parlay con valor <span className="badge badge-live">Prueba · sólo admin</span>
          </h2>
          <p className="muted small" style={{ margin: 0 }}>
            Piernas en las que {bookmaker} paga más que el momio justo del modelo y del mercado. Se publica la víspera y ya
            no cambia: lo que se publicó es lo que se mide (resultados y CLV, en Rendimiento). {ACCEPT_HELP.value}
          </p>
        </div>
      </div>
      {built.length === 0 ? (
        <EmptyState title="Sin parlay con valor para este día">
          Se publica desde la noche anterior si hay piernas que cumplan la regla; si no, se reintenta en cada corrida
          mientras queden partidos con tiempo para medir su cierre. Que no haya parlay también es una respuesta.
        </EmptyState>
      ) : (
        <div className="parlay-list">
          {built.map((p) => (
            <ParlayCard key={p.n} config={config} parlay={p} games={games} bookmaker={bookmaker} date={date} title="Con valor" />
          ))}
        </div>
      )}
    </section>
  );
}
