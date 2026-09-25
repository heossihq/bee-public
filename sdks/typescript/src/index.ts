/**
 * @heossihq/bee - Official TypeScript / JavaScript SDK for
 * Bee by HEOSSI - The Progressive Quantum-Native Intelligence Engine.
 *
 * Bee exposes an OpenAI-compatible /chat/completions surface backed by a
 * governed model ladder (Cell, Brood, Comb, Buzz, Hive, Swarm).
 * Enclave is a private deployment mode, not a selectable seventh model.
 * This SDK is the typed entry point - pure
 * ESM, zero runtime dependencies, native fetch.
 *
 * See https://bee.heossi.com/docs for the full API reference.
 */

export type { BeeClientOptions } from "./client.js";
export { BeeClient } from "./client.js";
export {
  BeeActionRequiredError,
  BeeAuthError,
  BeeError,
  BeeRateLimitError,
  BeeTimeoutError,
} from "./errors.js";
export type {
  ByopaDirectAdapter,
  ByopaDirectRequest,
  ByopaDirectResult,
  QuantumLocalAccelerator,
  QuantumLocalResult,
} from "./quantum-local.js";
export { executeByopaDirect, quantumLocalSelect } from "./quantum-local.js";
export type {
  BeeDomain,
  BeeModelId,
  BeeUpgradeAction,
  BeeUpgradeDecision,
  BeeUpgradeReason,
  ChatCompletion,
  ChatCompletionChoice,
  ChatCompletionChunk,
  ChatCompletionChunkChoice,
  ChatCompletionCreateParams,
  ChatCompletionUsage,
  ChatMessage,
  ComputerUseAction,
  ComputerUseActionRequest,
  ComputerUseApprovalClass,
  ComputerUseCapability,
  ComputerUseCapabilityState,
  ComputerUseHostReport,
  ComputerUseHostReportValidation,
  ContentPart,
  DomainIntelligenceMetadata,
  ImageUrlPart,
  ModelInfo,
  ModelsListResponse,
  ProvenanceLink,
  ProvenanceResult,
  QuantumProductId,
  QuantumReasoningCandidate,
  QuantumReasoningCapabilities,
  QuantumReasoningJob,
  QuantumReasoningJobCreateParams,
  QuantumReasoningJobStatus,
  QuantumReasoningModel,
  QuantumReasoningRealRequestStatus,
  Role,
  TextPart,
  UsageAllowance,
  UsageBreakdownTier,
  UsageFairUse,
  UsageResponse,
} from "./types.js";
