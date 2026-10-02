# Budowanie firmware z zamrożoną aplikacją Squirrel!

`build_firmware.py` leży w folderze z kodem aplikacji (tym z `nuts.py`, `squirrel_app.py` …) i buduje z niego plik `.bin`,
w którym cały kod jest **zamrożony** (bytecode we flashu, nie w RAM-ie i nie na dysku urządzenia).

## Gdzie to położyć
Struktura znana z UIFlow2 (u Ciebie: folder edycji → `main` → `apps` → `Squirrel`). Narzędzie traktuje **własny folder** jako folder z kodem,
więc ma leżeć w **`apps/Squirrel/`**, razem z `nuts.py`, `squirrel_app.py` i resztą modułów:

```
<folder edycji>/
├── main_flash.py / main      ← niepotrzebne, można usunąć (zastępuje je device/main.py)
└── apps/
    └── Squirrel/             ← TU: build_firmware.py, BUILD.md, squirrel_boot.py + wszystkie moduły .py
        ├── device/main.py    ← to wgrywasz Thonnym jako /flash/main.py (nie jest zamrażany)
        ├── fonts/squirrel.vlw
        ├── screens/…         ← może być też płasko; narzędzie samo ułoży pakiet
        ├── .build/  dist/    ← powstają przy pracy narzędzia (dodaj do .gitignore, jeśli folder jest w git)
```
W folderze wyżej narzędzie odmówi i powie, dokąd je przenieść.

## Szybka pomoc, gdy brakuje pamięci (bez ESP-IDF i bez quilt)
Kompilacja `.py` na urządzeniu zjada RAM i go fragmentuje; w czasie importu 43 modułów to ok. 250 KB źródeł. `.mpy` pomijają kompilację
na urządzeniu i zwykle usuwają błędy „brak pamięci przy inicjalizacji”. Potrzebny jest tylko kompilator C:
```
python3 build_firmware.py --build-mpy-cross     # make w micropython/mpy-cross z repozytorium firmware
python3 build_firmware.py --mpy                 # dist/mpy/ = to samo drzewo, ale .mpy
```
Wgraj zawartość `dist/mpy/` do `/flash/apps/Squirrel/` (z podfolderem `screens/`) i usuń stare `.py` oraz stare `.mpy`
(`.mpy` ma pierwszeństwo przed `.py` o tej samej nazwie). `device/main.py` jako `/flash/main.py` działa bez zmian.
Ten `mpy-cross` powstaje **bez łatek** z `--setup`. Format jest ten sam, ale gdyby urządzenie zgłosiło `incompatible .mpy file`, trzeba pełnego `--setup`.
To rozwiązanie przejściowe: kod nadal ląduje w RAM-ie, tylko bez narzutu kompilacji. Zamrożenie (pełny build) zdejmuje go z RAM-u zupełnie.

## Wgrywanie gotowego pliku
`esptool.py` jest tylko w środowisku ESP-IDF, nie w zwykłej powłoce, a plik leży w `dist/`. Narzędzie robi to samo bez ręcznego ładowania środowiska:
```
python3 build_firmware.py --flash-image squirrel-M5STACK_CardputerADV_Custom_Squirrel-<git>-<czas>.bin
python3 build_firmware.py --flash-image <plik> --flash /dev/ttyACM0     # gdy trzeba wskazać port
```
Przed wgraniem: zamknij Thonny, urządzenie musi być w trybie pobierania (przytrzymaj G0 przy podłączaniu USB). Obraz zapisuje cały flash od 0x0:
ustawienia UIFlow w NVS (np. zapamiętane Wi-Fi) są zastępowane, a pliki wgrane na `/flash` mogą zniknąć, więc po wgraniu wgraj od nowa `/flash/main.py` (`device/main.py`)
i `/flash/fonts/squirrel.vlw`. Ustawienia, notatki i reszta aplikacji są na karcie SD i zostają.

## Co zostało przetestowane, a co nie
- **Przetestowane (154 sprawdzenia):** zbieranie źródeł, układ pakietu `screens/` (także z płaskiego folderu), kontrola importów,
  generowanie płytki pochodnej i manifestu, pełny przebieg `--check`, `--setup`, `--stage-only`, `--mpy`, `--clean`, `--flash`,
  budowanie, wybór pełnego obrazu `.bin`. Test używa **sztucznego repozytorium** z prawdziwym `make`, `bash` i `export.sh`.
- **Niesprawdzone, bo nie widziałem Twojego repozytorium:** czy `m5stack/Makefile` przyjmie nową płytkę (kopię
  `M5STACK_CardputerADV_Custom`), gdzie dokładnie ląduje `.bin`, czy `make patch` jest u Ciebie już wykonany.
  Narzędzie sprawdza to samo (`--check`) i mówi wprost, co zastało. Jeśli pierwszy build się nie uda, wklej mi cały wypis.

## Jednorazowo (po kolei, każde polecenie osobno)
Najpierw `python3 build_firmware.py --check`: pokazuje, czego brakuje, i nic nie zmienia. Zwykle do zrobienia są cztery rzeczy:

1. **`sudo apt install quilt`** – `make patch` go potrzebuje.
2. **ESP-IDF 5.4.x.** To firmware jest budowany i łatany pod **5.4.2** (starsze, np. 5.0.4, i nowsze, np. 5.5, nie nadają się; `make patch`
   zmienia pliki samego ESP-IDF). Jeśli `--check` nie widzi 5.4.x: `python3 build_firmware.py --install-idf`
   (klonuje v5.4.2 do `~/esp-idf-v5.4.2`, ok. 1–2 GB, potem znajdzie go sam, nawet gdy `IDF_PATH` w powłoce wskazuje starszy).
3. **`python3 build_firmware.py --setup`** – `make submodules`, `patch`, `littlefs`, `mpy-cross`. Wykona się raz (znacznik `.build/setup.done`);
   odmówi, jeśli nie ma `quilt` albo ESP-IDF 5.4.x.
4. **Porządek w folderze z kodem.** `--check` zgłosi dwie rzeczy, które trzeba rozstrzygnąć samemu:
   - ten sam ekran w dwóch miejscach (np. `time_sync_screen.py` obok i w `screens/`) z **różną** treścią – jeden jest nieaktualny, a program nie zgaduje,
     który. Usuń nieaktualny albo użyj `--prefer newer|flat|screens`;
   - skrypty PC (`vlw.py`, `make_vlw.py`, `check_vlw.py` są pomijane same; inne importujące np. `PIL` zgłaszane jako błąd): `"exclude": ["plik.py"]` w
     `build_config.json` albo `--exclude plik.py`.

Domyślne repozytorium to `/home/pirx/src/cardputer-adv-micropython`; inne: `--repo`, `SQUIRREL_FW_REPO` albo `build_config.json`
(`{"repo": "...", "idf": "/home/pirx/esp-idf-v5.4.2", "exclude": [], "prefer": "newer"}`).

## Co buduje `make` (z `m5stack/Makefile` M5Stack) i co z tego wgrywać
- `make … build` robi tylko aplikację (`micropython.bin`) z bootloaderem i tablicą partycji: **nie jest to plik do wgrania**.
- `make … pack` robi to samo i **składa pełny obraz** `build-…/uiflow-<git>.bin` (bootloader + partycje + aplikacja + system plików systemowych, wgrywany od `0x0`).
  To domyślny cel narzędzia (`--target pack`). Nie zapisuje partycji użytkownika (`vfs`), więc pliki na `/flash` (twój `main.py`, font) powinny zostać;
  po wgraniu sprawdź i tak, czy `/flash/main.py` jest.
- `make … pack_all` dodaje **pusty** system plików użytkownika: kasuje `/flash` (trzeba wgrać `main.py` i font od nowa). Narzędzie ostrzega.
- Typ płytki (`BOARD_TYPE`) Makefile wylicza z **nazwy** płytki z listy `M5STACK_CardputerADV:cardputeradv`. Dla nazwy pochodnej wychodzi `none`, więc narzędzie
  czyta typ płytki bazowej z tej listy i przekazuje go jawnie (`BOARD_TYPE=…`).

## Codziennie
```
python3 build_firmware.py --stage-only          # szybko (sekundy): zbiera pliki i kompiluje je tym samym mpy-cross co firmware
python3 build_firmware.py                       # pełny build -> dist/squirrel-<płytka>-<git>-<czas>.bin (+ .txt z listą plików)
python3 build_firmware.py --flash /dev/ttyACM0  # to samo i od razu wgranie (tylko pełny obraz, od adresu 0x0)
```
Wgrywanie: zamknij Thonny (trzyma port); gdy port nie odpowiada, przytrzymaj G0 przy podłączaniu kabla.
Budowanie startuje w czystym środowisku (bez zmiennych `IDF_*` i bez wpisów `esp-idf`/`.espressif` w `PATH`), a katalog `m5stack/build-…_Squirrel` zostaje
usunięty, jeśli poprzedni build zrobiono innym ESP-IDF (stary cache CMake zatruwa nowy build).
Narzędzie niczego nie zmienia w istniejących plikach repozytorium: dodaje płytkę `M5STACK_CardputerADV_Custom_Squirrel`
(kopia bazowej + jedna linia `freeze(...)` w jej `manifest.py`) i wpisuje ją do `.git/info/exclude`. `--clean` ją usuwa.

## Co musi być na urządzeniu (wgrywane Thonnym, niezależnie od firmware)
| Plik na urządzeniu | Skąd | Po co |
|---|---|---|
| `/flash/main.py` | `device/main.py` | firmware czyta `main.py` z systemu plików (nie da się go zamrozić); ma 10 linii |
| `/flash/fonts/squirrel.vlw` | `fonts/squirrel.vlw` | **opcjonalny**, tylko dla polskich liter: font czyta firmware jako plik |
| `/sd/Squirrel/…` | tworzy aplikacja | ustawienia (`config.txt`), `wifi.json`, notatki, To-Do, nagrania, statystyki. Skopiuj swoje stare, jeśli chcesz je zachować |

**Nie wgrywaj ani nie zostawiaj:** `/flash/apps/Squirrel/*.py` i żadnych modułów `.py`/`.mpy` w `/flash/` (poza `main.py`).
Katalog bieżący jest na `sys.path` **przed** kodem zamrożonym, więc taki plik po cichu przesłania zamrożony moduł o tej samej nazwie
(to był problem z `bars.py`). `verify_device.py` i tools/, archive/, tests/ nie są potrzebne na urządzeniu.

## Sprawdzenie na urządzeniu
```python
import sq_info; sq_info.report()
```
Pokazuje: numer buildu, liczbę zamrożonych modułów, pliki, które **przesłaniają** zamrożone, czy `main.py` startuje aplikację, czy jest
font oraz skąd załadowano `nuts` (zamrożony: ścieżka bez `/` na początku). W logu startowym (`/flash/boot_log.txt`) jest wiersz
`[MAIN] frozen build <id> (N modules)`.

## Tryb DEV (zmiana kodu bez przebudowy firmware)
Utwórz pusty plik `/flash/DEV` (Thonny: nowy plik na urządzeniu) i wgraj poprawione `.py` do `/flash/apps/Squirrel/` (podfolder `screens/`
dla ekranów). Od tej chwili te pliki mają pierwszeństwo przed zamrożonymi. Usuń `/flash/DEV`, żeby wrócić do kodu z firmware.
Plik `.mpy` o tej samej nazwie co `.py` w tym samym folderze wygrywa z `.py` (też to, co było przyczyną błędu z `from_top`).

## Zmiany w aplikacji pod zamrożony kod
- `squirrel_boot.py` – jedyne miejsce, które zna ścieżki i sposób uruchomienia (`run()`); `main.py` tylko go importuje
  (najpierw z firmware, a gdy go tam nie ma, z `/flash/apps/Squirrel`, więc ten sam `main.py` działa też bez zamrożenia).
- Font szukany najpierw w `/flash/fonts/`; kalibrator zapisuje `/flash/keymap.json` (nie potrzeba katalogu `/flash/apps/Squirrel`).
- `POWER_UNLOAD_SCREENS`: kod zamrożony leży we flashu i `sys.modules.pop` go nie zwolni, a tylko obiekty ekranu – możesz tę opcję wyłączyć.

## Gdy coś nie działa
| Objaw | Co zrobić |
|---|---|
| `does not look like the firmware repository` | zły `--repo` |
| `No ESP-IDF 5.4.x found` | `--install-idf`; tylko 5.4.x (5.0.4 nie zbuduje tego firmware, 5.5: mikrofon zwraca ciszę); `--allow-any-idf` omija kontrolę przy budowaniu, nigdy przy `--setup` |
| `quilt is not installed` | `sudo apt install quilt` |
| `Two different copies of the same screen module` | usuń nieaktualny plik albo `--prefer newer` |
| `mpy-cross is not built` | `--setup` (setup repozytorium nie jest skończony) |
| `... does not compile with the firmware's mpy-cross` | wskazany plik używa składni nieobsługiwanej przez MicroPython |
| `CFG_TUD_CDC_EP_BUFSIZE undeclared` w `espressif__esp_tinyusb` | niedopasowane wersje zależności: bez `dependencies.lock` menedżer komponentów wziął najnowszy `tinyusb` (0.21) do starego `esp_tinyusb` (1.0.x), a Espressif paruje `esp_tinyusb ~1.0.x` ze starym `tinyusb` z gałęzi 0.15. W `m5stack/main/idf_component.yml` obok `espressif/esp_tinyusb` dopisz `espressif/tinyusb:` z `version: "0.15.0~10"` (wersje w rejestrze zapisuje się numer~rewizja: `0.15.0~1` … `0.15.0~10`; `~0.15.10` nie istnieje), potem `--reset-deps` i build |
| `Cannot stat …/firmware_info.py` przy zamrażaniu | manifest płytki `M5STACK_CardputerADV_Custom` wymienia `firmware_info.py` ścieżką do **płytki bazowej**. Plik tworzy `Makefile` forka celem pozornym `firmware-info` (`scripts/gen-firmware-info.sh`, z `git describe --tags`), ale **tylko gdy `BOARD` to dokładnie `M5STACK_CardputerADV_Custom`**; dla płytki pochodnej cel nic nie robi. Narzędzie (1) nie zmienia nazw płytek w plikach `.py`, (2) przed budowaniem szuka w `Makefile` celu, którego polecenie ZAPISUJE ten plik, i uruchamia go dla płytki bazowej (u Ciebie: `make BOARD=M5STACK_CardputerADV_Custom firmware-info`). Gdy się nie uda, **zatrzymuje się od razu** i podpowiada, co sprawdzić (`--allow-missing` pomija kontrolę) |
| `no versions of espressif/tinyusb match …` | taka wersja nie istnieje w rejestrze; użyj dokładnej z listy `https://components.espressif.com/components/espressif/tinyusb/versions` |
| inny błąd w trakcie buildu | całe wyjście jest w `.build/make.log`; `python3 build_firmware.py --diagnose` rozpoznaje znane przypadki (brak miejsca, `quilt`, port szeregowy, rozwiązywanie zależności) |
| `make` nie zna płytki / błąd w manifeście | wklej mi cały wypis; płytka bazowa mogła mieć inne pliki, niż zakładam |
| `no new .bin was found` | build przeszedł, ale plik leży gdzie indziej: poszukaj `build-*/` w `m5stack/` |
| po wgraniu brak aplikacji | sprawdź, czy `/flash/main.py` jest na urządzeniu (nowy obraz mógł odtworzyć system plików) |
