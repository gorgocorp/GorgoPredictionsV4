/**
 * Lee un momio escrito por el usuario: americano ("-120", "+145", "145") o decimal ("1.83").
 * Devuelve el momio decimal, o null si no es válido.
 */
export function parseOdds(input: string): number | null {
  const text = input.trim().replace(",", ".").replace(/\s+/g, "");
  if (!text) return null;
  const value = Number(text);
  if (!Number.isFinite(value)) return null;
  const signed = /^[+-]/.test(text);
  if (!signed && text.includes(".") && value > 1 && value < 100) return value; // decimal
  if (value <= -100) return 1 + 100 / -value; // americano negativo
  if (value >= 100) return 1 + value / 100; // americano positivo
  if (!signed && value > 1 && value < 100) return value; // decimal sin punto ("2")
  return null;
}

/** Probabilidad que le da la casa a un momio decimal (incluye su comisión). */
export function impliedProbability(decimal: number): number {
  return 1 / decimal;
}

export type Verdict = "suspicious" | "value" | "none";

/** Compara la probabilidad del modelo contra la de la casa (en puntos porcentuales). */
export function verdict(pModel: number, pBook: number): Verdict {
  const diff = (pModel - pBook) * 100;
  if (diff >= 10) return "suspicious";
  if (diff >= 2) return "value";
  return "none";
}
