#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export GI_TYPELIB_PATH="$project_dir/.desktop-deps/usr/lib/$(dpkg-architecture -qDEB_HOST_MULTIARCH)/girepository-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
# System GTK must not load modules inherited from an editor installed as a Snap.
unset GTK_PATH GIO_MODULE_DIR GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR

# Run detached from the terminal when asked (-b/--background). Without it the tray
# stays in the foreground, which is what desktop autostart expects.
background=0
args=()
for arg in "$@"; do
    case "$arg" in
        -b|--background) background=1 ;;
        *) args+=("$arg") ;;
    esac
done

if [[ "$background" -eq 1 ]]; then
    log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/gaze-correction"
    mkdir -p "$log_dir"
    # setsid detaches from the controlling terminal so closing it won't kill the tray.
    setsid /usr/bin/python3 "$project_dir/desktop/tray.py" "${args[@]+"${args[@]}"}" \
        >>"$log_dir/tray.log" 2>&1 < /dev/null &
    echo "Gaze Correction tray started in the background (PID $!). Log: $log_dir/tray.log"
    exit 0
fi

exec /usr/bin/python3 "$project_dir/desktop/tray.py" "${args[@]+"${args[@]}"}"
