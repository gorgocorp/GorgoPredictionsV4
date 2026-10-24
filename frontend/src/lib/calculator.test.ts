import { describe, expect, it } from "vitest";
import type { Leg } from "./api";
import { checkSide, commission, marketLines, recommend } from "./calculator";

let nextId = 1;
function cards(match_id: number, side: "over" | "under", line: number, p_model: number, p_market: number | null, overrides: Partial<Leg> = {}): Leg {
  return {
    id: nextId++,
    sport: "futbol",
    match_id,
    market: "cards",
    side,
    line,
    team: null,
    stat: null,
    player_id: null,
    player_name: null,
    description: `${side === "over" ? "Más" : "Menos"} de ${line} tarjetas`,
    p_model,
    odd: null,
    bookmaker: null,
    p_market,
    hits_10: null,
    games_10: null,
    hits_25: null,
    games_25: null,
    result: null,
    evaluated_at: "2026-10-24T06:16:00Z",
    player_status: null,
    book_odds: null,
    ...overrides,
  };
}

// Partidos del parlay con valor del 24-oct-2026 (modelo y mercado de V4; momios de Caliente que pasó el usuario).
const STOKE = 1;
const AUGSBURG = 2;
const stokeOver = cards(STOKE, "over", 3.5, 0.5259, 0.5053);
const stokeUnder = cards(STOKE, "under", 3.5, 0.4741, 0.4947);
const augOver = cards(AUGSBURG, "over", 3.5, 0.4997, 0.5492);
const augUnder = cards(AUGSBURG, "under", 3.5, 0.5003, 0.4508);

describe("marketLines", () => {
  it("junta las líneas del mismo mercado y partido, de menor a mayor y con los lados en orden", () => {
    const under45 = cards(STOKE, "under", 4.5, 0.6446, 0.673);
    const over45 = cards(STOKE, "over", 4.5, 0.3554, 0.327);
    const teamCards = cards(STOKE, "over", 1.5, 0.6, 0.6, { market: "team_cards", team: "home" });
    const groups = marketLines(under45, [under45, stokeUnder, teamCards, stokeOver, over45, augUnder]);
    expect(groups.map((g) => [g.line, g.legs.map((l) => l.side)])).toEqual([
      [3.5, ["over", "under"]],
      [4.5, ["over", "under"]],
    ]);
  });
});

describe("checkSide", () => {
  it("dice desde qué momio hay valor y quién lo ve", () => {
    const stoke = checkSide(stokeUnder, "-118");
    expect(stoke.odd).toBeCloseTo(1.8475, 4);
    expect(stoke.valueFrom).toBe(2.11);
    expect(stoke.value).toBe("none");
    expect(stoke.evModel).toBeCloseTo(0.4741 * 1.8475 - 1, 3);
    expect(stoke.evMarket).toBeCloseTo(0.4947 * 1.8475 - 1, 3);

    const augsburg = checkSide(augUnder, "+115");
    expect(augsburg.valueFrom).toBe(2.22);
    expect(augsburg.value).toBe("model_only"); // el modelo ve +7.6%, el mercado −3.1%
    expect(checkSide(augUnder, "+125").value).toBe("value");
  });

  it("sin momio o con uno no válido no hay veredicto", () => {
    expect(checkSide(stokeUnder, "").value).toBeNull();
    expect(checkSide(stokeUnder, "abc").odd).toBeNull();
  });
});

describe("commission", () => {
  it("lo que cobra la casa en la línea, si están todos sus lados", () => {
    expect(commission([checkSide(stokeOver, "-118"), checkSide(stokeUnder, "-118")])).toBeCloseTo(0.0825, 3);
    expect(commission([checkSide(augOver, "-163"), checkSide(augUnder, "+115")])).toBeCloseTo(0.0849, 3);
    expect(commission([checkSide(augOver, "-163"), checkSide(augUnder, "")])).toBeNull();
    expect(commission([checkSide(augOver, "-163")])).toBeNull();
  });
});

describe("recommend", () => {
  const day = (stoke: [string, string], augsburg: [string, string]) => [
    [checkSide(stokeOver, stoke[0]), checkSide(stokeUnder, stoke[1])],
    [checkSide(augOver, augsburg[0]), checkSide(augUnder, augsburg[1])],
  ];

  it("pide los momios de cada partido antes de recomendar", () => {
    expect(recommend(day(["", ""], ["", ""]))).toEqual({ kind: "missing" });
    expect(recommend(day(["-118", "-118"], ["", ""]))).toEqual({ kind: "missing" });
  });

  it("con los momios del 24-oct: nada, y la más cercana es Augsburg menos de 3.5", () => {
    const r = recommend(day(["-118", "-118"], ["-163", "+115"]));
    expect(r.kind).toBe("none");
    expect(r.kind === "none" && r.closest?.leg).toBe(augUnder);
  });

  it("con un solo partido con valor, sólo esa pierna", () => {
    const r = recommend(day(["-118", "-118"], ["-163", "+130"]));
    expect(r.kind === "single" && r.pick.leg).toBe(augUnder);
  });

  it("con valor en los dos partidos, el parlay", () => {
    const r = recommend(day(["-118", "+115"], ["-163", "+130"]));
    expect(r.kind).toBe("parlay");
    if (r.kind !== "parlay") return;
    expect(r.picks.map((p) => p.leg)).toEqual([stokeUnder, augUnder]);
    expect(r.odd).toBeCloseTo(2.15 * 2.3, 6);
    expect(r.valueFrom).toBe(4.68); // 1 / (47.41% × 45.08%): la menor entre modelo y mercado de cada pierna
    expect(r.evMarket).toBeCloseTo(0.4947 * 0.4508 * 2.15 * 2.3 - 1, 6);
    expect(r.evModel).toBeCloseTo(0.4741 * 0.5003 * 2.15 * 2.3 - 1, 6);
  });
});
