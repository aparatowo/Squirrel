# bars.py - what the '#' status bars show
#
# A bar is a row (or column) of '#' characters.  The number of characters never changes; only
# their colour does.  A cell is a colour name, or None for the normal colour (the theme's main colour).
#
#   battery  horizontal bar: the normal part stays at the left; the TAIL at the right shows what has
#            been used up, in the colour of the state: blue (high), green, yellow, red (low).
#            Vertical bar (the clock): the other way up - the tail is at the TOP and eats the
#            remaining charge downwards, so what is left is at the bottom, like a level in a tank.
#   focus    the coloured part grows from the left / top with today's progress towards the daily
#            goal: red, yellow, green, and blue once the goal is reached.  While the timer runs the
#            last coloured cell blinks, so it is visible at a glance that time is being counted.

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


class StatusBars:
    """Current cells for the bars, from the settings, the battery and the focus timer."""

    def __init__(self, cfg, battery, focus, now_ms=None):
        self._cfg = cfg
        self._battery = battery
        self._focus = focus
        self._now = now_ms or time.ticks_ms

    def battery_cells(self, n, from_top=False):
        """from_top=True: the vertical bar, its tail at the top (cells are numbered top to bottom)."""
        c = self._cfg
        cells = battery_cells(self._battery.level(), n, c.get("BATTERY_BLUE_PCT"),
                              c.get("BATTERY_GREEN_PCT"), c.get("BATTERY_YELLOW_PCT"))
        return cells[::-1] if from_top else cells

    def focus_cells(self, n):
        c = self._cfg
        goal = self._focus.goal_seconds
        progress = self._focus.today_seconds() * 100 // goal if goal > 0 else 0
        blink_on = (self._now() // 500) % 2 == 0
        return focus_cells(progress, n, c.get("FOCUS_RED_PCT"), c.get("FOCUS_YELLOW_PCT"),
                           self._focus.state == "running", blink_on)
