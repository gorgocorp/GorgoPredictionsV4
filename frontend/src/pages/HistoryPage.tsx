import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { EmptyState, ErrorState, ResultBadge, Skeleton } from "../components/States";
import { api, toQuery, type HistoryFilters, type HistoryParlay, type HistorySummary } from "../lib/api";
import { dateTime, localTime, longDate, odds, pct, signedPct } from "../lib/format";
import { asSport, SPORT_KEYS, SPORTS } from "../lib/sports";

const PAGE_SIZE = 20;
const MODES = [
  { value: "", label: "Todos" },
  { value: "prob", label: "Máx. probabilidad" },
  { value: "ev", label: "Máx. valor" },
] as const;
const RESULTS = [
  { value: "", label: "Todos" },
  { value: "won", label: "Ganados" },
  { value: "lost", label: "Perdidos" },
  { value: "pending", label: "Pendientes" },
] as const;

function units(value: number): string {
  return `${value >= 0 ? "+" : "−"}${Math.abs(value).toFixed(2)} u`;
}

function Summary({ s }: { s: HistorySummary }) {
  return (
    <>
      <div className="kpis">
        <div className="card kpi">
          <span className="stat-label">Parlays acertados</span>
          <span className="kpi-value">
            {s.won} <span className="muted small">de {s.settled} liquidados</span>
          </span>
          <span className="muted xs">
            {s.settled > 0
              ? `El modelo esperaba ${s.expected_wins.toFixed(1)} (${pct(s.expected_wins / s.settled, 0)} en promedio)`
              : "Todavía no termina ningún partido de estos parlays"}
          </span>
        </div>
        <div className="card kpi">
          <span className="stat-label">Unidades (1 por parlay)</span>
          <span className={`kpi-value ${s.profit_units !== null && s.profit_units > 0 ? "ev-pos" : ""}`}>
            {s.profit_units !== null ? units(s.profit_units) : "—"}
          </span>
          <span className="muted xs">
            {s.profit_units !== null
              ? `ROI ${signedPct(s.roi)} · ${s.with_odds} parlays con momio de la casa`
              : "Sólo cuentan parlays con momio de la casa en todas sus piernas"}
          </span>
        </div>
        <div className="card kpi">
          <span className="stat-label">Registrados</span>
          <span className="kpi-value">{s.parlays}</span>
          <span className="muted xs">
            {s.pending} pendientes · {s.lost} perdidos · {s.void} anulados
          </span>
        </div>
      </div>
      {s.settled > 0 && (
        <div className="card table-wrap">
          <table className="data">
            <caption className="visually-hidden">Aciertos por número de piernas</caption>
            <thead>
              <tr>
                <th scope="col">Piernas</th>
                <th scope="col" className="r">
                  Liquidados
                </th>
                <th scope="col" className="r">
                  Acertados
                </th>
                <th scope="col" className="r" title="Suma de las probabilidades del modelo">
                  Esperados por el modelo
                </th>
              </tr>
            </thead>
            <tbody>
              {s.by_size
                .filter((b) => b.settled > 0)
                .map((b) => (
                  <tr key={b.n_legs}>
                    <td className="num">{b.n_legs}</td>
                    <td className="r num">{b.settled}</td>
                    <td className="r num">
                      {b.won} ({pct(b.won / b.settled)})
                    </td>
                    <td className="r num">
                      {b.expected.toFixed(1)} ({pct(b.expected / b.settled)})
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function ParlayEvidence({ p }: { p: HistoryParlay }) {
  const sport = SPORTS[p.sport];
  return (
    <article className="card parlay-card" aria-label={`Parlay de ${sport.label} de ${p.n_legs} piernas del ${p.day}`}>
      <div className="parlay-head">
        <div>
          <h3>
            <span className="sport-tag" data-sport={p.sport}>
              {sport.label}
            </span> {p.n_legs} piernas
          </h3>
          <span className="muted xs">
            {p.mode === "prob" ? "Máxima probabilidad" : "Máximo valor"}
            {p.preseason && " · pretemporada"}
          </span>
        </div>
        <ResultBadge result={p.result} pendingLabel="Pendiente" />
      </div>

      <div className="parlay-stats">
        <div className="stat">
          <span className="stat-label">Prob. predicha</span>
          <span className="stat-value">{pct(p.probability, 1)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Momio {p.bookmaker ?? "casa"}</span>
          <span className="stat-value">{p.odd ? p.odd.toFixed(2) : "—"}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Ganancia (1 u)</span>
          <span className={`stat-value ${p.profit !== null && p.profit > 0 ? "ev-pos" : ""}`}>
            {p.profit !== null ? units(p.profit) : p.result === "won" ? "Sin momio" : "—"}
          </span>
        </div>
      </div>

      <p className="evidence-line xs">
        <span>
          Registrado el <strong>{dateTime(p.evaluated_at)}</strong> · primer partido {dateTime(p.first_start)}
        </span>{" "}
        {p.recorded_before_start ? (
          <span className="badge badge-won" title="La predicción quedó guardada antes de que empezara el primer partido">
            <span aria-hidden="true">✓</span> Antes del partido
          </span>
        ) : (
          <span className="badge badge-warn">
            <span aria-hidden="true">!</span> Registro posterior al inicio
          </span>
        )}
      </p>

      <ol className="leg-list">
        {p.legs.map((l) => (
          <li key={l.pick_id} className="leg-item">
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
              <span className="num">{pct(l.p_model)}</span>
              <br />
              <span className="muted xs num">{l.odd ? odds(l.odd) : "sin momio"}</span>
              <br />
              <ResultBadge result={l.result} pendingLabel="Pendiente" />
            </span>
          </li>
        ))}
      </ol>
    </article>
  );
}

export function HistoryPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("pagina") ?? 1));
  const sport = asSport(params.get("deporte"));
  const filters: HistoryFilters = {
    sport: sport ?? undefined,
    desde: params.get("desde") ?? undefined,
    hasta: params.get("hasta") ?? undefined,
    mode: (params.get("modo") as HistoryFilters["mode"]) || undefined,
    n_legs: params.get("piernas") ? Number(params.get("piernas")) : undefined,
    result: (params.get("resultado") as HistoryFilters["result"]) || undefined,
    include_preseason: params.get("pretemporada") !== "0",
  };
  const history = useQuery({
    queryKey: ["history", filters, page],
    queryFn: () => api.history({ ...filters, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
    placeholderData: keepPreviousData,
    refetchInterval: 300_000,
  });

  const update = (changes: Record<string, string | null>, resetPage = true) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(changes)) {
          if (v === null || v === "") next.delete(k);
          else next.set(k, v);
        }
        if (resetPage) next.delete("pagina");
        return next;
      },
      { replace: true },
    );

  const pages = history.data ? Math.max(1, Math.ceil(history.data.total / PAGE_SIZE)) : 1;
  const byDate = new Map<string, HistoryParlay[]>();
  for (const p of history.data?.items ?? []) byDate.set(p.day, [...(byDate.get(p.day) ?? []), p]);

  return (
    <div className="day-main">
      <div className="section-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Historial</h1>
          <p className="muted small" style={{ margin: 0 }}>
            Cada parlay que sugirió el sistema, registrado antes de los partidos y liquidado con el resultado real.
          </p>
        </div>
        <a className="btn" href={`/api/history.csv?${toQuery(filters)}`} download>
          Descargar CSV
        </a>
      </div>

      <div className="filters">
        <div className="segmented" role="group" aria-label="Deporte">
          <button type="button" aria-pressed={sport === null} onClick={() => update({ deporte: null })}>
            Todos
          </button>
          {SPORT_KEYS.map((k) => (
            <button key={k} type="button" aria-pressed={sport === k} onClick={() => update({ deporte: k })}>
              {SPORTS[k].label}
            </button>
          ))}
        </div>
        <label className="field">
          Desde
          <input className="input num" type="date" value={filters.desde ?? ""} onChange={(e) => update({ desde: e.target.value })} />
        </label>
        <label className="field">
          Hasta
          <input className="input num" type="date" value={filters.hasta ?? ""} onChange={(e) => update({ hasta: e.target.value })} />
        </label>
        <div className="segmented" role="group" aria-label="Tipo de parlay">
          {MODES.map((m) => (
            <button key={m.value} type="button" aria-pressed={(filters.mode ?? "") === m.value} onClick={() => update({ modo: m.value || null })}>
              {m.label}
            </button>
          ))}
        </div>
        <label className="field">
          Piernas
          <select className="select" value={filters.n_legs ?? ""} onChange={(e) => update({ piernas: e.target.value || null })}>
            <option value="">Todas</option>
            {[2, 3, 4, 5, 6, 7, 8].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <div className="segmented" role="group" aria-label="Resultado">
          {RESULTS.map((r) => (
            <button key={r.value} type="button" aria-pressed={(filters.result ?? "") === r.value} onClick={() => update({ resultado: r.value || null })}>
              {r.label}
            </button>
          ))}
        </div>
        {sport !== "futbol" && (
          <label className="toggle" title="Partidos de pretemporada de la NBA">
            <input type="checkbox" checked={filters.include_preseason} onChange={(e) => update({ pretemporada: e.target.checked ? null : "0" })} />
            Incluir pretemporada NBA
          </label>
        )}
      </div>

      {history.isPending ? (
        <>
          <div className="kpis">
            <Skeleton height={96} />
            <Skeleton height={96} />
            <Skeleton height={96} />
          </div>
          <Skeleton height={300} />
        </>
      ) : history.isError ? (
        <ErrorState message={(history.error as Error).message} onRetry={() => history.refetch()} />
      ) : history.data.total === 0 ? (
        <EmptyState
          title="No hay parlays con estos filtros"
          action={
            <button type="button" className="btn" onClick={() => setParams({}, { replace: true })}>
              Quitar filtros
            </button>
          }
        >
          El sistema registra los parlays de los próximos días en cada corrida del scheduler (cada 6 horas y antes de cada horario de
          partidos).
        </EmptyState>
      ) : (
        <>
          <Summary s={history.data.summary} />
          {history.data.summary.settled === 0 && (
            <div className="banner banner-info">
              <span aria-hidden="true">i</span>
              <span>Aún no hay resultados: cada parlay se liquida solo cuando terminan todos sus partidos.</span>
            </div>
          )}
          {[...byDate].map(([date, items]) => (
            <section key={date} aria-label={longDate(date)}>
              <h2 className="history-day">{longDate(date)}</h2>
              <div className="parlay-list">
                {items.map((p) => (
                  <ParlayEvidence key={p.id} p={p} />
                ))}
              </div>
            </section>
          ))}
          {pages > 1 && (
            <nav className="pager card" aria-label="Paginación del historial">
              <button type="button" className="btn btn-sm" disabled={page <= 1} onClick={() => update({ pagina: String(page - 1) }, false)}>
                Anterior
              </button>
              <span className="muted num">
                Página {page} de {pages} · {history.data.total} parlays
              </span>
              <button type="button" className="btn btn-sm" disabled={page >= pages} onClick={() => update({ pagina: String(page + 1) }, false)}>
                Siguiente
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
