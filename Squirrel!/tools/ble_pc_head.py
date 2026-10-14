# tools/ble_pc_head.py - the PC as the head of the Bluetooth sync, for testing a node (the watch) without a Cardputer
#
# Needs a Bluetooth adapter and bleak (pip install bleak; Linux / macOS / Windows).  On the node open
# Settings -> Bluetooth sync, then, from the folder with squirrel_app.py:
#     python3 tools/ble_pc_head.py            # finds the first Squirrel! node, prints what it has
#     python3 tools/ble_pc_head.py --name T-Watch
# It reads INFO and TIME and lists / fetches every record of every data set (read only: nothing is written).
# The first time it pairs with the node like a head (ble/auth.py): type the code the node shows.  The key is kept in
# ~/.squirrel_pc_head.json.
import argparse
import asyncio
import os
import sys

sys.path.insert(0, ".")
from bleak import BleakClient, BleakScanner
from ble import auth as A
from ble import protocol as P

SET_SETTINGS = 0x03
_NAMES = {P.SET_ROUTINES: "routines", P.SET_TODO: "To-Dos", P.SET_NOTES: "notes"}


async def run(name):
    dev = None
    for _ in range(3):
        found = await BleakScanner.discover(timeout=8, service_uuids=[P.SERVICE_UUID])
        found = [d for d in found if not name or name in (d.name or "")]
        if found:
            dev = found[0]
            break
    if dev is None:
        print("no Squirrel! node found - is Settings -> Bluetooth sync open on it?")
        return 1
    print("found", dev.name, dev.address)
    async with BleakClient(dev) as c:
        print("INFO ", P.unpack_info(await c.read_gatt_char(P.INFO_UUID)))
        print("TIME ", P.unpack_time(await c.read_gatt_char(P.TIME_UUID)))
        answers = asyncio.Queue()
        await c.start_notify(P.CONTROL_UUID, lambda _h, d: answers.put_nowait(bytes(d)))

        async def ask(code, which, rid=0, payload=b""):
            for frame in P.frames(code, which, rid, payload, max(20, c.mtu_size - 3)):
                await c.write_gatt_char(P.CONTROL_UUID, frame, response=True)
            parts = P.Reassembler()
            while True:
                got, which_, rid_, part, last, data = P.parse_frame(await asyncio.wait_for(answers.get(), 10))
                if got == P.ANS_ACK:
                    return b""
                if got != P.ANS_DATA:
                    raise RuntimeError("answer %d %r" % (got, data))
                whole = parts.feed(got, which_, rid_, part, last, data)
                if whole is not None:
                    return whole

        store = A.AuthStore(os.path.expanduser("~/.squirrel_pc_head.json"))
        key = store.get(dev.address)
        if key is None:
            head_nonce = A.random_bytes(A.NONCE_LEN)
            node_nonce = await ask(P.CMD_AUTH_HELLO, P.SET_INFO, 0, head_nonce)
            code = (await asyncio.get_running_loop().run_in_executor(None, input, "code shown on the node: ")).strip()
            key = A.pair_key(code.replace(" ", ""), head_nonce, node_nonce)
            await ask(P.CMD_AUTH_CONFIRM, P.SET_INFO, 0, A.confirm_proof(key, node_nonce))
            store.set(dev.address, key)
            print("paired")
        challenge = await ask(P.CMD_AUTH_CHALLENGE, P.SET_INFO)
        await ask(P.CMD_AUTH_PROVE, P.SET_INFO, 0, A.session_proof(key, challenge))
        for which, label in _NAMES.items():
            _rev, entries = P.unpack_list(which, await ask(P.CMD_LIST, which))
            print("%s: %d" % (label, len(entries)))
            for e in entries:
                print("   ", P.unpack_record(which, await ask(P.CMD_GET, which, e["id"])))
        print("stats:", P.unpack_list(P.SET_STATS, await ask(P.CMD_LIST, P.SET_STATS))[1])
        print("routine log:", P.unpack_list(P.SET_EVENTS, await ask(P.CMD_LIST, P.SET_EVENTS))[1])
        print("settings:", P.unpack_settings(await ask(P.CMD_GET, SET_SETTINGS)))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The PC as the head of the Bluetooth sync (read only).")
    ap.add_argument("--name", help="part of the node's name (default: the first node found)")
    sys.exit(asyncio.run(run(ap.parse_args().name)))
