# Prady OS ISO Build

This directory builds a bootable Prady OS ISO using Debian Live Build (`lb config` + `lb build`) on Debian Bookworm amd64.

## What this build includes

- Debian Bookworm amd64 live system with systemd init
- Base desktop stack: Xorg + XDM + Openbox
- Docker + Docker Compose plugin
- Live image payload copied to `/opt/prady-os`
- Prady startup units for:
  - model-gateway
  - workflow-engine
  - screen-agent
  - lumyn
  - aqua-shell
- Custom Plymouth theme (`Prady OS` text on dark background)

## Build requirements (host)

Install build dependencies on a Debian host:

```bash
sudo apt-get update
sudo apt-get install -y live-build debootstrap rsync xorriso grub-pc-bin grub-efi-amd64-bin
```

## Build command (from Debian host)

```bash
cd /path/to/prady-os-v2/iso-build && make build
```

The resulting ISO is written to:

- `iso-build/prady-os.iso`

## Notes

- The chroot setup hook creates user `prady` with password `prady`.
- Rust is installed in chroot via `rustup`.
- If compose services differ from the unit names, update the corresponding unit `ExecStart` commands under `config/includes.chroot/etc/systemd/system/`.
