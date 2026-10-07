import { describe, expect, it } from "vitest";
import { american } from "./format";
import { payout, summarize } from "./parlay";

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
