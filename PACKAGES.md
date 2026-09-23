# Bee packages and developer distributions

Bee is operated intelligence infrastructure. These packages and extensions are public integration and client distributions, not a publication of the private Bee service monorepo.

Every artifact is distributed through its canonical ecosystem registry. Bee does not require a duplicate GitHub Packages feed. The machine-readable [package index](PACKAGE-INDEX.json) is covered by the repository checksums and attached to releases.

| Ecosystem | Artifact | Version | Role | License | Install |
| --- | --- | --- | --- | --- | --- |
| npm | [@heossihq/bee](https://www.npmjs.com/package/@heossihq/bee) | `1.0.6` | `typescript-sdk` | Apache-2.0 | `npm install @heossihq/bee` |
| PyPI | [bee-sdk](https://pypi.org/project/bee-sdk/) | `1.0.6` | `python-sdk-and-mcp-runtime` | Apache-2.0 | `pip install bee-sdk==1.0.6` |
| MCP Registry | [io.github.heossihq/bee-public](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.heossihq/bee-public) | `1.0.6` | `mcp-server` | Apache-2.0 | `uvx --from "bee-sdk==1.0.6" bee-mcp` |
| npm | [@heossihq/beecode](https://www.npmjs.com/package/@heossihq/beecode) | `1.0.6` | `proprietary-code-cli` | Proprietary | `npm install -g @heossihq/beecode` |
| Visual Studio Marketplace | [Heossi.beecode](https://marketplace.visualstudio.com/items?itemName=Heossi.beecode) | `0.2.12` | `proprietary-vscode-extension` | Proprietary | `code --install-extension Heossi.beecode` |
| Open VSX | [Heossi.beecode](https://open-vsx.org/extension/Heossi/beecode) | `0.2.12` | `proprietary-vscode-extension` | Proprietary | `Open VSX: Heossi.beecode` |

## Source and licensing boundary

The TypeScript SDK, Python SDK, MCP implementation, contracts, examples, and PQ verification material are inspectable in this public repository under Apache-2.0. Bee Code CLI and editor-extension implementations remain proprietary; the catalog identifies their canonical distribution endpoints without representing their source as public.

Hosted model serving, orchestration, governance, training, commercial applications, and infrastructure implementations remain in the private `heossihq/bee` monorepo. Publishing a package never changes repository visibility or the organization package-creation policy.

Versions are derived from reviewed source metadata and independently checked against their canonical registries before a public release.
