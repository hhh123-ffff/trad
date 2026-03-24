/** Query value type supported by API helper. */
type QueryValue = string | number | boolean | null | undefined;

/** Backend error response structure from FastAPI custom handler. */
interface ApiErrorPayload {
  success?: boolean;
  error?: string;
  details?: unknown;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

/** Build URL query string from plain key-value object. */
function buildQueryString(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

/** Parse backend error payload into readable string. */
async function parseApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    if (payload.error) {
      return payload.error;
    }
  } catch {
    // Ignore JSON parsing issues and fall back to status text.
  }
  return `Request failed with status ${response.status}`;
}

/** Execute GET request against backend API. */
export async function apiGet<T>(path: string, params: Record<string, QueryValue> = {}): Promise<T> {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const query = buildQueryString(params);
  const response = await fetch(`${API_BASE}${normalized}${query}`, {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as T;
}

/** Execute POST request against backend API. */
export async function apiPost<TResponse, TPayload>(path: string, payload: TPayload): Promise<TResponse> {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const response = await fetch(`${API_BASE}${normalized}`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as TResponse;
}
