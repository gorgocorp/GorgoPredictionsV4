import type { Leg } from "./api";
import { ceilOdd, promised } from "./builder";
import { legValue, parseOdds, type LegValue } from "./oddsInput";
import { persistentStore } from "./store";

/**
 * Calculadora Caliente (sólo admin): parte del parlay con valor del día y lo compara con los momios de una casa que no
 * está en la API. Esa casa suele ofrecer otra línea que Bet365 (3.5 tarjetas en vez de 4.5), así que en cada partido se
 * escoge la línea y se escriben sus momios. Hay valor con la misma regla que el boleto y el parlay con valor: el momio
 * paga más que el justo del modelo y del mercado. No escribe nada ni toca la prueba del parlay con valor.
 */

/** Orden de los lados de un mercado al mostrarlos. */
const SIDE_ORDER = ["over", "under", "yes", "no", "home", "draw", "away", "1x", "x2", "12"];

/** Lados que suman 100% entre sí: con todos sus momios se puede calcular la comisión de la casa. */
const PARTITIONS = [["over", "under"], ["yes", "no"], ["home", "draw", "away"]].map((sides) => sides.join(","));

export interface LineGroup {
  /** null en mercados sin línea (1X2, doble oportunidad, ambos anotan). */
  line: number | null;
  /** Lados que tiene V4 en esa línea, en orden. */
  legs: Leg[];
}

const sideRank = (side: string) => (SIDE_ORDER.includes(side) ? SIDE_ORDER.indexOf(side) : SIDE_ORDER.length);

/** Las líneas del mismo mercado que `published` (mismo partido, equipo, estadística y jugador), de menor a mayor. */
export function marketLines(published: Leg, legs: Leg[]): LineGroup[] {
  const groups = new Map<number | null, Leg[]>();
  for (const l of legs) {
    const same =
      l.match_id === published.match_id &&
      l.market === published.market &&
      l.team === published.team &&
      l.stat === published.stat &&
      l.player_id === published.player_id;
    if (same) groups.set(l.line, [...(groups.get(l.line) ?? []), l]);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => (a ?? 0) - (b ?? 0))
    .map(([line, group]) => ({ line, legs: group.sort((a, b) => sideRank(a.side) - sideRank(b.side)) }));
}

export interface SideCheck {
  leg: Leg;
  /** Lo que se escribió (americano o decimal). */
  raw: string;
  /** Momio de la casa en decimal; null si no se escribió o no es válido. */
  odd: number | null;
  /** Lo que se promete: la menor entre el modelo y el mercado (sin mercado, el modelo). */
  promised: number;
  /** Desde qué momio hay valor para el modelo y el mercado (redondeado hacia arriba). */
  valueFrom: number;
  value: LegValue | null;
  /** Valor esperado por unidad con cada probabilidad: p × momio − 1. */
  evModel: number | null;
  evMarket: number | null;
}

export function checkSide(leg: Leg, raw: string): SideCheck {
  const odd = parseOdds(raw);
  const p = promised(leg, "value");
  return {
    leg,
    raw,
    odd,
    promised: p,
    valueFrom: ceilOdd(1 / p),
    value: odd === null ? null : legValue(leg.p_model, leg.p_market, odd),
    evModel: odd === null ? null : leg.p_model * odd - 1,
    evMarket: odd === null || leg.p_market === null ? null : leg.p_market * odd - 1,
  };
}

/**
 * Comisión de la casa en una línea: cuánto suman sus probabilidades implícitas por encima de 100%. Sólo en mercados
 * cuyos lados suman 100% y con el momio de todos ellos; si no, null.
 */
export function commission(checks: SideCheck[]): number | null {
  const sides = checks.map((c) => c.leg.side).join(",");
  if (!PARTITIONS.includes(sides) || checks.some((c) => c.odd === null)) return null;
  return checks.reduce((acc, c) => acc + 1 / (c.odd as number), 0) - 1;
}

export type Recommendation =
  /** Falta escribir algún momio en la línea escogida de algún partido. */
  | { kind: "missing" }
  /** Nada tiene valor; `closest` es la opción que más se acercó a su "valor desde". */
  | { kind: "none"; closest: SideCheck | null }
  | { kind: "single"; pick: SideCheck }
  | { kind: "parlay"; picks: SideCheck[]; odd: number; valueFrom: number; evModel: number; evMarket: number };

/**
 * Qué conviene meter con los momios escritos (`matches`: las opciones de la línea escogida de cada partido). De cada
 * partido, la opción con valor que más se promete (a igual, la de más valor para el mercado). Con dos o más partidos
 * con valor, el parlay; con uno, sólo esa pierna (con una sin valor, el parlay pierde valor); con ninguno, nada.
 */
export function recommend(matches: SideCheck[][]): Recommendation {
  if (matches.length === 0 || matches.some((options) => options.every((o) => o.odd === null))) return { kind: "missing" };
  const best = matches.flatMap((options) => {
    const withValue = options.filter((o) => o.value === "value");
    withValue.sort((a, b) => b.promised - a.promised || (b.evMarket ?? 0) - (a.evMarket ?? 0));
    return withValue.slice(0, 1);
  });
  if (best.length === 0) {
    const priced = matches.flat().filter((o) => o.odd !== null);
    const ratio = (o: SideCheck) => (o.odd as number) / o.valueFrom;
    return { kind: "none", closest: priced.reduce<SideCheck | null>((top, o) => (!top || ratio(o) > ratio(top) ? o : top), null) };
  }
  if (best.length === 1) return { kind: "single", pick: best[0] };
  const odd = best.reduce((acc, o) => acc * (o.odd as number), 1);
  return {
    kind: "parlay",
    picks: best,
    odd,
    valueFrom: ceilOdd(best.reduce((acc, o) => acc / o.promised, 1)),
    evModel: best.reduce((acc, o) => acc * o.leg.p_model, 1) * odd - 1,
    evMarket: best.reduce((acc, o) => acc * (o.leg.p_market as number), 1) * odd - 1,
  };
}

interface CalculatorState {
  /** Momio escrito por pierna (id del pick), tal como se escribió. */
  odds: Record<string, string>;
  /** Línea escogida por partido (match id). */
  lines: Record<string, number>;
}

function stringsOf(raw: unknown): Record<string, string> {
  if (!raw || typeof raw !== "object") return {};
  return Object.fromEntries(Object.entries(raw).filter(([, v]) => typeof v === "string"));
}

function numbersOf(raw: unknown): Record<string, number> {
  if (!raw || typeof raw !== "object") return {};
  return Object.fromEntries(Object.entries(raw).filter(([, v]) => typeof v === "number" && Number.isFinite(v)));
}

/** Lo escrito en la calculadora se guarda en el navegador: salir de la página no lo borra. */
export const calculator = persistentStore<CalculatorState>("gorgo-v4.calculadora.v1", { odds: {}, lines: {} }, (raw) => {
  const parsed = raw as Partial<CalculatorState> | null;
  return parsed && typeof parsed === "object" ? { odds: stringsOf(parsed.odds), lines: numbersOf(parsed.lines) } : null;
});
