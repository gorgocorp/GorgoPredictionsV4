import { describe, expect, it } from "vitest";
import { american } from "./format";
import { payout, summarize, summarizeSingles } from "./parlay";

describe("summarize", () => {
  it("multiplica probabilidades y momios", () => {
    const s = summarize([
      { matchId: 1, pModel: 0.8, odd: 1.3 },
      { matchId: 2, pModel: 0.7, odd: 1.5 },
    ]);
    expect(s.probability).toBeCloseTo(0.56);
    expect(s.fairOdd).toBeCloseTo(1 / 0.56);
    expect(s.odd).toBeCloseTo(1.95);
    expect(s.ev).toBeCloseTo(0.56 * 1.95 - 1);
    expect(s.sameGame).toEqual([]);
  });

  it("sin momio en alguna pierna no hay momio combinado ni EV", () => {
    const s = summarize([
      { matchId: 1, pModel: 0.8, odd: 1.3 },
      { matchId: 2, pModel: 0.7, odd: null },
    ]);
    expect(s.odd).toBeNull();
    expect(s.ev).toBeNull();
  });

  it("detecta piernas del mismo partido", () => {
    const s = summarize([
      { matchId: 1, pModel: 0.8, odd: null },
      { matchId: 1, pModel: 0.7, odd: null },
      { matchId: 2, pModel: 0.7, odd: null },
    ]);
    expect(s.sameGame).toEqual([1]);
  });
});

describe("payout y momios americanos", () => {
  it("calcula el pago", () => {
    expect(payout(100, 2.5)).toBe(250);
    expect(payout(0, 2.5)).toBeNull();
    expect(payout(100, null)).toBeNull();
  });

  it("convierte decimal a americano", () => {
    expect(american(2.5)).toBe("+150");
    expect(american(1.5)).toBe("-200");
    expect(american(2.0)).toBe("+100");
  });
});

describe("summarizeSingles", () => {
  it("suma (no multiplica): cada apuesta se gana o se pierde por separado", () => {
    const s = summarizeSingles([
      { pModel: 0.8, odd: 1.3, stake: 100 },
      { pModel: 0.6, odd: 2.0, stake: 50 },
    ]);
    expect(s.bets).toBe(2);
    expect(s.staked).toBe(150);
    expect(s.expectedWins).toBeCloseTo(1.4);
    expect(s.payoutAll).toBeCloseTo(130 + 100);
    expect(s.expectedProfit).toBeCloseTo(100 * (0.8 * 1.3 - 1) + 50 * (0.6 * 2 - 1));
  });

  it("sin momio en alguna no hay pago ni ganancia esperada", () => {
    const s = summarizeSingles([
      { pModel: 0.8, odd: 1.3, stake: 100 },
      { pModel: 0.6, odd: null, stake: 50 },
    ]);
    expect(s.payoutAll).toBeNull();
    expect(s.expectedProfit).toBeNull();
    expect(s.staked).toBe(150);
  });
});
