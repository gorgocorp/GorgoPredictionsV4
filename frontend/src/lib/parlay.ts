export interface ParlayInput {
  /** Partido común (core.matches): único aunque el boleto mezcle deportes. */
  matchId: number;
  pModel: number;
  /** Probabilidad sin comisión del mercado; null o sin dato si no la hay. */
  pMarket?: number | null;
  odd: number | null;
}

/** Producto de las probabilidades del mercado; null si a alguna pierna le falta. */
function marketProduct(legs: { pMarket?: number | null }[]): number | null {
  if (legs.length === 0 || legs.some((l) => l.pMarket == null)) return null;
  return legs.reduce((acc, l) => acc * (l.pMarket as number), 1);
}

export interface ParlaySummary {
  legs: number;
  probability: number;
  /** Probabilidad de acertar todo según el mercado; null si a alguna pierna le falta. */
  marketProbability: number | null;
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
    marketProbability: marketProduct(legs),
    fairOdd: probability > 0 ? 1 / probability : Infinity,
    odd,
    ev: odd !== null ? probability * odd - 1 : null,
    sameGame: [...counts].filter(([, n]) => n > 1).map(([id]) => id),
  };
}

export function payout(stake: number, odd: number | null): number | null {
  return odd === null || !Number.isFinite(stake) || stake <= 0 ? null : stake * odd;
}

export interface SingleInput {
  pModel: number;
  /** Probabilidad sin comisión del mercado; null o sin dato si no la hay. */
  pMarket?: number | null;
  /** Momio de la casa (decimal); null si falta. */
  odd: number | null;
  stake: number;
}

export interface SinglesSummary {
  bets: number;
  staked: number;
  /** Cuántas espera acertar el modelo. */
  expectedWins: number;
  /** Cuántas espera acertar el mercado; null si a alguna le falta su probabilidad. */
  expectedWinsMarket: number | null;
  /** Lo que regresa la casa si se aciertan todas; null si falta algún momio. */
  payoutAll: number | null;
  /** Ganancia esperada según el modelo, Σ monto·(p·momio − 1); null si falta algún momio. */
  expectedProfit: number | null;
  /** Lo mismo con la probabilidad del mercado; null si falta algún momio o alguna probabilidad del mercado. */
  expectedProfitMarket: number | null;
}

/** Apuestas individuales: cada pierna se gana o se pierde por separado, así que se suman (no se multiplican). */
export function summarizeSingles(legs: SingleInput[]): SinglesSummary {
  const priced = legs.length > 0 && legs.every((l) => l.odd !== null);
  const withMarket = legs.length > 0 && legs.every((l) => l.pMarket != null);
  return {
    bets: legs.length,
    staked: legs.reduce((acc, l) => acc + l.stake, 0),
    expectedWins: legs.reduce((acc, l) => acc + l.pModel, 0),
    expectedWinsMarket: withMarket ? legs.reduce((acc, l) => acc + (l.pMarket as number), 0) : null,
    payoutAll: priced ? legs.reduce((acc, l) => acc + l.stake * (l.odd as number), 0) : null,
    expectedProfit: priced ? legs.reduce((acc, l) => acc + l.stake * (l.pModel * (l.odd as number) - 1), 0) : null,
    expectedProfitMarket:
      priced && withMarket ? legs.reduce((acc, l) => acc + l.stake * ((l.pMarket as number) * (l.odd as number) - 1), 0) : null,
  };
}
