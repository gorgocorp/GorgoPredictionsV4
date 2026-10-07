import type { QueryClient } from "@tanstack/react-query";
import type { SportKey } from "./api";

/**
 * Llaves de React Query: lo de cada deporte empieza con su clave (["nba", "day", fecha], ["futbol", "slate", …]);
 * lo común no (["meta"], ["bets"], ["history", …], ["performance", …]).
 */

/** Tras recalcular o marcar una baja: vuelve a pedir partidos, piernas y planteles del deporte. */
export function invalidateSport(client: QueryClient, sport: SportKey): void {
  for (const key of ["day", "legs", "slate", "slate-legs", "roster"]) {
    client.invalidateQueries({ queryKey: [sport, key] });
  }
  client.invalidateQueries({ queryKey: ["meta"] });
}
