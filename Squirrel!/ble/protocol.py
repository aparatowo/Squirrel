# ble/protocol.py - the Squirrel! record format on the air: UUIDs and the binary encoding of docs/implementation/en/data-format.md
#
# Pure Python (struct only): the same module runs on the ESP32 ports, under the PC simulator and in the PC tests, and is
# the reference for a C version and any other implementation.  Nothing here touches the radio.
#
# Records are the canonical JSON objects of data-format.md section 3 (Python dicts with exactly those keys);
# pack_* / unpack_* turn them into the bytes of section 4 and back.  Little-endian; texts UTF-8, cut only on a
# character boundary; times in seconds since 1970-01-01 LOCAL time.
import struct

_STRUCT_ERROR = getattr(struct, "error", ValueError)     # MicroPython raises ValueError

PROTOCOL_VERSION = 1
FORMAT_VERSION = 1

_BASE = "beea%04x-f159-4fd4-b434-1d8d3db5b0bc"
SERVICE_UUID = _BASE % 0x0000
INFO_UUID = _BASE % 0x0001
TIME_UUID = _BASE % 0x0002
SETTINGS_UUID = _BASE % 0x0003
ROUTINES_UUID = _BASE % 0x0004
TODO_UUID = _BASE % 0x0005
STATS_UUID = _BASE % 0x0006
STATUS_UUID = _BASE % 0x0007
CONTROL_UUID = _BASE % 0x0008
NOTES_UUID = _BASE % 0x0009
EVENTS_UUID = _BASE % 0x000A

def uuid_bytes(uuid):
    """'beea0000-f159-...' -> its 16 bytes as they go into an advertisement (little-endian)."""
    h = uuid.replace("-", "")
    return bytes(int(h[i:i + 2], 16) for i in range(len(h) - 2, -1, -2))


# data sets: the low byte of their characteristic's UUID
SET_INFO = 0x01         # PUT with id = slot: the head tells a node its slot (the node joins, docs/implementation/en/bluetooth.md 4)
SET_SETTINGS = 0x03     # GET / PUT with id 0: the settings (too long for a plain read)
SET_ROUTINES = 0x04
SET_TODO = 0x05
SET_STATS = 0x06
SET_NOTES = 0x09
SET_EVENTS = 0x0A       # the routine log a node reports to the head
SET_PROPOSALS = 0x0B    # reserved: content edits made on a node, for the head to decide on (a later step)

# INFO
KINDS = ("", "cardputer", "twatch", "nuts", "web")
CAPS = ("rtc", "todo", "routines", "stats", "pomodoro", "breathing", "cuckoo", "steps", "hub", "notes")

# TIME
SOURCES = ("soft", "manual", "rtc", "ntp", "peer")
_SOURCE_RANK = {"soft": 0, "peer": 1, "manual": 1, "rtc": 2, "ntp": 3}

# STAT kinds
STAT_KINDS = ("routines", "todos", "focus_min", "steps")

# EVENT results: what became of a routine that came up
EVENT_RESULTS = ("done", "skip", "missed")      # missed = no answer, even after the snoozes

# limits (data-format.md section 3), in bytes on the air
MAX_ROUTINE_TEXT = 200          # 50 characters
MAX_TODO_TEXT = 2000            # 500 characters
MAX_ITEM_TEXT = 255             # 100 characters
MAX_ITEMS = 64
MAX_NOTE_TEXT = 8000            # 2000 characters
TOMBSTONE_KEEP_S = 30 * 86400

_ON = 0x01
_DEL = 0x80

# CONTROL
CMD_LIST = 0x01
CMD_GET = 0x02
CMD_PUT = 0x03
CMD_DELETE = 0x04     # the head removes one of its records from a node (it is gone from the head's list)
CMD_AUTH_HELLO = 0x05      # pairing: the head's nonce -> the node's nonce (and it shows a code)   (ble/auth.py)
CMD_AUTH_CONFIRM = 0x06    # pairing: the head's proof that it has the key made from the code -> ACK / ERR_BAD_CODE
CMD_AUTH_CHALLENGE = 0x07  # every session: -> a fresh challenge
CMD_AUTH_PROVE = 0x08      # every session: the head's answer to it -> ACK / ERR_NOT_AUTH
AUTH_COMMANDS = (CMD_AUTH_HELLO, CMD_AUTH_CONFIRM, CMD_AUTH_CHALLENGE, CMD_AUTH_PROVE)
ANS_DATA = 0x10
ANS_ACK = 0x11
ANS_ERR = 0x12
FLAG_LAST = 0x01
ERR_UNKNOWN_SET = 1
ERR_ORDER = 2           # a part out of order (lost / repeated): the whole record has to be sent again
ERR_TOO_BIG = 3
ERR_BAD_DATA = 4
ERR_NO_RECORD = 5
ERR_NOT_AUTH = 6        # this head has not proved it is paired with this node (in this session)
ERR_BAD_CODE = 7        # pairing: the code typed in was not the one shown
MAX_PAYLOAD = 9000      # the largest record (a note) with room to spare; more is refused (ERR_TOO_BIG)

# The settings that travel between devices (SETTINGS: config.txt lines).  A device takes only the keys it knows and
# validates them with its own schema; an unknown key is skipped, so an older device does not refuse the whole write.
SYNCED_KEYS = (
    "CUCKOO_ENABLED", "CUCKOO_QUARTERS", "CUCKOO_QUARTER_VOLUME",
    "POMODORO_WORK_MIN", "POMODORO_BREAK_MIN", "POMODORO_LONG_BREAK_MIN", "POMODORO_CYCLES",
    "ROUTINE_SNOOZE_MIN",
    "QUIET_SOUND_FROM", "QUIET_SOUND_TO", "QUIET_SOUND_DAYS",
    "TRAINING_PLAN",
    "BLE_AUTO_SYNC_MIN",
)

# ---------------------------------------------------------------------------------------------------------- the epoch
# MicroPython's epoch is 2000 on some ports and 1970 on others; the format always speaks 1970.
try:
    import time as _time
    _EPOCH_SHIFT = 946684800 if _time.gmtime(0)[0] == 2000 else 0
except Exception:
    _EPOCH_SHIFT = 0


def to_wire_time(t):
    """time.time() of this device -> seconds since 1970."""
    return int(t) + _EPOCH_SHIFT


def from_wire_time(t):
    return t - _EPOCH_SHIFT


def day_number(key):
    """'2026-10-12' -> days since 1970-01-01."""
    from timeutil import days_from_civil
    y, m, d = key.split("-")
    return days_from_civil(int(y), int(m), int(d))


def day_key(z):
    from timeutil import civil_from_days
    return "%04d-%02d-%02d" % civil_from_days(z)


# ------------------------------------------------------------------------------------------------------------ texts
def _utf8_cut(b, max_bytes):
    if len(b) <= max_bytes:
        return b
    b = b[:max_bytes]
    i = len(b) - 1
    while i > 0 and (b[i] & 0xC0) == 0x80:         # back to the lead byte of the last character
        i -= 1
    lead = b[i]
    need = 1 if lead < 0x80 else 2 if lead < 0xE0 else 3 if lead < 0xF0 else 4
    return b[:i] if i + need > len(b) else b       # that character was cut: drop it whole


def pack_str(text, max_bytes=255):
    """str8: u8 length + UTF-8."""
    b = _utf8_cut(text.encode("utf-8"), min(max_bytes, 255))
    return bytes((len(b),)) + b


def pack_str16(text, max_bytes=65535):
    """str16: u16 length + UTF-8."""
    b = _utf8_cut(text.encode("utf-8"), max_bytes)
    return struct.pack("<H", len(b)) + b


def _take(buf, pos, n):
    end = pos + n
    if end > len(buf):
        raise ValueError("text runs past the end")
    return bytes(buf[pos:end]).decode("utf-8"), end


def unpack_str(buf, pos):
    """(text, position after it) of a str8."""
    return _take(buf, pos + 1, buf[pos])


def unpack_str16(buf, pos):
    return _take(buf, pos + 2, struct.unpack_from("<H", buf, pos)[0])


# ------------------------------------------------------------------------------------------------------------ INFO
_INFO = "<BBHB"


def pack_info(info):
    caps = 0
    for name in info["caps"]:
        caps |= 1 << CAPS.index(name)
    return (struct.pack(_INFO, PROTOCOL_VERSION, KINDS.index(info["kind"]), caps, info.get("slot", 0))
            + pack_str(info["name"], 32) + pack_str(info["app"], 16))


def unpack_info(buf):
    version, kind, caps, slot = struct.unpack_from(_INFO, buf, 0)
    name, pos = unpack_str(buf, struct.calcsize(_INFO))
    app, _ = unpack_str(buf, pos)
    return {"version": version, "kind": KINDS[kind] if kind < len(KINDS) else "",
            "caps": [c for n, c in enumerate(CAPS) if caps >> n & 1], "name": name, "app": app, "slot": slot}


# ------------------------------------------------------------------------------------------------------------ TIME
_TIME = "<IhBIB"


def pack_time(t):
    flags = (1 if t.get("has_rtc") else 0) | (2 if t.get("rtc_valid") else 0)
    return struct.pack(_TIME, t["time"], t.get("offset", 0), SOURCES.index(t["source"]),
                       min(t.get("age", 0), 0xFFFFFFFF), flags)


def unpack_time(buf):
    t, offset, source, age, flags = struct.unpack_from(_TIME, buf, 0)
    return {"time": t, "offset": offset, "source": SOURCES[source] if source < len(SOURCES) else "soft", "age": age,
            "has_rtc": bool(flags & 1), "rtc_valid": bool(flags & 2)}


def better_clock(a, b):
    """Which of two TIME records to trust: "a", "b" or None (equally good - nothing to do).
    A hardware clock that says it is not valid counts as a soft one; between equal sources the fresher one wins,
    by more than an hour (a few minutes of difference in age decide nothing)."""
    def rank(v):
        if v["source"] == "rtc" and not v.get("rtc_valid"):
            return 0
        return _SOURCE_RANK.get(v["source"], 0)
    ra, rb = rank(a), rank(b)
    if ra != rb:
        return "a" if ra > rb else "b"
    if abs(a.get("age", 0) - b.get("age", 0)) > 3600:
        return "a" if a.get("age", 0) < b.get("age", 0) else "b"
    return None


# -------------------------------------------------------------------------------------------------------- SETTINGS
def pack_settings(values):
    """{key: text as config.txt has it} -> "KEY=text\\n" lines, UTF-8 (only the synced keys)."""
    return "".join("%s=%s\n" % (k, values[k]) for k in SYNCED_KEYS if k in values).encode("utf-8")


def unpack_settings(buf, known=SYNCED_KEYS):
    """-> {key: text} of the keys in `known`; other lines are skipped."""
    out = {}
    for line in bytes(buf).decode("utf-8").split("\n"):
        key, sep, value = line.partition("=")
        key = key.strip()
        if sep and key in known:
            out[key] = value.strip()
    return out


def training_text(plan):
    """[["blue", 120], ...] -> "blue:120,..." (TRAINING_PLAN in SETTINGS)."""
    return ",".join("%s:%d" % (colour, seconds) for colour, seconds in plan)


def training_plan(text):
    plan = []
    for block in text.split(","):
        colour, sep, seconds = block.strip().partition(":")
        if not sep or colour not in ("blue", "yellow", "orange", "red", "green"):
            raise ValueError("training block %r" % block)
        plan.append([colour, int(seconds)])
    if not 1 <= len(plan) <= 16:
        raise ValueError("training: %d blocks" % len(plan))
    return plan


# --------------------------------------------------------------------------------------------------------- records
_ROUTINE = "<HBBBBBII"


def pack_routine(r):
    if r.get("del"):
        return struct.pack(_ROUTINE, r["id"], _DEL, 0, 0, 0, 0, r["e"], 0) + pack_str("")
    return struct.pack(_ROUTINE, r["id"], _ON if r["on"] else 0, r["h"], r["m"], r["d"] & 127, r.get("to", 255),
                       r.get("e", 0), r.get("c", 0)) + pack_str(r["t"], MAX_ROUTINE_TEXT)


def unpack_routine(buf, pos=0):
    rid, flags, h, m, d, to, e, c = struct.unpack_from(_ROUTINE, buf, pos)
    text, pos = unpack_str(buf, pos + struct.calcsize(_ROUTINE))
    if flags & _DEL:
        return {"id": rid, "e": e, "del": True}, pos
    if h > 23 or m > 59:
        raise ValueError("routine %d: time %d:%d" % (rid, h, m))
    return {"id": rid, "t": text, "h": h, "m": m, "d": d & 127, "on": bool(flags & _ON), "to": to, "e": e, "c": c}, pos


_TODO = "<HBII"
_ITEM = "<BI"


def pack_todo(r):
    if r.get("del"):
        return struct.pack(_TODO, r["id"], _DEL, r["e"], 0) + pack_str16("") + b"\x00"
    items = r.get("items", [])[:MAX_ITEMS]
    out = [struct.pack(_TODO, r["id"], _ON if r["done"] else 0, r.get("e", 0), r.get("c", 0)),
           pack_str16(r["t"], MAX_TODO_TEXT), bytes((len(items),))]
    for item in items:
        out.append(struct.pack(_ITEM, _ON if item["done"] else 0, item.get("c", 0)) + pack_str(item["t"], MAX_ITEM_TEXT))
    return b"".join(out)


def unpack_todo(buf, pos=0):
    rid, flags, e, c = struct.unpack_from(_TODO, buf, pos)
    text, pos = unpack_str16(buf, pos + struct.calcsize(_TODO))
    count = buf[pos]
    pos += 1
    items = []
    for _ in range(count):
        iflags, ic = struct.unpack_from(_ITEM, buf, pos)
        itext, pos = unpack_str(buf, pos + struct.calcsize(_ITEM))
        items.append({"t": itext, "done": bool(iflags & _ON), "c": ic})
    if flags & _DEL:
        return {"id": rid, "e": e, "del": True}, pos
    r = {"id": rid, "t": text, "done": bool(flags & _ON), "e": e, "c": c}
    if items:
        r["items"] = items
    return r, pos


_NOTE = "<HBI"


def pack_note(r):
    if r.get("del"):
        return struct.pack(_NOTE, r["id"], _DEL, r["e"]) + pack_str16("")
    return struct.pack(_NOTE, r["id"], 0, r.get("e", 0)) + pack_str16(r["t"], MAX_NOTE_TEXT)


def unpack_note(buf, pos=0):
    rid, flags, e = struct.unpack_from(_NOTE, buf, pos)
    text, pos = unpack_str16(buf, pos + struct.calcsize(_NOTE))
    if flags & _DEL:
        return {"id": rid, "e": e, "del": True}, pos
    return {"id": rid, "t": text, "e": e}, pos


_STAT = "<HBH"


def pack_stat(s):
    return struct.pack(_STAT, day_number(s["day"]), STAT_KINDS.index(s["k"]), max(0, min(s["n"], 0xFFFF)))


def unpack_stat(buf, pos=0):
    day, kind, n = struct.unpack_from(_STAT, buf, pos)
    if kind >= len(STAT_KINDS):
        raise ValueError("stat kind %d" % kind)
    return {"day": day_key(day), "k": STAT_KINDS[kind], "n": n}, pos + struct.calcsize(_STAT)


_EVENT = "<HIB"


def pack_event(ev):
    return struct.pack(_EVENT, ev["r"], ev["at"], EVENT_RESULTS.index(ev["res"]))


def unpack_event(buf, pos=0):
    rid, at, res = struct.unpack_from(_EVENT, buf, pos)
    if res >= len(EVENT_RESULTS):
        raise ValueError("event result %d" % res)
    return {"r": rid, "at": at, "res": EVENT_RESULTS[res]}, pos + struct.calcsize(_EVENT)


_PACK = {SET_ROUTINES: pack_routine, SET_TODO: pack_todo, SET_NOTES: pack_note, SET_STATS: pack_stat,
         SET_EVENTS: pack_event}
_UNPACK = {SET_ROUTINES: unpack_routine, SET_TODO: unpack_todo, SET_NOTES: unpack_note, SET_STATS: unpack_stat,
           SET_EVENTS: unpack_event}
_INLINE = (SET_STATS, SET_EVENTS)       # sets without ids: LIST answers with the records themselves


def pack_record(which, r):
    return _PACK[which](r)


def unpack_record(which, buf):
    """One whole record (a GET answer, a PUT) -> its dict.  ValueError on anything malformed or left over."""
    if which not in _UNPACK:
        raise ValueError(ERR_UNKNOWN_SET)
    try:
        r, pos = _UNPACK[which](buf, 0)
    except (_STRUCT_ERROR, IndexError, UnicodeError) as e:
        raise ValueError("damaged record: %s" % e)
    if pos != len(buf):
        raise ValueError("%d bytes after the record" % (len(buf) - pos))
    return r


# ------------------------------------------------------------------------------------------------- LIST: the index
_HEADER = "<BIH"
_ENTRY = "<HBII"


def state_time(r):
    """The "c" of a LIST entry: the latest state change of the record, its checklist items included."""
    c = r.get("c", 0)
    for item in r.get("items", ()):
        if item.get("c", 0) > c:
            c = item["c"]
    return c


def pack_list(revision, records):
    """The answer to LIST: header + one entry (id, del, e, c) per record (c: state_time())."""
    return struct.pack(_HEADER, FORMAT_VERSION, revision, len(records)) + b"".join(
        struct.pack(_ENTRY, r["id"], _DEL if r.get("del") else 0, r.get("e", 0), state_time(r)) for r in records)


def pack_inline_list(which, revision, records):
    """The answer to LIST of a set without ids (statistics, events): the records themselves."""
    return struct.pack(_HEADER, FORMAT_VERSION, revision, len(records)) + b"".join(_PACK[which](r) for r in records)


def pack_since(t):
    """The data of a LIST of the events: only those after this (wire) time."""
    return struct.pack("<I", t)


def unpack_since(data):
    return struct.unpack_from("<I", data, 0)[0] if len(data) >= 4 else 0


def unpack_list(which, buf):
    """-> (revision, [entries]): {"id", "e", "c"[, "del"]} - or for statistics / events the records themselves."""
    try:
        fmt, revision, count = struct.unpack_from(_HEADER, buf, 0)
        if fmt != FORMAT_VERSION:
            raise ValueError("format %d, this device knows %d" % (fmt, FORMAT_VERSION))
        pos, out = struct.calcsize(_HEADER), []
        for _ in range(count):
            if which in _INLINE:
                s, pos = _UNPACK[which](buf, pos)
                out.append(s)
                continue
            rid, flags, e, c = struct.unpack_from(_ENTRY, buf, pos)
            pos += struct.calcsize(_ENTRY)
            entry = {"id": rid, "e": e, "c": c}
            if flags & _DEL:
                entry["del"] = True
            out.append(entry)
    except (_STRUCT_ERROR, IndexError) as e:
        raise ValueError("damaged list: %s" % e)
    if pos != len(buf):
        raise ValueError("%d bytes after the list" % (len(buf) - pos))
    return revision, out


# ----------------------------------------------------------------------------------------------- CONTROL: in parts
_FRAME = "<BBHHB"       # command / answer code, set, record id, part number, flags - then the data
FRAME_OVERHEAD = struct.calcsize(_FRAME)


def frame(code, which, rid=0, part=0, last=True, data=b""):
    return struct.pack(_FRAME, code, which, rid, part, FLAG_LAST if last else 0) + data


def parse_frame(buf):
    """A CONTROL write or notification -> (code, set, id, part, last, data)."""
    if len(buf) < FRAME_OVERHEAD:
        raise ValueError("frame of %d bytes" % len(buf))
    code, which, rid, part, flags = struct.unpack_from(_FRAME, buf, 0)
    return code, which, rid, part, bool(flags & FLAG_LAST), bytes(buf[FRAME_OVERHEAD:])


def frames(code, which, rid, payload, room):
    """Cut payload into frames of at most `room` bytes (room = MTU - 3).  An empty payload is one frame."""
    step = room - FRAME_OVERHEAD
    if step <= 0:
        raise ValueError("MTU too small")
    parts = [payload[i:i + step] for i in range(0, len(payload), step)] or [b""]
    return [frame(code, which, rid, n, n == len(parts) - 1, parts[n]) for n in range(len(parts))]


def error_frame(which, rid, error):
    return frame(ANS_ERR, which, rid, data=bytes((error,)))


class Reassembler:
    """Puts the parts of one transfer back together; feed() -> the whole payload after the last part, else None.
    A part out of order raises ValueError(ERR_ORDER) and forgets what was collected (the sender starts again)."""

    def __init__(self, limit=MAX_PAYLOAD):
        self._limit = limit
        self.reset()

    def reset(self):
        self._key = None
        self._next = 0
        self._parts = []
        self._size = 0

    def feed(self, code, which, rid, part, last, data):
        key = (code, which, rid)
        if part == 0:
            self.reset()
            self._key = key
        elif key != self._key or part != self._next:
            self.reset()
            raise ValueError(ERR_ORDER)
        self._size += len(data)
        if self._size > self._limit:
            self.reset()
            raise ValueError(ERR_TOO_BIG)
        self._parts.append(data)
        self._next = part + 1
        if not last:
            return None
        payload = b"".join(self._parts)
        self.reset()
        return payload
