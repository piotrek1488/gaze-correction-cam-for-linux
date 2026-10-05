#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export GI_TYPELIB_PATH="$project_dir/.desktop-deps/usr/lib/$(dpkg-architecture -qDEB_HOST_MULTIARCH)/girepository-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
# System GTK must not load modules inherited from an editor installed as a Snap.
unset GTK_PATH GIO_MODULE_DIR GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR
exec /usr/bin/python3 "$project_dir/desktop/tray.py" "$@"
