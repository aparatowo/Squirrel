# screens/playback_screen.py — Voice note playback screen
#
# ENTER       — pause / resume (play again once the file has ended)
# LEFT/RIGHT  — jump 10 s back / forward
# UP/DOWN     — volume +/- 10%
# DEL         — (FN+Backspace) delete the recording: opens a warning, then DEL x3 confirms,
#               ESC cancels — the same flow as deleting a note
# ESC         — stop and go back
#
# Playback is streamed by AudioManager.tick() from the main loop, so this
# screen never blocks; it only redraws when the state or the second changes.

import time
from M5 import Lcd
from screens.base_screen import BaseScreen

_SEEK_MS = 10000
DELETE_CONFIRM_PRESSES = 3      # DEL presses needed after the warning appears


def _mmss(ms):
    s = ms // 1000
    return f"{s // 60:02d}:{s % 60:02d}"


class PlaybackScreen(BaseScreen):
    keeps_screen_on = True         # the screen must not dim while this one is shown
    VOL_STEP = 0.1

    def __init__(self, app):
        super().__init__(app)
        self._filepath = None
        self._title = ""
        self._drawn = None      # (state, whole seconds) currently on the display
        self._delete_confirm = None   # None = not active, int = DEL presses remaining

    def on_enter(self, filepath="", title="", **kwargs):
        self._filepath = filepath
        self._title = title
        self._drawn = None
        self._delete_confirm = None
        if self._filepath:
            self.app.audio.start_playback(self._filepath)

    def on_exit(self):
        self.app.audio.stop_playback()

    def _snapshot(self):
        audio = self.app.audio
        return (audio.playback_state(), audio.position_ms() // 1000)

    def needs_refresh(self):
        return self._snapshot() != self._drawn

    def _handle_delete_confirm(self, action):
        """Input while the delete warning is on screen; every other key is ignored."""
        if action == 'ESC':
            self._delete_confirm = None            # cancel; playback stays paused
        elif action == 'DEL':
            self._delete_confirm -= 1
            if self._delete_confirm <= 0:
                self._delete_now()

    def _delete_now(self):
        """Close the file (it is open while streaming), remove it and return to the list."""
        self.app.audio.stop_playback()
        ok = self.app.storage.delete_path(self._filepath)
        self._delete_confirm = None
        self.app.renderer.render_alert("Deleted!" if ok else "Delete failed!")
        time.sleep(0.6)
        self.app.set_screen("MENU", menu_name="RECORDS")

    def handle_input(self, action):
        audio = self.app.audio
        if self._delete_confirm is not None:
            self._handle_delete_confirm(action)
            return
        if action == 'ESC':
            audio.stop_playback()
            self.app.set_screen("MENU", menu_name="RECORDS")

        elif action == 'ENTER':
            state = audio.playback_state()
            if state == 'playing':
                audio.pause_playback()
            elif state == 'paused':
                audio.resume_playback()
            elif self._filepath:
                audio.start_playback(self._filepath)      # ended (or failed): play again

        elif action == 'LEFT':
            audio.seek(-_SEEK_MS)

        elif action == 'RIGHT':
            audio.seek(_SEEK_MS)

        elif action == 'UP':
            audio.set_volume(audio.get_volume() + self.VOL_STEP)

        elif action == 'DOWN':
            audio.set_volume(audio.get_volume() - self.VOL_STEP)

        elif action == 'DEL' and self._filepath:
            audio.pause_playback()                 # no-op unless it is playing
            self._delete_confirm = DELETE_CONFIRM_PRESSES

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        fonts = renderer.fonts
        audio = self.app.audio

        state = audio.playback_state()
        pos = audio.position_ms()
        total = audio.duration_ms()
        self._drawn = (state, pos // 1000)

        Lcd.setTextSize(fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(f">> {self._title[:22]}", 5, 5)
        Lcd.drawRect(5, 22, 230, 2, theme["FG"])

        if state == 'playing':
            Lcd.setTextColor(theme["ACCENT"], theme["BG"])
            label = "PLAYING"
        elif state == 'paused':
            Lcd.setTextColor(theme["WARNING"], theme["BG"])
            label = "PAUSED"
        else:
            Lcd.setTextColor(theme["WARNING"], theme["BG"])
            label = "STOPPED"
        Lcd.drawString(label, 5, 30)

        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString(f"{_mmss(pos)} / {_mmss(total)}", 5, 42)
        Lcd.drawRect(5, 54, 220, 6, theme["FG"])
        if total:
            Lcd.fillRect(6, 55, int(218 * pos / total), 4, theme["ACCENT"])

        vol = audio.volume_pct_int()
        Lcd.drawString(f"Vol: {vol:3d}%", 5, 66)
        Lcd.drawRect(70, 66, 150, 10, theme["FG"])
        Lcd.fillRect(71, 67, int(148 * vol / 100), 8, theme["ACCENT"])

        Lcd.drawString("[ENTER] Pause/Play", 5, 85)
        Lcd.drawString("[L/R] -/+10s  [U/D] Vol", 5, 100)
        Lcd.drawString("[ESC] Back", 5, 115)
        Lcd.setTextColor(theme["ERROR"], theme["BG"])
        Lcd.drawString("[DEL] Delete", 80, 115)

        # The delete warning is drawn on top of the normal screen.
        if self._delete_confirm is not None:
            renderer.render_delete_confirm(self._delete_confirm)
