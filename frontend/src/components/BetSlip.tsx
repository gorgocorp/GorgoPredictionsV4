import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { oddFor } from "../lib/books";
import { american, money, pct, signedPct } from "../lib/format";
import { impliedProbability, parseOdds, verdict, type Verdict } from "../lib/oddsInput";
import { summarize } from "../lib/parlay";
import { commonPreferences, useCommonPreferences } from "../lib/preferences";
import { bookKey, slip, useSlip } from "../lib/slip";
import { SPORTS } from "../lib/sports";
import { Spinner } from "./States";
import { useToast } from "./Toast";

const VERDICT: Record<Verdict, { label: string; className: string; title: string }> = {
  suspicious: {
    label: "Sospechoso",
    className: "badge-warn",
    title: "El modelo se separa más de 10 puntos de la casa: casi siempre es información que el modelo no tiene",
  },
  value: { label: "Valor", className: "badge-won", title: "El modelo ve un poco más de probabilidad que la casa" },
  none: { label: "Sin valor", className: "badge-neutral", title: "La casa le da igual o más probabilidad que el modelo" },
};

function decimalLabel(d: number): string {
  return `${d.toFixed(2)} (${american(d)})`;
}

/** Casas para elegir en el boleto; "Otra…" deja escribir cualquier nombre. */
const BOOKS = ["Caliente", "1xBet", "Bet365", "Codere", "Betano", "Playdoit", "Strendus"];
const OTHER = "__otra__";

function SlipBody({ bookmaker, apiBooks, onClose }: { bookmaker: string; apiBooks: string[]; onClose?: () => void }) {
  const state = useSlip();
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
  const autoBooks = apiBooks.join(" o ");

  // Momio de la casa del usuario por pierna: el que escribió para esa casa o, si su casa está en la API
  // (Bet365, 1xBet), el de la API. Cada casa conserva sus propios momios escritos.
  const sameAsApi = key === bookmaker.toLowerCase();
  const legs = state.legs.map((l) => {
    const apiOdd = oddFor(l.bookOdds, myBook) ?? (sameAsApi && !l.bookOdds ? l.odd : null);
    const raw = l.typedOdds?.[key] ?? (apiOdd ? apiOdd.toFixed(2) : "");
    const book = parseOdds(raw);
    return { ...l, raw, book, pBook: book ? impliedProbability(book) : null };
  });
  const allPriced = legs.length > 0 && legs.every((l) => l.book !== null);
  const product = allPriced ? legs.reduce((acc, l) => acc * (l.book as number), 1) : null;
  const totalRaw = state.totalOdds?.[key] ?? "";
  const totalOverride = totalRaw ? parseOdds(totalRaw) : null;
  const ticketOdd = totalOverride ?? product;
  const model = summarize(state.legs.map((l) => ({ matchId: l.matchId, pModel: l.pModel, odd: null })));
  const pBook = ticketOdd ? 1 / ticketOdd : null;
  const ev = ticketOdd ? model.probability * ticketOdd - 1 : null;
  const suspicious = legs.filter((l) => l.pBook !== null && verdict(l.pModel, l.pBook) === "suspicious").length;

  const register = useMutation({
    mutationFn: () =>
      api.createBet({
        bookmaker: myBook,
        stake: state.stake,
        legs: legs.map((l) => ({ pick_id: l.pickId, odd: l.book as number })),
        total_odd: totalOverride ?? undefined,
      }),
    onSuccess: () => {
      slip.clear();
      queryClient.invalidateQueries({ queryKey: ["bets"] });
      notify(`Apuesta registrada en Mis apuestas (${myBook})`, { label: "Ver", onClick: () => navigate("/mis-apuestas") });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "No se pudo registrar la apuesta"),
  });

  const submit = () => {
    if (!myBook.trim()) return setError("Escribe el nombre de tu casa de apuestas.");
    const missing = legs.filter((l) => l.book === null).length;
    if (missing) return setError(`Escribe el momio de ${myBook} en ${missing === 1 ? "la pierna que falta" : `las ${missing} piernas que faltan`}.`);
    if (totalRaw && totalOverride === null) return setError("El momio total no es válido. Escribe, por ejemplo, +1200 o 13.00.");
    if (!(state.stake > 0)) return setError("Escribe cuánto apostaste.");
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
      (l, i) => `${i + 1}. ${SPORTS[l.sport].label} · ${l.matchup} — ${l.description}${l.book ? ` @ ${american(l.book)}` : ""}`,
    );
    const head = `Parlay ${legs.length} piernas · modelo ${pct(model.probability, 1)}${ticketOdd ? ` · ${myBook} ${american(ticketOdd)}` : ""}`;
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
          Agrega piernas con el botón <strong>+</strong> de la tabla o carga un parlay sugerido; puedes mezclar NBA y fútbol. Luego
          escribe los momios que te da {myBook || "tu casa"} para compararlos con el modelo y registrar tu apuesta. Si apuestas en{" "}
          {autoBooks}, sus momios se llenan solos desde la API.
        </p>
      ) : (
        <>
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
                    {l.pBook !== null && (
                      <span className={`badge ${VERDICT[verdict(l.pModel, l.pBook)].className}`} title={VERDICT[verdict(l.pModel, l.pBook)].title}>
                        {VERDICT[verdict(l.pModel, l.pBook)].label} {signedPct(l.pModel - l.pBook, 0)}
                      </span>
                    )}
                  </span>
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

          {model.sameGame.length > 0 && (
            <div className="banner banner-warn" role="alert">
              <span aria-hidden="true">!</span>
              <span>Tienes varias piernas del mismo partido. Están correlacionadas: la probabilidad del modelo no es confiable.</span>
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

          <div className="slip-totals">
            <div className="stat">
              <span className="stat-label">Modelo: acertar todo</span>
              <span className="stat-value">{pct(model.probability, 1)}</span>
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
              <span className={`stat-value ${ev !== null && ev > 0 && suspicious === 0 ? "ev-pos" : ""}`}>{signedPct(ev)}</span>
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

          {error && (
            <p className="banner banner-warn" role="alert" style={{ margin: 0 }}>
              {error}
            </p>
          )}

          <div className="card-actions">
            <button type="button" className="btn btn-sm btn-primary" onClick={submit} disabled={register.isPending}>
              {register.isPending ? <Spinner label="Registrando" /> : null}
              Registrar apuesta
            </button>
            <button type="button" className="btn btn-sm" onClick={copy}>
              Copiar
            </button>
            <button type="button" className="btn btn-sm" onClick={clear}>
              Vaciar
            </button>
          </div>
          <p className="muted xs" style={{ margin: 0 }}>
            Registrar guarda tu boleto en Mis apuestas con los momios de {myBook || "tu casa"}; se liquida solo al terminar los partidos. Sólo
            se puede registrar antes de que empiece el primer partido.
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
          {state.legs.length > 0 && <span className="muted num"> · modelo {pct(model.probability, 1)}</span>}
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
