import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { oddFor } from "../lib/books";
import { ceilOdd } from "../lib/builder";
import { american, money, orList, pct, signedPct } from "../lib/format";
import { impliedProbability, legValue, parseOdds, verdict } from "../lib/oddsInput";
import { summarize, summarizeSingles } from "../lib/parlay";
import { commonPreferences, useCommonPreferences } from "../lib/preferences";
import { useViewer } from "../lib/session";
import { bookKey, slip, slipMode, stakeOf, useSlip, type SlipMode } from "../lib/slip";
import { SPORTS } from "../lib/sports";
import { Spinner } from "./States";
import { useToast } from "./Toast";
import { ValueBadge } from "./ValueBadge";

/** Desde aquí el boleto avisa que un parlay largo acumula la comisión de la casa en cada pierna. */
const LONG_PARLAY = 4;

function decimalLabel(d: number): string {
  return `${d.toFixed(2)} (${american(d)})`;
}

/** Ganancia con signo: "+$12.50" o "−$4.00"; "—" si no se puede calcular. */
function signedMoney(amount: number | null): string {
  return amount === null ? "—" : `${amount >= 0 ? "+" : "−"}${money(Math.abs(amount))}`;
}

/** Lo que dice el mercado de una pierna: su probabilidad y el momio justo, o por qué no la hay. */
function marketText(pMarket: number | null | undefined): string {
  if (pMarket === undefined) return "Mercado: quita la pierna y vuelve a agregarla para verlo";
  if (pMarket === null) return "Mercado: ninguna casa cotiza este mercado completo";
  return `Mercado ${pct(pMarket)} · momio justo ${decimalLabel(ceilOdd(1 / pMarket))}`;
}

const MODE_INFO: Record<SlipMode, { label: string; help: string }> = {
  parlay: { label: "Parlay", help: "Una sola apuesta con todas las piernas: ganas si aciertas todas." },
  singles: { label: "Individuales", help: "Una apuesta por pierna, cada una con su monto: se ganan o se pierden por separado." },
};

/** Monto escrito en un campo numérico (vacío o negativo = 0). */
const amount = (value: string) => Math.max(0, Number(value) || 0);

/** Casas para elegir en el boleto; "Otra…" deja escribir cualquier nombre. */
const BOOKS = ["Caliente", "1xBet", "Bet365", "Pinnacle", "Codere", "Betano", "Playdoit", "Strendus"];
const OTHER = "__otra__";

function SlipBody({ bookmaker, apiBooks, onClose }: { bookmaker: string; apiBooks: string[]; onClose?: () => void }) {
  const state = useSlip();
  const { full } = useViewer();
  const { myBook } = useCommonPreferences();
  const notify = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const stakeId = useId();
  const bookId = useId();
  const totalId = useId();
  const [error, setError] = useState<string | null>(null);
  const key = bookKey(myBook);
  const knownBook = BOOKS.find((b) => b.toLowerCase() === key);
  // "Otra…": se muestra un campo de texto (también si la casa guardada no está en la lista).
  const [customBook, setCustomBook] = useState(!knownBook);
  const isApiBook = (b: string) => apiBooks.some((a) => a.toLowerCase() === b.toLowerCase());
  const autoBooks = orList(apiBooks);

  // Momio de la casa del usuario por pierna: el que escribió para esa casa o, si su casa está en la API
  // (Bet365, 1xBet, Pinnacle), el de la API. Cada casa conserva sus propios momios escritos.
  const sameAsApi = key === bookmaker.toLowerCase();
  const legs = state.legs.map((l) => {
    const apiOdd = oddFor(l.bookOdds, myBook) ?? (sameAsApi && !l.bookOdds ? l.odd : null);
    const raw = l.typedOdds?.[key] ?? (apiOdd ? apiOdd.toFixed(2) : "");
    const book = parseOdds(raw);
    return {
      ...l,
      raw,
      book,
      pBook: book ? impliedProbability(book) : null,
      value: book ? legValue(l.pModel, l.pMarket, book) : null,
      stake: stakeOf(state, l.pickId),
    };
  });
  const mode = slipMode(state);
  const singles = mode === "singles";
  const singlesTotals = summarizeSingles(legs.map((l) => ({ pModel: l.pModel, pMarket: l.pMarket, odd: l.book, stake: l.stake })));
  const allPriced = legs.length > 0 && legs.every((l) => l.book !== null);
  const product = allPriced ? legs.reduce((acc, l) => acc * (l.book as number), 1) : null;
  const totalRaw = state.totalOdds?.[key] ?? "";
  const totalOverride = totalRaw ? parseOdds(totalRaw) : null;
  const ticketOdd = totalOverride ?? product;
  const model = summarize(state.legs.map((l) => ({ matchId: l.matchId, pModel: l.pModel, pMarket: l.pMarket, odd: null })));
  const pBook = ticketOdd ? 1 / ticketOdd : null;
  const ev = ticketOdd ? model.probability * ticketOdd - 1 : null;
  const evMarket = ticketOdd && model.marketProbability !== null ? model.marketProbability * ticketOdd - 1 : null;
  // Verde sólo si el modelo y el mercado ven valor (sin mercado en alguna pierna, nunca).
  const bothValue = ev !== null && ev > 0 && evMarket !== null && evMarket > 0;
  const singlesBothValue =
    singlesTotals.expectedProfit !== null &&
    singlesTotals.expectedProfit > 0 &&
    singlesTotals.expectedProfitMarket !== null &&
    singlesTotals.expectedProfitMarket > 0;
  /** Ganancia esperada como porcentaje de lo apostado (para el título del dato). */
  const ofStaked = (profit: number | null) =>
    profit !== null && singlesTotals.staked > 0 ? `${signedPct(profit / singlesTotals.staked)} de lo apostado` : undefined;
  const modelOnly = legs.filter((l) => l.value === "model_only").length;
  // Donde no hay mercado, la única alerta es que el modelo se separe mucho de la casa.
  const suspicious = legs.filter((l) => l.pMarket == null && l.pBook !== null && verdict(l.pModel, l.pBook) === "suspicious").length;

  const register = useMutation({
    mutationFn: async () => {
      if (singles) {
        const r = await api.createSingles({
          bookmaker: myBook,
          bets: legs.map((l) => ({ pick_id: l.pickId, odd: l.book as number, stake: l.stake })),
        });
        return r.ids.length;
      }
      await api.createBet({
        bookmaker: myBook,
        stake: state.stake,
        legs: legs.map((l) => ({ pick_id: l.pickId, odd: l.book as number })),
        total_odd: totalOverride ?? undefined,
      });
      return 0;
    },
    onSuccess: (singlesCount) => {
      slip.clear();
      queryClient.invalidateQueries({ queryKey: ["bets"] });
      const what =
        singlesCount === 0
          ? "Apuesta registrada"
          : singlesCount === 1
            ? "Apuesta individual registrada"
            : `${singlesCount} apuestas individuales registradas`;
      notify(`${what} en Mis apuestas (${myBook})`, { label: "Ver", onClick: () => navigate("/mis-apuestas") });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "No se pudo registrar la apuesta"),
  });

  const submit = () => {
    if (!myBook.trim()) return setError("Escribe el nombre de tu casa de apuestas.");
    const missing = legs.filter((l) => l.book === null).length;
    if (missing) return setError(`Escribe el momio de ${myBook} en ${missing === 1 ? "la pierna que falta" : `las ${missing} piernas que faltan`}.`);
    if (singles) {
      const noStake = legs.filter((l) => !(l.stake > 0)).length;
      if (noStake) return setError(`Escribe cuánto apostaste en ${noStake === 1 ? "la pierna que falta" : `las ${noStake} piernas que faltan`}.`);
    } else {
      if (totalRaw && totalOverride === null) return setError("El momio total no es válido. Escribe, por ejemplo, +1200 o 13.00.");
      if (!(state.stake > 0)) return setError("Escribe cuánto apostaste.");
    }
    setError(null);
    register.mutate();
  };

  const clear = () => {
    const previous = slip.get();
    slip.clear();
    setError(null);
    notify("Boleto vaciado", { label: "Deshacer", onClick: () => slip.restore(previous) });
  };

  const copy = async () => {
    const lines = legs.map(
      (l, i) =>
        `${i + 1}. ${SPORTS[l.sport].label} · ${l.matchup} — ${l.description}${l.book ? ` @ ${american(l.book)}` : ""}${singles ? ` · ${money(l.stake)}` : ""}`,
    );
    const head = singles
      ? `Individuales · ${legs.length} ${legs.length === 1 ? "apuesta" : "apuestas"} · ${money(singlesTotals.staked)} en total`
      : `Parlay ${legs.length} piernas · modelo ${pct(model.probability, 1)}${ticketOdd ? ` · ${myBook} ${american(ticketOdd)}` : ""}`;
    try {
      await navigator.clipboard.writeText([head, ...lines].join("\n"));
      notify("Boleto copiado al portapapeles");
    } catch {
      notify("No se pudo copiar: tu navegador bloqueó el portapapeles");
    }
  };

  return (
    <div className="slip">
      <div className="section-head" style={{ marginBottom: 0 }}>
        <h2>
          Boleto <span className="muted num">({legs.length})</span>
        </h2>
        {onClose && (
          <button type="button" className="btn btn-ghost btn-icon" aria-label="Cerrar boleto" onClick={onClose} autoFocus>
            ✕
          </button>
        )}
      </div>

      <label className="field" htmlFor={bookId}>
        Tu casa de apuestas
        <select
          id={bookId}
          className="select"
          value={customBook || !knownBook ? OTHER : knownBook}
          onChange={(e) => {
            setError(null);
            if (e.target.value === OTHER) {
              setCustomBook(true);
              commonPreferences.update({ myBook: "" });
            } else {
              setCustomBook(false);
              commonPreferences.update({ myBook: e.target.value });
            }
          }}
        >
          {BOOKS.map((b) => (
            <option key={b} value={b}>
              {b}
              {isApiBook(b) ? " · momios automáticos" : ""}
            </option>
          ))}
          <option value={OTHER}>Otra…</option>
        </select>
      </label>
      {(customBook || !knownBook) && (
        <input
          className="input"
          value={myBook}
          onChange={(e) => commonPreferences.update({ myBook: e.target.value })}
          placeholder="Nombre de tu casa"
          aria-label="Nombre de tu casa de apuestas"
          autoFocus={customBook}
        />
      )}

      {legs.length === 0 ? (
        <p className="muted small" style={{ margin: 0 }}>
          {full ? (
            <>
              Agrega piernas con el botón <strong>+</strong> o carga un parlay o las individuales sugeridas; puedes mezclar NBA y fútbol.
            </>
          ) : (
            <>Carga un parlay gratis; puedes mezclar NBA y fútbol.</>
          )}{" "}
          Luego
          escribe los momios que te da {myBook || "tu casa"} para compararlos con el modelo y registrar tu apuesta. Si apuestas en{" "}
          {autoBooks}, sus momios se llenan solos.
        </p>
      ) : (
        <>
          {legs.length > 1 && (
            <div className="slip-mode">
              <div className="segmented" role="group" aria-label="Cómo apostar el boleto">
                {(["parlay", "singles"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    aria-pressed={mode === m}
                    onClick={() => {
                      setError(null);
                      slip.setMode(m);
                    }}
                  >
                    {MODE_INFO[m].label}
                    {m === "singles" && <span className="num"> ({legs.length})</span>}
                  </button>
                ))}
              </div>
              <span className="muted xs">{MODE_INFO[mode].help}</span>
            </div>
          )}
          <ul className="slip-legs">
            {legs.map((l) => (
              <li key={l.pickId} className="slip-leg">
                <span>
                  <span className="muted xs">
                    <span className="sport-tag" data-sport={l.sport}>
                      {SPORTS[l.sport].label}
                    </span> {l.matchup}
                  </span>
                  <br />
                  {l.description}
                  <span className="slip-odds">
                    <input
                      className="input num"
                      value={l.raw}
                      onChange={(e) => {
                        setError(null);
                        slip.setLegOdd(l.pickId, myBook, e.target.value);
                      }}
                      placeholder="-120"
                      inputMode="text"
                      aria-label={`Momio de ${myBook || "tu casa"} para ${l.description}`}
                    />
                    <span className="xs num">
                      Modelo <strong>{pct(l.pModel)}</strong>
                      {l.pBook !== null ? (
                        <>
                          {" "}· {myBook} {pct(l.pBook)}
                        </>
                      ) : l.raw ? (
                        <span style={{ color: "var(--lost)" }}> · momio no válido</span>
                      ) : null}
                    </span>
                    {l.value && <ValueBadge value={l.value} />}
                  </span>
                  <span className="slip-market xs num muted">{marketText(l.pMarket)}</span>
                  {singles && (
                    <span className="slip-odds">
                      <label className="slip-stake xs">
                        Monto
                        <input
                          className="input num"
                          type="number"
                          inputMode="decimal"
                          min={0}
                          step={10}
                          value={l.stake}
                          onChange={(e) => {
                            setError(null);
                            slip.setLegStake(l.pickId, amount(e.target.value));
                          }}
                          aria-label={`Monto (MXN) para ${l.description}`}
                        />
                      </label>
                      <span className="xs num muted">{l.book ? `Paga ${money(l.stake * l.book)}` : "Paga —"}</span>
                    </span>
                  )}
                </span>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm btn-icon"
                  aria-label={`Quitar ${l.description}`}
                  title="Quitar"
                  onClick={() => slip.remove(l.pickId)}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>

          {!singles && model.sameGame.length > 0 && (
            <div className="banner banner-warn" role="alert">
              <span aria-hidden="true">!</span>
              <span>
                Tienes varias piernas del mismo partido. Están correlacionadas: la probabilidad de acertar todo (del modelo y del mercado) no
                es confiable.
              </span>
            </div>
          )}
          {!singles && legs.length >= LONG_PARLAY && (
            <div className="banner banner-warn" role="alert">
              <span aria-hidden="true">!</span>
              <span>
                Llevas {legs.length} piernas. Cada una le suma la comisión de la casa: a la larga, un parlay largo pierde más que uno de 2 o 3
                piernas, aunque pague más.
              </span>
            </div>
          )}
          {modelOnly > 0 && (
            <div className="banner banner-warn" role="alert">
              <span aria-hidden="true">!</span>
              <span>
                {modelOnly === legs.length
                  ? legs.length === 1
                    ? "En esta pierna"
                    : "En todas las piernas"
                  : `En ${modelOnly} de ${legs.length} piernas`}{" "}
                sólo el modelo ve valor; el mercado no. Cuando no coinciden, el resultado suele quedar más cerca del mercado.
              </span>
            </div>
          )}
          {suspicious > 0 && (
            <div className="banner banner-warn" role="alert">
              <span aria-hidden="true">!</span>
              <span>
                {suspicious === legs.length ? "Todas las piernas" : `${suspicious} de ${legs.length} piernas`} se separan más de 10 puntos de{" "}
                {myBook}. Diferencias así casi siempre son información que el modelo no tiene (alineaciones, descansos, lesiones). Revisa antes
                de apostar.
              </span>
            </div>
          )}

          {singles ? (
            <>
              <div className="slip-totals">
                <div className="stat">
                  <span className="stat-label">Total apostado</span>
                  <span className="stat-value">{money(singlesTotals.staked)}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Pago si aciertas todas</span>
                  <span className="stat-value">{singlesTotals.payoutAll !== null ? money(singlesTotals.payoutAll) : "—"}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Modelo: aciertos esperados</span>
                  <span className="stat-value">
                    {singlesTotals.expectedWins.toFixed(1)} <span className="muted small">de {legs.length}</span>
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">Mercado: aciertos esperados</span>
                  <span className="stat-value">
                    {singlesTotals.expectedWinsMarket !== null ? (
                      <>
                        {singlesTotals.expectedWinsMarket.toFixed(1)} <span className="muted small">de {legs.length}</span>
                      </>
                    ) : (
                      "—"
                    )}
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">Ganancia esperada (modelo)</span>
                  <span className={`stat-value ${singlesBothValue ? "ev-pos" : ""}`} title={ofStaked(singlesTotals.expectedProfit)}>
                    {signedMoney(singlesTotals.expectedProfit)}
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">Ganancia esperada (mercado)</span>
                  <span className={`stat-value ${singlesBothValue ? "ev-pos" : ""}`} title={ofStaked(singlesTotals.expectedProfitMarket)}>
                    {signedMoney(singlesTotals.expectedProfitMarket)}
                  </span>
                </div>
              </div>
              {legs.length > 1 && (
                <label className="field" htmlFor={stakeId}>
                  Mismo monto en todas (MXN)
                  <input
                    id={stakeId}
                    className="input num"
                    type="number"
                    inputMode="decimal"
                    min={0}
                    step={10}
                    value={state.stake}
                    onChange={(e) => {
                      setError(null);
                      slip.setAllStakes(amount(e.target.value));
                    }}
                  />
                </label>
              )}
              {singlesTotals.payoutAll === null && (
                <p className="muted xs" style={{ margin: 0 }}>
                  Escribe los momios de {myBook || "tu casa"} para ver el pago y la ganancia esperada.
                </p>
              )}
            </>
          ) : (
            <>
              <div className="slip-totals">
                <div className="stat">
                  <span className="stat-label">Modelo: acertar todo</span>
                  <span className="stat-value">{pct(model.probability, 1)}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Mercado: acertar todo</span>
                  <span className="stat-value">{pct(model.marketProbability, 1)}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">{myBook || "Casa"}: acertar todo</span>
                  <span className="stat-value">{pBook !== null ? pct(pBook, 1) : "—"}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Momio {myBook}</span>
                  <span className="stat-value">{ticketOdd ? decimalLabel(ticketOdd) : "—"}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Valor esperado (modelo)</span>
                  <span className={`stat-value ${bothValue ? "ev-pos" : ""}`}>{signedPct(ev)}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Valor esperado (mercado)</span>
                  <span className={`stat-value ${bothValue ? "ev-pos" : ""}`}>{signedPct(evMarket)}</span>
                </div>
              </div>

              <div className="slip-totals">
                <label className="field" htmlFor={stakeId}>
                  Apuesta (MXN)
                  <input
                    id={stakeId}
                    className="input num"
                    type="number"
                    inputMode="decimal"
                    min={0}
                    step={10}
                    value={state.stake}
                    onChange={(e) => slip.setStake(Math.max(0, Number(e.target.value)))}
                  />
                </label>
                <label className="field" htmlFor={totalId}>
                  Momio total del boleto (opcional)
                  <input
                    id={totalId}
                    className="input num"
                    value={totalRaw}
                    onChange={(e) => {
                      setError(null);
                      slip.setTotalOdd(myBook, e.target.value);
                    }}
                    placeholder={product ? american(product) : "+1200"}
                  />
                </label>
              </div>
              <div className="stat">
                <span className="stat-label">Pago si aciertas todo</span>
                <span className="stat-value">{ticketOdd ? money(state.stake * ticketOdd) : `Escribe los momios de ${myBook || "tu casa"}`}</span>
              </div>
            </>
          )}
          <p className="muted xs" style={{ margin: 0 }}>
            Mercado: probabilidad sin comisión de Pinnacle o, si no la cotiza, la mediana de las casas. Hay valor cuando{" "}
            {myBook || "tu casa"} paga más que el momio justo del modelo y del mercado.
          </p>

          {error && (
            <p className="banner banner-warn" role="alert" style={{ margin: 0 }}>
              {error}
            </p>
          )}

          <div className="card-actions">
            <button type="button" className="btn btn-sm btn-primary" onClick={submit} disabled={register.isPending}>
              {register.isPending ? <Spinner label="Registrando" /> : null}
              {singles && legs.length > 1 ? `Registrar ${legs.length} apuestas` : "Registrar apuesta"}
            </button>
            <button type="button" className="btn btn-sm" onClick={copy}>
              Copiar
            </button>
            <button type="button" className="btn btn-sm" onClick={clear}>
              Vaciar
            </button>
          </div>
          <p className="muted xs" style={{ margin: 0 }}>
            {singles
              ? `Registrar guarda cada pierna como una apuesta aparte en Mis apuestas, con los momios de ${myBook || "tu casa"}; cada una se liquida sola al terminar su partido. Se registran antes de que empiece su partido.`
              : `Registrar guarda tu boleto en Mis apuestas con los momios de ${myBook || "tu casa"}; se liquida solo al terminar los partidos. Sólo se puede registrar antes de que empiece el primer partido.`}
          </p>
        </>
      )}
    </div>
  );
}

/** Boleto (común a los dos deportes): panel fijo en escritorio; barra inferior + hoja deslizable en móvil. */
export function BetSlip({ bookmaker, apiBooks }: { bookmaker: string; apiBooks: string[] }) {
  const state = useSlip();
  const [open, setOpen] = useState(false);
  const openerRef = useRef<HTMLButtonElement>(null);
  const model = summarize(state.legs.map((l) => ({ matchId: l.matchId, pModel: l.pModel, odd: null })));

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      openerRef.current?.focus();
    };
  }, [open]);

  return (
    <aside className="slip-aside" aria-label="Boleto">
      <div className="card slip-desktop">
        <SlipBody bookmaker={bookmaker} apiBooks={apiBooks} />
      </div>

      <div className="slip-mobile-bar">
        <span className="small">
          <strong>Boleto ({state.legs.length})</strong>
          {state.legs.length > 1 && slipMode(state) === "singles" ? (
            <span className="muted num"> · {state.legs.length} individuales</span>
          ) : (
            state.legs.length > 0 && <span className="muted num"> · modelo {pct(model.probability, 1)}</span>
          )}
        </span>
        <button ref={openerRef} type="button" className="btn btn-primary" aria-expanded={open} onClick={() => setOpen(true)}>
          Ver boleto
        </button>
      </div>
      <div className="sheet-backdrop" data-open={open} onClick={() => setOpen(false)} />
      {open && (
        <div className="card sheet" role="dialog" aria-modal="true" aria-label="Boleto">
          <SlipBody bookmaker={bookmaker} apiBooks={apiBooks} onClose={() => setOpen(false)} />
        </div>
      )}
    </aside>
  );
}
