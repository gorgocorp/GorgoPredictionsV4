import { useQuery } from "@tanstack/react-query";
import { BetSlip } from "../components/BetSlip";
import { EmptyState, ErrorState, ResultBadge, Skeleton } from "../components/States";
import { useToast } from "../components/Toast";
import { api, type FeaturedParlay, type FeaturedResponse, type FeaturedWindow, type HistorySummary, type SportKey } from "../lib/api";
import { canLoad, copyText, legPrice, legProbability, rangeText, toSlipLegs, windowStatus } from "../lib/featured";
import { dateTime, localTime, odds, pct, shortDay } from "../lib/format";
import { slip } from "../lib/slip";

const weekdayTime = new Intl.DateTimeFormat("es-MX", { weekday: "long", day: "numeric", month: "long", hour: "numeric", minute: "2-digit" });

function Rules({ rules }: { rules: FeaturedResponse["rules"] }) {
  return (
    <ul className="rule-list small" aria-label="Reglas de cada pierna">
      <li>La cotiza alguna casa a {rules.min_odd.toFixed(2)} o más: nada de "menos de 10.5 goles".</li>
      <li>
        El modelo y el mercado le dan al menos {pct(rules.min_prob)}, y se promete la menor de las dos.
      </li>
      <li>Una pierna por partido y máximo {rules.max_per_market} del mismo mercado.</li>
      <li>Sin props de jugador: al publicarse nadie conoce las alineaciones de días después.</li>
    </ul>
  );
}

function RecordCard({ label, s }: { label: string; s: HistorySummary }) {
  const sizes = s.by_size.filter((b) => b.settled > 0);
  return (
    <div className="card kpi">
      <span className="stat-label">{label}</span>
      <span className="kpi-value">
        {s.won} <span className="muted small">de {s.settled} parlays acertados</span>
      </span>
      {sizes.length === 0 ? (
        <span className="muted xs">Todavía no se liquida ninguno: el contador empieza con el primer resultado.</span>
      ) : (
        <table className="data record-table">
          <caption className="visually-hidden">Aciertos de {label.toLowerCase()} por número de piernas</caption>
          <thead>
            <tr>
              <th scope="col">Piernas</th>
              <th scope="col" className="r">
                Acertados
              </th>
              <th scope="col" className="r" title="Suma de las probabilidades prometidas">
                Esperados
              </th>
            </tr>
          </thead>
          <tbody>
            {sizes.map((b) => (
              <tr key={b.n_legs}>
                <td className="num">{b.n_legs}</td>
                <td className="r num">
                  {b.won} de {b.settled}
                </td>
                <td className="r num">{b.expected.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function FeaturedCard({ label, parlay, bookmaker, actions }: { label: string; parlay: FeaturedParlay; bookmaker: string; actions: boolean }) {
  const notify = useToast();
  const loadable = canLoad(parlay);

  const load = () => {
    const previous = slip.get();
    slip.replace(toSlipLegs(parlay));
    notify(`${label} de ${parlay.n_legs} piernas cargado al boleto`, { label: "Deshacer", onClick: () => slip.restore(previous) });
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(copyText(label, parlay, bookmaker));
      notify("Parlay copiado al portapapeles");
    } catch {
      notify("No se pudo copiar: tu navegador bloqueó el portapapeles");
    }
  };

  return (
    <article className="card parlay-card" aria-label={`${label} de ${parlay.n_legs} piernas`}>
      <div className="parlay-head">
        <h3>{parlay.n_legs} piernas</h3>
        <ResultBadge result={parlay.result} pendingLabel="Pendiente" />
      </div>
      <div className="parlay-stats">
        <div className="stat">
          <span className="stat-label" title="En cada pierna, la menor entre el modelo y el mercado">
            Probabilidad
          </span>
          <span className="stat-value">{pct(parlay.probability, 1)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Momio justo</span>
          <span className="stat-value">{(1 / parlay.probability).toFixed(2)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">{bookmaker}</span>
          <span className="stat-value" title={parlay.odd ? undefined : `Alguna pierna no la cotiza ${bookmaker}`}>
            {parlay.odd ? parlay.odd.toFixed(2) : "—"}
          </span>
        </div>
      </div>
      <ol className="leg-list">
        {parlay.legs.map((l) => {
          const price = legPrice(l);
          return (
            <li key={l.pick_id} className="leg-item">
              <span>
                <span className="muted xs">
                  {l.competition} · {shortDay(l.date)} {localTime(l.starts_at)}
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
                {price ? (
                  <span className="muted xs num" title={price.book ? `${bookmaker} no la cotiza: el mejor momio de las otras casas` : undefined}>
                    {odds(price.odd)}
                    {price.book && ` en ${price.book}`}
                  </span>
                ) : (
                  <span className="muted xs">sin momio</span>
                )}
                {l.result && (
                  <>
                    <br />
                    <ResultBadge result={l.result} />
                  </>
                )}
              </span>
            </li>
          );
        })}
      </ol>
      {actions && (
        <div className="card-actions">
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={load}
            disabled={!loadable}
            title={loadable ? undefined : "Ya empezó algún partido de este parlay: no se puede apostar completo"}
          >
            Cargar al boleto
          </button>
          <button type="button" className="btn btn-sm" onClick={copy}>
            Copiar
          </button>
        </div>
      )}
    </article>
  );
}

function CurrentWindow({ w, bookmaker }: { w: FeaturedWindow; bookmaker: string }) {
  const status = windowStatus(w);
  const titleId = `featured-${w.mode}`;
  const publishText = weekdayTime.format(new Date(w.publish_at));
  return (
    <section aria-labelledby={titleId}>
      <div className="section-head">
        <div>
          <h2 id={titleId}>{w.label}</h2>
          <p className="muted small" style={{ margin: 0 }}>
            Partidos del {rangeText(w.start, w.end)}.{" "}
            {status === "published" && `Publicado el ${dateTime(w.parlays[0].evaluated_at)}; ya no cambia.`}
          </p>
        </div>
      </div>
      {status === "published" ? (
        <div className="parlay-list">
          {w.parlays.map((p) => (
            <FeaturedCard key={p.id} label={w.label} parlay={p} bookmaker={bookmaker} actions />
          ))}
        </div>
      ) : status === "upcoming" ? (
        <EmptyState title={`Se publica el ${publishText}`}>
          Se arma una sola vez con los partidos del {rangeText(w.start, w.end)} y ya no cambia: lo que se publica es lo que se
          mide.
        </EmptyState>
      ) : (
        <EmptyState title="Todavía no se publica">
          Sale en la primera corrida del sistema desde el {publishText}, y sólo si hay al menos dos piernas que cumplan las
          reglas. Si no las hay, esta semana no habrá {w.label.toLowerCase()}: no conviene forzarlo.
        </EmptyState>
      )}
    </section>
  );
}

function PastWindow({ w, bookmaker }: { w: FeaturedWindow; bookmaker: string }) {
  return (
    <details className="card past-window">
      <summary>
        <span>
          <strong>{w.label}</strong> <span className="muted small">· {rangeText(w.start, w.end)}</span>
        </span>
        <span className="past-results">
          {w.parlays.length === 0 ? (
            <span className="muted xs">No se publicó</span>
          ) : (
            w.parlays.map((p) => (
              <span key={p.id} className="xs">
                {p.n_legs}: <ResultBadge result={p.result} pendingLabel="Pendiente" />
              </span>
            ))
          )}
        </span>
      </summary>
      {w.parlays.length > 0 && (
        <div className="parlay-list">
          {w.parlays.map((p) => (
            <FeaturedCard key={p.id} label={w.label} parlay={p} bookmaker={bookmaker} actions={false} />
          ))}
        </div>
      )}
    </details>
  );
}

/** Parlays de la semana y de fin de semana: se publican una vez, se miden solos y llevan su contador de aciertos. */
export function FeaturedPage({ sport }: { sport: SportKey }) {
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta, refetchInterval: 60_000 });
  const featured = useQuery({ queryKey: [sport, "featured"], queryFn: () => api.featured(sport), refetchInterval: 300_000 });
  const bookmaker = meta.data?.bookmaker ?? "Bet365";
  const bookmakers = meta.data?.bookmakers ?? [bookmaker];

  return (
    <div className="day-layout">
      <div className="day-main">
        <div className="section-head" style={{ marginBottom: 0 }}>
          <div>
            <h1>Parlays de la semana</h1>
            <p className="muted small" style={{ margin: 0 }}>
              De 2 a 5 piernas con las predicciones del modelo. El de la semana se publica el lunes y el de fin de semana el
              jueves, una sola vez, y se liquidan solos con el resultado real.
            </p>
          </div>
        </div>

        {featured.isPending ? (
          <>
            <div className="kpis">
              <Skeleton height={120} />
              <Skeleton height={120} />
            </div>
            <Skeleton height={320} />
          </>
        ) : featured.isError ? (
          <ErrorState message={(featured.error as Error).message} onRetry={() => featured.refetch()} />
        ) : (
          <>
            <Rules rules={featured.data.rules} />
            <section aria-label="Contador de aciertos">
              <div className="kpis">
                {featured.data.current.map((w) => (
                  <RecordCard key={w.mode} label={w.label} s={featured.data.record[w.mode]} />
                ))}
              </div>
            </section>
            {featured.data.current.map((w) => (
              <CurrentWindow key={w.mode} w={w} bookmaker={bookmaker} />
            ))}
            {featured.data.past.length > 0 && (
              <section aria-labelledby="featured-past">
                <h2 id="featured-past">Semanas anteriores</h2>
                <div className="past-list">
                  {featured.data.past.map((w) => (
                    <PastWindow key={`${w.mode}-${w.start}`} w={w} bookmaker={bookmaker} />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
      <BetSlip bookmaker={bookmaker} apiBooks={bookmakers} />
    </div>
  );
}
