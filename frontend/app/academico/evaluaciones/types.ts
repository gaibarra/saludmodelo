export type Cycle = {
  school: number | null;
  school_name: string;
  id: number;
  institution: number;
  code: string;
  name: string;
  starts: string;
  ends: string;
  revision: number;
  closed_at: string | null;
  closed_report: number | null;
  can_manage: boolean;
};
export type Placement = {
  id: number;
  student: number;
  student_name: string;
  enrollment: string;
  program: string;
  cycle: number;
  service: number;
  service_name: string;
  site_name: string;
  group: string;
  supervisor_name: string;
  revoked_at: string | null;
};
export type Level = { label: string; description: string };
export type Rubric = {
  id: number;
  competency: number;
  cycle: number;
  service: number;
  service_name: string;
  program: string;
  code: string;
  version: number;
  title: string;
  criterion: string;
  levels: Level[];
  required_level: number;
  required: boolean;
  author: string;
  rationale: string;
  created_at: string;
};
export type Evaluation = {
  id: number;
  placement: number;
  competency: number;
  rubric: number;
  version: number;
  score: number;
  rationale: string;
  evidence: { practice: number; version: number }[];
  evaluator: string;
  created_at: string;
  rubric_snapshot: Rubric;
};
export type Assessment = {
  rubric: Rubric;
  evaluation: Evaluation | null;
  state: string;
};
export type Totals = Record<
  string,
  { participations: number; minutes: number }
>;
export type Practice = {
  id: number;
  version: number;
  title: string;
  performed_on: string;
  minutes: number;
  competency: string;
  evidence_reference: string;
  activity_reference: string;
  status: string;
  history: {
    version: number;
    action: string;
    actor: string;
    rationale: string;
    snapshot: Record<string, string | number>;
    created_at: string;
  }[];
};
export type PlacementReport = {
  id: number;
  service: number;
  service_name: string;
  site_name: string;
  group: string;
  supervisor: string;
  starts: string;
  ends: string;
  target_minutes: number | null;
  revoked_at: string | null;
  revocation_reason: string;
  totals: Totals;
  practices: Practice[];
  competencies: (Assessment & { history: Evaluation[] })[];
  issues: string[];
};
export type StudentReport = {
  id: number;
  name: string;
  enrollment: string;
  program: string;
  placements: PlacementReport[];
  totals: Totals;
  issues: string[];
};
export type Report = {
  school: number | null;
  school_name: string;
  id: number;
  cycle: number;
  cycle_name: string;
  sequence: number;
  kind: string;
  created_at: string;
  created_by: string;
  closed_at: string | null;
  closed_by: string | null;
  close_reason: string;
  current_closure: boolean;
  stale: boolean;
  issues_count: number;
  can_close: boolean;
  can_reopen: boolean;
  digest: string;
  snapshot?: {
    cycle: {
      id: number;
      institution: string;
      school_name?: string;
      code: string;
      name: string;
      starts: string;
      ends: string;
      source_revision: number;
    };
    students: StudentReport[];
    services: {
      id: number;
      name: string;
      site_name: string;
      students: number;
      totals: Totals;
    }[];
    totals: Totals;
    issues: string[];
    coverage: string;
    automatic_accreditation: boolean;
  };
};
export const states: Record<string, string> = {
  not_evaluated: "Sin evaluar",
  needs_review: "Requiere nueva revisión",
  achieved: "Nivel requerido alcanzado",
  not_achieved: "Nivel requerido no alcanzado",
  submitted: "Por revisar",
  returned: "Devuelta",
  validated: "Validada",
  void: "Anulada",
  resubmitted: "Corregida y enviada",
  validate: "Validada",
  return: "Devuelta",
};
export const hours = (minutes: number) =>
  `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
export function errorText(error: unknown) {
  const m = (error as Error).message;
  try {
    const e = JSON.parse(m);
    return typeof e === "string"
      ? e
      : Object.entries(e)
          .map(
            ([k, v]) =>
              `${k === "detail" ? "" : k + ": "}${Array.isArray(v) ? v.join(" ") : typeof v === "object" ? JSON.stringify(v) : v}`,
          )
          .join("\n");
  } catch {
    return m;
  }
}
