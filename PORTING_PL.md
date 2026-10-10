# Squirrel! — architektura portów (propozycja)

Status: **etap 0 zaimplementowany** (niezacommitowany, do testu na urządzeniu), etapy 1–3 to nadal propozycja.
Cel: jeden kod aplikacji, wiele urządzeń. Pierwsze dwa porty to **Cardputer ADV**
(obecny kod, traktowany od teraz jako port) i **LilyGo T-Watch 2020 V3**.

## 0. Etap 0 — co zrobiono i czym różni się od planu

Zrobione kroki 1–9 z §4. Weryfikacja bez urządzenia: symulator `Squirrel!/tools/sim/` (aplikacja pod MicroPython unix
1.25 z atrapami sprzętu) przechodzi scenariusz po wszystkich menu, tworzy TODO/notatkę/Mind Dump, nagrywa i odtwarza,
uruchamia focus i Pomodoro. **Stary i nowy kod dają identyczny ślad** (28 013 wywołań rysujących, log konsoli,
`boot_log.txt`, pliki na SD) — także w wariancie z kodem zamrożonym. Wszystkie moduły kompilują się `mpy-cross` z firmware.

Odstępstwa od planu (świadome):
- **Brak `hw/null.py`.** Istniejące klasy już mają formę „nic nie rób”: `AudioManager(backend=None)`,
  `led.begin(pin=None)`, `buzzer.begin(pin=None)`, `RTCManager(chip=None)`, `BatteryMonitor(read=None)` — opisane w `hw/ports.py`.
- **`hw/ports.py` to dokumentacja** (interfejsy jako klasy z docstringami); sterowniki po nich nie dziedziczą,
  build go nie zamraża.
- **`AudioManager` został w `hw/`** — dostaje obiekty Mic/Speaker od płytki (`drivers/m5_audio.py`). API M5.Mic/M5.Speaker
  jest więc interfejsem audio; T-Watch dostanie adapter I2S z tymi samymi wywołaniami.
- **`hw/radio.py` i `wifi_ntp.py` nie przeniesione** — to czysty MicroPython, działa na każdym ESP32.
- **Ukrywanie menu bez duplikacji:** `features.toml` → build wylicza `HIDDEN_MENUS/SCREENS/ACTIONS/GROUPS` w `port_config.py`,
  `menu_tree.py` filtruje raz przy imporcie, Personalize pomija grupy.
- **Przyciski mają role, nie nazwy:** `make_buttons() -> {"quick": ...}`; ekrany: `on_quick_button()` zamiast `on_button0()`.
- **Kontrola importów w buildzie** obejmuje teraz wszystkie pakiety aplikacji (port, który importuje moduł innego portu
  albo wyciętej funkcji, nie przejdzie `--stage-only`).

Koszt: ~1,5 KB sterty po starcie (zmierzone ~3 KB na 64-bitowym PC z kodem zamrożonym), ~5 KB bajtkodu we flashu.

Zostaje na etap 1 (wyszło przy teście sztucznego portu bez klawiatury/nagrywania/Wi-Fi/LED/buzzera):
- listy TODO/Notatki pokazują „+ [New Item]”, który bez edytora kończy się komunikatem „Cannot open” (bez awarii);
- menu *Silent mode* pokazuje kanały Buzzer/LED także urządzeniu, które ich nie ma;
- współrzędne pionowe ekranów (stopki na y≈115–119) są pod 135 px — układ 240×240 do zrobienia;
- przepis bazy firmware `micropython-esp32` w `build_firmware.py` (dziś pełny build tylko dla UIFlow 2).

---

## 1. Stan obecny — co wiąże kod ze sprzętem

Logika aplikacji jest już w dużej mierze oddzielona od sprzętu (ekrany dostają akcje jako
napisy `"UP"`, `"ENTER"`, `"ESC"`…, usługi są tykane przez `ServiceManager`, ekrany rzadko
używane ładują się leniwie). Sprzężenia, które trzeba rozwiązać:

| Miejsce | Problem |
|---|---|
| `squirrel_app.py` | importuje i tworzy konkretne sterowniki (`CardputerKeypad`, `SDCardManager`, `RTCManager` z DS1302, `AudioManager` z M5, `ButtonPoller(0)`…) |
| `squirrel_boot.py` | wywołuje `M5.begin()` — na T-Watch modułu `M5` nie ma |
| `nuts.py` | miesza **fakty sprzętowe** (piny SD/DS1302/buzzera/LED, adres TCA8418, mapy klawiatury) z **domyślnymi ustawieniami użytkownika**; importuje `M5.Lcd` tylko po to, by odczytać kolory |
| 19 plików | `from M5 import ...` — m.in. `ui_renderer.py`, `notifier.py`, 6 ekranów (`from M5 import Lcd` zamiast `from gfx import Lcd`), `hw/battery.py`, `hw/audio_manager.py`, `hw/led.py` |
| `ui_renderer.py`, `notifier.py`, `screens/rhythm_screens.py` | stały rozmiar ekranu 240×135 wpisany liczbami |
| `hw/power.py` | piny wybudzania `(0, 11)` i adres BMI270 wpisane w kod; magistrala I2C pożyczana z klawiatury (`keypad.i2c`) |
| `menu_tree.py`, `appconfig_schema.py` | menu i ustawienia pokazują wszystko (LED, buzzer, DS1302, Wi-Fi) niezależnie od tego, czy sprzęt istnieje |
| `build_firmware.py` | zna tylko jedną bazę firmware (`cardputer-adv-micropython`, UIFlow2) i jedną płytkę |

Uwaga: `Claude.md` opisuje katalog `hal/` z adapterami T-Watch (`AXP202Power`, `ST7789Display`…),
ale w repozytorium go nie ma — opis trzeba będzie zaktualizować po wdrożeniu tej propozycji.

---

## 2. Docelowa struktura

```
Squirrel!/
  ports/
    cardputer_adv/
      port.toml           # opis sprzętu + wybór funkcji (czytany TYLKO na PC przez build_firmware.py)
      board.py            # fabryka: składa sterowniki w obiekt Hardware
      keymap.py           # mapy klawiatury (przeniesione z nuts.py)
    twatch2020_v3/
      port.toml
      board.py
      gestures.py         # dotyk -> akcje ("UP", "ENTER", "ESC", ...)
  drivers/                # sterowniki nazwane OD UKŁADU, nie od urządzenia -> wielokrotnego użytku
    tca8418_keypad.py     #   (dziś hw/cardputer_keypad.py)
    ds1302.py, pcf8563.py
    axp202.py             #   T-Watch 2020; AXP2101 dla T-Watch S3 itd. w przyszłości
    m5_power.py           #   adapter M5.Power (Cardputer)
    bmi270.py, bma423.py
    ft6336_touch.py
    st7789_display.py     #   adapter ekranu dla firmware bez modułu M5
    m5_display.py         #   adapter M5.Lcd
    ws2812_led.py         #   (dziś hw/led.py, część sprzętowa)
    pin_pulser.py         #   wspólny silnik wzorców dla buzzera I silnika wibracji
    m5_audio.py, i2s_audio.py
    sd_spi.py, flash_storage.py
    wifi.py               #   (dziś hw/radio.py + wifi_ntp.py)
  hw/                     # INTERFEJSY (porty) + obiekty „Null” dla brakującego sprzętu
    ports.py              #   Display, Input, Storage, Clock, PowerSource, AudioOut, AudioIn,
                          #   Signal (LED / buzzer / wibracje), Motion, Radio, Buttons
    null.py               #   NullLed, NullSignal, NullAudio, NullMotion, NullRadio ...
  features.py             # has("led"), has("text_edit") ... (czyta wygenerowany port_config)
  port_config.py          # GENEROWANY przez build_firmware.py z port.toml (zamrażany w firmware)
  nuts.py                 # już tylko domyślne ustawienia użytkownika i stałe aplikacji
```

### 2.1 Zasada: aplikacja nie wie, na czym działa

```python
# squirrel_app.py (szkic)
import board                           # port_config.BOARD_MODULE -> ports/<port>/board.py
hw = board.make_hardware()             # obiekt z polami: display, input, storage, clock, power,
                                       # audio_out, audio_in, led, buzzer, vibro, motion, radio, buttons
self.renderer = UIRenderer(hw.display)
self.keypad   = hw.input               # ten sam kontrakt co dziś CardputerKeypad
self.rtc      = RTCManager(hw.clock)   # sprzętowy RTC albo None -> SoftTimeProvider
```

Brakujący sprzęt to **obiekt Null**, nie `None`: `NullLed.signal(...)` nic nie robi, więc
wywołania w `scheduler.py`, `intervals.py`, `notifier.py` nie potrzebują `if`-ów.

### 2.2 Interfejsy (`hw/ports.py`) — minimalne, wywiedzione z tego, czego kod już używa

| Interfejs | Kontrakt (to, co aplikacja już wywołuje) | Cardputer ADV | T-Watch 2020 V3 |
|---|---|---|---|
| `Display` | podzbiór API `M5.Lcd`: `fillRect`, `drawString`, `setTextColor`, `setTextSize`, `textWidth`, `fillScreen`, `setBrightness`, `width`, `height` | `m5_display` (M5.Lcd + `.vlw`) | `st7789_display` (moduł C st7789, konwersja RGB888→RGB565, czcionki bitmapowe z polskimi znakami) |
| `Input` | `get_pressed_action() -> (akcja, modifier_changed)`, `set_text_mode()`, `modifiers_as_keys`, `display_modifier`, `acknowledge()` | `tca8418_keypad` | `ft6336_touch` + `gestures.py` |
| `Buttons` | zdarzenia nazwane: `"BTN_A"`, `"PWR_SHORT"`, `"PWR_LONG"` (zamiast `on_button0`) | G0 | przycisk boczny (PEK układu AXP202, przerwanie GPIO35) |
| `Storage` | `mount() -> base_dir`, `free_bytes()`, `is_removable` | karta SD (SPI) → `/sd/Squirrel` | wewnętrzny flash (littlefs) → `/flash/Squirrel` |
| `Clock` | dzisiejszy `TimeProvider` + `persistent: bool` | DS1302 (dodatek, opcjonalny) lub brak | PCF8563 (wbudowany, podtrzymywany baterią) |
| `PowerSource` | `level()`, `charging()` (może być `None`), `millivolts()`, `vbus()` | `m5_power` (ADC, ładowanie nieznane) | `axp202` (pełne dane: %, mV, ładowanie, VBUS, prąd) |
| `AudioOut` | `beep()`, `start_playback()`… (dzisiejszy `AudioManager`) | M5.Speaker | I2S MAX98357A (zasilanie z szyny AXP) |
| `AudioIn` | `start_recording()`… | M5.Mic (ES8311) | mikrofon PDM — patrz ryzyka, §6 |
| `Signal` | `signal(mode, color?)`, `busy`, `off()` | LED WS2812, buzzer (dodatek) | silnik wibracji (GPIO4, przez `pin_pulser`) |
| `Motion` | `tick()`, zdarzenia `"TILT"`, `"TAP2"`, `"FACE_DOWN"`, `"SHAKE"`, `steps()` | BMI270 | BMA423 |
| `Radio` | `power_down()`, `connect()`, NTP | Wi-Fi | Wi-Fi (opcjonalnie, domyślnie wyłączone) |

Rozmiar ekranu, piny wybudzania i układ czcionek pochodzą z `port_config` (`SCREEN_W`,
`SCREEN_H`, `WAKE_PINS`…), a nie z literałów w kodzie.

---

## 3. Konfiguracja portu

### 3.1 Format: rekomenduję TOML zamiast YAML

Plik portu jest czytany **tylko na PC**, przez `build_firmware.py` — MicroPython na urządzeniu
nigdy go nie parsuje. Z obu formatów:

- **TOML** — parser `tomllib` jest w bibliotece standardowej Pythona od 3.11, a `build_firmware.py`
  ma dziś zasadę „tylko biblioteka standardowa”. Komentarze, typy, czytelne sekcje.
- **YAML** — równie czytelny, ale wymaga `PyYAML` (dodatkowa zależność) i ma pułapki typów
  (`no` → `False`, `0755` → liczba ósemkowa).

Struktura jest identyczna w obu formatach; jeśli wolisz `.yml`, przejście to zamiana parsera
w jednej funkcji. Poniżej przykłady w TOML.

### 3.2 Co robi z nim `build_firmware.py`

```
python3 build_firmware.py --port twatch2020_v3
```

1. Czyta `ports/<port>/port.toml` i `features.toml` (rejestr funkcji, §3.4).
2. **Waliduje**: każda włączona funkcja ma wymagany sprzęt (np. `voice_notes` bez `audio_in`
   → błąd buildu, zanim ruszy półgodzinna kompilacja).
3. **Generuje `port_config.py`** — zwykły moduł Pythona ze stałymi (piny, rozmiar ekranu,
   `FEATURES = frozenset(...)`, `BOARD_MODULE`), zamrażany razem z aplikacją.
4. **Wybiera pliki do zamrożenia**: moduły i ekrany wyłączonych funkcji nie trafiają do obrazu
   (mniej flasha, mniej RAM-u przy imporcie). Sterowniki spoza listy portu też nie.
5. Wybiera **bazę firmware**: przepis `cardputer-adv-micropython` (UIFlow2, moduł `M5`) albo
   `micropython-esp32` (upstream MicroPython + moduł C sterownika ekranu).
6. Dalej jak dziś: płytka pochodna, `make`, obraz w `dist/squirrel-<port>-<git>-<czas>.bin`.

Tryb DEV (`/flash/DEV`) działa dalej: wygenerowany `port_config.py` można wgrać obok
pozostałych plików.

### 3.3 Przykład: `ports/cardputer_adv/port.toml`

```toml
[port]
name     = "cardputer_adv"
title    = "M5Stack Cardputer ADV"
mcu      = "esp32s3"
firmware = "cardputer-adv-micropython"      # przepis bazy firmware w build_firmware.py
board    = "M5STACK_CardputerADV_Custom"
idf      = "v5.4.2"                         # 5.5.x: mikrofon ES8311 zwraca ciszę

[display]
driver = "m5_display"
width  = 240
height = 135
fonts  = "vlw"

[i2c.sys]                                   # wspólna magistrala: klawiatura + IMU
id = 0
sda = 8
scl = 9
freq = 400_000

[input]
driver = "tca8418_keypad"
bus    = "sys"
addr   = 0x34
int    = 11
keymap = "keymap"                           # ports/cardputer_adv/keymap.py

[buttons]
BTN_A = { pin = 0, active_low = true }      # G0: szybkie nagrywanie

[storage]
driver = "sd_spi"
slot = 3
sck = 40
miso = 39
mosi = 14
cs = 12
freq = 1_000_000
base_dir = "/sd/Squirrel"

[clock]
driver   = "ds1302"                         # dodatek lutowany; brak odpowiedzi = zegar programowy
optional = true
clk = 6
dat = 4
rst = 3

[power]
driver = "m5_power"                         # ADC: poziom tak, ładowanie nieznane

[audio_out]
driver = "m5_audio"

[audio_in]
driver = "m5_audio"
sample_rate = 16000

[signal.led]
driver = "ws2812_led"
pin = 21
max_sum = 228
min_backlight = 255                         # LED zasilany z szyny podświetlenia (patrz nuts.LED_MIN_BACKLIGHT)

[signal.buzzer]
driver = "pin_pulser"
pin = 13
pwm_freq = 0                                # 0 = buzzer aktywny
installed = true                            # dodatek: false = pin nigdy nie jest ruszany

[motion]
driver = "bmi270"
bus = "sys"
addr = [0x69, 0x68]
default = "off"                             # dziś: wyłączany przy starcie (oszczędność)

[radio]
wifi = true

[power_mgmt]
wake_pins = [0, 11]
slow_cpu_hz = 80_000_000

[features]                                  # nadpisania; reszta wynika ze sprzętu (§3.4)
voice_notes = true
motion_gestures = false                     # eksperymentalne, domyślnie wyłączone
```

### 3.4 Przykład: `ports/twatch2020_v3/port.toml`

Piny i zasilanie **potwierdzone testami na zegarku 2026-10-10** (`Squirrel!/tools/hwtest/README_PL.md`, sekcja „Wyniki”).
Poprawki względem pierwszej wersji tej propozycji: audio zasila **LDO4 = 3,3 V** (nie LDO3), dotyk ma reset na GPIO14,
SPI ekranu najwyżej 26,67 MHz, obraz obrócony o 180° (MADCTL 0xC0, przesunięcie 80 wierszy).

```toml
[port]
name     = "twatch2020_v3"
title    = "LilyGo T-Watch 2020 V3"
mcu      = "esp32"                          # klasyczny ESP32, 16 MB flash, 8 MB PSRAM
firmware = "micropython-esp32"              # upstream MicroPython (bez UIFlow / modułu M5)
board    = "ESP32_GENERIC"
variant  = "SPIRAM"
idf      = "v5.4.2"
c_modules = ["st7789"]                      # sterownik ekranu jako moduł C (szybki, z czcionkami)

[i2c.sys]                                   # AXP202, BMA423, PCF8563
id = 0
sda = 21
scl = 22
freq = 400_000

[i2c.touch]
id = 1
sda = 23
scl = 32
freq = 400_000

[power]
driver = "axp202"
bus = "sys"
irq = 35
rails = { display = "ldo2", audio = "ldo4" }   # LDO2: ekran; LDO4 = 3,3 V: wzmacniacz (LDO3 nieużywane w V3)

[display]
driver = "st7789_display"
width  = 240
height = 240
madctl = 0xC0                               # obrót 180 stopni ...
row_offset = 80                             # ... pamięć panelu ma 320 wierszy
spi = { id = 2, sck = 18, mosi = 19, cs = 5, dc = 27, baud = 26_666_666 }   # więcej nie przez macierz GPIO
backlight = { pin = 15, pwm = true }
fonts = "bitmap"                            # czcionki skonwertowane z TTF, z polskimi znakami

[input]
driver = "ft6336_touch"
bus = "touch"
addr = 0x38
int = 38
rst = 14                                    # impuls resetu przed użyciem
gestures = "gestures"                       # ports/twatch2020_v3/gestures.py

[buttons]
PWR = { source = "axp202.pek" }             # krótko = wybudź / wstecz, długo = szybka akcja

[storage]
driver = "flash_storage"
base_dir = "/flash/Squirrel"
quota_kb = 4096                             # limit dla danych aplikacji na wewnętrznym flashu

[clock]
driver = "pcf8563"
bus = "sys"
int = 37
persistent = true                           # nie potrzebuje Wi-Fi do odzyskania czasu

[audio_out]
driver = "i2s_audio"
bck = 26
ws = 25
dout = 33
rail = "audio"
stereo = true                               # MAX98357A gra jeden kanał / mieszankę

[audio_in]
driver = "pdm_mic"                          # wymaga obsługi PDM (patrz §6) - na razie wyłączone
data = 2
clk = 0
enabled = false

[signal.vibro]
driver = "pin_pulser"
pin = 4

[motion]
driver = "bma423"
bus = "sys"
int = 39
features = ["tilt_wake", "double_tap", "step_counter"]

[radio]
wifi = true                                 # sprzęt jest; z menu znika, gdy features.wifi_ntp = false

[power_mgmt]
wake_pins = [35, 38, 39]                    # AXP (przycisk), dotyk, akcelerometr
screen_timeout_s = 8

[features]
wifi_ntp = false                            # RTC jest podtrzymywany - Wi-Fi zbędne
text_edit = false                           # brak klawiatury
voice_notes = false
steps = true
```

### 3.5 Rejestr funkcji: `features.toml` (wspólny dla wszystkich portów)

Jedno miejsce, które mówi, czego każda funkcja potrzebuje i z czego się składa. Na jego
podstawie build wybiera pliki, a aplikacja filtruje menu i ustawienia.

```toml
[voice_notes]
requires = ["audio_in", "storage.removable|storage.quota_kb>=2048"]
modules  = ["screens/record_screen.py", "screens/playback_screen.py"]
screens  = ["RECORD", "PLAYBACK"]
menus    = ["RECORDS"]

[text_edit]
requires = ["input.keyboard"]
modules  = ["screens/note_editor_screen.py", "screens/mind_dump_screen.py", "line_editor.py",
            "note_editor.py", "screens/input_screen.py"]
screens  = ["NOTE_EDITOR", "MIND_DUMP"]
menus    = ["MIND"]
settings = ["Keyboard"]

[wifi_ntp]
requires = ["radio.wifi"]
modules  = ["wifi_ntp.py", "wifi_profiles.py", "time_sync.py", "screens/wifi_screen.py",
            "screens/time_sync_screen.py"]
screens  = ["WIFI_NETWORKS", "TIME_SYNC"]
menus    = ["CONNECTIONS"]
settings = ["Network"]                      # grupy z appconfig_schema.py

[led]
requires = ["signal.led"]
modules  = ["screens/led_test_screen.py"]
screens  = ["LED_TESTS"]
menus    = ["LED_TEST", "LED_MODES"]
settings = ["LED"]

[buzzer]
requires = ["signal.buzzer"]
menus    = ["BUZZER_TEST"]
settings = ["Buzzer"]

[vibro]
requires = ["signal.vibro"]
settings = ["Vibration"]

[key_calibration]
requires = ["input.keyboard"]
modules  = ["key_calibrator.py"]
screens  = ["CALIBRATOR"]

[steps]
requires = ["motion.step_counter"]
```

W kodzie: `menu_tree.py` dostaje mapę `REQUIRES = {"LED_TEST": "led", ...}` (albo 5. pole
wpisu), `MenuScreen` pomija pozycje, dla których `features.has(...)` jest fałszem, a
`appconfig_schema.py` — całe grupy ustawień. Kanały ciszy (`SILENT`) budują się z listy
sygnałów portu: na Cardputerze *dźwięk / buzzer / LED*, na zegarku *dźwięk / wibracje*.

---

## 4. Plan zmian (kolejność ma znaczenie)

### Etap 0 — refaktoryzacja bez zmiany zachowania na Cardputerze

Każdy krok osobno buildowalny i testowalny na obecnym urządzeniu.

1. **`port_config.py` + `features.py`.** Najpierw napisany ręcznie dla Cardputera; `nuts.py`
   tymczasowo re-eksportuje stałe sprzętowe (`from port_config import SD_SCK, ...`), żeby nic
   się nie posypało.
2. **Usunięcie `M5` spoza adapterów.** `nuts.Colors` → stałe RGB888 (bez `M5.Lcd`);
   6 ekranów: `from M5 import Lcd` → `from gfx import Lcd`; `import M5` w `ui_renderer.py`
   i `notifier.py` — przez `gfx`. Po tym kroku `M5` występuje tylko w `gfx.py`, `hw/battery.py`,
   `hw/audio_manager.py`, `hw/led.py`, `squirrel_boot.py`.
3. **Geometria ekranu** z `port_config.SCREEN_W/H` w `ui_renderer.py`, `notifier.py`,
   `rhythm_screens.py`.
4. **`hw/ports.py` + `hw/null.py`** i **`ports/cardputer_adv/board.py`**; `squirrel_app.py`
   bierze sprzęt z `board.make_hardware()`. `squirrel_boot.py`: `M5.begin()` → `board.begin()`.
5. **Wspólna magistrala I2C** tworzona przez `board`, nie przez klawiaturę
   (`power.start()` przestaje sięgać do `keypad.i2c`).
6. **Przyciski jako zdarzenia** (`BTN_A`, `PWR_SHORT`…) zamiast `on_button0`;
   na Cardputerze `BTN_A` = dzisiejszy G0.
7. **Przeniesienie sterowników do `drivers/`** z nazwami od układów; `buzzer.py` rozdzielony
   na silnik wzorców (`pin_pulser`) + ustawienia „który feature może brzęczeć”.
8. **Filtrowanie menu i ustawień** wg `features`.
9. **`build_firmware.py --port`**: czytanie `port.toml`, walidacja, generowanie
   `port_config.py`, wybór plików. Domyślny port = `cardputer_adv`, więc dzisiejsze
   `python3 build_firmware.py` działa bez zmian.

### Etap 1 — uruchomienie T-Watch (minimum użyteczne)

1. Przepis bazy `micropython-esp32` w `build_firmware.py` (upstream MicroPython,
   `ESP32_GENERIC` + `SPIRAM`, moduł C ekranu).
2. `axp202.py` — **pierwszy w kolejności startu** (włączenie LDO2, inaczej ekran jest czarny),
   poziom baterii, ładowanie, przycisk PEK.
3. `st7789_display.py` z kontraktem `Display`; czcionka z polskimi znakami.
4. `ft6336_touch.py` + `gestures.py`: przesunięcie w górę/dół → `UP`/`DOWN`, stuknięcie →
   `ENTER`, przesunięcie w prawo → `ESC`, długie przytrzymanie → `OPT` (oznacz jako zrobione).
   Pozycje menu są numerowane, więc stuknięcie w wiersz może wysyłać jego cyfrę.
5. `pcf8563.py` jako `Clock(persistent=True)`; `RTCManager` przy starcie czyta czas z RTC,
   a przy ręcznym ustawieniu zapisuje go z powrotem (dziś robi to dla DS1302).
6. `flash_storage.py`, wibracje przez `pin_pulser`.
7. Układ ekranów dla 240×240 (więcej miejsca w pionie: większy zegar, 6–7 wierszy listy).

### Etap 2 — to, co zegarek robi lepiej

1. BMA423: podniesienie nadgarstka wybudza ekran, podwójne stuknięcie zamyka powiadomienie,
   licznik kroków jako czwarty słupek w statystykach.
2. Agresywne oszczędzanie: ekran gaśnie po kilku sekundach, uśpienie płytkie (light sleep)
   z wybudzaniem przez AXP / dotyk / akcelerometr, wyłączanie szyny audio, gdy głośnik milczy.
3. Dźwięk przez I2S MAX98357A (sygnały, kukułka).

### Etap 3 — wymiana danych (oba porty)

Zegarek bez klawiatury potrzebuje innej drogi do tworzenia notatek i TODO:
1. **Najprościej: USB** — pliki w `/flash/Squirrel` edytowane z PC (`mpremote`, Thonny).
   Format plików jest ten sam co na karcie SD Cardputera, więc wystarczy je skopiować.
2. Później, opcjonalnie: synchronizacja przez Wi-Fi (punkt dostępowy + prosta strona) albo BLE.

---

## 5. Funkcje: wdrożyć / pominąć / później

Legenda: ✅ wdrożyć · ⚙️ opcjonalne, wyłączane w buildzie · 🔜 później · ❌ pominąć

| Funkcja | Cardputer ADV | T-Watch 2020 V3 | Uwagi |
|---|---|---|---|
| Zegar (ekran główny) | ✅ | ✅ | zegarek: wybudzanie podniesieniem nadgarstka |
| Lista TODO — przegląd, oznaczanie jako zrobione | ✅ | ✅ | stuknięcie / długie przytrzymanie |
| Tworzenie i edycja TODO / notatek | ✅ | ❌ → 🔜 przez synchronizację | brak klawiatury; ekranowa klawiatura na 240×240 jest niewygodna |
| Podgląd notatek | ✅ | ✅ | |
| Mind Dump | ✅ | ❌ | wymaga pisania |
| Notatki głosowe — nagrywanie | ✅ (karta SD) | ❌ → 🔜 | mikrofon PDM + mało miejsca na flashu (§6) |
| Notatki głosowe — odtwarzanie | ✅ | ❌ | nie ma czego odtwarzać bez nagrywania |
| Szybkie nagrywanie przyciskiem | ✅ (G0) | ❌ | przycisk boczny = wybudź / wstecz |
| Focus timer + statystyki | ✅ | ✅ | zegarek: + kroki |
| Pomodoro / Trening | ✅ | ✅ | na zegarku wibracje — dyskretne, idealne |
| Metronom | ✅ | ✅ | wibracje zamiast dźwięku |
| Oddychanie | ✅ (LED) | ✅ (wibracje / animacja) | |
| Rutyny — powiadomienia | ✅ | ✅ | |
| Rutyny — edycja | ✅ | ❌ (tylko włącz/wyłącz) | nazwy wpisywane na Cardputerze / przez sync |
| Kukułka | ✅ | ✅ | |
| Tryb cichy | ✅ (dźwięk/buzzer/LED) | ✅ (dźwięk/wibracje) | kanały z listy sygnałów portu |
| Personalizacja | ✅ | ✅ | ustawienia filtrowane wg funkcji |
| Wi-Fi + NTP, sieci Wi-Fi | ✅ (główne źródło czasu) | ⚙️ domyślnie wyłączone | RTC zegarka jest podtrzymywany |
| Sprzętowy RTC | ⚙️ DS1302 (dodatek) | ✅ PCF8563 | |
| Ręczne ustawianie czasu | ✅ | ✅ | zapis również do sprzętowego RTC |
| Bateria — poziom | ✅ (ADC) | ✅ (AXP202) | |
| Bateria — stan ładowania, prąd | ❌ (sprzęt nie podaje) | ✅ | `LED_CHARGING` na Cardputerze nie ma sensu bez tej informacji |
| Dziennik baterii | ✅ | ✅ | zegarek: więcej kolumn (prąd, VBUS) |
| LED RGB | ✅ | ❌ | brak sprzętu |
| Buzzer | ⚙️ (dodatek) | ❌ | |
| Wibracje | ❌ | ✅ | ten sam silnik wzorców co buzzer |
| Kalibracja klawiszy | ✅ | ❌ | |
| Czcionka z polskimi znakami | ✅ (.vlw) | ✅ (bitmapowa) | różny mechanizm, ten sam kontrakt `Display` |
| Akcelerometr: podniesienie wybudza | ⚙️ 🔜 | ✅ | |
| Akcelerometr: podwójne stuknięcie zamyka powiadomienie | ❌ | ✅ | |
| Akcelerometr: ekranem w dół = cisza / drzemka | ⚙️ 🔜 | ⚙️ 🔜 | naturalny gest dla Cardputera leżącego na biurku |
| Akcelerometr: potrząśnięcie = odłóż rutynę | ⚙️ 🔜 | ⚙️ 🔜 | |
| Licznik kroków | ❌ | ✅ | |
| Oszczędzanie: wolniejszy CPU, light sleep | ✅ | ✅ | zegarek: agresywniej, wybudzanie z 3 źródeł |
| Nadajnik IR | — | ❌ | poza zakresem Squirrel |
| Synchronizacja (USB / Wi-Fi / BLE) | 🔜 | 🔜 (USB od etapu 1) | |

Na Cardputerze akcelerometr BMI270 zostaje domyślnie wyłączony (jak dziś, bo zużywa prąd);
gesty są opcjonalną funkcją `motion_gestures`, włączaną w `port.toml`.

---

## 6. Ryzyka i otwarte pytania

1. **Mikrofon PDM na T-Watch V3.** `machine.I2S` w upstream MicroPython obsługuje tylko
   standardowy tryb I2S, nie PDM. Nagrywanie wymaga modułu C albo łatki na firmware — stąd
   „później”. Miejsce na flashu (16 MB, ~13 MiB na system plików po firmware ~2,5 MiB): WAV 16 bit mono
   16 kHz (32 KB/s) to **~7 min** łącznie, 8 kHz (jak Cardputer) ~14 min; z kompresją IMA ADPCM 4:1 ~28 / ~56 min
   (koder w C albo `viper` — czysty Python za wolny).
2. **Pliki konfiguracyjne akcelerometrów.** BMA423 i BMI270 wymagają wgrania do układu
   kilkukilobajtowego bloba, zanim zadziałają funkcje typu licznik kroków / wykrywanie ruchu.
   Sterowniki MicroPython istnieją (porty z bibliotek LilyGo i Boscha); trzeba sprawdzić
   licencje przed włączeniem ich do repozytorium (`THIRD_PARTY_NOTICES.md`).
3. **Dwie bazy firmware.** Cardputer jest na UIFlow2 (`M5`, `hardware.SDCard`), zegarek będzie
   na upstream MicroPython. Wszystko, co dziś woła `M5` bezpośrednio, musi przejść przez
   adapter — to główny koszt etapu 0.
4. **Kolory i wydajność rysowania.** `M5.Lcd` przyjmuje RGB888, sterownik ST7789 — RGB565.
   Adapter konwertuje i trzyma konwersje w pamięci podręcznej. Pełne przerysowania ekranu
   240×240 są droższe niż 240×135: warto zachować dzisiejsze „rysuj tylko to, co się zmieniło”.
5. **Pamięć.** Cardputer ADV nie ma PSRAM, T-Watch ma 8 MB — leniwe ładowanie ekranów zostaje,
   bo to wciąż ograniczenie Cardputera.
6. **Format konfiguracji.** Rekomendacja: TOML (biblioteka standardowa). Jeśli `.yml` jest
   ważny z innych względów — do decyzji, koszt to jedna zależność.
7. **Kolejne urządzenia.** Sterowniki nazwane od układów ułatwiają następne porty:
   T-Watch S3 (AXP2101, BMA423, PCF8563), Cardputer bez ADV, M5StickC Plus2, LilyGo T-Deck
   (ma klawiaturę — wtedy `text_edit` wraca).
