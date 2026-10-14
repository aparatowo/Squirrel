# Speicher, Tempo und Energie

*[English](../en/performance.md) · [Polski](../pl/performance.md) · [Français](../fr/performance.md) · Deutsch*

Squirrel! muss auf das schwächste seiner Geräte passen: ein ESP32-S3 **ohne PSRAM** (der Cardputer ADV, viele günstige
Uhren) gibt MicroPython etwa **160 KB** Heap für alles. Was es heute kostet, und wie es klein gehalten wird.

## 1. Gemessen (2.0)

| Was | Wert |
|---|---|
| Der Heap der App auf dem Cardputer (ohne PSRAM), auf der Uhr | 54 KB von 160 KB |
| davon die Einstellungen (95 Stück) | 7,4 KB |
| Eine andere Sprache als Englisch | unter 1 KB RAM (die Tabellen bleiben im Flash) |
| Einen Text auf der Uhr suchen (ESP32 mit 80 MHz) | 91 µs (763 µs ohne Cache); einen Bildschirm zeichnen etwa 2 % langsamer als auf Englisch |
| Das Display der Uhr, ganzer Framebuffer / Streifen | Menü 132 / 141 ms, Uhr 292 / 366 ms |
| Framebuffer für 240 × 240 / 240 × 280, in Streifen | 115 / 134 KB, 19 KB |
| Eine automatische Bluetooth-Synchronisation, auf der Uhr | etwa 1 mAh (ihr Akku: etwa 380 mAh) |

## 2. Wie es klein gehalten wird

- **Eingefrorener Code.** Alle Module sind Bytecode im Flash (`build_firmware.py`): nichts wird auf dem Gerät
  kompiliert, und Code belegt keinen Heap. Konstante Tabellen (Übersetzungen, Glyphen, die Schrift) bleiben auch im
  Flash.
- **Einstellungen als Zeilen.** `appconfig` hält einen Verweis auf jede `SETTINGS`-Zeile aus `appconfig_schema.py`
  statt einer Kopie pro Einstellung und nimmt die Standardwerte direkt aus `nuts`.
- **Übersetzungen** sind ein sortiertes Tupel pro Sprache, durch Halbierung durchsucht; ein Cache der letzten 200
  Texte, und die eigenen Texte des Nutzers (`lang_<code>.tsv`) sind die einzigen im RAM. Siehe [i18n.md](i18n.md).
- **Das Display in Streifen** ohne PSRAM (`drivers/st7789_fb.py`): die Zeichenaufrufe eines Bildes werden gemerkt und in
  einen Puffer von 40 Zeilen wieder abgespielt, ein Streifen nach dem anderen. Von selbst gewählt: das ganze Bild nur,
  wenn es höchstens ein Viertel des freien Heaps belegt; `[display] buffer_rows` erzwingt Streifen. Siehe
  [ports.md](ports.md).
- **Bildschirme entladen** (`POWER_UNLOAD_SCREENS`): die Objekte eines selten benutzten Bildschirms gehen, wenn du ihn
  verlässt.
- **Faule Importe** dessen, was nur ein Bildschirm oder eine Funktion braucht; eine Funktion, die das Gerät nicht hat,
  ist gar nicht in seiner Firmware (`features.toml`).
- **Bluetooth:** nur während einer Sitzung; ein Datensatz zur Zeit im Speicher (in Teilen gesendet und empfangen); die
  automatische Speicherbereinigung ist während einer Sitzung aus, und `tick()` räumt aus der Hauptschleife auf - eine
  Bereinigung, die eine Allokation im IRQ des Funks auslöste, lief auf dessen kleinem Stack.

## 3. Energie

- Die Funkmodule sind nur an, solange sie arbeiten: WLAN für die Uhrzeit beim Start, Bluetooth für eine
  Sync-Sitzung (ein ESP32 kann mit eingeschaltetem BT-Controller nicht leicht schlafen).
- Der Bildschirm wird nach einer Weile ohne Eingabe dunkler; `POWER_SAVE` verlangsamt die CPU, solange er gedimmt ist.
- `POWER_SLEEP`: `light` (experimentell) schläft bei gedimmtem Bildschirm und wacht bei einer Taste, einem Knopf oder
  einer Berührung auf; `deep` (die Uhr) schläft tief und wacht durch den Alarm ihrer Uhr für die nächste Routine, den
  Kuckuck oder die Sync-Zeit auf (`alarms.py` hält die Warteschlange, `deep_sleep.py` speichert und stellt den Zustand
  wieder her). Nach dem Aufwachen wird das Zifferblatt gezeichnet, bevor der Rest der App startet (`EARLY_CLOCK`).
- Die Zeiten der automatischen Synchronisation richten sich nach der Uhr, damit sich die Geräte treffen, ohne vorher zu
  reden: die Uhr lauscht 90 s pro Zeitfenster, der Chef verbindet sich 20 s nach dessen Beginn.

## 4. Sicherheitsnetze

- **Watchdog** (`WATCHDOG_S`, 60 s): wenn die Hauptschleife nicht zurückkommt, startet das Gerät neu; die Daten
  bleiben.
- **Absturzprotokoll** (`firmware_patches/0002-panic-record.patch`): die Ursache und der Backtrace eines Absturzes, oder
  was Kern 0 tat, als der Task-Watchdog auslöste, überstehen den Neustart im RTC-Speicher;
  `tools/hwtest/panic_record.py` liest sie.
- `LOW_HEAP` in `hw/power.py`: eine Bereinigung, bevor der Heap knapp wird.

## 5. Erneut prüfen

```python
import gc, micropython; gc.collect(); micropython.mem_info()      # in the REPL of a running app (DEV mode)
```

`tools/hwtest/ble_e2e.py --mem` gibt während einer Synchronisation jede halbe Sekunde den Speicher des Cardputers aus;
`tools/hwtest/twatch_gfx_bench.py` misst das Zeichnen der Uhr.
