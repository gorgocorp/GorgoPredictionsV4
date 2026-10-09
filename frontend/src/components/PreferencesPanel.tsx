import { useEffect, useRef, useState } from "react";
import type { League, Leg } from "../lib/api";
import { isEligible } from "../lib/builder";
import { pct } from "../lib/format";
import { isDefault, preferences, SIZES, usePreferences } from "../lib/preferences";
import type { SportConfig } from "../lib/sports";

const MIN_PROBS = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85];
const MIN_ODDS = [1.05, 1.1, 1.15, 1.2, 1.3, 1.4, 1.5, 1.7, 2.0];

function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function PreferencesPanel({
  config,
  open,
  onClose,
  legs,
  bookmaker,
  bookmakers,
  systemBook,
  sharpBook,
  leagues,
}: {
  config: SportConfig;
  open: boolean;
  onClose: () => void;
  legs: Leg[];
  /** Casa con la que se comparan los momios ahora. */
  bookmaker: string;
  /** Casas de la API disponibles. */
  bookmakers: string[];
  /** Casa con la que el sistema registra y mide sus parlays. */
  systemBook: string;
  /** Casa de referencia del mercado (casi sin comisión). */
  sharpBook: string;
  /** Fútbol: competiciones para elegir; vacío = sin filtro de ligas. */
  leagues: League[];
}) {
  const prefs = usePreferences(config.key);
  const [hint, setHint] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<Element | null>(null);

  useEffect(() => {
    if (!open) return;
    returnFocus.current = document.activeElement;
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      (returnFocus.current as HTMLElement | null)?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  const eligible = legs.filter((l) => isEligible(l, prefs, "prob"));
  const games = new Set(eligible.map((l) => l.match_id)).size;
  const update = (changes: Parameters<typeof preferences.update>[1]) => preferences.update(config.key, changes);

  const setMarkets = (market: string) => {
    const next = toggle(prefs.markets, market);
    if (next.length === 0) return setHint("Deja al menos un mercado activo.");
    setHint(null);
    update({ markets: next });
  };
  const setStats = (stat: string) => {
    const next = toggle(prefs.stats, stat);
    if (next.length === 0) return setHint("Deja al menos una estadística, o desactiva las props de jugador.");
    setHint(null);
    update({ stats: next });
  };
  // Sin ligas elegidas = todas. Al desmarcar una con "todas" activo, quedan las demás.
  const allLeagues = prefs.leagues.length === 0;
  const setLeague = (id: number) => {
    const current = allLeagues ? leagues.map((l) => l.id) : prefs.leagues;
    const next = toggle(current, id);
    if (next.length === 0) return setHint("Deja al menos una liga.");
    setHint(null);
    update({ leagues: next.length === leagues.length ? [] : next });
  };
  const setSizes = (n: number) => {
    const next = toggle(prefs.sizes, n);
    if (next.length === 0) return setHint("Deja al menos un tamaño de parlay.");
    setHint(null);
    update({ sizes: next });
  };

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div ref={panelRef} className="drawer" role="dialog" aria-modal="true" aria-labelledby="prefs-title" tabIndex={-1}>
        <div className="drawer-head">
          <div>
            <h2 id="prefs-title">Personalizar {config.label}</h2>
            <p className="muted small" style={{ margin: 0 }}>
              Elige qué apuestas juegas. Se aplica a los parlays sugeridos y a la tabla de piernas.
            </p>
          </div>
          <button type="button" className="btn btn-ghost btn-icon" aria-label="Cerrar" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="drawer-body">
          <fieldset className="pref-group">
            <legend>Mercados</legend>
            {config.markets.map((m) => (
              <label key={m.value} className="pref-option">
                <input type="checkbox" checked={prefs.markets.includes(m.value)} onChange={() => setMarkets(m.value)} />
                <span>
                  {m.label}
                  <span className="muted xs"> · {m.help}</span>
                </span>
              </label>
            ))}
          </fieldset>

          {leagues.length > 0 && (
            <fieldset className="pref-group">
              <legend>Ligas</legend>
              <div className="chip-toggles">
                {leagues.map((l) => {
                  const on = allLeagues || prefs.leagues.includes(l.id);
                  return (
                    <button key={l.id} type="button" className="chip-toggle" aria-pressed={on} onClick={() => setLeague(l.id)}>
                      {on && <span aria-hidden="true">✓ </span>}
                      {l.name}
                    </button>
                  );
                })}
              </div>
              {!allLeagues && (
                <button type="button" className="btn btn-sm btn-ghost" onClick={() => update({ leagues: [] })}>
                  Todas las ligas
                </button>
              )}
            </fieldset>
          )}

          {prefs.markets.includes("player") && (
            <fieldset className="pref-group">
              <legend>{config.statsTitle}</legend>
              <div className="chip-toggles">
                {config.stats.map((s) => (
                  <button key={s.value} type="button" className="chip-toggle" aria-pressed={prefs.stats.includes(s.value)} onClick={() => setStats(s.value)}>
                    {prefs.stats.includes(s.value) && <span aria-hidden="true">✓ </span>}
                    {s.label}
                  </button>
                ))}
              </div>
            </fieldset>
          )}

          <fieldset className="pref-group">
            <legend>Cada pierna</legend>
            <div className="pref-row">
              <label className="field">
                Probabilidad mínima
                <select className="select" value={prefs.minProb} onChange={(e) => update({ minProb: Number(e.target.value) })}>
                  {MIN_PROBS.map((p) => (
                    <option key={p} value={p}>
                      {pct(p)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Momio mínimo
                <select className="select" value={prefs.minOdd} onChange={(e) => update({ minOdd: Number(e.target.value) })}>
                  {MIN_ODDS.map((o) => (
                    <option key={o} value={o}>
                      {o.toFixed(2)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {bookmakers.length > 1 && (
              <label className="field">
                Comparar con los momios de (en los dos deportes)
                <select
                  className="select"
                  value={bookmaker}
                  onChange={(e) => update({ priceBook: e.target.value === systemBook ? "" : e.target.value })}
                >
                  {bookmakers.map((b) => (
                    <option key={b} value={b}>
                      {b}
                      {b === systemBook ? " (con la que se mide el sistema)" : ""}
                      {b.toLowerCase() === sharpBook.toLowerCase() ? " (referencia del mercado, casi sin comisión)" : ""}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="toggle">
              <input type="checkbox" checked={prefs.onlyPriced} onChange={(e) => update({ onlyPriced: e.target.checked })} />
              Sólo piernas con momio de {bookmaker}
            </label>
            <label className="toggle">
              <input type="checkbox" checked={prefs.includeQuestionable} onChange={(e) => update({ includeQuestionable: e.target.checked })} />
              Incluir jugadores en duda ({config.questionableSource})
            </label>
            <p className="muted xs" style={{ margin: 0 }}>
              Más probabilidad por pierna = parlays que pegan más seguido pero pagan menos. Sólo entran piernas que cotiza alguna
              casa; si {bookmaker} no la cotiza, el momio mínimo se compara con el mejor de las otras.
            </p>
          </fieldset>

          <fieldset className="pref-group">
            <legend>Tamaños de parlay</legend>
            <div className="chip-toggles">
              {SIZES.map((n) => (
                <button key={n} type="button" className="chip-toggle" aria-pressed={prefs.sizes.includes(n)} aria-label={`${n} piernas`} onClick={() => setSizes(n)}>
                  {n}
                </button>
              ))}
            </div>
          </fieldset>

          {hint && (
            <p className="banner banner-warn" role="alert" style={{ margin: 0 }}>
              {hint}
            </p>
          )}
        </div>

        <div className="drawer-foot">
          <span className="small" aria-live="polite">
            <strong className="num">{eligible.length}</strong> piernas en <strong className="num">{games}</strong> partidos cumplen tu configuración
          </span>
          <div className="card-actions">
            <button
              type="button"
              className="btn"
              disabled={isDefault(prefs, config.key)}
              onClick={() => {
                setHint(null);
                preferences.reset(config.key);
              }}
            >
              Restablecer
            </button>
            <button type="button" className="btn btn-primary" onClick={onClose}>
              Listo
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
