"use client";
import { useState } from "react";
import { api, listApi } from "../lib/api";
type Consultation = {
  id: number;
  original: string;
  service_name: string;
  question: string;
  due: string;
  opened_by_name: string;
  assigned_to_name: string;
  state: string;
  etag: number;
  help_version: number | null;
  answer_version: number | null;
  resolution: string;
  messages: { id: number; author: string; body: string; created_at: string }[];
  can_reply: boolean;
  can_resolve: boolean;
};
const states: Record<string, string> = {
  open: "Pendiente de respuesta",
  answered: "Respondida",
  resolved: "Resuelta",
};
export default function Consultations({ instanceId }: { instanceId?: number }) {
  const [items, setItems] = useState<Consultation[]>([]);
  const [people, setPeople] = useState<
    { id: number; name: string; username: string }[]
  >([]);
  const [loaded, setLoaded] = useState(false),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const [question, setQuestion] = useState(""),
    [recipient, setRecipient] = useState(""),
    [due, setDue] = useState("");
  const [attempt, setAttempt] = useState<{ body: string; key: string }>();
  async function refresh() {
    setBusy(true);
    try {
      setItems(
        await listApi<Consultation>(
          "consultations/" + (instanceId ? `?instance=${instanceId}` : ""),
        ),
      );
      if (instanceId)
        setPeople(
          (
            await api<{ people: typeof people }>(
              `consultations/recipients/?instance=${instanceId}`,
            )
          ).people,
        );
      setLoaded(true);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function create() {
    const body = JSON.stringify({
      instance: instanceId,
      assigned_to: Number(recipient),
      question,
      due,
    });
    const key = attempt?.body === body ? attempt.key : crypto.randomUUID();
    setAttempt({ body, key });
    setBusy(true);
    setNotice("");
    try {
      await api("consultations/", "POST", {
        ...JSON.parse(body),
        client_key: key,
      });
      setQuestion("");
      setAttempt(undefined);
      await refresh();
      setNotice("Consulta registrada.");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const today = new Date();
  const minDate = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");
  return (
    <section aria-label="Consultas privadas" className="help">
      <h3>Consultas privadas</h3>
      <p>
        Solo participan quien abre la consulta y la persona asignada, mientras
        conserven acceso al servicio. Resolver una duda no aprueba ayudas ni
        respuestas.
      </p>
      <button disabled={busy} onClick={refresh}>
        {loaded ? "Actualizar consultas" : "Abrir consultas"}
      </button>
      <p role="status">{notice}</p>
      {loaded && (
        <>
          {instanceId && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void create();
              }}
            >
              <label>
                Persona a consultar
                <select
                  required
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                >
                  <option value="">Seleccione…</option>
                  {people.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.username})
                    </option>
                  ))}
                </select>
              </label>
              {!people.length && (
                <p>
                  No hay otra persona con nombramiento vigente para revisar este
                  servicio.
                </p>
              )}
              <label>
                Duda concreta
                <textarea
                  required
                  maxLength={5000}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
              </label>
              <label>
                Fecha de respuesta esperada
                <input
                  required
                  type="date"
                  min={minDate > "2026-10-01" ? minDate : "2026-10-01"}
                  value={due}
                  onChange={(e) => setDue(e.target.value)}
                />
              </label>
              <button disabled={busy || !people.length}>
                Registrar consulta
              </button>
            </form>
          )}
          {!items.length && <p>No hay consultas visibles para su cuenta.</p>}
          {items.map((item) => (
            <Thread key={item.id} item={item} refresh={refresh} />
          ))}
        </>
      )}
    </section>
  );
}
function Thread({
  item,
  refresh,
}: {
  item: Consultation;
  refresh: () => Promise<void>;
}) {
  const [body, setBody] = useState(""),
    [reason, setReason] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState<{ body: string; key: string }>();
  async function mutate(action: "message" | "resolve") {
    const key = attempt?.body === body ? attempt.key : crypto.randomUUID();
    if (action === "message") setAttempt({ body, key });
    setBusy(true);
    setNotice("");
    try {
      await api(
        `consultations/${item.id}/${action}/`,
        "POST",
        action === "message"
          ? { version: item.etag, body, client_key: key }
          : { version: item.etag, rationale: reason },
      );
      if (action === "message") {
        setBody("");
        setAttempt(undefined);
      } else setReason("");
      await refresh();
      setNotice("Cambio registrado.");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="panel" aria-label={"Consulta: " + item.question}>
      <h4>{item.question}</h4>
      <p>{item.original}</p>
      <p>
        {item.service_name} · {states[item.state]} · Fecha esperada: {item.due}
      </p>
      <p>
        {item.opened_by_name} → {item.assigned_to_name}
      </p>
      <small>
        Al abrir: ayuda {item.help_version ?? "sin versión"}; respuesta{" "}
        {item.answer_version ?? "sin versión"}.
      </small>
      {item.messages.map((m) => (
        <div key={m.id}>
          <strong>{m.author}</strong>
          <small> · {new Date(m.created_at).toLocaleString()}</small>
          <pre>{m.body}</pre>
        </div>
      ))}
      {item.resolution && <p>Resolución: {item.resolution}</p>}
      {item.can_reply && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void mutate("message");
          }}
        >
          <label>
            Mensaje de seguimiento
            <textarea
              required
              maxLength={5000}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
          </label>
          <button disabled={busy}>Enviar seguimiento</button>
        </form>
      )}
      {item.can_resolve && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void mutate("resolve");
          }}
        >
          <label>
            Cómo quedó resuelta la duda
            <textarea
              required
              maxLength={5000}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          <button disabled={busy}>Marcar duda resuelta</button>
        </form>
      )}
      <p role="status">{notice}</p>
    </article>
  );
}
