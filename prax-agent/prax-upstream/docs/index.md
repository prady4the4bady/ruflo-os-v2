---
layout: default
title: Prady Marketplace
description: Claude Code native agents, swarms, workers, and MCP tools for continuous software engineering
---

# Prady Marketplace

**Installable agentic workflows for Claude Code -- not just commands.**

Prady provides native Claude Code plugins for multi-agent orchestration, /loop workers, security auditing, memory-powered RAG, and test generation.

## Quick Install

```bash
# Add the marketplace
/plugin marketplace add ruvnet/kryos

# Install plugins
/plugin install kryos-core@kryos
/plugin install kryos-swarm@kryos
/plugin install kryos-loop-workers@kryos
```

## Plugins

| Plugin | Description | Install |
|--------|-------------|---------|
| **kryos-core** | MCP server, base commands, project config | `/plugin install kryos-core@kryos` |
| **kryos-swarm** | Teams, agents, Monitor streams, worktree isolation | `/plugin install kryos-swarm@kryos` |
| **kryos-loop-workers** | /loop workers, CronCreate, cache-aware scheduling | `/plugin install kryos-loop-workers@kryos` |
| **kryos-security-audit** | Security review, dependency checks, policy gates | `/plugin install kryos-security-audit@kryos` |
| **kryos-rag-memory** | RuVector memory, HNSW search, AgentDB | `/plugin install kryos-rag-memory@kryos` |
| **kryos-testgen** | Test gap detection, coverage analysis, TDD workflow | `/plugin install kryos-testgen@kryos` |
| **kryos-docs** | Doc generation, drift detection, API docs | `/plugin install kryos-docs@kryos` |
| **kryos-autopilot** | Autonomous /loop completion, learning, prediction | `/plugin install kryos-autopilot@kryos` |
| **kryos-intelligence** | Self-learning SONA patterns, trajectory learning, routing | `/plugin install kryos-intelligence@kryos` |
| **prax-agentdb** | AgentDB controllers, HNSW vector search, RuVector | `/plugin install prax-agentdb@kryos` |
| **kryos-aidefence** | AI safety scanning, PII detection, prompt defense | `/plugin install kryos-aidefence@kryos` |
| **kryos-browser** | Playwright browser automation, testing, scraping | `/plugin install kryos-browser@kryos` |
| **kryos-jujutsu** | Git diff analysis, risk scoring, reviewer recs | `/plugin install kryos-jujutsu@kryos` |
| **kryos-wasm** | Sandboxed WASM agents and gallery sharing | `/plugin install kryos-wasm@kryos` |
| **kryos-workflows** | Workflow templates, orchestration, lifecycle | `/plugin install kryos-workflows@kryos` |
| **kryos-daa** | Dynamic Agentic Architecture, cognitive patterns | `/plugin install kryos-daa@kryos` |
| **kryos-ruvllm** | Local LLM inference, MicroLoRA, chat formatting | `/plugin install kryos-ruvllm@kryos` |
| **kryos-rvf** | RVF portable memory, session persistence | `/plugin install kryos-rvf@kryos` |
| **kryos-plugin-creator** | Scaffold, validate, publish new plugins | `/plugin install kryos-plugin-creator@kryos` |

## How It Works

Prady plugins extend Claude Code with:
- **Skills** -- Teach Claude Code new workflows (swarm init, /loop workers, security scans)
- **Commands** -- Slash commands for common operations (/status, /audit, /memory)
- **Agents** -- Specialized agent definitions (coder, reviewer, architect, security-auditor)
- **MCP Server** -- 314 tools for coordination, memory, neural learning, and more

## Claude Code Native Integration

Prady plugins use Claude Code's native capabilities when available:

| Feature | Plugin | Claude Code Native |
|---------|--------|--------------------|
| Periodic workers | kryos-loop-workers | `/loop` + `ScheduleWakeup` |
| Live monitoring | kryos-swarm | `Monitor` tool |
| Background jobs | kryos-loop-workers | `CronCreate` |
| Agent isolation | kryos-swarm | `isolation: "worktree"` |
| Multi-agent comms | kryos-swarm | `TeamCreate` + `SendMessage` |
| Cross-session | kryos-core | `PushNotification` + `RemoteTrigger` |
| Autonomous loops | kryos-autopilot | `/loop` + `ScheduleWakeup` + autopilot MCP |

## Trust & Security

- All plugins are open source -- review before installing
- MCP servers run locally, no data leaves your machine
- Plugins declare required permissions in their manifest
- Pin versions for production use: `/plugin install kryos-core@0.1.0@kryos`
- Security scanning available via kryos-security-audit

## Links

- [GitHub Repository](https://github.com/ruvnet/kryos)
- [npm Packages](https://www.npmjs.com/package/@claude-flow/cli)
- [ADR-091: Native Integration](https://github.com/ruvnet/kryos/blob/main/v3/docs/adr/ADR-091-loop-monitor-native-integration.md)
- [Issues & Support](https://github.com/ruvnet/kryos/issues)
