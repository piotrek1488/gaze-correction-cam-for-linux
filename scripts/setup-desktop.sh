#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
if ! /usr/bin/python3 -c "import gi; gi.require_version('Gtk','3.0')" 2>/dev/null; then
    echo 'Install desktop dependencies: sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1' >&2
    exit 1
fi
if ! /usr/bin/python3 -c "import gi; gi.require_version('AyatanaAppIndicator3','0.1')" 2>/dev/null; then
    if ! /sbin/ldconfig -p | grep -q libayatana-appindicator3.so; then
        echo 'Install: sudo apt install gir1.2-ayatanaappindicator3-0.1' >&2
        exit 1
    fi
    mkdir -p .downloads .desktop-deps
    (cd .downloads && apt-get download gir1.2-ayatanaappindicator3-0.1)
    for package in .downloads/gir1.2-ayatanaappindicator3-0.1_*.deb; do
        dpkg-deb -x "$package" .desktop-deps
    done
fi
/usr/bin/python3 scripts/install-desktop.py
# Launch detached so the setup script returns the terminal instead of blocking.
exec ./run-tray.sh --background
