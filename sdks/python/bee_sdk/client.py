"""Bee SDK client.

Two flavours:
  - `Bee`        synchronous, uses urllib stdlib only (zero deps)
  - `AsyncBee`   async, uses httpx (optional dep - `pip install bee-sdk[async]`)

Both expose the same surface:

    .chat(message, domain=..., max_tokens=...)         → str
    .chat_messages(messages, ...)                      → ChatResponse
    .chat_stream(message, ...)                         → Iterator[str]
    .feedback(interaction_id, rating)                  → None
    .domains()                                         → list[str]
    .health()                                          → dict
    .adapters()                                        → dict
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Any

from .types import (
    ChatMessage,
    ChatResponse,
    ComputerUseActionRequest,
    ComputerUseHostReport,
    ComputerUseHostReportValidation,
    CustomerModelId,
    Domain,
    QuantumProductId,
    QuantumReasoningJob,
    QuantumReasoningJobPage,
    QuantumReasoningJobStatus,
    QuantumReasoningModel,
    UpgradeDecision,
)

# Public API gateway. This is where customer API-key authentication, plan
# enforcement, and usage metering run. Never target a raw provider endpoint.
DEFAULT_BASE_URL = "https://api.bee.heossi.com/bee"
DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Model tier sent in the request body. Which tiers an API key may use is
# decided by the key's plan at the gateway (403 model_access_denied when the
# plan doesn't include it). bee-cell is the free tier, so it's the safe
# default; override per-call or via BEE_MODEL.
DEFAULT_MODEL = "bee-cell"


def _resolve_model(model: CustomerModelId | None) -> str:
    return model or os.environ.get("BEE_MODEL") or DEFAULT_MODEL


class BeeError(Exception):
    """Base error class for the SDK."""


class BeeAPIError(BeeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


class BeeActionRequiredError(BeeAPIError):
    """A machine-readable entitlement, capacity, credit, or recovery decision."""

    def __init__(self, status: int, body: str, decision: UpgradeDecision) -> None:
        super().__init__(status, body)
        self.decision = decision


def _upgrade_decision(body: str) -> UpgradeDecision | None:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    decision = parsed.get("bee_upgrade") if isinstance(parsed, dict) else None
    return decision if isinstance(decision, dict) else None


class RateLimitError(BeeAPIError):
    """Raised on persistent 429 after retries exhausted."""


class _BaseClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.base_url = (base_url or os.environ.get("BEE_API_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or os.environ.get("BEE_API_KEY")
        self.timeout = timeout
        self.retries = retries

    def _headers(self, extra: dict | None = None) -> dict:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "bee-sdk/1.0.12",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if extra:
            h.update(extra)
        return h


class Bee(_BaseClient):
    """Synchronous client. Zero non-stdlib dependencies."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        super().__init__(base_url=base_url, api_key=api_key, timeout=timeout, retries=retries)

    @classmethod
    def async_client(cls, **kwargs) -> AsyncBee:
        """Convenience factory for the async client."""
        return AsyncBee(**kwargs)

    # ── HTTP plumbing ───────────────────────────────────────────────────
    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        *,
        retries: int | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        last_err: Exception | None = None
        max_retries = self.retries if retries is None else retries
        for attempt in range(max_retries + 1):
            req = urllib.request.Request(
                url, data=data, headers=self._headers(headers), method=method
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                body_text = e.read().decode(errors="replace")
                if e.code in RETRYABLE_STATUS and attempt < max_retries:
                    last_err = e
                    time.sleep(min(2**attempt, 8))
                    continue
                decision = _upgrade_decision(body_text)
                if decision is not None:
                    raise BeeActionRequiredError(e.code, body_text, decision) from e
                if e.code == 429:
                    raise RateLimitError(e.code, body_text) from e
                raise BeeAPIError(e.code, body_text) from e
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_err = e
                if attempt < max_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                raise BeeError(f"network error after {max_retries + 1} attempts: {e}") from e
        raise BeeError(f"unreachable: {last_err}")

    # ── Public API ──────────────────────────────────────────────────────
    def chat(
        self,
        message: str,
        domain: Domain | None = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        system: str | None = None,
        model: CustomerModelId | None = None,
    ) -> str:
        """Single-turn chat. Returns the assistant text only.

        `model` picks the Bee tier (bee-cell … bee-swarm); which tiers your
        key may use is governed by its plan. Defaults to BEE_MODEL env or
        bee-cell. For multi-turn or detailed metadata, use `chat_messages`.
        """
        msgs: list[ChatMessage] = []
        if system:
            msgs.append(ChatMessage(role="system", content=system))
        msgs.append(ChatMessage(role="user", content=message))
        return self.chat_messages(
            msgs,
            domain=domain,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
        ).content

    def chat_messages(
        self,
        messages: list[ChatMessage],
        domain: Domain | None = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        model: CustomerModelId | None = None,
    ) -> ChatResponse:
        body = {
            "model": _resolve_model(model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if domain:
            body["domain"] = domain
        out = self._request("POST", "/chat/completions", body)
        choice = (out.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        return ChatResponse(
            id=out.get("id", ""),
            model=out.get("model", ""),
            content=msg.get("content", ""),
            role=msg.get("role", "assistant"),
            finish_reason=choice.get("finish_reason"),
            usage=out.get("usage", {}),
            interaction_id=out.get("interaction_id"),
            domain_intelligence=out.get("bee_domain_intelligence"),
            raw=out,
        )

    def validate_computer_use_host_report(
        self,
        host: ComputerUseHostReport,
        request: ComputerUseActionRequest | None = None,
    ) -> ComputerUseHostReportValidation:
        """Validate a real computer-use host report/action contract at Bee's gateway."""
        body: dict[str, Any] = {"host": host}
        if request is not None:
            body["request"] = request
        return self._request("POST", "/computer/v1/host-reports", body)

    def chat_stream(
        self,
        message: str,
        domain: Domain | None = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        system: str | None = None,
        model: CustomerModelId | None = None,
    ) -> Iterator[str]:
        """Stream tokens as they're generated.

        Falls back to a single-shot response if the server doesn't yet
        emit SSE chunks (current /chat/completions doesn't stream;
        this method preserves the API for when streaming lands).
        """
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": message})
        body = {
            "model": _resolve_model(model),
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if domain:
            body["domain"] = domain
        # Try SSE first; if the server returns plain JSON, yield it whole.
        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                ct = resp.headers.get("content-type", "")
                if "text/event-stream" in ct:
                    for line in resp:
                        s = line.decode().strip()
                        if not s or not s.startswith("data:"):
                            continue
                        payload = s[5:].strip()
                        if payload == "[DONE]":
                            return
                        try:
                            d = json.loads(payload)
                            delta = (d.get("choices") or [{}])[0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue
                else:
                    # Server didn't honour stream=True - yield full response.
                    out = json.loads(resp.read().decode())
                    content = (out.get("choices") or [{}])[0].get("message", {}).get("content", "")
                    if content:
                        yield content
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            decision = _upgrade_decision(body_text)
            if decision is not None:
                raise BeeActionRequiredError(e.code, body_text, decision) from e
            raise BeeAPIError(e.code, body_text) from e

    def feedback(self, interaction_id: str, rating: str, comment: str | None = None) -> None:
        """Submit thumbs-up/down feedback. rating: 'up' | 'down'."""
        self._request(
            "POST",
            "/feedback",
            {
                "interaction_id": interaction_id,
                "rating": rating,
                "comment": comment,
            },
        )

    def provenance(self, session_id: str) -> dict:
        """Verify an agentic-coding session's provenance chain.

        When an agent-loop request carries a stable ``session_id``, Bee seals each
        served turn into a per-session, ML-DSA-65-signed (NIST FIPS 204) hash chain.
        Returns Bee's verdict, the chain (digests only - never your code), and the
        SPKI ``public_key_pem`` so you can INDEPENDENTLY re-verify every link offline
        with any FIPS-204 verifier.
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("provenance(session_id) requires a session id string")
        from urllib.parse import quote

        return self._request("GET", f"/provenance/{quote(session_id, safe='')}")

    def usage(self, window: str = "day") -> dict:
        """Account & usage for the caller: ``account`` (email, plan, organization),
        ``usage`` (pooled tokens, per-tier allowances, ``resets_at``, messages,
        active days, credits), and ``breakdown`` - the "what's contributing" tier
        share over a ``day`` (24h) or ``week`` (7d) window. This is the SAME real
        data the Bee workspace, desktop, mobile, and IDE surfaces show, for every
        tier - no fabricated numbers, no internal model ids.
        """
        w = "week" if window == "week" else "day"
        return self._request("GET", f"/usage?window={w}")

    def domains(self) -> list[str]:
        """List the domains Bee knows about."""
        # The domain list is published by /adapters (active + domains + loaded_count),
        # not /models (which is the OpenAI-shape tier list, no `domains` key).
        return self._request("GET", "/adapters").get("domains", [])

    def health(self) -> dict:
        return self._request("GET", "/health")

    def adapters(self) -> dict:
        """Currently-loaded LoRA adapters per domain (added 2026-04-28)."""
        return self._request("GET", "/adapters")

    # ── Documents (RAG) - gated on the `rag` plan entitlement ────────────
    def documents_search(self, query: str, k: int = 3) -> dict:
        """Search your Bee documents (RAG); returns the top matching chunks.

        Tenant-scoped to your API key's account. Requires a rag-entitled
        plan (the gateway 403s `rag_not_in_plan` otherwise). Added 0.5.0.
        """
        return self._request("POST", "/documents/retrieve", {"query": query, "k": k})

    def documents_add(self, content: str, source: str = "sdk-upload") -> dict:
        """Add a document to your Bee knowledge base so documents_search (and
        Bee) can use it. Counts against your plan's document limit. Added 0.5.0.
        """
        return self._request("POST", "/documents/upload", {"content": content, "source": source})

    # ── Personal memory - universal per-user opt-in (default-on) ──────────
    def memories_search(self, query: str, top_k: int = 6) -> dict:
        """Search your Bee personal memory. Honours your memory opt-in: a
        disabled account returns `{enabled: false, memories: []}`. Added 0.5.0.
        """
        return self._request("POST", "/memories/search", {"query": query, "top_k": top_k})

    def memories_add(self, content: str, kind: str = "fact") -> dict:
        """Save a fact to your Bee personal memory (recalled in future chats).
        `kind` ∈ identity|preference|fact|skill|project|episode. Near-duplicates
        are de-duplicated server-side. Added 0.5.0.
        """
        return self._request("POST", "/memories", {"content": content, "kind": kind})

    def documents_list(self) -> dict:
        """List the documents in your Bee knowledge base (the source manifest).
        Powers the bee://documents MCP resource. Added 0.6.0.
        """
        return self._request("GET", "/documents")

    def document_text(self, source: str) -> dict:
        """Return one document's full reconstructed text, by source name. Powers
        the bee://documents/<source> MCP resource template. 404 if the source is
        unknown to your account. Added 0.6.0.
        """
        from urllib.parse import quote

        return self._request("GET", f"/documents/text?source={quote(source)}")

    def memories_list(self) -> dict:
        """List your Bee personal memories. Powers the bee://memory MCP resource;
        honours your memory opt-in. Added 0.6.0.
        """
        return self._request("GET", "/memories")

    # ── Quantum Reasoning Lab - durable, tenant-scoped jobs ──────────────
    def quantum_reasoning_create(
        self,
        prompt: str,
        model: QuantumReasoningModel,
        product: QuantumProductId,
        provider_connection_id: str | None = None,
        workspace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> QuantumReasoningJob:
        """Create a durable Lab job and return its initial job record."""
        body = {"prompt": prompt, "model": model, "product": product}
        if provider_connection_id is not None:
            body["provider_connection_id"] = provider_connection_id
        if workspace_id is not None:
            body["workspace_id"] = workspace_id
        result = self._request(
            "POST",
            "/quantum-reasoning/jobs",
            body,
            {"Idempotency-Key": idempotency_key or str(uuid.uuid4())},
        )
        return result["job"]

    def quantum_reasoning_jobs(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        status: QuantumReasoningJobStatus | None = None,
        model: QuantumReasoningModel | None = None,
    ) -> QuantumReasoningJobPage:
        """List tenant jobs plus current model and real-QPU capabilities."""
        from urllib.parse import urlencode

        query = urlencode(
            {
                key: value
                for key, value in {
                    "cursor": cursor,
                    "limit": limit,
                    "status": status,
                    "model": model,
                }.items()
                if value is not None
            }
        )
        return self._request("GET", f"/quantum-reasoning/jobs{f'?{query}' if query else ''}")

    def quantum_reasoning_job(self, job_id: str) -> QuantumReasoningJob:
        """Retrieve one job with decrypted prompt, candidates, result, and evidence."""
        return self._request("GET", f"/quantum-reasoning/jobs/{job_id}")["job"]

    def quantum_reasoning_remove(self, job_id: str) -> dict:
        """Cancel queued work or erase terminal content while retaining audit metadata."""
        return self._request("DELETE", f"/quantum-reasoning/jobs/{job_id}")

    def quantum_reasoning_wait(
        self,
        job_id: str,
        *,
        timeout: float = 900,
        poll_interval: float = 2,
    ) -> QuantumReasoningJob:
        """Poll until the job reaches a terminal state or the timeout expires."""
        if timeout <= 0 or poll_interval <= 0:
            raise ValueError("timeout and poll_interval must be positive")
        deadline = time.monotonic() + timeout
        active = {"queued", "generating_candidates", "scoring", "selecting", "awaiting_qpu"}
        while time.monotonic() < deadline:
            job = self.quantum_reasoning_job(job_id)
            if job.get("status") not in active:
                return job
            time.sleep(poll_interval)
        raise TimeoutError(f"timed out waiting for quantum reasoning job {job_id}")


class AsyncBee(_BaseClient):
    """Async client - requires httpx. `pip install bee-sdk[async]`."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            import httpx
        except ImportError as e:
            raise ImportError(
                "AsyncBee requires httpx. Install with `pip install bee-sdk[async]`."
            ) from e
        self._client = httpx.AsyncClient(timeout=self.timeout, headers=self._headers())

    async def __aenter__(self) -> AsyncBee:
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the reusable connection pool."""
        await self._client.aclose()

    async def chat(
        self,
        message: str,
        domain: Domain | None = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        system: str | None = None,
        model: CustomerModelId | None = None,
    ) -> str:
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": message})
        body = {
            "model": _resolve_model(model),
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if domain:
            body["domain"] = domain
        r = await self._client.post(f"{self.base_url}/chat/completions", json=body)
        if r.status_code >= 400:
            decision = _upgrade_decision(r.text)
            if decision is not None:
                raise BeeActionRequiredError(r.status_code, r.text, decision)
            raise BeeAPIError(r.status_code, r.text)
        out = r.json()
        return (out.get("choices") or [{}])[0].get("message", {}).get("content", "")

    async def chat_stream(
        self,
        message: str,
        domain: Domain | None = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        system: str | None = None,
        model: CustomerModelId | None = None,
    ) -> AsyncIterator[str]:
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": message})
        async with self._client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json={
                "model": _resolve_model(model),
                **({"domain": domain} if domain else {}),
                "messages": msgs,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            },
        ) as resp:
            if resp.status_code >= 400:
                body_text = (await resp.aread()).decode(errors="replace")
                decision = _upgrade_decision(body_text)
                if decision is not None:
                    raise BeeActionRequiredError(resp.status_code, body_text, decision)
                raise BeeAPIError(resp.status_code, body_text)
            async for line in resp.aiter_lines():
                s = line.strip()
                if not s or not s.startswith("data:"):
                    continue
                payload = s[5:].strip()
                if payload == "[DONE]":
                    return
                try:
                    d = json.loads(payload)
                    delta = (d.get("choices") or [{}])[0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
                except json.JSONDecodeError:
                    continue

    async def quantum_reasoning_create(
        self,
        prompt: str,
        model: QuantumReasoningModel,
        product: QuantumProductId,
        provider_connection_id: str | None = None,
        workspace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> QuantumReasoningJob:
        body = {"prompt": prompt, "model": model, "product": product}
        if provider_connection_id is not None:
            body["provider_connection_id"] = provider_connection_id
        if workspace_id is not None:
            body["workspace_id"] = workspace_id
        headers = self._headers({"Idempotency-Key": idempotency_key or str(uuid.uuid4())})
        response = await self._client.post(
            f"{self.base_url}/quantum-reasoning/jobs", json=body, headers=headers
        )
        response.raise_for_status()
        return response.json()["job"]

    async def quantum_reasoning_jobs(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        status: QuantumReasoningJobStatus | None = None,
        model: QuantumReasoningModel | None = None,
    ) -> QuantumReasoningJobPage:
        params = {
            key: value
            for key, value in {
                "cursor": cursor,
                "limit": limit,
                "status": status,
                "model": model,
            }.items()
            if value is not None
        }
        response = await self._client.get(f"{self.base_url}/quantum-reasoning/jobs", params=params)
        response.raise_for_status()
        return response.json()

    async def quantum_reasoning_job(self, job_id: str) -> QuantumReasoningJob:
        response = await self._client.get(f"{self.base_url}/quantum-reasoning/jobs/{job_id}")
        response.raise_for_status()
        return response.json()["job"]

    async def quantum_reasoning_remove(self, job_id: str) -> dict:
        response = await self._client.delete(f"{self.base_url}/quantum-reasoning/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    async def quantum_reasoning_wait(
        self,
        job_id: str,
        *,
        timeout: float = 900,
        poll_interval: float = 2,
    ) -> QuantumReasoningJob:
        import asyncio

        if timeout <= 0 or poll_interval <= 0:
            raise ValueError("timeout and poll_interval must be positive")
        deadline = time.monotonic() + timeout
        active = {"queued", "generating_candidates", "scoring", "selecting", "awaiting_qpu"}
        while time.monotonic() < deadline:
            job = await self.quantum_reasoning_job(job_id)
            if job.get("status") not in active:
                return job
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"timed out waiting for quantum reasoning job {job_id}")
