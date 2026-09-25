"""Bee Python SDK - official client for Bee API.

    pip install bee-sdk

    from bee_sdk import Bee

    bee = Bee()  # reads BEE_API_URL + BEE_API_KEY from env
    print(bee.chat("Explain quantum error correction", domain="quantum"))

    # Streaming
    for chunk in bee.chat_stream("Write a fibonacci function", domain="programming"):
        print(chunk, end="", flush=True)

    # Async
    import asyncio
    async def main():
        client = Bee.async_client()
        result = await client.chat("Audit this code for SQL injection", domain="cybersecurity")
        print(result)
    asyncio.run(main())

The SDK calls the Bee FastAPI surface (see bee/server.py for the full
endpoint catalogue). For MCP-tool integration (Claude Desktop, Cursor,
VS Code, …) this package ships a hosted MCP server - run ``bee-mcp``
(console script) or ``python -m bee_sdk.mcp``; see ``bee_sdk/mcp.py``.
"""

from .client import (
    AsyncBee,
    Bee,
    BeeActionRequiredError,
    BeeAPIError,
    BeeError,
    RateLimitError,
)
from .quantum_local import QuantumLocalResult, execute_byopa_direct, quantum_local_select
from .types import (
    ChatMessage,
    ChatResponse,
    ComputerUseAction,
    ComputerUseActionRequest,
    ComputerUseApprovalClass,
    ComputerUseCapability,
    ComputerUseCapabilityState,
    ComputerUseHostReport,
    ComputerUseHostReportValidation,
    ComputerUseHostType,
    CustomerModelId,
    Domain,
    DomainIntelligenceMetadata,
    ModelTier,
    QuantumProductId,
    QuantumReasoningCandidate,
    QuantumReasoningFallbackReason,
    QuantumReasoningJob,
    QuantumReasoningJobPage,
    QuantumReasoningJobStatus,
    QuantumReasoningModel,
    QuantumReasoningOutcomeState,
    QuantumReasoningRealRequestStatus,
)

__version__ = "1.0.27"
__all__ = [
    "Bee",
    "AsyncBee",
    "BeeError",
    "RateLimitError",
    "BeeAPIError",
    "BeeActionRequiredError",
    "ChatMessage",
    "ChatResponse",
    "ComputerUseAction",
    "ComputerUseActionRequest",
    "ComputerUseApprovalClass",
    "ComputerUseCapability",
    "ComputerUseCapabilityState",
    "ComputerUseHostReport",
    "ComputerUseHostReportValidation",
    "ComputerUseHostType",
    "CustomerModelId",
    "Domain",
    "DomainIntelligenceMetadata",
    "ModelTier",
    "QuantumProductId",
    "QuantumReasoningFallbackReason",
    "QuantumReasoningCandidate",
    "QuantumReasoningJob",
    "QuantumReasoningJobPage",
    "QuantumReasoningJobStatus",
    "QuantumReasoningModel",
    "QuantumReasoningOutcomeState",
    "QuantumReasoningRealRequestStatus",
    "QuantumLocalResult",
    "quantum_local_select",
    "execute_byopa_direct",
    "__version__",
]
