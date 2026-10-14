// squirrel_protocol.js - the Squirrel! record format on the air, for the Web Bluetooth page (and Node, for the tests)
//
// The JavaScript twin of Squirrel!/ble/protocol.py (docs/implementation/en/data-format.md section 4): records are the canonical JSON
// objects of section 3; pack* / unpack* turn them into the bytes the devices send and back.  Little-endian; texts
// UTF-8, cut only on a character boundary; times in seconds since 1970-01-01 LOCAL time.  Kept in step with the
// Python module by tools/tests/test_web_protocol.py (the same records, byte for byte).
(function (root) {
  "use strict";

  const BASE = (n) => "beea" + n.toString(16).padStart(4, "0") + "-f159-4fd4-b434-1d8d3db5b0bc";
  const UUID = {
    SERVICE: BASE(0x0000), INFO: BASE(0x0001), TIME: BASE(0x0002), SETTINGS: BASE(0x0003), ROUTINES: BASE(0x0004),
    TODO: BASE(0x0005), STATS: BASE(0x0006), STATUS: BASE(0x0007), CONTROL: BASE(0x0008), NOTES: BASE(0x0009),
    EVENTS: BASE(0x000a),
  };
  const SET = { INFO: 0x01, SETTINGS: 0x03, ROUTINES: 0x04, TODO: 0x05, STATS: 0x06, NOTES: 0x09, EVENTS: 0x0a };
  const CMD = { LIST: 0x01, GET: 0x02, PUT: 0x03, DELETE: 0x04,
    AUTH_HELLO: 0x05, AUTH_CONFIRM: 0x06, AUTH_CHALLENGE: 0x07, AUTH_PROVE: 0x08 };
  const ANS = { DATA: 0x10, ACK: 0x11, ERR: 0x12 };
  const ERR = { NOT_AUTH: 6, BAD_CODE: 7 };
  const KINDS = ["", "cardputer", "twatch", "nuts", "web"];
  const CAPS = ["rtc", "todo", "routines", "stats", "pomodoro", "breathing", "cuckoo", "steps", "hub", "notes"];
  const SOURCES = ["soft", "manual", "rtc", "ntp", "peer"];
  const STAT_KINDS = ["routines", "todos", "focus_min", "steps"];
  const EVENT_RESULTS = ["done", "skip", "missed"];
  const ON = 0x01, DEL = 0x80, LAST = 0x01, FRAME = 7, FORMAT_VERSION = 1;
  const LIMIT = { ROUTINE: 200, TODO: 2000, ITEM: 255, ITEMS: 64, NOTE: 8000 };

  const enc = new TextEncoder(), dec = new TextDecoder("utf-8", { fatal: true });

  // ---------------------------------------------------------------------------------------------- bytes
  class Writer {
    constructor() { this.parts = []; }
    u8(v) { this.parts.push(Uint8Array.of(v & 0xff)); return this; }
    u16(v) { const b = new Uint8Array(2); new DataView(b.buffer).setUint16(0, v, true); this.parts.push(b); return this; }
    i16(v) { const b = new Uint8Array(2); new DataView(b.buffer).setInt16(0, v, true); this.parts.push(b); return this; }
    u32(v) { const b = new Uint8Array(4); new DataView(b.buffer).setUint32(0, v >>> 0, true); this.parts.push(b); return this; }
    raw(b) { this.parts.push(b); return this; }
    str8(t, max = 255) { const b = cut(enc.encode(t), Math.min(max, 255)); return this.u8(b.length).raw(b); }
    str16(t, max = 65535) { const b = cut(enc.encode(t), max); return this.u16(b.length).raw(b); }
    bytes() {
      const out = new Uint8Array(this.parts.reduce((n, p) => n + p.length, 0));
      let o = 0;
      for (const p of this.parts) { out.set(p, o); o += p.length; }
      return out;
    }
  }

  class Reader {
    constructor(b) { this.b = b instanceof Uint8Array ? b : new Uint8Array(b); this.v = new DataView(this.b.buffer, this.b.byteOffset, this.b.byteLength); this.p = 0; }
    need(n) { if (this.p + n > this.b.length) throw new Error("runs past the end"); }
    u8() { this.need(1); return this.b[this.p++]; }
    u16() { this.need(2); const v = this.v.getUint16(this.p, true); this.p += 2; return v; }
    i16() { this.need(2); const v = this.v.getInt16(this.p, true); this.p += 2; return v; }
    u32() { this.need(4); const v = this.v.getUint32(this.p, true); this.p += 4; return v; }
    take(n) { this.need(n); const s = dec.decode(this.b.subarray(this.p, this.p + n)); this.p += n; return s; }
    str8() { return this.take(this.u8()); }
    str16() { return this.take(this.u16()); }
    end() { if (this.p !== this.b.length) throw new Error((this.b.length - this.p) + " bytes left over"); }
  }

  function cut(b, max) {                       // UTF-8 cut on a character boundary
    if (b.length <= max) return b;
    b = b.subarray(0, max);
    let i = b.length - 1;
    while (i > 0 && (b[i] & 0xc0) === 0x80) i--;
    const lead = b[i], need = lead < 0x80 ? 1 : lead < 0xe0 ? 2 : lead < 0xf0 ? 3 : 4;
    return i + need > b.length ? b.subarray(0, i) : b;
  }

  // ---------------------------------------------------------------------------------------------- time
  function wireNow(date = new Date()) {         // local time, seconds since 1970 (what the devices keep)
    return Math.floor(date.getTime() / 1000) - date.getTimezoneOffset() * 60;
  }
  function dayKey(z) {
    const d = new Date(z * 86400000);
    return d.toISOString().slice(0, 10);
  }
  function dayNumber(key) { return Math.round(Date.parse(key + "T00:00:00Z") / 86400000); }

  // ---------------------------------------------------------------------------------------------- simple values
  function packInfo(i) {
    let caps = 0;
    for (const c of i.caps) caps |= 1 << CAPS.indexOf(c);
    return new Writer().u8(1).u8(KINDS.indexOf(i.kind)).u16(caps).u8(i.slot || 0).str8(i.name, 32).str8(i.app, 16).bytes();
  }
  function unpackInfo(b) {
    const r = new Reader(b), version = r.u8(), kind = r.u8(), caps = r.u16(), slot = r.u8();
    return { version, kind: KINDS[kind] || "", caps: CAPS.filter((_, n) => caps >> n & 1), name: r.str8(), app: r.str8(), slot };
  }
  function packTime(t) {
    return new Writer().u32(t.time).i16(t.offset || 0).u8(SOURCES.indexOf(t.source)).u32(Math.min(t.age || 0, 0xffffffff))
      .u8((t.has_rtc ? 1 : 0) | (t.rtc_valid ? 2 : 0)).bytes();
  }
  function unpackTime(b) {
    const r = new Reader(b), time = r.u32(), offset = r.i16(), source = r.u8(), age = r.u32(), flags = r.u8();
    return { time, offset, source: SOURCES[source] || "soft", age, has_rtc: !!(flags & 1), rtc_valid: !!(flags & 2) };
  }
  function packSettings(values) {
    return enc.encode(Object.entries(values).map(([k, v]) => k + "=" + v + "\n").join(""));
  }
  function unpackSettings(b) {
    const out = {};
    for (const line of dec.decode(b).split("\n")) {
      const i = line.indexOf("=");
      if (i > 0) out[line.slice(0, i).trim()] = line.slice(i + 1).trim();
    }
    return out;
  }

  // ---------------------------------------------------------------------------------------------- records
  function packRoutine(r) {
    if (r.del) return new Writer().u16(r.id).u8(DEL).u8(0).u8(0).u8(0).u8(0).u32(r.e).u32(0).str8("").bytes();
    return new Writer().u16(r.id).u8(r.on ? ON : 0).u8(r.h).u8(r.m).u8(r.d & 127).u8(r.to ?? 255).u32(r.e || 0).u32(r.c || 0)
      .str8(r.t, LIMIT.ROUTINE).bytes();
  }
  function readRoutine(rd) {
    const id = rd.u16(), flags = rd.u8(), h = rd.u8(), m = rd.u8(), d = rd.u8(), to = rd.u8(), e = rd.u32(), c = rd.u32(), t = rd.str8();
    if (flags & DEL) return { id, e, del: true };
    if (h > 23 || m > 59) throw new Error("routine time");
    return { id, t, h, m, d: d & 127, on: !!(flags & ON), to, e, c };
  }
  function packTodo(r) {
    if (r.del) return new Writer().u16(r.id).u8(DEL).u32(r.e).u32(0).str16("").u8(0).bytes();
    const items = (r.items || []).slice(0, LIMIT.ITEMS);
    const w = new Writer().u16(r.id).u8(r.done ? ON : 0).u32(r.e || 0).u32(r.c || 0).str16(r.t, LIMIT.TODO).u8(items.length);
    for (const it of items) w.u8(it.done ? ON : 0).u32(it.c || 0).str8(it.t, LIMIT.ITEM);
    return w.bytes();
  }
  function readTodo(rd) {
    const id = rd.u16(), flags = rd.u8(), e = rd.u32(), c = rd.u32(), t = rd.str16(), n = rd.u8(), items = [];
    for (let k = 0; k < n; k++) { const f = rd.u8(), ic = rd.u32(); items.push({ t: rd.str8(), done: !!(f & ON), c: ic }); }
    if (flags & DEL) return { id, e, del: true };
    const r = { id, t, done: !!(flags & ON), e, c };
    if (items.length) r.items = items;
    return r;
  }
  function packNote(r) {
    if (r.del) return new Writer().u16(r.id).u8(DEL).u32(r.e).str16("").bytes();
    return new Writer().u16(r.id).u8(0).u32(r.e || 0).str16(r.t, LIMIT.NOTE).bytes();
  }
  function readNote(rd) {
    const id = rd.u16(), flags = rd.u8(), e = rd.u32(), t = rd.str16();
    return flags & DEL ? { id, e, del: true } : { id, t, e };
  }
  function packStat(s) { return new Writer().u16(dayNumber(s.day)).u8(STAT_KINDS.indexOf(s.k)).u16(Math.max(0, Math.min(s.n, 0xffff))).bytes(); }
  function readStat(rd) { const day = rd.u16(), k = rd.u8(), n = rd.u16(); return { day: dayKey(day), k: STAT_KINDS[k], n }; }
  function packEvent(ev) { return new Writer().u16(ev.r).u32(ev.at).u8(EVENT_RESULTS.indexOf(ev.res)).bytes(); }
  function readEvent(rd) { const r = rd.u16(), at = rd.u32(), res = rd.u8(); return { r, at, res: EVENT_RESULTS[res] }; }

  const PACK = { [SET.ROUTINES]: packRoutine, [SET.TODO]: packTodo, [SET.NOTES]: packNote, [SET.STATS]: packStat, [SET.EVENTS]: packEvent };
  const READ = { [SET.ROUTINES]: readRoutine, [SET.TODO]: readTodo, [SET.NOTES]: readNote, [SET.STATS]: readStat, [SET.EVENTS]: readEvent };
  const INLINE = [SET.STATS, SET.EVENTS];

  function packRecord(which, r) { return PACK[which](r); }
  function unpackRecord(which, b) { const rd = new Reader(b), r = READ[which](rd); rd.end(); return r; }

  function stateTime(r) {                        // the "c" of a LIST entry: checklist items included
    let c = r.c || 0;
    for (const it of r.items || []) if ((it.c || 0) > c) c = it.c;
    return c;
  }
  function packList(revision, records) {
    const w = new Writer().u8(FORMAT_VERSION).u32(revision).u16(records.length);
    for (const r of records) w.u16(r.id).u8(r.del ? DEL : 0).u32(r.e || 0).u32(stateTime(r));
    return w.bytes();
  }
  function unpackList(which, b) {
    const rd = new Reader(b), fmt = rd.u8(), revision = rd.u32(), n = rd.u16(), out = [];
    if (fmt !== FORMAT_VERSION) throw new Error("format " + fmt);
    for (let k = 0; k < n; k++) {
      if (INLINE.includes(which)) { out.push(READ[which](rd)); continue; }
      const id = rd.u16(), flags = rd.u8(), e = rd.u32(), c = rd.u32(), entry = { id, e, c };
      if (flags & DEL) entry.del = true;
      out.push(entry);
    }
    rd.end();
    return { revision, entries: out };
  }

  // ---------------------------------------------------------------------------------------------- CONTROL frames
  function frames(code, which, id, payload, room) {
    const step = room - FRAME, out = [];
    if (step <= 0) throw new Error("MTU too small");
    const n = Math.max(1, Math.ceil(payload.length / step));
    for (let k = 0; k < n; k++) {
      const part = payload.subarray(k * step, (k + 1) * step);
      out.push(new Writer().u8(code).u8(which).u16(id).u16(k).u8(k === n - 1 ? LAST : 0).raw(part).bytes());
    }
    return out;
  }
  function parseFrame(b) {
    const rd = new Reader(b);
    if (b.length < FRAME) throw new Error("short frame");
    return { code: rd.u8(), which: rd.u8(), id: rd.u16(), part: rd.u16(), last: !!(rd.u8() & LAST), data: rd.b.subarray(FRAME) };
  }

  // ---------------------------------------------------------------------------------------------- pairing
  // ble/auth.py: the key made from the code, HMAC-SHA256 cut to 16 bytes (WebCrypto: https or localhost only)
  const NONCE_LEN = 16;
  const join = (label, b) => new Writer().raw(enc.encode(label)).raw(b).bytes();
  async function hmac(key, msg) {
    const k = await crypto.subtle.importKey("raw", key, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    return new Uint8Array(await crypto.subtle.sign("HMAC", k, msg)).subarray(0, 16);
  }
  function randomBytes(n) { return crypto.getRandomValues(new Uint8Array(n)); }
  const pairKey = (code, headNonce, nodeNonce) =>
    hmac(enc.encode(code), new Writer().raw(join("squirrel-pair", headNonce)).raw(nodeNonce).bytes());
  const confirmProof = (key, nodeNonce) => hmac(key, join("confirm", nodeNonce));
  const sessionProof = (key, challenge) => hmac(key, join("session", challenge));

  // ---------------------------------------------------------------------------------------------- ids
  const COUNTER_BITS = 13;
  function nextId(records, slot = 0) {
    let top = 0;
    for (const r of records) if (r.id >> COUNTER_BITS === slot) top = Math.max(top, r.id & ((1 << COUNTER_BITS) - 1));
    return slot << COUNTER_BITS | (top + 1);
  }
  function checklistItems(text) {                // the ">" lines after the title (todo_editor.checklist_items)
    return text.split("\n").slice(1).map((l) => l.trim()).filter((l) => l.startsWith(">")).map((l) => l.slice(1).trim()).filter(Boolean);
  }

  const api = {
    UUID, SET, CMD, ANS, ERR, CAPS, NONCE_LEN, randomBytes, pairKey, confirmProof, sessionProof, Writer, Reader, wireNow, dayKey, dayNumber,
    packInfo, unpackInfo, packTime, unpackTime, packSettings, unpackSettings,
    packRecord, unpackRecord, packList, unpackList, stateTime, frames, parseFrame, nextId, checklistItems,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SquirrelProtocol = api;
})(typeof window !== "undefined" ? window : globalThis);
