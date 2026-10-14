# tools/tests/test_ble_node.py - ble/peripheral.py + ble/node_data.py against a fake central (CPython)
#
# Real files in a temporary folder (routines.json, To-Dos, notes, done.dat, config.txt); the radio is
# tools/sim/fakes/bluetooth.py, which also plays the head.
import os
import sys
import tempfile
sys.path.insert(0, ".")
import time
if not hasattr(time, "ticks_ms"):                # CPython: MicroPython's tick counters
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_add = lambda a, b: a + b
    time.ticks_diff = lambda a, b: a - b
import importlib.util
_spec = importlib.util.spec_from_file_location("bluetooth", "tools/sim/fakes/bluetooth.py")
fake = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake)
sys.modules["bluetooth"] = fake

import nuts
from appconfig import cfg
from ble import protocol as P
from ble.node_data import NodeData
from ble.peripheral import BleNode, SET_SETTINGS
from scheduler import RoutineStore, EventLog
from storage_manager import StorageManager
from todo_editor import TodoEditor

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


base = tempfile.mkdtemp()
nuts.TRAINING_FILE = base + "/training.json"
cfg.load(base + "/config.txt")
st = StorageManager(base)
st.save_item("todo", "Lista zakupów", "Lista zakupów\n> mleko\n> chleb\n")
st.save_item("todo", "Zadzwonić", "Zadzwonić do Leszka")
st.save_item("notes", "Uwagi", "Uwagi\nlinia")
todo = TodoEditor(st)
with open(base + "/routines.json", "w") as f:
    f.write('[{"t": "Leki", "h": 8, "m": 0, "on": true, "d": 63}]')
routines = RoutineStore(base + "/routines.json")
events = EventLog(base + "/focus/events.txt")
events.add(1, 1000, "done")
events.add(1, 2000, "missed")


class Rtc:
    last_sync_source = "pcf8563"
    set_to = None

    def set_manual(self, dt):
        self.set_to = dt


rtc = Rtc()
data = NodeData(cfg, rtc, st, todo, routines, events=events, kind="twatch", name="T-Watch",
                caps=("rtc", "routines", "todo"), slot=1, has_rtc=True)
from ble import auth as A
data.auth = A.AuthStore(base + "/ble_auth.json")
clock = [0]
log = []
node = BleNode(data, name="Squirrel! T-Watch", log=log.append, now_ms=lambda: clock[0])
ble = fake.BLE()
node.start(window_s=10)
h = node.handles

check("advertising", node.state == "advertising" and ble.advertising is not None)
check("adv has the service", P.uuid_bytes(P.SERVICE_UUID) in ble.advertising[1])
check("name in the scan response", b"Squirrel! T-Watch" in ble.advertising[2])
check("info", P.unpack_info(ble.central_read(h["info"]))["kind"] == "twatch")
t = P.unpack_time(ble.central_read(h["time"]))
check("time", t["source"] == "rtc" and t["rtc_valid"] and abs(t["time"] - __import__("timeutil").wire_now()) < 5)

ble.central_connect()
ble.central_mtu(100)
node.tick()
check("connected", node.state == "connected" and node.room == 97)


def ask(code, which, rid=0, payload=b""):
    """One request as the head makes it -> ("data", payload) / ("ack",) / ("err", code)."""
    ble.notified.clear()
    for frame in P.frames(code, which, rid, payload, node.room):
        ble.central_write(h["control"], frame)
        node.tick()
    for _ in range(20):
        node.tick()
    parts = P.Reassembler()
    for _conn, handle, value in ble.notified:
        code_, which_, rid_, part, last, d = P.parse_frame(value)
        if code_ == P.ANS_ACK:
            return ("ack",)
        if code_ == P.ANS_ERR:
            return ("err", d[0])
        out = parts.feed(code_, which_, rid_, part, last, d)
        if out is not None:
            return ("data", out)
    return ("nothing",)


# pairing (ble/auth.py): nothing is served before it
check("not paired: LIST refused", ask(P.CMD_LIST, P.SET_ROUTINES) == ("err", P.ERR_NOT_AUTH))
head_nonce = bytes(range(16))
ans = ask(P.CMD_AUTH_HELLO, P.SET_INFO, 0, head_nonce)
check("pairing: a code shown", ans[0] == "data" and len(ans[1]) == 16 and len(node.passkey or "") == 6)
wrong = A.pair_key("%06d" % ((int(node.passkey) + 1) % 1000000), head_nonce, ans[1])
check("pairing: a wrong code refused", ask(P.CMD_AUTH_CONFIRM, P.SET_INFO, 0, A.confirm_proof(wrong, ans[1]))
      == ("err", P.ERR_BAD_CODE) and data.auth.get("head") is None and node.passkey is None)
ans = ask(P.CMD_AUTH_HELLO, P.SET_INFO, 0, head_nonce)
key = A.pair_key(node.passkey, head_nonce, ans[1])
check("pairing: the right code", ask(P.CMD_AUTH_CONFIRM, P.SET_INFO, 0, A.confirm_proof(key, ans[1])) == ("ack",)
      and data.auth.get("head") == key)
check("paired, not proved yet: refused", ask(P.CMD_LIST, P.SET_ROUTINES) == ("err", P.ERR_NOT_AUTH))
challenge = ask(P.CMD_AUTH_CHALLENGE, P.SET_INFO)[1]
check("a wrong proof refused", ask(P.CMD_AUTH_PROVE, P.SET_INFO, 0, bytes(16)) == ("err", P.ERR_NOT_AUTH))
check("a challenge is used once", ask(P.CMD_AUTH_PROVE, P.SET_INFO, 0, A.session_proof(key, challenge))
      == ("err", P.ERR_NOT_AUTH))
challenge = ask(P.CMD_AUTH_CHALLENGE, P.SET_INFO)[1]
check("session proved", ask(P.CMD_AUTH_PROVE, P.SET_INFO, 0, A.session_proof(key, challenge)) == ("ack",)
      and node.authorized)
check("HMAC as in RFC 4231 (case 2)", A.hmac_sha256(b"Jefe", b"what do ya want for nothing?").hex()
      == "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843")

# LIST and GET
ans = ask(P.CMD_LIST, P.SET_ROUTINES)
rev, entries = P.unpack_list(P.SET_ROUTINES, ans[1])
check("list routines", [e["id"] for e in entries] == [1])
ans = ask(P.CMD_GET, P.SET_ROUTINES, 1)
check("get routine", P.unpack_record(P.SET_ROUTINES, ans[1])["t"] == "Leki")
check("get missing", ask(P.CMD_GET, P.SET_ROUTINES, 99) == ("err", P.ERR_NO_RECORD))

ans = ask(P.CMD_LIST, P.SET_TODO)
_rev, entries = P.unpack_list(P.SET_TODO, ans[1])
check("todo ids in the node's slot", all(e["id"] >> 13 == 1 for e in entries) and len(entries) == 2)
shop_id = [e["id"] for e in entries if P.unpack_record(P.SET_TODO, ask(P.CMD_GET, P.SET_TODO, e["id"])[1])["t"].startswith("Lista")][0]
shop = P.unpack_record(P.SET_TODO, ask(P.CMD_GET, P.SET_TODO, shop_id)[1])
check("checklist items", [i["t"] for i in shop["items"]] == ["mleko", "chleb"])

ans = ask(P.CMD_LIST, P.SET_EVENTS, payload=P.pack_since(1500))
check("events since", P.unpack_list(P.SET_EVENTS, ans[1])[1] == [{"r": 1, "at": 2000, "res": "missed"}])

# PUT from the head: a new routine, a To-Do with a ticked item, a note; then DELETE
new_routine = {"id": 2, "t": "Spacer", "h": 17, "m": 30, "d": 31, "on": True, "to": 255, "e": 5, "c": 0}
check("put routine", ask(P.CMD_PUT, P.SET_ROUTINES, 2, P.pack_record(P.SET_ROUTINES, new_routine)) == ("ack",))
check("routine stored", [r["t"] for r in RoutineStore(base + "/routines.json").items] == ["Leki", "Spacer"])
head_todo = {"id": 7, "t": "Lista zakupów sobota\n> jajka\n> kawa", "done": False, "e": 9, "c": 0,
             "items": [{"t": "jajka", "done": True, "c": 1760259600}, {"t": "kawa", "done": False, "c": 0}]}
check("put todo", ask(P.CMD_PUT, P.SET_TODO, 7, P.pack_record(P.SET_TODO, head_todo)) == ("ack",))
got = P.unpack_record(P.SET_TODO, ask(P.CMD_GET, P.SET_TODO, 7)[1])
check("todo round trip", got["t"] == head_todo["t"] and got["items"][0]["done"] and not got["items"][1]["done"]
      and got["items"][0]["c"] == 1760259600 and got["e"] == 9)
renamed = dict(head_todo, t="Lista zakupów niedziela\n> jajka", e=10)
ask(P.CMD_PUT, P.SET_TODO, 7, P.pack_record(P.SET_TODO, renamed))
check("rename keeps one file", "lista_zakupow_sobota" not in st.stems("todo") and "lista_zakupow_niedziela" in st.stems("todo"))
check("put note", ask(P.CMD_PUT, P.SET_NOTES, 3, P.pack_record(P.SET_NOTES, {"id": 3, "t": "Plan\n" + "x" * 1500, "e": 4})) == ("ack",))
check("long note in parts", len(P.unpack_record(P.SET_NOTES, ask(P.CMD_GET, P.SET_NOTES, 3)[1])["t"]) == 1505)
check("delete todo", ask(P.CMD_DELETE, P.SET_TODO, 7) == ("ack",) and "lista_zakupow_niedziela" not in st.stems("todo"))
check("delete missing", ask(P.CMD_DELETE, P.SET_TODO, 7) == ("err", P.ERR_NO_RECORD))

# settings and the clock
ans = ask(P.CMD_GET, SET_SETTINGS)
values = P.unpack_settings(ans[1])
check("settings read", "POMODORO_WORK_MIN" in values and "TRAINING_PLAN" in values)
ask(P.CMD_PUT, SET_SETTINGS, 0, P.pack_settings({"POMODORO_WORK_MIN": "30", "TRAINING_PLAN": "red:60,green:30"}))
check("settings applied", cfg.get("POMODORO_WORK_MIN") == 30)
check("training applied", P.unpack_settings(ask(P.CMD_GET, SET_SETTINGS)[1])["TRAINING_PLAN"] == "red:60,green:30")
ble.central_write(h["time"], P.pack_time({"time": 20373 * 86400 + 8 * 3600 + 15 * 60, "source": "ntp"}))
node.tick()
check("clock set", rtc.set_to[:6] == (2025, 10, 12, 8, 15, 0) and rtc.last_sync_source == "peer")

# damaged input, a full notification buffer, the end of the session
check("bad frame", ask(P.CMD_PUT, P.SET_ROUTINES, 2, b"\x00\x01") == ("err", P.ERR_BAD_DATA))
ble.notify_fails = 3
check("retries a full buffer", ask(P.CMD_GET, P.SET_ROUTINES, 1)[0] == "data")
ble.central_disconnect()
node.tick()
check("visible a little longer (a second round)", node.state == "advertising")
clock[0] += 16000
node.tick()
check("then off", node.state == "off" and not ble.active())

# nobody comes: the window closes
node2 = BleNode(data, log=log.append, now_ms=lambda: clock[0])
node2.start(window_s=10)
clock[0] += 11000
node2.tick()
check("window closes", node2.state == "off")

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
