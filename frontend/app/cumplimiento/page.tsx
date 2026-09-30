"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, listApi, setCsrf } from "../../lib/api";
type Norm = {
  id: number;
  code: string;
  title: string;
  subject: string;
  scope_text: string;
  links: string[];
};
type Options = {
  can_edit: boolean;
  can_check: boolean;
  can_review: boolean;
  norms: Norm[];
  controls: { id: number; text: string }[];
  questions: { id: number; text: string }[];
  owners: { id: number; username: string }[];
};
type Draft = {
  version: number;
  norm: number;
  control: number;
  process_name: string;
  question: number;
  owner: number;
  evidence: string[];
  nature: string;
  numeral: string;
  consulted_version: string;
  official_url: string;
  consulted_on: string | null;
  validity: string;
  applicability: string;
  applicability_reason: string;
  obligation: string;
  link_reason: string;
  next_review: string | null;
};
type Row = {
  id: number;
  etag: number;
  version: number;
  state: string;
  issues: string[];
  revision: Draft & {
    norm_code: string;
    norm_title: string;
    control_text: string;
    question_text: string;
  };
  tests: unknown[];
  reviews: unknown[];
  history?: {
    revision: Row["revision"];
    reviews: {
      decision: string;
      rationale: string;
      reviewer__username: string;
      created_at: string;
    }[];
    tests: {
      result: string;
      procedure: string;
      expected: string;
      observed: string;
      author__username: string;
      created_at: string;
    }[];
  }[];
};
const initial: Draft = {
  version: 0,
  norm: 0,
  control: 0,
  process_name: "",
  question: 0,
  owner: 0,
  evidence: [],
  nature: "legal_obligation",
  numeral: "",
  consulted_version: "",
  official_url: "",
  consulted_on: null,
  validity: "pending",
  applicability: "pending",
  applicability_reason: "",
  obligation: "",
  link_reason: "",
  next_review: null,
};
const states: Record<string, string> = {
  draft: "Borrador",
  returned: "Devuelto",
  needs_review: "Requiere nueva revisión",
  approved: "Revisión aprobada",
  not_applicable_reviewed: "No aplicabilidad revisada",
};
export default function CompliancePage() {
  const [services, setServices] = useState<
      { id: number; name: string; site_name: string }[]
    >([]),
    [service, setService] = useState(0),
    [options, setOptions] = useState<Options>(),
    [rows, setRows] = useState<Row[]>([]),
    [selected, setSelected] = useState<Row>(),
    [draft, setDraft] = useState<Draft>(initial),
    [page, setPage] = useState(1),
    [more, setMore] = useState(false),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const [answers, setAnswers] = useState<
    { questionnaire: number; evidence: { id: string; name: string }[] }[]
  >([]);
  const [procedure, setProcedure] = useState(""),
    [expected, setExpected] = useState(""),
    [observed, setObserved] = useState(""),
    [testResult, setTestResult] = useState("failed"),
    [reason, setReason] = useState("");
  useEffect(() => {
    api<{ authenticated: boolean; csrf: string }>("session/")
      .then(async (s) => {
        setCsrf(s.csrf);
        if (s.authenticated) setServices(await listApi("services/"));
        else setNotice("Inicie sesión desde Mi trabajo.");
      })
      .catch((e) => setNotice(e.message));
  }, []);
  async function load(id = service, p = page) {
    if (!id) return;
    setBusy(true);
    setNotice("");
    try {
      const [o, list, a] = await Promise.all([
        api<Options>(`compliance/services/${id}/options/`),
        api<{ results: Row[]; has_next: boolean }>(
          `compliance/services/${id}/?page=${p}`,
        ),
        listApi<{
          questionnaire: number;
          evidence: { id: string; name: string }[];
        }>(`answers/?service=${id}`),
      ]);
      setOptions(o);
      setRows(list.results);
      setMore(list.has_next);
      setAnswers(a);
      setPage(p);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function field<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft({ ...draft, [key]: value });
  }
  async function open(row: Row) {
    setBusy(true);
    try {
      const detail = await api<Row>(`compliance/records/${row.id}/`);
      setSelected(detail);
      const form = { ...initial };
      for (const key of Object.keys(initial) as (keyof Draft)[])
        Object.assign(form, {
          [key]: key === "version" ? detail.etag : detail.revision[key],
        });
      setDraft(form);
      setReason("");
      setProcedure("");
      setExpected("");
      setObserved("");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function action(path: string, body: unknown) {
    setBusy(true);
    setNotice("");
    try {
      const row = await api<Row>(path, "POST", body);
      await open(row);
      await load();
      setNotice("Registro guardado; consulte el estado y los pendientes.");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const norm = options?.norms.find((n) => n.id === draft.norm);
  return (
    <main>
      <nav>
        <Link href="/personal">Mi trabajo</Link> ·{" "}
        <Link href="/administracion">Administración</Link>
      </nav>
      <h1>Matriz de cumplimiento</h1>
      <p>
        Relaciona fuentes, obligaciones y pruebas. Importar el plan no verifica
        vigencia ni demuestra cumplimiento. Cada aplicabilidad debe justificarse
        para la sede y servicio.
      </p>
      <p role="status">{notice}</p>
      <label>
        Servicio de cumplimiento
        <select
          value={service}
          disabled={busy}
          onChange={(e) => {
            const id = Number(e.target.value);
            setService(id);
            setSelected(undefined);
            setOptions(undefined);
            setRows([]);
            setDraft({ ...initial });
            load(id, 1);
          }}
        >
          <option value={0}>Seleccione…</option>
          {services.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} · {s.site_name}
            </option>
          ))}
        </select>
      </label>
      {options && (
        <>
          <button disabled={busy} onClick={() => load()}>
            Actualizar matriz
          </button>{" "}
          <a href={`/api/v1/compliance/services/${service}/export/`}>
            Exportar matriz JSON
          </a>
          <p>
            La exportación identifica autor, fecha, versión y alcance; queda
            auditada.
          </p>
          {!options.norms.length && (
            <p>
              No hay catálogo normativo autorizado. Importe o concilie las
              tablas del plan y autorice su lote para la institución.
            </p>
          )}
          <table>
            <caption>Registros del servicio</caption>
            <thead>
              <tr>
                <th>Fuente</th>
                <th>Obligación / mejora</th>
                <th>Estado</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.revision.norm_code}</td>
                  <td>{r.revision.obligation}</td>
                  <td>{states[r.state]}</td>
                  <td>
                    <button disabled={busy} onClick={() => open(r)}>
                      Abrir registro {r.id}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && (
            <p>
              Sin registros en esta página. La selección de fuentes no crea
              obligaciones automáticamente.
            </p>
          )}
          <button
            disabled={busy || page === 1}
            onClick={() => load(service, page - 1)}
          >
            Página anterior
          </button>
          <span> Página {page} </span>
          <button
            disabled={busy || !more}
            onClick={() => load(service, page + 1)}
          >
            Página siguiente
          </button>
          {options.can_edit && (
            <button
              disabled={busy}
              onClick={() => {
                setSelected(undefined);
                setDraft({ ...initial });
              }}
            >
              Nuevo registro de cumplimiento
            </button>
          )}
          {selected && (
            <section className="panel">
              <h2>
                Registro {selected.id} · versión {selected.version}
              </h2>
              <p>{states[selected.state]}</p>
              <ul>
                {selected.issues.map((i, n) => (
                  <li key={n}>{i}</li>
                ))}
              </ul>
              <details>
                <summary>Historial, pruebas y decisiones</summary>
                {selected.history?.map((h) => (
                  <article key={h.revision.version}>
                    <h3>
                      Versión {h.revision.version} · {h.revision.norm_code}
                    </h3>
                    <p>
                      {h.revision.norm_title} · Numeral:{" "}
                      {h.revision.numeral || "Por verificar"}
                    </p>
                    <p>
                      {h.revision.nature === "legal_obligation"
                        ? "Obligación propuesta"
                        : "Mejora recomendada"}
                      : {h.revision.obligation}
                    </p>
                    <p>Proceso: {h.revision.process_name}</p>
                    <p>Control: {h.revision.control_text}</p>
                    <p>Pregunta: {h.revision.question_text}</p>
                    <p>Vínculo: {h.revision.link_reason}</p>
                    <p>
                      Aplicabilidad:{" "}
                      {h.revision.applicability === "applies"
                        ? "Aplica"
                        : h.revision.applicability === "not_applies"
                          ? "No aplica"
                          : "Por verificar"}
                      . {h.revision.applicability_reason}
                    </p>
                    <p>
                      Versión consultada:{" "}
                      {h.revision.consulted_version || "Sin confirmar"} ·
                      Consulta: {h.revision.consulted_on || "Sin fecha"} ·
                      Próxima revisión: {h.revision.next_review || "Sin fecha"}
                    </p>
                    {h.revision.official_url && (
                      <p>
                        <a
                          href={h.revision.official_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Fuente consultada por el autor
                        </a>
                      </p>
                    )}
                    <p>
                      {h.revision.evidence.length} documentos vinculados a la
                      respuesta de esta versión.
                    </p>
                    {h.tests.map((t, i) => (
                      <div key={i}>
                        <strong>
                          Prueba{" "}
                          {t.result === "passed"
                            ? "satisfactoria"
                            : "no satisfactoria"}
                        </strong>
                        <p>
                          {t.author__username} ·{" "}
                          {new Date(t.created_at).toLocaleString("es-MX")}
                        </p>
                        <p>Procedimiento: {t.procedure}</p>
                        <p>Esperado: {t.expected}</p>
                        <p>Observado: {t.observed}</p>
                      </div>
                    ))}
                    {h.reviews.map((r, i) => (
                      <p key={i}>
                        {r.decision === "approved"
                          ? "Revisión aprobada"
                          : "Devuelto"}{" "}
                        · {r.reviewer__username} ·{" "}
                        {new Date(r.created_at).toLocaleString("es-MX")}:{" "}
                        {r.rationale}
                      </p>
                    ))}
                  </article>
                ))}
              </details>
            </section>
          )}
          {options.can_edit && (
            <form
              className="panel"
              onSubmit={(e) => {
                e.preventDefault();
                action(
                  selected
                    ? `compliance/records/${selected.id}/`
                    : `compliance/services/${service}/`,
                  draft,
                );
              }}
            >
              <h2>
                {selected ? "Nueva versión del registro" : "Preparar registro"}
              </h2>
              <label>
                Entrada normativa
                <select
                  required
                  aria-label="Entrada normativa"
                  value={draft.norm}
                  onChange={(e) => field("norm", Number(e.target.value))}
                >
                  <option value={0}>Seleccione…</option>
                  {options.norms.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.code} · {n.title}
                    </option>
                  ))}
                </select>
              </label>
              {norm && (
                <details>
                  <summary>Texto literal del catálogo</summary>
                  <p>{norm.subject}</p>
                  <p>{norm.scope_text}</p>
                  {norm.links
                    .filter((u) => u.startsWith("https://"))
                    .map((u, i) => (
                      <p key={i}>
                        <a href={u} target="_blank" rel="noreferrer">
                          Enlace conservado {i + 1}
                        </a>
                      </p>
                    ))}
                  <p>Alcance indicado en el plan; requiere revisión local.</p>
                </details>
              )}
              <label>
                Control del plan
                <select
                  aria-label="Control del plan"
                  value={draft.control}
                  onChange={(e) => field("control", Number(e.target.value))}
                >
                  <option value={0}>Seleccione…</option>
                  {options.controls.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.text}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Proceso del servicio
                <input
                  required
                  maxLength={200}
                  value={draft.process_name}
                  onChange={(e) => field("process_name", e.target.value)}
                />
              </label>
              <label>
                Pregunta vinculada
                <select
                  aria-label="Pregunta vinculada"
                  value={draft.question}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      question: Number(e.target.value),
                      evidence: [],
                    })
                  }
                >
                  <option value={0}>Seleccione…</option>
                  {options.questions.map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.text}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Responsable del registro
                <select
                  aria-label="Responsable del registro"
                  value={draft.owner}
                  onChange={(e) => field("owner", Number(e.target.value))}
                >
                  <option value={0}>Seleccione…</option>
                  {options.owners.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.username}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Naturaleza
                <select
                  aria-label="Naturaleza"
                  value={draft.nature}
                  onChange={(e) => field("nature", e.target.value)}
                >
                  <option value="legal_obligation">
                    Obligación jurídica propuesta
                  </option>
                  <option value="recommended_improvement">
                    Mejora recomendada
                  </option>
                </select>
              </label>
              {(
                [
                  ["numeral", "Numeral exacto"],
                  ["consulted_version", "Versión normativa consultada"],
                  ["official_url", "URL oficial consultada"],
                ] as const
              ).map(([key, label]) => (
                <label key={key}>
                  {label}
                  <input
                    type={key === "official_url" ? "url" : "text"}
                    maxLength={
                      key === "official_url"
                        ? 1000
                        : key === "numeral"
                          ? 160
                          : 200
                    }
                    value={draft[key]}
                    onChange={(e) => field(key, e.target.value)}
                  />
                </label>
              ))}
              <label>
                Fecha de consulta
                <input
                  type="date"
                  value={draft.consulted_on ?? ""}
                  onChange={(e) =>
                    field("consulted_on", e.target.value || null)
                  }
                />
              </label>
              <label>
                Vigencia revisada
                <select
                  aria-label="Vigencia revisada"
                  value={draft.validity}
                  onChange={(e) => field("validity", e.target.value)}
                >
                  <option value="pending">Por verificar</option>
                  <option value="verified">
                    Verificada por el autor, pendiente de revisión independiente
                  </option>
                  <option value="obsolete">
                    Retirada o sustituida según fuente consultada
                  </option>
                </select>
              </label>
              <label>
                Aplicabilidad propuesta
                <select
                  aria-label="Aplicabilidad propuesta"
                  value={draft.applicability}
                  onChange={(e) => field("applicability", e.target.value)}
                >
                  <option value="pending">Por verificar</option>
                  <option value="applies">Aplica</option>
                  <option value="not_applies">No aplica</option>
                </select>
              </label>
              {(
                [
                  [
                    "applicability_reason",
                    "Supuesto y fundamento de aplicabilidad",
                  ],
                  ["obligation", "Obligación o mejora propuesta"],
                  [
                    "link_reason",
                    "Por qué se vincula con esta pregunta y control",
                  ],
                ] as const
              ).map(([key, label]) => (
                <label key={key}>
                  {label}
                  <textarea
                    required
                    maxLength={key === "obligation" ? 10000 : 5000}
                    value={draft[key]}
                    onChange={(e) => field(key, e.target.value)}
                  />
                </label>
              ))}
              <label>
                Próxima revisión
                <input
                  type="date"
                  value={draft.next_review ?? ""}
                  onChange={(e) => field("next_review", e.target.value || null)}
                />
              </label>
              <fieldset>
                <legend>Evidencia de la respuesta vinculada</legend>
                {(
                  answers.find((a) => a.questionnaire === draft.question)
                    ?.evidence ?? []
                ).map((d) => (
                  <label key={d.id}>
                    <input
                      type="checkbox"
                      checked={draft.evidence.includes(d.id)}
                      onChange={(e) =>
                        field(
                          "evidence",
                          e.target.checked
                            ? [...draft.evidence, d.id]
                            : draft.evidence.filter((id) => id !== d.id),
                        )
                      }
                    />
                    {d.name}
                  </label>
                ))}
              </fieldset>
              <p>
                Guardar vincula la versión actual de la respuesta y crea un
                borrador nuevo. Conserva el historial y exige otra revisión.
              </p>
              <button
                disabled={
                  busy ||
                  !draft.norm ||
                  !draft.control ||
                  !draft.question ||
                  !draft.owner
                }
              >
                Guardar registro de cumplimiento
              </button>
            </form>
          )}
          {selected && options.can_check && (
            <form
              className="panel"
              onSubmit={(e) => {
                e.preventDefault();
                action(`compliance/records/${selected.id}/test/`, {
                  version: selected.etag,
                  procedure,
                  expected,
                  observed,
                  result: testResult,
                });
              }}
            >
              <h2>Registrar prueba de esta versión</h2>
              <label>
                Procedimiento ejecutado
                <textarea
                  required
                  maxLength={5000}
                  value={procedure}
                  onChange={(e) => setProcedure(e.target.value)}
                />
              </label>
              <label>
                Resultado esperado
                <textarea
                  required
                  maxLength={5000}
                  value={expected}
                  onChange={(e) => setExpected(e.target.value)}
                />
              </label>
              <label>
                Resultado observado
                <textarea
                  required
                  maxLength={5000}
                  value={observed}
                  onChange={(e) => setObserved(e.target.value)}
                />
              </label>
              <label>
                Resultado de prueba
                <select
                  aria-label="Resultado de prueba"
                  value={testResult}
                  onChange={(e) => setTestResult(e.target.value)}
                >
                  <option value="failed">No satisfactorio</option>
                  <option value="passed">Satisfactorio</option>
                </select>
              </label>
              <button disabled={busy}>Registrar prueba</button>
            </form>
          )}
          {selected && options.can_review && (
            <section className="panel">
              <h2>Revisión independiente</h2>
              <label>
                Fundamento de revisión del registro
                <textarea
                  maxLength={5000}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
              {(["approved", "returned"] as const).map((decision) => (
                <button
                  key={decision}
                  disabled={busy || !reason.trim()}
                  onClick={() =>
                    action(`compliance/records/${selected.id}/review/`, {
                      version: selected.etag,
                      decision,
                      rationale: reason,
                    })
                  }
                >
                  {decision === "approved"
                    ? "Aprobar revisión del registro"
                    : "Devolver registro"}
                </button>
              ))}
              <p>
                La decisión se limita a esta versión y su evidencia. No autoriza
                actos clínicos ni certifica cumplimiento integral.
              </p>
            </section>
          )}
        </>
      )}
    </main>
  );
}
