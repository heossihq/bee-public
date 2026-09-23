# bee-sdk

Official Python client and MCP server for **Bee by HEOSSI - The Progressive Quantum-Native Intelligence Engine**, a governed multimodal intelligence platform from [HEOSSI](https://www.heossi.com).

<!-- mcp-name: io.github.heossihq/bee-public -->

SDK version: `1.0.11` - includes auditable BSIS domain-intelligence metadata, 14 governed MCP tools, readiness-aware MCP resources, typed per-call/`BEE_MODEL` selection across bee-cell through bee-swarm (access follows your key's plan), and stdio plus Streamable HTTP transports.

Includes a hosted **Model Context Protocol** server: `pip install bee-sdk` then
run `bee-mcp` (stdio) to expose Bee's 14 tools to Claude Desktop, Cursor, VS
Code, Zed, Windsurf, and other MCP clients:

- intelligence: `bee_chat`, `bee_code`, `bee_security`, `bee_research`
- trust and account: `bee_verify_provenance`, `bee_usage`
- knowledge: `bee_documents_search`, `bee_documents_add`
- memory: `bee_memory_search`, `bee_memory_add`
- Quantum Reasoning Lab: `bee_quantum_reasoning_run`,
  `bee_quantum_reasoning_jobs`, `bee_quantum_reasoning_get`,
  `bee_quantum_reasoning_remove`

It also serves `bee://status`, `bee://domains`, `bee://documents`, and
`bee://memory`, plus the `bee://documents/{source}` resource template. Hosted
writes and quantum execution remain tenant-scoped, explicitly described, and
plan/policy gated. For a request/response remote endpoint, run
`bee-mcp --http PORT` (localhost by default; put public deployments behind a
trusted authenticated proxy). See
[bee.heossi.com/docs/mcp](https://bee.heossi.com/docs/mcp).

> **Status:** functional sync + async client (stdlib + optional `httpx`).
> The SDK targets the Bee `/chat/completions` API contract on
> production via the public gateway `https://api.bee.heossi.com/bee` - this
> is the default and it is where API-key auth, plan / per-tier allowance
> enforcement and usage metering happen. Do **not** point `BEE_API_URL`
> at the raw Modal app URL: that bypasses billing and a `bee_sk_` key
> is rejected there (the backend only trusts Supabase JWTs / the
> static `BEE_API_KEYS` env, not customer-issued keys). Override
> `BEE_API_URL` only for a self-hosted Bee Enclave or staging.

## Install

Install from PyPI (canonical):

```bash
pip install bee-sdk          # sync client (stdlib only - zero deps)
pip install bee-sdk[async]   # async client (adds httpx)
```

Install + quickstart on the marketing site:
[bee.heossi.com/docs/sdks](https://bee.heossi.com/docs/sdks).

## Quick start

```python
from bee_sdk import Bee

bee = Bee()  # reads BEE_API_URL + BEE_API_KEY from env
print(bee.chat("Explain Shor's algorithm at NISQ depth", domain="quantum"))
```

Quantum work is submitted as a durable Quantum Reasoning Lab product job. For
customer-local execution, use `quantum_local_select`; for direct customer-owned
provider execution, use `execute_byopa_direct`.

For a durable, inspectable Lab run:

```python
job = bee.quantum_reasoning_create(
    prompt="Compare two fault-tolerant designs.",
    model="bee-hive",
    product="simulation_cloud",
)
detail = bee.quantum_reasoning_wait(job["id"], timeout=900)
print(detail["status"], detail.get("candidates"), detail.get("inference_receipt_id"))
```

Pass a stable `idempotency_key` when your application may retry creation. Reusing
that key with different input returns `409`; reusing it with the same input
returns the original job. `quantum_reasoning_jobs(cursor=..., limit=...,
status=..., model=...)` supports cursor pagination. Automatic execution retry is
deliberately unavailable; ambiguous work must be reconciled.
`quantum_reasoning_remove` cancels an eligible queued job or erases the content
of a terminal job, subject to workspace role controls.

Lab jobs are tenant-scoped, encrypted at rest, and retained for 90 days.
Real-QPU execution is explicitly metered and any classical fallback is returned as such.

Durable Lab jobs require an explicit product: `simulation_cloud` or
`managed_qpu`. `local_simulator` and `byopa_direct` run in the customer's own
environment and never enter Bee's hosted queue. `byopa_managed` remains gated
until its provider-specific managed adapter is activated.

### Streaming

```python
for chunk in bee.chat_stream("Write a Rust fibonacci function", domain="programming"):
    print(chunk, end="", flush=True)
```

### Entitlement and capacity actions

Bee returns one versioned action contract for model access, domain tiers,
allowances, credits, context recovery, documents, and rate limits. The SDK
raises `BeeActionRequiredError` and preserves the complete decision:

```python
from bee_sdk import Bee, BeeActionRequiredError

try:
    Bee().chat("Use Bee Hive.", model="bee-hive")
except BeeActionRequiredError as error:
    print(error.decision["reason"])
    print(error.decision["actions"])
```

### Async

```python
import asyncio
from bee_sdk import AsyncBee

async def main():
    async with AsyncBee() as client:
        text = await client.chat("Audit this contract for re-entrancy", domain="blockchain")
        print(text)

asyncio.run(main())
```

### Multi-turn

```python
from bee_sdk import Bee, ChatMessage

bee = Bee()
resp = bee.chat_messages(
    [
        ChatMessage(role="system", content="You are a senior security auditor."),
        ChatMessage(role="user", content="Review this nginx config for hardening gaps:\n\n..."),
    ],
    domain="cybersecurity",
    max_tokens=1024,
)
print(resp.content)
print(resp.usage, resp.interaction_id)
```

### Feedback loop

```python
resp = bee.chat_messages([...], domain="ai")
if user_likes_answer:
    bee.feedback(resp.interaction_id, rating="up")
```

### Documents (RAG) & personal memory

Both are tenant-scoped to your API key's account. Documents need a rag-entitled
plan; memory is a per-user opt-in (default-on).

```python
# Documents - add to your knowledge base, then search it
bee.documents_add("Q3 revenue grew 14% QoQ to S$2.1M.", source="q3-report")
hits = bee.documents_search("how did revenue change in Q3?", k=3)

# Personal memory - remember a fact, recall it later
bee.memories_add("Prefers TypeScript over JavaScript.", kind="preference")
mem = bee.memories_search("language preference")  # {enabled, memories: [...]}
```

## Domains

The `domain=` parameter selects which LoRA adapter Bee routes through. Tier-1 domains:

| domain | what it's tuned for |
|---|---|
| `general` | balanced, no specialization |
| `programming` | code generation, refactoring, debugging |
| `ai` | ML/AI papers, training, evaluation |
| `cybersecurity` | threat modelling, audits, defensive analysis |
| `cryptography_pqc` | cryptography and post-quantum security intelligence |
| `quantum` | NISQ-aware quantum computing, Qiskit |
| `fintech` | payments, risk, compliance |
| `blockchain` | smart contract audits, protocol design |
| `infrastructure` | systems, networking, devops |
| `research` | literature review, paper critique |
| `business` | strategy, GTM, ops |
| `accounting` | accounting, reporting, controls |
| `biology` | biological sciences |
| `chemistry` | chemical sciences |
| `education` | teaching and learning |
| `mathematics` | mathematical reasoning |
| `physics` | physical sciences |

The gateway applies plan, model-tier, promotion, safety and availability gates to
explicit domain requests. Omit `domain` to let Bee's governed classifier select
the applicable available specialist. Domain adapters and model weights are
served privately through the hosted gateway.

## Environment variables

| var | purpose |
|---|---|
| `BEE_API_URL` | Endpoint override. Defaults to the public gateway `https://api.bee.heossi.com/bee` (where auth + billing + metering run). Set this **only** for a self-hosted Bee Enclave or a staging environment - never the raw Modal app URL (that bypasses billing and rejects `bee_sk_` keys). |
| `BEE_API_KEY` | Customer Bearer token. Create one at [workspace.bee.heossi.com/account/api-keys](https://workspace.bee.heossi.com/account/api-keys). |

## Errors

```python
from bee_sdk import BeeAPIError, RateLimitError, BeeError

try:
    bee.chat("...", domain="quantum")
except RateLimitError as e:        # 429 after retries
    ...
except BeeAPIError as e:           # other HTTP errors
    print(e.status, e.body)
except BeeError:                   # network / timeout
    ...
```

The sync client retries 429/5xx with exponential backoff (max 4 attempts).

## Versioning

`bee-sdk` follows the Bee API surface. Breaking API changes bump the **minor**
version pre-1.0; the SDK is currently **1.0.11** and the API is `v1`.

## License

Apache-2.0 © 2026 HEOSSI (Pte.) Ltd.
