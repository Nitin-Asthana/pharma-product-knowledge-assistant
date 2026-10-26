import type {
  Citation,
  Health,
  Product,
  ProductSummary,
  ResponseStyle,
  Source,
  SourceStatus,
  Stats,
} from "../types";

// API base is empty by default so the Vite dev proxy (and same-origin
// production hosting) handle routing. Override with VITE_API_BASE if the
// backend is hosted elsewhere.
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status}): ${path}`);
  }
  return res.json() as Promise<T>;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Request failed (${res.status}): ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => getJSON<Health>("/health"),
  stats: () => getJSON<Stats>("/api/stats"),
  sources: () => getJSON<{ sources: Source[] }>("/api/sources"),
  sourcesStatus: () => getJSON<{ sources: SourceStatus[] }>("/api/sources/status"),
  categories: (sourceId?: string) =>
    getJSON<{ categories: { therapeutic_category: string; product_count: number }[] }>(
      `/api/categories${sourceId ? `?source_id=${encodeURIComponent(sourceId)}` : ""}`
    ),
  ingredients: (sourceId?: string) =>
    getJSON<{ ingredients: string[] }>(
      `/api/ingredients${sourceId ? `?source_id=${encodeURIComponent(sourceId)}` : ""}`
    ),
  products: (params: {
    source_id?: string;
    category?: string;
    ingredient?: string;
    q?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params.source_id) qs.set("source_id", params.source_id);
    if (params.category) qs.set("category", params.category);
    if (params.ingredient) qs.set("ingredient", params.ingredient);
    if (params.q) qs.set("q", params.q);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return getJSON<{ count: number; products: ProductSummary[] }>(
      `/api/products${suffix}`
    );
  },
  product: (productId: string) =>
    getJSON<Product>(`/api/products/${encodeURIComponent(productId)}`),
  chat: (body: {
    message: string;
    conversation_id?: string | null;
    response_style: ResponseStyle;
    source_ids: string[];
  }) => postJSON<import("../types").ChatResponse>("/api/chat", body),
};

// Streaming chat via Server-Sent Events over a POST body. We use fetch with a
// ReadableStream reader because EventSource does not support POST.
export interface StreamHandlers {
  onStatus?: (stage: string) => void;
  onToken?: (text: string) => void;
  onDone?: (payload: {
    citations: Citation[];
    products: string[];
    intent: string;
    retrieval_mode: string;
    conversation_id: string;
  }) => void;
  onError?: (err: Error) => void;
}

export async function streamChat(
  body: {
    message: string;
    conversation_id?: string | null;
    response_style: ResponseStyle;
    source_ids: string[];
  },
  handlers: StreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    handlers.onError?.(new Error(`Stream failed (${res.status})`));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (rawEvent: string) => {
    const lines = rawEvent.split("\n");
    let event = "message";
    const dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (dataLines.length === 0) return;
    let data: unknown;
    try {
      data = JSON.parse(dataLines.join("\n"));
    } catch {
      return;
    }
    if (event === "status") handlers.onStatus?.((data as { stage: string }).stage);
    else if (event === "token") handlers.onToken?.((data as { text: string }).text);
    else if (event === "done")
      handlers.onDone?.(data as Parameters<NonNullable<StreamHandlers["onDone"]>>[0]);
  };

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // Normalize CR out so event boundaries are detected regardless of whether
    // the server (sse-starlette) separates events with \r\n\r\n or \n\n. Stripping
    // all CR is safe for text/JSON SSE payloads and robust across chunk splits.
    buffer += decoder.decode(value, { stream: true }).replace(/\r/g, "");
    let idx: number;
    // SSE events are separated by a blank line.
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      dispatch(rawEvent);
    }
  }
}
