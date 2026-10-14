# The common data format

*[Polski](../pl/data-format.md) · [Français](../fr/data-format.md) · [Deutsch](../de/data-format.md)*

The records of the whole Squirrel! family: the Cardputer, the T-Watch and any future app
(a phone app, say). Format version **1**. Reference implementation: `Squirrel!/ble/protocol.py` (and its JavaScript
twin `Squirrel!/tools/web/squirrel_protocol.js`, checked byte for byte by `tools/tests/test_web_protocol.py`). How the
sync uses them: [bluetooth.md](bluetooth.md).

## 1. The principle

- **The canonical model is JSON.** Every record has one definition: field names, types, ranges (section 3). That is
  how it looks in JSON files on the ESP32, in a phone app, in the tests.
- **Bluetooth carries a binary encoding** of the same model (section 4) - field for field, nothing lost. A small
  device need not parse JSON: it keeps C structures matching the binary encoding.
- Each device may store data its own way (text files, `done.dat`, C structures). This specification says only what
  is outside; the mapping to the ESP32's files is in section 5.
- Unknown fields are skipped, not refused (a newer version on one device does not break an older one on another). New
  fields come only as optional ones. A change of a field's meaning is a new format version.

## 2. Common fields and rules

| Field | Type | Meaning |
|---|---|---|
| `id` | int 1-65535 | The record's id. Bits 15-13: the author's **slot** - 0 = a **boss** record, 1-6 = a **local** record of the node in that slot, 7 = reserved. Bits 12-0: the author's counter. The boss gives the slots when nodes join. |
| `e` | int | Time of the last **content edit** - the content's version (compared for proposals, 3.8). |
| `c` | int | Time of the last **state change** (on / done / ticked). A content edit does not change it. |
| `del` | bool | Reserved (a tombstone). Not used with a boss: the boss deletes through its list. |

- **Time** = seconds since 1970-01-01 00:00 in the device's **local time** (not UTC; the offset is in `TIME`).
  0 = "never".
- **Text** = UTF-8. Limits are in characters (as on the screens); in the binary encoding in bytes (section 4).
- **The boss and the nodes.** One device of a set is the **boss** (the Cardputer by default): the only author of the
  content of records with slot 0. The others are **nodes**. Merging two copies (`ble/merge.py`), for each `id`:
  - the content of boss records - always from the boss; a boss record missing from the boss's list is deleted on the
    node;
  - the state - from the copy with the greater `c` (a tick on the watch reaches the boss and goes on from there);
  - a node's local records (slot ≠ 0) - the boss does not change, delete or take them (adoption: 3.8).
  So clocks decide only the state; the boss decides the content, and the version `e` finds edit conflicts (3.8).
- **The weekday** is worked out from the date, never taken from `localtime()[6]` (ESP32 firmwares disagree on it).

## 3. The records (JSON)

### 3.1 Routine - `routine`

```json
{"id": 8193, "t": "Pills", "h": 8, "m": 0, "d": 63, "on": true, "to": 255, "e": 1760259600, "c": 1760259600}
```

| Field | Type | Range | Meaning |
|---|---|---|---|
| `t` | str | ≤ 50 characters | the text of the reminder |
| `h`, `m` | int | 0-23, 0-59 | the time |
| `d` | int | 0-127 | the weekdays, bit 0 = Monday ... bit 6 = Sunday |
| `on` | bool | | switched on (state: a change sets `c`) |
| `to` | int | 0-255 | the devices it comes up on: bit n = slot n; 255 = all |

### 3.2 To-Do - `todo` (a checklist too)

```json
{"id": 2, "t": "Shopping\n> milk\n> bread", "done": false, "e": 1760259600, "c": 0,
 "items": [{"t": "milk", "done": true, "c": 1760260000}]}
```

| Field | Type | Range | Meaning |
|---|---|---|---|
| `t` | str | ≤ 500 characters | the whole text; the first line is the title |
| `done` | bool | | done (state) |
| `items` | list | ≤ 64 | checklists only: the state of their items (the `>` lines) |
| `items[].t` | str | ≤ 100 characters | the item's text - the key it is known by |
| `items[].done`, `items[].c` | bool, int | | the item's state and the time it changed (merged per item, like records) |

**A checklist** (a shopping list, the steps of a task ...): the lines after the title that start with `>` are items
ticked one by one (the item's text = the line without the `>` and the spaces around it). Other lines are plain text. A
To-Do without `>` lines is ticked as a whole. When every item is ticked, `done` = true.

### 3.3 Note - `note`

```json
{"id": 3, "t": "Remarks\nthe first line is the title", "e": 1760259600}
```

| Field | Type | Range | Meaning |
|---|---|---|---|
| `t` | str | ≤ 2000 characters | the whole text; the first line is the title |

A note has no state (`c`).

### 3.4 A day's statistic - `stat`

```json
{"day": "2026-10-12", "k": "focus_min", "n": 95}
```

| Field | Type | Meaning |
|---|---|---|
| `day` | str `YYYY-MM-DD` | the day |
| `k` | str | `routines` (routines done), `todos` (To-Dos done), `focus_min` (focus minutes), `steps` |
| `n` | int 0-65535 | that day's value on that device |

Statistics are not merged: each device is the only source of its own; the boss keeps them apart per slot.

### 3.5 Settings - `settings`

An object `{KEY: value}` with the key names of the settings schema (`appconfig_schema.py`). Only the synced keys
(`ble/protocol.py: SYNCED_KEYS`):

| Keys | Type |
|---|---|
| `CUCKOO_ENABLED`, `CUCKOO_QUARTERS` | bool |
| `CUCKOO_QUARTER_VOLUME` | int 0-100 |
| `POMODORO_WORK_MIN` (1-90), `POMODORO_BREAK_MIN` (1-30), `POMODORO_LONG_BREAK_MIN` (1-60), `POMODORO_CYCLES` (1-8) | int |
| `ROUTINE_SNOOZE_MIN` | int 1-60 |
| `QUIET_SOUND_FROM`, `QUIET_SOUND_TO` | str `HH:MM` |
| `QUIET_SOUND_DAYS` | str of 7 characters, `MTWTFSS`, `.` = a day not ticked |
| `TRAINING_PLAN` | a list `[[colour, seconds], ...]`, ≤ 16 blocks, colours: `blue yellow orange red green` |
| `BLE_AUTO_SYNC_MIN` | int 0-240 (0 = sync on demand only) |

Settings are a whole of the device, with no `id`; the boss's are written to the nodes.

### 3.6 Routine event - `event` (the routine log)

```json
{"r": 8193, "at": 1760259600, "res": "done"}
```

| Field | Type | Meaning |
|---|---|---|
| `r` | int | the routine's `id` |
| `at` | int | the time the routine was set for (local time) |
| `res` | str | `done`, `skip` (skipped), `missed` (no answer, after the snoozes too) |

A node keeps events for 60 days and reports them to the boss; the boss takes only those after the last sync.
Events are not merged: each has one source (the node); the boss keeps them apart per slot.

### 3.7 Time - `time`, the device - `info`, the state - `status`

```json
{"time": 1760270400, "offset": 120, "source": "rtc", "age": 10, "has_rtc": true, "rtc_valid": true}
{"version": 1, "kind": "twatch", "caps": ["rtc", "routines", "todo", "stats", "steps"], "name": "T-Watch", "app": "2.0", "slot": 1}
```

`source`: `soft`, `manual`, `rtc`, `ntp`, `peer`. `kind`: `cardputer`, `twatch`, `web` (code 3 is reserved).
`caps`: `rtc todo routines stats pomodoro breathing cuckoo steps hub notes`. `status` (mode, timer): reserved.

### 3.8 Proposal - `proposal` (reserved, a later step)

A content change made on a node (an editor connected straight to the node): it works on the node at once and waits
for the boss's decision.

```json
{"op": "edit", "set": "routine", "id": 1, "base": 1760259600, "rec": {"...": "a record of 3.1"}}
```

| Field | Meaning |
|---|---|
| `op` | `edit` (a boss record), `new` (a new record - local so far), `delete` |
| `base` | the `e` of the boss record the change was made on. The boss takes it without asking if its own `e` is still the same; otherwise it is a conflict (auto: the boss wins; "ask": the user decides) |

The binary encoding comes with the implementation (set `0x0B` is reserved).

## 4. The binary encoding (Bluetooth)

Little-endian. `str8` = u8 length in bytes + UTF-8; `str16` = u16 + UTF-8. Text is cut only on a character boundary.
Time = u32. Common flags: bit 7 = `del` (a tombstone: after the flags only `e`, the rest zeros / empty).

```
routine   u16 id | u8 flags (b0 on, b7 del) | u8 h | u8 m | u8 d | u8 to | u32 e | u32 c | str8 t
todo      u16 id | u8 flags (b0 done, b7 del) | u32 e | u32 c | str16 t
          | u8 number of items | item: u8 flags (b0 done) | u32 c | str8 t
note      u16 id | u8 flags (b7 del) | u32 e | str16 t
stat      u16 day (days since 1970-01-01) | u8 k (0 routines, 1 todos, 2 focus_min, 3 steps) | u16 n
event     u16 r | u32 at | u8 res (0 done, 1 skip, 2 missed)
list      u16 id | u8 flags (b7 del) | u32 e | u32 c           - one entry per record, no content
time      u32 time | i16 offset | u8 source (0 soft, 1 manual, 2 rtc, 3 ntp, 4 peer) | u32 age
          | u8 flags (b0 has_rtc, b1 rtc_valid)
info      u8 version | u8 kind (1 cardputer, 2 twatch, 3 reserved, 4 web) | u16 caps (bits in the order of 3.7)
          | u8 slot | str8 name | str8 app
settings  UTF-8 text, lines KEY=value (as in config.txt); TRAINING_PLAN = "blue:120,yellow:180,..."
```

### The `CONTROL` channel - moving records

```
request (write):        u8 cmd  | u8 set | u16 id | u16 part | u8 flags (b0 last) | data
answer (notification):  u8 code | u8 set | u16 id | u16 part | u8 flags (b0 last) | data

cmd   0x01 LIST   - a set's list: a header (u8 format, u32 revision, u16 count) + "list" entries
      0x02 GET    - one record (id)
      0x03 PUT    - one record (id) in parts; taken after the last part, whole or not at all
      0x04 DELETE - a boss record (id) removed from a node; from the boss only, never a node's local records
      0x05 AUTH_HELLO     - pairing: data 16 B boss nonce -> DATA 16 B node nonce; the node shows 6 digits
      0x06 AUTH_CONFIRM   - pairing: data 16 B proof (below) -> ACK or ERR 7; the node keeps the key
      0x07 AUTH_CHALLENGE - every session: -> DATA 16 B challenge (used once)
      0x08 AUTH_PROVE     - every session: data 16 B answer -> ACK or ERR 6
      (the AUTH_* requests have set 0x01 and id 0)
code  0x10 DATA (the answer to LIST / GET, in parts), 0x11 ACK, 0x12 ERR (data: u8 error code)
errors 1 unknown set, 2 a part out of order, 3 too big, 4 bad data, 5 no such record,
       6 not paired (no AUTH_PROVE in this session), 7 a wrong code when pairing
set   0x01 info (PUT with id = slot: the node joins), 0x03 settings (GET / PUT with id 0; text as above),
      0x04 routines, 0x05 To-Dos, 0x06 statistics, 0x09 notes, 0x0A events, 0x0B proposals (reserved)
```

Statistics and events have no `id`: the answer to `LIST` holds the records themselves (`stat`: the last 60 days;
`event`: those after the time given in the `LIST` request's data, u32 - the boss remembers how far it has read).
The routines can also be fetched with one `GET` of `id` 0 (every record in one answer) - they are small.

### Pairing and the proof of a session (`ble/auth.py`)

HMAC = HMAC-SHA256 cut to 16 bytes; texts in ASCII, `+` joins bytes.

```
key      K   = HMAC(the code as 6 ASCII digits, "squirrel-pair" + boss nonce + node nonce)
CONFIRM      = HMAC(K, "confirm" + node nonce)
PROVE        = HMAC(K, "session" + challenge)
```

The code never goes over the air. A node keeps one key (`"head"`), the boss one key per node (by address); both in
`ble_auth.json` on the internal flash. Until `AUTH_PROVE` succeeds in a session, a node answers ERR 6 to every other
request and ignores a write of `TIME`; `INFO` and `TIME` can be read without pairing. **The records go unencrypted** -
see [bluetooth.md](bluetooth.md) §6.

## 5. Mapping onto the ESP32's files

| Record | File | Notes |
|---|---|---|
| routine | `routines.json` - a list of the JSON objects of 3.1 | older files without `id`, `to`, `e`, `c`: on reading they get an `id` (a boss counter), `to` = 255, `e` = `c` = 0 |
| event | `focus/events.txt` - lines `r,at,res` | 60 days; on the boss: `focus/peers/<slot>/events.txt` |
| todo | `todo/<name>.txt` (the text), `todo/done.dat` (`name,date` = done; `name#item,date` = an item ticked), `todo/meta.json` (`{name: {id, e, c, items: {item: c}}}`) | files with no entry in `meta.json` (from before 2.0, copied over USB): `e` = `c` = 0, the `id` given at the first list |
| note | `notes/<name>.txt`, `notes/meta.json` (`{name: {id, e}}`) | |
| stat | `focus/routines.txt`, `focus/todos.txt`, `focus/focus.txt` (seconds -> minutes), steps | `focus/peers/<slot>/` - the other devices' statistics on the boss |
| settings | `config.txt` | |
