# alarms.py - the coming moments at which the device has something to do (routines, the cuckoo, snoozed routines)
#
# Sources register a function  events(now, until) -> [(epoch seconds, label), ...]  (epoch: time.time()'s, local).
# AlarmQueue merges them: upcoming() for the "Upcoming alarms" screen, next() for the deep sleep (deep_sleep.py), which
# writes it into the hardware clock's alarm - when it comes, the device wakes, the source does its job (the scheduler
# fires the routine as usual), and before the next sleep the next one is written.  Nothing here touches hardware.
import time


class AlarmQueue:
    def __init__(self):
        self._sources = []

    def add_source(self, events):
        self._sources.append(events)

    def upcoming(self, now=None, n=8, horizon_s=8 * 86400):
        """The next n events after `now`, earliest first."""
        now = time.time() if now is None else now
        out = []
        for events in self._sources:
            try:
                out.extend(events(now, now + horizon_s))
            except Exception:
                pass
        out.sort(key=lambda e: e[0])
        return out[:n]

    def next(self, now=None):
        """(epoch, label) of the first event after `now`, or None."""
        first = self.upcoming(now, 1)
        return first[0] if first else None
