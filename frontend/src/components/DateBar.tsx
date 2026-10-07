import type { CalendarDay } from "../lib/api";

function neighbours(calendar: CalendarDay[] | undefined, date: string) {
  if (!calendar) return { prev: undefined, next: undefined };
  const prev = [...calendar].reverse().find((d) => d.date < date)?.date;
  const next = calendar.find((d) => d.date > date)?.date;
  return { prev, next };
}

/** Elegir día: anterior / siguiente con partidos (calendario del deporte), fecha y Hoy. */
export function DateBar({
  date,
  today,
  calendar,
  onChange,
}: {
  date: string;
  today: string;
  calendar: CalendarDay[] | undefined;
  onChange: (d: string) => void;
}) {
  const { prev, next } = neighbours(calendar, date);
  return (
    <div className="card-actions" role="group" aria-label="Elegir día">
      <button type="button" className="btn btn-icon" disabled={!prev} onClick={() => prev && onChange(prev)} aria-label="Día anterior con partidos" title="Día anterior con partidos">
        ‹
      </button>
      <input className="input num" type="date" value={date} onChange={(e) => e.target.value && onChange(e.target.value)} aria-label="Fecha (hora local)" />
      <button type="button" className="btn btn-icon" disabled={!next} onClick={() => next && onChange(next)} aria-label="Siguiente día con partidos" title="Siguiente día con partidos">
        ›
      </button>
      <button type="button" className="btn" disabled={date === today} onClick={() => onChange(today)}>
        Hoy
      </button>
    </div>
  );
}
