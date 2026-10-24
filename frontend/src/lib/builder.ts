import type { Leg, Result, SystemParlay } from "./api";
import { bestBookOdd, marketOdd } from "./books";
import { isAllowed, type Preferences } from "./preferences";

/**
 * Armado de parlays en el navegador con las preferencias del usuario.
 * Misma lógica que el backend (app/core/parlay.py): una pierna por partido, la mejor
 * de cada partido según el modo y luego los N mejores partidos (óptimo exacto para un
 * objetivo multiplicativo).
 */

export type Mode = "prob" | "ev";

/** Cómo se lee un parlay: los modos que se arman aquí y el parlay con valor (en prueba), que sólo registra el sistema. */
export type ParlayKind = Mode | "value";

/** Tope de probabilidad por modo: piernas casi seguras pagan demasiado poco. */
export const MAX_PROB: Record<Mode, number> = { prob: 0.92, ev: 0.97 };

/**
 * Lo que se promete de una pierna. Máxima probabilidad escoge con el modelo pero promete la menor entre el modelo y el
 * mercado sin comisión: escoger lo que el modelo ve más seguro escoge justo donde es más optimista que el mercado.
 * El parlay con valor también promete la menor. Máximo valor promete el modelo (con él se calcula su valor esperado).
 */
export function promised(leg: Pick<Leg, "p_model" | "p_market">, mode: ParlayKind): number {
  return mode !== "ev" && leg.p_market !== null ? Math.min(leg.p_model, leg.p_market) : leg.p_model;
}

type Priced = Pick<Leg, "p_model" | "p_market" | "odd" | "book_odds">;

function rawAcceptFrom(leg: Priced, mode: ParlayKind): number | null {
  if (mode === "ev") return 1 / leg.p_model;
  if (mode === "value") return 1 / promised(leg, mode);
  return marketOdd(leg.book_odds) ?? leg.odd;
}

/** Redondea hacia arriba a 2 decimales: el momio que se muestra nunca queda abajo del mínimo real. */
export function ceilOdd(odd: number): number {
  return Math.ceil(odd * 100 - 1e-9) / 100;
}

/** Qué significa "Acepta desde" en cada modo (texto visible y del title). */
export const ACCEPT_HELP: Record<ParlayKind, string> = {
  prob: "“Acepta desde” es lo que paga el mercado (la mediana de las casas): si tu casa paga menos, pagas más comisión de la normal.",
  ev: "“Acepta desde” es el momio justo del modelo: si tu casa paga menos, ya no hay valor.",
  value: "“Acepta desde” es el momio con el que el modelo y el mercado ven valor: si tu casa paga menos, ya no lo hay.",
};

/**
 * "Acepta desde": lo menos que conviene aceptar por una pierna en cualquier casa, esté o no en la API (p. ej.
 * Caliente). Máximo valor: el momio justo del modelo; abajo de él ya no hay valor. Máxima probabilidad: lo que paga el
 * mercado (la mediana de las casas de la API); abajo de él se paga más comisión de la normal. Ahí no sirve el justo:
 * por su comisión, ninguna casa lo paga. Parlay con valor: el mayor de los momios justos del modelo y del mercado.
 */
export function acceptFrom(leg: Priced, mode: ParlayKind): number | null {
  const odd = rawAcceptFrom(leg, mode);
  return odd === null ? null : ceilOdd(odd);
}

/** "Acepta desde" del parlay completo: el producto del de sus piernas (null si a alguna le falta). */
export function parlayAcceptFrom(legs: Priced[], mode: ParlayKind): number | null {
  let product = 1;
  for (const leg of legs) {
    const odd = rawAcceptFrom(leg, mode);
    if (odd === null) return null;
    product *= odd;
  }
  return ceilOdd(product);
}

export interface BuiltParlay {
  n: number;
  mode: ParlayKind;
  /** Parlay con una pierna de cada partido que tenga alguna elegible (p. ej. la jornada completa). */
  whole?: boolean;
  legs: Leg[];
  /** Producto de lo que se promete de cada pierna (`promised`). */
  probability: number;
  odd: number | null;
  ev: number | null;
  result: Result;
}

export function isEligible(leg: Leg, prefs: Preferences, mode: Mode): boolean {
  if (!isAllowed(leg, prefs)) return false;
  if (leg.player_status === "questionable" && !prefs.includeQuestionable) return false;
  if (leg.p_model < prefs.minProb || leg.p_model > MAX_PROB[mode]) return false;
  // Máxima probabilidad promete la menor entre modelo y mercado: exige el mercado, también dentro del rango.
  if (mode === "prob" && (leg.p_market === null || leg.p_market < prefs.minProb || leg.p_market > MAX_PROB.prob)) return false;
  // Sólo piernas que cotiza alguna casa (el parlay se tiene que poder apostar). Si la casa elegida no la
  // cotiza, el momio mínimo se compara con el mejor de las otras.
  const price = leg.odd ?? bestBookOdd(leg.book_odds)?.odd ?? null;
  if (price === null || price < prefs.minOdd) return false;
  if (leg.odd === null) return mode !== "ev" && !prefs.onlyPriced;
  return mode !== "ev" || leg.p_model * leg.odd - 1 >= 0;
}

const SCORE: Record<Mode, (l: Leg) => number> = {
  // Se escoge con el modelo; se promete con `promised`.
  prob: (l) => l.p_model,
  ev: (l) => l.p_model * (l.odd ?? 0),
};

/**
 * Parlay del sistema con sus piernas completas (las que la API manda a la cuenta). Cada pierna lleva el modelo y el
 * mercado con los que se registró: lo que se prometió y midió (las de partidos posteriores siguen cambiando).
 */
export function fromSystem(p: SystemParlay, legs: Map<number, Leg>): BuiltParlay | null {
  const full = p.legs.flatMap((l) => {
    const leg = legs.get(l.pick_id);
    return leg ? [{ ...leg, p_model: l.p_model, p_market: l.p_market }] : [];
  });
  if (full.length !== p.legs.length) return null;
  return { n: p.n_legs, mode: p.mode, legs: full, probability: p.probability, odd: p.odd, ev: p.ev, result: p.result };
}

export function parlayResult(results: Result[]): Result {
  if (results.includes("lost")) return "lost";
  if (results.includes(null)) return null;
  return results.some((r) => r === "won") ? "won" : "void";
}

/** Piernas candidatas ordenadas: la mejor de cada partido, de mejor a peor. */
export function rankedLegs(legs: Leg[], prefs: Preferences, mode: Mode): Leg[] {
  const score = SCORE[mode];
  const best = new Map<number, Leg>();
  for (const leg of legs) {
    if (!isEligible(leg, prefs, mode)) continue;
    const current = best.get(leg.match_id);
    if (!current || score(leg) > score(current)) best.set(leg.match_id, leg);
  }
  return [...best.values()].sort((a, b) => score(b) - score(a));
}

/** Tope del parlay "completo": lo más que acepta un boleto. */
export const MAX_WHOLE_LEGS = 20;

function toParlay(chosen: Leg[], mode: Mode): Omit<BuiltParlay, "n"> {
  const probability = chosen.reduce((acc, l) => acc * promised(l, mode), 1);
  const odd = chosen.every((l) => l.odd !== null) ? chosen.reduce((acc, l) => acc * (l.odd as number), 1) : null;
  return {
    mode,
    legs: chosen,
    probability,
    odd,
    ev: odd !== null ? probability * odd - 1 : null,
    result: parlayResult(chosen.map((l) => l.result)),
  };
}

/**
 * Una pierna por cada partido que tenga alguna elegible: la mejor de cada uno (p. ej. "toda la
 * jornada"). null si hay menos de 2 partidos o más de MAX_WHOLE_LEGS.
 */
export function buildWhole(legs: Leg[], prefs: Preferences, mode: Mode): BuiltParlay | null {
  const ranked = rankedLegs(legs, prefs, mode);
  if (ranked.length < 2 || ranked.length > MAX_WHOLE_LEGS) return null;
  return { n: ranked.length, whole: true, ...toParlay(ranked, mode) };
}

export function buildParlays(legs: Leg[], prefs: Preferences, mode: Mode): BuiltParlay[] {
  const ranked = rankedLegs(legs, prefs, mode);
  return [...prefs.sizes]
    .sort((a, b) => a - b)
    .filter((n) => ranked.length >= n)
    .map((n) => ({ n, ...toParlay(ranked.slice(0, n), mode) }));
}
