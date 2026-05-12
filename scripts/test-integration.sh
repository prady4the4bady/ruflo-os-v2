#!/bin/bash
# Tests the full stack is wired correctly.
# In developer environments, checks are skipped when required runtime dependencies are unavailable.
set -e

have() {
  command -v "$1" >/dev/null 2>&1
}

echo "=== Testing Vyrex API ==="
if have curl && [ -S /run/vyrex/api.sock ]; then
  if have jq; then
    curl -s --unix-socket /run/vyrex/api.sock http://localhost/v1/models | jq .
  else
    echo "jq not found; printing raw response"
    curl -s --unix-socket /run/vyrex/api.sock http://localhost/v1/models
  fi
else
  echo "SKIP: Vyrex socket or curl missing"
fi

echo "=== Testing Prax Agent ==="
if have node && [ -f /opt/kryos/agent/dist/index.js ]; then
  node /opt/kryos/agent/dist/index.js "take a screenshot and tell me what you see"
else
  echo "SKIP: Node runtime or /opt/kryos/agent/dist/index.js missing"
fi

echo "=== Testing Input Control ==="
if have ydotool; then
  ydotool mousemove -x 500 -y 500
  echo "Mouse moved to 500,500"
else
  echo "SKIP: ydotool not available"
fi

echo "=== Testing Screen Capture ==="
if have grim; then
  grim /tmp/test-capture.png && echo "Screenshot saved"
else
  echo "SKIP: grim not available"
fi

echo "=== Integration test script completed ==="
