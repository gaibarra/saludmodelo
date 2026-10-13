"use client";
import {FormEvent,useState} from 'react';
import {api,setCsrf} from '../lib/api';
export default function PasswordChange(){
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
 async function submit(e:FormEvent<HTMLFormElement>){
  e.preventDefault();const form=e.currentTarget;const f=new FormData(form);setBusy(true);setError('');setMessage('');
  try{const result=await api<{detail:string;csrf:string}>('security/password/','POST',{current_password:f.get('current_password'),new_password:f.get('new_password'),confirm_password:f.get('confirm_password')});setCsrf(result.csrf);form.reset();setMessage(result.detail)}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 return <section aria-labelledby="password-title" style={{maxWidth:560,margin:'24px 0'}}><h2 id="password-title">Cambiar contraseña</h2><p>Escribe tu contraseña actual y elige una nueva de al menos 12 caracteres. Evita contraseñas comunes o relacionadas con tu nombre.</p>{error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}<form onSubmit={submit}><fieldset disabled={busy} style={{display:'grid',gap:12}}><label>Contraseña actual<input name="current_password" type="password" autoComplete="current-password" required maxLength={256}/></label><label>Nueva contraseña<input name="new_password" type="password" autoComplete="new-password" required minLength={12} maxLength={128}/></label><label>Confirmar nueva contraseña<input name="confirm_password" type="password" autoComplete="new-password" required minLength={12} maxLength={128}/></label><button type="submit">{busy?'Guardando…':'Actualizar contraseña'}</button></fieldset></form></section>
}
