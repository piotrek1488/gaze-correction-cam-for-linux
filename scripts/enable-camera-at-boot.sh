#!/usr/bin/env bash
# Explicit one-time administrator setup; does not unload existing cameras.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
    exec pkexec /bin/bash "$(readlink -f "$0")"
fi
modinfo v4l2loopback >/dev/null
printf '%s\n' 'options v4l2loopback devices=1 video_nr=10 card_label="Gaze Correction" exclusive_caps=1' > /etc/modprobe.d/gaze-correction.conf
printf '%s\n' 'v4l2loopback' > /etc/modules-load.d/gaze-correction.conf
modprobe v4l2loopback
