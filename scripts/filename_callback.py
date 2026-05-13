# git-filter-repo filename-callback body.
# Rename every path segment via the canonical Prady OS name map.
# Returning None drops the tree entry from the commit; we use that to
# pre-emptively drop predecessor files whose rename would collide with
# a file that already lived in the tree under its new name.
#
# The known collisions come from an earlier canonical-rename sweep that
# created new vyrex.py / lumyn.py / etc. alongside nemoclaw.py /
# hermes.py / etc. in the same working tree before the old names were
# deleted. For those pairs, the old-named file is always the one we
# want gone from history.

_SEGMENT_MAP = [
    # Multi-word renames first.
    (b"ruflo-agent-runtime",       b"prax-runtime"),
    (b"ruflo-upstream",            b"prax-upstream"),
    (b"ruflo-agent",               b"prax-agent"),
    (b"ruflo-firstboot-check",     b"prady-firstboot-check"),
    (b"ruflo-firstboot",           b"prady-firstboot"),
    (b"ruflo-session",             b"prady-session"),
    (b"ruflo-hermes-agent",        b"prady-lumyn"),
    (b"ruflo-hermes",              b"prady-lumyn"),
    (b"ruflo-nemoclaw-proxy",      b"prady-vyrex-proxy"),
    (b"ruflo-aqua-shell",          b"prady-desktop-shell"),
    (b"ruflo-model-gateway",       b"prady-model-gateway"),
    (b"ruflo-screen-agent",        b"prady-screen-agent"),
    (b"ruflo-workflow-engine",     b"prady-workflow-engine"),
    (b"ruflo-audit-log",           b"prady-audit-log"),
    (b"ruflo-automation",          b"prady-automation"),
    (b"ruflo-computer-use",        b"prady-computer-use"),
    (b"ruflo-memory-service",      b"prady-memory-service"),
    (b"ruflo-model-hub",           b"prady-model-hub"),
    (b"ruflo-notification-bus",    b"prady-notification-bus"),
    (b"ruflo-package-manager",     b"prady-package-manager"),
    (b"ruflo-persona-service",     b"prady-persona-service"),
    (b"ruflo-security-policy",     b"prady-security-policy"),
    (b"ruflo-swarm-coordinator",   b"prady-swarm-coordinator"),
    (b"ruflo-task-scheduler",      b"prady-task-scheduler"),
    (b"ruflo-watchdog",            b"prady-watchdog"),
    (b"ruflo-wayland-mcp",         b"prady-wayland-mcp"),
    (b"ruflo-setup",               b"prady-setup"),
    (b"ruflo-logo",                b"prady-logo"),
    (b"ruflo-ai",                  b"prady-ai"),
    (b"ruflo-base",                b"prady-base"),
    (b"ruflo-desktop",             b"prady-desktop"),
    (b"nemoclaw-upstream",         b"vyrex-upstream"),
    (b"hermes-upstream",           b"lumyn-upstream"),
    (b"HermesTaskPanel",           b"LumynTaskPanel"),
    (b"HermesConsole",             b"LumynConsole"),
    (b"hermes_bridge",             b"lumyn_bridge"),
    (b"hermes_format",             b"lumyn_format"),
    (b"hermes_policy",             b"lumyn_policy"),
    (b"hermes-skills",             b"lumyn-skills"),
    (b"hermes-config",             b"lumyn-config"),
    (b"hermes-agent",              b"lumyn"),
    # Mixed-case variants that appear in vendored content.
    (b"RUFLO-MCP",                 b"PRADY-MCP"),
    (b"RuFloUniverse",             b"PradyUniverse"),
    (b"RuFlo",                     b"Prady"),
    (b"ruFlo",                     b"prady"),
    (b"NemoClaw",                  b"Vyrex"),
    (b"nemoclaw",                  b"vyrex"),
    (b"Hermes",                    b"Lumyn"),
    (b"hermes",                    b"lumyn"),
    (b"Ruflo",                     b"Prady"),
    (b"ruflo",                     b"prady"),
    (b"RUFLO",                     b"PRADY"),
    (b"HERMES",                    b"LUMYN"),
    (b"NEMOCLAW",                  b"VYREX"),
    (b"nemos_shell",               b"prady_shell"),
    (b"nemos_models",              b"prady_models"),
]

# Old-named files whose rewrite would have collided with an already-existing
# file elsewhere in the tree. Drop them so history keeps only one copy.
_DROP_IF_PRESENT = {
    b"ai-core/model-gateway/app/nemoclaw.py",
    b"ai-core/model-gateway/app/_vyrex_compat.py",
    b"ai-core/model-gateway/tests/test_nemoclaw.py",
    b"orchestration/kryos-swarm/app/hermes_bridge.py",
    b"orchestration/kryos-swarm/tests/test_hermes_bridge.py",
    b"platform/lumyn-bridge/hermes_bridge.py",
    b"platform/lumyn-bridge/tests/test_hermes_bridge.py",
    b"platform/vyrex-proxy/tests/test_nemoclaw_proxy.py",
    b"prax-agent/src/hermes/hermes-adapter.ts",
    b"prax-agent/src/hermes/hermes-agent.ts",
    b"prax-agent/src/hermes/structured-plan.ts",
    b"prax-agent/src/nemoclaw-client.ts",
    b"prax-agent/src/ruflo-integration.ts",
    b"prax-agent/src/tools/ruflo-tools-adapter.ts",
    b"shell/prady-shell/components/NemoclawStatus.ts",
    b"shell/prady-shell/components/RufloAssistant.ts",
    b"ui/desktop-shell/src/HermesTaskPanel.tsx",
    b"ui/desktop-shell/src/__tests__/HermesConsole.test.tsx",
    b"ui/desktop-shell/src/apps/HermesConsole.tsx",
    b"vyrex/policies/hermes_policy.yaml",
    b"vyrex/policies/hermes-skills.yaml",
    b"agents/lumyn/app/hermes_format.py",
    b"agents/lumyn/config/hermes-config.yaml",
    b"build/iso/scripts/02-install-ruflo.sh",
    b"ui/desktop-shell/tsconfig.tsbuildinfo",
}

if filename in _DROP_IF_PRESENT:
    return None

_out = filename
for _old, _new in _SEGMENT_MAP:
    _out = _out.replace(_old, _new)
return _out
