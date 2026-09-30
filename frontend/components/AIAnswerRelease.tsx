"use client";
import { useState } from "react";
import { api } from "../lib/api";
export type AnswerReleases = {
  version: number;
  revision: number;
  text: string;
  can_release: boolean;
  can_revoke: boolean;
  releases: {
    id: number;
    provider: string;
    purpose: "review" | "interview";
    version: number;
    expires: string;
    revoked: boolean;
    usable: boolean;
  }[];
};
export default function AIAnswerRelease({ instance }: { instance: number }) {
  const [data, setData] = useState<AnswerReleases>();
  const [purpose, setPurpose] = useState("review");
  const [provider, setProvider] = useState("openai"),
    [classification, setClassification] = useState("public"),
    [expires, setExpires] = useState(""),
    [rationale, setRationale] = useState("");
  const [checked, setChecked] = useState(false),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  async function load() {
    setData(await api<AnswerReleases>(`ai/answer-releases/${instance}/`));
    setChecked(false);
  }
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
  return (
    <section className="help" aria-label="Autorización de respuesta para IA">
      <details>
        <summary>Autorizar salida de una respuesta a IA</summary>
        <p>
          Otra persona con permiso de revisión debe comprobar que el texto no
          contiene datos personales, expedientes identificables, secretos ni
          información confidencial. Esta autorización permite enviarlo al
          proveedor elegido; no aprueba los hechos.
        </p>
        <button disabled={busy} onClick={() => run(load)}>
          Consultar texto y autorizaciones
        </button>
        {data && (
          <>
            <p>Respuesta guardada, versión {data.revision}</p>
            <pre>{data.text}</pre>
            {data.can_release && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void run(async () => {
                    await api(`ai/answer-releases/${instance}/`, "POST", {
                      version: data.version,
                      provider,
                      purpose,
                      classification,
                      expires,
                      rationale,
                      checked,
                    });
                    await load();
                    setNotice("Autorización registrada.");
                  });
                }}
              >
                <label>
                  Finalidad autorizada
                  <select
                    value={purpose}
                    onChange={(e) => {
                      setPurpose(e.target.value);
                      setChecked(false);
                    }}
                  >
                    <option value="review">Revisar la respuesta</option>
                    <option value="interview">
                      Usar como antecedente en la guía
                    </option>
                  </select>
                </label>
                <label>
                  Proveedor para esta respuesta
                  <select
                    value={provider}
                    onChange={(e) => {
                      setProvider(e.target.value);
                      setChecked(false);
                    }}
                  >
                    <option value="openai">OpenAI</option>
                    <option value="deepseek">DeepSeek</option>
                  </select>
                </label>
                <label>
                  Clasificación del texto
                  <select
                    value={classification}
                    onChange={(e) => {
                      setClassification(e.target.value);
                      setChecked(false);
                    }}
                  >
                    <option value="public">Información pública</option>
                    <option value="reviewed_anonymized">
                      Anonimizada y revisada
                    </option>
                  </select>
                </label>
                <label>
                  Vigente hasta
                  <input
                    type="date"
                    required
                    value={expires}
                    onChange={(e) => setExpires(e.target.value)}
                  />
                </label>
                <label>
                  Fundamento de salida
                  <textarea
                    required
                    maxLength={5000}
                    value={rationale}
                    onChange={(e) => setRationale(e.target.value)}
                  />
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => setChecked(e.target.checked)}
                  />
                  Cotejé exactamente este texto y su clasificación; puede salir
                  al proveedor seleccionado.
                </label>
                <button disabled={busy || !checked}>
                  Autorizar esta versión
                </button>
              </form>
            )}
            {data.releases.map((r) => (
              <p key={r.id}>
                Autorización {r.id} · {r.provider} ·{" "}
                {r.purpose === "interview"
                  ? "Antecedente para guía"
                  : "Revisión"}{" "}
                · versión {r.version} · hasta {r.expires} ·{" "}
                {r.usable ? "Vigente" : "No utilizable"}{" "}
                {!r.revoked && data.can_revoke && (
                  <button
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        await api(`ai/answer-releases/${r.id}/revoke/`, "POST");
                        await load();
                      })
                    }
                  >
                    Revocar {r.id}
                  </button>
                )}
              </p>
            ))}
          </>
        )}
        <p role="status">{notice}</p>
      </details>
    </section>
  );
}
