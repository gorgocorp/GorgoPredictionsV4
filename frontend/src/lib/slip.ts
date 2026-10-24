import type { Leg, SlateGame, SportKey } from "./api";
import { asSport, type SportConfig } from "./sports";
import { persistentStore } from "./store";

/** Una pierna en el boleto. Guarda una copia de los datos para no depender de la página abierta. */
export interface SlipLeg {
  pickId: number;
  /** Un boleto puede mezclar NBA y fútbol. */
  sport: SportKey;
  /** Partido común (core.matches): detecta piernas del mismo partido aunque se mezclen deportes. */
  matchId: number;
  date: string;
  matchup: string;
  description: string;
  pModel: number;
  /**
   * Probabilidad sin comisión del mercado que traía la pierna al agregarla (en los destacados, la de cuando se
   * publicaron); null si ninguna casa cotiza su mercado completo. Falta en los boletos guardados antes de que el
   * boleto la guardara.
   */
  pMarket?: number | null;
  odd: number | null;
  /** Momios de las casas de la API (para llenar solo el momio si tu casa es una de ellas). */
  bookOdds?: Record<string, number> | null;
  /** Momios que escribió el usuario por casa (clave en minúsculas), tal como los escribió (americano o decimal). */
  typedOdds?: Record<string, string>;
}

/** Cómo se apuesta el boleto: un parlay con todas las piernas o una apuesta individual por pierna. */
export type SlipMode = "parlay" | "singles";

export interface SlipState {
  legs: SlipLeg[];
  /** Monto del parlay; en individuales, el de cada pierna que no tenga uno propio. */
  stake: number;
  /** Momio total del boleto por casa (clave en minúsculas), si la casa lo muestra distinto al producto de las piernas. */
  totalOdds?: Record<string, string>;
  mode?: SlipMode;
  /** Individuales: monto propio de una pierna (por pickId). */
  stakes?: Record<number, number>;
}

/** Clave de una casa en los momios escritos: sin espacios extra ni mayúsculas. */
export const bookKey = (book: string) => book.trim().toLowerCase();

export function matchupOf(config: SportConfig, game: SlateGame | undefined): string {
  return game ? config.matchup(game.home.name, game.away.name) : "—";
}

/** Copia de una pierna para el boleto; el día es el del partido (fútbol) o el de la página. */
export function toSlipLeg(config: SportConfig, leg: Leg, game: SlateGame | undefined, date: string): SlipLeg {
  return {
    pickId: leg.id,
    sport: leg.sport,
    matchId: leg.match_id,
    date: game?.match_date ?? date,
    matchup: matchupOf(config, game),
    description: leg.description,
    pModel: leg.p_model,
    pMarket: leg.p_market,
    odd: leg.odd,
    bookOdds: leg.book_odds,
  };
}

const EMPTY: SlipState = { legs: [], stake: 100, mode: "parlay" };

/** Con una sola pierna, el boleto es una apuesta individual aunque esté en modo parlay. */
export function slipMode(state: SlipState): SlipMode {
  return state.legs.length === 1 ? "singles" : (state.mode ?? "parlay");
}

/** Monto de una pierna en individuales: el suyo o el general. */
export function stakeOf(state: SlipState, pickId: number): number {
  return state.stakes?.[pickId] ?? state.stake;
}

function parseStakes(raw: unknown): Record<number, number> {
  if (!raw || typeof raw !== "object") return {};
  return Object.fromEntries(
    Object.entries(raw).filter(([id, v]) => Number.isInteger(Number(id)) && typeof v === "number" && Number.isFinite(v) && v >= 0),
  );
}

/** Probabilidad del mercado guardada: un número entre 0 y 1, null (sin mercado) o nada (boleto anterior). */
function parseMarket(raw: unknown): number | null | undefined {
  if (raw === null) return null;
  return typeof raw === "number" && raw > 0 && raw < 1 ? raw : undefined;
}

/** Boleto guardado en el navegador; descarta piernas incompletas (p. ej. de otra versión). */
export function parseSlip(raw: unknown): SlipState | null {
  const parsed = raw as SlipState;
  if (!Array.isArray(parsed?.legs)) return null;
  const legs = parsed.legs
    .filter(
      (l) => l && Number.isInteger(l.pickId) && Number.isInteger(l.matchId) && asSport(l.sport) !== null && typeof l.description === "string",
    )
    .map((l) => ({ ...l, pMarket: parseMarket(l.pMarket) }));
  return {
    legs,
    stake: Number(parsed.stake) || EMPTY.stake,
    totalOdds: parsed.totalOdds ?? {},
    mode: parsed.mode === "singles" ? "singles" : "parlay",
    stakes: parseStakes(parsed.stakes),
  };
}

const store = persistentStore<SlipState>("gorgo-v4.slip.v1", EMPTY, parseSlip);

export const slip = {
  get: store.get,
  has: (pickId: number) => store.get().legs.some((l) => l.pickId === pickId),
  add(leg: SlipLeg) {
    if (!slip.has(leg.pickId)) store.set({ ...store.get(), legs: [...store.get().legs, leg] });
  },
  remove(pickId: number) {
    const stakes = Object.fromEntries(Object.entries(store.get().stakes ?? {}).filter(([id]) => Number(id) !== pickId));
    store.set({ ...store.get(), legs: store.get().legs.filter((l) => l.pickId !== pickId), stakes });
  },
  toggle(leg: SlipLeg) {
    if (slip.has(leg.pickId)) slip.remove(leg.pickId);
    else slip.add(leg);
  },
  /** Cambia las piernas del boleto (p. ej. un parlay sugerido o las individuales sugeridas). */
  replace(legs: SlipLeg[], mode: SlipMode = "parlay") {
    store.set({ ...store.get(), legs, totalOdds: {}, mode, stakes: {} });
  },
  setMode(mode: SlipMode) {
    store.set({ ...store.get(), mode });
  },
  setStake(stake: number) {
    store.set({ ...store.get(), stake });
  },
  /** Individuales: el mismo monto para todas las piernas (quita los montos propios). */
  setAllStakes(stake: number) {
    store.set({ ...store.get(), stake, stakes: {} });
  },
  /** Individuales: monto propio de una pierna. */
  setLegStake(pickId: number, stake: number) {
    store.set({ ...store.get(), stakes: { ...store.get().stakes, [pickId]: stake } });
  },
  restore(previous: SlipState) {
    store.set(previous);
  },
  /** Guarda el momio que escribió el usuario para su casa: cada casa conserva los suyos. */
  setLegOdd(pickId: number, book: string, value: string) {
    const key = bookKey(book);
    store.set({
      ...store.get(),
      legs: store.get().legs.map((l) => (l.pickId === pickId ? { ...l, typedOdds: { ...l.typedOdds, [key]: value } } : l)),
    });
  },
  setTotalOdd(book: string, value: string) {
    store.set({ ...store.get(), totalOdds: { ...store.get().totalOdds, [bookKey(book)]: value } });
  },
  clear() {
    store.set({ ...store.get(), legs: [], totalOdds: {}, stakes: {} });
  },
};

export const useSlip = store.use;
