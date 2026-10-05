# Gaze Correction Cam for Linux

> **This is a Linux (Ubuntu) port** of the original macOS project
> [WangWilly/gaze-correction-cam](https://github.com/WangWilly/gaze-correction-cam) by
> [@WangWilly](https://github.com/WangWilly). The gaze-correction idea and the neural
> warping models are the original author's work; this repository adapts the Python
> core to Linux. See [Acknowledgements](#acknowledgements).

**Make natural eye contact on every video call — on Linux.**

Gaze Correction Cam adjusts your eye direction in real time, so you always look
directly at the people you're talking to, even when you're reading notes or looking
at your own video tile. This port runs the correction core on Ubuntu and exposes the
result as a **virtual camera** that Zoom, Teams, Meet and other apps can use, plus an
optional **system-tray launcher** with autostart.

<img src="https://github.com/user-attachments/assets/66e2355a-20d7-4ac5-b711-cb1b2ff653d7" style="width: 160px; display: block;">

## Demo

<a href="https://www.youtube.com/watch?v=tOobANsNzOQ" target="_blank">
  <img src="https://img.youtube.com/vi/tOobANsNzOQ/0.jpg" style="width: 320px; display: block;">
</a>

## Requirements

- Ubuntu (tested on 26.04) or a comparable Linux distribution
- Python **3.12** (x86_64)
- A connected webcam or built-in camera
- `v4l2loopback` for virtual-camera output into video-call apps (installed by the
  setup script)

## Quick start

```bash
# 1. Install dependencies and download model weights
./scripts/setup-ubuntu.sh

# 2. Create the virtual camera device (requires sudo, one time)
./scripts/setup-virtual-camera.sh

# 3. Run with a live preview from your webcam
./run-ubuntu.sh --camera /dev/video0

# ...or stream the corrected feed into the virtual camera for video calls
./run-ubuntu.sh --virtual-camera /dev/video10
```

Then pick **"Gaze Correction"** as your camera in your video-call app.

> Start the frame producer (`run-ubuntu.sh`) **before** opening the camera list in
> your meeting app. The preview window shows overlays, but the virtual camera and any
> recording receive a clean image.

Full instructions, installation on another machine, and troubleshooting are in
**[docs/UBUNTU.md](docs/UBUNTU.md)** (Polish: [docs/UBUNTU_PL.md](docs/UBUNTU_PL.md)).

## Common commands

```bash
./run-ubuntu.sh --camera /dev/video2                 # pick a different webcam
./run-ubuntu.sh --headless --max-frames 100          # no window, process 100 frames
./run-ubuntu.sh --input in.mp4 --output out.avi --headless   # process a video file
./run-ubuntu.sh --no-correction                      # camera-only passthrough test
./run-ubuntu.sh --backend dlib                        # use the dlib detector
```

The output file is video only (no audio). `--fps` sets the expected camera/output
rate but does not guarantee inference speed.

## Desktop integration (tray icon + autostart)

```bash
./scripts/setup-desktop.sh
```

This installs a system-tray launcher and a login autostart entry. From the tray menu
you can start/stop correction, open the preview with calibration, change settings
(camera devices, resolution, FPS, calibration geometry), toggle autostart, and open
the log. By default only the icon starts at login — enable "start camera
automatically" in Settings if you want the correction to run on login too.

## Controls

In the preview window:

| Key | Action |
| --- | ------ |
| `g` | Toggle gaze correction on / off (watch the GAZE ON/OFF overlay) |
| `c` | Toggle the calibration panel |
| `q` / `Esc` | Quit |

## Calibration

Press `c` to open the calibration panel and tune the correction for your setup. The
correction strength depends on where your camera sits relative to the screen, so the
defaults may need adjusting.

| Control | Action |
| ------- | ------ |
| `↑` `↓` `←` `→` | Adjust camera position (X / Y) |
| `+` / `-` | Adjust camera distance (Z) |
| `[` / `]` | Adjust focal length |
| `r` | Reset to the values from the start of the session |

Settings are stored in `user_settings.db`.

> **Tip:** Start with the defaults. Calibrate only if the correction looks off, or
> set the camera offset to match where your webcam physically sits relative to the
> screen center (in cm).

## How it works

1. Captures your webcam feed in real time.
2. Detects your face and eye positions (MediaPipe by default, dlib optional).
3. Estimates the angle your eyes need to be redirected by, from the camera/screen
   geometry.
4. Applies a learned neural-network warp to the eye regions to redirect your gaze.
5. Outputs the corrected video to a window, a file, and/or a `v4l2loopback` virtual
   camera.

The virtual-camera output is based on
[pyvirtualcam](https://github.com/letmaik/pyvirtualcam) and
[v4l2loopback](https://github.com/v4l2loopback/v4l2loopback).

## Tests

```bash
.venv/bin/python -m pytest -q tests
```

Requires pytest installed and the models downloaded. Validation details and measured
results are in [docs/VALIDATION.md](docs/VALIDATION.md)
(Polish: [docs/VALIDATION_PL.md](docs/VALIDATION_PL.md)).

## Documentation

- [docs/UBUNTU.md](docs/UBUNTU.md) — installation and usage (Polish: [UBUNTU_PL.md](docs/UBUNTU_PL.md))
- [docs/VALIDATION.md](docs/VALIDATION.md) — validation and measured results (Polish: [VALIDATION_PL.md](docs/VALIDATION_PL.md))
- [docs/architecture.md](docs/architecture.md) — architecture and module reference
- [docs/ANALIZA_PL.md](docs/ANALIZA_PL.md) — in-depth code and model analysis (Polish)

## Original macOS project

The original project ships as a macOS virtual-camera app. If you are on macOS, use
the upstream project directly:
[WangWilly/gaze-correction-cam](https://github.com/WangWilly/gaze-correction-cam)
([macOS app download](https://drive.google.com/file/d/1E47OZ66YPab1QuTbxN97hL2u3GYwyUbz/view?usp=drive_link)).

## Acknowledgements

This project is a **Linux port** and would not exist without the original work:

- **Original project:** [WangWilly/gaze-correction-cam](https://github.com/WangWilly/gaze-correction-cam)
- **Original author:** [@WangWilly](https://github.com/WangWilly)

The gaze-correction idea, the neural warping models and the original macOS
implementation are the author's work. Huge thanks for building and open-sourcing it.
This repository only adapts the Python core to Linux (V4L2 / `v4l2loopback` output, a
desktop tray launcher, autostart and Ubuntu setup scripts) and keeps the original
models unchanged.

If you use this port, please also star and credit the
[original repository](https://github.com/WangWilly/gaze-correction-cam).

Licensed under the same terms as the upstream project — see [LICENSE](LICENSE).
