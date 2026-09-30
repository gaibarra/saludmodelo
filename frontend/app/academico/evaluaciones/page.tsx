"use client";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, listApi, setCsrf } from "../../../lib/api";
import {
  Assessment,
  Cycle,
  Evaluation,
  Level,
  Placement,
  Report,
  Rubric,
  states,
  errorText,
} from "./types";
import "../academic.css";
type Options = {
  services: {
    id: number;
    institution: number;
    school: number | null;
    name: string;
    site_name: string;
  }[];
};
type Evidence = {
  id: number;
  placement: number;
  etag: number;
  title: string;
  performed_on: string;
  minutes: number;
};
function RubricForm({
  cycle,
  services,
  editing,
  onSaved,
}: {
  cycle: Cycle;
  services: Options["services"];
  editing: Rubric | null;
  onSaved: () => Promise<void>;
}) {
  const [levels, setLevels] = useState<Level[]>(
    editing?.levels ||
      [1, 2, 3, 4].map((i) => ({ label: `Nivel ${i}`, description: "" })),
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api("academic/rubrics/", "POST", {
        cycle: cycle.id,
        service: editing?.service || Number(f.get("service")),
        program: editing?.program ?? String(f.get("program") || ""),
        code: editing?.code || f.get("code"),
        version: editing?.version || 0,
        title: f.get("title"),
        criterion: f.get("criterion"),
        levels,
        required_level: Number(f.get("required_level")),
        required: f.get("required") === "on",
        rationale: f.get("rationale"),
      });
      await onSaved();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="panel" onSubmit={save}>
      <h3>
        {editing
          ? `Nueva versión de ${editing.code}`
          : "Definir competencia y rúbrica"}
      </h3>
      <p>
        Describe qué observará el supervisor y los niveles de desempeño. La
        versión guardada se aplicará a las nuevas evaluaciones.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="academic-two">
        <label>
          Servicio de la competencia
          <select
            aria-label="Servicio de la competencia"
            name="service"
            required
            defaultValue={editing?.service || ""}
            disabled={!!editing}
          >
            <option value="" disabled>
              Seleccionar servicio
            </option>
            {services
              .filter(
                (s) =>
                  s.institution === cycle.institution &&
                  s.school === cycle.school,
              )
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.site_name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Programa al que aplica (opcional)
          <input
            name="program"
            maxLength={160}
            defaultValue={editing?.program}
            disabled={!!editing}
          />
        </label>
      </div>
      <small>
        Deja el programa vacío para aplicarlo a todos los alumnos del servicio.
        Si lo indicas, utiliza el nombre registrado en sus cuentas académicas.
      </small>
      <div className="academic-two">
        <label>
          Código de competencia
          <input
            name="code"
            required
            maxLength={60}
            defaultValue={editing?.code}
            disabled={!!editing}
          />
        </label>
        <label>
          Nombre de competencia
          <input
            name="title"
            required
            maxLength={200}
            defaultValue={editing?.title}
          />
        </label>
      </div>
      <label>
        Criterio observable
        <textarea
          name="criterion"
          required
          maxLength={3000}
          defaultValue={editing?.criterion}
        />
      </label>
      <h4>Niveles de desempeño, de menor a mayor</h4>
      {levels.map((level, index) => (
        <fieldset className="academic-rubric-level" key={index}>
          <legend>Nivel {index + 1}</legend>
          <label>
            Nombre del nivel {index + 1}
            <input
              value={level.label}
              maxLength={80}
              required
              onChange={(e) =>
                setLevels((old) =>
                  old.map((l, i) =>
                    i === index ? { ...l, label: e.target.value } : l,
                  ),
                )
              }
            />
          </label>
          <label>
            Descripción del nivel {index + 1}
            <input
              value={level.description}
              maxLength={1000}
              required
              onChange={(e) =>
                setLevels((old) =>
                  old.map((l, i) =>
                    i === index ? { ...l, description: e.target.value } : l,
                  ),
                )
              }
            />
          </label>
        </fieldset>
      ))}
      <button
        type="button"
        disabled={levels.length >= 6}
        onClick={() =>
          setLevels([
            ...levels,
            { label: `Nivel ${levels.length + 1}`, description: "" },
          ])
        }
      >
        Añadir nivel
      </button>
      <button
        type="button"
        disabled={levels.length <= 2}
        onClick={() => setLevels(levels.slice(0, -1))}
      >
        Quitar último nivel
      </button>
      <label>
        Nivel mínimo requerido
        <select
          aria-label="Nivel mínimo requerido"
          name="required_level"
          required
          defaultValue={editing?.required_level || 1}
        >
          {levels.map((l, i) => (
            <option key={i} value={i + 1}>
              {i + 1} · {l.label}
            </option>
          ))}
        </select>
      </label>
      <label className="checkrow">
        <input
          type="checkbox"
          name="required"
          defaultChecked={editing?.required ?? true}
        />
        Competencia obligatoria para esta rotación
      </label>
      <label>
        Motivo y referencia institucional
        <textarea name="rationale" required minLength={5} maxLength={2000} />
      </label>
      {editing && (
        <p>
          La versión anterior se conserva. Las valoraciones previas quedarán
          señaladas para una nueva revisión.
        </p>
      )}
      <button disabled={busy}>Guardar rúbrica</button>
    </form>
  );
}
function EvaluationCard({
  item,
  placement,
  canEvaluate,
  evidence,
  onSaved,
}: {
  item: Assessment;
  placement: number;
  canEvaluate: boolean;
  evidence: Evidence[];
  onSaved: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const r = item.rubric;
  const current = item.evaluation;
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api(`academic/placements/${placement}/evaluations/`, "POST", {
        rubric: r.id,
        version: current?.version || 0,
        score: Number(f.get("score")),
        rationale: f.get("rationale"),
        evidence: f.getAll("evidence").map((id) => ({
          practice: Number(id),
          version: evidence.find((p) => p.id === Number(id))!.etag,
        })),
      });
      await onSaved();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="panel">
      <div className="academic-card-heading">
        <div>
          <span className="academic-state">{states[item.state]}</span>
          <h3>
            {r.code} · {r.title}
          </h3>
        </div>
        <span>Rúbrica v{r.version}</span>
      </div>
      <p>{r.criterion}</p>
      <p>
        {r.required ? "Obligatoria" : "Opcional"} · Nivel requerido:{" "}
        {r.required_level} · {r.levels[r.required_level - 1].label}
      </p>
      <ol>
        {r.levels.map((l, i) => (
          <li key={i}>
            <strong>{l.label}:</strong> {l.description}
          </li>
        ))}
      </ol>
      {current && (
        <div className="help">
          <p>
            <strong>Última valoración:</strong> {current.score} ·{" "}
            {current.rubric_snapshot.levels[current.score - 1]?.label} ·{" "}
            {current.evaluator}
          </p>
          <p>{current.rationale}</p>
          <p>
            Evidencias:{" "}
            {current.evidence
              .map((e) => `práctica ${e.practice}, versión ${e.version}`)
              .join("; ")}
            .
          </p>
        </div>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {canEvaluate && (
        <details>
          <summary>
            {current ? "Registrar nueva valoración" : "Evaluar competencia"}
          </summary>
          <form onSubmit={submit}>
            <label>
              Nivel observado
              <select
                aria-label="Nivel observado"
                name="score"
                required
                defaultValue=""
              >
                <option value="" disabled>
                  Elegir nivel según la rúbrica
                </option>
                {r.levels.map((l, i) => (
                  <option key={i} value={i + 1}>
                    {i + 1} · {l.label}
                  </option>
                ))}
              </select>
            </label>
            <fieldset>
              <legend>Prácticas validadas que sustentan la evaluación</legend>
              {evidence.length === 0 ? (
                <p>Aún no hay prácticas validadas de esta rotación.</p>
              ) : (
                evidence.map((p) => (
                  <label key={p.id} className="checkrow">
                    <input
                      type="checkbox"
                      name="evidence"
                      value={p.id}
                      defaultChecked={current?.evidence.some(
                        (e) => e.practice === p.id && e.version === p.etag,
                      )}
                    />
                    {p.performed_on} · #{p.id} · {p.title} · {p.minutes} min
                  </label>
                ))
              )}
            </fieldset>
            <label>
              Justificación de la evaluación
              <textarea
                name="rationale"
                required
                minLength={5}
                maxLength={4000}
              />
            </label>
            <button disabled={busy || evidence.length === 0}>
              Guardar evaluación
            </button>
          </form>
        </details>
      )}
    </article>
  );
}
export default function EvaluationsPage() {
  const [cycles, setCycles] = useState<Cycle[]>([]);
  const [placements, setPlacements] = useState<Placement[]>([]);
  const [options, setOptions] = useState<Options>({ services: [] });
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [cycleId, setCycleId] = useState("");
  const [placementId, setPlacementId] = useState("");
  const [tab, setTab] = useState("evaluations");
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [canEvaluate, setCanEvaluate] = useState(false);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [history, setHistory] = useState<Evaluation[] | null>(null);
  const [editing, setEditing] = useState<Rubric | null>(null);
  const [rubricForm, setRubricForm] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  const reportKey = useRef<string | null>(null);
  const cycle = cycles.find((c) => c.id === Number(cycleId));
  const placement = placements.find((p) => p.id === Number(placementId));
  const metadata = useCallback(async () => {
    const [c, p, o, r] = await Promise.all([
      listApi<Cycle>("academic/cycles/"),
      listApi<Placement>("academic/placements/"),
      api<Options>("academic/options/"),
      listApi<Rubric>("academic/rubrics/"),
    ]);
    setCycles(c);
    setPlacements(p);
    setOptions(o);
    setRubrics(r);
    setCycleId((old) => old || String(c[0]?.id || ""));
  }, []);
  useEffect(() => {
    api<{ authenticated: boolean; csrf: string }>("session/")
      .then(async (s) => {
        setCsrf(s.csrf);
        if (!s.authenticated)
          throw new Error(
            "Ingresa con tu cuenta y completa la verificación de acceso.",
          );
        await metadata();
        setReady(true);
      })
      .catch((e) => setError(errorText(e)));
  }, [metadata]);
  const load = useCallback(async () => {
    const run = ++generation.current;
    setHistory(null);
    setAssessments([]);
    setCanEvaluate(false);
    setEvidence([]);
    if (!cycleId) {
      setReports([]);
      return;
    }
    const reportRows = await listApi<Report>(
      `academic/cycles/${cycleId}/reports/`,
    );
    if (run !== generation.current) return;
    setReports(reportRows);
    if (placement) {
      const [a, p] = await Promise.all([
        api<{ results: Assessment[]; can_evaluate: boolean }>(
          `academic/placements/${placement.id}/evaluations/`,
        ),
        listApi<Evidence>(
          `academic/practices/?cycle=${cycleId}&student=${placement.student}&service=${placement.service}&status=validated`,
        ),
      ]);
      if (run !== generation.current) return;
      setAssessments(a.results);
      setCanEvaluate(a.can_evaluate);
      setEvidence(p.filter((p) => p.placement === placement.id));
    }
  }, [cycleId, placement]);
  useEffect(() => {
    if (ready) load().catch((e) => setError(errorText(e)));
  }, [load, ready]);
  async function saved() {
    await metadata();
    await load();
    setMessage("Registro guardado. Las versiones anteriores se conservan.");
  }
  async function generate() {
    setBusy(true);
    setError("");
    try {
      reportKey.current ??= crypto.randomUUID();
      const r = await api<Report>(
        `academic/cycles/${cycleId}/reports/`,
        "POST",
        { client_key: reportKey.current },
      );
      reportKey.current = null;
      await load();
      setMessage(
        `Informe ${r.sequence} generado. Ábrelo para revisar el consolidado y los informes individuales antes del cierre.`,
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <header>
        <div>
          <span>ESCUELA DE SALUD · EVALUACIÓN ACADÉMICA</span>
          <h1>Competencias e informes de cierre</h1>
        </div>
        <Link href="/academico" style={{ color: "white" }}>
          Volver a prácticas
        </Link>
      </header>
      <main className="academic-main">
        <p className="academic-intro">
          Evalúa el desempeño con evidencia y conserva los resultados de cada
          alumno al finalizar el ciclo.
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
        {!ready ? (
          <p>
            Comprobando acceso… <Link href="/personal">Ir al acceso</Link>
          </p>
        ) : (
          <>
            <label>
              Ciclo académico
              <select
                aria-label="Ciclo académico"
                value={cycleId}
                onChange={(e) => {
                  setCycleId(e.target.value);
                  setPlacementId("");
                  setEditing(null);
                  setRubricForm(false);
                  reportKey.current = null;
                  setMessage("");
                }}
              >
                <option value="">Seleccionar ciclo</option>
                {cycles.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.school ? c.school_name + " · " : ""}
                    {c.name}
                    {c.closed_at ? " · cerrado" : ""}
                  </option>
                ))}
              </select>
            </label>
            {cycle && (
              <>
                <p>
                  Periodo: {cycle.starts} a {cycle.ends}.{" "}
                  {cycle.closed_at
                    ? "Ciclo cerrado; sus registros están protegidos."
                    : "Ciclo abierto."}
                </p>
                <nav
                  className="panel academic-nav"
                  aria-label="Evaluación y cierre"
                >
                  <button
                    aria-pressed={tab === "evaluations"}
                    onClick={() => setTab("evaluations")}
                  >
                    Evaluaciones por alumno
                  </button>
                  <button
                    aria-pressed={tab === "reports"}
                    onClick={() => setTab("reports")}
                  >
                    Informes de cierre
                  </button>
                  {cycle.can_manage && (
                    <button
                      aria-pressed={tab === "rubrics"}
                      onClick={() => setTab("rubrics")}
                    >
                      Rúbricas y competencias
                    </button>
                  )}
                </nav>
                {tab === "rubrics" && cycle.can_manage ? (
                  <>
                    <h2>Competencias de los servicios</h2>
                    {!cycle.closed_at && (
                      <button
                        onClick={() => {
                          setEditing(null);
                          setRubricForm(true);
                        }}
                      >
                        Añadir competencia
                      </button>
                    )}
                    {rubricForm && !cycle.closed_at && (
                      <RubricForm
                        key={editing?.id || `new-${cycle.id}`}
                        cycle={cycle}
                        services={options.services}
                        editing={editing}
                        onSaved={async () => {
                          setRubricForm(false);
                          await saved();
                        }}
                      />
                    )}
                    {rubrics
                      .filter((r) => r.cycle === cycle.id)
                      .map((r) => (
                        <article className="panel" key={r.id}>
                          <h3>
                            {r.code} · {r.title}
                          </h3>
                          <p>
                            {r.service_name} ·{" "}
                            {r.program || "Todos los programas"} · versión{" "}
                            {r.version}
                          </p>
                          <p>{r.criterion}</p>
                          <ol>
                            {r.levels.map((l, i) => (
                              <li key={i}>
                                {i + 1}. {l.label}: {l.description}
                              </li>
                            ))}
                          </ol>
                          <p>
                            Nivel requerido: {r.required_level} ·{" "}
                            {r.required ? "Obligatoria" : "Opcional"}
                          </p>
                          {!cycle.closed_at && (
                            <button
                              onClick={() => {
                                setEditing(r);
                                setRubricForm(true);
                                window.scrollTo({ top: 0, behavior: "smooth" });
                              }}
                            >
                              Crear nueva versión de {r.code}
                            </button>
                          )}
                        </article>
                      ))}
                  </>
                ) : tab === "reports" ? (
                  <section>
                    <h2>Informes de cierre del ciclo</h2>
                    <p>
                      Cada versión conserva las prácticas, evaluaciones y
                      pendientes registrados al generarla. Dirección puede abrir
                      el consolidado o seleccionar un alumno para su informe
                      individual.
                    </p>
                    {cycle.can_manage && !cycle.closed_at && (
                      <button disabled={busy} onClick={generate}>
                        Generar versión del informe
                      </button>
                    )}
                    {reports.length === 0 && (
                      <p>Aún no hay informes disponibles para tu cuenta.</p>
                    )}
                    {reports.map((r) => (
                      <article className="panel" key={r.id}>
                        <h3>
                          Informe {r.sequence} ·{" "}
                          {r.kind === "individual"
                            ? "Individual"
                            : "Consolidado"}
                        </h3>
                        <p>
                          {new Date(r.created_at).toLocaleString("es-MX")} ·{" "}
                          {r.created_by}
                        </p>
                        <p>
                          {r.closed_at
                            ? r.current_closure
                              ? "Cierre vigente"
                              : "Cierre histórico"
                            : r.stale
                              ? "Borrador desactualizado; genera una nueva versión"
                              : "Borrador para revisión"}{" "}
                          · {r.issues_count} pendientes documentados
                        </p>
                        <Link
                          className="button"
                          href={`/academico/informes/${r.id}`}
                        >
                          Abrir informe {r.sequence}
                        </Link>
                      </article>
                    ))}
                  </section>
                ) : (
                  <section>
                    <h2>Evaluación por alumno y servicio</h2>
                    <label>
                      Rotación a evaluar
                      <select
                        aria-label="Rotación a evaluar"
                        value={placementId}
                        onChange={(e) => setPlacementId(e.target.value)}
                      >
                        <option value="">Seleccionar alumno y servicio</option>
                        {placements
                          .filter((p) => p.cycle === cycle.id)
                          .map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.enrollment} · {p.student_name} ·{" "}
                              {p.service_name}
                              {p.revoked_at ? " · revocada" : ""}
                            </option>
                          ))}
                      </select>
                    </label>
                    {placement && (
                      <>
                        <p>
                          Supervisor: {placement.supervisor_name} · Grupo{" "}
                          {placement.group}
                        </p>
                        {assessments.length === 0 && (
                          <p>
                            No hay competencias configuradas para el servicio y
                            programa de esta rotación.
                          </p>
                        )}
                        {assessments.map((item) => (
                          <EvaluationCard
                            key={`${item.rubric.id}-${item.evaluation?.id || 0}`}
                            item={item}
                            placement={placement.id}
                            canEvaluate={canEvaluate}
                            evidence={evidence}
                            onSaved={saved}
                          />
                        ))}
                        <button
                          disabled={busy}
                          onClick={async () => {
                            if (history) {
                              setHistory(null);
                              return;
                            }
                            setBusy(true);
                            try {
                              setHistory(
                                await listApi<Evaluation>(
                                  `academic/placements/${placement.id}/evaluations/history/`,
                                ),
                              );
                            } catch (e) {
                              setError(errorText(e));
                            } finally {
                              setBusy(false);
                            }
                          }}
                        >
                          {history
                            ? "Ocultar historial de evaluaciones"
                            : "Ver historial de evaluaciones"}
                        </button>
                        {history && (
                          <section className="panel">
                            <h3>Historial conservado</h3>
                            {history.length === 0 ? (
                              <p>Sin evaluaciones todavía.</p>
                            ) : (
                              history.map((e) => (
                                <article
                                  key={e.id}
                                  className="academic-history"
                                >
                                  <h4>
                                    {e.rubric_snapshot.code} · evaluación{" "}
                                    {e.version} · rúbrica{" "}
                                    {e.rubric_snapshot.version}
                                  </h4>
                                  <p>
                                    {e.evaluator} ·{" "}
                                    {new Date(e.created_at).toLocaleString(
                                      "es-MX",
                                    )}
                                  </p>
                                  <p>
                                    Nivel: {e.score} ·{" "}
                                    {
                                      e.rubric_snapshot.levels[e.score - 1]
                                        ?.label
                                    }
                                  </p>
                                  <p>{e.rationale}</p>
                                </article>
                              ))
                            )}
                          </section>
                        )}
                      </>
                    )}
                  </section>
                )}
              </>
            )}
          </>
        )}
      </main>
    </>
  );
}
