"use client";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, listApi, setCsrf } from "../../lib/api";
import "./academic.css";

type Options = {
  schools: {
    id: number;
    institution: number;
    name: string;
    can_manage: boolean;
  }[];
  institutions: { id: number; name: string; can_manage: boolean }[];
  users: { id: number; institution: number; name: string; schools: number[] }[];
  services: {
    id: number;
    institution: number;
    school: number | null;
    name: string;
    site_name: string;
  }[];
  supervisors: {
    id: number;
    service: number;
    name: string;
    starts: string;
    ends: string;
  }[];
};
type Cycle = {
  school: number | null;
  school_name: string;
  id: number;
  institution: number;
  code: string;
  closed_at: string | null;
  name: string;
  starts: string;
  ends: string;
};
type Student = {
  school: number | null;
  id: number;
  institution: number;
  user: number;
  name: string;
  enrollment: string;
  program: string;
};
type Placement = {
  school: number | null;
  id: number;
  student: number;
  student_name: string;
  enrollment: string;
  program: string;
  cycle: number;
  cycle_name: string;
  service: number;
  service_name: string;
  site_name: string;
  supervisor: number;
  supervisor_name: string;
  group: string;
  starts: string;
  ends: string;
  target_minutes: number | null;
  revoked_at: string | null;
  revocation_reason: string;
  can_submit: boolean;
  can_manage: boolean;
};
type Practice = {
  id: number;
  placement: number;
  etag: number;
  status: string;
  title: string;
  performed_on: string;
  minutes: number;
  competency: string;
  evidence_reference: string;
  activity_reference: string;
  student: number;
  student_name: string;
  enrollment: string;
  program: string;
  group: string;
  service: number;
  service_name: string;
  cycle: number;
  supervisor_name: string;
  can_resubmit: boolean;
  can_review: boolean;
  can_void: boolean;
};
type History = {
  id: number;
  version: number;
  action: string;
  actor: string;
  rationale: string;
  snapshot: Record<string, string | number>;
  created_at: string;
};
type Summary = {
  as_of: string;
  states: { status: string; participations: number; minutes: number }[];
};
const labels: Record<string, string> = {
  submitted: "Por revisar",
  returned: "Devuelta",
  validated: "Validada",
  void: "Anulada",
  resubmitted: "Corregida y enviada",
  validate: "Validada",
  return: "Devuelta",
};
const hours = (minutes: number) =>
  `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
const today = () =>
  new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 10);
function humanError(e: unknown) {
  let m = (e as Error).message;
  try {
    const value = JSON.parse(m);
    m =
      typeof value === "string"
        ? value
        : Object.entries(value)
            .map(
              ([k, v]) =>
                `${k === "detail" ? "" : k + ": "}${Array.isArray(v) ? v.join(" ") : v}`,
            )
            .join("\n");
  } catch {}
  return m;
}
function number(f: FormData, key: string) {
  return Number(f.get(key));
}
function PracticeFields({ row }: { row?: Practice }) {
  return (
    <>
      <label>
        Actividad realizada
        <input
          name="title"
          required
          maxLength={200}
          defaultValue={row?.title}
        />
      </label>
      <div className="academic-two">
        <label>
          Fecha de la práctica
          <input
            name="performed_on"
            type="date"
            required
            max={today()}
            defaultValue={row?.performed_on || today()}
          />
        </label>
        <label>
          Duración de tu participación (minutos)
          <input
            name="minutes"
            type="number"
            required
            min={1}
            max={1440}
            defaultValue={row?.minutes}
          />
        </label>
      </div>
      <label>
        Competencia trabajada
        <input
          name="competency"
          required
          maxLength={300}
          defaultValue={row?.competency}
        />
      </label>
      <label>
        Referencia de evidencia
        <input
          name="evidence_reference"
          required
          maxLength={500}
          defaultValue={row?.evidence_reference}
        />
      </label>
      <small>
        Indica el folio de la bitácora o evidencia que revisará el supervisor.
        No escribas nombres de pacientes ni información clínica.
      </small>
      <label>
        Referencia de actividad compartida (opcional)
        <input
          name="activity_reference"
          maxLength={100}
          defaultValue={row?.activity_reference}
        />
      </label>
    </>
  );
}
function practicePayload(f: FormData) {
  return {
    title: f.get("title"),
    performed_on: f.get("performed_on"),
    minutes: number(f, "minutes"),
    competency: f.get("competency"),
    evidence_reference: f.get("evidence_reference"),
    activity_reference: f.get("activity_reference") || "",
  };
}
function PracticeCard({
  row,
  onSaved,
}: {
  row: Practice;
  onSaved: () => Promise<void>;
}) {
  const [history, setHistory] = useState<History[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function act(
    e: FormEvent<HTMLFormElement>,
    kind: "review" | "resubmit",
  ) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const form = e.currentTarget;
    setBusy(true);
    setError("");
    try {
      await api(
        `academic/practices/${row.id}/${kind}/`,
        "POST",
        kind === "review"
          ? {
              version: row.etag,
              action: f.get("action"),
              rationale: f.get("rationale"),
            }
          : {
              ...practicePayload(f),
              version: row.etag,
              rationale: f.get("rationale"),
            },
      );
      setHistory(null);
      form.reset();
      await onSaved();
    } catch (e) {
      setError(humanError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="panel academic-practice">
      <div className="academic-card-heading">
        <div>
          <span className={`academic-state state-${row.status}`}>
            {labels[row.status]}
          </span>
          <h3>{row.title}</h3>
        </div>
        <strong>{hours(row.minutes)}</strong>
      </div>
      <p>
        <strong>{row.student_name}</strong> · {row.enrollment} ·{" "}
        {row.service_name}
      </p>
      <p>
        {row.performed_on} · Grupo {row.group} · Supervisor:{" "}
        {row.supervisor_name}
      </p>
      <dl>
        <dt>Competencia</dt>
        <dd>{row.competency}</dd>
        <dt>Evidencia referenciada</dt>
        <dd>{row.evidence_reference}</dd>
        {row.activity_reference && (
          <>
            <dt>Actividad compartida</dt>
            <dd>{row.activity_reference}</dd>
          </>
        )}
      </dl>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {row.can_resubmit && (
        <details>
          <summary>Corregir y volver a enviar</summary>
          <form onSubmit={(e) => act(e, "resubmit")}>
            <PracticeFields row={row} />
            <label>
              Qué corregiste
              <textarea
                name="rationale"
                required
                minLength={5}
                maxLength={2000}
              />
            </label>
            <button disabled={busy}>Enviar corrección</button>
          </form>
        </details>
      )}
      {(row.can_review || row.can_void) && (
        <details>
          <summary>Revisar práctica</summary>
          <form onSubmit={(e) => act(e, "review")}>
            <label>
              Decisión
              <select aria-label="Decisión" name="action">
                {row.can_review && (
                  <>
                    <option value="validate">Validar participación</option>
                    <option value="return">Devolver para corrección</option>
                  </>
                )}
                {row.can_void && (
                  <option value="void">Anular registro con motivo</option>
                )}
              </select>
            </label>
            <label>
              Observaciones del revisor
              <textarea
                name="rationale"
                required
                minLength={5}
                maxLength={2000}
              />
            </label>
            <button disabled={busy}>Guardar revisión</button>
          </form>
        </details>
      )}
      <button
        className="academic-link"
        type="button"
        disabled={busy}
        onClick={async () => {
          if (history) {
            setHistory(null);
            return;
          }
          setBusy(true);
          try {
            setHistory(
              await listApi<History>(`academic/practices/${row.id}/history/`),
            );
          } catch (e) {
            setError(humanError(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        {history ? "Ocultar historial" : "Ver historial y observaciones"}
      </button>
      {history && (
        <ol className="academic-history">
          {history.map((h) => (
            <li key={h.id}>
              <strong>
                Versión {h.version} · {labels[h.action] || h.action}
              </strong>
              <p>
                {h.actor} · {new Date(h.created_at).toLocaleString("es-MX")}
              </p>
              <p>{h.rationale || "Entrega inicial del alumno."}</p>
              <details>
                <summary>Datos de esta versión</summary>
                <p>
                  {h.snapshot.title} · {h.snapshot.performed_on} ·{" "}
                  {hours(Number(h.snapshot.minutes))}
                </p>
                <p>Competencia: {h.snapshot.competency}</p>
                <p>Evidencia: {h.snapshot.evidence_reference}</p>
              </details>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}
function Configuration({
  options,
  cycles,
  students,
  onSaved,
}: {
  options: Options;
  cycles: Cycle[];
  students: Student[];
  onSaved: () => Promise<void>;
}) {
  const managed = options.institutions.filter(
    (i) =>
      i.can_manage ||
      options.schools.some((s) => s.institution === i.id && s.can_manage),
  );
  const [school, setSchool] = useState(
    String(
      options.schools.find(
        (s) => s.can_manage && s.institution === managed[0]?.id,
      )?.id || "",
    ),
  );
  const [institution, setInstitution] = useState(String(managed[0]?.id || ""));
  const [service, setService] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function save(
    e: FormEvent<HTMLFormElement>,
    kind: "cycles" | "students" | "placements",
  ) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const form = e.currentTarget;
    setBusy(true);
    setError("");
    setMessage("");
    let payload: unknown;
    if (kind === "cycles")
      payload = {
        institution: Number(institution),
        school: school ? Number(school) : null,
        code: f.get("code"),
        name: f.get("name"),
        starts: f.get("starts"),
        ends: f.get("ends"),
      };
    else if (kind === "students")
      payload = {
        institution: Number(institution),
        school: school ? Number(school) : null,
        user: number(f, "user"),
        enrollment: f.get("enrollment"),
        program: f.get("program"),
      };
    else
      payload = {
        student: number(f, "student"),
        cycle: number(f, "cycle"),
        service: Number(service),
        supervisor: number(f, "supervisor"),
        group: f.get("group"),
        starts: f.get("starts"),
        ends: f.get("ends"),
        target_minutes: f.get("target_minutes")
          ? number(f, "target_minutes")
          : null,
      };
    try {
      await api(`academic/${kind}/`, "POST", payload);
      form.reset();
      await onSaved();
      setMessage("Registro académico guardado.");
    } catch (e) {
      setError(humanError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <h2>Organizar el ciclo académico</h2>
      <p>
        Las cuentas del alumno y del supervisor se crean en{" "}
        <Link href="/escuelas">Administración de escuelas</Link>. El supervisor
        necesita un nombramiento vigente como personal clínico o responsable del
        servicio.
      </p>
      <label>
        Institución para configurar
        <select
          aria-label="Institución para configurar"
          value={institution}
          onChange={(e) => {
            setInstitution(e.target.value);
            setSchool(
              String(
                options.schools.find(
                  (s) =>
                    s.institution === Number(e.target.value) && s.can_manage,
                )?.id || "",
              ),
            );
            setService("");
          }}
        >
          {managed.map((i) => (
            <option key={i.id} value={i.id}>
              {i.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Escuela para configurar
        <select
          aria-label="Escuela para configurar"
          value={school}
          onChange={(e) => {
            setSchool(e.target.value);
            setService("");
          }}
        >
          {!options.schools.some(
            (s) => s.institution === Number(institution),
          ) && <option value="">Registros anteriores sin escuela</option>}
          {options.schools
            .filter(
              (s) => s.institution === Number(institution) && s.can_manage,
            )
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
        </select>
      </label>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {message && (
        <p role="status" className="help">
          {message}
        </p>
      )}
      <div className="academic-setup">
        <form className="panel" onSubmit={(e) => save(e, "cycles")}>
          <h3>Nuevo ciclo</h3>
          <label>
            Código del ciclo
            <input name="code" required maxLength={60} />
          </label>
          <label>
            Nombre del ciclo
            <input name="name" required maxLength={160} />
          </label>
          <label>
            Inicio del ciclo
            <input name="starts" type="date" required />
          </label>
          <label>
            Fin del ciclo
            <input name="ends" type="date" required />
          </label>
          <button disabled={busy}>Crear ciclo</button>
        </form>
        <form className="panel" onSubmit={(e) => save(e, "students")}>
          <h3>Registrar alumno</h3>
          <label>
            Cuenta del alumno
            <select
              aria-label="Cuenta del alumno"
              name="user"
              required
              defaultValue=""
            >
              <option value="" disabled>
                Seleccionar cuenta
              </option>
              {options.users
                .filter(
                  (u) =>
                    u.institution === Number(institution) &&
                    (!school || u.schools.includes(Number(school))) &&
                    !students.some((s) => s.user === u.id),
                )
                .map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Matrícula
            <input name="enrollment" required maxLength={60} />
          </label>
          <label>
            Programa académico
            <input name="program" required maxLength={160} />
          </label>
          <button disabled={busy}>Registrar alumno</button>
        </form>
        <form className="panel" onSubmit={(e) => save(e, "placements")}>
          <h3>Asignar rotación y supervisor</h3>
          <label>
            Alumno
            <select aria-label="Alumno" name="student" required defaultValue="">
              <option value="" disabled>
                Seleccionar alumno
              </option>
              {students
                .filter(
                  (s) =>
                    s.institution === Number(institution) &&
                    s.school === (school ? Number(school) : null),
                )
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.enrollment} · {s.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Ciclo de la rotación
            <select
              aria-label="Ciclo de la rotación"
              name="cycle"
              required
              defaultValue=""
            >
              <option value="" disabled>
                Seleccionar ciclo
              </option>
              {cycles
                .filter(
                  (c) =>
                    c.institution === Number(institution) &&
                    c.school === (school ? Number(school) : null),
                )
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.school ? c.school_name + " · " : ""}
                    {c.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Servicio de la rotación
            <select
              aria-label="Servicio de la rotación"
              required
              value={service}
              onChange={(e) => setService(e.target.value)}
            >
              <option value="" disabled>
                Seleccionar servicio
              </option>
              {options.services
                .filter(
                  (s) =>
                    s.institution === Number(institution) &&
                    s.school === (school ? Number(school) : null),
                )
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} · {s.site_name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Supervisor
            <select
              aria-label="Supervisor"
              name="supervisor"
              required
              defaultValue=""
              key={service}
            >
              <option value="" disabled>
                Seleccionar supervisor
              </option>
              {Array.from(
                new Map(
                  options.supervisors
                    .filter((s) => s.service === Number(service))
                    .map((s) => [s.id, s]),
                ).values(),
              ).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Grupo
            <input name="group" required maxLength={80} />
          </label>
          <div className="academic-two">
            <label>
              Inicio de rotación
              <input name="starts" type="date" required />
            </label>
            <label>
              Fin de rotación
              <input name="ends" type="date" required />
            </label>
          </div>
          <label>
            Meta de minutos (opcional)
            <input name="target_minutes" type="number" min={1} max={1000000} />
          </label>
          <small>
            La meta se usa como referencia. Validar una práctica no acredita
            automáticamente el ciclo.
          </small>
          <button disabled={busy}>Asignar rotación</button>
        </form>
      </div>
      <section className="panel">
        <h3>Ciclos registrados</h3>
        {cycles
          .filter(
            (c) =>
              c.institution === Number(institution) &&
              c.school === (school ? Number(school) : null),
          )
          .map((c) => (
            <p key={c.id}>
              {c.code} · {c.school ? c.school_name + " · " : ""}
              {c.name} · {c.starts} a {c.ends}
            </p>
          ))}
        <h3>Alumnos registrados</h3>
        {students
          .filter(
            (s) =>
              s.institution === Number(institution) &&
              s.school === (school ? Number(school) : null),
          )
          .map((s) => (
            <p key={s.id}>
              {s.enrollment} · {s.name} · {s.program}
            </p>
          ))}
      </section>
    </section>
  );
}
export default function AcademicPage() {
  const [options, setOptions] = useState<Options>();
  const [cycles, setCycles] = useState<Cycle[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [placements, setPlacements] = useState<Placement[]>([]);
  const [rows, setRows] = useState<Practice[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [count, setCount] = useState(0);
  const [summary, setSummary] = useState<Summary>();
  const [tab, setTab] = useState("practices");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const generation = useRef(0);
  const pendingSubmission = useRef<{ fingerprint: string; key: string } | null>(
    null,
  );
  const query = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v),
  ).toString();
  const loadRecords = useCallback(async () => {
    const run = ++generation.current;
    const [page, s] = await Promise.all([
      api<{ results: Practice[]; count: number; next: string | null }>(
        `academic/practices/?${query}`,
      ),
      api<Summary>(`academic/summary/?${query}`),
    ]);
    if (run !== generation.current) return;
    setRows(page.results);
    setNext(page.next);
    setCount(page.count);
    setSummary(s);
  }, [query]);
  const loadMeta = useCallback(async () => {
    const [o, c, s, p] = await Promise.all([
      api<Options>("academic/options/"),
      listApi<Cycle>("academic/cycles/"),
      listApi<Student>("academic/students/"),
      listApi<Placement>("academic/placements/"),
    ]);
    setOptions(o);
    setCycles(c);
    setStudents(s);
    setPlacements(p);
  }, []);
  useEffect(() => {
    let active = true;
    api<{ authenticated: boolean; csrf: string }>("session/")
      .then(async (s) => {
        if (!active) return;
        setCsrf(s.csrf);
        setAuthenticated(s.authenticated);
        if (s.authenticated) {
          await loadMeta();
          const school = new URLSearchParams(window.location.search).get(
            "school",
          );
          if (school) setFilters((f) => ({ ...f, school }));
        } else
          setError(
            "Ingresa con tu cuenta y completa la verificación de acceso para continuar.",
          );
      })
      .catch((e) => setError(humanError(e)));
    return () => {
      active = false;
    };
  }, [loadMeta]);
  useEffect(() => {
    if (authenticated) loadRecords().catch((e) => setError(humanError(e)));
  }, [authenticated, loadRecords]);
  async function saved() {
    await Promise.all([loadMeta(), loadRecords()]);
    setMessage("Cambios guardados. El resumen está actualizado.");
  }
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const payload = {
        ...practicePayload(f),
        placement: number(f, "placement"),
      };
      const fingerprint = JSON.stringify(payload);
      if (pendingSubmission.current?.fingerprint !== fingerprint)
        pendingSubmission.current = { fingerprint, key: crypto.randomUUID() };
      await api("academic/practices/", "POST", {
        ...payload,
        client_key: pendingSubmission.current.key,
      });
      pendingSubmission.current = null;
      form.reset();
      await saved();
      setMessage(
        "Práctica enviada al supervisor. Sus horas aún están por revisar.",
      );
    } catch (e) {
      setError(humanError(e));
    } finally {
      setBusy(false);
    }
  }
  const mine = placements.filter((p) => p.can_submit);
  const managed =
    options?.institutions.some((i) => i.can_manage) ||
    options?.schools.some((s) => s.can_manage);
  const visiblePlacements = placements.filter(
    (p) =>
      (!filters.school || p.school === Number(filters.school)) &&
      (!filters.cycle || p.cycle === Number(filters.cycle)) &&
      (!filters.student || p.student === Number(filters.student)) &&
      (!filters.service || p.service === Number(filters.service)) &&
      (!filters.group || p.group === filters.group) &&
      (!filters.program || p.program === filters.program) &&
      (!filters.supervisor || p.supervisor === Number(filters.supervisor)) &&
      (!filters.institution ||
        students.find((s) => s.id === p.student)?.institution ===
          Number(filters.institution)),
  );
  function filter(name: string, value: string) {
    setFilters((old) => ({ ...old, [name]: value }));
    setError("");
  }
  return (
    <>
      <header>
        <div>
          <span>ESCUELA DE SALUD · SEGUIMIENTO ACADÉMICO</span>
          <h1>Prácticas de los alumnos</h1>
        </div>
        <Link href="/personal" style={{ color: "white" }}>
          Volver a mi trabajo
        </Link>
      </header>
      <main className="academic-main">
        <p className="academic-intro">
          Consulta lo que cada alumno realiza durante el ciclo, quién lo
          supervisa y qué participaciones ya fueron validadas.
        </p>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {message && (
          <p role="status" className="help">
            {message}
          </p>
        )}
        {!authenticated ? (
          <Link href="/personal">Ingresar</Link>
        ) : !options ? (
          <p>Cargando información académica…</p>
        ) : (
          <>
            <nav
              className="panel academic-nav"
              aria-label="Secciones académicas"
            >
              <Link className="button" href="/academico/evaluaciones">
                Competencias e informes de cierre
              </Link>
              <button
                aria-pressed={tab === "practices"}
                onClick={() => setTab("practices")}
              >
                Prácticas y avance
              </button>
              <button
                aria-pressed={tab === "placements"}
                onClick={() => setTab("placements")}
              >
                Rotaciones y supervisores
              </button>
              {mine.length > 0 && (
                <button
                  aria-pressed={tab === "capture"}
                  onClick={() => setTab("capture")}
                >
                  Registrar práctica
                </button>
              )}
              {managed && (
                <button
                  aria-pressed={tab === "configuration"}
                  onClick={() => setTab("configuration")}
                >
                  Configurar núcleo académico
                </button>
              )}
            </nav>
            {tab === "configuration" && managed ? (
              <Configuration
                options={options}
                cycles={cycles}
                students={students}
                onSaved={saved}
              />
            ) : tab === "capture" ? (
              <form className="panel academic-capture" onSubmit={submit}>
                <h2>Registrar mi práctica</h2>
                <p>
                  Describe tu participación real. El supervisor revisará la
                  evidencia antes de validar.
                </p>
                <label>
                  Mi rotación
                  <select
                    aria-label="Mi rotación"
                    name="placement"
                    required
                    defaultValue=""
                  >
                    <option value="" disabled>
                      Seleccionar rotación
                    </option>
                    {mine.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.service_name} · {p.cycle_name} · {p.supervisor_name}
                      </option>
                    ))}
                  </select>
                </label>
                <PracticeFields />
                <button disabled={busy}>Enviar al supervisor</button>
              </form>
            ) : (
              <>
                <section
                  className="panel academic-filters"
                  aria-label="Filtros académicos"
                >
                  <label>
                    Escuela
                    <select
                      aria-label="Escuela"
                      value={filters.school || ""}
                      onChange={(e) => filter("school", e.target.value)}
                    >
                      <option value="">Todas las autorizadas</option>
                      {options.schools.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                          {s.can_manage ? "" : " · Consulta"}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Institución
                    <select
                      aria-label="Institución"
                      value={filters.institution || ""}
                      onChange={(e) => filter("institution", e.target.value)}
                    >
                      <option value="">Todas las autorizadas</option>
                      {options.institutions.map((i) => (
                        <option key={i.id} value={i.id}>
                          {i.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Ciclo
                    <select
                      aria-label="Ciclo"
                      value={filters.cycle || ""}
                      onChange={(e) => filter("cycle", e.target.value)}
                    >
                      <option value="">Todos los ciclos</option>
                      {cycles.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.school ? c.school_name + " · " : ""}
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Alumno
                    <select
                      aria-label="Alumno"
                      value={filters.student || ""}
                      onChange={(e) => filter("student", e.target.value)}
                    >
                      <option value="">Todos los alumnos autorizados</option>
                      {students.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.enrollment} · {s.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Servicio
                    <select
                      aria-label="Servicio"
                      value={filters.service || ""}
                      onChange={(e) => filter("service", e.target.value)}
                    >
                      <option value="">Todos los servicios autorizados</option>
                      {Array.from(
                        new Map(placements.map((p) => [p.service, p])).values(),
                      ).map((p) => (
                        <option key={p.service} value={p.service}>
                          {p.service_name} · {p.site_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Supervisor
                    <select
                      aria-label="Supervisor"
                      value={filters.supervisor || ""}
                      onChange={(e) => filter("supervisor", e.target.value)}
                    >
                      <option value="">
                        Todos los supervisores autorizados
                      </option>
                      {Array.from(
                        new Map(
                          placements.map((p) => [p.supervisor, p]),
                        ).values(),
                      ).map((p) => (
                        <option key={p.supervisor} value={p.supervisor}>
                          {p.supervisor_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Programa
                    <select
                      aria-label="Programa"
                      value={filters.program || ""}
                      onChange={(e) => filter("program", e.target.value)}
                    >
                      <option value="">Todos los programas</option>
                      {Array.from(new Set(students.map((s) => s.program))).map(
                        (p) => (
                          <option key={p}>{p}</option>
                        ),
                      )}
                    </select>
                  </label>
                  <label>
                    Grupo
                    <select
                      aria-label="Grupo"
                      value={filters.group || ""}
                      onChange={(e) => filter("group", e.target.value)}
                    >
                      <option value="">Todos los grupos</option>
                      {Array.from(new Set(placements.map((p) => p.group))).map(
                        (g) => (
                          <option key={g}>{g}</option>
                        ),
                      )}
                    </select>
                  </label>
                  <button
                    className="academic-link"
                    onClick={() => setFilters({})}
                  >
                    Limpiar filtros
                  </button>
                </section>
                {tab === "placements" ? (
                  <section>
                    <h2>Rotaciones y supervisores</h2>
                    {visiblePlacements.length === 0 && (
                      <p>No hay rotaciones para esta selección.</p>
                    )}
                    <div className="academic-placements">
                      {visiblePlacements.map((p) => (
                        <article key={p.id} className="panel">
                          <h3>
                            {p.student_name} · {p.enrollment}
                          </h3>
                          <p>
                            {p.program} · Grupo {p.group}
                          </p>
                          <p>
                            <strong>{p.service_name}</strong> · {p.site_name}
                          </p>
                          <p>
                            {p.cycle_name} · {p.starts} a {p.ends}
                          </p>
                          <p>Supervisor: {p.supervisor_name}</p>
                          <p>
                            Meta:{" "}
                            {p.target_minutes
                              ? hours(p.target_minutes)
                              : "Sin meta configurada"}
                          </p>
                          {p.revoked_at ? (
                            <p className="help">
                              Asignación revocada: {p.revocation_reason}
                            </p>
                          ) : (
                            p.can_manage && (
                              <details>
                                <summary>Revocar asignación</summary>
                                <form
                                  onSubmit={async (e) => {
                                    e.preventDefault();
                                    const f = new FormData(e.currentTarget);
                                    setBusy(true);
                                    try {
                                      await api(
                                        `academic/placements/${p.id}/revoke/`,
                                        "POST",
                                        { rationale: f.get("rationale") },
                                      );
                                      await saved();
                                    } catch (e) {
                                      setError(humanError(e));
                                    } finally {
                                      setBusy(false);
                                    }
                                  }}
                                >
                                  <label>
                                    Motivo de revocación
                                    <textarea
                                      name="rationale"
                                      required
                                      minLength={5}
                                      maxLength={2000}
                                    />
                                  </label>
                                  <p>
                                    Se conservarán las prácticas registradas y
                                    se impedirá enviar nuevas en esta rotación.
                                  </p>
                                  <button disabled={busy}>
                                    Revocar rotación
                                  </button>
                                </form>
                              </details>
                            )
                          )}
                        </article>
                      ))}
                    </div>
                  </section>
                ) : (
                  <>
                    <section
                      className="academic-metrics"
                      aria-label="Resumen de participaciones"
                    >
                      {["submitted", "returned", "validated", "void"].map(
                        (status) => {
                          const m = summary?.states.find(
                            (s) => s.status === status,
                          );
                          return (
                            <article className="panel" key={status}>
                              <span>{labels[status]}</span>
                              <strong>{m?.participations || 0}</strong>
                              <span>{hours(m?.minutes || 0)}</span>
                            </article>
                          );
                        },
                      )}
                    </section>
                    <p className="academic-caption">
                      El resumen cuenta participaciones individuales, no
                      pacientes ni actividades únicas. Las horas validadas por
                      el supervisor no acreditan automáticamente el ciclo.{" "}
                      {summary && (
                        <>
                          Actualizado:{" "}
                          {new Date(summary.as_of).toLocaleString("es-MX")}.
                        </>
                      )}
                    </p>
                    <h2>Registro de prácticas</h2>
                    <p>{count} participaciones en esta selección.</p>
                    {rows.length === 0 && (
                      <section className="panel">
                        <h3>Aún no hay prácticas registradas</h3>
                        <p>
                          Primero configura un alumno, un ciclo y una rotación.
                          El alumno podrá enviar su práctica desde su cuenta.
                        </p>
                      </section>
                    )}
                    {rows.map((row) => (
                      <PracticeCard
                        key={`${row.id}-${row.etag}`}
                        row={row}
                        onSaved={saved}
                      />
                    ))}
                    {next && (
                      <button
                        disabled={busy}
                        onClick={async () => {
                          setBusy(true);
                          const run = generation.current;
                          try {
                            const url = new URL(next, window.location.origin);
                            const p = await api<{
                              results: Practice[];
                              next: string | null;
                            }>(
                              url.pathname.replace("/api/v1/", "") + url.search,
                            );
                            if (run === generation.current) {
                              setRows((old) => [...old, ...p.results]);
                              setNext(p.next);
                            }
                          } catch (e) {
                            setError(humanError(e));
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Ver más prácticas
                      </button>
                    )}
                  </>
                )}
              </>
            )}
          </>
        )}
      </main>
    </>
  );
}
