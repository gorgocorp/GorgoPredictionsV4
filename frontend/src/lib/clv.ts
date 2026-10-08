import type { ClvData } from "./api";
import { pct } from "./format";

/** Piernas con valor que no cuentan en el CLV y por qué: ["3 sin Pinnacle al cierre (…)", …]. */
export function clvExclusions(clv: ClvData): string[] {
  const { excluded: e } = clv;
  const n = (count: number) => count.toLocaleString("es-MX");
  const texts: string[] = [];
  if (e.no_close) texts.push(`${n(e.no_close)} sin lectura a ${clv.close_max_minutes} min o menos del inicio`);
  if (e.no_reference) texts.push(`${n(e.no_reference)} sin Pinnacle al cierre (no cotiza ese mercado o esa línea)`);
  if (e.short_window) {
    const published = e.short_window === 1 ? "publicada" : "publicadas";
    texts.push(`${n(e.short_window)} ${published} a menos de ${clv.min_window_hours} h del cierre`);
  }
  if (e.doubtful) {
    texts.push(`${n(e.doubtful)} con precio dudoso (a más de ${pct(clv.max_price_gap)} del precio justo al publicarse)`);
  }
  return texts;
}
