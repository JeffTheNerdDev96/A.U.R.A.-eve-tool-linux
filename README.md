# A.U.R.A.-eve-tool-linux
Your all-in-one EVE Online tactical tool — Linux Edition

# Adaptive Underworld Recon Array (A.U.R.A.) — Native Linux & Ubuntu Quickstart

**Product Version:** `v0.6.0-alpha.4`  
**License:** GNU Affero General Public License Version 3 (AGPL-3.0)  
**Author & Maintainer:** JeffTheNerdDev96  

---

## 1. Prerequisites

A.U.R.A. Linux requires **Python 3.12+** and modern Vulkan/OpenGL libraries.

### Ubuntu 24.04 / 22.04 LTS & Debian:
```bash
sudo apt update && sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    libgl1-mesa-glx \
    libegl1 \
    libvulkan1 \
    vulkan-tools \
    mesa-vulkan-drivers \
    tesseract-ocr \
    tesseract-ocr-eng
```

### Fedora Linux (39 / 40 / 41):
```bash
sudo dnf install -y python3 python3-pip vulkan-loader mesa-vulkan-drivers tesseract
```

### Arch Linux:
```bash
sudo pacman -S python python-pip vulkan-icd-loader mesa tesseract tesseract-data-eng
```

---

## 2. Quick Setup

From within the `A.U.R.A. Linux` directory:

```bash
# 1. Run the automated Ubuntu setup script
./distro/setup_ubuntu.sh

# 2. Select hardware acceleration (Vulkan, CUDA, or CPU)
./distro/install_ubuntu.sh

# 3. Launch A.U.R.A.
./distro/run_aura.sh
```

---

## 3. Desktop Application Launcher

The setup script automatically registers `aura.desktop` in `~/.local/share/applications/`.  
You can search for **"Adaptive Underworld Recon Array"** in your GNOME / KDE / Cinnamon application menu and pin it to your dock.

---

## 4. EVE Online Chatlog & Telemetry Discovery on Linux

A.U.R.A. automatically discovers EVE Online chatlogs across all popular Linux game runners:

| Platform | Discovered Path |
|---|---|
| **Steam Proton** | `~/.steam/steam/steamapps/compatdata/8500/pfx/drive_c/users/steamuser/Documents/EVE/logs/Chatlogs` |
| **Flatpak Steam** | `~/.var/app/com.valvesoftware.Steam/.steam/steam/steamapps/compatdata/8500/pfx/drive_c/users/steamuser/Documents/EVE/logs/Chatlogs` |
| **Lutris** | `~/Games/eve-online/drive_c/users/<user>/Documents/EVE/logs/Chatlogs` |
| **Wine Prefix** | `~/.wine/drive_c/users/<user>/Documents/EVE/logs/Chatlogs` |

---

## 5. Wayland & X11 Integration

- **Wayland (Default on Ubuntu 22.04/24.04):** A.U.R.A. automatically routes to native Wayland with fallback to XCB.
- **Explicit Override:**
  ```bash
  QT_QPA_PLATFORM=wayland ./distro/run_aura.sh   # Force Wayland
  QT_QPA_PLATFORM=xcb ./distro/run_aura.sh       # Force X11 / XCB
  ```

---

## 6. Packaging & Releases

Prebuilt native packages target the two most common Linux families:

- **Ubuntu / Debian:** `./packaging/ubuntu/build_deb.sh` → `dist/aura-eve-tool_*.deb`
- **Fedora / RHEL:** `./packaging/fedora/build_rpm.sh` → `dist/aura-eve-tool-*.rpm`

Both install the application to `/opt/aura` with a `/usr/bin/aura` launcher.
See [`packaging/README.md`](packaging/README.md). GitHub Actions builds both
artifacts on every `v*` tag.

---

## 7. Verification

```bash
cd "A.U.R.A. Linux"
python tools/run_all_tests.py
```

---

## 8. License & Copyleft

Protected under the **GNU Affero General Public License Version 3 (AGPL-3.0)**.  
See [`LICENSE`](LICENSE) in the repository root.
