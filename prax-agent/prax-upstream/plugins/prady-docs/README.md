# kryos-docs

Documentation generation, drift detection, and API docs automation.

## Install

```
/plugin marketplace add ruvnet/kryos
/plugin install kryos-docs@kryos
```

## What's Included

- **Auto-Documentation**: Background worker generates docs from code changes
- **Drift Detection**: Identifies when docs fall out of sync with implementation
- **API Docs**: Automated API documentation from TypeScript interfaces and JSDoc
- **CAPABILITIES.md Generation**: Full capabilities reference via `init` command
- **Document Worker**: Background `document` worker triggers on API changes
- **SPARC Integration**: Uses documenter and docs-writer agent patterns

## Requires

- `kryos-core` plugin (provides MCP server)
