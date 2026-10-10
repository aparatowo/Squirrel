import time
from boot_log import log
from gfx import Lcd
from screens.base_screen import BaseScreen
from appconfig import cfg
from menu_tree import MENUS, COLLECTIONS, PARENTS
from features import has
from ui.touch import has_touch, mm, MIN_TARGET_MM

# A touch screen (the watch): rows a finger can hit, on the whole panel; a tap on a row opens it, a tap on the title
# goes back, a long press ticks a To-Do.  The Cardputer's view is untouched.
_T_HEADER = 30
_T_ROW = max(mm(MIN_TARGET_MM), 24)
# what "+ [New Item]" of a file list needs; without it the row is not shown at all
_ADD_NEEDS = {"TODO": "text_edit", "NOTES": "text_edit", "MIND": "text_edit", "RECORDS": "voice_notes"}

# DEL presses needed after the warning appears (same as in the note viewer and the player)
DELETE_CONFIRM_PRESSES = 3

class MenuScreen(BaseScreen):
    quick_record_from = True        # G0 may start the quick recorder from here

    @property
    def modifiers_as_keys(self):
        """In the To-Do list OPT is a key: it ticks the To-Do as done."""
        return self.current_menu == "TODO"

    def __init__(self, app):
        super().__init__(app)
        self.current_menu = "MAIN"
        self.selected_index = 0
        self.scroll_offset = 0
        self._touch = has_touch()
        self.max_visible = 5
        if self._touch:
            from gfx import PANEL_H
            self.max_visible = max(1, (PANEL_H - _T_HEADER) // _T_ROW)
        self._remember = {}             # menu id -> (selected_index, scroll_offset, label) as the user left it
        self._items_cache = None        # file lists are cached per visit
        self._items_cache_menu = None
        self._delete_confirm = None     # None = no warning, int = DEL presses still needed
        self._delete_target = None      # (absolute path, label) of the file being deleted

    def on_enter(self, menu_name=None, fresh=False, **kwargs):
        # Files may have been added, edited or deleted while another screen was active.
        self._items_cache = None
        if menu_name == "TODO":
            try:
                self.app.todo_editor.purge()          # done To-Dos older than a week go
            except Exception as e:
                log(f"[TODO] clean-up failed: {e}")
        self._delete_confirm = None      # a warning never survives leaving the screen
        self._delete_target = None
        if fresh:
            # Entered anew (from the clock): every menu starts at its first row again.
            self._remember = {}
        if menu_name:
            # Coming back from a screen: land on the entry we left from.
            self._open(menu_name, restore=not fresh)

    @property
    def full_height(self):
        return self._touch

    def _first(self):
        """The first row that can be chosen: 1 in a file list whose "+ [New Item]" the device cannot do (no editor)."""
        need = _ADD_NEEDS.get(self.current_menu)
        return 1 if need is not None and not has(need) else 0

    def return_target(self):
        """Where the quick recorder should come back to: this very menu, on the same row."""
        self._remember_position()
        return ("MENU", {"menu_name": self.current_menu})

    # Position memory: going BACK to a menu (ESC / LEFT from a submenu, or a screen that returns here) lands on the
    # row the user left it from; going INTO a menu starts at its first row.  Every menu and file list works the same
    # way, so the whole path back is remembered (a note -> Text Notes on that note -> Notes on "Text Notes" ...).
    # A file list is matched by the row's text first, because files may have been added or deleted meanwhile.

    def _open(self, menu, restore):
        self.current_menu = menu
        self.selected_index, self.scroll_offset = 0, 0
        saved = self._remember.get(menu) if restore else None
        if saved is not None:
            index, self.scroll_offset, label = saved
            items = self._get_current_items()
            if items[index:index + 1] != [label] and label in items:
                index = items.index(label)                # the same file, moved by an added / removed one
            self.selected_index = index
            self._clamp_selection()
        if self.selected_index < self._first():
            self.selected_index = self.scroll_offset = self._first()
        apply = getattr(self.app, "_apply_screen_input_mode", None)        # OPT must arrive as a key in the To-Do list only
        if apply is not None and getattr(self.app, "active_screen", None) is self:
            apply()

    def _remember_position(self):
        items = self._get_current_items()
        label = items[self.selected_index] if self.selected_index < len(items) else None
        self._remember[self.current_menu] = (self.selected_index, self.scroll_offset, label)

    def _go_back(self):
        parent = PARENTS.get(self.current_menu)
        if parent is None:
            self.app.set_screen("CLOCK")
        else:
            self._open(parent, restore=True)

    def _get_current_items(self):
        if self.current_menu in MENUS:
            entries = MENUS[self.current_menu][1]
            return ["%d. %s" % (i + 1, self._label(entry)) for i, entry in enumerate(entries)]

        if self._items_cache is not None and self._items_cache_menu == self.current_menu:
            return self._items_cache

        items = ["+ [New Item]"]
        extension = COLLECTIONS[self.current_menu][1]
        items.extend(self.app.storage.list_items(self.current_menu, extension=extension))
        if self.current_menu == "TODO":
            items = self.app.todo_editor.decorate(items)               # [ ] / [X] in front of each To-Do
        self._items_cache = items
        self._items_cache_menu = self.current_menu
        return items

    def _label(self, entry):
        """The label of a menu entry, with its summary when it has one (the 4th item, see menu_tree.py)."""
        if len(entry) < 4:
            return entry[0]
        return "%-7s %s" % (entry[0], self._summary(entry[3]))

    @staticmethod
    def _summary(what):
        """'quiet:<channel>': the days of that channel's quiet hours ("M T W T F - -"), or "off"."""
        if what.startswith("quiet:"):
            from quiet_hours import keys
            from appconfig import days_shown
            k_from, k_to, k_days = keys(what[6:])
            days = cfg.get(k_days)
            return "off" if cfg.get(k_from) == cfg.get(k_to) or not days else days_shown(days)
        return ""

    def _clamp_selection(self):
        """Keep the highlighted row and the scroll window valid after the list got shorter."""
        total = len(self._get_current_items())
        self.selected_index = max(0, min(self.selected_index, total - 1))
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.selected_index - self.max_visible + 1
        self.scroll_offset = max(0, min(self.scroll_offset, max(0, total - self.max_visible)))

    def _begin_delete(self, items):
        """DEL on a file row opens the warning; on '+ [New Item]' or in a tree menu it does nothing."""
        if self.current_menu not in COLLECTIONS or self.selected_index == 0:
            return
        extension = COLLECTIONS[self.current_menu][1]
        path = self.app.storage._get_filepath_by_index(self.current_menu, self.selected_index - 1, extension)
        if path is None:
            return
        label = items[self.selected_index]
        self._delete_target = (path, label.split(". ", 1)[-1])      # drop the list number
        self._delete_confirm = DELETE_CONFIRM_PRESSES

    def _handle_delete_confirm(self, action):
        """Input while the warning is up: ESC cancels, DEL counts down, everything else is ignored."""
        if action == 'ESC':
            self._delete_confirm = None
            self._delete_target = None
        elif action == 'DEL':
            self._delete_confirm -= 1
            if self._delete_confirm <= 0:
                self._delete_now()

    def _delete_now(self):
        path = self._delete_target[0]
        ok = self.app.storage.delete_path(path)
        self._delete_confirm = None
        self._delete_target = None
        self._items_cache = None                  # the folder changed: read it again
        self.app.renderer.render_alert("Deleted!" if ok else "Delete failed!")
        time.sleep(0.6)
        self._clamp_selection()

    def handle_input(self, action):
        if self._delete_confirm is not None:
            self._handle_delete_confirm(action)
            return

        items = self._get_current_items()
        total_items = len(items)

        first = self._first()
        if self._touch and action in ('ENTER', 'OPT') and not self._touch_select(items):
            return
        if first and total_items <= first:
            if action in ('LEFT', 'ESC'):
                self._go_back()
            return                                          # an empty list the device cannot add to

        if action == 'UP':
            self.selected_index = first + (self.selected_index - 1 - first) % (total_items - first)
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            elif self.selected_index == total_items - 1:
                self.scroll_offset = max(first, total_items - self.max_visible)

        elif action == 'DOWN':
            self.selected_index = first + (self.selected_index + 1 - first) % (total_items - first)
            if self.selected_index >= self.scroll_offset + self.max_visible:
                self.scroll_offset = self.selected_index - self.max_visible + 1
            elif self.selected_index == first:
                self.scroll_offset = first

        elif action == 'DEL':
            self._begin_delete(items)

        elif action == 'OPT' and self.current_menu == "TODO" and self.selected_index > 0:
            self._toggle_todo()

        elif action in ('LEFT', 'ESC'):
            self._go_back()

        elif action in ('RIGHT', 'ENTER'):
            if self.current_menu in MENUS:
                self._activate_entry(MENUS[self.current_menu][1][self.selected_index])
            elif self.selected_index == 0:
                self._remember_position()
                self.handle_add_new_item()
            else:
                self._open_collection_item(items)

    def _touch_select(self, items):
        """A tap / long press: on the title = back, on a row = choose it (then ENTER / OPT acts on it).  False when
        it hit nothing."""
        xy = getattr(self.app.keypad, "tap_xy", None)
        if xy is None:
            return False
        if xy[1] < _T_HEADER:
            self._go_back()
            return False
        index = self.scroll_offset + (xy[1] - _T_HEADER) // _T_ROW
        if index >= len(items) or index < self._first():
            return False
        self.selected_index = index
        return True

    def _toggle_todo(self):
        from scheduler import valid_now, day_key
        t = valid_now()
        if t is None:
            self.app.renderer.render_alert("Set time first!")        # a done date needs a real clock
            time.sleep(0.8)
            return
        self.app.todo_editor.toggle_done(self.selected_index - 1, day_key(t))
        self._items_cache = None                                      # redraw with the new mark

    def _activate_entry(self, entry):
        kind, arg = entry[1], entry[2]
        self._remember_position()
        if kind == "menu":
            self._open(arg, restore=False)
        elif kind == "screen":
            if isinstance(arg, tuple):                       # (name, keyword arguments)
                self.app.set_screen(arg[0], **arg[1])
            else:
                self.app.set_screen(arg)
        elif kind == "action":
            self._run_action(arg)
        else:   # "soon"
            self.app.renderer.render_alert("Coming soon")
            time.sleep(0.6)

    def _run_action(self, name):
        if name == "reload_config":
            # Re-read config.txt now (it is also checked in the background every few seconds)
            result = cfg.reload()
            if result is None:
                self.app.renderer.render_alert("No config file")
            else:
                self.app.renderer.render_options("Config: %d changed, %d bad" % result)
            time.sleep(1.2)
        elif name.startswith("buzz:"):
            from hw.buzzer import buzzer
            played = buzzer.play(name[5:])
            self.app.renderer.render_options("Buzzer: " + name[5:] if played else (buzzer.problem or "Silent (recording)"))
            end = time.ticks_add(time.ticks_ms(), 800)
            while buzzer.busy or time.ticks_diff(end, time.ticks_ms()) > 0:     # the main loop waits: keep the signal in time
                buzzer.tick()
                time.sleep_ms(5)
        elif name.startswith("led:"):
            from hw.led import led
            played = led.play(name[4:], "green")
            self.app.renderer.render_options("LED: " + name[4:] if played else led.status())
            end = time.ticks_add(time.ticks_ms(), 800)
            while led.busy or time.ticks_diff(end, time.ticks_ms()) > 0:        # the main loop waits: keep the light in time
                led.tick()
                self.app.dimmer.tick()          # ... and the back-light up: the LED is powered through it
                time.sleep_ms(5)
        elif name == "test_sound":
            played = self.app.audio.beep("notify", force=True)          # a test sounds in the silent hours too
            self.app.renderer.render_options("Signal played" if played else "Muted (sound off / recording)")
            time.sleep(0.8)
        elif name == "test_notification":
            from notifier import Notification
            self.app.notifier.post(Notification(
                "This is a test. OPT = done, DEL = cancel", title="Test notification", timeout_s=15,
                on_done=lambda: log("[NOTIFY] test: done"),
                on_cancel=lambda: log("[NOTIFY] test: cancelled"),
                on_timeout=lambda: log("[NOTIFY] test: timed out")))
        elif name == "sync_rtc":
            # Read the time from a DS1302 that is plugged in right now
            self.app.renderer.render_options("Connecting RTC...")
            ok, msg = self.app.rtc.sync_from_hardware()
            if ok:
                self.app.renderer.render_options(msg[:32])
            else:
                self.app.renderer.render_alert("No RTC found!")
            time.sleep(1.5)

    def _open_collection_item(self, items):
        file_index = self.selected_index - 1
        item_name = items[self.selected_index]
        if self.current_menu == "TODO":
            item_name = item_name.replace("[ ] ", "", 1).replace("[X] ", "", 1)      # the viewer's title has no mark
        self._remember_position()
        if self.current_menu == "RECORDS":
            # Build full filepath for playback
            filepath = self.app.storage._get_filepath_by_index(
                "RECORDS", file_index, extension=".wav"
            )
            self.app.set_screen("PLAYBACK", filepath=filepath, title=item_name)
        else:
            content = self.app.storage.read_item(self.current_menu, file_index)
            self.app.set_screen("VIEWER", title=item_name, content=content or "(Empty file)",
                                file_index=file_index, menu_name=self.current_menu)

    def handle_add_new_item(self):
        # A new note or TODO is typed in the same editor as an existing one is edited (cursor keys, wrapping at
        # the full width, a character counter).  Its first line is the title; saving returns to this list.
        if self.current_menu in ("TODO", "NOTES"):
            self.app.set_screen("NOTE_EDITOR", menu_name=self.current_menu, file_index=None)

        elif self.current_menu == "MIND":
            self.app.set_screen("MIND_DUMP", return_to=("MENU", {"menu_name": "MIND"}))

        elif self.current_menu == "RECORDS":
            self.app.set_screen("RECORD")

    def render(self, renderer):
        if self.current_menu in MENUS:
            title = MENUS[self.current_menu][0]
        else:
            title = COLLECTIONS[self.current_menu][0]
        items = self._get_current_items()
        if self._touch:
            return self._render_touch(renderer, title, items)
        renderer.render_menu(title, items, self.selected_index, self.scroll_offset, self.max_visible)
        if self.current_menu == "TODO" and self._delete_confirm is None:
            Lcd.setTextColor(renderer.theme["ACCENT"], renderer.theme["BG"])
            Lcd.drawString("OPT = done", 5, 124)
        if self._delete_confirm is not None:
            renderer.render_delete_confirm(self._delete_confirm, self._delete_target[1])

    def _render_touch(self, renderer, title, items):
        """Rows of ~6 mm on the whole panel, size-2 text; the title (tap = back) with the position in the list."""
        renderer.clear()
        theme = renderer.theme
        w, h = Lcd.screen_size()
        first = self._first()
        shown = len(items) - first
        Lcd.setTextSize(2)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        Lcd.drawString("<", 4, 7)
        Lcd.drawString(title[:14], 4 + 18, 7)
        if shown > self.max_visible:
            pos = "%d/%d" % (self.selected_index - first + 1, shown)
            Lcd.setTextSize(1)
            Lcd.drawString(pos, w - 4 - 6 * len(pos), 11)
        Lcd.drawLine(0, _T_HEADER - 2, w - 1, _T_HEADER - 2, theme["FG"])
        if shown <= 0:
            Lcd.setTextSize(2)
            Lcd.drawString("(empty)", 4, _T_HEADER + (_T_ROW - 16) // 2)
            return
        if self.scroll_offset < first:
            self.scroll_offset = first
        for row in range(self.max_visible):
            i = self.scroll_offset + row
            if i >= len(items):
                break
            y = _T_HEADER + row * _T_ROW
            text = items[i]
            if self.current_menu in MENUS and ". " in text:
                text = text.split(". ", 1)[1]                 # no numbers: the row is tapped, not typed
            selected = i == self.selected_index
            if selected:
                Lcd.fillRect(0, y + 1, w, _T_ROW - 2, theme["PANEL_BG"])
            Lcd.setTextColor(theme["ACCENT"] if selected else theme["FG"], theme["PANEL_BG"] if selected else theme["BG"])
            Lcd.setTextSize(2)
            Lcd.drawString(text[:(w - 8) // 12], 4, y + (_T_ROW - 16) // 2)
        if self.current_menu == "TODO":
            Lcd.setTextSize(1)
            Lcd.setTextColor(theme["ACCENT"], theme["BG"])
            Lcd.drawString("hold = done", w - 4 - 66, h - 10)
