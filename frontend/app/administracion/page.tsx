"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import SourceChanges from "./SourceChanges";
import Link from "next/link";
import Consultations from "../../components/Consultations";
import AIPolicy from "../../components/AIPolicy";
import { api, listApi, setCsrf } from "../../lib/api";

type Named = { id: number; name: string };
type Service = Named & {
  site: number;
  site_name: string;
  institution: number;
  etag: number;
  confirmed: boolean;
};
type Member = {
  id: number;
  username: string;
  name: string;
  institution: number;
};
type Setup = {
  institutions: Named[];
  campuses: (Named & { institution: number })[];
  sites: (Named & { campus: number })[];
  services: Service[];
  users: Member[];
  questionnaire_services: Service[];
};
type Grant = {
  substitutes: number | null;
  id: number;
  username: string;
  service: number;
  role: string;
  starts: string;
  ends: string;
  revoked_at: string | null;
  rationale: string;
  revocation_reason: string;
};
type CatalogQuestion = {
  id: number;
  code: string;
  original: string;
  section: string;
  version: number;
  locator: string;
};
type Proposal = {
  content: Record<string, string>;
  digest: string;
  references: { id: number; locator: string; text: string }[];
};
type HelpRevision = {
  origin: string;
  sources: { id: number; locator: string; text: string }[];
  id: number;
  number: number;
  content: Record<string, string>;
  author_name: string;
  created_at: string;
  review: null | { decision: string; reviewer: string; rationale: string };
};
type Questionnaire = {
  id: number;
  service: number;
  etag: number;
  published: boolean;
  published_help: number | null;
  original: string;
  section: string;
  locator: string;
  code: string;
  revisions: HelpRevision[];
  draft_available: boolean;
  can_consult: boolean;
  can_edit: boolean;
  can_review: boolean;
};
const HELP: Record<string, string> = {
  plain_explanation: "Qué significa",
  purpose: "Para qué se pregunta",
  knower: "Quién conoce la respuesta",
  where_to_find: "Dónde buscar la información",
  steps: "Pasos para responder",
  fictional_example: "Ejemplo ficticio (identifíquelo expresamente)",
  evidence: "Evidencia necesaria y alternativas",
  sufficiency: "Errores frecuentes y respuesta suficiente",
  applicability: "Cuándo aplica y de qué depende",
  escalation: "A quién consultar y cómo resolver una duda",
};
const ROLES: Record<string, string> = {
  director: "Dirección de servicio",
  coordinator: "Coordinación del plan",
  manager: "Responsable de servicio",
  contributor: "Colaborador",
  compliance: "Validador de cumplimiento o jurídico",
  clinical: "Validador clínico",
  developer: "Desarrollador",
  technical: "Administrador técnico",
  auditor: "Auditor de consulta",
};
function value(form: FormData, key: string) {
  return String(form.get(key) ?? "");
}
function Picker({
  id,
  label,
  items,
  name,
}: {
  id: string;
  label: string;
  items: Named[];
  name?: string;
}) {
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <select id={id} name={name ?? id} required defaultValue="">
        <option value="" disabled>
          Seleccione…
        </option>
        {items.map((i) => (
          <option value={i.id} key={i.id}>
            {i.name}
          </option>
        ))}
      </select>
    </>
  );
}

export default function Administration() {
  const [setup, setSetup] = useState<Setup>();
  const [user, setUser] = useState("");
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState("organization");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [grants, setGrants] = useState<Grant[]>([]);
  const [serviceId, setServiceId] = useState<number>();
  const [catalog, setCatalog] = useState<CatalogQuestion[]>([]);
  const [forms, setForms] = useState<Questionnaire[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [filter, setFilter] = useState("");
  const refresh = useCallback(async () => {
    const [s, g] = await Promise.all([
      api<Setup>("administration/setup/"),
      listApi<Grant>("administration/assignments/"),
    ]);
    setSetup(s);
    setGrants(g);
    return s;
  }, []);
  useEffect(() => {
    api<{ authenticated: boolean; username: string; csrf: string }>("session/")
      .then(async (session) => {
        setCsrf(session.csrf);
        if (session.authenticated) {
          setUser(session.username);
          await refresh();
        }
      })
      .catch((e) => setNotice(e.message))
      .finally(() => setReady(true));
  }, [refresh]);
  const loadForms = useCallback(async (id: number) => {
    const data = await listApi<Questionnaire>("questionnaires/?service=" + id);
    setForms(data);
  }, []);
  useEffect(() => {
    if (!serviceId || !setup) return;
    let live = true;
    setForms([]);
    setCatalog([]);
    setSelected([]);
    Promise.all([
      listApi<Questionnaire>("questionnaires/?service=" + serviceId),
      setup.services.some((s) => s.id === serviceId)
        ? api<{ questions: CatalogQuestion[] }>(
            "administration/catalog/?service=" + serviceId,
          )
        : Promise.resolve({ questions: [] }),
    ])
      .then(([q, c]) => {
        if (live) {
          setForms(q);
          setCatalog(c.questions);
        }
      })
      .catch((e) => {
        if (live) setNotice(e.message);
      });
    return () => {
      live = false;
    };
  }, [serviceId, setup]);
  async function run(work: () => Promise<unknown>, message: string) {
    setBusy(true);
    setNotice("Guardando…");
    try {
      await work();
      await refresh();
      setNotice(message);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function create(e: FormEvent<HTMLFormElement>, kind: string) {
    e.preventDefault();
    const element = e.currentTarget;
    const f = new FormData(element);
    let data: unknown;
    if (kind === "campuses")
      data = {
        institution: Number(f.get("institution")),
        name: value(f, "name"),
      };
    if (kind === "sites")
      data = {
        campus: Number(f.get("campus")),
        name: value(f, "name"),
        timezone: value(f, "timezone"),
      };
    if (kind === "services")
      data = {
        site: Number(f.get("site")),
        name: value(f, "name"),
        kind: value(f, "kind"),
      };
    if (kind === "users")
      data = {
        institution: Number(f.get("institution")),
        username: value(f, "username"),
        first_name: value(f, "first_name"),
        last_name: value(f, "last_name"),
        password: value(f, "password"),
      };
    if (kind === "assignments")
      data = {
        substitutes: f.get("substitutes") ? Number(f.get("substitutes")) : null,
        service: Number(f.get("service")),
        user: Number(f.get("user")),
        role: value(f, "role"),
        starts: value(f, "starts"),
        ends: value(f, "ends"),
        rationale: value(f, "rationale"),
      };
    void run(async () => {
      await api("administration/" + kind + "/", "POST", data);
      element.reset();
    }, "Registro guardado.");
  }
  const administrative = Boolean(
    setup?.institutions.length || setup?.services.length,
  );
  return (
    <>
      <header>
        <div>
          <span>ESCUELA DE SALUD · UNIVERSIDAD MODELO</span>
          <h1>Administración del plan</h1>
        </div>
        <Link href="/personal" className="button">
          Volver a mi trabajo
        </Link>
      </header>
      <main>
        <p
          role="status"
          aria-live="polite"
          className={notice.includes("Guardado") ? "" : "notice"}
        >
          {notice}
        </p>
        {!ready ? (
          <p>Cargando permisos…</p>
        ) : !user ? (
          <section className="panel">
            <h2>Ingrese para continuar</h2>
            <Link href="/personal">Ir al acceso</Link>
          </section>
        ) : (
          <>
            <nav className="panel" aria-label="Secciones de administración">
              {administrative && (
                <>
                  <button
                    aria-pressed={tab === "organization"}
                    onClick={() => setTab("organization")}
                  >
                    Sedes y servicios
                  </button>
                  <button
                    aria-pressed={tab === "people"}
                    onClick={() => setTab("people")}
                  >
                    Usuarios y nombramientos
                  </button>
                </>
              )}
              <button
                aria-pressed={tab === "questions"}
                onClick={() => setTab("questions")}
              >
                Cuestionarios y ayudas
              </button>
            </nav>
            {!administrative && tab !== "questions" && (
              <section className="panel">
                <h2>Administración restringida a Dirección</h2>
                <p>
                  Puede preparar o revisar cuestionarios de los servicios que
                  tenga asignados. El acceso técnico no concede nombramientos
                  institucionales.
                </p>
                <button onClick={() => setTab("questions")}>
                  Abrir mis cuestionarios
                </button>
              </section>
            )}
            {setup && administrative && tab === "organization" && (
              <>
                <div className="admin-grid">
                  {setup.institutions.length > 0 && (
                    <>
                      <form
                        className="panel"
                        onSubmit={(e) => create(e, "campuses")}
                      >
                        <h2>Nuevo campus</h2>
                        <Picker
                          id="campus-institution"
                          name="institution"
                          label="Institución"
                          items={setup.institutions}
                        />
                        <label htmlFor="campus-name">Nombre del campus</label>
                        <input
                          id="campus-name"
                          name="name"
                          maxLength={120}
                          required
                        />
                        <button disabled={busy}>Crear campus</button>
                      </form>
                      <form
                        className="panel"
                        onSubmit={(e) => create(e, "sites")}
                      >
                        <h2>Nueva sede</h2>
                        <Picker
                          id="site-campus"
                          name="campus"
                          label="Campus"
                          items={setup.campuses}
                        />
                        <label htmlFor="site-name">Nombre de la sede</label>
                        <input
                          id="site-name"
                          name="name"
                          maxLength={120}
                          required
                        />
                        <label htmlFor="site-timezone">Zona horaria</label>
                        <input
                          id="site-timezone"
                          name="timezone"
                          defaultValue="America/Merida"
                          required
                        />
                        <button disabled={busy}>Crear sede</button>
                      </form>
                      <form
                        className="panel"
                        onSubmit={(e) => create(e, "services")}
                      >
                        <h2>Nuevo servicio o unidad administrativa</h2>
                        <Picker
                          id="service-site"
                          name="site"
                          label="Sede"
                          items={setup.sites}
                        />
                        <label htmlFor="service-name">
                          Nombre del servicio o unidad
                        </label>
                        <input
                          id="service-name"
                          name="name"
                          maxLength={160}
                          required
                        />
                        <label htmlFor="service-kind">Tipo</label>
                        <select id="service-kind" name="kind">
                          <option value="service">Servicio</option>
                          <option value="administration">
                            Unidad administrativa
                          </option>
                        </select>
                        <button disabled={busy}>Crear servicio</button>
                      </form>
                    </>
                  )}
                </div>
                <section className="panel">
                  <h2>Alcance de servicios</h2>
                  {setup.services.length === 0 ? (
                    <p>
                      No hay servicios registrados. Cree primero el campus y la
                      sede.
                    </p>
                  ) : (
                    setup.services.map((s) => (
                      <div className="row" key={s.id}>
                        <h3>
                          {s.name} · {s.site_name}
                        </h3>
                        {s.confirmed ? (
                          <p>Alcance confirmado</p>
                        ) : (
                          <form
                            onSubmit={(e) => {
                              e.preventDefault();
                              const f = new FormData(e.currentTarget);
                              void run(
                                () =>
                                  api(
                                    `administration/services/${s.id}/confirm/`,
                                    "POST",
                                    {
                                      version: s.etag,
                                      rationale: value(f, "rationale"),
                                    },
                                  ),
                                "Alcance confirmado.",
                              );
                            }}
                          >
                            <label htmlFor={"confirm-" + s.id}>
                              Fundamento de la confirmación
                            </label>
                            <input
                              id={"confirm-" + s.id}
                              name="rationale"
                              required
                              maxLength={5000}
                            />
                            <button disabled={busy}>Confirmar servicio</button>
                          </form>
                        )}
                      </div>
                    ))
                  )}
                </section>
              </>
            )}
            {setup && administrative && tab === "people" && (
              <>
                <div className="admin-grid">
                  {setup.institutions.length > 0 && (
                    <form
                      className="panel"
                      onSubmit={(e) => create(e, "users")}
                    >
                      <h2>Registrar usuario</h2>
                      <p>La cuenta se crea sin permisos de servicio.</p>
                      <Picker
                        id="user-institution"
                        name="institution"
                        label="Institución de la persona"
                        items={setup.institutions}
                      />
                      <label htmlFor="new-user">Usuario</label>
                      <input
                        id="new-user"
                        name="username"
                        autoComplete="off"
                        maxLength={150}
                        required
                      />
                      <label htmlFor="first-name">Nombre</label>
                      <input
                        id="first-name"
                        name="first_name"
                        maxLength={150}
                        required
                      />
                      <label htmlFor="last-name">Apellidos</label>
                      <input id="last-name" name="last_name" maxLength={150} />
                      <label htmlFor="new-password">
                        Contraseña inicial (mínimo 12 caracteres)
                      </label>
                      <input
                        id="new-password"
                        name="password"
                        type="password"
                        minLength={12}
                        maxLength={256}
                        autoComplete="new-password"
                        required
                      />
                      <button disabled={busy}>Crear usuario</button>
                    </form>
                  )}
                  <form
                    className="panel"
                    onSubmit={(e) => create(e, "assignments")}
                  >
                    <h2>Aprobar nombramiento</h2>
                    <p>
                      Confirme la función y la competencia de la persona. No
                      puede asignarse permisos a sí mismo.
                    </p>
                    <Picker
                      id="grant-user"
                      name="user"
                      label="Persona"
                      items={setup.users
                        .filter((u) => u.username !== user)
                        .map((u) => ({
                          id: u.id,
                          name: `${u.name} (${u.username})`,
                        }))}
                    />
                    <Picker
                      id="grant-service"
                      name="service"
                      label="Servicio del nombramiento"
                      items={setup.services}
                    />
                    <label htmlFor="grant-role">Rol autorizado</label>
                    <select id="grant-role" name="role">
                      {Object.entries(ROLES).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                    <label htmlFor="grant-substitutes">Nombramiento titular a suplir (opcional)</label>
                    <select id="grant-substitutes" name="substitutes"><option value="">Nombramiento independiente</option>{grants.filter(g=>!g.revoked_at&&!g.substitutes).map(g=><option key={g.id} value={g.id}>#{g.id} · {g.username} · {ROLES[g.role]} · {setup.services.find(s=>s.id===g.service)?.name} · {g.starts} — {g.ends}</option>)}</select>
                    <p>Para suplencia, elija otra persona, el mismo servicio y rol, y fechas dentro de la vigencia del titular. Revocar al titular revoca sus suplencias. No se transfieren tareas ni firmas.</p>
                    <label htmlFor="grant-starts">Inicio de vigencia</label>
                    <input
                      id="grant-starts"
                      name="starts"
                      type="date"
                      required
                    />
                    <label htmlFor="grant-ends">Fin de vigencia</label>
                    <input id="grant-ends" name="ends" type="date" required />
                    <label htmlFor="grant-reason">
                      Fundamento y competencia confirmada
                    </label>
                    <textarea
                      id="grant-reason"
                      name="rationale"
                      maxLength={5000}
                      required
                    />
                    <button disabled={busy}>Aprobar nombramiento</button>
                  </form>
                </div>
                <section className="panel">
                  <h2>Nombramientos e historial</h2>
                  {!grants.length ? (
                    <p>Aún no hay nombramientos.</p>
                  ) : (
                    grants.map((g) => (
                      <div className="row" key={g.id}>
                        <h3>
                          #{g.id} · {g.username} · {ROLES[g.role]}
                        </h3>
                        <p>
                          {setup.services.find((s) => s.id === g.service)?.name}{" "}
                          · {g.starts} — {g.ends}
                        </p>
                        <p>{g.rationale}</p>
                        {g.substitutes && <p>Suplencia del nombramiento #{g.substitutes}</p>}
                        {g.revoked_at ? (
                          <p>Revocado: {g.revocation_reason}</p>
                        ) : (
                          <form
                            onSubmit={(e) => {
                              e.preventDefault();
                              const f = new FormData(e.currentTarget);
                              void run(
                                () =>
                                  api(
                                    `administration/assignments/${g.id}/revoke/`,
                                    "POST",
                                    { rationale: value(f, "rationale") },
                                  ),
                                "Nombramiento revocado. El historial se conserva.",
                              );
                            }}
                          >
                            <label htmlFor={"revoke-" + g.id}>
                              Motivo de revocación
                            </label>
                            <input
                              id={"revoke-" + g.id}
                              name="rationale"
                              maxLength={5000}
                              required
                            />
                            <button disabled={busy}>
                              Revocar nombramiento
                            </button>
                          </form>
                        )}
                      </div>
                    ))
                  )}
                </section>
              </>
            )}
            {setup && tab === "questions" && (
              <>
                <section className="panel">
                  <h2>Preparar cuestionarios</h2>
                  <p>
                    Seleccione las preguntas del alcance, prepare sus diez
                    apartados de ayuda y solicite revisión por otra persona
                    antes de publicar.
                  </p>
                  <label htmlFor="questionnaire-service">
                    Servicio del cuestionario
                  </label>
                  <select
                    id="questionnaire-service"
                    value={serviceId ?? ""}
                    onChange={(e) => setServiceId(Number(e.target.value))}
                  >
                    <option value="" disabled>
                      Seleccione…
                    </option>
                    {setup.questionnaire_services.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} · {s.site_name}
                      </option>
                    ))}
                  </select>
                  {serviceId && (
                    <p>
                      {forms.filter((f) => f.published).length} de{" "}
                      {forms.length} preguntas publicadas ·{" "}
                      {
                        forms.filter(
                          (f) =>
                            f.revisions[0]?.review?.decision === "approved",
                        ).length
                      }{" "}
                      fichas vigentes revisadas
                    </p>
                  )}
                </section>
                {serviceId &&
                  setup.services.some((s) => s.id === serviceId) && (
                    <details className="panel">
                      <summary>
                        Seleccionar preguntas del inventario autorizado
                      </summary>
                      {!catalog.length ? (
                        <p>
                          No hay inventario autorizado para esta institución. El
                          operador debe importar la fuente y registrar su acceso
                          institucional.
                        </p>
                      ) : (
                        <>
                          <label htmlFor="question-search">
                            Buscar por texto, sección o código
                          </label>
                          <input
                            id="question-search"
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                          />
                          <div className="catalog">
                            {catalog
                              .filter((q) =>
                                (q.original + " " + q.section + " " + q.code)
                                  .toLowerCase()
                                  .includes(filter.toLowerCase()),
                              )
                              .map((q) => (
                                <label className="checkrow" key={q.id}>
                                  <input
                                    type="checkbox"
                                    checked={selected.includes(q.id)}
                                    onChange={(e) =>
                                      setSelected(
                                        e.target.checked
                                          ? [...selected, q.id]
                                          : selected.filter(
                                              (id) => id !== q.id,
                                            ),
                                      )
                                    }
                                  />
                                  <span>
                                    <strong>{q.code}</strong>
                                    <br />
                                    {q.original}
                                    <small>{q.section}</small>
                                  </span>
                                </label>
                              ))}
                          </div>
                          <form
                            onSubmit={(e) => {
                              e.preventDefault();
                              const f = new FormData(e.currentTarget);
                              void run(
                                () =>
                                  api("questionnaires/select/", "POST", {
                                    service: serviceId,
                                    question_versions: selected,
                                    rationale: value(f, "rationale"),
                                  }),
                                "Preguntas agregadas al alcance; sus ayudas requieren preparación y revisión.",
                              );
                            }}
                          >
                            <label htmlFor="selection-reason">
                              Fundamento de selección del alcance
                            </label>
                            <textarea
                              id="selection-reason"
                              name="rationale"
                              required
                              maxLength={5000}
                            />
                            <button disabled={busy || !selected.length}>
                              Agregar {selected.length} preguntas
                            </button>
                          </form>
                        </>
                      )}
                    </details>
                  )}
                {serviceId && !forms.length && (
                  <section className="panel">
                    <p>No hay preguntas asignadas a este servicio todavía.</p>
                  </section>
                )}
                {serviceId &&
                  setup.services.some((s) => s.id === serviceId) && (
                    <AIPolicy key={serviceId} service={serviceId} />
                  )}
                {forms.map((q) => (
                  <HelpEditor
                    key={`${q.id}:${serviceId}`}
                    initial={q}
                    user={user}
                    onChange={() => loadForms(q.service)}
                  />
                ))}
              </>
            )}
          </>
        )}
      </main>
    </>
  );
}

function HelpEditor({
  initial,
  user,
  onChange,
}: {
  initial: Questionnaire;
  user: string;
  onChange: () => Promise<void>;
}) {
  const [q, setQ] = useState(initial);
  const [proposal, setProposal] = useState<Proposal>();
  const [proposalDigest, setProposalDigest] = useState("");
  const [content, setContent] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      Object.keys(HELP).map((k) => [k, initial.revisions[0]?.content[k] ?? ""]),
    ),
  );
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [reason, setReason] = useState("");
  // Never overwrite unsaved text after a refresh or a conflict.
  useEffect(() => {
    if (!dirty) {
      setQ(initial);
      setContent(
        Object.fromEntries(
          Object.keys(HELP).map((k) => [
            k,
            initial.revisions[0]?.content[k] ?? "",
          ]),
        ),
      );
    }
  }, [initial, dirty]);
  const latest = q.revisions[0];
  const complete = Object.keys(HELP).every((k) => content[k]?.trim());
  async function mutate(action: string, data: unknown) {
    setBusy(true);
    setNotice("Guardando…");
    try {
      const next = await api<Questionnaire>(
        `questionnaires/${q.id}/${action}/`,
        "POST",
        data,
      );
      setQ(next);
      setProposalDigest("");
      setProposal(undefined);
      setDirty(false);
      setNotice(
        action === "publish"
          ? "Pregunta publicada."
          : action === "review"
            ? "Revisión registrada."
            : "Borrador guardado.",
      );
      await onChange();
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="panel" aria-label={"Ficha " + q.code}>
      <small>
        {q.code} · {q.section}
      </small>
      <h2>{q.original}</h2>
      <SourceChanges key={q.id} instance={q.id} onChange={onChange}/>
      <p>
        {q.published ? "Publicada" : "En preparación"} ·{" "}
        {latest ? `Ayuda versión ${latest.number}` : "Sin ficha de ayuda"}
        {latest?.review &&
          ` · ${latest.review.decision === "approved" ? "Revisada" : "Devuelta"}`}
      </p>
      <details>
        <summary>Ver fuente original</summary>
        <p>{q.locator}</p>
      </details>
      {q.can_edit && q.draft_available && (
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              setProposal(await api<Proposal>(`questionnaires/${q.id}/draft/`));
            } catch (e) {
              setNotice((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Comparar borrador de la fuente
        </button>
      )}
      {proposal && (
        <section aria-label="Propuesta de ayuda">
          <h3>Borrador editorial para revisión humana</h3>
          <p>
            Revise cada apartado y adáptelo a su servicio. Los ejemplos son
            ficticios. Usar la propuesta reemplaza el texto del editor; todavía
            debe guardarlo y solicitar revisión independiente.
          </p>
          {Object.entries(HELP).map(([key, label]) => (
            <details key={key}>
              <summary>{label}: comparar</summary>
              <strong>Texto actual del editor</strong>
              <pre>{content[key] || "Sin contenido"}</pre>
              <strong>Propuesta</strong>
              <pre>{proposal.content[key]}</pre>
            </details>
          ))}
          <h4>Referencias comprobadas</h4>
          {proposal.references.map((r) => (
            <details key={r.id}>
              <summary>{r.locator}</summary>
              <pre>{r.text}</pre>
            </details>
          ))}
          <button
            disabled={busy}
            onClick={() => {
              setContent({ ...proposal.content });
              setProposalDigest(proposal.digest);
              setDirty(true);
              setProposal(undefined);
            }}
          >
            Usar propuesta en el editor
          </button>
          <button onClick={() => setProposal(undefined)}>
            Cerrar comparación
          </button>
        </section>
      )}
      <details open={!latest}>
        <summary>Editar ficha de ayuda</summary>
        <p>
          Describa la pregunta concreta y su servicio. Los ejemplos deben estar
          identificados como ficticios. Una ficha completa necesita revisión
          humana antes de publicarse.
        </p>
        {Object.entries(HELP).map(([key, label]) => (
          <div key={key}>
            <label htmlFor={`help-${q.id}-${key}`}>{label}</label>
            <textarea
              id={`help-${q.id}-${key}`}
              value={content[key] ?? ""}
              maxLength={5000}
              readOnly={!q.can_edit}
              onChange={(e) => {
                setContent({ ...content, [key]: e.target.value });
                setDirty(true);
              }}
            />
          </div>
        ))}
        {q.can_edit && (
          <button
            disabled={busy}
            onClick={() =>
              mutate("help", {
                version: q.etag,
                content,
                proposal_digest: proposalDigest,
              })
            }
          >
            Guardar borrador de ayuda
          </button>
        )}
        <small>
          {complete
            ? "Diez apartados completos; falta confirmar su suficiencia."
            : "Puede guardar una ficha incompleta y retomarla."}
        </small>
      </details>
      <p role="status" aria-live="polite">
        {notice}
      </p>
      {q.can_review && latest && (
        <section className="help">
          <h3>Revisión y publicación</h3>
          {latest.author_name === user ? (
            <p>Otra persona debe revisar esta versión.</p>
          ) : !latest.review ? (
            <>
              <label htmlFor={"help-reason-" + q.id}>
                Fundamento de la revisión
              </label>
              <textarea
                id={"help-reason-" + q.id}
                value={reason}
                maxLength={5000}
                onChange={(e) => setReason(e.target.value)}
              />
              <button
                disabled={busy || dirty || !reason.trim()}
                onClick={() =>
                  mutate("review", {
                    version: q.etag,
                    decision: "approved",
                    rationale: reason,
                  })
                }
              >
                Aprobar ayuda
              </button>
              <button
                disabled={busy || dirty || !reason.trim()}
                onClick={() =>
                  mutate("review", {
                    version: q.etag,
                    decision: "returned",
                    rationale: reason,
                  })
                }
              >
                Devolver ayuda
              </button>
            </>
          ) : (
            <p>
              {latest.review.reviewer}: {latest.review.rationale}
            </p>
          )}
          {latest.review?.decision === "approved" &&
            q.published_help !== latest.id && (
              <>
                <p>
                  Publicar un cambio de ayuda conserva las respuestas y retira
                  su validación vigente para volver a revisarlas.
                </p>
                <button
                  disabled={busy || dirty}
                  onClick={() => mutate("publish", { version: q.etag })}
                >
                  Publicar pregunta
                </button>
              </>
            )}
        </section>
      )}
      <details>
        <summary>Historial de ayudas y revisiones</summary>
        {q.revisions.map((r) => (
          <details key={r.id}>
            <summary>
              Versión {r.number} · {r.author_name}
              {r.id === q.published_help ? " · Publicada" : ""}
            </summary>
            {Object.entries(r.content).map(([k, v]) => (
              <div key={k}>
                <strong>{HELP[k] ?? k}</strong>
                <pre>{v}</pre>
              </div>
            ))}
            <p>
              Origen:{" "}
              {r.origin === "manual"
                ? "Edición manual"
                : r.origin === "source_draft_edited"
                  ? "Propuesta adaptada"
                  : "Borrador de la fuente"}
            </p>
            {r.sources.map((source) => (
              <details key={source.id}>
                <summary>{source.locator}</summary>
                <pre>{source.text}</pre>
              </details>
            ))}
            {r.review && (
              <p>
                Revisión: {r.review.reviewer} · {r.review.rationale}
              </p>
            )}
          </details>
        ))}
      </details>
      {q.can_consult && <Consultations instanceId={q.id} />}
    </article>
  );
}
