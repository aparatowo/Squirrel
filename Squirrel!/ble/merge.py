# ble/merge.py - a node's copy of a list put together with the head's (routines, To-Dos, notes) - docs/implementation/en/data-format.md 2
#
# The head (the Cardputer) is the only AUTHOR of content: which head records exist and what they say comes from it -
# a record missing from the head's list is deleted on the node.  The STATE of a record ("on" of a routine, "done" of a
# To-Do and of each checklist item) may change anywhere; "c" is the (wire) time of its last change and the later
# change wins.  A record whose id carries a node's slot is that node's LOCAL record (made there by an editor connected
# to the node directly): the head never changes or deletes it and does not take it over (adopting it is a later step).
# Content edits made on a node (proposals) are a later step too (docs/implementation/en/bluetooth.md 10).

SLOT_BITS = 3            # an id: the creator's slot in the top 3 bits (0 = the head), its own counter below
COUNTER_BITS = 13
HEAD_SLOT = 0


def slot_of(rid):
    return rid >> COUNTER_BITS


def merge(head, node, state_key):
    """head: the head's records; node: the node's (head records and its local ones).  state_key: "on" / "done", or
    None for records without a state (notes).
    -> (head_new, node_new, head_differs, node_differs): what each side should hold, and which has to write it."""
    by_id = {}
    for r in node:
        by_id[r["id"]] = r
    head_new = []
    for h in head:
        n = by_id.get(h["id"])
        head_new.append(h if n is None or state_key is None else _state(h, n, state_key))
    local = [r for r in node if slot_of(r["id"]) != HEAD_SLOT]
    node_new = head_new + local
    return head_new, node_new, head_new != list(head), node_new != list(node)


def _state(h, n, state_key):
    """The head's record with the later of the two states (and the later state of each checklist item)."""
    later = n if n.get("c", 0) > h.get("c", 0) else h
    items = merge_items(h.get("items"), n.get("items"))
    if later is h and items == h.get("items"):
        return h
    r = dict(h)
    r[state_key] = later[state_key]
    r["c"] = later.get("c", 0)
    if items:
        r["items"] = items
    return r


def merge_items(a, b):
    """The items of two copies of a checklist, by their text: the later "c" gives "done".  a: the head's."""
    if not b:
        return a
    if not a:
        return b
    by_text = {}
    for item in b:
        by_text[item["t"]] = item
    out, seen = [], set()
    for item in a:
        seen.add(item["t"])
        o = by_text.get(item["t"])
        out.append(o if o is not None and o.get("c", 0) > item.get("c", 0) else item)
    out.extend(item for item in b if item["t"] not in seen)
    return out


def next_id(records, slot=HEAD_SLOT):
    """A new record's id for the device in `slot`: one above its highest counter (never reused while the record lives)."""
    mine = [r["id"] & ((1 << COUNTER_BITS) - 1) for r in records if slot_of(r["id"]) == slot]
    counter = max(mine or [0]) + 1
    if counter >= 1 << COUNTER_BITS:
        raise ValueError("no ids left in slot %d" % slot)
    return slot << COUNTER_BITS | counter
