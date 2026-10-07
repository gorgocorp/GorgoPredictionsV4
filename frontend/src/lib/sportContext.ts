import { useEffect } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import type { SportKey } from "./api";
import { asSport } from "./sports";
import { persistentStore } from "./store";

/** Último deporte elegido (lo lee también index.html antes de pintar, para el color de acento). */
const sportStore = persistentStore<SportKey>("gorgo.sport", "futbol", (raw) => asSport(raw as string));

export const lastSport = sportStore.get;

export function sportFromPath(pathname: string): SportKey | null {
  return asSport(pathname.split("/")[1]);
}

/**
 * Deporte de la página actual: el de la ruta (/nba, /futbol…) o el de ?deporte= en Historial y
 * Rendimiento. `context` es null en páginas que mezclan deportes (Mis apuestas, Historial con "Todos").
 */
export function useSportContext(): { context: SportKey | null; sport: SportKey } {
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const stored = sportStore.use();
  const fromParam = asSport(params.get("deporte"));
  const context =
    sportFromPath(pathname) ??
    (pathname === "/rendimiento" ? (fromParam ?? stored) : pathname === "/historial" ? fromParam : null);
  return { context, sport: context ?? stored };
}

/** Recuerda el deporte elegido y aplica su color de acento. */
export function useSportTheme(): void {
  const { context, sport } = useSportContext();
  useEffect(() => {
    if (context && context !== sportStore.get()) sportStore.set(context);
  }, [context]);
  useEffect(() => {
    document.documentElement.dataset.sport = sport;
  }, [sport]);
}
