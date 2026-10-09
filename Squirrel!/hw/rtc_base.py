# rtc_base.py — Abstract RTC interface (port)
#
# Any RTC implementation must subclass TimeProvider and implement
# all methods below.  The rest of the application only talks to
# TimeProvider — it never imports a concrete driver directly.


class TimeProvider:
    """Abstract base class for RTC sources.

    Implementations:
      - DS1302TimeProvider  (rtc_ds1302.py)  — hardware RTC via 3-wire bus
      - SoftTimeProvider    (rtc_provider.py) — ESP32 internal timer fallback

    All datetime tuples follow MicroPython's time.localtime() convention:
      (year, month, mday, hour, minute, second, weekday, yearday)
    where weekday: 0=Monday … 6=Sunday.
    """

    @property
    def is_available(self) -> bool:
        """True when the provider has a valid time source."""
        raise NotImplementedError

    def get_datetime(self) -> tuple:
        """Return current datetime as (year, month, mday, hour, minute, second, weekday, yearday)."""
        raise NotImplementedError

    def set_datetime(self, dt: tuple) -> None:
        """Set the datetime.  dt must be (year, month, mday, hour, minute, second, weekday, yearday)."""
        raise NotImplementedError

    def get_date_str(self) -> str:
        """Return date formatted as DD-MM-YYYY (used by the clock screen)."""
        dt = self.get_datetime()
        return f"{dt[2]:02d}-{dt[1]:02d}-{dt[0]}"

    def get_time_str(self) -> str:
        """Return time formatted as HH:MM (used by the clock screen)."""
        dt = self.get_datetime()
        return f"{dt[3]:02d}:{dt[4]:02d}"