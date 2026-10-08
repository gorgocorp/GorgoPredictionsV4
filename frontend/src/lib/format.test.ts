import { describe, expect, it } from "vitest";
import { orList } from "./format";

describe("orList", () => {
  it("une las casas como se dice en español", () => {
    expect(orList(["Bet365", "1xBet", "Pinnacle"])).toBe("Bet365, 1xBet o Pinnacle");
    expect(orList(["Bet365", "1xBet"])).toBe("Bet365 o 1xBet");
    expect(orList(["Bet365"])).toBe("Bet365");
  });
});
