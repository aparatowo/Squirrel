# Bluetooth sync - design

*[Polski](../pl/bluetooth.md) · [Français](../fr/bluetooth.md) · [Deutsch](../de/bluetooth.md)*

How the Squirrel! devices sync over Bluetooth Low Energy, as built in 2.0. The records and their encoding:
[data-format.md](data-format.md). For users: [guides/en/bluetooth.md](../../guides/en/bluetooth.md). Open issues:
[backlog.md](backlog.md).

## 1. Choices, and why

| Choice | Why |
|---|---|
| MicroPython's raw `bluetooth` module (IRQ handler + `tick()`), not `aioble` | `aioble` is not in the firmware, and the app has no asyncio: it runs on one main loop of ticked services. An IRQ handler that only queues, and a `tick()` that does the work, fit that loop and need less RAM. |
| One protocol in `ble/` for every device; the role from `features.toml` | The Bluetooth stack (NimBLE) is the same on the ESP32 and the ESP32-S3; devices differ only in their role (boss / node) and in what data they have. |
| A canonical JSON model + one binary encoding on the air | Every implementation - the phone app, a C one on a small watch - has the same records; on the air one compact codec that needs no JSON parser. |
| One `SETTINGS` set in the `config.txt` text form | The app already has a schema with validation (`appconfig_schema.py`); a new setting needs no new characteristic. |
| Sync sessions, not a radio always on | An ESP32 cannot light-sleep with the BT controller on, and a deep sleep turns the radio off: advertising all the time would eat the watch's battery. The radio is on only for a session, like Wi-Fi for the time. |
| The better clock sets the worse one | The Cardputer often has no hardware clock; the watch has one. Time goes from Wi-Fi time > hardware clock > set by hand > the soft clock. |
| Pairing with a code in the application, not (yet) link encryption | See section 6. |

## 2. Roles

One device of a set is the **boss** (`head` in the code: `BleHead`, `ble_head_screen.py`, `features.toml` `ble_hub`;
on the screens: the nodes wait for *the squirrel*, which looks for *nuts*) - the only author of content (the
Cardputer: it has the keyboard). The others are **nodes**. A node takes one connection at a time.

```
   Web Bluetooth page (phone / computer)
            │  connects to the boss (or to a node)
            ▼
   BOSS: Cardputer - central towards the nodes; peripheral towards the page ("Be visible")
    ├── T-Watch        - node (peripheral)
    └── (other watches later - nodes too)
```

| Data | Boss | Node (watch) | Web page |
|---|---|---|---|
| To-Do / checklist content | writes | reads | writes (through the boss) |
| To-Do and checklist item ticks | ✅ | ✅ | ✅ |
| Routines: text, time, days, devices | writes | reads | writes (through the boss) |
| Routine on / off | ✅ | ✅ | ✅ |
| Statistics, routine log | its own / each node's / together | its own, reported | - |
| Synced settings | ✅ | from the boss | ✅ |
| Time | by clock quality | by clock quality | sets it from the phone |

## 3. GATT profile

One service for the whole family; the characteristics share the base and differ in the second group of digits.
Base: `beeaXXXX-f159-4fd4-b434-1d8d3db5b0bc`.

| `XXXX` | Name | Properties | Content |
|---|---|---|---|
| `0000` | Squirrel! service | - | advertised: this is how a scanner knows the family |
| `0001` | `INFO` | R | protocol version, device kind, capability mask, slot, name, app version |
| `0002` | `TIME` | R / W | local time, UTC offset, clock source and age; refreshed every second; a write sets the clock (paired bosses only) |
| `0003` | `SETTINGS` | R | the settings' revision (the settings themselves through `CONTROL`, set `0x03`) |
| `0004` | `ROUTINES` | R | revision of the routines |
| `0005` | `TODO` | R | revision of the To-Dos |
| `0006` | `STATS` | R | revision of the statistics |
| `0007` | `STATUS` | R / N | reserved: mode, timer state, battery |
| `0008` | `CONTROL` | W / N | requests and answers: list, get, put, delete, pairing ([data-format.md](data-format.md) §4) |
| `0009` | `NOTES` | R | revision of the notes (devices with notes only) |
| `000a` | `EVENTS` | R | revision of the routine log |

Capability bits in `INFO`: 0 hardware clock, 1 To-Do, 2 routines, 3 statistics, 4 Pomodoro, 5 breathing, 6 cuckoo,
7 steps, 8 hub, 9 notes. The boss syncs only what a node reports.

## 4. A session

1. The node advertises the service for a window (2 minutes from its Bluetooth screen, 90 s for an automatic sync).
2. The boss connects to each known node in turn (it remembers them in `ble.json`: address, slot, last sync).
3. MTU exchange, service discovery, `INFO` (protocol version), notifications on `CONTROL`.
4. **Pairing / proof** (section 6).
5. **The clock:** the better one sets the other (no write if they agree to 2 seconds).
6. **Joining:** a node whose slot differs is given its slot (`PUT` on set `INFO`). Its records from before - copied
   over USB, say - move to that slot and become its local records.
7. **Settings:** the boss writes the synced keys that differ (`ble/protocol.SYNCED_KEYS`).
8. **Records** - routines, To-Dos, notes: the node's list of each set first (id, edit time `e`, state time `c`), then
   only the records that differ, in both directions (section 5).
9. **Reports:** the node's statistics (the last 60 days) and its routine log since the last sync; the boss keeps them
   per node in `focus/peers/<slot>/`.
10. Disconnect. The node stays visible for 15 s more, for a second round.

**The second round:** after the first, the boss has everything, but the node synced first does not yet know the
state changes the later ones brought (a tick on the watch, for the next device). The boss connects again to the nodes
whose lists still differ - and to those that failed in the first round.

A record goes in parts and is taken whole or not at all: a broken connection spoils nothing, and only one record at
a time is in memory.

## 5. Who is right

Per record (`ble/merge.py`):

- **Content** of the boss's records (slot 0 in the id) always comes from the boss. A boss record missing from the
  boss's list is deleted on the node.
- **State** - a routine on / off, a To-Do done, a checklist item ticked - comes from the copy where it changed later
  (`c`). Each checklist item has its own time, so ticking different items on two devices does not clash.
- **A node's local records** (its slot in the id) are never changed, deleted or taken by the boss.

Clocks decide only state (a conflict is two different ticks of one record: rare and harmless); content does not
depend on time, so a wrong clock cannot overwrite an edit.

**Checklists:** the lines of a To-Do that start with `>` are its items. They are recognised by the content, not the
title, so they work the same on every device; the ticks are kept beside the file (`todo/done.dat`), so the text never
changes.

**Routines on chosen devices:** a routine's `to` field is a bit mask of slots (bit n = slot n; 255 = every device,
the ones added later too). Each device fires only the routines that have its bit.

## 6. Pairing and security

**In 2.0: pairing in the application** (`ble/auth.py`; the commands in [data-format.md](data-format.md) §4).

- **Pairing (once):** the boss sends a random nonce (`AUTH_HELLO`); the node answers with its own and shows a 6-digit
  code; the user types it on the boss; both derive `K = HMAC-SHA256(code, "squirrel-pair" + nonces)[:16]`, and the
  boss proves it has it (`AUTH_CONFIRM`). The code itself never goes over the air.
- **Every session:** the node gives a fresh one-time challenge (`AUTH_CHALLENGE`); the boss answers with
  `HMAC(K, "session" + challenge)` (`AUTH_PROVE`). Until then the node refuses everything (error 6) but reading `INFO`
  and `TIME`, and ignores a write of the time.
- **Keys:** `ble_auth.json` on the internal flash - never on a removable card. Forgetting a device on the boss deletes
  its key; a node that lost its key asks for a new code. The Web Bluetooth page keeps its key in the browser's
  `localStorage`, per device.

> ⚠️ **What this does not protect.** The records go **unencrypted**: someone in radio range with BLE sniffing gear
> can read them during a sync (not change them, not sync a device without the key). An overheard pairing lets the key
> be found offline (the code has 6 digits). The guides tell users to pair away from strangers and to keep secrets out
> of synced notes.

**Link encryption (LE Secure Connections)** is in the code but off (`nuts.BLE_LINK_PAIRING = False`): a passkey shown
on the node, bonds kept by the app (`ble/secrets.py`, the IRQ's `GET_SECRET` / `SET_SECRET`), and a fix to NimBLE for
the central's passkey events (`firmware_patches/0001-nimble-central-passkey.patch`). It worked, but the Cardputer reset
during some sessions - which turned out to be another bug (backlog A).

## 7. Automatic sync

`BLE_AUTO_SYNC_MIN` (0 = on demand; 15 ... 240) - `ble/auto.py`. The sessions are aligned to the clock: the minutes of
the day divisible by the period. The node is an alarm source (`alarms.py`), so a watch in deep sleep wakes for each
slot and advertises for 90 s; the boss starts 20 s after the slot. A slot is skipped while the radio is taken (a
Bluetooth screen, the Wi-Fi time sync) or when a node needs pairing (that needs the user). A Bluetooth screen opened
during an automatic session stops it. The setting is synced from the boss, so the nodes follow it.

## 8. MicroPython on the ESP32: what to know

- The IRQ handler runs on the NimBLE task's stack, in the middle of its work. The data it gets - the tuple, the
  addresses, the buffers, **the UUID objects** - is valid only during the call: everything kept is copied
  (`bytes(...)`, `bluetooth.UUID(...)`). **`tuple(data)` is not a copy**: MicroPython returns the very same tuple, and
  keeping it reset the Cardputer at random points of a sync until it was found (`tuple(list(data))` copies).
- No generators, no parsing in the handler; `tick()` does that. The handler must answer `GET_SECRET` / `SET_SECRET`
  (returning nothing to `SET_SECRET` reset the Cardputer).
- While the radio works, the automatic garbage collection is off and `tick()` collects from the main loop
  (`radio_gc`): a collection started by an allocation in the IRQ ran on the NimBLE task's small stack.
- The background services pause during a session (`ServiceManager.paused`), so the main loop answers the radio
  promptly.
- Turning the radio off right after a session raced NimBLE's timers: `_settle()` waits 100 ms first.

## 9. The code

```
ble/protocol.py     UUIDs, record codecs, frames, SYNCED_KEYS - plain Python, tested on the PC
ble/merge.py        boss copy + node copy -> the result (content from the boss, state by time, local untouched)
ble/peripheral.py   the node: GATT server, IRQ, parts, pairing answers, tick()
ble/central.py      the boss: scan, connect, the session as a generator driven by tick()
ble/node_data.py    the app's data as records (routines, To-Dos, notes, settings, statistics, time)
ble/peers.py        the boss's devices (ble.json) and their reports (focus/peers/<slot>/)
ble/auth.py         pairing with a code, the proof of every session, the key store
ble/secrets.py      the bonds of link pairing (off)
ble/auto.py         automatic sync on the clock
screens/ble_head_screen.py   the boss's Bluetooth screen (devices, Add device, Sync now, Auto sync, quick sync)
screens/ble_sync_screen.py   the node's Bluetooth screen (waiting, the pairing code)
tools/web/                   the Web Bluetooth page and its JavaScript codec
```

`features.toml`: `ble_sync` (every port with `[radio] ble = true`: the node part), `ble_hub` (a port with a keyboard
too: the boss part).

## 10. Not yet built

- **Edits on a node** (a phone connected to the watch): applied at once, kept as *proposals* with the version they were
  made on; the boss decides at the next sync - accepted if it did not change that record meanwhile, a conflict
  otherwise; new records stay local or are adopted. A `SYNC_MODE` of *auto* / *ask* with a screen of differences
  (send / take / skip per category). Set `0x0B` is reserved for it.
- **A new boss:** taking a full copy of the boss's records from any node, the ids and counters with it, and pairing
  the nodes again.
- **Small devices:** the protocol is meant to be implementable in C without dynamic allocation.
