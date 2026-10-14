# Ports: die Geräte und ein neues hinzufügen

*[English](../en/ports.md) · [Polski](../pl/ports.md) · [Français](../fr/ports.md) · Deutsch*

Squirrel! läuft auf mehreren Geräten aus einem Code. Jedes Gerät ist ein **Port**: ein Ordner `Squirrel!/ports/<name>/`
mit einer Beschreibung der Hardware (`port.toml`) und einem Modul, das diese Hardware für die App zusammensetzt
(`board.py`). Auf einem Gerät installieren: [guides/de/getting-started.md](../../guides/de/getting-started.md); bauen
im Detail: [building.md](building.md).

## 1. Die Ports

| Port (`--port`) | Gerät | Basis-Firmware | Image bei |
|---|---|---|---|
| `cardputer_adv` (Standard) | M5Stack Cardputer ADV (ESP32-S3, ohne PSRAM) | `cardputer-adv-micropython` - UIFlow 2 mit dem Modul `M5` | 0x0 |
| `twatch2020_v3` | LilyGo T-Watch 2020 V3 (ESP32, 16 MB Flash, 8 MB PSRAM) | `micropython-esp32` - einfaches MicroPython v1.25.0 | 0x1000 |
| `generic_s3_watch` | *experimentell, noch nicht auf einem Gerät ausprobiert*: die als "ESP32-S3 smartwatch" verkauften Uhren (ST7789, CST816, Akku an einem ADC-Pin) | `micropython-esp32` | 0x0 |

Was jedes Gerät hat:

| | Cardputer ADV | T-Watch 2020 V3 | allgemeine S3-Uhr |
|---|---|---|---|
| Eingabe | Tastatur | Touch, ein Knopf | Touch, ein Knopf |
| Notizen und Aufgaben schreiben | ✅ | - (liest und hakt ab) | - |
| Sprachnotizen | ✅ | - | - |
| Ton / Summer / Vibration | Lautsprecher, Summer (optional) | Vibration | - |
| LED | WS2812 (optional) | - | - |
| Hardware-Uhr | DS1302 (optional) | PCF8563 mit Alarm | - (Zeit über WLAN oder Bluetooth) |
| Tiefschlaf | - | ✅ (wacht für Routinen, Kuckuck, Synchronisation auf) | - |
| Bluetooth | Chef | Knoten | Knoten |
| Daten | microSD-Karte | interner Flash | interner Flash |

Die Pins der allgemeinen Uhr sind die eines verbreiteten 1,69"-Boards: prüfe jeden auf deiner Uhr (ihr Schaltplan,
oder die Scans in `tools/hwtest/`) vor dem ersten Build - jeder ist in ihrer `port.toml` mit `CHECK` markiert.

## 2. Woraus ein Port besteht

```
Squirrel!/
  features.toml          hardware-dependent features: what they need, what to hide and leave out without it
  ports/<port>/
    port.toml            the device's hardware: pins, addresses, drivers, feature choices (read on the PC only)
    board.py             puts the drivers together for the app (the only module that knows which device this is)
    firmware/            MicroPython board definition and patches (micropython-esp32 recipe only)
    keymap.py ...        other files of the port
  drivers/               drivers named after the CHIP (st7789_fb, ft6336, cst816, pcf8563, axp202, adc_battery ...);
                         pins come as arguments
  hw/                    device-independent logic: touch -> gestures, battery, sleep, buzzer, LED, clock
  ui/                    touch widgets (ui/touch.py) shared by every touch screen
  port_config.py         GENERATED from port.toml and features.toml - do not edit by hand
```

**Was bei einem Build passiert:**

1. `build_firmware.py --port X` liest `ports/X/port.toml` und `features.toml`.
2. Jeder Abschnitt der `port.toml` ist ein Stück Hardware; jeder Schlüssel mit `true` ist eine Eigenschaft davon (z. B.
   `input.touch`). Eine Funktion aus `features.toml` wird gebaut, wenn der Port alles aus ihren `requires` hat und die
   `[features]` des Ports sie nicht abschalten.
3. `port_config.py` wird geschrieben: jeder Schlüssel wird eine Konstante, benannt nach seinem Pfad
   (`[display] ppi = 220` → `DISPLAY_PPI = 220`, `[i2c.sys] sda = 21` → `I2C_SYS_SDA = 21`), dazu `HARDWARE`,
   `FEATURES` und Listen dessen, was die App verbergen muss (`HIDDEN_MENUS`, `HIDDEN_SCREENS`, `HIDDEN_ACTIONS`,
   `HIDDEN_GROUPS`, `HIDDEN_KEYS`).
4. Nur die in `port.toml` genannten Treiber (`driver = "..."`) kommen in die Firmware, zusammen mit den
   `drivers/`-Modulen, die sie importieren; Module von Funktionen, die der Port nicht hat, und die Ordner anderer Ports
   bleiben draußen.
5. Eine Importprüfung stoppt den Build, wenn Code ein Modul importiert, das nicht Teil dieses Builds ist.

---

## 3. Ein neuer Port Schritt für Schritt

Annahme: Treiber für die Chips des Geräts sind schon in `drivers/` (oder du schreibst sie nach den Schnittstellen in
Abschnitt 5).

### Schritt 1 — der Ordner

`Squirrel!/ports/<name>/` mit `__init__.py` (leer), `port.toml` und `board.py`. Der Ordnername muss gleich
`[port] name` sein.

### Schritt 2 — `port.toml`

Kopiere den Port, der von der Hardware her am nächsten ist, und ändere die Werte. Alle Schlüssel: Abschnitt 4.
Mindestens nötig:

```toml
[port]
name     = "my_watch"
title    = "My Watch"
mcu      = "esp32"
firmware = "micropython-esp32"
board    = "firmware"
idf      = "v5.4.2"
machine  = "My Watch"             # part of sys.implementation._machine

[display]
driver = "st7789_fb"
width  = 240
height = 240

[storage]
driver   = "flash_storage"
base_dir = "/Squirrel"
flash_root = ""
```

Bestätige jeden Hardwarewert (Pin, Adresse, Frequenz, Displaydrehung) zuerst auf dem Gerät. Die Tests in
`tools/hwtest/` laufen über den REPL auf einfachem MicroPython, bevor Squirrel! ins Spiel kommt; siehe `twatch_hw.py`.

### Schritt 3 — `board.py`

Ein Modul mit Funktionen, die die App in dieser Reihenfolge aufruft. Es liest Werte aus `port_config` und gibt sie an
die Treiber weiter. Beispiele: `ports/twatch2020_v3/board.py` (Touch, Uhr mit Alarm, Tiefschlaf),
`ports/cardputer_adv/board.py` (Tastatur, SD-Karte, Modul `M5`) und `ports/generic_s3_watch/board.py` (das kleinste:
Touch, Akku am ADC, ein Knopf).

| Funktion | Wann | Gibt zurück / tut |
|---|---|---|
| `begin()` | zuerst, in `squirrel_boot.py` | schaltet die Versorgung ein und startet das Display (z. B. die PMU vor dem Panel) |
| `begin_buzzer(buzzer, quiet)` | als Erstes in der App | `buzzer.begin(...)`; ohne Summer `buzzer.begin(quiet=quiet)` |
| `make_storage()` | bevor die Einstellungen gelesen werden | ein Objekt mit `mount()`, `remount()`, `is_mounted` |
| `make_input()` | | eine Tastatur, oder `hw.touch_input.TouchInput(chip, ACTIONS, ...)` |
| `make_buttons()` | | `{role: button}`; Rollen: `"quick"` (schneller Rekorder), `"back"` (= ESC, weckt den Bildschirm) |
| `clock_chip()` | | `(factory, name)` oder `(None, None)`; `factory()` → das Objekt der Hardware-Uhr |
| `make_audio()` | | `hw.audio_manager.AudioManager(backend)`; `AudioManager(None)` = kein Ton |
| `power_source()` | | ein Objekt mit `level()`, `charging()`, `millivolts()` (jede kann `None` zurückgeben) |
| `begin_led(led, battery)` | | `led.begin(battery=battery)` ohne LED; mit einer auch `pin` und den Treiber |
| `motion_off()` | | schaltet den Beschleunigungssensor aus; gibt seine I2C-Adresse oder `None` zurück |
| `i2c(name)` | | das aktuelle `machine.I2C`-Objekt des Busses `name`, oder `None` |

Optional (die App prüft, ob sie existieren):

| Name | Zweck |
|---|---|
| `EARLY_CLOCK = True` | das Zifferblatt zeigt die Zeit, bevor der Rest der App gebaut ist (schneller nach dem Aufwachen) |
| `arm_light_sleep_wake()` | eigene Weckquellen für den leichten Schlaf (klassischer ESP32: ext0/ext1), statt `[power_mgmt] wake_pins` |
| `wake_reason()` | nach einem Tiefschlaf: `"alarm"`, `"button"` oder `None` — von der Funktion `deep_sleep` verlangt |
| `deep_sleep(alarm, touch=None)` | stellt den Alarm der Uhr (`(year, month, day, hour, minute)` oder `None`), schaltet Display und Peripherie aus, `machine.deepsleep()` — von `deep_sleep` verlangt |

Touchscreen: das Wörterbuch `ACTIONS` in `board.py` macht aus Gesten App-Aktionen. Auf der Uhr:

```python
ACTIONS = {"tap": "ENTER", "swipe_up": "UP", "swipe_down": "DOWN", "swipe_right": "ESC", "swipe_left": "RIGHT",
           "long": "OPT"}
```

### Schritt 4 — Firmware

**Ein Gerät mit UIFlow 2 (dem Modul `M5`)** — Rezept `cardputer-adv-micropython`; `[port] board` ist das Basis-Board im
Firmware-Repository.

**Jeder andere ESP32 oder ESP32-S3** — Rezept `micropython-esp32`. `ports/<name>/firmware/` (benannt nach
`[port] board`) enthält die Board-Definition für `make BOARD_DIR=...`:

| Datei | Inhalt |
|---|---|
| `mpconfigboard.cmake` | `SDKCONFIG_DEFAULTS` (z. B. `boards/sdkconfig.base`, `sdkconfig.spiram`, `sdkconfig.240mhz`, deine eigene `sdkconfig.board`) und `MICROPY_FROZEN_MANIFEST` |
| `mpconfigboard.h` | `MICROPY_HW_BOARD_NAME` (Quelle von `sys.implementation._machine`, verglichen mit `[port] machine`) und `MICROPY_HW_MCU_NAME` |
| `sdkconfig.board` | Flashgröße, Partitionstabelle, schnellerer Start |
| `manifest.py` | `include("$(PORT_DIR)/boards/manifest.py")` und `freeze("$(BOARD_DIR)/squirrel")` |
| `patches/*.patch` | Patches an MicroPython v1.25.0, mit `git apply` angewendet (optional) |

Das Skript kopiert diesen Ordner zusammen mit den Quellen nach `.build/board-<port>/`; der Baum `vendor/micropython`
bleibt unberührt (bis auf die Patches). Nach einer Änderung an `sdkconfig*` oder `mpconfigboard.cmake` erzeugt das
Skript `sdkconfig` selbst neu.

Ein anderer Chip als ESP32 / ESP32-S3 (z. B. RP2040) braucht ein neues Rezept in `build_firmware.py`.

### Schritt 5 — Funktionen

Funktionen schalten sich nach der Hardware von selbst ein. In `[features]` kannst du eine nur abschalten
(`wifi_ntp = false`) oder verlangen (`true`). Eine Funktion zu verlangen, die die Hardware nicht leisten kann, stoppt
den Build mit einem Fehler.

| Funktion | Braucht | Ohne sie |
|---|---|---|
| `text_edit` | `input.keyboard` | kein Editor für Notizen, Aufgaben und Gedankenablage |
| `notes` | `input.keyboard` | Notizenmenü verborgen |
| `key_calibration` | `input.keyboard` | keine Tastenkalibrierung |
| `voice_notes` | `audio_in`, `storage.removable` | keine Aufnahmen |
| `wifi_ntp` | `radio.wifi` | Zeit nur von Hand oder von der Hardware-Uhr |
| `hw_clock` | `clock` | kein "Sync RTC" |
| `led` | `signal.led` | LED-Einstellungen und -Tests verborgen |
| `buzzer` | `signal.buzzer` | Summer-Einstellungen und -Test verborgen |
| `deep_sleep` | `clock.alarm`, `power_mgmt.deep_sleep` | kein Schlafmodus `deep` und kein Bildschirm "Geplante Alarme" |
| `ble_sync` | `radio.ble` | keine Bluetooth-Synchronisation (der Knoten-Teil) |
| `ble_hub` | `radio.ble`, `input.keyboard` | das Gerät kann nicht der Chef einer Synchronisation sein |

Eine neue hardware-abhängige Funktion ist ein neuer Abschnitt in `features.toml`: `requires`, `modules` (Dateien, die
aus dem Build bleiben), `screens`, `menus`, `actions`, `settings` (Einstellungsgruppen) und `keys` (einzelne
Einstellungen).

### Schritt 6 — prüfen

```bash
python3 build_firmware.py --port my_watch --gen-port-config   # port.toml errors; port_config.py to inspect
python3 build_firmware.py --port my_watch --stage-only        # file selection, imports, mpy-cross compile
python3 build_firmware.py --gen-port-config                   # restores the Cardputer's port_config.py
python3 build_firmware.py --port my_watch --flash /dev/ttyACM0
```

Die `port_config.py` neben den Quellen gehört zum Standardport (dem Cardputer). Stelle sie nach `--gen-port-config`
für einen anderen Port immer vor dem Commit wieder her. Ein Build erzeugt immer seine eigene Kopie und ignoriert die
neben den Quellen.

Erster Start: `/boot_log.txt` (Uhr) oder `/flash/boot_log.txt` (Cardputer) zeigt, welche Teile gestartet sind
(`[TOUCH]`, `[RTC]`, `[POWER]` ...). Bericht in Thonny: `import sq_info; sq_info.report()`.

Wenn du gemeinsamen Code änderst, prüfe, dass der Cardputer sich weiter genauso verhält: `tools/sim/compare.sh`
vergleicht Zeichenspur, Protokoll und Dateien zweier Versionen im Simulator (`tools/sim/README.md`).

---

## 4. `port.toml` — Schlüsselreferenz

Regeln:
- ein Abschnitt = ein Stück Hardware; `installed = false` in einem Abschnitt heißt, dass es fehlt (der Abschnitt bleibt
  als Verdrahtungsnotiz);
- ein Schlüssel mit `true` = eine Hardware-Eigenschaft, die Funktionen verlangen können (`input.touch`, `clock.alarm`);
- `driver = "x"` = die Datei `drivers/x.py`, die existieren muss;
- Zahlen können als `0x38` und `400_000` geschrieben werden.

Der Build prüft: `[port]`, `[display]` mit `driver`, `width`, `height`, `[storage]` mit `base_dir`, dass jeder Treiber
und `board.py` existieren. Andere Schlüssel liest `board.py`, ihre Namen sind also frei, aber die unten genannten zu
nutzen hält die Ports einheitlich.

### `[port]`
| Schlüssel | Bedeutung |
|---|---|
| `name` | der Name des Port-Ordners |
| `title` | Anzeigename |
| `mcu` | `esp32`, `esp32s3` |
| `firmware` | Rezept: `micropython-esp32` oder `cardputer-adv-micropython` |
| `board` | Ordner der Board-Definition im Port (`micropython-esp32`) oder das UIFlow-Basis-Board |
| `idf` | ESP-IDF-Version (`v5.4.2`) |
| `machine` | Teil von `sys.implementation._machine`; die Gerätevorbereitung verweigert jedes andere Gerät |
| `reset_lines_low` | `true` für eine USB-Seriell-Brücke mit Auto-Reset (CH9102, CP210x): DTR/RTS werden beim Öffnen des REPL abgesenkt |

### `[display]`
| Schlüssel | Bedeutung |
|---|---|
| `driver` | `m5_display` (M5.Lcd) oder `st7789_fb` (Framebuffer + Senden des geänderten Rechtecks; siehe unten) |
| `width`, `height` | Panelgröße in Pixeln |
| `layout_height` | die Höhe, für die noch nicht umgestaltete Bildschirme zeichnen (135 = das Layout des Cardputers, zentriert) |
| `ppi` | Pixel pro Zoll; Touch-Ziele und Gesten werden daraus in Millimetern bemessen |
| `fonts` | `vlw` (M5-Schriften) oder `bitmap` |
| `spi_id`, `sck`, `mosi`, `cs`, `dc`, `rst`, `baud`, `backlight`, `madctl`, `row_offset` | Verdrahtung und Ausrichtung des Panels (`st7789_fb`) |
| `buffer_rows` | `st7789_fb` in Streifen dieser Zeilenzahl (Standard: das ganze Panel, wenn es höchstens ein Viertel des freien RAMs belegt, sonst Streifen von 40 Zeilen) |
| `clock_footer` | der Standardtext unter der Uhr (nie übersetzt) |

**Streifenmodus.** Ein ganzer Framebuffer sind 2 Bytes pro Pixel: 115 KB für 240 × 240. Ein Modul ohne PSRAM hat etwa
160 KB Heap für alles, deshalb hält `st7789_fb` dort kein ganzes Bild: es merkt sich die Zeichenaufrufe eines Bildes
und spielt sie für jeden Streifen von 40 Zeilen in einen 19-KB-Puffer, wobei jeder Streifen gesendet wird, sobald er
fertig ist. Das Bild ist dasselbe (`tools/tests/test_st7789_strips.py`), das Zeichnen etwas langsamer.

### `[i2c.<name>]`
`id`, `sda`, `scl`, `freq`. Andere Abschnitte verweisen mit `bus = "<name>"` auf einen Bus.

### `[input]`
| Schlüssel | Bedeutung |
|---|---|
| `driver` | `tca8418_keypad` (Tastatur) oder ein Touch-Chip (`ft6336`, `cst816`) |
| `keyboard` | `true` = man kann Text tippen (Funktionen `text_edit`, `notes`) |
| `touch` | `true` = Touch-Bildschirme in voller Höhe |
| `swap_xy`, `mirror_x`, `mirror_y` | Umrechnung von den Koordinaten des Touch-Chips auf das Bild |
| `bus`, `addr`, `int`, `rst` | Verdrahtung |

### `[buttons.<rolle>]`
`driver` (`gpio_button`, `axp_pek`) und z. B. `pin`. Rollen: `quick`, `back`.

### `[storage]`
| Schlüssel | Bedeutung |
|---|---|
| `driver` | `sd_spi` oder `flash_storage` |
| `removable` | `true` = eine Karte (von `voice_notes` verlangt) |
| `base_dir` | der Datenordner von Squirrel! (`/sd/Squirrel`, `/Squirrel`) |
| `flash_root` | wo der interne Flash eingehängt ist: `/flash` (UIFlow), `""` (einfaches MicroPython) |
| `slot`, `width`, `sck`, `miso`, `mosi`, `cs`, `freq` | SD-Karte |

### `[clock]`
`driver` (`ds1302`, `pcf8563`), `bus` oder Pins, `int`, `alarm = true`, wenn der Alarm des Chips das Gerät wecken kann.

### `[power]`
`driver` (`m5_power`, `axp202`, `adc_battery`), `bus`, `irq`; `adc_battery`: `pin`, `divider`.

### `[audio_out]`, `[audio_in]`
`driver` (`m5_audio`). Ohne diese Abschnitte kein Ton und keine Aufnahme.

### `[signal.led]`, `[signal.buzzer]`
LED: `driver = "ws2812"`, `pin`, `min_backlight`, `max_sum`. Summer oder Vibrationsmotor: `driver = "pin_pulser"`,
`pin`, `pwm_freq` (0 = an/aus, sonst ein Ton in Hz), `installed`.

### `[motion]`
`driver` (`bmi270`, `bma423`), `bus`, `addrs` — vorerst wird der Beschleunigungssensor beim Start nur ausgeschaltet.

### `[radio]`
`wifi = true`, `ble = true` (die Bluetooth-Synchronisation).

### `[power_mgmt]`
| Schlüssel | Bedeutung |
|---|---|
| `wake_pins` | Pins, die aus dem leichten Schlaf wecken (aktiv low) |
| `slow_cpu_hz` | CPU-Takt, solange der Bildschirm gedimmt ist |
| `deep_sleep` | `true` = das Gerät kann wirklich schlafen (mit `clock.alarm` schaltet es die Funktion `deep_sleep` ein) |
| `wake_button`, `wake_alarm` | Pins, die aus dem Tiefschlaf wecken: der Knopf und die INT-Leitung der Uhr |

### `[features]`
`<funktion> = false | true` — siehe Schritt 5.

---

## 5. Treiber-Schnittstellen

Ein neuer Treiber muss von nichts erben; er braucht nur dieselben Aufrufe. Im Code beschrieben:
`Squirrel!/hw/ports.py`.

| Teil | Nötige Aufrufe |
|---|---|
| Display (`drivers/<x>.py` mit einem Objekt `lcd`) | die Aufrufe von M5.Lcd: `fillScreen`, `fillRect`, `drawRect`, `drawLine`, `fillCircle`, `drawCircle`, `drawPixel`, `drawString`, `setTextColor`, `setTextSize`, `textWidth`, `fontHeight`, `setBrightness`, `getBrightness`, `setFont` (wirft ohne Schriften); Farben `0xRRGGBB`. Framebuffer: `_needs_flush = True` und `flush()`; volle Höhe für Touch-Bildschirme: `_can_layout = True`, `set_layout(h)`, `layout_origin()`; vor einem Tiefschlaf: `sleep()` |
| Touch-Chip | `read_point()` → `(x, y)` oder `None` (`OSError` bei einem Busfehler), `reopen()`; vor einem Tiefschlaf: `hibernate()`. Gesten, Schwellen in Millimetern und Umrechnungen macht `hw/touch_input.py` |
| Tastatur | `get_pressed_action()` → `(action, modifier_changed)`, `set_text_mode(on)`, `acknowledge()` |
| Knopf | `pressed()` — `True` einmal pro Druck |
| Speicher | `mount()`, `remount()`, `is_mounted` |
| Versorgung | `level()`, `charging()`, `millivolts()` — `None`, wenn unbekannt |
| Hardware-Uhr | `hw.rtc_base.TimeProvider`: `is_available`, `get_datetime()`, `set_datetime(dt)` (Tupel wie `time.localtime()`); mit Alarm auch `set_alarm(dt or None)`, `alarm_fired()`, `clear_alarm_flag()` |
| Summer / Vibration | eine Klasse mit `set(on)` (und `pwm` für einen Ton), als `pulser` an `buzzer.begin` übergeben |

---

## 6. Bekannte Fallen (aus dem T-Watch-Port)

- **Kein REPL nach dem Öffnen des Ports**: die CH9102-Brücke hält den ESP32 über DTR/RTS im Reset →
  `reset_lines_low = true`.
- **Panik bei schnellem SPI**: auf einem klassischen ESP32 begrenzen Pins außerhalb von IO_MUX den SPI auf ~26,67 MHz;
  nutze `miso=None`, wenn der Standard-MISO mit einem anderen Pin kollidiert.
- **Viper-Code**: `mpy-cross` braucht `-march=xtensawin` (der Build gibt es mit).
- **Eingefrorener Code hat Vorrang** vor Dateien im Flash. `.py`-Dateien in `<flash>/apps/Squirrel` ersetzen ihn nur im
  DEV-Modus (Markierungsdatei `<flash>/DEV`) — praktisch für schnelle Versuche ohne neuen Firmware-Build.
- **`BUILD=` auf der `make`-Befehlszeile** zerstört den MicroPython-Build — nicht übergeben.
- **Von einer PMU versorgte Peripherie** (AXP202): Display, Ton und Touch brauchen vielleicht einen bestimmten LDO mit
  einer bestimmten Spannung, bevor der Treiber etwas sendet.
- **Anstehende Interrupts** des Energie- oder Uhren-Chips halten die INT-Leitung auf low und verhindern das Aufwachen —
  lösche sie in `begin()`.
