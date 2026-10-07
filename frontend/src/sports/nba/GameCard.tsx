import { lastWord, localTime, pct } from "../../lib/format";
import type { GameCardProps } from "../../components/SlateBody";
import type { Absence, Game, RosterSide } from "./api";
import { AVAILABILITY_LABELS, LIVE_STATUSES, STATUS_LABELS } from "./config";

function StatusBadge({ game }: { game: Game }) {
  const label = STATUS_LABELS[game.status] ?? game.status;
  if (game.status === "NS") return <span className="small muted num">{localTime(game.starts_at)}</span>;
  if (LIVE_STATUSES.has(game.status)) {
    return (
      <span className="badge badge-live">
        <span aria-hidden="true">●</span> {label}
      </span>
    );
  }
  return <span className="badge badge-neutral">{label}</span>;
}

function TeamRow({ name, logo, projected, score }: { name: string; logo: string | null; projected?: number; score?: number }) {
  return (
    <div className="team-row">
      {logo ? <img src={logo} alt="" loading="lazy" /> : <span />}
      <span className="team-name" title={name}>
        {name}
      </span>
      <span className="team-proj num" title="Puntos proyectados por el modelo">
        {projected !== undefined ? projected.toFixed(1) : ""}
      </span>
      <span className="team-score num">{score ?? ""}</span>
    </div>
  );
}

function AbsenceLine({ team, absences, missing }: { team: string; absences: Absence[]; missing: number }) {
  if (absences.length === 0) return null;
  return (
    <p className="absence-line xs">
      <strong>{lastWord(team)}:</strong>{" "}
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
      {missing > 0 && <span className="muted"> · −{missing.toFixed(1)} pts de producción</span>}
    </p>
  );
}

function RosterLine({ team, side }: { team: string; side: RosterSide | null }) {
  if (!side) return null;
  const names = (list: [string, number][]) => list.map(([n, p]) => `${n} (${p.toFixed(0)})`).join(", ");
  return (
    <p className="absence-line xs">
      <strong>{lastWord(team)}:</strong>{" "}
      {side.arrived.length > 0 && <>llegaron {names(side.arrived)}. </>}
      {side.departed.length > 0 && <>Se fueron {names(side.departed)}. </>}
      <span className="muted">
        Neto {side.gain >= 0 ? "+" : ""}
        {side.gain.toFixed(1)} pts de producción · se aplica al {Math.round(side.weight * 100)}%
      </span>
    </p>
  );
}

export function GameCard({ game, selected, onSelect, onAbsences }: GameCardProps<Game>) {
  const proj = game.projection;
  const pHome = proj?.p_home_win;
  const away = game.absences.filter((a) => a.team === "away");
  const home = game.absences.filter((a) => a.team === "home");
  return (
    <article className="card game-card" data-selected={selected} aria-label={`${game.away.name} en ${game.home.name}`}>
      <div className="game-top">
        <StatusBadge game={game} />
        {!game.has_odds && game.status === "NS" && (
          <span className="badge badge-neutral" title="La API todavía no publica momios de este partido">
            Sin momios
          </span>
        )}
      </div>
      <TeamRow name={game.away.name} logo={game.away.logo} projected={proj?.away_points} score={game.score?.away} />
      <TeamRow name={game.home.name} logo={game.home.logo} projected={proj?.home_points} score={game.score?.home} />
      {proj && pHome !== undefined && (
        <>
          <div
            className="winbar"
            role="img"
            aria-label={`Probabilidad de ganar: ${lastWord(game.away.name)} ${pct(1 - pHome)}, ${lastWord(game.home.name)} ${pct(pHome)}`}
          >
            <span style={{ width: `${(1 - pHome) * 100}%` }} />
            <span style={{ width: `${pHome * 100}%` }} />
          </div>
          <div className="game-foot muted">
            <span className="num">
              {lastWord(game.away.name)} {pct(1 - pHome)}
            </span>
            <span className="num">Total {(proj.home_points + proj.away_points).toFixed(1)}</span>
            <span className="num">
              {pct(pHome)} {lastWord(game.home.name)}
            </span>
          </div>
        </>
      )}
      {(away.length > 0 || home.length > 0) && (
        <div className="absences">
          <AbsenceLine team={game.away.name} absences={away} missing={game.missing_points.away} />
          <AbsenceLine team={game.home.name} absences={home} missing={game.missing_points.home} />
        </div>
      )}
      {(game.roster.detail.away || game.roster.detail.home) && (
        <details className="roster-changes">
          <summary className="xs">Cambios de plantel vs. temporada pasada</summary>
          <div className="absences">
            <RosterLine team={game.away.name} side={game.roster.detail.away} />
            <RosterLine team={game.home.name} side={game.roster.detail.home} />
            <p className="muted xs" style={{ margin: 0 }}>
              Puntos por partido en los mismos minutos. El ajuste se desvanece conforme se juegan partidos de esta temporada.
            </p>
          </div>
        </details>
      )}
      {game.injury_report.pending.length > 0 && (
        <p className="xs muted" style={{ margin: 0 }}>
          Reporte de lesiones pendiente:{" "}
          {game.injury_report.pending.map((s) => lastWord(s === "home" ? game.home.name : game.away.name)).join(", ")}
        </p>
      )}
      <div className="game-foot">
        <span className="muted xs">{game.picks_count > 0 ? `${game.picks_count} piernas` : "Sin picks todavía"}</span>
        <span className="card-actions">
          <button type="button" className="btn btn-sm" onClick={onAbsences}>
            Bajas{game.absences.length > 0 ? ` (${game.absences.length})` : ""}
          </button>
          <button type="button" className="btn btn-sm" aria-pressed={selected} onClick={onSelect} disabled={game.picks_count === 0}>
            {selected ? "Quitar filtro" : "Ver piernas"}
          </button>
        </span>
      </div>
    </article>
  );
}
