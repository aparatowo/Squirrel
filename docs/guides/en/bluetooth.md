# Bluetooth sync

*[Polski](../pl/bluetooth.md) · [Français](../fr/bluetooth.md) · [Deutsch](../de/bluetooth.md)*

Your Squirrel! devices keep each other up to date over Bluetooth. Version 2.0. How it is built (for developers):
[implementation/en/bluetooth.md](../../implementation/en/bluetooth.md).

## What goes where

One device is the **boss** - the Cardputer: it has the keyboard, so content is written there. The others are
**nodes** - today the watch.

| What | Direction |
|---|---|
| the content of routines, To-Dos and notes | boss → node (the boss is the only author) |
| ticks: To-Dos, checklist items, a routine on / off | both ways - the later change wins |
| the routine log (done / skipped / no answer), statistics | node → boss, kept apart for each device |
| settings: cuckoo, Pomodoro, training plan, quiet hours, routine snooze, auto sync | boss → node |
| the time | from the better clock to the worse one (Wi-Fi time > hardware clock > set by hand) |

What the watch had before it joined (To-Dos copied over USB, say) stays the watch's own: the boss neither overwrites
nor deletes it.

## The first time: pairing

1. **Watch:** *Settings → Bluetooth* (or swipe down on the clock) - it waits for the boss for 2 minutes.
2. **Cardputer:** *Settings → Bluetooth → Add device* - it looks for devices; ENTER on the watch.
3. The watch shows **6 digits**; type them on the Cardputer and press ENTER.

The code is needed only once. A device that has not paired gets nothing and changes nothing.

<img src="../../../shots/cardputer/en/bluetooth.png" width="360"> <img src="../../../shots/twatch/en/ble_sync.png" width="240">

## Every day

- **Quick sync:** **Aa** on the Cardputer's clock (or TAB, then S) syncs every device and comes back to the clock;
  on the watch, **swipe down** on the clock - it waits for the Cardputer and comes back by itself.
- **Sync now** in *Settings → Bluetooth* does the same from the menu; ENTER on a device syncs only that one, and the
  list shows when each was synced and what happened.
- **By itself:** *Auto sync* in *Settings → Bluetooth* (ENTER switches it: on demand, every 15, 30, 60, 120 or 240
  minutes). The syncs are on the clock - every 60 minutes means at full hours - so the devices meet without talking
  first: the watch wakes up for them even from a deep sleep and listens for 90 seconds; the Cardputer syncs 20 seconds
  after the hour. Each sync costs the watch about 1 mAh (its battery has about 380).

<img src="../../../shots/cardputer/en/quick-sync.png" width="360">

## Statistics of every device

The Cardputer keeps the statistics each device reported: in *Focus tools → Statistics*, LEFT / RIGHT shows this
device, each synced device, or all of them together.

## Routines on chosen devices

With synced devices, a routine has a *Devices* field: it comes up only on the ticked ones. All ticked means every
device, the ones added later too.

## Time from a device

*Settings → Time and date → Time from a device*: the Cardputer takes the time of the first device with a valid
hardware clock (the watch has one).

## A phone or a computer

[`Squirrel!/tools/web/squirrel_ble.html`](../../../Squirrel!/tools/web/squirrel_ble.html) is a page for Chrome or Edge
that talks to the devices over Web Bluetooth: connected to the Cardputer (*Settings → Bluetooth → Be visible*) it edits
To-Dos, checklists, routines, notes and settings; connected to the watch it ticks and switches routines; it can set
the time from the phone. It pairs with the same 6-digit code. How to open it:
[tools/web/README.md](../../../Squirrel!/tools/web/README.md).

On a computer the page opens straight from the folder, no server needed (on Linux Chrome needs one flag switched on,
see that README); a phone needs it on an `https://` address. **A watch remembers one pairing:** pairing the page with
the watch makes the Cardputer ask for a new code at its next sync, and pairing the Cardputer again makes the page ask.
Pairing the page with the Cardputer changes nothing for the watch.

## Forgetting a device

On the Cardputer: *Settings → Bluetooth*, the device, **DEL twice**. Its key goes too; adding it again asks for a new
code.

## ⚠️ What pairing protects, and what not

Without the code nobody can sync your devices or change them. But the records themselves go over the air
**unencrypted**: someone nearby with Bluetooth sniffing gear could **read** them during a sync, and recover the key
from an overheard pairing (the code has only 6 digits). So pair away from strangers, and keep passwords and sensitive
data out of the To-Dos and notes you sync. Encrypting the link itself is ready in the code and will be switched on
once it has been tested enough ([backlog](../../implementation/en/backlog.md)).

## When something goes wrong

| What you see | What to do |
|---|---|
| *No devices - add one first* | Pair the watch first (above). |
| *failed: no answer* | Now and then a sync gets no answer right after connecting; the Cardputer tries again in the same go. If it still fails, *Sync now* again. |
| *Nobody came* on the watch | The Cardputer did not connect within 2 minutes: start the sync there while the watch waits. |
| A code is asked for again | One of the devices forgot the pairing (reset, new data), or the web page was paired with the watch since: type the new code. |
| The Cardputer restarts by itself after a minute | Very rarely it freezes; a watchdog restarts it, your data stays ([backlog](../../implementation/en/backlog.md), B). |
