import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { DateBar } from "../../components/DateBar";
import { SlateBody } from "../../components/SlateBody";
import { EmptyState, ErrorState, Skeleton, SkeletonCards, Spinner } from "../../components/States";
import { useToast } from "../../components/Toast";
import { api, ApiError } from "../../lib/api";
import { longDate, relativeTime } from "../../lib/format";
import { invalidateSport } from "../../lib/queries";
import { isAdmin, useViewer } from "../../lib/session";
import { AvailabilityPanel } from "./AvailabilityPanel";
import { nbaApi } from "./api";
import { NBA, PHASE_LABELS } from "./config";
import { GameCard } from "./GameCard";

export function DayPage() {
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();
  const notify = useToast();
  const admin = isAdmin(useViewer());
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta, refetchInterval: 60_000 });
  const today = meta.data?.today;
  const date = params.get("fecha") ?? today;

  const day = useQuery({ queryKey: ["nba", "day", date], queryFn: () => nbaApi.day(date!), enabled: !!date, refetchInterval: 120_000 });
  const legs = useQuery({ queryKey: ["nba", "legs", date], queryFn: () => nbaApi.legs(date!), enabled: !!date, refetchInterval: 120_000 });
  const { data: calendar } = useQuery({ queryKey: ["nba", "calendar"], queryFn: nbaApi.calendar, staleTime: 3_600_000 });

  const refresh = useMutation({
    mutationFn: () => nbaApi.refresh(date!),
    onSuccess: (r) => {
      notify(
        r.games === 0
          ? "No hay partidos por empezar ese día: los picks de partidos iniciados quedan congelados"
          : `Listo: ${r.picks} piernas y ${r.parlays} parlays de ${r.games} partidos`,
      );
      invalidateSport(queryClient, "nba");
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
  const openGames = gameList.filter((g) => g.status === "NS" && new Date(g.starts_at).getTime() > Date.now());
  const phases = new Set(gameList.map((g) => g.phase));
  const lastEvaluated = (legs.data ?? []).reduce<string | null>((max, l) => (!max || l.evaluated_at > max ? l.evaluated_at : max), null);
  const nextGameDay = calendar?.find((d) => d.date > date)?.date;
  const setDate = (d: string) => setParams(d === today ? {} : { fecha: d });

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
    <>
      <div className="section-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>
            <span className="sport-tag" data-sport="nba">
              NBA
            </span> {longDate(date)}
          </h1>
          <p className="muted small" style={{ margin: 0 }}>
            {[...phases].map((p) => PHASE_LABELS[p]).join(" · ") || "Sin partidos"}
            {" · "}hora local
            {lastEvaluated && <> · Picks calculados {relativeTime(lastEvaluated)}</>}
          </p>
        </div>
        <div className="card-actions">
          <DateBar date={date} today={today} calendar={calendar} onChange={setDate} />
          {refreshButton}
        </div>
      </div>

      {phases.has("preseason") && (
        <div className="banner banner-warn">
          <span aria-hidden="true">!</span>
          <span>
            Pretemporada: las estrellas juegan pocos minutos y casi no hay momios. Los picks se registran pero no cuentan en el
            rendimiento. La temporada regular empieza el 20 de octubre.
          </span>
        </div>
      )}
    </>
  );

  return (
    <SlateBody
      config={NBA}
      header={header}
      games={{ ...day, data: day.data?.games }}
      legs={legs}
      parlays={day.data?.parlays}
      multiDay={false}
      slipDate={date}
      gamesNote="Horas en tu zona horaria · puntos proyectados por el modelo"
      refreshButton={refreshButton}
      noPicksMessage={`El sistema los calcula cada 6 horas para hoy y mañana, y otra vez antes de cada horario de partidos.${admin ? " Puedes calcularlos ahora." : ""}`}
      emptyGames={
        <EmptyState
          title="No hay partidos de la NBA este día"
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
