import { describe, expect, it } from "vitest";
import { legValue, parseOdds, verdict } from "./oddsInput";

describe("parseOdds", () => {
  it("lee momios americanos", () => {
    expect(parseOdds("-120")).toBeCloseTo(1.8333, 3);
    expect(parseOdds("+145")).toBeCloseTo(2.45, 3);
    expect(parseOdds("145")).toBeCloseTo(2.45, 3);
    expect(parseOdds("+1200")).toBeCloseTo(13, 3);
  });

  it("lee momios decimales", () => {
    expect(parseOdds("1.83")).toBe(1.83);
    expect(parseOdds("1,83")).toBe(1.83);
    expect(parseOdds("2")).toBe(2);
  });

  it("rechaza valores inválidos", () => {
    for (const bad of ["", "abc", "-50", "0.9", "1", "+99"]) expect(parseOdds(bad)).toBeNull();
  });
});

describe("verdict", () => {
  it("clasifica la diferencia modelo vs casa", () => {
    expect(verdict(0.83, 0.545)).toBe("suspicious");
    expect(verdict(0.6, 0.55)).toBe("value");
    expect(verdict(0.5, 0.55)).toBe("none");
  });
});

describe("legValue", () => {
  it("hay valor sólo si la casa paga más que el momio justo del modelo y del mercado", () => {
    // Pelicans: modelo 74%, mercado 42% (justo 2.40); Caliente paga 2.35.
    expect(legValue(0.7389, 0.4165, 2.35)).toBe("model_only");
    // Hornets +1.5: Caliente paga 1.98, más que el justo del modelo (1.41) y del mercado (1.81).
    expect(legValue(0.707, 0.5522, 1.98)).toBe("value");
    expect(legValue(0.45, 0.52, 2.0)).toBe("market_only");
    expect(legValue(0.45, 0.48, 2.0)).toBe("none");
  });

  it("sin probabilidad del mercado no hay con qué comparar", () => {
    expect(legValue(0.7, null, 2.0)).toBe("no_market");
    expect(legValue(0.7, undefined, 2.0)).toBe("no_market");
  });

  it("pagar justo el momio justo no es valor", () => {
    expect(legValue(0.5, 0.5, 2.0)).toBe("none");
  });
});
