import type { Leg, SlateGame, SystemParlay } from "../lib/api";
import type { BuiltParlay } from "../lib/builder";
import type { SportConfig } from "../lib/sports";
import { Paywall, ParlaysPlaceholder } from "./Locked";
import { ParlayCard } from "./ParlaysSection";
import { EmptyState } from "./States";

/** Parlay del sistema con sus piernas completas (las que la API manda a la cuenta). */
function toBuilt(p: SystemParlay, legs: Map<number, Leg>): BuiltParlay | null {
  const full = p.legs.map((l) => legs.get(l.pick_id)).filter((l): l is Leg => l !== undefined);
  if (full.length !== p.legs.length) return null;
  return { n: p.n_legs, legs: full, probability: p.probability, odd: p.odd, ev: p.ev, result: p.result };
}

/**
 * Lo que ve una cuenta free en un día: los parlays gratis (máxima probabilidad de 2 y 3 piernas, los que registra
 * y mide el sistema) y, difuminado, todo lo que incluye la suscripción.
 */
export function FreePicks({
  config,
  parlays,
  legs,
  games,
  bookmaker,
  date,
  totalLegs,
}: {
  config: SportConfig;
  /** Parlays gratis del día; undefined en vistas de varios días (sin parlays gratis). */
  parlays: SystemParlay[] | undefined;
  legs: Leg[];
  games: Map<number, SlateGame>;
  /** Casa con la que el sistema registra sus parlays. */
  bookmaker: string;
  date: string;
  /** Piernas que analizó el modelo en estos partidos. */
  totalLegs: number;
}) {
  const byId = new Map(legs.map((l) => [l.id, l]));
  const built = (parlays ?? [])
    .map((p) => toBuilt(p, byId))
    .filter((p): p is BuiltParlay => p !== null)
    .sort((a, b) => a.n - b.n);

  return (
    <>
      {parlays && (
        <section aria-labelledby="free-parlays-title">
          <div className="section-head">
            <div>
              <h2 id="free-parlays-title">Parlays gratis del día</h2>
              <p className="muted small" style={{ margin: 0 }}>
                Los de máxima probabilidad de 2 y 3 piernas con la configuración estándar: los mismos que registra y mide el
                historial. Nunca dos piernas del mismo partido.
              </p>
            </div>
          </div>
          {built.length === 0 ? (
            <EmptyState title="Hoy no hay parlay gratis">
              Hacen falta al menos dos partidos con piernas que cumplan la configuración estándar y que ya cotice alguna
              casa. Si todavía no llegan los momios, vuelve más cerca de los partidos.
            </EmptyState>
          ) : (
            <div className="parlay-list">
              {built.map((p) => (
                <ParlayCard key={p.n} config={config} parlay={p} games={games} bookmaker={bookmaker} date={date} title="Gratis" />
              ))}
            </div>
          )}
        </section>
      )}

      <section aria-label="Con suscripción">
        <Paywall title="Todo lo demás, con suscripción" placeholder={<ParlaysPlaceholder />}>
          Parlays de 2 a 8 piernas, los de máximo valor, las {totalLegs} piernas que analizó el modelo con sus momios y
          proyecciones, y tu propia configuración para armar los tuyos.
        </Paywall>
      </section>
    </>
  );
}
