import type { ParlayMode } from "./api";

/** Nombre de cada tipo de parlay del sistema (largo para títulos, corto para tablas y filtros). */
export const PARLAY_MODES: Record<ParlayMode, { label: string; short: string }> = {
  prob: { label: "Máxima probabilidad", short: "Máx. probabilidad" },
  ev: { label: "Máximo valor", short: "Máx. valor" },
  week: { label: "Parlay de la semana", short: "De la semana" },
  weekend: { label: "Parlay de fin de semana", short: "Fin de semana" },
};
