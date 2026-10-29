# bars.py - what the '#' status bars show
#
# A bar is a row (or column) of '#' characters.  The number of characters never changes; only
# their colour does.  A cell is a colour name, or None for the normal colour (the theme's main colour).
#
#   battery  horizontal bar: the normal part stays at the left; the TAIL at the right shows what has
#            been used up, in the colour of the state: blue (high), green, yellow, red (low).
#            Vertical bar (the clock): the other way up - the tail is at the TOP and eats the
#            remaining charge downwards, so what is left is at the bottom, like a level in a tank.
#   focus    the coloured part grows from the left with today's progress towards the daily goal:
#            red, yellow, green, and blue once the goal is reached.  While the timer runs the last
#            coloured cell blinks, so it is visible at a glance that time is being counted.
#            Vertical bar (the clock): it rises from the bottom (FOCUS_BAR_FROM = "bottom"), or grows
#            down from the top (the classic way).
#   time     the clock's horizontal bars (BARS_TOP, BARS_BOTTOM): the time gone by, in one colour,
#            over the bar's normal colour.  Top: grows from the left with the hourglass's run (its
#            leading cell blinks while it counts), or with the hour when the hourglass is idle (or
#            BARS_TOP = "hour").  Bottom: grows from the right with the quarter hour, so the normal
#            colour drains to the left, and starts again at :00, :15, :30, :45.  "full": the plain
#            bar; "off": none.

import time


def _share(n, pct):
    """pct percent of n cells, rounded to the nearest whole cell."""
    return (pct * n + 50) // 100


def battery_color(level, blue_pct, green_pct, yellow_pct):
    high, mid, low = sorted((blue_pct, green_pct, yellow_pct), reverse=True)
    if level >= high:
        return "blue"
    if level >= mid:
        return "green"
    if level >= low:
        return "yellow"
    return "red"


def battery_cells(level, n, blue_pct, green_pct, yellow_pct):
    cells = [None] * n
    if level is None:
        return cells                               # unknown: show the bar untouched
    level = 0 if level < 0 else (100 if level > 100 else level)
    color = battery_color(level, blue_pct, green_pct, yellow_pct)
    for i in range(n - _share(n, 100 - level), n):
        cells[i] = color
    return cells


def focus_color(progress, red_pct, yellow_pct):
    if progress >= 100:
        return "blue"
    low, high = sorted((red_pct, yellow_pct))
    if progress < low:
        return "red"
    if progress < high:
        return "yellow"
    return "green"


def focus_cells(progress, n, red_pct, yellow_pct, running=False, blink_on=True):
    cells = [None] * n
    progress = 0 if progress < 0 else progress
    color = focus_color(progress, red_pct, yellow_pct)
    filled = _share(n, 100 if progress > 100 else progress)
    for i in range(filled):
        cells[i] = color
    if running:
        last = filled - 1 if filled > 0 else 0      # with nothing filled yet, the first cell blinks
        cells[last] = color if blink_on else None
    return cells


def time_cells(done, total, n, color, from_right=False, blink_on=None):
    """n cells, the share done / total of them (rounded down: full only at the end) in `color` - from the left, or
    from the right.  blink_on (True / False, None = no blinking): the phase of the leading cell, which blinks like the
    focus bar's while its timer counts (the first cell while nothing is coloured yet)."""
    cells = [None] * n
    if total <= 0:
        return cells
    done = 0 if done < 0 else (total if done > total else done)
    filled = done * n // total
    for i in range(filled):
        cells[i] = color
    if blink_on is not None:
        cells[filled - 1 if filled > 0 else 0] = color if blink_on else None
    return cells[::-1] if from_right else cells


class StatusBars:
    """Current cells for the bars, from the settings, the battery, the focus timer, the clock and the hourglass."""

    def __init__(self, cfg, battery, focus, now_ms=None, clock=None, hourglass=None):
        """clock() -> time.localtime()-like tuple (the hour / quarter bars); hourglass() -> the hourglass service or
        None while it does not exist yet."""
        self._cfg = cfg
        self._battery = battery
        self._focus = focus
        self._now = now_ms or time.ticks_ms
        self._clock = clock or time.localtime
        self._hourglass = hourglass or (lambda: None)

    def battery_cells(self, n, from_top=False):
        """from_top=True: the vertical bar, its tail at the top (cells are numbered top to bottom)."""
        c = self._cfg
        cells = battery_cells(self._battery.level(), n, c.get("BATTERY_BLUE_PCT"),
                              c.get("BATTERY_GREEN_PCT"), c.get("BATTERY_YELLOW_PCT"))
        return cells[::-1] if from_top else cells

    def _progress(self):
        goal = self._focus.goal_seconds
        return self._focus.today_seconds() * 100 // goal if goal > 0 else 0

    def charging(self):
        """True while the battery charges (or is guessed to: CHARGE_GUESS) and the mark is wanted (BARS_CHARGING)."""
        return bool(self._cfg.get("BARS_CHARGING") and self._battery is not None and self._battery.charging is True)

    def battery_color(self):
        """The colour of the battery bar's tail, for text about the battery; None: the bar's own colour (no tail)."""
        level, c = self._battery.level(), self._cfg
        if not level or level < 0:
            return None
        return battery_color(min(level, 100), c.get("BATTERY_BLUE_PCT"), c.get("BATTERY_GREEN_PCT"),
                             c.get("BATTERY_YELLOW_PCT"))

    def focus_color(self, progress=None):
        """The colour of the focus bar's filled cells, for text about focus; None: nothing done yet (the bar's own
        colour). progress: percent of the daily goal, today's by default."""
        progress = self._progress() if progress is None else progress
        if progress <= 0:
            return None
        c = self._cfg
        return focus_color(progress, c.get("FOCUS_RED_PCT"), c.get("FOCUS_YELLOW_PCT"))

    def focus_cells(self, n, vertical=False):
        """vertical=True: the clock's bar, cells numbered top to bottom - it rises from the bottom unless
        FOCUS_BAR_FROM says "top"."""
        c = self._cfg
        progress = self._progress()
        blink_on = (self._now() // 500) % 2 == 0
        cells = focus_cells(progress, n, c.get("FOCUS_RED_PCT"), c.get("FOCUS_YELLOW_PCT"),
                            self._focus.state == "running", blink_on)
        return cells[::-1] if vertical and c.get("FOCUS_BAR_FROM") == "bottom" else cells

    def _seconds_into(self, period):
        t = self._clock()
        return (t[4] * 60 + t[5]) % period

    def top_cells(self, n):
        """The clock's top bar, left to right, or None when it is off (BARS_TOP)."""
        mode, color = self._cfg.get("BARS_TOP"), self._cfg.get("BARS_TOP_COLOR")
        if mode == "off":
            return None
        if mode == "full":
            return [None] * n
        hg = self._hourglass() if mode == "hourglass" else None
        if hg is not None and hg.state != "idle":
            blink = (self._now() // 500) % 2 == 0 if hg.state == "running" else None
            return time_cells(hg.elapsed_ms(), hg.total_s * 1000, n, color, blink_on=blink)
        return time_cells(self._seconds_into(3600), 3600, n, color)

    def bottom_cells(self, n):
        """The clock's bottom bar, left to right, or None when it is off (BARS_BOTTOM)."""
        mode = self._cfg.get("BARS_BOTTOM")
        if mode == "off":
            return None
        if mode == "full":
            return [None] * n
        return time_cells(self._seconds_into(900), 900, n, self._cfg.get("BARS_BOTTOM_COLOR"), from_right=True)
