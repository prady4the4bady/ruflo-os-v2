# kryos-plugin-creator

Scaffold, validate, and publish new Claude Code plugins with proper structure and MCP tool wiring.

## Install

```
/plugin marketplace add ruvnet/kryos
/plugin install kryos-plugin-creator@kryos
```

## Features

- **Scaffold plugins**: Generate complete plugin directory structure in seconds
- **Validate format**: Check plugin.json, SKILL.md frontmatter, and file references
- **MCP tool wiring**: Auto-discover and wire kryos MCP tools into skills
- **Marketplace integration**: Update marketplace.json for distribution

## Commands

- `/create-plugin` -- Interactively scaffold a new Claude Code plugin

## Skills

- `create-plugin` -- Generate plugin structure with skills, commands, and agents
- `validate-plugin` -- Validate plugin format and catch issues before publishing
