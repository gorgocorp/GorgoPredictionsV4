import { lastWord, relativeTime } from "../../lib/format";
import type { SportConfig } from "../../lib/sports";

/** Grupo de preferencias de cada estadística de jugador: los combinados van juntos. */
const STAT_GROUP_OF: Record<string, string> = {
  points: "points",
  rebounds: "rebounds",
  assists: "assists",
  threes: "threes",
  fgm: "fgm",
  pra: "combos",
  pr: "combos",
  pa: "combos",
  ra: "combos",
};

export const STATUS_LABELS: Record<string, string> = {
  NS: "Programado",
  Q1: "1er cuarto",
  Q2: "2º cuarto",
  Q3: "3er cuarto",
  Q4: "4º cuarto",
  OT: "Tiempo extra",
  BT: "Descanso",
  HT: "Medio tiempo",
  FT: "Final",
  AOT: "Final (TE)",
  POST: "Pospuesto",
  CANC: "Cancelado",
  SUSP: "Suspendido",
  AWD: "Adjudicado",
  ABD: "Abandonado",
};

export const LIVE_STATUSES = new Set(["Q1", "Q2", "Q3", "Q4", "OT", "BT", "HT"]);

export const PHASE_LABELS: Record<string, string> = {
  preseason: "Pretemporada",
  regular: "Temporada regular",
  playin: "Play-in",
  playoffs: "Playoffs",
};

export const AVAILABILITY_LABELS: Record<string, string> = {
  out: "Fuera",
  doubtful: "Dudoso",
  questionable: "En duda",
  probable: "Probable",
  available: "Disponible",
};

export const NBA: SportConfig = {
  key: "nba",
  label: "NBA",
  markets: [
    { value: "ml", label: "Ganador", help: "Moneyline: qué equipo gana" },
    { value: "spread", label: "Handicap", help: "Spread: ganar o perder por cierto margen" },
    { value: "total", label: "Over/Under del partido", help: "Puntos totales de los dos equipos" },
    { value: "team_total", label: "Over/Under por equipo", help: "Puntos de un solo equipo" },
    { value: "player", label: "Props de jugador", help: "Estadísticas individuales" },
  ],
  marketLabels: {
    ml: "Ganador",
    spread: "Handicap",
    total: "Total",
    team_total: "Total equipo",
    player: "Jugador",
  },
  stats: [
    { value: "points", label: "Puntos", short: "Puntos" },
    { value: "rebounds", label: "Rebotes", short: "Rebotes" },
    { value: "assists", label: "Asistencias", short: "Asistencias" },
    { value: "threes", label: "Triples", short: "Triples" },
    { value: "fgm", label: "Tiros de campo", short: "Tiros" },
    { value: "combos", label: "Combinados (pts+reb+ast…)", short: "Combinados" },
  ],
  statGroup: (stat) => STAT_GROUP_OF[stat],
  statsTitle: "Estadísticas de jugador",
  statsPrefix: "Props",
  matchup: (home, away) => `${lastWord(away)} @ ${lastWord(home)}`,
  questionableSource: "reporte de lesiones",
  playerBadge: (status) => ({
    label: AVAILABILITY_LABELS[status] ?? status,
    className: status === "questionable" ? "badge-warn" : "badge-neutral",
    title: "Según el reporte oficial de lesiones. Si no juega, la apuesta se anula.",
  }),
  hitsTitle: "Veces que lo logró en sus últimos 10 y 25 partidos",
  newsExamples: "lesión, descanso",
  dataJobs: ["games"],
  syncLines: (m) => [
    `Reporte de lesiones NBA: ${m.last_injury_report_at ? relativeTime(m.last_injury_report_at) : "sin reporte (pretemporada)"}`,
  ],
};
