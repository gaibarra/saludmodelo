"use client";
import { useState } from "react";
import type { AnswerReleases } from "./AIAnswerRelease";
import { aiActions } from "../lib/ai-actions";
import { api } from "../lib/api";
type Options = {
  providers: string[];
  actions: string[];
  static_help: Record<string, string>;
  fragments: Record<string, { id: number; locator: string; text: string }[]>;
  requests: { id: number; state: string; error: string }[];
};
type Output = {
  id: number;
  action: string;
  reviewed_version?: number | null;
  state: string;
  error: string;
  provider: string;
  model: string;
  estimated_cost: string | null;
  result: null | {
    plain_explanation: string;
    follow_up_questions: string[];
    missing_information: string[];
    suggested_fields: { field_id: string; value: string }[];
    citations: { fragment_id: number; locator: string; quote: string }[];
    conflicts: { description: string; fragment_ids: number[] }[];
  };
};
export default function AIHelp({
  instance,
  version,
  currentText,
  dirty,
  onApply,
}: {
  instance: number;
  version: number;
  currentText: string;
  dirty?: boolean;
  onApply: (id: number) => Promise<void>;
}) {
  const [releaseData, setReleaseData] = useState<AnswerReleases>();
  const [releaseId, setReleaseId] = useState(0);
  const [confirmed, setConfirmed] = useState(false);
  const [options, setOptions] = useState<Options>();
  const [action, setAction] = useState("suggest");
  const [provider, setProvider] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [result, setResult] = useState<Output>();
  const [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState<{ body: string; key: string }>();
  async function load() {
    setBusy(true);
    try {
      setOptions(await api<Options>(`ai/questions/${instance}/`));
      setReleaseData(
        await api<AnswerReleases>(`ai/answer-releases/${instance}/`),
      );
      setConfirmed(false);
      setReleaseId(0);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function inspect(id: number) {
    setBusy(true);
    setResult(undefined);
    try {
      setResult(await api<Output>(`ai/requests/${id}/`));
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function generate() {
    setNotice("");
    const body = JSON.stringify({
      provider,
      action,
      fragment_ids: selected,
      version,
      ...((action === "review" || action === "interview") && releaseId > 0
        ? { answer_release_id: releaseId, confirm_answer_send: confirmed }
        : {}),
    });
    const key = attempt?.body === body ? attempt.key : crypto.randomUUID();
    setAttempt({ body, key });
    setBusy(true);
    try {
      const job = await api<{ id: number }>(
        `ai/questions/${instance}/`,
        "POST",
        { ...JSON.parse(body), client_key: key },
      );
      await inspect(job.id);
      await load();
      setNotice("Solicitud registrada. Actualice para consultar el resultado.");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="help" aria-label="Asistencia con documentos">
      <h3>Asistencia con documentos</h3>
      <button disabled={busy} onClick={load}>
        {options ? "Actualizar asistencia" : "Abrir asistencia"}
      </button>
      <p role="status">{notice}</p>
      {options && (
        <>
          {!options.providers.length ? (
            <>
              <p>
                La salida a proveedores de IA está deshabilitada. Puede
                continuar con la ayuda revisada y la captura manual.
              </p>
              <details>
                <summary>Consultar ayuda disponible</summary>
                {Object.values(options.static_help).map((text, i) => (
                  <pre key={i}>{text}</pre>
                ))}
              </details>
            </>
          ) : (
            <>
              <label>
                Tipo de asistencia
                <select
                  value={action}
                  onChange={(e) => {
                    setAction(e.target.value);
                    setConfirmed(false);
                    setReleaseId(0);
                  }}
                >
                  <option value="">Seleccione…</option>
                  {options.actions.map((a) => (
                    <option key={a} value={a}>
                      {aiActions[a] ?? a}
                    </option>
                  ))}
                </select>
              </label>
              <p>
                Explicar y guiar pueden utilizar sólo la pregunta. La guía puede
                incorporar opcionalmente una respuesta guardada con autorización
                específica. La entrevista privada y su historial permanecen
                locales.
              </p>
              <label>
                Proveedor autorizado
                <select
                  value={provider}
                  onChange={(e) => {
                    setProvider(e.target.value);
                    setConfirmed(false);
                    setReleaseId(0);
                    setSelected([]);
                  }}
                >
                  <option value="">Seleccione…</option>
                  {options.providers.map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
              </label>
              <p>
                Seleccione hasta ocho fragmentos autorizados. Se enviarán estos
                textos y la pregunta original. Revisar mi respuesta, o guiar con
                un antecedente seleccionado, envía además la versión guardada
                autorizada que confirme abajo; el borrador sin guardar permanece
                local.
              </p>
              {(options.fragments[provider] ?? []).map((f) => (
                <label key={f.id} className="block">
                  <input
                    type="checkbox"
                    checked={selected.includes(f.id)}
                    disabled={!selected.includes(f.id) && selected.length >= 8}
                    onChange={(e) =>
                      setSelected(
                        e.target.checked
                          ? [...selected, f.id]
                          : selected.filter((id) => id !== f.id),
                      )
                    }
                  />
                  {f.locator}
                  <pre>{f.text}</pre>
                </label>
              ))}
              {provider && !options.fragments[provider]?.length && (
                <p>
                  No hay fragmentos con autorización vigente para este
                  proveedor.
                </p>
              )}
              {action === "contradictions" && (
                <p>
                  Seleccione al menos dos fragmentos distintos. Se compararán
                  sólo estas fuentes, sin enviar su respuesta. Los hallazgos
                  requieren resolución humana.
                </p>
              )}
              {["review", "interview"].includes(action) && (
                <>
                  <p>
                    La asistencia genera observaciones; no valida los hechos ni
                    guarda una respuesta nueva.
                  </p>
                  {dirty && (
                    <p>
                      Guarde sus cambios y obtenga autorización de la nueva
                      versión antes de revisarla con IA.
                    </p>
                  )}
                  <label>
                    Respuesta autorizada
                    <select
                      value={releaseId}
                      onChange={(e) => {
                        setReleaseId(Number(e.target.value));
                        setConfirmed(false);
                      }}
                    >
                      <option value={0}>
                        {action === "interview"
                          ? "Guiar sin compartir antecedentes"
                          : "Seleccione…"}
                      </option>
                      {releaseData?.version === version &&
                        releaseData.releases
                          .filter(
                            (r) =>
                              r.usable &&
                              r.provider === provider &&
                              (r.purpose ?? "review") === action,
                          )
                          .map((r) => (
                            <option key={r.id} value={r.id}>
                              Versión {r.version} · autorización {r.id}
                            </option>
                          ))}
                    </select>
                  </label>
                  {releaseId > 0 && (
                    <>
                      <pre>{releaseData?.text}</pre>
                      <label>
                        <input
                          type="checkbox"
                          checked={confirmed}
                          onChange={(e) => setConfirmed(e.target.checked)}
                        />
                        Confirmo enviar esta respuesta guardada al proveedor
                        seleccionado.
                      </label>
                    </>
                  )}
                </>
              )}
              <button
                disabled={
                  busy ||
                  ((action === "review" ||
                    (action === "interview" && releaseId > 0)) &&
                    (!releaseId ||
                      !confirmed ||
                      dirty ||
                      releaseData?.version !== version)) ||
                  !provider ||
                  !options.actions.includes(action) ||
                  (action === "contradictions" && selected.length < 2) ||
                  (["suggest", "extract", "report"].includes(action) &&
                    !selected.length)
                }
                onClick={generate}
              >
                {aiActions[action] ?? "Solicitar asistencia"}
              </button>
            </>
          )}
          {options.requests.map((r) => (
            <button key={r.id} disabled={busy} onClick={() => inspect(r.id)}>
              Solicitud {r.id}:{" "}
              {r.state === "ready"
                ? "disponible"
                : r.state === "applied"
                  ? "usada en borrador"
                  : ["failed", "rejected", "cancelled"].includes(r.state)
                    ? "no completada"
                    : "en proceso"}
            </button>
          ))}
        </>
      )}
      {result && (
        <>
          <button disabled={busy} onClick={() => inspect(result.id)}>
            Actualizar resultado
          </button>
          {["pending", "running", "ready"].includes(result.state) && (
            <button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api(`ai/requests/${result.id}/decision/`, "POST", {
                    decision: result.state === "ready" ? "reject" : "cancel",
                  });
                  await inspect(result.id);
                  await load();
                  setAttempt(undefined);
                  setNotice(
                    "Decisión registrada. Cancelar impide usar el resultado; no revierte un envío ya realizado.",
                  );
                } catch (e) {
                  setNotice((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {result.state === "ready"
                ? "Rechazar propuesta"
                : "Cancelar solicitud"}
            </button>
          )}
          {result.state === "failed" && (
            <p>
              No se completó la propuesta. Revise autorizaciones, configuración
              o cuota; su respuesta guardada se conserva.
            </p>
          )}
          {result.result && (
            <>
              <p>
                {aiActions[result.action]} · {result.provider} · {result.model}{" "}
                · Estimación USD: {result.estimated_cost ?? "sin dato"}
              </p>
              {result.action === "review" && (
                <p>
                  Observaciones sobre la respuesta guardada, versión{" "}
                  {result.reviewed_version ?? "indicada en la autorización"}.
                  Requieren revisión humana.
                </p>
              )}
              {result.action === "report" && (
                <p>
                  Borrador sobre esta pregunta y las fuentes seleccionadas.
                  Pendiente de revisión humana; no enviado.
                </p>
              )}
              <pre>{result.result.plain_explanation}</pre>
              {result.result.follow_up_questions.map((q, i) => (
                <p key={i}>{q}</p>
              ))}
              {result.result.missing_information.map((q, i) => (
                <p key={i}>Falta confirmar: {q}</p>
              ))}
              {result.action === "contradictions" &&
                result.result.conflicts.length === 0 && (
                  <p>
                    No se señalaron posibles contradicciones en esta
                    comparación. Esto no acredita consistencia completa; revise
                    la cobertura y las fuentes.
                  </p>
                )}
              {result.result.conflicts.map((c, i) => (
                <section key={i} aria-label={`Posible contradicción ${i + 1}`}>
                  <p>Posible contradicción: {c.description}</p>
                  {result.result?.citations
                    .filter((citation) =>
                      c.fragment_ids?.includes(citation.fragment_id),
                    )
                    .map((citation) => (
                      <blockquote key={citation.fragment_id}>
                        <p>{citation.locator}</p>
                        <pre>{citation.quote}</pre>
                      </blockquote>
                    ))}
                  <p>
                    Pendiente de resolución humana; no se elige automáticamente
                    una versión.
                  </p>
                </section>
              ))}
              {result.result.suggested_fields.map((f) => (
                <div key={f.field_id}>
                  <strong>Su texto actual</strong>
                  <pre>{currentText}</pre>
                  <strong>Propuesta para comparar</strong>
                  <pre>{f.value}</pre>
                </div>
              ))}
              {result.result.citations.map((c) => (
                <details key={c.fragment_id}>
                  <summary>{c.locator}</summary>
                  <pre>{c.quote}</pre>
                </details>
              ))}
              {result.action === "suggest" &&
                result.result.suggested_fields.length > 0 && (
                  <>
                    <p>
                      Usar la propuesta reemplaza el texto del editor y guarda
                      una nueva versión en borrador. Confirme los hechos antes
                      de enviarla a revisión.
                    </p>
                    <button
                      disabled={busy}
                      onClick={async () => {
                        setBusy(true);
                        try {
                          await onApply(result.id);
                          await inspect(result.id);
                          setNotice("Propuesta guardada como borrador.");
                        } catch (e) {
                          setNotice((e as Error).message);
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      Usar propuesta y guardar borrador
                    </button>
                  </>
                )}
            </>
          )}
        </>
      )}
    </section>
  );
}
