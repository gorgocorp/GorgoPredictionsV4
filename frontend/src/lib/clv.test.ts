import { describe, expect, it } from "vitest";
import type { ClvData } from "./api";
import { clvExclusions } from "./clv";

const clv = (excluded: Partial<ClvData["excluded"]>): ClvData => ({
  value: null,
  long_shots: null,
  all: null,
  hours_before: null,
  excluded: { no_close: 0, no_reference: 0, short_window: 0, doubtful: 0, ...excluded },
  close_max_minutes: 90,
  min_window_hours: 2,
  max_price_gap: 0.2,
  long_shot_odd: 10,
});

describe("clvExclusions", () => {
  it("lista sólo los motivos con piernas, en el orden en que se revisan", () => {
    expect(clvExclusions(clv({ no_reference: 1234, short_window: 1, doubtful: 2, no_close: 3 }))).toEqual([
      "3 sin lectura a 90 min o menos del inicio",
      "1,234 sin Pinnacle al cierre (no cotiza ese mercado o esa línea)",
      "1 publicada a menos de 2 h del cierre",
      "2 con precio dudoso (a más de 20% del precio justo al publicarse)",
    ]);
  });

  it("usa plural con varias piernas publicadas tarde", () => {
    expect(clvExclusions(clv({ short_window: 30 }))).toEqual(["30 publicadas a menos de 2 h del cierre"]);
  });

  it("sin piernas descartadas no dice nada", () => {
    expect(clvExclusions(clv({}))).toEqual([]);
  });
});
