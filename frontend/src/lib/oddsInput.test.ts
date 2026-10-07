import { describe, expect, it } from "vitest";
import { parseOdds, verdict } from "./oddsInput";

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
