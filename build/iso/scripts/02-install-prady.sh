#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${ISO_DIR}/../.." && pwd)"
ROOTFS="${ISO_DIR}/rootfs"
TARGET_OPT="${ROOTFS}/opt/kryos-os"

if [[ "${EUID}" -ne 0 ]]; then
  echo "[02-install-kryos] Please run as root (sudo)."
  exit 1
fi

if [[ ! -d "${ROOTFS}" ]]; then
  echo "[02-install-kryos] Missing rootfs. Run 01-bootstrap.sh first."
  exit 1
fi

mkdir -p "${TARGET_OPT}"

rsync -a --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude 'build/iso/rootfs' \
  --exclude 'build/prady-os.iso' \
  --exclude '__pycache__' \
  "${REPO_ROOT}/" "${TARGET_OPT}/"

mkdir -p "${ROOTFS}/opt/kryos-os/config"

# Build OOBE wizard assets inside chroot before service wiring.
cat > "${ROOTFS}/tmp/build-oobe.sh" <<'CHROOT'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/kryos-os/ui/oobe-wizard
npm install
npm run build
CHROOT
chmod +x "${ROOTFS}/tmp/build-oobe.sh"
chroot "${ROOTFS}" /bin/bash /tmp/build-oobe.sh
rm -f "${ROOTFS}/tmp/build-oobe.sh"

mkdir -p "${ROOTFS}/etc/systemd/system"

cat > "${ROOTFS}/etc/systemd/system/kryos-redis.service" <<'UNIT'
[Unit]
Description=Kryos Redis
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/docker run --rm --name kryos-redis -p 6379:6379 redis:7-alpine
ExecStop=/usr/bin/docker stop kryos-redis
Restart=always

[Install]
WantedBy=kryos.target
UNIT

cat > "${ROOTFS}/etc/systemd/system/kryos-vyrex.service" <<'UNIT'
[Unit]
Description=Kryos Vyrex
After=kryos-redis.service docker.service
Requires=kryos-redis.service

[Service]
Type=simple
ExecStart=/usr/bin/docker run --rm --name kryos-vyrex -v /opt/kryos-os/vyrex/policies:/policies:ro nvidia/vyrex:latest
ExecStop=/usr/bin/docker stop kryos-vyrex
Restart=always

[Install]
WantedBy=kryos.target
UNIT

cat > "${ROOTFS}/etc/systemd/system/kryos-model-gateway.service" <<'UNIT'
[Unit]
Description=Kryos Model Gateway
After=kryos-vyrex.service
Requires=kryos-vyrex.service

[Service]
Type=simple
WorkingDirectory=/opt/kryos-os
ExecStart=/usr/bin/docker compose -f /opt/kryos-os/docker-compose.dev.yml up model-gateway
ExecStop=/usr/bin/docker compose -f /opt/kryos-os/docker-compose.dev.yml stop model-gateway
Restart=always

[Install]
WantedBy=kryos.target
UNIT

cat > "${ROOTFS}/etc/systemd/system/kryos-swarm.service" <<'UNIT'
[Unit]
Description=Kryos Swarm
After=kryos-model-gateway.service
Requires=kryos-model-gateway.service

[Service]
Type=simple
WorkingDirectory=/opt/kryos-os
ExecStart=/usr/bin/docker compose -f /opt/kryos-os/docker-compose.dev.yml up kryos-swarm
ExecStop=/usr/bin/docker compose -f /opt/kryos-os/docker-compose.dev.yml stop kryos-swarm
Restart=always

[Install]
WantedBy=kryos.target
UNIT

cat > "${ROOTFS}/etc/systemd/system/kryos-platform.service" <<'UNIT'
[Unit]
Description=Kryos Platform Services
After=kryos-swarm.service
Requires=kryos-swarm.service

[Service]
Type=simple
WorkingDirectory=/opt/kryos-os
ExecStart=/usr/bin/docker compose -f /opt/kryos-os/docker-compose.dev.yml up vision-agent input-controller process-manager memory-store watchdog loop-runner
ExecStop=/usr/bin/docker compose -f /opt/kryos-os/docker-compose.dev.yml stop vision-agent input-controller process-manager memory-store watchdog loop-runner
Restart=always

[Install]
WantedBy=kryos.target
UNIT

cat > "${ROOTFS}/etc/systemd/system/kryos-oobe.service" <<'UNIT'
[Unit]
Description=Kryos OOBE API Service
After=network-online.target
Before=kryos-desktop.service

[Service]
Type=simple
WorkingDirectory=/opt/kryos-os/platform/oobe
ExecStart=/usr/bin/python3 /opt/kryos-os/platform/oobe/oobe_service.py
Restart=always

[Install]
WantedBy=kryos.target
UNIT

cat > "${ROOTFS}/etc/systemd/system/kryos-oobe-serve.service" <<'UNIT'
[Unit]
Description=Kryos OOBE Wizard Static Server
After=network-online.target
Before=kryos-desktop.service

[Service]
Type=simple
WorkingDirectory=/opt/kryos-os/ui/oobe-wizard
ExecStart=/usr/bin/npx serve -s /opt/kryos-os/ui/oobe-wizard/dist -l 8099
Restart=always

[Install]
WantedBy=kryos.target
UNIT

cat > "${ROOTFS}/etc/systemd/system/kryos-desktop.service" <<'UNIT'
[Unit]
Description=Kryos Desktop Shell
After=kryos-platform.service kryos-oobe.service
Requires=kryos-platform.service

[Service]
Type=simple
WorkingDirectory=/opt/kryos-os/ui/desktop-shell
ExecStart=/bin/bash -c 'cd /opt/kryos-os/ui/desktop-shell && npm run build && npx serve -s dist -l 3000'
Restart=always

[Install]
WantedBy=kryos.target
UNIT

cat > "${ROOTFS}/etc/systemd/system/kryos-browser.service" <<'UNIT'
[Unit]
Description=Kryos Browser Kiosk
After=kryos-desktop.service
Requires=kryos-desktop.service

[Service]
Type=simple
Environment=DISPLAY=:0
ExecStart=/usr/bin/chromium --kiosk --no-sandbox --app=http://localhost:3000 --disable-infobars
Restart=always

[Install]
WantedBy=kryos.target
UNIT

cat > "${ROOTFS}/etc/systemd/system/kryos.target" <<'UNIT'
[Unit]
Description=Kryos Full Stack Target
Requires=kryos-redis.service kryos-vyrex.service kryos-model-gateway.service kryos-swarm.service kryos-platform.service kryos-oobe.service kryos-desktop.service kryos-browser.service
After=multi-user.target
AllowIsolate=yes
UNIT

mkdir -p "${ROOTFS}/etc/systemd/system/default.target.wants"
ln -sfn /etc/systemd/system/kryos.target "${ROOTFS}/etc/systemd/system/default.target"

chroot "${ROOTFS}" /bin/bash -lc '
  set -e
  systemctl enable kryos-redis.service
  systemctl enable kryos-vyrex.service
  systemctl enable kryos-model-gateway.service
  systemctl enable kryos-swarm.service
  systemctl enable kryos-platform.service
  systemctl enable kryos-oobe.service
  systemctl enable kryos-desktop.service
  systemctl enable kryos-browser.service
'

echo "[02-install-kryos] Done."

