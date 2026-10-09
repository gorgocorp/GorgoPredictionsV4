import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect } from "react";
import { api, ApiError, SESSION_EXPIRED, type Role, type Viewer } from "./api";
import { slip } from "./slip";

/**
 * Sesión de la cuenta. La cookie es httpOnly (el navegador no la deja leer): la sesión se conoce preguntando a
 * /api/auth/me. Toda la app vive dentro de una sesión; sin ella sólo se muestra "Entrar".
 */

const SESSION_KEY = ["session"];

export const PLAN_LABELS: Record<Role, string> = { admin: "Admin", subscriber: "Suscriptor", free: "Gratis" };

async function fetchViewer(): Promise<Viewer | null> {
  try {
    return await api.auth.me();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
}

/** Lo guardado en caché de una cuenta no se le muestra a otra. */
function forgetData(client: QueryClient): void {
  client.removeQueries({ predicate: (q) => q.queryKey[0] !== SESSION_KEY[0] });
}

/** La sesión actual (null = no hay). Si una petición responde 401, vuelve a null. */
export function useSessionQuery() {
  const client = useQueryClient();
  useEffect(() => {
    const expired = () => {
      forgetData(client);
      client.setQueryData(SESSION_KEY, null);
    };
    window.addEventListener(SESSION_EXPIRED, expired);
    return () => window.removeEventListener(SESSION_EXPIRED, expired);
  }, [client]);
  return useQuery({ queryKey: SESSION_KEY, queryFn: fetchViewer, staleTime: Infinity, refetchOnWindowFocus: true });
}

export function startSession(client: QueryClient, viewer: Viewer): void {
  forgetData(client);
  client.setQueryData(SESSION_KEY, viewer);
}

/** Salir: cierra la sesión en el servidor y vacía el boleto (en una computadora compartida no queda nada). */
export async function endSession(client: QueryClient): Promise<void> {
  try {
    await api.auth.logout();
  } finally {
    slip.clear();
    forgetData(client);
    client.setQueryData(SESSION_KEY, null);
  }
}

const ViewerContext = createContext<Viewer | null>(null);
export const ViewerProvider = ViewerContext.Provider;

/** Quién inició sesión (sólo dentro de la app con sesión). */
export function useViewer(): Viewer {
  const viewer = useContext(ViewerContext);
  if (!viewer) throw new Error("useViewer se usa dentro de ViewerProvider");
  return viewer;
}

export const isAdmin = (viewer: Viewer) => viewer.role === "admin";
