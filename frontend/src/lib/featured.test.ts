import { describe, expect, it } from "vitest";
import type { FeaturedLeg, FeaturedParlay, FeaturedWindow } from "./api";
import { canLoad, copyText, legPrice, legProbability, rangeText, toSlipLegs, windowStatus } from "./featured";

const leg = (overrides: Partial<FeaturedLeg> = {}): FeaturedLeg => ({
  pick_id: 1,
  position: 1,
  sport: "futbol",
  match_id: 10,
  competition: "Liga MX",
  matchup: "América vs Chivas",
  starts_at: "2030-01-12T02:00:00Z",
  date: "2030-01-11",
  market: "total",
  description: "Menos de 4.5 goles",
  p_model: 0.82,
  p_market: 0.76,
  odd: 1.3,
  book_odds: { Bet365: 1.3, "1xBet": 1.33 },
  result: null,
  outcome: { value: null, text: "Pendiente" },
  ...overrides,
});

const parlay = (legs: FeaturedLeg[]): FeaturedParlay => ({
  id: 1,
  mode: "week",
  n_legs: legs.length,
  probability: 0.57,
  odd: 1.7,
  result: null,
  settled_odd: null,
  evaluated_at: "2030-01-07T14:05:00Z",
  legs,
});

const window = (parlays: FeaturedParlay[]): FeaturedWindow => ({
  mode: "weekend",
  label: "Parlay de fin de semana",
  start: "2030-01-11",
  end: "2030-01-13",
  publish_at: "2030-01-10T14:00:00Z",
  parlays,
});

describe("parlays destacados", () => {
  it("promete la menor entre el modelo y el mercado", () => {
    expect(legProbability(leg())).toBe(0.76);
    expect(legProbability(leg({ p_model: 0.7 }))).toBe(0.7);
    expect(legProbability(leg({ p_market: null }))).toBe(0.82);
  });

  it("distingue publicado, por publicar y sin publicar ya pasada su hora", () => {
    const before = Date.parse("2030-01-10T13:59:00Z");
    const after = Date.parse("2030-01-10T14:01:00Z");
    expect(windowStatus(window([]), before)).toBe("upcoming");
    expect(windowStatus(window([]), after)).toBe("missing");
    expect(windowStatus(window([parlay([leg()])]), before)).toBe("published");
  });

  it("sólo se carga al boleto si no ha empezado ninguno de sus partidos", () => {
    const p = parlay([leg(), leg({ pick_id: 2, starts_at: "2030-01-13T18:00:00Z" })]);
    expect(canLoad(p, Date.parse("2030-01-11T12:00:00Z"))).toBe(true);
    expect(canLoad(p, Date.parse("2030-01-12T03:00:00Z"))).toBe(false);
  });

  it("muestra el momio de la casa del sistema o, si no la cotiza, el mejor de las otras", () => {
    expect(legPrice(leg())).toEqual({ odd: 1.3, book: null });
    expect(legPrice(leg({ odd: null }))).toEqual({ odd: 1.33, book: "1xBet" });
    expect(legPrice(leg({ odd: null, book_odds: null }))).toBeNull();
  });

  it("carga al boleto cada pierna con el día de su partido", () => {
    const [slipLeg] = toSlipLegs(parlay([leg()]));
    expect(slipLeg).toEqual({
      pickId: 1,
      sport: "futbol",
      matchId: 10,
      date: "2030-01-11",
      matchup: "América vs Chivas",
      description: "Menos de 4.5 goles",
      pModel: 0.82,
      odd: 1.3,
      bookOdds: { Bet365: 1.3, "1xBet": 1.33 },
    });
  });

  it("copia el parlay con el precio de cada pierna", () => {
    const text = copyText("Parlay de la semana", parlay([leg(), leg({ pick_id: 2, odd: null, description: "No anotan ambos" })]), "Bet365");
    expect(text).toBe(
      [
        "Parlay de la semana · 2 piernas · prob. 57.0% · momio Bet365 1.70",
        "1. América vs Chivas — Menos de 4.5 goles @ 1.30",
        "2. América vs Chivas — No anotan ambos @ 1.33 (1xBet)",
      ].join("\n"),
    );
  });
});

describe("rangeText", () => {
  it("nombra el mes una vez si la ventana no cambia de mes", () => {
    expect(rangeText("2026-10-19", "2026-10-25")).toBe("19 al 25 de octubre");
    expect(rangeText("2026-09-28", "2026-10-04")).toBe("28 de septiembre al 4 de octubre");
  });
});
