# todo_editor.py - TODO entry handler
#
# A To-Do is a text file in todo/.  "Done" is kept apart from the files, in todo/done.dat ("name,YYYY-MM-DD" lines):
# the text of a To-Do is never touched by ticking it.  A done To-Do is deleted TODO_KEEP_DAYS (7) days after it was
# ticked (purge()), and every tick is counted for the statistics (todos_done, a scheduler.DayCounter).
#
# A line that starts with ">" is an item of a CHECKLIST, ticked on its own (screens/checklist_screen.py) - a shopping
# list, the steps of a task, anything; the other lines are plain text.  An item's mark is a "name#item text,date" line
# of done.dat - the file stays as it was typed - and once every item is ticked the whole To-Do is done (and goes after
# TODO_KEEP_DAYS like any other To-Do).  A To-Do without ">" lines is a plain one, ticked as a whole.
import os
from appconfig import cfg
from boot_log import log
from timeutil import days_from_civil

ITEM_MARK = ">"


def checklist_items(content):
    """The items of a To-Do: its lines (after the title) that start with ">", without the ">"; empty ones left out."""
    out = []
    for line in content.split("\n")[1:]:
        text = line.strip()
        if text.startswith(ITEM_MARK):
            text = text[len(ITEM_MARK):].strip()
            if text:
                out.append(text)
    return out


class TodoEditor:
    def __init__(self, storage_manager, todos_done=None):
        self.storage = storage_manager
        self._counter = todos_done
        self._done_path = f"{storage_manager.base_dir}/todo/done.dat"

    def extract_title(self, text):
        """Extracts title using the first line or MAX_LEN slice."""
        cleaned_text = text.strip()
        if not cleaned_text:
            return "Untitled_Todo"

        # First line check
        first_line = cleaned_text.split("\n")[0].strip()

        # Trim to configured max title length
        if len(first_line) > cfg.get("TODO_TITLE_MAX_LEN"):
            title = first_line[:cfg.get("TODO_TITLE_MAX_LEN")].rstrip()
        else:
            title = first_line

        return title

    def create_todo(self, content):
        """Validates length and saves new TODO item."""
        if len(content) > cfg.get("TODO_MAX_CHARS"):
            print(f"[TODO WARN] Content exceeds max limit of {cfg.get('TODO_MAX_CHARS')} chars. Truncating...")
            content = content[:cfg.get("TODO_MAX_CHARS")]

        title = self.extract_title(content)
        title = self.storage.unique_title("todo", title, cfg.get("TODO_TITLE_MAX_LEN"))    # never overwrite another TODO
        print(f"[TODO ACTION] Creating TODO with title: '{title}'")

        success = self.storage.save_item("todo", title, content)
        if success:
            print("[TODO SUCCESS] Item successfully created.")
        else:
            print("[TODO ERROR] Failed to save TODO item.")
        return success

    # ---------------- done / not done ----------------

    def done_map(self):
        out = {}
        try:
            with open(self._done_path) as f:
                for line in f.read().split("\n"):
                    stem, _sep, date = line.rpartition(",")
                    if stem and len(date) == 10:
                        out[stem] = date
        except OSError:
            pass
        return out

    def _save_map(self, done):
        try:
            with open(self._done_path, "w") as f:
                f.write("".join("%s,%s\n" % (k, done[k]) for k in sorted(done)))
            return True
        except OSError as e:
            log(f"[TODO] cannot save done.dat: {e}")
            return False

    def decorate(self, items):
        """['+ [New item]', '1. Buy milk', ...] -> the same with '[ ]' / '[X]' in front of each To-Do's title;
        a checklist that is not done yet shows how many of its items are ticked ('[2/5]')."""
        done = self.done_map()
        stems = self.storage.stems("todo")
        out = [items[0]] if items else []
        for n, text in enumerate(items[1:]):
            number, sep, title = text.partition(". ")
            stem = stems[n] if n < len(stems) else None
            if stem in done:
                mark = "[X]"
            else:
                state = self.checklist_state(n, done) if stem is not None else []
                mark = "[%d/%d]" % (sum(1 for _t, d in state if d), len(state)) if state else "[ ]"
            out.append("%s%s%s %s" % (number, sep, mark, title))
        return out

    @staticmethod
    def strip_mark(label):
        """'3. [2/5] Lista zakupów' -> '3. Lista zakupów' (the viewer's title has no mark)."""
        number, sep, rest = label.partition(". ")
        if not sep:
            number, rest = "", label
        if rest.startswith("["):
            close = rest.find("] ")
            if close > 0:
                rest = rest[close + 2:]
        return number + sep + rest

    # ---------------- checklists ----------------

    def has_checklist_at(self, index):
        stems = self.storage.stems("todo")
        return 0 <= index < len(stems) and bool(checklist_items(self.storage.read_item("todo", index) or ""))

    def checklist_state(self, index, done=None):
        """[(item text, ticked)] of the To-Do at `index` (0 = first file); [] when it has no ">" items."""
        stems = self.storage.stems("todo")
        if not 0 <= index < len(stems):
            return []
        content = self.storage.read_item("todo", index) or ""
        done = self.done_map() if done is None else done
        stem = stems[index]
        return [(text, (stem + "#" + text) in done) for text in checklist_items(content)]

    def toggle_item(self, index, text, today):
        """Tick / un-tick one item of the checklist at `index`.  Ticking the last one ticks the whole list (it
        counts in the statistics as one To-Do); un-ticking one of a done list un-ticks it.  Returns the item's new state."""
        stems = self.storage.stems("todo")
        if not 0 <= index < len(stems):
            return None
        stem, done = stems[index], self.done_map()
        key = stem + "#" + text
        was_done = stem in done
        if key in done:
            del done[key]
            result = False
            if stem in done:
                if self._counter is not None:
                    self._counter.add(done[stem], -1)
                del done[stem]
        else:
            done[key] = today
            result = True
            items = checklist_items(self.storage.read_item("todo", index) or "")
            if stem not in done and all((stem + "#" + t) in done for t in items):
                done[stem] = today
                if self._counter is not None:
                    self._counter.add(today, 1)
        self._save_map(done)
        self._state(stem, item=text)
        if was_done != (stem in done):
            self._state(stem)
        return result

    def toggle_done(self, index, today):
        """Tick / un-tick the To-Do at `index` (0 = first file). today = 'YYYY-MM-DD'. Returns True if it is done now, None if no such To-Do."""
        stems = self.storage.stems("todo")
        if not 0 <= index < len(stems):
            return None
        stem, done = stems[index], self.done_map()
        if stem in done:
            if self._counter is not None:
                self._counter.add(done[stem], -1)          # un-ticking takes the point back from the day it was given
            del done[stem]
            result = False
        else:
            done[stem] = today
            if self._counter is not None:
                self._counter.add(today, 1)
            result = True
        self._save_map(done)
        self._state(stem)
        return result

    def apply_state(self, stem, done, items, day=None):
        """Put the state of `stem` as another device sent it: done or not, and {item text: day ticked} of its ticked
        items (the others are un-ticked).  Not counted in this device's statistics; the meta times are the caller's."""
        marks = self.done_map()
        for key in [k for k in marks if k.startswith(stem + "#")]:
            if key[len(stem) + 1:] not in items:
                del marks[key]
        for text, when in items.items():
            marks.setdefault(stem + "#" + text, when)
        if done:
            marks.setdefault(stem, day or marks.get(stem) or "2000-01-01")
        else:
            marks.pop(stem, None)
        self._save_map(marks)

    def _state(self, stem, item=None):
        m = self.storage.meta("todo")
        if m is not None:
            m.state(stem, item=item)

    def purge(self, today_days=None):
        """Delete To-Dos that have been done for TODO_KEEP_DAYS days or more; forget marks of files that are gone.

        Returns how many To-Dos were deleted."""
        if today_days is None:
            from scheduler import valid_now
            t = valid_now()
            if t is None:
                return 0
            today_days = days_from_civil(t[0], t[1], t[2])
        done = self.done_map()
        if not done:
            return 0
        keep = cfg.get("TODO_KEEP_DAYS")
        exist = set(self.storage.stems("todo"))
        deleted, changed = 0, False
        for stem in list(done):
            if stem not in done:
                continue                                  # an item mark of a list deleted a moment ago
            base = stem.partition("#")[0]                 # "name#item": an item of a checklist
            if base not in exist:
                del done[stem]
                changed = True
                continue
            if base != stem:
                continue                                  # items go with their list, not by their own date
            y, m, d = done[stem].split("-")
            if today_days - days_from_civil(int(y), int(m), int(d)) >= keep:
                if not self.storage.delete_path(f"{self.storage.base_dir}/todo/{stem}.txt"):
                    log(f"[TODO] cannot delete {stem}")
                    continue
                deleted += 1
                del done[stem]
                for key in list(done):
                    if key.startswith(stem + "#"):
                        del done[key]
                changed = True
        if changed:
            self._save_map(done)
        return deleted
