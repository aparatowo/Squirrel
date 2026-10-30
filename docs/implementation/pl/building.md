# Budowanie firmware

*[English](../en/building.md) · Polski · [Français](../fr/building.md) · [Deutsch](../de/building.md)*

`Squirrel!/build_firmware.py` buduje obraz firmware z całą aplikacją **zamrożoną** w środku: kod to bajtkod we flashu,
nie pliki na urządzeniu i nie kompilacja do RAM-u przy starcie. Potrzebuje tylko biblioteki standardowej Pythona.
Krótka wersja dla użytkowników jest w [guides/pl/getting-started.md](../../guides/pl/getting-started.md); tu jest cała
historia. Urządzenia i ich `port.toml`: [ports.md](ports.md).

Każde polecenie uruchamiaj w `Squirrel!/`.

## 1. Raz na komputer

```bash
python3 build_firmware.py --install-idf          # ESP-IDF 5.4.2 (~1 GB) into ~/esp-idf-v5.4.2 (or: --install-idf DIR)
python3 build_firmware.py --check                # what is in place, what is missing - changes nothing
```

- **Tylko ESP-IDF 5.4.x.** Firmware Cardputera jest łatany pod 5.4.2; z 5.5 jego mikrofon nagrywa ciszę, starsze go
  nie zbudują. Skrypt sam znajduje 5.4.x, nawet gdy `IDF_PATH` w powłoce wskazuje gdzie indziej.
- **Cardputer, raz:** `sudo apt install quilt`, potem `python3 build_firmware.py --setup` (submoduły, łatki, littlefs,
  mpy-cross repozytorium UIFlow; znacznik `.build/setup.done`, `--force` powtarza).
- **Zegarki** nie potrzebują niczego więcej: pierwszy build klonuje MicroPython v1.25.0 do `vendor/micropython` i sam
  nakłada łatki portu.

Repozytorium firmware Cardputera (`cardputer-adv-micropython`) jest klonowane do `vendor/` przy pierwszym uruchomieniu.
Inne miejsce: `--repo`, zmienna `SQUIRREL_FW_REPO` albo `build_config.json`:

```json
{"repo": "/path/to/cardputer-adv-micropython", "idf": "/path/to/esp-idf-v5.4.2", "port": "twatch2020_v3", "exclude": []}
```

## 2. Na co dzień

```bash
python3 build_firmware.py --stage-only                    # seconds: collect the sources, check imports, compile them
python3 build_firmware.py                                 # full image -> dist/squirrel-<board>-<git>-<time>.bin (+ .txt)
python3 build_firmware.py --flash /dev/ttyACM0            # build and flash
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0     # another device
```

Plik `.txt` obok obrazu wylicza, co jest w środku. Build startuje w czystym środowisku (bez zmiennych `IDF_*` z Twojej
powłoki) i zaczyna od nowa, gdy poprzedni użył innego ESP-IDF.

**Co robi build:** czyta `ports/<port>/port.toml` i `features.toml`, zapisuje `port_config.py` dla tego urządzenia,
pomija moduły funkcji, których urządzenie nie ma, sterowniki, których jego `port.toml` nie wymienia, i foldery innych
portów, zatrzymuje się, jeśli jakiś moduł importuje coś spoza tego buildu, kompiluje wszystko własnym `mpy-cross`
firmware i zamraża to we własnej definicji płytki (pliki repozytorium firmware nie są zmieniane: płytka pochodna,
wpisana do `.git/info/exclude`; `--clean` ją usuwa). `lang/<kod>.py` (tłumaczenia, budowane z `translations/*.tsv`
przez `tools/i18n/build.py`) jest zamrażany jak każdy moduł, a czcionka Cardputera trafia do partycji systemowej obrazu.

## 3. Wgrywanie

```bash
python3 build_firmware.py --flash-image <file from dist/> --flash /dev/ttyACM0    # an image built earlier
python3 build_firmware.py --setup-device /dev/ttyACM0                            # only prepare a device
python3 build_firmware.py --flash /dev/ttyACM0 --no-device-setup                 # flash, do not prepare
```

- Zamknij Thonny (albo cokolwiek, co trzyma port). `ls /dev/serial/by-id/` nazywa urządzenia: `...Espressif...` /
  `...M5Stack...` to Cardputer, `...1a86...` T-Watch (CH9102).
- **Cardputer:** jego konsola USB to TinyUSB, część aplikacji, a reset zrywa połączenie - wgrywanie działającego
  Cardputera często się nie udaje. Przytrzymaj **G0** przy podłączaniu kabla: czeka wtedy w trybie pobierania (czarny
  ekran, port nazywa się wtedy `...Espressif_USB_JTAG...`). Po wgraniu sam startuje i wraca pod nazwą aplikacji;
  komunikat "did not come back" znaczy wtedy tylko, że nazwa się zmieniła.
- Obraz Cardputera to cały flash od 0x0 (ustawienia NVS UIFlow są zastępowane; Twoje dane są na karcie SD); obrazy
  zegarków nie ruszają partycji danych (`/Squirrel` zostaje).

**Przygotowanie urządzenia** (po `--flash PORT` robi się samo, każdy krok tylko gdy trzeba, i tylko na urządzeniu,
którego `sys.implementation._machine` zawiera `[port] machine` portu):

1. `/flash/main.py` (albo `/main.py`) = `device/main.py`, który uruchamia Squirrel!; starszy zostaje jako `main.py.old`;
2. Cardputer: `/flash/boot.py` UIFlow dostaje nazwę `boot.py.uiflow`, gdy importuje `startup`, którego to firmware nie
   ma (przywrócenie nazwy przywraca menu UIFlow);
3. Cardputer: opcja startu UIFlow `boot_option = 0` (od razu uruchom `main.py`).

## 4. Sprawdzenie urządzenia

```python
import sq_info; sq_info.report()       # in Thonny
```

Pokazuje build, liczbę zamrożonych modułów, pliki, które **przesłaniają** zamrożone moduły, czy `main.py` uruchamia
aplikację, czcionkę i skąd przyszedł `nuts`. Log startowy (`/flash/boot_log.txt` na Cardputerze, `/boot_log.txt` na
zegarku) ma linię `[MAIN] frozen build <id> (N modules)`.

Nie zostawiaj modułów `.py` / `.mpy` we flashu urządzenia (poza `main.py`): przesłoniłyby zamrożone o tej samej nazwie.

## 5. Tryb DEV: zmiany kodu bez nowego firmware

Utwórz pusty plik `/flash/DEV` (zegarek: `/DEV`) i wgraj zmienione pliki `.py` do `/flash/apps/Squirrel/` (podfoldery
jak w źródłach). Teraz wygrywają z zamrożonymi; usuń `DEV`, żeby wrócić. Folder (`screens/`, `hw/`, `drivers/`,
`ports/`) na urządzeniu zasłania **cały** zamrożony pakiet o tej nazwie, więc kopiuj go w całości. `.mpy` wygrywa z
`.py` o tej samej nazwie.

Szybka pomoc, gdy urządzeniu brakuje pamięci przy kompilacji plików `.py`: `--build-mpy-cross`, potem `--mpy` zapisuje
pliki `.mpy` do `dist/mpy/` (bez ESP-IDF).

## 6. Inne opcje

| Opcja | Co robi |
|---|---|
| `--target build` | tylko aplikacja (`micropython.bin`) - nie pełny obraz |
| `--target pack_all` | obraz z **pustym** systemem plików użytkownika: kasuje `/flash` |
| `--gen-port-config` | zapisuje `port_config.py` obok źródeł (dla trybu DEV i symulatora); domyślny port, chyba że `--port` |
| `--exclude FILE` | pomiń plik w obrazie (powtarzalne; skrypty PC jak `vlw.py` są pomijane same) |
| `--prefer newer\|flat\|screens` | ten sam ekran w dwóch miejscach o różnej treści: który wygrywa |
| `--update-repo` | `git pull` w repozytorium firmware |
| `--reset-deps` | usuwa `dependencies.lock` i `managed_components` (rozwiązywane od nowa przy następnym buildzie) |
| `--diagnose` | wyjaśnia ostatni nieudany build z `.build/make.log` |
| `--allow-any-idf` | buduj z innym ESP-IDF (nie dla `--setup`; niezalecane) |
| `--allow-missing` | buduj, nawet jeśli manifest płytki bazowej wymienia brakujący plik |

`port_config.py` obok źródeł należy do domyślnego portu (Cardputera); po `--gen-port-config --port X` przywróć go przed
commitem. Build zawsze zapisuje własny.

## 7. Łatki do firmware

Firmware jest zmieniany tylko łatkami trzymanymi w repozytorium, nakładanymi na tymczasową kopię jako stos:

| Łatka | Co robi |
|---|---|
| `firmware_patches/0001-nimble-central-passkey.patch` | NimBLE: zdarzenia passkey po stronie centrali (szyfrowanie łącza, na razie wyłączone) |
| `firmware_patches/0002-panic-record.patch` | raport paniki albo watchdoga zadań trzymany w pamięci RTC przez reset (odczytuje go `tools/hwtest/panic_record.py`): konsola TinyUSB Cardputera nic nie pokazuje przy awarii |
| `ports/<port>/firmware/patches/*.patch` | dla każdego zegarka: czego potrzebuje jego build MicroPythona |

## 8. Gdy coś nie działa

| Komunikat | Co zrobić |
|---|---|
| `No ESP-IDF 5.4.x found` | `--install-idf` |
| `quilt is not installed` | `sudo apt install quilt` |
| `mpy-cross is not built` | `--setup` (repozytorium Cardputera nie jest jeszcze przygotowane) |
| `Two different copies of the same screen module` | usuń nieaktualny plik albo `--prefer newer` |
| `... does not compile with the firmware's mpy-cross` | ten plik używa składni, której MicroPython nie ma |
| `imports ..., which is not in the sources (of this port)` | moduł potrzebuje funkcji albo sterownika, który ten port pomija: zaimportuj go wewnątrz funkcji, która go potrzebuje, albo dodaj go do portu |
| `CFG_TUD_CDC_EP_BUFSIZE undeclared` | niedopasowane komponenty TinyUSB: przypnij `espressif/tinyusb` do `0.15.0~10` w `m5stack/main/idf_component.yml`, potem `--reset-deps` |
| `Cannot stat .../firmware_info.py` | skrypt generuje go dla płytki bazowej przed buildem; gdy to się nie uda, mówi, co sprawdzić (`--allow-missing` pomija kontrolę) |
| wgrywanie się nie udaje | zamknij Thonny; Cardputer: przytrzymaj G0 przy podłączaniu; Linux: `sudo usermod -aG dialout $USER` i zaloguj się ponownie |
| po wgraniu brak aplikacji | od 2.1 firmware sam zapisuje `/flash/main.py` przy pierwszym starcie (pełny obraz z M5Burner, wymazany układ); poza tym `--setup-device PORT`; sprawdź `/flash/main.py` |
| cokolwiek innego | całe wyjście jest w `.build/make.log`; `--diagnose` rozpoznaje znane przypadki |
