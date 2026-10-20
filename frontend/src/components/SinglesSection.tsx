import { useMemo, useState } from "react";
import type { Leg, SlateGame } from "../lib/api";
import { bestBookOdd } from "../lib/books";
import { MAX_WHOLE_LEGS, promised, rankedLegs, type Mode } from "../lib/builder";
import { odds, pct, signedPct } from "../lib/format";
import { usePreferences } from "../lib/preferences";
import { matchupOf, slip, toSlipLeg, useSlip } from "../lib/slip";
import type { SportConfig } from "../lib/sports";
import { EmptyState, ResultBadge } from "./States";
import { useToast } from "./Toast";

/** Cuántas se muestran antes de "Ver todas". */
const SHOWN = 8;
const SUSPICIOUS_EDGE = 0.1;

const MODE_INFO: Record<Mode, { label: string; help: string }> = {
  prob: {
    label: "Máxima probabilidad",
    help: "Las piernas que el modelo ve más probables y que ya cotiza alguna casa. De cada una se promete la menor entre el modelo y el mercado.",
  },
  ev: {
    label: "Máximo valor",
    help: "Las piernas donde el modelo ve más valor contra el momio de la casa.",
  },
};

/**
 * Apuestas individuales sugeridas: la mejor pierna de cada partido según el modo, con los mismos filtros que los
 * parlays (Personalizar), de mejor a peor. Cada una se apuesta sola: no se multiplican probabilidades.
 */
export function SinglesSection({
  config,
  legs,
  games,
  bookmaker,
  date,
}: {
  config: SportConfig;
  legs: Leg[];
  /** Partidos por match_id. */
  games: Map<number, SlateGame>;
  bookmaker: string;
  date: string;
}) {
  const prefs = usePreferences(config.key);
  const [mode, setMode] = useState<Mode>("prob");
  const [expanded, setExpanded] = useState(false);
  const byMode = useMemo(() => ({ prob: rankedLegs(legs, prefs, "prob"), ev: rankedLegs(legs, prefs, "ev") }), [legs, prefs]);
  const ranked = byMode[mode];
  const shown = expanded ? ranked : ranked.slice(0, SHOWN);
  const toLoad = shown.slice(0, MAX_WHOLE_LEGS);
  const expectedWins = shown.reduce((acc, l) => acc + promised(l, mode), 0);
  const { legs: inSlip } = useSlip();
  const slipIds = useMemo(() => new Set(inSlip.map((l) => l.pickId)), [inSlip]);
  const notify = useToast();

  const toggle = (leg: Leg) => {
    const before = slip.get();
    const adding = !slipIds.has(leg.id);
    if (adding && before.legs.length === 0) slip.setMode("singles");
    slip.toggle(toSlipLeg(config, leg, games.get(leg.match_id), date));
    if (adding && before.legs.length > 0 && (before.mode ?? "parlay") === "parlay") {
      notify("Se agregó como pierna del parlay del boleto", { label: "Cambiar a individuales", onClick: () => slip.setMode("singles") });
    }
  };

  const load = () => {
    const previous = slip.get();
    slip.replace(
      toLoad.map((l) => toSlipLeg(config, l, games.get(l.match_id), date)),
      "singles",
    );
    notify(`${toLoad.length} apuestas individuales cargadas al boleto`, { label: "Deshacer", onClick: () => slip.restore(previous) });
  };

  return (
    <section aria-labelledby="singles-title">
      <div className="section-head">
        <div>
          <h2 id="singles-title">Apuestas individuales</h2>
          <p className="muted small" style={{ margin: 0 }}>
            {MODE_INFO[mode].help} La mejor de cada partido, con los mismos filtros que los parlays.
          </p>
        </div>
        <div className="segmented" role="group" aria-label="Tipo de apuesta individual">
          {(["prob", "ev"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              onClick={() => {
                setMode(m);
                setExpanded(false);
              }}
            >
              {MODE_INFO[m].label} ({byMode[m].length})
            </button>
          ))}
        </div>
      </div>

      {ranked.length === 0 ? (
        <EmptyState title="Sin apuestas individuales con esta configuración">
          {mode === "ev"
            ? `Ninguna pierna de tus mercados tiene valor positivo contra ${bookmaker}. Que no haya apuesta también es una respuesta: no conviene forzarla.`
            : "Ninguna pierna cumple tus filtros y la cotiza alguna casa. Prueba agregar mercados, bajar la probabilidad o el momio mínimo, o vuelve cuando lleguen más momios."}
        </EmptyState>
      ) : (
        <div className="card singles-card">
          <p className="muted xs" style={{ margin: 0 }}>
            De {shown.length === 1 ? "esta" : `estas ${shown.length}`}, {mode === "prob" ? "se espera" : "el modelo espera"} acertar{" "}
            <strong className="num">{expectedWins.toFixed(1)}</strong>. Cada una se gana o se pierde por separado.
          </p>
          <ol className="leg-list">
            {shown.map((l) => {
              const added = slipIds.has(l.id);
              const p = promised(l, mode);
              const ev = l.odd !== null ? p * l.odd - 1 : null;
              const other = l.odd ? null : bestBookOdd(l.book_odds);
              const edge = l.p_market !== null ? l.p_model - l.p_market : null;
              const badge = l.player_status ? config.playerBadge(l.player_status) : null;
              return (
                <li key={l.id} className="single-item">
                  <button
                    type="button"
                    className={`btn btn-sm btn-icon ${added ? "btn-primary" : ""}`}
                    aria-pressed={added}
                    aria-label={added ? `Quitar del boleto: ${l.description}` : `Agregar al boleto: ${l.description}`}
                    title={added ? "Quitar del boleto" : "Agregar al boleto"}
                    onClick={() => toggle(l)}
                  >
                    {added ? "✓" : "+"}
                  </button>
                  <span>
                    <span className="muted xs">{matchupOf(config, games.get(l.match_id))}</span>
                    <br />
                    {l.description}
                    {badge && (
                      <>
                        {" "}
                        <span className={`badge ${badge.className}`} title={badge.title}>
                          {badge.label}
                        </span>
                      </>
                    )}
                    {edge !== null && edge > SUSPICIOUS_EDGE && (
                      <>
                        {" "}
                        <span
                          className="badge badge-warn"
                          title={`Ventaja de más de 10 pts sobre el mercado: suele ser una noticia (${config.newsExamples}) que el modelo no conoce`}
                        >
                          <span aria-hidden="true">!</span> Revisa noticias
                        </span>
                      </>
                    )}
                    {l.result && (
                      <>
                        {" "}
                        <ResultBadge result={l.result} />
                      </>
                    )}
                  </span>
                  <span className="leg-meta">
                    <span
                      className="num"
                      title={
                        mode === "prob" && l.p_market !== null
                          ? `Modelo ${pct(l.p_model)} · Mercado ${pct(l.p_market)}: se promete la menor`
                          : "Probabilidad del modelo"
                      }
                    >
                      <strong>{pct(p)}</strong>
                    </span>
                    <br />
                    {l.odd ? (
                      <span className="muted xs num" title={`Momio de ${bookmaker}`}>
                        {odds(l.odd)}
                      </span>
                    ) : other ? (
                      <span className="muted xs" title={`${bookmaker} no la cotiza: el mejor momio de las otras casas`}>
                        <span className="num">{odds(other.odd)}</span>
                        <br />
                        en {other.book}
                      </span>
                    ) : (
                      <span className="muted xs">sin momio</span>
                    )}
                    {ev !== null && (
                      <>
                        <br />
                        <span className={`xs num ${ev > 0 ? "ev-pos" : "ev-neg"}`} title="Valor esperado por unidad: probabilidad × momio − 1">
                          EV {signedPct(ev)}
                        </span>
                      </>
                    )}
                  </span>
                </li>
              );
            })}
          </ol>
          <div className="card-actions">
            <button type="button" className="btn btn-sm btn-primary" onClick={load}>
              {toLoad.length === 1 ? "Cargar al boleto" : `Cargar las ${toLoad.length} al boleto`}
            </button>
            {ranked.length > SHOWN && (
              <button type="button" className="btn btn-sm" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
                {expanded ? `Ver sólo las ${SHOWN} mejores` : `Ver las ${ranked.length}`}
              </button>
            )}
          </div>
          {shown.length > MAX_WHOLE_LEGS && (
            <p className="muted xs" style={{ margin: 0 }}>
              El boleto acepta hasta {MAX_WHOLE_LEGS} piernas: se cargan las {MAX_WHOLE_LEGS} mejores.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
