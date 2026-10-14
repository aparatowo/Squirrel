# tools/tests/test_checklist.py - checklists (">" items) in todo_editor.py (CPython, from the folder with squirrel_app.py)
import os
import sys
import tempfile
sys.path.insert(0, ".")
from storage_manager import StorageManager
from todo_editor import TodoEditor, checklist_items

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


class Counter:
    def __init__(self):
        self.days = {}

    def add(self, key, n=1):
        self.days[key] = self.days.get(key, 0) + n


check("items", checklist_items("Zakupy\n> mleko\n\n  >chleb\npamiętać o torbie\n> masło, 82%\n>\n") ==
      ["mleko", "chleb", "masło, 82%"])
check("title is never an item", checklist_items("> nie pozycja\n> pozycja") == ["pozycja"])
check("no items", checklist_items("Zadzwonić\ndo Leszka") == [])

base = tempfile.mkdtemp()
st = StorageManager(base)
st.save_item("todo", "Sobota", "Sobota\n> mleko\nz rana\n> chleb, razowy\n")
st.save_item("todo", "Zadzwonić", "Zadzwonić")
counter = Counter()
ed = TodoEditor(st, counter)
i = st.stems("todo").index("sobota")
check("at", ed.has_checklist_at(i) and not ed.has_checklist_at(1 - i))
check("state", ed.checklist_state(i) == [("mleko", False), ("chleb, razowy", False)])
items = ed.decorate(["+ [New item]"] + st.list_items("todo"))
check("progress", "[0/2] Sobota" in items[1 + i])
check("strip", ed.strip_mark(items[1 + i]) == "%d. Sobota" % (i + 1))
check("strip done", ed.strip_mark("2. [X] Foo") == "2. Foo" and ed.strip_mark("[ ] Foo") == "Foo")

ed.toggle_item(i, "mleko", "2026-10-12")
check("one ticked", ed.checklist_state(i) == [("mleko", True), ("chleb, razowy", False)] and not counter.days)
ed.toggle_item(i, "chleb, razowy", "2026-10-12")
check("all -> done", "sobota" in ed.done_map() and counter.days == {"2026-10-12": 1})
check("decorate done", "[X] Sobota" in ed.decorate(["+"] + st.list_items("todo"))[1 + i])
ed.toggle_item(i, "mleko", "2026-10-13")
check("untick -> not done", "sobota" not in ed.done_map() and counter.days == {"2026-10-12": 0})

# purge: item marks survive while the list exists; the list goes after TODO_KEEP_DAYS with its marks
ed.toggle_item(i, "mleko", "2026-10-12")
from timeutil import days_from_civil
check("purge keeps", ed.purge(days_from_civil(2026, 10, 13)) == 0 and len(ed.done_map()) == 3)
check("purge deletes", ed.purge(days_from_civil(2026, 10, 30)) == 1 and ed.done_map() == {})
check("file gone", st.stems("todo") == ["zadzwonic"])

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
