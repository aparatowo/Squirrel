# verify_device.py - for a setup with plain .py files in /flash/apps/Squirrel.
# With a FROZEN build use  import sq_info; sq_info.report()  instead (see BUILD.md).
BASE = '/flash/apps/Squirrel/'
EXPECT = {
    'services.py': ['class ServiceManager'],
    'hw/__init__.py': ['the parts of the app that run the hardware'],
    'drivers/__init__.py': ['one module per CHIP'],
    'ports/__init__.py': ['one folder per device'],
    'ports/cardputer_adv/__init__.py': [],
    'ports/cardputer_adv/board.py': ['def make_input', 'def begin_led', 'def clock_chip', 'def motion_off'],
    'ports/cardputer_adv/keymap.py': ['MAP_ALT_SHIFT', 'class KeyMap', 'MODIFIER_STICKY'],
    'port_config.py': ["PORT = 'cardputer_adv'", 'HIDDEN_GROUPS', 'STORAGE_BASE_DIR', 'POWER_MGMT_WAKE_PINS'],
    'features.py': ['def has'],
    'drivers/m5_display.py': ['import Lcd as lcd'],
    'drivers/m5_power.py': ['def level', 'def charging', 'def millivolts'],
    'drivers/m5_audio.py': ['def open'],
    'drivers/ws2812.py': ['class WS2812Rmt', 'DRIVERS'],
    'drivers/pin_pulser.py': ['class PinPulser'],
    'drivers/bmi270.py': ['def off'],
    'bars.py': ['def battery_cells', 'def focus_cells', 'class StatusBars', 'from_top'],
    'hw/battery.py': ['class BatteryMonitor', 'class BatteryLogger'],
    'screen_dimmer.py': ['class ScreenDimmer'],
    'quiet_hours.py': ['def is_quiet', 'def quiet_guard', 'CHANNELS'],
    'screens/silent_mode_screen.py': ['class SilentModeScreen'],
    'screens/led_test_screen.py': ['class LedTestScreen', 'set_test'],
    'hw/led.py': ['class Led', 'def set_breath', 'def signal', 'MODES', 'RGB', 'fallback=None'],
    'hw/buzzer.py': ['class Buzzer', 'def signal', 'MODES', 'BUZZER_', 'pulser=None'],
    'sound.py': ['PATTERNS', 'def build', 'cuckoo', 'tock'],
    'notifier.py': ['class Notifier', 'class NotifyOverlay', 'def wrap'],
    'line_editor.py': ['class LineEditor'],
    'wifi_profiles.py': ['def choose_network', 'class WifiProfiles'],
    'drivers/gpio_button.py': ['class ButtonPoller'],
    'appconfig.py': ['class Config', 'cfg = Config()'],
    'appconfig_schema.py': ['SETTINGS = (', 'FOCUS_DOT', 'BARS_CLOCK', 'SCREEN_DIM_CLOCK_SECONDS', 'SCREEN_DIM_OTHER_SECONDS', 'NOTIFY_VOLUME', 'COLOR_KEY_SHIFT', 'KEYBOARD_LAYOUT', 'FONT_ENABLED', 'POMODORO_WORK_MIN', 'CUCKOO_ENABLED', 'POWER_LIGHT_SLEEP', 'METRO_VOLUME', 'BATTERY_LOG'],
    'drivers/sd_spi.py': ['def _mount_direct', 'self._args'],
    'note_editor.py': ['from appconfig import cfg', 'unique_title'],
    'todo_editor.py': ['from appconfig import cfg', 'unique_title', 'def toggle_done', 'def purge', 'def decorate'],
    'focus_timer.py': ['class FocusTimer', 'from timeutil import'],
    'timeutil.py': ['def local_from_utc'],
    'hw/radio.py': ['class RadioManager'],
    'wifi_ntp.py': ['class WifiNtpClient', 'def choose', 'def candidates'],
    'time_sync.py': ['class TimeSyncService', 'clock write failed', '_tick_scanning'],
    'menu_tree.py': ['HIDDEN_MENUS', 'NOTES_ROOT', 'reload_config', 'PERSONALIZE', 'EXPERIMENTAL', 'WIFI_NETWORKS', 'CONNECTIONS', 'TIME_DATE', 'FONT_TEST', 'Fallback network', 'Time settings', 'ROUTINES', 'INTERVALS', 'METRONOME', 'BREATHING', 'MIND'],
    'squirrel_app.py': ['self.services.tick()', 'self.timesync', 'def _on_quick_button', 'board.make_input()', 'cfg.load(nuts.CONFIG_FILE)', 'def _recover_from_error', '_LAZY_SCREENS', 'self.notifier', 'self.dimmer', 'def show_overlay', 'from gfx import Lcd', 'gfx.start(', 'FONT_TEST', 'held_at_start', 'self.scheduler', 'self.power', 'def runner', 'def metronome', '_unload_screen', '[MEM]', '_KEEP_LOADED', 'BatteryLogger'],
    'key_calibrator.py': ['def on_quick_button', 'last_key_code', 'from gfx import Lcd'],
    'drivers/tca8418_keypad.py': ['class TCA8418Keypad', 'def _init_controller', 'MAP_ALT_SHIFT', 'compose(action', 'from charmap import compose', 'def acknowledge'],
    'ui_renderer.py': ['def draw_focus_indicator', 'name=None', 'from appconfig import cfg', 'def draw_bars_clock', 'def refresh_bars', 'from gfx import Lcd', 'KEY_OPT', 'COLOR_KEY_NORMAL', '_line_layout', 'VIEW_COLS'],
    'drivers/ds1302.py': ['def read_valid'],
    'hw/rtc_provider.py': ['def sync_on_boot', 'def _open_chip'],
    'hw/audio_manager.py': ['def playback_state', 'def cancel_recording', 'from appconfig import cfg', 'def beep', 'volume=None', 'backend=None'],
    'storage_manager.py': ['def delete_path', 'def unique_title', 'def file_stem', 'def _real_title', 'from charmap import ascii_name', 'def stems'],
    'nuts.py': ['AUDIO_MIC_MAGNIFICATION', 'CONFIG_FILE', 'def named_color', 'FOCUS_DOT', 'BARS_CLOCK', 'WIFI_PROFILES_FILE', 'NOTIFY_VOLUME', 'KEYBOARD_LAYOUT', 'FONT_FILES', 'COLOR_KEY_OPT', 'LIGHTGREEN', 'TODO_KEEP_DAYS', 'MIND_DUMP_MAX_CHARS', 'POWER_SAVE', 'ROUTINES_FILE', 'TRAINING_FILE', '/flash/fonts/squirrel.vlw', 'STORAGE_BASE_DIR', 'BATTERY_LOG'],
    'screens/menu_screen.py': ['from menu_tree import', 'def return_target', 'def _begin_delete', 'reload_config', 'test_notification', 'isinstance(arg, tuple)', 'NOTE_EDITOR', '_toggle_todo', 'modifiers_as_keys'],
    'screens/clock_screen.py': ["FOCUS_KEY = 'OPT'", 'modifiers_as_keys = True', 'shows_focus_dot', 'shows_bars'],
    'screens/mind_dump_screen.py': ['class MindDumpScreen', 'MIND_DUMP_MAX_CHARS', 'unique_title'],
    'screens/wifi_screen.py': ['class WifiScreen', 'LineEditor', 'from gfx import Lcd'],
    'screens/personalize_screen.py': ['class PersonalizeScreen', 'from gfx import Lcd', '_ELSEWHERE', 'groups=None'],
    'screens/record_screen.py': ['def on_quick_button', 'keeps_screen_on', 'from gfx import Lcd'],
    'screens/focus_stats_screen.py': ['class FocusStatsScreen', 'menu_name="FOCUS"', 'quick_record_from', 'from gfx import Lcd', 'def bar_height', 'routines_done'],
    'screens/time_sync_screen.py': ['class TimeSyncScreen', 'from gfx import Lcd'],
    'screens/playback_screen.py': ['DELETE_CONFIRM_PRESSES', 'from gfx import Lcd'],
    'charmap.py': ['def fold', 'def ascii_name', 'def compose', 'LAYOUTS'],
    'gfx.py': ['class Display', 'def load_font', 'def start', 'charmap.fold', 'DISPLAY_DRIVER'],
    'text_layout.py': ['def wrap_line', 'def move_vertical', 'def scroll_to', 'VIEW_COLS', 'VIEW_ROWS'],
    'screens/font_test_screen.py': ['class FontTestScreen', 'TRY_SECONDS', 'machine.reset()'],
    'screens/note_editor_screen.py': ['COLS = 36', 'from text_layout import', 'from gfx import Lcd', 'Moved to Notes!'],
    'scheduler.py': ['class DayCounter', 'class RoutineStore', 'class Scheduler', 'def valid_now'],
    'intervals.py': ['class IntervalRunner', 'class Metronome', 'def pomodoro_plan', 'MAX_S'],
    'hw/power.py': ['class PowerManager', 'motion_off', 'wake_pins', 'def collect', 'gc.threshold', 'LOW_HEAP', '_repair_clock'],
    'screens/routines_screen.py': ['class RoutinesScreen', '_in_days'],
    'screens/interval_screen.py': ['class IntervalScreen', '_edit_input'],
    'screens/rhythm_screens.py': ['class MetronomeScreen', 'class BreathingScreen', 'def breath_phase'],
    'screens/viewer_screen.py': ['class ViewerScreen', 'VIEW_COLS', "'TAB'"],
    'squirrel_boot.py': ['def run', 'DEV_MARKER', 'sq_info', 'BOARD_MODULE'],
    'boot_log.py': ['def _rotate'],
}








bad = 0
# files that were renamed or replaced: an old copy on the device only causes confusion
OLD = ['usb_msc.py', 'usb_drive.py', 'usb_check.py', 'screens/usb_drive_screen.py', 'screens/input_screen.py',
       # moved to hw/: a flat copy left in /flash/apps/Squirrel is never used again
       'audio_manager.py', 'battery.py', 'buttons.py', 'buzzer.py', 'cardputer_keypad.py', 'led.py', 'power.py', 'radio.py', 'rtc_base.py', 'rtc_ds1302.py', 'rtc_provider.py', 'sd_card.py',
       # moved from hw/ to drivers/ (named after the chip) when the ports came
       'hw/cardputer_keypad.py', 'hw/rtc_ds1302.py', 'hw/sd_card.py', 'hw/buttons.py']
for name, markers in EXPECT.items():
    try:
        with open(BASE + name) as f:
            text = f.read()
        missing = [m for m in markers if m not in text]
        status = 'OK     ' if not missing else 'STARA/ZLA TRESC'
    except OSError:
        status = 'BRAK   '
    print(status, name)
    bad += (status != 'OK     ')
for name in OLD:
    try:
        open(BASE + name).close()
        print('STARY PLIK - USUN   ', name)
        bad += 1
    except OSError:
        pass
import os
# a compiled .mpy next to a .py is imported INSTEAD of it: a stale one hides every later change
for name in EXPECT:
    mpy = BASE + name[:-3] + '.mpy'
    try:
        os.stat(mpy)
        print('PRZESLANIA .py - USUN', name[:-3] + '.mpy')
        bad += 1
    except OSError:
        pass
# the font is binary: only its size can be checked
for name, size in {'fonts/squirrel.vlw': 19863}.items():
    try:
        got = os.stat(BASE + name)[6]
        status = 'OK     ' if got == size else 'ZLY ROZMIAR %d (ma byc %d)' % (got, size)
    except OSError:
        status = 'BRAK (potrzebny tylko dla polskich liter)'
    print(status, name)
    bad += (status[:2] != 'OK' and not status.startswith('BRAK'))
print('WSZYSTKO OK' if not bad else 'DO POPRAWY: %d' % bad)
