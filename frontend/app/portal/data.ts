export const services = [
  { slug: "odontologia", name: "Odontología", icon: "✦", summary: "Cuidado y prevención de la salud bucal.", detail: "Solicita orientación o atención odontológica. El equipo del servicio revisará tu solicitud y confirmará si hay disponibilidad." },
  { slug: "fisioterapia", name: "Fisioterapia", icon: "◈", summary: "Movimiento, bienestar y rehabilitación.", detail: "Consulta la posibilidad de recibir atención de fisioterapia. El servicio te indicará el siguiente paso." },
  { slug: "nutricion", name: "Nutrición", icon: "◉", summary: "Orientación para tus hábitos de alimentación.", detail: "Solicita información y orientación nutricional. El servicio confirmará la disponibilidad antes de asignar una cita." },
  { slug: "psicologia", name: "Psicología", icon: "♡", summary: "Atención psicológica en La Casita.", detail: "La Escuela de Salud incorpora la atención psicológica de la Unidad de Servicios Comunitarios La Casita. Consulta el contacto de la unidad para confirmar disponibilidad y modalidades actuales. Las solicitudes en la aplicación se habilitarán cuando el servicio confirme su operación." },
  { slug: "ciencias-del-deporte", name: "Ciencias del deporte", icon: "↗", summary: "Actividad física, evaluación y desempeño.", detail: "Conoce las posibilidades de atención en Ciencias del deporte y envía una solicitud al equipo." },
  { slug: "atencion-comunitaria", name: "Atención comunitaria", icon: "✳", summary: "Servicios de La Casita.", detail: "Atención Comunitaria es un servicio de la Escuela de Salud en La Casita, con administración separada de Psicología. Consulta las actividades y disponibilidad con el equipo de la unidad." },
] as const;
export type ServiceSlug = (typeof services)[number]["slug"];
export function serviceName(slug: string) { return services.find(s => s.slug === slug)?.name || slug; }
export const siteName: Record<string,string> = { cholul: "Cholul", casita: "Casita", indistinta: "Cualquiera" };
export const statusName: Record<string,string> = { pending: "Pendiente de confirmación", confirmed: "Confirmada", declined: "Sin disponibilidad", withdrawn: "Retirada" };
