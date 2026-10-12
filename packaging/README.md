# A.U.R.A. — Dual-Distro Packaging (Ubuntu `.deb` + Fedora `.rpm`)

**License:** GNU Affero General Public License v3.0 (AGPL-3.0)

This directory contains the native Linux packaging pipelines for **Ubuntu / Debian**
and **Fedora / RHEL**. Both packages install the application source to `/opt/aura`
and a Wayland-aware launcher to `/usr/bin/aura`, and depend on the distribution's
own Python packages (no bundled virtual environment).

## Layout

```
packaging/
├─ common/
│  ├─ aura                 # /usr/bin/aura launcher shim (Wayland + XCB fallback)
│  ├─ aura.desktop         # FreeDesktop launcher entry
│  ├─ aura.1               # man page
│  └─ aura-llm-setup.sh    # optional llama-cpp-python / VOIP venv provisioner
├─ ubuntu/
│  ├─ debian/              # Debian source package control files
│  └─ build_deb.sh         # builds dist/aura-eve-tool_<ver>.deb
├─ fedora/
│  ├─ aura-eve-tool.spec   # RPM spec (also usable directly with COPR)
│  └─ build_rpm.sh         # builds dist/aura-eve-tool-<ver>.noarch.rpm
└─ build_all.sh            # convenience orchestrator
```

## Install layout (both distros)

| Path | Content |
|---|---|
| `/opt/aura/` | application source (`app.py`, `core/`, `subsystems/`, `ui/`, `assets/`, `data/`) |
| `/usr/bin/aura` | launcher shim |
| `/usr/share/applications/aura.desktop` | desktop entry |
| `/usr/share/icons/hicolor/256x256/apps/aura.png` | icon |
| `/usr/share/man/man1/aura.1` | man page |
| `~/.local/share/aura/{logs,models}` | per-user runtime state (XDG) |

## Building

Ubuntu / Debian host:

```bash
sudo apt install dpkg-dev debhelper
./packaging/ubuntu/build_deb.sh        # -> dist/aura-eve-tool_0.6.0~alpha.4_all.deb
```

Fedora / RHEL host:

```bash
sudo dnf install rpm-build
./packaging/fedora/build_rpm.sh        # -> dist/aura-eve-tool-0.6.0-0.4.alpha.fcXX.noarch.rpm
```

Both (where the toolchain exists):

```bash
./packaging/build_all.sh
```

## Dependencies

The packages depend on the distribution's Python modules (`python3-pyqt6`,
`python3-psutil`, `python3-numpy`, `python3-pillow`, `python3-pypdf`,
`python3-docx`/`python3-python-docx`, `python3-openpyxl`, `python3-slixmpp`,
`python3-pytesseract`), plus `tesseract-ocr`/`tesseract`, Vulkan/OpenGL loaders,
and the Opus codec.

Local GGUF inference (`llama-cpp-python`) and the Mumble VOIP stack
(`pymumble`, `opuslib`) are not packaged by every distribution. Provision them
into an isolated venv that the launcher automatically prefers:

```bash
sudo /usr/lib/aura/aura-llm-setup.sh vulkan   # or: cuda | cpu
```

## CI / COPR

`.github/workflows/build-linux-packages.yml` builds the `.deb` on `ubuntu-24.04`
and the `.rpm` inside a `fedora:latest` container on every `v*` tag.

For hosted Fedora builds, create a COPR project pointing at this repository and
set the spec file path to `packaging/fedora/aura-eve-tool.spec`.
