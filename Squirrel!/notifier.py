# notifier.py - full-screen notifications with a sound
#
# Notifier is a background service.  post() queues a Notification; tick() shows it as an OVERLAY
# (the screen underneath is untouched, so nothing typed there is lost), lights the screen up,
# plays the signal now and every `repeat_s` seconds, and ends it when
#   OPT  (the green key)          -> on_done
#   Backspace / FN+Backspace      -> on_cancel
#   nothing for `timeout_s`       -> on_timeout
# Other keys are ignored on purpose: a notification must not be dismissed by accident.
# While a recording runs the notification waits (recording has priority; the sound would also
# be muted), and appears as soon as the recording ends.

import time
from M5 import Lcd
from boot_log import log


def wrap(text, width, max_lines):
    """Split `text` into lines of at most `width` characters, at spaces where possible."""
    lines, line = [], ""
    for word in text.split():
        while len(word) > width:                       # a word longer than a line is cut
            if line:
                lines.append(line)
                line = ""
            lines.append(word[:width])
            word = word[width:]
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= width:
            line += " " + word
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines[:max_lines]


class Notification:
    def __init__(self, text, title="", sound="notify", timeout_s=30, repeat_s=4,
                 on_done=None, on_cancel=None, on_timeout=None,
                 done_label="Done", cancel_label="Cancel"):
        self.text = text
        self.title = title
        self.sound = sound
        self.timeout_s = timeout_s
        self.repeat_s = repeat_s
        self.on_done = on_done
        self.on_cancel = on_cancel
        self.on_timeout = on_timeout
        self.done_label = done_label
        self.cancel_label = cancel_label


class Notifier:
    def __init__(self, host, audio):
        self._host = host              # wake(), show_overlay(overlay), hide_overlay()
        self._audio = audio            # is_recording(), beep(pattern)
        self._queue = []
        self.current = None
        self._shown_at = 0
        self._last_beep = 0

    @property
    def busy(self):
        return self.current is not None or bool(self._queue)

    def post(self, notification):
        self._queue.append(notification)

    def seconds_left(self):
        if self.current is None:
            return 0
        left = self.current.timeout_s * 1000 - time.ticks_diff(time.ticks_ms(), self._shown_at)
        return max(0, (left + 999) // 1000)

    def tick(self):
        now = time.ticks_ms()
        if self.current is None:
            if self._queue and not self._recording():
                self._show(self._queue.pop(0), now)
            return
        n = self.current
        if time.ticks_diff(now, self._shown_at) >= n.timeout_s * 1000:
            self._finish("timeout")
        elif n.repeat_s and time.ticks_diff(now, self._last_beep) >= n.repeat_s * 1000:
            self._last_beep = now
            self._beep(n.sound)

    def abort(self):
        """Drop the notification on display without calling anything (used when the screen is reset)."""
        self.current = None

    def handle_input(self, action):
        if action == 'OPT':
            self._finish("done")
        elif action in ('BACKSPACE', 'DEL'):
            self._finish("cancel")

    def _recording(self):
        try:
            return bool(self._audio.is_recording())
        except Exception:
            return False

    def _beep(self, pattern):
        try:
            self._audio.beep(pattern)
        except Exception as e:
            log(f"[NOTIFY] Sound failed: {e}")

    def _show(self, notification, now):
        self.current = notification
        self._shown_at = now
        self._last_beep = now
        self._host.wake()
        self._beep(notification.sound)
        self._host.show_overlay(NotifyOverlay(self, notification))

    def _finish(self, how):
        n, self.current = self.current, None
        if n is None:
            return
        self._host.hide_overlay()
        callback = n.on_done if how == "done" else (n.on_cancel if how == "cancel" else n.on_timeout)
        if callback is not None:
            try:
                callback()
            except Exception as e:
                log(f"[NOTIFY] Callback for '{how}' failed: {e}")


class NotifyOverlay:
    """What the screen shows while a notification is up."""

    def __init__(self, notifier, notification):
        self._notifier = notifier
        self._n = notification
        self._drawn = None

    def handle_input(self, action):
        self._notifier.handle_input(action)

    def needs_refresh(self):
        return self._notifier.seconds_left() != self._drawn

    def render(self, renderer):
        theme = renderer.theme
        n = self._n
        left = self._notifier.seconds_left()
        self._drawn = left
        renderer.clear()
        Lcd.drawRect(0, 0, 240, 135, theme["ACCENT"])
        Lcd.drawRect(1, 1, 238, 133, theme["ACCENT"])
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        if n.title:
            Lcd.drawString(n.title[:30], max(4, (240 - 6 * len(n.title[:30])) // 2), 8)
        Lcd.drawString("%ds" % left, 240 - 6 * (len(str(left)) + 1) - 6, 8)
        Lcd.setTextSize(2)
        Lcd.setTextColor(theme["WARNING"], theme["BG"])
        lines = wrap(n.text, 18, 4)
        y = 30 + (4 - len(lines)) * 8
        for line in lines:
            Lcd.drawString(line, (240 - 12 * len(line)) // 2, y)
            y += 18
        Lcd.setTextSize(1)
        Lcd.setTextColor(theme["ACCENT"], theme["BG"])
        Lcd.drawString("[OPT] " + n.done_label, 8, 118)
        text = "[DEL] " + n.cancel_label
        Lcd.setTextColor(theme["ERROR"], theme["BG"])
        Lcd.drawString(text, 240 - 8 - 6 * len(text), 118)
