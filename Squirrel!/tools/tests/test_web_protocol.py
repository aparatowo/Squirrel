# tools/tests/test_web_protocol.py - the Web Bluetooth page's codec (tools/web/squirrel_protocol.js) against
# ble/protocol.py: the same records must give the same bytes, and the bytes the same records.  Needs Node.js.
#     python3 tools/tests/test_web_protocol.py        (from the folder with squirrel_app.py)
import json
import subprocess
import sys
import tempfile
sys.path.insert(0, ".")
from ble import auth as A
from ble import protocol as P

routine = {"id": 8193, "t": "Leki ąę", "h": 8, "m": 0, "d": 63, "on": True, "to": 1, "e": 1750000000, "c": 1760000000}
todo = {"id": 2, "t": "Zakupy\n> mleko\n> chleb", "done": False, "e": 5, "c": 0,
        "items": [{"t": "mleko", "done": True, "c": 7}, {"t": "chleb", "done": False, "c": 0}]}
note = {"id": 9, "t": "Uwagi\n" + "ł" * 300, "e": 3}
cases = [
    ("record", P.SET_ROUTINES, routine, P.pack_record(P.SET_ROUTINES, routine)),
    ("record", P.SET_ROUTINES, {"id": 3, "e": 9, "del": True}, P.pack_record(P.SET_ROUTINES, {"id": 3, "e": 9, "del": True})),
    ("record", P.SET_TODO, todo, P.pack_record(P.SET_TODO, todo)),
    ("record", P.SET_TODO, {"id": 4, "t": "Zadzwonić", "done": True, "e": 1, "c": 2},
     P.pack_record(P.SET_TODO, {"id": 4, "t": "Zadzwonić", "done": True, "e": 1, "c": 2})),
    ("record", P.SET_NOTES, note, P.pack_record(P.SET_NOTES, note)),
    ("record", P.SET_STATS, {"day": "2026-10-12", "k": "focus_min", "n": 95},
     P.pack_record(P.SET_STATS, {"day": "2026-10-12", "k": "focus_min", "n": 95})),
    ("record", P.SET_EVENTS, {"r": 1, "at": 1760259600, "res": "missed"},
     P.pack_record(P.SET_EVENTS, {"r": 1, "at": 1760259600, "res": "missed"})),
    ("info", 0, {"version": 1, "kind": "twatch", "caps": ["rtc", "routines", "steps"], "name": "T-Watch", "app": "2.0", "slot": 1},
     P.pack_info({"kind": "twatch", "caps": ["rtc", "routines", "steps"], "name": "T-Watch", "app": "2.0", "slot": 1})),
    ("time", 0, {"time": 1760270400, "offset": 120, "source": "rtc", "age": 10, "has_rtc": True, "rtc_valid": True},
     P.pack_time({"time": 1760270400, "offset": 120, "source": "rtc", "age": 10, "has_rtc": True, "rtc_valid": True})),
    ("list", P.SET_TODO, {"revision": 7, "entries": [{"id": 2, "e": 5, "c": 7}]}, P.pack_list(7, [todo])),
    ("list", P.SET_STATS, {"revision": 1, "entries": [{"day": "2026-10-11", "k": "steps", "n": 8000}]},
     P.pack_inline_list(P.SET_STATS, 1, [{"day": "2026-10-11", "k": "steps", "n": 8000}])),
]
payload = P.pack_record(P.SET_NOTES, note)
frames = [f.hex() for f in P.frames(P.CMD_PUT, P.SET_NOTES, 9, payload, 60)]
head_nonce, node_nonce, challenge = bytes(range(16)), bytes(range(16, 32)), bytes(range(32, 48))
key = A.pair_key("042917", head_nonce, node_nonce)
auth = {"code": "042917", "head": head_nonce.hex(), "node": node_nonce.hex(), "challenge": challenge.hex(),
        "key": key.hex(), "confirm": A.confirm_proof(key, node_nonce).hex(), "session": A.session_proof(key, challenge).hex()}
vectors = {"auth": auth, "cases": [[kind, which, rec, data.hex()] for kind, which, rec, data in cases],
           "frames": {"payload": payload.hex(), "room": 60, "hex": frames}}

NODE = r'''
const P = require(process.argv[2]);
const v = JSON.parse(require("fs").readFileSync(process.argv[3], "utf8"));
const hex = (b) => Buffer.from(b).toString("hex"), bin = (h) => new Uint8Array(Buffer.from(h, "hex"));
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
let failed = 0;
const fail = (what, got, want) => { failed++; console.log("FAIL", what, JSON.stringify(got), JSON.stringify(want)); };
const sortKeys = (o) => Array.isArray(o) ? o.map(sortKeys) : (o && typeof o === "object")
  ? Object.fromEntries(Object.keys(o).sort().map((k) => [k, sortKeys(o[k])])) : o;
for (const [kind, which, rec, data] of v.cases) {
  let packed, unpacked;
  if (kind === "record") { packed = P.packRecord(which, rec); unpacked = P.unpackRecord(which, bin(data)); }
  else if (kind === "info") { packed = P.packInfo(rec); unpacked = P.unpackInfo(bin(data)); }
  else if (kind === "time") { packed = P.packTime(rec); unpacked = P.unpackTime(bin(data)); }
  else if (kind === "list") { packed = null; unpacked = P.unpackList(which, bin(data)); }
  if (packed !== null && hex(packed) !== data) fail(kind + " pack " + which, hex(packed), data);
  if (!same(sortKeys(unpacked), sortKeys(rec))) fail(kind + " unpack " + which, unpacked, rec);
}
const fr = P.frames(0x03, 0x09, 9, bin(v.frames.payload), v.frames.room).map(hex);
if (!same(fr, v.frames.hex)) fail("frames", fr, v.frames.hex);
const f0 = P.parseFrame(bin(v.frames.hex[0]));
if (!(f0.code === 3 && f0.which === 9 && f0.id === 9 && f0.part === 0 && !f0.last)) fail("parse frame", f0, "PUT 9 9 0");
if (P.checklistItems("Zakupy\n> mleko\n  >chleb\nopis\n>") .join() !== "mleko,chleb") fail("checklist", "", "");
if (P.nextId([{id: 1}, {id: 7 << 13 | 4}], 7) !== (7 << 13 | 5)) fail("nextId", "", "");
(async () => {
  const a = v.auth, key = await P.pairKey(a.code, bin(a.head), bin(a.node));
  if (hex(key) !== a.key) fail("pair key", hex(key), a.key);
  if (hex(await P.confirmProof(key, bin(a.node))) !== a.confirm) fail("confirm proof", "", a.confirm);
  if (hex(await P.sessionProof(key, bin(a.challenge))) !== a.session) fail("session proof", "", a.session);
  console.log(failed ? "FAILED: " + failed : "OK");
  process.exit(failed ? 1 : 0);
})();
'''

with tempfile.TemporaryDirectory() as d:
    with open(d + "/vectors.json", "w") as f:
        json.dump(vectors, f)
    with open(d + "/check.js", "w") as f:
        f.write(NODE)
    import os
    js = os.path.abspath("tools/web/squirrel_protocol.js")
    sys.exit(subprocess.call(["node", d + "/check.js", js, d + "/vectors.json"]))
