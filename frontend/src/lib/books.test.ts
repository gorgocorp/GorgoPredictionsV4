import { describe, expect, it } from "vitest";
import type { Leg } from "./api";
import { oddFor, withPrices } from "./books";

const leg = (overrides: Partial<Leg>): Leg => ({
  id: 1,
  sport: "nba",
  match_id: 1,
  market: "ml",
  side: "home",
  line: null,
  team: null,
  stat: null,
  player_id: null,
  player_name: null,
  description: "Gana Hornets",
  p_model: 0.66,
  odd: 1.54,
  bookmaker: "Bet365",
  p_market: null,
  hits_10: null,
  games_10: null,
  hits_25: null,
  games_25: null,
  result: null,
  evaluated_at: "2026-10-06T00:00:00Z",
  player_status: null,
  book_odds: { Bet365: 1.54, "1xBet": 1.48 },
  ...overrides,
});

describe("momios por casa", () => {
  it("busca la casa sin distinguir mayúsculas", () => {
    expect(oddFor({ Bet365: 1.54, "1xBet": 1.48 }, "1XBET")).toBe(1.48);
    expect(oddFor({ Bet365: 1.54 }, "Caliente")).toBeNull();
    expect(oddFor(null, "1xBet")).toBeNull();
  });

  it("con la casa del sistema no cambia nada; con otra usa su momio o ninguno", () => {
    const legs = [leg({}), leg({ id: 2, book_odds: { Bet365: 2.1 } })];
    expect(withPrices(legs, "Bet365", "Bet365")).toBe(legs);
    expect(withPrices(legs, "1xBet", "Bet365").map((l) => l.odd)).toEqual([1.48, null]);
    expect(withPrices(legs, "1xBet", "Bet365")[0].bookmaker).toBe("1xBet");
  });

  it("funciona igual con piernas de fútbol", () => {
    const futbol = [leg({ sport: "futbol", market: "1x2", league_id: 39, book_odds: { Bet365: 1.8, "1xBet": 1.86 } })];
    expect(withPrices(futbol, "1xBet", "Bet365").map((l) => l.odd)).toEqual([1.86]);
  });
});
