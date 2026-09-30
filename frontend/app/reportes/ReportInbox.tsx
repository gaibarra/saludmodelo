"use client";
import {useEffect,useState} from 'react';
import {api,setCsrf} from '../../lib/api';
import WeeklyContent,{Report} from './WeeklyContent';
type Delivery={id:number;report_id:number;service:string;period:string;availability:string;acknowledged_at:string|null;rationale:string};
type InboxPage={results:Delivery[];next_before:number|null};
type Saved={id:number;service_id:number;content:Report;content_hash:string;state:string;availability:string;disposition:{rationale:string}|null};
export default function ReportInbox(){
 const [rows,setRows]=useState<Delivery[]>([]),[next,setNext]=useState<number|null>(null),[selected,setSelected]=useState<{delivery:Delivery;report:Saved}>(),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 async function load(before?:number){
  const page=await api<InboxPage>(`reports/inbox/${before?`?before=${before}`:''}`);
  setRows(previous=>before?[...previous,...page.results.filter(row=>!previous.some(old=>old.id===row.id))]:page.results);setNext(page.next_before);
 }
 useEffect(()=>{
  let current=true;
  api<{csrf:string}>('session/').then(async session=>{
   if(!current)return;setCsrf(session.csrf);
   const page=await api<InboxPage>('reports/inbox/');
   if(current){setRows(page.results);setNext(page.next_before);}
  }).catch(e=>{if(current)setNotice(e.message);});
  return ()=>{current=false;};
 },[]);
 async function run(fn:()=>Promise<void>){setBusy(true);setNotice('');try{await fn();}catch(e){setNotice((e as Error).message);setSelected(undefined);setRows([]);setNext(null);}finally{setBusy(false);}}
 return <section aria-label="Bandeja de informes"><h2>Mis informes recibidos</h2><button disabled={busy} onClick={()=>void run(async()=>{setSelected(undefined);await load();})}>Actualizar bandeja</button><p role="status">{notice}</p>{rows.length?<ul>{rows.map(d=><li key={d.id}>{d.service} · Semana {d.period} · {d.availability==='retained'?'Conservado':d.availability==='withdrawn'?'Retirado':'Sustituido'} · {d.acknowledged_at?'Lectura confirmada':'Lectura pendiente'} <button disabled={busy} onClick={()=>void run(async()=>setSelected({delivery:d,report:await api<Saved>(`reports/saved/${d.report_id}/`)}))}>Leer informe recibido {d.report_id}</button></li>)}</ul>:<p>No hay informes recibidos con acceso vigente.</p>}{next!==null&&<button disabled={busy} onClick={()=>void run(()=>load(next))}>Cargar más informes recibidos</button>}{selected&&<article><h3>Informe recibido {selected.report.id}</h3><p>Motivo de distribución: {selected.delivery.rationale}</p>{selected.report.availability!=='retained'&&<p>Este informe fue retirado o sustituido: {selected.report.disposition?.rationale}. Se muestra como historial.</p>}<WeeklyContent report={selected.report.content} service={String(selected.report.service_id)} saved/>{!selected.delivery.acknowledged_at&&selected.report.availability==='retained'&&selected.report.state==='approved'&&<button disabled={busy} onClick={()=>void run(async()=>{await api(`reports/deliveries/${selected.delivery.id}/acknowledge/`,'POST',{content_hash:selected.report.content_hash});setSelected(undefined);await load();setNotice('Lectura confirmada para su cuenta. No modifica la aprobación del informe.');})}>Confirmar que leí este informe</button>}</article>}</section>;
}
