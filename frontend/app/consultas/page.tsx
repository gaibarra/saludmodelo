"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Consultations from "../../components/Consultations";
import { api, setCsrf } from "../../lib/api";
export default function ConsultationsPage() {
  const [user, setUser] = useState(""),
    [notice, setNotice] = useState("Cargando sesión…");
  useEffect(() => {
    api<{ authenticated: boolean; username: string; csrf: string }>("session/")
      .then((s) => {
        setCsrf(s.csrf);
        setUser(s.authenticated ? s.username : "");
        setNotice(
          s.authenticated ? "" : "Inicie sesión para consultar su bandeja.",
        );
      })
      .catch((e) => setNotice(e.message));
  }, []);
  return (
    <main>
      <nav>
        <Link href="/personal">Mi trabajo</Link> ·{" "}
        <Link href="/administracion">Administración y cuestionarios</Link>
      </nav>
      <h1>Mis consultas</h1>
      <p role="status">{notice}</p>
      {user && (
        <>
          <p>{user}</p>
          <Consultations />
        </>
      )}
    </main>
  );
}
