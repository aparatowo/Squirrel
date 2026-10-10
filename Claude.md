# Squirrel!

MicroPython notes/TODO manager for M5Stack Cardputer (ESP32-S3).
Runs under UIFlow2 / MicroPython 1.25.0 on ESP-IDF 5.4.2.
Licence: MIT — Rafał Nitychoruk (Ijon Tichy).

## Repo layout

```
squirrel_app.py        # entry point (uruchamiany z /flash/main.py)
squirrel_boot.py       # boot sequence (/flash/main.py wywołuje to)
nuts.py                # kolory, stałe aplikacji, domyślne ustawienia użytkownika (BEZ faktów sprzętowych)
features.toml          # rejestr funkcji zależnych od sprzętu (czego wymagają, jakie moduły/menu/ekrany/grupy ustawień)
features.py            # has("voice_notes") ... (czyta port_config.FEATURES)
port_config.py         # GENEROWANY z ports/<port>/port.toml (build_firmware.py --gen-port-config) - nie edytować
ports/                 # jeden folder na urządzenie
  cardputer_adv/       #   port.toml (sprzęt, piny, funkcje), board.py (składa sterowniki), keymap.py
screens/               # UI screens (base_screen.py + indywidualne pliki)
ui_renderer.py         # warstwa rysowania
gfx.py                 # ekran widziany przez aplikację (sterownik z port_config.DISPLAY_DRIVER), SCREEN_W/SCREEN_H
storage_manager.py     # I/O plików na SD card (/sd/Squirrel)
drivers/               # sterowniki nazwane od UKŁADU (piny dostają jako argumenty, nie czytają port_config)
  tca8418_keypad.py, sd_spi.py, ds1302.py, gpio_button.py, ws2812.py, pin_pulser.py, bmi270.py
  m5_display.py, m5_power.py, m5_audio.py   # API firmware UIFlow 2 (moduł M5)
hw/                    # logika sprzętu niezależna od urządzenia (import: from hw.<moduł> import ...)
  ports.py             #   dokumentacja interfejsów portu (nie importowany, nie zamrażany)
  rtc_base.py          #   abstrakcja TimeProvider
  rtc_provider.py      #   RTCManager (zegar sprzętowy z portu) + SoftTimeProvider
  audio_manager.py     #   nagrywanie/odtwarzanie przez obiekty Mic/Speaker portu
  battery.py, power.py, radio.py
  buzzer.py, led.py    #   tryby, ustawienia, cisza; pin/sterownik daje płytka
ui/                    # interfejs niezależny od urządzenia: touch.py = widżety dotykowe (przyciski, stepper, przytrzymanie),
                       #   rozmiary w mm z [display] ppi; ekran dotykowy: full_height = True, panel = TouchPanel()
tools/sim/             # symulator: aplikacja pod MicroPython unix z atrapami sprzętu; porównanie dwóch wersji
device/                # main.py = launcher /flash/main.py (wgrywa go build_firmware.py --flash / --setup-device)
fonts/                 # squirrel.vlw (polskie znaki)
vendor/                # cardputer-adv-micropython (klonowane przez build_firmware.py)
build_firmware.py      # buduje .bin z zamrożonym kodem aplikacji
dist/                  # zbudowane obrazy .bin (gitignore)
.build/                # stan pośredni budowania (gitignore)
```

## Architektura

- **Screens**: `screens/base_screen.py` jako klasa bazowa; każdy ekran w osobnym pliku
- **Modifier keys**: SHIFT i FN — sticky (toggle przy ponownym naciśnięciu); CTRL/OPT/ALT — momentary (auto-reset po jednym klawiszu); zdefiniowane w `nuts.py` jako `MODIFIER_STICKY` / `MODIFIER_MOMENTARY`
- **Note/TODO**: ten sam flow `InputScreen`; pierwsza linia = tytuł
- **Edytor notatek**: `note_editor.py` (logika biznesowa) + `note_editor_screen.py` (UI/klawiatura/kursor) — oba potrzebne
- **SD card**: montowana przez `machine.SDCard` (fallback: `hardware.SDCard` z UIFlow2); zarządzana przez `drivers/sd_spi.py`
- **RTC**: DS1302 odczytywany raz przy bocie; czas można też ustawić przez NTP (Wi-Fi wyłączane po synchronizacji); fallback: `SoftTimeProvider`
- **Keyboard**: TCA8418 (I2C matrix driver); GPIO 3/4/5/6 wolne od klawiatury

## Konwencje kodowania

- Bez button-hint footerów na listach plików — hinty tylko w podglądzie pliku
- Komentarze w kodzie po angielsku; UI po polsku
- Konfiguracja aplikacji w `nuts.py`, sprzętu w `ports/<port>/port.toml`; kod aplikacji nie hardkoduje stałych ani pinów
- Moduł `M5` tylko w `drivers/m5_*.py` i `ports/cardputer_adv/board.py`; reszta rysuje przez `gfx.Lcd`
- Refaktoryzacja bez zmiany zachowania: sprawdzaj `tools/sim/compare.sh` (ślad musi być identyczny)
- Jeden ekran = jeden plik w `screens/`; logika biznesowa oddzielona od UI

## Hardware

- **Board**: M5Stack Cardputer ADV (ESP32-S3)
- **Display**: wbudowany
- **Keyboard**: TCA8418 I2C matrix
- **SD card**: SPI (SCK=40 MISO=39 MOSI=14 CS=12 slot=3), montowana jako `/sd`
- **RTC**: DS1302 na GPIO 6/4/3 (opcjonalnie, fizycznie podłączony)
- **Audio**: ES8311 mic (uwaga: zwraca ciche próbki na ESP-IDF 5.5.x — używać 5.4.2)
- **Dev machine**: Linux Mint; upload plików przez Thonny

## Budowanie firmware

Firmware repo (`cardputer-adv-micropython`) jest klonowane automatycznie do `vendor/` przy pierwszym uruchomieniu.

```bash
# Pierwsze uruchomienie (raz na maszynę):
python3 build_firmware.py --install-idf    # instaluje ESP-IDF 5.4.2 (~1 GB)
python3 build_firmware.py --setup          # submoduły, patche, mpy-cross (wymaga quilt)

# Codzienne użycie:
python3 build_firmware.py --check          # sprawdź środowisko, nic nie zmieniaj
python3 build_firmware.py                  # zbuduj → dist/squirrel-*.bin
python3 build_firmware.py --flash /dev/ttyACM0   # zbuduj i wgraj

# Aktualizacja firmware repo:
python3 build_firmware.py --update-repo    # git pull vendor/cardputer-adv-micropython

# Inne:
python3 build_firmware.py --mpy            # kompiluj do .mpy bez budowania firmware
python3 build_firmware.py --stage-only     # sprawdź źródła bez budowania
python3 build_firmware.py --diagnose       # wyjaśnij ostatni błąd buildu
```

Wymagania systemowe: `git`, `make`, `gcc`, `quilt`, `python3`.
ESP-IDF 5.4.2 — **nie 5.5.x** (mikrofon zwraca ciszę na nowszych wersjach).

Po flashowaniu wgraj przez Thonny: `/flash/main.py` (z `device/main.py`) i `/flash/fonts/squirrel.vlw`.

## Porty (Cardputer ADV, T-Watch 2020 V3)

Architektura i plan: `PORTING_PL.md`.  Etap 0 (refaktoryzacja, Cardputer jako port) zrobiony; T-Watch: jeszcze nie ma
folderu `ports/twatch2020_v3/` ani sterowników (AXP202, ST7789, FT6336, PCF8563, BMA423) - etap 1.
Sprzęt urządzenia: `ports/<port>/port.toml` -> `port_config.py`; płytka: `ports/<port>/board.py` (interfejsy w `hw/ports.py`).
Funkcja zależna od sprzętu = wpis w `features.toml`; brakujący sprzęt ukrywa jej menu/ekrany/ustawienia i wycina moduły z buildu.
Uśpienie: `POWER_SLEEP` off/light/deep. Deep (funkcja `deep_sleep`: `[clock] alarm` + `[power_mgmt] deep_sleep`) =
`deep_sleep.py` (kiedy zasnąć, zapis/odtworzenie stanu: focus, drzemki rutyn) + `alarms.py` (kolejka zdarzeń: rutyny,
kukułka, drzemki → najbliższe do alarmu RTC); budzi przycisk (ext0) albo alarm RTC (ext1). Wczesna tarcza po wybudzeniu:
`squirrel_boot._early_clock` (płytka z `EARLY_CLOCK = True`). `.frozen` jest na początku `sys.path` (poza trybem DEV).
Dotyk w warstwach: sterownik układu (`drivers/ft6336.py`: tylko `read_point()`) → `hw/touch_input.py` (gesty → akcje, `tap_xy`/
`touch_xy`, przekształcenie z `[input]` portu) → `ui/touch.py` (widżety w mm). Nowy zegarek z innym dotykiem = nowy `read_point()`.

## Planowane funkcje

- **Zegar z kukułką** — powiadomienia czasowe/przypomnienia
- **Pomodoro / Metronom / Ćwiczenia oddechowe** — jeden wpis menu, pierwsza pozycja
- **Mind Dump** — submenu Notatki; trigger z ekranu zegara przez Aa; max 200 znaków; ENTER zapisuje
- **Dyktafon** — buttonA / G0 z każdego ekranu głównego
- **Quick Capture** — FN+SPACE z ekranu zegara
- **"Teraz robię"** — widok focus, duża czcionka, jeden wyróżniony TODO
- **Filtr DZIŚ** — na liście TODO
- **Automatyczny timestamp** notatek z DS1302
- **Tagi emocjonalne** per notatka: 🔥💡😰🕑 (jeden klawisz po wpisie)
- **Statystyki** — czas focus / rutyny / done TODO (jeden ekran, 3 słupki dziennie)
- Ukończone TODO usuwane po tygodniu
- Tło/timery (kukułka, metronom, focus) działają niezależnie od aktualnego menu, także przy wyłączonym ekranie