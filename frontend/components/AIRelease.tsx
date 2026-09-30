"use client";
import { useState } from "react";
import { api } from "../lib/api";
export type Release = {
  id: number;
  fragment_id: number;
  provider: string;
  expires: string;
  revoked: boolean;
};
export default function AIRelease({
  instance,
  fragments,
  releases,
  canRelease,
  onChanged,
}: {
  instance: number;
  fragments: { id: number; locator: string; text: string }[];
  releases: Release[];
  canRelease: boolean;
  onChanged: () => Promise<void>;
}) {
  const [selected, setSelected] = useState<number[]>([]),
    [provider, setProvider] = useState("openai"),
    [classification, setClassification] = useState("public"),
    [expires, setExpires] = useState(""),
    [rationale, setRationale] = useState(""),
    [checked, setChecked] = useState(false),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  async function send(path: string, body?: unknown) {
    setBusy(true);
    setNotice("");
    try {
      await api(path, "POST", body);
      setSelected([]);
      setChecked(false);
      await onChanged();
      setNotice("Autorización actualizada.");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details>
      <summary>Autorizaciones de fragmentos para IA</summary>
      <p>
        La autorización permite que un capturista envíe estos fragmentos al
        proveedor elegido cuando exista una política habilitada. Revíselo antes
        de autorizar.
      </p>
      {canRelease && (
        <>
          <p>Seleccione hasta ocho fragmentos de esta página.</p>
          {fragments.map((f) => (
            <label key={f.id}>
              <input
                type="checkbox"
                checked={selected.includes(f.id)}
                disabled={
                  busy || (!selected.includes(f.id) && selected.length >= 8)
                }
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
          <label>
            Proveedor autorizado
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              <option value="openai">OpenAI</option>
              <option value="deepseek">DeepSeek</option>
            </select>
          </label>
          <label>
            Clasificación revisada
            <select
              value={classification}
              onChange={(e) => setClassification(e.target.value)}
            >
              <option value="public">Información pública</option>
              <option value="reviewed_anonymized">
                Información anonimizada y revisada
              </option>
            </select>
          </label>
          <label>
            Autorización hasta
            <input
              type="date"
              value={expires}
              onChange={(e) => setExpires(e.target.value)}
            />
          </label>
          <label>
            Fundamento de autorización
            <textarea
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
            Cotejé estos fragmentos: no contienen datos personales, expedientes
            clínicos, credenciales ni información confidencial.
          </label>
          <button
            disabled={
              busy ||
              !checked ||
              !selected.length ||
              !expires ||
              !rationale.trim()
            }
            onClick={() =>
              send(`ai/releases/${instance}/`, {
                fragment_ids: selected,
                provider,
                classification,
                expires,
                rationale,
              })
            }
          >
            Autorizar fragmentos seleccionados
          </button>
        </>
      )}
      {releases.map((r) => (
        <p key={r.id}>
          Fragmento {r.fragment_id} · {r.provider} · hasta {r.expires} ·{" "}
          {r.revoked ? "Revocada" : "Registrada"}{" "}
          {canRelease && !r.revoked && (
            <button
              disabled={busy}
              onClick={() => send(`ai/releases/${r.id}/revoke/`)}
            >
              Revocar autorización {r.id}
            </button>
          )}
        </p>
      ))}
      <p role="status">{notice}</p>
    </details>
  );
}
