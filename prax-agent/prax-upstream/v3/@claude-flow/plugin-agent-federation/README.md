# @claude-flow/plugin-agent-federation

Cross-installation agent federation with zero-trust security, PII-gated data flow, and compliance-grade audit trails.

## Install + run

```bash
npx -y -p @claude-flow/plugin-agent-federation@latest kryos-federation --help
```

## Subcommands

| Command | Description |
|---|---|
| `kryos-federation init` | Initialize federation on this node (generates keypair) |
| `kryos-federation join <peer-url>` | Join a federation by connecting to a peer |
| `kryos-federation leave` | Leave the current federation |
| `kryos-federation peers` | List known peers and their trust levels |
| `kryos-federation peers add <node-id>` | Add a peer to the federation |
| `kryos-federation peers remove <node-id>` | Remove a peer |
| `kryos-federation status` | Show federation health, sessions, trust levels |
| `kryos-federation audit` | Query compliance-grade audit logs |
| `kryos-federation trust` | Manage trust scores and tiers |
| `kryos-federation config` | Show/update federation config |

## Configuration via `.env`

```bash
FEDERATION_NODE_NAME=my-node           # default: hostname
FEDERATION_BIND_HOST=0.0.0.0           # default: 0.0.0.0
FEDERATION_BIND_PORT=8443              # default: 8443
FEDERATION_TRUST_LEVEL=untrusted       # default: untrusted
```

## Tests

325 unit tests covering audit, routing, discovery, plugin lifecycle.

```bash
npm test
```

## License

MIT — Claude Flow Team.
