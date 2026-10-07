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
  odd: number | null;
  /** Momios de las casas de la API (para llenar solo el momio si tu casa es una de ellas). */
  bookOdds?: Record<string, number> | null;
  /** Momios que escribió el usuario por casa (clave en minúsculas), tal como los escribió (americano o decimal). */
  typedOdds?: Record<string, string>;
}

export interface SlipState {
  legs: SlipLeg[];
  stake: number;
  /** Momio total del boleto por casa (clave en minúsculas), si la casa lo muestra distinto al producto de las piernas. */
  totalOdds?: Record<string, string>;
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
    odd: leg.odd,
    bookOdds: leg.book_odds,
  };
}

const EMPTY: SlipState = { legs: [], stake: 100 };

/** Boleto guardado en el navegador; descarta piernas incompletas (p. ej. de otra versión). */
export function parseSlip(raw: unknown): SlipState | null {
  const parsed = raw as SlipState;
  if (!Array.isArray(parsed?.legs)) return null;
  const legs = parsed.legs.filter(
    (l) => l && Number.isInteger(l.pickId) && Number.isInteger(l.matchId) && asSport(l.sport) !== null && typeof l.description === "string",
  );
  return { legs, stake: Number(parsed.stake) || EMPTY.stake, totalOdds: parsed.totalOdds ?? {} };
}

const store = persistentStore<SlipState>("gorgo-v4.slip.v1", EMPTY, parseSlip);

export const slip = {
  get: store.get,
  has: (pickId: number) => store.get().legs.some((l) => l.pickId === pickId),
  add(leg: SlipLeg) {
    if (!slip.has(leg.pickId)) store.set({ ...store.get(), legs: [...store.get().legs, leg] });
  },
  remove(pickId: number) {
    store.set({ ...store.get(), legs: store.get().legs.filter((l) => l.pickId !== pickId) });
  },
  toggle(leg: SlipLeg) {
    if (slip.has(leg.pickId)) slip.remove(leg.pickId);
    else slip.add(leg);
  },
  replace(legs: SlipLeg[]) {
    store.set({ ...store.get(), legs, totalOdds: {} });
  },
  setStake(stake: number) {
    store.set({ ...store.get(), stake });
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
    store.set({ ...store.get(), legs: [], totalOdds: {} });
  },
};

export const useSlip = store.use;
