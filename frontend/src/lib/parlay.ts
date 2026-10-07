export interface ParlayInput {
  /** Partido común (core.matches): único aunque el boleto mezcle deportes. */
  matchId: number;
  pModel: number;
  odd: number | null;
}

export interface ParlaySummary {
  legs: number;
  probability: number;
  fairOdd: number;
  /** Momio combinado de la casa; null si alguna pierna no tiene momio. */
  odd: number | null;
  /** Valor esperado por unidad apostada: p·momio − 1. */
  ev: number | null;
  /** Partidos con más de una pierna (correlacionadas). */
  sameGame: number[];
}

export function summarize(legs: ParlayInput[]): ParlaySummary {
  const probability = legs.reduce((acc, l) => acc * l.pModel, 1);
  const priced = legs.length > 0 && legs.every((l) => l.odd !== null);
  const odd = priced ? legs.reduce((acc, l) => acc * (l.odd as number), 1) : null;
  const counts = new Map<number, number>();
  for (const l of legs) counts.set(l.matchId, (counts.get(l.matchId) ?? 0) + 1);
  return {
    legs: legs.length,
    probability,
    fairOdd: probability > 0 ? 1 / probability : Infinity,
    odd,
    ev: odd !== null ? probability * odd - 1 : null,
    sameGame: [...counts].filter(([, n]) => n > 1).map(([id]) => id),
  };
}

export function payout(stake: number, odd: number | null): number | null {
  return odd === null || !Number.isFinite(stake) || stake <= 0 ? null : stake * odd;
}
