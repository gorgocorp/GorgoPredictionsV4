import { useMemo } from "react";
import type { SportKey } from "./api";
import { SPORTS } from "./sports";
import { persistentStore } from "./store";

export const SIZES = [2, 3, 4, 5, 6, 7, 8];

/** Qué juega el usuario en un deporte (cada deporte guarda las suyas). */
export interface SportPreferences {
  /** Mercados que juega el usuario (valores de SportConfig.markets). */
  markets: string[];
  /** Estadísticas (o grupos) de jugador que juega (valores de SportConfig.stats). */
  stats: string[];
  /** Ligas que juega el usuario; vacío = todas (sólo fútbol). */
  leagues: number[];
  /** Probabilidad mínima del modelo por pierna. */
  minProb: number;
  /** Momio mínimo por pierna (de la casa, o justo si no hay momio). */
  minOdd: number;
  /** Sólo piernas con momio de la casa. */
  onlyPriced: boolean;
  /** Tamaños de parlay a mostrar. */
  sizes: number[];
  /** Incluir props de jugadores "en duda" en los parlays (si no juegan, la pierna se anula). */
  includeQuestionable: boolean;
}

/** Lo del usuario que no depende del deporte: dónde apuesta y con qué momios compara. */
export interface CommonPreferences {
  /** Casa donde apuesta el usuario (sus momios se escriben en el boleto, o se llenan solos si está en la API). */
  myBook: string;
  /** Casa de la API con cuyos momios se comparan piernas y parlays ("" = la del sistema). */
  priceBook: string;
}

export type Preferences = SportPreferences & CommonPreferences;

const DEFAULT_COMMON: CommonPreferences = { myBook: "Caliente", priceBook: "" };

function sportDefaults(sport: SportKey): SportPreferences {
  return {
    markets: SPORTS[sport].markets.map((m) => m.value),
    stats: SPORTS[sport].stats.map((s) => s.value),
    leagues: [],
    minProb: 0.6,
    minOdd: 1.15,
    onlyPriced: false,
    sizes: SIZES,
    includeQuestionable: false,
  };
}

const DEFAULT_SPORT: Record<SportKey, SportPreferences> = { nba: sportDefaults("nba"), futbol: sportDefaults("futbol") };

/** Configuración estándar: la misma con la que el sistema registra y mide sus parlays. */
export function defaultPreferences(sport: SportKey): Preferences {
  return { ...DEFAULT_SPORT[sport], ...DEFAULT_COMMON };
}

const sameSet = <T,>(a: T[], b: T[]) => a.length === b.length && a.every((x) => b.includes(x));

export function isDefault(p: Preferences, sport: SportKey): boolean {
  const d = DEFAULT_SPORT[sport];
  return (
    sameSet(p.markets, d.markets) &&
    sameSet(p.stats, d.stats) &&
    p.leagues.length === 0 &&
    p.minProb === d.minProb &&
    p.minOdd === d.minOdd &&
    p.onlyPriced === d.onlyPriced &&
    sameSet(p.sizes, d.sizes) &&
    p.includeQuestionable === d.includeQuestionable &&
    p.priceBook === DEFAULT_COMMON.priceBook
  );
}

function parseSport(sport: SportKey) {
  return (raw: unknown): SportPreferences | null => {
    if (!raw || typeof raw !== "object") return null;
    const r = raw as Partial<SportPreferences>;
    const d = DEFAULT_SPORT[sport];
    const markets = (r.markets ?? []).filter((m) => d.markets.includes(m));
    const stats = (r.stats ?? []).filter((s) => d.stats.includes(s));
    const sizes = (r.sizes ?? []).filter((n) => SIZES.includes(n));
    const leagues = (r.leagues ?? []).filter((n) => Number.isInteger(n));
    return {
      markets: markets.length ? markets : d.markets,
      stats: stats.length ? stats : d.stats,
      leagues,
      minProb: typeof r.minProb === "number" ? r.minProb : d.minProb,
      minOdd: typeof r.minOdd === "number" ? r.minOdd : d.minOdd,
      onlyPriced: Boolean(r.onlyPriced),
      sizes: sizes.length ? sizes : d.sizes,
      includeQuestionable: Boolean(r.includeQuestionable),
    };
  };
}

function parseCommon(raw: unknown): CommonPreferences | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Partial<CommonPreferences>;
  return {
    myBook: typeof r.myBook === "string" && r.myBook.trim() ? r.myBook : DEFAULT_COMMON.myBook,
    priceBook: typeof r.priceBook === "string" ? r.priceBook : DEFAULT_COMMON.priceBook,
  };
}

const sportStores = {
  nba: persistentStore<SportPreferences>("gorgo-v4.prefs.nba.v1", DEFAULT_SPORT.nba, parseSport("nba")),
  futbol: persistentStore<SportPreferences>("gorgo-v4.prefs.futbol.v1", DEFAULT_SPORT.futbol, parseSport("futbol")),
};
const commonStore = persistentStore<CommonPreferences>("gorgo-v4.prefs.common.v1", DEFAULT_COMMON, parseCommon);

export const preferences = {
  get: (sport: SportKey): Preferences => ({ ...sportStores[sport].get(), ...commonStore.get() }),
  /** Guarda cambios: lo del deporte en su configuración y la casa del usuario en la común. */
  update(sport: SportKey, changes: Partial<Preferences>) {
    const { myBook, priceBook, ...rest } = changes;
    if (Object.keys(rest).length > 0) sportStores[sport].set({ ...sportStores[sport].get(), ...rest });
    if (myBook !== undefined || priceBook !== undefined) {
      commonStore.set({ myBook: myBook ?? commonStore.get().myBook, priceBook: priceBook ?? commonStore.get().priceBook });
    }
  },
  /** Vuelve a la configuración estándar del deporte; la casa donde apuestas no cambia. */
  reset(sport: SportKey) {
    sportStores[sport].set(DEFAULT_SPORT[sport]);
    commonStore.set({ ...commonStore.get(), priceBook: DEFAULT_COMMON.priceBook });
  },
};

/** Casa del usuario y casa de comparación (las mismas en los dos deportes). */
export const commonPreferences = {
  get: commonStore.get,
  update: (changes: Partial<CommonPreferences>) => commonStore.set({ ...commonStore.get(), ...changes }),
};

export const useCommonPreferences = commonStore.use;

export function usePreferences(sport: SportKey): Preferences {
  const own = sportStores[sport].use();
  const common = commonStore.use();
  return useMemo(() => ({ ...own, ...common }), [own, common]);
}

/** ¿La pierna pertenece a una liga, mercado (y estadística) que el usuario juega en su deporte? */
export function isAllowed(leg: { sport: SportKey; market: string; stat: string | null; league_id?: number }, p: Preferences): boolean {
  if (p.leagues.length > 0 && leg.league_id !== undefined && !p.leagues.includes(leg.league_id)) return false;
  if (!p.markets.includes(leg.market)) return false;
  if (leg.market === "player") {
    const group = leg.stat ? SPORTS[leg.sport].statGroup(leg.stat) : undefined;
    return group !== undefined && p.stats.includes(group);
  }
  return true;
}
