"""Contract tests for the public MCP catalog used by registries and Glama."""

import unittest
from typing import get_args

from bee_sdk.mcp import DOMAINS, MODELS, RESOURCE_TEMPLATES, RESOURCES, TOOLS, handle_tool_call
from bee_sdk.types import CustomerModelId

EXPECTED_TOOLS = [
    "bee_chat",
    "bee_code",
    "bee_security",
    "bee_smith_assurance",
    "bee_research",
    "bee_verify_provenance",
    "bee_usage",
    "bee_documents_search",
    "bee_documents_add",
    "bee_memory_search",
    "bee_memory_add",
    "bee_quantum_reasoning_run",
    "bee_quantum_reasoning_jobs",
    "bee_quantum_reasoning_get",
    "bee_quantum_reasoning_remove",
    "bee_computer_use_validate_host",
]

EXPECTED_MCP_DOMAINS = [
    "general",
    "programming",
    "ai",
    "cybersecurity",
    "cryptography_pqc",
    "quantum",
    "fintech",
    "blockchain",
    "infrastructure",
    "research",
    "business",
]


class MCPCatalogTest(unittest.TestCase):
    def test_model_catalog_matches_the_public_sdk_request_type(self) -> None:
        expected = [
            "bee-cell",
            "bee-brood",
            "bee-comb",
            "bee-buzz",
            "bee-hive",
            "bee-swarm",
        ]
        self.assertEqual(MODELS, expected)
        self.assertEqual(list(get_args(CustomerModelId)), expected)
        self.assertEqual(TOOLS[0]["inputSchema"]["properties"]["model"]["enum"], expected)

    def test_domain_catalog_matches_the_hosted_curated_surface(self) -> None:
        self.assertEqual(DOMAINS, EXPECTED_MCP_DOMAINS)
        self.assertEqual(TOOLS[0]["inputSchema"]["properties"]["domain"]["enum"], EXPECTED_MCP_DOMAINS)

    def test_exact_tool_catalog_and_behavioral_annotations(self) -> None:
        self.assertEqual([tool["name"] for tool in TOOLS], EXPECTED_TOOLS)
        read_only = 0
        writes = 0
        for tool in TOOLS:
            self.assertTrue(tool["title"])
            self.assertGreaterEqual(len(tool["description"]), 80)
            annotations = tool["annotations"]
            self.assertEqual(annotations["title"], tool["title"])
            for hint in (
                "readOnlyHint",
                "destructiveHint",
                "idempotentHint",
                "openWorldHint",
            ):
                self.assertIsInstance(annotations[hint], bool)
            read_only += annotations["readOnlyHint"] is True
            writes += annotations["readOnlyHint"] is False
        self.assertEqual(read_only, 11)
        self.assertEqual(writes, 5)

    def test_resources_are_exact_and_tenant_data_is_described(self) -> None:
        self.assertEqual(
            [resource["uri"] for resource in RESOURCES],
            ["bee://status", "bee://domains", "bee://documents", "bee://memory"],
        )
        self.assertEqual(
            [template["uriTemplate"] for template in RESOURCE_TEMPLATES],
            ["bee://documents/{source}"],
        )

    def test_smith_dispatch_is_fail_closed_and_customer_scoped(self) -> None:
        class Client:
            kwargs: dict = {}

            def chat(self, **kwargs):
                self.kwargs = kwargs
                return "disposition"

        client = Client()
        result = handle_tool_call(
            client,
            "bee_smith_assurance",
            {
                "task": "release_disposition",
                "target": "customer release",
                "authorization_scope": "written scope",
                "evidence": "signed evidence",
                "profile": "regulated",
            },
        )
        self.assertEqual(result, "disposition")
        self.assertEqual(client.kwargs["domain"], "cybersecurity")
        self.assertEqual(client.kwargs["temperature"], 0)
        self.assertIn("written scope", client.kwargs["message"])
        self.assertIn("fail closed", client.kwargs["system"])
        self.assertIn("not a government certification", client.kwargs["system"])

    def test_usage_renders_dynamic_fair_use_without_a_fake_token_bundle(self) -> None:
        class Client:
            def usage(self, _window):
                return {
                    "account": {
                        "plan_name": "Bee Cell",
                        "plan_id": "bee-cell",
                        "organization": "Personal",
                        "email": "user@example.com",
                    },
                    "usage": {
                        "usage_policy": "dynamic_fair_use",
                        "fair_use": {"status": "available", "percent_used": 12},
                        "resets_at": "2026-10-01T00:00:00Z",
                        "completed_requests": 3,
                        "active_days": 1,
                        "allowances": [],
                    },
                    "breakdown": {},
                }

        result = handle_tool_call(Client(), "bee_usage", {"window": "week"})
        self.assertIn("Included usage: available · 12% used", result)
        self.assertNotIn("Pooled tokens", result)


if __name__ == "__main__":
    unittest.main()
