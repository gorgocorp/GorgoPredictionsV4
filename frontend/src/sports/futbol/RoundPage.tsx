import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { SlateBody } from "../../components/SlateBody";
import { EmptyState, ErrorState, Skeleton, SkeletonCards, Spinner } from "../../components/States";
import { useToast } from "../../components/Toast";
import { api, ApiError } from "../../lib/api";
import { longDate, shiftDate, shortDay, weekendRange } from "../../lib/format";
import { invalidateSport } from "../../lib/queries";
import { isAdmin, useViewer } from "../../lib/session";
import { AvailabilityPanel } from "./AvailabilityPanel";
import { futbolApi, type SlateFilter } from "./api";
import { FUTBOL, roundLabel } from "./config";
import { GameCard } from "./GameCard";

type Mode = "jornada" | "fechas";
const DEFAULT_LEAGUE = 262; // Liga MX
const MAX_DAYS = 14;

/**
 * Parlays de varios días: la jornada completa de una liga (aunque se juegue de viernes a domingo)
 * o cualquier rango de fechas (p. ej. todo el fin de semana, todas las ligas).
 */
export function RoundPage() {
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();
  const notify = useToast();
  const admin = isAdmin(useViewer());
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta, refetchInterval: 60_000 });
  const today = meta.data?.today;
  const mode: Mode = params.get("modo") === "fechas" ? "fechas" : "jornada";
  const leagues = meta.data?.sports.futbol.leagues ?? [];
  const league = Number(params.get("liga") ?? DEFAULT_LEAGUE);

  const rounds = useQuery({
    queryKey: ["futbol", "rounds", league],
    queryFn: () => futbolApi.rounds(league),
    enabled: mode === "jornada" && Number.isFinite(league),
    staleTime: 600_000,
  });
  const jornada = params.get("jornada") ?? rounds.data?.current ?? undefined;
  const weekend = today ? weekendRange(today) : undefined;
  const desde = params.get("desde") ?? weekend?.desde;
  const hasta = params.get("hasta") ?? weekend?.hasta;

  const filter: SlateFilter | null =
    mode === "jornada" ? (jornada ? { league, jornada } : null) : desde && hasta ? { desde, hasta } : null;
  const key = JSON.stringify(filter);
  const slate = useQuery({
    queryKey: ["futbol", "slate", key],
    queryFn: () => futbolApi.slate(filter!),
    enabled: filter !== null,
    refetchInterval: 120_000,
  });
  const legs = useQuery({
    queryKey: ["futbol", "slate-legs", key],
    queryFn: () => futbolApi.slateLegs(filter!),
    enabled: filter !== null,
    refetchInterval: 120_000,
  });

  const refresh = useMutation({
    mutationFn: () => futbolApi.slateRefresh(filter!),
    onSuccess: (r) => {
      notify(
        r.days === 0
          ? "No hay partidos por empezar: los picks de partidos iniciados quedan congelados"
          : `Listo: ${r.picks} piernas de ${r.games} partidos en ${r.days} ${r.days === 1 ? "día" : "días"}`,
      );
      invalidateSport(queryClient, "futbol");
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : "No se pudo recalcular"),
  });

  const update = (changes: Record<string, string | null>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(changes)) {
          if (v === null) next.delete(k);
          else next.set(k, v);
        }
        for (const k of ["partido", "pagina"]) next.delete(k);
        return next;
      },
      { replace: true },
    );

  if (meta.isError) return <ErrorState message={(meta.error as Error).message} onRetry={() => meta.refetch()} />;
  if (!today) {
    return (
      <div className="day-main">
        <Skeleton height={40} width={320} />
        <SkeletonCards count={6} height={170} />
      </div>
    );
  }

  const gameList = slate.data?.games ?? [];
  const openGames = gameList.filter((g) => g.status === "NS" && new Date(g.starts_at).getTime() > Date.now());
  const leagueName = leagues.find((l) => l.id === league)?.name ?? "Liga";
  const span = slate.data ? `${shortDay(slate.data.desde)} a ${shortDay(slate.data.hasta)}` : "";
  const days = new Set(gameList.map((g) => g.match_date)).size;

  const refreshButton = admin && (
    <button
      type="button"
      className="btn btn-primary"
      onClick={() => refresh.mutate()}
      disabled={refresh.isPending || openGames.length === 0}
      title={openGames.length === 0 ? "Sólo se recalculan partidos que no han empezado" : "Recalcula cada día con partidos por empezar"}
    >
      {refresh.isPending ? <Spinner label="Calculando" /> : null}
      {refresh.isPending ? "Calculando… (hasta un minuto)" : "Recalcular"}
    </button>
  );

  const quick = (label: string, d: string, h: string) => (
    <button type="button" className="btn btn-sm" aria-pressed={desde === d && hasta === h} onClick={() => update({ desde: d, hasta: h })}>
      {label}
    </button>
  );

  const header = (
    <>
      <div className="section-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>
            <span className="sport-tag" data-sport="futbol">
              Fútbol
            </span>{" "}
            {mode === "jornada" ? `${leagueName} · ${jornada ? roundLabel(jornada) : "Jornada"}` : "Varios días"}
          </h1>
          <p className="muted small" style={{ margin: 0 }}>
            {gameList.length > 0
              ? `${gameList.length} partidos · ${span}${days > 1 ? ` (${days} días)` : ""} · hora local`
              : mode === "fechas" && desde && hasta
                ? `${longDate(desde)} a ${longDate(hasta)}`
                : "Arma un parlay con partidos de varios días"}
          </p>
        </div>
        <div className="card-actions">{refreshButton}</div>
      </div>

      <div className="filters">
        <div className="segmented" role="group" aria-label="Cómo elegir los partidos">
          <button type="button" aria-pressed={mode === "jornada"} onClick={() => update({ modo: null, desde: null, hasta: null })}>
            Jornada de una liga
          </button>
          <button type="button" aria-pressed={mode === "fechas"} onClick={() => update({ modo: "fechas", jornada: null, liga: null })}>
            Rango de fechas
          </button>
        </div>

        {mode === "jornada" ? (
          <>
            <label className="field">
              Liga
              <select className="select" value={league} onChange={(e) => update({ liga: e.target.value, jornada: null })}>
                {leagues.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field" style={{ flex: "1 1 260px" }}>
              Jornada
              <select className="select" value={jornada ?? ""} disabled={!rounds.data} onChange={(e) => update({ jornada: e.target.value })}>
                {(rounds.data?.rounds ?? []).map((r) => (
                  <option key={r.round} value={r.round}>
                    {roundLabel(r.round)} · {shortDay(r.desde)}
                    {r.hasta !== r.desde ? ` a ${shortDay(r.hasta)}` : ""}
                    {r.open === 0 ? " (terminada)" : r.round === rounds.data?.current ? " (en curso)" : ""}
                  </option>
                ))}
              </select>
            </label>
          </>
        ) : (
          <>
            <label className="field">
              Desde
              <input className="input num" type="date" value={desde ?? ""} onChange={(e) => e.target.value && update({ desde: e.target.value })} />
            </label>
            <label className="field">
              Hasta
              <input
                className="input num"
                type="date"
                value={hasta ?? ""}
                min={desde}
                max={desde ? shiftDate(desde, MAX_DAYS - 1) : undefined}
                onChange={(e) => e.target.value && update({ hasta: e.target.value })}
              />
            </label>
            <div className="card-actions" role="group" aria-label="Rangos rápidos">
              {weekend && quick("Fin de semana", weekend.desde, weekend.hasta)}
              {quick("Próximos 3 días", today, shiftDate(today, 2))}
              {quick("Próximos 7 días", today, shiftDate(today, 6))}
            </div>
          </>
        )}
      </div>
      {rounds.isError && mode === "jornada" && <ErrorState message={(rounds.error as Error).message} onRetry={() => rounds.refetch()} />}
    </>
  );

  return (
    <SlateBody
      config={FUTBOL}
      header={header}
      games={{ ...slate, data: slate.data?.games }}
      legs={legs}
      multiDay
      slipDate={desde ?? today}
      gamesNote="Goles esperados por el modelo · todo a 90 minutos"
      refreshButton={refreshButton}
      wholeLabel={mode === "jornada" ? "Jornada completa" : "Todos los partidos"}
      noPicksMessage={`El sistema calcula los picks de los próximos 7 días en cada sincronización (cada 6 horas).${admin ? " Para partidos más lejanos o para tenerlos ya, recalcula." : ""}`}
      emptyGames={
        <EmptyState title={mode === "jornada" ? "Esta jornada no tiene partidos" : "No hay partidos de tus ligas en esas fechas"}>
          {mode === "fechas" ? "Prueba con otro rango (hasta 14 días)." : "Elige otra jornada."}
        </EmptyState>
      }
      GameCard={GameCard}
      AvailabilityPanel={AvailabilityPanel}
    />
  );
}
