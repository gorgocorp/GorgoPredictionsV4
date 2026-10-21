import type { ResultsKind } from "./api";

/** Ruta de la página pública de resultados: se ve con o sin sesión. */
export const RESULTS_PATH = "/resultados";

export const KIND_LABELS: Record<ResultsKind, string> = {
  daily: "Parlays del día",
  week: "Parlay de la semana",
  weekend: "Parlay de fin de semana",
};

export const KIND_SINGULAR: Record<ResultsKind, string> = {
  daily: "Parlay del día",
  week: "Parlay de la semana",
  weekend: "Parlay de fin de semana",
};

const monthFmt = new Intl.DateTimeFormat("es-MX", { month: "long", year: "numeric" });
const fullDateFmt = new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "long", year: "numeric" });

/** "2026-10" -> "Octubre de 2026". */
export function monthLabel(month: string): string {
  const [y, m] = month.split("-").map(Number);
  const text = monthFmt.format(new Date(y, m - 1, 15, 12));
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** "2026-10-19" -> "19 de octubre de 2026" (sin desfase de zona horaria). */
export function fullDate(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  return fullDateFmt.format(new Date(y, m - 1, d, 12));
}

/** Unidades a 1 por parlay: 0.463 -> "+0.46 u", -1 -> "-1.00 u". */
export function units(profit: number | null | undefined): string {
  if (profit === null || profit === undefined) return "—";
  const v = profit.toFixed(2);
  return profit > 0 ? `+${v} u` : `${v} u`;
}

/** Cuántos parlays no cuentan por ser de la regla anterior, en una frase (vacía si no hay). */
export function excludedText(n: number): string {
  if (n === 0) return "";
  return n === 1
    ? "No cuenta 1 parlay del día que se armó antes de ese cambio, con la regla anterior."
    : `No cuentan ${n} parlays del día que se armaron antes de ese cambio, con la regla anterior.`;
}
