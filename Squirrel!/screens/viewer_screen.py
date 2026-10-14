# screens/viewer_screen.py
#
# On a touch screen (the watch): the whole panel, the title as a header (a tap on it = back, so does a swipe right),
# the text in size 2 wrapped at spaces; swipes up / down scroll by a page.  No editing and no deleting there.
from screens.base_screen import BaseScreen
from features import has
from ui.touch import has_touch, TouchList
from i18n import _

# Number of DEL presses required to confirm deletion
DELETE_CONFIRM_PRESSES = 3


class ViewerScreen(BaseScreen):
    """Read-only viewer for notes and TODOs with FN-layer navigation.

    Key map (normal mode):
        ESC / FN+LEFT   -> back to menu
        FN+UP / FN+DOWN -> scroll content
        FN+LEFT         -> previous file
        FN+RIGHT        -> next file
        ENTER           -> open in editor
        DEL (FN+BS)     -> start delete confirmation flow

    Delete confirmation:
        DEL pressed DELETE_CONFIRM_PRESSES times in a row -> delete & go back
        ESC at any point                                   -> cancel, view restored
    """

    def __init__(self, app):
        super().__init__(app)
        self.title = ""
        self.content = ""
        self.file_index = None
        self.menu_name = ""
        self.scroll_offset = 0
        # Delete confirmation state: None = not active, int = presses remaining
        self._delete_confirm = None
        self._touch = has_touch()
        self._list = TouchList() if self._touch else None

    @property
    def full_height(self):
        return self._touch

    def _touch_rows(self):
        """The text wrapped for the touch layout: size 2, a row as wide as the panel."""
        from gfx import Lcd
        from text_layout import wrap_line
        cols = (Lcd.screen_size()[0] - 8) // 12
        lines = self.content.split("\n")
        if lines and lines[0].strip() == self.title.strip():
            lines = lines[1:]                          # the title is the header already
        rows = []
        for line in lines:
            for a, b in wrap_line(line, cols):
                rows.append(line[a:b].rstrip())
        return rows

    def _touch_page(self):
        from gfx import Lcd
        return max(1, (Lcd.screen_size()[1] - TouchList.HEADER - 6) // 20)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self, title="", content="", file_index=None, menu_name="", **kwargs):
        self.title = title
        self.content = content
        self.file_index = file_index
        self.menu_name = menu_name
        self.scroll_offset = 0
        self._delete_confirm = None

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _name(self):
        """The title without its list number ("1. Ideas" -> "Ideas"), for the delete warning."""
        head, sep, rest = self.title.partition(". ")
        return (rest if sep and head.isdigit() else self.title) or None

    def _total_lines(self):
        """Total wrapped-line count for scroll boundary checking."""
        from ui_renderer import view_rows
        return len(view_rows(self.content))

    def _load_file(self, index):
        """Load a file by index from the current collection."""
        content = self.app.storage.read_item(self.menu_name, index)
        items = self.app.storage.list_items(self.menu_name)
        # list_items returns ["+ [New item]", "1. Title", ...], file names start at [1]
        title = items[index + 1] if (index + 1) < len(items) else "???"
        self.title = title
        self.content = content or _("(Empty)")
        self.file_index = index
        self.scroll_offset = 0
        self._delete_confirm = None

    def _navigate(self, delta):
        """Move to adjacent file (+1 = next, -1 = prev)."""
        total = self.app.storage.count_items(self.menu_name)
        if total == 0:
            return
        new_index = (self.file_index + delta) % total
        self._load_file(new_index)

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def handle_input(self, action):
        if self._touch:
            if action in ('ESC', 'LEFT'):
                self.app.set_screen("MENU", menu_name=self.menu_name)
            elif action in ('ENTER', 'OPT'):
                if self._list.hit(getattr(self.app.keypad, "tap_xy", None), 0, 0) == "back":
                    self.app.set_screen("MENU", menu_name=self.menu_name)
            elif action in ('UP', 'DOWN'):
                page, total = self._touch_page(), len(self._touch_rows())
                step = page - 1 if action == 'DOWN' else 1 - page
                self.scroll_offset = max(0, min(self.scroll_offset + step, max(0, total - page)))
            return
        # --- Delete confirmation flow ---
        if self._delete_confirm is not None:
            self._handle_delete_confirm(action)
            return

        # --- Normal viewer actions ---
        if action in ('ESC', 'LEFT'):
            self.app.set_screen("MENU", menu_name=self.menu_name)

        elif action == 'RIGHT':
            self._navigate(+1)

        elif action == 'UP':
            if self.scroll_offset > 0:
                self.scroll_offset -= 1

        elif action == 'DOWN':
            max_scroll = max(0, self._total_lines() - 5)
            if self.scroll_offset < max_scroll:
                self.scroll_offset += 1

        elif action == 'ENTER' and has("text_edit"):
            # Open in editor — pass title (first line) and full content (only where there is an editor: not on the watch)
            self.app.set_screen(
                "NOTE_EDITOR",
                title=self.title,
                body=self.content,
                file_index=self.file_index,
                menu_name=self.menu_name,
            )

        elif action == 'DEL':
            # Start delete confirmation: user must press DEL N more times
            self._delete_confirm = DELETE_CONFIRM_PRESSES
            # Render the first confirmation overlay immediately
            self.app.renderer.render_delete_confirm(self._delete_confirm, self._name())

    def _handle_delete_confirm(self, action):
        """Process input while the delete confirmation overlay is active."""
        if action == 'ESC':
            # Cancel — dismiss overlay and redraw normal view
            self._delete_confirm = None

        elif action == 'DEL':
            self._delete_confirm -= 1
            if self._delete_confirm <= 0:
                # Confirmed — delete and go back to menu
                self.app.storage.delete_item(self.menu_name, self.file_index)
                self._delete_confirm = None
                self.app.renderer.render_alert(_("Deleted!"))
                import time
                time.sleep(0.6)
                self.app.set_screen("MENU", menu_name=self.menu_name)
            else:
                # Still counting down — redraw overlay with updated count
                self.app.renderer.render_delete_confirm(self._delete_confirm, self._name())
        # Any other key is ignored while confirm is active

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, renderer):
        if self._touch:
            return self._render_touch(renderer)
        renderer.render_view_item(self.title, self.content, self.scroll_offset)
        # If the confirm overlay is active, draw it on top of the view
        if self._delete_confirm is not None:
            renderer.render_delete_confirm(self._delete_confirm, self._name())

    def _render_touch(self, renderer):
        from gfx import Lcd
        theme = renderer.theme
        renderer.clear()
        rows, page = self._touch_rows(), self._touch_page()
        title = self.title.split(". ", 1)[-1]
        pos = "%d/%d" % (self.scroll_offset // page + 1, (len(rows) + page - 1) // page) if len(rows) > page else None
        self._list.draw_header(theme, title, pos)
        Lcd.setTextSize(2)
        Lcd.setTextColor(theme["FG"], theme["BG"])
        y = TouchList.HEADER + 4
        for row in rows[self.scroll_offset:self.scroll_offset + page]:
            Lcd.drawString(row, 4, y)
            y += 20
