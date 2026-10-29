# Proposal: Squirrel! in modules the user switches on

*[Polski](../pl/modules-proposal.md)*

A proposal and its analysis, **not built**. Written 2026-10-19 for a decision; linked from the [backlog](backlog.md).

## 1. The idea

- Squirrel! starts as a **small version**: the clock and the focus tools, nothing more.
- Everything else is a **module** the user switches on in *Settings → Features* (notes, To-Dos, voice notes, routines,
  Bluetooth, Wi-Fi time ...).
- Modules that are off are **greyed out** in the menus (seen, not usable: "switch it on in Settings → Features").
- A module switched on starts **after a restart** and is loaded into memory as everything is today.

Two goals in one: less memory for what is not used, and a calmer device for a person who is overwhelmed by twenty
menu entries on the first day.

## 2. What there is today

| Layer | When | What it decides |
|---|---|---|
| `features.toml` + `port.toml` | **build** | what the hardware allows: a feature without its hardware is not in the firmware at all, its menus, screens and settings are hidden (`port_config.HIDDEN_*`) |
| `_LAZY_SCREENS` | first use | every screen but the clock and the menu is compiled and created only when opened, and given back afterwards (`POWER_UNLOAD_SCREENS`) |
| lazy services | first use | Pomodoro / Training, the metronome, the hourglass; since this branch the low-battery warnings and the clock module's driver |
| settings | at once | many parts already do nothing while their setting is off (cuckoo, auto sync, the battery log) - but they are loaded |

At start-up the Cardputer ADV imports **44 modules** and builds about a dozen objects for features the user may never
use: `StorageManager`, `TodoEditor`, `NoteEditor`, two `DayCounter`s, `RoutineStore` + `Scheduler`, `TimeSyncService`
(Wi-Fi), `AutoSync` (Bluetooth), `BatteryLogger`, the menu tree with every entry.

## 3. How it could be built

### 3.1 A registry of modules

One new file, `modules.py`, describes each module as data (like `features.toml` does for hardware):

```python
MODULES = (
    # name        needs (built features)      depends on   python modules it brings     menus / screens / settings
    ("todo",      (),                         (),          ("todo_editor",),            ...),
    ("notes",     ("notes",),                 (),          ("note_editor",),            ...),
    ("voice",     ("voice_notes",),           (),          (),                          ...),
    ("routines",  (),                         (),          ("scheduler",),              ...),
    ("bluetooth", ("ble_sync",),              (),          ("ble.auto",),               ...),
    ("wifi_time", ("wifi_ntp",),              (),          ("time_sync", "wifi_ntp"),   ...),
    ...
)
BASE = ("clock", "focus")            # always on: the clock, the focus tools, Settings
```

A setting `MODULES` in `config.txt` (a list of names, like the days of the quiet hours) says which are on. `features`
gets a second question next to `has(name)` (built?): `enabled(name)` - built **and** switched on.

### 3.2 Start-up

`SquirrelApp.__init__` creates each part only `if enabled(...)` - the same pattern as `if has("wifi_ntp")` today, one
level up. A module that is off is never imported: its objects, buffers and services do not exist.

### 3.3 Menus: greyed out, not hidden

`menu_tree.py` gets one more optional item per entry: the module it needs. `MenuScreen` draws such an entry in grey and,
on ENTER, shows "Switch it on in Settings → Features" instead of opening it. Hardware that is missing stays hidden as
today (there is nothing to switch on). The touch list (the watch) does the same.

### 3.4 Settings → Features

A screen with one row per module the firmware has: on / off, a line about what it does, and its rough memory cost.
Leaving it after a change asks "Restart now?". Switching a module **off** keeps its files and settings: switching it on
again brings everything back.

### 3.5 Profiles (later)

Ready sets - *Focus only*, *Focus + To-Do*, *Everything* - offered on the first start, so nobody has to understand
the list of modules before using the device.

## 4. Analysis

### 4.1 How much memory it saves - honestly

The code itself is **frozen into the firmware**: it lives in flash and costs no heap whether it is used or not. A module
that is off saves only what its import and its objects build in RAM: module globals, dictionaries and lists, instances,
buffers, open files, a service in the main loop. Per module that is roughly **1-10 KB** (to be measured: see 4.4).
The big consumers are already loaded on demand: the radios (NimBLE and Wi-Fi: tens of KB, only during a sync), the
audio buffers (only while recording / playing), the screens (lazy).

So: on the Cardputer ADV (~160 KB of heap) a "Focus only" start might win **15-30 KB** - useful against
fragmentation and for the screens loaded later, but not a different class of device. The bigger win is the second goal:
**fewer things on the screen** for someone who should not have to ignore them.

### 4.2 What gets harder

| Point | Why | What to decide |
|---|---|---|
| Bluetooth sync | the boss sends To-Dos, notes, routines; a node with the module off - keep the files (they are only files) or refuse them? | **sync stays independent of the modules**: data moves, the UI is what is switched off |
| Routines off | no reminders, no "Planned alarms" on the watch, deep sleep has fewer alarms | a clear line in the Features screen |
| Dependencies | statistics count routines and To-Dos done; the TAB menu and the shortcuts (CTRL+T, CTRL+N) point at modules | each shortcut checks `enabled()`; the statistics show zero for a module that is off |
| Settings of a module that is off | shown or hidden? | hidden in Personalize, kept in `config.txt` |
| Tests | every combination of modules | `compare.sh` with 2-3 profiles; a test that every menu entry has its module or none |
| A restart | MicroPython cannot really unload: switching off at runtime would leave fragments | restart, as the idea says - honest and simple |
| Two layers of "features" | hardware (build) and the user's choice (runtime) can be confused | keep the names apart: `has()` = built, `enabled()` = switched on |

### 4.3 Effort (rough)

| Phase | Work | Size |
|---|---|---|
| 0. Measure | free heap after start-up per part, on the device (`[MEM]` lines, `sq_info.report()`) | small |
| 1. UI only | `modules.py`, `MODULES` setting, Settings → Features, greyed entries, restart prompt; everything still loaded | medium |
| 2. Real loading | `SquirrelApp` creates parts only when enabled; shortcuts, TAB menu, statistics, sync checked | medium-large |
| 3. Profiles | first-start choice, presets | small |

Phase 1 alone already gives the calmer device; phase 2 gives the memory; phase 0 says whether phase 2 is worth it.

### 4.4 How to measure (phase 0)

On the device, in DEV mode: comment out the creation of one part at a time in `SquirrelApp.__init__`, restart, read
`[MEM] free heap after start-up` from the boot log; three runs each (the heap varies). The difference is that part's
cost. A table of those numbers belongs in the Features screen ("about 6 KB").

## 5. Recommendation

1. Do **phase 0** first: ten measurements on the Cardputer ADV decide whether the memory part is worth it.
2. Do **phase 1** in any case: greyed-out modules and *Settings → Features* serve the people Squirrel! is for, whatever
   the memory says.
3. Keep **Bluetooth sync and the data on disk independent of the modules**: switching a module off hides it; it never
   deletes, refuses or changes data.
4. Default for a new device: *Focus + To-Do* (the To-Do list is what most people come for), *Everything* one tap away.

Open questions for the author: what exactly is in the small version (the To-Do list?); greyed out or hidden for the
watch's small screen; does a module switched off keep sending its data in a sync (recommended: yes).
