/** Tipos y llamadas comunes a los dos deportes. Lo propio de cada deporte está en src/sports/<deporte>/api.ts. */

export type SportKey = "nba" | "futbol";
export type Result = "won" | "lost" | "void" | null;

export interface Team {
  id: number;
  name: string;
  logo: string | null;
}

export interface League {
  id: number;
  name: string;
  country: string | null;
  logo: string | null;
  current_season?: number | null;
}

/** Lo que las piezas comunes (partidos, piernas, parlays, boleto) usan de un partido de cualquier deporte. */
export interface SlateGame {
  /** ID del proveedor (API-Basketball o API-Football); es el que va en la URL (?partido=). */
  id: number;
  /** Identidad común del partido (core.matches): única entre deportes. */
  match_id: number;
  starts_at: string;
  status: string;
  picks_count: number;
  home: Team;
  away: Team;
  /** Fútbol: competición del partido. */
  league?: League;
  /** Fútbol: día del partido en hora local (YYYY-MM-DD). */
  match_date?: string;
}

/** Una pierna evaluada por el modelo (cualquier deporte). */
export interface Leg {
  id: number;
  sport: SportKey;
  match_id: number;
  /** Fútbol: liga del partido. */
  league_id?: number;
  market: string;
  side: string;
  line: number | null;
  team: string | null;
  stat: string | null;
  player_id: number | null;
  player_name: string | null;
  description: string;
  p_model: number;
  odd: number | null;
  bookmaker: string | null;
  p_market: number | null;
  hits_10: number | null;
  games_10: number | null;
  hits_25: number | null;
  games_25: number | null;
  result: Result;
  evaluated_at: string;
  /** NBA: designación del reporte de lesiones; fútbol: "questionable" o "starter". */
  player_status: string | null;
  /** Momio de cada casa de la API que cotiza la pierna, p. ej. {"Bet365": 1.83, "1xBet": 1.87}. */
  book_odds: Record<string, number> | null;
}

export interface CalendarDay {
  date: string;
  games: number;
  /** NBA: partidos fuera de pretemporada. */
  official?: number;
}

export interface RefreshResult {
  games: number;
  picks: number;
  parlays: number;
  days: number;
}

export interface SyncJob {
  status: "running" | "success" | "failed";
  started_at: string;
  finished_at: string | null;
  error: string | null;
}

export interface SportMeta {
  key: SportKey;
  label: string;
  model_version: string;
  sync: Record<string, SyncJob>;
  last_odds_at: string | null;
  last_picks_at: string | null;
  last_settled_at: string | null;
  /** NBA: último reporte oficial de lesiones. */
  last_injury_report_at?: string | null;
  /** Fútbol: última descarga de bajas de la API. */
  last_injuries_at?: string | null;
  /** Fútbol: competiciones del proyecto. */
  leagues?: League[];
}

export interface Meta {
  /** Casa con la que el sistema registra y mide sus parlays. */
  bookmaker: string;
  /** Casas de la API cuyos momios se guardan en cada pierna. */
  bookmakers: string[];
  today: string;
  timezone: string;
  sports: Record<SportKey, SportMeta>;
}

export interface CalibrationBin {
  lo: number;
  hi: number;
  n: number;
  predicted: number;
  actual: number;
}

export interface ParlayPerformance {
  mode: "prob" | "ev";
  n_legs: number;
  count: number;
  predicted: number;
  actual: number;
  count_with_odds: number;
  roi: number | null;
}

export interface Performance {
  sport: SportKey;
  filters: Record<string, unknown>;
  legs: { settled: number; void: number; won: number };
  by_market: { market: string; n: number; predicted: number; actual: number }[];
  calibration: CalibrationBin[];
  model_vs_market: { n: number; brier_model: number; brier_market: number } | null;
  positive_ev: { n: number; hit_rate: number; avg_odd: number; profit: number; roi: number } | null;
  parlays: ParlayPerformance[];
}

export interface PerformanceFilters {
  include_preseason?: boolean;
  league?: number | null;
}

export interface HistoryLeg {
  pick_id: number;
  position: number;
  sport: SportKey;
  match_id: number;
  external_id: number;
  competition: string;
  matchup: string;
  starts_at: string;
  market: string;
  description: string;
  p_model: number;
  odd: number | null;
  result: Result;
  outcome: { value: number | null; text: string };
}

export interface HistoryParlay {
  id: number;
  sport: SportKey;
  day: string;
  mode: "prob" | "ev";
  n_legs: number;
  probability: number;
  odd: number | null;
  result: Result;
  settled_odd: number | null;
  evaluated_at: string;
  settled_at: string | null;
  first_start: string;
  /** NBA: incluye partidos de pretemporada. */
  preseason: boolean;
  bookmaker: string | null;
  model_version: string;
  profit: number | null;
  recorded_before_start: boolean;
  legs: HistoryLeg[];
}

export interface HistorySummary {
  parlays: number;
  settled: number;
  won: number;
  lost: number;
  void: number;
  pending: number;
  expected_wins: number;
  with_odds: number;
  profit_units: number | null;
  roi: number | null;
  by_size: { n_legs: number; parlays: number; settled: number; won: number; expected: number }[];
}

export interface HistoryResponse {
  summary: HistorySummary;
  total: number;
  items: HistoryParlay[];
}

export interface HistoryFilters {
  sport?: SportKey;
  desde?: string;
  hasta?: string;
  mode?: "prob" | "ev";
  n_legs?: number;
  result?: "won" | "lost" | "void" | "pending";
  include_preseason?: boolean;
  limit?: number;
  offset?: number;
}

/** Parámetros de una URL a partir de un objeto (omite vacíos). */
export function toQuery(f: object): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(f)) {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  }
  return q.toString();
}

export interface BetLeg {
  position: number;
  pick_id: number;
  sport: SportKey;
  competition: string;
  matchup: string;
  starts_at: string;
  description: string;
  p_model: number;
  odd: number;
  result: Result;
  outcome: { value: number | null; text: string };
}

export interface Bet {
  id: number;
  bookmaker: string;
  stake: number;
  odd: number;
  model_probability: number;
  book_probability: number;
  note: string | null;
  created_at: string;
  first_start: string;
  result: Result;
  settled_odd: number | null;
  payout: number | null;
  settled_at: string | null;
  profit: number | null;
  can_delete: boolean;
  legs: BetLeg[];
}

export interface BetsSummary {
  bets: number;
  pending: number;
  won: number;
  lost: number;
  void: number;
  expected_wins: number;
  book_expected_wins: number;
  staked: number;
  returned: number;
  profit: number;
  roi: number | null;
  pending_stake: number;
}

export interface NewBet {
  bookmaker: string;
  stake: number;
  legs: { pick_id: number; odd: number }[];
  total_odd?: number;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor. Revisa que el contenedor web esté corriendo.");
  }
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => request<Meta>("/api/meta"),
  history: (f: HistoryFilters) => request<HistoryResponse>(`/api/history?${toQuery(f)}`),
  bets: () => request<{ summary: BetsSummary; items: Bet[] }>("/api/bets"),
  createBet: (bet: NewBet) =>
    request<{ id: number }>("/api/bets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(bet),
    }),
  deleteBet: (id: number) => request<{ deleted: number }>(`/api/bets/${id}`, { method: "DELETE" }),
  performance: (sport: SportKey, f: PerformanceFilters) => request<Performance>(`/api/performance?${toQuery({ sport, ...f })}`),
};
