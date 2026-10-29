# success_log.py - the success journal (Notes -> Success journal): one list a day of what went well
#
# A day is a text file wins/YYYY-MM-DD.txt: its first line is the date, and every later line that starts with "-" or
# ">" is one thing that worked out - the To-Do checklist's rule (todo_editor.checklist_items), with "-" as well, the way
# a list is typed anyway.  Other lines are plain text (how it went, a thought).
# "+ [Today]" opens today's file in the editor, a fresh "- " line at its end; a past day is opened from the list.
# The statistics (screens/focus_stats_screen.py) count the items of the last days from the files themselves: an
# edited or deleted day can never put them out of step.  Written on the Cardputer; not synced over Bluetooth (yet).
from todo_editor import checklist_items

MARKS = ("-", ">")
COLLECTION = "wins"


def items(content):
    """The things done of a day's text (its first line, the date, is not one)."""
    return checklist_items(content, MARKS)


def tidy(day, content):
    """The text to save: the date as its first line, no empty item lines ("-" alone), no trailing blank lines."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != day:
        lines.insert(0, day)
    out = [lines[0].strip()]
    for line in lines[1:]:
        if line.strip() in MARKS:
            continue                           # an item started and left empty
        out.append(line.rstrip())
    while len(out) > 1 and not out[-1]:
        out.pop()
    return "\n".join(out) + "\n"


class SuccessLog:
    def __init__(self, storage):
        self.storage = storage

    @staticmethod
    def today():
        """Today's "YYYY-MM-DD", or None while the clock is not set."""
        from scheduler import valid_now, day_key
        t = valid_now()
        return day_key(t) if t else None

    def _index(self, day):
        stems = self.storage.stems(COLLECTION)
        return stems.index(day) if day in stems else None

    def editor_args(self, day):
        """What the editor (NOTE_EDITOR) opens a day with: its text so far and a new "- " line to type into."""
        index = self._index(day)
        body = (self.storage.read_item(COLLECTION, index) or "") if index is not None else ""
        body = tidy(day, body).rstrip("\n") + "\n- "
        return {"menu_name": "WINS", "file_index": index, "body": body, "day": day}

    def save(self, day, content):
        """Save a day's list (a new one, or over the old one).  True when it was written."""
        content = tidy(day, content)
        index = self._index(day)
        if index is None:
            return self.storage.save_item(COLLECTION, day, content)
        return self.storage.update_item(COLLECTION, index, day, content)

    def count(self, day):
        """The things done on `day` (0 without a file)."""
        try:
            with open("%s/%s/%s.txt" % (self.storage.base_dir, COLLECTION, day)) as f:
                return len(items(f.read()))
        except OSError:
            return 0
