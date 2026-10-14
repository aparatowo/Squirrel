# Bluetooth-Synchronisation - Entwurf

*[English](../en/bluetooth.md) · [Polski](../pl/bluetooth.md) · [Français](../fr/bluetooth.md) · Deutsch*

Wie sich die Squirrel!-Geräte über Bluetooth Low Energy synchronisieren, wie es in 2.0 gebaut ist. Die Datensätze und
ihre Kodierung: [data-format.md](data-format.md). Für Nutzer: [guides/de/bluetooth.md](../../guides/de/bluetooth.md).
Offene Fragen: [backlog.md](backlog.md).

## 1. Entscheidungen, und warum

| Entscheidung | Warum |
|---|---|
| Das rohe `bluetooth`-Modul von MicroPython (IRQ-Handler + `tick()`), nicht `aioble` | `aioble` ist nicht in der Firmware, und die App hat kein asyncio: sie läuft auf einer Hauptschleife reihum aufgerufener Dienste. Ein IRQ-Handler, der nur einreiht, und ein `tick()`, das die Arbeit macht, passen zu dieser Schleife und brauchen weniger RAM. |
| Ein Protokoll in `ble/` für jedes Gerät; die Rolle aus `features.toml` | Der Bluetooth-Stack (NimBLE) ist auf ESP32 und ESP32-S3 derselbe; Geräte unterscheiden sich nur in ihrer Rolle (Chef / Knoten) und darin, welche Daten sie haben. |
| Ein kanonisches JSON-Modell + eine binäre Kodierung in der Luft | Jede Implementierung - die Handy-App, eine in C auf einer kleinen Uhr - hat dieselben Datensätze; in der Luft ein kompakter Codec, der keinen JSON-Parser braucht. |
| Ein `SETTINGS`-Satz in der Textform von `config.txt` | Die App hat schon ein Schema mit Prüfung (`appconfig_schema.py`); eine neue Einstellung braucht keine neue Charakteristik. |
| Sync-Sitzungen, kein dauernd eingeschalteter Funk | Ein ESP32 kann mit eingeschaltetem BT-Controller nicht leicht schlafen, und ein Tiefschlaf schaltet den Funk ab: dauerndes Werben würde den Akku der Uhr fressen. Der Funk ist nur für eine Sitzung an, wie WLAN für die Uhrzeit. |
| Die bessere Uhr stellt die schlechtere | Der Cardputer hat oft keine Hardware-Uhr; die Uhr hat eine. Die Zeit geht von WLAN-Zeit > Hardware-Uhr > von Hand gestellt > Software-Uhr. |
| Koppeln mit einem Code in der App, (noch) keine Verschlüsselung der Verbindung | Siehe Abschnitt 6. |

## 2. Rollen

Ein Gerät des Sets ist der **Chef** (`head` im Code: `BleHead`, `ble_head_screen.py`, `features.toml` `ble_hub`; auf
den Bildschirmen: die Knoten warten auf *das Eichhörnchen*, das nach *Nüssen* sucht) - der einzige Autor des Inhalts
(der Cardputer: er hat die Tastatur). Die anderen sind **Knoten**. Ein Knoten nimmt eine Verbindung zur Zeit an.

```
   Web Bluetooth page (phone / computer)
            │  connects to the boss (or to a node)
            ▼
   BOSS: Cardputer - central towards the nodes; peripheral towards the page ("Be visible")
    ├── T-Watch        - node (peripheral)
    └── (other watches later - nodes too)
```

| Daten | Chef | Knoten (Uhr) | Webseite |
|---|---|---|---|
| Inhalt von Aufgaben / Checklisten | schreibt | liest | schreibt (über den Chef) |
| Haken an Aufgaben und Checklisten-Punkten | ✅ | ✅ | ✅ |
| Routinen: Text, Zeit, Tage, Geräte | schreibt | liest | schreibt (über den Chef) |
| Routine an / aus | ✅ | ✅ | ✅ |
| Statistik, Routinen-Protokoll | eigene / jedes Knotens / zusammen | eigene, gemeldet | - |
| Synchronisierte Einstellungen | ✅ | vom Chef | ✅ |
| Zeit | nach Qualität der Uhr | nach Qualität der Uhr | stellt sie vom Handy |

## 3. GATT-Profil

Ein Dienst für die ganze Familie; die Charakteristiken teilen die Basis und unterscheiden sich in der zweiten
Zifferngruppe. Basis: `beeaXXXX-f159-4fd4-b434-1d8d3db5b0bc`.

| `XXXX` | Name | Eigenschaften | Inhalt |
|---|---|---|---|
| `0000` | Squirrel!-Dienst | - | beworben: daran erkennt ein Scanner die Familie |
| `0001` | `INFO` | R | Protokollversion, Geräteart, Fähigkeitsmaske, Slot, Name, App-Version |
| `0002` | `TIME` | R / W | Ortszeit, UTC-Abstand, Quelle und Alter der Uhr; jede Sekunde aufgefrischt; ein Schreiben stellt die Uhr (nur gekoppelte Chefs) |
| `0003` | `SETTINGS` | R | die Revision der Einstellungen (die Einstellungen selbst über `CONTROL`, Satz `0x03`) |
| `0004` | `ROUTINES` | R | Revision der Routinen |
| `0005` | `TODO` | R | Revision der Aufgaben |
| `0006` | `STATS` | R | Revision der Statistik |
| `0007` | `STATUS` | R / N | reserviert: Modus, Timerzustand, Akku |
| `0008` | `CONTROL` | W / N | Anfragen und Antworten: auflisten, holen, schreiben, löschen, koppeln ([data-format.md](data-format.md) §4) |
| `0009` | `NOTES` | R | Revision der Notizen (nur Geräte mit Notizen) |
| `000a` | `EVENTS` | R | Revision des Routinen-Protokolls |

Fähigkeitsbits in `INFO`: 0 Hardware-Uhr, 1 Aufgaben, 2 Routinen, 3 Statistik, 4 Pomodoro, 5 Atmung, 6 Kuckuck,
7 Schritte, 8 Hub, 9 Notizen. Der Chef synchronisiert nur, was ein Knoten meldet.

## 4. Eine Sitzung

1. Der Knoten wirbt für ein Zeitfenster mit dem Dienst (2 Minuten von seinem Bluetooth-Bildschirm, 90 s für eine
   automatische Synchronisation).
2. Der Chef verbindet sich nacheinander mit jedem bekannten Knoten (er merkt sie sich in `ble.json`: Adresse, Slot,
   letzte Synchronisation).
3. MTU-Austausch, Dienstsuche, `INFO` (Protokollversion), Benachrichtigungen auf `CONTROL`.
4. **Koppeln / Beweis** (Abschnitt 6).
5. **Die Uhr:** die bessere stellt die andere (kein Schreiben, wenn sie auf 2 Sekunden übereinstimmen).
6. **Beitreten:** ein Knoten mit abweichendem Slot bekommt seinen Slot (`PUT` auf den Satz `INFO`). Seine Datensätze von
   vorher - per USB kopiert zum Beispiel - wechseln auf diesen Slot und werden seine lokalen Datensätze.
7. **Einstellungen:** der Chef schreibt die synchronisierten Schlüssel, die sich unterscheiden
   (`ble/protocol.SYNCED_KEYS`).
8. **Datensätze** - Routinen, Aufgaben, Notizen: zuerst die Liste jedes Satzes beim Knoten (ID, Bearbeitungszeit `e`,
   Zustandszeit `c`), dann nur die Datensätze, die sich unterscheiden, in beide Richtungen (Abschnitt 5).
9. **Berichte:** die Statistik des Knotens (die letzten 60 Tage) und sein Routinen-Protokoll seit der letzten
   Synchronisation; der Chef bewahrt sie pro Knoten in `focus/peers/<slot>/` auf.
10. Trennen. Der Knoten bleibt noch 15 s sichtbar, für einen zweiten Durchgang.

**Der zweite Durchgang:** nach dem ersten hat der Chef alles, aber der zuerst synchronisierte Knoten kennt die
Zustandsänderungen der späteren noch nicht (ein Haken auf der Uhr, für das nächste Gerät). Der Chef verbindet sich
erneut mit den Knoten, deren Listen sich noch unterscheiden - und mit denen, die im ersten Durchgang scheiterten.

Ein Datensatz geht in Teilen und wird ganz oder gar nicht übernommen: eine abgebrochene Verbindung verdirbt nichts, und
nur ein Datensatz zur Zeit ist im Speicher.

## 5. Wer hat recht

Pro Datensatz (`ble/merge.py`):

- **Inhalt** der Datensätze des Chefs (Slot 0 in der ID) kommt immer vom Chef. Ein Datensatz des Chefs, der in der
  Liste des Chefs fehlt, wird auf dem Knoten gelöscht.
- **Zustand** - eine Routine an / aus, eine Aufgabe erledigt, ein Checklisten-Punkt abgehakt - kommt von der Kopie, in
  der er sich später geändert hat (`c`). Jeder Checklisten-Punkt hat seine eigene Zeit, also stören sich verschiedene
  Haken auf zwei Geräten nicht.
- **Die lokalen Datensätze eines Knotens** (sein Slot in der ID) werden vom Chef nie geändert, gelöscht oder übernommen.

Uhren entscheiden nur über den Zustand (ein Konflikt sind zwei verschiedene Haken an einem Datensatz: selten und
harmlos); der Inhalt hängt nicht von der Zeit ab, eine falsche Uhr kann also keine Bearbeitung überschreiben.

**Checklisten:** die Zeilen einer Aufgabe, die mit `>` beginnen, sind ihre Punkte. Sie werden am Inhalt erkannt, nicht
am Titel, funktionieren also auf jedem Gerät gleich; die Haken liegen neben der Datei (`todo/done.dat`), der Text
ändert sich also nie.

**Routinen auf bestimmten Geräten:** das Feld `to` einer Routine ist eine Bitmaske der Slots (Bit n = Slot n; 255 =
jedes Gerät, auch später hinzugefügte). Jedes Gerät löst nur die Routinen aus, die sein Bit haben.

## 6. Koppeln und Sicherheit

**In 2.0: Koppeln in der App** (`ble/auth.py`; die Befehle in [data-format.md](data-format.md) §4).

- **Koppeln (einmal):** der Chef sendet eine zufällige Nonce (`AUTH_HELLO`); der Knoten antwortet mit seiner und zeigt
  einen 6-stelligen Code; der Nutzer gibt ihn auf dem Chef ein; beide leiten
  `K = HMAC-SHA256(code, "squirrel-pair" + nonces)[:16]` ab, und der Chef beweist, dass er ihn hat (`AUTH_CONFIRM`).
  Der Code selbst geht nie durch die Luft.
- **Jede Sitzung:** der Knoten gibt eine frische Einmal-Herausforderung (`AUTH_CHALLENGE`); der Chef antwortet mit
  `HMAC(K, "session" + challenge)` (`AUTH_PROVE`). Bis dahin verweigert der Knoten alles (Fehler 6) außer dem Lesen von
  `INFO` und `TIME`, und ignoriert ein Schreiben der Zeit.
- **Schlüssel:** `ble_auth.json` im internen Flash - nie auf einer Wechselkarte. Ein Gerät auf dem Chef zu vergessen
  löscht seinen Schlüssel; ein Knoten, der seinen Schlüssel verloren hat, verlangt einen neuen Code. Die
  Web-Bluetooth-Seite hält ihren Schlüssel im `localStorage` des Browsers, pro Gerät.

> ⚠️ **Was das nicht schützt.** Die Datensätze gehen **unverschlüsselt**: jemand in Funkreichweite mit
> BLE-Abhörgerät kann sie während einer Synchronisation lesen (nicht ändern, kein Gerät ohne den Schlüssel
> synchronisieren). Ein belauschtes Koppeln lässt den Schlüssel offline finden (der Code hat 6 Ziffern). Die
> Anleitungen sagen den Nutzern, nicht in der Nähe von Fremden zu koppeln und keine Geheimnisse in synchronisierte
> Notizen zu schreiben.

**Verschlüsselung der Verbindung (LE Secure Connections)** ist im Code, aber aus (`nuts.BLE_LINK_PAIRING = False`): ein
auf dem Knoten gezeigter Passkey, von der App gehaltene Bindungen (`ble/secrets.py`, `GET_SECRET` / `SET_SECRET` aus dem
IRQ), und eine Korrektur an NimBLE für die Passkey-Ereignisse der Central
(`firmware_patches/0001-nimble-central-passkey.patch`). Es funktionierte, aber der Cardputer startete in manchen
Sitzungen neu - was sich als ein anderer Fehler herausstellte (Backlog A).

## 7. Automatische Synchronisation

`BLE_AUTO_SYNC_MIN` (0 = auf Abruf; 15 ... 240) - `ble/auto.py`. Die Sitzungen richten sich nach der Uhr: die Minuten
des Tages, die durch den Abstand teilbar sind. Der Knoten ist eine Alarmquelle (`alarms.py`), also wacht eine Uhr im
Tiefschlaf zu jedem Zeitfenster auf und wirbt 90 s; der Chef beginnt 20 s nach dem Zeitfenster. Ein Zeitfenster wird
übersprungen, wenn der Funk belegt ist (ein Bluetooth-Bildschirm, die Zeit-Synchronisation über WLAN) oder ein Knoten
gekoppelt werden muss (das braucht den Nutzer). Ein Bluetooth-Bildschirm, der während einer automatischen Sitzung
geöffnet wird, beendet sie. Die Einstellung wird vom Chef synchronisiert, die Knoten folgen ihr also.

## 8. MicroPython auf dem ESP32: was man wissen sollte

- Der IRQ-Handler läuft auf dem Stack der NimBLE-Task, mitten in ihrer Arbeit. Die Daten, die er bekommt - das Tupel,
  die Adressen, die Puffer, **die UUID-Objekte** - gelten nur während des Aufrufs: alles, was man behält, wird kopiert
  (`bytes(...)`, `bluetooth.UUID(...)`). **`tuple(data)` ist keine Kopie**: MicroPython gibt dasselbe Tupel zurück, und
  es zu behalten setzte den Cardputer an zufälligen Stellen einer Synchronisation zurück, bis es gefunden wurde
  (`tuple(list(data))` kopiert).
- Keine Generatoren, kein Parsen im Handler; das macht `tick()`. Der Handler muss auf `GET_SECRET` / `SET_SECRET`
  antworten (nichts auf `SET_SECRET` zurückzugeben setzte den Cardputer zurück).
- Während der Funk arbeitet, ist die automatische Speicherbereinigung aus, und `tick()` räumt aus der Hauptschleife auf
  (`radio_gc`): eine Bereinigung, die eine Allokation im IRQ auslöste, lief auf dem kleinen Stack der NimBLE-Task.
- Die Hintergrunddienste pausieren während einer Sitzung (`ServiceManager.paused`), damit die Hauptschleife dem Funk
  schnell antwortet.
- Den Funk direkt nach einer Sitzung abzuschalten kollidierte mit den Timern von NimBLE: `_settle()` wartet zuerst
  100 ms.

## 9. Der Code

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

`features.toml`: `ble_sync` (jeder Port mit `[radio] ble = true`: der Knoten-Teil), `ble_hub` (ein Port, der auch eine
Tastatur hat: der Chef-Teil).

## 10. Noch nicht gebaut

- **Änderungen auf einem Knoten** (ein Handy, das mit der Uhr verbunden ist): sofort angewendet, als *Vorschläge* mit
  der Version gespeichert, auf der sie gemacht wurden; der Chef entscheidet bei der nächsten Synchronisation -
  angenommen, wenn er diesen Datensatz inzwischen nicht geändert hat, sonst ein Konflikt; neue Datensätze bleiben lokal
  oder werden übernommen. Ein `SYNC_MODE` *auto* / *ask* mit einem Bildschirm der Unterschiede (senden / nehmen /
  überspringen je Kategorie). Satz `0x0B` ist dafür reserviert.
- **Ein neuer Chef:** eine vollständige Kopie der Datensätze des Chefs von einem beliebigen Knoten übernehmen, mit den
  IDs und Zählern, und die Knoten neu koppeln.
- **Kleine Geräte:** das Protokoll ist so gedacht, dass es sich in C ohne dynamische Allokation umsetzen lässt.
