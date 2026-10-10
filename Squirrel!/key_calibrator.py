# key_calibrator.py - records which matrix code each key sends
#
# Press the key named on the screen, one after another.  The result is written to
# keymap.json (for reference; the live key maps are in nuts.py).
#   G0 - leave at any moment without saving.  ESC and BACKSPACE are among the keys being
#        calibrated here, so they cannot be used to exit.
import json
import time
from gfx import Lcd
from screens.base_screen import BaseScreen

TARGET_KEYS = [
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    ' ', '.', ',', '/', ';', '\'', '[', ']', '\\', '`', '-', '=', '+',
    'ENTER', 'BACKSPACE', 'ESC', 'TAB',
    'UP', 'DOWN', 'LEFT', 'RIGHT'
]


def _label(key):
    return "SPACE" if key == ' ' else key


class CalibrationScreen(BaseScreen):
    def __init__(self, app, save_path="/flash/apps/Squirrel/keymap.json"):
        super().__init__(app)
        self.save_path = save_path
        self.current_step = 0
        self.keymap = {}
        self.current_target = TARGET_KEYS[0]

    def on_enter(self, **kwargs):
        print("[CALIBRATOR] Key calibration started")
        self.current_step = 0
        self.keymap.clear()
        self.current_target = TARGET_KEYS[0]

    def on_quick_button(self):
        """G0: leave without saving."""
        print("[CALIBRATOR] Left with G0 (nothing saved)")
        self.app.set_screen("MENU", menu_name="SETTINGS")

    def handle_input(self, action):
        # The keypad remembers the matrix code of the key it just reported
        code = self.app.keypad.last_key_code
        target = self.current_target
        print(f"[CALIB LOG] Step {self.current_step + 1}/{len(TARGET_KEYS)} | target [{target}] | key code {code}")

        self.keymap[target] = code
        self.app.renderer.render_options(f"Saved: {_label(target)} -> {code}")
        time.sleep(0.3)

        self.current_step += 1
        if self.current_step < len(TARGET_KEYS):
            self.current_target = TARGET_KEYS[self.current_step]
        else:
            self.save_and_finish()

    def save_and_finish(self):
        print("[CALIBRATOR RESULT] " + json.dumps(self.keymap))
        try:
            with open(self.save_path, "w") as f:
                json.dump(self.keymap, f)
            print(f"[CALIBRATOR] Saved the map to {self.save_path}")
            self.app.renderer.render_options("Saved Keymap!")
        except Exception as e:
            print(f"[CALIBRATOR ERROR] Save failed: {e}")
            self.app.renderer.render_alert("Save Error!")

        time.sleep(1.0)
        self.app.set_screen("MENU", menu_name="SETTINGS")

    def render(self, renderer):
        renderer.clear()
        theme = renderer.theme
        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("# Key Calibration", 5, 5)
        Lcd.drawString(f"Step {self.current_step + 1}/{len(TARGET_KEYS)}", 5, 28)
        Lcd.setTextColor(theme["WARNING"], theme["BG"])
        Lcd.setTextSize(2)
        Lcd.drawString(f"Press: {_label(self.current_target)}", 5, 55)
        Lcd.setTextSize(renderer.fonts["MENU_ITEM"])
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("[G0] Exit without saving", 5, 115)