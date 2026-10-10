# squirrel_app.py

import sys
import time
import boot_log
import gfx
from gfx import Lcd
from boot_log import log, trace
from ui_renderer import UIRenderer
from storage_manager import StorageManager
from todo_editor import TodoEditor
from note_editor import NoteEditor
from hw.rtc_provider import RTCManager
from services import ServiceManager
from focus_timer import FocusTimer
from hw.radio import RadioManager
from hw.battery import BatteryMonitor, BatteryLogger
from bars import StatusBars
from screen_dimmer import ScreenDimmer
from notifier import Notifier
from scheduler import DayCounter, RoutineStore, Scheduler
from hw.power import PowerManager, collect
import nuts
import port_config
from features import has
from appconfig import cfg
from hw.buzzer import buzzer
from hw.led import led

from screens.clock_screen import ClockScreen
from screens.menu_screen import MenuScreen

# The device's hardware is put together by its port (ports/<port>/board.py, see hw/ports.py)
board = __import__(port_config.BOARD_MODULE, None, None, ("begin",))

# Main-loop profiler: a single phase slower than this is written to the boot log.
_SLOW_PHASE_MS = 150
_MAX_SLOW_LOGS = 40

# A failing screen must not take the whole application down: the error is logged and the
# user lands on the clock.  Only a run of errors (no clean second in between) is fatal.
_MAX_RECOVERIES = 5

# Screens that are needed rarely are compiled and created on first use, not at start-up: the heap
# is small, and a failure to load one of them (MemoryError) then only costs that one feature.
# name -> (module, class, constructor arguments after `app`)
_LAZY_SCREENS = {
    "VIEWER": ("screens.viewer_screen", "ViewerScreen", ()),
    "NOTE_EDITOR": ("screens.note_editor_screen", "NoteEditorScreen", ()),
    "RECORD": ("screens.record_screen", "RecordScreen", ()),
    "PLAYBACK": ("screens.playback_screen", "PlaybackScreen", ()),
    "FOCUS_STATS": ("screens.focus_stats_screen", "FocusStatsScreen", ()),
    "SET_TIME": ("screens.set_time_screen", "SetTimeScreen", ()),
    "TIME_SYNC": ("screens.time_sync_screen", "TimeSyncScreen", ()),
    "CALIBRATOR": ("key_calibrator", "CalibrationScreen", ()),
    "PERSONALIZE": ("screens.personalize_screen", "PersonalizeScreen", ()),
    "MIND_DUMP": ("screens.mind_dump_screen", "MindDumpScreen", ()),
    "WIFI_NETWORKS": ("screens.wifi_screen", "WifiScreen", ()),
    "ROUTINES": ("screens.routines_screen", "RoutinesScreen", ()),
    "INTERVALS": ("screens.interval_screen", "IntervalScreen", ()),
    "METRONOME": ("screens.rhythm_screens", "MetronomeScreen", ()),
    "BREATHING": ("screens.rhythm_screens", "BreathingScreen", ()),
    "FONT_TEST": ("screens.font_test_screen", "FontTestScreen", ()),
    "SILENT_MODE": ("screens.silent_mode_screen", "SilentModeScreen", ()),
    "LED_TESTS": ("screens.led_test_screen", "LedTestScreen", ()),
    "ALARMS": ("screens.alarms_screen", "AlarmsScreen", ()),
}
# Of those, the ones used again and again stay in memory once they have been opened (compiling them anew at every visit
# would be slow and would fragment the heap); the rest are given back when the user leaves them (POWER_UNLOAD_SCREENS).
_KEEP_LOADED = ("VIEWER", "NOTE_EDITOR", "MIND_DUMP", "RECORD", "PLAYBACK", "FOCUS_STATS")
_BARS_TICK_MS = 500          # how often the status bars are brought up to date (the focus cell blinks at 1 Hz)
_CLEAN_STREAK = 100          # ~2 s of error-free loop iterations resets the error count


class SquirrelApp:
    _config_changed = False       # set by a settings change; the main loop then redraws once
    _slow_logs = 0
    _errors = 0                   # errors survived recently (see _recover_from_error)
    _bars_at = 0
    overlay = None                # what covers the active screen (a notification), or None
    _ok_streak = 0

    power = None            # the PowerManager, once the app is built

    def __init__(self):
        print("\n==========================================")
        print("[APP INIT] Start modularnej aplikacji Squirrel...")
        print("==========================================")

        # 0. The buzzer's pin LOW at once: until then it floats, and the NPN behind it could sound
        board.begin_buzzer(buzzer, quiet=lambda: self.audio.is_recording())

        # 1. Storage (the SD card) — must be mounted before StorageManager
        self.sd = board.make_storage()

        # Settings come next: they live on the card, and everything below reads them.
        cfg.load(nuts.CONFIG_FILE)
        self._config_changed = False
        cfg.on_change(self._on_config_changed)

        # 2. Hardware and helper layers
        self.renderer = UIRenderer()
        self.keypad = board.make_input()
        try:
            self.buttons = board.make_buttons()     # {role: button}; "quick" = G0 on the Cardputer: the quick recorder
        except Exception as e:
            log(f"[BTN] unavailable: {e}")
            self.buttons = {}
        self._button_list = tuple(self.buttons.items())     # the main loop goes through this on every pass
        # The font with the Polish letters, if the user has accepted it (Settings -> Experimental -> Font test).
        # Holding the quick button (G0) while the device starts skips it: the way out if a font ever misbehaves.
        held = bool(getattr(self.buttons.get("quick"), "held_at_start", False))
        log(f"[FONT] start-up: {gfx.start(cfg.get('FONT_ENABLED'), nuts.FONT_FILES, skip=held)}")
        self.rtc = RTCManager(*board.clock_chip())
        self.rtc.sync_on_boot()      # one-time read of a permanently attached hardware clock (DS1302 on the Cardputer)
        self.audio = board.make_audio()
        self.storage = StorageManager(nuts.BASE_DIR)

        # Background services: ticked by the main loop whichever screen is active
        self.services = ServiceManager()
        self.services.add(buzzer)       # plays buzzer signals in the background
        self.focus = self.services.add(FocusTimer(
            self.rtc, nuts.BASE_DIR + "/focus",
            goal_seconds=lambda: cfg.get("FOCUS_GOAL_MINUTES") * 60))

        # Status bars, screen dimming and notifications (all ticked by the main loop)
        source = board.power_source()
        self.battery = self.services.add(BatteryMonitor(read=source.level, charging=source.charging))
        board.begin_led(led, self.battery)            # dark at once; then signals, Breathing, the charging light
        self.services.add(led)
        self.bars = StatusBars(cfg, self.battery, self.focus)
        self.renderer.bars = self.bars
        self.dimmer = self.services.add(ScreenDimmer(Lcd, cfg, self._can_dim,
                                                     lambda: self.active_screen is self.screens["CLOCK"],
                                                     on_wake=cfg.check_file,     # an edit of config.txt made from a PC counts after a wake
                                                     floor=led.backlight_floor)) # the LED is powered through the back-light
        self.battery_log = self.services.add(BatteryLogger(cfg, self.battery, self.dimmer, nuts.BASE_DIR + "/battery.csv",
                                                           voltage=source.millivolts))
        self.notifier = self.services.add(Notifier(self, self.audio))

        # Radios stay off unless a network task needs them.  Without a working hardware clock the
        # clock is set once over Wi-Fi + NTP (network saved by UIFlow); otherwise power down now.
        self.radio = RadioManager()
        self.timesync = None
        if has("wifi_ntp"):
            from wifi_ntp import WifiNtpClient
            from time_sync import TimeSyncService
            self.timesync = self.services.add(TimeSyncService(
                self.rtc,
                WifiNtpClient(self.radio,
                              lambda: cfg.get("WIFI_SSID"), lambda: cfg.get("WIFI_PASSWORD")),
                utc_offset_min=lambda: cfg.get("TIME_UTC_OFFSET_MIN"),
                eu_dst=lambda: cfg.get("TIME_EU_DST")))
        clock_chip = board.clock_chip()[1]
        want_sync = (self.timesync is not None and cfg.get("TIMESYNC_AT_BOOT")
                     and (clock_chip is None or self.rtc.last_sync_source != clock_chip))
        if want_sync:
            self.timesync.start("boot")     # switches the radios off when it ends - or fails to start
        else:
            self.radio.power_down("boot")

        # Business logic helpers for TODO and Notes; the tallies behind the statistics
        self.routines_done = DayCounter(nuts.BASE_DIR + "/focus/routines.txt")
        self.todos_done = DayCounter(nuts.BASE_DIR + "/focus/todos.txt")
        self.todo_editor = TodoEditor(self.storage, self.todos_done)
        self.note_editor = NoteEditor(self.storage)

        # Routines, the cuckoo clock and the daily clean-up of done To-Dos
        self.routines = RoutineStore(nuts.ROUTINES_FILE)
        self.scheduler = self.services.add(Scheduler(self.routines, self.notifier, self.audio, cfg,
                                                     self.routines_done, self.todo_editor))
        self._runner = None             # Pomodoro / Training and the metronome are created when first used
        self._metronome = None

        # A device whose clock has an alarm sleeps for real (POWER_SLEEP = deep): the coming routines / cuckoo are the
        # alarms that wake it (deep_sleep.py, alarms.py); what was going on before the sleep is put back here.
        self.deep_sleep = None
        if has("deep_sleep"):
            from alarms import AlarmQueue
            from deep_sleep import DeepSleep
            self.alarms = AlarmQueue()
            self.alarms.add_source(self.scheduler.events)
            self.deep_sleep = self.services.add(DeepSleep(self, board, cfg, self.alarms, nuts.BASE_DIR + "/sleep.json"))
            self.deep_sleep.on_boot()

        # Memory and energy: the GC threshold, the motion sensor off, slower CPU while the screen is dimmed
        try:
            import machine
        except ImportError:
            machine = None
        self.power = self.services.add(PowerManager(cfg, self.dimmer, self._power_busy, machine, self.keypad,
                                                    wake_pins=port_config.POWER_MGMT_WAKE_PINS,
                                                    slow_hz=port_config.POWER_MGMT_SLOW_CPU_HZ,
                                                    arm_wake=getattr(board, "arm_light_sleep_wake", None)))
        self.power.start(board.motion_off)
        # what the energy log times, now that every part exists (see hw/battery.py)
        self.battery_log.attach(slow=lambda: self.power.slow, led=lambda: led.backlight_floor() > 0,
                                speaker=lambda: self.audio.speaker_on, radio=self._radio_in_use,
                                sleeps=lambda: self.power.sleeps)

        # 3. Screen registry
        self.screens = {                # everything else is built on first use, see _LAZY_SCREENS
            "CLOCK": ClockScreen(self),
            "MENU": MenuScreen(self),
        }

        self.active_screen = self.screens["CLOCK"]
        self.running = True
        log(f"[MEM] free heap after start-up: {collect()} bytes")        # collect() first: construction leaves garbage behind
        
    def cfg_sleep_mode(self):
        return cfg.get("POWER_SLEEP")

    def runner(self):
        """The Pomodoro / Training timer (a background service), created on first use."""
        if self._runner is None:
            from intervals import IntervalRunner
            self._runner = self.services.add(IntervalRunner(self.audio, self.notifier))
        return self._runner

    def metronome(self):
        if self._metronome is None:
            from intervals import Metronome
            self._metronome = self.services.add(Metronome(self.audio, cfg))
        return self._metronome

    def _power_busy(self):
        """True while something needs the CPU at full speed and the screen's attention."""
        try:
            if self.audio.is_recording() or self.audio.is_playing() or self.notifier.busy or buzzer.busy or led.busy:
                return True
            busy = getattr(self.timesync, "busy", False)
            if (busy() if callable(busy) else busy) or (self._metronome is not None and self._metronome.running):
                return True
        except Exception:
            return True
        return False

    def _radio_in_use(self):
        busy = getattr(self.timesync, "busy", False)
        return busy() if callable(busy) else bool(busy)

    def _unload_screen(self, name):
        """Give a rarely used screen back to the heap (the next visit builds it again)."""
        module_name = _LAZY_SCREENS[name][0]
        self.screens.pop(name, None)
        if not any(v[0] == module_name and k in self.screens for k, v in _LAZY_SCREENS.items()):
            sys.modules.pop(module_name, None)          # no screen of this module is left: its code can go too
        trace(f"[MEM] {name} unloaded, free heap {collect()} bytes")

    def _load_screen(self, name):
        """Create a rarely used screen the first time it is asked for.  Returns False if it cannot be."""
        module_name, class_name, args = _LAZY_SCREENS[name]
        collect()                                          # importing needs a big contiguous block: tidy the heap first
        try:
            module = __import__(module_name, None, None, (class_name,))
            self.screens[name] = getattr(module, class_name)(self, *args)
            trace(f"[MEM] {name} loaded, free heap {collect()} bytes")
            return True
        except Exception as e:                       # includes MemoryError
            log(f"[NAV] Cannot load {name}: {type(e).__name__}: {e}")
            try:
                self.renderer.render_alert("Not enough memory" if isinstance(e, MemoryError) else "Cannot open")
                time.sleep(0.8)
            except Exception:
                pass
            return False

    def set_screen(self, screen_name, **kwargs):
        if screen_name not in self.screens and screen_name in _LAZY_SCREENS:
            if not self._load_screen(screen_name):
                return
        if screen_name in self.screens:
            trace(f"[NAV] -> {screen_name}")
            # Domyślnie wracamy do trybu nawigacji przy każdej zmianie ekranu
            if hasattr(self, 'keypad'):
                self.keypad.set_text_mode(False)
            
            # Przełączamy faktyczny aktywny ekran pętli run()
            previous = self.active_screen
            self.active_screen = self.screens[screen_name]
            Lcd.full_height(bool(getattr(self.active_screen, "full_height", False)))     # touch screens: the whole panel
            if screen_name == "CLOCK" and previous is not self.active_screen:
                collect()                  # back to the clock = the device is about to idle: tidy the heap now, not in the middle of a task
            for old_name, old in list(self.screens.items()):
                if old is previous and old_name in _LAZY_SCREENS and old_name != screen_name and old_name not in _KEEP_LOADED and cfg.get("POWER_UNLOAD_SCREENS"):
                    try:
                        previous.on_exit()
                    except Exception as e:
                        log(f"[NAV] on_exit of {old_name} failed: {e}")
                    self._unload_screen(old_name)
            self._apply_screen_input_mode()
            self.active_screen.on_enter(**kwargs)
            
            # Od razu renderujemy nowo aktywowany ekran
            self._render_active()

    # ---- used by the notifier and the dimmer ----

    def wake(self):
        """Light the screen up (a notification is about to appear)."""
        self.dimmer.wake()

    def show_overlay(self, overlay):
        self.overlay = overlay
        self.keypad.modifiers_as_keys = True          # OPT, the "done" key, must arrive as a key
        self._render_active()

    def hide_overlay(self):
        self.overlay = None
        self._apply_screen_input_mode()
        self._render_active()

    def _can_dim(self):
        if self.overlay is not None or getattr(self.active_screen, "keeps_screen_on", False):
            return False
        try:
            return not self.audio.is_recording()
        except Exception:
            return True

    def _tick_bars(self):
        now = time.ticks_ms()
        if time.ticks_diff(now, self._bars_at) < _BARS_TICK_MS:
            return
        self._bars_at = now
        if self.overlay is None and not self.dimmer.dimmed:
            self.renderer.refresh_bars()
            Lcd.flush()

    def _return_target(self, screen):
        """(screen name, kwargs) that brings the user back to `screen` afterwards."""
        custom = getattr(screen, "return_target", None)
        if custom is not None:
            return custom()
        for name, candidate in self.screens.items():
            if candidate is screen:
                return (name, {})
        return ("CLOCK", {})

    def _on_button(self, role):
        """A button of the device pressed (its role: see the port's make_buttons())."""
        if role == "quick":
            self._on_quick_button()
        elif role == "back":                   # a device without ESC key (the watch's side button): the same as ESC ...
            if self.active_screen is self.screens["CLOCK"]:
                return                         # ... except on the clock: there it only lights the screen up
            self.active_screen.handle_input("ESC")
            self._render_active()

    def _on_quick_button(self):
        """The quick button (G0 on the Cardputer) pressed.  The recorder screen toggles start/stop itself; from the
        clock and the menus the quick recorder starts at once and returns there when the take is saved.
        Screens that hold unsaved input (editors, time entry) ignore the button."""
        screen = self.active_screen
        handler = getattr(screen, "on_quick_button", None)
        if handler is not None:
            handler()
            self._render_active()
            return
        if not has("voice_notes") or not getattr(screen, "quick_record_from", False):
            trace(f"[BTN0] ignored on {type(screen).__name__}")
            return
        target = self._return_target(screen)
        trace(f"[BTN0] quick recorder from {target[0]}")
        self.set_screen("RECORD", autostart=True, return_to=target)

    def _on_config_changed(self, key, value):
        self._config_changed = True         # the main loop redraws the screen once

    def _apply_screen_input_mode(self):
        """Let the active screen choose whether Aa / OPT / FN / CTRL / ALT are plain keys."""
        self.keypad.modifiers_as_keys = bool(getattr(self.active_screen, "modifiers_as_keys", False))

    def _render_active(self):
        """Render the active screen (or the notification over it), then the focus dot / bars on top."""
        self.renderer.forget_bars()
        if self.overlay is not None:
            self.overlay.render(self.renderer)
            Lcd.flush()
            return
        self.active_screen.render(self.renderer)
        # The focus dot is optional (Personalize) and never on the main screen
        if cfg.get("FOCUS_DOT") and getattr(self.active_screen, "shows_focus_dot", True):
            self.renderer.draw_focus_indicator(self.focus.indicator())
        if getattr(self.active_screen, "shows_bars", False):
            self.renderer.draw_bars_clock()
        Lcd.flush()                    # a frame-buffer display (the watch) shows it now; M5.Lcd: nothing to do

    def run(self):
        """Main application event loop.

        Every phase is timed; when one exceeds _SLOW_PHASE_MS a [SLOW] line
        naming the phase, the key and the screen is appended to the boot log.
        (Deliberate time.sleep() pauses after Save/Delete show up there too.)
        An error inside a screen is logged and answered with a return to the clock.
        """
        try:
            self._apply_screen_input_mode()
            self._render_active()
        except Exception as e:
            self._recover_from_error(e)

        while self.running:
            try:
                self._step()
                self._ok_streak += 1
                if self._ok_streak >= _CLEAN_STREAK:
                    self._errors = 0
            except Exception as e:
                self._ok_streak = 0
                self._recover_from_error(e)
            power = self.power
            if power is None or not power.maybe_sleep():
                time.sleep_ms(power.pause_ms() if power else 20)

    def _recover_from_error(self, error):
        """Log the error and go back to the clock; give up after a run of failures."""
        self._errors += 1
        name = type(self.active_screen).__name__
        log(f"[ERROR] {name}: {type(error).__name__}: {error}")
        try:
            path = getattr(boot_log, "LOG_PATH", None)
            if path:
                with open(path, "a") as f:
                    sys.print_exception(error, f)
        except Exception:
            pass
        if self._errors > _MAX_RECOVERIES:
            log("[ERROR] Too many errors in a row - stopping")
            raise error
        if self.overlay is not None:                   # a failing notification must not trap the user
            self.overlay = None
            self.notifier.abort()
        try:
            on_exit = getattr(self.active_screen, "on_exit", None)
            if on_exit is not None:
                on_exit()                              # a screen may hold something that must be given back
        except Exception as e:
            log(f"[ERROR] on_exit failed: {e}")
        try:
            self.set_screen("CLOCK")
        except Exception as e:
            log(f"[ERROR] Cannot return to the clock: {e}")
            raise error

    def _step(self):
        """One iteration of the main loop (without the pause between iterations)."""
        t0 = time.ticks_ms()
        # Background work — must run every iteration, whichever screen is active:
        # chunked audio recording / playback, the services (focus timer, ...) and the buttons (G0)
        self.audio.tick()
        self.services.tick()
        if self._config_changed:
            self._config_changed = False
            self._render_active()      # colours / offsets may have changed
        self._tick_bars()
        for role, button in self._button_list:
            if button.pressed():
                self.dimmer.wake()     # a button lights the screen up AND acts (G0: the quick-recorder button)
                if self.deep_sleep is not None:
                    self.deep_sleep.user_active()
                if self.overlay is None:
                    self._on_button(role)
        t1 = time.ticks_ms()

        # get_pressed_action returns (action, modifier_changed).
        # modifier_changed is True when a modifier key was toggled (FN, Aa,
        # CTRL…) so the indicator re-renders even though action is None.
        action, modifier_changed = self.keypad.get_pressed_action()
        if action or modifier_changed:
            if self.deep_sleep is not None:
                self.deep_sleep.user_active()
            if self.dimmer.wake():     # the key that wakes a dimmed screen does nothing else
                action, modifier_changed = None, False
        t2 = time.ticks_ms()

        screen_name = type(self.active_screen).__name__
        input_ms = 0
        render_ms = 0

        if action and self.overlay is not None:
            self.overlay.handle_input(action)          # closing it redraws the screen underneath
        elif self.overlay is not None:
            if self.overlay.needs_refresh():
                self._render_active()                  # the countdown
        elif action:
            self.active_screen.handle_input(action)
            t3 = time.ticks_ms()
            self._render_active()
            t4 = time.ticks_ms()
            input_ms = time.ticks_diff(t3, t2)
            render_ms = time.ticks_diff(t4, t3)
        elif modifier_changed or self.active_screen.needs_refresh():
            # Redraw without input: modifier indicator or live content
            # (clock, recording / playback timer).
            self._render_active()
            render_ms = time.ticks_diff(time.ticks_ms(), t2)

        audio_ms = time.ticks_diff(t1, t0)
        keypad_ms = time.ticks_diff(t2, t1)
        worst = max(audio_ms, keypad_ms, input_ms, render_ms)
        if worst >= _SLOW_PHASE_MS and self._slow_logs < _MAX_SLOW_LOGS:
            self._slow_logs += 1
            log(f"[SLOW] bg={audio_ms} keypad={keypad_ms} input={input_ms} "
                f"render={render_ms} action={action} screen={screen_name}")
