%global         srcname A.U.R.A. Linux

Name:           aura-eve-tool
Version:        0.6.0
Release:        0.4.alpha%{?dist}
Summary:        EVE Online tactical AI assistant and intel radar (Angel Cartel theme)
License:        AGPL-3.0-or-later
URL:            https://github.com/JeffTheNerdDev96/A.U.R.A.-eve-tool-linux
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  sed

Requires:       python3 >= 3.12
Requires:       python3-pyqt6
Requires:       python3-psutil
Requires:       python3-numpy
Requires:       python3-pillow
Requires:       python3-pypdf
Requires:       python3-python-docx
Requires:       python3-openpyxl
Requires:       python3-slixmpp
Requires:       python3-pytesseract
Requires:       tesseract
Requires:       opus
Requires:       vulkan-loader
Requires:       google-noto-sans-fonts
Recommends:     mesa-vulkan-drivers
Recommends:     python3-llama-cpp-python
Recommends:     python3-pymumble

%description
A.U.R.A. (Adaptive Underworld Recon Array) is an Angel Cartel themed EVE Online
tactical companion featuring a local GGUF language model neural core, a Live
Intel Radar, D-Scan and fleet composition analysis, a fitting laboratory,
wormhole mapping, and XMPP / Mumble VOIP integration.

The application is installed under /opt/aura. Per-user runtime state (logs and
model weights) is stored under ~/.local/share/aura following the FreeDesktop
XDG Base Directory specification.

Protected under the GNU Affero General Public License v3.0 (AGPL-3.0).

%prep
%setup -q -n %{name}-%{version}

%build
# Pure Python application: nothing to compile.

%install
rm -rf %{buildroot}
install -d %{buildroot}/opt/aura \
           %{buildroot}%{_bindir} \
           %{buildroot}%{_datadir}/applications \
           %{buildroot}%{_datadir}/icons/hicolor/256x256/apps \
           %{buildroot}%{_mandir}/man1 \
           %{buildroot}%{_libdir}/aura
cp -a "%{srcname}"/. %{buildroot}/opt/aura/
install -m 0755 packaging/common/aura %{buildroot}%{_bindir}/aura
install -m 0644 packaging/common/aura.desktop %{buildroot}%{_datadir}/applications/aura.desktop
install -m 0644 "%{srcname}"/assets/brand/app_icon.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/aura.png
install -m 0644 packaging/common/aura.1 %{buildroot}%{_mandir}/man1/aura.1
install -m 0755 packaging/common/aura-llm-setup.sh %{buildroot}%{_libdir}/aura/aura-llm-setup.sh

%post
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q %{_datadir}/applications || :
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q %{_datadir}/icons/hicolor || :
fi

%postun
if [ "$1" = 0 ]; then
    rm -rf /opt/aura/.venv 2>/dev/null || :
fi

%files
%license LICENSE
%doc README.md CHANGELOG.md
/opt/aura
%{_bindir}/aura
%{_datadir}/applications/aura.desktop
%{_datadir}/icons/hicolor/256x256/apps/aura.png
%{_mandir}/man1/aura.1
%{_libdir}/aura/aura-llm-setup.sh

%changelog
* Fri Dec 12 2025 JeffTheNerdDev96 <JeffTheNerdDev96@users.noreply.github.com> - 0.6.0-0.4.alpha
- Feature parity with Windows v0.6.0-alpha.4 (D-Scan, Mumble VOIP, dogma math,
  eve_ships_data / eve_modules_data, cross-platform paths)
- Initial Fedora RPM packaging
