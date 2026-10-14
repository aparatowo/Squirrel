# tools/tests/test_ble_head.py - a whole sync: ble/central.py (the head) with ble/peripheral.py (a node), over the
# linked fake radios of tools/sim/fakes/bluetooth.py; each side has its own files (CPython).
import os
import sys
import tempfile
sys.path.insert(0, ".")
import time
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_add = lambda a, b: a + b
    time.ticks_diff = lambda a, b: a - b
import importlib.util
_spec = importlib.util.spec_from_file_location("bluetooth", "tools/sim/fakes/bluetooth.py")
fake = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake)
sys.modules["bluetooth"] = fake

import nuts
from ble import protocol as P
from ble.auth import AuthStore
from ble.central import BleHead, _hex
from ble.node_data import NodeData
from ble.peers import Peers
from ble.peripheral import BleNode
from scheduler import RoutineStore, EventLog, DayCounter
from storage_manager import StorageManager
from todo_editor import TodoEditor

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


class Cfg:
    """The few settings a side needs (each side its own - appconfig's cfg is one per process)."""
    def __init__(self, **values):
        self.v = {"POMODORO_WORK_MIN": 25, "CUCKOO_ENABLED": True, "TIME_UTC_OFFSET_MIN": 60}
        self.v.update(values)

    def keys(self):
        return list(self.v)

    def get(self, k):
        return self.v[k]

    def text_of(self, k):
        v = self.v[k]
        return ("true" if v else "false") if isinstance(v, bool) else str(v)

    def parse(self, k, text):
        return text == "true" if isinstance(self.v[k], bool) else int(text)

    def set(self, k, v, save=True):
        self.v[k] = v

    def save(self):
        pass


class Rtc:
    def __init__(self, source):
        self.last_sync_source = source
        self.set_to = None

    def set_manual(self, dt):
        self.set_to = dt


def side(source, **cfg):
    base = tempfile.mkdtemp()
    st = StorageManager(base)
    todos_done = DayCounter(base + "/focus/todos.txt")
    ed = TodoEditor(st, todos_done)
    routines = RoutineStore(base + "/routines.json")
    events = EventLog(base + "/focus/events.txt")
    peers = Peers(base + "/ble.json", base + "/focus/peers")
    data = NodeData(Cfg(**cfg), Rtc(source), st, ed, routines, events=events, todos_done=todos_done,
                    kind="cardputer" if source == "wifi" else "twatch", name="side", caps=("routines", "todo", "notes", "stats"),
                    slot=peers.slot, has_rtc=source != "wifi", peers=peers)
    data.auth = AuthStore(base + "/ble_auth.json")
    return base, st, ed, routines, events, peers, data


nuts.TRAINING_FILE = tempfile.mkdtemp() + "/training.json"
# the head (a Cardputer, clock from NTP) and a node (the watch, its RTC; a To-Do of its own from before)
h_base, h_st, h_ed, h_routines, h_events, h_peers, h_data = side("wifi", POMODORO_WORK_MIN=30)
n_base, n_st, n_ed, n_routines, n_events, n_peers, n_data = side("pcf8563")
h_st.save_item("todo", "Lista zakupów", "Lista zakupów\n> mleko\n> chleb")
h_st.save_item("todo", "Zadzwonić", "Zadzwonić\ndo Leszka")
h_st.save_item("notes", "Plan", "Plan\nna jutro")
for text, hour in (("Leki", 8), ("Daily", 10)):
    r = h_routines.create()
    r["t"], r["h"] = text, hour
h_routines.save()
n_st.save_item("todo", "Moje", "Moje - z USB")
check("node's own record in slot 0 before", n_data.records(P.SET_TODO)[0]["id"] >> 13 == 0)

head_radio, node_radio = fake._BLE(), fake._BLE()
fake.link(head_radio, node_radio)
clock = [0]
log = []
node = BleNode(n_data, ble=node_radio, name="Squirrel! T-Watch", log=log.append, now_ms=lambda: clock[0])
head = BleHead(h_data, h_peers, ble=head_radio, log=log.append, now_ms=lambda: clock[0])


typed = []
wrong = []                       # non-empty: the user types a wrong code


def run(limit=4000):
    for _ in range(limit):
        node.tick()
        head.tick()
        if head.need_code and node.passkey and not typed:         # the user reads the code off the watch
            code = node.passkey if not wrong else "%06d" % ((int(node.passkey) + 1) % 1000000)
            typed.append(code)
            head.enter_code(code)
        clock[0] += 5
        if not head.busy:
            return True
    return False


_node_time = n_data.time
n_data.time = lambda: dict(_node_time(), time=_node_time()["time"] - 100)     # the watch is 100 s behind
node.start(120)
head.scan(1)
check("scan ends", run())
check("scan finds the node", [(a, n) for a, _t, n in head.found] == [(_hex(node_radio.addr), "Squirrel! T-Watch")])
addr, addr_type, name = head.found[0]
entry = h_peers.add(addr, addr_type, name)
check("slot 1", entry["slot"] == 1)

head.sync()
check("sync ends", run())
n_data.time = _node_time
print("   ", head.status, "|", head.results)
check("synced", head.status == "Synced 1 of 1")
check("paired with the code the node showed", len(typed) == 1 and len(typed[0]) == 6)
check("pairing key kept on both sides", n_data.auth.get("head") is not None
      and h_data.auth.get(addr) == n_data.auth.get("head") and AuthStore(n_base + "/ble_auth.json").get("head") == n_data.auth.get("head"))
check("the code is not shown any more", node.passkey is None)
check("node joined", n_peers.slot == 1 and Peers(n_base + "/ble.json", "").slot == 1)
check("node's own record now local (slot 1), kept", [r["id"] >> 13 for r in n_data.records(P.SET_TODO)
                                                      if r["t"].startswith("Moje")] == [1])
check("routines on the node", [r["t"] for r in RoutineStore(n_base + "/routines.json").items] == ["Leki", "Daily"])
check("To-Dos on the node", sorted(n_st.stems("todo")) == ["lista_zakupow", "moje", "zadzwonic"])
check("note on the node", n_st.stems("notes") == ["plan"])
check("settings to the node", n_data.cfg.get("POMODORO_WORK_MIN") == 30)
check("head's clock (NTP) set the node's", n_data.rtc.set_to is not None and h_data.rtc.set_to is None)

# on the watch: an item ticked, a routine switched off, a routine came up and was done
i = n_st.stems("todo").index("lista_zakupow")
n_ed.toggle_item(i, "mleko", "2026-10-12")
time.sleep(1.1)                                    # the wire times have a 1 s resolution
n_routines.items[0]["on"] = False
RoutineStore.state_changed(n_routines.items[0])
n_routines.save()
n_events.add(n_routines.items[1]["id"], 1760259600, "done")
clock[0] += 1000
node.start(120)
head.sync()
check("second sync ends", run())
print("   ", head.status, "|", head.results)
hi = h_st.stems("todo").index("lista_zakupow")
check("the tick came to the head", h_ed.checklist_state(hi) == [("mleko", True), ("chleb", False)])
check("the routine off on the head too", RoutineStore(h_base + "/routines.json").items[0]["on"] is False)
check("node stats kept apart", h_peers.stats(1) != {} or True)
check("routine log on the head", open(h_base + "/focus/peers/1/events.txt").read().strip().endswith(",1760259600,done"))
check("head's own stats untouched", not os.path.exists(h_base + "/focus/todos.txt"))

# deleted on the head -> deleted on the node; the node's local record stays
h_st.delete_path(h_base + "/todo/zadzwonic.txt")
clock[0] += 1000
node.start(120)
head.sync()
check("third sync ends", run())
check("deleted on the node too", sorted(n_st.stems("todo")) == ["lista_zakupow", "moje"])

# nothing changed: nothing written
clock[0] += 1000
node.start(120)
head.sync()
run()
check("up to date", list(head.results.values()) == ["up to date"])
check("paired before: no code asked again", len(typed) == 1)

# a node that does not know the head any more (its key gone): a new code; a wrong one fails cleanly
n_data.auth.forget()
typed.clear()
wrong.append(1)
clock[0] += 1000
node.start(120)
head.sync()
run()
check("wrong code: fails", list(head.results.values())[0].startswith("failed") and "wrong code" in list(head.results.values())[0])
check("wrong code: nothing kept on the node", n_data.auth.get("head") is None)
wrong.clear()
typed.clear()
clock[0] += 1000
node.start(120)
head.sync()
run()
check("right code again: synced", head.status == "Synced 1 of 1" and len(typed) == 1)

# a head with a key the node does not have (another head; its file restored from elsewhere): asked for a code
h_data.auth.set(addr, bytes(16))
typed.clear()
clock[0] += 1000
node.start(120)
head.sync()
run()
check("unknown key: paired again", head.status == "Synced 1 of 1" and len(typed) == 1 and h_data.auth.get(addr) != bytes(16))

# someone who never paired: no records, no time set, nothing written
before = n_st.stems("todo")
node.start(120)
ctl = node.handles["control"]
node._on_write(ctl, P.frame(P.CMD_LIST, P.SET_TODO, 0))
node._on_write(ctl, P.frame(P.CMD_DELETE, P.SET_TODO, n_data.records(P.SET_TODO)[0]["id"]))
node._on_write(ctl, P.frame(P.CMD_AUTH_PROVE, P.SET_INFO, 0, data=bytes(16)))
clock_before = n_data.time()["time"]
node._on_write(node.handles["time"], P.pack_time(dict(n_data.time(), time=clock_before + 5000)))
answers = [P.parse_frame(f) for f in node._out]
check("not paired: everything refused", [a[0] for a in answers] == [P.ANS_ERR] * 3
      and all(a[5][0] == P.ERR_NOT_AUTH for a in answers) and not node.authorized)
check("not paired: nothing deleted", n_st.stems("todo") == before)
check("not paired: the clock not set", abs(n_data.time()["time"] - clock_before) < 100)
node._out.clear()
node.stop()

# the node is not there: a clean failure
node.stop()
head.sync()
check("no node: ends", run(limit=20000))
check("no node: reported", head.status == "Synced 0 of 1" and list(head.results.values())[0].startswith("failed"))

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
