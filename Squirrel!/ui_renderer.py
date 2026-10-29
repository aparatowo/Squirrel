from gfx import Lcd, SCREEN_W, SCREEN_H
from nuts import THEME, FONTS_THEME, named_color
from appconfig import cfg
from i18n import _
from text_layout import wrap_line

VIEW_WIDTH = 26                 # characters in a row of the viewer's box (the font is wider than 6 px)


def view_rows(content):
    """The viewer's rows: each line of the text wrapped at spaces."""
    rows = []
    for line in content.split("\n"):
        for a, b in wrap_line(line, VIEW_WIDTH):
            rows.append(line[a:b])
    return rows

# theme entry -> setting that holds its colour name
_COLOR_SETTINGS = (("BG", "COLOR_BG"), ("FG", "COLOR_FG"), ("ACCENT", "COLOR_ACCENT"),
                   ("WARNING", "COLOR_WARNING"), ("ERROR", "COLOR_ERROR"),
                   ("KEY_SHIFT", "COLOR_KEY_SHIFT"), ("KEY_FN", "COLOR_KEY_FN"), ("KEY_OPT", "COLOR_KEY_OPT"))

# the charging mark by the clock's battery bar: a lightning of 5 x 8 pixels, (first column, last column) of each row
_BOLT = ((2, 4), (1, 3), (0, 2), (0, 4), (2, 4), (1, 3), (0, 2), (0, 0))

_V_CELLS = SCREEN_H // 8   # '#' characters in a vertical bar (8 px each: 128 px of the 135 px Cardputer screen)
_SCREEN_W = SCREEN_W
# The menu header lines and the horizontal bars are measured in pixels with the font in use (Lcd.textWidth), not counted
# in characters: the firmware's own font and the .vlw font have different widths, and 36 characters fill the screen
# with one but not with the other.


def _text_width(text):
    """Width of `text` in pixels with the current font and size (6 px per character if the display cannot say)."""
    try:
        width = Lcd.textWidth(text)
        if width > 0:
            return width
    except Exception:
        pass
    return 6 * len(text)


def _line_layout():
    """(cells, cell width, x of the first cell): '#' characters that fill the screen width, centred."""
    cell = max(1, _text_width("#"))
    cells = max(1, _SCREEN_W // cell)
    return cells, cell, (_SCREEN_W - cells * cell) // 2


class UIRenderer:
    def __init__(self):
        self.theme = THEME
        self.fonts = FONTS_THEME
        self.bars = None               # bars.StatusBars, set by the app
        self._bar_cache = {}           # what each bar currently shows on screen: only changes are redrawn
        self._bars_kind = None         # which bars the screen that was drawn last has: "clock" | "menu"
        self._list = None              # the list on screen (render_menu): (what it shows, the selected row) or None
        self.epoch = 0                 # +1 whenever what is on screen may have been painted over: a screen that redraws
                                       # only parts of itself draws all of it when this changed since its last frame
        self._apply_colors()
        cfg.on_change(self._on_setting_changed)

    def _apply_colors(self):
        """Copy the colour settings into the theme dict (in place: screens hold this very dict)."""
        for theme_key, setting in _COLOR_SETTINGS:
            self.theme[theme_key] = named_color(cfg.get(setting))
        normal = cfg.get("COLOR_KEY_NORMAL")          # "text" = the colour of the text itself
        self.theme["KEY_NORMAL"] = self.theme["FG"] if normal == "text" else named_color(normal)

    def detach(self):
        """No longer follow the settings (a renderer used only for a moment: squirrel_boot's early clock)."""
        cfg.off_change(self._on_setting_changed)

    def _on_setting_changed(self, key, value):
        if key.startswith("COLOR_"):
            self._apply_colors()

    def clear(self):
        Lcd.fillScreen(self.theme["BG"])
        self._bar_cache = {}           # the screen is blank again, so nothing of the bars is on it
        self._bars_kind = None
        self._painted_over()

    def forget_list(self):
        """Something else was drawn over the screen (another screen, a notification): render_menu (and every screen
        that redraws only parts of itself, see epoch) draws all of it."""
        self._painted_over()

    def _painted_over(self):
        self._list = None
        self.epoch += 1

    # ---- status bars ('#' characters; see bars.py) ----

    def _cell_color(self, cell):
        return self.theme["FG"] if cell is None else named_color(cell)

    def _paint_bar(self, bar_id, cells, positions):
        """Draw the cells that differ from what is on screen (all of them after clear())."""
        old = self._bar_cache.get(bar_id)
        Lcd.setTextSize(1)
        for i, cell in enumerate(cells):
            if old is None or old[i] != cell:
                Lcd.setTextColor(self._cell_color(cell), self.theme["BG"])
                Lcd.drawString("#", positions[i][0], positions[i][1])
        self._bar_cache[bar_id] = list(cells)

    def _paint_line(self, bar_id, cells, y, cell_w=6, x0=0):
        """A horizontal bar: a fresh one is drawn in runs of one colour, later only what changed."""
        old = self._bar_cache.get(bar_id)
        if old is not None and len(old) == len(cells):
            self._paint_bar(bar_id, cells, [(x0 + cell_w * i, y) for i in range(len(cells))])
            return
        Lcd.setTextSize(1)
        i = 0
        while i < len(cells):
            j = i
            while j < len(cells) and cells[j] == cells[i]:
                j += 1
            Lcd.setTextColor(self._cell_color(cells[i]), self.theme["BG"])
            Lcd.drawString("#" * (j - i), x0 + cell_w * i, y)
            i = j
        self._bar_cache[bar_id] = list(cells)

    def draw_bars_clock(self):
        """The clock's bars.  Vertical, at both sides (BARS_CLOCK): battery on the left, focus progress on the right, as
        tall as the screen the clock draws on (16 cells on the Cardputer, 30 on the watch's full panel).  Horizontal, in
        their first and last rows and between them (BARS_TOP, BARS_BOTTOM): the hourglass / the hour at the top, the
        quarter hour at the bottom."""
        if self.bars is None:
            return
        x, y = cfg.get("BARS_OFFSET_X"), cfg.get("BARS_OFFSET_Y")
        w, h = Lcd.screen_size()
        n = h // 8 if h > SCREEN_H else _V_CELLS
        sides = cfg.get("BARS_CLOCK")
        if sides:
            self._paint_bar("L", self.bars.battery_cells(n, from_top=True), [(x, y + 8 * i) for i in range(n)])
            self._paint_bar("R", self.bars.focus_cells(n, vertical=True), [(w - 6 - x, y + 8 * i) for i in range(n)])
        Lcd.setTextSize(1)
        cell = max(1, _text_width("#"))
        margin = x + 6 if sides else 0                  # clear of the side bars
        cells = max(1, (w - 2 * margin) // cell)
        x0 = margin + (w - 2 * margin - cells * cell) // 2
        self._charging_mark((x + 8) if sides else 2, y + 10)
        top, bottom = self.bars.top_cells(cells), self.bars.bottom_cells(cells)
        if top is not None:
            self._paint_line("HT", top, y, cell, x0)
        if bottom is not None:
            self._paint_line("HB", bottom, y + 8 * (n - 1), cell, x0)
        self._bars_kind = "clock"

    def _charging_mark(self, x, y):
        """The lightning by the battery bar while it charges; drawn / wiped only when that changes."""
        on = self.bars.charging()
        if self._bar_cache.get("CHG", False) == on:
            return
        self._bar_cache["CHG"] = on
        if not on:
            Lcd.fillRect(x, y, 5, 8, self.theme["BG"])
            return
        for row, (a, b) in enumerate(_BOLT):
            Lcd.fillRect(x + a, y + row, b - a + 1, 1, self.theme["WARNING"])

    def _draw_menu_bars(self):
        Lcd.setTextSize(1)
        n, cell_w, x0 = _line_layout()
        self._paint_line("T", self.bars.battery_cells(n), 0, cell_w, x0)
        self._paint_line("B", self.bars.focus_cells(n), 24, cell_w, x0)
        self._bars_kind = "menu"

    def forget_bars(self):
        """A new screen is about to be drawn: until it draws bars itself, there are none to refresh."""
        self._bars_kind = None

    def refresh_bars(self):
        """Bring the bars of the screen on display up to date without redrawing the screen."""
        if self.bars is None:
            return
        if self._bars_kind == "clock":
            self.draw_bars_clock()
        elif self._bars_kind == "menu":
            self._draw_menu_bars()

    def _draw_centered_string(self, text: str, y: int, size: int, offset_x: int = 0, offset_y: int = 0):
        Lcd.setTextSize(size)
        screen_width = SCREEN_W
        text_width = len(text) * 6 * size
        x = max(0, (screen_width - text_width) // 2) + offset_x
        Lcd.drawString(text, x, y + offset_y)

    def _draw_segment_digit(self, x, y, digit, w=24, h=48, thickness=5, color=0xFFA500):
        segments = {
            '0': (1,1,1,0,1,1,1), '1': (0,0,1,0,0,1,0), '2': (1,0,1,1,1,0,1),
            '3': (1,0,1,1,0,1,1), '4': (0,1,1,1,0,1,0), '5': (1,1,0,1,0,1,1),
            '6': (1,1,0,1,1,1,1), '7': (1,0,1,0,0,1,0), '8': (1,1,1,1,1,1,1),
            '9': (1,1,1,1,0,1,1)
        }

        if digit == ':':
            Lcd.fillRect(x + w//2 - 2, y + h//3, 5, 5, color)
            Lcd.fillRect(x + w//2 - 2, y + (2*h)//3, 5, 5, color)
            return

        seg = segments.get(str(digit), (0,0,0,0,0,0,0))
        t = thickness
        hw = w
        hh = h // 2

        if seg[0]: Lcd.fillRect(x, y, hw, t, color)
        if seg[1]: Lcd.fillRect(x, y, t, hh, color)
        if seg[2]: Lcd.fillRect(x + hw - t, y, t, hh, color)
        if seg[3]: Lcd.fillRect(x, y + hh - t//2, hw, t, color)
        if seg[4]: Lcd.fillRect(x, y + hh, t, hh, color)
        if seg[5]: Lcd.fillRect(x + hw - t, y + hh, t, hh, color)
        if seg[6]: Lcd.fillRect(x, y + h - t, hw, t, color)

    def draw_vector_clock(self, time_str, base_y=32, color=0xFFA500, offset_x=0, offset_y=0,
                          digit_w=26, digit_h=50, spacing=8, colon_w=14, thickness=5):
        total_w = (4 * digit_w) + (3 * spacing) + colon_w
        start_x = ((SCREEN_W - total_w) // 2) + offset_x
        if time_str[:1] == "1":
            # a '1' is only its two right-hand segments: the empty left of its cell makes 10:00 - 19:59 look shifted
            # to the right.  Half of that empty part, (digit_w - thickness) // 2, centres what is drawn (10 px here)
            start_x += cfg.get("CLOCK_ONE_OFFSET_X")
        y = base_y + offset_y

        curr_x = start_x
        for char in time_str:
            if char == ':':
                self._draw_segment_digit(curr_x, y, ':', w=colon_w, h=digit_h, color=color)
                curr_x += colon_w + spacing
            else:
                self._draw_segment_digit(curr_x, y, char, w=digit_w, h=digit_h, thickness=thickness, color=color)
                curr_x += digit_w + spacing

    def render_clock(self, date_str="26-09-2026", time_str="12:00"):
        self.clear()
        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])

        self._draw_centered_string(
            date_str, y=12, size=self.fonts["CLOCK_DATE"],
            offset_x=cfg.get("CLOCK_DATE_OFFSET_X"), offset_y=cfg.get("CLOCK_DATE_OFFSET_Y")
        )

        self.draw_vector_clock(
            time_str, base_y=32, color=self.theme["FG"],
            offset_x=cfg.get("CLOCK_TIME_OFFSET_X"), offset_y=cfg.get("CLOCK_TIME_OFFSET_Y")
        )

        self._draw_centered_string(
            cfg.get("CLOCK_FOOTER_TEXT"), y=98, size=self.fonts["CLOCK_FOOTER"],
            offset_x=cfg.get("CLOCK_FOOTER_OFFSET_X"), offset_y=cfg.get("CLOCK_FOOTER_OFFSET_Y")
        )

    def render_clock_tall(self, date_str, time_str, weekday, status):
        """The clock on a tall screen (the watch's 240 x 240): the date with the weekday, big digits, the footer text,
        a line of status (focus today, battery) - the same settings (colours, offsets, footer) as render_clock."""
        self.clear()
        w, h = Lcd.screen_size()
        fg = self.theme["FG"]
        Lcd.setTextColor(fg, self.theme["BG"])
        self._draw_centered_string(weekday + " " + date_str, y=h * 8 // 100, size=2,
                                   offset_x=cfg.get("CLOCK_DATE_OFFSET_X"), offset_y=cfg.get("CLOCK_DATE_OFFSET_Y"))
        digit_h = h * 40 // 100                                   # 96 px on the watch
        self.draw_vector_clock(time_str, base_y=h * 22 // 100, color=fg,
                               offset_x=cfg.get("CLOCK_TIME_OFFSET_X"), offset_y=cfg.get("CLOCK_TIME_OFFSET_Y"),
                               digit_w=digit_h * 42 // 100, digit_h=digit_h, spacing=digit_h // 10,
                               colon_w=digit_h // 6, thickness=max(5, digit_h // 11))
        footer = cfg.get("CLOCK_FOOTER_TEXT")            # the device's motto: deliberately not translated
        size = 2 if 12 * len(footer) <= w - 24 else 1
        self._draw_centered_string(footer, y=h * 70 // 100, size=size,
                                   offset_x=cfg.get("CLOCK_FOOTER_OFFSET_X"), offset_y=cfg.get("CLOCK_FOOTER_OFFSET_Y"))
        if status:                                      # (text, colour) pairs, each in the colour of its bar
            gap = 3
            x = max(0, (w - 6 * (sum(len(t) for t, _c in status) + gap * (len(status) - 1))) // 2)
            for text, color in status:
                Lcd.setTextColor(self._cell_color(color), self.theme["BG"])
                Lcd.setTextSize(1)
                Lcd.drawString(text, x, h * 87 // 100)
                x += 6 * (len(text) + gap)

    def _band(self, y, h):
        """Blank one band of the screen right before it is drawn again.  A list is painted band by band, top to
        bottom, instead of after a clear() of the whole screen: on a display drawn directly (the Cardputer's M5.Lcd -
        the watch draws into a frame buffer) a full clear shows as a black flash while the text comes back, each
        letter of the .vlw font drawn one by one.  The bands cover the whole screen, so nothing of what was there
        before (another screen, a warning over the list) is left."""
        Lcd.fillRect(0, y, SCREEN_W, h, self.theme["BG"])

    def _menu_row(self, y, text, selected):
        self._band(y - 2, 15)
        Lcd.setTextColor(self.theme["ACCENT" if selected else "FG"], self.theme["BG"])
        Lcd.drawString(("> " if selected else "  ") + text[:36], 5, y)   # "> " + 36 characters: the screen's width

    def _menu_bottom(self, y, selected_index, total_items):
        self._band(y - 2, SCREEN_H - (y - 2))                   # under the rows, to the bottom
        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
        pos_info = f"[{selected_index + 1}/{total_items}]"
        Lcd.drawString(pos_info, 236 - 6 * len(pos_info), 124)          # where we are in the list, bottom right

    def render_menu(self, title, items, selected_index, scroll_offset, max_visible=5):
        """A list with a title.  When only the selection moved since the last call (the same rows, scrolled the same,
        nothing drawn over them since: see forget_list), only the row it left, the row it came to and the [n/m]
        counter are painted again - not the whole screen."""
        t = self.theme
        visible = tuple(items[scroll_offset : scroll_offset + max_visible])
        what = (title, visible, len(items), scroll_offset, self.fonts["MENU_ITEM"], t["FG"], t["BG"], t["ACCENT"],
                self.bars is not None and cfg.get("BARS_MENU"))
        last, self._list = self._list, (what, selected_index)
        if last is not None and last[0] == what:
            Lcd.setTextSize(self.fonts["MENU_ITEM"])
            for index in (last[1], selected_index) if last[1] != selected_index else ():
                row = index - scroll_offset
                if 0 <= row < len(visible):
                    self._menu_row(40 + 15 * row, visible[row], index == selected_index)
            self._menu_bottom(40 + 15 * len(visible), selected_index, len(items))
            if what[-1]:
                self._draw_menu_bars()                     # only the '#' cells that changed
            return
        self._bar_cache = {}                               # as clear() would: the bars are drawn anew below
        self._bars_kind = None
        self._band(0, 38)                                  # the header: '#' lines and the title
        Lcd.setTextSize(self.fonts["MENU_ITEM"])
        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])

        title = title[:34]
        title_x = max(0, (_SCREEN_W - _text_width(title)) // 2)          # centred in pixels, whatever the font

        if self.bars is not None and cfg.get("BARS_MENU"):
            Lcd.drawString(title, title_x, 12)
            self._draw_menu_bars()                       # the two '#' lines show battery and focus
            Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
        else:
            n, cell_w, x0 = _line_layout()               # '#' lines as wide as the screen
            line = "#" * n
            Lcd.drawString(line, x0, 0)
            Lcd.drawString(title, title_x, 12)
            Lcd.drawString(line, x0, 24)

        for row, item in enumerate(visible):
            self._menu_row(40 + 15 * row, item, scroll_offset + row == selected_index)
        self._menu_bottom(40 + 15 * len(visible), selected_index, len(items))

    def render_keypad_mode_indicator(self, keypad=None):
        """Draws the keyboard mode indicator in the top-right corner.

        Reads keypad.display_modifier (set on toggle, cleared after action) and
        keypad.is_text_mode to pick the right label and colour.  Falls back
        gracefully when keypad is None or lacks the attribute.
        """
        if not keypad:
            return

        is_text = getattr(keypad, 'is_text_mode', False)
        if not is_text:
            return

        x = 215
        y = 5

        modifier = getattr(keypad, 'display_modifier', None)

        # Colours are RGB888 like everywhere in M5.Lcd (the earlier RGB565 constants showed up as other colours)
        if modifier == 'FN':
            text = "FN"
            fg_col = self.theme["KEY_FN"]
        elif modifier == 'SHIFT':
            text = "Aa"
            fg_col = self.theme["KEY_SHIFT"]
        elif modifier in ('CTRL', 'OPT', 'ALT'):
            text = modifier[:2]
            fg_col = self.theme["KEY_OPT"]
        else:
            text = "aa"
            fg_col = self.theme["KEY_NORMAL"]

        Lcd.setTextColor(fg_col, self.theme["BG"])
        Lcd.drawString(text, x, y)

    def render_input_prompt(self, prompt, buffer_text, keypad=None, cursor_pos=None):
        self.clear()
        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
        Lcd.setTextSize(self.fonts["MENU_ITEM"])
        
        Lcd.drawString(f"# {prompt[:20]}", 5, 10)

        # the keyboard mode mark in the top right corner
        self.render_keypad_mode_indicator(keypad)

        Lcd.drawRect(5, 28, 230, 78, self.theme["ACCENT"])
        
        if cursor_pos is None:
            cursor_pos = len(buffer_text)
            
        disp_text = buffer_text[:cursor_pos] + "_" + buffer_text[cursor_pos:]
        lines = disp_text.split("\n")
        
        line_y = 32
        for line in lines:
            if line_y > 92:
                break
            for a, b in wrap_line(line, VIEW_WIDTH):
                if line_y > 92:
                    break
                Lcd.drawString(line[a:b], 10, line_y)
                line_y += 14

        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
        Lcd.drawString(_("[CTRL+S] Save | [ESC] Exit"), 5, 112)

    def render_view_item(self, title, content, scroll_offset=0):
        self.clear()
        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
        Lcd.setTextSize(self.fonts["MENU_ITEM"])

        title_disp = title[:24]
        Lcd.drawString(f"== {title_disp} ==", 5, 5)
        Lcd.drawRect(5, 23, 230, 85, self.theme["FG"])
        
        all_lines = view_rows(content)
                
        visible_lines = all_lines[scroll_offset:scroll_offset + 5]
        
        y = 28
        for line in visible_lines:
            Lcd.drawString(line, 10, y)
            y += 14

        fx = cfg.get("VIEW_FOOTER_OFFSET_X")
        fy = cfg.get("VIEW_FOOTER_OFFSET_Y")
        
        parts = ((_("[ESC] Back"), "FG"), (_("[DEL] Delete"), "ERROR"), (_("[ENTER] Edit"), "ACCENT"))
        free = SCREEN_W - 6 * sum(len(text) for text, _k in parts)      # spread over the row, whatever the language
        gap = max(6, free // 2) if free >= 12 else max(0, free // 2)
        x = fx if free >= 12 else 0
        for text, key in parts:
            Lcd.setTextColor(self.theme[key], self.theme["BG"])
            Lcd.drawString(text, x, fy)
            x += 6 * len(text) + gap

    def render_options(self, text):
        self._painted_over()           # over the screen: it is drawn whole again once this is gone
        Lcd.fillRect(20, 40, 200, 45, self.theme["WARNING"])
        Lcd.setTextColor(self.theme["BG"], self.theme["WARNING"])
        Lcd.setTextSize(self.fonts["ALERT"])
        Lcd.drawString(text, 35, 55)
        Lcd.flush()                    # shown at once: the callers pause right after it

    def render_alert(self, text):
        self._painted_over()
        Lcd.fillRect(20, 40, 200, 45, self.theme["BG"])
        Lcd.drawRect(20, 40, 200, 45, self.theme["ERROR"])
        Lcd.setTextColor(self.theme["ERROR"], self.theme["BG"])
        Lcd.setTextSize(self.fonts["ALERT"])
        Lcd.drawString(text, 35, 55)
        Lcd.flush()

    def render_delete_confirm(self, presses_left, name=None):
        """Overlay asking the user to press DEL N more times to confirm deletion.

        Draws a red-bordered modal over the current screen content so the user
        can still see what they are about to delete.

        Parameters
        ----------
        presses_left : int
            How many more DEL presses are needed (counts down: 2, 1).
        name : str, optional
            What is being deleted.  Lists pass it because the modal covers the highlighted
            row; without it the third line just repeats how to cancel.
        """
        self._painted_over()
        Lcd.fillRect(15, 35, 210, 65, self.theme["BG"])
        Lcd.drawRect(15, 35, 210, 65, self.theme["ERROR"])
        Lcd.setTextColor(self.theme["ERROR"], self.theme["BG"])
        Lcd.setTextSize(self.fonts["ALERT"])
        Lcd.drawString(_("!! DELETE !!  Press DEL:"), 20, 42)
        remaining_str = _("   %dx more  (ESC = cancel)") % presses_left
        Lcd.drawString(remaining_str, 20, 60)
        Lcd.drawString(name[:26] if name else _("ESC to cancel"), 20, 78)

    def draw_focus_indicator(self, state):
        """Small dot in the top-right corner while the focus timer is counting (the accent colour), nothing otherwise.

        Paused shows no dot: the timer has no "stopped" once started (OPT only pauses it), so a dot for a pause stayed
        on for the rest of the day.  Drawn after every full render (which clears the screen), so it never needs erasing.
        """
        if state != "running":
            return
        Lcd.fillCircle(236, 2, 2, self.theme["ACCENT"])     # in the very corner: clear of the status texts at y = 5
