import { LockedProjection } from "../../components/Locked";
import type { GameCardProps } from "../../components/SlateBody";
import { localTime, pct, shortTeam } from "../../lib/format";
import type { Absence, Game } from "./api";
import { AVAILABILITY_LABELS, LIVE_STATUSES, STATUS_LABELS } from "./config";

function StatusBadge({ game }: { game: Game }) {
  const label = STATUS_LABELS[game.status] ?? game.status;
  if (game.status === "NS" || game.status === "TBD") return <span className="small muted num">{localTime(game.starts_at)}</span>;
  if (LIVE_STATUSES.has(game.status)) {
    return (
      <span className="badge badge-live">
        <span aria-hidden="true">●</span> {label}
        {game.elapsed ? ` ${game.elapsed}'` : ""}
      </span>
    );
  }
  return <span className="badge badge-neutral">{label}</span>;
}

function TeamRow({ name, logo, expected, score }: { name: string; logo: string | null; expected?: number; score?: number | null }) {
  return (
    <div className="team-row">
      {logo ? <img src={logo} alt="" loading="lazy" /> : <span />}
      <span className="team-name" title={name}>
        {name}
      </span>
      <span className="team-proj num" title="Goles esperados por el modelo">
        {expected !== undefined ? expected.toFixed(2) : ""}
      </span>
      <span className="team-score num">{score ?? ""}</span>
    </div>
  );
}

function AbsenceLine({ team, absences }: { team: string; absences: Absence[] }) {
  if (absences.length === 0) return null;
  return (
    <p className="absence-line xs">
      <strong>{shortTeam(team)}:</strong>{" "}
      {absences.map((a, i) => (
        <span key={a.player_id}>
          {i > 0 && ", "}
          {a.name}{" "}
          <span className="muted">
            ({AVAILABILITY_LABELS[a.status].toLowerCase()}
            {a.manual ? ", manual" : ""})
          </span>
        </span>
      ))}
    </p>
  );
}

function FinalNote({ game }: { game: Game }) {
  const s = game.score;
  if (!s || s.final_home === null || (s.final_home === s.home && s.final_away === s.away && s.pen_home === null)) return null;
  return (
    <p className="xs muted" style={{ margin: 0 }}>
      A 90': {s.home}-{s.away} (así se liquida) · final {s.final_home}-{s.final_away}
      {s.pen_home !== null && ` · penales ${s.pen_home}-${s.pen_away}`}
    </p>
  );
}

export function GameCard({ game, selected, onSelect, onAbsences }: GameCardProps<Game>) {
  const proj = game.projection;
  const home = game.absences.filter((a) => a.team === "home");
  const away = game.absences.filter((a) => a.team === "away");
  const cards = proj && proj.home_cards !== null && proj.away_cards !== null ? proj.home_cards + proj.away_cards : null;
  const [topScore, topP] = proj?.top_scores[0] ?? ["", 0];
  const h = shortTeam(game.home.name);
  const a = shortTeam(game.away.name);

  return (
    <article className="card game-card" data-selected={selected} aria-label={`${game.home.name} contra ${game.away.name}`}>
      <div className="game-top">
        <StatusBadge game={game} />
        <span className="card-actions">
          {game.has_lineups && game.status === "NS" && (
            <span className="badge badge-won" title="Alineaciones confirmadas: las props ya sólo incluyen titulares">
              Alineaciones
            </span>
          )}
          {!game.has_odds && game.status === "NS" && (
            <span className="badge badge-neutral" title="La API todavía no publica momios de este partido (llegan de 1 a 14 días antes)">
              Sin momios
            </span>
          )}
        </span>
      </div>
      <TeamRow name={game.home.name} logo={game.home.logo} expected={proj?.home_goals} score={game.score?.home} />
      <TeamRow name={game.away.name} logo={game.away.logo} expected={proj?.away_goals} score={game.score?.away} />
      <FinalNote game={game} />
      {proj && (
        <>
          <div
            className="winbar winbar-3"
            role="img"
            aria-label={`Probabilidades: gana ${h} ${pct(proj.p_home)}, empate ${pct(proj.p_draw)}, gana ${a} ${pct(proj.p_away)}`}
          >
            <span style={{ width: `${proj.p_home * 100}%` }} />
            <span style={{ width: `${proj.p_draw * 100}%` }} />
            <span style={{ width: `${proj.p_away * 100}%` }} />
          </div>
          <div className="game-foot muted" aria-hidden="true">
            <span className="num" title={`Gana ${game.home.name}`}>
              1 · {pct(proj.p_home)}
            </span>
            <span className="num" title="Empate">
              X · {pct(proj.p_draw)}
            </span>
            <span className="num" title={`Gana ${game.away.name}`}>
              2 · {pct(proj.p_away)}
            </span>
          </div>
          <div className="game-facts xs">
            <span title="Marcador más probable a 90 minutos">
              Marcador <strong className="num">{topScore}</strong> <span className="muted num">({pct(topP)})</span>
            </span>
            <span title="Más de 2.5 goles">
              +2.5 <strong className="num">{pct(proj.p_over25)}</strong>
            </span>
            <span title="Ambos anotan">
              Ambos <strong className="num">{pct(proj.p_btts)}</strong>
            </span>
            {cards !== null && (
              <span title="Tarjetas esperadas (amarillas + rojas), incluye al árbitro">
                Tarjetas <strong className="num">{cards.toFixed(1)}</strong>
              </span>
            )}
          </div>
        </>
      )}
      {game.projection_locked && <LockedProjection outcomes={3} />}
      {(home.length > 0 || away.length > 0) && (
        <div className="absences">
          <AbsenceLine team={game.home.name} absences={home} />
          <AbsenceLine team={game.away.name} absences={away} />
        </div>
      )}
      {game.referee && (
        <p className="xs muted" style={{ margin: 0 }}>
          Árbitro: {game.referee.split(",")[0]}
        </p>
      )}
      <div className="game-foot">
        <span className="muted xs">{game.picks_count > 0 ? `${game.picks_count} piernas` : "Sin picks todavía"}</span>
        <span className="card-actions">
          <button type="button" className="btn btn-sm" onClick={onAbsences}>
            Bajas{game.absences.length > 0 ? ` (${game.absences.length})` : ""}
          </button>
          {onSelect && (
            <button type="button" className="btn btn-sm" aria-pressed={selected} onClick={onSelect} disabled={game.picks_count === 0}>
              {selected ? "Quitar filtro" : "Ver piernas"}
            </button>
          )}
        </span>
      </div>
    </article>
  );
}
