import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState, ErrorState, ResultBadge, Skeleton, Spinner } from "../components/States";
import { useToast } from "../components/Toast";
import { api, ApiError, type Bet, type BetsSummary } from "../lib/api";
import { american, dateTime, localTime, money, pct, signedPct } from "../lib/format";
import { useSportContext } from "../lib/sportContext";
import { SPORTS } from "../lib/sports";

function Summary({ s }: { s: BetsSummary }) {
  const decided = s.won + s.lost;
  return (
    <div className="kpis">
      <div className="card kpi">
        <span className="stat-label">Ganancia</span>
        <span className={`kpi-value ${s.profit > 0 ? "ev-pos" : ""}`}>
          {s.profit >= 0 ? "+" : "−"}
          {money(Math.abs(s.profit))}
        </span>
        <span className="muted xs">
          Apostado {money(s.staked)} · regresó {money(s.returned)}
          {s.roi !== null && ` · ROI ${signedPct(s.roi)}`}
        </span>
      </div>
      <div className="card kpi">
        <span className="stat-label">Boletos acertados</span>
        <span className="kpi-value">
          {s.won} <span className="muted small">de {decided}</span>
        </span>
        <span className="muted xs">
          {decided > 0
            ? `El modelo esperaba ${s.expected_wins.toFixed(1)}; la casa, ${s.book_expected_wins.toFixed(1)}`
            : "Todavía no se liquida ningún boleto"}
        </span>
      </div>
      <div className="card kpi">
        <span className="stat-label">Pendientes</span>
        <span className="kpi-value">{s.pending}</span>
        <span className="muted xs">
          {money(s.pending_stake)} en juego · {s.void} anulados
        </span>
      </div>
    </div>
  );
}

function BetCard({ bet }: { bet: Bet }) {
  const queryClient = useQueryClient();
  const notify = useToast();
  const [confirming, setConfirming] = useState(false);
  const remove = useMutation({
    mutationFn: () => api.deleteBet(bet.id),
    onSuccess: () => {
      notify("Apuesta borrada");
      queryClient.invalidateQueries({ queryKey: ["bets"] });
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : "No se pudo borrar"),
  });
  const sports = [...new Set(bet.legs.map((l) => SPORTS[l.sport].label))];

  return (
    <article className="card parlay-card" aria-label={`Apuesta de ${bet.legs.length} piernas en ${bet.bookmaker}`}>
      <div className="parlay-head">
        <div>
          <h3>
            {bet.bookmaker} · {bet.legs.length} {bet.legs.length === 1 ? "pierna" : "piernas"}
          </h3>
          <span className="muted xs">
            {money(bet.stake)} a {american(bet.odd)} ({bet.odd.toFixed(2)}) · {sports.join(" y ")}
          </span>
        </div>
        <ResultBadge result={bet.result} pendingLabel="Pendiente" />
      </div>

      <div className="parlay-stats">
        <div className="stat">
          <span className="stat-label">Modelo</span>
          <span className="stat-value">{pct(bet.model_probability, 1)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">{bet.bookmaker}</span>
          <span className="stat-value">{pct(bet.book_probability, 1)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">{bet.result ? "Resultado" : "Pago posible"}</span>
          <span className={`stat-value ${bet.profit !== null && bet.profit > 0 ? "ev-pos" : ""}`}>
            {bet.profit !== null ? `${bet.profit >= 0 ? "+" : "−"}${money(Math.abs(bet.profit))}` : money(bet.stake * bet.odd)}
          </span>
        </div>
      </div>

      <p className="evidence-line xs">
        <span>
          Registrada el <strong>{dateTime(bet.created_at)}</strong> · primer partido {dateTime(bet.first_start)}
        </span>{" "}
        <span className="badge badge-won" title="La apuesta quedó guardada antes de que empezara el primer partido">
          <span aria-hidden="true">✓</span> Antes del partido
        </span>
      </p>

      <ol className="leg-list">
        {bet.legs.map((l) => (
          <li key={l.position} className="leg-item">
            <span>
              <span className="muted xs">
                {l.competition} · {l.matchup} · {localTime(l.starts_at)}
              </span>
              <br />
              {l.description}
              <br />
              <span className="xs">
                Real: <strong>{l.outcome.text}</strong>
              </span>
            </span>
            <span className="leg-meta">
              <span className="num">
                {american(l.odd)} <span className="muted xs">({pct(1 / l.odd)})</span>
              </span>
              <br />
              <span className="muted xs num">modelo {pct(l.p_model)}</span>
              <br />
              <ResultBadge result={l.result} pendingLabel="Pendiente" />
            </span>
          </li>
        ))}
      </ol>

      {bet.can_delete && (
        <div className="card-actions">
          {confirming ? (
            <>
              <button type="button" className="btn btn-sm" onClick={() => remove.mutate()} disabled={remove.isPending}>
                {remove.isPending ? <Spinner label="Borrando" /> : null}
                Sí, borrar
              </button>
              <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirming(false)}>
                Cancelar
              </button>
            </>
          ) : (
            <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirming(true)}>
              Borrar (sólo antes del partido)
            </button>
          )}
        </div>
      )}
    </article>
  );
}

export function MyBetsPage() {
  const bets = useQuery({ queryKey: ["bets"], queryFn: api.bets, refetchInterval: 120_000 });
  const { sport } = useSportContext();

  return (
    <div className="day-main">
      <div className="section-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Mis apuestas</h1>
          <p className="muted small" style={{ margin: 0 }}>
            Lo que apostaste en tu casa (NBA, fútbol o mezclado), registrado antes de los partidos y liquidado solo con los resultados
            reales.
          </p>
        </div>
      </div>

      {bets.isPending ? (
        <>
          <div className="kpis">
            <Skeleton height={96} />
            <Skeleton height={96} />
            <Skeleton height={96} />
          </div>
          <Skeleton height={260} />
        </>
      ) : bets.isError ? (
        <ErrorState message={(bets.error as Error).message} onRetry={() => bets.refetch()} />
      ) : bets.data.items.length === 0 ? (
        <EmptyState
          title="Registra tu primera apuesta"
          action={
            <Link className="btn" to={`/${sport}`}>
              Ir a los partidos del día
            </Link>
          }
        >
          Arma tu boleto, escribe los momios que te da tu casa (p. ej. Caliente) y pulsa “Registrar apuesta” antes de que empiece el
          primer partido. Se liquida solo con los resultados reales (en fútbol, el marcador a 90 minutos).
        </EmptyState>
      ) : (
        <>
          <Summary s={bets.data.summary} />
          <div className="parlay-list">
            {bets.data.items.map((b) => (
              <BetCard key={b.id} bet={b} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
