"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, listApi, setCsrf } from "../../lib/api";
type Decision = {
  id: number;
  title: string;
  question: string;
  alternatives: string;
  due: string;
  state: string;
  etag: number;
  resolution: string;
  requested_by: number;
  task_id: number | null;
  task_snapshot: { title?: string; etag?: number };
  task_current: {
    id: number;
    title: string;
    etag: number;
    state: string;
  } | null;
  can_resolve: boolean;
  can_manage: boolean;
  can_withdraw: boolean;
  events?: {
    version: number;
    action: string;
    note: string;
    created_at: string;
    snapshot: { resolution: string; state: string };
  }[];
};
type DecisionNotice = {coverage_ids?:number[];decision_id:number;title:string;due:string;decision_version:number;calendar_version:number;stage:number;working_days_late:number;acknowledged_at:string|null};
type Register = { can_create: boolean; decisions: Decision[]; notices:{calendar_confirmed:boolean;observed_day:string;timezone:string;items:DecisionNotice[]} };
const states: Record<string, string> = {
  pending: "Pendiente",
  resolved: "Resuelta",
  dismissed: "Descartada",
  withdrawn: "Retirada",
};
export default function Decisions() {
  const [services, setServices] = useState<
      { id: number; name: string; site_name: string }[]
    >([]),
    [service, setService] = useState(""),
    [register, setRegister] = useState<Register>(),
    [selected, setSelected] = useState<Decision>(),
    [tasks, setTasks] = useState<{ id: number; title: string }[]>([]);
  const [title, setTitle] = useState(""),
    [question, setQuestion] = useState(""),
    [alternatives, setAlternatives] = useState(""),
    [due, setDue] = useState(""),
    [task, setTask] = useState(""),
    [note, setNote] = useState(""),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState<{ body: string; key: string }>();
  useEffect(() => {
    Promise.all([
      api<{ csrf: string }>("session/"),
      listApi<{ id: number; name: string; site_name: string }>("services/"),
    ])
      .then(([session, rows]) => {
        setCsrf(session.csrf);
        setServices(rows);
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
  async function load(id: string) {
    setRegister(await api<Register>(`decisions/services/${id}/`));
    const board = await api<{ tasks: { id: number; title: string }[] }>(
      `tracking/services/${id}/`,
    );
    setTasks(board.tasks);
  }
  async function mutate(path: string, data: Record<string, unknown>) {
    const body = JSON.stringify({ path, ...data });
    const key = attempt?.body === body ? attempt.key : crypto.randomUUID();
    setAttempt({ body, key });
    const d = await api<Decision>(path, "POST", { ...data, client_key: key });
    await load(service);
    setSelected(d);
    setNote("");
    setAttempt(undefined);
    setNotice("Decisión registrada. No se modificaron tareas ni aprobaciones.");
  }
  return (
    <main>
      <Link href="/personal">Volver a mi trabajo</Link>
      <h1>Decisiones del servicio</h1>
      <p>
        Solicitudes para Dirección. Registrar una resolución conserva su
        fundamento; los cambios de tareas y de línea base mantienen su revisión
        propia.
      </p>
      <label>
        Servicio de las decisiones
        <select
          disabled={busy}
          value={service}
          onChange={(e) => {
            const id = e.target.value;
            setService(id);
            setRegister(undefined);
            setSelected(undefined);
            setTasks([]);
            setTask("");
            setAttempt(undefined);
            if (id) void run(() => load(id));
          }}
        >
          <option value="">Seleccione…</option>
          {services.map((s) => (
            <option value={s.id} key={s.id}>
              {s.name} · {s.site_name}
            </option>
          ))}
        </select>
      </label>
      <p role="status">{notice}</p>
      {register && (
        <>
          <section aria-label="Avisos de decisiones"><h2>Avisos personales de decisiones</h2><p>Se calculan al consultar en el calendario confirmado. Marcar como leído no resuelve ni detiene el seguimiento; cada escalamiento o reapertura puede generar un nuevo aviso.</p><button disabled={busy} onClick={()=>run(()=>load(service))}>Actualizar avisos</button>
          {!register.notices.calendar_confirmed ? <p>Falta confirmar el calendario laboral para calcular avisos.</p> : <><p>Fecha de consulta: {register.notices.observed_day} ({register.notices.timezone}).</p>{!register.notices.items.length && <p>No hay avisos personales activos para este día hábil.</p>}{register.notices.items.map(n=><article key={n.decision_id} aria-label={`Aviso de ${n.title}`}><h3>{n.title}</h3>{!!n.coverage_ids?.length && <p>Aviso por suplencia vigente de la persona solicitante; el acuse es personal.</p>}<p>Plazo: {n.due}. Días hábiles posteriores al plazo: {n.working_days_late}. {n.stage===3?'Escalamiento desde el tercer día hábil.':n.stage===2?'Recordatorio desde el segundo día hábil.':'Aviso inicial de plazo.'}</p>{n.acknowledged_at?<p>Lectura registrada: {new Date(n.acknowledged_at).toLocaleString('es-MX')}.</p>:<button disabled={busy} onClick={()=>run(async()=>{await api(`decisions/${n.decision_id}/acknowledge/`,'POST',{decision_version:n.decision_version,calendar_version:n.calendar_version,stage:n.stage});await load(service);setNotice('Lectura registrada; la decisión conserva su estado.');})}>Marcar aviso {n.decision_id} como leído</button>}<button disabled={busy} onClick={()=>run(async()=>{setSelected(await api<Decision>(`decisions/${n.decision_id}/`));setNote('');})}>Consultar decisión {n.decision_id}</button></article>)}</>}
          </section>
          <h2>Registro</h2>
          {!register.decisions.length ? (
            <p>No hay solicitudes de decisión registradas.</p>
          ) : (
            <ul>
              {register.decisions.map((d) => (
                <li key={d.id}>
                  <button
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        setSelected(await api<Decision>(`decisions/${d.id}/`));
                        setNote("");
                        setAttempt(undefined);
                      })
                    }
                  >
                    {d.title} · {states[d.state]} · plazo {d.due}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {register.can_create && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  await mutate(`decisions/services/${service}/`, {
                    title,
                    question,
                    alternatives,
                    due,
                    task: task ? Number(task) : null,
                  });
                  setTitle("");
                  setQuestion("");
                  setAlternatives("");
                });
              }}
            >
              <fieldset disabled={busy}>
                <h2>Solicitar decisión</h2>
                <label>
                  Título de la decisión
                  <input
                    required
                    maxLength={250}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </label>
                <label>
                  Qué debe decidir Dirección
                  <textarea
                    required
                    maxLength={5000}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                  />
                </label>
                <label>
                  Alternativas y consecuencias conocidas
                  <textarea
                    required
                    maxLength={5000}
                    value={alternatives}
                    onChange={(e) => setAlternatives(e.target.value)}
                  />
                </label>
                <label>
                  Plazo interno esperado
                  <input
                    type="date"
                    required
                    min="2026-10-01"
                    value={due}
                    onChange={(e) => setDue(e.target.value)}
                  />
                </label>
                <label>
                  Tarea relacionada
                  <select
                    value={task}
                    onChange={(e) => setTask(e.target.value)}
                  >
                    <option value="">Sin tarea relacionada</option>
                    {tasks.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.title}
                      </option>
                    ))}
                  </select>
                </label>
                <button disabled={busy}>Registrar solicitud</button>
              </fieldset>
            </form>
          )}
        </>
      )}
      {selected && (
        <section aria-label="Detalle de decisión">
          <h2>{selected.title}</h2>
          <p>
            {states[selected.state]} · versión {selected.etag} · plazo{" "}
            {selected.due}
          </p>
          <h3>Solicitud</h3>
          <pre>{selected.question}</pre>
          <h3>Alternativas</h3>
          <pre>{selected.alternatives}</pre>
          {selected.task_current && (
            <>
              <h3>Tarea relacionada</h3>
              <p>
                Al solicitar: {selected.task_snapshot.title} · versión{" "}
                {selected.task_snapshot.etag}
              </p>
              <p>
                Actual: {selected.task_current.title} · versión{" "}
                {selected.task_current.etag}
              </p>
              {selected.task_snapshot.etag !== selected.task_current.etag && (
                <p>
                  La tarea cambió desde la solicitud. Revise el contexto antes
                  de resolver.
                </p>
              )}
              <Link href="/seguimiento">Consultar seguimiento</Link>
            </>
          )}
          {selected.resolution && (
            <>
              <h3>Resolución registrada</h3>
              <pre>{selected.resolution}</pre>
            </>
          )}
          <button
            disabled={busy}
            onClick={() =>
              run(async () =>
                setSelected(await api<Decision>(`decisions/${selected.id}/`)),
              )
            }
          >
            Actualizar contexto
          </button>
          <label>
            Fundamento de la acción
            <textarea
              maxLength={5000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          {(
            [
              [
                "resolve",
                "Registrar resolución",
                selected.can_resolve && selected.state === "pending",
              ],
              [
                "dismiss",
                "Descartar con fundamento",
                selected.can_resolve && selected.state === "pending",
              ],
              [
                "withdraw",
                "Retirar solicitud",
                selected.can_withdraw && selected.state === "pending",
              ],
              [
                "reopen",
                "Reabrir con fundamento",
                selected.can_manage && selected.state !== "pending",
              ],
            ] as const
          ).map(
            ([action, label, show]) =>
              show && (
                <button
                  key={action}
                  disabled={busy || !note.trim()}
                  onClick={() =>
                    run(() =>
                      mutate(`decisions/${selected.id}/`, {
                        version: selected.etag,
                        action,
                        note,
                        task_version: selected.task_current?.etag ?? null,
                      }),
                    )
                  }
                >
                  {label}
                </button>
              ),
          )}
          <h3>Historial conservado</h3>
          {selected.events?.map((e) => (
            <article key={e.version}>
              <p>
                Versión {e.version} ·{" "}
                {new Date(e.created_at).toLocaleString("es-MX")} ·{" "}
                {states[e.snapshot.state]}
              </p>
              <pre>{e.note}</pre>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
