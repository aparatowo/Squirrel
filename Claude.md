# Squirrel!

MicroPython notes/TODO manager for M5Stack Cardputer (ESP32-S3).
Runs under UIFlow2 / MicroPython 1.25.0 on ESP-IDF 5.4.2.
Licence: MIT — Rafał Nitychoruk (Ijon Tichy).

## Repo layout

```
squirrel_app.py        # entry point (uruchamiany z /flash/main.py)
squirrel_boot.py       # boot sequence (/flash/main.py wywołuje to)
nuts.py                # cała konfiguracja: keymaps, kolory, stałe, BASE_DIR
screens/               # UI screens (base_screen.py + indywidualne pliki)
ui_renderer.py         # warstwa rysowania
storage_manager.py     # I/O plików na SD card (/sd/Squirrel)
hw/                    # moduły dotykające sprzętu bezpośrednio (import: from hw.<moduł> import ...)
  sd_card.py           #   SDCardManager (SPI: SCK=40 MISO=39 MOSI=14 CS=12 slot=3)
  cardputer_keypad.py  #   obsługa klawiatury I2C (TCA8418)
  rtc_base.py          #   abstrakcja TimeProvider
  rtc_ds1302.py        #   adapter DS1302 (GPIO CLK=6 DAT=4 RST=3)
  rtc_provider.py      #   RTCManager + SoftTimeProvider fallback
  audio_manager.py     #   głośnik i mikrofon
  battery.py, buttons.py, power.py, radio.py
  buzzer.py            #   buzzer na G13 (NPN)
  led.py               #   wbudowana dioda RGB (G21)
hal/                   # adaptery HAL dla portu T-Watch (ports-and-adapters)
device/                # pliki wgrywane przez Thonny: main.py, fonts/
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
- **SD card**: montowana przez `hardware.SDCard` (UIFlow2 driver); zarządzana przez `hw/sd_card.py`
- **RTC**: DS1302 odczytywany raz przy bocie; czas można też ustawić przez NTP (Wi-Fi wyłączane po synchronizacji); fallback: `SoftTimeProvider`
- **Keyboard**: TCA8418 (I2C matrix driver); GPIO 3/4/5/6 wolne od klawiatury

## Konwencje kodowania

- Bez button-hint footerów na listach plików — hinty tylko w podglądzie pliku
- Komentarze w kodzie po angielsku; UI po polsku
- Konfiguracja wyłącznie w `nuts.py`; kod aplikacji nie hardkoduje stałych
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

## Port T-Watch 2020 v3

HAL w `hal/` według wzorca ports-and-adapters:
- `hal/ports.py` — abstrakcyjne interfejsy (DisplayPort, TouchPort, RTCPort, PowerPort, NotifyPort, ButtonPort)
- `hal/<devicename>/` — adaptery dla konkretnego urządzenia
- `hal/registry.py` — auto-detekcja hardware przez skan I2C

Zbudowane adaptery: `AXP202Power`, `ST7789Display`, `FT6336Touch`, `PCF8563RTC`, `VibroNotify`, `SideButton`.
Główny interfejs użytkownika: web server REST + inline HTML (brak klawiatury fizycznej).

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