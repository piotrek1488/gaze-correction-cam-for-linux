# Analysis of gaze-correction-cam and the Ubuntu port

> Polish version: [ANALIZA_PL.md](ANALIZA_PL.md).

Analysis state: 2026-10-05. Reference point: upstream `a94ec59` (full hash: `git rev-parse HEAD`). The port changes were kept locally for review; they were not published in the author's repository.

## 1. What the repository actually ships

The README describes a finished macOS app and a camera extension. The public source tree, however, contains Python modules, not a Swift/Xcode project or a CoreMediaIO extension. The original `bin_single_window.py` opens the camera via OpenCV and displays the result through `imshow`. It does not create a virtual camera. Simply running the original on Linux is therefore not enough to use the correction in a meeting app.

The core is portable: NumPy, OpenCV, TensorFlow, YAML and SQLite. `pyobjc` appears in the dependencies, but the main processing path does not import it. It is an unnecessary installation obstacle on Linux, not an essential part of the algorithm.

The repository does not contain the weights. The older v0.1.1 release contains `weights.zip` and the dlib landmark model. Newer releases contain DMG installers. In the port, the weights were taken from v0.1.1 and the versioned MediaPipe FaceLandmarker model was used.

## 2. Data flow and responsibilities

| Element | Actual role |
|---|---|
| `bin_single_window.py` | CLI parser, resolution setup, object construction, window startup |
| `displayers/face_predictor.py` | Face detection via dlib or MediaPipe, landmarks, eye crop, anchor maps |
| `displayers/dis_single_window.py` | First detected face, correction, overlays, key handling |
| `model_managers/gaze_corrector_v1.py` | Two TensorFlow graphs/sessions, geometry, inference, eye paste-back |
| `model_managers/user_settings_db.py` | SQLite with camera parameters as JSON; parameterized queries |
| `tf_models/gaze_corrector_v1/gaze_warp_model.py` | Angle encoder, coarse and fine network, brightness correction |
| `tf_models/gaze_corrector_v1/layers.py` | Keras layers in TF1-compatible graphs |
| `tf_models/gaze_corrector_v1/spatial_transform.py` | Bilinear sampling by a displacement field |
| `ubuntu_camera.py` (port) | V4L2/file capture, window, AVI writing, v4l2loopback output, resource lifecycle |

Pipeline: BGR frame → landmarks → two 48×64×3 crops and 48×64×12 maps → correction angle → separate L/R models → crop rescaling → paste into the frame → output.

Each anchor map contains coordinate differences relative to six landmarks (X and Y for each point). The order of the left-eye points is reversed to match the model's input format. The encoder turns a pair of angles into 16 features and spreads them spatially. The network estimates flow at two scales; `tanh` bounds the displacements. The LCM module blends the warp result with white to correct brightness.

## 3. What the algorithm measures and what it does not

This is not a full estimator of the current gaze direction. `estimate_gaze_angle` derives the eye distance from their pixel separation, the given focal length and a default IPD of 6.3 cm. It then computes an angle from the screen/camera geometry. It assumes a specific target position and requires calibration. It does not read the position of the other party's window on the desktop, nor which text the user is currently reading.

The default camera offset of `(0, -21, -1)` cm and a focal length of 650 px are not universal. Changing the resolution without a corresponding focal-length adjustment changes the estimate. Upstream MediaPipe uses iris centers for the geometry, while dlib uses the eye corners; these backends are not perfectly equivalent.

The model is historical. The source documentation references "Look at Me! Correcting Eye Gaze in Live Video Communication" from 2019; the file bundled with the weights states a training date of 20180413 and `Trained head poses: 0`. From this I infer limited robustness to large head rotations; I do not treat it as a measured quality limit. The dataset documentation describes 37 participants, which further limits the basis for claims about universal quality.

## 4. Issues found and how they were handled

| Upstream issue | Effect | Port |
|---|---|---|
| Unconditional `pyobjc` | macOS dependency installed on Linux | Platform marker; separate Ubuntu requirements |
| No virtual output | The meeting app does not see the result | `pyvirtualcam` + an existing `v4l2loopback` device |
| MediaPipe receives BGR as SRGB | Incorrect colors for the detector | Explicit BGR→RGB only on the detection input |
| Time from the regular clock | Possible repeated/rewound timestamps | Monotonic clock and a minimum of previous+1 ms |
| Negative crop indices | Incorrect image fragments/shapes | Skip an incomplete crop at the image boundary |
| A missing checkpoint only warns | A session with uninitialized variables | Startup error with model-download instructions |
| Relative `L`/`R` prefix from the checkpoint | Restore from the wrong directory | Prefix built from the model directory |
| Catching all inference errors | The preview may pretend correction works | An error ends the program and goes to stderr |
| macOS arrow codes and 8-bit truncation | Non-working Linux calibration | X11/Qt codes and `waitKeyEx` |
| No eye-distance validation | Division by zero | Validation before the computations |
| Focal length may drop to zero | Incorrect geometry | A positive value, bounded during adjustment |
| Config size instead of frame size | Wrong geometry after camera negotiation | Size of the actual frame |
| No `finally` around the original loop | Resources not closed after an exception | The new runner uses `ExitStack` |
| Paths depending on the invocation directory | Starting outside the repo does not work | The launcher and runner determine the project directory |
| Overlays mixed into the output | Captions in the call | A separate copy for the preview |

The warp formulas, the network's input channel order, and the architecture were not changed based on code aesthetics alone: they must match the trained weights. The interpolator uses the historical convention of scaling to width/height rather than width-1/height-1; a modification would require a separate quality comparison against the original model.

## 5. Code and documentation quality

The architecture separates detection, model and presentation, which makes porting easier. Dataclasses and predictor injection are useful in tests. SQLite is sufficient for a handful of parameters and does not require a server.

There are also signs of an unfinished refactoring. `docs/architecture.md` mentions files `gaze_corrector.py`, `flx.py`, `transformation.py` and calibration tools that are not present in the current tree under those names. The documentation describes detection at a lower resolution, but the current dlib predictor works on the full frame; `face_detect_size` in the config does not control it. The eye-extraction code is duplicated between the backends. The original `bin_test_*` scripts are manual detection demonstrations, not automated regression tests.

In `utils/config.py`, parser arguments with `type=eval` remain. The new runner does not use that module; eventually it would be worth removing the legacy parser or replacing those conversions with `int`/`float`. No separate security audit of the whole project was performed.

## 6. Scope of the delivered port

- Physical camera via V4L2, 640×480 by default.
- MediaPipe detection without compiling dlib; dlib optionally retained.
- The original trained correction networks for both eyes.
- Preview with correction toggle and calibration.
- File processing, MJPEG AVI writing, headless mode and a frame limit.
- Clean BGR output to the virtual camera.
- Closing of the camera, file, detector and model on shutdown/exception.
- Hash-consistency check of downloaded models, requirements and regression tests.

This is not a 1:1 port of the macOS binary interface: its code was not published in the analyzed repo. No custom kernel driver, DEB installer, GTK/Qt panel or autostart was added (the desktop tray and autostart were added later). The goal is a locally runnable app and standard Linux video integration.

## 7. Limitations and further work

The first face is processed. There is no identity tracking between frames, no landmark smoothing, no blink detection and no gating of the correction by head pose. The eyes are pasted rectangularly with an edge crop; there is no mask and no smooth blending. These elements may cause flickering or seams. The inference layer is synchronous; the two L/R sessions were not batched. Model compatibility was preserved rather than claiming unmeasured acceleration.

The most justified further work: measuring latency from camera to receiver, landmark smoothing, disabling the warp during blinking/large pose, an eye-blending mask, saving focal-length profiles for different resolutions, and then a possible model-format migration after a numerical comparison.

The upstream code is BSD-3-Clause. The dependencies and downloaded models have their own terms; the repository license alone does not settle the redistribution rights of all weights. The port downloads models from their sources rather than bundling them into the tracked Git tree.

## 8. Sources

- Repository: https://github.com/WangWilly/gaze-correction-cam
- Weights: https://github.com/WangWilly/gaze-correction-cam/releases/tag/v0.1.1
- Paper referenced by the repo: https://doi.org/10.1145/3311784
- Python camera output: https://github.com/letmaik/pyvirtualcam
- Linux camera module: https://github.com/v4l2loopback/v4l2loopback

The results of the actual local tests are in `VALIDATION.md`.
