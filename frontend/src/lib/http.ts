/**
 * Lightweight HTTP helper for the Cortex frontend.
 *
 * - Injects base URL from Vite env.
 * - Automatically attaches Authorization header if a token provider is configured.
 * - Parses JSON.
 * - Throws a typed ApiError on non-2xx responses.
 */

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface RequestOptions {
  method?: HttpMethod;
  headers?: Record<string, string>;
  /** Query parameters that will be encoded into the URL */
  query?: Record<string, string | number | boolean | null | undefined>;
  /** Request body; will be JSON.stringified if not undefined */
  body?: unknown;
  /** Optional AbortSignal from the caller (React Query, custom hook, etc.) */
  signal?: AbortSignal;
}

/**
 * Shape of an error payload returned by the Cortex backend.
 * Kept deliberately generic; backends can include arbitrary `details`.
 */
export interface ApiErrorPayload {
  message: string;
  code?: string;
  details?: unknown;
}

/**
 * Error thrown for any non-2xx HTTP response.
 * React code can narrow on `instanceof ApiError` for error UIs.
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly code?: string;
  public readonly details?: unknown;

  constructor(params: { message: string; status: number; code?: string; details?: unknown }) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.code = params.code;
    this.details = params.details;
  }
}

// Base URL & auth token are configurable at runtime, but default to Vite env + localStorage.
let apiBaseUrl: string =
  (import.meta as any).env?.VITE_CORTEX_API_BASE_URL ?? "http://localhost:8000";

type AuthTokenProvider = () => string | null | undefined;

let authTokenProvider: AuthTokenProvider | null = () =>
  typeof window !== "undefined"
    ? window.localStorage.getItem("cortex_auth_token")
    : null;

/**
 * Override the API base URL (e.g., in tests or storybook).
 * The trailing slash is stripped to make path joins predictable.
 */
export function setApiBaseUrl(url: string) {
  apiBaseUrl = url.replace(/\/+$/, "");
}

/**
 * Override how we obtain the auth token.
 * Useful for wiring to a dedicated auth store instead of localStorage.
 */
export function setAuthTokenProvider(provider: AuthTokenProvider | null) {
  authTokenProvider = provider;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const normalizedBase = apiBaseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(normalizedBase + normalizedPath);

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null) continue;
      url.searchParams.append(key, String(value));
    }
  }

  return url.toString();
}

async function parseJsonSafe(response: Response): Promise<any | undefined> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) return undefined;

  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

/**
 * Core HTTP function.
 *
 * Components should NEVER call this directly.
 * Instead, use the typed functions in `cortexApi.ts` or feature-specific hooks.
 */
export async function http<TResponse = unknown>(
  path: string,
  options: RequestOptions = {}
): Promise<TResponse> {
  const { method = "GET", headers = {}, query, body, signal } = options;

  const url = buildUrl(path, query);

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };

  if (body !== undefined && !(body instanceof FormData)) {
    finalHeaders["Content-Type"] = finalHeaders["Content-Type"] ?? "application/json";
  }

  const token = authTokenProvider ? authTokenProvider() : null;
  if (token) {
    finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  const init: RequestInit = {
    method,
    headers: finalHeaders,
    signal,
  };

  if (body !== undefined) {
    init.body = body instanceof FormData ? body : JSON.stringify(body);
  }

  const response = await fetch(url, init);

  if (!response.ok) {
    const payload = (await parseJsonSafe(response)) as ApiErrorPayload | undefined;
    const message =
      payload?.message ||
      `Request to ${url} failed with status ${response.status} ${response.statusText}`;

    throw new ApiError({
      message,
      status: response.status,
      code: payload?.code,
      details: payload?.details ?? payload,
    });
  }

  if (response.status === 204) {
    // No Content
    return undefined as TResponse;
  }

  const data = await parseJsonSafe(response);
  return data as TResponse;
}
