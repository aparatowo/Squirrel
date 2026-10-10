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


def run():
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
