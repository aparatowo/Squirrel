# squirrel_boot.py - starts Squirrel!  (the one place that knows about paths and about how the app is launched)
#
# /flash/main.py only does `import squirrel_boot; squirrel_boot.run()`.
#   * In a FROZEN build this module is part of the firmware, together with the whole app: nothing but main.py
#     (and the optional font) has to be on the flash.
#   * In a plain-files setup it is found in /flash/apps/Squirrel (main.py adds that folder to sys.path).
#
# DEV MODE: create an empty file /flash/DEV (Thonny: new file on the device).  Then /flash/apps/Squirrel is put FIRST
# on sys.path, so a .py file copied there replaces the frozen module of the same name - edit and test without
# rebuilding the firmware (a screens/ or hw/ folder there hides the WHOLE frozen package: copy it complete).
# Delete /flash/DEV to go back to the frozen code.  Never leave a .py with the name of a
# frozen module in /flash itself or next to main.py: it is found first and silently hides the frozen one
# (sq_info.report() lists such files).

import sys

DEV_MARKER = "/flash/DEV"
DEV_PATH = "/flash/apps/Squirrel"


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
        import M5
        M5.begin()
        log("[MAIN] M5.begin() OK")
    except Exception as e:
        log(f"[MAIN WARN] M5.begin() failed: {e}")

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
