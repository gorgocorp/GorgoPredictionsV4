import type { Leg, Result } from "./api";
import { isAllowed, type Preferences } from "./preferences";

/**
 * Armado de parlays en el navegador con las preferencias del usuario.
 * Misma lógica que el backend (app/core/parlay.py): una pierna por partido, la mejor
 * de cada partido según el modo y luego los N mejores partidos (óptimo exacto para un
 * objetivo multiplicativo).
 */

export type Mode = "prob" | "ev";

/** Tope de probabilidad por modo: piernas casi seguras pagan demasiado poco. */
export const MAX_PROB: Record<Mode, number> = { prob: 0.92, ev: 0.97 };

export interface BuiltParlay {
  n: number;
  /** Parlay con una pierna de cada partido que tenga alguna elegible (p. ej. la jornada completa). */
  whole?: boolean;
  legs: Leg[];
  probability: number;
  odd: number | null;
  ev: number | null;
  result: Result;
}

export function isEligible(leg: Leg, prefs: Preferences, mode: Mode): boolean {
  if (!isAllowed(leg, prefs)) return false;
  if (leg.player_status === "questionable" && !prefs.includeQuestionable) return false;
  if (leg.p_model < prefs.minProb || leg.p_model > MAX_PROB[mode]) return false;
  if (leg.odd === null) {
    if (mode === "ev" || prefs.onlyPriced) return false;
    return 1 / leg.p_model >= prefs.minOdd;
  }
  if (leg.odd < prefs.minOdd) return false;
  return mode !== "ev" || leg.p_model * leg.odd - 1 >= 0;
}

const SCORE: Record<Mode, (l: Leg) => number> = {
  prob: (l) => l.p_model,
  ev: (l) => l.p_model * (l.odd ?? 0),
};

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

function toParlay(chosen: Leg[]): Omit<BuiltParlay, "n"> {
  const probability = chosen.reduce((acc, l) => acc * l.p_model, 1);
  const odd = chosen.every((l) => l.odd !== null) ? chosen.reduce((acc, l) => acc * (l.odd as number), 1) : null;
  return {
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
  return { n: ranked.length, whole: true, ...toParlay(ranked) };
}

export function buildParlays(legs: Leg[], prefs: Preferences, mode: Mode): BuiltParlay[] {
  const ranked = rankedLegs(legs, prefs, mode);
  return [...prefs.sizes]
    .sort((a, b) => a - b)
    .filter((n) => ranked.length >= n)
    .map((n) => ({ n, ...toParlay(ranked.slice(0, n)) }));
}
