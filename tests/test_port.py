from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys

import cv2
import numpy as np
import pytest
from displayers.face_predictor import DlibFacePredictor, MediaPipeFacePredictor, EyeLandmarks, EyeExtractionConfig

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('cls', [DlibFacePredictor, MediaPipeFacePredictor])
def test_eye_crop_and_boundary(cls):
    predictor = object.__new__(cls)
    frame = np.full((100, 120, 3), 128, np.uint8)
    points = [(40, 50), (45, 47), (55, 47), (60, 50), (55, 53), (45, 53)]
    eye = predictor._extract_single_eye(frame, EyeLandmarks(points, (50, 50)), 'L', EyeExtractionConfig())
    assert eye.image.shape == (48, 64, 3)
    assert eye.anchor_map.shape == (48, 64, 12)
    assert eye.image.dtype == np.float32
    near_edge = [(x-40, y-48) for x, y in points]
    assert predictor._extract_single_eye(frame, EyeLandmarks(near_edge, (10, 2)), 'L', EyeExtractionConfig()) is None


def test_mediapipe_receives_rgb_and_monotonic_timestamps():
    predictor = object.__new__(MediaPipeFacePredictor)
    images, timestamps = [], []
    predictor._mp = SimpleNamespace(ImageFormat=SimpleNamespace(SRGB=1),
        Image=lambda **kwargs: images.append(kwargs['data']) or kwargs['data'])
    predictor._start_time = 0
    predictor._last_timestamp = 10**15
    predictor.landmarker = SimpleNamespace(detect_for_video=lambda image, timestamp:
        timestamps.append(timestamp) or SimpleNamespace(face_landmarks=[]))
    frame = np.zeros((2, 2, 3), np.uint8)
    frame[:] = [10, 20, 30]
    predictor._detect_landmarks(frame)
    predictor._detect_landmarks(frame)
    assert images[0][0, 0].tolist() == [30, 20, 10]
    assert timestamps[1] > timestamps[0]


def test_file_pipeline(tmp_path):
    source, output = tmp_path / 'in.avi', tmp_path / 'out.avi'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'MJPG'), 10, (64, 48))
    assert writer.isOpened()
    for _ in range(4):
        writer.write(np.full((48, 64, 3), 80, np.uint8))
    writer.release()
    result = subprocess.run([sys.executable, str(ROOT/'ubuntu_camera.py'), '--input', str(source),
        '--output', str(output), '--no-correction', '--headless'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    cap = cv2.VideoCapture(str(output))
    assert cap.get(cv2.CAP_PROP_FRAME_COUNT) == 4
    ok, frame = cap.read()
    cap.release()
    assert ok and np.abs(frame.astype(float) - 80).mean() < 2


def test_missing_camera_reports_error():
    result = subprocess.run([sys.executable, str(ROOT/'ubuntu_camera.py'), '--camera', '/dev/video9999',
        '--no-correction', '--headless', '--max-frames', '1'], capture_output=True, text=True)
    assert result.returncode == 1
    assert 'Cannot open input' in result.stderr


def test_same_camera_rejected():
    result = subprocess.run([sys.executable, str(ROOT/'ubuntu_camera.py'), '--camera', '10',
        '--virtual-camera', '/dev/video10', '--headless'], capture_output=True, text=True)
    assert result.returncode == 2
    assert 'must differ' in result.stderr


def test_real_checkpoints():
    from model_managers.gaze_corrector_v1 import GazeModel, GazeModelConfig
    model = GazeModel(GazeModelConfig(model_dir=str(ROOT/'weights/warping_model/flx/12')+'/'))
    try:
        eye = np.random.default_rng(1).random((48, 64, 3), dtype=np.float32)
        anchors = np.zeros((48, 64, 12), np.float32)
        for side in ('L', 'R'):
            a = model.infer_eye(side, eye, anchors, [0, 0])
            b = model.infer_eye(side, eye, anchors, [15, 0])
            assert a.shape == eye.shape and np.isfinite(a).all() and np.isfinite(b).all()
            assert np.max(np.abs(a-b)) > 0.001
    finally:
        model.close()


def test_missing_checkpoint_is_fatal(tmp_path):
    import tensorflow as tf
    from model_managers.gaze_corrector_v1 import GazeModel
    model = object.__new__(GazeModel)
    with tf.Graph().as_default():
        tf.compat.v1.get_variable('test', shape=[1])
        with tf.compat.v1.Session() as session:
            with pytest.raises(FileNotFoundError):
                model._restore_checkpoint(session, str(tmp_path/'L'))


def test_virtual_camera_clean_frames_and_cleanup(monkeypatch):
    import ubuntu_camera
    import pyvirtualcam
    from displayers.dis_single_window import SingleWindowGazeCorrector
    import displayers.face_predictor as predictors
    captured, sent, closed = [], [], []
    source = np.full((48, 64, 3), 50, np.uint8)

    class Capture:
        def __init__(self, *args):
            self.count = 0
        def isOpened(self): return True
        def set(self, *args): pass
        def read(self):
            self.count += 1
            return (True, source.copy()) if self.count <= 2 else (False, None)
        def release(self): closed.append('input')

    class Virtual:
        def __init__(self, **kwargs): captured.append(kwargs)
        def __enter__(self): return self
        def __exit__(self, *args): closed.append('virtual')
        def send(self, frame): sent.append(frame.copy())
        def sleep_until_next_frame(self): pass

    class App:
        gaze_correction_enabled = True
        calibration_mode = False
        gaze_corrector = SimpleNamespace(close=lambda: closed.append('model'))
        def __init__(self, **kwargs): pass
        def process_frame(self, frame): return frame + 10
        def draw_status(self, frame): frame[:] = 255

    monkeypatch.setattr(cv2, 'VideoCapture', Capture)
    monkeypatch.setattr(pyvirtualcam, 'Camera', Virtual)
    monkeypatch.setattr(predictors, 'create_face_predictor', lambda backend: object())
    monkeypatch.setattr('displayers.dis_single_window.SingleWindowGazeCorrector', App)
    monkeypatch.setattr(cv2, 'namedWindow', lambda *args: None)
    monkeypatch.setattr(cv2, 'imshow', lambda *args: None)
    monkeypatch.setattr(cv2, 'waitKeyEx', lambda *args: -1)
    monkeypatch.setattr(cv2, 'getWindowProperty', lambda *args: 1)
    monkeypatch.setattr(cv2, 'destroyAllWindows', lambda: closed.append('window'))
    monkeypatch.setenv('DISPLAY', ':0')
    monkeypatch.setattr(sys, 'argv', ['ubuntu_camera.py', '--virtual-camera', '/dev/video10', '--max-frames', '2'])
    assert ubuntu_camera.main() == 0
    assert len(sent) == 2 and np.all(sent[0] == 60)
    assert captured[0]['fmt'] == pyvirtualcam.PixelFormat.BGR
    assert set(closed) == {'input', 'virtual', 'model', 'window'}


def test_model_sessions_close_after_restore_failure(tmp_path):
    from model_managers.gaze_corrector_v1 import GazeModel, GazeModelConfig
    model = object.__new__(GazeModel)
    with pytest.raises(FileNotFoundError):
        model.__init__(GazeModelConfig(model_dir=str(tmp_path)+'/'))
    assert model.l_sess._closed
