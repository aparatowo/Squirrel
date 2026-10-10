# 🐿️ Squirrel! — porty: instalacja i nowe urządzenia

*[English version](PORTS_EN.md)*

Squirrel! działa na kilku urządzeniach z jednego kodu. Każde urządzenie to **port**: folder `Squirrel!/ports/<nazwa>/`
z opisem sprzętu (`port.toml`) i modułem, który ten sprzęt składa dla aplikacji (`board.py`). Ten dokument opisuje:

1. jak zainstalować Squirrel! na wybranym urządzeniu,
2. jak dodać nowe urządzenie, gdy sterowniki jego układów już istnieją,
3. co musi zawierać plik `port.toml`.

Historia i uzasadnienie architektury: [PORTING_PL.md](PORTING_PL.md). Instrukcja krok po kroku dla Cardputera ADV:
[INSTALACJA_PL.md](INSTALACJA_PL.md).

---

## 1. Obsługiwane urządzenia

| Port (`--port`) | Urządzenie | Firmware bazowy | Obraz wgrywany od |
|---|---|---|---|
| `cardputer_adv` (domyślny) | M5Stack Cardputer ADV (ESP32-S3) | `cardputer-adv-micropython` — UIFlow 2 z modułem `M5` | 0x0 |
| `twatch2020_v3` | LilyGo T-Watch 2020 V3 (ESP32, 16 MB flash, 8 MB PSRAM) | `micropython-esp32` — czysty MicroPython v1.25.0 | 0x1000 |

Co działa na którym urządzeniu: [RELEASE_1.2_pl.md](RELEASE_1.2_pl.md).

---

## 2. Instalacja na konkretnym urządzeniu

Wszystkie polecenia wykonuje się w folderze `Squirrel!/`. Skrypt `build_firmware.py` korzysta wyłącznie z biblioteki
standardowej Pythona.

### 2.1. Raz na komputerze

```bash
python3 build_firmware.py --install-idf     # ESP-IDF 5.4.2 (~1 GB) do ~/esp-idf-v5.4.2
python3 build_firmware.py --check           # sprawdza środowisko, niczego nie zmienia
```

Tylko dla Cardputera, raz: `python3 build_firmware.py --setup` (submoduły i łatki repozytorium UIFlow; wymaga
`sudo apt install quilt`). Dla zegarka nie trzeba nic więcej: przy pierwszym buildzie skrypt sam klonuje MicroPythona
v1.25.0 do `vendor/micropython` i nakłada łatki portu.

### 2.2. Który port USB?

```bash
ls /dev/ttyACM* /dev/ttyUSB*
udevadm info -q property -n /dev/ttyACM0 | grep ID_VENDOR_ID
```

Cardputer zgłasza producenta `303a` (Espressif), T-Watch `1a86` (układ CH9102). Przed wgrywaniem zamknij Thonny, bo
blokuje port.

### 2.3. Build i wgranie jednym poleceniem

```bash
# Cardputer ADV (port domyślny)
python3 build_firmware.py --flash /dev/ttyACM0

# T-Watch 2020 V3
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0
```

Skrypt buduje obraz (`dist/squirrel-<port>-...bin` z plikiem `.txt` opisującym zawartość), wgrywa go i przygotowuje
urządzenie: zapisuje `main.py` uruchamiający Squirrel!, a na Cardputerze także wyłącza `boot.py` z UIFlow. Pierwszy
build kompiluje całe ESP-IDF, więc trwa kilka minut; kolejne trwają krócej.

Wgrywanie nie usuwa danych: notatek, To-Do, statystyk ani `config.txt`. Na Cardputerze dane są na karcie SD, na zegarku
w `/Squirrel` na wewnętrznym flashu, którego obraz wgrywany od 0x1000 nie nadpisuje.

### 2.4. Inne warianty

```bash
# wgranie gotowego obrazu bez budowania
python3 build_firmware.py --port twatch2020_v3 --flash-image dist/squirrel-twatch2020_v3-....bin --flash /dev/ttyACM0

# tylko przygotowanie urządzenia wgranego wcześniej
python3 build_firmware.py --port twatch2020_v3 --setup-device /dev/ttyACM0

# sam build, bez wgrywania
python3 build_firmware.py --port twatch2020_v3
```

Żeby nie podawać `--port` za każdym razem, zapisz domyślny port w `Squirrel!/build_config.json`:

```json
{"port": "twatch2020_v3"}
```

### 2.5. Konkretna wersja Squirrel!

Wydania są oznaczone tagami git (`1.1`, `1.2`, ...):

```bash
git fetch --tags
git checkout 1.2          # potem build jak w 2.3
git checkout main         # powrót do najnowszego kodu
```

Porty istnieją od wersji 1.2; wersja 1.1 i starsze budują się wyłącznie dla Cardputera ADV.

### 2.6. T-Watch: przed pierwszym wgraniem

Zegarek ma fabrycznie inne oprogramowanie. Zanim je nadpiszesz, zrób pełną kopię flasha:

```bash
tools/hwtest/twatch_phase0.sh /dev/ttyACM0        # 16 MB, kilka minut, z sumą MD5 -> .build/hwtest/
```

Przywrócenie stanu fabrycznego: `esptool.py --chip esp32 -p /dev/ttyACM0 -b 921600 write_flash 0x0 <kopia>.bin`.

---

## 3. Z czego składa się port

```
Squirrel!/
  features.toml          funkcje zależne od sprzętu: czego wymagają, co ukryć i wyciąć, gdy ich nie ma
  ports/<port>/
    port.toml            sprzęt urządzenia: piny, adresy, sterowniki, wybór funkcji (czytany tylko na PC)
    board.py             składa sterowniki dla aplikacji (jedyny moduł, który wie, jakie to urządzenie)
    firmware/            definicja płytki MicroPythona (tylko przepis micropython-esp32)
    keymap.py ...        inne pliki własne portu
  drivers/               sterowniki nazwane od UKŁADU (st7789_fb, ft6336, pcf8563, axp202 ...); piny dostają w argumentach
  hw/                    logika niezależna od urządzenia: dotyk -> gesty, bateria, uśpienie, brzęczyk, dioda, zegar
  ui/                    widżety dotykowe (ui/touch.py) wspólne dla każdego ekranu dotykowego
  port_config.py         GENEROWANY z port.toml i features.toml - nie edytuj ręcznie
```

**Jak to działa przy buildzie:**

1. `build_firmware.py --port X` czyta `ports/X/port.toml` i `features.toml`.
2. Każda sekcja `port.toml` to element sprzętu; każdy klucz z wartością `true` to jego cecha (np. `input.touch`).
   Funkcja z `features.toml` jest budowana, gdy port ma wszystko z jej `requires`, a `[features]` portu jej nie wyłącza.
3. Powstaje `port_config.py`: każdy klucz staje się stałą nazwaną od ścieżki (`[display] ppi = 220` →
   `DISPLAY_PPI = 220`, `[i2c.sys] sda = 21` → `I2C_SYS_SDA = 21`), do tego `HARDWARE`, `FEATURES` i listy tego, co aplikacja
   ma ukryć (`HIDDEN_MENUS`, `HIDDEN_SCREENS`, `HIDDEN_ACTIONS`, `HIDDEN_GROUPS`, `HIDDEN_KEYS`).
4. Do firmware trafiają tylko sterowniki wskazane w `port.toml` (`driver = "..."`) razem z modułami `drivers/`, które one
   importują; moduły funkcji, których port nie ma, i foldery innych portów są pomijane.
5. Kontrola importów zatrzymuje build, jeśli kod importuje moduł, którego w tym buildzie nie ma.

---

## 4. Nowy port krok po kroku

Założenie: sterowniki układów urządzenia są już w `drivers/` (albo dopisujesz je według interfejsów z części 6).

### Krok 1 — folder

`Squirrel!/ports/<nazwa>/` z plikami `__init__.py` (pusty), `port.toml` i `board.py`. Nazwa folderu musi być taka
sama jak `[port] name`.

### Krok 2 — `port.toml`

Najlepiej skopiować port najbliższy sprzętowo i zmienić wartości. Pełny opis kluczy: część 5. Wymagane minimum:

```toml
[port]
name     = "moj_zegarek"
title    = "Mój zegarek"
mcu      = "esp32"
firmware = "micropython-esp32"
board    = "firmware"
idf      = "v5.4.2"
machine  = "Moj Zegarek"          # fragment sys.implementation._machine

[display]
driver = "st7789_fb"
width  = 240
height = 240

[storage]
driver   = "flash_storage"
base_dir = "/Squirrel"
flash_root = ""
```

Każdą wartość sprzętową (pin, adres, częstotliwość, obrót ekranu) najpierw potwierdź na urządzeniu. Testy w
`tools/hwtest/` uruchamiają się przez REPL na czystym MicroPythonie, jeszcze bez Squirrel!; wzór: `twatch_hw.py`.

### Krok 3 — `board.py`

Moduł z funkcjami wywoływanymi przez aplikację w podanej kolejności. Czyta wartości z `port_config` i przekazuje je
sterownikom. Wzory: `ports/twatch2020_v3/board.py` (dotyk, zegar z alarmem, deep sleep) i `ports/cardputer_adv/board.py`
(klawiatura, karta SD, moduł `M5`).

| Funkcja | Kiedy | Co zwraca / robi |
|---|---|---|
| `begin()` | pierwsza, w `squirrel_boot.py` | włącza zasilanie i ekran (np. AXP przed panelem) |
| `begin_buzzer(buzzer, quiet)` | pierwsza w aplikacji | `buzzer.begin(...)`; bez brzęczyka `buzzer.begin(quiet=quiet)` |
| `make_storage()` | przed wczytaniem ustawień | obiekt z `mount()`, `remount()`, `is_mounted` |
| `make_input()` | | klawiatura albo `hw.touch_input.TouchInput(chip, ACTIONS, ...)` |
| `make_buttons()` | | `{rola: przycisk}`; role: `"quick"` (szybkie nagrywanie), `"back"` (= ESC, budzi ekran) |
| `clock_chip()` | | `(fabryka, nazwa)` albo `(None, None)`; `fabryka()` → obiekt zegara sprzętowego |
| `make_audio()` | | `hw.audio_manager.AudioManager(backend)`; `AudioManager(None)` = bez dźwięku |
| `power_source()` | | obiekt z `level()`, `charging()`, `millivolts()` (każda może zwrócić `None`) |
| `begin_led(led, battery)` | | `led.begin(battery=battery)` bez diody, z diodą także `pin` i sterownik |
| `motion_off()` | | wyłącza akcelerometr; zwraca jego adres I2C albo `None` |
| `i2c(name)` | | aktualny obiekt `machine.I2C` magistrali `name` albo `None` |

Opcjonalne (aplikacja sprawdza, czy istnieją):

| Nazwa | Do czego |
|---|---|
| `EARLY_CLOCK = True` | tarcza pokazuje godzinę, zanim zbuduje się reszta aplikacji (szybszy widok po wybudzeniu) |
| `arm_light_sleep_wake()` | własne źródła wybudzenia z light sleep (klasyczny ESP32: ext0/ext1), zamiast `[power_mgmt] wake_pins` |
| `wake_reason()` | po deep sleep: `"alarm"`, `"button"` albo `None` — wymagane przy funkcji `deep_sleep` |
| `deep_sleep(alarm, touch=None)` | ustawia alarm zegara (`(rok, mies, dzień, godz, min)` albo `None`), wyłącza ekran i peryferia, `machine.deepsleep()` — wymagane przy `deep_sleep` |

Ekran dotykowy: słownik `ACTIONS` w `board.py` zamienia gesty na akcje aplikacji. Na zegarku:

```python
ACTIONS = {"tap": "ENTER", "swipe_up": "UP", "swipe_down": "DOWN", "swipe_right": "ESC", "swipe_left": "RIGHT",
           "long": "OPT"}
```

### Krok 4 — firmware

**Urządzenie z UIFlow 2 (moduł `M5`)** — przepis `cardputer-adv-micropython`; `[port] board` to płytka bazowa w
repozytorium firmware.

**Każde inne ESP32** — przepis `micropython-esp32`. W `ports/<nazwa>/firmware/` (nazwa z `[port] board`) leży definicja
płytki dla `make BOARD_DIR=...`:

| Plik | Zawartość |
|---|---|
| `mpconfigboard.cmake` | `SDKCONFIG_DEFAULTS` (np. `boards/sdkconfig.base`, `sdkconfig.spiram`, `sdkconfig.240mhz`, własny `sdkconfig.board`) i `MICROPY_FROZEN_MANIFEST` |
| `mpconfigboard.h` | `MICROPY_HW_BOARD_NAME` (z niego pochodzi `sys.implementation._machine`, porównywany z `[port] machine`) i `MICROPY_HW_MCU_NAME` |
| `sdkconfig.board` | rozmiar flasha, tablica partycji, przyspieszenia startu |
| `manifest.py` | `include("$(PORT_DIR)/boards/manifest.py")` i `freeze("$(BOARD_DIR)/squirrel")` |
| `patches/*.patch` | łatki do MicroPythona v1.25.0, nakładane przez `git apply` (opcjonalne) |

Skrypt kopiuje ten folder razem ze źródłami do `.build/board-<port>/`; drzewo `vendor/micropython` zostaje bez zmian
(poza łatkami). Po zmianie `sdkconfig*` albo `mpconfigboard.cmake` skrypt sam wygeneruje `sdkconfig` od nowa.

Inny układ niż ESP32 / ESP32-S3 (np. RP2040) wymaga nowego przepisu w `build_firmware.py`.

### Krok 5 — funkcje

Funkcje włączają się same na podstawie sprzętu. W `[features]` można je tylko wyłączyć (`wifi_ntp = false`) albo
wymusić (`true`). Wymuszenie funkcji, której sprzęt nie spełnia, kończy build błędem.

| Funkcja | Wymaga | Bez niej |
|---|---|---|
| `text_edit` | `input.keyboard` | brak edytora notatek, To-Do i Mind Dump |
| `notes` | `input.keyboard` | menu notatek ukryte |
| `key_calibration` | `input.keyboard` | brak kalibracji klawiszy |
| `voice_notes` | `audio_in`, `storage.removable` | brak nagrań |
| `wifi_ntp` | `radio.wifi` | czas tylko ręcznie lub z zegara sprzętowego |
| `hw_clock` | `clock` | brak „Sync RTC” |
| `led` | `signal.led` | ustawienia i testy diody ukryte |
| `buzzer` | `signal.buzzer` | ustawienia i test brzęczyka ukryte |
| `deep_sleep` | `clock.alarm`, `power_mgmt.deep_sleep` | brak trybu `deep` i ekranu „Upcoming alarms” |

Nowa funkcja zależna od sprzętu to nowa sekcja w `features.toml`: `requires`, `modules` (pliki pomijane w buildzie),
`screens`, `menus`, `actions`, `settings` (grupy ustawień) i `keys` (pojedyncze ustawienia).

### Krok 6 — sprawdzenie

```bash
python3 build_firmware.py --port moj_zegarek --gen-port-config   # błędy port.toml, port_config.py do obejrzenia
python3 build_firmware.py --port moj_zegarek --stage-only        # dobór plików, importy, kompilacja mpy-cross
python3 build_firmware.py --gen-port-config                      # przywraca port_config.py Cardputera
python3 build_firmware.py --port moj_zegarek --flash /dev/ttyACM0
```

`port_config.py` obok źródeł należy do portu domyślnego (Cardputera). Po `--gen-port-config` dla innego portu zawsze
przywróć go przed commitem. Build zawsze generuje własną kopię i nie korzysta z tej obok źródeł.

Pierwszy start: `/boot_log.txt` (zegarek) lub `/flash/boot_log.txt` (Cardputer) pokazuje, które elementy się
uruchomiły (`[TOUCH]`, `[RTC]`, `[POWER]` ...). Raport w Thonny: `import sq_info; sq_info.report()`.

Jeśli zmieniasz kod wspólny, sprawdź, czy Cardputer zachowuje się tak samo: `tools/sim/compare.sh` porównuje ślad
rysowania, log i pliki dwóch wersji w symulatorze (`tools/sim/README.md`).

---

## 5. `port.toml` — opis kluczy

Zasady:
- sekcja = element sprzętu; `installed = false` w sekcji oznacza, że go nie ma (sekcja zostaje jako notatka o połączeniu);
- klucz z wartością `true` = cecha sprzętu, którą mogą wymagać funkcje (`input.touch`, `clock.alarm`);
- `driver = "x"` = plik `drivers/x.py`, który musi istnieć;
- liczby można zapisywać jako `0x38` i `400_000`.

Build sprawdza: `[port]`, `[display]` z `driver`, `width`, `height`, `[storage]` z `base_dir`, istnienie każdego
sterownika i `board.py`. Pozostałe klucze czyta `board.py`, więc nazwy są dowolne, ale warto trzymać się tych poniżej,
żeby porty były do siebie podobne.

### `[port]`
| Klucz | Znaczenie |
|---|---|
| `name` | nazwa folderu portu |
| `title` | nazwa do wyświetlania |
| `mcu` | `esp32`, `esp32s3` |
| `firmware` | przepis: `micropython-esp32` albo `cardputer-adv-micropython` |
| `board` | folder definicji płytki w porcie (`micropython-esp32`) albo płytka bazowa UIFlow |
| `idf` | wersja ESP-IDF (`v5.4.2`) |
| `machine` | fragment `sys.implementation._machine`; przygotowanie urządzenia odmawia pracy na innym |
| `reset_lines_low` | `true` dla mostka USB-serial z auto-resetem (CH9102, CP210x): DTR/RTS opuszczone przy otwieraniu REPL |

### `[display]`
| Klucz | Znaczenie |
|---|---|
| `driver` | `m5_display` (M5.Lcd) albo `st7789_fb` (bufor ramki + wysyłanie zmienionego prostokąta) |
| `width`, `height` | rozmiar panelu w pikselach |
| `layout_height` | wysokość, dla której rysują ekrany jeszcze nieprzerobione (135 = układ Cardputera, wyśrodkowany) |
| `ppi` | piksele na cal; z niego liczone są milimetry celów dotyku i gestów |
| `fonts` | `vlw` (czcionki M5) albo `bitmap` |
| `spi_id`, `sck`, `mosi`, `cs`, `dc`, `baud`, `backlight`, `madctl`, `row_offset` | podłączenie i orientacja panelu (`st7789_fb`) |

### `[i2c.<nazwa>]`
`id`, `sda`, `scl`, `freq`. Inne sekcje wskazują magistralę przez `bus = "<nazwa>"`.

### `[input]`
| Klucz | Znaczenie |
|---|---|
| `driver` | `tca8418_keypad` (klawiatura) albo układ dotyku (`ft6336`) |
| `keyboard` | `true` = można pisać (funkcje `text_edit`, `notes`) |
| `touch` | `true` = ekrany dotykowe na pełną wysokość |
| `swap_xy`, `mirror_x`, `mirror_y` | przekształcenie współrzędnych układu dotyku na obraz |
| `bus`, `addr`, `int`, `rst` | podłączenie |

### `[buttons.<rola>]`
`driver` (`gpio_button`, `axp_pek`) i np. `pin`. Role: `quick`, `back`.

### `[storage]`
| Klucz | Znaczenie |
|---|---|
| `driver` | `sd_spi` albo `flash_storage` |
| `removable` | `true` = karta (wymagana przez `voice_notes`) |
| `base_dir` | folder danych Squirrel! (`/sd/Squirrel`, `/Squirrel`) |
| `flash_root` | gdzie zamontowany jest wewnętrzny flash: `/flash` (UIFlow), `""` (czysty MicroPython) |
| `slot`, `width`, `sck`, `miso`, `mosi`, `cs`, `freq` | karta SD |

### `[clock]`
`driver` (`ds1302`, `pcf8563`), `bus` albo piny, `int`, `alarm = true`, jeśli alarm układu może obudzić urządzenie.

### `[power]`
`driver` (`m5_power`, `axp202`), `bus`, `irq`.

### `[audio_out]`, `[audio_in]`
`driver` (`m5_audio`). Bez tych sekcji nie ma dźwięku ani nagrywania.

### `[signal.led]`, `[signal.buzzer]`
Dioda: `driver = "ws2812"`, `pin`, `min_backlight`, `max_sum`. Brzęczyk albo silnik wibracyjny: `driver = "pin_pulser"`,
`pin`, `pwm_freq` (0 = włącz/wyłącz, inaczej ton w Hz), `installed`.

### `[motion]`
`driver` (`bmi270`, `bma423`), `bus`, `addrs` — dziś akcelerometr jest tylko wyłączany przy starcie.

### `[radio]`
`wifi = true`.

### `[power_mgmt]`
| Klucz | Znaczenie |
|---|---|
| `wake_pins` | piny budzące z light sleep (aktywne stanem niskim) |
| `slow_cpu_hz` | taktowanie przy przygaszonym ekranie |
| `deep_sleep` | `true` = urządzenie może spać naprawdę (z `clock.alarm` włącza funkcję `deep_sleep`) |
| `wake_button`, `wake_alarm` | piny budzące z deep sleep: przycisk i linia INT zegara |

### `[features]`
`<funkcja> = false | true` — patrz krok 5.

---

## 6. Interfejsy sterowników

Nowy sterownik nie musi po niczym dziedziczyć; wystarczy, że ma te same wywołania. Opis w kodzie: `Squirrel!/hw/ports.py`.

| Element | Wymagane wywołania |
|---|---|
| ekran (`drivers/<x>.py` z obiektem `lcd`) | wywołania M5.Lcd: `fillScreen`, `fillRect`, `drawRect`, `drawLine`, `fillCircle`, `drawCircle`, `drawPixel`, `drawString`, `setTextColor`, `setTextSize`, `textWidth`, `fontHeight`, `setBrightness`, `getBrightness`, `setFont` (rzuca wyjątek bez czcionek); kolory `0xRRGGBB`. Bufor ramki: `_needs_flush = True` i `flush()`; pełna wysokość dla ekranów dotykowych: `_can_layout = True`, `set_layout(h)`, `layout_origin()`; przed deep sleep: `sleep()` |
| układ dotyku | `read_point()` → `(x, y)` albo `None` (wyjątek `OSError` przy błędzie magistrali), `reopen()`; przed deep sleep: `hibernate()`. Gesty, progi w mm i przekształcenia robi `hw/touch_input.py` |
| klawiatura | `get_pressed_action()` → `(akcja, zmiana_modyfikatora)`, `set_text_mode(on)`, `acknowledge()` |
| przycisk | `pressed()` — `True` raz na naciśnięcie |
| pamięć | `mount()`, `remount()`, `is_mounted` |
| zasilanie | `level()`, `charging()`, `millivolts()` — `None`, gdy nieznane |
| zegar sprzętowy | `hw.rtc_base.TimeProvider`: `is_available`, `get_datetime()`, `set_datetime(dt)` (krotki jak `time.localtime()`); z alarmem także `set_alarm(dt or None)`, `alarm_fired()`, `clear_alarm_flag()` |
| brzęczyk / wibracja | klasa z `set(on)` (i `pwm` dla tonu) przekazywana jako `pulser` do `buzzer.begin` |

---

## 7. Znane pułapki (z portu T-Watch)

- **Brak REPL po otwarciu portu**: mostek CH9102 trzyma ESP32 w resecie przez DTR/RTS → `reset_lines_low = true`.
- **Panika przy szybkim SPI**: na klasycznym ESP32 piny poza IO_MUX ograniczają SPI do ~26,67 MHz; `miso=None`, jeśli
  domyślny MISO koliduje z innym pinem.
- **Kod viper**: `mpy-cross` musi dostać `-march=xtensawin` (build robi to sam).
- **Kod zamrożony ma pierwszeństwo** przed plikami na flashu. Pliki `.py` z `<flash>/apps/Squirrel` zastępują go tylko
  w trybie DEV (plik-znacznik `<flash>/DEV`) — wygodne do szybkich prób bez przebudowy firmware.
- **`BUILD=` w wierszu poleceń `make`** psuje build MicroPythona — nie podawaj go.
- **Zasilanie peryferiów przez PMU** (AXP202): ekran, dźwięk i dotyk mogą wymagać włączenia konkretnego LDO o
  konkretnym napięciu, zanim sterownik cokolwiek wyśle.
- **Zaległe przerwania** układu zasilania lub zegara trzymają linię INT w stanie niskim i uniemożliwiają wybudzenie —
  skasuj je w `begin()`.
