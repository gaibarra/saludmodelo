"use client";
import { useState } from "react";
import AIRelease, { type Release } from "./AIRelease";
import { api } from "../lib/api";
type Document = {
  id: string;
  instance: number;
  ai_releases: Release[];
  name: string;
  sha256: string;
  state: string;
  etag: number;
  answer_version: number;
  current_answer_version: number;
  is_current: boolean;
  expired: boolean;
  format: string;
  security_state: string;
  scan_required: boolean;
  requires_ocr_check: boolean;
  can_review: boolean;
  can_retry: boolean;
  extraction: { state: string; error: string; count: number };
  reviews: {
    decision: string;
    reviewer: string;
    rationale: string;
    valid_until: string | null;
    created_at: string;
  }[];
};
type Fragments = {
  count: number;
  page: number;
  has_next: boolean;
  fragments: {
    id: number;
    ordinal: number;
    locator: string;
    text: string;
    cells: string[] | null;
    method: string;
    confidence: number | null;
  }[];
};
const labels: Record<string, string> = {
  received: "Recibida",
  accepted: "Aceptada",
  returned: "Devuelta",
  pending: "Pendiente de extracción",
  running: "Extrayendo",
  ready: "Texto disponible",
  failed: "Extracción no completada",
};
const errors: Record<string, string> = {
  input_limit: "El archivo supera el límite.",
  text_limit: "El texto supera dos millones de caracteres.",
  fragment_limit: "Hay más de diez mil fragmentos.",
  column_limit: "Hay más de doscientas columnas.",
  empty_document: "No contiene texto extraíble.",
  invalid_utf8: "La codificación no es UTF-8.",
  invalid_csv: "El CSV no tiene una estructura válida.",
  binary_content: "Contiene datos binarios.",
  digest_mismatch: "El archivo almacenado no coincide con el recibido.",
  storage_unavailable: "El original no está disponible.",
  timeout: "Se agotó el tiempo de extracción.",
  security_blocked: "El análisis de seguridad bloqueó el documento.",
  scanner_unavailable:
    "El análisis de seguridad no está disponible. Solicite revisión técnica.",
  sandbox_failed: "No se pudo completar el análisis aislado.",
  ocr_required: "Este PDF requiere reconocimiento de texto de sus imágenes.",
  active_content: "El documento contiene elementos activos no admitidos.",
  external_reference:
    "El documento contiene referencias externas no admitidas.",
  archive_limit: "El documento comprimido excede los límites de análisis.",
  invalid_office: "No se pudo interpretar la estructura de Office.",
  invalid_pdf: "No se pudo interpretar el PDF.",
  attempt_limit: "Se agotaron los intentos de recuperación.",
};
export default function Evidence({
  id,
  name,
  url,
  downloadAllowed,
}: {
  id: string;
  name: string;
  url: string;
  downloadAllowed: boolean;
}) {
  const [doc, setDoc] = useState<Document>();
  const [ocrChecked, setOcrChecked] = useState(false);
  const [fragments, setFragments] = useState<Fragments>();
  const [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [reason, setReason] = useState(""),
    [until, setUntil] = useState("");
  async function load(page = 1) {
    setBusy(true);
    setNotice("");
    try {
      const [d, f] = await Promise.all([
        api<Document>(`evidence/${id}/`),
        api<Fragments>(`evidence/${id}/fragments/?page=${page}`),
      ]);
      setDoc(d);
      setFragments(f);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function review(decision: string) {
    if (!doc) return;
    setBusy(true);
    setNotice("");
    try {
      setDoc(
        await api<Document>(`evidence/${id}/`, "POST", {
          version: doc.etag,
          decision,
          rationale: reason,
          ocr_checked: ocrChecked,
          valid_until: decision === "accepted" ? until : null,
        }),
      );
      setReason("");
      setNotice("Revisión de evidencia registrada.");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="help" aria-label={"Documento: " + name}>
      <p>
        {(
          doc
            ? !doc.scan_required || doc.security_state === "clean"
            : downloadAllowed
        ) ? (
          <a href={url}>{name}</a>
        ) : (
          <span>{name} · Descarga pendiente de seguridad</span>
        )}
      </p>
      <button disabled={busy} onClick={() => load()}>
        {doc ? "Actualizar documento" : "Ver texto y revisión"}
      </button>
      {doc && (
        <>
          <p>
            {labels[doc.state] ?? doc.state} · {labels[doc.extraction.state]}
          </p>
          {doc.scan_required && (
            <p>
              Seguridad:{" "}
              {doc.security_state === "clean"
                ? "sin detecciones en el análisis"
                : doc.security_state === "blocked"
                  ? "documento bloqueado"
                  : doc.security_state === "unavailable"
                    ? "análisis no disponible"
                    : "pendiente de análisis"}
              . El resultado no acredita autenticidad ni suficiencia.
            </p>
          )}
          <p>
            Adjunto a la respuesta versión {doc.answer_version}.
            {!doc.is_current &&
              ` La respuesta actual es la versión ${doc.current_answer_version}; esta evidencia conserva su contexto anterior.`}
          </p>
          {doc.expired && <p>Vigencia vencida. Requiere una nueva revisión.</p>}
          <small>
            Recibir y extraer texto no confirma su autenticidad ni su
            suficiencia. Compare con el original antes de aceptar. Las fórmulas
            de CSV se muestran como texto.
          </small>
          <details>
            <summary>Huella del original</summary>
            <pre>{doc.sha256}</pre>
          </details>
          {doc.extraction.state === "pending" && (
            <p>
              El trabajador documental debe procesar este archivo. Puede
              actualizar después.
            </p>
          )}
          {doc.extraction.error && (
            <p>
              {errors[doc.extraction.error] ??
                "No fue posible completar la extracción. Solicite revisión técnica o adjunte una nueva versión."}
            </p>
          )}
          {fragments && (
            <>
              <p>
                {fragments.count} fragmentos · Página {fragments.page}
              </p>
              {fragments.fragments.map((f) => (
                <div key={f.ordinal}>
                  <strong>{f.locator}</strong>
                  {f.method === "ocr" && (
                    <p>
                      Texto reconocido por OCR. Confianza orientativa:{" "}
                      {f.confidence?.toFixed(1) ?? "sin dato"}/100; debe
                      cotejarse con el original.
                    </p>
                  )}
                  {f.cells ? (
                    <ol>
                      {f.cells.map((cell, i) => (
                        <li key={i}>
                          Columna {i + 1}: <pre>{cell}</pre>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <pre>{f.text}</pre>
                  )}
                </div>
              ))}
              <button
                disabled={busy || fragments.page === 1}
                onClick={() => load(fragments.page - 1)}
              >
                Fragmentos anteriores
              </button>
              <button
                disabled={busy || !fragments.has_next}
                onClick={() => load(fragments.page + 1)}
              >
                Fragmentos siguientes
              </button>
            </>
          )}
          {fragments && (
            <AIRelease
              instance={doc.instance}
              fragments={fragments.fragments}
              releases={doc.ai_releases}
              canRelease={
                doc.can_review &&
                doc.state === "accepted" &&
                doc.is_current &&
                !doc.expired
              }
              onChanged={() => load(fragments.page)}
            />
          )}
          {doc.can_retry && (
            <button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  setDoc(
                    await api<Document>(`evidence/${id}/retry/`, "POST", {
                      version: doc.etag,
                    }),
                  );
                  setNotice("Extracción puesta en cola nuevamente.");
                } catch (e) {
                  setNotice((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Reintentar extracción
            </button>
          )}
          {doc.can_review && (
            <>
              <label>
                Fundamento de revisión documental
                <textarea
                  value={reason}
                  maxLength={5000}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
              {doc.requires_ocr_check && (
                <label>
                  <input
                    type="checkbox"
                    checked={ocrChecked}
                    onChange={(e) => setOcrChecked(e.target.checked)}
                  />
                  Comparé el texto OCR con el original
                </label>
              )}
              <label>
                Válida hasta
                <input
                  type="date"
                  value={until}
                  onChange={(e) => setUntil(e.target.value)}
                />
              </label>
              <button
                disabled={
                  busy ||
                  !reason.trim() ||
                  !until ||
                  (doc.requires_ocr_check && !ocrChecked) ||
                  doc.extraction.state !== "ready"
                }
                onClick={() => review("accepted")}
              >
                Aceptar evidencia
              </button>
              <button
                disabled={busy || !reason.trim()}
                onClick={() => review("returned")}
              >
                Devolver evidencia
              </button>
              <p>
                La decisión se limita a este documento y su versión de
                respuesta; no valida automáticamente la respuesta ni una
                obligación normativa.
              </p>
            </>
          )}
          <details>
            <summary>Historial de revisión documental</summary>
            {doc.reviews.map((r, i) => (
              <div key={i}>
                <p>
                  {labels[r.decision]} · {r.reviewer} ·{" "}
                  {new Date(r.created_at).toLocaleString("es-MX")}
                </p>
                <pre>{r.rationale}</pre>
                {r.valid_until && <p>Válida hasta: {r.valid_until}</p>}
              </div>
            ))}
          </details>
        </>
      )}
      <p role="status">{notice}</p>
    </section>
  );
}
