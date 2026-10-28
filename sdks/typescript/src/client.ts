/**
 * BeeClient - dependency-free TypeScript SDK for Bee.
 *
 * Usage:
 *
 *   import { BeeClient } from "@heossihq/bee";
 *
 *   const bee = new BeeClient({ apiKey: process.env.BEE_API_KEY! });
 *
 *   const out = await bee.chat.completions.create({
 *     model: "bee-cell",
 *     messages: [{ role: "user", content: "Hello." }],
 *   });
 *   console.log(out.choices[0].message.content);
 *
 * The SDK targets api.bee.heossi.com/bee/* (the public API proxy). Override `baseURL` to point at a self-hosted Bee Enclave or
 * a staging environment.
 */

import {
  BeeActionRequiredError,
  BeeAuthError,
  BeeError,
  BeeRateLimitError,
  BeeTimeoutError,
} from "./errors.js";
import type {
  BeeUpgradeDecision,
  ChatCompletion,
  ChatCompletionChunk,
  ChatCompletionCreateParams,
  ChatMessage,
  ComputerUseActionRequest,
  ComputerUseHostReport,
  ComputerUseHostReportValidation,
  ModelsListResponse,
  ProvenanceResult,
  QuantumReasoningCapabilities,
  QuantumReasoningJob,
  QuantumReasoningJobCreateParams,
  UsageResponse,
} from "./types.js";

const DEFAULT_BASE_URL = "https://api.bee.heossi.com/bee";
const DEFAULT_TIMEOUT_MS = 300_000;

export interface BeeClientOptions {
  /** Bee API key. Issue from https://workspace.bee.heossi.com/account/api-keys. */
  apiKey: string;
  /** Override the default base URL. Useful for staging or self-hosted Enclave. */
  baseURL?: string;
  /** Per-request timeout in ms. Default 300_000. */
  timeoutMs?: number;
  /** Extra headers to send on every request. */
  headers?: Record<string, string>;
  /** Inject a custom fetch (for tests / Node <18 polyfills). Defaults to globalThis.fetch. */
  fetch?: typeof fetch;
}

export class BeeClient {
  private readonly apiKey: string;
  private readonly baseURL: string;
  private readonly timeoutMs: number;
  private readonly extraHeaders: Record<string, string>;
  private readonly fetchImpl: typeof fetch;

  readonly chat: ChatNamespace;
  readonly models: ModelsNamespace;
  readonly quantumReasoning: QuantumReasoningNamespace;
  readonly provenance: ProvenanceNamespace;
  readonly usage: UsageNamespace;
  readonly computerUse: ComputerUseNamespace;

  constructor(opts: BeeClientOptions) {
    if (!opts.apiKey || typeof opts.apiKey !== "string") {
      throw new Error("BeeClient: apiKey is required");
    }
    this.apiKey = opts.apiKey;
    this.baseURL = (opts.baseURL ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.timeoutMs = typeof opts.timeoutMs === "number" ? opts.timeoutMs : DEFAULT_TIMEOUT_MS;
    this.extraHeaders = { ...(opts.headers ?? {}) };
    const f = opts.fetch ?? globalThis.fetch;
    if (typeof f !== "function") {
      throw new Error(
        "BeeClient: no fetch implementation found. On Node <18, pass `fetch` explicitly.",
      );
    }
    this.fetchImpl = f;

    this.chat = new ChatNamespace(this);
    this.models = new ModelsNamespace(this);
    this.quantumReasoning = new QuantumReasoningNamespace(this);
    this.provenance = new ProvenanceNamespace(this);
    this.usage = new UsageNamespace(this);
    this.computerUse = new ComputerUseNamespace(this);
  }

  /** Internal - request wrapper with timeout, auth header, and structured error mapping. */
  async _request(
    method: "GET" | "POST" | "PATCH" | "DELETE",
    path: string,
    body: unknown,
    accept: "application/json" | "text/event-stream",
    requestHeaders: Record<string, string> = {},
  ): Promise<Response> {
    const url = `${this.baseURL}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.apiKey}`,
      Accept: accept,
      ...this.extraHeaders,
      ...requestHeaders,
    };
    if (body !== undefined) headers["Content-Type"] = "application/json";

    let resp: Response;
    try {
      resp = await this.fetchImpl(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
    } catch (err) {
      clearTimeout(timer);
      if (err instanceof Error && err.name === "AbortError") {
        throw new BeeTimeoutError(`Request to ${url} timed out`, this.timeoutMs);
      }
      throw err;
    }
    clearTimeout(timer);

    if (!resp.ok) {
      const errorBody = await safeReadJson(resp);
      const actionDecision =
        errorBody &&
        typeof errorBody === "object" &&
        "bee_upgrade" in errorBody &&
        errorBody.bee_upgrade &&
        typeof errorBody.bee_upgrade === "object"
          ? (errorBody.bee_upgrade as BeeUpgradeDecision)
          : null;
      const message = `Bee request to ${path} failed: HTTP ${resp.status}`;
      if (actionDecision) {
        throw new BeeActionRequiredError(message, resp.status, errorBody, actionDecision);
      }
      if (resp.status === 401 || resp.status === 403) {
        throw new BeeAuthError(message, resp.status, errorBody);
      }
      if (resp.status === 429) {
        const ra = resp.headers.get("retry-after");
        const retryAfter = ra && /^\d+$/.test(ra) ? Number.parseInt(ra, 10) : null;
        throw new BeeRateLimitError(message, errorBody, retryAfter);
      }
      throw new BeeError(message, resp.status, errorBody);
    }
    return resp;
  }
}

class ChatNamespace {
  readonly completions: ChatCompletionsResource;
  constructor(client: BeeClient) {
    this.completions = new ChatCompletionsResource(client);
  }
}

class ChatCompletionsResource {
  constructor(private readonly client: BeeClient) {}

  /** Non-streaming chat completion. */
  async create(
    params: ChatCompletionCreateParams & { stream?: false | undefined },
  ): Promise<ChatCompletion>;
  /** Streaming chat completion - returns an async iterator over OpenAI SSE chunks. */
  async create(
    params: ChatCompletionCreateParams & { stream: true },
  ): Promise<AsyncIterable<ChatCompletionChunk>>;
  async create(
    params: ChatCompletionCreateParams,
  ): Promise<ChatCompletion | AsyncIterable<ChatCompletionChunk>> {
    validateMessages(params.messages);
    const body = {
      model: params.model ?? "bee-cell",
      messages: params.messages,
      ...(params.domain ? { domain: params.domain } : {}),
      ...(typeof params.temperature === "number" ? { temperature: params.temperature } : {}),
      ...(typeof params.max_tokens === "number" ? { max_tokens: params.max_tokens } : {}),
      ...(typeof params.seed === "number" ? { seed: params.seed } : {}),
      ...(params.stream ? { stream: true } : {}),
    };

    if (params.stream) {
      const resp = await this.client._request(
        "POST",
        "/chat/completions",
        body,
        "text/event-stream",
      );
      return iterateSse(resp);
    }
    const resp = await this.client._request("POST", "/chat/completions", body, "application/json");
    return (await resp.json()) as ChatCompletion;
  }
}

class ModelsNamespace {
  constructor(private readonly client: BeeClient) {}
  async list(): Promise<ModelsListResponse> {
    const resp = await this.client._request("GET", "/models", undefined, "application/json");
    return (await resp.json()) as ModelsListResponse;
  }
}

class ComputerUseNamespace {
  constructor(private readonly client: BeeClient) {}

  async validateHostReport(params: {
    host: ComputerUseHostReport;
    request?: ComputerUseActionRequest;
  }): Promise<ComputerUseHostReportValidation> {
    const resp = await this.client._request(
      "POST",
      "/computer/v1/host-reports",
      params,
      "application/json",
    );
    return (await resp.json()) as ComputerUseHostReportValidation;
  }
}

class QuantumReasoningNamespace {
  readonly jobs: QuantumReasoningJobsResource;
  constructor(client: BeeClient) {
    this.jobs = new QuantumReasoningJobsResource(client);
  }
}

class QuantumReasoningJobsResource {
  constructor(private readonly client: BeeClient) {}

  async create(params: QuantumReasoningJobCreateParams): Promise<QuantumReasoningJob> {
    if (!params.prompt?.trim()) throw new Error("BeeClient: prompt is required");
    const idempotencyKey = params.idempotency_key ?? crypto.randomUUID();
    const resp = await this.client._request(
      "POST",
      "/quantum-reasoning/jobs",
      {
        prompt: params.prompt,
        model: params.model,
        product: params.product,
        ...(params.provider_connection_id !== undefined
          ? { provider_connection_id: params.provider_connection_id }
          : {}),
        ...(params.workspace_id !== undefined ? { workspace_id: params.workspace_id } : {}),
      },
      "application/json",
      { "Idempotency-Key": idempotencyKey },
    );
    return ((await resp.json()) as { job: QuantumReasoningJob }).job;
  }

  async list(
    params: {
      cursor?: string;
      limit?: number;
      status?: QuantumReasoningJob["status"];
      model?: QuantumReasoningJob["model"];
    } = {},
  ): Promise<{
    jobs: QuantumReasoningJob[];
    capabilities: QuantumReasoningCapabilities;
    next_cursor: string | null;
  }> {
    const search = new URLSearchParams();
    if (params.cursor) search.set("cursor", params.cursor);
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    if (params.status) search.set("status", params.status);
    if (params.model) search.set("model", params.model);
    const resp = await this.client._request(
      "GET",
      `/quantum-reasoning/jobs${search.size ? `?${search}` : ""}`,
      undefined,
      "application/json",
    );
    return (await resp.json()) as {
      jobs: QuantumReasoningJob[];
      capabilities: QuantumReasoningCapabilities;
      next_cursor: string | null;
    };
  }

  async retrieve(id: string): Promise<QuantumReasoningJob> {
    const resp = await this.client._request(
      "GET",
      `/quantum-reasoning/jobs/${encodeURIComponent(id)}`,
      undefined,
      "application/json",
    );
    return ((await resp.json()) as { job: QuantumReasoningJob }).job;
  }

  /** Cancels queued work or erases terminal content while retaining audit metadata. */
  async remove(id: string): Promise<{ ok: true; status: "cancelled" | "deleted" }> {
    const resp = await this.client._request(
      "DELETE",
      `/quantum-reasoning/jobs/${encodeURIComponent(id)}`,
      undefined,
      "application/json",
    );
    return (await resp.json()) as { ok: true; status: "cancelled" | "deleted" };
  }

  async wait(
    id: string,
    options: { timeout_ms?: number; poll_interval_ms?: number; signal?: AbortSignal } = {},
  ): Promise<QuantumReasoningJob> {
    const timeout = options.timeout_ms ?? 15 * 60_000;
    const pollInterval = options.poll_interval_ms ?? 2_000;
    if (timeout <= 0 || pollInterval <= 0) {
      throw new Error("BeeClient: timeout_ms and poll_interval_ms must be positive");
    }
    const deadline = Date.now() + timeout;
    const active = new Set([
      "queued",
      "generating_candidates",
      "scoring",
      "selecting",
      "awaiting_qpu",
    ]);
    while (Date.now() < deadline) {
      if (options.signal?.aborted) throw options.signal.reason ?? new Error("Aborted");
      const job = await this.retrieve(id);
      if (!active.has(job.status)) return job;
      if (options.signal?.aborted) throw options.signal.reason ?? new Error("Aborted");
      await new Promise<void>((resolve, reject) => {
        const onAbort = () => {
          clearTimeout(timer);
          reject(options.signal?.reason ?? new Error("Aborted"));
        };
        const timer = setTimeout(() => {
          options.signal?.removeEventListener("abort", onAbort);
          resolve();
        }, pollInterval);
        options.signal?.addEventListener("abort", onAbort, { once: true });
      });
    }
    throw new Error(`BeeClient: timed out waiting for quantum reasoning job ${id}`);
  }
}

/**
 * Verifiable agent provenance. When an agent-loop request carries a stable
 * `session_id`, Bee seals each served turn into a per-session, ML-DSA-65-signed
 * (NIST FIPS 204) hash chain. `verify(sessionId)` returns Bee's verdict, the
 * chain (digests only - never your code), and the SPKI public key so you can
 * INDEPENDENTLY re-verify every link offline with any FIPS-204 verifier.
 */
class ProvenanceNamespace {
  constructor(private readonly client: BeeClient) {}
  async verify(sessionId: string): Promise<ProvenanceResult> {
    if (!sessionId || typeof sessionId !== "string") {
      throw new Error("BeeClient: provenance.verify requires a session id");
    }
    const resp = await this.client._request(
      "GET",
      `/provenance/${encodeURIComponent(sessionId)}`,
      undefined,
      "application/json",
    );
    return (await resp.json()) as ProvenanceResult;
  }
}

/**
 * Account & usage. `retrieve()` returns the caller's account (email, plan,
 * organization), usage (pooled tokens, per-tier allowances, resets_at, messages,
 * active days, credits), and the "what's contributing" tier breakdown over a
 * `day` (24h) or `week` (7d) window - the SAME real data the Bee workspace,
 * desktop, mobile, and IDE surfaces show, for every tier.
 */
class UsageNamespace {
  constructor(private readonly client: BeeClient) {}
  async retrieve(window: "day" | "week" = "day"): Promise<UsageResponse> {
    const w = window === "week" ? "week" : "day";
    const resp = await this.client._request(
      "GET",
      `/usage?window=${w}`,
      undefined,
      "application/json",
    );
    return (await resp.json()) as UsageResponse;
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────

function validateMessages(messages: ChatMessage[]): void {
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new Error("BeeClient: messages must be a non-empty array");
  }
  for (const m of messages) {
    if (!m || typeof m.role !== "string") {
      throw new Error("BeeClient: each message must have a string `role`");
    }
    if (typeof m.content !== "string" && !Array.isArray(m.content)) {
      throw new Error("BeeClient: each message `content` must be a string or array of parts");
    }
  }
}

async function safeReadJson(resp: Response): Promise<unknown> {
  try {
    return await resp.json();
  } catch {
    try {
      return await resp.text();
    } catch {
      return null;
    }
  }
}

/**
 * Yield OpenAI-style SSE chunks. The server emits `data: {...}\n\n`
 * lines terminated by `data: [DONE]\n\n`. Lines we can't parse as JSON
 * are skipped silently - same behaviour as the OpenAI SDK.
 */
async function* iterateSse(resp: Response): AsyncIterable<ChatCompletionChunk> {
  if (!resp.body) {
    throw new BeeError("Streaming response had no body", resp.status, null);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      for (;;) {
        const eventEnd = buffer.indexOf("\n\n");
        if (eventEnd === -1) break;
        const event = buffer.slice(0, eventEnd);
        buffer = buffer.slice(eventEnd + 2);
        const dataLine = event
          .split("\n")
          .find((line) => line.startsWith("data:"))
          ?.slice(5)
          .trim();
        if (!dataLine) continue;
        if (dataLine === "[DONE]") return;
        try {
          yield JSON.parse(dataLine) as ChatCompletionChunk;
        } catch {
          // Malformed line - skip and continue.
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
