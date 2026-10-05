"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
import InstitutionalLogo from "./InstitutionalLogo";
export default function InstitutionalMasthead(){
 const path=usePathname();
 // Public and staff layouts already carry the same institutional mark.
 if(path==='/'||path==='/portal'||path.startsWith('/portal/')||path==='/personal'||path.startsWith('/personal/'))return null;
 return <div className="institutional-masthead"><Link href="/personal"><InstitutionalLogo size="compact"/><span><strong>Universidad Modelo</strong><small>Escuelas de Salud y Odontología</small></span></Link></div>;
}
