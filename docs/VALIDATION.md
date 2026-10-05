# Local validation — 2026-10-05

> Polish version: [VALIDATION_PL.md](VALIDATION_PL.md).

Environment: Ubuntu 26.04.1 LTS, x86_64, kernel 7.0.0-34-generic, isolated Python
3.12.15. TensorFlow 2.19.0, MediaPipe 0.10.32, OpenCV contrib 4.11.0.86, NumPy 2.1.3,
pyvirtualcam 0.14.0. Full set: `requirements-ubuntu.lock`.

## Checks performed

- `python -m pytest -q tests`: **10 tests passed**. They cover eye crops, image
  boundaries, BGR→RGB, monotonic timestamps, input/output files, an invalid device,
  camera-loop prevention, the real L/R checkpoints, missing weights, resource cleanup,
  and clean frames on the virtual output (mock).
- Graph vs checkpoint comparison: 59 graph variables, 140 checkpoint variables,
  **0 name/shape mismatches**. The extra checkpoint variables are not needed by the
  inference graph.
- Inference on both real checkpoints produces finite results of the expected shape and
  an angle-dependent output; random weights were not used as a substitute.
- `./run-ubuntu.sh --headless --max-frames 90`: **90 frames**, 30.2 FPS from the
  physical HP camera `/dev/video0`. No image was saved or transmitted. This measurement
  does not count detected faces, so it is not a standalone face-correction benchmark.
- Full detection and correction on the public
  `https://storage.googleapis.com/mediapipe-assets/portrait.jpg`: one detected face, 30
  iterations, **29.0 FPS**, 1763 changed pixels in the last frame. The image was scaled
  to 640 px width keeping the aspect ratio. The result was reviewed: the change is in
  the eyes, the rest of the image is preserved. This is a single functional test, not a
  quality assessment over a representative set.
- Processing a 15-frame video created from the public photo: **15 frames written**,
  23.7 FPS processing. `artifacts/portrait-input.avi` → `artifacts/portrait-output.avi`.
- `./run-ubuntu.sh --max-frames 10`: starting the OpenCV preview in a GNOME/Wayland
  session via XWayland, reading 10 frames, clean shutdown. A short startup test, not a
  reliable FPS benchmark.
- `uv pip check`: consistent dependencies. `git diff --check` and `bash -n`: no errors.
- Both downloaded model hashes verified via `scripts/download_models.py`.

## Validation limitations

During the first validation the `v4l2loopback` module was not available for the
running kernel. `sudo -n true` reported that a password was required. **No real test of
reception through the virtual camera or Zoom/Teams/browser was performed.** The output
code is covered by an interface test with a mock backend; that does not replace a
driver test. `scripts/setup-virtual-camera.sh` was prepared for configuration.

No test of the dlib backend, CUDA, other Ubuntu releases, or long-term stability was
performed. Inference tests ran on CPU. TensorFlow printed CUDA/cuDNN initialization
messages and `cuInit 303`, but ran CPU inference correctly; this does not indicate
working GPU acceleration.

Not every calibration key was tested manually. No latency measurement from camera
exposure to display in the meeting app was performed. The reported FPS numbers are not
a guarantee of smoothness on other devices.

Artifacts from the public photo live in the Git-ignored `artifacts/` directory. No
test artifact contains a user recording.

## Additional verification after the user installed the module

2026-10-05, around 11:41 local command-environment time:

- `v4l2loopback` is loaded; `v4l2-ctl --list-devices` shows **Gaze Correction**,
  `/dev/video10`.
- The real program with correction was run:
  `./run-ubuntu.sh --virtual-camera /dev/video10 --headless --max-frames 1800`.
- An independent OpenCV process opened `/dev/video10` via V4L2 and received
  **90 frames at 640×480 BGR**, around **31.0 FPS** in a short measurement. Mean frame
  brightness varied between 152.0 and 195.53. No camera image was saved.
- While streaming, the device reports `Video Capture`, format `YU12`, 640×480, 30 FPS.
  Before streaming it reported `Video Output`, consistent with exclusive_caps mode.
- This confirms the real path app → pyvirtualcam → v4l2loopback → a separate V4L2
  receiver. The earlier limitation about the missing driver test no longer applies.
- **Teams still unverified**: the Browser tool returned `No browser is available`, and
  the list of available browsers was empty. No call or meeting was made. The V4L2 test
  is not a confirmation of the Teams preview or WebRTC negotiation.

## Attempt in Teams Web / Edge — 2026-10-05, 13:26–13:30

After connecting the Browser extension, a signed-in Teams
(`https://teams.cloud.microsoft/`) was opened in Edge, along with the
Settings → Devices panel. The Camera field was inactive with the value "None"; so were
the microphone and speaker lists. There was no video preview. In parallel the app was
streaming to `/dev/video10`, and a separate receiver again read 30 frames at 640×480.
Teams behavior is therefore not yet confirmed. Next step: manually check the site
permission and refresh. An attempt to open the internal Edge settings page through the
tool was rejected by the Browser URL policy. No call was made and no meeting was joined.

## Teams Web confirmation — 2026-10-05

**Result: the Gaze Correction camera preview in Teams Web works.**

Tested with Edge 154.0.4258.53 and `https://teams.cloud.microsoft/` on this machine.
After the user granted camera permission, Teams initially saw only the physical HP
camera. `wpctl inspect` showed that WirePlumber had remembered `/dev/video10` as
`:video_output:` before streaming started. Restarting with
`systemctl --user restart wireplumber` while the producer was active created the
**Gaze Correction (V4L2)** source; the camera then appeared in the Teams list.

In Teams, Gaze Correction was selected, and then on the quick-meeting pre-join screen
that entry was confirmed as selected. The local preview was enabled and "Don't use
audio" was chosen. The image was confirmed visually, and the `video` element reported
512×384, `readyState=4`, `paused=false`, and a playback time over 27 s. The `msedge`
process had `/dev/video10` open in parallel with the Python producer. This confirms the
real path app → v4l2loopback → Edge → Teams preview, not just device-name visibility.

"Join now" was not clicked, no test call was made, and no invitations were sent. The
pre-join screen was closed with "Cancel". Reception by a second participant and network
transmission quality were not tested. Screenshots were viewed in the tool during the
test; no private image was saved as a file in the repository.
