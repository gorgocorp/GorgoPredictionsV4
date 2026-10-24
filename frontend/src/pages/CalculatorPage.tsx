import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { useToast } from "../components/Toast";
import { ValueBadge } from "../components/ValueBadge";
import { api, type Leg, type SlateGame, type SystemParlay } from "../lib/api";
import { calculator, checkSide, commission, marketLines, recommend, type LineGroup, type Recommendation, type SideCheck } from "../lib/calculator";
import { localTime, longDate, odds, pct, signedPct } from "../lib/format";
import { commonPreferences } from "../lib/preferences";
import { matchupOf, slip, toSlipLeg } from "../lib/slip";
import { asSport, SPORT_KEYS, SPORTS, type SportConfig } from "../lib/sports";

/** La casa que no está en la API y cuyos momios se escriben aquí. */
const BOOK = "Caliente";

/** Un partido del parlay con valor: la pierna publicada, las líneas que tiene V4 y lo escrito en la línea escogida. */
interface MatchState {
  game: SlateGame | undefined;
  published: SystemParlay["legs"][number];
  lines: LineGroup[];
  group: LineGroup;
  checks: SideCheck[];
  /** Ya empezó: no se puede apostar y no entra en la recomendación. */
  started: boolean;
}

function evText(c: SideCheck): string {
  return `modelo ${signedPct(c.evModel)} · mercado ${signedPct(c.evMarket)}`;
}

function MatchCard({ config, match, onLine, onOdd }: {
  config: SportConfig;
  match: MatchState;
  onLine: (line: number) => void;
  onOdd: (pickId: number, value: string) => void;
}) {
  const { game, published, lines, group, checks, started } = match;
  const fee = commission(checks);
  return (
    <section className="card card-pad calc-match" aria-label={`Partido ${matchupOf(config, game)}`}>
      <div className="section-head" style={{ marginBottom: 0 }}>
        <h2>{matchupOf(config, game)}</h2>
        {game && <span className="muted small num">{started ? "Ya empezó" : localTime(game.starts_at)}</span>}
      </div>
      <p className="muted small" style={{ margin: 0 }}>
        En el parlay: {published.description} · Bet365 {odds(published.odd)} · se promete{" "}
        {pct(published.p_market === null ? published.p_model : Math.min(published.p_model, published.p_market))}
      </p>
      {lines.length > 1 && (
        <div className="segmented" role="group" aria-label={`Línea de ${BOOK}`}>
          {lines.map((g) => (
            <button key={g.line} type="button" aria-pressed={g.line === group.line} onClick={() => g.line !== null && onLine(g.line)}>
              {g.line}
            </button>
          ))}
        </div>
      )}
      <ul className="calc-sides">
        {checks.map((c) => (
          <li key={c.leg.id} className="calc-side">
            <span className="calc-side-name">
              {c.leg.description}
              <br />
              <span className="muted xs num">
                Modelo {pct(c.leg.p_model)} · Mercado {pct(c.leg.p_market)}
                {c.leg.odd !== null && ` · Bet365 ${c.leg.odd.toFixed(2)}`}
              </span>
            </span>
            <input
              className="input num"
              value={c.raw}
              onChange={(e) => onOdd(c.leg.id, e.target.value)}
              placeholder="-118"
              inputMode="text"
              disabled={started}
              aria-label={`Momio de ${BOOK} para ${c.leg.description}`}
            />
            <span className="xs num">
              Hay valor desde <strong>{odds(c.valueFrom)}</strong>
              {c.raw && c.odd === null && <span style={{ color: "var(--lost)" }}> · momio no válido</span>}
              {c.odd !== null && (
                <>
                  <br />
                  <span className="muted">{evText(c)}</span>
                </>
              )}
            </span>
            {c.value && <ValueBadge value={c.value} />}
          </li>
        ))}
      </ul>
      {fee !== null && (
        <p className="muted xs" style={{ margin: 0 }}>
          Comisión de {BOOK} en esta línea: {pct(fee, 1)}.
        </p>
      )}
    </section>
  );
}

function RecommendationCard({ rec, onLoad }: { rec: Recommendation; onLoad: (picks: SideCheck[], mode: "parlay" | "singles") => void }) {
  if (rec.kind === "missing") {
    return (
      <section className="card card-pad" aria-labelledby="calc-rec-title">
        <h2 id="calc-rec-title">Recomendación</h2>
        <p className="muted small" style={{ margin: 0 }}>
          Escribe los momios de {BOOK} de cada partido (en la línea que ofrece) para ver qué conviene meter.
        </p>
      </section>
    );
  }
  return (
    <section className="card card-pad calc-rec" aria-labelledby="calc-rec-title" aria-live="polite">
      {rec.kind === "none" && (
        <>
          <h2 id="calc-rec-title">Hoy no metas nada</h2>
          <p className="small" style={{ margin: 0 }}>
            {BOOK} no paga lo suficiente en ninguna opción para que el modelo y el mercado vean valor.
            {rec.closest &&
              ` La más cercana: ${rec.closest.leg.description} a ${odds(rec.closest.odd)}, que necesita ${odds(rec.closest.valueFrom)} o más.`}{" "}
            Que no haya apuesta también es una respuesta.
          </p>
        </>
      )}
      {rec.kind === "single" && (
        <>
          <h2 id="calc-rec-title">Mete sólo esta pierna</h2>
          <p className="small" style={{ margin: 0 }}>
            <strong>{rec.pick.leg.description}</strong> a {odds(rec.pick.odd)} (hay valor desde {odds(rec.pick.valueFrom)}): valor
            esperado {evText(rec.pick)}. La otra no tiene valor: meterla en parlay le quita el valor a esta.
          </p>
          <div className="card-actions">
            <button type="button" className="btn btn-sm btn-primary" onClick={() => onLoad([rec.pick], "singles")}>
              Cargar al boleto
            </button>
          </div>
        </>
      )}
      {rec.kind === "parlay" && (
        <>
          <h2 id="calc-rec-title">Mete el parlay</h2>
          <p className="small" style={{ margin: 0 }}>
            <strong>{rec.picks.map((p) => p.leg.description).join(" + ")}</strong>. {BOOK} paga {odds(rec.odd)} y hay valor desde{" "}
            {odds(rec.valueFrom)}: valor esperado modelo {signedPct(rec.evModel)} · mercado {signedPct(rec.evMarket)}.
          </p>
          <div className="card-actions">
            <button type="button" className="btn btn-sm btn-primary" onClick={() => onLoad(rec.picks, "parlay")}>
              Cargar al boleto
            </button>
          </div>
        </>
      )}
      <p className="muted xs" style={{ margin: 0 }}>
        Valor no es seguridad: un parlay de 2 piernas de 45% a 65% cada una se pierde la mayoría de las veces aunque el precio
        convenga. El valor se ve a la larga y con monto fijo.
      </p>
    </section>
  );
}

/**
 * Calculadora Caliente (sólo admin): con el parlay con valor del día y los momios de Caliente (que no están en la API),
 * recomienda meter el parlay, una sola pierna o nada. No escribe nada: lo que se mete se registra en Mis apuestas.
 */
export function CalculatorPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const notify = useToast();
  const state = calculator.use();
  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta, refetchInterval: 60_000 });
  const sport = asSport(params.get("deporte")) ?? "futbol";
  const config = SPORTS[sport];
  const today = meta.data?.today;
  const date = params.get("fecha") ?? today;
  const day = useQuery({ queryKey: [sport, "day", date], queryFn: () => config.loadDay(date!), enabled: !!date });
  const legs = useQuery({ queryKey: [sport, "legs", date], queryFn: () => config.loadLegs(date!), enabled: !!date });

  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(changes)) {
      if (v === null) next.delete(k);
      else next.set(k, v);
    }
    setParams(next);
  };

  if (meta.isError) return <ErrorState message={(meta.error as Error).message} onRetry={() => meta.refetch()} />;

  const parlay = day.data?.parlays.find((p) => p.mode === "value");
  const byId = new Map((legs.data ?? []).map((l) => [l.id, l]));
  const games = new Map((day.data?.games ?? []).map((g) => [g.match_id, g]));
  const now = Date.now();
  const matches: MatchState[] = (parlay?.legs ?? []).flatMap((published) => {
    const leg: Leg | undefined = byId.get(published.pick_id);
    if (!leg) return [];
    const lines = marketLines(leg, legs.data ?? []);
    const chosen = state.lines[String(published.match_id)] ?? leg.line;
    const group = lines.find((g) => g.line === chosen) ?? lines.find((g) => g.line === leg.line) ?? lines[0];
    const game = games.get(published.match_id);
    return [{
      game,
      published,
      lines,
      group,
      checks: group.legs.map((l) => checkSide(l, state.odds[String(l.id)] ?? "")),
      started: game ? new Date(game.starts_at).getTime() <= now : false,
    }];
  });
  const rec = recommend(matches.filter((m) => !m.started).map((m) => m.checks));

  const setLine = (matchId: number, line: number) => calculator.set({ ...state, lines: { ...state.lines, [String(matchId)]: line } });
  const setOdd = (pickId: number, value: string) => calculator.set({ ...state, odds: { ...state.odds, [String(pickId)]: value } });

  const load = (picks: SideCheck[], mode: "parlay" | "singles") => {
    const previous = slip.get();
    slip.replace(picks.map((p) => toSlipLeg(config, p.leg, games.get(p.leg.match_id), date!)), mode);
    for (const p of picks) slip.setLegOdd(p.leg.id, BOOK, p.raw);
    commonPreferences.update({ myBook: BOOK });
    navigate(`/${sport}${date === today ? "" : `?fecha=${date}`}`);
    notify(`${picks.length === 1 ? "Pierna cargada" : "Parlay cargado"} al boleto con los momios de ${BOOK}`, {
      label: "Deshacer",
      onClick: () => slip.restore(previous),
    });
  };

  return (
    <div className="day-main">
      <div className="section-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>
            Calculadora {BOOK} <span className="badge badge-live">Sólo admin</span>
          </h1>
          <p className="muted small" style={{ margin: 0 }}>
            Parte del parlay con valor del día. {BOOK} suele ofrecer otra línea que Bet365: en cada partido escoge la que
            ofrece y escribe sus momios. Con la misma regla que el boleto (hay valor si {BOOK} paga más que el momio justo del
            modelo y del mercado), te dice si conviene meter el parlay, una sola pierna o nada.
          </p>
        </div>
      </div>

      <div className="card-actions">
        <div className="segmented" role="group" aria-label="Deporte">
          {SPORT_KEYS.map((k) => (
            <button key={k} type="button" aria-pressed={k === sport} onClick={() => update({ deporte: k })}>
              {SPORTS[k].label}
            </button>
          ))}
        </div>
        {date && (
          <input
            className="input num"
            type="date"
            value={date}
            onChange={(e) => e.target.value && update({ fecha: e.target.value === today ? null : e.target.value })}
            aria-label="Fecha (hora local)"
          />
        )}
        <button type="button" className="btn" disabled={!today || date === today} onClick={() => update({ fecha: null })}>
          Hoy
        </button>
      </div>

      {!date || day.isPending || legs.isPending ? (
        <Skeleton height={260} />
      ) : day.isError || legs.isError ? (
        <ErrorState
          message={((day.error ?? legs.error) as Error).message}
          onRetry={() => {
            day.refetch();
            legs.refetch();
          }}
        />
      ) : !parlay || matches.length === 0 ? (
        <EmptyState title={`Sin parlay con valor de ${config.label} el ${longDate(date).toLowerCase()}`}>
          Se publica desde la noche anterior si hay piernas que cumplan la regla (en NBA, cuando llegan sus momios). Que no
          haya parlay también es una respuesta.
        </EmptyState>
      ) : (
        <>
          <div className="calc-grid">
            {matches.map((m) => (
              <MatchCard
                key={m.published.pick_id}
                config={config}
                match={m}
                onLine={(line) => setLine(m.published.match_id, line)}
                onOdd={setOdd}
              />
            ))}
          </div>
          <RecommendationCard rec={rec} onLoad={load} />
        </>
      )}
    </div>
  );
}
