# squirrel_boot.py - starts Squirrel!  (the one place that knows about paths and about how the app is launched)
#
# /flash/main.py only does `import squirrel_boot; squirrel_boot.run()`.  (Paths here are the Cardputer's: on a port
# with plain MicroPython the flash is the root, so /flash/DEV is /DEV - port_config.STORAGE_FLASH_ROOT.)
#   * In a FROZEN build this module is part of the firmware, together with the whole app: nothing but main.py
#     (and the optional font) has to be on the flash.
#   * In a plain-files setup it is found in /flash/apps/Squirrel (main.py adds that folder to sys.path).
#
# DEV MODE: create an empty file /flash/DEV (Thonny: new file on the device).  Then /flash/apps/Squirrel is put FIRST
# on sys.path, so a .py file copied there replaces the frozen module of the same name - edit and test without
# rebuilding the firmware (a screens/, hw/, drivers/ or ports/ folder there hides the WHOLE frozen package: copy it
# complete).  port_config.py there must be the one of this device (build_firmware.py --gen-port-config --port ...).
# Delete /flash/DEV to go back to the frozen code.  Never leave a .py with the name of a
# frozen module in /flash itself or next to main.py: it is found first and silently hides the frozen one
# (sq_info.report() lists such files).

import sys
from port_config import STORAGE_FLASH_ROOT as _FLASH      # "/flash" on UIFlow, "" (the root) on plain MicroPython

DEV_MARKER = _FLASH + "/DEV"
DEV_PATH = _FLASH + "/apps/Squirrel"


def dev_mode():
    try:
        import os
        os.stat(DEV_MARKER)
        return True
    except OSError:
        return False


def _frozen_first():
    """The frozen modules before the file system: MicroPython looks in the current folder first ('' before '.frozen'),
    which costs a few file-system lookups per import and lets a stray file hide a frozen module.  DEV mode puts its
    folder in front of this again (run())."""
    if ".frozen" in sys.path:
        sys.path.remove(".frozen")
        sys.path.insert(0, ".frozen")


def _early_clock(board, log):
    """Show the time as soon as the display is up, before the app is built (it takes seconds: after every wake from a
    deep sleep the ESP32 starts from scratch).  Only for a board that asks for it (EARLY_CLOCK) - its storage needs
    no mounting, so the settings (colours, the footer) can be read this early; the app does not read them again."""
    try:
        import time
        import nuts
        from appconfig import cfg
        cfg.load(nuts.CONFIG_FILE)
        t = time.localtime()
        if t[0] < 2024:                       # a cold start: the internal clock is not set yet - the hardware one is
            factory = board.clock_chip()[0]
            if factory is not None:
                dt = factory().read_valid()
                import machine
                machine.RTC().datetime((dt[0], dt[1], dt[2], dt[6], dt[3], dt[4], dt[5], 0))
                t = time.localtime()
        if t[0] < 2024:
            return
        from gfx import Lcd
        from ui_renderer import UIRenderer
        Lcd.full_height(True)
        r = UIRenderer()
        r.render_clock_tall("%02d-%02d-%d" % (t[2], t[1], t[0]), "%02d:%02d" % (t[3], t[4]),
                            ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[t[6] % 7], "")
        Lcd.flush()
        r.detach()
        log("[MAIN] early clock shown")
    except Exception as e:
        log(f"[MAIN] early clock skipped: {type(e).__name__}: {e}")


def run():
    _frozen_first()
    if dev_mode() and DEV_PATH not in sys.path[:1]:
        sys.path.insert(0, DEV_PATH)

    import boot_log
    boot_log.begin_session()
    log = boot_log.log

    log(f"[MAIN] __name__={__name__}")
    if dev_mode():
        log(f"[MAIN] DEV mode: files in {DEV_PATH} replace the frozen modules")
    try:
        import sq_info
        log(f"[MAIN] frozen build {sq_info.BUILD} ({len(sq_info.FILES)} modules)")
    except ImportError:
        log("[MAIN] not a frozen build (plain files)")
    try:
        import machine
        log(f"[MAIN] reset_cause={machine.reset_cause()}")
    except Exception as e:
        log(f"[MAIN] reset_cause unavailable: {e}")

    try:
        import port_config
        board = __import__(port_config.BOARD_MODULE, None, None, ("begin",))
        board.begin()
        log(f"[MAIN] board {port_config.PORT}: begin() OK")
        if getattr(board, "EARLY_CLOCK", False):
            _early_clock(board, log)
    except Exception as e:
        log(f"[MAIN WARN] board begin() failed: {e}")

    try:
        from squirrel_app import SquirrelApp
        app = SquirrelApp()
        log("[MAIN] App constructed, entering main loop")
        app.run()
    except KeyboardInterrupt:
        log("[MAIN] Stopped by user")
    except Exception as e:
        log(f"[MAIN CRITICAL] {e}")
        try:
            from hw.buzzer import buzzer
            buzzer.off()
        except Exception:
            pass
        try:
            from hw.led import led
            led.off()
        except Exception:
            pass
        try:
            with open(boot_log.LOG_PATH, "a") as f:
                sys.print_exception(e, f)
        except Exception:
            pass
        try:
            sys.print_exception(e)
        except Exception:
            pass
