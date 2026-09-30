"use client";
import { FormEvent, useState } from "react";
import { api } from "../lib/api";
type Item = {
  id: string;
  prompt: string;
  origin: string;
  reply: string;
  knowledge: string;
};
type State = {
  exists: boolean;
  etag: number;
  answer_etag: number;
  context_answer_etag?: number;
  help_revision?: number;
  stale?: boolean;
  sources_blocked?: boolean;
  items: Item[];
  next: string[];
  answered?: number;
  declared?: number;
  total?: number;
  current_answer?: string;
  preview?: string;
  can_apply?: boolean;
  guide?: string;
  ai_requests?: number[];
  applied_revision?: number | null;
  history: { version: number; action: string; created_at: string }[];
};
const labels: Record<string, string> = {
  known: "Lo declaro con la información disponible",
  unknown: "No lo sé",
  absent: "No existe actualmente",
  unconfirmed: "Está por confirmar",
  not_applicable: "Considero que no aplica",
};
const actions: Record<string, string> = {
  open: "Inicio",
  reply: "Declaración guardada",
  add_ai: "Aclaraciones IA incorporadas",
  rebase: "Contexto actualizado; requiere reconfirmación",
  apply: "Traslado a borrador",
};
function Reply({
  item,
  disabled,
  onSave,
}: {
  item: Item;
  disabled: boolean;
  onSave: (extra: Record<string, unknown>) => Promise<void>;
}) {
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await onSave({
      item_id: item.id,
      reply: f.get("reply"),
      knowledge: f.get("knowledge"),
    });
  }
  return (
    <form onSubmit={submit} className="panel">
      <h4>{item.prompt}</h4>
      <p>
        {item.origin === "ai"
          ? "Aclaración de una solicitud IA autorizada"
          : "Paso de la ayuda revisada"}
      </p>
      <label>
        Estado de esta información
        <select
          name="knowledge"
          defaultValue={
            item.knowledge === "pending" ? "unconfirmed" : item.knowledge
          }
        >
          {Object.entries(labels).map(([key, text]) => (
            <option key={key} value={key}>
              {text}
            </option>
          ))}
        </select>
      </label>
      <label>
        Su declaración
        <textarea name="reply" maxLength={2000} defaultValue={item.reply} />
      </label>
      <button disabled={disabled}>Guardar apartado</button>
    </form>
  );
}
export default function Interview({
  instance,
  answerVersion,
  currentText,
  dirty,
  onApplied,
}: {
  instance: number;
  answerVersion: number;
  currentText: string;
  dirty: boolean;
  onApplied: () => Promise<void>;
}) {
  const [data, setData] = useState<State>();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState<{ body: string; key: string }>();
  const [job, setJob] = useState("");
  function error(e: unknown) {
    const text = (e as Error).message;
    try {
      const parsed = JSON.parse(text);
      setNotice(parsed.detail || text);
    } catch {
      setNotice(text);
    }
  }
  async function load() {
    setBusy(true);
    try {
      setData(await api<State>(`interviews/${instance}/`));
      setNotice("Avances recuperados del gestor.");
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  async function send(action: string, extra: Record<string, unknown> = {}) {
    const body = JSON.stringify({
      action,
      version: data?.etag ?? 0,
      answer_version: data?.answer_etag ?? answerVersion,
      ...extra,
    });
    const key = attempt?.body === body ? attempt.key : crypto.randomUUID();
    setAttempt({ body, key });
    setBusy(true);
    try {
      const result = await api<State>(`interviews/${instance}/`, "POST", {
        ...JSON.parse(body),
        client_key: key,
      });
      setData((previous) => ({ ...previous, ...result }));
      if (action === "apply" && result.applied_revision) await onApplied();
      setNotice(
        action === "apply"
          ? "Nueva versión guardada como borrador por confirmar."
          : "Apartado y avance guardados. Puede salir y retomar después.",
      );
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  const blocked = busy || !!data?.stale || !!data?.sources_blocked;
  return (
    <section className="help" aria-label="Entrevista guiada">
      <h3>Entrevista guiada</h3>
      <p>
        Guarde hasta dos aclaraciones a la vez. Sus declaraciones permanecen en
        el gestor y no se envían a proveedores IA. Declarar un dato no equivale
        a validarlo institucionalmente.
      </p>
      <button onClick={load} disabled={busy}>
        {data ? "Actualizar entrevista" : "Abrir entrevista"}
      </button>
      <p role="status">{notice}</p>
      {data && !data.exists && (
        <button onClick={() => send("open")} disabled={busy}>
          Iniciar con la ayuda revisada
        </button>
      )}
      {data?.exists && (
        <>
          <p>
            Registrados: {data.answered ?? 0} de {data.total}. Declarados
            conocidos: {data.declared ?? 0}. Los datos por confirmar conservan
            su pendiente.
          </p>
          {data.guide && (
            <details>
              <summary>Guía revisada completa</summary>
              <pre>{data.guide}</pre>
            </details>
          )}
          {(data.stale || data.sources_blocked) && (
            <>
              <p>
                La respuesta, ayuda o autorización de fuentes cambió. Actualice
                el contexto para continuar. Se conservará el historial; los
                textos de pasos coincidentes quedarán para reconfirmar y las
                aclaraciones IA deberán incorporarse nuevamente.
              </p>
              <button disabled={busy} onClick={() => send("rebase")}>
                Actualizar contexto y reconfirmar
              </button>
            </>
          )}
          {!data.sources_blocked &&
            data.items
              .filter((i) => data.next.includes(i.id))
              .map((item) => (
                <Reply
                  key={`${item.id}-${data.help_revision}-${data.context_answer_etag}`}
                  item={item}
                  disabled={blocked}
                  onSave={(extra) => send("reply", extra)}
                />
              ))}
          <details>
            <summary>Declaraciones guardadas y correcciones</summary>
            {data.items
              .filter((i) => i.knowledge !== "pending")
              .map((item) => (
                <Reply
                  key={item.id}
                  item={item}
                  disabled={blocked}
                  onSave={(extra) => send("reply", extra)}
                />
              ))}
          </details>
          {!!data.ai_requests?.length && (
            <>
              <label>
                Solicitud IA con aclaraciones
                <select value={job} onChange={(e) => setJob(e.target.value)}>
                  <option value="">Seleccione…</option>
                  {data.ai_requests.map((id) => (
                    <option key={id} value={id}>
                      Solicitud {id}
                    </option>
                  ))}
                </select>
              </label>
              <button
                disabled={blocked || !job}
                onClick={() => send("add_ai", { request_id: Number(job) })}
              >
                Incorporar aclaraciones autorizadas
              </button>
            </>
          )}
          <details>
            <summary>Comparar antes de guardar en la respuesta</summary>
            <strong>Texto actual del editor</strong>
            <pre>{currentText}</pre>
            <strong>Respuesta guardada en el servidor</strong>
            <pre>{data.current_answer}</pre>
            <strong>Texto de la entrevista</strong>
            <pre>{data.preview || "Sin texto disponible."}</pre>
          </details>
          <p>
            Trasladar reemplaza el texto de la respuesta con una nueva versión
            en borrador por confirmar y conserva las versiones anteriores.
            Complete todos los apartados o indique qué desconoce.
          </p>
          {dirty && (
            <p>
              Hay cambios sin guardar en el editor principal. Guárdelos y
              actualice el contexto antes de trasladar la entrevista.
            </p>
          )}
          <button
            disabled={blocked || !data.can_apply || dirty}
            onClick={() => send("apply")}
          >
            Usar entrevista y guardar borrador
          </button>
          <details>
            <summary>Historial de entrevista</summary>
            {data.history.map((h) => (
              <p key={h.version}>
                Versión {h.version}: {actions[h.action] ?? h.action} ·{" "}
                {new Date(h.created_at).toLocaleString("es-MX")}
              </p>
            ))}
          </details>
        </>
      )}
    </section>
  );
}
