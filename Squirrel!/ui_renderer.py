import M5
from gfx import Lcd
from nuts import THEME, FONTS_THEME, named_color
from appconfig import cfg

# theme entry -> setting that holds its colour name
_COLOR_SETTINGS = (("BG", "COLOR_BG"), ("FG", "COLOR_FG"), ("ACCENT", "COLOR_ACCENT"),
                   ("WARNING", "COLOR_WARNING"), ("ERROR", "COLOR_ERROR"),
                   ("KEY_SHIFT", "COLOR_KEY_SHIFT"), ("KEY_FN", "COLOR_KEY_FN"), ("KEY_OPT", "COLOR_KEY_OPT"))

_V_CELLS = 16          # '#' characters in a vertical bar (8 px each: 128 px of the 135 px screen)
_SCREEN_W = 240
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
        self._apply_colors()
        cfg.on_change(self._on_setting_changed)

    def _apply_colors(self):
        """Copy the colour settings into the theme dict (in place: screens hold this very dict)."""
        for theme_key, setting in _COLOR_SETTINGS:
            self.theme[theme_key] = named_color(cfg.get(setting))
        normal = cfg.get("COLOR_KEY_NORMAL")          # "text" = the colour of the text itself
        self.theme["KEY_NORMAL"] = self.theme["FG"] if normal == "text" else named_color(normal)

    def _on_setting_changed(self, key, value):
        if key.startswith("COLOR_"):
            self._apply_colors()

    def clear(self):
        Lcd.fillScreen(self.theme["BG"])
        self._bar_cache = {}           # the screen is blank again, so nothing of the bars is on it
        self._bars_kind = None

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
        """Vertical bars at both sides of the clock: battery on the left, focus progress on the right."""
        if self.bars is None or not cfg.get("BARS_CLOCK"):
            return
        x, y = cfg.get("BARS_OFFSET_X"), cfg.get("BARS_OFFSET_Y")
        self._paint_bar("L", self.bars.battery_cells(_V_CELLS, from_top=True), [(x, y + 8 * i) for i in range(_V_CELLS)])
        self._paint_bar("R", self.bars.focus_cells(_V_CELLS), [(234 - x, y + 8 * i) for i in range(_V_CELLS)])
        self._bars_kind = "clock"

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
        screen_width = 240
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

    def draw_vector_clock(self, time_str, base_y=32, color=0xFFA500, offset_x=0, offset_y=0):
        digit_w, digit_h, spacing, colon_w = 26, 50, 8, 14
        total_w = (4 * digit_w) + (3 * spacing) + colon_w
        start_x = ((240 - total_w) // 2) + offset_x
        y = base_y + offset_y

        curr_x = start_x
        for char in time_str:
            if char == ':':
                self._draw_segment_digit(curr_x, y, ':', w=colon_w, h=digit_h, color=color)
                curr_x += colon_w + spacing
            else:
                self._draw_segment_digit(curr_x, y, char, w=digit_w, h=digit_h, thickness=5, color=color)
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

    def render_menu(self, title, items, selected_index, scroll_offset, max_visible=5):
        self.clear()
        Lcd.setTextSize(self.fonts["MENU_ITEM"])
        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])

        total_items = len(items)
        pos_info = f"[{selected_index + 1}/{total_items}]"
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

        y = 40
        visible_items = items[scroll_offset : scroll_offset + max_visible]

        for idx, item in enumerate(visible_items):
            actual_index = scroll_offset + idx
            display_text = item[:32] if len(item) > 32 else item

            if actual_index == selected_index:
                Lcd.setTextColor(self.theme["ACCENT"], self.theme["BG"])
                Lcd.drawString(f"> {display_text}", 5, y)
            else:
                Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
                Lcd.drawString(f"  {display_text}", 5, y)
            
            y += 15

        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
        Lcd.drawString(pos_info, 236 - 6 * len(pos_info), 124)          # where we are in the list, bottom right

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

        # Rysowanie znacznika w prawym górnym rogu
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
            for i in range(0, max(1, len(line)), 26):
                if line_y > 92:
                    break
                chunk = line[i:i+26]
                Lcd.drawString(chunk, 10, line_y)
                line_y += 14

        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
        Lcd.drawString("[CTRL+S] Save | [ESC] Exit", 5, 112)

    def render_view_item(self, title, content, scroll_offset=0):
        self.clear()
        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
        Lcd.setTextSize(self.fonts["MENU_ITEM"])

        title_disp = title[:24]
        Lcd.drawString(f"== {title_disp} ==", 5, 5)
        Lcd.drawRect(5, 23, 230, 85, self.theme["FG"])
        
        all_lines = []
        for line in content.split("\n"):
            for chunk_start in range(0, max(1, len(line)), 26):
                all_lines.append(line[chunk_start:chunk_start+26])
                
        visible_lines = all_lines[scroll_offset:scroll_offset + 5]
        
        y = 28
        for line in visible_lines:
            Lcd.drawString(line, 10, y)
            y += 14

        fx = cfg.get("VIEW_FOOTER_OFFSET_X")
        fy = cfg.get("VIEW_FOOTER_OFFSET_Y")
        
        Lcd.setTextColor(self.theme["FG"], self.theme["BG"])
        Lcd.drawString("[ESC] Back", fx, fy)
        Lcd.setTextColor(self.theme["ERROR"], self.theme["BG"])
        Lcd.drawString("[DEL] Delete", fx + 75, fy)
        Lcd.setTextColor(self.theme["ACCENT"], self.theme["BG"])
        Lcd.drawString("[ENTER] Edit", fx + 158, fy)

    def render_options(self, text):
        Lcd.fillRect(20, 40, 200, 45, self.theme["WARNING"])
        Lcd.setTextColor(self.theme["BG"], self.theme["WARNING"])
        Lcd.setTextSize(self.fonts["ALERT"])
        Lcd.drawString(text, 35, 55)

    def render_alert(self, text):
        Lcd.fillRect(20, 40, 200, 45, self.theme["BG"])
        Lcd.drawRect(20, 40, 200, 45, self.theme["ERROR"])
        Lcd.setTextColor(self.theme["ERROR"], self.theme["BG"])
        Lcd.setTextSize(self.fonts["ALERT"])
        Lcd.drawString(text, 35, 55)

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
        Lcd.fillRect(15, 35, 210, 65, self.theme["BG"])
        Lcd.drawRect(15, 35, 210, 65, self.theme["ERROR"])
        Lcd.setTextColor(self.theme["ERROR"], self.theme["BG"])
        Lcd.setTextSize(self.fonts["ALERT"])
        Lcd.drawString("!! DELETE !!  Press DEL:", 20, 42)
        remaining_str = f"   {presses_left}x more  (ESC = cancel)"
        Lcd.drawString(remaining_str, 20, 60)
        Lcd.drawString(name[:26] if name else "ESC to cancel", 20, 78)

    def draw_focus_indicator(self, state):
        """Small dot in the top-right corner while the focus timer is counting.

        Green = running, yellow = paused, nothing when stopped.  Drawn after every
        full render (which clears the screen), so it never needs erasing.
        """
        if state == "running":
            color = self.theme["ACCENT"]
        elif state == "paused":
            color = self.theme["WARNING"]
        else:
            return
        Lcd.fillCircle(233, 6, 3, color)
