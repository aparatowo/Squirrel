# rtc_provider.py — RTC manager with manual sync and soft fallback
#
# Architecture:
#   - SoftTimeProvider  : always active, uses ESP32 internal RTC (machine.RTC)
#   - RTCManager        : wraps SoftTimeProvider; sync_from_hardware() briefly
#                         connects to the hardware clock chip, copies its time to
#                         the soft RTC, then lets the chip go — no permanent
#                         connection needed.
#
# The hardware clock is the port's ([clock] in ports/<port>/port.toml): the board
# gives RTCManager a factory that opens it (on the Cardputer a DS1302 on the EXT
# header, drivers/ds1302.py), or none.  The chip only needs to be physically
# connected during sync.  After sync the soft RTC keeps time until the next power cycle.

import machine
from boot_log import log
from hw.rtc_base import TimeProvider


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

    def __init__(self, chip=None, chip_name="ds1302"):
        """chip() -> a TimeProvider of the hardware clock (raises when it does not answer); None = the device has none.
        chip_name names it in last_sync_source and in the messages ("ds1302" -> "DS1302")."""
        self._provider = SoftTimeProvider()
        self._chip = chip
        self._chip_name = chip_name
        self.last_sync_source = "soft"   # "soft" | chip_name | "manual"

    def _open_chip(self):
        if self._chip is None:
            raise OSError("no hardware clock on this device")
        return self._chip()

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
            hw = self._open_chip()
            dt = hw.read_valid()
        except Exception as e:
            log(f"[RTC] Boot sync skipped: {e}")
            return False
        self._provider.set_datetime(dt)
        self.last_sync_source = self._chip_name
        log(f"[RTC] Boot sync from {self._chip_name.upper()}: {self.get_time_str()} {self.get_date_str()}")
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
            hw = self._open_chip()
            dt = hw.get_datetime()
            self._provider.set_datetime(dt)
            self.last_sync_source = self._chip_name

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
            hw = self._open_chip()
            hw.set_datetime(dt)
            print(f"[RTC] Time mirrored to {self._chip_name.upper()}")
        except Exception as e:
            print(f"[RTC] {self._chip_name.upper()} mirror skipped: {e}")
