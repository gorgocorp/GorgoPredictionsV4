import { relativeTime, shortTeam } from "../../lib/format";
import type { SportConfig } from "../../lib/sports";

export const STATUS_LABELS: Record<string, string> = {
  TBD: "Por definir",
  NS: "Programado",
  "1H": "1er tiempo",
  HT: "Medio tiempo",
  "2H": "2º tiempo",
  ET: "Tiempo extra",
  BT: "Descanso (TE)",
  P: "Penales",
  SUSP: "Suspendido",
  INT: "Interrumpido",
  LIVE: "En juego",
  FT: "Final",
  AET: "Final (TE)",
  PEN: "Final (penales)",
  PST: "Pospuesto",
  CANC: "Cancelado",
  ABD: "Abandonado",
  AWD: "Adjudicado",
  WO: "Walkover",
};

export const LIVE_STATUSES = new Set(["1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE"]);

export const AVAILABILITY_LABELS: Record<string, string> = {
  out: "Baja",
  questionable: "En duda",
  available: "Disponible",
};

export const POSITION_LABELS: Record<string, string> = { G: "POR", D: "DEF", M: "MED", F: "DEL" };

const ROUND_NAMES: [RegExp, string][] = [
  [/^Regular Season - (\d+)$/, "Jornada $1"],
  [/^(Apertura|Clausura) - (\d+)$/, "$1 · Jornada $2"],
  [/^League Stage - (\d+)$/, "Fase de liga · Jornada $1"],
  [/^Group Stage - (\d+)$/, "Fase de grupos · Jornada $1"],
  [/^Group ([A-Z]) - (\d+)$/, "Grupo $1 · Jornada $2"],
  [/^Round of 16$/, "Octavos de final"],
  [/^8th Finals$/, "Octavos de final"],
  [/^Quarter-finals$/, "Cuartos de final"],
  [/^Semi-finals$/, "Semifinales"],
  [/^Final$/, "Final"],
];

/** Nombre de la ronda de la API en español: "Apertura - 11" -> "Apertura · Jornada 11". */
export function roundLabel(round: string): string {
  for (const [pattern, label] of ROUND_NAMES) {
    if (pattern.test(round)) return round.replace(pattern, label);
  }
  return round;
}

export const FUTBOL: SportConfig = {
  key: "futbol",
  label: "Fútbol",
  markets: [
    { value: "1x2", label: "1X2", help: "Gana local, empate o gana visitante" },
    { value: "dc", label: "Doble oportunidad", help: "Local o empate, visitante o empate, o no hay empate" },
    { value: "total", label: "Goles (más/menos)", help: "Goles totales del partido" },
    { value: "team_total", label: "Goles por equipo", help: "Goles de un solo equipo" },
    { value: "btts", label: "Ambos anotan", help: "Sí / No" },
    { value: "score", label: "Marcador exacto", help: "Resultado exacto a 90 minutos" },
    { value: "cards", label: "Tarjetas (más/menos)", help: "Amarillas + rojas del partido" },
    { value: "team_cards", label: "Tarjetas por equipo", help: "Amarillas + rojas de un equipo" },
    { value: "player", label: "Apuestas de jugador", help: "Goleador, remates, asistencias, tarjeta" },
  ],
  marketLabels: {
    "1x2": "1X2",
    dc: "Doble oportunidad",
    total: "Goles",
    team_total: "Goles equipo",
    btts: "Ambos anotan",
    score: "Marcador",
    cards: "Tarjetas",
    team_cards: "Tarjetas equipo",
    player: "Jugador",
  },
  stats: [
    { value: "goals", label: "Goleador", short: "Goleador" },
    { value: "ga", label: "Gol o asistencia", short: "Gol o asistencia" },
    { value: "assists", label: "Asistencia", short: "Asistencia" },
    { value: "shots_on", label: "Remates a puerta", short: "Remates a puerta" },
    { value: "shots", label: "Remates", short: "Remates" },
    { value: "cards", label: "Recibe tarjeta", short: "Recibe tarjeta" },
  ],
  statGroup: (stat) => stat,
  statsTitle: "Apuestas de jugador",
  statsPrefix: "Jugador",
  matchup: (home, away) => `${shortTeam(home)} vs ${shortTeam(away)}`,
  questionableSource: "según la API",
  playerBadge: (status) =>
    status === "questionable"
      ? { label: "En duda", className: "badge-warn", title: "La API lo marca en duda. Si no juega, la apuesta se anula." }
      : status === "starter"
        ? { label: "Titular", className: "badge-won", title: "Titular en la alineación confirmada" }
        : null,
  hitsTitle: "Props: veces que lo logró en sus últimos 10 y 25 partidos jugados",
  newsExamples: "baja, rotación",
  dataJobs: ["details", "fixtures"],
  syncLines: (m) => [`Bajas (API-Football): ${relativeTime(m.last_injuries_at)}`, `${m.leagues?.length ?? 0} ligas`],
};
