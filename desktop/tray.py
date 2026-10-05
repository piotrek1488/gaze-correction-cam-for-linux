#!/usr/bin/env python3
"""GTK/AppIndicator shell; TensorFlow runs only in the separate worker."""
import os
from pathlib import Path
import signal
import subprocess
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, Gio, GLib, AyatanaAppIndicator3 as Indicator
from desktop.control import Worker, ROOT, CONFIG_DIR, STATE_DIR, load_settings, atomic_json, validate, set_autostart, autostart_enabled
from model_managers.user_settings_db import UserSettingsDB

# Prefer the non-deprecated GLibUnix.signal_add when available (newer PyGObject),
# and fall back to GLib.unix_signal_add on older systems.
try:
    gi.require_version('GLibUnix', '2.0')
    from gi.repository import GLibUnix
    _unix_signal_add = GLibUnix.signal_add
except (ValueError, ImportError):
    _unix_signal_add = GLib.unix_signal_add

# libayatana-appindicator (the GTK3 build) prints a one-time deprecation warning
# on startup. The non-deprecated libayatana-appindicator-glib typelib is not
# installed here, so silence just that message instead of spamming stderr.
def _filter_appindicator_warning(domain, level, message, _user_data):
    if message and 'libayatana-appindicator is deprecated' in message:
        return
    GLib.log_default_handler(domain, level, message, None)


GLib.log_set_handler(
    'libayatana-appindicator',
    GLib.LogLevelFlags.LEVEL_WARNING | GLib.LogLevelFlags.LEVEL_MESSAGE,
    _filter_appindicator_warning,
    None,
)


class Tray(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.local.GazeCorrection', flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.ready = False
        self.dialog = None
        self.quitting = False

    def do_activate(self):
        if self.ready:
            self.show_settings()
            return
        self.ready = True
        self.hold()
        self.worker = Worker()
        try:
            self.settings = load_settings()
        except (OSError, ValueError, sqlite3.Error) as exc:
            from desktop.control import DEFAULTS
            self.settings = DEFAULTS.copy()
            self.error(f'Nie można odczytać ustawień: {exc}')
        self.indicator = Indicator.Indicator.new('gaze-correction', str(ROOT/'desktop/gaze-idle.svg'), Indicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_title('Gaze Correction')
        self.indicator.set_status(Indicator.IndicatorStatus.ACTIVE)
        menu = Gtk.Menu()
        self.status_item = Gtk.MenuItem(label='Kamera zatrzymana')
        self.status_item.set_sensitive(False)
        menu.append(self.status_item)
        menu.append(Gtk.SeparatorMenuItem())
        self.start_item = self.item(menu, 'Włącz korekcję', lambda *_: self.start(False))
        self.stop_item = self.item(menu, 'Zatrzymaj kamerę', self.stop)
        self.item(menu, 'Podgląd i kalibracja…', lambda *_: self.start(True))
        self.item(menu, 'Ustawienia…', self.show_settings)
        menu.append(Gtk.SeparatorMenuItem())
        self.auto_item = Gtk.CheckMenuItem(label='Uruchamiaj ikonę po zalogowaniu')
        self.auto_item.set_active(autostart_enabled())
        self.auto_item.connect('toggled', self.toggle_autostart)
        menu.append(self.auto_item)
        self.item(menu, 'Przygotuj kamerę po restarcie…', self.prepare_module)
        self.item(menu, 'Otwórz log', lambda *_: self.open_file(self.worker.log_path))
        self.item(menu, 'Instrukcja', lambda *_: self.open_file(ROOT/'docs/UBUNTU.md'))
        menu.append(Gtk.SeparatorMenuItem())
        self.item(menu, 'Zakończ', self.exit_app)
        menu.show_all()
        self.indicator.set_menu(menu)
        GLib.timeout_add(500, self.tick)
        _unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self.exit_app)
        _unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.exit_app)
        if self.settings['auto_camera']:
            self.start(False)

    def item(self, menu, label, callback):
        item = Gtk.MenuItem(label=label)
        item.connect('activate', callback)
        menu.append(item)
        return item

    def error(self, message):
        dialog = Gtk.MessageDialog(transient_for=self.dialog, modal=True, message_type=Gtk.MessageType.ERROR,
                                  buttons=Gtk.ButtonsType.CLOSE, text='Gaze Correction', secondary_text=str(message))
        dialog.connect('response', lambda d, *_: d.destroy())
        dialog.show_all()

    def start(self, preview):
        try:
            self.worker.start(self.settings, preview)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.error(exc)

    def stop(self, *_):
        self.worker.pending = None
        self.worker.stop()

    def tick(self):
        try:
            self.worker.poll()
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.worker.last_error = str(exc)
        status = self.worker.status()
        self.status_item.set_label(status)
        self.start_item.set_sensitive(not self.worker.running())
        self.stop_item.set_sensitive(self.worker.running())
        icon = 'gaze-active.svg' if status.startswith('Kamera działa') else 'gaze-idle.svg'
        if getattr(self, '_icon', None) != icon:
            self.indicator.set_icon_full(str(ROOT/'desktop'/icon), status)
            self._icon = icon
        if self.quitting and not self.worker.running():
            self.indicator.set_status(Indicator.IndicatorStatus.PASSIVE)
            self.release()
            self.quit()
            return False
        return True

    def toggle_autostart(self, item):
        try:
            set_autostart(item.get_active())
        except OSError as exc:
            self.error(exc)

    def prepare_module(self, *_):
        child = subprocess.Popen([str(ROOT/'scripts/enable-camera-at-boot.sh')])
        def finished():
            result = child.poll()
            if result is None:
                return True
            if result != 0:
                self.error('Nie skonfigurowano modułu. Wymagane jest uwierzytelnienie administratora i zainstalowany v4l2loopback.')
            return False
        GLib.timeout_add(500, finished)

    def open_file(self, path):
        if not path.exists():
            self.error('Plik nie istnieje. Uruchom kamerę, aby utworzyć log.')
            return
        try:
            Gio.AppInfo.launch_default_for_uri(path.as_uri(), None)
        except GLib.Error as exc:
            self.error(exc)

    def exit_app(self, *_):
        self.quitting = True
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
        self.stop()
        return False

    def show_settings(self, *_):
        if self.dialog:
            self.dialog.present()
            return
        dialog = Gtk.Dialog(title='Gaze Correction — ustawienia', application=self, flags=0)
        self.dialog = dialog
        dialog.add_buttons('Anuluj', Gtk.ResponseType.CANCEL, 'Zapisz', Gtk.ResponseType.OK)
        dialog.set_default_size(470, 540)
        box = dialog.get_content_area()
        box.set_border_width(18)
        grid = Gtk.Grid(column_spacing=16, row_spacing=10)
        box.add(grid)
        entries = {}
        def row(label, widget):
            index = len(entries)
            grid.attach(Gtk.Label(label=label, xalign=0), 0, index, 1, 1)
            grid.attach(widget, 1, index, 1, 1)
            return widget
        for key, label in [('camera','Kamera wejściowa'),('virtual_camera','Kamera dla Teams')]:
            entries[key] = row(label, Gtk.Entry(text=self.settings[key]))
        for key,label,low,high,step in [('width','Szerokość obrazu',160,3840,160),('height','Wysokość obrazu',120,2160,120),('fps','Klatki na sekundę',1,60,1)]:
            widget = Gtk.SpinButton.new_with_range(low,high,step)
            widget.set_value(self.settings[key])
            entries[key] = row(label,widget)
        db = UserSettingsDB(str(ROOT/'user_settings.db'))
        saved = db.get_setting('camera_default') or dict(focal_length=650.,ipd=6.3,camera_offset=[0.,-21.,-1.])
        geometry = [('focal_length','Ogniskowa (px)',10,5000,10,saved['focal_length']),
                    ('ipd','Rozstaw oczu (cm)',3,10,.1,saved['ipd'])]
        for i,axis in enumerate('xyz'):
            geometry.append((axis,f'Pozycja kamery {axis.upper()} (cm)',-200,200,.5,saved['camera_offset'][i]))
        for key,label,low,high,step,value in geometry:
            widget=Gtk.SpinButton.new_with_range(low,high,step)
            widget.set_digits(1)
            widget.set_value(value)
            entries[key]=row(label,widget)
        auto = Gtk.CheckButton(label='Włączaj kamerę automatycznie przy starcie ikony')
        auto.set_active(self.settings['auto_camera'])
        box.pack_start(auto,False,False,12)
        hint = Gtk.Label(label='Zapisane zmiany uruchomią działającą kamerę ponownie.\nPodgląd: klawisz C pokazuje kalibrację, Q zamyka kamerę.', xalign=0)
        hint.set_line_wrap(True)
        box.pack_start(hint,False,False,6)
        def response(d, result):
            if result == Gtk.ResponseType.OK:
                try:
                    cfg={key:(entries[key].get_text().strip() if key in ('camera','virtual_camera') else entries[key].get_value_as_int())
                         for key in ('camera','virtual_camera','width','height','fps')}
                    cfg['auto_camera']=auto.get_active()
                    cfg=validate(cfg)
                    db.save_setting('camera_default',dict(focal_length=entries['focal_length'].get_value(),
                        ipd=entries['ipd'].get_value(),camera_offset=[entries[k].get_value() for k in 'xyz']))
                    atomic_json(CONFIG_DIR/'settings.json',cfg)
                    self.settings=cfg
                    if self.worker.running():
                        self.worker.start(cfg,self.worker.preview)
                except (OSError, ValueError, sqlite3.Error) as exc:
                    self.error(exc)
                    return
            self.dialog=None
            d.destroy()
        dialog.connect('response',response)
        dialog.connect('delete-event',lambda d,e: (response(d,Gtk.ResponseType.CANCEL),True)[1])
        dialog.show_all()


if __name__ == '__main__':
    raise SystemExit(Tray().run(sys.argv))
