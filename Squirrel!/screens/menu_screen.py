import time
from boot_log import log
from gfx import Lcd
from screens.base_screen import BaseScreen
from appconfig import cfg
from menu_tree import MENUS, COLLECTIONS, PARENTS

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
        self.max_visible = 5
        self._remember = {}             # menu id -> (selected_index, scroll_offset)
        self._items_cache = None        # file lists are cached per visit
        self._items_cache_menu = None
        self._delete_confirm = None     # None = no warning, int = DEL presses still needed
        self._delete_target = None      # (absolute path, label) of the file being deleted

    def on_enter(self, menu_name=None, **kwargs):
        # Files may have been added, edited or deleted while another screen was active.
        self._items_cache = None
        if menu_name == "TODO":
            try:
                self.app.todo_editor.purge()          # done To-Dos older than a week go
            except Exception as e:
                log(f"[TODO] clean-up failed: {e}")
        self._delete_confirm = None      # a warning never survives leaving the screen
        self._delete_target = None
        if menu_name:
            # Coming back from a screen: land on the entry we left from.
            self._open(menu_name, restore=True)

    def return_target(self):
        """Where the quick recorder should come back to: this very menu."""
        return ("MENU", {"menu_name": self.current_menu})

    def _open(self, menu, restore):
        self.current_menu = menu
        if restore and menu in MENUS:
            self.selected_index, self.scroll_offset = self._remember.get(menu, (0, 0))
        else:
            self.selected_index, self.scroll_offset = 0, 0
        apply = getattr(self.app, "_apply_screen_input_mode", None)        # OPT must arrive as a key in the To-Do list only
        if apply is not None and getattr(self.app, "active_screen", None) is self:
            apply()

    def _remember_position(self):
        self._remember[self.current_menu] = (self.selected_index, self.scroll_offset)

    def _go_back(self):
        parent = PARENTS.get(self.current_menu)
        if parent is None:
            self.app.set_screen("CLOCK")
        else:
            self._open(parent, restore=True)

    def _get_current_items(self):
        if self.current_menu in MENUS:
            entries = MENUS[self.current_menu][1]
            return ["%d. %s" % (i + 1, entry[0]) for i, entry in enumerate(entries)]

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

        if action == 'UP':
            self.selected_index = (self.selected_index - 1) % total_items
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            elif self.selected_index == total_items - 1:
                self.scroll_offset = max(0, total_items - self.max_visible)

        elif action == 'DOWN':
            self.selected_index = (self.selected_index + 1) % total_items
            if self.selected_index >= self.scroll_offset + self.max_visible:
                self.scroll_offset = self.selected_index - self.max_visible + 1
            elif self.selected_index == 0:
                self.scroll_offset = 0

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
                self.handle_add_new_item()
            else:
                self._open_collection_item(items)

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
        label, kind, arg = entry
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
        elif name == "test_sound":
            played = self.app.audio.beep("notify")
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
        renderer.render_menu(title, items, self.selected_index, self.scroll_offset, self.max_visible)
        if self.current_menu == "TODO" and self._delete_confirm is None:
            Lcd.setTextColor(renderer.theme["ACCENT"], renderer.theme["BG"])
            Lcd.drawString("OPT = done", 5, 124)
        if self._delete_confirm is not None:
            renderer.render_delete_confirm(self._delete_confirm, self._delete_target[1])
