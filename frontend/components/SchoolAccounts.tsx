"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import InstitutionalLogo from "./InstitutionalLogo";
import { api } from "../lib/api";
import "./school-accounts.css";
type Account = {id:number;username:string;first_name:string;last_name:string;email:string;is_active:boolean;version:string;can_manage:boolean;can_edit_name:boolean;restriction:string};
type Page = {count:number;next:string|null;previous:string|null;results:Account[]};
type Mode="name"|"view"|"edit"|"deactivate"|"reactivate"|"create";
const titles:Record<Mode,string>={name:"Corregir nombre",view:"Detalle de cuenta",edit:"Editar cuenta",deactivate:"Dar de baja",reactivate:"Reactivar cuenta",create:"Crear cuenta"};
const fullName=(u:Account)=>`${u.first_name} ${u.last_name}`.trim()||u.username;
export default function SchoolAccounts({school,institution,refreshToken,onChanged}:{school:number;institution:number;refreshToken:number;onChanged:()=>Promise<void>}) {
 const [open,setOpen]=useState(true),[query,setQuery]=useState(""),[search,setSearch]=useState(""),[state,setState]=useState("all"),[page,setPage]=useState(1),[tick,setTick]=useState(0);
 const [rows,setRows]=useState<Page>(),[loading,setLoading]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(""),[message,setMessage]=useState("");
 const [selected,setSelected]=useState<Account>(),[mode,setMode]=useState<Mode>("view"),[modal,setModal]=useState(false),[dirty,setDirty]=useState(false),[discard,setDiscard]=useState(false);
 const detailRevision=useRef(0),dialog=useRef<HTMLDialogElement>(null),trigger=useRef<HTMLElement|null>(null);
 useEffect(()=>()=>{detailRevision.current++},[]);
 useEffect(()=>{if(!modal)return;const d=dialog.current!;d.showModal();const prior=document.body.style.overflow;document.body.style.overflow="hidden";return()=>{d.close();document.body.style.overflow=prior;trigger.current?.focus();};},[modal]);
 useEffect(()=>{if(!open)return;let active=true;setLoading(true);
  api<Page>(`schools/${school}/accounts/?page=${page}&q=${encodeURIComponent(search)}&state=${state}`).then(v=>{if(active)setRows(v)}).catch(e=>{if(active){setRows(undefined);setError(String(e))}}).finally(()=>{if(active)setLoading(false)});
  return()=>{active=false};
 },[open,school,search,state,page,tick,refreshToken]);
 function launch(next:Mode){trigger.current=document.activeElement as HTMLElement;setSelected(undefined);setMode(next);setError("");setMessage("");setDirty(false);setDiscard(false);setModal(true);}
 function close(force=false){if(busy)return;if(dirty&&!force){setDiscard(true);return;}detailRevision.current++;setModal(false);setSelected(undefined);setError("");setDirty(false);setDiscard(false);}
 async function inspect(id:number,next:Mode){launch(next);const rev=++detailRevision.current;setBusy(true);
  try{const value=await api<Account>(`schools/${school}/accounts/${id}/`);if(rev===detailRevision.current)setSelected(value)}catch(e){if(rev===detailRevision.current)setError(String(e))}finally{if(rev===detailRevision.current)setBusy(false)}
 }
 async function save(e:FormEvent<HTMLFormElement>){e.preventDefault();if(mode!=="create"&&!selected)return;setBusy(true);setError("");setMessage("");const f=new FormData(e.currentTarget);
  try{
   if(mode==="create"){
    await api(`schools/${school}/users/`,"POST",{institution,username:f.get('username'),first_name:f.get('first_name'),last_name:f.get('last_name'),password:f.get('password')});
    setModal(false);setSelected(undefined);setOpen(true);setSearch("");setQuery("");setState("all");
   }else if(selected){
    const payload=mode==="name"?{first_name:f.get('first_name'),last_name:f.get('last_name'),version:selected.version,rationale:f.get('rationale')}:mode==="edit"?{username:f.get('username'),first_name:f.get('first_name'),last_name:f.get('last_name'),email:f.get('email'),version:selected.version,rationale:f.get('rationale')}:{version:selected.version,rationale:f.get('rationale')};
    const value=await api<Account>(`schools/${school}/accounts/${selected.id}/${mode==="name"?"name/":mode==="reactivate"?"reactivate/":""}`,(mode==="edit"||mode==="name")?"PATCH":mode==="deactivate"?"DELETE":"POST",payload);
    setSelected(value);setMode('view');
   }
   setDirty(false);setDiscard(false);setMessage(mode==="create"?'Cuenta creada. Ya puedes asignarle su función o registrarla como alumno.':'Cambio guardado. El historial se conserva.');setPage(1);setTick(n=>n+1);
   try{await onChanged();}catch{setMessage('Cuenta guardada. Recarga la página para actualizar los demás formularios.');}
  }catch(e){setError(String(e))}finally{setBusy(false)}
 }
 return <section className="panel accounts" aria-label="Cuentas registradas">
  <header className="accounts-header"><div><span className="accounts-eyebrow">DIRECTORIO DE LA ESCUELA</span><h3>Alumnos y colaboradores</h3><p>Consulta sus datos y administra el acceso desde un solo lugar.</p></div><button className="accounts-primary" onClick={()=>launch('create')}>＋ Crear cuenta</button></header>
  <div className="accounts-toolbar"><button className="accounts-link" type="button" aria-expanded={open} onClick={()=>setOpen(!open)}>{open?'Ocultar tabla de registrados':'Abrir tabla de registrados'}</button><span>Las bajas conservan el historial</span></div>
  {!modal&&error&&<p role="alert" className="accounts-error">{error}</p>}{!modal&&message&&<p role="status" className="accounts-success">{message}</p>}
  {open&&<>
   <form className="accounts-filters" onSubmit={e=>{e.preventDefault();setError('');setSearch(query.trim());setPage(1);setTick(n=>n+1)}}>
    <label className="accounts-search">Buscar por nombre, usuario o correo<input value={query} maxLength={150} onChange={e=>setQuery(e.target.value)} type="search" placeholder="Escribe un nombre o correo…" /></label>
    <label>Estado<select aria-label="Estado de cuentas" value={state} onChange={e=>{setState(e.target.value);setPage(1)}}><option value="all">Todos</option><option value="active">Activos</option><option value="inactive">Dados de baja</option></select></label>
    <button disabled={busy}>Buscar</button><button className="accounts-secondary" type="button" disabled={busy} onClick={()=>{setQuery('');setSearch('');setState('all');setPage(1);setTick(n=>n+1)}}>Limpiar búsqueda</button>
   </form>
   <div className="accounts-results" role="status">{loading?'Cargando cuentas…':rows?`${rows.count} cuentas encontradas`:''}</div>
   {rows&&<><div className="accounts-scroll" aria-busy={loading}><table><thead><tr><th>Persona</th><th>Contacto y acceso</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>
   {rows.results.map(u=><tr key={u.id}><td><div className="accounts-person"><span className="accounts-avatar" aria-hidden="true">{fullName(u).slice(0,1).toUpperCase()}</span><div><strong>{fullName(u)}</strong>{!u.can_manage&&<small className="accounts-protected">Gestión institucional</small>}</div></div></td><td><span>{u.email||'Correo sin registrar'}</span><small>Usuario: {u.username}</small></td><td><span className={`accounts-badge ${u.is_active?'active':'inactive'}`}>{u.is_active?'Activo':'Baja'}</span></td><td><div className="accounts-actions"><button className="accounts-secondary" disabled={busy||loading} type="button" onClick={()=>inspect(u.id,'view')}>Ver</button>{!u.can_manage&&u.can_edit_name&&<button className="accounts-secondary" disabled={busy||loading} onClick={()=>inspect(u.id,'name')}>Corregir nombre</button>}{u.can_manage&&<><button className="accounts-secondary" disabled={busy||loading} type="button" onClick={()=>inspect(u.id,'edit')}>Editar</button><button className={u.is_active?'accounts-danger-link':'accounts-link'} disabled={busy||loading} type="button" onClick={()=>inspect(u.id,u.is_active?'deactivate':'reactivate')}>{u.is_active?'Dar de baja':'Reactivar'}</button></>}</div></td></tr>)}
   {!rows.results.length&&<tr><td colSpan={4} className="accounts-empty"><strong>No encontramos cuentas</strong><p>Prueba otro nombre o limpia los filtros. También puedes crear una cuenta nueva.</p></td></tr>}
   </tbody></table></div><footer className="accounts-pagination"><span>Página {page} de {Math.max(1,Math.ceil(rows.count/50))}</span><div><button className="accounts-secondary" type="button" disabled={busy||loading||!rows.previous} onClick={()=>setPage(p=>p-1)}>Anterior</button><button className="accounts-secondary" type="button" disabled={busy||loading||!rows.next} onClick={()=>setPage(p=>p+1)}>Siguiente</button></div></footer></>}
  </>}
  {modal&&<dialog ref={dialog} className="accounts-modal" aria-labelledby="account-modal-title" onCancel={e=>{e.preventDefault();close();}}>
   <header className="accounts-modal-header"><div className="accounts-modal-brand"><InstitutionalLogo size="compact"/><div><span className="accounts-eyebrow">CUENTA DE LA ESCUELA</span><h2 id="account-modal-title">{titles[mode]}</h2></div></div><button className="accounts-close" autoFocus={mode==='view'} aria-label="Cerrar ventana" disabled={busy} onClick={()=>close()}>×</button></header>
   <div className="accounts-modal-body">
   {error&&<p role="alert" className="accounts-error">{error}</p>}{message&&<p role="status" className="accounts-success">{message}</p>}
   {busy&&!selected&&mode!=="create"&&<p role="status">Cargando cuenta…</p>}
   {discard&&<div className="accounts-discard" role="alert"><strong>Tienes cambios sin guardar</strong><p>¿Quieres descartarlos y cerrar?</p><button className="accounts-secondary" onClick={()=>setDiscard(false)}>Seguir editando</button><button className="accounts-danger" onClick={()=>close(true)}>Descartar cambios</button></div>}
   {selected&&mode==='view'?<section aria-label="Detalle de cuenta"><div className="accounts-profile"><span className="accounts-avatar" aria-hidden="true">{fullName(selected).slice(0,1).toUpperCase()}</span><div><h3>{fullName(selected)}</h3><span className={`accounts-badge ${selected.is_active?'active':'inactive'}`}>Estado: {selected.is_active?'Activo':'Baja'}</span></div></div><dl><dt>Usuario</dt><dd>{selected.username}</dd><dt>Correo</dt><dd>{selected.email||'Sin registrar'}</dd></dl>{selected.restriction&&<p className="accounts-notice">{selected.restriction}</p>}<footer className="accounts-modal-footer"><button className="accounts-secondary" onClick={()=>close()}>Cerrar detalle</button>{!selected.can_manage&&selected.can_edit_name&&<button onClick={()=>{setMode('name');setMessage('')}}>Corregir nombre</button>}{selected.can_manage&&<button onClick={()=>{setMode('edit');setMessage('')}}>Editar cuenta</button>}</footer></section>:(mode==='create'||selected)&&<form key={`${selected?.id}-${selected?.version}-${mode}`} id={mode==='create'?'registro-cuenta':'editar-cuenta'} onSubmit={save} onChange={()=>setDirty(true)}><fieldset disabled={busy}>
    {mode==='name'||mode==='edit'||mode==='create'?<><div className="accounts-form-grid"><label>Nombre<input name="first_name" autoFocus maxLength={150} defaultValue={selected?.first_name||''} required autoComplete="off" /></label><label>Apellidos<input name="last_name" defaultValue={selected?.last_name||''} maxLength={150} autoComplete="off" /></label></div>{mode==='name'?<p className="accounts-notice">Sólo se corregirán nombre y apellidos. El usuario, correo, contraseña y permisos se mantienen.</p>:<><label>Usuario<input aria-label="Usuario" name="username" defaultValue={selected?.username||''} maxLength={150} required autoComplete="off" /><small>Se utilizará para ingresar a la aplicación.</small></label>{mode==='edit'?<label>Correo<input name="email" type="email" defaultValue={selected?.email||''} maxLength={254}/></label>:<><label>Contraseña inicial<input name="password" type="password" minLength={12} maxLength={256} autoComplete="new-password" required/><small>Al menos 12 caracteres.</small></label><p className="accounts-notice">Se vinculará sólo a esta escuela. Después podrás registrar al alumno o asignar su función.</p></>}</>}</>:<><h3>{selected&&fullName(selected)}</h3><p className="accounts-notice">{mode==='deactivate'?'La baja bloqueará el acceso y cerrará sus sesiones. Su cuenta, asignaciones y prácticas se conservarán.':'Podrá ingresar nuevamente con sus credenciales y permisos vigentes. Revisa las asignaciones conservadas.'}</p></>}
    {mode!=='create'&&<label>Motivo del cambio<textarea name="rationale" minLength={5} maxLength={2000} rows={3} required placeholder="Explica brevemente el motivo para conservarlo en el historial."/></label>}
    <footer className="accounts-modal-footer"><button className="accounts-secondary" type="button" onClick={()=>close()}>Cancelar</button><button className={mode==='deactivate'?'accounts-danger':'accounts-primary'} disabled={busy||(mode!=='create'&&!(mode==='name'?selected?.can_edit_name:selected?.can_manage))}>{busy?'Guardando…':mode==='create'?'Crear cuenta':(mode==='edit'||mode==='name')?'Guardar cambios':mode==='deactivate'?'Confirmar baja':'Confirmar reactivación'}</button></footer>
   </fieldset></form>}
   </div>
  </dialog>}
 </section>
}
