import { useMemo, useState } from "react";
import type { Leg, SlateGame } from "../lib/api";
import { bestBookOdd } from "../lib/books";
import { buildParlays, buildWhole, type BuiltParlay, type Mode } from "../lib/builder";
import { odds, pct, signedPct } from "../lib/format";
import { isDefault, usePreferences, type Preferences } from "../lib/preferences";
import { matchupOf, slip, toSlipLeg } from "../lib/slip";
import type { SportConfig } from "../lib/sports";
import { EmptyState, ResultBadge } from "./States";
import { useToast } from "./Toast";

const MODE_INFO: Record<Mode, { label: string; help: string }> = {
  prob: {
    label: "Máxima probabilidad",
    help: "Las piernas más probables que ya cotiza alguna casa, una por partido.",
  },
  ev: {
    label: "Máximo valor",
    help: "Sólo piernas donde el modelo ve valor positivo contra el momio de la casa.",
  },
};

function summaryParts(config: SportConfig, p: Preferences, bookmaker: string): string[] {
  const parts: string[] = [];
  if (p.markets.length < config.markets.length) {
    parts.push(config.markets.filter((m) => p.markets.includes(m.value)).map((m) => m.label).join(", "));
  }
  if (p.markets.includes("player") && p.stats.length < config.stats.length) {
    parts.push(`${config.statsPrefix}: ${config.stats.filter((s) => p.stats.includes(s.value)).map((s) => s.short).join(", ")}`);
  }
  if (p.leagues.length > 0) parts.push(`${p.leagues.length} ${p.leagues.length === 1 ? "liga" : "ligas"}`);
  parts.push(`Prob. ≥ ${pct(p.minProb)}`, `Momio ≥ ${p.minOdd.toFixed(2)}`);
  if (p.priceBook) parts.push(`Momios de ${bookmaker}`);
  if (p.onlyPriced) parts.push(`Sólo con momio ${bookmaker}`);
  return parts;
}

export function ParlayCard({
  config,
  parlay,
  games,
  bookmaker,
  date,
  title,
}: {
  config: SportConfig;
  parlay: BuiltParlay;
  games: Map<number, SlateGame>;
  bookmaker: string;
  date: string;
  title?: string;
}) {
  const notify = useToast();

  const load = () => {
    const previous = slip.get();
    slip.replace(parlay.legs.map((l) => toSlipLeg(config, l, games.get(l.match_id), date)));
    notify(`Parlay de ${parlay.n} piernas cargado al boleto`, { label: "Deshacer", onClick: () => slip.restore(previous) });
  };

  const copy = async () => {
    const lines = parlay.legs.map((l, i) => {
      const other = l.odd ? null : bestBookOdd(l.book_odds);
      const price = l.odd ? ` @ ${l.odd.toFixed(2)}` : other ? ` @ ${other.odd.toFixed(2)} (${other.book})` : "";
      return `${i + 1}. ${matchupOf(config, games.get(l.match_id))} — ${l.description}${price}`;
    });
    const head = `Parlay ${config.label} · ${parlay.n} piernas · prob. modelo ${pct(parlay.probability, 1)}${parlay.odd ? ` · momio ${bookmaker} ${parlay.odd.toFixed(2)}` : ""}`;
    try {
      await navigator.clipboard.writeText([head, ...lines].join("\n"));
      notify("Parlay copiado al portapapeles");
    } catch {
      notify("No se pudo copiar: tu navegador bloqueó el portapapeles");
    }
  };

  return (
    <article className="card parlay-card" aria-label={`Parlay de ${parlay.n} piernas`}>
      <div className="parlay-head">
        <h3>{title ? `${title} · ${parlay.n} piernas` : `${parlay.n} piernas`}</h3>
        <ResultBadge result={parlay.result} pendingLabel="Pendiente" />
      </div>
      <div className="parlay-stats">
        <div className="stat">
          <span className="stat-label">Prob. modelo</span>
          <span className="stat-value">{pct(parlay.probability, 1)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Momio justo</span>
          <span className="stat-value">{(1 / parlay.probability).toFixed(2)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">{bookmaker}</span>
          <span className="stat-value" title={parlay.ev !== null ? `EV ${signedPct(parlay.ev)}` : `Alguna pierna no la cotiza ${bookmaker}`}>
            {parlay.odd ? parlay.odd.toFixed(2) : "—"}
          </span>
        </div>
      </div>
      <ol className="leg-list">
        {parlay.legs.map((l) => {
          // Si la casa elegida no la cotiza, el mejor momio de las otras casas (con su nombre).
          const other = l.odd ? null : bestBookOdd(l.book_odds);
          return (
            <li key={l.id} className="leg-item">
              <span>
                <span className="muted xs">{matchupOf(config, games.get(l.match_id))}</span>
                <br />
                {l.description}
              </span>
              <span className="leg-meta">
                <span className="num">{pct(l.p_model)}</span>
                <br />
                {l.odd ? (
                  <span className="muted xs num">{odds(l.odd)}</span>
                ) : other ? (
                  <span className="muted xs" title={`${bookmaker} no la cotiza: el mejor momio de las otras casas`}>
                    <span className="num">{odds(other.odd)}</span>
                    <br />
                    en {other.book}
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
      <div className="card-actions">
        <button type="button" className="btn btn-sm btn-primary" onClick={load}>
          Cargar al boleto
        </button>
        <button type="button" className="btn btn-sm" onClick={copy}>
          Copiar
        </button>
      </div>
    </article>
  );
}

export function ParlaysSection({
  config,
  legs,
  games,
  bookmaker,
  date,
  wholeLabel,
  onCustomize,
}: {
  config: SportConfig;
  legs: Leg[];
  /** Partidos por match_id. */
  games: Map<number, SlateGame>;
  bookmaker: string;
  date: string;
  /** Si se indica (p. ej. "Jornada completa"), agrega un parlay con una pierna de cada partido. */
  wholeLabel?: string;
  onCustomize: () => void;
}) {
  const prefs = usePreferences(config.key);
  const [mode, setMode] = useState<Mode>("prob");
  const byMode = useMemo(() => {
    const build = (m: Mode) => {
      const parlays = buildParlays(legs, prefs, m);
      const whole = wholeLabel ? buildWhole(legs, prefs, m) : null;
      // El completo sólo si es más largo que el mayor de los tamaños elegidos.
      return whole && !parlays.some((p) => p.n >= whole.n) ? [whole, ...parlays] : parlays;
    };
    return { prob: build("prob"), ev: build("ev") };
  }, [legs, prefs, wholeLabel]);
  const shown = byMode[mode];
  const custom = !isDefault(prefs, config.key);

  return (
    <section aria-labelledby="parlays-title">
      <div className="section-head">
        <div>
          <h2 id="parlays-title">Parlays sugeridos</h2>
          <p className="muted small" style={{ margin: 0 }}>
            {MODE_INFO[mode].help} Nunca dos piernas del mismo partido.
          </p>
        </div>
        <div className="card-actions">
          <div className="segmented" role="group" aria-label="Tipo de parlay">
            {(["prob", "ev"] as const).map((m) => (
              <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)}>
                {MODE_INFO[m].label} ({byMode[m].length})
              </button>
            ))}
          </div>
          <button type="button" className="btn" onClick={onCustomize}>
            <span aria-hidden="true">⚙</span> Personalizar
          </button>
        </div>
      </div>

      <div className="pref-summary small">
        {custom ? (
          <span className="badge badge-live">Personalizado</span>
        ) : (
          <span className="badge badge-neutral" title="La configuración con la que el sistema registra y mide sus parlays">
            Configuración estándar
          </span>
        )}
        <span className="muted">{summaryParts(config, prefs, bookmaker).join(" · ")}</span>
        {custom && <span className="muted xs">· El rendimiento histórico se mide con la configuración estándar.</span>}
      </div>

      {shown.length === 0 ? (
        <EmptyState
          title="Sin parlays con esta configuración"
          action={
            <button type="button" className="btn" onClick={onCustomize}>
              Ajustar configuración
            </button>
          }
        >
          {mode === "ev"
            ? `No hay suficientes piernas con valor positivo contra ${bookmaker} en partidos distintos dentro de tus mercados. Que no haya parlay también es una respuesta: no conviene forzarlo.`
            : "No hay al menos dos partidos con piernas que cumplan tus filtros y que ya cotice alguna casa. Prueba agregar mercados, bajar la probabilidad o el momio mínimo, o vuelve cuando lleguen más momios."}
        </EmptyState>
      ) : (
        <div className="parlay-list">
          {shown.map((p) => (
            <ParlayCard
              key={`${p.whole ? "w" : ""}${p.n}`}
              config={config}
              parlay={p}
              games={games}
              bookmaker={bookmaker}
              date={date}
              title={p.whole ? wholeLabel : undefined}
            />
          ))}
        </div>
      )}
    </section>
  );
}
