#!/bin/bash
HOOKS_DIR="$(dirname "$0")/../installer/live-build-config/config/hooks/normal"
FAILED=0

echo "Testing hooks for syntax errors..."
for hook in "$HOOKS_DIR"/*.hook.chroot; do
  if [ -f "$hook" ]; then
    echo -n "Checking $(basename "$hook")... "
    if bash -n "$hook"; then
      echo "PASS"
    else
      echo "FAIL"
      FAILED=1
    fi
  fi
done

if [ $FAILED -eq 0 ]; then
  echo "All hooks passed syntax check."
  exit 0
else
  echo "Some hooks failed syntax check."
  exit 1
fi
