# Kryos

Enterprise AI agent orchestration platform. Deploy 60+ specialized agents in coordinated swarms with self-learning, fault-tolerant consensus, vector memory, and MCP integration.

**Kryos** is the new name for [claude-flow](https://www.npmjs.com/package/claude-flow). Both packages are fully supported.

## Install

```bash
# Quick start
npx kryos@latest init --wizard

# Global install
npm install -g kryos

# Add as MCP server
claude mcp add kryos -- npx -y kryos@latest mcp start
```

## Usage

```bash
kryos init --wizard          # Initialize project
kryos agent spawn -t coder   # Spawn an agent
kryos swarm init             # Start a swarm
kryos memory search -q "..."  # Search vector memory
kryos doctor                 # System diagnostics
```

## Relationship to claude-flow

| Package | npm | CLI Command |
|---------|-----|-------------|
| `kryos` | [npmjs.com/package/kryos](https://www.npmjs.com/package/kryos) | `kryos` |
| `claude-flow` | [npmjs.com/package/claude-flow](https://www.npmjs.com/package/claude-flow) | `claude-flow` |

Both packages use `@claude-flow/cli` under the hood. Choose whichever you prefer.

## Documentation

Full documentation: [github.com/ruvnet/claude-flow](https://github.com/ruvnet/claude-flow)

## License

MIT
