import { request, type CalendarDay, type Leg, type SystemParlay, type RefreshResult, type Team } from "../../lib/api";

/** Rutas de NBA (/api/nba): backend/app/sports/nba/api.py. */

export interface Projection {
  home_points: number;
  away_points: number;
  p_home_win: number;
  evaluated_at: string;
}

export type Availability = "out" | "doubtful" | "questionable" | "probable" | "available";

export interface Absence {
  player_id: number;
  name: string;
  team: "home" | "away";
  status: Availability;
  report_status: Availability | null;
  reason: string | null;
  manual: boolean;
}

export interface RosterSide {
  /** Puntos por partido netos ganados por cambios de plantel (negativo = perdió). */
  gain: number;
  /** Fracción del rating que aún viene de la temporada anterior. */
  weight: number;
  departed: [string, number][];
  arrived: [string, number][];
}

export interface Game {
  id: number;
  match_id: number;
  starts_at: string;
  status: string;
  phase: "preseason" | "regular" | "playin" | "playoffs";
  is_finished: boolean;
  home: Team;
  away: Team;
  score: { home: number; away: number } | null;
  projection: Projection | null;
  /** Hay proyección del modelo pero la cuenta no la ve (free, partido sin empezar). */
  projection_locked: boolean;
  has_odds: boolean;
  picks_count: number;
  missing_points: { home: number; away: number };
  roster: { home: number; away: number; detail: { home: RosterSide | null; away: RosterSide | null } };
  absences: Absence[];
  injury_report: { report_at: string | null; pending: ("home" | "away")[]; covered: boolean };
}

export interface RosterPlayer {
  player_id: number;
  name: string;
  team: "home" | "away";
  games: number;
  points: number;
  minutes: number;
  status: Availability | null;
  report_status: Availability | null;
  reason: string | null;
  manual: boolean;
}

export interface Roster {
  game_id: number;
  date: string;
  started: boolean;
  players: RosterPlayer[];
  unmatched: { name: string; status: Availability; team: "home" | "away" }[];
}

export interface DayView {
  date: string;
  games: Game[];
  /** Parlays que registró el sistema ese día (a una cuenta free, sólo los gratis). */
  parlays: SystemParlay[];
}

const BASE = "/api/nba";

export const nbaApi = {
  calendar: () => request<CalendarDay[]>(`${BASE}/calendar`),
  day: (date: string) => request<DayView>(`${BASE}/days/${date}`),
  legs: (date: string) => request<Leg[]>(`${BASE}/days/${date}/legs`),
  refresh: (date: string) => request<RefreshResult>(`${BASE}/days/${date}/refresh`, { method: "POST" }),
  roster: (gameId: number) => request<Roster>(`${BASE}/games/${gameId}/roster`),
  setAvailability: (date: string, playerId: number, status: "out" | "available" | null) =>
    request<RefreshResult>(`${BASE}/availability`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date, player_id: playerId, status }),
    }),
};
