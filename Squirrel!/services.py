# services.py - background services ticked by the main loop
#
# A service is any object with a tick() method.  Services own their state and
# keep running whichever screen is active (or none is visible), because the main
# loop ticks them on every iteration.  Screens only start/stop them and read
# their state.  A failing service must never take the whole application down:
# errors are logged, and a service that keeps failing is switched off.

from boot_log import log

_MAX_CONSECUTIVE_ERRORS = 5


class ServiceManager:
    def __init__(self):
        self._entries = []      # [service, consecutive_errors, disabled]

    def add(self, service):
        """Register a service and return it (so it can be assigned in one line)."""
        self._entries.append([service, 0, False])
        return service

    def tick(self):
        for entry in self._entries:
            if entry[2]:
                continue
            try:
                entry[0].tick()
                entry[1] = 0
            except Exception as e:
                entry[1] += 1
                name = type(entry[0]).__name__
                log(f"[SERVICE] {name} error ({entry[1]}): {e}")
                if entry[1] >= _MAX_CONSECUTIVE_ERRORS:
                    entry[2] = True
                    log(f"[SERVICE] {name} disabled after repeated errors")
