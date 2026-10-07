import { FUTBOL } from "../sports/futbol/config";
import { NBA } from "../sports/nba/config";
import type { SportKey, SportMeta } from "./api";

export interface MarketOption {
  value: string;
  label: string;
  help: string;
}

export interface StatOption {
  value: string;
  label: string;
  /** Nombre corto para el resumen de la configuración. */
  short: string;
}

export interface Badge {
  label: string;
  className: string;
  title: string;
}

/**
 * Lo que cambia entre deportes en las piezas comunes (piernas, parlays, preferencias, encabezado).
 * Cada deporte define el suyo en src/sports/<deporte>/config.ts.
 */
export interface SportConfig {
  key: SportKey;
  label: string;
  /** Mercados que el usuario puede activar en Personalizar (en este orden también en los filtros). */
  markets: MarketOption[];
  /** Nombre corto de cada mercado (tabla de piernas, rendimiento). */
  marketLabels: Record<string, string>;
  /** Estadísticas (o grupos de estadísticas) de jugador que el usuario puede activar. */
  stats: StatOption[];
  /** Grupo de `stats` al que pertenece la estadística de una pierna de jugador. */
  statGroup: (stat: string) => string | undefined;
  /** Título de las estadísticas de jugador en Personalizar. */
  statsTitle: string;
  /** Prefijo de las estadísticas de jugador en el resumen de la configuración. */
  statsPrefix: string;
  /** Partido con nombres cortos: "Nets @ Hornets" o "América vs Toluca". */
  matchup: (home: string, away: string) => string;
  /** De dónde sale que un jugador esté en duda (Personalizar). */
  questionableSource: string;
  /** Etiqueta de una pierna según el estado del jugador; null si no lleva. */
  playerBadge: (status: string) => Badge | null;
  /** Título de la columna de aciertos recientes. */
  hitsTitle: string;
  /** Noticias que el modelo no conoce (aviso de ventaja grande sobre el mercado). */
  newsExamples: string;
  /** Tareas de ingesta que marcan "Datos" en el encabezado (la primera que exista). */
  dataJobs: string[];
  /** Líneas propias del deporte en el detalle de la sincronización. */
  syncLines: (meta: SportMeta) => string[];
}

export const SPORT_KEYS: SportKey[] = ["nba", "futbol"];

export const SPORTS: Record<SportKey, SportConfig> = { nba: NBA, futbol: FUTBOL };

export function asSport(value: string | null | undefined): SportKey | null {
  return value === "nba" || value === "futbol" ? value : null;
}
