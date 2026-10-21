import type { Leg, SlateGame, SystemParlay } from "../lib/api";
import { ACCEPT_HELP, type BuiltParlay } from "../lib/builder";
import type { SportConfig } from "../lib/sports";
import { Paywall, ParlaysPlaceholder } from "./Locked";
import { ParlayCard } from "./ParlaysSection";
import { EmptyState } from "./States";

/**
 * Parlay del sistema con sus piernas completas (las que la API manda a la cuenta). Cada pierna lleva el modelo y el
 * mercado con los que se registró: lo que se prometió y midió (las de partidos posteriores siguen cambiando).
 */
function toBuilt(p: SystemParlay, legs: Map<number, Leg>): BuiltParlay | null {
  const full = p.legs.flatMap((l) => {
    const leg = legs.get(l.pick_id);
    return leg ? [{ ...leg, p_model: l.p_model, p_market: l.p_market }] : [];
  });
  if (full.length !== p.legs.length) return null;
  return { n: p.n_legs, mode: p.mode, legs: full, probability: p.probability, odd: p.odd, ev: p.ev, result: p.result };
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
                historial. De cada pierna se promete la menor entre el modelo y el mercado. Nunca dos piernas del mismo
                partido. {ACCEPT_HELP.prob}
              </p>
            </div>
          </div>
          {built.length === 0 ? (
            <EmptyState title="Hoy no hay parlay gratis">
              Hacen falta al menos dos partidos con piernas que cumplan la configuración estándar, que ya cotice alguna
              casa y que el mercado también vea probables. Si todavía no llegan los momios, vuelve más cerca de los
              partidos.
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
          Parlays de 2 a 8 piernas, los de máximo valor, las apuestas individuales sugeridas, las {totalLegs} piernas que
          analizó el modelo con sus momios y proyecciones, y tu propia configuración para armar los tuyos.
        </Paywall>
      </section>
    </>
  );
}
