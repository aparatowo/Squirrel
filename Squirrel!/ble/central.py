# ble/central.py - the head of the Bluetooth sync: finds its nodes, syncs them one by one (docs/implementation/en/bluetooth.md 4, 5)
#
# On MicroPython's `bluetooth` module, like ble/peripheral.py: the IRQ handler only queues (copies) what happened, and
# tick() drives a session written as a generator - every step yields Wait(events, timeout) and gets the event back
# (or _Timeout thrown in), so a session reads top to bottom: connect, discover, time, settings, records, reports.
#
#   head = BleHead(NodeData(... slot=0), Peers(...))
#   head.scan(8)        # -> head.found: [(addr, addr_type, name)] of Squirrel! nodes in range
#   head.sync()         # every known node, then a second round for those that still differ
#   head.tick()         # often; head.state "off" / "scanning" / "syncing"; head.status: a line for the screen
#
# Per node: the head's records give the content; a state changed on the node (a tick, a routine switched off) comes
# back to the head (ble/merge.py); records missing from the head's list are deleted on the node, the node's local ones
# (its own slot) are left alone.  The better clock sets the other one.  The node's statistics and routine log are kept
# apart on the head (ble/peers.py).
from ble import protocol as P
from ble.merge import merge, slot_of, HEAD_SLOT
from ble.secrets import SECRETS
from ble.peripheral import _settle, radio_gc, radio_gc_tick, link_pairing, require_pairing

_IRQ_SCAN_RESULT = 5
_IRQ_SCAN_DONE = 6
_IRQ_PERIPHERAL_CONNECT = 7
_IRQ_PERIPHERAL_DISCONNECT = 8
_IRQ_GATTC_SERVICE_RESULT = 9
_IRQ_GATTC_SERVICE_DONE = 10
_IRQ_GATTC_CHARACTERISTIC_RESULT = 11
_IRQ_GATTC_CHARACTERISTIC_DONE = 12
_IRQ_GATTC_DESCRIPTOR_RESULT = 13
_IRQ_GATTC_DESCRIPTOR_DONE = 14
_IRQ_GATTC_READ_RESULT = 15
_IRQ_GATTC_READ_DONE = 16
_IRQ_GATTC_WRITE_DONE = 17
_IRQ_GATTC_NOTIFY = 18
_IRQ_MTU_EXCHANGED = 21
_IRQ_ENCRYPTION_UPDATE = 28
_IRQ_PASSKEY_ACTION = 31
_CODE_TYPED = 1001               # not the stack's: the code the user typed (enter_code())
_PASSKEY_INPUT = 2               # this device types in the code the other one shows
_IO_KEYBOARD_ONLY = 2
_CODE_MS = 90000                 # how long the head waits for the code to be typed

# The head's messages stay English here (the code reads them: results[...].startswith("failed")); a screen shows them
# translated with i18n.fill(text, STATUS_TEMPLATES) - every message this module makes is one of these.
STATUS_TEMPLATES = ("Failed: %s", "Looking for nuts...", "Found %d", "No devices - add one first", "Synced %d of %d",
                    "Connecting: %s", "%s: routines", "%s: To-Dos", "%s: notes", "%s: reports", "Pairing: %s",
                    "Type the code shown on %s", "Securing the link: %s")
# why a session failed (the %s of "Failed: %s" / "failed: %s"); anything else (an OSError) is shown as it is
REASON_TEMPLATES = ("disconnected", "no answer (waited for %s)", "protocol %d, this device speaks %d",
                    "no place for the pairing keys", "wrong code", "pairing method %d not supported",
                    "pairing failed - wrong code?", "not a Squirrel! device", "the Squirrel! service is incomplete",
                    "the node refused (%d)", "the node refused a write (%d) - not paired?")
RESULT_TEMPLATES = ("failed: %s", "clock taken", "no valid clock there", "up to date", "clock set there", "joined as %d",
                    "%d settings", "routines %d/%d", "todo %d/%d", "notes %d/%d", "%d log entries")

_STEP_MS = 8000                  # one GATT operation
_CONNECT_MS = 10000
_SETS = ((P.SET_ROUTINES, "on"), (P.SET_TODO, "done"), (P.SET_NOTES, None))


class _Timeout(Exception):
    pass


class _Refused(_Timeout):
    def __init__(self, code):
        super().__init__("the node refused (%d)" % code)
        self.code = code


class _Wait:
    def __init__(self, events, ms=_STEP_MS):
        self.events, self.ms = events, ms


def _uuid(u):
    import bluetooth
    return bluetooth.UUID(u)


def _hex(addr):
    return "".join("%02x" % b for b in addr)


def _unhex(text):
    return bytes(int(text[i:i + 2], 16) for i in range(0, len(text), 2))


def _service_in(adv):
    """Does this advertisement carry the Squirrel! service UUID?  -> (True/False, the name in it or None)."""
    want, ok, name, i = P.uuid_bytes(P.SERVICE_UUID), False, None, 0
    adv = bytes(adv)
    while i + 1 < len(adv):
        n, kind = adv[i], adv[i + 1]
        if n == 0:
            break
        body = adv[i + 2:i + 1 + n]
        if kind in (0x06, 0x07) and want in body:
            ok = True
        elif kind in (0x08, 0x09):
            try:
                name = body.decode()
            except UnicodeError:
                pass
        i += 1 + n
    return ok, name


class BleHead:
    def __init__(self, data, peers, ble=None, log=None, now_ms=None):
        self.data, self.peers = data, peers
        self._ble = ble
        self._log = log or (lambda text: None)
        self._now = now_ms or _ticks
        self.state = "off"
        self.status = ""
        self.found = []                   # [(addr hex, addr_type, name)] of the last scan
        self.results = {}                 # addr -> a line: what the last sync of that node did (or why it failed)
        self._queue = []
        self._gen = None
        self._wait = None
        self._wait_since = 0
        self._names = {}                  # addr -> name seen in a scan response
        self._notes = []                  # CONTROL notifications not consumed yet
        self._head_revs = {}              # addr -> the head's revisions right after that node's sync
        self._conn = None
        self._chars = {}
        self._room = 20
        self.need_code = False            # pairing: the screen asks for the code the node shows, then enter_code()

    # ---------------------------------------------------------------------------------------------- radio
    def _radio(self):
        if self._ble is None:
            import bluetooth
            self._ble = bluetooth.BLE()
        ble = self._ble
        if not ble.active():
            ble.active(True)
        try:
            ble.config(mtu=256)
        except Exception:
            pass
        if link_pairing():                                # pairing: LE Secure Connections, the code typed in here
            try:
                ble.config(bond=True, le_secure=True, mitm=True, io=_IO_KEYBOARD_ONLY)
            except Exception as e:
                self._log("[BLE] pairing options refused: %s" % e)
        ble.irq(self._irq)
        return ble

    def enter_code(self, code):
        """The 6 digits the user read off the node's screen."""
        self._queue.append((_CODE_TYPED, int(code)))

    def _irq(self, event, data):
        # Runs in the Bluetooth stack's task, on its small stack.  The data tuple, and the addresses, buffers and
        # UUIDs in it, point into the stack's own memory and are valid only during this call: everything kept is
        # copied - bytes(), bluetooth.UUID() - into a new tuple (keeping them reset the Cardputer, 2026-10-12).
        # No parsing, no generators here; tick() does the rest.
        if SECRETS.handles(event):
            return SECRETS.irq(event, data)
        if event == _IRQ_SCAN_RESULT:
            self._queue.append((event, (data[0], bytes(data[1]), bytes(data[4]))))
        elif event == _IRQ_GATTC_READ_RESULT or event == _IRQ_GATTC_NOTIFY:
            self._queue.append((event, (data[0], data[1], bytes(data[2]))))
        elif event == _IRQ_PERIPHERAL_CONNECT or event == _IRQ_PERIPHERAL_DISCONNECT:
            self._queue.append((event, (data[0], data[1], bytes(data[2]))))
        elif event == _IRQ_GATTC_SERVICE_RESULT:
            self._queue.append((event, (data[0], data[1], data[2], _uuid(data[3]))))
        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            self._queue.append((event, (data[0], data[1], data[2], data[3], _uuid(data[4]))))
        elif event == _IRQ_GATTC_DESCRIPTOR_RESULT:
            self._queue.append((event, (data[0], data[1], _uuid(data[2]))))
        elif isinstance(data, tuple):
            # ints only, but the tuple itself is the stack's: tuple(data) would return that same object (MicroPython
            # does not copy a tuple), and the radio overwrote it before tick() read it - the Cardputer reset at random
            # points of a sync (2026-10-13).  list() makes the copy.
            self._queue.append((event, tuple(list(data))))
        else:
            self._queue.append((event, data))

    def stop(self):
        if self._ble is not None:
            try:
                self._ble.gap_scan(None)
            except Exception:
                pass
            _settle()                                   # let the stack's timers run out before it is torn down
            try:
                self._ble.active(False)
            except Exception:
                pass
        self._gen = self._wait = None
        self.state = "off"
        radio_gc(False)

    @property
    def busy(self):
        return self.state != "off"

    # ---------------------------------------------------------------------------------------------- driving
    def _begin(self, gen, state):
        radio_gc(True)                                    # see ble/peripheral.radio_gc(): no collection inside the IRQ
        self._radio()
        self._queue, self._notes = [], []
        self._gen, self.state = gen, state
        self._resume(None)

    def _resume(self, value, error=None):
        try:
            self._wait = self._gen.throw(error) if error is not None else self._gen.send(value)
            self._wait_since = self._now()
        except StopIteration:
            self.stop()
        except Exception as e:
            self._log("[BLE] head: %s: %s" % (type(e).__name__, e))
            self.status = "Failed: %s" % e
            self.stop()

    def tick(self):
        """-> True when the status changed."""
        if self._gen is None:
            return False
        before = (self.state, self.status)
        SECRETS.flush()
        radio_gc_tick()
        while self._queue and self._gen is not None:
            event, data = self._queue.pop(0)
            if event == _IRQ_SCAN_RESULT:
                addr_type, addr, adv = data
                ok, name = _service_in(adv)
                key = _hex(addr)
                if name:
                    self._names[key] = name
                if not ok:
                    continue
                data = (addr_type, key)
            elif event == _IRQ_PERIPHERAL_CONNECT:
                data = (data[0], data[1], _hex(data[2]))
            if event == _IRQ_GATTC_NOTIFY:
                self._notes.append(data[2])
            if self._wait is not None and event in self._wait.events:
                self._resume((event, data))
            elif event == _IRQ_PERIPHERAL_DISCONNECT and self._wait is not None:
                self._resume(None, _Timeout("disconnected"))
        if self._gen is not None and self._wait is not None:
            if _since(self._now(), self._wait_since) > self._wait.ms:
                self._resume(None, _Timeout("no answer (waited for %s)" % ",".join(str(e) for e in self._wait.events)))
        return (self.state, self.status) != before

    # ---------------------------------------------------------------------------------------------- scanning
    def scan(self, seconds=8):
        self._begin(self._scan(seconds), "scanning")

    def _scan(self, seconds):
        self.found, self._names = [], {}
        self.status = "Looking for nuts..."
        self._ble.gap_scan(seconds * 1000, 30000, 30000, True)
        seen = {}
        while True:
            event, data = yield _Wait((_IRQ_SCAN_RESULT, _IRQ_SCAN_DONE), seconds * 1000 + 3000)
            if event == _IRQ_SCAN_DONE:
                break
            addr_type, key = data
            seen[key] = addr_type
        self.found = [(k, t, self._names.get(k, "Squirrel!")) for k, t in seen.items()]
        self.status = "Found %d" % len(self.found)

    # ---------------------------------------------------------------------------------------------- syncing
    def sync(self, only=None, time_only=False):
        """Sync every known node (or the one with address `only`); time_only: just read the clock of the first node
        with a valid hardware clock and set this device's from it (Settings -> Time and date)."""
        self._begin(self._sync_all(only, time_only), "syncing")

    def _sync_all(self, only, time_only):
        nodes = [n for n in self.peers.nodes if only is None or n["addr"] == only]
        if not nodes:
            self.status = "No devices - add one first"
            return
        for round_no in (1, 2):
            # round 2: the nodes that still differ from the head, and those that failed (a sync now and then gets no
            # answer right after connecting - 2026-10-13; a second try usually goes through)
            todo = nodes if round_no == 1 else [n for n in nodes if self._head_revs.get(n["addr"]) != self._revisions()
                                                 or self.results.get(n["addr"], "").startswith("failed")]
            for node in todo:
                if round_no == 2:
                    self._log("[BLE] second round: %s" % node["name"])
                    try:
                        yield _Wait((), 2000)                 # the node advertises again a moment after a disconnect
                    except _Timeout:
                        pass
                try:
                    yield from self._session(node, time_only)
                except Exception as e:                       # one node failing must not stop the others
                    self.need_code = False
                    self.results[node["addr"]] = "failed: %s" % e
                    self._log("[BLE] %s: %s" % (node["name"], e))
                    yield from self._disconnect()
                if time_only and self.results.get(node["addr"], "").startswith("clock"):
                    break
            if time_only:
                break
        done = sum(1 for n in nodes if not self.results.get(n["addr"], "").startswith("failed"))
        self.status = "Synced %d of %d" % (done, len(nodes))
        self._log("[BLE] head: %s" % self.status)

    def _revisions(self):
        return tuple(self.data.revision(self.data.records(which)) for which, _k in _SETS)

    def _disconnect(self):
        conn = getattr(self, "_conn", None)
        self._conn = None
        if conn is None:
            return
        try:
            self._ble.gap_disconnect(conn)
        except Exception:
            return
        try:
            yield _Wait((_IRQ_PERIPHERAL_DISCONNECT,), 3000)
        except _Timeout:
            pass

    def _session(self, node, time_only):
        ble = self._ble
        name = node["name"]
        self.status = "Connecting: %s" % name
        ble.gap_connect(node["type"], _unhex(node["addr"]))
        _ev, (conn, _t, _a) = yield _Wait((_IRQ_PERIPHERAL_CONNECT,), _CONNECT_MS)
        self._conn = conn
        self._room = 20
        try:
            ble.gattc_exchange_mtu(conn)
            _ev, (_c, mtu) = yield _Wait((_IRQ_MTU_EXCHANGED,), 3000)
            self._room = max(20, mtu - 3)
        except (_Timeout, OSError):
            pass
        if require_pairing() and link_pairing():
            yield from self._pair(conn, name)
        self._chars = yield from self._discover(conn)
        info = P.unpack_info((yield from self._read(conn, "info")))
        if info["version"] != P.PROTOCOL_VERSION:
            raise _Timeout("protocol %d, this device speaks %d" % (info["version"], P.PROTOCOL_VERSION))
        yield from self._enable_notify(conn)
        if require_pairing() and not link_pairing():
            yield from self._auth(conn, node)
        log = []
        # the clock: the better one sets the other
        theirs = P.unpack_time((yield from self._read(conn, "time")))
        mine = self.data.time()
        better = P.better_clock(mine, theirs)
        if time_only:
            if theirs.get("rtc_valid"):
                self.data.set_time(theirs)
                self.results[node["addr"]] = "clock taken"
            else:
                self.results[node["addr"]] = "no valid clock there"
            yield from self._disconnect()
            return
        apart = abs(mine["time"] - theirs["time"]) > 2           # the same to two seconds: nothing to set
        if better == "a" and apart:
            yield from self._write(conn, "time", P.pack_time(self.data.time()))
            log.append("clock set there")
        elif better == "b" and apart:
            self.data.set_time(theirs)
            log.append("clock taken")
        if info["slot"] != node["slot"]:
            yield from self._ask(conn, P.CMD_PUT, P.SET_INFO, node["slot"])      # the node joins
            log.append("joined as %d" % node["slot"])
        # settings: the head's (only the keys that differ)
        theirs_s = P.unpack_settings((yield from self._ask(conn, P.CMD_GET, P.SET_SETTINGS)))
        mine_s = self.data.settings()
        diff = {k: v for k, v in mine_s.items() if theirs_s.get(k) != v and k in theirs_s}
        if diff:
            yield from self._ask(conn, P.CMD_PUT, P.SET_SETTINGS, 0, P.pack_settings(diff))
            log.append("%d settings" % len(diff))
        # records
        for which, state_key in _SETS:
            if which == P.SET_TODO and "todo" not in info["caps"]:
                continue
            if which == P.SET_NOTES and "notes" not in info["caps"]:
                continue
            self.status = "%s: %s" % (name, {P.SET_ROUTINES: "routines", P.SET_TODO: "To-Dos", P.SET_NOTES: "notes"}[which])
            sent, taken = yield from self._sync_set(conn, which, state_key)
            if sent or taken:
                log.append("%s %d/%d" % ({P.SET_ROUTINES: "routines", P.SET_TODO: "todo", P.SET_NOTES: "notes"}[which],
                                         sent, taken))
        # reports: statistics, routine log
        self.status = "%s: reports" % name
        if "stats" in info["caps"]:
            _rev, stats = P.unpack_list(P.SET_STATS, (yield from self._ask(conn, P.CMD_LIST, P.SET_STATS)))
            self.peers.save_stats(node["slot"], stats)
        _rev, events = P.unpack_list(P.SET_EVENTS, (yield from self._ask(conn, P.CMD_LIST, P.SET_EVENTS, 0,
                                                                           P.pack_since(node.get("events", 0)))))
        if events:
            self.peers.add_events(node["slot"], events)
            node["events"] = max(e["at"] for e in events)
            log.append("%d log entries" % len(events))
        yield from self._disconnect()
        from timeutil import wire_now
        node["synced"] = wire_now()
        self.peers.save()
        self._head_revs[node["addr"]] = self._revisions()
        self.results[node["addr"]] = ", ".join(log) or "up to date"
        self._log("[BLE] synced %s: %s" % (name, self.results[node["addr"]]))

    def _auth(self, conn, node):
        """Prove this head is paired with the node (ble/auth.py); with a new node, pair first with the code it shows."""
        from ble import auth as A
        name, addr = node["name"], node["addr"]
        store = self.data.auth
        if store is None:
            raise _Timeout("no place for the pairing keys")
        key = store.get(addr)
        if key is not None:
            try:
                yield from self._prove(conn, key)
                return
            except _Refused as e:
                if e.code != P.ERR_NOT_AUTH:
                    raise
                self._log("[BLE] %s does not know this head any more: pairing again" % name)
        self.status = "Pairing: %s" % name
        head_nonce = A.random_bytes(A.NONCE_LEN)
        node_nonce = yield from self._ask(conn, P.CMD_AUTH_HELLO, P.SET_INFO, 0, head_nonce)
        self.need_code = True
        self.status = "Type the code shown on %s" % name.replace("Squirrel! ", "")
        try:
            _ev, code = yield _Wait((_CODE_TYPED,), _CODE_MS)
        finally:
            self.need_code = False
        self.status = "Pairing: %s" % name
        key = A.pair_key("%06d" % code, head_nonce, node_nonce)
        try:
            yield from self._ask(conn, P.CMD_AUTH_CONFIRM, P.SET_INFO, 0, A.confirm_proof(key, node_nonce))
        except _Refused as e:
            raise _Timeout("wrong code" if e.code == P.ERR_BAD_CODE else str(e))
        store.set(addr, key)
        self._log("[BLE] paired with %s" % name)
        yield from self._prove(conn, key)

    def _prove(self, conn, key):
        from ble import auth as A
        challenge = yield from self._ask(conn, P.CMD_AUTH_CHALLENGE, P.SET_INFO)
        yield from self._ask(conn, P.CMD_AUTH_PROVE, P.SET_INFO, 0, A.session_proof(key, challenge))

    def _pair(self, conn, name):
        """Link pairing (nuts.BLE_LINK_PAIRING): encrypt the link: with a node paired before, at once; with a new one, with the code it shows."""
        self.status = "Securing the link: %s" % name
        self._ble.gap_pair(conn)
        while True:
            event, data = yield _Wait((_IRQ_ENCRYPTION_UPDATE, _IRQ_PASSKEY_ACTION, _CODE_TYPED),
                                      _CODE_MS if self.need_code else _STEP_MS)
            if event == _IRQ_PASSKEY_ACTION:
                if data[1] == _PASSKEY_INPUT:
                    self.need_code = True
                    self.status = "Type the code shown on %s" % name.replace("Squirrel! ", "")
                else:
                    raise _Timeout("pairing method %d not supported" % data[1])
            elif event == _CODE_TYPED:
                self.need_code = False
                self.status = "Pairing: %s" % name
                self._ble.gap_passkey(conn, _PASSKEY_INPUT, data)
            else:
                _c, encrypted, authenticated = data[0], data[1], data[2]
                self.need_code = False
                if encrypted and authenticated:
                    self._log("[BLE] link to %s secure%s" % (name, ", bonded" if len(data) > 3 and data[3] else ""))
                    return
                raise _Timeout("pairing failed - wrong code?")

    def _sync_set(self, conn, which, state_key):
        """-> (records written to the node, states taken from it)."""
        head = self.data.records(which)
        _rev, entries = P.unpack_list(which, (yield from self._ask(conn, P.CMD_LIST, which)))
        theirs = {e["id"]: e for e in entries}
        sent = taken = 0
        for h in head:
            e = theirs.get(h["id"])
            if e is None:
                yield from self._put(conn, which, h)
                sent += 1
                continue
            if e["e"] == h.get("e", 0) and e["c"] == P.state_time(h):
                continue
            n = P.unpack_record(which, (yield from self._ask(conn, P.CMD_GET, which, h["id"])))
            if state_key is None:
                merged = h
            else:
                head_new, _node_new, _hw, _nw = merge([h], [n], state_key)
                merged = head_new[0]
            if merged != h:
                self.data.put(which, merged)
                taken += 1
            if merged != n:
                yield from self._put(conn, which, merged)
                sent += 1
        mine = {h["id"] for h in head}
        for rid in theirs:
            if slot_of(rid) == HEAD_SLOT and rid not in mine:
                yield from self._ask(conn, P.CMD_DELETE, which, rid)
                sent += 1
        return sent, taken

    def _put(self, conn, which, r):
        yield from self._ask(conn, P.CMD_PUT, which, r["id"], P.pack_record(which, r))

    # ---------------------------------------------------------------------------------------------- GATT steps
    def _discover(self, conn):
        import bluetooth
        ble = self._ble
        ble.gattc_discover_services(conn)
        start = end = None
        want = bluetooth.UUID(P.SERVICE_UUID)
        while True:
            event, data = yield _Wait((_IRQ_GATTC_SERVICE_RESULT, _IRQ_GATTC_SERVICE_DONE))
            if event == _IRQ_GATTC_SERVICE_DONE:
                break
            if data[3] == want:
                start, end = data[1], data[2]
        if start is None:
            raise _Timeout("not a Squirrel! device")
        ble.gattc_discover_characteristics(conn, start, end)
        names = {bluetooth.UUID(P.INFO_UUID): "info", bluetooth.UUID(P.TIME_UUID): "time",
                 bluetooth.UUID(P.CONTROL_UUID): "control"}
        chars, ends = {}, []
        while True:
            event, data = yield _Wait((_IRQ_GATTC_CHARACTERISTIC_RESULT, _IRQ_GATTC_CHARACTERISTIC_DONE))
            if event == _IRQ_GATTC_CHARACTERISTIC_DONE:
                break
            _c, char_end, value, _props, uuid = data
            ends.append(value)
            for u, n in names.items():
                if uuid == u:
                    chars[n] = value
        if len(chars) < len(names):
            raise _Timeout("the Squirrel! service is incomplete")
        later = sorted(v for v in ends if v > chars["control"])
        chars["control_end"] = (later[0] - 1) if later else end
        return chars

    def _read(self, conn, name):
        self._ble.gattc_read(conn, self._chars[name])
        value = b""
        while True:
            event, data = yield _Wait((_IRQ_GATTC_READ_RESULT, _IRQ_GATTC_READ_DONE))
            if event == _IRQ_GATTC_READ_DONE:
                return value
            value = data[2]

    def _write(self, conn, name, value):
        self._ble.gattc_write(conn, self._chars[name], value, 1)
        _check_write((yield _Wait((_IRQ_GATTC_WRITE_DONE,))))

    def _enable_notify(self, conn):
        import bluetooth
        ble = self._ble
        ble.gattc_discover_descriptors(conn, self._chars["control"] + 1, self._chars["control_end"])
        cccd = None
        while True:
            event, data = yield _Wait((_IRQ_GATTC_DESCRIPTOR_RESULT, _IRQ_GATTC_DESCRIPTOR_DONE))
            if event == _IRQ_GATTC_DESCRIPTOR_DONE:
                break
            if data[2] == bluetooth.UUID(0x2902):
                cccd = data[1]
        if cccd is None:
            cccd = self._chars["control"] + 1                 # where NimBLE puts it
        ble.gattc_write(conn, cccd, b"\x01\x00", 1)
        _check_write((yield _Wait((_IRQ_GATTC_WRITE_DONE,))))

    def _ask(self, conn, code, which, rid=0, payload=b""):
        """One request on CONTROL -> the payload of the DATA answer (b"" for an ACK); ERR raises _Timeout."""
        self._notes = []
        for frame in P.frames(code, which, rid, payload, self._room):
            self._ble.gattc_write(conn, self._chars["control"], frame, 1)
            _check_write((yield _Wait((_IRQ_GATTC_WRITE_DONE,))))
        parts = P.Reassembler()
        while True:
            while not self._notes:
                yield _Wait((_IRQ_GATTC_NOTIFY,))
            got, w, i, part, last, data = P.parse_frame(self._notes.pop(0))
            if (w, i) != (which, rid):
                continue                                      # a late answer to something earlier
            if got == P.ANS_ACK:
                return b""
            if got == P.ANS_ERR:
                raise _Refused(data[0] if data else 0)
            whole = parts.feed(got, w, i, part, last, data)
            if whole is not None:
                return whole


def _check_write(answer):
    """A write the node refused (not paired, ...) ends the session with a reason, not with waiting for an answer."""
    _event, data = answer
    if len(data) > 2 and data[2]:
        raise _Timeout("the node refused a write (%d) - not paired?" % data[2])


def _ticks():
    import time
    return time.ticks_ms()


def _since(a, b):
    import time
    return time.ticks_diff(a, b)
