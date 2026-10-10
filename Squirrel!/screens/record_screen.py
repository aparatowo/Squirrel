# screens/record_screen.py — Voice recording screen (manual, and the quick recorder on G0)
#
# Opened from Voice Notes ("+ [New Item]") or by the G0 button from the clock / a menu.
#   ENTER or G0 - start, or stop and save
#   ESC         - while recording: discard the take; otherwise just leave
# After saving or discarding it returns to where it was opened from.
import os
import time
from gfx import Lcd
from screens.base_screen import BaseScreen
from nuts import BASE_DIR

_TICK_MS = 500   # blink period and timer granularity
_DEFAULT_RETURN = ("MENU", {"menu_name": "RECORDS"})


class RecordScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)
        self._filepath = None
        self._start_ticks = 0
        self._drawn_bucket = -1     # last 500 ms bucket that was drawn
        self._drawn_recording = False
        self._return_to = _DEFAULT_RETURN

    def on_enter(self, autostart=False, return_to=None, **kwargs):
        self._filepath = None
        self._start_ticks = 0
        self._drawn_bucket = -1
        self._drawn_recording = False
        self._return_to = return_to or _DEFAULT_RETURN
        if autostart:
            self._start()

    def on_exit(self):
        if self.app.audio.is_recording():
            self.app.audio.stop_recording()

    def _leave(self):
        name, kwargs = self._return_to
        self.app.set_screen(name, **kwargs)

    def _bucket(self):
        """Number of 500 ms steps since recording started (drives blink + MM:SS)."""
        return time.ticks_diff(time.ticks_ms(), self._start_ticks) // _TICK_MS

    def needs_refresh(self):
        recording = self.app.audio.is_recording()
        if recording != self._drawn_recording:
            return True   # recording ended by itself (e.g. write error)
        return recording and self._bucket() != self._drawn_bucket

    def on_quick_button(self):
        """G0 while this screen is open: the same start / stop toggle as ENTER."""
        if self.app.audio.is_recording():
            self._stop()
        else:
            self._start()

    def handle_input(self, action):
        if action == 'ESC':
            if self.app.audio.is_recording():
                self.app.audio.cancel_recording()
                self.app.renderer.render_alert("Discarded")
                time.sleep(0.5)
            self._leave()
            return

        if action == 'ENTER':
            self.on_quick_button()

    def _start(self):
        dt = self.app.rtc.get_datetime()
        fname = f"REC_{dt[0]:04d}{dt[1]:02d}{dt[2]:02d}_{dt[3]:02d}{dt[4]:02d}{dt[5]:02d}.wav"
        folder = f"{BASE_DIR}/records"
        try:
            os.mkdir(folder)       # a fresh card has none until Voice Notes is opened: the quick recorder (G0) comes first
        except OSError:
            pass                   # it is there already
        self._filepath = f"{folder}/{fname}"
        ok = self.app.audio.start_recording(self._filepath)
        if ok:
            self._start_ticks = time.ticks_ms()
        else:
            self.app.renderer.render_alert("Rec Error!")
            time.sleep(0.8)
            self._leave()

    def _stop(self):
        if self.app.audio.stop_recording():
            self.app.renderer.render_options("Saved!")
        else:
            self.app.renderer.render_alert("Too short - not saved")
        time.sleep(0.6)
        self._leave()

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        fonts = renderer.fonts
        Lcd.setTextSize(fonts["MENU_ITEM"])

        recording = self.app.audio.is_recording()
        self._drawn_recording = recording

        if not recording:
            Lcd.setTextColor(theme["FG"], theme["BG"])
            Lcd.drawString("# Voice Recorder", 5, 5)
            Lcd.drawString("ENTER or G0 to start", 5, 40)
            Lcd.drawString("ESC to go back", 5, 58)
            return

        bucket = self._bucket()
        self._drawn_bucket = bucket
        elapsed = bucket // 2          # two buckets per second
        blink_on = (bucket % 2 == 0)

        dot_col = theme["ERROR"] if blink_on else theme["BG"]
        Lcd.fillCircle(15, 18, 8, dot_col)
        Lcd.setTextColor(theme["ERROR"], theme["BG"])
        Lcd.drawString("REC", 30, 11)

        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(f"{elapsed // 60:02d}:{elapsed % 60:02d}", 100, 11)
        if self._filepath:
            Lcd.drawString(self._filepath.split("/")[-1][:26], 5, 38)
        Lcd.drawString("[G0/ENTER] Save  [ESC] Discard", 5, 115)
