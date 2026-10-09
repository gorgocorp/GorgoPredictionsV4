import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { DateBar } from "../../components/DateBar";
import { SlateBody } from "../../components/SlateBody";
import { EmptyState, ErrorState, Skeleton, SkeletonCards, Spinner } from "../../components/States";
import { useToast } from "../../components/Toast";
import { api, ApiError } from "../../lib/api";
import { longDate, relativeTime } from "../../lib/format";
import { invalidateSport } from "../../lib/queries";
import { isAdmin, useViewer } from "../../lib/session";
import { AvailabilityPanel } from "./AvailabilityPanel";
import { futbolApi } from "./api";
import { FUTBOL } from "./config";
import { GameCard } from "./GameCard";

export function DayPage() {
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();
  const notify = useToast();
  const admin = isAdmin(useViewer());
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta, refetchInterval: 60_000 });
  const today = meta.data?.today;
  const date = params.get("fecha") ?? today;

  const day = useQuery({ queryKey: ["futbol", "day", date], queryFn: () => futbolApi.day(date!), enabled: !!date, refetchInterval: 120_000 });
  const legs = useQuery({ queryKey: ["futbol", "legs", date], queryFn: () => futbolApi.legs(date!), enabled: !!date, refetchInterval: 120_000 });
  const { data: calendar } = useQuery({ queryKey: ["futbol", "calendar"], queryFn: futbolApi.calendar, staleTime: 3_600_000 });

  const refresh = useMutation({
    mutationFn: () => futbolApi.refresh(date!),
    onSuccess: (r) => {
      notify(
        r.games === 0
          ? "No hay partidos por empezar ese día: los picks de partidos iniciados quedan congelados"
          : `Listo: ${r.picks} piernas y ${r.parlays} parlays de ${r.games} partidos`,
      );
      invalidateSport(queryClient, "futbol");
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : "No se pudo recalcular"),
  });

  if (meta.isError) return <ErrorState message={(meta.error as Error).message} onRetry={() => meta.refetch()} />;
  if (!date || !today) {
    return (
      <div className="day-main">
        <Skeleton height={40} width={320} />
        <SkeletonCards count={6} height={170} />
      </div>
    );
  }

  const gameList = day.data?.games ?? [];
  const leagues = new Set(gameList.map((g) => g.league.id)).size;
  const openGames = gameList.filter((g) => g.status === "NS" && new Date(g.starts_at).getTime() > Date.now());
  const lastEvaluated = (legs.data ?? []).reduce<string | null>((max, l) => (!max || l.evaluated_at > max ? l.evaluated_at : max), null);
  const nextGameDay = calendar?.find((d) => d.date > date)?.date;
  const setDate = (d: string) => setParams(d === today ? {} : { fecha: d });
  const league = params.get("liga");

  const refreshButton = admin && (
    <button
      type="button"
      className="btn btn-primary"
      onClick={() => refresh.mutate()}
      disabled={refresh.isPending || openGames.length === 0}
      title={openGames.length === 0 ? "Sólo se recalculan partidos que no han empezado" : "Recalcula con los datos y momios más recientes"}
    >
      {refresh.isPending ? <Spinner label="Calculando" /> : null}
      {refresh.isPending ? "Calculando…" : "Recalcular"}
    </button>
  );

  const header = (
    <div className="section-head" style={{ marginBottom: 0 }}>
      <div>
        <h1>
          <span className="sport-tag" data-sport="futbol">
            Fútbol
          </span> {longDate(date)}
        </h1>
        <p className="muted small" style={{ margin: 0 }}>
          {gameList.length > 0 ? `${gameList.length} partidos en ${leagues} ${leagues === 1 ? "liga" : "ligas"}` : "Sin partidos"}
          {" · "}hora local
          {lastEvaluated && <> · Picks calculados {relativeTime(lastEvaluated)}</>}
          {" · "}
          <Link to={league ? `/futbol/jornada?liga=${league}` : "/futbol/jornada"}>Parlay de varios días (jornada o fin de semana)</Link>
        </p>
      </div>
      <div className="card-actions">
        <DateBar date={date} today={today} calendar={calendar} onChange={setDate} />
        {refreshButton}
      </div>
    </div>
  );

  return (
    <SlateBody
      config={FUTBOL}
      header={header}
      games={{ ...day, data: day.data?.games }}
      legs={legs}
      parlays={day.data?.parlays}
      multiDay={false}
      slipDate={date}
      gamesNote="Goles esperados por el modelo · todo a 90 minutos"
      refreshButton={refreshButton}
      noPicksMessage={`El sistema los calcula cada 6 horas para los próximos 7 días, y otra vez antes de cada horario de partidos.${admin ? " Puedes calcularlos ahora." : ""}`}
      emptyGames={
        <EmptyState
          title="No hay partidos de tus ligas este día"
          action={
            nextGameDay && (
              <button type="button" className="btn" onClick={() => setDate(nextGameDay)}>
                Ir al siguiente día con partidos
              </button>
            )
          }
        />
      }
      GameCard={GameCard}
      AvailabilityPanel={AvailabilityPanel}
    />
  );
}
