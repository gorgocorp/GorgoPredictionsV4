const timeFmt = new Intl.DateTimeFormat("es-MX", { hour: "2-digit", minute: "2-digit" });
const dateFmt = new Intl.DateTimeFormat("es-MX", { weekday: "long", day: "numeric", month: "long" });
const relFmt = new Intl.RelativeTimeFormat("es-MX", { numeric: "auto" });
const dateTimeFmt = new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

/** Fecha y hora local corta: "6 oct, 12:15 a.m.". */
export function dateTime(iso: string): string {
  return dateTimeFmt.format(new Date(iso));
}

export function pct(p: number | null | undefined, digits = 0): string {
  if (p === null || p === undefined || Number.isNaN(p)) return "—";
  return `${(p * 100).toFixed(digits)}%`;
}

export function signedPct(p: number | null | undefined, digits = 1): string {
  if (p === null || p === undefined) return "—";
  const v = (p * 100).toFixed(digits);
  return p > 0 ? `+${v}%` : `${v}%`;
}

/** Diferencia de probabilidades en puntos porcentuales: 0.012 -> "+1.2 pts". */
export function signedPts(p: number | null | undefined, digits = 1): string {
  if (p === null || p === undefined) return "—";
  const v = (p * 100).toFixed(digits);
  return p > 0 ? `+${v} pts` : `${v} pts`;
}

/** "Bet365, 1xBet o Pinnacle". */
export function orList(items: string[]): string {
  return new Intl.ListFormat("es-MX", { type: "disjunction" }).format(items);
}

export function american(decimal: number): string {
  if (decimal >= 2) return `+${Math.round((decimal - 1) * 100)}`;
  return `${Math.round(-100 / (decimal - 1))}`;
}

export function odds(decimal: number | null | undefined): string {
  if (!decimal || !Number.isFinite(decimal)) return "—";
  return `${decimal.toFixed(2)} (${american(decimal)})`;
}

export function money(amount: number): string {
  return amount.toLocaleString("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 2 });
}

export function localTime(iso: string): string {
  return timeFmt.format(new Date(iso));
}

/** "2026-10-20" -> "Martes, 20 de octubre" (sin desfase de zona horaria). */
export function longDate(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  const text = dateFmt.format(new Date(y, m - 1, d, 12));
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function relativeTime(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "nunca";
  const minutes = Math.round((new Date(iso).getTime() - now) / 60000);
  if (Math.abs(minutes) < 60) return relFmt.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 48) return relFmt.format(hours, "hour");
  return relFmt.format(Math.round(hours / 24), "day");
}

const shortDayFmt = new Intl.DateTimeFormat("es-MX", { weekday: "short", day: "numeric" });

/** "2026-10-09" -> "vie 9". */
export function shortDay(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  return shortDayFmt.format(new Date(y, m - 1, d, 12)).replace(".", "").replace(",", "");
}

/** Día de la semana de una fecha ISO: 0 = domingo … 6 = sábado. */
export function weekday(isoDate: string): number {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(y, m - 1, d, 12).getDay();
}

/** Próximo fin de semana (viernes a domingo) visto desde `today`; si ya es fin de semana, desde hoy. */
export function weekendRange(today: string): { desde: string; hasta: string } {
  const dow = weekday(today);
  if (dow === 0) return { desde: today, hasta: today };
  if (dow === 5 || dow === 6) return { desde: today, hasta: shiftDate(today, 7 - dow) };
  return { desde: shiftDate(today, 5 - dow), hasta: shiftDate(today, 7 - dow) };
}

export function shiftDate(isoDate: string, days: number): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + days));
  return dt.toISOString().slice(0, 10);
}

/** Nombre corto para espacios estrechos: quita prefijos y sufijos comunes ("FC", "Club", "CF"). */
export function shortTeam(name: string): string {
  const cleaned = name
    .replace(/^(FC|CF|AC|AS|SC|SL|RC|RCD|CD|CA|SS|SSC|US|AFC|1\. FC|Club)\s+/i, "")
    .replace(/\s+(FC|CF|SC|AC|FK|SK|UANL|UNAM|de Fútbol)$/i, "");
  return cleaned.length > 16 ? cleaned.split(" ").slice(0, 2).join(" ") : cleaned;
}

/** Última palabra del nombre ("Boston Celtics" -> "Celtics"), como se nombra a los equipos NBA. */
export function lastWord(name: string): string {
  const parts = name.split(" ");
  return parts[parts.length - 1];
}
