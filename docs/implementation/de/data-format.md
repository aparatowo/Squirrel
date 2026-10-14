# Das gemeinsame Datenformat

*[English](../en/data-format.md) · [Polski](../pl/data-format.md) · [Français](../fr/data-format.md) · Deutsch*

Die Datensätze der ganzen Squirrel!-Familie: der Cardputer, die T-Watch und jede künftige App (zum Beispiel auf dem
Handy). Formatversion **1**. Referenzimplementierung: `Squirrel!/ble/protocol.py` (und ihr JavaScript-Zwilling
`Squirrel!/tools/web/squirrel_protocol.js`, Byte für Byte von `tools/tests/test_web_protocol.py` geprüft). Wie die
Synchronisation sie nutzt: [bluetooth.md](bluetooth.md).

## 1. Das Prinzip

- **Das kanonische Modell ist JSON.** Jeder Datensatz hat eine Definition: Feldnamen, Typen, Bereiche (Abschnitt 3). So
  sieht er in JSON-Dateien auf dem ESP32 aus, in einer Handy-App, in den Tests.
- **Bluetooth trägt eine binäre Kodierung** desselben Modells (Abschnitt 4) - Feld für Feld, ohne Verlust. Ein kleines
  Gerät muss kein JSON parsen: es hält C-Strukturen, die der binären Kodierung entsprechen.
- Jedes Gerät darf Daten auf seine Weise speichern (Textdateien, `done.dat`, C-Strukturen). Diese Spezifikation sagt
  nur, was außen ist; die Zuordnung zu den Dateien des ESP32 steht in Abschnitt 5.
- Unbekannte Felder werden übersprungen, nicht abgelehnt (eine neuere Version auf einem Gerät macht eine ältere auf
  einem anderen nicht kaputt). Neue Felder kommen nur als optionale hinzu. Eine Bedeutungsänderung eines Feldes ist eine
  neue Formatversion.

## 2. Gemeinsame Felder und Regeln

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | int 1-65535 | Die ID des Datensatzes. Bits 15-13: der **Slot** des Autors - 0 = ein Datensatz des **Chefs**, 1-6 = ein **lokaler** Datensatz des Knotens in diesem Slot, 7 = reserviert. Bits 12-0: der Zähler des Autors. Der Chef vergibt die Slots, wenn Knoten beitreten. |
| `e` | int | Zeit der letzten **Inhaltsänderung** - die Version des Inhalts (für Vorschläge verglichen, 3.8). |
| `c` | int | Zeit der letzten **Zustandsänderung** (an / erledigt / abgehakt). Eine Inhaltsänderung ändert sie nicht. |
| `del` | bool | Reserviert (ein Grabstein). Mit einem Chef nicht benutzt: der Chef löscht über seine Liste. |

- **Zeit** = Sekunden seit 1970-01-01 00:00 in der **Ortszeit** des Geräts (nicht UTC; der Abstand steht in `TIME`).
  0 = "nie".
- **Text** = UTF-8. Grenzen sind in Zeichen (wie auf den Bildschirmen); in der binären Kodierung in Bytes
  (Abschnitt 4).
- **Der Chef und die Knoten.** Ein Gerät des Sets ist der **Chef** (standardmäßig der Cardputer): der einzige Autor des
  Inhalts der Datensätze mit Slot 0. Die anderen sind **Knoten**. Zusammenführen zweier Kopien (`ble/merge.py`), für
  jede `id`:
  - der Inhalt der Datensätze des Chefs - immer vom Chef; ein Datensatz des Chefs, der in der Liste des Chefs fehlt,
    wird auf dem Knoten gelöscht;
  - der Zustand - von der Kopie mit dem größeren `c` (ein Haken auf der Uhr erreicht den Chef und geht von dort
    weiter);
  - die lokalen Datensätze eines Knotens (Slot ≠ 0) - der Chef ändert, löscht und übernimmt sie nicht (Übernahme: 3.8).
  Uhren entscheiden also nur über den Zustand; der Chef entscheidet über den Inhalt, und die Version `e` findet
  Bearbeitungskonflikte (3.8).
- **Der Wochentag** wird aus dem Datum berechnet, nie aus `localtime()[6]` genommen (ESP32-Firmwares sind sich darin
  nicht einig).

## 3. Die Datensätze (JSON)

### 3.1 Routine - `routine`

```json
{"id": 8193, "t": "Pills", "h": 8, "m": 0, "d": 63, "on": true, "to": 255, "e": 1760259600, "c": 1760259600}
```

| Feld | Typ | Bereich | Bedeutung |
|---|---|---|---|
| `t` | str | ≤ 50 Zeichen | der Text der Erinnerung |
| `h`, `m` | int | 0-23, 0-59 | die Uhrzeit |
| `d` | int | 0-127 | die Wochentage, Bit 0 = Montag ... Bit 6 = Sonntag |
| `on` | bool | | eingeschaltet (Zustand: eine Änderung setzt `c`) |
| `to` | int | 0-255 | die Geräte, auf denen sie erscheint: Bit n = Slot n; 255 = alle |

### 3.2 Aufgabe - `todo` (auch eine Checkliste)

```json
{"id": 2, "t": "Shopping\n> milk\n> bread", "done": false, "e": 1760259600, "c": 0,
 "items": [{"t": "milk", "done": true, "c": 1760260000}]}
```

| Feld | Typ | Bereich | Bedeutung |
|---|---|---|---|
| `t` | str | ≤ 500 Zeichen | der ganze Text; die erste Zeile ist der Titel |
| `done` | bool | | erledigt (Zustand) |
| `items` | list | ≤ 64 | nur Checklisten: der Zustand ihrer Punkte (die `>`-Zeilen) |
| `items[].t` | str | ≤ 100 Zeichen | der Text des Punkts - der Schlüssel, unter dem er bekannt ist |
| `items[].done`, `items[].c` | bool, int | | der Zustand des Punkts und die Zeit seiner Änderung (pro Punkt zusammengeführt, wie Datensätze) |

**Eine Checkliste** (eine Einkaufsliste, die Schritte einer Aufgabe ...): die Zeilen nach dem Titel, die mit `>`
beginnen, sind Punkte, die einzeln abgehakt werden (der Text des Punkts = die Zeile ohne das `>` und die Leerzeichen
darum). Andere Zeilen sind einfacher Text. Eine Aufgabe ohne `>`-Zeilen wird als Ganzes abgehakt. Wenn jeder Punkt
abgehakt ist, ist `done` = true.

### 3.3 Notiz - `note`

```json
{"id": 3, "t": "Remarks\nthe first line is the title", "e": 1760259600}
```

| Feld | Typ | Bereich | Bedeutung |
|---|---|---|---|
| `t` | str | ≤ 2000 Zeichen | der ganze Text; die erste Zeile ist der Titel |

Eine Notiz hat keinen Zustand (`c`).

### 3.4 Statistik eines Tages - `stat`

```json
{"day": "2026-10-12", "k": "focus_min", "n": 95}
```

| Feld | Typ | Bedeutung |
|---|---|---|
| `day` | str `YYYY-MM-DD` | der Tag |
| `k` | str | `routines` (erledigte Routinen), `todos` (erledigte Aufgaben), `focus_min` (Fokusminuten), `steps` |
| `n` | int 0-65535 | der Wert dieses Tages auf diesem Gerät |

Statistiken werden nicht zusammengeführt: jedes Gerät ist die einzige Quelle seiner eigenen; der Chef hält sie pro
Slot getrennt.

### 3.5 Einstellungen - `settings`

Ein Objekt `{KEY: value}` mit den Schlüsselnamen des Einstellungsschemas (`appconfig_schema.py`). Nur die
synchronisierten Schlüssel (`ble/protocol.py: SYNCED_KEYS`):

| Schlüssel | Typ |
|---|---|
| `CUCKOO_ENABLED`, `CUCKOO_QUARTERS` | bool |
| `CUCKOO_QUARTER_VOLUME` | int 0-100 |
| `POMODORO_WORK_MIN` (1-90), `POMODORO_BREAK_MIN` (1-30), `POMODORO_LONG_BREAK_MIN` (1-60), `POMODORO_CYCLES` (1-8) | int |
| `ROUTINE_SNOOZE_MIN` | int 1-60 |
| `QUIET_SOUND_FROM`, `QUIET_SOUND_TO` | str `HH:MM` |
| `QUIET_SOUND_DAYS` | str aus 7 Zeichen, `MTWTFSS`, `.` = ein nicht angehakter Tag |
| `TRAINING_PLAN` | eine Liste `[[colour, seconds], ...]`, ≤ 16 Blöcke, Farben: `blue yellow orange red green` |
| `BLE_AUTO_SYNC_MIN` | int 0-240 (0 = Synchronisation nur auf Abruf) |

Einstellungen sind ein Ganzes des Geräts, ohne `id`; die des Chefs werden auf die Knoten geschrieben.

### 3.6 Routinen-Ereignis - `event` (das Routinen-Protokoll)

```json
{"r": 8193, "at": 1760259600, "res": "done"}
```

| Feld | Typ | Bedeutung |
|---|---|---|
| `r` | int | die `id` der Routine |
| `at` | int | die Zeit, für die die Routine gestellt war (Ortszeit) |
| `res` | str | `done`, `skip` (übersprungen), `missed` (keine Antwort, auch nach den Pausen) |

Ein Knoten bewahrt Ereignisse 60 Tage auf und meldet sie dem Chef; der Chef nimmt nur die nach der letzten
Synchronisation. Ereignisse werden nicht zusammengeführt: jedes hat eine Quelle (den Knoten); der Chef hält sie pro
Slot getrennt.

### 3.7 Zeit - `time`, das Gerät - `info`, der Zustand - `status`

```json
{"time": 1760270400, "offset": 120, "source": "rtc", "age": 10, "has_rtc": true, "rtc_valid": true}
{"version": 1, "kind": "twatch", "caps": ["rtc", "routines", "todo", "stats", "steps"], "name": "T-Watch", "app": "2.0", "slot": 1}
```

`source`: `soft`, `manual`, `rtc`, `ntp`, `peer`. `kind`: `cardputer`, `twatch`, `web` (Code 3 ist reserviert).
`caps`: `rtc todo routines stats pomodoro breathing cuckoo steps hub notes`. `status` (Modus, Timer): reserviert.

### 3.8 Vorschlag - `proposal` (reserviert, ein späterer Schritt)

Eine Inhaltsänderung auf einem Knoten (ein Editor, der direkt mit dem Knoten verbunden ist): sie wirkt sofort auf dem
Knoten und wartet auf die Entscheidung des Chefs.

```json
{"op": "edit", "set": "routine", "id": 1, "base": 1760259600, "rec": {"...": "a record of 3.1"}}
```

| Feld | Bedeutung |
|---|---|
| `op` | `edit` (ein Datensatz des Chefs), `new` (ein neuer Datensatz - bisher lokal), `delete` |
| `base` | das `e` des Datensatzes des Chefs, auf dem die Änderung gemacht wurde. Der Chef übernimmt sie ohne Frage, wenn sein eigenes `e` noch dasselbe ist; sonst ist es ein Konflikt (auto: der Chef gewinnt; "ask": der Nutzer entscheidet) |

Die binäre Kodierung kommt mit der Implementierung (Satz `0x0B` ist reserviert).

## 4. Die binäre Kodierung (Bluetooth)

Little-Endian. `str8` = u8-Länge in Bytes + UTF-8; `str16` = u16 + UTF-8. Text wird nur an einer Zeichengrenze
abgeschnitten. Zeit = u32. Gemeinsame Flags: Bit 7 = `del` (ein Grabstein: nach den Flags nur `e`, der Rest Nullen /
leer).

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

### Der Kanal `CONTROL` - Datensätze bewegen

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

Statistiken und Ereignisse haben keine `id`: die Antwort auf `LIST` enthält die Datensätze selbst (`stat`: die letzten
60 Tage; `event`: die nach der Zeit, die in den Daten der `LIST`-Anfrage steht, u32 - der Chef merkt sich, wie weit er
gelesen hat). Die Routinen lassen sich auch mit einem `GET` der `id` 0 holen (jeder Datensatz in einer Antwort) - sie
sind klein.

### Koppeln und der Beweis einer Sitzung (`ble/auth.py`)

HMAC = HMAC-SHA256, auf 16 Bytes gekürzt; Texte in ASCII, `+` verbindet Bytes.

```
key      K   = HMAC(the code as 6 ASCII digits, "squirrel-pair" + boss nonce + node nonce)
CONFIRM      = HMAC(K, "confirm" + node nonce)
PROVE        = HMAC(K, "session" + challenge)
```

Der Code geht nie durch die Luft. Ein Knoten hält einen Schlüssel (`"head"`), der Chef einen pro Knoten (nach
Adresse); beide in `ble_auth.json` im internen Flash. Bis `AUTH_PROVE` in einer Sitzung gelingt, antwortet ein Knoten
auf jede andere Anfrage mit ERR 6 und ignoriert ein Schreiben von `TIME`; `INFO` und `TIME` lassen sich ohne Koppeln
lesen. **Die Datensätze gehen unverschlüsselt** - siehe [bluetooth.md](bluetooth.md) §6.

## 5. Zuordnung zu den Dateien des ESP32

| Datensatz | Datei | Anmerkungen |
|---|---|---|
| routine | `routines.json` - eine Liste der JSON-Objekte aus 3.1 | ältere Dateien ohne `id`, `to`, `e`, `c`: beim Lesen bekommen sie eine `id` (ein Zähler des Chefs), `to` = 255, `e` = `c` = 0 |
| event | `focus/events.txt` - Zeilen `r,at,res` | 60 Tage; auf dem Chef: `focus/peers/<slot>/events.txt` |
| todo | `todo/<name>.txt` (der Text), `todo/done.dat` (`name,date` = erledigt; `name#item,date` = ein Punkt abgehakt), `todo/meta.json` (`{name: {id, e, c, items: {item: c}}}`) | Dateien ohne Eintrag in `meta.json` (von vor 2.0, per USB kopiert): `e` = `c` = 0, die `id` wird bei der ersten Liste vergeben |
| note | `notes/<name>.txt`, `notes/meta.json` (`{name: {id, e}}`) | |
| stat | `focus/routines.txt`, `focus/todos.txt`, `focus/focus.txt` (Sekunden -> Minuten), Schritte | `focus/peers/<slot>/` - die Statistiken der anderen Geräte auf dem Chef |
| settings | `config.txt` | |
