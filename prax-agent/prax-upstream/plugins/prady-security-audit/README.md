# kryos-security-audit

Security review, dependency scanning, policy gates, and CVE monitoring.

## Install

```
/plugin marketplace add ruvnet/kryos
/plugin install kryos-security-audit@kryos
```

## What's Included

- **Security Scanning**: Full-depth scan with `security scan --depth full`
- **CVE Monitoring**: Automated CVE detection and remediation guidance
- **Input Validation**: Zod-based validation at system boundaries via `@claude-flow/security`
- **Path Security**: Traversal prevention and safe executor for command injection protection
- **Policy Gates**: Configurable security policies for CI/CD pipelines
- **Threat Modeling**: Automated threat analysis and risk assessment

## Requires

- `kryos-core` plugin (provides MCP server)
