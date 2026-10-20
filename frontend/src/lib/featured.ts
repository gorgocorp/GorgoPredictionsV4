import type { FeaturedLeg, FeaturedParlay, FeaturedWindow } from "./api";
import { bestBookOdd } from "./books";
import type { SlipLeg } from "./slip";

/** Lo que se promete de una pierna destacada: la menor entre el modelo y el mercado. */
export function legProbability(leg: Pick<FeaturedLeg, "p_model" | "p_market">): number {
  return leg.p_market === null ? leg.p_model : Math.min(leg.p_model, leg.p_market);
}

export type WindowStatus = "published" | "upcoming" | "missing";

/**
 * Estado de un destacado: publicado, por publicar (aún no llega su hora) o sin publicar ya pasada su hora (el sistema
 * lo arma en su primera corrida desde esa hora y sólo si hay al menos dos piernas que cumplan las reglas).
 */
export function windowStatus(w: FeaturedWindow, now: number = Date.now()): WindowStatus {
  if (w.parlays.length > 0) return "published";
  return new Date(w.publish_at).getTime() > now ? "upcoming" : "missing";
}

/** Un parlay se puede cargar al boleto mientras no empiece ninguno de sus partidos. */
export function canLoad(p: FeaturedParlay, now: number = Date.now()): boolean {
  return p.legs.every((l) => new Date(l.starts_at).getTime() > now);
}

/** Precio a mostrar de una pierna: el de la casa del sistema o, si no la cotiza, el mejor de las otras casas. */
export function legPrice(leg: FeaturedLeg): { odd: number; book: string | null } | null {
  if (leg.odd) return { odd: leg.odd, book: null };
  const other = bestBookOdd(leg.book_odds);
  return other ? { odd: other.odd, book: other.book } : null;
}

export function toSlipLegs(p: FeaturedParlay): SlipLeg[] {
  return p.legs.map((l) => ({
    pickId: l.pick_id,
    sport: l.sport,
    matchId: l.match_id,
    date: l.date,
    matchup: l.matchup,
    description: l.description,
    pModel: l.p_model,
    odd: l.odd,
    bookOdds: l.book_odds,
  }));
}

/** Texto para copiar: encabezado y una línea por pierna con su precio. */
export function copyText(label: string, p: FeaturedParlay, bookmaker: string): string {
  const head = `${label} · ${p.n_legs} piernas · prob. ${(p.probability * 100).toFixed(1)}%${p.odd ? ` · momio ${bookmaker} ${p.odd.toFixed(2)}` : ""}`;
  const lines = p.legs.map((l, i) => {
    const price = legPrice(l);
    const priceText = price ? ` @ ${price.odd.toFixed(2)}${price.book ? ` (${price.book})` : ""}` : "";
    return `${i + 1}. ${l.matchup} — ${l.description}${priceText}`;
  });
  return [head, ...lines].join("\n");
}

const dayMonthFmt = new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "long" });
const dayFmt = new Intl.DateTimeFormat("es-MX", { day: "numeric" });

/** "2026-10-19", "2026-10-25" -> "19 al 25 de octubre"; entre meses, "29 de septiembre al 5 de octubre". */
export function rangeText(start: string, end: string): string {
  const at = (iso: string) => {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d, 12);
  };
  const [a, b] = [at(start), at(end)];
  const first = a.getMonth() === b.getMonth() ? dayFmt.format(a) : dayMonthFmt.format(a);
  return `${first} al ${dayMonthFmt.format(b)}`;
}
