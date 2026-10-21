import { describe, expect, it } from "vitest";
import { excludedText, fullDate, monthLabel, units } from "./results";

describe("resultados públicos", () => {
  it("nombra meses y fechas sin desfase de zona horaria", () => {
    expect(monthLabel("2026-10")).toBe("Octubre de 2026");
    expect(monthLabel("2027-01")).toBe("Enero de 2027");
    expect(fullDate("2026-10-19")).toBe("19 de octubre de 2026");
    expect(fullDate("2026-11-01")).toBe("1 de noviembre de 2026");
  });

  it("muestra la ganancia en unidades con signo", () => {
    expect(units(0.463)).toBe("+0.46 u");
    expect(units(-1)).toBe("-1.00 u");
    expect(units(0)).toBe("0.00 u");
    expect(units(null)).toBe("—");
  });

  it("dice cuántos parlays no cuentan por la regla anterior", () => {
    expect(excludedText(0)).toBe("");
    expect(excludedText(1)).toMatch(/^No cuenta 1 parlay del día que se armó/);
    expect(excludedText(2)).toMatch(/^No cuentan 2 parlays del día que se armaron/);
  });
});
