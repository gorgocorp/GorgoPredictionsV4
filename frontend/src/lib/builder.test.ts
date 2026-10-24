import { describe, expect, it } from "vitest";
import type { Leg, SportKey, SystemParlay } from "./api";
import { acceptFrom, buildParlays, buildWhole, fromSystem, isEligible, parlayAcceptFrom, parlayResult, promised } from "./builder";
import { defaultPreferences, isAllowed, isDefault, type Preferences } from "./preferences";

let nextId = 1;
/** Pierna de prueba; sin `p_market`, el mercado coincide con el modelo. */
function legOf(sport: SportKey, overrides: Partial<Leg>): Leg {
  const p_model = overrides.p_model ?? 0.7;
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
    p_model,
    odd: 1.5,
    bookmaker: null,
    p_market: p_model,
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

  describe("máxima probabilidad: escoge con el modelo y promete la menor entre modelo y mercado", () => {
    it("exige el mercado y que también esté entre el mínimo y el tope", () => {
      expect(isEligible(leg({ p_model: 0.8, p_market: null }), prefs(), "prob")).toBe(false);
      expect(isEligible(leg({ p_model: 0.8, p_market: 0.55 }), prefs(), "prob")).toBe(false);
      expect(isEligible(leg({ p_model: 0.8, p_market: 0.95 }), prefs(), "prob")).toBe(false);
      expect(isEligible(leg({ p_model: 0.8, p_market: 0.7 }), prefs(), "prob")).toBe(true);
      expect(isEligible(leg({ p_model: 0.8, p_market: 0.7 }), prefs({ minProb: 0.75 }), "prob")).toBe(false);
      // Máximo valor no lo necesita.
      expect(isEligible(leg({ p_model: 0.8, p_market: null }), prefs(), "ev")).toBe(true);
    });

    it("lo que se promete", () => {
      expect(promised(leg({ p_model: 0.88, p_market: 0.75 }), "prob")).toBe(0.75);
      expect(promised(leg({ p_model: 0.7, p_market: 0.8 }), "prob")).toBe(0.7);
      expect(promised(leg({ p_model: 0.7, p_market: null }), "prob")).toBe(0.7); // parlays registrados antes del cambio
      expect(promised(leg({ p_model: 0.88, p_market: 0.75 }), "ev")).toBe(0.88);
    });

    it("el orden es el del modelo y la probabilidad, el producto de lo prometido", () => {
      const legs = [
        leg({ match_id: 1, p_model: 0.88, p_market: 0.75, odd: 1.3 }),
        leg({ match_id: 2, p_model: 0.8, p_market: 0.85, odd: 1.2 }),
        leg({ match_id: 2, p_model: 0.78, p_market: 0.9, odd: 1.25 }), // mismo partido: el modelo la ve menos probable
        leg({ match_id: 3, p_model: 0.9, p_market: null, odd: 1.2 }), // sin mercado no entra
      ];
      const [two] = buildParlays(legs, prefs({ sizes: [2] }), "prob");
      expect(two.mode).toBe("prob");
      expect(two.legs.map((l) => l.match_id)).toEqual([1, 2]);
      expect(two.legs.map((l) => l.p_model)).toEqual([0.88, 0.8]);
      expect(two.probability).toBeCloseTo(0.75 * 0.8);
      expect(two.ev).toBeCloseTo(0.75 * 0.8 * 1.3 * 1.2 - 1);
      expect(buildWhole(legs, prefs(), "prob")?.probability).toBeCloseTo(0.75 * 0.8);
    });

    it("máximo valor promete el modelo", () => {
      const legs = [leg({ match_id: 1, p_model: 0.7, p_market: 0.6, odd: 1.6 }), leg({ match_id: 2, p_model: 0.65, p_market: null, odd: 1.7 })];
      const [two] = buildParlays(legs, prefs({ sizes: [2] }), "ev");
      expect(two.mode).toBe("ev");
      expect(two.probability).toBeCloseTo(0.7 * 0.65);
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

describe("acepta desde", () => {
  const leg = (overrides: Partial<Leg>) => legOf("nba", overrides);

  it("máxima probabilidad: lo que paga el mercado, no el justo (ninguna casa lo paga)", () => {
    // Hawks @ Magic, menos de 245.5: se promete 71% (justo 1.41) y las casas pagan alrededor de 1.31.
    const l = leg({ p_model: 0.82, p_market: 0.71, odd: 1.31, book_odds: { Bet365: 1.31, "1xBet": 1.31, Pinnacle: 1.36 } });
    expect(acceptFrom(l, "prob")).toBe(1.31);
    // Sin otras casas en book_odds (piernas viejas), el momio de la casa elegida.
    expect(acceptFrom(leg({ odd: 1.45, book_odds: null }), "prob")).toBe(1.45);
    expect(acceptFrom(leg({ odd: null, book_odds: null }), "prob")).toBeNull();
  });

  it("máximo valor: el momio justo del modelo", () => {
    expect(acceptFrom(leg({ p_model: 0.7, odd: 1.5 }), "ev")).toBe(1.43);
  });

  it("redondea hacia arriba: el que se muestra nunca queda abajo del mínimo", () => {
    expect(acceptFrom(leg({ p_model: 0.7068, odd: 1.5 }), "ev")).toBe(1.42); // 1/0.7068 = 1.4148
    expect(acceptFrom(leg({ odd: 1.3, book_odds: { Bet365: 1.3, "1xBet": 1.33 } }), "prob")).toBe(1.32); // mediana 1.315
    expect(acceptFrom(leg({ odd: 1.3, book_odds: { Bet365: 1.3 } }), "prob")).toBe(1.3);
  });

  it("el del parlay es el producto de sus piernas, redondeado al final", () => {
    const legs = [leg({ p_model: 0.7, odd: 1.5 }), leg({ p_model: 0.8, odd: 1.4 })];
    expect(parlayAcceptFrom(legs, "ev")).toBe(1.79); // 1 / (0.7 × 0.8) = 1.7857
    expect(parlayAcceptFrom(legs, "prob")).toBe(2.1); // 1.5 × 1.4
    expect(parlayAcceptFrom([...legs, leg({ odd: null, book_odds: null })], "prob")).toBeNull();
  });

  it("parlay con valor: el mayor de los momios justos del modelo y del mercado", () => {
    // Modelo 80% (justo 1.25), mercado 70% (justo 1.43): abajo de 1.43 el mercado ya no ve valor.
    const l = leg({ p_model: 0.8, p_market: 0.7, odd: 1.48 });
    expect(promised(l, "value")).toBe(0.7);
    expect(acceptFrom(l, "value")).toBe(1.43);
    expect(acceptFrom(leg({ p_model: 0.6, p_market: 0.65, odd: 1.7 }), "value")).toBe(1.67); // aquí el menor es el modelo
    expect(parlayAcceptFrom([l, leg({ p_model: 0.66, p_market: 0.63, odd: 1.62 })], "value")).toBe(2.27); // 1/(0.7 × 0.63)
  });
});

describe("fromSystem", () => {
  it("usa el modelo y el mercado con los que se registró cada pierna", () => {
    const today = legOf("futbol", { p_model: 0.9, p_market: 0.85 });
    const parlay: SystemParlay = {
      id: 1,
      mode: "value",
      n_legs: 1,
      probability: 0.63,
      odd: 1.62,
      ev: 0.0206,
      result: null,
      settled_odd: null,
      evaluated_at: "2026-10-24T02:00:00Z",
      legs: [{ pick_id: today.id, match_id: 1, market: "total", description: "pierna", p_model: 0.66, p_market: 0.63, odd: 1.62, result: null }],
    };
    const built = fromSystem(parlay, new Map([[today.id, today]]));
    expect(built?.mode).toBe("value");
    expect(built?.legs.map((l) => [l.p_model, l.p_market])).toEqual([[0.66, 0.63]]);
    expect(fromSystem(parlay, new Map())).toBeNull(); // falta una pierna: no se arma a medias
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
