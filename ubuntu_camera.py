#!/usr/bin/env python3
"""Ubuntu camera/file runner. All processing stays on this computer."""
import argparse
import json
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera', default='/dev/video0', help='V4L2 input device or numeric index')
    parser.add_argument('--input', type=Path, help='Process a video file instead of a camera')
    parser.add_argument('--output', type=Path, help='Save clean output as MJPEG AVI')
    parser.add_argument('--virtual-camera', metavar='/dev/video10', help='Existing v4l2loopback device')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--no-correction', action='store_true', help='Explicit passthrough; no models required')
    parser.add_argument('--backend', choices=['mediapipe', 'dlib'], default='mediapipe')
    parser.add_argument('--width', type=int, default=640)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--fps', type=float, default=30)
    parser.add_argument('--max-frames', type=int, default=0, help='0 means unlimited')
    parser.add_argument('--calibration', action='store_true', help='Open preview calibration controls')
    parser.add_argument('--status-file', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.width < 16 or args.height < 16 or not 0 < args.fps <= 240 or args.max_frames < 0:
        parser.error('Invalid dimensions, frame rate or frame count')
    if args.headless and not (args.output or args.virtual_camera or args.max_frames):
        parser.error('--headless requires --output, --virtual-camera or --max-frames')
    if not args.headless and not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        parser.error('No desktop display; use --headless')
    source = str(args.input.resolve()) if args.input else args.camera
    output = args.output.resolve() if args.output else None
    if output and args.input and output == args.input.resolve():
        parser.error('Input and output must differ')
    if args.virtual_camera and not args.input:
        input_device = Path(f'/dev/video{source}' if source.isdigit() else source).resolve()
        if input_device == Path(args.virtual_camera).resolve():
            parser.error('Input camera and virtual camera must differ')
    status_file = args.status_file.resolve() if args.status_file else None
    os.chdir(ROOT)
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
    import cv2
    with ExitStack() as stack:
        app = None
        if not args.no_correction:
            from displayers.dis_single_window import SingleWindowGazeCorrector
            from displayers.face_predictor import create_face_predictor
            predictor = create_face_predictor(args.backend)
            if hasattr(predictor, 'landmarker'):
                stack.callback(predictor.landmarker.close)
            app = SingleWindowGazeCorrector(face_predictor=predictor)
            stack.callback(app.gaze_corrector.close)
            app.calibration_mode = args.calibration
        cap = cv2.VideoCapture(int(source) if source.isdigit() else source,
                               cv2.CAP_ANY if args.input else cv2.CAP_V4L2)
        stack.callback(cap.release)
        if not cap.isOpened():
            raise RuntimeError(f'Cannot open input {source}; check camera permissions and other camera apps')
        if not args.input:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
            cap.set(cv2.CAP_PROP_FPS, args.fps)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError('Input opened but did not provide a frame')
        h, w = frame.shape[:2]
        fps = args.fps
        if args.input:
            file_fps = cap.get(cv2.CAP_PROP_FPS)
            if 0 < file_fps <= 240:
                fps = file_fps
        virtual = None
        if args.virtual_camera:
            import pyvirtualcam
            virtual = stack.enter_context(pyvirtualcam.Camera(width=w, height=h, fps=fps,
                device=args.virtual_camera, backend='v4l2loopback', fmt=pyvirtualcam.PixelFormat.BGR))
        writer = None
        if output:
            writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*'MJPG'), fps, (w, h))
            stack.callback(writer.release)
            if not writer.isOpened():
                raise RuntimeError(f'Cannot write video {output}; use an .avi path in an existing directory')
        if not args.headless:
            cv2.namedWindow('Gaze Correction Ubuntu', cv2.WINDOW_NORMAL)
            stack.callback(cv2.destroyAllWindows)
        if status_file:
            status_file.parent.mkdir(parents=True, exist_ok=True)
            stack.callback(lambda: status_file.unlink(missing_ok=True))
            temp_status = status_file.with_suffix('.tmp')
            temp_status.write_text(json.dumps(dict(pid=os.getpid(), width=w, height=h)))
            temp_status.replace(status_file)
        count, started = 0, time.monotonic()
        while ok:
            if frame.shape[:2] != (h, w):
                raise RuntimeError('Input resolution changed during capture')
            clean = app.process_frame(frame) if app and app.gaze_correction_enabled else frame.copy()
            if virtual:
                virtual.send(clean)
                virtual.sleep_until_next_frame()
            if writer:
                writer.write(clean)
            count += 1
            if not args.headless:
                preview = clean.copy()
                if app:
                    app.draw_status(preview)
                    if app.calibration_mode:
                        app.draw_calibration_overlay(preview)
                cv2.imshow('Gaze Correction Ubuntu', preview)
                key = cv2.waitKeyEx(1)
                if key in (ord('q'), 27) or cv2.getWindowProperty('Gaze Correction Ubuntu', cv2.WND_PROP_VISIBLE) < 1:
                    break
                if app:
                    if key == ord('g'):
                        app.gaze_correction_enabled = not app.gaze_correction_enabled
                    elif key == ord('c'):
                        app.calibration_mode = not app.calibration_mode
                    elif app.calibration_mode:
                        app.handle_calibration_key(key)
            if args.max_frames and count >= args.max_frames:
                break
            ok, frame = cap.read()
            if not ok and not args.input:
                raise RuntimeError('Camera stopped delivering frames')
        print(f'Processed {count} frames at {count / max(time.monotonic() - started, 0.001):.1f} FPS')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
