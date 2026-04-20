const PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";
const INTERNAL_API_BASE = process.env.INTERNAL_API_BASE ?? PUBLIC_API_BASE;
const API_BASE = typeof window === "undefined" ? INTERNAL_API_BASE : PUBLIC_API_BASE;
const DEFAULT_SERVER_REVALIDATE_SECONDS = parseNonNegativeInt(process.env.API_SERVER_REVALIDATE_SECONDS, 60);
const DEFAULT_CLIENT_CACHE_TTL_MS = parseNonNegativeInt(process.env.NEXT_PUBLIC_API_CLIENT_CACHE_TTL_MS, 15000);

type ApiResponse<T> = {
  meta?: Record<string, unknown>;
  data: T[];
};

type ApiGetOptions = {
  revalidateSeconds?: number;
  clientTtlMs?: number;
  forceRefresh?: boolean;
};

type CachedEntry = {
  expiresAt: number;
  payload: ApiResponse<unknown>;
};

const browserCache = new Map<string, CachedEntry>();
const inFlight = new Map<string, Promise<ApiResponse<unknown>>>();

function parseNonNegativeInt(input: string | undefined, fallback: number): number {
  const n = Number(input);
  if (!Number.isFinite(n) || n < 0) return fallback;
  return Math.floor(n);
}

function cloneResponse<T>(value: ApiResponse<unknown>): ApiResponse<T> {
  if (typeof structuredClone === "function") {
    return structuredClone(value) as ApiResponse<T>;
  }
  return JSON.parse(JSON.stringify(value)) as ApiResponse<T>;
}

export async function apiGet<T>(path: string, options: ApiGetOptions = {}): Promise<ApiResponse<T>> {
  const url = `${API_BASE}${path}`;
  const isBrowser = typeof window !== "undefined";
  const clientTtlMs = options.clientTtlMs ?? DEFAULT_CLIENT_CACHE_TTL_MS;
  const forceRefresh = options.forceRefresh ?? false;

  if (isBrowser && clientTtlMs > 0 && !forceRefresh) {
    const cached = browserCache.get(url);
    if (cached && cached.expiresAt > Date.now()) {
      return cloneResponse<T>(cached.payload);
    }
    if (cached) {
      browserCache.delete(url);
    }

    const pending = inFlight.get(url);
    if (pending) {
      return (await pending) as ApiResponse<T>;
    }
  }

  const requestInit: RequestInit & { next?: { revalidate: number } } = {};
  if (isBrowser) {
    requestInit.cache = "default";
  } else {
    const revalidateSeconds = options.revalidateSeconds ?? DEFAULT_SERVER_REVALIDATE_SECONDS;
    if (revalidateSeconds > 0) {
      requestInit.next = { revalidate: revalidateSeconds };
    } else {
      requestInit.cache = "no-store";
    }
  }

  const requestPromise = (async () => {
    const response = await fetch(url, requestInit);
    if (!response.ok) {
      return { meta: { error: `HTTP ${response.status}` }, data: [] as T[] };
    }
    const payload = (await response.json()) as ApiResponse<T>;
    if (isBrowser && clientTtlMs > 0) {
      browserCache.set(url, {
        expiresAt: Date.now() + clientTtlMs,
        payload: cloneResponse<unknown>(payload as ApiResponse<unknown>),
      });
    }
    return payload;
  })();

  if (isBrowser && clientTtlMs > 0) {
    inFlight.set(url, requestPromise as Promise<ApiResponse<unknown>>);
    try {
      return await requestPromise;
    } finally {
      inFlight.delete(url);
    }
  }

  return requestPromise;
}

export async function apiPost<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    return { meta: { error: `HTTP ${response.status}` }, data: [] };
  }
  return (await response.json()) as ApiResponse<T>;
}
