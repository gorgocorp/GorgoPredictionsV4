import type { Leg } from "./api";

/** Momio de una casa de la API para una pierna (el nombre no distingue mayúsculas: "1XBET" = "1xBet"). */
export function oddFor(bookOdds: Record<string, number> | null | undefined, book: string): number | null {
  if (!bookOdds || !book.trim()) return null;
  const wanted = book.trim().toLowerCase();
  const key = Object.keys(bookOdds).find((k) => k.toLowerCase() === wanted);
  return key ? bookOdds[key] : null;
}

/** El mejor momio entre las casas de la API que cotizan la pierna (null si ninguna la cotiza). */
export function bestBookOdd(bookOdds: Record<string, number> | null | undefined): { book: string; odd: number } | null {
  let best: { book: string; odd: number } | null = null;
  for (const [book, odd] of Object.entries(bookOdds ?? {})) {
    if (!best || odd > best.odd) best = { book, odd };
  }
  return best;
}

/**
 * Piernas con `odd` = momio de la casa elegida para comparar. La casa del sistema (`primary`) ya
 * viene en `odd`; para otra casa se toma de `book_odds` (null si esa casa no la cotiza).
 */
export function withPrices(legs: Leg[], book: string, primary: string): Leg[] {
  if (book.toLowerCase() === primary.toLowerCase()) return legs;
  return legs.map((l) => ({ ...l, odd: oddFor(l.book_odds, book), bookmaker: book }));
}
