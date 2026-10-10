# screens/viewer_screen.py
from screens.base_screen import BaseScreen
from features import has

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

    def _total_lines(self):
        """Total wrapped-line count for scroll boundary checking."""
        lines = []
        for line in self.content.split("\n"):
            chunks = max(1, (len(line) + 25) // 26)
            lines.extend([None] * chunks)
        return len(lines)

    def _load_file(self, index):
        """Load a file by index from the current collection."""
        content = self.app.storage.read_item(self.menu_name, index)
        items = self.app.storage.list_items(self.menu_name)
        # list_items returns ["+ [New Item]", "1. Title", ...], file names start at [1]
        title = items[index + 1] if (index + 1) < len(items) else "???"
        self.title = title
        self.content = content or "(Empty)"
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
            self.app.renderer.render_delete_confirm(self._delete_confirm)

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
                self.app.renderer.render_alert("Deleted!")
                import time
                time.sleep(0.6)
                self.app.set_screen("MENU", menu_name=self.menu_name)
            else:
                # Still counting down — redraw overlay with updated count
                self.app.renderer.render_delete_confirm(self._delete_confirm)
        # Any other key is ignored while confirm is active

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, renderer):
        renderer.render_view_item(self.title, self.content, self.scroll_offset)
        # If the confirm overlay is active, draw it on top of the view
        if self._delete_confirm is not None:
            renderer.render_delete_confirm(self._delete_confirm)