"use client";
import {useState} from 'react';
import {api} from '../../lib/api';
export default function TimeCorrection({entry,onSaved}:{entry:{id:number;correction_version:number;effective_minutes:number};onSaved:()=>Promise<void>}){
 const [minutes,setMinutes]=useState(String(entry.effective_minutes)),[reason,setReason]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 return <form aria-label={`Corregir registro ${entry.id}`} onSubmit={async e=>{
  e.preventDefault();setBusy(true);setNotice('');
  try{await api(`tracking/time/${entry.id}/correct/`,'POST',{version:entry.correction_version,minutes:Number(minutes),rationale:reason});await onSaved();}
  catch(error){setNotice((error as Error).message);}finally{setBusy(false);}
 }}><p>El original se conserva. Use cero para anular sus minutos. Para cambiar fecha o tarea, anule y registre una entrada nueva.</p><label>Minutos corregidos<input type="number" min="0" max="1440" required disabled={busy} value={minutes} onChange={e=>setMinutes(e.target.value)}/></label><label>Motivo del ajuste<textarea required maxLength={2000} disabled={busy} value={reason} onChange={e=>setReason(e.target.value)}/></label><button disabled={busy||!reason.trim()||Number(minutes)===entry.effective_minutes}>Guardar corrección de horas</button>{notice&&<p role="status">{notice}</p>}</form>;
}
