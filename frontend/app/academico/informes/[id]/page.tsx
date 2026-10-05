"use client";
import InstitutionalLogo from "../../../../components/InstitutionalLogo";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, setCsrf } from "../../../../lib/api";
import {
  Report,
  Totals,
  hours,
  states,
  errorText,
} from "../../evaluaciones/types";
import "../../academic.css";
function TotalsTable({ totals }: { totals: Totals }) {
  return (
    <table className="academic-report-table">
      <thead>
        <tr>
          <th>Estado</th>
          <th>Participaciones</th>
          <th>Duración</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(totals).map(([status, total]) => (
          <tr key={status}>
            <td>{states[status]}</td>
            <td>{total.participations}</td>
            <td>{hours(total.minutes)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<Report>();
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const reload = useCallback(async () => {
    const s = await api<{ csrf: string }>("session/");
    setCsrf(s.csrf);
    setReport(await api<Report>(`academic/reports/${params.id}/`));
  }, [params.id]);
  useEffect(() => {
    reload().catch((e) => setError(errorText(e)));
  }, [reload]);
  async function close(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!report) return;
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api(`academic/reports/${report.id}/close/`, "POST", {
        rationale: f.get("rationale"),
        accept_pending: f.get("accept_pending") === "on",
      });
      await reload();
      setMessage(
        "Ciclo cerrado. Esta versión se conserva y los registros quedan protegidos.",
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function reopen(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!report) return;
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api(`academic/cycles/${report.cycle}/reopen/`, "POST", {
        report: report.id,
        rationale: f.get("rationale"),
      });
      await reload();
      setMessage(
        "Ciclo reabierto. El cierre anterior se conserva y las correcciones requerirán un nuevo informe.",
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const content = report?.snapshot;
  const chosen = content?.students.find((s) => String(s.id) === selected);
  const students = chosen ? [chosen] : content?.students || [];
  const issues = chosen ? chosen.issues : content?.issues || [];
  return (
    <main className="academic-report">
      <div className="academic-print-controls">
        <Link href="/academico/evaluaciones">← Competencias e informes</Link>
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
      </div>
      {!report || !content ? (
        <p>Cargando informe…</p>
      ) : (
        <>
          <div className="academic-print-controls panel">
            <h2>Consultar y guardar informe</h2>
            {report.kind === "consolidated" && (
              <label>
                Contenido del informe
                <select
                  aria-label="Contenido del informe"
                  value={selected}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  <option value="">Consolidado de todo el ciclo</option>
                  {content.students.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.enrollment} · {s.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <button onClick={() => window.print()}>
              Imprimir o guardar PDF
            </button>
            <p>
              {report.stale
                ? "Este borrador está desactualizado. Genera una nueva versión antes de cerrar."
                : report.current_closure
                  ? "Este es el cierre vigente del ciclo."
                  : report.closed_at
                    ? "Cierre histórico conservado; el ciclo fue reabierto o tiene otro cierre."
                    : "Revisa esta versión antes de cerrar el ciclo."}
            </p>
          </div>
          <article className="academic-report-content">
            <div className="academic-report-heading">
              <div className="institutional-report-brand"><InstitutionalLogo size="report"/><strong>{content.cycle.institution}</strong></div>
              <h1>
                {chosen || report.kind === "individual"
                  ? "Informe individual de prácticas"
                  : "Informe consolidado de prácticas"}
              </h1>
              <h2>
                {report.school_name} · {content.cycle.name} ·{" "}
                {content.cycle.code}
              </h2>
              <p>
                Periodo: {content.cycle.starts} a {content.cycle.ends}
              </p>
              <p>
                Informe {report.sequence} · Corte:{" "}
                {new Date(report.created_at).toLocaleString("es-MX")} ·
                Preparado por {report.created_by}
              </p>
              <p>
                <strong>
                  {report.closed_at
                    ? "CIERRE CONSERVADO"
                    : "BORRADOR DE CIERRE"}
                </strong>
                {report.closed_at && (
                  <>
                    {" "}
                    · {new Date(report.closed_at).toLocaleString(
                      "es-MX",
                    )} · {report.closed_by}
                  </>
                )}
              </p>
              {report.close_reason && (
                <p>Motivo del cierre: {report.close_reason}</p>
              )}
              {report.stale && (
                <p>
                  Borrador desactualizado respecto a los registros actuales.
                </p>
              )}
              {report.closed_at && !report.current_closure && (
                <p>
                  Cierre histórico; no representa un cierre vigente del ciclo.
                </p>
              )}
            </div>
            <p>
              {chosen
                ? "Informe individual extraído de la versión conservada del ciclo."
                : content.coverage}
            </p>
            <p>
              La evaluación utiliza las rúbricas configuradas por Dirección.
              Este informe documenta resultados y pendientes; no acredita
              automáticamente el ciclo.
            </p>
            <h2>Resumen {chosen ? "del alumno" : "del informe"}</h2>
            <TotalsTable totals={chosen ? chosen.totals : content.totals} />
            {!chosen && report.kind === "consolidated" && (
              <>
                <h2>Resumen por servicio</h2>
                <div className="academic-table-scroll">
                  <table className="academic-report-table">
                    <thead>
                      <tr>
                        <th>Servicio / sede</th>
                        <th>Alumnos</th>
                        <th>Participaciones validadas</th>
                        <th>Duración validada</th>
                      </tr>
                    </thead>
                    <tbody>
                      {content.services.map((s) => (
                        <tr key={s.id}>
                          <td>
                            {s.name} · {s.site_name}
                          </td>
                          <td>{s.students}</td>
                          <td>{s.totals.validated.participations}</td>
                          <td>{hours(s.totals.validated.minutes)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            <h2>Pendientes documentados ({issues.length})</h2>
            {issues.length ? (
              <ul>
                {issues.map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            ) : (
              <p>
                Sin pendientes según las reglas y registros incluidos en esta
                versión.
              </p>
            )}
            {students.map((s) => (
              <section key={s.id} className="academic-report-student">
                <h2>
                  {s.enrollment} · {s.name}
                </h2>
                <p>Programa: {s.program}</p>
                <TotalsTable totals={s.totals} />
                {s.placements.map((p) => (
                  <section key={p.id} className="academic-report-placement">
                    <h3>
                      {p.service_name} · {p.site_name}
                    </h3>
                    <p>
                      Rotación {p.id} · Grupo {p.group} · {p.starts} a {p.ends}
                    </p>
                    <p>
                      Supervisor: {p.supervisor}. Meta:{" "}
                      {p.target_minutes
                        ? hours(p.target_minutes)
                        : "sin meta configurada"}
                      .
                    </p>
                    {p.revoked_at && (
                      <p>Asignación revocada: {p.revocation_reason}</p>
                    )}
                    <h4>Competencias</h4>
                    {p.competencies.length === 0 ? (
                      <p>Sin rúbricas configuradas.</p>
                    ) : (
                      p.competencies.map((c) => (
                        <section
                          key={c.rubric.id}
                          className="academic-report-competency"
                        >
                          <h4>
                            {c.rubric.code} · {c.rubric.title} ·{" "}
                            {states[c.state]}
                          </h4>
                          <p>
                            Rúbrica v{c.rubric.version} ·{" "}
                            {c.rubric.required ? "Obligatoria" : "Opcional"} ·
                            Nivel requerido: {c.rubric.required_level}
                          </p>
                          <p>{c.rubric.criterion}</p>
                          <ol>
                            {c.rubric.levels.map((l, i) => (
                              <li key={i}>
                                <strong>
                                  {i + 1}. {l.label}:
                                </strong>{" "}
                                {l.description}
                              </li>
                            ))}
                          </ol>
                          {c.evaluation ? (
                            <>
                              <p>
                                <strong>Valoración:</strong>{" "}
                                {c.evaluation.score} ·{" "}
                                {
                                  c.evaluation.rubric_snapshot.levels[
                                    c.evaluation.score - 1
                                  ]?.label
                                }{" "}
                                · {c.evaluation.evaluator} ·{" "}
                                {new Date(
                                  c.evaluation.created_at,
                                ).toLocaleString("es-MX")}
                              </p>
                              <p>{c.evaluation.rationale}</p>
                              <p>
                                Rúbrica utilizada: versión{" "}
                                {c.evaluation.rubric_snapshot.version}. Nivel
                                requerido:{" "}
                                {c.evaluation.rubric_snapshot.required_level}.
                              </p>
                              {c.evaluation.rubric !== c.rubric.id && (
                                <div>
                                  <p>
                                    {c.evaluation.rubric_snapshot.criterion}
                                  </p>
                                  <ol>
                                    {c.evaluation.rubric_snapshot.levels.map(
                                      (level, index) => (
                                        <li key={index}>
                                          {level.label}: {level.description}
                                        </li>
                                      ),
                                    )}
                                  </ol>
                                </div>
                              )}
                              <p>
                                Evidencias:{" "}
                                {c.evaluation.evidence
                                  .map(
                                    (e) =>
                                      `práctica ${e.practice}, versión ${e.version}`,
                                  )
                                  .join("; ")}
                              </p>
                            </>
                          ) : (
                            <p>Sin evaluación registrada.</p>
                          )}
                          {c.history.length > 1 && (
                            <div>
                              <h4>Valoraciones anteriores conservadas</h4>
                              {c.history.slice(0, -1).map((e) => (
                                <div key={e.id}>
                                  <p>
                                    Evaluación {e.version} · Rúbrica{" "}
                                    {e.rubric_snapshot.version} · {e.evaluator}{" "}
                                    · Nivel {e.score} (
                                    {
                                      e.rubric_snapshot.levels[e.score - 1]
                                        ?.label
                                    }
                                    )
                                  </p>
                                  <p>
                                    {new Date(e.created_at).toLocaleString(
                                      "es-MX",
                                    )}{" "}
                                    · Nivel requerido:{" "}
                                    {e.rubric_snapshot.required_level}
                                  </p>
                                  <p>{e.rationale}</p>
                                  <p>
                                    Criterio utilizado:{" "}
                                    {e.rubric_snapshot.criterion}
                                  </p>
                                  <ol>
                                    {e.rubric_snapshot.levels.map(
                                      (level, index) => (
                                        <li key={index}>
                                          {level.label}: {level.description}
                                        </li>
                                      ),
                                    )}
                                  </ol>
                                  <p>
                                    Evidencias:{" "}
                                    {e.evidence
                                      .map(
                                        (ev) =>
                                          `práctica ${ev.practice}, versión ${ev.version}`,
                                      )
                                      .join("; ")}
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}
                        </section>
                      ))
                    )}
                    <h4>Prácticas registradas ({p.practices.length})</h4>
                    {p.practices.length === 0 ? (
                      <p>No hay prácticas registradas.</p>
                    ) : (
                      p.practices.map((pr) => (
                        <div key={pr.id} className="academic-report-practice">
                          <p>
                            <strong>
                              #{pr.id} · {pr.title}
                            </strong>{" "}
                            · {states[pr.status]} · versión {pr.version}
                          </p>
                          <p>
                            {pr.performed_on} · {hours(pr.minutes)} ·
                            Competencia registrada: {pr.competency}
                          </p>
                          <p>Evidencia referenciada: {pr.evidence_reference}</p>
                          {pr.activity_reference && (
                            <p>Actividad compartida: {pr.activity_reference}</p>
                          )}
                          <details className="academic-report-history" open>
                            <summary>Historial de esta práctica</summary>
                            {pr.history.map((h) => (
                              <div key={h.version}>
                                <p>
                                  Versión {h.version} ·{" "}
                                  {states[h.action] || h.action} · {h.actor} ·{" "}
                                  {new Date(h.created_at).toLocaleString(
                                    "es-MX",
                                  )}
                                </p>
                                <p>{h.rationale || "Entrega inicial."}</p>
                                <p>
                                  {h.snapshot.title} · {h.snapshot.performed_on}{" "}
                                  · {h.snapshot.minutes} min ·{" "}
                                  {h.snapshot.evidence_reference}
                                </p>
                              </div>
                            ))}
                          </details>
                        </div>
                      ))
                    )}
                  </section>
                ))}
              </section>
            ))}
            <footer className="academic-report-footer">
              Versión {report.sequence} · Corte conservado {report.created_at} ·
              Referencia {report.id}
            </footer>
          </article>
          <div className="academic-print-controls">
            {report.can_close && (
              <form className="panel" onSubmit={close}>
                <h2>Cerrar el ciclo con esta versión</h2>
                <p>
                  El cierre incluye a todos los alumnos y servicios del ciclo,
                  aunque estés consultando un informe individual. Se impedirá
                  modificar sus registros hasta una reapertura de Dirección.
                </p>
                {report.issues_count > 0 && (
                  <label className="checkrow">
                    <input type="checkbox" name="accept_pending" required />
                    Reconozco los {report.issues_count} pendientes del
                    consolidado y autorizo el cierre documental con esos
                    pendientes.
                  </label>
                )}
                <label>
                  Motivo del cierre
                  <textarea
                    name="rationale"
                    required
                    minLength={5}
                    maxLength={2000}
                  />
                </label>
                <button disabled={busy}>Confirmar cierre del ciclo</button>
              </form>
            )}
            {report.can_reopen && (
              <details className="panel">
                <summary>Reabrir ciclo para corregir registros</summary>
                <form onSubmit={reopen}>
                  <p>Esta versión del informe permanecerá conservada.</p>
                  <label>
                    Motivo de reapertura
                    <textarea
                      name="rationale"
                      required
                      minLength={5}
                      maxLength={2000}
                    />
                  </label>
                  <button disabled={busy}>Reabrir ciclo</button>
                </form>
              </details>
            )}
          </div>
        </>
      )}
    </main>
  );
}
