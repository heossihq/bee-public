/**
 * OpenAI-compatible request / response types for Bee.
 *
 * Bee exposes a strict subset of the OpenAI Chat Completions surface
 * at https://api.bee.heossi.com/bee/chat/completions - same JSON shapes,
 * same streaming format. Anything unsupported (function calling,
 * logprobs, n>1, etc.) silently 400s upstream rather than surfacing
 * a misleading "ok" response. This SDK exposes only what's verified
 * to work end-to-end so callers don't ship dead options.
 */

export type Role = "system" | "user" | "assistant";

/**
 * Customer-selectable Tier-1 Bee specialist domains.
 *
 * Higher-tier Stage-0 families are intentionally not included until they pass
 * promotion and customer-path serving gates. Callers may omit this field to
 * allow Bee's governed classifier to select a domain.
 */
export type BeeDomain =
  | "general"
  | "programming"
  | "ai"
  | "cybersecurity"
  | "cryptography_pqc"
  | "quantum"
  | "fintech"
  | "blockchain"
  | "infrastructure"
  | "research"
  | "business"
  | "accounting"
  | "biology"
  | "chemistry"
  | "education"
  | "mathematics"
  | "physics";

export type TextPart = { type: "text"; text: string };
export type ImageUrlPart = {
  type: "image_url";
  image_url: { url: string; detail?: "auto" | "low" | "high" };
};
export type ContentPart = TextPart | ImageUrlPart;

/** Customer-selectable production model tiers. Access is enforced by the API key's plan. */
export type BeeModelId =
  | "bee-cell"
  | "bee-brood"
  | "bee-comb"
  | "bee-buzz"
  | "bee-hive"
  | "bee-swarm";

export interface ChatMessage {
  role: Role;
  /** A plain string OR an OpenAI-style multimodal content array. */
  content: string | ContentPart[];
}

export interface ChatCompletionCreateParams {
  /** Customer-selectable Bee tier. Default `bee-cell`. */
  model?: BeeModelId;
  /** Optional governed Tier-1 specialist. Omit to use Bee's automatic classifier. */
  domain?: BeeDomain;
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
  /** Optional deterministic seed (forwarded to the backend; honoured by some tiers). */
  seed?: number;
  /** When true, returns an async iterator of OpenAI SSE chunks. */
  stream?: boolean;
}

export interface ChatCompletionChoice {
  index: number;
  message: { role: "assistant"; content: string };
  finish_reason: string;
}

export interface ChatCompletionUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface DomainIntelligenceMetadata {
  version: string;
  primary_domain: string;
  perspectives: string[];
  serving: "general" | "baseline_specialist_synthesis" | "specialist_adapter";
  evidence_policy:
    | "model_knowledge"
    | "tenant_context_recommended"
    | "live_sources_recommended"
    | "live_sources_required";
  recommended_model: string | null;
  notice: string | null;
}

export interface ChatCompletion {
  id: string;
  object: "chat.completion";
  created: number;
  model: string;
  choices: ChatCompletionChoice[];
  usage: ChatCompletionUsage;
  /** Auditable BSIS subject, evidence, serving-readiness and upgrade decision. */
  bee_domain_intelligence?: DomainIntelligenceMetadata;
}

export interface ChatCompletionChunkChoice {
  index: number;
  delta: { role?: "assistant"; content?: string };
  finish_reason: string | null;
}

export interface ChatCompletionChunk {
  id: string;
  object: "chat.completion.chunk";
  created: number;
  model: string;
  choices: ChatCompletionChunkChoice[];
}

export interface ModelInfo {
  id: string;
  object: "model";
  created?: number;
  owned_by?: string;
}

export interface ModelsListResponse {
  object: "list";
  data: ModelInfo[];
}

export type QuantumReasoningModel = "bee-hive" | "bee-swarm";
export type QuantumProductId =
  | "local_simulator"
  | "simulation_cloud"
  | "managed_qpu"
  | "byopa_direct"
  | "byopa_managed";
export type QuantumReasoningJobStatus =
  | "queued"
  | "generating_candidates"
  | "scoring"
  | "selecting"
  | "awaiting_qpu"
  | "completed"
  | "classical_fallback"
  | "failed"
  | "cancelled";
export type QuantumReasoningRealRequestStatus =
  | "not_requested"
  | "reserved"
  | "executed"
  | "provider_used_simulator"
  | "quantum_not_enabled"
  | "quantum_allowance_exhausted"
  | "released_after_failure";

export interface QuantumReasoningCandidate {
  index: number;
  content: string;
  score: number;
}

export interface QuantumReasoningJob {
  id: string;
  product: Exclude<QuantumProductId, "local_simulator" | "byopa_direct">;
  status: QuantumReasoningJobStatus;
  model: QuantumReasoningModel;
  scoring_method: "hive_logprob" | "swarm_judge";
  requested_real: boolean;
  prompt?: string;
  candidates?: QuantumReasoningCandidate[];
  selected_index?: number;
  result?: string;
  selector_backend?: string;
  selector_confidence?: number;
  used_real_qubits: boolean;
  quoted_credits: number | null;
  fallback_reason: "selector_unreachable" | "invalid_selection" | null;
  real_request_status: QuantumReasoningRealRequestStatus;
  usage: Record<string, number>;
  inference_receipt_id: string | null;
  attempt_count: number;
  max_attempts: number;
  next_attempt_at: string | null;
  outcome_state: "not_started" | "in_progress" | "committed" | "outcome_unknown" | "reconciled";
  error: { code: string; message: string } | null;
  workspace_id?: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface QuantumReasoningCapabilities {
  allowed_models: QuantumReasoningModel[];
  real_enabled: boolean;
  allowance_credits: number;
  used_credits: number;
  remaining_credits: number;
  workspace_role: "owner" | "admin" | "member";
  can_run_real: boolean;
  can_manage_jobs: boolean;
  products: Array<{
    product: QuantumProductId;
    purchased: boolean;
    server_dispatch: boolean;
    available: boolean;
  }>;
}

export interface QuantumReasoningJobCreateParams {
  prompt: string;
  model: QuantumReasoningModel;
  product: QuantumProductId;
  provider_connection_id?: string | null;
  workspace_id?: string | null;
  /** At-least 16 characters. Reuse it to retry the same logical create safely. */
  idempotency_key?: string;
}

/** One sealed, ML-DSA-65-signed link in a session's provenance chain. */
export interface ProvenanceLink {
  seq: number;
  sessionId: string;
  prevHash: string;
  /** Digests of the turn - never the raw code/args. */
  action: { tool: string; argsDigest: string; resultDigest: string; tier: string };
  issuedAt: string;
  linkHash: string;
  signatureAlgorithm: "ML-DSA-65";
  signatureKeyId: string;
  signature: string;
}

/** Result of {@link BeeClient.provenance}.verify - server verdict + re-verifiable chain. */
export interface ProvenanceResult {
  session_id: string;
  /** Bee's verdict for the whole chain. */
  verified: boolean;
  /** Number of sealed turns. */
  turns: number;
  verification: { ok: boolean; count: number; failedAt?: number; reason?: string };
  signature_algorithm: "ML-DSA-65";
  /** SPKI PEM - re-verify every link offline with any FIPS-204 verifier. */
  public_key_pem: string | null;
  chain: ProvenanceLink[];
}

export type ComputerUseCapabilityState =
  | "supported"
  | "unsupported"
  | "permission_required"
  | "not_verified";

export interface ComputerUseCapability {
  state: ComputerUseCapabilityState;
  reason: string | null;
}

export interface ComputerUseHostReport {
  protocol: "bee.computer.v1";
  host_id: string;
  host_type:
    | "macos_desktop"
    | "windows_desktop"
    | "linux_desktop"
    | "browser"
    | "webview"
    | "vscode"
    | "cli"
    | "ios"
    | "android";
  version: string;
  capabilities: {
    screen_observation: ComputerUseCapability;
    accessibility_tree: ComputerUseCapability;
    pointer_input: ComputerUseCapability;
    keyboard_input: ComputerUseCapability;
    browser_navigation: ComputerUseCapability;
  };
  evidence: { checked_at: string; checker: string };
}

export type ComputerUseAction =
  | "observe_screen"
  | "observe_accessibility_tree"
  | "click"
  | "double_click"
  | "type_text"
  | "key_press"
  | "scroll"
  | "navigate_url";

export type ComputerUseApprovalClass = "none" | "observe" | "input" | "navigation" | "publication";

export interface ComputerUseActionRequest {
  protocol: "bee.computer.v1";
  action_id: string;
  host_id: string;
  action: ComputerUseAction;
  arguments: Record<string, unknown>;
  approval: ComputerUseApprovalClass;
  approved_at: string;
  approval_token_digest: string;
}

export interface ComputerUseHostReportValidation {
  protocol: "bee.computer.v1";
  accepted: boolean;
  host_id: string;
  host_type: ComputerUseHostReport["host_type"];
  request_action: ComputerUseAction | null;
}

export type BeeUpgradeReason =
  | "model_access_required"
  | "domain_tier_required"
  | "feature_required"
  | "token_allowance_exhausted"
  | "tier_allowance_exhausted"
  | "insufficient_credits"
  | "overage_cap_reached"
  | "context_limit_reached"
  | "rate_limited";

export interface BeeUpgradeAction {
  kind:
    | "upgrade_plan"
    | "enable_usage_credits"
    | "add_credits"
    | "manage_spend_cap"
    | "purchase_addon"
    | "compact_context"
    | "new_conversation"
    | "retry_later"
    | "contact_sales";
  label: string;
  available: boolean;
  url: string | null;
  plan_id?: string;
}

export interface BeeUpgradeDecision {
  schema_version: "2026-07-31";
  reason: BeeUpgradeReason;
  current_plan: string;
  required_plan: string | null;
  requested_model?: string;
  requested_domain?: string;
  requested_feature?: string;
  binding_limit?: {
    kind:
      | "tokens"
      | "requests"
      | "seconds"
      | "credits"
      | "context"
      | "rate"
      | "documents"
      | "storage";
    unit:
      | "tokens"
      | "requests"
      | "seconds"
      | "cents"
      | "percent"
      | "documents"
      | "bytes"
      | "characters";
    used?: number;
    limit?: number;
    remaining?: number;
    resets_at?: string | null;
    retry_after_seconds?: number | null;
  };
  actions: BeeUpgradeAction[];
}

/** One metered tier's allowance for the current billing period. */
export interface UsageAllowance {
  tier: string;
  label: string;
  unit: "requests" | "seconds" | "tokens";
  used: number;
  limit: number;
  remaining: number;
  percent: number;
  overage_behavior: "hard_fail" | "payg" | "contract";
  addons_enabled: boolean;
}

/** One Bee tier's share of recent token usage ("what's contributing"). */
export interface UsageBreakdownTier {
  label: string;
  tokens: number;
  messages: number;
  percent: number;
}

/** Relative Cell capacity under the task-weighted fair-use policy. */
export interface UsageFairUse {
  status: "available" | "approaching_limit" | "limited";
  percent_used: number;
  remaining_percent: number;
  resets_at: string;
  weighting: Array<"context" | "output" | "reasoning" | "tools" | "agent_turns">;
}

/** Result of {@link BeeClient.usage}.retrieve - real account, usage, and breakdown. */
export interface UsageResponse {
  account: {
    email: string | null;
    plan_id: string;
    plan_name: string;
    organization: string;
  };
  usage: {
    period: "billing_period";
    resets_at: string;
    tokens_used: number;
    tokens_included: number | null;
    usage_policy: "dynamic_fair_use" | "fixed_or_metered";
    fair_use: UsageFairUse | null;
    messages: number;
    completed_requests: number;
    active_days: number;
    credits_usd: number;
    usage_credits_available: boolean;
    binding_limit: BeeUpgradeDecision["binding_limit"] | null;
    upgrade: BeeUpgradeDecision | null;
    allowances: UsageAllowance[];
  };
  breakdown: {
    window: "day" | "week";
    hours: number;
    total_tokens: number;
    total_messages: number;
    input_percent: number;
    tiers: UsageBreakdownTier[];
  };
}
