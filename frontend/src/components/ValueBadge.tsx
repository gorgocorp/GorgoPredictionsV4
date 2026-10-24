import type { LegValue } from "../lib/oddsInput";

/** Etiqueta de quién ve valor en el momio de tu casa (boleto y Calculadora Caliente). */
export const VALUE_LABELS: Record<LegValue, { label: string; className: string; title: string }> = {
  value: { label: "Valor", className: "badge-won", title: "Tu casa paga más que el momio justo del modelo y del mercado" },
  model_only: {
    label: "Sólo el modelo",
    className: "badge-warn",
    title: "El modelo ve valor y el mercado no: cuando no coinciden, el resultado suele quedar más cerca del mercado",
  },
  market_only: {
    label: "Sólo el mercado",
    className: "badge-neutral",
    title: "Tu casa paga más que el momio justo del mercado, pero el modelo no ve valor",
  },
  none: { label: "Sin valor", className: "badge-neutral", title: "Tu casa paga menos que el momio justo del modelo y del mercado" },
  no_market: {
    label: "Sin mercado",
    className: "badge-neutral",
    title: "Ninguna casa cotiza este mercado completo: sólo está la opinión del modelo",
  },
};

export function ValueBadge({ value }: { value: LegValue }) {
  const v = VALUE_LABELS[value];
  return (
    <span className={`badge ${v.className}`} title={v.title}>
      {v.label}
    </span>
  );
}
