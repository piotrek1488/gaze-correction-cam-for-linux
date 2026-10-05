import json
import signal
from pathlib import Path
from unittest.mock import Mock

import pytest
from desktop import control


def test_autostart_can_be_enabled_and_disabled(tmp_path, monkeypatch):
    target=tmp_path/'autostart/gaze-correction.desktop'
    monkeypatch.setattr(control,'AUTOSTART',target)
    control.set_autostart(True)
    assert control.autostart_enabled()
    assert str(control.ROOT/'run-tray.sh') in target.read_text()
    control.set_autostart(False)
    assert not control.autostart_enabled()


def test_invalid_same_camera_rejected():
    with pytest.raises(ValueError):
        control.validate({'camera':'/dev/video10'})


def test_worker_restart_waits_for_previous_process(tmp_path, monkeypatch):
    worker=control.Worker(tmp_path)
    process=Mock()
    process.poll.return_value=None
    worker.process=process
    worker.start(control.DEFAULTS,preview=True)
    process.send_signal.assert_called_once_with(signal.SIGINT)
    assert worker.pending == (control.DEFAULTS,True)
    assert worker.process is process
    replacement=Mock()
    monkeypatch.setattr(worker,'start',replacement)
    process.poll.return_value=130
    worker.poll()
    replacement.assert_called_once_with(control.DEFAULTS,True)
    assert worker.pending is None


def test_worker_failure_is_visible_and_stale_status_removed(tmp_path):
    worker=control.Worker(tmp_path)
    control.atomic_json(worker.status_file,{'pid':123,'width':640,'height':480})
    process=Mock(pid=123)
    process.poll.return_value=1
    worker.process=process
    worker.poll()
    assert 'kod 1' in worker.status()
    assert not worker.status_file.exists()


def test_status_only_accepts_current_process(tmp_path):
    worker=control.Worker(tmp_path)
    worker.process=Mock(pid=123)
    worker.process.poll.return_value=None
    control.atomic_json(worker.status_file,{'pid':987,'width':640,'height':480})
    assert worker.status() == 'Uruchamianie kamery…'
    control.atomic_json(worker.status_file,{'pid':123,'width':640,'height':480})
    assert worker.status() == 'Kamera działa · 640×480'
