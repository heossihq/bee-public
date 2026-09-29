# @heossihq/bee

Official TypeScript / JavaScript SDK for **Bee: Quantum Intelligence - The Progressive Quantum-Native Intelligence Engine**.

[![npm](https://img.shields.io/npm/v/@heossihq/bee.svg)](https://www.npmjs.com/package/@heossihq/bee)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)

Bee exposes an **OpenAI-compatible** `/chat/completions` surface backed by a governed six-model ladder - Cell, Brood, Comb, Buzz, Hive, and Swarm. Enclave is a private deployment mode, not a seventh selectable model. This SDK is the typed entry point.

- ✅ Pure ESM, zero runtime dependencies
- ✅ Native `fetch` (Node 18+, Deno, Bun, every browser)
- ✅ Streaming via async iterator
- ✅ Multimodal content (text + image_url) on Hive / Swarm / Enclave
- ✅ Structured errors (`BeeActionRequiredError`, `BeeAuthError`, `BeeRateLimitError`, `BeeTimeoutError`)

## Install

```bash
npm install @heossihq/bee
# or pnpm add @heossihq/bee
# or yarn add @heossihq/bee
```

## Quickstart

Get an API key from [workspace.bee.heossi.com/account/api-keys](https://workspace.bee.heossi.com/account/api-keys).
The default API base is `https://api.bee.heossi.com/bee`. The SDK requires an
API key; the public gateway translates that edge credential into an internal
hybrid delegation and does not forward the raw `bee_sk_*` key to Modal or
Workspace internals.

```ts
import { BeeClient } from "@heossihq/bee";

const bee = new BeeClient({ apiKey: process.env.BEE_API_KEY! });

const out = await bee.chat.completions.create({
  model: "bee-cell",
  domain: "cryptography_pqc", // optional; omit for governed automatic routing
  messages: [
    { role: "system", content: "You are a precise assistant." },
    { role: "user", content: "Summarise the SOLID principles in 2 lines." },
  ],
});

console.log(out.choices[0].message.content);
```

`domain` is typed to Bee's customer-selectable Tier-1 specialist families.
Higher-tier Stage-0 families are not advertised by the SDK until they pass
promotion, safety, latency and customer-path serving gates.

## Streaming

```ts
const stream = await bee.chat.completions.create({
  model: "bee-cell",
  messages: [{ role: "user", content: "Write a short haiku about bees." }],
  stream: true,
});

for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
}
```

## Vision (Cell through Swarm)

```ts
const out = await bee.chat.completions.create({
  model: "bee-hive",
  messages: [
    {
      role: "user",
      content: [
        { type: "text", text: "What is in this image?" },
        {
          type: "image_url",
          image_url: { url: "https://example.com/photo.jpg" },
        },
      ],
    },
  ],
});
```

## Quantum Reasoning Lab

Quantum work is a durable product job, not a chat-completion body option. Use
`quantumLocalSelect` for customer-local CPU/GPU simulation, `executeByopaDirect`
for a customer-owned provider adapter, or `bee.quantumReasoning.create(...)` for
an entitled hosted product.

Durable Lab jobs require an explicit product: `simulation_cloud` or
`managed_qpu`. `local_simulator` and `byopa_direct` run in the customer's own
environment and are intentionally rejected by Bee's hosted job endpoint.
`byopa_managed` remains unavailable until a provider-specific managed adapter
passes its production activation gate.

For durable, inspectable runs, use the Quantum Reasoning Lab job resource:

```ts
const job = await bee.quantumReasoning.jobs.create({
  prompt: "Compare two fault-tolerant designs.",
  model: "bee-hive",
  product: "simulation_cloud",
});

const detail = await bee.quantumReasoning.jobs.wait(job.id, {
  timeout_ms: 15 * 60_000,
});
console.log(detail.status, detail.candidates, detail.inference_receipt_id);
```

Pass a stable `idempotency_key` when your application may retry creation. Reusing
that key with different input returns `409`; reusing it with the same input
returns the original job. `jobs.list({ cursor, limit, status, model })` supports
cursor pagination. Automatic execution retry is deliberately unavailable;
ambiguous work must be reconciled. `jobs.remove(id)` cancels eligible queued work or erases the
content of a terminal job, subject to workspace role controls.

Jobs are tenant-scoped, encrypted at rest, and retained for 90 days. Real-QPU
runs remain explicitly metered and may report a visible classical fallback.

## List models

```ts
const { data } = await bee.models.list();
for (const m of data) console.log(m.id);
```

## Self-hosted Bee Enclave

Override `baseURL` to point at your on-prem deployment:

```ts
const bee = new BeeClient({
  apiKey: process.env.BEE_API_KEY!,
  baseURL: "https://bee.your-company.example/bee",
});
```

## Error handling

```ts
import {
  BeeActionRequiredError,
  BeeAuthError,
  BeeRateLimitError,
  BeeTimeoutError,
} from "@heossihq/bee";

try {
  await bee.chat.completions.create({ messages: [{ role: "user", content: "Hi" }] });
} catch (err) {
  if (err instanceof BeeActionRequiredError) {
    console.warn(err.decision.reason, err.decision.actions);
  } else if (err instanceof BeeRateLimitError) {
    console.warn(`Rate-limited. Retry after ${err.retryAfterSeconds}s`);
  } else if (err instanceof BeeAuthError) {
    console.error("Bad API key or plan does not grant this tier");
  } else if (err instanceof BeeTimeoutError) {
    console.error("Request timed out");
  } else {
    throw err;
  }
}
```

## OpenAI SDK compatibility

Because Bee speaks the OpenAI Chat Completions wire format, you can also point the official `openai` package at Bee directly - useful for migration:

```ts
import OpenAI from "openai";

const bee = new OpenAI({
  apiKey: process.env.BEE_API_KEY,
  baseURL: "https://api.bee.heossi.com/bee",
});
```

`@heossihq/bee` is the lighter, dependency-free option when you don't need the full OpenAI SDK surface.

## Other surfaces

- **MCP server** for Claude Desktop / Cursor / VS Code → see [bee.heossi.com/docs/mcp](https://bee.heossi.com/docs/mcp)
- **Python SDK** → `pip install bee-sdk`
- **REST reference** → [bee.heossi.com/docs](https://bee.heossi.com/docs)
- **Status & roadmap** → [bee.heossi.com/status](https://bee.heossi.com/status), [bee.heossi.com/roadmap](https://bee.heossi.com/roadmap)

## License

[Apache-2.0](./LICENSE) - © HEOSSI (Pte.) Ltd.
