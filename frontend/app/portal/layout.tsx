import Link from "next/link";
import InstitutionalLogo from "../../components/InstitutionalLogo";
import { services } from "./data";
import "./portal.css";
export default function PortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="salud-portal">
      <header className="portal-header">
        <Link href="/" className="portal-brand">
          <InstitutionalLogo />
          <span>
            <strong>Salud y Odontología</strong>
            <small>Universidad Modelo</small>
          </span>
        </Link>
        <nav aria-label="Portal público">
          <Link href="/">Inicio</Link>
          <Link href="/#servicios">Servicios</Link>
          <Link href="/portal/directorio">Directorio</Link>
          <Link href="/portal/cuenta">Mi cuenta</Link>
          <Link href="/personal" className="portal-staff-entry">Acceso del personal</Link>
        </nav>
      </header>
      <nav className="portal-tabs" aria-label="Servicios de salud">
        {services.map((s) => (
          <Link key={s.slug} href={`/portal/servicios/${s.slug}`}>
            {s.name}
          </Link>
        ))}
      </nav>
      {children}
      <footer className="portal-footer">
        <div className="institutional-footer-brand">
          <InstitutionalLogo size="compact" />
          <div><strong>Escuelas de Salud y Odontología · Universidad Modelo</strong>
          <p>
            Explora nuestros servicios y consulta el estado de tus solicitudes
            desde tu cuenta.
          </p></div>
        </div>
        <div>
          <Link href="/portal/directorio">Directorio</Link>
          <Link href="/portal/cuenta">Mi cuenta</Link>
          <Link href="/personal">Acceso del personal</Link>
        </div>
      </footer>
    </div>
  );
}
