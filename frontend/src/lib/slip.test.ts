import { describe, expect, it } from "vitest";
import { parseSlip, slip, type SlipLeg } from "./slip";

const leg: SlipLeg = {
  pickId: 1,
  sport: "nba",
  matchId: 10,
  date: "2026-10-06",
  matchup: "Nets @ Hornets",
  description: "Gana Hornets",
  pModel: 0.66,
  odd: 1.54,
  bookOdds: { Bet365: 1.54, "1xBet": 1.48 },
};

describe("boleto", () => {
  it("cada casa conserva los momios que escribiste", () => {
    slip.replace([leg]);
    slip.setLegOdd(1, "Caliente", "-182");
    slip.setLegOdd(1, " 1XBET ", "1.50");
    slip.setTotalOdd("Caliente", "+1200");
    expect(slip.get().legs[0].typedOdds).toEqual({ caliente: "-182", "1xbet": "1.50" });
    expect(slip.get().totalOdds).toEqual({ caliente: "+1200" });

    slip.replace([leg]);
    expect(slip.get().totalOdds).toEqual({});
    slip.clear();
    expect(slip.get()).toMatchObject({ legs: [], totalOdds: {} });
  });

  it("mezcla deportes y no repite una pierna", () => {
    const futbol: SlipLeg = { ...leg, pickId: 2, sport: "futbol", matchId: 20, matchup: "América vs Toluca", description: "Gana local" };
    slip.replace([]);
    slip.add(leg);
    slip.add(futbol);
    slip.add(leg);
    expect(slip.get().legs.map((l) => [l.sport, l.pickId])).toEqual([
      ["nba", 1],
      ["futbol", 2],
    ]);
    slip.toggle(leg);
    expect(slip.has(1)).toBe(false);
    slip.clear();
  });

  it("al leer lo guardado descarta piernas sin deporte o sin partido (otra versión)", () => {
    const legacy = { pickId: 3, gameId: 5, date: "2026-10-06", matchup: "x", description: "y", pModel: 0.6, odd: null };
    const parsed = parseSlip({ legs: [leg, legacy], stake: "50" });
    expect(parsed?.legs).toEqual([leg]);
    expect(parsed?.stake).toBe(50);
    expect(parseSlip({ nada: true })).toBeNull();
  });
});
