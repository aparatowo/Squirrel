# todo_editor.py - TODO entry handler
#
# A To-Do is a text file in todo/.  "Done" is kept apart from the files, in todo/done.dat ("name,YYYY-MM-DD" lines):
# the text of a To-Do is never touched by ticking it.  A done To-Do is deleted TODO_KEEP_DAYS (7) days after it was
# ticked (purge()), and every tick is counted for the statistics (todos_done, a scheduler.DayCounter).
import os
from appconfig import cfg
from boot_log import log
from timeutil import days_from_civil


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
        """['+ [New Item]', '1. Buy milk', ...] -> the same with '[ ]' / '[X]' in front of each To-Do's title."""
        done = self.done_map()
        stems = self.storage.stems("todo")
        out = [items[0]] if items else []
        for n, text in enumerate(items[1:]):
            number, sep, title = text.partition(". ")
            mark = "[X]" if (n < len(stems) and stems[n] in done) else "[ ]"
            out.append("%s%s%s %s" % (number, sep, mark, title))
        return out

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
        return result

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
            y, m, d = done[stem].split("-")
            if stem not in exist:
                del done[stem]
                changed = True
            elif today_days - days_from_civil(int(y), int(m), int(d)) >= keep:
                try:
                    os.remove(f"{self.storage.base_dir}/todo/{stem}.txt")
                    deleted += 1
                except OSError as e:
                    log(f"[TODO] cannot delete {stem}: {e}")
                    continue
                del done[stem]
                changed = True
        if changed:
            self._save_map(done)
        return deleted
