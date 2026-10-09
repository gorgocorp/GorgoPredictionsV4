/** Tipos y llamadas comunes a los dos deportes. Lo propio de cada deporte está en src/sports/<deporte>/api.ts. */

export type SportKey = "nba" | "futbol";
export type Result = "won" | "lost" | "void" | null;

/** admin: ve todo y administra; subscriber: ve todo mientras su suscripción esté vigente; free: los parlays gratis. */
export type Role = "admin" | "subscriber" | "free";

/** Quién inició sesión (/api/auth/me y /api/auth/login). */
export interface Viewer {
  id: number;
  username: string;
  role: Role;
  /** Plan efectivo: un suscriptor vencido está en "free". */
  plan: Role;
  /** Ve todo: admin o suscripción vigente. */
  full: boolean;
  /** Último día con suscripción (YYYY-MM-DD, hora local); null = sin vencimiento. */
  subscription_until: string | null;
}

/** Una cuenta en la administración (/api/admin/users). */
export interface AdminUser {
  id: number;
  username: string;
  role: Role;
  subscription_until: string | null;
  active: boolean;
  created_at: string;
  last_login_at: string | null;
  has_password: boolean;
  bets: number;
  /** Ve todo hoy (activa y con plan completo vigente). */
  full: boolean;
}

export interface UserChange {
  role: Role;
  subscription_until: string | null;
  active: boolean;
}

export interface NewUser {
  username: string;
  password: string;
  role: Role;
  subscription_until: string | null;
}

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

/** Parlay registrado por el sistema para un día (configuración estándar). A una cuenta free sólo le llegan los gratis. */
export interface SystemParlay {
  id: number;
  mode: "prob" | "ev";
  n_legs: number;
  probability: number;
  odd: number | null;
  ev: number | null;
  result: Result;
  settled_odd: number | null;
  evaluated_at: string;
  legs: {
    pick_id: number;
    match_id: number;
    market: string;
    description: string;
    p_model: number;
    odd: number | null;
    result: Result;
  }[];
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
  /** Casa de referencia del mercado (casi sin comisión): contra su cierre se mide el CLV. */
  sharp_bookmaker: string;
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

/** CLV de un grupo de piernas: momio de publicación × probabilidad sin comisión de Pinnacle al cierre − 1. */
export interface ClvSummary {
  n: number;
  avg: number;
  median: number;
  beat_rate: number;
  n_move: number;
  /** Probabilidad de Pinnacle al cierre − al publicarse (null si ninguna la tenía al publicarse). */
  avg_move: number | null;
}

/** Por qué no cuenta una pierna con valor, en el orden en que se revisa. */
export interface ClvExclusions {
  /** Su última lectura fue a más de `close_max_minutes` del inicio. */
  no_close: number;
  /** Pinnacle no cotizaba su mercado completo al cierre. */
  no_reference: number;
  /** Publicada a menos de `min_window_hours` del cierre: misma foto de los momios. */
  short_window: number;
  /** Su momio de publicación estaba a más de `max_price_gap` del precio justo de ese momento. */
  doubtful: number;
}

export interface ClvData {
  /** Piernas con valor al publicarse (probabilidad del modelo × momio > 1) de momio menor a `long_shot_odd`. */
  value: ClvSummary | null;
  /** Piernas con valor de momio `long_shot_odd` o más: su precio justo es poco confiable. */
  long_shots: ClvSummary | null;
  /** Todas las piernas de momio menor a `long_shot_odd` (referencia: incluye los dos lados de cada mercado). */
  all: ClvSummary | null;
  hours_before: number | null;
  excluded: ClvExclusions;
  close_max_minutes: number;
  min_window_hours: number;
  max_price_gap: number;
  long_shot_odd: number;
}

export interface Performance {
  sport: SportKey;
  filters: Record<string, unknown>;
  legs: { settled: number; void: number; won: number };
  by_market: { market: string; n: number; predicted: number; actual: number; clv_n: number; clv: number | null }[];
  calibration: CalibrationBin[];
  model_vs_market: { n: number; brier_model: number; brier_market: number } | null;
  positive_ev: { n: number; hit_rate: number; avg_odd: number; profit: number; roi: number } | null;
  clv: ClvData | null;
  parlays: ParlayPerformance[];
}

export interface PerformanceFilters {
  include_preseason?: boolean;
  league?: number | null;
}

export interface HistoryLeg {
  locked: false;
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

/** Pierna que una cuenta free no ve (partido sin empezar fuera de los parlays gratis): sólo el partido. */
export interface LockedLeg {
  locked: true;
  position: number;
  sport: SportKey;
  competition: string;
  matchup: string;
  starts_at: string;
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
  /** Alguna pierna llega bloqueada (cuenta free). */
  locked: boolean;
  legs: (HistoryLeg | LockedLeg)[];
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

/** Evento de `window` cuando la API responde 401 (la sesión venció o se cerró): la app vuelve a "Entrar". */
export const SESSION_EXPIRED = "gorgo:session-expired";

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor. Revisa que el contenedor web esté corriendo.");
  }
  if (res.status === 401 && !url.startsWith("/api/auth/")) window.dispatchEvent(new Event(SESSION_EXPIRED));
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

/** Petición con cuerpo JSON. */
function send<T>(url: string, method: "POST" | "PUT", body?: unknown): Promise<T> {
  return request<T>(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export const api = {
  auth: {
    me: () => request<Viewer>("/api/auth/me"),
    login: (username: string, password: string) => send<Viewer>("/api/auth/login", "POST", { username, password }),
    logout: () => send<{ ok: true }>("/api/auth/logout", "POST"),
    changePassword: (current: string, next: string) => send<{ ok: true }>("/api/auth/password", "POST", { current, new: next }),
  },
  admin: {
    users: () => request<AdminUser[]>("/api/admin/users"),
    createUser: (user: NewUser) => send<{ id: number }>("/api/admin/users", "POST", user),
    updateUser: (id: number, change: UserChange) => send<{ id: number }>(`/api/admin/users/${id}`, "PUT", change),
    resetPassword: (id: number, password: string) => send<{ id: number }>(`/api/admin/users/${id}/password`, "PUT", { password }),
  },
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
