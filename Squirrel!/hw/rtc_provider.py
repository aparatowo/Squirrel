# rtc_provider.py — RTC manager with manual sync and soft fallback
#
# Architecture:
#   - SoftTimeProvider  : always active, uses ESP32 internal RTC (machine.RTC)
#   - RTCManager        : wraps SoftTimeProvider; sync_from_hardware() briefly
#                         connects to DS1302, copies its time to the soft RTC,
#                         then lets the DS1302 go — no permanent connection needed.
#
# The DS1302 only needs to be physically connected during sync.
# After sync the soft RTC keeps time until the next power cycle.

import machine
from boot_log import log
from hw.rtc_base import TimeProvider
from nuts import RTC_CLK_PIN, RTC_DAT_PIN, RTC_RST_PIN


class SoftTimeProvider(TimeProvider):
    """TimeProvider backed by the ESP32 internal RTC (machine.RTC).

    Accuracy: ±several seconds/day, no battery backup — resets on power loss.
    Always available; used as the sole time source after an optional DS1302 sync.
    """

    def __init__(self):
        self._rtc = machine.RTC()
        print("[RTC] Soft time provider ready")

    @property
    def is_available(self) -> bool:
        return True

    def get_datetime(self) -> tuple:
        # machine.RTC.datetime() → (year, month, mday, weekday, hour, min, sec, subsec)
        r = self._rtc.datetime()
        return (r[0], r[1], r[2], r[4], r[5], r[6], r[3], 0)

    def set_datetime(self, dt: tuple) -> None:
        year, month, mday, hour, minute, second, weekday, _ = dt
        # machine.RTC expects: (year, month, mday, weekday, hour, min, sec, subsec)
        self._rtc.datetime((year, month, mday, weekday, hour, minute, second, 0))


class RTCManager:
    """Owns the active TimeProvider and exposes a one-shot hardware sync.

    Normal operation:
        app.rtc.get_time_str()   # delegates to SoftTimeProvider
        app.rtc.get_date_str()

    Manual sync from Settings screen:
        ok, msg = app.rtc.sync_from_hardware()
        # ok  : bool — True on success
        # msg : str  — display message for the UI
    """

    def __init__(self):
        self._provider = SoftTimeProvider()
        self.last_sync_source = "soft"   # "soft" | "ds1302"

    # ------------------------------------------------------------------
    # Public API — delegates to active provider
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        return self._provider.is_available

    def get_datetime(self) -> tuple:
        return self._provider.get_datetime()

    def set_datetime(self, dt: tuple) -> None:
        self._provider.set_datetime(dt)

    def get_date_str(self) -> str:
        return self._provider.get_date_str()

    def get_time_str(self) -> str:
        return self._provider.get_time_str()

    # ------------------------------------------------------------------
    # One-shot hardware sync (called from Settings screen)
    # ------------------------------------------------------------------

    def sync_on_boot(self) -> bool:
        """Once at start-up: take the time from a permanently attached DS1302.

        Only a plausible, running, stable reading is accepted (see read_valid);
        anything else leaves the internal clock untouched.  Returns True if synced.
        """
        try:
            from hw.rtc_ds1302 import DS1302TimeProvider
            hw = DS1302TimeProvider(RTC_CLK_PIN, RTC_DAT_PIN, RTC_RST_PIN)
            dt = hw.read_valid()
        except Exception as e:
            log(f"[RTC] Boot sync skipped: {e}")
            return False
        self._provider.set_datetime(dt)
        self.last_sync_source = "ds1302"
        log(f"[RTC] Boot sync from DS1302: {self.get_time_str()} {self.get_date_str()}")
        return True

    def sync_from_hardware(self) -> tuple:
        """Try to read time from DS1302 and copy it to the soft RTC.

        The DS1302 only needs to be connected during this call.
        After it returns, the physical module can be safely unplugged.

        Returns:
            (True,  "Synced: HH:MM DD-MM-YYYY")  on success
            (False, "RTC not found: <reason>")    on failure
        """
        try:
            from hw.rtc_ds1302 import DS1302TimeProvider
            hw = DS1302TimeProvider(RTC_CLK_PIN, RTC_DAT_PIN, RTC_RST_PIN)
            dt = hw.get_datetime()
            self._provider.set_datetime(dt)
            self.last_sync_source = "ds1302"

            time_str = self._provider.get_time_str()
            date_str = self._provider.get_date_str()
            msg = f"Synced: {time_str} {date_str}"
            print(f"[RTC] {msg}")
            return True, msg

        except Exception as e:
            msg = f"RTC not found: {e}"
            print(f"[RTC] Sync failed: {e}")
            return False, msg

    def set_manual(self, dt: tuple) -> None:
        """Set time manually and mirror to DS1302 if connected.

        dt: (year, month, mday, hour, minute, second, weekday, yearday)
        Sets the soft RTC first (always), then tries to write the same time
        to DS1302 so it survives a power cycle.
        """
        self._provider.set_datetime(dt)
        self.last_sync_source = "manual"
        print(f"[RTC] Time set manually: {self.get_time_str()} {self.get_date_str()}")

        # Mirror to hardware RTC if available — non-fatal if not connected
        try:
            from hw.rtc_ds1302 import DS1302TimeProvider
            hw = DS1302TimeProvider(RTC_CLK_PIN, RTC_DAT_PIN, RTC_RST_PIN)
            hw.set_datetime(dt)
            print("[RTC] Time mirrored to DS1302")
        except Exception as e:
            print(f"[RTC] DS1302 mirror skipped: {e}")
