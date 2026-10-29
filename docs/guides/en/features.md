# Features

*[Polski](../pl/features.md) · [Français](../fr/features.md) · [Deutsch](../de/features.md)*

What Squirrel! does, screen by screen. Version 2.0. The keys and gestures for all of it: [shortcuts.md](shortcuts.md).
Pictures: the Cardputer on the left, the watch on the right (where it has the screen).

---

## 🕐 The clock

The home screen is a clock: big digits, the date, and a line of your own at the bottom (*no need to go nuts* on the
Cardputer, *Squirrel! is watching* on the watch - change it in Personalize, or leave it). The bars of `#` around it
show time passing at a glance:

- **left** - the battery; **right** - today's focus time against your goal, rising from the bottom (*Focus bar from:
  top* fills it the classic way, from the top);
- **top** - the hour going by, filling from the left; while the [hourglass](#-hourglass) runs, its time instead (the
  leading `#` blinks);
- **bottom** - the quarter hour, filling from the right; it starts again at :00, :15, :30 and :45.

Each of them can be a plain bar or switched off (*Personalize → Bars*). The watch also shows the weekday and, in words,
the focus time and the battery.

Times from 10:00 to 19:59 start with a "1", drawn by its right side only, so the clock then moves 10 pixels to the
left (16 on the watch) to look centred (*Personalize → Display → Clock 1x:xx X*; 0 turns it off).

<img src="../../../shots/cardputer/en/clock.png" width="360"> <img src="../../../shots/twatch/en/clock.png" width="240">

From the clock: any key opens the menu, **OPT** starts or pauses the focus timer, **Aa** syncs your devices, **TAB**
opens a small menu of the things you reach for most:

<img src="../../../shots/cardputer/en/tab-menu.png" width="360">

On the watch: a **double tap** starts the focus timer, a **triple tap** pauses it, a single tap opens the menu - all on a lit screen (a tap on a dark one only wakes it).

The time comes from a hardware clock where there is one (the watch's PCF8563; on the Cardputer an optional clock
module - a DS3231 on the Grove port, or a DS1302 on the ADV's EXT header - once you say which one in *Settings → Time
and date → Time settings → Clock module*; until then its code is not even loaded), from Wi-Fi at start-up, or from
another Squirrel! device over Bluetooth (*Settings → Time and date → Time from a device*).

## ✅ To-Dos and checklists

A list of things to do that does not judge you. A To-Do is a title and, if you want, more text. **OPT** marks it done
(on the watch: hold it). Done To-Dos stay for a week (`TODO_KEEP_DAYS`), then they go by themselves.

<img src="../../../shots/cardputer/en/todo-list.png" width="360"> <img src="../../../shots/twatch/en/menu_todo.png" width="240">

**Checklists.** Lines that start with `>` are items to tick - a shopping list, the steps of a task:

```
Saturday shopping
> milk
> bread
> nuts
remember the bag
```

Such a To-Do opens as a checklist; the list shows the progress (`[1/3]`); when every item is ticked, the whole To-Do
is done. The text of the file never changes - the ticks are kept apart.

<img src="../../../shots/cardputer/en/checklist-ticked.png" width="360"> <img src="../../../shots/twatch/en/checklist.png" width="240">

The To-Dos are written on the Cardputer (it has the keyboard); on the watch you read them and tick them.

## 📋 Text notes

A place for things that must leave your head now: a title (the first line) and the text, saved at once to the SD
card as plain `.txt` files you can read on any computer. **CTRL+S** saves, **ESC** throws the changes away.

<img src="../../../shots/cardputer/en/editor.png" width="360"> <img src="../../../shots/cardputer/en/note-viewer.png" width="360">

Deleting asks you to press DEL three times - a slip of the finger cannot lose a note.

<img src="../../../shots/cardputer/en/delete-confirm.png" width="360">

## 🏆 Success journal

One list a day of what went well - small things count. *Notes → Success journal → + [Today]* opens today's list with a
new line ready: every line that starts with `-` or `>` is one thing done (as in a To-Do's checklist); other lines are
just text. The number of things done goes into the statistics, apart from the focus time.

<img src="../../../shots/cardputer/en/success-journal.png" width="360">

## 🧠 Mind dump

For the thought that keeps circling. TAB, then M on the clock: write it (up to 200 characters - enough to catch the
thought, too few to spiral into it), ENTER, and you are back where you were. Mind dump thoughts have their own list
(*Notes → Mind dump*); edit one there and it becomes a proper note.

<img src="../../../shots/cardputer/en/mind-dump.png" width="360">

## 🎙️ Voice notes

When typing is too slow: **G0** on the clock or in a menu starts recording at once, G0 again saves. The recordings
are `.wav` files on the SD card; play them back from *Notes → Voice notes* (pause, 10 s back / forward, volume).

<img src="../../../shots/cardputer/en/recorder.png" width="360"> <img src="../../../shots/cardputer/en/voice-notes.png" width="360">

## 🔄 Routines

Recurring reminders: a text, a time of day, the days of the week. When one is due, the screen says so - **OPT**: done
(it counts in the statistics), **DEL**: skip. No answer for 30 seconds: it comes back after a snooze
(`ROUTINE_SNOOZE_MIN`). Missing one changes nothing - no red, no streak lost; the next time simply comes.

<img src="../../../shots/cardputer/en/routines.png" width="360"> <img src="../../../shots/cardputer/en/routine-due.png" width="360">

With synced devices, a routine has a *Devices* field: it comes up only on the devices you tick (the pills on the
watch, the plants on the Cardputer). On the watch, routines are switched on and off with a tap; they are written on
the Cardputer.

## 🦅 Cuckoo clock

A quiet signal on every full hour - and, if you want, a softer tick every quarter of an hour. Not an alarm: a tap on
the shoulder, *time is passing*. It keeps going with the screen off. Sound, buzzer, LED or vibration, as you set them;
silent mode keeps it quiet at night.

## 🍅 Pomodoro and training

Work for a block, rest, repeat: Pomodoro shows the block (*Work*, *Break*, *Long break*), the time left and the row of
blocks to come. It runs in the background - leave the screen and it keeps counting; the focus time goes into the
statistics. *Training* is the same timer with blocks you put together yourself (prepare, light, normal, hard, rest).

<img src="../../../shots/cardputer/en/pomodoro-running.png" width="360"> <img src="../../../shots/twatch/en/pomodoro_running.png" width="240">

## ⏳ Hourglass

A plain countdown: set the minutes, start, and get on with it. The clock's top bar fills as the time runs out; at the
end it rings - sound, LED and buzzer or vibration, again every few seconds until you answer it - in the silent hours
too, since you set it yourself. It runs in the background like Pomodoro, and keeps the minutes for the next time.

<img src="../../../shots/cardputer/en/hourglass-running.png" width="360"> <img src="../../../shots/cardputer/en/clock-hourglass.png" width="360">

## 🥁 Metronome and 🫁 breathing

The metronome beats every 1/8 s up to every 2 minutes - something steady to follow, in the background - with a short beep, or a dry click like
a clock's (*Personalize → Audio → Metronome sound*). Breathing
guides you through *Box 4-4-4-4*, *Relax 4-7-8* or *Calm 5-5*: a circle grows as you breathe in and shrinks as you
breathe out (the LED follows it, if you have one).

<img src="../../../shots/cardputer/en/metronome.png" width="360"> <img src="../../../shots/cardputer/en/breathing.png" width="360">

## 📊 Statistics

Today's focus time against your goal, and the last 7 days. No targets to fail, no comparisons - a quiet picture of
your days. With synced devices: LEFT / RIGHT shows this device, each synced device, or all of them together.

A distraction counted as focus? **-** takes the last 15 minutes back (*Personalize → Focus → Take back minutes*);
DEL twice zeroes today. Under today's time: what went well today and this week, from the success journal.

<img src="../../../shots/cardputer/en/statistics.png" width="360"> <img src="../../../shots/twatch/en/focus_stats.png" width="240">

## 🔗 Bluetooth sync

The Cardputer and the watch keep each other up to date: routines, To-Dos, notes and settings go to the watch; ticks,
the routine log and statistics come back. **Aa** on the Cardputer's clock syncs at once; or let them sync by themselves
every 15 minutes to 4 hours. All about it: [bluetooth.md](bluetooth.md).

<img src="../../../shots/cardputer/en/bluetooth.png" width="360"> <img src="../../../shots/twatch/en/ble_sync.png" width="240">

## 🔕 Silent mode

Hours and days when the sound, the buzzer or the LED keep quiet - each on its own (*Settings → Silent mode*). A night
counts for the day it starts.

<img src="../../../shots/cardputer/en/silent-mode.png" width="360"> <img src="../../../shots/twatch/en/silent_sound.png" width="240">

## 🎨 Personalize and languages

Colours, the text under the clock, the Pomodoro and focus times, the signals, sleep - all in *Settings → Personalize*,
each with a line of help, and all kept in `config.txt` on the device (a plain text file you may edit too).

The screens speak **English, Polish, French or German** (*Personalize → Display → Language*); any language but
English turns on the font with its accented letters. A text you would put differently can be changed on the device,
without new firmware: [Squirrel!/translations/README.md](../../../Squirrel!/translations/README.md).

<img src="../../../shots/cardputer/en/personalize.png" width="360"> <img src="../../../shots/cardputer/en/personalize-language.png" width="360">

## 🔋 Energy

The screen dims after a while without a key; with *Sleep mode* the device sleeps while dimmed (the watch sleeps deeply
and wakes for its routines, the cuckoo and its sync times). The radios are on only while they work: Wi-Fi for the time
at start-up, Bluetooth for a sync. The Cardputer ADV has no sleep mode for now: in a light sleep its
back-light flashed and G0 started the recorder by itself (to be solved); the saving while the screen is dimmed stays.
On the first Cardputer the sleep mode is experimental (*Settings → Experimental → Settings*).

**A low battery** is announced at 15 %, 10 %, 5 % and right before it runs out - on the screen, with a sound and the
buzzer or vibration if you want them (*Personalize → Power → Battery warnings*, *Warning sound*; *Buzzer → Low
battery*). The LED can blink with the warning (*Personalize → LED → Battery: blink*).
While the battery charges, a small lightning shows by the battery bar on the clock (*Personalize → Bars →
Charging mark*).

**Charging.** The watch's power chip says when it charges (or sits on USB power, full). The Cardputers cannot tell: their
battery is only measured. *Settings → Experimental → Settings → Charge detection* makes them guess it - from the battery's voltage
(it jumps when a charger comes or goes, and rises slowly while the battery fills) and from a computer on the USB. A plain
charger without data cannot be seen any other way. Experimental: tell us how well it guesses.
