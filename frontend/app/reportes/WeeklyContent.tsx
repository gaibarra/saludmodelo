import Link from "next/link";
type Metric = {
  numerator: number;
  denominator: number;
  pending: number;
  label: string;
};
export type Report = {
  id: string;
  status: string;
  service: { id: number; name: string };
  generated_at: string;
  period: { start: string; end_exclusive: string; partial: boolean };
  current: {
    accepted_tasks: Metric;
    validated_answers: Metric;
    cancelled_committed: number;
    uncommitted: number;
    overdue_task_ids: number[];
    blocked_task_ids: number[];
    critical_task_ids: number[];
  };
  period_activity: {
    decision_events: {
      id: number;
      decision_id: number;
      action: string;
      created_at: string;
    }[];
    minutes: number;
    events: { id: number; task_id: number; kind: string; created_at: string }[];
    baseline_decisions: {
      id: number;
      task_id: number;
      state: string;
      reviewed_at: string;
    }[];
  };
  current_pending_operational_decisions: {
    id: number;
    title: string;
    due: string;
  }[];
  current_pending_decisions: { id: number; task_id: number }[];
  references: {
    tasks: { id: number; title: string; state: string; committed: boolean }[];
  };
  eligible_recipients: { user_id: number; user__username: string }[];
  limitations: string[];
};
const stateLabels: Record<string, string> = {
  pending: "Pendiente",
  approved: "Aprobado",
  rejected: "Rechazado",
  accepted: "Aceptada",
  cancelled: "Cancelada",
  blocked: "Bloqueada",
  in_progress: "En curso",
  submitted: "En revisión",
  returned: "Devuelta",
};

export default function WeeklyContent({report,service,query="",saved=false}:{report:Report;service:string;query?:string;saved?:boolean}) { return (
        <section aria-label="Borrador semanal">
          <h2>{report.service.name} · Informe del servicio</h2>
          <p>
            Desde {report.period.start} hasta antes de{" "}
            {report.period.end_exclusive}.{" "}
            {report.period.partial
              ? "Período todavía incompleto."
              : "Período concluido."}
          </p>
          <p>
            Estado actual observado:{" "}
            {new Date(report.generated_at).toLocaleString("es-MX")}. No es una
            reconstrucción histórica.
          </p>
          <h3>Situación actual</h3>
          <p>
            Tareas aceptadas: {report.current.accepted_tasks.label}; pendientes:{" "}
            {report.current.accepted_tasks.pending}.
          </p>
          <p>
            Canceladas dentro de línea base:{" "}
            {report.current.cancelled_committed}. Sin compromiso aprobado:{" "}
            {report.current.uncommitted}.
          </p>
          <p>
            Respuestas validadas: {report.current.validated_answers.label};
            pendientes: {report.current.validated_answers.pending}.
          </p>
          <p>
            Tareas comprometidas vencidas:{" "}
            {report.current.overdue_task_ids.length}; bloqueadas:{" "}
            {report.current.blocked_task_ids.length}; críticas:{" "}
            {report.current.critical_task_ids.length}.
          </p>
          <h3>Actividad del período</h3>
          <p>
            Minutos registrados: {report.period_activity.minutes}. Eventos de
            tareas: {report.period_activity.events.length}. Decisiones de línea
            base: {report.period_activity.baseline_decisions.length}.
          </p>
          <ul>
            {report.period_activity.baseline_decisions.map((d) => (
              <li key={d.id}>
                Cambio {d.id}, tarea {d.task_id}:{" "}
                {stateLabels[d.state] ?? d.state} ·{" "}
                {new Date(d.reviewed_at).toLocaleString("es-MX")}
              </li>
            ))}
          </ul>
          <h3>Movimientos de decisiones del servicio</h3>
          {!report.period_activity.decision_events.length ? (
            <p>No hay movimientos registrados en el período.</p>
          ) : (
            <ul>
              {report.period_activity.decision_events.map((e) => (
                <li key={e.id}>
                  Decisión {e.decision_id}:{" "}
                  {(
                    {
                      create: "Solicitud",
                      resolve: "Resolución",
                      dismiss: "Descarte",
                      withdraw: "Retiro",
                      reopen: "Reapertura",
                    } as Record<string, string>
                  )[e.action] ?? e.action}{" "}
                  · {new Date(e.created_at).toLocaleString("es-MX")}
                </li>
              ))}
            </ul>
          )}
          <h3>Decisiones pendientes actuales</h3>
          {!report.current_pending_decisions.length ? (
            <p>No hay cambios de línea base pendientes registrados.</p>
          ) : (
            <ul>
              {report.current_pending_decisions.map((d) => (
                <li key={d.id}>
                  Cambio {d.id}, tarea {d.task_id}
                </li>
              ))}
            </ul>
          )}
          <h3>Solicitudes de decisión pendientes</h3>
          {report.current_pending_operational_decisions.length ? (
            <ul>
              {report.current_pending_operational_decisions.map((d) => (
                <li key={d.id}>
                  {d.title} · plazo {d.due}
                </li>
              ))}
            </ul>
          ) : (
            <p>No hay solicitudes pendientes en el registro del servicio.</p>
          )}
          <Link href="/decisiones">Consultar decisiones e historial</Link>
          <h3>Tareas fuente</h3>
          {!report.references.tasks.length ? (
            <p>No hay tareas registradas para este servicio.</p>
          ) : (
            <ul>
              {report.references.tasks.map((t) => (
                <li key={t.id}>
                  Tarea {t.id}: {t.title} · {stateLabels[t.state] ?? t.state} ·{" "}
                  {t.committed ? "Línea base" : "Propuesta"}
                </li>
              ))}
            </ul>
          )}
          <Link href="/seguimiento">Consultar seguimiento y fuentes</Link>
          <h3>Destinatarios con acceso vigente</h3>
          <p>Elegibilidad observada al generar; no acredita distribución actual.</p>
          {report.eligible_recipients.length ? (
            <ul>
              {report.eligible_recipients.map((u) => (
                <li key={u.user_id}>{u.user__username}</li>
              ))}
            </ul>
          ) : (
            <p>Sin destinatarios vigentes.</p>
          )}
          <h3>Alcance del borrador</h3>
          <ul>
            {report.limitations.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
          {!saved && <><a href={`/api/v1/reports/services/${service}/weekly/export/${query}`}>Generar exportación JSON actualizada</a><p>La exportación vuelve a consultar datos y puede diferir si hubo cambios.</p></>}
        </section>
);}
