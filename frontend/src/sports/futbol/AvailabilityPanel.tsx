import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { ErrorState, Skeleton, Spinner } from "../../components/States";
import { useToast } from "../../components/Toast";
import { ApiError } from "../../lib/api";
import { localTime } from "../../lib/format";
import { invalidateSport } from "../../lib/queries";
import { futbolApi, type Game, type RosterPlayer } from "./api";
import { AVAILABILITY_LABELS, POSITION_LABELS } from "./config";

type Choice = "report" | "available" | "out";

const BADGE: Record<string, string> = {
  out: "badge-lost",
  questionable: "badge-warn",
  available: "badge-won",
};

function choiceOf(p: RosterPlayer): Choice {
  if (!p.manual) return "report";
  return p.status === "out" ? "out" : "available";
}

function PlayerRow({
  player,
  fixtureId,
  disabled,
  lineups,
}: {
  player: RosterPlayer;
  fixtureId: number;
  disabled: boolean;
  lineups: boolean;
}) {
  const queryClient = useQueryClient();
  const notify = useToast();
  const mutation = useMutation({
    mutationFn: (choice: Choice) => futbolApi.setAvailability(fixtureId, player.player_id, choice === "report" ? null : choice),
    onSuccess: (_r, choice) => {
      notify(
        choice === "out"
          ? `${player.name}: marcado como baja (sin sus props). Picks y parlays recalculados.`
          : choice === "available"
            ? `${player.name}: marcado como disponible. Recalculado.`
            : `${player.name}: se usa lo que diga la API. Recalculado.`,
      );
      invalidateSport(queryClient, "futbol");
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : "No se pudo guardar"),
  });

  const current = choiceOf(player);
  const options: { value: Choice; label: string }[] = [
    { value: "report", label: player.report_status ? "API" : "Normal" },
    { value: "available", label: "Juega" },
    { value: "out", label: "Baja" },
  ];

  return (
    <li className="avail-row">
      <div className="avail-name">
        <span>
          <strong>{player.name}</strong>{" "}
          {player.position && <span className="muted xs">{POSITION_LABELS[player.position] ?? player.position}</span>}
          {player.report_status && (
            <>
              {" "}
              <span className={`badge ${BADGE[player.report_status]}`} title={player.reason ?? undefined}>
                {AVAILABILITY_LABELS[player.report_status]}
              </span>
            </>
          )}
          {lineups && player.is_starter !== null && (
            <>
              {" "}
              <span className={`badge ${player.is_starter ? "badge-won" : "badge-neutral"}`}>{player.is_starter ? "Titular" : "Suplente"}</span>
            </>
          )}
        </span>
        <span className="muted xs num">
          {player.starts} de 6 como titular · {player.minutes} min · {player.goals} G {player.assists} A
          {player.reason ? ` · ${player.reason}` : ""}
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
  const roster = useQuery({
    queryKey: ["futbol", "roster", game?.id],
    queryFn: () => futbolApi.roster(game!.id),
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
  const started = game.status !== "NS";

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div ref={panelRef} className="drawer" role="dialog" aria-modal="true" aria-labelledby="avail-title" tabIndex={-1}>
        <div className="drawer-head">
          <div>
            <h2 id="avail-title">Bajas</h2>
            <p className="muted small" style={{ margin: 0 }}>
              {game.home.name} vs {game.away.name} · {game.league.name} · {localTime(game.starts_at)}
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
              Bajas y dudas según API-Football (lesiones, suspensiones; se actualiza cada pocas horas y no todas las ligas lo
              publican). Marcar a alguien como baja quita sus props. Los goles esperados no se ajustan por bajas: en el
              backtest hacerlo empeoró el pronóstico (los ratings ya reflejan las ausencias largas).
              {roster.data?.lineups && " Ya hay alineaciones confirmadas: mandan sobre esta lista."}
            </span>
          </div>
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
            (["home", "away"] as const).map((side) => {
              const players = roster.data.players.filter((p) => p.team === side);
              const others = roster.data.others.filter((u) => u.team === side);
              return (
                <section key={side} aria-label={side === "home" ? game.home.name : game.away.name}>
                  <h3 style={{ marginBottom: "var(--space-2)" }}>{side === "home" ? game.home.name : game.away.name}</h3>
                  {players.length === 0 ? (
                    <p className="muted small">Sin jugadores con partidos recientes en nuestra base.</p>
                  ) : (
                    <ul className="avail-list">
                      {players.map((p) => (
                        <PlayerRow key={p.player_id} player={p} fixtureId={game.id} disabled={started} lineups={roster.data.lineups} />
                      ))}
                    </ul>
                  )}
                  {others.length > 0 && (
                    <p className="muted xs">
                      También en la lista de la API (sin partidos recientes):{" "}
                      {others.map((u) => `${u.name} (${AVAILABILITY_LABELS[u.status].toLowerCase()}${u.reason ? `, ${u.reason}` : ""})`).join(", ")}.
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
