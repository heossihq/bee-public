# Bee MCP installation for agents

Install `bee-mcp`, the stdio MCP server included in `bee-sdk`. It forwards sixteen governed tools to `https://api.bee.heossi.com/bee`; it does not download a model or require a GPU.

## Requirements

- Python 3.10 or later
- A `bee_sk_...` key from https://workspace.bee.heossi.com/account/api-keys

## Install and verify

```bash
pip install bee-sdk
bee-mcp --help
```

With `uv`, no persistent install is required:

```bash
uvx --from bee-sdk@latest bee-mcp
```

Register that command in the client's MCP configuration. Templates for Claude Desktop, Cursor, VS Code, and OpenCode are in [`mcp/configs`](./mcp/configs). Substitute the user's key locally and never write a real key into source control.

After restarting the client, confirm the Bee server connects and lists sixteen tools. Call `bee_chat` with `{"message":"Say OK.","max_tokens":16}`. A non-empty response verifies the authenticated gateway path.

Canonical MCP Registry identity: `io.github.heossihq/bee-public`.
