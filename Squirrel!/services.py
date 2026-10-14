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
    paused = False              # True while a Bluetooth session runs (screens/ble_*_screen.py): the services wait

    def __init__(self):
        self._entries = []      # [service, consecutive_errors, disabled]

    def add(self, service):
        """Register a service and return it (so it can be assigned in one line)."""
        self._entries.append([service, 0, False])
        return service

    def tick(self):
        # Paused for the few seconds of a Bluetooth session: MicroPython runs the radio's IRQ handler under the same
        # lock as this loop, so a loop busy with the services (files on the card, ...) keeps the radio waiting.
        # (It was first taken for the cause of the Cardputer's resets during a sync; that was ble/central.py keeping
        # the IRQ's own tuple - 2026-10-13.)
        if self.paused:
            return
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
