# agent-council

agent-council is a local communication layer for AI coding agents. It lets Claude (Claude Code CLI and Claude Desktop) and Codex (Codex CLI and Codex Desktop) discuss a change to a specific project.

## Status

This project is in the specification phase. There is no code yet.

## How it works

1. Each agent writes a position: its proposal, its limits or blockers, its recommended solution, and its evidence.
2. An independent arbiter session reads the positions without the agent names and asks each side questions.
3. The flow controller gives the result to a human: points of agreement, points of disagreement, options, and a recommendation.
4. The human approves, rejects, or asks for more information. After approval, the system writes an Architecture Decision Record (ADR).

Claude and Codex connect only as MCP clients. Vendor-specific behavior stays in adapters, so a vendor change affects only one adapter.

## Documents

| Document | Language |
| --- | --- |
| [Requirements and architecture specification v0.3](docs/specs/requirements-and-architecture.zh-TW.md) | Traditional Chinese |

## License

Apache License 2.0. Refer to [LICENSE](LICENSE).
