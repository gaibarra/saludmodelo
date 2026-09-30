"use client";
import {useEffect,useRef,useState} from 'react';
import {api} from '../../lib/api';
export type ReplacementReport={id:number;start:string;content_hash:string};
type Page={results:ReplacementReport[];next_before:number|null};
export default function ReportReplacementPicker({service,start,exclude,value,onChange,disabled,onBusyChange}:{service:string;start:string;exclude:number;value:number|null;onChange:(value:ReplacementReport|undefined)=>void;disabled:boolean;onBusyChange:(busy:boolean)=>void}){
 const [rows,setRows]=useState<ReplacementReport[]>([]),[next,setNext]=useState<number|null>(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const alive=useRef(true);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;onBusyChange(false);};},[onBusyChange]);
 async function load(before?:number){setBusy(true);onBusyChange(true);setNotice('');if(!before)onChange(undefined);try{const params=new URLSearchParams({start,state:'approved',retained_only:'true',exclude:String(exclude)});if(before)params.set('before',String(before));const data=await api<Page>(`reports/services/${service}/saved/?${params}`);if(!alive.current)return;setRows(old=>before?[...old,...data.results.filter(r=>!old.some(p=>p.id===r.id))]:data.results);setNext(data.next_before);if(!data.results.length&&!before)setNotice('No hay sustitutos aprobados disponibles para este período.');}catch(e){if(!alive.current)return;setNotice((e as Error).message);setRows([]);setNext(null);onChange(undefined);}finally{if(alive.current){setBusy(false);onBusyChange(false);}}}
 return <div aria-label="Búsqueda de informe sustituto"><p>Consulte los informes aprobados del mismo período. Puede cargar versiones anteriores aunque no estén en la página principal.</p><button type="button" disabled={disabled||busy} onClick={()=>void load()}>Buscar sustitutos aprobados</button><label>Informe aprobado sustituto<select disabled={disabled||busy} value={value??''} onChange={e=>onChange(rows.find(r=>String(r.id)===e.target.value))}><option value="">Retirar sin sustituto</option>{rows.map(r=><option key={r.id} value={r.id}>Informe {r.id} · {r.start}</option>)}</select></label>{next!==null&&<button type="button" disabled={disabled||busy} onClick={()=>void load(next)}>Cargar más sustitutos aprobados</button>}{notice&&<p role="status">{notice}</p>}</div>;
}
