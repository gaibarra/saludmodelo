let csrf = "";
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const form = data instanceof FormData;
  const r = await fetch("/api/v1/" + path, {
    method,
    credentials: "same-origin",
    headers: {
      ...(!form ? { "Content-Type": "application/json" } : {}),
      "X-CSRFToken": csrf,
    },
    body: data ? (form ? data : JSON.stringify(data)) : undefined,
  });
  if (!r.ok) {
    const e = await r
      .json()
      .catch(() => ({ detail: "No se pudo conectar. Intente de nuevo." }));
    throw new Error(
      r.status === 409
        ? "Hay cambios de otra persona. Su texto sigue en pantalla; cópielo y recargue para comparar."
        : JSON.stringify(e),
    );
  }
  return r.status === 204 ? (undefined as T) : r.json();
}
export async function listApi<T>(path: string): Promise<T[]> {
  const results: T[] = [];
  let next: string | null = path;
  while (next) {
    const page: { results: T[]; next: string | null } = await api(next);
    results.push(...page.results);
    next = page.next
      ? new URL(page.next, window.location.origin).pathname.replace(
          "/api/v1/",
          "",
        ) + new URL(page.next, window.location.origin).search
      : null;
  }
  return results;
}

export function setCsrf(value: string) {
  csrf = value;
}
