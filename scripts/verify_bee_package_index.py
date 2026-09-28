#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional


USER_AGENT = "Bee-public-package-verifier/1.0"
REQUEST_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2


def request_json(url: str, *, body: Optional[dict] = None) -> dict:
    data = None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(1, REQUEST_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (OSError, TimeoutError):
            if attempt == REQUEST_ATTEMPTS:
                raise
            time.sleep(RETRY_DELAY_SECONDS)
    raise AssertionError("unreachable")


def registry_version(artifact: dict) -> str:
    ecosystem = artifact["ecosystem"]
    name = artifact["name"]
    if ecosystem == "npm":
        encoded = urllib.parse.quote(name, safe="")
        return request_json(f"https://registry.npmjs.org/{encoded}/latest")["version"]
    if ecosystem == "PyPI":
        return request_json(f"https://pypi.org/pypi/{name}/json")["info"]["version"]
    if ecosystem == "MCP Registry":
        response = request_json(
            "https://registry.modelcontextprotocol.io/v0/servers"
            "?search=io.github.heossihq/bee-public"
        )
        versions = [
            (entry.get("server") or entry).get("version")
            for entry in response.get("servers", [])
            if (entry.get("server") or entry).get("name") == name
        ]
        if artifact["version"] not in versions:
            raise RuntimeError(f"MCP Registry version is missing: {name}@{artifact['version']}")
        return artifact["version"]
    if ecosystem == "Open VSX":
        namespace, extension = name.split(".", maxsplit=1)
        return request_json(f"https://open-vsx.org/api/{namespace}/{extension}/latest")["version"]
    if ecosystem == "Visual Studio Marketplace":
        response = request_json(
            "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
            "?api-version=7.2-preview.1",
            body={
                "filters": [
                    {
                        "criteria": [{"filterType": 7, "value": name}],
                        "pageNumber": 1,
                        "pageSize": 1,
                        "sortBy": 0,
                        "sortOrder": 0,
                    }
                ],
                "assetTypes": [],
                "flags": 914,
            },
        )
        return response["results"][0]["extensions"][0]["versions"][0]["version"]
    raise RuntimeError(f"Unsupported ecosystem: {ecosystem}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Verify Bee package-index versions against canonical registries."
    )
    parser.add_argument("index", nargs="?", default="PACKAGE-INDEX.json")
    args = parser.parse_args(argv)
    index_path = Path(args.index)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    artifacts = index.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise RuntimeError(f"No artifacts found in {index_path}")

    for artifact in artifacts:
        expected = artifact["version"]
        actual = registry_version(artifact)
        if actual != expected:
            raise RuntimeError(
                f'{artifact["ecosystem"]} {artifact["name"]}: '
                f"index={expected}, registry={actual}"
            )
        print(f'verified: {artifact["ecosystem"]} {artifact["name"]}@{actual}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
