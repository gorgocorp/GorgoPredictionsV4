import type { SportKey } from "./api";

/** Referencia de cada deporte: backtest día por día sin información futura (ver README de cada proyecto). */
export interface BacktestReference {
  title: string;
  info: string;
  teamLabel: string;
  propsLabel: string;
  /** Parlays de n piernas: [predicho, real] con piernas de equipo y con props de jugador. */
  rows: { n: number; team: [number, number]; props: [number, number] }[];
}

export const BACKTESTS: Record<SportKey, BacktestReference> = {
  nba: {
    title: "Referencia: backtest 2025-26",
    info: "Simulación día por día sin información futura (208 días). Piernas más probables de cada día, una por partido. Sirve para saber qué esperar; el rendimiento real de arriba es el que cuenta.",
    teamLabel: "Ganadores: predicho",
    propsLabel: "Props: predicho",
    rows: [
      { n: 2, team: [0.597, 0.604], props: [0.721, 0.663] },
      { n: 3, team: [0.435, 0.457], props: [0.611, 0.561] },
      { n: 4, team: [0.309, 0.35], props: [0.518, 0.483] },
      { n: 5, team: [0.213, 0.27], props: [0.439, 0.414] },
      { n: 6, team: [0.145, 0.182], props: [0.372, 0.37] },
      { n: 7, team: [0.096, 0.21], props: [0.315, 0.323] },
      { n: 8, team: [0.061, 0.082], props: [0.266, 0.275] },
    ],
  },
  futbol: {
    title: "Referencia: backtest",
    info: "Simulación día por día sin información futura: agosto 2025 a octubre 2026, uno de cada 2 días (183 días, 3,069 partidos de las 15 ligas). Cada día, la pierna más probable de cada partido (entre 60% y 87%), una por partido. Sirve para saber qué esperar; el rendimiento real de arriba es el que cuenta.",
    teamLabel: "Equipos: predicho",
    propsLabel: "Jugadores: predicho",
    rows: [
      { n: 2, team: [0.75, 0.77], props: [0.729, 0.718] },
      { n: 3, team: [0.649, 0.675], props: [0.614, 0.574] },
      { n: 4, team: [0.56, 0.604], props: [0.519, 0.493] },
      { n: 5, team: [0.484, 0.52], props: [0.436, 0.429] },
      { n: 6, team: [0.418, 0.46], props: [0.369, 0.352] },
      { n: 7, team: [0.362, 0.411], props: [0.309, 0.286] },
      { n: 8, team: [0.311, 0.374], props: [0.259, 0.25] },
    ],
  },
};
