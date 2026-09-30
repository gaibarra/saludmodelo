"use client";
import { useEffect, useState } from "react";
import TaskHistory from "./TaskHistory";
import ReservationEditor,{Reservation} from "./ReservationEditor";
import TaskCapacity from "./TaskCapacity";
import AdministrativeTimeRequests, {AdministrativeTimeForm} from './AdministrativeTime';
import TimeCorrection from "./TimeCorrection";
import Link from "next/link";
import { api, listApi, setCsrf } from "../../lib/api";
type Fields = {
  reservation_plan:Reservation[];
  budget_bucket:string;
  title: string;
  owner: number;
  substitute: number | null;
  coordinator: number | null;
  starts: string;
  due: string;
  priority: string;
  estimated_minutes: number;
  acceptance_criteria: string;
  predecessors: number[];
};
type Task = Fields & {
  id: number;
  etag: number;
  committed: boolean;
  state: string;
  owner_name: string;
  active_substitutions: {id:number;user_id:number;user__username:string;starts:string;ends:string}[];
  actual_minutes: number;
  blocked_since: string | null;
  changes?: {
    id: number;
    state: string;
    rationale: string;
    requested_by__username: string;
    review_reason: string;
    proposal: Fields & { cancel: boolean };
  }[];
  events?: {
    actor__username: string;
    kind: string;
    note: string;
    created_at: string;
  }[];
  time_entries?: {
    id:number;effective_minutes:number;correction_version:number;can_correct:boolean;can_request_correction?:boolean;
    corrections:{version:number;minutes:number;rationale:string;actor__username?:string;created_at:string}[];
    actor__username: string;
    day: string;
    minutes: number;
    note: string;
  }[];
};
type Board = {
  updated_at: string;
  today: string;
  timezone: string;
  can_edit: boolean;
  can_work: boolean;
  can_review_baseline: boolean;
  can_calendar: boolean;
  people: { user_id: number; user__username: string; role: string }[];
  tasks: Task[];
  forecast: {
    task: number;
    starts: string | null;
    due: string | null;
    blocked: boolean;
  }[];
  calendar: {
    etag: number;
    confirmed: boolean;
    weekdays: number[];
    holidays: string[];
    rationale: string;
  };
  metrics: {
    capture: { label: string };
    validated: { label: string };
    accepted: { label: string };
    cancelled_committed: number;
    actual_minutes: number;
    estimated_minutes: number;
    uncommitted: number;
    overdue: number[];
    due_soon: number[];
    blocked: number[];
    critical: number[];
    load: {
      owner: number;
      name: string;
      tasks: number[];
      estimated_minutes: number;
    }[];
  };
  unavailable_metrics: string[];
  notifications: {
    coverage_id?: number | null;
    id: number;
    event__task_id: number;
    event__key: string;
    created_at: string;
  }[];
};
const empty: Fields = {
  reservation_plan:[],budget_bucket:"base",
  title: "",
  owner: 0,
  substitute: null,
  coordinator: null,
  starts: "2026-10-01",
  due: "2026-10-07",
  priority: "normal",
  estimated_minutes: 0,
  acceptance_criteria: "",
  predecessors: [],
};
const labels: Record<string, string> = {
  pending: "Pendiente",
  in_progress: "En curso",
  blocked: "Bloqueada",
  submitted: "Entrega en revisión",
  accepted: "Cierre aceptado",
  returned: "Devuelta",
  cancelled: "Cancelada",
};
export default function Tracking() {
  const [dependencyOptions,setDependencyOptions]=useState<{id:number;title:string;service__name:string}[]>([]);
  const [services, setServices] = useState<
      { id: number; name: string; site_name: string }[]
    >([]),
    [sid, setSid] = useState(0),
    [board, setBoard] = useState<Board>(),
    [selected, setSelected] = useState<Task>(),
    [form, setForm] = useState<Fields>(empty),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [stateFilter, setStateFilter] = useState(""),
    [priorityFilter, setPriorityFilter] = useState(""),
    [ownerFilter, setOwnerFilter] = useState(0),
    [from, setFrom] = useState(""),
    [to, setTo] = useState(""),
    [onlyIds, setOnlyIds] = useState<number[] | null>(null),
    [reason, setReason] = useState(""),
    [cancel, setCancel] = useState(false),
    [note, setNote] = useState(""),
    [minutes, setMinutes] = useState(60),
    [day, setDay] = useState("2026-10-01"),
    [timeKey, setTimeKey] = useState<string>(),
    [holidays, setHolidays] = useState(""),
    [weekdays, setWeekdays] = useState<number[]>([0, 1, 2, 3, 4]),
    [calendarReason, setCalendarReason] = useState(""),
    [source, setSource] = useState<{
      master_calendar: string;
      c22: { text: string }[];
    }>();
  useEffect(() => {
    api<{ authenticated: boolean; csrf: string }>("session/")
      .then(async (s) => {
        setCsrf(s.csrf);
        if (s.authenticated) setServices(await listApi("services/"));
        else setNotice("Inicie sesión desde Mi trabajo.");
      })
      .catch((e) => setNotice(e.message));
  }, []);
  async function load(id = sid) {
    setBusy(true);
    try {
      const b = await api<Board>(`tracking/services/${id}/`);
      setBoard(b);
      setDependencyOptions(await api<{id:number;title:string;service__name:string}[]>(`tracking/services/${id}/dependencies/`));
      setWeekdays(b.calendar.weekdays);
      setHolidays(b.calendar.holidays.join("\n"));
      setCalendarReason(b.calendar.rationale);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function open(id: number) {
    setBusy(true);
    try {
      const t = await api<Task>(`tracking/tasks/${id}/`);
      setSelected(t);
      const values = { ...empty };
      for (const key of Object.keys(empty) as (keyof Fields)[])
        Object.assign(values, { [key]: t[key] });
      setForm(values);
      setReason("");
      setNote("");
      setCancel(false);
      setTimeKey(undefined);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function showIds(ids: number[] | null) {
    setOnlyIds(ids);
    setStateFilter("");
    setPriorityFilter("");
    setOwnerFilter(0);
    setFrom("");
    setTo("");
  }
  function field<K extends keyof Fields>(key: K, value: Fields[K]) {
    setForm({ ...form, [key]: value });
  }
  async function send(path: string, body: unknown) {
    setBusy(true);
    setNotice("");
    try {
      const result = await api<Task>(path, "POST", body);
      await open(result.id);
      await load();
      setNotice("Registro guardado; la línea base sólo cambia con aprobación.");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const people =
    board?.people.filter(
      (p, i, a) => a.findIndex((x) => x.user_id === p.user_id) === i,
    ) ?? [];
  const visible =
    board?.tasks.filter(
      (t) =>
        (!stateFilter || t.state === stateFilter) &&
        (!priorityFilter || t.priority === priorityFilter) &&
        (!ownerFilter || t.owner === ownerFilter) &&
        (!from || t.due >= from) &&
        (!to || t.due <= to) &&
        (!onlyIds || onlyIds.includes(t.id)),
    ) ?? [];
  return (
    <main>
      <nav>
        <Link href="/personal">Mi trabajo</Link> ·{" "}
        <Link href="/cumplimiento">Cumplimiento</Link>
      </nav>
      <h1>Seguimiento y calendario</h1>
      <p role="status">{notice}</p>
      <label>
        Servicio de seguimiento
        <select
          aria-label="Servicio de seguimiento"
          disabled={busy}
          value={sid}
          onChange={(e) => {
            const id = Number(e.target.value);
            setSid(id);
            setBoard(undefined);
            setSelected(undefined);
            setSource(undefined);
            setForm({ ...empty });
            setOnlyIds(null);
            if (id) load(id);
          }}
        >
          <option value={0}>Seleccione…</option>
          {services.map((s) => (
            <option value={s.id} key={s.id}>
              {s.name} · {s.site_name}
            </option>
          ))}
        </select>
      </label>
      {board && (
        <>
          <p>
            Actualizado:{" "}
            {new Date(board.updated_at).toLocaleString("es-MX", {
              timeZone: board.timezone,
            })}{" "}
            · {board.timezone}
          </p>
          <p>
            Capacidad institucional de referencia: 295 horas base + 59 de
            reserva = 354 horas. Es provisional y no se multiplica por servicio.
            Horas registradas aquí:{" "}
            {(board.metrics.actual_minutes / 60).toFixed(2)}; estimadas
            comprometidas: {(board.metrics.estimated_minutes / 60).toFixed(2)}.
          </p>
          <section className="panel">
            <h2>Indicadores del servicio</h2>
            <p>
              Captura suficiente enviada: {board.metrics.capture.label}.
              Respuestas validadas: {board.metrics.validated.label}.{" "}
              <Link href="/personal/plan">Consultar cuestionario</Link>
            </p>
            <button
              onClick={() => {
                setOnlyIds(
                  board.tasks.filter((t) => t.committed).map((t) => t.id),
                );
                setStateFilter("");
              }}
            >
              Cierres aceptados: {board.metrics.accepted.label}
            </button>
            <p>
              Cancelaciones comprometidas conservadas en el denominador:{" "}
              {board.metrics.cancelled_committed}. Propuestas fuera de línea
              base: {board.metrics.uncommitted}.
            </p>
            {(
              [
                ["overdue", "Vencidas"],
                ["due_soon", "Vencen en siete días"],
                ["blocked", "Bloqueadas"],
                ["critical", "Prioridad crítica"],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                onClick={() => {
                  showIds(board.metrics[k]);
                  setStateFilter("");
                }}
              >
                {label}: {board.metrics[k].length}
              </button>
            ))}
            {board.unavailable_metrics.map((s) => (
              <p key={s}>{s}</p>
            ))}
          </section>
          <section className="panel">
            <h2>Filtrar tareas</h2>
            <label>
              Estado de tarea
              <select
                aria-label="Estado de tarea"
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
              >
                <option value="">Todos</option>
                {Object.entries(labels).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Prioridad del filtro
              <select
                aria-label="Prioridad del filtro"
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
              >
                <option value="">Todas</option>
                {["low", "normal", "high", "critical"].map((v) => (
                  <option key={v} value={v}>
                    {
                      {
                        low: "Baja",
                        normal: "Normal",
                        high: "Alta",
                        critical: "Crítica",
                      }[v]
                    }
                  </option>
                ))}
              </select>
            </label>
            <label>
              Responsable del filtro
              <select
                aria-label="Responsable del filtro"
                value={ownerFilter}
                onChange={(e) => setOwnerFilter(Number(e.target.value))}
              >
                <option value={0}>Todos</option>
                {people.map((p) => (
                  <option key={p.user_id} value={p.user_id}>
                    {p.user__username}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Vence desde
              <input
                type="date"
                value={from}
                onChange={(e) => setFrom(e.target.value)}
              />
            </label>
            <label>
              Vence hasta
              <input
                type="date"
                value={to}
                onChange={(e) => setTo(e.target.value)}
              />
            </label>
            <button
              onClick={() => {
                setOnlyIds(null);
                setStateFilter("");
                setPriorityFilter("");
                setOwnerFilter(0);
                setFrom("");
                setTo("");
              }}
            >
              Quitar filtros
            </button>
            <button disabled={busy} onClick={() => load()}>
              Actualizar seguimiento
            </button>
          </section>
          <section className="panel">
            <TaskCapacity key={sid} service={sid}/><h2>Tablero por estado</h2>
            {Object.entries(labels).map(([key, label]) => (
              <details key={key} open>
                <summary>
                  {label} ({visible.filter((t) => t.state === key).length})
                </summary>
                {visible
                  .filter((t) => t.state === key)
                  .map((t) => (
                    <p key={t.id}>
                      <button disabled={busy} onClick={() => open(t.id)}>
                        Tarea {t.id}: {t.title}
                      </button>{" "}
                      · {t.owner_name} · {t.starts} a {t.due} ·{" "}
                      {t.committed ? "Comprometida" : "Propuesta"}
                      {!!t.active_substitutions?.length && <span> · Suplencias vigentes: {t.active_substitutions.map(g=>`${g.user__username} (${g.starts} a ${g.ends})`).join(', ')}</span>}
                      {t.blocked_since &&
                        ` · Bloqueada desde ${new Date(t.blocked_since).toLocaleDateString("es-MX", { timeZone: board.timezone })}`}
                    </p>
                  ))}
              </details>
            ))}
          </section>
          <details className="panel">
            <summary>Calendario con dependencias y fechas propuestas</summary>
            <p>
              Las propuestas usan el calendario{" "}
              {board.calendar.confirmed
                ? "confirmado"
                : "provisional de lunes a viernes"}
              . No cambian las fechas aprobadas. Un bloqueo sin fecha de
              resolución deja las sucesoras sin fecha estimable.
            </p>
            <table>
              <thead>
                <tr>
                  <th>Tarea</th>
                  <th>Fechas guardadas</th>
                  <th>Predecesoras</th>
                  <th>Propuesta</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((t) => {
                  const f = board.forecast.find((f) => f.task === t.id);
                  return (
                    <tr key={t.id}>
                      <td>
                        <button onClick={() => open(t.id)}>{t.title}</button>
                      </td>
                      <td>
                        {t.starts} a {t.due}
                      </td>
                      <td>{t.predecessors.join(", ") || "Ninguna"}</td>
                      <td>
                        {f?.blocked
                          ? "Pendiente de resolver bloqueo"
                          : `${f?.starts} a ${f?.due}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </details>
          <details className="panel">
            <summary>Carga por responsable</summary>
            {board.metrics.load.map((l) => (
              <p key={l.owner}>
                <button
                  onClick={() => {
                    setOnlyIds(null);
                    setOwnerFilter(l.owner);
                  }}
                >
                  {l.name}: {l.tasks.length} tareas abiertas
                </button>{" "}
                · {(l.estimated_minutes / 60).toFixed(2)} horas estimadas
              </p>
            ))}
          </details>
          <details className="panel">
            <summary>Calendario institucional y referencia C22</summary>
            <p>
              Estado:{" "}
              {board.calendar.confirmed
                ? "Confirmado para avisos internos"
                : "Sin confirmar; los avisos programados están deshabilitados"}
              .
            </p>
            <button
              disabled={busy}
              onClick={async () => {
                try {
                  setSource(await api(`tracking/services/${sid}/source/`));
                } catch (e) {
                  setNotice((e as Error).message);
                }
              }}
            >
              Consultar calendario de la fuente
            </button>
            {source && (
              <>
                <pre>{source.master_calendar}</pre>
                {source.c22.map((r, i) => (
                  <p key={i}>{r.text}</p>
                ))}
              </>
            )}
            {board.can_calendar && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  setBusy(true);
                  try {
                    await api(`tracking/services/${sid}/calendar/`, "POST", {
                      version: board.calendar.etag,
                      weekdays,
                      holidays: holidays
                        .split("\n")
                        .map((s) => s.trim())
                        .filter(Boolean),
                      rationale: calendarReason,
                    });
                    await load();
                    setNotice(
                      "Calendario institucional confirmado y versionado.",
                    );
                  } catch (e) {
                    setNotice((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <p>
                  Este calendario afecta a todos los servicios de la
                  institución. Confirmarlo habilita avisos internos al
                  responsable y, tras dos y tres días hábiles sin respuesta, a
                  suplente y coordinador asignados.
                </p>
                {[
                  "Lunes",
                  "Martes",
                  "Miércoles",
                  "Jueves",
                  "Viernes",
                  "Sábado",
                  "Domingo",
                ].map((d, i) => (
                  <label key={i}>
                    <input
                      type="checkbox"
                      checked={weekdays.includes(i)}
                      onChange={(e) =>
                        setWeekdays(
                          e.target.checked
                            ? [...weekdays, i]
                            : weekdays.filter((x) => x !== i),
                        )
                      }
                    />
                    {d}
                  </label>
                ))}
                <label>
                  Fechas no laborables (AAAA-MM-DD, una por línea)
                  <textarea
                    value={holidays}
                    onChange={(e) => setHolidays(e.target.value)}
                  />
                </label>
                <label>
                  Fundamento del calendario
                  <textarea
                    required
                    value={calendarReason}
                    onChange={(e) => setCalendarReason(e.target.value)}
                  />
                </label>
                <button disabled={busy || !weekdays.length}>
                  Confirmar calendario institucional
                </button>
              </form>
            )}
          </details>
          <details className="panel">
            <summary>Avisos internos ({board.notifications.length})</summary>
            {board.notifications.map((n) => (
              <p key={n.id}>
                <button onClick={() => open(n.event__task_id)}>
                  Revisar tarea {n.event__task_id}
                </button>{" "}
                {n.coverage_id ? " · Por suplencia vigente · " : " · "}
                {new Date(n.created_at).toLocaleString("es-MX", {
                  timeZone: board.timezone,
                })}
              </p>
            ))}
          </details>
          {board.can_edit && (
            <>
              <button
                disabled={busy}
                onClick={() => {
                  setSelected(undefined);
                  setForm({ ...empty });
                  setReason("");
                  setCancel(false);
                }}
              >
                Nueva tarea propuesta
              </button>
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  send(
                    selected
                      ? `tracking/tasks/${selected.id}/change/`
                      : `tracking/services/${sid}/`,
                    selected
                      ? {
                          ...form,
                          version: selected.etag,
                          rationale: reason,
                          cancel,
                        }
                      : form,
                  );
                }}
              >
                <h2>
                  {selected
                    ? "Proponer cambio de línea base"
                    : "Preparar tarea"}
                </h2>
                <label>
                  Título de tarea
                  <input
                    required
                    maxLength={250}
                    value={form.title}
                    onChange={(e) => field("title", e.target.value)}
                  />
                </label>
                {(
                  [
                    ["owner", "Responsable de tarea"],
                    ["substitute", "Suplente de tarea"],
                    ["coordinator", "Coordinador de escalación"],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key}>
                    {label}
                    <select
                      aria-label={label}
                      value={form[key] ?? 0}
                      onChange={(e) =>
                        field(
                          key,
                          Number(e.target.value) ||
                            (key === "owner" ? 0 : null),
                        )
                      }
                    >
                      <option value={0}>Sin asignar</option>
                      {(key === "coordinator"
                        ? board.people.filter((p) => p.role === "coordinator")
                        : people
                      ).map((p) => (
                        <option key={p.user_id} value={p.user_id}>
                          {p.user__username}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
                <label>
                  Inicio previsto
                  <input
                    type="date"
                    min="2026-10-01"
                    required
                    value={form.starts}
                    onChange={(e) => field("starts", e.target.value)}
                  />
                </label>
                <label>
                  Fin previsto
                  <input
                    type="date"
                    min={form.starts}
                    required
                    value={form.due}
                    onChange={(e) => field("due", e.target.value)}
                  />
                </label>
                <label>
                  Prioridad de tarea
                  <select
                    aria-label="Prioridad de tarea"
                    value={form.priority}
                    onChange={(e) => field("priority", e.target.value)}
                  >
                    {["low", "normal", "high", "critical"].map((v) => (
                      <option key={v} value={v}>
                        {
                          {
                            low: "Baja",
                            normal: "Normal",
                            high: "Alta",
                            critical: "Crítica",
                          }[v]
                        }
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Esfuerzo estimado en minutos
                  <input
                    required
                    type="number"
                    min={0}
                    max={1000000}
                    value={form.estimated_minutes}
                    onChange={(e) =>
                      field("estimated_minutes", Number(e.target.value))
                    }
                  />
                </label>
                <ReservationEditor rows={form.reservation_plan} onChange={rows=>field('reservation_plan',rows)} owner={form.owner} substitute={form.substitute} starts={form.starts} disabled={busy}/>
                <label>Presupuesto de la tarea<select value={form.budget_bucket} onChange={e=>field('budget_bucket',e.target.value)}><option value="base">Base</option><option value="reserve">Reserva institucional</option></select></label>
                <label>
                  Criterios para aceptar el cierre
                  <textarea
                    required
                    maxLength={5000}
                    value={form.acceptance_criteria}
                    onChange={(e) =>
                      field("acceptance_criteria", e.target.value)
                    }
                  />
                </label>
                <fieldset>
                  <legend>Predecesoras que deben estar aceptadas</legend>
                  {dependencyOptions
                    .filter((t) => t.id !== selected?.id)
                    .map((t) => (
                      <label key={t.id}>
                        <input
                          type="checkbox"
                          checked={form.predecessors.includes(t.id)}
                          onChange={(e) =>
                            field(
                              "predecessors",
                              e.target.checked
                                ? [...form.predecessors, t.id]
                                : form.predecessors.filter((id) => id !== t.id),
                            )
                          }
                        />
                        {t.service__name}: {t.title}
                      </label>
                    ))}
                </fieldset>
                {selected && (
                  <>
                    <label>
                      Fundamento del cambio
                      <textarea
                        required
                        maxLength={5000}
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                      />
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={cancel}
                        onChange={(e) => setCancel(e.target.checked)}
                      />
                      Proponer cancelación sin borrar historia
                    </label>
                  </>
                )}
                <button disabled={busy || !form.owner}>
                  {selected
                    ? "Solicitar aprobación de línea base"
                    : "Guardar tarea propuesta"}
                </button>
              </form>
            </>
          )}
          {selected && (
            <section className="panel">
              <h2>Tarea seleccionada: {selected.title}</h2>
              <p>
                {labels[selected.state]} ·{" "}
                {selected.committed ? "Comprometida" : "Fuera de línea base"} ·{" "}
                {(selected.actual_minutes / 60).toFixed(2)} horas registradas
              </p>
              <p>Criterios: {selected.acceptance_criteria}</p>
              <fieldset disabled={busy || !board.can_work}>
                <legend>Avance y registro de trabajo</legend>
                {!board.can_work && (
                  <p>
                    Acceso de consulta: los cambios requieren un nombramiento de
                    trabajo.
                  </p>
                )}
                <label>
                  Resultado, bloqueo o fundamento
                  <textarea
                    maxLength={5000}
                    value={note}
                    onChange={(e) => {
                      setNote(e.target.value);
                      setTimeKey(undefined);
                    }}
                  />
                </label>
                {[
                  "in_progress",
                  "blocked",
                  "submitted",
                  "accepted",
                  "returned",
                ].map((target) => (
                  <button
                    key={target}
                    disabled={busy || !note.trim()}
                    onClick={() =>
                      send(`tracking/tasks/${selected.id}/state/`, {
                        version: selected.etag,
                        target,
                        note,
                      })
                    }
                  >
                    {labels[target]}
                  </button>
                ))}
                <h3>Tiempo real</h3>
                <label>
                  Fecha del trabajo
                  <input
                    type="date"
                    min="2026-10-01"
                    max={board.today}
                    value={day}
                    onChange={(e) => {
                      setDay(e.target.value);
                      setTimeKey(undefined);
                    }}
                  />
                </label>
                <label>
                  Minutos trabajados
                  <input
                    type="number"
                    min={1}
                    max={1440}
                    value={minutes}
                    onChange={(e) => {
                      setMinutes(Number(e.target.value));
                      setTimeKey(undefined);
                    }}
                  />
                </label>
                <button
                  disabled={busy || !note.trim()}
                  onClick={() => {
                    const key = timeKey ?? crypto.randomUUID();
                    setTimeKey(key);
                    send(`tracking/tasks/${selected.id}/time/`, {
                      day,
                      minutes,
                      note,
                      client_key: key,
                    });
                  }}
                >
                  Registrar tiempo real
                </button>
              </fieldset>
              <h3>Cambios propuestos e historial</h3>
              {selected.changes?.map((c) => (
                <article key={c.id}>
                  <p>
                    Propuesta {c.id} ·{" "}
                    {{
                      pending: "Pendiente",
                      approved: "Aprobada",
                      rejected: "Rechazada",
                    }[c.state] ?? c.state}{" "}
                    · {c.requested_by__username}: {c.rationale}
                  </p>
                  <p>
                    {c.proposal.cancel ? "Cancelar" : "Comprometer o modificar"}
                    : {c.proposal.title}; {c.proposal.starts} a {c.proposal.due}
                    ; responsable{" "}
                    {people.find((p) => p.user_id === c.proposal.owner)
                      ?.user__username ?? "fuera de nombramiento actual"}
                    ; {c.proposal.estimated_minutes} minutos.
                  </p>
                  <p>
                    Criterios propuestos: {c.proposal.acceptance_criteria}.
                    Predecesoras:{" "}
                    {c.proposal.predecessors.join(", ") || "ninguna"}
                  </p>
                  <p>Presupuesto: {c.proposal.budget_bucket==='reserve'?'Reserva institucional':'Base'}. Reservas: {(c.proposal.reservation_plan??[]).map(r=>`${r.day}: persona ${r.person}, ${r.minutes} min`).join('; ')||'Sin reservas explícitas'}.</p>
                  <p>{c.review_reason}</p>
                  {c.state === "pending" && board.can_review_baseline && (
                    <>
                      <button disabled={busy} onClick={async()=>{setBusy(true);try{const preview=await api<{message:string}>(`tracking/changes/${c.id}/preview/`,'POST',{});setNotice(preview.message);}catch(e){setNotice((e as Error).message);}finally{setBusy(false);}}}>Simular aprobación {c.id}</button>
                      <button
                        disabled={busy || !note.trim()}
                        onClick={() =>
                          send(`tracking/changes/${c.id}/decision/`, {
                            approve: true,
                            rationale: note,
                          })
                        }
                      >
                        Aprobar cambio {c.id}
                      </button>
                      <button
                        disabled={busy || !note.trim()}
                        onClick={() =>
                          send(`tracking/changes/${c.id}/decision/`, {
                            approve: false,
                            rationale: note,
                          })
                        }
                      >
                        Rechazar cambio {c.id}
                      </button>
                    </>
                  )}
                </article>
              ))}
              <TaskHistory key={selected.id} task={selected.id}/>
              <AdministrativeTimeRequests key={`admin-${selected.id}`} task={selected.id} onSaved={async()=>{await open(selected.id);await load();}}/>
              <details>
                <summary>Actividad y tiempo registrado</summary>
                {selected.events?.map((e, i) => (
                  <p key={i}>
                    {new Date(e.created_at).toLocaleString("es-MX", {
                      timeZone: board.timezone,
                    })}{" "}
                    · {e.actor__username}: {e.note}
                  </p>
                ))}
                {selected.time_entries?.map(e => (
                  <article key={e.id} aria-label={`Registro de horas ${e.id}`}>
                    <p>{e.day} · {e.actor__username} · {e.effective_minutes} minutos efectivos; original: {e.minutes}. {e.note}</p>
                    {e.corrections.map(c=><p key={c.version}>Ajuste {c.version}: {c.minutes} minutos · {c.actor__username} · {c.rationale} · {new Date(c.created_at).toLocaleString('es-MX')}</p>)}
                    {e.can_request_correction&&<AdministrativeTimeForm key={`admin-${e.id}-${e.correction_version}`} entry={e} onSaved={async()=>{await open(selected.id);await load();}}/>}
                    {e.can_correct&&<TimeCorrection key={`${e.id}-${e.correction_version}`} entry={e} onSaved={async()=>{await open(selected.id);await load();}}/>}
                  </article>
                ))}
              </details>
            </section>
          )}
        </>
      )}
    </main>
  );
}
