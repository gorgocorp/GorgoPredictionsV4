import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { api, type CalibrationBin, type Performance, type PerformanceFilters } from "../lib/api";
import { BACKTESTS } from "../lib/backtest";
import { pct, signedPct } from "../lib/format";
import { useSportContext } from "../lib/sportContext";
import { SPORT_KEYS, SPORTS, type SportConfig } from "../lib/sports";

function CalibrationChart({ bins }: { bins: CalibrationBin[] }) {
  const size = 320;
  const pad = 36;
  const lo = 0.5;
  const scale = (v: number) => pad + ((v - lo) / (1 - lo)) * (size - 2 * pad);
  const y = (v: number) => size - scale(v);
  const maxN = Math.max(...bins.map((b) => b.n), 1);
  const ticks = [0.5, 0.6, 0.7, 0.8, 0.9, 1];

  return (
    <figure className="chart" style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Calibración: probabilidad predicha contra frecuencia real. La tabla de abajo tiene los mismos datos.">
        <g className="grid">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={scale(t)} x2={scale(t)} y1={y(lo)} y2={y(1)} />
              <line x1={scale(lo)} x2={scale(1)} y1={y(t)} y2={y(t)} />
            </g>
          ))}
        </g>
        <line x1={scale(lo)} y1={y(lo)} x2={scale(1)} y2={y(1)} stroke="var(--text-muted)" strokeDasharray="4 4" />
        <g className="axis">
          {ticks.map((t) => (
            <g key={t}>
              <text x={scale(t)} y={size - pad + 16} textAnchor="middle">
                {pct(t)}
              </text>
              <text x={pad - 6} y={y(t) + 4} textAnchor="end">
                {pct(t)}
              </text>
            </g>
          ))}
          <text x={size / 2} y={size - 4} textAnchor="middle">
            Predicho
          </text>
          <text x={10} y={size / 2} textAnchor="middle" transform={`rotate(-90 10 ${size / 2})`}>
            Real
          </text>
        </g>
        {bins.map((b) => (
          <circle
            key={b.lo}
            cx={scale(b.predicted)}
            cy={y(Math.max(lo, b.actual))}
            r={4 + 8 * Math.sqrt(b.n / maxN)}
            fill="var(--accent)"
            fillOpacity={0.75}
            stroke="var(--surface)"
          >
            <title>{`Predicho ${pct(b.predicted, 1)} · real ${pct(b.actual, 1)} · n=${b.n}`}</title>
          </circle>
        ))}
      </svg>
      <figcaption className="muted xs">
        Puntos sobre la diagonal = el modelo acierta lo que dice. Tamaño del punto = cantidad de piernas.
      </figcaption>
    </figure>
  );
}

function Kpis({ data }: { data: Performance }) {
  const { legs, model_vs_market: mvm, positive_ev: ev } = data;
  return (
    <div className="kpis">
      <div className="card kpi">
        <span className="stat-label">Piernas liquidadas</span>
        <span className="kpi-value">{legs.settled.toLocaleString("es-MX")}</span>
        <span className="muted xs">
          {pct(legs.settled ? legs.won / legs.settled : null, 1)} ganadas · {legs.void} anuladas
        </span>
      </div>
      <div className="card kpi">
        <span className="stat-label">Modelo vs mercado (Brier)</span>
        <span className="kpi-value">{mvm ? `${mvm.brier_model.toFixed(4)}` : "—"}</span>
        <span className="muted xs">
          {mvm ? `Mercado ${mvm.brier_market.toFixed(4)} · menor es mejor · n=${mvm.n}` : "Requiere piernas con momio liquidadas"}
        </span>
      </div>
      <div className="card kpi">
        <span className="stat-label">Piernas con EV positivo (1 u c/u)</span>
        <span className={`kpi-value ${ev && ev.roi > 0 ? "ev-pos" : ""}`}>{ev ? signedPct(ev.roi) : "—"}</span>
        <span className="muted xs">
          {ev ? `ROI · ${ev.n} piernas · ${pct(ev.hit_rate, 1)} acierto · ganancia ${ev.profit >= 0 ? "+" : ""}${ev.profit.toFixed(1)} u` : "Sin piernas con valor liquidadas"}
        </span>
      </div>
    </div>
  );
}

function ByMarket({ data, config }: { data: Performance; config: SportConfig }) {
  if (data.by_market.length === 0) return null;
  return (
    <section className="card card-pad" aria-labelledby="market-title">
      <h2 id="market-title" style={{ marginBottom: "var(--space-3)" }}>
        Por mercado
      </h2>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Mercado</th>
              <th scope="col" className="r">
                Piernas
              </th>
              <th scope="col" className="r" title="Probabilidad promedio que dio el modelo">
                Predicho
              </th>
              <th scope="col" className="r">
                Real
              </th>
              <th scope="col" className="r">
                Diferencia
              </th>
            </tr>
          </thead>
          <tbody>
            {data.by_market.map((m) => (
              <tr key={m.market}>
                <td>{config.marketLabels[m.market] ?? m.market}</td>
                <td className="r num">{m.n.toLocaleString("es-MX")}</td>
                <td className="r num">{pct(m.predicted, 1)}</td>
                <td className="r num">{pct(m.actual, 1)}</td>
                <td className="r num">{signedPct(m.actual - m.predicted)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function PerformancePage() {
  const [params, setParams] = useSearchParams();
  const { sport } = useSportContext();
  const config = SPORTS[sport];
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta, refetchInterval: 60_000 });
  const includePreseason = params.get("pretemporada") === "1";
  const league = params.get("liga") ? Number(params.get("liga")) : null;
  const filters: PerformanceFilters = sport === "nba" ? { include_preseason: includePreseason } : { league };
  const perf = useQuery({
    queryKey: ["performance", sport, filters],
    queryFn: () => api.performance(sport, filters),
    refetchInterval: 300_000,
  });
  const backtest = BACKTESTS[sport];

  const update = (changes: Record<string, string | null>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(changes)) {
          if (v === null) next.delete(k);
          else next.set(k, v);
        }
        return next;
      },
      { replace: true },
    );

  return (
    <div className="day-main">
      <div className="section-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Rendimiento de {config.label}</h1>
          <p className="muted small" style={{ margin: 0 }}>
            Resultados reales de los picks registrados antes de cada partido, con los momios de ese momento.
          </p>
        </div>
        <div className="card-actions">
          <div className="segmented" role="group" aria-label="Deporte">
            {SPORT_KEYS.map((k) => (
              <button key={k} type="button" aria-pressed={sport === k} onClick={() => update({ deporte: k })}>
                {SPORTS[k].label}
              </button>
            ))}
          </div>
          {sport === "nba" ? (
            <label className="toggle">
              <input type="checkbox" checked={includePreseason} onChange={(e) => update({ pretemporada: e.target.checked ? "1" : null })} />
              Incluir pretemporada
            </label>
          ) : (
            <label className="field">
              Liga
              <select className="select" value={league ?? ""} onChange={(e) => update({ liga: e.target.value || null })}>
                <option value="">Todas</option>
                {(meta.data?.sports.futbol.leagues ?? []).map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      </div>

      {perf.isPending ? (
        <>
          <div className="kpis">
            <Skeleton height={96} />
            <Skeleton height={96} />
            <Skeleton height={96} />
          </div>
          <Skeleton height={320} />
        </>
      ) : perf.isError ? (
        <ErrorState message={(perf.error as Error).message} onRetry={() => perf.refetch()} />
      ) : perf.data.legs.settled === 0 ? (
        <EmptyState title="Todavía no hay resultados">
          Los primeros llegan cuando terminen partidos con picks registrados. La liquidación es automática cada 6 horas.
          {sport === "nba" && !includePreseason && " Por defecto se excluye la pretemporada: la temporada regular empieza el 20 de octubre."}
        </EmptyState>
      ) : (
        <>
          <Kpis data={perf.data} />
          <ByMarket data={perf.data} config={config} />
          <div className="perf-grid">
            <section className="card card-pad" aria-labelledby="calib-title">
              <h2 id="calib-title" style={{ marginBottom: "var(--space-3)" }}>
                Calibración
              </h2>
              <CalibrationChart bins={perf.data.calibration} />
              <div className="table-wrap" style={{ marginTop: "var(--space-3)" }}>
                <table className="data">
                  <caption className="visually-hidden">Calibración por rango de probabilidad</caption>
                  <thead>
                    <tr>
                      <th scope="col">Rango</th>
                      <th scope="col" className="r">
                        Piernas
                      </th>
                      <th scope="col" className="r">
                        Predicho
                      </th>
                      <th scope="col" className="r">
                        Real
                      </th>
                      <th scope="col" className="r">
                        Diferencia
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {perf.data.calibration.map((b) => (
                      <tr key={b.lo}>
                        <td className="num">
                          {pct(b.lo)}–{pct(b.hi)}
                        </td>
                        <td className="r num">{b.n}</td>
                        <td className="r num">{pct(b.predicted, 1)}</td>
                        <td className="r num">{pct(b.actual, 1)}</td>
                        <td className="r num">{signedPct(b.actual - b.predicted)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            <section className="card card-pad" aria-labelledby="parlay-perf-title">
              <h2 id="parlay-perf-title" style={{ marginBottom: "var(--space-3)" }}>
                Parlays sugeridos
              </h2>
              {perf.data.parlays.length === 0 ? (
                <p className="muted small">Todavía no hay parlays liquidados.</p>
              ) : (
                <div className="table-wrap">
                  <table className="data">
                    <thead>
                      <tr>
                        <th scope="col">Modo</th>
                        <th scope="col" className="r">
                          Piernas
                        </th>
                        <th scope="col" className="r">
                          Parlays
                        </th>
                        <th scope="col" className="r">
                          Predicho
                        </th>
                        <th scope="col" className="r">
                          Real
                        </th>
                        <th scope="col" className="r">
                          ROI
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {perf.data.parlays.map((p) => (
                        <tr key={`${p.mode}-${p.n_legs}`}>
                          <td>{p.mode === "prob" ? "Máx. probabilidad" : "Máx. valor"}</td>
                          <td className="r num">{p.n_legs}</td>
                          <td className="r num">{p.count}</td>
                          <td className="r num">{pct(p.predicted, 1)}</td>
                          <td className="r num">{pct(p.actual, 1)}</td>
                          <td className={`r num ${p.roi !== null && p.roi > 0 ? "ev-pos" : ""}`} title={`${p.count_with_odds} con momio`}>
                            {signedPct(p.roi)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        </>
      )}

      <section className="card card-pad" aria-labelledby="backtest-title">
        <h2 id="backtest-title">{backtest.title}</h2>
        <p className="muted small">{backtest.info}</p>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th scope="col" className="r">
                  Piernas
                </th>
                <th scope="col" className="r">
                  {backtest.teamLabel}
                </th>
                <th scope="col" className="r">
                  Real
                </th>
                <th scope="col" className="r">
                  {backtest.propsLabel}
                </th>
                <th scope="col" className="r">
                  Real
                </th>
              </tr>
            </thead>
            <tbody>
              {backtest.rows.map((r) => (
                <tr key={r.n}>
                  <td className="r num">{r.n}</td>
                  <td className="r num">{pct(r.team[0])}</td>
                  <td className="r num">{pct(r.team[1])}</td>
                  <td className="r num">{pct(r.props[0])}</td>
                  <td className="r num">{pct(r.props[1])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
