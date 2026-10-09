import { describe, expect, it } from "vitest";
import type { Leg, SportKey } from "./api";
import { buildParlays, buildWhole, isEligible, parlayResult } from "./builder";
import { defaultPreferences, isAllowed, isDefault, type Preferences } from "./preferences";

let nextId = 1;
function legOf(sport: SportKey, overrides: Partial<Leg>): Leg {
  return {
    id: nextId++,
    sport,
    match_id: 1,
    ...(sport === "futbol" ? { league_id: 39 } : {}),
    market: "player",
    side: "over",
    line: sport === "nba" ? 19.5 : 0.5,
    team: null,
    stat: sport === "nba" ? "points" : "shots_on",
    player_id: 1,
    player_name: "X",
    description: "pierna",
    p_model: 0.7,
    odd: 1.5,
    bookmaker: null,
    p_market: null,
    hits_10: null,
    games_10: null,
    hits_25: null,
    games_25: null,
    result: null,
    evaluated_at: "2026-10-20T12:00:00Z",
    player_status: null,
    book_odds: null,
    ...overrides,
  };
}

const prefsOf = (sport: SportKey) => (changes: Partial<Preferences> = {}): Preferences => ({ ...defaultPreferences(sport), ...changes });

describe("fútbol", () => {
  const leg = (overrides: Partial<Leg>) => legOf("futbol", overrides);
  const prefs = prefsOf("futbol");

  describe("preferencias", () => {
    it("filtra por mercado y por estadística de jugador", () => {
      const p = prefs({ markets: ["total", "player"], stats: ["goals"] });
      expect(isAllowed(leg({ market: "total", stat: null }), p)).toBe(true);
      expect(isAllowed(leg({ market: "1x2", stat: null }), p)).toBe(false);
      expect(isAllowed(leg({ market: "player", stat: "goals" }), p)).toBe(true);
      expect(isAllowed(leg({ market: "player", stat: "shots" }), p)).toBe(false);
    });

    it("filtra por liga sólo si el usuario eligió alguna", () => {
      expect(isAllowed(leg({ league_id: 262 }), prefs())).toBe(true);
      expect(isAllowed(leg({ league_id: 262 }), prefs({ leagues: [39, 140] }))).toBe(false);
      expect(isAllowed(leg({ league_id: 39 }), prefs({ leagues: [39, 140] }))).toBe(true);
    });

    it("detecta la configuración estándar", () => {
      expect(isDefault(defaultPreferences("futbol"), "futbol")).toBe(true);
      expect(isDefault(prefs({ markets: ["total"] }), "futbol")).toBe(false);
      expect(isDefault(prefs({ leagues: [262] }), "futbol")).toBe(false);
    });
  });

  describe("isEligible", () => {
    it("respeta probabilidad y momio mínimos", () => {
      expect(isEligible(leg({ p_model: 0.55 }), prefs(), "prob")).toBe(false);
      expect(isEligible(leg({ p_model: 0.95 }), prefs(), "prob")).toBe(false); // tope 92%
      expect(isEligible(leg({ p_model: 0.7, odd: 1.1 }), prefs(), "prob")).toBe(false); // paga menos de 1.15
      expect(isEligible(leg({ p_model: 0.7, odd: null, book_odds: { "1xBet": 1.5 } }), prefs({ onlyPriced: true }), "prob")).toBe(false);
    });

    it("en modo valor exige momio y EV positivo", () => {
      expect(isEligible(leg({ p_model: 0.7, odd: null }), prefs(), "ev")).toBe(false);
      expect(isEligible(leg({ p_model: 0.7, odd: 1.3 }), prefs(), "ev")).toBe(false); // EV -9%
      expect(isEligible(leg({ p_model: 0.7, odd: 1.5 }), prefs(), "ev")).toBe(true);
    });

    it("sólo piernas que cotiza alguna casa; sin la casa elegida, el mínimo va contra el mejor de las otras", () => {
      expect(isEligible(leg({ p_model: 0.7, odd: null }), prefs(), "prob")).toBe(false); // ninguna casa la cotiza
      expect(isEligible(leg({ p_model: 0.7, odd: null, book_odds: { Pinnacle: 1.3, "1xBet": 1.25 } }), prefs(), "prob")).toBe(true);
      // La cotizan pero casi no paga, aunque su momio justo (1.18) sí pasaría.
      expect(isEligible(leg({ p_model: 0.85, odd: null, book_odds: { "1xBet": 1.07 } }), prefs(), "prob")).toBe(false);
      expect(isEligible(leg({ p_model: 0.7, odd: null, book_odds: { Pinnacle: 1.3 } }), prefs(), "ev")).toBe(false);
    });
  });

  describe("jugadores en duda", () => {
    it("se excluyen salvo que el usuario los incluya", () => {
      const doubtful = leg({ p_model: 0.7, player_status: "questionable" });
      expect(isEligible(doubtful, prefs(), "prob")).toBe(false);
      expect(isEligible(doubtful, prefs({ includeQuestionable: true }), "prob")).toBe(true);
      expect(isEligible(leg({ p_model: 0.7, player_status: "starter" }), prefs(), "prob")).toBe(true);
    });
  });

  describe("buildParlays", () => {
    const legs = [
      leg({ match_id: 1, p_model: 0.8, market: "total", stat: null }),
      leg({ match_id: 1, p_model: 0.85 }),
      leg({ match_id: 2, p_model: 0.75, market: "dc", stat: null }),
      leg({ match_id: 3, p_model: 0.65 }),
    ];

    it("una pierna por partido, las mejores primero", () => {
      const parlays = buildParlays(legs, prefs(), "prob");
      expect(parlays.map((p) => p.n)).toEqual([2, 3]);
      expect(parlays[1].legs.map((l) => l.p_model)).toEqual([0.85, 0.75, 0.65]);
      expect(parlays[1].probability).toBeCloseTo(0.85 * 0.75 * 0.65);
    });

    it("sin props usa la siguiente mejor pierna del partido", () => {
      const parlays = buildParlays(legs, prefs({ markets: ["1x2", "dc", "total", "team_total"] }), "prob");
      expect(parlays.map((p) => p.n)).toEqual([2]);
      expect(parlays[0].legs.map((l) => l.market)).toEqual(["total", "dc"]);
    });

    it("sólo los tamaños elegidos", () => {
      expect(buildParlays(legs, prefs({ sizes: [3] }), "prob").map((p) => p.n)).toEqual([3]);
    });
  });

  describe("buildWhole", () => {
    it("una pierna por cada partido con alguna elegible", () => {
      const legs = [
        leg({ match_id: 1, p_model: 0.8 }),
        leg({ match_id: 1, p_model: 0.7 }),
        leg({ match_id: 2, p_model: 0.75 }),
        leg({ match_id: 3, p_model: 0.65 }),
        leg({ match_id: 4, p_model: 0.4 }), // no llega al mínimo: ese partido queda fuera
      ];
      const whole = buildWhole(legs, prefs(), "prob");
      expect(whole?.n).toBe(3);
      expect(whole?.whole).toBe(true);
      expect(whole?.probability).toBeCloseTo(0.8 * 0.75 * 0.65);
      expect(buildWhole([leg({ match_id: 1 })], prefs(), "prob")).toBeNull();
    });
  });
});

describe("NBA", () => {
  const leg = (overrides: Partial<Leg>) => legOf("nba", overrides);
  const prefs = prefsOf("nba");

  describe("preferencias", () => {
    it("filtra por mercado y por estadística de jugador (los combinados van juntos)", () => {
      const p = prefs({ markets: ["total", "player"], stats: ["rebounds"] });
      expect(isAllowed(leg({ market: "total", stat: null }), p)).toBe(true);
      expect(isAllowed(leg({ market: "ml", stat: null }), p)).toBe(false);
      expect(isAllowed(leg({ market: "player", stat: "rebounds" }), p)).toBe(true);
      expect(isAllowed(leg({ market: "player", stat: "pra" }), p)).toBe(false);
      expect(isAllowed(leg({ market: "player", stat: "pra" }), prefs({ stats: ["combos"] }))).toBe(true);
    });

    it("detecta la configuración estándar", () => {
      expect(isDefault(defaultPreferences("nba"), "nba")).toBe(true);
      expect(isDefault(prefs({ markets: ["total"] }), "nba")).toBe(false);
    });
  });

  describe("isEligible", () => {
    it("respeta probabilidad y momio mínimos", () => {
      expect(isEligible(leg({ p_model: 0.55 }), prefs(), "prob")).toBe(false);
      expect(isEligible(leg({ p_model: 0.95 }), prefs(), "prob")).toBe(false); // tope 92%
      expect(isEligible(leg({ p_model: 0.7, odd: 1.1 }), prefs(), "prob")).toBe(false); // paga menos de 1.15
      expect(isEligible(leg({ p_model: 0.7, odd: null, book_odds: { "1xBet": 1.5 } }), prefs({ onlyPriced: true }), "prob")).toBe(false);
    });

    it("en modo valor exige momio y EV positivo", () => {
      expect(isEligible(leg({ p_model: 0.7, odd: null }), prefs(), "ev")).toBe(false);
      expect(isEligible(leg({ p_model: 0.7, odd: 1.3 }), prefs(), "ev")).toBe(false); // EV -9%
      expect(isEligible(leg({ p_model: 0.7, odd: 1.5 }), prefs(), "ev")).toBe(true);
    });
  });

  describe("jugadores en duda", () => {
    it("se excluyen salvo que el usuario los incluya", () => {
      const doubtful = leg({ p_model: 0.7, player_status: "questionable" });
      expect(isEligible(doubtful, prefs(), "prob")).toBe(false);
      expect(isEligible(doubtful, prefs({ includeQuestionable: true }), "prob")).toBe(true);
      expect(isEligible(leg({ p_model: 0.7, player_status: "probable" }), prefs(), "prob")).toBe(true);
    });
  });

  describe("buildParlays", () => {
    const legs = [
      leg({ match_id: 1, p_model: 0.8, market: "total", stat: null }),
      leg({ match_id: 1, p_model: 0.85 }),
      leg({ match_id: 2, p_model: 0.75, market: "spread", stat: null }),
      leg({ match_id: 3, p_model: 0.65 }),
    ];

    it("una pierna por partido, las mejores primero", () => {
      const parlays = buildParlays(legs, prefs(), "prob");
      expect(parlays.map((p) => p.n)).toEqual([2, 3]);
      expect(parlays[1].legs.map((l) => l.p_model)).toEqual([0.85, 0.75, 0.65]);
      expect(parlays[1].probability).toBeCloseTo(0.85 * 0.75 * 0.65);
    });

    it("sin props usa la siguiente mejor pierna del partido", () => {
      const parlays = buildParlays(legs, prefs({ markets: ["ml", "spread", "total", "team_total"] }), "prob");
      expect(parlays.map((p) => p.n)).toEqual([2]);
      expect(parlays[0].legs.map((l) => l.market)).toEqual(["total", "spread"]);
    });

    it("sólo los tamaños elegidos", () => {
      expect(buildParlays(legs, prefs({ sizes: [3] }), "prob").map((p) => p.n)).toEqual([3]);
    });
  });
});

describe("parlayResult", () => {
  it("pierde con una perdida, anula sólo si todo se anuló", () => {
    expect(parlayResult(["won", "lost", null])).toBe("lost");
    expect(parlayResult(["won", null])).toBeNull();
    expect(parlayResult(["won", "void"])).toBe("won");
    expect(parlayResult(["void", "void"])).toBe("void");
  });
});
