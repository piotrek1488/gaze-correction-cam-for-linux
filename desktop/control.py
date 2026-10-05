"""Desktop settings and non-blocking worker lifecycle (no GUI dependencies)."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'gaze-correction'
STATE_DIR = Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'gaze-correction'
AUTOSTART = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'autostart/gaze-correction.desktop'
DEFAULTS = dict(camera='/dev/video0', virtual_camera='/dev/video10', width=640, height=480, fps=30, auto_camera=False)


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2)+'\n')
    tmp.replace(path)


def validate(data):
    cfg = {**DEFAULTS, **data}
    for key in ('camera', 'virtual_camera'):
        if not isinstance(cfg[key], str) or not cfg[key].startswith('/dev/video') or not cfg[key][10:].isdigit():
            raise ValueError('Kamera musi mieć ścieżkę /dev/videoN.')
    if Path(cfg['camera']).resolve() == Path(cfg['virtual_camera']).resolve():
        raise ValueError('Kamera wejściowa i wirtualna muszą być różne.')
    for key, low, high in [('width', 160, 3840), ('height', 120, 2160), ('fps', 1, 60)]:
        if type(cfg[key]) is not int or not low <= cfg[key] <= high:
            raise ValueError(f'Nieprawidłowa wartość {key}.')
    if type(cfg['auto_camera']) is not bool:
        raise ValueError('Nieprawidłowa opcja automatycznego startu kamery.')
    return cfg


def load_settings():
    path = CONFIG_DIR/'settings.json'
    return validate(json.loads(path.read_text())) if path.exists() else DEFAULTS.copy()


def desktop_entry():
    # Desktop Entry Exec has its own escaping rules (not shell quoting).
    executable = str(ROOT/'run-tray.sh').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    return ('[Desktop Entry]\nType=Application\nName=Gaze Correction\n'
            'Comment=Korekcja spojrzenia — kamera i ustawienia\n'
            f'Exec="{executable}"\nIcon={ROOT}/desktop/gaze-idle.svg\n'
            'Terminal=false\nCategories=AudioVideo;Video;\nStartupNotify=false\n'
            'X-GNOME-Autostart-enabled=true\nX-GNOME-Autostart-Delay=8\n')


def autostart_enabled():
    return AUTOSTART.exists() and 'Hidden=true' not in AUTOSTART.read_text() and 'X-GNOME-Autostart-enabled=false' not in AUTOSTART.read_text()


def set_autostart(enabled):
    if enabled:
        AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
        AUTOSTART.write_text(desktop_entry())
    else:
        AUTOSTART.unlink(missing_ok=True)


class Worker:
    def __init__(self, state_dir=STATE_DIR):
        self.state_dir = state_dir
        state_dir.mkdir(parents=True, exist_ok=True)
        self.status_file = state_dir/'worker-status.json'
        self.log_path = state_dir/'camera.log'
        self.process = None
        self.deadline = None
        self.pending = None
        self.preview = False
        self.last_error = None

    def running(self):
        return self.process is not None and self.process.poll() is None

    def start(self, settings, preview=False):
        cfg = validate(settings)
        if self.running():
            self.pending = (cfg, preview)
            self.stop()
            return
        for key in ('camera', 'virtual_camera'):
            if not Path(cfg[key]).exists():
                raise ValueError(f'Brak urządzenia {cfg[key]}. Dla kamery wirtualnej uruchom scripts/setup-virtual-camera.sh.')
        self.last_error = None
        self.status_file.unlink(missing_ok=True)
        args = [str(ROOT/'run-ubuntu.sh'), '--camera', cfg['camera'], '--virtual-camera', cfg['virtual_camera'],
                '--width', str(cfg['width']), '--height', str(cfg['height']), '--fps', str(cfg['fps']),
                '--status-file', str(self.status_file)]
        args += ['--calibration'] if preview else ['--headless']
        with self.log_path.open('w') as log:
            self.process = subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                            start_new_session=True, env={**os.environ, 'PYTHONUNBUFFERED':'1'})
        self.preview = preview
        self.deadline = None

    def stop(self):
        if self.running() and self.deadline is None:
            self.process.send_signal(signal.SIGINT)
            self.deadline = time.monotonic()+5

    def poll(self):
        if self.process is None:
            return
        code = self.process.poll()
        if code is None:
            if self.deadline is not None and time.monotonic() >= self.deadline:
                self.process.kill()
            return
        expected = self.deadline is not None or code in (0, 130, -signal.SIGINT)
        self.process = None
        self.deadline = None
        self.status_file.unlink(missing_ok=True)
        if not expected:
            self.last_error = f'Kamera zakończyła pracę (kod {code}). Zobacz log.'
        if self.pending:
            cfg, preview = self.pending
            self.pending = None
            self.start(cfg, preview)

    def status(self):
        if self.deadline is not None:
            return 'Zatrzymywanie…'
        if not self.running():
            return self.last_error or 'Kamera zatrzymana'
        try:
            data = json.loads(self.status_file.read_text())
            if data.get('pid') == self.process.pid:
                return f"Kamera działa · {data['width']}×{data['height']}"
        except (OSError, ValueError, KeyError):
            pass
        return 'Uruchamianie kamery…'
