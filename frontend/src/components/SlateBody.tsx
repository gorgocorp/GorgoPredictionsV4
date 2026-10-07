import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useState, type ComponentType, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type League, type Leg, type SlateGame } from "../lib/api";
import { withPrices } from "../lib/books";
import { longDate } from "../lib/format";
import { usePreferences } from "../lib/preferences";
import type { SportConfig } from "../lib/sports";
import { BetSlip } from "./BetSlip";
import { LegsTable } from "./LegsTable";
import { ParlaysSection } from "./ParlaysSection";
import { PreferencesPanel } from "./PreferencesPanel";
import { EmptyState, ErrorState, Skeleton, SkeletonCards } from "./States";

/** Lo que usamos de una consulta de React Query. */
export interface QueryState<T> {
  data: T | undefined;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
}

export interface GameCardProps<G> {
  game: G;
  selected: boolean;
  onSelect: () => void;
  onAbsences: () => void;
}

interface GameGroup<G> {
  key: string;
  league: League | null;
  title: string | null;
  games: G[];
}

/** Fútbol: partidos por liga (un día) o por día y liga (varios días). NBA: un solo grupo sin título. */
function groupGames<G extends SlateGame>(games: G[], multiDay: boolean): GameGroup<G>[] {
  const groups = new Map<string, GameGroup<G>>();
  for (const g of games) {
    const league = g.league ?? null;
    const day = g.match_date ?? "";
    const key = league ? (multiDay ? `${day}|${league.id}` : String(league.id)) : "";
    const title = league ? (multiDay && day ? `${longDate(day)} · ${league.name}` : league.name) : null;
    const group = groups.get(key) ?? { key, league, title, games: [] };
    group.games.push(g);
    groups.set(key, group);
  }
  return [...groups.values()];
}

function leagueCounts(games: SlateGame[]): { league: League; count: number }[] {
  const counts = new Map<number, { league: League; count: number }>();
  for (const g of games) {
    if (!g.league) continue;
    const c = counts.get(g.league.id) ?? { league: g.league, count: 0 };
    c.count += 1;
    counts.set(g.league.id, c);
  }
  return [...counts.values()];
}

/**
 * Cuerpo común de las páginas Día (NBA y fútbol) y Jornada: partidos, parlays sugeridos, tabla de piernas,
 * boleto y paneles. Cada página pone su encabezado, de dónde salen partidos y piernas, y la tarjeta y el
 * panel de bajas de su deporte.
 */
export function SlateBody<G extends SlateGame>({
  config,
  header,
  games: gamesQuery,
  legs: legsQuery,
  multiDay,
  slipDate,
  gamesNote,
  emptyGames,
  noPicksMessage,
  refreshButton,
  wholeLabel,
  GameCard,
  AvailabilityPanel,
}: {
  config: SportConfig;
  header: ReactNode;
  games: QueryState<G[]>;
  legs: QueryState<Leg[]>;
  multiDay: boolean;
  slipDate: string;
  /** Nota junto al título "Partidos" (qué proyecta el modelo). */
  gamesNote: string;
  emptyGames: ReactNode;
  /** Mensaje cuando hay partidos por empezar pero todavía no hay picks. */
  noPicksMessage: string;
  refreshButton: ReactNode;
  wholeLabel?: string;
  GameCard: ComponentType<GameCardProps<G>>;
  AvailabilityPanel: ComponentType<{ game: G | null; onClose: () => void }>;
}) {
  const [params, setParams] = useSearchParams();
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta, refetchInterval: 60_000 });
  const bookmaker = meta.data?.bookmaker ?? "Bet365";
  const bookmakers = meta.data?.bookmakers ?? [bookmaker];
  const prefs = usePreferences(config.key);
  // Casa con la que se comparan piernas y parlays: la elegida en Personalizar si la API la trae.
  const priceBook = bookmakers.find((b) => b.toLowerCase() === prefs.priceBook.toLowerCase()) ?? bookmaker;
  const [prefsOpen, setPrefsOpen] = useState(false);
  const openPrefs = useCallback(() => setPrefsOpen(true), []);
  const closePrefs = useCallback(() => setPrefsOpen(false), []);
  const [absencesGameId, setAbsencesGameId] = useState<number | null>(null);
  const closeAbsences = useCallback(() => setAbsencesGameId(null), []);

  const gameList = useMemo(() => gamesQuery.data ?? [], [gamesQuery.data]);
  const pricedLegs = useMemo(() => withPrices(legsQuery.data ?? [], priceBook, bookmaker), [legsQuery.data, priceBook, bookmaker]);
  const games = useMemo(() => new Map<number, SlateGame>(gameList.map((g) => [g.match_id, g])), [gameList]);
  const selectedGame = params.get("partido") ? Number(params.get("partido")) : null;
  const selectedLeague = params.get("liga") ? Number(params.get("liga")) : null;
  const leagues = leagueCounts(gameList);
  // El filtro de liga sólo aplica si hay varias ligas (en una jornada, "liga" es la liga elegida).
  const leagueFilter = leagues.length > 1 ? selectedLeague : null;
  const groups = groupGames(gameList, multiDay).filter((g) => leagueFilter === null || g.league?.id === leagueFilter);
  const shownIds = new Set(groups.flatMap((g) => g.games.map((x) => x.match_id)));
  const shownLegs = leagueFilter === null ? pricedLegs : pricedLegs.filter((l) => shownIds.has(l.match_id));
  const openGames = gameList.filter((g) => g.status === "NS" && new Date(g.starts_at).getTime() > Date.now());
  const hasPicks = gameList.some((g) => g.picks_count > 0);

  const update = (changes: Record<string, string | null>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(changes)) {
          if (v === null) next.delete(k);
          else next.set(k, v);
        }
        next.delete("pagina");
        return next;
      },
      { replace: true },
    );
  const selectLeague = (id: number | null) => update({ liga: id === null ? null : String(id), partido: null });
  const selectGame = (id: number) => update({ partido: selectedGame === id ? null : String(id) });

  return (
    <div className="day-layout">
      <div className="day-main">
        {header}

        <section aria-labelledby="games-title">
          <div className="section-head">
            <h2 id="games-title">Partidos</h2>
            <span className="muted small">{gamesNote}</span>
          </div>
          {leagues.length > 1 && (
            <div className="league-chips" role="group" aria-label="Filtrar por liga">
              <button type="button" className="chip-toggle" aria-pressed={leagueFilter === null} onClick={() => selectLeague(null)}>
                Todas <span className="muted num">{gameList.length}</span>
              </button>
              {leagues.map(({ league, count }) => (
                <button
                  key={league.id}
                  type="button"
                  className="chip-toggle"
                  aria-pressed={leagueFilter === league.id}
                  onClick={() => selectLeague(leagueFilter === league.id ? null : league.id)}
                >
                  {league.logo && <img src={league.logo} alt="" className="league-logo" loading="lazy" />}
                  {league.name} <span className="muted num">{count}</span>
                </button>
              ))}
            </div>
          )}
          {gamesQuery.isPending ? (
            <SkeletonCards count={6} height={170} />
          ) : gamesQuery.isError ? (
            <ErrorState message={(gamesQuery.error as Error).message} onRetry={() => gamesQuery.refetch()} />
          ) : gameList.length === 0 ? (
            emptyGames
          ) : (
            groups.map((group) => (
              <div key={group.key} className="league-group">
                {group.league && (
                  <h3 className="league-head">
                    {group.league.logo && <img src={group.league.logo} alt="" className="league-logo" loading="lazy" />}
                    {group.title}
                    {!multiDay && (
                      <span className="muted small"> · {group.league.country === "World" ? "Internacional" : group.league.country}</span>
                    )}
                  </h3>
                )}
                <div className="games-grid">
                  {group.games.map((g) => (
                    <GameCard
                      key={g.id}
                      game={g}
                      selected={selectedGame === g.id}
                      onSelect={() => selectGame(g.id)}
                      onAbsences={() => setAbsencesGameId(g.id)}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </section>

        {gameList.length > 0 && !hasPicks && !gamesQuery.isPending && (
          <EmptyState title="Todavía no hay picks para estos partidos" action={openGames.length > 0 ? refreshButton : undefined}>
            {openGames.length > 0 ? noPicksMessage : "Estos partidos ya empezaron o terminaron y no se registraron picks antes."}
          </EmptyState>
        )}

        {hasPicks &&
          (legsQuery.isPending ? (
            <>
              <Skeleton height={260} />
              <Skeleton height={400} />
            </>
          ) : legsQuery.isError ? (
            <ErrorState message={(legsQuery.error as Error).message} onRetry={() => legsQuery.refetch()} />
          ) : (
            <>
              <ParlaysSection
                config={config}
                legs={shownLegs}
                games={games}
                bookmaker={priceBook}
                date={slipDate}
                wholeLabel={wholeLabel}
                onCustomize={openPrefs}
              />
              <LegsTable
                config={config}
                legs={shownLegs}
                games={games}
                date={slipDate}
                bookmaker={priceBook}
                showDay={multiDay}
                onCustomize={openPrefs}
              />
            </>
          ))}
      </div>
      <BetSlip bookmaker={bookmaker} apiBooks={bookmakers} />
      <PreferencesPanel
        config={config}
        open={prefsOpen}
        onClose={closePrefs}
        legs={shownLegs}
        bookmaker={priceBook}
        bookmakers={bookmakers}
        systemBook={bookmaker}
        leagues={meta.data?.sports[config.key].leagues ?? []}
      />
      <AvailabilityPanel game={gameList.find((g) => g.id === absencesGameId) ?? null} onClose={closeAbsences} />
    </div>
  );
}
