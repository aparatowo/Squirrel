# verify_device.py - for a setup with plain .py files in /flash/apps/Squirrel.
# With a FROZEN build use  import sq_info; sq_info.report()  instead (see BUILD.md).
BASE = '/flash/apps/Squirrel/'
EXPECT = {
    'services.py': ['class ServiceManager'],
    'bars.py': ['def battery_cells', 'def focus_cells', 'class StatusBars', 'from_top'],
    'battery.py': ['class BatteryMonitor', 'class BatteryLogger'],
    'screen_dimmer.py': ['class ScreenDimmer'],
    'sound.py': ['PATTERNS', 'def build', 'cuckoo', 'tock'],
    'notifier.py': ['class Notifier', 'class NotifyOverlay', 'def wrap'],
    'line_editor.py': ['class LineEditor'],
    'wifi_profiles.py': ['def choose_network', 'class WifiProfiles'],
    'buttons.py': ['class ButtonPoller', 'held_at_start'],
    'appconfig.py': ['class Config', 'cfg = Config()'],
    'appconfig_schema.py': ['SETTINGS = (', 'FOCUS_DOT', 'BARS_CLOCK', 'SCREEN_DIM_SECONDS', 'NOTIFY_VOLUME', 'COLOR_KEY_SHIFT', 'KEYBOARD_LAYOUT', 'FONT_ENABLED', 'POMODORO_WORK_MIN', 'CUCKOO_ENABLED', 'POWER_LIGHT_SLEEP', 'METRO_VOLUME', 'BATTERY_LOG'],
    'sd_card.py': ['def _mount_direct'],
    'note_editor.py': ['from appconfig import cfg', 'unique_title'],
    'todo_editor.py': ['from appconfig import cfg', 'unique_title', 'def toggle_done', 'def purge', 'def decorate'],
    'focus_timer.py': ['class FocusTimer', 'from timeutil import'],
    'timeutil.py': ['def local_from_utc'],
    'radio.py': ['class RadioManager'],
    'wifi_ntp.py': ['class WifiNtpClient', 'def choose', 'def candidates'],
    'time_sync.py': ['class TimeSyncService', 'clock write failed', '_tick_scanning'],
    'menu_tree.py': ['NOTES_ROOT', 'reload_config', 'PERSONALIZE', 'EXPERIMENTAL', 'WIFI_NETWORKS', 'CONNECTIONS', 'TIME_DATE', 'FONT_TEST', 'Fallback network', 'Time settings', 'ROUTINES', 'INTERVALS', 'METRONOME', 'BREATHING', 'MIND'],
    'squirrel_app.py': ['self.services.tick()', 'self.timesync', 'def _on_button0', 'cfg.load(nuts.CONFIG_FILE)', 'def _recover_from_error', '_LAZY_SCREENS', 'self.notifier', 'self.dimmer', 'def show_overlay', 'from gfx import Lcd', 'gfx.start(', 'FONT_TEST', 'held_at_start', 'self.scheduler', 'self.power', 'def runner', 'def metronome', '_unload_screen', '[MEM]', '_KEEP_LOADED', 'BatteryLogger'],
    'key_calibrator.py': ['def on_button0', 'last_key_code', 'from gfx import Lcd'],
    'cardputer_keypad.py': ['def _init_controller', 'MAP_ALT_SHIFT', 'compose(action', 'from charmap import compose', 'def acknowledge'],
    'ui_renderer.py': ['def draw_focus_indicator', 'name=None', 'from appconfig import cfg', 'def draw_bars_clock', 'def refresh_bars', 'from gfx import Lcd', 'KEY_OPT', 'COLOR_KEY_NORMAL', 'title[:34].center(36)', 'VIEW_COLS'],
    'rtc_ds1302.py': ['def read_valid'],
    'rtc_provider.py': ['def sync_on_boot'],
    'audio_manager.py': ['def playback_state', 'def cancel_recording', 'from appconfig import cfg', 'def beep', 'volume=None'],
    'storage_manager.py': ['def delete_path', 'def unique_title', 'def file_stem', 'def _real_title', 'from charmap import ascii_name', 'def stems'],
    'nuts.py': ['AUDIO_MIC_MAGNIFICATION', 'CONFIG_FILE', 'def named_color', 'FOCUS_DOT', 'BARS_CLOCK', 'WIFI_PROFILES_FILE', 'NOTIFY_VOLUME', 'KEYBOARD_LAYOUT', 'FONT_FILES', 'COLOR_KEY_OPT', 'MAP_ALT_SHIFT', 'LIGHTGREEN', 'TODO_KEEP_DAYS', 'MIND_DUMP_MAX_CHARS', 'POWER_SAVE', 'ROUTINES_FILE', 'TRAINING_FILE', '/flash/fonts/squirrel.vlw', 'class KeyMap', 'BATTERY_LOG'],
    'screens/menu_screen.py': ['from menu_tree import', 'def return_target', 'def _begin_delete', 'reload_config', 'test_notification', 'isinstance(arg, tuple)', 'NOTE_EDITOR', '_toggle_todo', 'modifiers_as_keys'],
    'screens/clock_screen.py': ["FOCUS_KEY = 'OPT'", 'modifiers_as_keys = True', 'shows_focus_dot', 'shows_bars'],
    'screens/mind_dump_screen.py': ['class MindDumpScreen', 'MIND_DUMP_MAX_CHARS', 'unique_title'],
    'screens/wifi_screen.py': ['class WifiScreen', 'LineEditor', 'from gfx import Lcd'],
    'screens/personalize_screen.py': ['class PersonalizeScreen', 'from gfx import Lcd', '_ELSEWHERE', 'groups=None'],
    'screens/record_screen.py': ['def on_button0', 'keeps_screen_on', 'from gfx import Lcd'],
    'screens/focus_stats_screen.py': ['class FocusStatsScreen', 'menu_name="FOCUS"', 'quick_record_from', 'from gfx import Lcd', 'def bar_height', 'routines_done'],
    'screens/time_sync_screen.py': ['class TimeSyncScreen', 'from gfx import Lcd'],
    'screens/playback_screen.py': ['DELETE_CONFIRM_PRESSES', 'from gfx import Lcd'],
    'charmap.py': ['def fold', 'def ascii_name', 'def compose', 'LAYOUTS'],
    'gfx.py': ['class Display', 'def load_font', 'def start', 'charmap.fold'],
    'text_layout.py': ['def wrap_line', 'def move_vertical', 'def scroll_to', 'VIEW_COLS', 'VIEW_ROWS'],
    'screens/font_test_screen.py': ['class FontTestScreen', 'TRY_SECONDS', 'machine.reset()'],
    'screens/note_editor_screen.py': ['COLS = 36', 'from text_layout import', 'from gfx import Lcd', 'Moved to Notes!'],
    'scheduler.py': ['class DayCounter', 'class RoutineStore', 'class Scheduler', 'def valid_now'],
    'intervals.py': ['class IntervalRunner', 'class Metronome', 'def pomodoro_plan', 'MAX_S'],
    'power.py': ['class PowerManager', 'def imu_off', 'def collect', 'gc.threshold', 'LOW_HEAP', '_repair_clock'],
    'screens/routines_screen.py': ['class RoutinesScreen', '_in_days'],
    'screens/interval_screen.py': ['class IntervalScreen', '_edit_input'],
    'screens/rhythm_screens.py': ['class MetronomeScreen', 'class BreathingScreen', 'def breath_phase'],
    'screens/viewer_screen.py': ['class ViewerScreen', 'VIEW_COLS', "'TAB'"],
    'squirrel_boot.py': ['def run', 'DEV_MARKER', 'sq_info'],
    'boot_log.py': ['def _rotate'],
}








bad = 0
# files that were renamed or replaced: an old copy on the device only causes confusion
OLD = ['usb_msc.py', 'usb_drive.py', 'usb_check.py', 'screens/usb_drive_screen.py', 'screens/input_screen.py']
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
