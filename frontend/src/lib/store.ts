import { useSyncExternalStore } from "react";

export interface PersistentStore<T> {
  get: () => T;
  set: (next: T) => void;
  subscribe: (listener: () => void) => () => void;
  use: () => T;
}

/**
 * Estado global pequeño guardado en localStorage (preferencias del navegador, no secretos).
 * Si el almacenamiento no está disponible, el estado vive sólo en memoria.
 */
export function persistentStore<T>(key: string, fallback: T, parse: (raw: unknown) => T | null): PersistentStore<T> {
  let state = fallback;
  if (typeof window !== "undefined") {
    try {
      const raw = localStorage.getItem(key);
      if (raw) state = parse(JSON.parse(raw)) ?? fallback;
    } catch {
      state = fallback;
    }
  }
  const listeners = new Set<() => void>();

  const store: PersistentStore<T> = {
    get: () => state,
    set(next) {
      state = next;
      try {
        localStorage.setItem(key, JSON.stringify(state));
      } catch {
        /* sin almacenamiento */
      }
      listeners.forEach((l) => l());
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    use: () => useSyncExternalStore(store.subscribe, store.get, () => fallback),
  };
  return store;
}
