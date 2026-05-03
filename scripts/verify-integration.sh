#!/bin/bash
echo "=== PradyOS Integration Verification ==="

echo "[1] Checking Vyrex..."
if [ -d "/opt/vyrex" ]; then
  echo "  ✓ Vyrex installed at /opt/vyrex"
  python3 -c "import vyrex; print('  ✓ Vyrex importable')" 2>/dev/null || echo "  ✗ Vyrex not importable"
else
  echo "  ✗ Vyrex NOT installed"
fi

echo "[2] Checking Lumyn..."
if [ -d "/opt/lumyn" ]; then
  echo "  ✓ Lumyn installed at /opt/lumyn"
  lumyn --version 2>/dev/null && echo "  ✓ lumyn CLI works" || echo "  ✗ lumyn CLI not in PATH"
else
  echo "  ✗ Lumyn NOT installed"
fi

echo "[3] Checking Prady..."
if [ -d "/opt/prax-agent" ]; then
  echo "  ✓ Prady installed at /opt/prax-agent"
  prady --version 2>/dev/null && echo "  ✓ prady CLI works" || echo "  ✗ prady CLI not in PATH"
else
  echo "  ✗ Prax Agent NOT installed"
fi

echo "[4] Checking systemd services..."
for svc in vyrex prax-agent prady-firstboot ydotoold; do
  systemctl is-enabled $svc 2>/dev/null && echo "  ✓ $svc enabled" || echo "  ✗ $svc NOT enabled"
done

echo "[5] Checking swarm config..."
if [ -f "/etc/prady/swarm-default.yaml" ]; then
  echo "  ✓ swarm-default.yaml exists"
  grep -q "inference_backend: vyrex" /etc/prady/swarm-default.yaml && \
    echo "  ✓ Vyrex set as inference backend" || echo "  ✗ inference_backend wrong"
  grep -q "lumyn-primary" /etc/prady/swarm-default.yaml && \
    echo "  ✓ Lumyn agents configured" || echo "  ✗ Lumyn agents missing"
else
  echo "  ✗ swarm-default.yaml MISSING"
fi

echo "=== Verification Complete ==="
