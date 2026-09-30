"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import SavedReports from "./SavedReports";
import ReportSchedule from "./ReportSchedule";
import ReportInbox from "./ReportInbox";
import WeeklyContent, { Report } from "./WeeklyContent";
import { api, listApi } from "../../lib/api";
export default function Reports() {
  const [services, setServices] = useState<
      { id: number; name: string; site_name: string }[]
    >([]),
    [service, setService] = useState(""),
    [start, setStart] = useState(""),
    [report, setReport] = useState<Report>(),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  useEffect(() => {
    listApi<{ id: number; name: string; site_name: string }>("services/")
      .then(setServices)
      .catch((e) => setNotice(e.message));
  }, []);
  const query = start ? `?start=${encodeURIComponent(start)}` : "";
  return (
    <main>
      <Link href="/personal">Volver a mi trabajo</Link>
      <h1>Informes semanales</h1>
      <ReportInbox />
      <p>
        Borrador local desde registros guardados. No se envía a destinatarios ni
        a proveedores de IA.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setReport(undefined);
          setNotice("");
          try {
            setReport(
              await api<Report>(`reports/services/${service}/weekly/${query}`),
            );
          } catch (error) {
            setNotice((error as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Servicio del informe
          <select
            disabled={busy}
            value={service}
            onChange={(e) => {
              setService(e.target.value);
              setReport(undefined);
            }}
            required
          >
            <option value="">Seleccione…</option>
            {services.map((s) => (
              <option value={s.id} key={s.id}>
                {s.name} · {s.site_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Inicio del período de siete días
          <input
            type="date"
            disabled={busy}
            value={start}
            onChange={(e) => {
              setStart(e.target.value);
              setReport(undefined);
            }}
          />
        </label>
        <p>Si no elige fecha, se toma el lunes de esta semana.</p>
        <button disabled={busy || !service}>Preparar borrador semanal</button>
      </form>
      <p role="status">{notice}</p>
      {service && <ReportSchedule key={`schedule-${service}`} service={service} />}
      {service && <SavedReports key={service} service={service} />}
      {report && (
        <WeeklyContent report={report} service={service} query={query} />
      )}
    </main>
  );
}
