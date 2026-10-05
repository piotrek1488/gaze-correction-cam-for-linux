#!/usr/bin/env bash
# Run deliberately: installs Ubuntu packages and loads a kernel module.
set -euo pipefail
sudo apt-get install v4l2loopback-dkms v4l-utils "linux-headers-$(uname -r)"
sudo modprobe v4l2loopback devices=1 video_nr=10 card_label='Gaze Correction' exclusive_caps=1
v4l2-ctl --list-devices
