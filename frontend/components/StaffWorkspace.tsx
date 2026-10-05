"use client";
import InstitutionalLogo from "./InstitutionalLogo";
import "../app/personal/personal.css";
import StaffDashboard from "./StaffDashboard";
import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import MFA, { Session } from "./MFA";
import Consultations from "./Consultations";
import Evidence from "./Evidence";
import Interview from "./Interview";
import AIAnswerRelease from "./AIAnswerRelease";
import AIHelp from "./AIHelp";
import { api, listApi, setCsrf } from "../lib/api";
type Service = {
  id: number;
  name: string;
  site_name: string;
  confirmed: boolean;
};
type Revision = {
  version: number;
  content: string;
  knowledge: string;
  author_id: number;
  created_at: string;
};
type Answer = {
  upload_formats: string[];
  questionnaire: number;
  can_consult: boolean;
  can_ai: boolean;
  id: number;
  etag: number;
  version: number;
  state: string;
  original: string;
  source: string;
  question_version: number;
  help: Record<string, unknown>;
  revisions: Revision[];
  evidence: {
    id: string;
    name: string;
    state: string;
    url: string;
    download_allowed: boolean;
  }[];
};
type Dashboard = {
  validated: { label: string; numerator: number; denominator: number };
  tasks_pending: number;
  updated_at: string;
  clinical_scope: string;
};
const stateLabels: Record<string, string> = {
  pending: "Pendiente",
  draft: "Borrador",
  submitted: "Enviada",
  in_review: "En revisión",
  validated: "Validada",
  returned: "Devuelta",
  received: "Recibida",
  accepted: "Aceptada",
};
const helpLabels: Record<string, string> = {
  plain_explanation: "Qué significa",
  purpose: "Para qué se pregunta",
  knower: "Quién conoce la respuesta",
  where_to_find: "Dónde buscar",
  steps: "Cómo responder",
  fictional_example: "Ejemplo ficticio",
  evidence: "Evidencia y alternativas",
  sufficiency: "Cuándo es suficiente",
  applicability: "Cuándo aplica",
  escalation: "Consultar al responsable",
};
export default function StaffWorkspace({ planning = false }: { planning?: boolean }) {
  const [mfa, setMfa] = useState<Session>();
  const [user, setUser] = useState("");
  const [ready, setReady] = useState(false);
  const [passwordOnlyDemo, setPasswordOnlyDemo] = useState(false);
  const [error, setError] = useState("");
  const [services, setServices] = useState<Service[]>([]);
  const [service, setService] = useState<number>();
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [dash, setDash] = useState<Dashboard>();
  const [tasks, setTasks] = useState<
    { id: number; title: string; due: string; state: string }[]
  >([]);
  async function refresh() {
    const [s, d, t] = await Promise.all([
      listApi<Service>("services/"),
      api<Dashboard>("dashboard/"),
      listApi<{ id: number; title: string; due: string; state: string }>(
        "tasks/",
      ),
    ]);
    setServices(s);
    setDash(d);
    setTasks(t);
  }
  useEffect(() => {
    api<Session>("session/")
      .then((s) => {
        setCsrf(s.csrf);
        setPasswordOnlyDemo(!!s.password_only_demo);
        if (s.username && !s.authenticated) setMfa(s);
        if (s.authenticated) {
          setUser(s.username);
          if (planning) return refresh();
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setReady(true));
  }, [planning]);
  useEffect(() => {
    if (service)
      listApi<Answer>("answers/?service=" + service)
        .then((a) => setAnswers(a))
        .catch((e) => setError(e.message));
  }, [service]);
  async function access(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      const s = await api<Session>("session/", "POST", {
        username: f.get("username"),
        password: f.get("password"),
      });
      setCsrf(s.csrf);
      if (!s.authenticated) {
        setMfa(s);
        return;
      }
      setUser(s.username);
      if (planning) await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <div className="staff-space">
      <header className="staff-header">
        <Link href="/" className="staff-brand" aria-label="Salud y Odontología · Universidad Modelo">
          <InstitutionalLogo />
          <span><strong>Salud y Odontología</strong><small>UNIVERSIDAD MODELO</small></span>
        </Link>
        <Link href="/" className="staff-return">← Portal de servicios</Link>
        {user && (
          <button
            onClick={async () => {
              await api("session/", "DELETE");
              window.location.reload();
            }}
          >
            Cerrar sesión · {user}
          </button>
        )}
      </header>
      <main className={user ? "staff-workspace" : "staff-access"}>
        {!user && <aside className="staff-welcome">
          <span className="staff-eyebrow">ESPACIO DEL PERSONAL</span>
          <h1>Tu trabajo, conectado con la formación.</h1>
          <p>Organiza las actividades de tu servicio y acompaña las prácticas de los alumnos desde un mismo lugar.</p>
          <div className="staff-schools" aria-label="Escuelas independientes">
            <div><span aria-hidden>✳</span><strong>Escuela de Salud</strong><small>Dirección y administración propias</small></div>
            <div><span aria-hidden>✦</span><strong>Escuela de Odontología</strong><small>Dirección y administración propias</small></div>
          </div>
          <p className="staff-scope">Tu cuenta determina los servicios y la información que puedes consultar o administrar.</p>
          <ul className="staff-features"><li>Prácticas y seguimiento de alumnos</li><li>Evaluación por competencias</li><li>Informes y cierre del ciclo académico</li></ul>
        </aside>}
        <div className={user ? "staff-content" : "staff-access-card"}>
        {!user && !passwordOnlyDemo && <div className="staff-progress" aria-label="Etapas de acceso"><span className={!mfa ? "current" : "done"}>1 · Tu cuenta</span><span aria-hidden>—</span><span className={mfa ? "current" : ""}>2 · Verificación</span></div>}
        {passwordOnlyDemo && <p className="staff-demo-access" role="status">Demostración y pruebas · Acceso con usuario y contraseña. El autenticador se reactivará antes de trabajar con información real.</p>}
        {user && planning && (
          <nav
            className="panel flex flex-wrap gap-6"
            aria-label="Navegación principal"
          >
            <Link href="/personal">Mi trabajo</Link>
            <Link href="/administracion">Administración y cuestionarios</Link>
            <Link href="/consultas">Consultas</Link>
            <Link href="/cumplimiento">Cumplimiento</Link>
            <Link href="/seguimiento">Seguimiento</Link>
            <Link href="/reportes">Informes semanales</Link>
            <Link href="/decisiones">Decisiones</Link>
            <Link href="/capacidad">Capacidad y ausencias</Link>
            <Link href="/solicitudes-servicio">Solicitudes de pacientes</Link>
            <Link href="/escuelas">Escuelas</Link>
            <Link href="/academico">Prácticas académicas</Link>
            <Link href="/seguridad">Seguridad de la cuenta</Link>
          </nav>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {!ready ? (
          <p>Comprobando acceso…</p>
        ) : mfa ? (
          <>
            <MFA session={mfa} onComplete={() => window.location.reload()} />
            <p className="staff-account-help">¿Esta no es tu cuenta? Cierra sesión e ingresa con tu correo institucional.</p>
          </>
        ) : !user ? (
          <section className="panel staff-login">
            <h2>Acceso del personal</h2>
            <p>
              Ingresa con tu cuenta institucional para continuar a tu espacio de trabajo.
            </p>
            <form onSubmit={access}>
              <label htmlFor="username">Usuario</label>
              <input
                id="username"
                name="username"
                autoComplete="username"
                placeholder="tu.correo@modelo.edu.mx"
                autoCapitalize="none"
                spellCheck={false}
                required
              />
              <label htmlFor="password">Contraseña</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
              />
              <button>Ingresar</button>
            </form>
            <p className="staff-account-help">Usa el correo institucional como usuario si tu cuenta fue registrada con él.</p>
          </section>
        ) : !planning ? (
          <StaffDashboard username={user} />
        ) : (
          <>
            <section className="panel">
              <span className="badge">Gestión del plan</span>
              <h2 className="mt-4">Mi trabajo de hoy</h2>
              <div className="flex flex-wrap gap-12">
                <div>
                  <p>Respuestas validadas</p>
                  <p className="metric">{dash?.validated.label}</p>
                  <small>
                    Preguntas del alcance confirmado dentro de sus servicios
                    autorizados.
                  </small>
                </div>
                <div>
                  <p>Pendientes abiertos</p>
                  <p className="metric">{dash?.tasks_pending ?? "—"}</p>
                </div>
              </div>
              <small>
                Actualizado:{" "}
                {dash && new Date(dash.updated_at).toLocaleString("es-MX")}
              </small>
              <details>
                <summary>Alcance asistencial</summary>
                <p>{dash?.clinical_scope}</p>
                <p>La aceptación del gestor se registra por separado.</p>
              </details>
            </section>
            <div className="grid">
              <aside className="panel">
                <h2>Mis servicios</h2>
                {services.length === 0 ? (
                  <p>
                    No tiene asignaciones vigentes. Solicite a Dirección la
                    confirmación de su servicio y periodo.
                  </p>
                ) : (
                  services.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => setService(s.id)}
                      aria-pressed={service === s.id}
                    >
                      {s.name}
                      <br />
                      {s.site_name}
                    </button>
                  ))
                )}
                <h3 className="mt-6">Pendientes</h3>
                {tasks.length === 0 ? (
                  <p>No hay pendientes registrados.</p>
                ) : (
                  tasks.map((t) => (
                    <p key={t.id}>
                      {t.title}
                      <small>
                        {t.due} · {stateLabels[t.state] ?? t.state}
                      </small>
                    </p>
                  ))
                )}
              </aside>
              <section>
                {!service ? (
                  <div className="panel">
                    <h2>Seleccione un servicio</h2>
                    <p>
                      Encontrará sus preguntas, ayudas, respuestas e historial.
                    </p>
                  </div>
                ) : answers.length === 0 ? (
                  <div className="panel">
                    <h2>El cuestionario está en preparación</h2>
                    <p>
                      Las preguntas se habilitarán cuando su alcance y sus
                      fichas de ayuda estén revisados. No hay respuestas
                      precargadas.
                    </p>
                  </div>
                ) : (
                  answers.map((a) => (
                    <Question key={a.id} initial={a} onSaved={refresh} />
                  ))
                )}
              </section>
            </div>
          </>
        )}
        </div>
      </main>
      <footer className="staff-footer"><span>Escuelas de Salud y Odontología · Universidad Modelo</span><Link href="/">Servicios para pacientes y público</Link></footer>
    </div>
  );
}
function Question({
  initial,
  onSaved,
}: {
  initial: Answer;
  onSaved: () => Promise<void>;
}) {
  const [a, setA] = useState(initial);
  const [content, setContent] = useState(initial.revisions[0]?.content ?? "");
  const [knowledge, setKnowledge] = useState(
    initial.revisions[0]?.knowledge ?? "known",
  );
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [rationale, setRationale] = useState("");
  async function act(fn: () => Promise<Answer>) {
    setBusy(true);
    setMessage("Guardando…");
    try {
      const fresh = await fn();
      setA(fresh);
      setMessage("Guardado confirmado.");
      await onSaved();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="panel">
      <small>
        Pregunta · versión {a.question_version} · Estado:{" "}
        {stateLabels[a.state] ?? a.state}
      </small>
      <h2>{a.original}</h2>
      <details className="help">
        <summary>Explícame y guíame paso a paso</summary>
        {Object.entries(a.help)
          .filter(([k]) => helpLabels[k])
          .map(([k, v]) => (
            <div key={k}>
              <strong>{helpLabels[k]}</strong>
              <pre>
                {typeof v === "string" ? v : JSON.stringify(v, null, 2)}
              </pre>
            </div>
          ))}
      </details>
      <details>
        <summary>Ver fuentes</summary>
        <p>Plan de Trabajo v3.1 · {a.source}</p>
      </details>
      <label htmlFor={"k" + a.id}>¿Qué sabe actualmente?</label>
      <select
        id={"k" + a.id}
        value={knowledge}
        onChange={(e) => setKnowledge(e.target.value)}
      >
        <option value="known">Puedo responder</option>
        <option value="unknown">No lo sé</option>
        <option value="absent">No existe actualmente</option>
        <option value="unconfirmed">Está por confirmar</option>
        <option value="not_applicable">Considero que no aplica</option>
      </select>
      <label htmlFor={"a" + a.id}>Respuesta o justificación</label>
      <textarea
        id={"a" + a.id}
        value={content}
        onChange={(e) => setContent(e.target.value)}
      />
      <button
        disabled={busy}
        onClick={() =>
          act(() =>
            api<Answer>(`answers/${a.id}/save/`, "POST", {
              version: a.etag,
              content,
              knowledge,
            }),
          )
        }
      >
        Guardar y continuar
      </button>
      <button
        disabled={busy || !a.version}
        onClick={() =>
          act(() =>
            api<Answer>(`answers/${a.id}/transition/`, "POST", {
              version: a.etag,
              target: "submitted",
            }),
          )
        }
      >
        Enviar a revisión
      </button>
      <p role="status" aria-live="polite">
        {message}
      </p>
      <details>
        <summary>Evidencia y declaraciones</summary>
        <p>
          Se admiten TXT y CSV UTF-8 con separador de coma, hasta 10 MB. La
          recepción no equivale a aceptación de evidencia.
        </p>
        <input
          aria-label="Adjuntar declaración"
          type="file"
          accept={a.upload_formats.map((format) => "." + format).join(",")}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              const f = new FormData();
              f.set("file", file);
              f.set("version", String(a.etag));
              void act(() =>
                api<Answer>(`answers/${a.id}/evidence/`, "POST", f),
              );
            }
          }}
        />
        {a.evidence.map((e) => (
          <Evidence
            key={e.id}
            id={e.id}
            name={e.name}
            url={e.url}
            downloadAllowed={e.download_allowed}
          />
        ))}
      </details>
      <details>
        <summary>Revisar respuesta</summary>
        <label htmlFor={"r" + a.id}>Fundamento u observaciones</label>
        <textarea
          id={"r" + a.id}
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
        />
        {(["validated", "returned"] as const).map((target) => (
          <button
            key={target}
            disabled={busy}
            onClick={() =>
              act(() =>
                api<Answer>(`answers/${a.id}/transition/`, "POST", {
                  version: a.etag,
                  target,
                  rationale,
                }),
              )
            }
          >
            {target === "validated"
              ? "Validar respuesta"
              : "Devolver con observaciones"}
          </button>
        ))}
        <small>
          Requiere permiso de revisión y una persona distinta del autor.
        </small>
      </details>
      <details>
        <summary>Historial de respuestas</summary>
        {a.revisions.map((r) => (
          <div key={r.version}>
            <small>
              Versión {r.version} ·{" "}
              {new Date(r.created_at).toLocaleString("es-MX")}
            </small>
            <pre>{r.content}</pre>
          </div>
        ))}
      </details>
      <AIAnswerRelease
        key={`release-${a.questionnaire}-${a.etag}`}
        instance={a.questionnaire}
      />
      {a.can_ai && (
        <AIHelp
          instance={a.questionnaire}
          version={a.etag}
          currentText={content}
          dirty={content !== (a.revisions[0]?.content ?? "")}
          onApply={async (id) => {
            const fresh = await api<Answer>(`ai/requests/${id}/`, "POST");
            setA(fresh);
            setContent(fresh.revisions[0]?.content ?? "");
            setKnowledge(fresh.revisions[0]?.knowledge ?? "unconfirmed");
            await onSaved();
          }}
        />
      )}
      {a.can_ai && (
        <Interview
          instance={a.questionnaire}
          answerVersion={a.etag}
          currentText={content}
          dirty={content !== (a.revisions[0]?.content ?? "")}
          onApplied={async () => {
            const fresh = await api<Answer>(`answers/${a.id}/`);
            setA(fresh);
            setContent(fresh.revisions[0]?.content ?? "");
            setKnowledge(fresh.revisions[0]?.knowledge ?? "unconfirmed");
            await onSaved();
          }}
        />
      )}
      {a.can_consult && <Consultations instanceId={a.questionnaire} />}
    </article>
  );
}
