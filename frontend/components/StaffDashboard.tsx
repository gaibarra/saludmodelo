"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, listApi } from "../lib/api";
import "../app/personal/dashboard.css";
import InstitutionalDirectory, { PublishedService } from "./InstitutionalDirectory";

type School = { id: number; name: string; code: string; can_manage: boolean };
type Board = School & { published_services?: PublishedService[]; students: number; cycles: number; reports: number; states: { status: string; participations: number; minutes: number }[] };
const shortcuts = [
  { href: "/caja", name: "Caja", detail: "Turnos, cobros en efectivo, arqueos y monitoreo por servicio.", icon: "05" },
  { href: "/academico", name: "Prácticas académicas", detail: "Alumnos, ciclos, supervisores y registro de participaciones.", icon: "01" },
  { href: "/academico/evaluaciones", name: "Evaluaciones e informes", detail: "Competencias, informes individuales y cierre del ciclo.", icon: "02" },
  { href: "/escuelas", name: "Escuelas", detail: "Consulta el avance y administra las escuelas autorizadas.", icon: "03" },
  { href: "/seguimiento", name: "Tareas y seguimiento", detail: "Actividades, responsables, fechas y avisos de tu servicio.", icon: "04" },
];
export default function StaffDashboard({ username }: { username: string }) {
  const [boards, setBoards] = useState<Board[]>([]);
  const [loading, setLoading] = useState(true), [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);setError("");
    (async () => {
      const rows = await listApi<School>("schools/");
      const data = await Promise.all(rows.map(s => api<Board>(`schools/${s.id}/`)));
      if(active) setBoards(data);
    })().catch(() => {if(active) setError("No pudimos cargar el resumen de las escuelas. Intenta de nuevo.");})
      .finally(() => {if(active) setLoading(false);});
    return () => {active=false;};
  }, [attempt]);
  const total = (key: "students" | "cycles" | "reports") => boards.reduce((n, s) => n+s[key],0);
  const count = (s: Board, status: string) => s.states.filter(v=>v.status===status).reduce((n,v)=>n+v.participations,0);
  const pending = boards.reduce((n,s)=>n+count(s,"submitted"),0);
  return <div className="academic-home">
    <aside className="home-sidebar">
      <span className="home-eyebrow">MI ESPACIO</span>
      <nav aria-label="Navegación principal">
        <Link href="/personal" aria-current="page">Panel académico</Link>
        <Link href="/academico">Alumnos y prácticas</Link>
        <Link href="/academico/evaluaciones">Evaluación y cierre</Link>
        <Link href="/escuelas">Mis escuelas</Link>
        <Link href="/seguimiento">Tareas y avisos</Link>
      </nav>
      <div className="home-sidebar-bottom"><span className="home-eyebrow">GESTIÓN DEL SERVICIO</span>
        <Link href="/personal/plan">Plan y cuestionarios</Link>
        <Link href="/solicitudes-servicio">Solicitudes de pacientes</Link>
        <Link href="/capacidad">Capacidad y ausencias</Link>
        <Link href="/decisiones">Decisiones</Link>
        <Link href="/seguridad">Seguridad de la cuenta</Link>
      </div>
    </aside>
    <div className="home-body">
      <section className="home-heading"><div><span className="home-eyebrow">FORMACIÓN Y SERVICIOS · UNIVERSIDAD MODELO</span><h1>Panel académico</h1><p>El avance de tus escuelas, desde cada práctica hasta el cierre del ciclo.</p></div><span className="home-account">{username}</span></section>
      {error ? <div role="alert" className="error">{error} <button onClick={()=>setAttempt(a=>a+1)}>Reintentar</button></div> : loading ? <p role="status">Cargando información académica…</p> : <>
        {boards.length > 0 && <section className="home-metrics" aria-label="Resumen académico autorizado">
          {[{name:"Alumnos registrados",value:total("students"),note:"En las escuelas visibles"},{name:"Ciclos registrados",value:total("cycles"),note:"Todos los ciclos disponibles"},{name:"Participaciones por revisar",value:pending,note:"Pendientes de supervisión"},{name:"Informes de ciclo",value:total("reports"),note:"Individuales y consolidados"}].map(m=><div key={m.name}><span>{m.name}</span><strong>{m.value}</strong><small>{m.note}</small></div>)}
        </section>}
        <section className="home-school-section"><div className="home-section-title"><h2>Tus escuelas</h2><p>Administración independiente y consulta según tus permisos.</p></div>
          <div className="home-schools">{boards.map(s=><article key={s.id} className="home-school-card" aria-label={s.name}>
            <div className="home-school-top"><span className="home-school-icon" aria-hidden>{s.code==="odontologia"?"✦":"✳"}</span><span className={s.can_manage?"home-access":"home-access readonly"}>{s.can_manage?"Administración":"Consulta académica"}</span></div>
            <h3>{s.name}</h3><p>{s.can_manage?"Gestiona la escuela y acompaña el avance de sus alumnos.":"Consulta las prácticas y los informes compartidos. Sin permiso para modificar registros."}</p>
            <dl><div><dt>Alumnos</dt><dd>{s.students}</dd></div><div><dt>Ciclos</dt><dd>{s.cycles}</dd></div><div><dt>Participaciones validadas</dt><dd>{count(s,"validated")}</dd></div></dl>
            {s.published_services && <p>Servicios publicados: {s.published_services.length}</p>}
            {s.cycles===0&&<p className="home-empty-note">Aún no hay ciclos registrados en esta escuela.</p>}
            <div className="home-school-actions"><Link className="home-primary" href={`/escuelas?school=${s.id}`}>{s.can_manage?"Abrir escuela":"Consultar escuela"} <span aria-hidden>→</span></Link><Link href={`/academico?school=${s.id}`}>Ver prácticas</Link></div>
          </article>)}</div>
          {boards.length===0&&<div className="home-empty"><h3>Tu espacio de trabajo</h3><p>Tu cuenta no tiene acceso a resúmenes de Dirección. Puedes consultar tus participaciones y actividades desde los accesos de abajo; cada módulo mostrará únicamente tu alcance autorizado.</p></div>}
        </section>
      </>}
      <section className="home-shortcuts"><div className="home-section-title"><h2>¿Qué necesitas hacer?</h2><p>Accede directamente al trabajo académico y operativo.</p></div><div className="home-shortcut-grid">{shortcuts.map(s=><Link href={s.href} key={s.href} aria-label={s.name}><span aria-hidden>{s.icon}</span><h3>{s.name}</h3><p>{s.detail}</p><b aria-hidden>↗</b></Link>)}</div></section>
      <InstitutionalDirectory compact />
      <section className="home-cycle-note"><span aria-hidden>↗</span><div><h2>Prepara el cierre desde el inicio del ciclo</h2><p>Registra alumnos y supervisores, valida las prácticas y completa las evaluaciones para reunir los informes de cada alumno y de la escuela.</p></div><Link href="/academico/evaluaciones">Revisar evaluación y cierre →</Link></section>
    </div>
  </div>;
}
