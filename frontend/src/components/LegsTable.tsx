import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { Leg, SlateGame } from "../lib/api";
import { odds, pct, shortDay, signedPct } from "../lib/format";
import { isAllowed, isDefault, usePreferences } from "../lib/preferences";
import { matchupOf, slip, toSlipLeg, useSlip } from "../lib/slip";
import type { SportConfig } from "../lib/sports";
import { EmptyState, ResultBadge } from "./States";
import { useToast } from "./Toast";

const PAGE_SIZE = 50;
const MIN_PROBS = [0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9];
const SUSPICIOUS_EDGE = 0.1;
/** Con pocos mercados el filtro es de botones; con muchos, una lista. */
const MAX_MARKET_BUTTONS = 6;
/** Lo que define la página (día, jornada, rango): "Limpiar filtros" no lo quita. */
const PAGE_PARAMS = ["fecha", "modo", "liga", "jornada", "desde", "hasta"];

function hits(h: number | null, n: number | null) {
  return h !== null && n ? `${h}/${n}` : "—";
}

export function LegsTable({
  config,
  legs,
  games,
  date,
  bookmaker,
  showDay = false,
  onCustomize,
}: {
  config: SportConfig;
  legs: Leg[];
  /** Partidos por match_id. */
  games: Map<number, SlateGame>;
  date: string;
  /** Casa de la API cuyos momios se muestran. */
  bookmaker: string;
  /** Varios días: muestra el día de cada partido. */
  showDay?: boolean;
  onCustomize: () => void;
}) {
  const [params, setParams] = useSearchParams();
  const prefs = usePreferences(config.key);
  const allowedLegs = useMemo(() => legs.filter((l) => isAllowed(l, prefs)), [legs, prefs]);
  const marketOptions = ["all", ...config.markets.map((m) => m.value).filter((m) => prefs.markets.includes(m))];
  const notify = useToast();
  const { legs: inSlip } = useSlip();
  const slipIds = useMemo(() => new Set(inSlip.map((l) => l.pickId)), [inSlip]);

  const requested = params.get("mercado") ?? "all";
  const market = marketOptions.includes(requested) ? requested : "all";
  const pricedOnly = params.get("momio") === "1";
  const minProb = Number(params.get("min") ?? 0.6);
  const query = params.get("q") ?? "";
  const sort = params.get("orden") === "ev" ? "ev" : "prob";
  // ?partido= lleva el ID del proveedor (el mismo que muestra la tarjeta del partido).
  const gameId = params.get("partido") ? Number(params.get("partido")) : null;
  const page = Math.max(1, Number(params.get("pagina") ?? 1));

  const update = (changes: Record<string, string | null>, resetPage = true) => {
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
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = allowedLegs.filter((l) => {
      const g = games.get(l.match_id);
      if (market !== "all" && l.market !== market) return false;
      if (pricedOnly && l.odd === null) return false;
      if (l.p_model < minProb) return false;
      if (gameId !== null && g?.id !== gameId) return false;
      if (q) {
        const haystack = `${l.description} ${g?.home.name ?? ""} ${g?.away.name ?? ""}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
    const ev = (l: Leg) => (l.odd !== null ? l.p_model * l.odd - 1 : -Infinity);
    return rows.sort((a, b) => (sort === "ev" ? ev(b) - ev(a) || b.p_model - a.p_model : b.p_model - a.p_model));
  }, [allowedLegs, games, market, pricedOnly, minProb, query, sort, gameId]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const visible = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const selectedGame = gameId !== null ? [...games.values()].find((g) => g.id === gameId) : undefined;
  const marketLabel = (m: string) => (m === "all" ? "Todos" : (config.marketLabels[m] ?? m));

  const toggle = (leg: Leg) => {
    const game = games.get(leg.match_id);
    const adding = !slipIds.has(leg.id);
    slip.toggle(toSlipLeg(config, leg, game, date));
    if (adding && inSlip.some((l) => l.matchId === leg.match_id)) {
      notify("Ojo: ya tienes una pierna de ese partido en el boleto (están correlacionadas)");
    }
  };

  return (
    <section aria-labelledby="legs-title">
      <div className="section-head">
        <div>
          <h2 id="legs-title">Piernas</h2>
          <p className="muted small" style={{ margin: 0 }}>
            Todas las piernas evaluadas por el modelo. Agrega las que quieras a tu boleto.
          </p>
        </div>
        <span className="card-actions">
          <span className="muted small num" aria-live="polite">
            {filtered.length} de {allowedLegs.length}
            {!isDefault(prefs, config.key) && allowedLegs.length < legs.length && " en tus mercados"}
          </span>
          <button type="button" className="btn btn-sm" onClick={onCustomize}>
            <span aria-hidden="true">⚙</span> Mis mercados
          </button>
        </span>
      </div>

      <div className="filters">
        {marketOptions.length <= MAX_MARKET_BUTTONS ? (
          <div className="segmented" role="group" aria-label="Mercado">
            {marketOptions.map((m) => (
              <button key={m} type="button" aria-pressed={market === m} onClick={() => update({ mercado: m === "all" ? null : m })}>
                {marketLabel(m)}
              </button>
            ))}
          </div>
        ) : (
          <label className="field">
            Mercado
            <select className="select" value={market} onChange={(e) => update({ mercado: e.target.value === "all" ? null : e.target.value })}>
              {marketOptions.map((m) => (
                <option key={m} value={m}>
                  {marketLabel(m)}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="field">
          Prob. mínima
          <select className="select" value={minProb} onChange={(e) => update({ min: e.target.value })}>
            {MIN_PROBS.map((p) => (
              <option key={p} value={p}>
                {p === 0 ? "Todas" : pct(p)}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Ordenar por
          <select className="select" value={sort} onChange={(e) => update({ orden: e.target.value === "ev" ? "ev" : null })}>
            <option value="prob">Probabilidad</option>
            <option value="ev">Valor esperado</option>
          </select>
        </label>
        <label className="field" style={{ flex: "1 1 200px" }}>
          Buscar
          <input
            className="input"
            type="search"
            placeholder="Jugador, equipo o mercado"
            value={query}
            onChange={(e) => update({ q: e.target.value })}
          />
        </label>
        <label className="toggle">
          <input type="checkbox" checked={pricedOnly} onChange={(e) => update({ momio: e.target.checked ? "1" : null })} />
          Sólo con momio
        </label>
      </div>

      {selectedGame && (
        <div style={{ marginBottom: "var(--space-3)" }}>
          <span className="chip">
            Partido: {matchupOf(config, selectedGame)}
            <button type="button" aria-label="Quitar filtro de partido" onClick={() => update({ partido: null })}>
              ✕
            </button>
          </span>
        </div>
      )}

      {filtered.length === 0 ? (
        <EmptyState
          title="Ninguna pierna coincide con los filtros"
          action={
            <button
              type="button"
              className="btn"
              onClick={() =>
                setParams(
                  (prev): Record<string, string> =>
                    Object.fromEntries(PAGE_PARAMS.flatMap((k) => (prev.get(k) ? [[k, prev.get(k) as string]] : []))),
                  { replace: true },
                )
              }
            >
              Limpiar filtros
            </button>
          }
        >
          Prueba bajar la probabilidad mínima o quitar el filtro de momio.
        </EmptyState>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">
                    <span className="visually-hidden">Boleto</span>
                  </th>
                  <th scope="col">Partido</th>
                  <th scope="col">Pierna</th>
                  <th scope="col" className="r" title="Probabilidad estimada por el modelo">
                    Modelo
                  </th>
                  <th scope="col" className="r" title="Probabilidad del mercado sin comisión (Pinnacle o mediana de casas)">
                    Mercado
                  </th>
                  <th scope="col" className="r">
                    Momio {bookmaker}
                  </th>
                  <th scope="col" className="r" title="Momio que correspondería a la probabilidad del modelo">
                    Justo
                  </th>
                  <th scope="col" className="r" title="Valor esperado por unidad: probabilidad × momio − 1">
                    EV
                  </th>
                  <th scope="col" className="r" title={config.hitsTitle}>
                    Últ. 10 · 25
                  </th>
                  <th scope="col">Resultado</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((l) => {
                  const ev = l.odd !== null ? l.p_model * l.odd - 1 : null;
                  const edge = l.p_market !== null ? l.p_model - l.p_market : null;
                  const added = slipIds.has(l.id);
                  const game = games.get(l.match_id);
                  const badge = l.player_status ? config.playerBadge(l.player_status) : null;
                  return (
                    <tr key={l.id} aria-selected={added}>
                      <td>
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
                      </td>
                      <td className="muted">
                        {showDay && game?.match_date && <span className="xs">{shortDay(game.match_date)} · </span>}
                        {matchupOf(config, game)}
                      </td>
                      <td className="wrap">
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
                      </td>
                      <td className="r num">
                        <strong>{pct(l.p_model)}</strong>
                      </td>
                      <td className="r num muted">{pct(l.p_market)}</td>
                      <td className="r num">{odds(l.odd)}</td>
                      <td className="r num muted">{(1 / l.p_model).toFixed(2)}</td>
                      <td className={`r num ${ev !== null && ev > 0 ? "ev-pos" : "ev-neg"}`}>{signedPct(ev)}</td>
                      <td className="r num muted">
                        {hits(l.hits_10, l.games_10)} · {hits(l.hits_25, l.games_25)}
                      </td>
                      <td>
                        <ResultBadge result={l.result} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {pages > 1 && (
            <nav className="pager" aria-label="Paginación de piernas">
              <button type="button" className="btn btn-sm" disabled={current <= 1} onClick={() => update({ pagina: String(current - 1) }, false)}>
                Anterior
              </button>
              <span className="muted num">
                Página {current} de {pages}
              </span>
              <button type="button" className="btn btn-sm" disabled={current >= pages} onClick={() => update({ pagina: String(current + 1) }, false)}>
                Siguiente
              </button>
            </nav>
          )}
        </div>
      )}
    </section>
  );
}
