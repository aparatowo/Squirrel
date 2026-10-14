# Pamięć, szybkość i energia

*[English](../en/performance.md) · Polski · [Français](../fr/performance.md) · [Deutsch](../de/performance.md)*

Squirrel! musi zmieścić się na najsłabszym ze swoich urządzeń: ESP32-S3 **bez PSRAM** (Cardputer ADV, wiele tanich
zegarków) daje MicroPythonowi około **160 KB** sterty na wszystko. Ile to kosztuje dziś i jak to jest trzymane w ryzach.

## 1. Zmierzone (2.0)

| Co | Wartość |
|---|---|
| Sterta aplikacji na Cardputerze (bez PSRAM), na zegarze | 54 KB ze 160 KB |
| z tego ustawienia (95 sztuk) | 7,4 KB |
| Język inny niż angielski | poniżej 1 KB RAM (tablice zostają we flashu) |
| Wyszukanie tekstu na zegarku (ESP32 przy 80 MHz) | 91 µs (763 µs bez pamięci podręcznej); rysowanie ekranu ok. 2 % wolniej niż po angielsku |
| Ekran zegarka, cały bufor ramki / pasy | menu 132 / 141 ms, zegar 292 / 366 ms |
| Bufor ramki dla 240 × 240 / 240 × 280, pasami | 115 / 134 KB, 19 KB |
| Automatyczna synchronizacja Bluetooth, na zegarku | ok. 1 mAh (jego bateria: ok. 380 mAh) |

## 2. Jak to jest trzymane w ryzach

- **Zamrożony kod.** Wszystkie moduły są kodem bajtowym we flashu (`build_firmware.py`): nic nie jest kompilowane na
  urządzeniu, a kod nie zajmuje sterty. Stałe tablice (tłumaczenia, glify, czcionka) też zostają we flashu.
- **Ustawienia jako wiersze.** `appconfig` trzyma jedno odwołanie do każdego wiersza `SETTINGS` z
  `appconfig_schema.py` zamiast kopii na każde ustawienie, a wartości domyślne bierze prosto z `nuts`.
- **Tłumaczenia** to jedna posortowana krotka na język, przeszukiwana przez połowienie; pamięć podręczna ostatnich 200
  tekstów, a własne teksty użytkownika (`lang_<kod>.tsv`) są jedynymi w RAM-ie. Zobacz [i18n.md](i18n.md).
- **Ekran pasami** bez PSRAM (`drivers/st7789_fb.py`): wywołania rysujące klatkę są zapamiętywane i odtwarzane do
  bufora 40 wierszy, pas po pasie. Wybór sam: cała klatka tylko wtedy, gdy zajmuje najwyżej ćwierć wolnej sterty;
  `[display] buffer_rows` wymusza pasy. Zobacz [ports.md](ports.md).
- **Zwalnianie ekranów** (`POWER_UNLOAD_SCREENS`): obiekty rzadko używanego ekranu znikają, gdy go opuszczasz.
- **Leniwe importy** tego, czego potrzebuje tylko jeden ekran albo jedna funkcja; funkcji, której urządzenie nie ma, w
  ogóle nie ma w jego firmware (`features.toml`).
- **Bluetooth:** tylko na czas sesji; jeden rekord w pamięci naraz (wysyłany i odbierany w częściach); automatyczne
  odśmiecanie jest wyłączone w trakcie sesji, a `tick()` odśmieca z pętli głównej - odśmiecanie uruchomione przez
  alokację w IRQ radia działało na jego małym stosie.

## 3. Energia

- Radia działają tylko wtedy, gdy pracują: Wi-Fi do czasu przy starcie, Bluetooth na sesję synchronizacji (ESP32 nie
  zaśnie lekko z włączonym kontrolerem BT).
- Ekran przygasa po chwili bez wejścia; `POWER_SAVE` zwalnia procesor, gdy jest przygaszony.
- `POWER_SLEEP`: `light` (eksperymentalnie) usypia przy przygaszonym ekranie i budzi się na klawisz, przycisk albo
  dotyk; `deep` (zegarek) śpi głęboko i budzi się alarmem swojego zegara na następną rutynę, kukułkę albo porę
  synchronizacji (`alarms.py` trzyma kolejkę, `deep_sleep.py` zapisuje i odtwarza stan). Po przebudzeniu tarcza
  zegara jest rysowana, zanim wystartuje reszta aplikacji (`EARLY_CLOCK`).
- Pory automatycznej synchronizacji są według zegara, więc urządzenia spotykają się bez wcześniejszej rozmowy: zegarek
  nasłuchuje 90 s na porę, szef łączy się 20 s po jej początku.

## 4. Siatki bezpieczeństwa

- **Watchdog** (`WATCHDOG_S`, 60 s): jeśli pętla główna nie wróci, urządzenie się restartuje; dane zostają.
- **Zapis awarii** (`firmware_patches/0002-panic-record.patch`): przyczyna i ślad awarii albo to, co robił rdzeń 0,
  gdy zadziałał watchdog zadań, przeżywają reset w pamięci RTC; `tools/hwtest/panic_record.py` je odczytuje.
- `LOW_HEAP` w `hw/power.py`: odśmiecanie, zanim sterty zabraknie.

## 5. Jak to sprawdzić ponownie

```python
import gc, micropython; gc.collect(); micropython.mem_info()      # in the REPL of a running app (DEV mode)
```

`tools/hwtest/ble_e2e.py --mem` wypisuje pamięć Cardputera co pół sekundy w trakcie synchronizacji;
`tools/hwtest/twatch_gfx_bench.py` mierzy rysowanie zegarka.
