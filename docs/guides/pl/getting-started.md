# Pierwsze kroki

*[English](../en/getting-started.md) · Polski · [Français](../fr/getting-started.md) · [Deutsch](../de/getting-started.md)*

Od nowego urządzenia do Squirrel! na nim. Wersja 2.0.

## Urządzenia

| Urządzenie | Co to jest | Czego potrzebujesz |
|---|---|---|
| **M5Stack Cardputer ADV** | kieszonkowy komputer z klawiaturą (ESP32-S3) - główne urządzenie Squirrel!, *szef* synchronizacji Bluetooth | karty microSD (FAT32) na Twoje dane |
| **LilyGo T-Watch 2020 V3** | zegarek z ekranem dotykowym (ESP32) - czyta i odhacza to, co dostał od Cardputera, rutyny i timery na nadgarstku | niczego więcej |
| **Ogólny smartwatch z ESP32-S3** | *eksperymentalnie*: tanie zegarki sprzedawane jako "ESP32-S3 smartwatch" - jeszcze niesprawdzone na urządzeniu | najpierw sprawdzenia jego pinów ([porty](../../implementation/pl/ports.md)) |

Co działa na którym: Cardputer ma wszystko; zegarek nie ma klawiatury (nie pisze notatek ani zadań - czyta je i
odhacza) ani na razie dźwięku i mikrofonu, za to wibruje, śpi głęboko i ma sprzętowy zegar.

## Na komputerze

- **Linux** (macOS i Windows powinny działać, ale poniższe instrukcje są dla Linuksa), **Python 3.10+**, **git**.
- **Kabel USB-C** (zegarek: micro-USB), który przenosi dane, a nie tylko ładuje.

```bash
git clone https://github.com/aparatowo/Squirrel.git
cd "Squirrel/Squirrel!"
python3 build_firmware.py --install-idf     # ESP-IDF 5.4.2 (~1 GB), once
python3 build_firmware.py --check           # is everything in place? (changes nothing)
```

Cardputer potrzebuje jeszcze jednego kroku, raz: `python3 build_firmware.py --setup` (wymaga
`sudo apt install quilt`).

## Budowanie i wgrywanie

Zamknij Thonny (albo cokolwiek innego, co trzyma port USB), potem:

```bash
# Cardputer ADV (the default device)
python3 build_firmware.py --flash /dev/ttyACM0

# T-Watch 2020 V3
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0
```

Pierwsze budowanie kompiluje całe ESP-IDF i trwa kilka minut; następne są szybsze. Skrypt buduje obraz (w `dist/`),
wgrywa go i przygotowuje urządzenie, więc Squirrel! startuje sam.

**Który port?** `ls /dev/serial/by-id/` je nazywa: Cardputer to `...Espressif...` albo `...M5Stack...`, zegarek
`...1a86...`.

**Cardputer nie daje się wgrać?** Jego konsola USB jest częścią aplikacji, a reset zrywa połączenie USB. Przytrzymaj
**G0** przy podłączaniu kabla: Cardputer czeka wtedy w trybie pobierania (czarny ekran) i wgrywanie działa. Potem sam
uruchamia nowe firmware.

**Zegarek po raz pierwszy:** przychodzi z innym oprogramowaniem. Najpierw zachowaj jego kopię:
`tools/hwtest/twatch_phase0.sh /dev/ttyACM0` (16 MB, kilka minut).

## Pierwsze uruchomienie

- **Cardputer:** włóż kartę microSD (FAT32); Squirrel! sam założy na niej folder `/Squirrel`.
- **Czas:** Cardputer ustawia zegar przez Wi-Fi przy starcie - dodaj sieć w *Ustawienia → Połączenia → Sieci WiFi*
  (hotspot telefonu też się nada; 2,4 GHz). Albo ustaw go ręcznie (*Ustawienia → Czas i data → Ustaw czas*), albo
  weź go z zegarka przez Bluetooth.
- **Język:** *Ustawienia → Personalizacja → Ekran → Język* - English, Polski, Français, Deutsch.
- **Zegarek i Cardputer razem:** sparuj je raz ([synchronizacja Bluetooth](bluetooth.md)).

Potem: [funkcje](features.md) - co tu jest, [skróty](shortcuts.md) - klawisze.

## Twoje dane

Wszystko to zwykłe pliki: notatki i zadania jako `.txt`, notatki głosowe jako `.wav`, statystyki, rutyny i
`config.txt` (Twoje ustawienia, z komentarzem przy każdym). Na Cardputerze są na karcie SD w `/Squirrel`; na zegarku
w `/Squirrel` w jego pamięci flash. Wgranie nowej wersji je zostawia.

Nic nie opuszcza Twojego urządzenia - poza synchronizacją Bluetooth z Twoimi własnymi sparowanymi urządzeniami i Wi-Fi
tylko do ustawienia czasu.

## Aktualizacja

```bash
cd Squirrel
git pull
cd "Squirrel!"
python3 build_firmware.py --flash /dev/ttyACM0          # (--port twatch2020_v3 for the watch)
```

Konkretna wersja: `git checkout 2.0` (wydania to tagi gita), potem budowanie jak wyżej.

## Gdy coś nie działa

| Problem | Co zrobić |
|---|---|
| `port not found`, port zajęty | Zamknij Thonny; sprawdź `ls /dev/serial/by-id/`; na Linuksie może być potrzebne `sudo usermod -aG dialout $USER` (i ponowne zalogowanie). |
| Cardputer nie daje się wgrać | Przytrzymaj G0 przy podłączaniu kabla (wyżej). |
| Czarny ekran po wgraniu | Odłącz i podłącz kabel; sprawdź, czy kabel przenosi dane. |
| Aplikacja nie startuje | `python3 build_firmware.py --setup-device PORT` przygotowuje urządzenie od nowa; w Thonny: `import sq_info; sq_info.report()`. |
| Notatki się nie zapisują (Cardputer) | Czy karta microSD jest włożona i sformatowana jako FAT32? |
| Od czasu do czasu sam się restartuje | Watchdog restartuje zawieszone urządzenie po minucie; dane zostają. Jeśli zdarza się często, zgłoś to. |

Więcej dla tych, którzy budują i zmieniają Squirrel!: [dokumenty implementacyjne](../../implementation/pl/).
