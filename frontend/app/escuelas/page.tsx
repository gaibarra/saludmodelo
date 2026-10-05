"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import SchoolAccounts from "../../components/SchoolAccounts";
import InstitutionalDirectory, { PublishedService } from "../../components/InstitutionalDirectory";
import { api, listApi, setCsrf } from "../../lib/api";
import "../academico/academic.css";
type School = {
  id: number;
  institution: number;
  name: string;
  code: string;
  can_manage: boolean;
};
type Board = School & {
  published_services?: PublishedService[];
  cycles: number;
  students: number;
  reports: number;
  states: { status: string; participations: number; minutes: number }[];
};
type Management = {
  users: { id: number; name: string }[];
  sites: { id: number; name: string }[];
  services: { id: number; name: string; confirmed: boolean; etag: number }[];
};
const stateNames: Record<string, string> = {
  submitted: "Por revisar",
  returned: "Por corregir",
  validated: "Validadas",
  void: "Anuladas",
};
export default function SchoolsPage() {
  const [schools, setSchools] = useState<School[]>([]),
    [board, setBoard] = useState<Board>(),
    [management, setManagement] = useState<Management>();
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const revision = useRef(0);
  const selectedSchool = useRef<number|undefined>(undefined);
  const [accountRevision,setAccountRevision]=useState(0);
  async function open(id: number) {
    const token = ++revision.current;
    selectedSchool.current=id;
    setBoard(undefined);
    setManagement(undefined);
    setError("");
    setMessage("");
    try {
      const b = await api<Board>(`schools/${id}/`);
      const m = b.can_manage ? await api<Management>(`schools/${id}/management/`) : undefined;
      if (token !== revision.current) return;
      setBoard(b);
      setManagement(m);
    } catch (e) {
      if (token === revision.current) setError(String(e));
    }
  }
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const session = await api<{ csrf: string; authenticated: boolean }>(
          "session/",
        );
        if (!alive) return;
        setCsrf(session.csrf);
        if (!session.authenticated)
          throw Error("Ingresa y completa MFA para consultar tus escuelas.");
        const rows = await listApi<School>("schools/");
        if (!alive) return;
        setSchools(rows);
        if (rows.length) {
          const requested = Number(new URLSearchParams(window.location.search).get("school"));
          await open(rows.find(s => s.id === requested)?.id ?? rows[0].id);
        }
      } catch (e) {
        if (alive) setError(String(e));
      }
    })();
    return () => {
      alive = false;
      revision.current++;
    };
  }, []);
  async function save(e: FormEvent<HTMLFormElement>, kind: string) {
    e.preventDefault();
    if (!board) return;
    const form = e.currentTarget,
      f = new FormData(form);
    const v = Object.fromEntries(f.entries());
    const owner = board.id;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      let path = `schools/${owner}/${kind}/`,
        payload: unknown = v;
      if (kind === "users") payload = { ...v, institution: board.institution };
      if (kind === "services") payload = { ...v, site: Number(v.site) };
      if (kind === "assignment") {
        path = "administration/assignments/";
        payload = { ...v, user: Number(v.user), service: Number(v.service) };
      }
      await api(path, "POST", payload);
      if(kind === "users") setAccountRevision(n=>n+1);
      form.reset();
      await open(owner);
      setMessage("Cambio guardado en la escuela seleccionada.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function confirmService(id: number, version: number) {
    if (!board) return;
    setBusy(true);
    setError("");
    try {
      await api(`administration/services/${id}/confirm/`, "POST", {
        version,
        rationale: "Servicio confirmado por su dirección escolar",
      });
      await open(board.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <header className="topbar">
        <Link href="/personal">Salud Modelo</Link>
        <h1>Escuelas</h1>
        <Link href="/caja">Caja por servicio</Link>
        <Link href="/academico">Prácticas académicas</Link>
      </header>
      <main
        className="academic-shell"
        style={{ maxWidth: 1200, margin: "auto", padding: 24 }}
      >
        <p>
          Cada escuela tiene su propia dirección y administración. Salud y Odontología
          no tienen acceso a la información interna de la otra escuela.
        </p>
        <nav
          aria-label="Escuelas autorizadas"
          style={{ display: "flex", gap: 12, flexWrap: "wrap" }}
        >
          {schools.map((s) => (
            <button
              key={s.id}
              disabled={busy}
              aria-pressed={board?.id === s.id}
              onClick={() => open(s.id)}
            >
              {s.name}
              {s.can_manage ? "" : " · Sólo consulta académica"}
            </button>
          ))}
        </nav>
        {error && <p role="alert">{error}</p>}
        {message && <p role="status">{message}</p>}
        {!schools.length && !error && (
          <p>No hay escuelas asignadas a tu cuenta.</p>
        )}
        {board && (
          <section key={board.id}>
            <h2>{board.name}</h2>
            <p>
              {board.can_manage
                ? "Administración de esta escuela"
                : "Consulta académica autorizada · Sin permiso para modificar registros"}
            </p>
            <div className="academic-two">
              <article className="panel">
                <h3>Alumnos y ciclos</h3>
                <p>
                  {board.students} alumnos · {board.cycles} ciclos ·{" "}
                  {board.reports} informes conservados
                </p>
              </article>
              <article className="panel">
                <h3>Prácticas</h3>
                {board.states.length ? (
                  board.states.map((s) => (
                    <p key={s.status}>
                      {stateNames[s.status]}: {s.participations} participaciones
                      · {(s.minutes / 60).toFixed(1)} horas
                    </p>
                  ))
                ) : (
                  <p>Sin prácticas registradas.</p>
                )}
              </article>
            </div>
            <p>
              <Link href={`/academico?school=${board.id}`}>
                Consultar prácticas de esta escuela
              </Link>{" "}
              ·{" "}
              <Link href="/academico/evaluaciones">
                Competencias e informes por ciclo
              </Link>
            </p>
            {board.published_services && board.published_services.length > 0 && (
              <details className="school-directory-disclosure">
                <summary>Consultar servicios publicados ({board.published_services.length})</summary>
                <InstitutionalDirectory items={board.published_services} />
              </details>
            )}
            {board.can_manage && management && (
              <>
                <h2>Administración de {board.name}</h2>
                <SchoolAccounts key={board.id} school={board.id} institution={board.institution} refreshToken={accountRevision} onChanged={async()=>{const m=await api<Management>(`schools/${board.id}/management/`);if(selectedSchool.current===board.id)setManagement(m)}} />
                <div className="academic-two">
                  <form className="panel" onSubmit={(e) => save(e, "services")}>
                    <h3>Registrar servicio</h3>
                    <label>
                      Nombre del servicio
                      <input name="name" required maxLength={160} />
                    </label>
                    <label>
                      Sede
                      <select aria-label="Sede" name="site" required>
                        <option value="">Seleccionar</option>
                        {management.sites.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button disabled={busy}>Registrar servicio</button>
                    <ul>
                      {management.services.map((s) => (
                        <li key={s.id}>
                          {s.name} ·{" "}
                          {s.confirmed ? (
                            "Confirmado"
                          ) : (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => confirmService(s.id, s.etag)}
                            >
                              Confirmar
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </form>
                  <form
                    className="panel"
                    onSubmit={(e) => save(e, "assignment")}
                  >
                    <h3>Asignar función de colaborador</h3>
                    <label>
                      Persona
                      <select aria-label="Persona" name="user" required>
                        <option value="">Seleccionar</option>
                        {management.users.map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Servicio
                      <select aria-label="Servicio" name="service" required>
                        <option value="">Seleccionar</option>
                        {management.services.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Función
                      <select aria-label="Función" name="role">
                        <option value="clinical">Supervisor clínico</option>
                        <option value="manager">Responsable de servicio</option>
                        <option value="contributor">Colaborador</option>
                        <option value="coordinator">Coordinador</option>
                        <option value="compliance">Revisor</option>
                      </select>
                    </label>
                    <label>
                      Desde
                      <input type="date" name="starts" required />
                    </label>
                    <label>
                      Hasta
                      <input type="date" name="ends" required />
                    </label>
                    <label>
                      Justificación
                      <input name="rationale" required />
                    </label>
                    <button disabled={busy}>Asignar función</button>
                    <p>
                      <Link href="/administracion">
                        Consultar o revocar nombramientos
                      </Link>
                    </p>
                  </form>
                </div>
              </>
            )}
          </section>
        )}
      </main>
    </>
  );
}
