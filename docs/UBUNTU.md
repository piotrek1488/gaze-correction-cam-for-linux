# Ubuntu — installation and usage

> Polish version: [UBUNTU_PL.md](UBUNTU_PL.md).

The port lives in `ubuntu_camera.py`. The original macOS interface is not part of
the public code; the Ubuntu version uses an OpenCV window and a V4L2 camera. All
processing happens locally.

## Quick run

Set up a local `.venv` (Python 3.12) and the models, then run:

```bash
cd ~/git/gaze-correction-cam
./run-ubuntu.sh
```

Default input is `/dev/video0` with the MediaPipe detector. `g` toggles correction
on/off, `c` opens calibration, `q` or Escape quits. In calibration mode the arrow
keys move the camera in XY, `+/-` adjusts Z, `[/]` the focal length, and `r`
restores the values from the start of the session. Settings are stored in
`user_settings.db`. The default geometry comes from upstream and should be tuned to
your monitor/laptop.

```bash
./run-ubuntu.sh --camera /dev/video2
./run-ubuntu.sh --headless --max-frames 100
./run-ubuntu.sh --input /path/to/input.mp4 --output /path/to/result.avi --headless
./run-ubuntu.sh --no-correction  # explicit camera-only test
```

The output file contains video only, no audio. `--fps` sets the expected
camera/output rate but does not guarantee inference speed. When processing is slow,
a camera recording may play back faster than real time. File recordings keep the
source FPS.

## Camera in Zoom / Teams / browser

Install the module once for the current kernel (the script asks for your `sudo`
password):

```bash
./scripts/setup-virtual-camera.sh
./run-ubuntu.sh --virtual-camera /dev/video10
```

In your meeting app, pick **Gaze Correction**. Start the frame producer first, then
open the app's camera list. The preview shows overlays, but the virtual camera and
the recording receive a clean image.

After a reboot the module must be loaded again:

```bash
sudo modprobe v4l2loopback devices=1 video_nr=10 card_label='Gaze Correction' exclusive_caps=1
```

If the module is already loaded, `modprobe` will not change its existing
parameters: pick the existing loopback device from `v4l2-ctl --list-devices`. Do not
unload the module while OBS or another program is using it. Device number 10 must be
free. Secure Boot may require enrolling a MOK key during DKMS installation. Input and
output must be different devices.

The output path is based on
[pyvirtualcam](https://github.com/letmaik/pyvirtualcam) and
[v4l2loopback](https://github.com/v4l2loopback/v4l2loopback).

## Installing on another Ubuntu

Supported dependency configuration for the port: Python **3.12**, Linux x86_64. Do
not use the system Python 3.14 to install these pinned libraries.

```bash
sudo apt-get install python3.12-venv libgl1 libglib2.0-0
./scripts/setup-ubuntu.sh
```

If your distribution does not ship Python 3.12, install it separately (for example
via uv) and pass the path in `PYTHON_BIN`. The script does not change the system
interpreter. You can also prepare the environment with `uv venv --python 3.12 .venv`,
install `requirements-ubuntu.txt` via
`uv pip install --python .venv/bin/python -r requirements-ubuntu.txt`, and then run
`.venv/bin/python scripts/download_models.py`.

Core dependencies are pinned in `requirements-ubuntu.txt`; the full set verified
locally is recorded in `requirements-ubuntu.lock`. The `poetry.lock` file comes from
upstream and is not used by the Ubuntu installer.

The default MediaPipe backend does not require compiling dlib. The `--backend dlib`
option requires an extra dlib install and
`lm_feat/shape_predictor_68_face_landmarks.dat` from the upstream v0.1.1 release.

Model downloads are verified against SHA256. The correction weights come from the
[v0.1.1 release](https://github.com/WangWilly/gaze-correction-cam/releases/tag/v0.1.1),
and the detector comes from the versioned MediaPipe model store. These are not models
retrained as part of the port.

## Troubleshooting

- No image: check the device, permissions, and whether the camera is busy.
- Checkpoint error: run `.venv/bin/python scripts/download_models.py`. The program
  aborts on an inference error instead of showing an unchanged frame as working
  correction.
- No window: run inside a graphical session, or use `--headless` with an output or a
  frame limit.
- Do not install `opencv-python`, `opencv-contrib-python`, and headless variants at
  the same time in this environment: they share the `cv2` module.
- Quality: glasses, strong head rotation, blinking, and large angles can cause
  artifacts. The model corrects small eye patches; it does not reconstruct the whole
  face.

Tests: `.venv/bin/python -m pytest -q tests`. They require pytest installed and the
models downloaded. The checkpoint test runs inference for both eyes and checks the
response to an angle change; it is not a photorealism assessment.

## Teams / Edge sees HP but not Gaze Correction

On this Ubuntu 26.04 / PipeWire 1.6.2 setup, WirePlumber may remember the
`v4l2loopback` device as an output device if it scans it before the producer starts.
In that case correct reception via OpenCV does not yet mean visibility in Teams.

1. Run `./run-ubuntu.sh --virtual-camera /dev/video10` and leave the app running.
2. In a second terminal check `wpctl status`: the camera must appear under
   **Video → Sources**, not only under Devices.
3. If it is not under Sources, and outside an active call, run
   `systemctl --user restart wireplumber`. This briefly interrupts audio/video; check
   your audio output afterwards, especially Bluetooth headphones.
4. In Teams pick **Settings → Devices → Camera → Gaze Correction**. If the list does
   not refresh automatically, reload the Teams tab.
5. The site `teams.cloud.microsoft` must have the browser's camera permission.

A working local preview in Teams was confirmed on this machine. The Python app must
keep streaming the whole time the camera is used in a call.
