# tools/tests/test_ble_merge.py - ble/merge.py on the PC (CPython or the MicroPython unix port)
import sys
sys.path.insert(0, ".")
from ble.merge import merge, merge_items, next_id, slot_of

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


def r(i, on, c, t="x", e=0):
    return {"id": i, "on": on, "c": c, "t": t, "e": e}


LOCAL = 1 << 13 | 1                     # a record made on the node in slot 1

head = [r(1, True, 100, "Leki", e=50), r(2, True, 100), r(3, True, 300)]
node = [r(1, False, 200, "stary tekst", e=10), r(2, False, 50), r(4, True, 999), r(LOCAL, True, 0, "lokalne")]
head_new, node_new, head_w, node_w = merge(head, node, "on")
check("content from the head, later state", head_new[0] == r(1, False, 200, "Leki", e=50))
check("earlier state loses", head_new[1] == r(2, True, 100))
check("head keeps its list", [x["id"] for x in head_new] == [1, 2, 3])
check("node: head records, deleted one gone, local kept", [x["id"] for x in node_new] == [1, 2, 3, LOCAL])
check("local untouched", node_new[3] == r(LOCAL, True, 0, "lokalne"))
check("both write", head_w and node_w)
check("inputs untouched", head[0]["on"] is True and node[0]["t"] == "stary tekst")

h2, n2, hw, nw = merge(head, [dict(x) for x in head], "on")
check("equal: nothing to write", h2 == head and n2 == head and not hw and not nw)

h2, n2, hw, nw = merge(head, [], "on")
check("empty node takes all", n2 == head and not hw and nw)

# a state changed on the node only: the head takes it, the node has nothing new
h2, n2, hw, nw = merge([r(1, True, 100)], [r(1, False, 200)], "on")
check("node tick -> head", h2 == [r(1, False, 200)] and hw and not nw)

# notes: no state - the head's copy, always
h2, n2, _, _ = merge([{"id": 1, "t": "a", "e": 5}], [{"id": 1, "t": "b", "e": 9}], None)
check("note from the head", h2 == n2 == [{"id": 1, "t": "a", "e": 5}])

# checklists: items by text, the later tick wins per item
def todo(items):
    return {"id": 7, "t": "Lista zakupów\nmleko\nchleb\njajka", "done": False, "e": 1, "c": 0, "items": items}

cp = todo([{"t": "mleko", "done": True, "c": 10}, {"t": "chleb", "done": False, "c": 30}])
tw = todo([{"t": "mleko", "done": False, "c": 5}, {"t": "chleb", "done": True, "c": 20}, {"t": "jajka", "done": True, "c": 40}])
h2, n2, hw, nw = merge([cp], [tw], "done")
check("items merged", h2[0]["items"] == [{"t": "mleko", "done": True, "c": 10}, {"t": "chleb", "done": False, "c": 30},
                                          {"t": "jajka", "done": True, "c": 40}] and h2 == n2 and hw and nw)
check("merge_items empty", merge_items(None, [1]) == [1] and merge_items([], None) == [])

check("next id", next_id([r(1, True, 0), r(2, True, 0)]) == 3 and next_id([]) == 1)
check("next id per slot", next_id([r(1, True, 0), r(7 << 13 | 4, True, 0)], 7) == 7 << 13 | 5)
check("slot", slot_of(LOCAL) == 1 and slot_of(5) == 0)

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
