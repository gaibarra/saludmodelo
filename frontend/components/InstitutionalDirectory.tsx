"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../lib/api";
import "../app/portal/directory.css";
export type PublishedService = {
  code: string; name: string; area: string; additional_areas?: string[]; additional_sources?: {label:string;url:string;checked_on:string}[]; school: number | null; school_name: string;
  description: string; audience: "general" | "university"; schedule: string[];
  contacts: { label: string; href: string }[]; notes: string; location_note: string;
  source_url: string; source_checked_on: string;
};
export default function InstitutionalDirectory({ area, items, compact = false }: { area?: string; items?: PublishedService[]; compact?: boolean }) {
  const [records,setRecords]=useState<PublishedService[]>(items??[]),[loading,setLoading]=useState(items===undefined),[error,setError]=useState("");
  useEffect(()=>{
    if(items!==undefined){setRecords(items);setLoading(false);return;}
    let active=true;
    api<{published_services?:PublishedService[]}>("public/services/").then(r=>{if(active)setRecords(r.published_services??[]);})
      .catch(()=>{if(active)setError("No pudimos cargar el directorio. Puedes consultar la fuente institucional.");})
      .finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[items]);
  const selected=area===undefined?records:records.filter(r=>r.area===area || r.additional_areas?.includes(area));
  return <section className="institutional-directory" aria-label="Directorio institucional publicado">
    <div className="directory-heading"><span>INFORMACIÓN INSTITUCIONAL</span><h2>Servicios publicados por la Universidad</h2><p>Horarios y contactos del directorio oficial. Confirma disponibilidad antes de acudir.</p></div>
    {loading?<p role="status">Consultando servicios publicados…</p>:error?<p role="alert">{error} <a href="https://www.unimodelo.edu.mx/servicios" target="_blank" rel="noreferrer">Abrir directorio oficial</a></p>:selected.length===0?<p className="directory-empty">{"Aún no hay una ficha institucional incorporada para esta área."} <a href="https://www.unimodelo.edu.mx/servicios" target="_blank" rel="noreferrer">Consultar fuente oficial</a></p>:<div className={compact?"directory-grid compact":"directory-grid"}>{selected.map(row=><article className="directory-card" key={row.code} aria-label={row.name}>
      <span className="directory-audience">{row.audience==="university"?"Comunidad universitaria":"Público en general"}</span>
      <h3>{row.name}</h3><p>{row.description}</p>
      {!compact&&<><h4>Horario publicado</h4><ul>{row.schedule.map(line=><li key={line}>{line}</li>)}</ul><h4>Contacto</h4><ul>{row.contacts.map((c,i)=><li key={i}>{c.href?<a href={c.href} target={c.href.startsWith("https:")?"_blank":undefined} rel="noreferrer">{c.label}</a>:<span>{c.label}</span>}</li>)}</ul>{row.notes&&<p className="directory-note">{row.notes}</p>}<p className="directory-location">{row.location_note}</p></>}
      <div className="directory-source"><a href={row.source_url} target="_blank" rel="noreferrer">Fuente: Universidad Modelo ↗</a>{row.additional_sources?.map(source=><span key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.label} ↗</a><small>Verificado: {source.checked_on.split("-").reverse().join("/")}</small></span>)}<small>Consultado: {row.source_checked_on.split("-").reverse().join("/")}</small></div>
      {compact&&row.area&&<Link className="directory-more" href={`/portal/servicios/${row.area}`}>Ver horarios y contacto →</Link>}
      {compact&&!row.area&&<Link className="directory-more" href="/portal/directorio">Ver ficha institucional →</Link>}
    </article>)}</div>}
  </section>;
}
