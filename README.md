# Gaze Correction Cam for Linux

> **This is a Linux (Ubuntu) port** of the original macOS project
> [WangWilly/gaze-correction-cam](https://github.com/WangWilly/gaze-correction-cam).
> All credit for the original design, the gaze-warping models and the core idea
> goes to the original author, [@WangWilly](https://github.com/WangWilly).
> This port adapts the Python core to run on Linux with a `v4l2loopback`
> virtual camera, a system-tray launcher and autostart. See the
> [Acknowledgements](#acknowledgements) section below.

> **Ubuntu port docs:** quick start in [docs/UBUNTU.md](docs/UBUNTU.md),
> code and model analysis (Polish) in [docs/ANALIZA_PL.md](docs/ANALIZA_PL.md),
> validation results in [docs/VALIDATION.md](docs/VALIDATION.md).

**Make natural eye contact on every video call.**

Gaze Correction Cam automatically adjusts your eye direction in real-time — so you always look directly at the people you're talking to, even when you're reading notes or looking at your own video tile. The original project ships as a macOS virtual camera extension; this port brings the same gaze-correction core to Linux.

<img src="https://github.com/user-attachments/assets/66e2355a-20d7-4ac5-b711-cb1b2ff653d7" style="width: 160px; display: block;">

## Demo

<a href="https://www.youtube.com/watch?v=tOobANsNzOQ" target="_blank">
  <img src="https://img.youtube.com/vi/tOobANsNzOQ/0.jpg" style="width: 320px; display: block;">
</a>

## Quick start (Linux)

This port runs the gaze-correction core on Ubuntu and exposes the result as a
virtual camera that Zoom, Teams, Meet and other apps can use.

```bash
# 1. Install dependencies and download model weights
./scripts/setup-ubuntu.sh

# 2. Create the virtual camera device (requires sudo, one time)
./scripts/setup-virtual-camera.sh

# 3. Run with live preview from your webcam
./run-ubuntu.sh --camera /dev/video0

# ...or stream the corrected feed into the virtual camera for video calls
./run-ubuntu.sh --virtual-camera /dev/video10
```

Then pick **"Gaze Correction"** as your camera in your video-call app.

Optional desktop integration (tray icon + autostart):

```bash
./scripts/setup-desktop.sh
```

Full instructions, troubleshooting and calibration tips are in
[docs/UBUNTU.md](docs/UBUNTU.md).

## Download (macOS, original project)

**[⬇️ Download the macOS App](https://drive.google.com/file/d/1E47OZ66YPab1QuTbxN97hL2u3GYwyUbz/view?usp=drive_link)**

Install the `.app`, grant camera access, and you're ready to go. The macOS app
is provided by the original project; this repository focuses on the Linux port.

## Requirements

- macOS 14 (Sonoma) or later
- A connected webcam or built-in camera
- Camera access permission granted to the app

## Getting Started

1. **Download and open** the app from the link above.
2. **Grant camera access** when prompted by macOS.
3. **Select your camera** from the dropdown in the top-right corner of the app window.
4. **Enable gaze correction** using the toggle in the settings panel.
5. **Set this app as your camera** in Zoom, Teams, FaceTime, or any video app — look for **"Gaze Correction Camera"** in the camera device list.

## Controls

| Key | Action |
| --- | ------ |
| `g` | Toggle gaze correction on / off |
| `c` | Toggle calibration panel |
| `q` | Quit |

## Calibration

Press `c` to open the calibration panel and fine-tune the correction for your setup:

| Control | Action |
| ------- | ------ |
| `↑` `↓` `←` `→` | Adjust camera position up/down/left/right |
| `+` / `-` | Adjust camera distance (closer/further) |
| `[` / `]` | Adjust focal length |
| `r` | Reset all values to default |

> **Tip:** Start with the defaults. Only calibrate if the gaze correction looks off for your specific desk setup.

---

## Advanced: Build from Source / Python CLI

If you want to run from source or use the Python CLI directly:

### Prerequisites

- [Python 3.12+](https://www.python.org/downloads/)
- [Poetry](https://python-poetry.org/docs/)
- [CMake](https://cmake.org/download/)
- [pkg-config](https://www.freedesktop.org/wiki/Software/pkg-config/)

### Install

```bash
brew install pkg-config cmake
poetry install
```

### Download model weights

Download from [GitHub Releases](https://github.com/WangWilly/gaze-correction-cam/releases) and place in the correct directories:

- `lm_feat/shape_predictor_68_face_landmarks.dat`
- `weights/warping_model/flx/12/L/` and `.../R/` — checkpoint + weight files
- *(Optional)* `models/face_landmarker.task` — for MediaPipe backend

### Run

```bash
# Default (dlib backend)
poetry run python bin_single_window.py

# MediaPipe backend
poetry run python bin_single_window.py --backend mediapipe

# Specific camera
poetry run python bin_single_window.py --camera 1
```

---

## How It Works

1. Captures your webcam feed in real-time
2. Detects your face and eye positions using computer vision
3. Calculates where your eyes need to point to look at the camera
4. Applies a learned neural network warp to redirect your gaze
5. Outputs the corrected video as a virtual camera device

---

## Acknowledgements

This project is a **Linux port** and would not exist without the original work:

- **Original project:** [WangWilly/gaze-correction-cam](https://github.com/WangWilly/gaze-correction-cam)
- **Original author:** [@WangWilly](https://github.com/WangWilly)

The gaze-correction idea, the neural warping models and the original macOS
implementation are the author's work. Huge thanks for building and open-sourcing
it. This repository only adapts the Python core to Linux (V4L2 / `v4l2loopback`
output, a desktop tray launcher, autostart and Ubuntu setup scripts) and keeps
the original models unchanged.

If you use this port, please also star and credit the
[original repository](https://github.com/WangWilly/gaze-correction-cam).

Licensed under the same terms as the upstream project — see [LICENSE](LICENSE).

---

*Looking for architecture details or module documentation? See [docs/architecture.md](docs/architecture.md).*
