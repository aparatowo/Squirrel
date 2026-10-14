# fakes/bluetooth.py - MicroPython's `bluetooth` module without a radio: for the simulator and the PC tests
#
# BLE() is one object, as on the device.  Besides the API the app uses, it can play the CENTRAL that talks to the app's
# GATT server (ble/peripheral.py):  central_connect(), central_write(handle, data), central_read(handle),
# notified (the notifications sent so far), central_disconnect(), central_mtu(n).
# Two radios can also be linked "over the air" (link(head, node)): the head's gap_scan / gap_connect / gattc_* then
# reach the node's GATT server, and the node's notifications reach the head - the head's side of ble/central.py.

_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3
_IRQ_MTU_EXCHANGED = 21
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
_IRQ_ENCRYPTION_UPDATE = 28
_IRQ_PASSKEY_ACTION = 31
FLAG_WRITE_AUTH = 0x2000

FLAG_READ = 0x0002
FLAG_WRITE = 0x0008
FLAG_NOTIFY = 0x0010


class UUID:
    def __init__(self, value):
        self.value = value.value if isinstance(value, UUID) else value

    def __bytes__(self):
        h = self.value.replace("-", "") if isinstance(self.value, str) else "%04x" % self.value
        return bytes(int(h[i:i + 2], 16) for i in range(len(h) - 2, -1, -2))     # little-endian, as on the device

    def __eq__(self, other):
        return isinstance(other, UUID) and other.value == self.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return "UUID(%r)" % (self.value,)


class _BLE:
    def __init__(self):
        self._active = False
        self._irq = None
        self._values = {}
        self._next_handle = 1
        self.advertising = None
        self.notified = []            # (conn, handle, bytes)
        self.notify_fails = 0         # the next n gatts_notify() calls raise OSError (out of buffers)
        self.conn = None
        self.services = None
        self.addr = b"\x24\x0a\xc4\xfa\x13\xde"
        self.peers = []               # linked radios this one can see (as a central)
        self.head = None              # the central linked to this one (as a node)
        self.subscribed = False
        self.secure = False           # the link is paired / encrypted (as the node sees it)
        self.bonded = set()           # addresses of the radios this one has a bond with
        self.shown_code = None        # the node: the code it showed in the last pairing
        self.wrong_code = False       # the head: answer the next pairing with a wrong code (tests)

    # ---- the API the app uses
    def active(self, v=None):
        if v is None:
            return self._active
        self._active = bool(v)
        if not v:
            if self.conn is not None and self.head is not None:
                self.head._irq(_IRQ_PERIPHERAL_DISCONNECT, (self.conn, 0, self.addr))
            self.advertising, self.conn = None, None
        return self._active

    def config(self, *args, **kwargs):
        if args:
            return {"mac": (0, b"\x00\x11\x22\x33\x44\x55"), "mtu": 256, "gap_name": "sim"}.get(args[0])
        return None

    def irq(self, handler):
        self._irq = handler

    def gatts_register_services(self, services):
        self.services = services
        self._next_handle, self._values = 1, {}      # as on the device: registering again starts the handles anew
        out = []
        for _uuid, chars in services:
            handles = []
            for _c in chars:
                handles.append(self._next_handle)
                self._values[self._next_handle] = b""
                self._next_handle += 2
            out.append(tuple(handles))
        return tuple(out)

    def gatts_set_buffer(self, handle, size, append=False):
        pass

    def gatts_write(self, handle, data):
        self._values[handle] = bytes(data)

    def gatts_read(self, handle):
        return self._values[handle]

    def gatts_notify(self, conn, handle, data=None):
        if self.notify_fails:
            self.notify_fails -= 1
            raise OSError(12)
        value = bytes(data if data is not None else self._values[handle])
        self.notified.append((conn, handle, value))
        if self.head is not None and self.subscribed:
            self.head._irq(_IRQ_GATTC_NOTIFY, (conn, handle, value))

    def gap_advertise(self, interval_us, adv_data=None, resp_data=None, connectable=True):
        self.advertising = None if interval_us is None else (interval_us, adv_data, resp_data)

    def gap_disconnect(self, conn):
        if self.conn == conn:                         # this radio is the node
            self.central_disconnect()
            if self.head is not None:
                self.head._irq(_IRQ_PERIPHERAL_DISCONNECT, (conn, 0, self.addr))
            return
        node = self._node()                           # this radio is the head
        if node is not None and node.conn == conn:
            node.central_disconnect()
            self._irq(_IRQ_PERIPHERAL_DISCONNECT, (conn, 0, node.addr))

    # ---- as a central, over a link()
    def _node(self):
        return self.peers[0] if self.peers else None

    def gap_scan(self, duration_ms, interval_us=None, window_us=None, active=False):
        if duration_ms is None:
            return
        for node in self.peers:
            if node.advertising is not None:
                _i, adv, resp = node.advertising
                self._irq(_IRQ_SCAN_RESULT, (0, node.addr, 0, -50, adv))
                if resp:
                    self._irq(_IRQ_SCAN_RESULT, (0, node.addr, 4, -50, resp))
        self._irq(_IRQ_SCAN_DONE, ())

    def gap_connect(self, addr_type, addr, *args):
        node = self._node()
        if node is None or node.advertising is None or bytes(addr) != node.addr:
            return                                    # nothing there: the head times out
        node.central_connect(1)
        self._irq(_IRQ_PERIPHERAL_CONNECT, (1, addr_type, node.addr))

    def gattc_exchange_mtu(self, conn):
        node = self._node()
        node.central_mtu(185)
        self._irq(_IRQ_MTU_EXCHANGED, (conn, 185))

    def _layout(self):
        """[(service uuid, start, end, [(uuid, flags, value handle)])] of the node."""
        node, out, h = self._node(), [], 1
        for uuid, chars in node.services:
            items = []
            for c in chars:
                items.append((c[0], c[1], h))
                h += 2
            out.append((uuid, items[0][2] - 1, items[-1][2] + 1, items))
        return out

    def gattc_discover_services(self, conn, uuid=None):
        for suuid, start, end, _items in self._layout():
            self._irq(_IRQ_GATTC_SERVICE_RESULT, (conn, start, end, suuid))
        self._irq(_IRQ_GATTC_SERVICE_DONE, (conn, 0))

    def gattc_discover_characteristics(self, conn, start, end, uuid=None):
        for _s, _a, _b, items in self._layout():
            for n, (cuuid, flags, value) in enumerate(items):
                if start <= value <= end:
                    char_end = items[n + 1][2] - 2 if n + 1 < len(items) else end
                    self._irq(_IRQ_GATTC_CHARACTERISTIC_RESULT, (conn, char_end, value, flags, cuuid))
        self._irq(_IRQ_GATTC_CHARACTERISTIC_DONE, (conn, 0))

    def gattc_discover_descriptors(self, conn, start, end):
        for _s, _a, _b, items in self._layout():
            for cuuid, flags, value in items:
                if flags & FLAG_NOTIFY and start <= value + 1 <= end:
                    self._irq(_IRQ_GATTC_DESCRIPTOR_RESULT, (conn, value + 1, UUID(0x2902)))
        self._irq(_IRQ_GATTC_DESCRIPTOR_DONE, (conn, 0))

    def gattc_read(self, conn, handle):
        self._irq(_IRQ_GATTC_READ_RESULT, (conn, handle, self._node().central_read(handle)))
        self._irq(_IRQ_GATTC_READ_DONE, (conn, handle, 0))

    def gattc_write(self, conn, handle, data, mode=0):
        node = self._node()
        status = 0
        if handle not in node._values:                # a descriptor: the CCCD
            node.subscribed = bytes(data)[:1] == b"\x01"
        elif self._needs_auth(node, handle) and not node.secure:
            status = 5                                 # ATT: insufficient authentication - the write does not happen
        else:
            node.central_write(handle, data)
        if mode == 1:
            self._irq(_IRQ_GATTC_WRITE_DONE, (conn, handle, status))

    @staticmethod
    def _needs_auth(node, handle):
        h = 1
        for _uuid, chars in node.services:
            for c in chars:
                if h == handle:
                    return bool(c[1] & FLAG_WRITE_AUTH)
                h += 2
        return False

    # ---- pairing (passkey entry: the node shows the code, the head types it in)
    def gap_pair(self, conn):
        node = self._node()
        if node.addr in self.bonded:                   # paired before: encrypted at once
            node.secure = True
            node._irq(_IRQ_ENCRYPTION_UPDATE, (conn, 1, 1, 1, 16))
            self._irq(_IRQ_ENCRYPTION_UPDATE, (conn, 1, 1, 1, 16))
            return
        node._irq(_IRQ_PASSKEY_ACTION, (conn, 3, 0))  # the node: show a code (it answers with gap_passkey)

    def gap_passkey(self, conn, action, passkey):
        if action == 3:                                # the node chose the code: the head is asked to type it
            self.shown_code = passkey
            if self.head is not None:
                self.head._irq(_IRQ_PASSKEY_ACTION, (conn, 2, 0))
            return
        if action == 2:                                # the head typed a code
            node = self._node()
            ok = passkey == node.shown_code and not self.wrong_code
            node.secure = ok
            if ok:
                self.bonded.add(node.addr)
            node._irq(_IRQ_ENCRYPTION_UPDATE, (conn, int(ok), int(ok), int(ok), 16))
            self._irq(_IRQ_ENCRYPTION_UPDATE, (conn, int(ok), int(ok), int(ok), 16))

    # ---- the central's side (tests, the simulator)
    def central_connect(self, conn=1):
        self.conn = conn
        self.advertising = None
        self._irq(_IRQ_CENTRAL_CONNECT, (conn, 0, b"\x00" * 6))

    def central_mtu(self, mtu):
        self._irq(_IRQ_MTU_EXCHANGED, (self.conn, mtu))

    def central_write(self, handle, data):
        self._values[handle] = bytes(data)
        self._irq(_IRQ_GATTS_WRITE, (self.conn, handle))

    def central_read(self, handle):
        return self._values[handle]

    def central_disconnect(self):
        self.secure = False
        conn, self.conn = self.conn, None
        if conn is not None and self._irq is not None:
            self._irq(_IRQ_CENTRAL_DISCONNECT, (conn, 0, b"\x00" * 6))


def link(head, node):
    """Put two radios in range of each other: `head` (a central) can find and use `node` (a GATT server)."""
    head.peers = [node]
    node.head = head


_the_ble = _BLE()


def BLE():
    return _the_ble


def _reset():
    """A fresh radio (between tests)."""
    global _the_ble
    _the_ble = _BLE()
