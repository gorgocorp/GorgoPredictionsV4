import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { ErrorState, Skeleton, Spinner } from "../../components/States";
import { useToast } from "../../components/Toast";
import { ApiError } from "../../lib/api";
import { localTime, relativeTime } from "../../lib/format";
import { invalidateSport } from "../../lib/queries";
import { isAdmin, useViewer } from "../../lib/session";
import { nbaApi, type Game, type RosterPlayer } from "./api";
import { AVAILABILITY_LABELS } from "./config";

type Choice = "report" | "available" | "out";

const BADGE: Record<string, string> = {
  out: "badge-lost",
  doubtful: "badge-warn",
  questionable: "badge-warn",
  probable: "badge-neutral",
  available: "badge-won",
};

function choiceOf(p: RosterPlayer): Choice {
  if (!p.manual) return "report";
  return p.status === "out" ? "out" : "available";
}

function PlayerRow({ player, date, disabled }: { player: RosterPlayer; date: string; disabled: boolean }) {
  const queryClient = useQueryClient();
  const notify = useToast();
  const mutation = useMutation({
    mutationFn: (choice: Choice) => nbaApi.setAvailability(date, player.player_id, choice === "report" ? null : choice),
    onSuccess: (_r, choice) => {
      notify(
        choice === "out"
          ? `${player.name}: marcado como baja. Proyecciones y parlays recalculados.`
          : choice === "available"
            ? `${player.name}: marcado como disponible. Recalculado.`
            : `${player.name}: se usa el reporte oficial. Recalculado.`,
      );
      invalidateSport(queryClient, "nba");
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : "No se pudo guardar"),
  });

  const current = choiceOf(player);
  const options: { value: Choice; label: string }[] = [
    { value: "report", label: player.report_status ? "Reporte" : "Normal" },
    { value: "available", label: "Juega" },
    { value: "out", label: "Baja" },
  ];

  return (
    <li className="avail-row">
      <div className="avail-name">
        <span>
          <strong>{player.name}</strong>
          {player.report_status && player.report_status !== "available" && (
            <>
              {" "}
              <span className={`badge ${BADGE[player.report_status]}`} title={player.reason ?? undefined}>
                {AVAILABILITY_LABELS[player.report_status]}
              </span>
            </>
          )}
        </span>
        <span className="muted xs num">
          {player.points.toFixed(1)} pts · {player.minutes.toFixed(0)} min (últ. {player.games})
          {player.reason && player.report_status !== "available" ? ` · ${player.reason}` : ""}
        </span>
      </div>
      <div className="segmented" role="radiogroup" aria-label={`Disponibilidad de ${player.name}`}>
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={current === o.value}
            disabled={disabled || mutation.isPending}
            onClick={() => current !== o.value && mutation.mutate(o.value)}
          >
            {mutation.isPending && mutation.variables === o.value ? <Spinner label="Guardando" /> : o.label}
          </button>
        ))}
      </div>
    </li>
  );
}

export function AvailabilityPanel({ game, onClose }: { game: Game | null; onClose: () => void }) {
  const panelRef = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<Element | null>(null);
  const viewer = useViewer();
  const roster = useQuery({
    queryKey: ["nba", "roster", game?.id],
    queryFn: () => nbaApi.roster(game!.id),
    enabled: game !== null,
  });

  useEffect(() => {
    if (!game) return;
    returnFocus.current = document.activeElement;
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      (returnFocus.current as HTMLElement | null)?.focus?.();
    };
  }, [game, onClose]);

  if (!game) return null;
  const report = game.injury_report;
  const started = game.status !== "NS";
  const admin = isAdmin(viewer);

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div ref={panelRef} className="drawer" role="dialog" aria-modal="true" aria-labelledby="avail-title" tabIndex={-1}>
        <div className="drawer-head">
          <div>
            <h2 id="avail-title">Bajas</h2>
            <p className="muted small" style={{ margin: 0 }}>
              {game.away.name} @ {game.home.name} · {localTime(game.starts_at)}
            </p>
          </div>
          <button type="button" className="btn btn-ghost btn-icon" aria-label="Cerrar" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="drawer-body">
          <div className="banner banner-info">
            <span aria-hidden="true">i</span>
            <span>
              {report.covered && report.report_at
                ? `Reporte oficial de lesiones de la NBA, actualizado ${relativeTime(report.report_at)}.`
                : "Todavía no hay reporte oficial para este partido (no se publica en pretemporada). Puedes marcar bajas a mano."}{" "}
              Marcar a alguien como baja quita sus props y ajusta la proyección de los dos equipos.
            </span>
          </div>
          {report.pending.length > 0 && (
            <div className="banner banner-warn">
              <span aria-hidden="true">!</span>
              <span>
                {report.pending.map((side) => (side === "home" ? game.home.name : game.away.name)).join(" y ")} todavía no entrega su
                lista de lesionados.
              </span>
            </div>
          )}
          {!admin && (
            <p className="muted small" style={{ margin: 0 }}>
              Sólo el administrador marca bajas a mano; aquí ves el estado de cada jugador.
            </p>
          )}
          {started && (
            <p className="muted small" style={{ margin: 0 }}>
              El partido ya empezó: los cambios ya no afectan sus picks (quedaron congelados).
            </p>
          )}

          {roster.isPending ? (
            <>
              <Skeleton height={56} />
              <Skeleton height={56} />
              <Skeleton height={56} />
            </>
          ) : roster.isError ? (
            <ErrorState message={(roster.error as Error).message} onRetry={() => roster.refetch()} />
          ) : (
            (["away", "home"] as const).map((side) => {
              const players = roster.data.players.filter((p) => p.team === side);
              const unmatched = roster.data.unmatched.filter((u) => u.team === side);
              return (
                <section key={side} aria-label={side === "home" ? game.home.name : game.away.name}>
                  <h3 style={{ marginBottom: "var(--space-2)" }}>
                    {side === "home" ? game.home.name : game.away.name}
                    {game.missing_points[side] > 0 && (
                      <span className="muted small"> · faltan {game.missing_points[side].toFixed(1)} pts por partido</span>
                    )}
                  </h3>
                  {players.length === 0 ? (
                    <p className="muted small">Sin jugadores de rotación con partidos oficiales recientes.</p>
                  ) : (
                    <ul className="avail-list">
                      {players.map((p) => (
                        <PlayerRow key={p.player_id} player={p} date={roster.data.date} disabled={started || !admin} />
                      ))}
                    </ul>
                  )}
                  {unmatched.length > 0 && (
                    <p className="muted xs">
                      En el reporte pero sin identificar en nuestra base: {unmatched.map((u) => `${u.name} (${AVAILABILITY_LABELS[u.status]})`).join(", ")}.
                    </p>
                  )}
                </section>
              );
            })
          )}
        </div>
      </div>
    </>
  );
}
