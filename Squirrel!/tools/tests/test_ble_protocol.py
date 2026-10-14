# tools/tests/test_ble_protocol.py - ble/protocol.py (the binary encoding of docs/implementation/en/data-format.md) on the PC
#
# Runs under CPython and under the MicroPython unix port (no unittest, no pytest needed), from the folder with
# squirrel_app.py:   python3 tools/tests/test_ble_protocol.py   /   micropython tools/tests/test_ble_protocol.py
import sys
sys.path.insert(0, ".")
from ble import protocol as p

_failed = []


def check(name, cond):
    if not cond:
        _failed.append(name)
        print("FAIL", name)


def raises(fn, *args):
    try:
        fn(*args)
    except ValueError:
        return True
    return False


def round_trip(which, r):
    return p.unpack_record(which, p.pack_record(which, r)) == r


# texts: cut on a character boundary
s = p.pack_str("zażółć", 4)                        # z a ż(2) -> 4 bytes; ó would not fit
check("str cut", p.unpack_str(s, 0) == ("zaż", 5))
check("str16 cut", p.unpack_str16(p.pack_str16("ąąą", 5), 0) == ("ąą", 6))
check("str empty", p.unpack_str(p.pack_str(""), 0) == ("", 1))
check("str past end", raises(p.unpack_str, b"\x05ab", 0))

# INFO / TIME
info = {"version": 1, "kind": "twatch", "caps": ["rtc", "routines", "steps"], "name": "T-Watch", "app": "2.0", "slot": 1}
check("info", p.unpack_info(p.pack_info(info)) == info)
t = {"time": 1760270400, "offset": 120, "source": "rtc", "age": 10, "has_rtc": True, "rtc_valid": True}
check("time", p.unpack_time(p.pack_time(t)) == t)

# the better clock
ntp = {"source": "ntp", "age": 99999}
rtc = {"source": "rtc", "age": 0, "rtc_valid": True}
check("ntp beats rtc", p.better_clock(ntp, rtc) == "a")
check("rtc beats soft", p.better_clock({"source": "soft", "age": 0}, rtc) == "b")
check("invalid rtc = soft", p.better_clock({"source": "rtc", "age": 0, "has_rtc": True}, {"source": "soft"}) is None)
check("fresher wins", p.better_clock({"source": "manual", "age": 10}, {"source": "manual", "age": 7200}) == "a")

# SETTINGS: unknown keys and junk skipped; the training plan
got = p.unpack_settings(b"CUCKOO_ENABLED=true\nFOO=1\njunk\nPOMODORO_WORK_MIN = 25 \n")
check("settings", got == {"CUCKOO_ENABLED": "true", "POMODORO_WORK_MIN": "25"})
check("settings round", p.unpack_settings(p.pack_settings(got)) == got)
plan = [["blue", 120], ["red", 60]]
check("training", p.training_plan(p.training_text(plan)) == plan)
check("training bad", raises(p.training_plan, "purple:10") and raises(p.training_plan, "red"))

# records
routine = {"id": 8193, "t": "Leki ąę", "h": 8, "m": 0, "d": 63, "on": True, "to": 1, "e": 1750000000, "c": 1760000000}
check("routine", round_trip(p.SET_ROUTINES, routine))
check("routine tomb", round_trip(p.SET_ROUTINES, {"id": 3, "e": 1760000500, "del": True}))
check("routine bad hour", raises(p.unpack_record, p.SET_ROUTINES, p.pack_record(p.SET_ROUTINES, dict(routine, h=24))))
check("routine trailing", raises(p.unpack_record, p.SET_ROUTINES, p.pack_record(p.SET_ROUTINES, routine) + b"x"))
check("routine short", raises(p.unpack_record, p.SET_ROUTINES, p.pack_record(p.SET_ROUTINES, routine)[:-2]))

todo = {"id": 2, "t": "Lista zakupów\n- mleko\n- chleb", "done": False, "e": 5, "c": 0,
        "items": [{"t": "mleko", "done": True, "c": 7}, {"t": "chleb", "done": False, "c": 0}]}
check("todo", round_trip(p.SET_TODO, todo))
check("todo plain", round_trip(p.SET_TODO, {"id": 4, "t": "Zadzwonić", "done": True, "e": 1, "c": 2}))
check("todo tomb", round_trip(p.SET_TODO, {"id": 4, "e": 9, "del": True}))
long_text = "ż" * 500
check("todo 500 chars", p.unpack_record(p.SET_TODO, p.pack_record(p.SET_TODO, dict(todo, t=long_text)))["t"] == long_text)

note = {"id": 9, "t": "Uwagi\n" + "ł" * 1990, "e": 3}
check("note", round_trip(p.SET_NOTES, note))
check("note tomb", round_trip(p.SET_NOTES, {"id": 9, "e": 4, "del": True}))

stat = {"day": "2026-10-12", "k": "focus_min", "n": 95}
check("stat", round_trip(p.SET_STATS, stat))
check("unknown set", raises(p.unpack_record, 0x42, b""))

# LIST
records = [routine, {"id": 3, "e": 1760000500, "del": True}]
rev, entries = p.unpack_list(p.SET_ROUTINES, p.pack_list(7, records))
check("list", rev == 7 and entries == [{"id": 8193, "e": 1750000000, "c": 1760000000}, {"id": 3, "e": 1760000500, "c": 0, "del": True}])
stats = [stat, {"day": "2026-10-11", "k": "steps", "n": 8000}]
check("stats list", p.unpack_list(p.SET_STATS, p.pack_inline_list(p.SET_STATS, 1, stats)) == (1, stats))
events = [{"r": 1, "at": 1760259600, "res": "done"}, {"r": 8193, "at": 1760263200, "res": "missed"}]
check("event", round_trip(p.SET_EVENTS, events[0]))
check("events list", p.unpack_list(p.SET_EVENTS, p.pack_inline_list(p.SET_EVENTS, 3, events)) == (3, events))
check("since", p.unpack_since(p.pack_since(1760259600)) == 1760259600 and p.unpack_since(b"") == 0)
check("list trailing", raises(p.unpack_list, p.SET_ROUTINES, p.pack_list(1, records) + b"\x00"))

# CONTROL: a PUT of a long note in parts, put back together
payload = p.pack_record(p.SET_NOTES, note)
fs = p.frames(p.CMD_PUT, p.SET_NOTES, 9, payload, 20)          # the smallest MTU: 23 - 3
check("frames fit", all(len(f) <= 20 for f in fs))
ra = p.Reassembler()
out = None
for f in fs:
    out = ra.feed(*p.parse_frame(f))
check("reassembled", out == payload and p.unpack_record(p.SET_NOTES, out) == note)

# a lost part: refused, and a fresh start works
ra.feed(*p.parse_frame(fs[0]))
lost = False
try:
    ra.feed(*p.parse_frame(fs[2]))
except ValueError as e:
    lost = e.args[0] == p.ERR_ORDER
check("lost part", lost)
for f in fs:
    out = ra.feed(*p.parse_frame(f))
check("restart", out == payload)

# parts of another record in between: refused
ra.feed(*p.parse_frame(fs[0]))
check("other record", raises(ra.feed, *p.parse_frame(p.frames(p.CMD_PUT, p.SET_NOTES, 10, payload, 20)[1])))

big = False
try:
    rb = p.Reassembler(limit=100)
    for f in p.frames(p.CMD_PUT, p.SET_TODO, 1, bytes(200), 60):
        rb.feed(*p.parse_frame(f))
except ValueError as e:
    big = e.args[0] == p.ERR_TOO_BIG
check("too big", big)

check("empty payload", p.parse_frame(p.frames(p.ANS_DATA, p.SET_STATS, 0, b"", 100)[0]) == (p.ANS_DATA, p.SET_STATS, 0, 0, True, b""))
check("error frame", p.parse_frame(p.error_frame(p.SET_TODO, 5, p.ERR_NO_RECORD)) == (p.ANS_ERR, p.SET_TODO, 5, 0, True, b"\x05"))
check("short frame", raises(p.parse_frame, b"\x01\x02"))

check("uuid bytes", p.uuid_bytes("00112233-4455-6677-8899-aabbccddeeff")[:2] == b"\xff\xee")
check("uuid", p.TIME_UUID == "beea0002-f159-4fd4-b434-1d8d3db5b0bc" and p.NOTES_UUID.startswith("beea0009"))

print("FAILED: %d" % len(_failed) if _failed else "OK")
sys.exit(1 if _failed else 0)
