import { useInfiniteQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { BrandMark, ThemeToggle } from "../components/Header";
import { EmptyState, ErrorState, ResultBadge, Skeleton, Spinner } from "../components/States";
import { api, ApiError, type HistorySummary, type ResultsParlay, type ResultsResponse, type SportKey } from "../lib/api";
import { legProbability } from "../lib/featured";
import { dateTime, odds, pct, signedPct, signedPts } from "../lib/format";
import { excludedText, fullDate, KIND_LABELS, KIND_SINGULAR, monthLabel, RESULTS_PATH, units } from "../lib/results";
import { lastSport } from "../lib/sportContext";
import { SPORT_KEYS, SPORTS } from "../lib/sports";

const PAGE = 20;

function Kpis({ data }: { data: ResultsResponse }) {
  const s = data.summary;
  const legs = data.legs;
  return (
    <div className="kpis">
      <div className="card kpi">
        <span className="stat-label">Parlays acertados</span>
        <span className="kpi-value">
          {s.won} <span className="muted small">de {s.settled}</span>
        </span>
        <span className="muted xs">
          {s.settled ? `Según lo prometido esperábamos ${s.expected_wins.toFixed(1)}` : "Todavía no termina ninguno"}
        </span>
      </div>
      <div className="card kpi">
        <span className="stat-label">Piernas acertadas</span>
        <span className="kpi-value">
          {legs.won} <span className="muted small">de {legs.settled}</span>
        </span>
        <span className="muted xs">
          {legs.settled ? `${pct(legs.won / legs.settled, 1)} · prometimos ${pct(legs.promised, 1)} en promedio` : "Todavía no termina ninguna"}
        </span>
      </div>
      <div className="card kpi">
        <span className="stat-label">A 1 unidad por parlay</span>
        <span className={`kpi-value ${s.profit_units !== null && s.profit_units > 0 ? "ev-pos" : ""}`}>{units(s.profit_units)}</span>
        <span className="muted xs">
          {s.roi === null ? "Sin parlays con momio liquidados" : `ROI ${signedPct(s.roi)} · ${s.with_odds} parlays con momio`}
        </span>
      </div>
      <div className="card kpi">
        <span className="stat-label">En juego</span>
        <span className="kpi-value">{s.pending}</span>
        <span className="muted xs">Aparecen aquí cuando terminan sus partidos</span>
      </div>
    </div>
  );
}

function SummaryCells({ s }: { s: HistorySummary }) {
  return (
    <>
      <td className="r num">{s.settled}</td>
      <td className="r num">{s.won}</td>
      <td className="r num">{s.expected_wins.toFixed(1)}</td>
      <td className={`r num ${s.profit_units !== null && s.profit_units > 0 ? "ev-pos" : ""}`}>{units(s.profit_units)}</td>
      <td className={`r num ${s.roi !== null && s.roi > 0 ? "ev-pos" : ""}`}>{signedPct(s.roi)}</td>
    </>
  );
}

function SummaryHead({ first }: { first: string }) {
  return (
    <thead>
      <tr>
        <th scope="col">{first}</th>
        <th scope="col" className="r">
          Terminados
        </th>
        <th scope="col" className="r">
          Acertados
        </th>
        <th scope="col" className="r" title="Suma de las probabilidades prometidas">
          Esperados
        </th>
        <th scope="col" className="r" title="A 1 unidad por parlay, con el momio al registrarse">
          Ganancia
        </th>
        <th scope="col" className="r">
          ROI
        </th>
      </tr>
    </thead>
  );
}

function Breakdown({ data }: { data: ResultsResponse }) {
  return (
    <div className="perf-grid">
      <section className="card card-pad" aria-labelledby="results-kinds">
        <h2 id="results-kinds" style={{ marginBottom: "var(--space-3)" }}>
          Por tipo de parlay
        </h2>
        <div className="table-wrap">
          <table className="data">
            <SummaryHead first="Tipo" />
            <tbody>
              {data.groups.map((g) => (
                <tr key={`${g.sport}-${g.kind}`}>
                  <td>
                    {SPORTS[g.sport].label} · {KIND_LABELS[g.kind]}
                  </td>
                  <SummaryCells s={g.summary} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card card-pad" aria-labelledby="results-months">
        <h2 id="results-months" style={{ marginBottom: "var(--space-3)" }}>
          Por mes
        </h2>
        <div className="table-wrap">
          <table className="data">
            <SummaryHead first="Mes" />
            <tbody>
              {data.months.map((m) => (
                <tr key={m.month}>
                  <td>{monthLabel(m.month)}</td>
                  <SummaryCells s={m.summary} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Calibration({ data }: { data: ResultsResponse }) {
  return (
    <section className="card card-pad" aria-labelledby="results-calibration">
      <h2 id="results-calibration">¿Se cumple lo que prometemos?</h2>
      <p className="muted small">
        Cada pierna promete la menor entre la probabilidad de nuestro modelo y la del mercado (la de las casas sin su
        comisión). Si lo real queda cerca de lo prometido, las probabilidades dicen la verdad. Con pocas piernas, la
        diferencia es sobre todo suerte.
      </p>
      <div className="table-wrap">
        <table className="data">
          <caption className="visually-hidden">Piernas terminadas por rango de probabilidad prometida</caption>
          <thead>
            <tr>
              <th scope="col">Prometido</th>
              <th scope="col" className="r">
                Piernas
              </th>
              <th scope="col" className="r">
                Promedio prometido
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
            {data.calibration.map((b) => (
              <tr key={b.lo}>
                <td className="num">
                  {pct(b.lo)}–{pct(b.hi)}
                </td>
                <td className="r num">{b.n}</td>
                <td className="r num">{pct(b.promised, 1)}</td>
                <td className="r num">{pct(b.actual, 1)}</td>
                <td className="r num">{signedPts(b.actual - b.promised)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ResultCard({ p }: { p: ResultsParlay }) {
  const label = `${SPORTS[p.sport].label} · ${KIND_SINGULAR[p.kind]}`;
  const book = p.bookmaker ?? "la casa";
  return (
    <article className="card parlay-card" aria-label={`${label} de ${p.n_legs} piernas`}>
      <div className="parlay-head">
        <h3>
          {label} · {p.n_legs} piernas
        </h3>
        <ResultBadge result={p.result} />
      </div>
      <p className="muted xs" style={{ margin: 0 }}>
        Registrado el {dateTime(p.evaluated_at)} · primer partido el {dateTime(p.first_start)}
      </p>
      <div className="parlay-stats">
        <div className="stat">
          <span className="stat-label" title="En cada pierna, la menor entre el modelo y el mercado">
            Prometido
          </span>
          <span className="stat-value">{pct(p.probability, 1)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Momio {book}</span>
          <span className="stat-value" title={p.settled_odd ? undefined : `Alguna pierna no la cotizaba ${book}`}>
            {p.settled_odd ? p.settled_odd.toFixed(2) : "—"}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Ganancia</span>
          <span className={`stat-value ${p.profit !== null && p.profit > 0 ? "ev-pos" : ""}`}>{units(p.profit)}</span>
        </div>
      </div>
      <ol className="leg-list">
        {p.legs.map((l) =>
          l.locked ? (
            <li key={l.position} className="leg-item">
              <span>
                <span className="muted xs">
                  {l.competition} · {dateTime(l.starts_at)}
                </span>
                <br />
                {l.matchup}
              </span>
              <span className="leg-meta muted xs">Con cuenta</span>
            </li>
          ) : (
            <li key={l.position} className="leg-item">
              <span>
                <span className="muted xs">
                  {l.competition} · {dateTime(l.starts_at)}
                </span>
                <br />
                <span className="muted xs">{l.matchup}</span>
                <br />
                {l.description}
                {l.result && (
                  <>
                    <br />
                    <span className="xs">
                      Real: <strong>{l.outcome.text}</strong>
                    </span>
                  </>
                )}
              </span>
              <span className="leg-meta">
                <span className="num">{pct(legProbability(l))}</span>
                <br />
                <span className="muted xs num">
                  Modelo {pct(l.p_model)} · Mercado {pct(l.p_market)}
                </span>
                <br />
                <span className="muted xs num">{l.odd ? odds(l.odd) : "sin momio"}</span>
                {l.result && (
                  <>
                    <br />
                    <ResultBadge result={l.result} />
                  </>
                )}
              </span>
            </li>
          ),
        )}
      </ol>
    </article>
  );
}

function HowWeCount({ data }: { data: ResultsResponse }) {
  return (
    <section className="card card-pad" aria-labelledby="results-rules">
      <h2 id="results-rules">Cómo contamos</h2>
      <ul className="rule-list small">
        <li>
          Cuentan todos los parlays gratis: los de máxima probabilidad de 2 y 3 piernas de cada día de NBA y de fútbol, y
          los de la semana y de fin de semana de fútbol.
        </li>
        <li>
          Desde el {fullDate(data.since)}, cuando empezamos a prometer en cada pierna la menor entre nuestro modelo y el
          mercado. Esa fecha no se mueve. {excludedText(data.excluded)}
        </li>
        <li>
          Cada parlay se registra antes de su primer partido, se congela cuando ese partido empieza y se liquida solo con
          el resultado oficial. La hora de registro sale en cada uno.
        </li>
        <li>
          La ganancia es a 1 unidad por parlay con el momio de la casa al registrarse. Un parlay sin momio de la casa
          cuenta para los aciertos pero no para la ganancia; una pierna anulada sale del parlay.
        </li>
        <li>Aquí sólo salen los parlays que ya terminaron. Los que siguen en juego se ven con una cuenta.</li>
      </ul>
    </section>
  );
}

/**
 * Resultados públicos: el registro de los parlays gratis, con o sin sesión (lo que muestra lo decide la API,
 * app/core/results.py). Si está apagada, la API responde 404 y aquí se dice que todavía no está disponible.
 */
export function ResultsPage({ signedIn }: { signedIn: boolean | undefined }) {
  const [params, setParams] = useSearchParams();
  const raw = params.get("deporte");
  const sport: SportKey | undefined = raw === "nba" || raw === "futbol" ? raw : undefined;
  const results = useInfiniteQuery({
    queryKey: ["public-results", sport ?? "all"],
    queryFn: ({ pageParam }) => api.public.results({ sport, limit: PAGE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((n, p) => n + p.items.length, 0);
      return loaded < last.total ? loaded : undefined;
    },
    refetchInterval: 300_000,
    // Apagada responde 404: no tiene caso reintentar.
    retry: (failures, error) => !(error instanceof ApiError && error.status === 404) && failures < 1,
  });
  const data = results.data?.pages[0];
  const items = results.data?.pages.flatMap((p) => p.items) ?? [];
  const unavailable = results.error instanceof ApiError && results.error.status === 404;

  const pick = (k: SportKey | undefined) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (k) next.set("deporte", k);
        else next.delete("deporte");
        return next;
      },
      { replace: true },
    );

  return (
    <>
      <header className="app-header">
        <Link to={RESULTS_PATH} className="brand" aria-label="Gorgo Predictions, resultados">
          <BrandMark sport={sport ?? lastSport()} />
          <span>Gorgo Predictions</span>
        </Link>
        <div className="header-right">
          <ThemeToggle />
          {signedIn !== undefined && (
            <Link to="/" className="btn btn-primary btn-sm">
              {signedIn ? "Ir a la app" : "Entrar"}
            </Link>
          )}
        </div>
      </header>
      <main className="page">
        <div className="day-main">
          <div className="section-head" style={{ marginBottom: 0 }}>
            <div>
              <h1>Resultados</h1>
              <p className="muted small" style={{ margin: 0 }}>
                {data
                  ? `Todos los parlays gratis que publicamos desde el ${fullDate(data.since)}, con la hora en que se registraron y lo que pasó. Ninguno se borra ni se edita.`
                  : "Todos los parlays gratis que publicamos, con la hora en que se registraron y lo que pasó."}
              </p>
            </div>
            {!unavailable && (
              <div className="segmented" role="group" aria-label="Deporte">
                <button type="button" aria-pressed={!sport} onClick={() => pick(undefined)}>
                  Todos
                </button>
                {SPORT_KEYS.map((k) => (
                  <button key={k} type="button" aria-pressed={sport === k} onClick={() => pick(k)}>
                    {SPORTS[k].label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {results.isPending ? (
            <>
              <div className="kpis" aria-busy="true" aria-label="Cargando">
                <Skeleton height={96} />
                <Skeleton height={96} />
                <Skeleton height={96} />
                <Skeleton height={96} />
              </div>
              <Skeleton height={320} />
            </>
          ) : unavailable ? (
            <EmptyState
              title="Esta página todavía no está disponible"
              action={
                <Link to="/" className="btn btn-primary">
                  {signedIn ? "Ir a la app" : "Entrar"}
                </Link>
              }
            >
              Muy pronto vas a poder ver aquí el resultado de cada parlay gratis que publicamos.
            </EmptyState>
          ) : results.isError ? (
            <ErrorState message={(results.error as Error).message} onRetry={() => results.refetch()} />
          ) : data!.summary.parlays === 0 ? (
            <>
              <EmptyState title="Todavía no hay parlays">
                {sport ? `Todavía no publicamos parlays gratis de ${SPORTS[sport].label} desde el ${fullDate(data!.since)}.` : "Todavía no publicamos parlays gratis."}
              </EmptyState>
              <HowWeCount data={data!} />
            </>
          ) : (
            <>
              <Kpis data={data!} />
              {data!.summary.settled > 0 && (
                <>
                  <Breakdown data={data!} />
                  {data!.calibration.length > 0 && <Calibration data={data!} />}
                </>
              )}
              <section aria-labelledby="results-list">
                <div className="section-head">
                  <h2 id="results-list">Parlays terminados</h2>
                  <span className="muted small">{data!.total.toLocaleString("es-MX")} en total · del más reciente al más antiguo</span>
                </div>
                {items.length === 0 ? (
                  <EmptyState title="Todavía no termina ninguno">
                    {data!.summary.pending === 1 ? "Hay 1 parlay en juego" : `Hay ${data!.summary.pending} parlays en juego`}: aparecen aquí
                    con su resultado cuando terminan sus partidos.
                  </EmptyState>
                ) : (
                  <>
                    <div className="parlay-list">
                      {items.map((p) => (
                        <ResultCard key={p.id} p={p} />
                      ))}
                    </div>
                    {results.hasNextPage && (
                      <div style={{ marginTop: "var(--space-3)", textAlign: "center" }}>
                        <button type="button" className="btn" onClick={() => results.fetchNextPage()} disabled={results.isFetchingNextPage}>
                          {results.isFetchingNextPage && <Spinner label="Cargando" />}
                          {results.isFetchingNextPage ? "Cargando…" : `Ver más (${data!.total - items.length} restantes)`}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </section>
              <HowWeCount data={data!} />
            </>
          )}

          {signedIn === false && !unavailable && (
            <section className="card card-pad results-cta" aria-labelledby="results-cta">
              <h2 id="results-cta">¿Quieres los parlays de hoy?</h2>
              <p className="muted small" style={{ margin: 0 }}>
                Con una cuenta ves los parlays gratis antes de que empiecen sus partidos.
              </p>
              <Link to="/" className="btn btn-primary">
                Entrar
              </Link>
            </section>
          )}
        </div>
      </main>
    </>
  );
}
