import { describe, expect, it } from "vitest";
import { commonPreferences, defaultPreferences, isDefault, preferences } from "./preferences";

describe("preferencias por deporte", () => {
  it("cada deporte tiene sus mercados y estadísticas estándar", () => {
    expect(defaultPreferences("nba").markets).toEqual(["ml", "spread", "total", "team_total", "player"]);
    expect(defaultPreferences("futbol").markets).toContain("btts");
    expect(defaultPreferences("nba").stats).toContain("combos");
    expect(defaultPreferences("futbol").stats).toContain("shots_on");
  });

  it("lo de un deporte no cambia el otro; la casa del usuario es común", () => {
    preferences.update("nba", { markets: ["ml"], minProb: 0.7 });
    expect(preferences.get("nba").markets).toEqual(["ml"]);
    expect(preferences.get("futbol").markets).toEqual(defaultPreferences("futbol").markets);
    expect(preferences.get("futbol").minProb).toBe(0.6);

    preferences.update("futbol", { priceBook: "1xBet", myBook: "Codere" });
    expect(preferences.get("nba")).toMatchObject({ priceBook: "1xBet", myBook: "Codere" });
    expect(isDefault(preferences.get("futbol"), "futbol")).toBe(false); // comparar con otra casa ya no es lo estándar
  });

  it("restablecer vuelve a lo estándar sin olvidar dónde apuestas", () => {
    preferences.update("nba", { markets: ["ml"] });
    commonPreferences.update({ myBook: "Codere", priceBook: "1xBet" });
    preferences.reset("nba");
    expect(isDefault(preferences.get("nba"), "nba")).toBe(true);
    expect(preferences.get("nba").myBook).toBe("Codere");
    expect(preferences.get("futbol").priceBook).toBe("");
  });
});
