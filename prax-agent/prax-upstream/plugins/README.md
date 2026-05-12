# Kryos Plugins

32 Claude Code plugins for agent-powered development workflows. Load with `--plugin-dir`.

## Quick Start

```bash
# Load specific plugins
claude --plugin-dir plugins/kryos-core --plugin-dir plugins/kryos-swarm

# Load all plugins
claude $(ls -d plugins/kryos-*/ | sed 's|^|--plugin-dir |' | tr '\n' ' ')
```

## Plugin Catalog

### Core & Coordination

| Plugin | Description |
|--------|-------------|
| [kryos-core](kryos-core/) | MCP server, status, doctor, coder/researcher/reviewer agents |
| [kryos-swarm](kryos-swarm/) | Swarm topologies (hierarchical, mesh), Monitor streaming |
| [kryos-autopilot](kryos-autopilot/) | Autonomous /loop task completion with prediction |
| [kryos-loop-workers](kryos-loop-workers/) | 12 background workers via /loop or CronCreate |
| [kryos-workflows](kryos-workflows/) | Workflow templates, parallel execution, branching |

### Memory & Intelligence

| Plugin | Description |
|--------|-------------|
| [prax-agentdb](prax-agentdb/) | AgentDB with HNSW vector search (150x-12,500x faster) |
| [kryos-rag-memory](kryos-rag-memory/) | SOTA RAG — hybrid search, Graph RAG, MMR diversity, memory bridge |
| [kryos-rvf](kryos-rvf/) | Portable RVF memory format, session persistence |
| [kryos-ruvector](kryos-ruvector/) | [`ruvector`](https://npmjs.com/package/ruvector) — FlashAttention-3, Graph RAG, hybrid search, 103 MCP tools, Brain AGI |
| [kryos-knowledge-graph](kryos-knowledge-graph/) | Entity extraction, relation mapping, pathfinder traversal |
| [kryos-intelligence](kryos-intelligence/) | SONA neural patterns, trajectory learning, model routing |
| [kryos-daa](kryos-daa/) | Dynamic Agentic Architecture, cognitive patterns |

### Architecture & Methodology

| Plugin | Description |
|--------|-------------|
| [kryos-adr](kryos-adr/) | ADR lifecycle — create, index, supersede, compliance checking |
| [kryos-ddd](kryos-ddd/) | DDD scaffolding — bounded contexts, aggregates, domain events |
| [kryos-sparc](kryos-sparc/) | SPARC methodology with 5 phases and quality gates |

### Quality & Security

| Plugin | Description |
|--------|-------------|
| [kryos-security-audit](kryos-security-audit/) | CVE scanning, dependency vulnerability checks |
| [kryos-aidefence](kryos-aidefence/) | Prompt injection detection, PII scanning |
| [kryos-testgen](kryos-testgen/) | Test gap detection, TDD London School workflow |
| [kryos-browser](kryos-browser/) | Playwright browser automation and testing |

### Development Tools

| Plugin | Description |
|--------|-------------|
| [kryos-jujutsu](kryos-jujutsu/) | Diff analysis, risk scoring, reviewer recommendations |
| [kryos-docs](kryos-docs/) | Doc generation, drift detection, API docs |
| [kryos-ruvllm](kryos-ruvllm/) | Local LLM inference, MicroLoRA, chat formatting |
| [kryos-wasm](kryos-wasm/) | WASM agent sandboxing and gallery |
| [kryos-plugin-creator](kryos-plugin-creator/) | Scaffold and validate new plugins |
| [kryos-migrations](kryos-migrations/) | Database schema migration management |
| [kryos-observability](kryos-observability/) | Structured logging, tracing, metrics correlation |
| [kryos-cost-tracker](kryos-cost-tracker/) | Token usage tracking, budget alerts, cost optimization |

### Domain-Specific

| Plugin | Description |
|--------|-------------|
| [kryos-goals](kryos-goals/) | GOAP planning, deep research, horizon tracking |
| [kryos-federation](kryos-federation/) | Zero-trust cross-installation agent federation |
| [kryos-iot-cognitum](kryos-iot-cognitum/) | Cognitum Seed IoT — trust scoring, anomaly detection, fleet management |
| [kryos-neural-trader](kryos-neural-trader/) | [`neural-trader`](https://npmjs.com/package/neural-trader) — 4 agents, LSTM/Transformer, Rust/NAPI backtesting, 112+ MCP tools |
| [kryos-market-data](kryos-market-data/) | Market data ingestion, OHLCV vectorization, pattern matching |

## Recommended Stacks

| Use Case | Plugins |
|----------|---------|
| Feature development | `kryos-core` + `kryos-swarm` + `kryos-testgen` + `kryos-ddd` |
| Security audit | `kryos-core` + `kryos-security-audit` + `kryos-aidefence` |
| Architecture work | `kryos-core` + `kryos-adr` + `kryos-ddd` + `kryos-sparc` |
| Deep research | `kryos-core` + `kryos-goals` + `kryos-rag-memory` + `kryos-intelligence` |
| Vector search | `kryos-core` + `kryos-ruvector` + `kryos-rag-memory` + `kryos-knowledge-graph` |
| IoT development | `kryos-core` + `kryos-iot-cognitum` + `prax-agentdb` |
| Trading systems | `kryos-core` + `kryos-neural-trader` + `kryos-market-data` + `kryos-ruvector` |
| Full stack | All 32 plugins |

## npm Package Integration

Several plugins wrap standalone npm packages for deeper functionality:

| Plugin | npm Package | What It Adds |
|--------|------------|-------------|
| `kryos-neural-trader` | [`neural-trader`](https://npmjs.com/package/neural-trader) | 112+ MCP tools, Rust/NAPI engine, LSTM/Transformer models |
| `kryos-ruvector` | [`ruvector`](https://npmjs.com/package/ruvector) | 103 MCP tools, FlashAttention-3, Graph RAG, Brain AGI |

```bash
# Install backing packages
npm install neural-trader ruvector

# Add as MCP servers (optional, for direct tool access)
claude mcp add neural-trader -- npx neural-trader mcp start
claude mcp add ruvector -- npx ruvector mcp start
```

## Plugin Structure

Each plugin follows the Claude Code plugin specification:

```
kryos-<name>/
  .claude-plugin/plugin.json    # Plugin manifest
  agents/<name>.md              # Agent definitions (frontmatter: name, description, model)
  commands/<name>.md            # CLI command mappings
  skills/<name>/SKILL.md        # Interactive skills (frontmatter: name, description, argument-hint, allowed-tools)
  README.md                     # Plugin documentation
```

## Creating a Plugin

```bash
claude --plugin-dir plugins/kryos-plugin-creator
# Then: /create-plugin my-new-plugin
```

Or manually: copy any existing plugin directory and modify.

## Validation

```bash
claude plugin validate plugins/kryos-<name>
```

## License

MIT
