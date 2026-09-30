"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import ExceptionalRecovery from './ExceptionalRecovery';
import MFA, { Session } from "../../components/MFA";
import { api, setCsrf } from "../../lib/api";
export default function Security() {
  const [session, setSession] = useState<Session>();
  const [error, setError] = useState("");
  useEffect(() => {
    api<Session>("session/")
      .then((s) => {
        setCsrf(s.csrf);
        setSession(s);
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <main>
      <h1>Seguridad de la cuenta</h1>
      {error && <p role="alert">{error}</p>}
      {session?.authenticated && <ExceptionalRecovery username={session.username}/>}
      {session?.username ? (
        <MFA
          session={session}
          onComplete={() => {
            window.location.href = "/";
          }}
        />
      ) : (
        <p>
          <Link href="/personal">Ingrese con su cuenta para continuar.</Link>
        </p>
      )}
    </main>
  );
}
