import { test, expect, Page } from "@playwright/test";
import { readFileSync } from "node:fs";
const password = process.env.E2E_PASSWORD!;
const helpLabels = [
  "Qué significa",
  "Para qué se pregunta",
  "Quién conoce la respuesta",
  "Dónde buscar la información",
  "Pasos para responder",
  "Ejemplo ficticio (identifíquelo expresamente)",
  "Evidencia necesaria y alternativas",
  "Errores frecuentes y respuesta suficiente",
  "Cuándo aplica y de qué depende",
  "A quién consultar y cómo resolver una duda",
];
async function login(page: Page, username: string) {
  await page.goto("/personal/plan");
  await page.getByLabel("Usuario", { exact: true }).fill(username);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Mi trabajo de hoy" }),
  ).toBeVisible();
}
async function logout(page: Page) {
  await page.goto("/personal/plan");
  await page.getByRole("button", { name: /Cerrar sesión/ }).click();
  await expect(
    page.getByRole("button", { name: "Ingresar", exact: true }),
  ).toBeVisible();
}
async function administration(page: Page) {
  await page
    .getByRole("link", { name: "Administración y cuestionarios" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Administración del plan" }),
  ).toBeVisible();
}
async function questionnaire(page: Page) {
  await administration(page);
  await page
    .getByRole("button", { name: "Cuestionarios y ayudas", exact: true })
    .click();
  await page
    .getByLabel("Servicio del cuestionario")
    .selectOption({ label: "Servicio sintético · Sede sintética" });
}

test("dirección configura; colaboradores preparan; otra persona revisa; captura queda persistida", async ({
  page,
}) => {
  await login(page, "e2e_director");
  await administration(page);
  const campus = page.locator("form").filter({
    has: page.getByRole("heading", { name: "Nuevo campus", exact: true }),
  });
  await campus
    .getByLabel("Institución", { exact: true })
    .selectOption({ label: "Institución sintética de pruebas" });
  await campus.getByLabel("Nombre del campus").fill("Campus sintético");
  await campus.getByRole("button", { name: "Crear campus" }).click();
  await expect(page.getByRole("status")).toHaveText("Registro guardado.");
  const site = page.locator("form").filter({
    has: page.getByRole("heading", { name: "Nueva sede", exact: true }),
  });
  await site
    .getByLabel("Campus", { exact: true })
    .selectOption({ label: "Campus sintético" });
  await site.getByLabel("Nombre de la sede").fill("Sede sintética");
  await site.getByRole("button", { name: "Crear sede" }).click();
  await expect(page.getByRole("status")).toHaveText("Registro guardado.");
  const service = page.locator("form").filter({
    has: page.getByRole("heading", {
      name: "Nuevo servicio o unidad administrativa",
    }),
  });
  await service
    .getByLabel("Sede", { exact: true })
    .selectOption({ label: "Sede sintética" });
  await service
    .getByLabel("Nombre del servicio o unidad")
    .fill("Servicio sintético");
  await service.getByRole("button", { name: "Crear servicio" }).click();
  await expect(page.getByRole("status")).toHaveText("Registro guardado.");
  await page
    .getByLabel("Fundamento de la confirmación")
    .fill("Alcance sintético confirmado para prueba");
  await page.getByRole("button", { name: "Confirmar servicio" }).click();
  await expect(
    page.getByText("Alcance confirmado", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Usuarios y nombramientos" }).click();
  for (const [username, name, role] of [
    ["e2e_writer", "Colaborador sintético", "contributor"],
    ["e2e_reviewer", "Revisor sintético", "manager"],
  ]) {
    const user = page.locator("form").filter({
      has: page.getByRole("heading", { name: "Registrar usuario" }),
    });
    await user
      .getByLabel("Institución de la persona")
      .selectOption({ label: "Institución sintética de pruebas" });
    await user.getByLabel("Usuario", { exact: true }).fill(username);
    await user.getByLabel("Nombre", { exact: true }).fill(name);
    await user
      .getByLabel("Contraseña inicial (mínimo 12 caracteres)")
      .fill(password);
    await user.getByRole("button", { name: "Crear usuario" }).click();
    await expect(page.getByRole("status")).toHaveText("Registro guardado.");
    const grant = page.locator("form").filter({
      has: page.getByRole("heading", {
        name: "Aprobar nombramiento",
        exact: true,
      }),
    });
    await grant
      .getByLabel("Persona", { exact: true })
      .selectOption({ label: `${name} (${username})` });
    await grant
      .getByLabel("Servicio del nombramiento")
      .selectOption({ label: "Servicio sintético" });
    await grant.getByLabel("Rol autorizado").selectOption(role);
    await grant.getByLabel("Inicio de vigencia").fill(process.env.E2E_START!);
    await grant.getByLabel("Fin de vigencia").fill(process.env.E2E_END!);
    await grant
      .getByLabel("Fundamento y competencia confirmada")
      .fill("Competencia sintética confirmada para este ensayo");
    await grant
      .getByRole("button", { name: "Aprobar nombramiento", exact: true })
      .click();
    await expect(page.getByRole("status")).toHaveText("Registro guardado.");
  }
  await page
    .getByRole("button", { name: "Cuestionarios y ayudas", exact: true })
    .click();
  await page
    .getByLabel("Servicio del cuestionario")
    .selectOption({ label: "Servicio sintético · Sede sintética" });
  await page
    .getByText("Seleccionar preguntas del inventario autorizado", {
      exact: true,
    })
    .click();
  await page.getByRole("checkbox").check();
  await page
    .getByLabel("Fundamento de selección del alcance")
    .fill("Pregunta sintética del ensayo");
  await page.getByRole("button", { name: "Agregar 1 preguntas" }).click();
  await expect(
    page.getByRole("heading", { name: /La cita reserva simultáneamente/ }),
  ).toBeVisible();
  await logout(page);
  await login(page, "e2e_writer");
  await questionnaire(page);
  await page
    .getByRole("button", { name: "Comparar borrador de la fuente" })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Borrador editorial para revisión humana",
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Usar propuesta en el editor" })
    .click();
  for (const label of helpLabels)
    await expect(page.getByLabel(label, { exact: true })).not.toHaveValue("");
  await page
    .getByLabel("Para qué se pregunta", { exact: true })
    .fill(
      "Adaptación sintética: comprobar recursos antes de confirmar una cita.",
    );
  await page.getByRole("button", { name: "Guardar borrador de ayuda" }).click();
  await expect(
    page.getByText("Borrador guardado.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Aprobar ayuda", exact: true }),
  ).toHaveCount(0);
  await logout(page);
  await login(page, "e2e_reviewer");
  await questionnaire(page);
  await page
    .getByLabel("Fundamento de la revisión")
    .fill("Se revisaron los diez apartados y el ejemplo ficticio");
  await page
    .getByRole("button", { name: "Aprobar ayuda", exact: true })
    .click();
  await expect(
    page.getByText("Revisión registrada.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Publicar pregunta", exact: true })
    .click();
  await expect(
    page.getByText("Pregunta publicada.", { exact: true }),
  ).toBeVisible();
  await logout(page);
  await login(page, "e2e_writer");
  await page.getByRole("button", { name: /Servicio sintético/ }).click();
  await page
    .getByLabel("Respuesta o justificación")
    .fill("Declaración sintética: se comprueban sillón y supervisor.");
  await page.getByRole("button", { name: "Guardar y continuar" }).click();
  await expect(
    page.getByText("Guardado confirmado.", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: /Servicio sintético/ }).click();
  await expect(page.getByLabel("Respuesta o justificación")).toHaveValue(
    "Declaración sintética: se comprueban sillón y supervisor.",
  );
  await page.getByText("Evidencia y declaraciones", { exact: true }).click();
  await page.getByLabel("Adjuntar declaración").setInputFiles({
    name: "declaracion-sintetica.docx",
    mimeType:
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    buffer: readFileSync(process.env.E2E_DOCUMENT!),
  });
  await expect(
    page.getByText(/declaracion-sintetica.docx/).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Ver texto y revisión", exact: true })
    .click();
  await expect
    .poll(
      async () => {
        await page
          .getByRole("button", { name: "Actualizar documento", exact: true })
          .click();
        return page.getByText(/^Recibida ·/).textContent();
      },
      { timeout: 60000, intervals: [250, 500, 1000] },
    )
    .toMatch(/Recibida · (Texto disponible|Extracción no completada)/);
  await expect(
    page.getByText("Recibida · Texto disponible", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("word/document.xml · párrafo 1", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Aceptar evidencia", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Enviar a revisión" }).click();
  await expect(page.getByText(/Estado: Enviada/)).toBeVisible();
  await logout(page);
  await login(page, "e2e_reviewer");
  await page.getByRole("button", { name: /Servicio sintético/ }).click();
  await page.getByText("Evidencia y declaraciones", { exact: true }).click();
  await page
    .getByRole("button", { name: "Ver texto y revisión", exact: true })
    .click();
  await expect
    .poll(
      async () => {
        await page
          .getByRole("button", { name: "Actualizar documento", exact: true })
          .click();
        return page.getByText(/^Recibida ·/).textContent();
      },
      { timeout: 60000, intervals: [250, 500, 1000] },
    )
    .toMatch(/Recibida · (Texto disponible|Extracción no completada)/);
  await expect(
    page.getByText("Recibida · Texto disponible", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Fundamento de revisión documental")
    .fill(
      "Texto y original sintéticos cotejados; declaración suficiente para el ensayo.",
    );
  await page
    .getByLabel("Válida hasta", { exact: true })
    .fill(process.env.E2E_END!);
  await page
    .getByRole("button", { name: "Aceptar evidencia", exact: true })
    .click();
  await expect(
    page.getByText("Aceptada · Texto disponible", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Estado: Enviada/)).toBeVisible();
  await page
    .getByText("Autorizaciones de fragmentos para IA", { exact: true })
    .click();
  await page.getByLabel(/word\/document.xml · párrafo 1/).check();
  await page
    .getByLabel("Autorización hasta", { exact: true })
    .fill(process.env.E2E_END!);
  await page
    .getByLabel("Fundamento de autorización", { exact: true })
    .fill("Sólo texto sintético público para probar la autorización.");
  await page.getByLabel(/Cotejé estos fragmentos/).check();
  await page
    .getByRole("button", {
      name: "Autorizar fragmentos seleccionados",
      exact: true,
    })
    .click();
  await expect(
    page.getByText("Autorización actualizada.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Revocar autorización/ }).click();
  await expect(page.getByText(/Fragmento .*Revocada/)).toBeVisible();
  await page.screenshot({ path: "test-results/evidencia.png", fullPage: true });
  await page.getByText("Revisar respuesta", { exact: true }).click();
  await page
    .getByLabel("Fundamento u observaciones")
    .fill("Declaración sintética revisada por otra persona");
  await page
    .getByRole("button", { name: "Validar respuesta", exact: true })
    .click();
  await expect(page.getByText("1 de 1", { exact: true })).toBeVisible();
  await expect(page.getByText(/Estado: Validada/)).toBeVisible();
  await logout(page);
  await login(page, "e2e_writer");
  await page.getByRole("button", { name: /Servicio sintético/ }).click();
  await page
    .getByRole("button", { name: "Abrir consultas", exact: true })
    .click();
  await page
    .getByLabel("Persona a consultar")
    .selectOption({ label: "Revisor sintético (e2e_reviewer)" });
  await page
    .getByLabel("Duda concreta")
    .fill("Consulta sintética sobre reserva de recursos");
  await page
    .getByLabel("Fecha de respuesta esperada")
    .fill(process.env.E2E_END!);
  await page
    .getByRole("button", { name: "Registrar consulta", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Consulta sintética sobre reserva de recursos",
    }),
  ).toBeVisible();
  await logout(page);
  await login(page, "e2e_reviewer");
  await page.getByRole("link", { name: "Consultas", exact: true }).click();
  await page
    .getByRole("button", { name: "Abrir consultas", exact: true })
    .click();
  await page
    .getByLabel("Mensaje de seguimiento")
    .fill("Respuesta sintética: comprobar recursos y supervisor.");
  await page.getByRole("button", { name: "Enviar seguimiento" }).click();
  await expect(
    page.getByText("Respuesta sintética: comprobar recursos y supervisor.", {
      exact: true,
    }),
  ).toBeVisible();
  await logout(page);
  await login(page, "e2e_writer");
  await page.getByRole("link", { name: "Consultas", exact: true }).click();
  await page
    .getByRole("button", { name: "Abrir consultas", exact: true })
    .click();
  await page
    .getByLabel("Cómo quedó resuelta la duda")
    .fill("Aclaración sintética recibida y comprendida.");
  await page.getByRole("button", { name: "Marcar duda resuelta" }).click();
  await expect(
    page.getByText("Resolución: Aclaración sintética recibida y comprendida.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/consultas.png", fullPage: true });
  await page.goto("/personal/plan");
  await page.getByRole("button", { name: /Servicio sintético/ }).click();
  await expect(page.getByText("1 de 1", { exact: true })).toBeVisible();
  await expect(page.getByText(/Estado: Validada/)).toBeVisible();
  await page
    .getByRole("button", { name: "Abrir asistencia", exact: true })
    .click();
  await expect(
    page.getByText(
      "La salida a proveedores de IA está deshabilitada. Puede continuar con la ayuda revisada y la captura manual.",
    ),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/recorrido-gestor.png",
    fullPage: true,
  });
});

test("acceso adaptable a teléfono y navegación por teclado", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/personal/plan");
  await expect(page.getByLabel("Usuario", { exact: true })).toBeVisible();
  await page.getByLabel("Usuario", { exact: true }).focus();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Contraseña", { exact: true })).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/acceso-movil.png",
    fullPage: true,
  });
});

test("matriz: captura, prueba, revisión independiente e historial", async ({
  page,
}) => {
  page.setDefaultTimeout(15000);
  await login(page, "e2e_matrix_author");
  await page.getByRole("link", { name: "Cumplimiento", exact: true }).click();
  await page
    .getByLabel("Servicio de cumplimiento")
    .selectOption({ label: "Servicio matriz sintética · Sede matriz" });
  await page
    .getByLabel("Entrada normativa", { exact: true })
    .selectOption({ index: 1 });
  await page
    .getByLabel("Control del plan", { exact: true })
    .selectOption({ index: 1 });
  await page
    .getByLabel("Proceso del servicio")
    .fill("Proceso sintético de revisión documental");
  await page.getByLabel("Pregunta vinculada").selectOption({ index: 1 });
  await page
    .getByLabel("Responsable del registro")
    .selectOption({ label: "e2e_matrix_author" });
  await page
    .getByLabel("Numeral exacto")
    .fill("Numeral sintético, no verificación jurídica");
  await page
    .getByLabel("Versión normativa consultada")
    .fill("Versión sintética del ensayo");
  await page
    .getByLabel("URL oficial consultada")
    .fill("https://example.invalid/synthetic");
  await page
    .getByLabel("Fecha de consulta", { exact: true })
    .fill(process.env.E2E_START!);
  await page.getByLabel("Vigencia revisada").selectOption("verified");
  await page.getByLabel("Aplicabilidad propuesta").selectOption("applies");
  await page
    .getByLabel("Supuesto y fundamento de aplicabilidad")
    .fill("Supuesto exclusivamente sintético.");
  await page
    .getByLabel("Obligación o mejora propuesta")
    .fill("Obligación sintética para probar la trazabilidad.");
  await page
    .getByLabel("Por qué se vincula con esta pregunta y control")
    .fill("Vínculo sintético del ensayo.");
  await page.getByLabel("Próxima revisión").fill(process.env.E2E_END!);
  await page
    .getByLabel("Evidencia sintética matriz.txt", { exact: true })
    .check();
  await page
    .getByRole("button", {
      name: "Guardar registro de cumplimiento",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: /Registro .*versión 1/ }),
  ).toBeVisible();
  await page
    .getByLabel("Procedimiento ejecutado")
    .fill("Cotejo sintético del expediente de prueba.");
  await page
    .getByLabel("Resultado esperado")
    .fill("Coincidencia de documentos sintéticos.");
  await page
    .getByLabel("Resultado observado")
    .fill("Coincidencia verificada sólo para el ensayo.");
  await page
    .getByLabel("Resultado de prueba", { exact: true })
    .selectOption("passed");
  await page
    .getByRole("button", { name: "Registrar prueba", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Registro guardado");
  await page.goto("/personal/plan");
  await logout(page);
  await login(page, "e2e_matrix_reviewer");
  await page.getByRole("link", { name: "Cumplimiento", exact: true }).click();
  await page
    .getByLabel("Servicio de cumplimiento")
    .selectOption({ label: "Servicio matriz sintética · Sede matriz" });
  await page.getByRole("button", { name: /Abrir registro/ }).click();
  await page
    .getByLabel("Fundamento de revisión del registro")
    .fill("Revisión independiente sintética, sin conclusión jurídica real.");
  await page
    .getByRole("button", { name: "Aprobar revisión del registro", exact: true })
    .click();
  await expect(
    page.getByRole("cell", { name: "Revisión aprobada", exact: true }),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exportar matriz JSON" }).click();
  await download;
  await page.screenshot({
    path: "test-results/cumplimiento.png",
    fullPage: true,
  });
  await page
    .getByLabel("Obligación o mejora propuesta")
    .fill("Obligación sintética modificada; requiere nueva revisión.");
  await page
    .getByRole("button", {
      name: "Guardar registro de cumplimiento",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: /Registro .*versión 2/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "Borrador", exact: true }),
  ).toBeVisible();
});

test("seguimiento: propuesta, línea base, horas y cierre independiente", async ({
  page,
}) => {
  page.setDefaultTimeout(15000);
  async function board() {
    await page.getByRole("link", { name: "Seguimiento", exact: true }).click();
    await page
      .getByLabel("Servicio de seguimiento", { exact: true })
      .selectOption({
        label: "Servicio seguimiento sintético · Sede seguimiento",
      });
  }
  async function openTask() {
    await page
      .getByRole("button", { name: /Tarea .*Ensayo sintético de seguimiento/ })
      .click();
  }
  await login(page, "e2e_task_manager");
  await board();
  await page
    .getByLabel("Título de tarea", { exact: true })
    .fill("Ensayo sintético de seguimiento");
  await page
    .getByLabel("Responsable de tarea", { exact: true })
    .selectOption({ label: "e2e_task_manager" });
  await page.getByLabel("Inicio previsto").fill("2026-10-01");
  await page.getByLabel("Fin previsto").fill("2026-10-02");
  await page.getByLabel("Esfuerzo estimado en minutos").fill("120");
  await page
    .getByLabel("Criterios para aceptar el cierre")
    .fill("Caso normal y excepción sintéticos comprobados.");
  await page
    .getByRole("button", { name: "Guardar tarea propuesta", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Tarea seleccionada: Ensayo sintético de seguimiento",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByLabel("Fundamento del cambio")
    .fill("Compromiso sintético para probar el flujo.");
  await page
    .getByRole("button", {
      name: "Solicitar aprobación de línea base",
      exact: true,
    })
    .click();
  await expect(page.getByText(/Propuesta .*Pendiente/)).toBeVisible();
  await logout(page);
  await login(page, "e2e_task_director");
  await board();
  await openTask();
  await page
    .getByLabel("Resultado, bloqueo o fundamento")
    .fill("Presupuesto y criterios sintéticos revisados.");
  await page.getByRole("button", { name: /Aprobar cambio/ }).click();
  await expect(page.getByRole("status")).toContainText("Registro guardado");
  await page
    .getByText("Calendario institucional y referencia C22", { exact: true })
    .click();
  await page
    .getByLabel("Fundamento del calendario")
    .fill("Calendario sintético de lunes a viernes.");
  await page
    .getByLabel("Fechas no laborables (AAAA-MM-DD, una por línea)")
    .fill("2026-10-12");
  await page
    .getByRole("button", {
      name: "Confirmar calendario institucional",
      exact: true,
    })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Calendario institucional confirmado y versionado.",
  );
  await logout(page);
  await login(page, "e2e_task_manager");
  await board();
  await openTask();
  await page
    .getByLabel("Resultado, bloqueo o fundamento")
    .fill("Dos horas sintéticas de trabajo comprobado.");
  await page.getByLabel("Fecha del trabajo").fill("2026-10-02");
  await page.getByLabel("Minutos trabajados").fill("120");
  await page
    .getByRole("button", { name: "Registrar tiempo real", exact: true })
    .click();
  await expect(page.getByText(/2.00 horas registradas/)).toBeVisible();
  await page
    .getByLabel("Resultado, bloqueo o fundamento")
    .fill("Casos normal y excepción sintéticos completados.");
  await page
    .getByRole("button", { name: "Entrega en revisión", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Registro guardado");
  await page
    .getByLabel("Resultado, bloqueo o fundamento")
    .fill("Intento sintético de autoaceptación.");
  await page
    .getByRole("button", { name: "Cierre aceptado", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("otra persona");
  await logout(page);
  await login(page, "e2e_task_director");
  await board();
  await openTask();
  await page
    .getByLabel("Resultado, bloqueo o fundamento")
    .fill("Cierre sintético cotejado por otra persona.");
  await page
    .getByRole("button", { name: "Cierre aceptado", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Cierres aceptados: 1 de 1",
      exact: true,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/seguimiento.png",
    fullPage: true,
  });
});

test("MFA activa autenticador, bloquea sesión pendiente y permite recuperación de un uso", async ({
  page,
}) => {
  const { createHmac } = await import("node:crypto");
  function code(secret: string) {
    const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    let bits = "";
    for (const letter of secret)
      bits += alphabet.indexOf(letter).toString(2).padStart(5, "0");
    const key = Buffer.from(
      bits.match(/.{8}/g)!.map((value) => parseInt(value, 2)),
    );
    const counter = Buffer.alloc(8);
    counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
    const digest = createHmac("sha1", key).update(counter).digest();
    const offset = digest[19] & 15;
    return ((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000)
      .toString()
      .padStart(6, "0");
  }
  await login(page, "e2e_mfa");
  await page.getByRole("link", { name: "Seguridad de la cuenta" }).click();
  await page
    .getByLabel("Confirme su contraseña", { exact: true })
    .fill(password);
  await page
    .getByRole("button", { name: "Preparar autenticador", exact: true })
    .click();
  const secret = await page.getByTestId("mfa-secret").innerText();
  await page
    .getByLabel("Código del autenticador", { exact: true })
    .fill(code(secret));
  await page
    .getByRole("button", { name: "Confirmar autenticador", exact: true })
    .click();
  await expect(
    page.getByRole("list", { name: "Códigos de recuperación" }).locator("code"),
  ).toHaveCount(8);
  const codes = await page
    .getByRole("list", { name: "Códigos de recuperación" })
    .locator("code")
    .allTextContents();
  expect(codes).toHaveLength(8);
  await page.setViewportSize({ width: 375, height: 900 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page
    .getByRole("button", { name: "Guardé mis códigos; continuar" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Mi trabajo de hoy" }),
  ).toBeVisible();
  await logout(page);
  await page.getByLabel("Usuario", { exact: true }).fill("e2e_mfa");
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Verificación en dos pasos" }),
  ).toBeVisible();
  expect((await page.request.get("/api/v1/services/")).status()).toBe(403);
  await page.getByLabel("Código de verificación o recuperación").fill(codes[0]);
  await page
    .getByRole("button", { name: "Verificar acceso", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Mi trabajo de hoy" }),
  ).toBeVisible();
  await logout(page);
  await page.getByLabel("Usuario", { exact: true }).fill("e2e_mfa");
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await page.getByLabel("Código de verificación o recuperación").fill(codes[0]);
  await page
    .getByRole("button", { name: "Verificar acceso", exact: true })
    .click();
  await expect(page.locator("section").getByRole("alert")).toContainText(
    "ya utilizado",
  );
  await page.getByLabel("Código de verificación o recuperación").fill(codes[1]);
  await page
    .getByRole("button", { name: "Verificar acceso", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Mi trabajo de hoy" }),
  ).toBeVisible();
});

test("entrevista conserva avances al retomar y traslada sólo a borrador", async ({
  page,
}) => {
  await login(page, "e2e_interview");
  await page
    .getByRole("button", { name: /Servicio entrevista sintética/ })
    .click();
  const interview = page.getByRole("region", { name: "Entrevista guiada" });
  await interview
    .getByRole("button", { name: "Abrir entrevista", exact: true })
    .click();
  await interview
    .getByRole("button", { name: "Iniciar con la ayuda revisada", exact: true })
    .click();
  const form = (prompt: string) =>
    interview.locator("form").filter({
      has: page.getByRole("heading", { name: prompt, exact: true }),
    });
  await expect(form("Indique responsable.")).toBeVisible();
  await expect(form("Indique sede.")).toBeVisible();
  await expect(form("Indique excepción.")).toHaveCount(0);
  await form("Indique sede.")
    .getByLabel("Su declaración")
    .fill("Sede que aún estoy redactando");
  await form("Indique responsable.")
    .getByLabel("Estado de esta información")
    .selectOption("known");
  await form("Indique responsable.")
    .getByLabel("Su declaración")
    .fill("Responsable sintético registrado");
  await form("Indique responsable.")
    .getByRole("button", { name: "Guardar apartado" })
    .click();
  await expect(form("Indique excepción.")).toBeVisible();
  await expect(form("Indique sede.").getByLabel("Su declaración")).toHaveValue(
    "Sede que aún estoy redactando",
  );
  await page.reload();
  await page
    .getByRole("button", { name: /Servicio entrevista sintética/ })
    .click();
  await interview
    .getByRole("button", { name: "Abrir entrevista", exact: true })
    .click();
  await expect(form("Indique sede.")).toBeVisible();
  await expect(form("Indique responsable.")).not.toBeVisible();
  await interview
    .getByText("Declaraciones guardadas y correcciones", { exact: true })
    .click();
  await expect(
    form("Indique responsable.").getByLabel("Su declaración"),
  ).toHaveValue("Responsable sintético registrado");
  await form("Indique sede.")
    .getByLabel("Estado de esta información")
    .selectOption("known");
  await form("Indique sede.")
    .getByLabel("Su declaración")
    .fill("Sede ficticia");
  await form("Indique sede.")
    .getByRole("button", { name: "Guardar apartado" })
    .click();
  await form("Indique excepción.")
    .getByLabel("Estado de esta información")
    .selectOption("unknown");
  await form("Indique excepción.")
    .getByRole("button", { name: "Guardar apartado" })
    .click();
  await interview
    .getByRole("button", { name: "Usar entrevista y guardar borrador" })
    .click();
  await expect(interview.getByRole("status")).toContainText(
    "borrador por confirmar",
  );
  await expect(
    page.getByLabel("Respuesta o justificación", { exact: true }),
  ).toContainText("Responsable sintético registrado");
  await expect(
    interview.getByRole("button", {
      name: "Usar entrevista y guardar borrador",
    }),
  ).toBeDisabled();
});

test("acciones IA permiten explicar sin documentos y no ofrecen aplicar explicación (API simulada)", async ({
  page,
}) => {
  await login(page, "e2e_interview");
  await page
    .getByRole("button", { name: /Servicio entrevista sintética/ })
    .click();
  let sent: Record<string, unknown> | undefined;
  await page.route("**/api/v1/ai/questions/*/", async (route) => {
    if (route.request().method() === "POST") {
      sent = route.request().postDataJSON();
      await route.fulfill({ json: { id: 99001, state: "ready" }, status: 202 });
    } else {
      await route.fulfill({
        json: {
          providers: ["openai"],
          actions: ["suggest", "explain", "extract", "interview"],
          static_help: {},
          fragments: { openai: [] },
          requests: [],
        },
      });
    }
  });
  await page.route("**/api/v1/ai/requests/99001/", async (route) => {
    await route.fulfill({
      json: {
        id: 99001,
        action: "explain",
        state: "ready",
        error: "",
        provider: "openai",
        model: "synthetic",
        estimated_cost: "0",
        result: {
          plain_explanation: "Explicación sintética de la pregunta",
          follow_up_questions: [],
          missing_information: [],
          suggested_fields: [],
          citations: [],
          conflicts: [],
        },
      },
    });
  });
  const assistant = page.getByRole("region", {
    name: "Asistencia con documentos",
  });
  await assistant
    .getByRole("button", { name: "Abrir asistencia", exact: true })
    .click();
  await assistant.getByLabel("Proveedor autorizado").selectOption("openai");
  await expect(
    assistant.getByRole("button", {
      name: "Proponer con mis documentos",
      exact: true,
    }),
  ).toBeDisabled();
  await assistant.getByLabel("Tipo de asistencia").selectOption("extract");
  await expect(
    assistant.getByRole("button", {
      name: "Extraer datos de mis documentos",
      exact: true,
    }),
  ).toBeDisabled();
  await assistant.getByLabel("Tipo de asistencia").selectOption("explain");
  await assistant
    .getByRole("button", { name: "Explícame", exact: true })
    .click();
  await expect(
    assistant.getByText("Explicación sintética de la pregunta", {
      exact: true,
    }),
  ).toBeVisible();
  expect(sent?.action).toBe("explain");
  expect(sent?.fragment_ids).toEqual([]);
  expect(sent).not.toHaveProperty("answer");
  await expect(
    assistant.getByRole("button", {
      name: "Usar propuesta y guardar borrador",
    }),
  ).toHaveCount(0);
});

test("revisión IA exige confirmar texto autorizado y bloquea cambios sin guardar (API simulada)", async ({
  page,
}) => {
  await login(page, "e2e_interview");
  await page
    .getByRole("button", { name: /Servicio entrevista sintética/ })
    .click();
  const editor = page.getByLabel("Respuesta o justificación", { exact: true });
  const original = await editor.inputValue();
  let sent: Record<string, unknown> | undefined;
  await page.route("**/api/v1/ai/answer-releases/*/", async (route) => {
    const response = await route.fetch();
    const real = await response.json();
    await route.fulfill({
      json: {
        ...real,
        text: "Texto sintético autorizado para revisión",
        releases: [
          {
            id: 99101,
            provider: "openai",
            version: real.revision,
            expires: "2099-01-01",
            revoked: false,
            usable: true,
          },
        ],
      },
    });
  });
  await page.route("**/api/v1/ai/questions/*/", async (route) => {
    if (route.request().method() === "POST") {
      sent = route.request().postDataJSON();
      await route.fulfill({ json: { id: 99102, state: "ready" }, status: 202 });
    } else
      await route.fulfill({
        json: {
          providers: ["openai"],
          actions: ["review"],
          static_help: {},
          fragments: { openai: [] },
          requests: [],
        },
      });
  });
  await page.route("**/api/v1/ai/requests/99102/", async (route) =>
    route.fulfill({
      json: {
        id: 99102,
        action: "review",
        state: "ready",
        error: "",
        provider: "openai",
        model: "synthetic",
        estimated_cost: "0",
        result: {
          plain_explanation:
            "Revisión sintética: confirme quién registra la solicitud.",
          follow_up_questions: [],
          missing_information: ["Responsable"],
          suggested_fields: [],
          citations: [],
          conflicts: [],
        },
      },
    }),
  );
  const assistant = page.getByRole("region", {
    name: "Asistencia con documentos",
  });
  await assistant
    .getByRole("button", { name: "Abrir asistencia", exact: true })
    .click();
  await assistant.getByLabel("Tipo de asistencia").selectOption("review");
  await assistant.getByLabel("Proveedor autorizado").selectOption("openai");
  const submit = assistant.getByRole("button", {
    name: "Revisar mi respuesta",
    exact: true,
  });
  await expect(submit).toBeDisabled();
  await assistant.getByLabel("Respuesta autorizada").selectOption("99101");
  await expect(
    assistant.getByText("Texto sintético autorizado para revisión", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(submit).toBeDisabled();
  await assistant
    .getByLabel(
      "Confirmo enviar esta respuesta guardada al proveedor seleccionado.",
    )
    .check();
  await expect(submit).toBeEnabled();
  await editor.fill(original + " modificación local");
  await expect(submit).toBeDisabled();
  await editor.fill(original);
  await submit.click();
  await expect(
    assistant.getByText(
      "Revisión sintética: confirme quién registra la solicitud.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(assistant.getByRole("status")).toContainText(
    "Solicitud registrada",
  );
  expect(sent?.answer_release_id).toBe(99101);
  expect(sent?.confirm_answer_send).toBe(true);
  expect(sent).not.toHaveProperty("answer");
  await expect(
    assistant.getByRole("button", {
      name: "Usar propuesta y guardar borrador",
    }),
  ).toHaveCount(0);
});

test("comparación IA exige dos fuentes y muestra ambos lados sin aplicar (API simulada)", async ({
  page,
}) => {
  await login(page, "e2e_interview");
  await page
    .getByRole("button", { name: /Servicio entrevista sintética/ })
    .click();
  let sent: Record<string, unknown> | undefined;
  const citations = [
    {
      fragment_id: 99201,
      locator: "Fuente sintética A",
      quote: "Autoriza coordinación.",
    },
    {
      fragment_id: 99202,
      locator: "Fuente sintética B",
      quote: "Autoriza exclusivamente dirección.",
    },
  ];
  await page.route("**/api/v1/ai/questions/*/", async (route) => {
    if (route.request().method() === "POST") {
      sent = route.request().postDataJSON();
      await route.fulfill({ json: { id: 99203, state: "ready" }, status: 202 });
    } else
      await route.fulfill({
        json: {
          providers: ["openai"],
          actions: ["contradictions"],
          static_help: {},
          fragments: {
            openai: citations.map((c) => ({
              id: c.fragment_id,
              locator: c.locator,
              text: c.quote,
            })),
          },
          requests: [],
        },
      });
  });
  await page.route("**/api/v1/ai/requests/99203/", async (route) =>
    route.fulfill({
      json: {
        id: 99203,
        action: "contradictions",
        state: "ready",
        error: "",
        provider: "openai",
        model: "synthetic",
        estimated_cost: "0",
        result: {
          plain_explanation: "Comparación sintética limitada a dos fuentes.",
          follow_up_questions: ["¿Quién confirma la autoridad vigente?"],
          missing_information: [],
          suggested_fields: [],
          citations,
          conflicts: [
            {
              description: "Autoridades incompatibles.",
              fragment_ids: [99201, 99202],
            },
          ],
        },
      },
    }),
  );
  const assistant = page.getByRole("region", {
    name: "Asistencia con documentos",
  });
  await assistant
    .getByRole("button", { name: "Abrir asistencia", exact: true })
    .click();
  await assistant
    .getByLabel("Tipo de asistencia")
    .selectOption("contradictions");
  await assistant.getByLabel("Proveedor autorizado").selectOption("openai");
  const submit = assistant.getByRole("button", {
    name: "Comparar posibles contradicciones",
    exact: true,
  });
  await expect(submit).toBeDisabled();
  await assistant.getByLabel(/Fuente sintética A/).check();
  await expect(submit).toBeDisabled();
  await assistant.getByLabel(/Fuente sintética B/).check();
  await submit.click();
  await expect(assistant.getByRole("status")).toContainText(
    "Solicitud registrada",
  );
  const finding = assistant.getByRole("region", {
    name: "Posible contradicción 1",
  });
  await expect(
    finding.getByText("Autoriza coordinación.", { exact: true }),
  ).toBeVisible();
  await expect(
    finding.getByText("Autoriza exclusivamente dirección.", { exact: true }),
  ).toBeVisible();
  await expect(
    finding.getByText(/Pendiente de resolución humana/),
  ).toBeVisible();
  expect(sent?.action).toBe("contradictions");
  expect(sent?.fragment_ids).toEqual([99201, 99202]);
  expect(sent).not.toHaveProperty("answer");
  await expect(
    assistant.getByRole("button", {
      name: "Usar propuesta y guardar borrador",
    }),
  ).toHaveCount(0);
});

test("informe semanal local conserva estado vacío y exporta con permisos reales", async ({
  page,
}) => {
  await login(page, "e2e_interview");
  await page
    .getByRole("link", { name: "Informes semanales", exact: true })
    .click();
  await page.getByLabel("Servicio del informe").selectOption({
    label: "Servicio entrevista sintética · Sede matriz",
  });
  await page.getByRole("button", { name: "Preparar borrador semanal" }).click();
  const report = page.getByRole("region", { name: "Borrador semanal" });
  await expect(report).toBeVisible();
  await expect(
    report.getByText(/Tareas aceptadas: Sin alcance definido/),
  ).toBeVisible();
  await expect(
    report.getByText("Elegibilidad observada al generar; no acredita distribución actual.", {
      exact: true,
    }),
  ).toBeVisible();
  const exportLink = report.getByRole("link", {
    name: "Generar exportación JSON actualizada",
  });
  const response = await page.request.get(
    (await exportLink.getAttribute("href"))!,
  );
  expect(response.status()).toBe(200);
  expect(response.headers()["cache-control"]).toBe("private, no-store");
  const payload = await response.json();
  expect(payload.status).toBe("draft");
  expect(payload.delivery).toBe("not_sent");
  expect(payload.current.accepted_tasks.denominator).toBe(0);
});

test("guía usa antecedente sólo tras confirmación y el informe exige fuentes (API simulada)", async ({
  page,
}) => {
  await login(page, "e2e_interview");
  await page
    .getByRole("button", { name: /Servicio entrevista sintética/ })
    .click();
  let sent: Record<string, unknown> | undefined;
  await page.route("**/api/v1/ai/answer-releases/*/", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({
      json: {
        ...data,
        text: "Antecedente declarado de prueba",
        releases: [
          {
            id: 99301,
            purpose: "interview",
            provider: "openai",
            version: data.revision,
            usable: true,
            revoked: false,
            expires: "2099-01-01",
          },
          {
            id: 99302,
            purpose: "review",
            provider: "openai",
            version: data.revision,
            usable: true,
            revoked: false,
            expires: "2099-01-01",
          },
        ],
      },
    });
  });
  await page.route("**/api/v1/ai/questions/*/", async (route) => {
    if (route.request().method() === "POST") {
      sent = route.request().postDataJSON();
      await route.fulfill({ json: { id: 99303, state: "ready" }, status: 202 });
    } else
      await route.fulfill({
        json: {
          providers: ["openai"],
          actions: ["interview", "report"],
          static_help: {},
          fragments: {
            openai: [
              {
                id: 99304,
                locator: "Fuente autorizada de informe",
                text: "Contenido sintético.",
              },
            ],
          },
          requests: [],
        },
      });
  });
  await page.route("**/api/v1/ai/requests/99303/", async (route) =>
    route.fulfill({
      json: {
        id: 99303,
        action: sent?.action,
        state: "ready",
        provider: "openai",
        model: "synthetic",
        error: "",
        estimated_cost: "0",
        result: {
          plain_explanation: "Salida sintética con fuentes",
          follow_up_questions: ["¿Qué falta confirmar?"],
          missing_information: [],
          suggested_fields: [],
          citations: [
            {
              fragment_id: 99304,
              locator: "Fuente autorizada de informe",
              quote: "Contenido sintético.",
            },
          ],
          conflicts: [],
        },
      },
    }),
  );
  const assistant = page.getByRole("region", {
    name: "Asistencia con documentos",
  });
  await assistant
    .getByRole("button", { name: "Abrir asistencia", exact: true })
    .click();
  await assistant.getByLabel("Proveedor autorizado").selectOption("openai");
  await assistant.getByLabel("Tipo de asistencia").selectOption("interview");
  const guide = assistant.getByRole("button", {
    name: "Guíame paso a paso",
    exact: true,
  });
  await expect(guide).toBeEnabled();
  await expect(
    assistant
      .getByLabel("Respuesta autorizada")
      .locator('option[value="99302"]'),
  ).toHaveCount(0);
  await assistant.getByLabel("Respuesta autorizada").selectOption("99301");
  await expect(guide).toBeDisabled();
  await assistant
    .getByLabel(
      "Confirmo enviar esta respuesta guardada al proveedor seleccionado.",
    )
    .check();
  await guide.click();
  await expect(assistant.getByRole("status")).toContainText(
    "Solicitud registrada",
  );
  expect(sent?.action).toBe("interview");
  expect(sent?.answer_release_id).toBe(99301);
  expect(sent?.confirm_answer_send).toBe(true);
  await assistant.getByLabel("Tipo de asistencia").selectOption("report");
  const reportButton = assistant.getByRole("button", {
    name: "Borrador de informe con mis documentos",
    exact: true,
  });
  await expect(reportButton).toBeDisabled();
  await assistant.getByLabel(/Fuente autorizada de informe/).check();
  await reportButton.click();
  await expect(assistant.getByRole("status")).toContainText(
    "Solicitud registrada",
  );
  expect(sent?.action).toBe("report");
  expect(sent).not.toHaveProperty("answer_release_id");
  await expect(
    assistant.getByText(
      /Borrador sobre esta pregunta y las fuentes seleccionadas/,
    ),
  ).toBeVisible();
  await expect(
    assistant.getByRole("button", {
      name: "Usar propuesta y guardar borrador",
    }),
  ).toHaveCount(0);
});

test("decisiones: solicitud, resolución independiente y reapertura conservan historial", async ({
  page,
}) => {
  page.setDefaultTimeout(15000);
  async function registry() {
    await page.getByRole("link", { name: "Decisiones", exact: true }).click();
    await page.getByLabel("Servicio de las decisiones").selectOption({
      label: "Servicio seguimiento sintético · Sede seguimiento",
    });
  }
  await login(page, "e2e_task_manager");
  await registry();
  await page
    .getByLabel("Título de la decisión")
    .fill("Elegir alternativa sintética");
  await page
    .getByLabel("Qué debe decidir Dirección")
    .fill("Confirmar cuál alternativa se documentará.");
  await page
    .getByLabel("Alternativas y consecuencias conocidas")
    .fill("A requiere revisar formato; B requiere confirmar alcance.");
  await page.getByLabel("Plazo interno esperado").fill("2026-10-09");
  await page
    .getByRole("button", { name: "Registrar solicitud", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Decisión registrada");
  let detail = page.getByRole("region", { name: "Detalle de decisión" });
  await expect(
    detail.getByRole("button", { name: "Registrar resolución", exact: true }),
  ).toHaveCount(0);
  await logout(page);
  await login(page, "e2e_task_director");
  await registry();
  await page
    .getByRole("button", { name: /Elegir alternativa sintética · Pendiente/ })
    .click();
  detail = page.getByRole("region", { name: "Detalle de decisión" });
  await detail
    .getByLabel("Fundamento de la acción")
    .fill("Se elige A para revisión posterior del formato.");
  await detail
    .getByRole("button", { name: "Registrar resolución", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Decisión registrada");
  await expect(
    detail.getByRole("heading", { name: "Resolución registrada" }),
  ).toBeVisible();
  await detail
    .getByLabel("Fundamento de la acción")
    .fill("Nueva información exige reconsiderar la solicitud.");
  await detail
    .getByRole("button", { name: "Reabrir con fundamento", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Decisión registrada");
  await expect(detail.getByText(/Pendiente · versión 3/)).toBeVisible();
  await expect(
    detail.getByText("Se elige A para revisión posterior del formato.", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Volver a mi trabajo", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Informes semanales", exact: true })
    .click();
  await page.getByLabel("Servicio del informe").selectOption({
    label: "Servicio seguimiento sintético · Sede seguimiento",
  });
  await page
    .getByRole("button", { name: "Preparar borrador semanal", exact: true })
    .click();
  await expect(
    page
      .getByRole("region", { name: "Borrador semanal" })
      .getByText(/Elegir alternativa sintética · plazo/),
  ).toBeVisible();
});

test("capacidad: propuesta con ausencia y aprobación independiente conserva minutos", async ({
  page,
}) => {
  page.setDefaultTimeout(15000);
  async function board() {
    await page
      .getByRole("link", { name: "Capacidad y ausencias", exact: true })
      .click();
    await page
      .getByLabel("Institución de la capacidad")
      .selectOption({ label: "Institución sintética de capacidad" });
    await page
      .getByRole("button", { name: "Consultar capacidad", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Capacidad registrada", exact: true }),
    ).toBeVisible();
  }
  await login(page, "e2e_capacity_proposer");
  await board();
  await page
    .getByLabel("Persona a planificar")
    .selectOption({ label: "e2e_capacity_worker" });
  await page.getByLabel("Día de capacidad").fill("2026-10-05");
  await page.getByLabel("Minutos de capacidad base").fill("480");
  await page.getByLabel("Minutos no disponibles por ausencia").fill("60");
  await page
    .getByLabel("Minutos para Servicio capacidad sintético")
    .fill("300");
  await page
    .getByLabel("Fundamento de planificación (sin motivos médicos)")
    .fill("Planificación sintética de disponibilidad.");
  await page
    .getByRole("button", {
      name: "Registrar propuesta de capacidad",
      exact: true,
    })
    .click();
  await expect(page.getByRole("status")).toContainText("Propuesta registrada");
  await expect(page.getByText(/Sin capacidad aprobada/).first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Aprobar capacidad", exact: true }),
  ).toHaveCount(0);
  await logout(page);
  await login(page, "e2e_capacity_reviewer");
  await board();
  const proposal = page
    .getByRole("article", { name: /Propuesta de capacidad/ })
    .first();
  await proposal
    .getByLabel(/Fundamento de revisión de propuesta/)
    .fill("Revisión independiente de la distribución sintética.");
  await proposal
    .getByRole("button", { name: "Aprobar capacidad", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText("Revisión registrada.");
  await expect(
    page.getByText(/420 minutos disponibles; 120 sin distribuir/),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /e2e_capacity_worker.*Aprobada/ }),
  ).toBeVisible();
});

test('informe conservado: revisión independiente y contenido fijo', async ({page}) => {
  async function openReports(){
    await page.goto('/reportes');
    await page.getByLabel('Servicio del informe').selectOption({label:'Servicio seguimiento sintético · Sede seguimiento'});
  }
  await login(page,'e2e_task_manager');await openReports();
  await page.getByLabel('Inicio de la versión a conservar').fill('2026-09-01');
  await page.getByRole('button',{name:'Generar y conservar versión',exact:true}).click();
  await expect(page.getByRole('heading',{name:/Versión conservada \d+/})).toBeVisible();
  await expect(page.getByText('Estado: Pendiente.',{exact:false})).toBeVisible();
  await logout(page);await login(page,'e2e_task_director');await openReports();
  await page.getByRole('button',{name:/Consultar versión \d+/}).first().click();
  await page.getByLabel('Fundamento de la revisión').fill('Revisión independiente de la instantánea sintética.');
  await page.getByRole('button',{name:'Aprobar versión',exact:true}).click();
  await expect(page.getByText('Estado: Aprobado.',{exact:false})).toBeVisible();
  await expect(page.getByRole('button',{name:'Aprobar versión',exact:true})).toHaveCount(0);
  await expect(page.getByRole('link',{name:'Exportar versión y resolución'})).toBeVisible();
});

test('informe: sustitución y retiro conservan resolución histórica',async({page})=>{
  async function openReports(){await page.goto('/reportes');await page.getByLabel('Servicio del informe').selectOption({label:'Servicio seguimiento sintético · Sede seguimiento'});}
  await login(page,'e2e_task_manager');await openReports();
  await page.getByLabel('Inicio de la versión a conservar').fill('2026-09-02');
  await page.getByRole('button',{name:'Generar y conservar versión',exact:true}).click();
  const title=page.getByRole('heading',{name:/Versión conservada \d+/});await expect(title).toBeVisible();
  const oldId=(await title.innerText()).match(/\d+/)![0];
  await expect(page.getByRole('button',{name:'Generar y conservar versión',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Generar y conservar versión',exact:true}).click();
  await expect(title).not.toHaveText(`Versión conservada ${oldId}`);
  const newId=(await title.innerText()).match(/\d+/)![0];
  await logout(page);await login(page,'e2e_task_director');await openReports();
  for(const id of [oldId,newId]){
    await page.getByRole('button',{name:`Consultar versión ${id}`,exact:true}).click();
    await page.getByLabel('Fundamento de la revisión').fill('Revisión sintética independiente.');
    await page.getByRole('button',{name:'Aprobar versión',exact:true}).click();
    await expect(page.getByText('Estado: Aprobado.',{exact:false})).toBeVisible();
    await expect(page.getByRole('button',{name:'Actualizar versiones',exact:true})).toBeEnabled();
  }
  await page.getByRole('button',{name:`Consultar versión ${oldId}`,exact:true}).click();
  await page.getByRole('button',{name:'Buscar sustitutos aprobados',exact:true}).click();
  await page.getByLabel('Informe aprobado sustituto').selectOption(newId);
  await page.getByLabel('Fundamento del retiro o sustitución').fill('Sustituir por versión aprobada corregida.');
  await page.getByRole('button',{name:'Registrar retiro o sustitución',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Informe sustituido',exact:true})).toBeVisible();
  await expect(page.getByText('Estado: Aprobado.',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'Consultar informe sustituto',exact:true}).click();
  await expect(title).toHaveText(`Versión conservada ${newId}`);
  await page.getByLabel('Fundamento del retiro o sustitución').fill('Retiro sintético sin borrar historia.');
  await page.getByRole('button',{name:'Registrar retiro o sustitución',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Informe retirado',exact:true})).toBeVisible();
});

test('avisos de decisiones: acuse personal con fecha simulada',async({page})=>{
  let acknowledged=false;
  await login(page,'e2e_task_manager');
  await page.route('**/api/v1/decisions/services/*/',async route=>{
    const response=await route.fetch();const body=await response.json();
    body.notices={calendar_confirmed:true,observed_day:'2026-10-14',timezone:'America/Merida',items:[{decision_id:987654,title:'Decisión sintética de aviso',due:'2026-10-09',decision_version:1,calendar_version:1,stage:2,working_days_late:2,acknowledged_at:acknowledged?'2026-10-14T12:00:00Z':null}]};
    await route.fulfill({response,json:body});
  });
  await page.route('**/api/v1/decisions/987654/acknowledge/',async route=>{
    expect(route.request().postDataJSON()).toEqual({decision_version:1,calendar_version:1,stage:2});
    acknowledged=true;await route.fulfill({json:{}});
  });
  await page.goto('/decisiones');
  await page.getByLabel('Servicio de las decisiones').selectOption({label:'Servicio seguimiento sintético · Sede seguimiento'});
  const notice=page.getByRole('article',{name:'Aviso de Decisión sintética de aviso'});
  await expect(notice.getByText(/Recordatorio desde el segundo/)).toBeVisible();
  await notice.getByRole('button',{name:'Marcar aviso 987654 como leído',exact:true}).click();
  await expect(notice.getByText(/Lectura registrada:/)).toBeVisible();
  await expect(notice.getByRole('button',{name:/Marcar aviso/})).toHaveCount(0);
  await expect(page.getByRole('status')).toHaveText('Lectura registrada; la decisión conserva su estado.');
});

test('suplencias: nombramiento temporal y revocación vinculada',async({page})=>{
  page.setDefaultTimeout(15000);
  await login(page,'e2e_coverage_director');await administration(page);
  await page.getByRole('button',{name:'Usuarios y nombramientos',exact:true}).click();
  const grant=page.locator('form').filter({has:page.getByRole('heading',{name:'Aprobar nombramiento',exact:true})});
  const sub=await grant.getByLabel('Persona',{exact:true}).locator('option').filter({hasText:'e2e_coverage_sub'}).getAttribute('value');
  await grant.getByLabel('Persona',{exact:true}).selectOption(sub!);
  await grant.getByLabel('Servicio del nombramiento').selectOption({label:'Servicio suplencias'});
  await grant.getByLabel('Rol autorizado').selectOption('contributor');
  const source=await grant.getByLabel('Nombramiento titular a suplir (opcional)').locator('option').filter({hasText:'e2e_coverage_holder'}).getAttribute('value');
  await grant.getByLabel('Nombramiento titular a suplir (opcional)').selectOption(source!);
  await grant.getByLabel('Inicio de vigencia').fill(process.env.E2E_START!);
  await grant.getByLabel('Fin de vigencia').fill(process.env.E2E_END!);
  await grant.getByLabel('Fundamento y competencia confirmada').fill('Cobertura temporal sintética autorizada.');
  await grant.getByRole('button',{name:'Aprobar nombramiento',exact:true}).click();
  await expect(page.getByRole('status')).toHaveText('Registro guardado.');
  await expect(page.getByText(`Suplencia del nombramiento #${source}`,{exact:true})).toBeVisible();
  const holder=page.locator('.row').filter({has:page.getByRole('heading',{name:/e2e_coverage_holder/})});
  await holder.getByLabel('Motivo de revocación').fill('Finaliza cobertura sintética del titular.');
  await holder.getByRole('button',{name:'Revocar nombramiento',exact:true}).click();
  const substitute=page.locator('.row').filter({has:page.getByRole('heading',{name:/e2e_coverage_sub/})});
  await expect(substitute.getByText(/Revocación del nombramiento titular/)).toBeVisible();
  await expect(substitute.getByRole('button',{name:'Revocar nombramiento',exact:true})).toHaveCount(0);
});

test('integración de suplencia: aviso interno y entrega de tarea con identidad propia',async({page})=>{
  page.setDefaultTimeout(15000);
  await login(page,'e2e_task_coverage');await page.goto('/seguimiento');
  await page.getByLabel('Servicio de seguimiento').selectOption({label:'Servicio cobertura de tareas · Sede cobertura'});
  await expect(page.getByText(/Suplencias vigentes: e2e_task_coverage/)).toBeVisible();
  await page.getByText(/Avisos internos \(1\)/).click();
  await expect(page.getByText(/Por suplencia vigente/)).toBeVisible();
  await page.getByRole('button',{name:/Revisar tarea \d+/}).click();
  await page.getByLabel('Resultado, bloqueo o fundamento').fill('Entrega realizada por suplente con identidad propia.');
  await page.getByRole('button',{name:'Entrega en revisión',exact:true}).click();
  await expect(page.getByText('Entrega realizada por suplente con identidad propia.',{exact:true})).toBeVisible();
});

test('programación semanal: dirección habilita y pausa sin enviar informes',async({page})=>{
 page.setDefaultTimeout(15000);
 await login(page,'e2e_task_director');await page.goto('/reportes');
 await page.getByLabel('Servicio del informe').selectOption({label:'Servicio seguimiento sintético · Sede seguimiento'});
 const schedule=page.getByRole('region',{name:'Programación de informes'});
 await schedule.getByLabel('Habilitar generación semanal de borradores').check();
 await schedule.getByLabel('Fundamento de programación').fill('Autorizar borradores semanales sintéticos.');
 await schedule.getByRole('button',{name:'Guardar programación',exact:true}).click();
 await expect(schedule.getByRole('status')).toContainText('Programación guardada');
 await expect(schedule.getByText(/Programación: Habilitada/)).toBeVisible();
 await page.reload();
 await page.getByLabel('Servicio del informe').selectOption({label:'Servicio seguimiento sintético · Sede seguimiento'});
 await expect(schedule.getByLabel('Habilitar generación semanal de borradores')).toBeChecked();
 await schedule.getByLabel('Habilitar generación semanal de borradores').uncheck();
 await schedule.getByLabel('Fundamento de programación').fill('Pausar generación sintética.');
 await schedule.getByRole('button',{name:'Guardar programación',exact:true}).click();
 await expect(schedule.getByText(/Programación: Pausada/)).toBeVisible();
 await expect(schedule.getByText('No hay ejecuciones con borrador conservado.',{exact:true})).toBeVisible();
});

test('recuperación semanal: formulario y resultado con respuesta simulada',async({page})=>{
 page.setDefaultTimeout(15000);
 await login(page,'e2e_task_director');await page.goto('/reportes');
 await page.getByLabel('Servicio del informe').selectOption({label:'Servicio seguimiento sintético · Sede seguimiento'});
 const schedule=page.getByRole('region',{name:'Programación de informes'});
 await schedule.getByLabel('Fundamento de programación').fill('Configurar recuperación sintética con programación pausada.');
 await schedule.getByRole('button',{name:'Guardar programación',exact:true}).click();
 await expect(schedule.getByRole('status')).toContainText('Programación guardada');
 await page.route('**/api/v1/reports/services/*/backfill/',async route=>{
   expect(route.request().postDataJSON()).toEqual({version:expect.any(Number),period:'2026-10-05',rationale:'Semana omitida sintética.'});
   await route.fulfill({status:201,json:{report_id:987654,created:true}});
 });
 await schedule.getByLabel('Lunes de la semana a recuperar').fill('2026-10-05');
 await schedule.getByLabel('Motivo de recuperación').fill('Semana omitida sintética.');
 await schedule.getByRole('button',{name:'Recuperar semana como borrador',exact:true}).click();
 await expect(schedule.getByRole('status')).toHaveText('Semana recuperada como borrador pendiente de revisión.');
 await expect(schedule.getByRole('link',{name:'Consultar o exportar informe recuperado 987654',exact:true})).toHaveAttribute('href','/api/v1/reports/saved/987654/');
});

test('distribución interna: aprobación, entrega y acuse personal del informe',async({page})=>{
 page.setDefaultTimeout(15000);
 async function reports(){await page.goto('/reportes');await page.getByLabel('Servicio del informe').selectOption({label:'Servicio seguimiento sintético · Sede seguimiento'});}
 await login(page,'e2e_task_manager');await reports();
 await page.getByLabel('Inicio de la versión a conservar').fill('2026-09-01');
 await page.getByRole('button',{name:'Generar y conservar versión',exact:true}).click();
 const heading=page.getByRole('heading',{name:/Versión conservada \d+/});await expect(heading).toBeVisible();
 const id=(await heading.innerText()).match(/\d+/)![0];
 await logout(page);await login(page,'e2e_task_director');await reports();
 await page.getByRole('button',{name:`Consultar versión ${id}`,exact:true}).click();
 await page.getByLabel('Fundamento de la revisión').fill('Revisión independiente sintética para distribución.');
 await page.getByRole('button',{name:'Aprobar versión',exact:true}).click();
 await page.route('**/api/v1/reports/saved/*/distribution/**',async route=>{
  if(route.request().method()!=='GET'){await route.continue();return;}
  const url=new URL(route.request().url());url.searchParams.set('page_size','1');
  const response=await route.fetch({url:url.toString()});await route.fulfill({response});
 });
 const distribution=page.getByRole('region',{name:'Distribución interna'});
 await distribution.getByRole('button',{name:'Consultar destinatarios y lecturas (Dirección)',exact:true}).click();
 while(!await distribution.getByLabel('e2e_task_manager',{exact:true}).count()){
  await distribution.getByRole('button',{name:'Cargar más destinatarios',exact:true}).click();
 }
 await distribution.getByLabel('e2e_task_manager',{exact:true}).check();
 const more=distribution.getByRole('button',{name:'Cargar más destinatarios',exact:true});
 while(await more.count())await more.click();
 await expect(distribution.getByLabel('e2e_task_manager',{exact:true})).toBeChecked();

 await distribution.getByLabel('Motivo de distribución').fill('Distribución sintética al responsable.');
 await distribution.getByRole('button',{name:'Distribuir en bandeja interna',exact:true}).click();
 await expect(distribution.getByRole('status')).toHaveText('Entregas nuevas: 1. Ya entregadas: 0.');
 await logout(page);await login(page,'e2e_task_manager');await page.goto('/reportes');
 const inbox=page.getByRole('region',{name:'Bandeja de informes'});
 await inbox.getByRole('button',{name:`Leer informe recibido ${id}`,exact:true}).click();
 await inbox.getByRole('button',{name:'Confirmar que leí este informe',exact:true}).click();
 await expect(inbox.getByRole('status')).toHaveText('Lectura confirmada para su cuenta. No modifica la aprobación del informe.');
 await logout(page);await login(page,'e2e_task_director');await reports();
 await page.getByRole('button',{name:`Consultar versión ${id}`,exact:true}).click();
 await distribution.getByRole('button',{name:'Consultar destinatarios y lecturas (Dirección)',exact:true}).click();
 await expect(distribution.getByText(/Lectura confirmada el/)).toBeVisible();
});

test('bandeja paginada: carga adicional y reinicio con respuestas simuladas',async({page})=>{
 await login(page,'e2e_task_manager');
 await page.route('**/api/v1/reports/inbox/**',async route=>{
  const next=new URL(route.request().url()).searchParams.get('before');
  if(next)expect(next).toBe('20');
  await route.fulfill({json:{results:[{id:next?10:20,report_id:next?910:920,service:'Servicio sintético paginado',period:'2026-09-01',availability:'retained',acknowledged_at:null,rationale:'Prueba'}],next_before:next?null:20}});
 });
 await page.goto('/reportes');
 const inbox=page.getByRole('region',{name:'Bandeja de informes'});
 await expect(inbox.getByRole('button',{name:'Leer informe recibido 920',exact:true})).toBeVisible();
 await inbox.getByRole('button',{name:'Cargar más informes recibidos',exact:true}).click();
 await expect(inbox.getByRole('button',{name:'Leer informe recibido 910',exact:true})).toBeVisible();
 await expect(inbox.getByRole('button',{name:'Leer informe recibido 920',exact:true})).toHaveCount(1);
 await expect(inbox.getByRole('button',{name:'Cargar más informes recibidos',exact:true})).toHaveCount(0);
 await inbox.getByRole('button',{name:'Actualizar bandeja',exact:true}).click();
 await expect(inbox.getByRole('button',{name:'Leer informe recibido 910',exact:true})).toHaveCount(0);
 await expect(inbox.getByRole('button',{name:'Cargar más informes recibidos',exact:true})).toBeVisible();
});

test('corrección de horas: conserva original y actualiza tiempo efectivo',async({page})=>{
 page.setDefaultTimeout(15000);
 await login(page,'e2e_time_author');await page.goto('/seguimiento');
 await page.getByLabel('Servicio de seguimiento').selectOption({label:'Servicio corrección de horas · Sede horas'});
 await page.getByRole('button',{name:/Tarea \d+: Tarea sintética de horas/}).click();
 await page.getByText('Actividad y tiempo registrado',{exact:true}).click();
 const entry=page.getByRole('article',{name:/Registro de horas/});
 await entry.getByLabel('Minutos corregidos',{exact:true}).fill('25');
 await entry.getByLabel('Motivo del ajuste',{exact:true}).fill('Corregir duplicación sintética.');
 await entry.getByRole('button',{name:'Guardar corrección de horas',exact:true}).click();
 await expect(entry.getByText(/25 minutos efectivos; original: 60/)).toBeVisible();
 await expect(entry.getByText(/Ajuste 1: 25 minutos/)).toContainText('Corregir duplicación sintética.');
 await entry.getByLabel('Minutos corregidos',{exact:true}).fill('0');
 await entry.getByLabel('Motivo del ajuste',{exact:true}).fill('Anulación sintética conservando historial.');
 await entry.getByRole('button',{name:'Guardar corrección de horas',exact:true}).click();
 await expect(entry.getByText(/0 minutos efectivos; original: 60/)).toBeVisible();
 await expect(entry.getByText(/Ajuste 1: 25 minutos/)).toBeVisible();
 await expect(entry.getByText(/Ajuste 2: 0 minutos/)).toBeVisible();
});

test('planificación de tareas: capacidad aprobada, ausencia y sobrecarga',async({page})=>{
 page.setDefaultTimeout(15000);
 await login(page,'e2e_time_author');await page.goto('/seguimiento');
 await page.getByLabel('Servicio de seguimiento').selectOption({label:'Servicio corrección de horas · Sede horas'});
 const panel=page.getByRole('region',{name:'Capacidad para tareas'});
 await panel.getByLabel('Inicio de semana para capacidad').fill('2026-10-01');
 await panel.getByRole('button',{name:'Comparar tareas con capacidad',exact:true}).click();
 await expect(panel.getByText('e2e_time_author · 2026-10-01: Sobrecarga',{exact:true})).toBeVisible();
 await expect(panel.getByText(/Carga estimada: 40 min · Asignación aprobada al servicio: 30 min · Exceso: 10 min/)).toContainText('Con indisponibilidad aprobada');
 await expect(panel.getByText('e2e_time_author · 2026-10-02: Sin capacidad aprobada',{exact:true})).toBeVisible();
 await expect(panel.getByText('e2e_time_author · 2026-10-05: Sin capacidad aprobada',{exact:true})).toBeVisible();
});

test('reservas: simular, aprobar y consultar presupuesto institucional',async({page})=>{
 page.setDefaultTimeout(15000);
 await login(page,'e2e_reservation_director');await page.goto('/seguimiento');
 await page.getByLabel('Servicio de seguimiento').selectOption({label:'Servicio reservas · Sede reservas'});
 await page.getByRole('button',{name:/Tarea \d+: Tarea con reserva sintética/}).click();
 await page.getByRole('button',{name:/Simular aprobación \d+/}).click();
 await expect(page.getByRole('status').filter({hasText:'La propuesta puede aprobarse'})).toBeVisible();
 await page.getByLabel('Resultado, bloqueo o fundamento').fill('Aprobación independiente con capacidad confirmada.');
 await page.getByRole('button',{name:/Aprobar cambio \d+/}).click();
 await expect(page.getByRole('status').filter({hasText:'Registro guardado'})).toBeVisible();
 const history=page.getByRole('region',{name:'Historial completo de tarea'});
 await history.getByRole('button',{name:'Consultar historial completo',exact:true}).click();
 await expect(history.getByText('Aprobación independiente con capacidad confirmada.',{exact:true})).toBeVisible();
 await page.goto('/capacidad');
 await page.getByRole('combobox',{name:'Institución de la capacidad',exact:true}).selectOption({label:'Institución reservas sintéticas'});
 const control=page.getByRole('region',{name:'Control institucional de planificación'});
 await control.getByRole('button',{name:'Consultar presupuesto y conflictos',exact:true}).click();
 await expect(control.getByText(/Reserva: comprometidos 120 min · reales 0 min · aprobados 200 min · saldo disponible 80 min/)).toBeVisible();
 await page.screenshot({path:'../entregas/cierre-gestor-2026-09-28/presupuesto-sintetico.png',fullPage:true});
});

test('fuente: propuesta y revisión independiente conservan cambio explícito',async({page})=>{
 page.setDefaultTimeout(15000);
 async function openSource(){await administration(page);await page.getByRole('button',{name:'Cuestionarios y ayudas',exact:true}).click();await page.getByLabel('Servicio del cuestionario').selectOption({label:'Servicio reservas · Sede reservas'});}
 await login(page,'e2e_reservation_manager');await openSource();
 const panel=page.getByRole('region',{name:'Cambio de fuente'});
 await panel.getByRole('button',{name:'Consultar cambios de fuente (Dirección)',exact:true}).click();
 await panel.getByRole('combobox',{name:'Nueva versión de fuente',exact:true}).selectOption({label:'Versión 2: Pregunta sintética fuente 2'});
 await panel.getByLabel('Motivo del cambio de fuente',{exact:true}).fill('Revisión sintética de alcance.');
 await panel.getByRole('button',{name:'Proponer cambio de fuente',exact:true}).click();
 await expect(panel.getByRole('status')).toHaveText('Cambio de fuente propuesto; pendiente de revisión independiente.');
 await logout(page);await login(page,'e2e_reservation_director');await openSource();
 await panel.getByRole('button',{name:'Consultar cambios de fuente (Dirección)',exact:true}).click();
 await panel.getByLabel('Fundamento de revisión de fuente',{exact:true}).fill('Cambio sintético revisado por otra persona.');
 await panel.getByRole('button',{name:/Aprobar cambio de fuente \d+/}).click();
 await expect(panel.getByRole('status')).toHaveText('Fuente actualizada; publicación y validación retiradas.');
 await expect(page.getByRole('heading',{name:'Pregunta sintética fuente 2',exact:true})).toBeVisible();
});

test('corrección administrativa: solicitud, revisión independiente e historial',async({page})=>{
 page.setDefaultTimeout(15000);
 async function openTask(){
  await page.goto('/seguimiento');
  await page.getByLabel('Servicio de seguimiento').selectOption({label:'Servicio ajustes administrativos · Sede horas'});
  await page.getByRole('button',{name:/Tarea \d+: Tarea de ajuste administrativo/}).click();
  await page.getByText('Actividad y tiempo registrado',{exact:true}).click();
 }
 await login(page,'e2e_admin_hours_requester');await openTask();
 const entry=page.getByRole('article',{name:/Registro de horas/});
 await entry.getByLabel('Minutos propuestos',{exact:true}).fill('25');
 await entry.getByLabel('Justificación administrativa',{exact:true}).fill('Duplicación comprobada en registro sintético.');
 await entry.getByRole('button',{name:'Solicitar corrección administrativa',exact:true}).click();
 await expect(entry.getByRole('status')).toContainText('registrada');
 await expect(entry.getByText(/60 minutos efectivos; original: 60/)).toBeVisible();
 const requests=page.getByRole('region',{name:'Correcciones administrativas de horas'});
 await requests.getByRole('button',{name:'Consultar solicitudes de corrección',exact:true}).click();
 await expect(requests.getByRole('article')).toContainText('Pendiente');
 await expect(requests.getByRole('button',{name:/Aprobar corrección/})).toHaveCount(0);
 await logout(page);await login(page,'e2e_admin_hours_reviewer');await openTask();
 await requests.getByRole('button',{name:'Consultar solicitudes de corrección',exact:true}).click();
 await requests.getByLabel(/Motivo de revisión de solicitud/).fill('Comprobación independiente del respaldo sintético.');
 await requests.getByRole('button',{name:/Aprobar corrección/}).click();
 await expect(requests.getByRole('article')).toContainText('Aprobada');
 await expect(entry.getByText(/25 minutos efectivos; original: 60/)).toBeVisible();
 await logout(page);await login(page,'e2e_admin_hours_author');await openTask();
 await expect(entry.getByText(/25 minutos efectivos; original: 60/)).toBeVisible();
 await requests.getByRole('button',{name:'Consultar solicitudes de corrección',exact:true}).click();
 await expect(requests.getByRole('article')).toContainText('e2e_admin_hours_requester');
 await expect(requests.getByRole('article')).toContainText('e2e_admin_hours_reviewer');
 await expect(requests.getByRole('button',{name:/Aprobar corrección/})).toHaveCount(0);
});

test('recuperación excepcional: doble autorización y nuevo autenticador obligatorio',async({page})=>{
 page.setDefaultTimeout(15000);
 const codes=JSON.parse(readFileSync(`${process.env.E2E_WORKDIR}/exceptional-recovery.json`,'utf8'));
 async function passwordLogin(username:string){await page.goto('/personal/plan');await page.getByLabel('Usuario',{exact:true}).fill(username);await page.getByLabel('Contraseña',{exact:true}).fill(password);await page.getByRole('button',{name:'Ingresar',exact:true}).click();await expect(page.getByRole('heading',{name:'Verificación en dos pasos',exact:true})).toBeVisible();}
 async function authorityLogin(username:string){await passwordLogin(username);await page.getByLabel('Código de verificación o recuperación',{exact:true}).fill(codes[username]);await page.getByRole('button',{name:'Verificar acceso',exact:true}).click();await expect(page.getByRole('heading',{name:'Mi trabajo de hoy',exact:true})).toBeVisible();await page.goto('/seguridad');}
 await authorityLogin('e2e_recovery_requester');
 const panel=page.getByRole('region',{name:'Recuperación excepcional de acceso',exact:true});
 await panel.getByRole('button',{name:'Consultar recuperaciones institucionales',exact:true}).click();
 await panel.getByLabel('Usuario que perdió su autenticador',{exact:true}).fill('e2e_recovery_target');
 await panel.getByLabel('Motivo de la recuperación',{exact:true}).fill('Pérdida sintética del dispositivo y códigos.');
 await panel.getByLabel('Referencia de verificación de identidad',{exact:true}).fill('VERIFICACION-SINTETICA-1');
 await panel.getByRole('button',{name:'Registrar solicitud de recuperación',exact:true}).click();
 await expect(panel.getByRole('article')).toContainText('Pendiente');
 await expect(panel.getByRole('button',{name:/Aprobar recuperación/})).toHaveCount(0);
 await logout(page);await authorityLogin('e2e_recovery_reviewer');
 await panel.getByRole('button',{name:'Consultar recuperaciones institucionales',exact:true}).click();
 await panel.getByLabel(/Motivo de decisión/).fill('Verificación independiente sintética completada.');
 await panel.getByLabel(/Referencia de verificación independiente/).fill('VERIFICACION-SINTETICA-2');
 await panel.getByRole('button',{name:/Aprobar recuperación/}).click();
 const token=await page.getByTestId('exceptional-token').innerText();
 await expect(panel.getByRole('article')).toContainText('Aprobada');
 await panel.getByRole('button',{name:'Ocultar código entregado',exact:true}).click();
 await panel.getByRole('button',{name:'Consultar recuperaciones institucionales',exact:true}).click();
 await expect(page.getByTestId('exceptional-token')).toHaveCount(0);
 await logout(page);await passwordLogin('e2e_recovery_target');
 await page.getByLabel('Contraseña de la cuenta',{exact:true}).fill(password);
 await page.getByLabel('Código excepcional de un solo uso',{exact:true}).fill(token);
 await page.getByRole('button',{name:'Canjear código excepcional',exact:true}).click();
 await expect(page.getByText(/Configure y confirme ahora su nuevo autenticador/)).toBeVisible();
 const denied=await page.request.get('/api/v1/services/');expect(denied.status()).toBe(403);
 await page.getByLabel('Confirme su contraseña',{exact:true}).fill(password);
 await page.getByRole('button',{name:'Preparar autenticador',exact:true}).click();
 const secret=await page.getByTestId('mfa-secret').innerText();
 const {createHmac}=await import('node:crypto');const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';let bits='';
 for(const letter of secret)bits+=alphabet.indexOf(letter).toString(2).padStart(5,'0');
 const key=Buffer.from(bits.match(/.{8}/g)!.map(v=>parseInt(v,2)));const counter=Buffer.alloc(8);counter.writeBigUInt64BE(BigInt(Math.floor(Date.now()/30000)));const digest=createHmac('sha1',key).update(counter).digest();const offset=digest[19]&15;const code=((digest.readUInt32BE(offset)&0x7fffffff)%1000000).toString().padStart(6,'0');
 await page.getByLabel('Código del autenticador',{exact:true}).fill(code);
 await page.getByRole('button',{name:'Confirmar autenticador',exact:true}).click();
 await expect(page.getByRole('list',{name:'Códigos de recuperación'}).locator('code')).toHaveCount(8);
 await page.getByRole('button',{name:'Guardé mis códigos; continuar',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Mi trabajo de hoy',exact:true})).toBeVisible();
});

test('archivo de informes: páginas antiguas, sustitutos e historial completo',async({page})=>{
 page.setDefaultTimeout(15000);
 const fixture=JSON.parse(readFileSync(`${process.env.E2E_WORKDIR}/report-history.json`,'utf8'));
 await login(page,'e2e_archive_director');await page.goto('/reportes');
 await page.getByLabel('Servicio del informe').selectOption({label:'Servicio archivo sintético · Sede archivo'});
 const saved=page.getByRole('region',{name:'Informes conservados',exact:true});
 await expect(saved.getByRole('button',{name:`Consultar versión ${fixture.oldest}`,exact:true})).toHaveCount(0);
 for(let i=0;i<2;i++)await saved.getByRole('button',{name:'Cargar más versiones conservadas',exact:true}).click();
 await expect(saved.getByRole('button',{name:`Consultar versión ${fixture.oldest}`,exact:true})).toBeVisible();
 await saved.getByRole('button',{name:`Consultar versión ${fixture.source}`,exact:true}).click();
 await saved.getByRole('button',{name:'Buscar sustitutos aprobados',exact:true}).click();
 await expect(saved.getByLabel('Informe aprobado sustituto').locator(`option[value="${fixture.oldest}"]`)).toHaveCount(0);
 await saved.getByRole('button',{name:'Cargar más sustitutos aprobados',exact:true}).click();
 await saved.getByLabel('Informe aprobado sustituto').selectOption(String(fixture.oldest));
 await saved.getByLabel('Fundamento del retiro o sustitución').fill('Sustituir con versión antigua verificada del archivo sintético.');
 await saved.getByRole('button',{name:'Registrar retiro o sustitución',exact:true}).click();
 await expect(saved.getByRole('heading',{name:'Informe sustituido',exact:true})).toBeVisible();
 await saved.getByRole('button',{name:'Consultar informe sustituto',exact:true}).click();
 await expect(saved.getByRole('heading',{name:`Versión conservada ${fixture.oldest}`,exact:true})).toBeVisible();
 const history=page.getByRole('region',{name:'Historial de borradores programados',exact:true});
 await history.getByRole('button',{name:'Consultar historial de borradores',exact:true}).click();
 await expect(history.getByRole('link',{name:`Consultar informe histórico ${fixture.oldest_run_report}`,exact:true})).toHaveCount(0);
 await history.getByRole('button',{name:'Cargar más borradores históricos',exact:true}).click();
 await expect(history.getByRole('link',{name:`Consultar informe histórico ${fixture.oldest_run_report}`,exact:true})).toBeVisible();
 await expect(history.getByRole('button',{name:'Cargar más borradores históricos',exact:true})).toHaveCount(0);
 await saved.getByRole('button',{name:'Actualizar versiones',exact:true}).click();
 await expect(saved.getByRole('button',{name:`Consultar versión ${fixture.oldest}`,exact:true})).toHaveCount(0);
});
