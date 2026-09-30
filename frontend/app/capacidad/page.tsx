"use client";
import { useEffect, useState } from "react";
import PlanningControl from "./PlanningControl";
import Link from "next/link";
import { api, setCsrf } from "../../lib/api";
type Day = {
  id: number;
  person: number;
  name: string;
  day: string;
  etag: number;
  confirmed: boolean;
  minutes: number;
  unavailable_minutes: number;
  available_minutes: number | null;
  unallocated_minutes: number | null;
  needs_review: boolean;
  allocations: { service_id: number; minutes: number }[];
};
type Proposal = {
  minutes: number;
  unavailable_minutes: number;
  allocations: { service: number; minutes: number }[];
};
type Change = {
  id: number;
  capacity_id: number;
  state: string;
  requested_by: number;
  rationale: string;
  proposal: Proposal;
  previous: {
    etag: number;
    confirmed: boolean;
    minutes: number;
    unavailable_minutes: number;
    allocations: { service_id: number; minutes: number }[];
  };
  review_reason: string;
  reviewed_by: number | null;
};
type Board = {
  start: string;
  end_exclusive: string;
  user_id: number;
  days: Day[];
  changes: Change[];
  people: { user_id: number; user__username: string }[];
  services: { id: number; name: string }[];
};
const states: Record<string, string> = {
  pending: "Pendiente",
  approved: "Aprobada",
  rejected: "Rechazada",
};
export default function Capacity() {
  const [institutions, setInstitutions] = useState<
      { id: number; name: string }[]
    >([]),
    [institution, setInstitution] = useState(""),
    [start, setStart] = useState("2026-10-01"),
    [board, setBoard] = useState<Board>();
  const [person, setPerson] = useState(""),
    [day, setDay] = useState(""),
    [minutes, setMinutes] = useState(""),
    [absence, setAbsence] = useState(""),
    [allocation, setAllocation] = useState<Record<string, string>>({}),
    [rationale, setRationale] = useState(""),
    [reasons, setReasons] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [attempt, setAttempt] = useState<{ body: string; key: string }>();
  useEffect(() => {
    Promise.all([
      api<{ csrf: string }>("session/"),
      api<{ id: number; name: string }[]>("capacity/institutions/"),
    ])
      .then(([session, rows]) => {
        setCsrf(session.csrf);
        setInstitutions(rows);
      })
      .catch((e) => setNotice(e.message));
  }, []);
  async function run(work: () => Promise<void>) {
    setBusy(true);
    setNotice("");
    try {
      await work();
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function load() {
    setBoard(
      await api<Board>(`capacity/institutions/${institution}/?start=${start}`),
    );
  }
  const current = board?.days.find(
    (d) => d.person === Number(person) && d.day === day,
  );
  const serviceName = (id: number) =>
    board?.services.find((s) => s.id === id)?.name ?? `Servicio ${id}`;
  return (
    <main>
      <Link href="/personal">Volver a mi trabajo</Link>
      <h1>Capacidad y ausencias</h1>
      <p>
        Planificación diaria de esta institución. Requiere propuesta y revisión
        de otra persona con mandato institucional. No registra motivos médicos
        ni modifica tareas.
      </p>
      {!institutions.length && (
        <p>No tiene instituciones disponibles para gestionar capacidad.</p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void run(load);
        }}
      >
        <fieldset disabled={busy}>
          <label>
            Institución de la capacidad
            <select
              required
              value={institution}
              onChange={(e) => {
                setInstitution(e.target.value);
                setBoard(undefined);
                setPerson("");
                setAllocation({});
                setAttempt(undefined);
              }}
            >
              <option value="">Seleccione…</option>
              {institutions.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Inicio de semana a consultar
            <input
              type="date"
              min="2026-10-01"
              required
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
                setBoard(undefined);
              }}
            />
          </label>
          <button disabled={!institution}>Consultar capacidad</button>
        </fieldset>
      </form>
      <p role="status">{notice}</p>
      {institution&&<PlanningControl key={institution} institution={institution}/>}
      {board && (
        <>
          <h2>Capacidad registrada</h2>
          <p>
            Desde {board.start} hasta antes de {board.end_exclusive}. Una
            persona sin registro no tiene capacidad definida; no se interpreta
            como cero disponible.
          </p>
          {!board.days.length ? (
            <p>No hay días de capacidad registrados en esta semana.</p>
          ) : (
            <ul>
              {board.days.map((d) => (
                <li key={d.id}>
                  {d.name} · {d.day}:{" "}
                  {d.confirmed
                    ? `${d.available_minutes} minutos disponibles; ${d.unallocated_minutes} sin distribuir`
                    : "Sin capacidad aprobada"}
                  {d.needs_review && (
                    <strong>
                      {" "}
                      · Revisar nombramientos; las asignaciones históricas no se
                      liberan automáticamente.
                    </strong>
                  )}
                  <ul>
                    {d.allocations.map((a) => (
                      <li key={a.service_id}>
                        {serviceName(a.service_id)}: {a.minutes} minutos
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void run(async () => {
                const data = {
                  person: Number(person),
                  day,
                  version: current?.etag ?? 0,
                  minutes: Number(minutes),
                  unavailable_minutes: Number(absence),
                  allocations: Object.entries(allocation)
                    .filter(([, value]) => Number(value) > 0)
                    .map(([id, value]) => ({
                      service: Number(id),
                      minutes: Number(value),
                    })),
                  rationale,
                };
                const body = JSON.stringify({ institution, ...data });
                const key =
                  attempt?.body === body ? attempt.key : crypto.randomUUID();
                setAttempt({ body, key });
                await api(`capacity/institutions/${institution}/`, "POST", {
                  ...data,
                  client_key: key,
                });
                await load();
                setAttempt(undefined);
                setNotice(
                  "Propuesta registrada; aún no modifica la capacidad aprobada.",
                );
              });
            }}
          >
            <fieldset disabled={busy}>
              <h2>Proponer capacidad o ausencia</h2>
              <label>
                Persona a planificar
                <select
                  required
                  value={person}
                  onChange={(e) => {
                    setPerson(e.target.value);
                    setAllocation({});
                  }}
                >
                  <option value="">Seleccione…</option>
                  {board.people.map((p) => (
                    <option key={p.user_id} value={p.user_id}>
                      {p.user__username}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Día de capacidad
                <input
                  type="date"
                  required
                  min={board.start}
                  max={new Date(
                    new Date(board.end_exclusive + "T12:00:00Z").getTime() -
                      86400000,
                  )
                    .toISOString()
                    .slice(0, 10)}
                  value={day}
                  onChange={(e) => setDay(e.target.value)}
                />
              </label>
              {current && (
                <p>
                  Versión actual {current.etag}: {current.minutes} minutos base;{" "}
                  {current.unavailable_minutes} no disponibles. La propuesta
                  sustituye la distribución completa de ese día.
                </p>
              )}
              <label>
                Minutos de capacidad base
                <input
                  type="number"
                  min="0"
                  max="1440"
                  required
                  value={minutes}
                  onChange={(e) => setMinutes(e.target.value)}
                />
              </label>
              <label>
                Minutos no disponibles por ausencia
                <input
                  type="number"
                  min="0"
                  max="1440"
                  required
                  value={absence}
                  onChange={(e) => setAbsence(e.target.value)}
                />
              </label>
              <h3>Distribución completa propuesta entre servicios</h3>
              <p>
                Dejar vacío equivale a no asignar minutos a ese servicio. No se
                copiarán asignaciones anteriores automáticamente.
              </p>
              {board.services.map((s) => (
                <label key={s.id}>
                  Minutos para {s.name}
                  <input
                    type="number"
                    min="0"
                    max="1440"
                    value={allocation[s.id] ?? ""}
                    onChange={(e) =>
                      setAllocation({ ...allocation, [s.id]: e.target.value })
                    }
                  />
                </label>
              ))}
              <label>
                Fundamento de planificación (sin motivos médicos)
                <textarea
                  required
                  maxLength={3000}
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                />
              </label>
              <button>Registrar propuesta de capacidad</button>
            </fieldset>
          </form>
          <h2>Propuestas e historial</h2>
          {board.changes.map((c) => {
            const d = board.days.find((x) => x.id === c.capacity_id);
            return (
              <article key={c.id} aria-label={`Propuesta de capacidad ${c.id}`}>
                <h3>
                  {d?.name} · {d?.day} · {states[c.state]}
                </h3>
                <p>
                  Antes:{" "}
                  {c.previous.confirmed
                    ? `${c.previous.minutes} minutos base, ${c.previous.unavailable_minutes} no disponibles`
                    : "Sin capacidad aprobada"}
                  .
                </p>
                <ul>
                  {c.previous.allocations.map((a) => (
                    <li key={a.service_id}>
                      Antes · {serviceName(a.service_id)}: {a.minutes} minutos
                    </li>
                  ))}
                </ul>
                <p>
                  Propuesta: {c.proposal.minutes} minutos base,{" "}
                  {c.proposal.unavailable_minutes} no disponibles.
                </p>
                <ul>
                  {c.proposal.allocations.map((a) => (
                    <li key={a.service}>
                      Propuesto · {serviceName(a.service)}: {a.minutes} minutos
                    </li>
                  ))}
                </ul>
                <pre>{c.rationale}</pre>
                {c.review_reason && <pre>{c.review_reason}</pre>}
                {c.state === "pending" && c.requested_by !== board.user_id && (
                  <>
                    <label>
                      Fundamento de revisión de propuesta {c.id}
                      <textarea
                        maxLength={3000}
                        value={reasons[c.id] ?? ""}
                        onChange={(e) =>
                          setReasons({ ...reasons, [c.id]: e.target.value })
                        }
                      />
                    </label>
                    {[true, false].map((approve) => (
                      <button
                        key={String(approve)}
                        disabled={busy || !reasons[c.id]?.trim()}
                        onClick={() =>
                          run(async () => {
                            await api(
                              `capacity/changes/${c.id}/review/`,
                              "POST",
                              { approve, rationale: reasons[c.id] },
                            );
                            await load();
                            setNotice("Revisión registrada.");
                          })
                        }
                      >
                        {approve ? "Aprobar capacidad" : "Rechazar propuesta"}
                      </button>
                    ))}
                  </>
                )}
              </article>
            );
          })}
          <p>
            Las 354 horas del plan son una referencia institucional provisional;
            no se multiplican por servicio ni se aprueban mediante este registro
            diario.
          </p>
        </>
      )}
    </main>
  );
}
