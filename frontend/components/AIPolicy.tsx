"use client";
import { useState } from "react";
import { aiActions } from "../lib/ai-actions";
import { api } from "../lib/api";
type Policy = {
  etag: number;
  enabled: boolean;
  providers: string[];
  actions: string[];
  monthly_calls: number;
  monthly_user_calls: number;
  monthly_tokens: number;
  monthly_cost_limit: string;
  rationale: string;
};
export default function AIPolicy({ service }: { service: number }) {
  const [policy, setPolicy] = useState<Policy>();
  const [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  return (
    <section className="panel">
      <h3>Política de asistencia IA</h3>
      <p>
        La habilitación requiere presupuesto aprobado y configuración técnica.
        Cada fragmento necesita además autorización independiente de salida. Se
        excluyen expedientes identificables y secretos.
      </p>
      <button
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            setPolicy(await api<Policy>(`ai/policies/${service}/`));
          } catch (e) {
            setNotice((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        Consultar política IA
      </button>
      {policy && (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            try {
              const { etag, ...data } = policy;
              setPolicy(
                await api<Policy>(`ai/policies/${service}/`, "POST", {
                  ...data,
                  version: etag,
                }),
              );
              setNotice("Política registrada.");
            } catch (e) {
              setNotice((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label className="block">
            <input
              type="checkbox"
              checked={policy.enabled}
              onChange={(e) =>
                setPolicy({ ...policy, enabled: e.target.checked })
              }
            />
            Habilitar según la política institucional
          </label>
          {["openai", "deepseek"].map((p) => (
            <label className="block" key={p}>
              <input
                type="checkbox"
                checked={policy.providers.includes(p)}
                onChange={(e) =>
                  setPolicy({
                    ...policy,
                    providers: e.target.checked
                      ? [...policy.providers, p]
                      : policy.providers.filter((x) => x !== p),
                  })
                }
              />
              {p}
            </label>
          ))}
          <fieldset>
            <legend>Acciones autorizadas</legend>
            {Object.entries(aiActions).map(([action, label]) => (
              <label className="block" key={action}>
                <input
                  type="checkbox"
                  checked={policy.actions.includes(action)}
                  onChange={(e) =>
                    setPolicy({
                      ...policy,
                      actions: e.target.checked
                        ? [...policy.actions, action]
                        : policy.actions.filter((x) => x !== action),
                    })
                  }
                />
                {label}
              </label>
            ))}
          </fieldset>
          <label>
            Máximo de llamadas del servicio al mes
            <input
              type="number"
              min="0"
              max="10000"
              required
              value={policy.monthly_calls}
              onChange={(e) =>
                setPolicy({ ...policy, monthly_calls: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Máximo de llamadas por usuario al mes
            <input
              type="number"
              min="0"
              max="10000"
              required
              value={policy.monthly_user_calls}
              onChange={(e) =>
                setPolicy({
                  ...policy,
                  monthly_user_calls: Number(e.target.value),
                })
              }
            />
          </label>
          <label>
            Máximo de tokens reservados al mes
            <input
              type="number"
              min="0"
              max="100000000"
              required
              value={policy.monthly_tokens}
              onChange={(e) =>
                setPolicy({ ...policy, monthly_tokens: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Presupuesto mensual aprobado en USD
            <input
              type="number"
              min="0"
              step="0.000001"
              required
              value={policy.monthly_cost_limit}
              onChange={(e) =>
                setPolicy({ ...policy, monthly_cost_limit: e.target.value })
              }
            />
          </label>
          <label>
            Fundamento de la autorización
            <textarea
              required
              maxLength={5000}
              value={policy.rationale}
              onChange={(e) =>
                setPolicy({ ...policy, rationale: e.target.value })
              }
            />
          </label>
          <button disabled={busy}>Guardar política IA</button>
        </form>
      )}
      <p role="status">{notice}</p>
    </section>
  );
}
