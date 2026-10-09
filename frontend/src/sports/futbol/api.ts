import { request, toQuery, type CalendarDay, type League, type Leg, type SystemParlay, type RefreshResult, type Team } from "../../lib/api";

/** Rutas de fútbol (/api/futbol): backend/app/sports/futbol/api.py. */

export interface Projection {
  home_goals: number;
  away_goals: number;
  p_home: number;
  p_draw: number;
  p_away: number;
  p_over25: number;
  p_btts: number;
  /** Marcadores más probables: [["1-0", 0.12], ...] */
  top_scores: [string, number][];
  home_cards: number | null;
  away_cards: number | null;
  lineups: boolean;
  evaluated_at: string;
}

export type Availability = "out" | "questionable" | "available";

export interface Absence {
  player_id: number;
  name: string;
  team: "home" | "away";
  status: Availability;
  report_status: Availability | null;
  reason: string | null;
  manual: boolean;
}

export interface Score {
  /** Marcador a 90 minutos (con el que se liquidan las apuestas). */
  home: number | null;
  away: number | null;
  final_home: number | null;
  final_away: number | null;
  pen_home: number | null;
  pen_away: number | null;
  ht_home: number | null;
  ht_away: number | null;
}

export interface Game {
  id: number;
  match_id: number;
  /** Fecha del partido en hora local (YYYY-MM-DD). */
  match_date: string;
  starts_at: string;
  status: string;
  elapsed: number | null;
  is_finished: boolean;
  round: string | null;
  referee: string | null;
  venue: string | null;
  league: League;
  home: Team;
  away: Team;
  score: Score | null;
  projection: Projection | null;
  /** Hay proyección del modelo pero la cuenta no la ve (free, partido sin empezar). */
  projection_locked: boolean;
  has_odds: boolean;
  has_lineups: boolean;
  picks_count: number;
  absences: Absence[];
}

export interface RosterPlayer {
  player_id: number;
  name: string;
  team: "home" | "away";
  position: string | null;
  games: number;
  starts: number;
  minutes: number;
  goals: number;
  assists: number;
  status: Availability | null;
  report_status: Availability | null;
  reason: string | null;
  manual: boolean;
  is_starter: boolean | null;
}

export interface Roster {
  fixture_id: number;
  date: string;
  started: boolean;
  lineups: boolean;
  players: RosterPlayer[];
  others: { player_id: number; name: string; status: Availability; reason: string | null; team: "home" | "away" }[];
}

export interface DayView {
  date: string;
  games: Game[];
  /** Parlays que registró el sistema ese día (a una cuenta free, sólo los gratis). */
  parlays: SystemParlay[];
}

export interface Round {
  round: string;
  desde: string;
  hasta: string;
  games: number;
  /** Partidos que todavía no empiezan. */
  open: number;
  finished: number;
}

export interface RoundsResponse {
  league: number;
  /** Jornada en curso (la primera con al menos la mitad de sus partidos por jugar). */
  current: string | null;
  rounds: Round[];
}

/** Partidos de varios días: una jornada de una liga o un rango de fechas. */
export interface SlateFilter {
  desde?: string;
  hasta?: string;
  league?: number;
  jornada?: string;
}

export interface SlateView {
  desde: string;
  hasta: string;
  league: number | null;
  jornada: string | null;
  games: Game[];
}

const BASE = "/api/futbol";

export const futbolApi = {
  calendar: () => request<CalendarDay[]>(`${BASE}/calendar`),
  day: (date: string) => request<DayView>(`${BASE}/days/${date}`),
  legs: (date: string) => request<Leg[]>(`${BASE}/days/${date}/legs`),
  refresh: (date: string) => request<RefreshResult>(`${BASE}/days/${date}/refresh`, { method: "POST" }),
  rounds: (league: number) => request<RoundsResponse>(`${BASE}/rounds?league=${league}`),
  slate: (f: SlateFilter) => request<SlateView>(`${BASE}/slate?${toQuery(f)}`),
  slateLegs: (f: SlateFilter) => request<Leg[]>(`${BASE}/slate/legs?${toQuery(f)}`),
  slateRefresh: (f: SlateFilter) => request<RefreshResult>(`${BASE}/slate/refresh?${toQuery(f)}`, { method: "POST" }),
  roster: (fixtureId: number) => request<Roster>(`${BASE}/fixtures/${fixtureId}/roster`),
  setAvailability: (fixtureId: number, playerId: number, status: "out" | "available" | null) =>
    request<RefreshResult>(`${BASE}/availability`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fixture_id: fixtureId, player_id: playerId, status }),
    }),
};
