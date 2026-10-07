import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api, type SportKey, type SportMeta } from "../lib/api";
import { relativeTime } from "../lib/format";
import { sportFromPath, useSportContext } from "../lib/sportContext";
import { SPORT_KEYS, SPORTS } from "../lib/sports";

type Theme = "system" | "light" | "dark";
const THEME_KEY = "gorgo.theme";
const THEME_LABELS: Record<Theme, string> = { system: "Sistema", light: "Claro", dark: "Oscuro" };
const NEXT_THEME: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };

function readTheme(): Theme {
  try {
    const t = localStorage.getItem(THEME_KEY);
    return t === "light" || t === "dark" ? t : "system";
  } catch {
    return "system";
  }
}

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") delete root.dataset.theme;
    else root.dataset.theme = theme;
    try {
      if (theme === "system") localStorage.removeItem(THEME_KEY);
      else localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* sin almacenamiento: el tema dura la sesión */
    }
  }, [theme]);

  return (
    <button
      type="button"
      className="btn btn-ghost btn-sm"
      onClick={() => setTheme(NEXT_THEME[theme])}
      aria-label={`Tema: ${THEME_LABELS[theme]}. Cambiar a ${THEME_LABELS[NEXT_THEME[theme]]}`}
      title={`Tema: ${THEME_LABELS[theme]}`}
    >
      <span aria-hidden="true">{theme === "dark" ? "☾" : theme === "light" ? "☀" : "◐"}</span>
      <span className="sync-text">{THEME_LABELS[theme]}</span>
    </button>
  );
}

function dataJob(sport: SportKey, m: SportMeta) {
  return SPORTS[sport].dataJobs.map((job) => m.sync[job]).find(Boolean);
}

function SyncStatus({ sport }: { sport: SportKey }) {
  const { data, isError } = useQuery({ queryKey: ["meta"], queryFn: api.meta, refetchInterval: 60_000 });
  if (isError) return <span className="badge badge-lost">Sin conexión con la API</span>;
  if (!data) return null;

  const failed = SPORT_KEYS.flatMap((k) =>
    Object.entries(data.sports[k].sync)
      .filter(([, j]) => j.status === "failed")
      .map(([job]) => `${SPORTS[k].label} (${job})`),
  );
  const detail = SPORT_KEYS.flatMap((k) => {
    const m = data.sports[k];
    return [
      `${SPORTS[k].label} · modelo ${m.model_version}`,
      `  Partidos y estadísticas: ${relativeTime(dataJob(k, m)?.finished_at)}`,
      `  Momios (${data.bookmakers.join(", ")}): ${relativeTime(m.last_odds_at)}`,
      `  Picks calculados: ${relativeTime(m.last_picks_at)}`,
      ...SPORTS[k].syncLines(m).map((line) => `  ${line}`),
    ];
  });
  const current = data.sports[sport];

  return (
    <span className="sync-status small muted" title={[...detail, `Hora ${data.timezone}`].join("\n")}>
      {failed.length > 0 ? (
        <span className="badge badge-warn">
          <span aria-hidden="true">!</span> Falló la sincronización de {failed.join(", ")}
        </span>
      ) : (
        <span className="sync-text">
          {SPORTS[sport].label}: datos {relativeTime(dataJob(sport, current)?.finished_at)} · momios {relativeTime(current.last_odds_at)}
        </span>
      )}
    </span>
  );
}

function BrandMark({ sport }: { sport: SportKey }) {
  return (
    <svg className="brand-mark" viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r="46" fill="var(--accent)" />
      {sport === "nba" ? (
        <path d="M4 50h92M50 4v92M18 18c18 18 18 46 0 64M82 18c-18 18-18 46 0 64" stroke="var(--surface)" strokeWidth="5" fill="none" />
      ) : (
        <>
          <path d="M50 31l18 13-7 21H39l-7-21z" fill="var(--surface)" />
          <path
            d="M50 31V6M68 44l23-7M61 65l14 20M39 65L25 85M32 44L9 37"
            stroke="var(--surface)"
            strokeWidth="5"
            strokeLinecap="round"
            fill="none"
          />
        </>
      )}
    </svg>
  );
}

/** NBA | Fútbol: en Historial y Rendimiento cambia el deporte de la página; en lo demás lleva al día de ese deporte. */
function SportSwitch({ context }: { context: SportKey | null }) {
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const go = (target: SportKey) => {
    if (pathname === "/historial" || pathname === "/rendimiento") {
      const next = new URLSearchParams(params);
      next.set("deporte", target);
      next.delete("pagina");
      navigate({ pathname, search: next.toString() });
      return;
    }
    // Entre los días de los dos deportes se conserva la fecha elegida.
    const fecha = sportFromPath(pathname) ? params.get("fecha") : null;
    navigate(fecha ? `/${target}?fecha=${fecha}` : `/${target}`);
  };

  return (
    <div className="segmented sport-switch" role="group" aria-label="Deporte">
      {SPORT_KEYS.map((k) => (
        <button key={k} type="button" aria-pressed={context === k} onClick={() => context !== k && go(k)}>
          {SPORTS[k].label}
        </button>
      ))}
    </div>
  );
}

export function Header() {
  const { context, sport } = useSportContext();
  return (
    <header className="app-header">
      <NavLink to={`/${sport}`} className="brand" aria-label="Gorgo Predictions, inicio">
        <BrandMark sport={sport} />
        <span>Gorgo Predictions</span>
      </NavLink>
      <SportSwitch context={context} />
      <nav className="nav" aria-label="Principal">
        <NavLink to={`/${sport}`} end>
          Día
        </NavLink>
        {sport === "futbol" && <NavLink to="/futbol/jornada">Jornada</NavLink>}
        <NavLink to="/historial">Historial</NavLink>
        <NavLink to="/mis-apuestas">Mis apuestas</NavLink>
        <NavLink to={`/rendimiento?deporte=${sport}`}>Rendimiento</NavLink>
      </nav>
      <div className="header-right">
        <SyncStatus sport={sport} />
        <ThemeToggle />
      </div>
    </header>
  );
}
