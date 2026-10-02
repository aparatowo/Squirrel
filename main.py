# /flash/main.py - entry point for Squirrel!
import sys

BASE_PATH = "/flash/apps/Squirrel"
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

import boot_log
boot_log.begin_session()
log = boot_log.log

log(f"[MAIN] __name__={__name__}")
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
        with open(boot_log.LOG_PATH, "a") as f:
            sys.print_exception(e, f)
    except Exception:
        pass
    try:
        sys.print_exception(e)
    except Exception:
        pass
    