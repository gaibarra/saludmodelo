import Link from "next/link";
import InstitutionalDirectory from "../../../../components/InstitutionalDirectory";
import { notFound } from "next/navigation";
import { services } from "../../data";
export function generateStaticParams() {
  return services.map((s) => ({ slug: s.slug }));
}
export default async function ServicePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const selected = services.find((s) => s.slug === slug);
  if (!selected) notFound();
  return (
    <main className="portal-main portal-service">
      <Link href="/portal#servicios" className="portal-back">
        ← Todos los servicios
      </Link>
      <span className="portal-eyebrow">SERVICIO DE SALUD</span>
      <h1>{selected.name}</h1>
      <p>
        {slug === "odontologia" ? "Escuela de Odontología" : "Escuela de Salud"}{" "}
        · Universidad Modelo
      </p>
      <p className="portal-lead">{selected.detail}</p>
      <InstitutionalDirectory area={slug} />
      <div className="portal-service-grid">
        <div className="portal-info-box">
          <h2>Solicitudes en este portal</h2>
          {process.env.NEXT_PUBLIC_DEMO_MODE === "1" && <p className="portal-alert">El portal está en demostración y todavía no recibe solicitudes reales. Para atención actual, utiliza los contactos institucionales publicados.</p>}
          <ol>
            <li>Crea una cuenta de paciente o ingresa con la tuya.</li>
            <li>Indica la sede y, si lo deseas, un día de preferencia.</li>
            <li>
              Consulta el estado en “Mi cuenta”. El servicio confirmará el
              horario si hay disponibilidad.
            </li>
          </ol>
          <Link
            className="portal-button"
            href={`/portal/cuenta?servicio=${slug}`}
          >
            Solicitar atención <span aria-hidden>→</span>
          </Link>
        </div>
        <div className="portal-aside">
          <h2>Antes de comenzar</h2>
          <p>
            Tu solicitud no equivale a una cita confirmada. Podrás retirarla
            mientras siga pendiente.
          </p>
          <p>
            No incluyas síntomas, diagnósticos ni documentos clínicos en esta
            etapa.
          </p>
        </div>
      </div>
      <section className="portal-other">
        <h2>También puedes explorar</h2>
        <div>
          {services
            .filter((s) => s.slug !== slug)
            .map((s) => (
              <Link key={s.slug} href={`/portal/servicios/${s.slug}`}>
                {s.name} <span aria-hidden>↗</span>
              </Link>
            ))}
        </div>
      </section>
    </main>
  );
}
