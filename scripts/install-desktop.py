#!/usr/bin/env python3
"""Install the per-user launcher and login entry, without root."""
from pathlib import Path
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from desktop.control import CONFIG_DIR, DEFAULTS, atomic_json, desktop_entry, set_autostart

applications=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'applications'
applications.mkdir(parents=True,exist_ok=True)
(applications/'gaze-correction.desktop').write_text(desktop_entry())
if not (CONFIG_DIR/'settings.json').exists():
    atomic_json(CONFIG_DIR/'settings.json',DEFAULTS)
set_autostart(True)
print('Installed Gaze Correction launcher and login autostart.')
