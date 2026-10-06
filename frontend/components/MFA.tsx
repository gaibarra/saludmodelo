"use client";
import { FormEvent, useState } from "react";
import { api, setCsrf } from "../lib/api";
export type Session = {
  csrf: string;
  password_only_demo?: boolean;
  password_only_pilot?: boolean;
  authenticated: boolean;
  username: string;
  mfa_required: boolean;
  mfa_enabled: boolean;
  mfa_verified: boolean;
  mfa_configured?: boolean;
  recovery_remaining?: number;
  recovery_pending?: boolean;
  recovery_enrollment_allowed?: boolean;
};
type Result = Session & { setup_secret?: string; recovery_codes?: string[] };
export default function MFA({
  session,
  onComplete,
}: {
  session: Session;
  onComplete: () => void;
}) {
  const [current, setCurrent] = useState(session);
  const [secret, setSecret] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>, action: string) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const form = e.currentTarget;
    const data = new FormData(form);
    try {
      const result = await api<Result>("mfa/", "POST", {
        action,
        password: data.get("password") || "",
        code: data.get("code") || "",
      });
      setCsrf(result.csrf);
      setCurrent(result);
      form.reset();
      if (result.setup_secret) setSecret(result.setup_secret);
      if (result.recovery_codes) {
        setCodes(result.recovery_codes);
        setSecret("");
      } else if (action === "verify") onComplete();
    } catch (e) {
      const message = (e as Error).message;
      try {
        const details = JSON.parse(message);
        setError(typeof details.detail === "string" ? details.detail : message);
      } catch {
        setError(message);
      }
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel" style={{ maxWidth: 640, margin: "24px auto" }}>
      <h2>Verificación en dos pasos</h2>
      <p>
        Cuenta: {current.username}. Use su aplicación autenticadora o un código
        de recuperación.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {codes.length > 0 ? (
        <>
          <h3>Guarde sus códigos de recuperación</h3>
          <p>
            Se muestran una sola vez. Cada código permite un acceso y sustituye
            al autenticador si lo pierde. Guárdelos en un lugar privado separado
            del teléfono.
          </p>
          <ul aria-label="Códigos de recuperación">
            {codes.map((c) => (
              <li key={c}>
                <code style={{ overflowWrap: "anywhere" }}>{c}</code>
              </li>
            ))}
          </ul>
          <button
            onClick={() => {
              setCodes([]);
              onComplete();
            }}
          >
            Guardé mis códigos; continuar
          </button>
        </>
      ) : secret ? (
        <>
          <h3>Agregar cuenta en su autenticador</h3>
          <p>
            Elija ingreso manual: cuenta {current.username}, emisor Salud
            Modelo, clave de tiempo (TOTP), seis dígitos y periodo de 30
            segundos. La configuración vence en diez minutos.
          </p>
          <p>
            Clave de configuración:{" "}
            <code data-testid="mfa-secret" style={{ overflowWrap: "anywhere" }}>
              {secret}
            </code>
          </p>
          <p>No comparta esta clave ni la incluya en capturas de pantalla.</p>
          <form onSubmit={(e) => submit(e, "confirm")}>
            <label>
              Código del autenticador
              <input
                name="code"
                autoComplete="one-time-code"
                inputMode="numeric"
                maxLength={6}
                required
              />
            </label>
            <button disabled={busy}>Confirmar autenticador</button>
          </form>
        </>
      ) : (
        <>
          {current.recovery_pending && !current.recovery_enrollment_allowed && (
            <form onSubmit={(e) => submit(e, "recover")}>
              <h3>Recuperación excepcional autorizada</h3>
              <p>Introduzca el código temporal entregado tras la verificación de identidad. Después deberá configurar un nuevo autenticador; el código no concede acceso al trabajo.</p>
              <label>Contraseña de la cuenta<input name="password" type="password" autoComplete="current-password" required /></label>
              <label>Código excepcional de un solo uso<input name="code" autoComplete="off" maxLength={80} required /></label>
              <button disabled={busy}>Canjear código excepcional</button>
            </form>
          )}
          {current.recovery_enrollment_allowed && <p>Identidad recuperada para esta sesión. Configure y confirme ahora su nuevo autenticador antes de acceder al trabajo.</p>}
          {current.mfa_enabled && !current.mfa_verified && !current.recovery_pending && (
            <form onSubmit={(e) => submit(e, "verify")}>
              <label>
                Código de verificación o recuperación
                <input
                  name="code"
                  autoComplete="one-time-code"
                  maxLength={80}
                  required
                />
              </label>
              <button disabled={busy}>Verificar acceso</button>
            </form>
          )}
          {!current.mfa_configured ? (
            <p>
              El operador autorizado debe configurar el cifrado de MFA antes de
              activar o sustituir un autenticador.
            </p>
          ) : (
            (!current.mfa_enabled || current.mfa_verified) && (!current.recovery_pending || current.recovery_enrollment_allowed) && (
              <>
                {current.mfa_enabled && (
                  <p>
                    MFA activo. Códigos de recuperación disponibles:{" "}
                    {current.recovery_remaining}.
                  </p>
                )}
                <form onSubmit={(e) => submit(e, "begin")}>
                  <h3>
                    {current.mfa_enabled
                      ? "Reemplazar autenticador"
                      : "Activar autenticador"}
                  </h3>
                  <label>
                    Confirme su contraseña
                    <input
                      name="password"
                      type="password"
                      autoComplete="current-password"
                      required
                    />
                  </label>
                  {current.mfa_enabled && (
                    <label>
                      Código actual o de recuperación
                      <input
                        name="code"
                        autoComplete="one-time-code"
                        required
                      />
                    </label>
                  )}
                  <button disabled={busy}>
                    {current.mfa_enabled
                      ? "Preparar reemplazo"
                      : "Preparar autenticador"}
                  </button>
                </form>
                {current.mfa_enabled && (
                  <form onSubmit={(e) => submit(e, "codes")}>
                    <h3>Renovar códigos de recuperación</h3>
                    <p>
                      Invalida los anteriores y la verificación de otras
                      sesiones.
                    </p>
                    <label>
                      Contraseña para renovar
                      <input
                        name="password"
                        type="password"
                        autoComplete="current-password"
                        required
                      />
                    </label>
                    <label>
                      Código para renovar
                      <input
                        name="code"
                        autoComplete="one-time-code"
                        required
                      />
                    </label>
                    <button disabled={busy}>Renovar códigos</button>
                  </form>
                )}
              </>
            )
          )}
          {current.authenticated && (
            <button onClick={onComplete}>Volver a mi trabajo</button>
          )}
        </>
      )}
      <button
        onClick={async () => {
          await api("session/", "DELETE");
          window.location.href = "/personal";
        }}
      >
        Cerrar sesión
      </button>
    </section>
  );
}
