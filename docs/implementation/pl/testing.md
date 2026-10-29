# Testowanie

*[English](../en/testing.md) · Polski · [Français](../fr/testing.md) · [Deutsch](../de/testing.md)*

Trzy poziomy: testy na PC (bez urządzenia), cała aplikacja w symulatorze (bez urządzenia) i skrypty, które działają na
urządzeniach przez USB. Wszystko uruchamiaj z `Squirrel!/`.

## 1. Testy na PC

```bash
for t in tools/tests/test_*.py; do python3 "$t" || echo "FAILED: $t"; done
python3 -m unittest tools/tests/test_i18n.py         # (any of them also runs this way)
```

| Test | Co sprawdza |
|---|---|
| `test_ble_protocol.py`, `test_ble_merge.py` | kodeki rekordów Bluetooth, ramki i zasady "kto ma rację" |
| `test_ble_node.py`, `test_ble_head.py` | całą synchronizację szef ↔ node przez udawane radio (`tools/sim/fakes/bluetooth.py` łączy dwa radia "w powietrzu"), z parowaniem |
| `test_ble_auto.py` | automatyczną synchronizację: pory według zegara, node jako źródło alarmów, pomijanie zajętego radia |
| `test_web_protocol.py` | kodek JavaScript strony Web Bluetooth daje te same bajty co `ble/protocol.py` (potrzebny `node`) |
| `test_checklist.py`, `test_routines.py` | checklisty (linie `>`, odhaczenia trzymane osobno), rutyny i ich dni |
| `test_cardputer_hw.py`, `test_hourglass_bars.py`, `test_battery.py`, `test_focus_wins.py` | matryca klawiszy pierwszego Cardputera i DS3231 na atrapach; klepsydra i belki czasu na zegarze; `test_battery.py`: ładowanie zgadywane z napięcia, ostrzeżenia o baterii, słabe świecenie diody; `test_focus_wins.py`: odejmowanie czasu skupienia, dziennik sukcesu, podwójne / potrójne stuknięcie zegarka |
| `test_appconfig.py` | `config.txt`: czytanie, zapis, komentarze, wartości domyślne zmienione przez nowszą wersję |
| `test_i18n.py` | wyszukiwanie, powrót do angielskiego, szablony (`fill`), własny `lang_<kod>.tsv` użytkownika |
| `test_st7789_strips.py` | ekran rysowany pasami daje ten sam obraz co pełny bufor ramki (tylko MicroPython: `framebuf`, viper - pod CPythonem pomijany) |

Do tego `python3 tools/i18n/check.py` (każdy tekst przetłumaczony, te same symbole zastępcze, etykiety dość krótkie) i
`python3 build_firmware.py --stage-only --port <port>` dla każdego portu (importy, kompilacja).

## 2. Symulator

`tools/sim/` uruchamia całą aplikację na PC pod **portem unix MicroPythona** (tym samym MicroPythonem co firmware), z
atrapami `M5`, `machine`, `esp32`, `network`, `bluetooth` ..., zegarem, który idzie tylko wtedy, gdy kod śpi, i z
`/sd` i `/flash` urządzenia w folderze. Jednorazowe zbudowanie portu unix:
[tools/sim/README.md](../../../Squirrel!/tools/sim/README.md).

- **Porównanie dwóch wersji:** refaktoryzacja, która nie zmienia zachowania, daje identyczny ślad - każde wywołanie
  ekranu, każdą linię logu, każdy zapisany plik:

  ```bash
  mkdir -p /tmp/base && git archive HEAD "Squirrel!" | tar -x -C /tmp/base
  tools/sim/compare.sh <micropython> "/tmp/base/Squirrel!" "$PWD" /tmp/simwork      # IDENTICAL / DIFFERENT
  ```

- **Każdy ekran, w głąb** (po zmianie interfejsu albo tłumaczenia): `crawl_scenario.py` otwiera każdą pozycję menu,
  każdy ekran z kilkoma klawiszami, każde ustawienie Personalizacji, każdy element list i powiadomienia; z
  `SQUIRREL_SIM_TOUCH=1` ta sama aplikacja jak na ekranie dotykowym 240 x 240, każdy przycisk stuknięty (renderowanie z
  `--height 240`). `check_trace.py` wypisuje tekst poza ekranem i angielski pozostawiony w innym języku:

  ```bash
  SQUIRREL_SIM_SCENARIO=tools/sim/crawl_scenario.py <micropython> -X heapsize=16M tools/sim/run_sim.py "$PWD" /tmp/c /tmp/c.txt
  python3 tools/sim/check_trace.py /tmp/c.txt --lang de                        # OFF / ENGLISH / ERROR findings
  python3 tools/sim/render_shots.py /tmp/c.txt /tmp/c-shots                    # the pictures, named by place
  ```

- **Zrzuty ekranu Cardputera** do przewodników: scenariusz 34 stanów, z przykładową treścią w języku z `config.txt`
  folderu roboczego (`LANGUAGE=pl` ...), zamieniany na pliki PNG:

  ```bash
  mkdir -p /tmp/w/sd/Squirrel /tmp/w/flash/fonts && cp squirrel.vlw /tmp/w/flash/fonts/
  echo "LANGUAGE=pl" > /tmp/w/sd/Squirrel/config.txt
  SQUIRREL_SIM_SCENARIO=tools/sim/shots_scenario.py <micropython> -X heapsize=8M tools/sim/run_sim.py "$PWD" /tmp/w /tmp/trace.txt
  python3 tools/sim/render_shots.py /tmp/trace.txt ../shots/cardputer/pl
  ```

  Czcionka w `/flash/fonts/` ma znaczenie: bez niej aplikacja pokazuje litery bez ogonków. Zdjęcia są rysowane czcionką
  6 × 8 zegarków, nie `.vlw` Cardputera ([backlog](backlog.md) D).

## 3. Na urządzeniach

Najpierw zamknij Thonny (trzyma port). `ls /dev/serial/by-id/` nazywa porty.

| Narzędzie | Co robi |
|---|---|
| `tools/hwtest/run.py PORT SCRIPT [TEST ...]` | uruchamia skrypt testu sprzętu przez REPL i pokazuje wyniki na żywo: `RESULT\|test\|PASS / FAIL / INFO / ASK / SKIP\|details` (ASK: potwierdź, co widziałeś, słyszałeś albo czułeś); log w `.build/hwtest/`. `PORT` może być `auto`. Skrypt działa tylko na urządzeniu nazwanym w jego pierwszej linii (`# EXPECT_MACHINE: ...`) |
| `twatch_hw.py`, `twatch_accel.py`, `cardputer_accel.py`, `cardputer_hw.py` | skrypty: układy zegarka po kolei (PMU, ekran, dotyk, zegar, wibracja), akcelerometry; `cardputer_hw.py`: DS3231 na porcie Grove (oba Cardputery), klawisze i dioda pierwszego Cardputera |
| `twatch_gfx_bench.py` | szybkość rysowania sterownika ekranu zegarka |
| `tools/hwtest/twatch_phase0.sh PORT` | przed pierwszym wgraniem na zegarek: identyfikator układu i flasha, pełna kopia 16 MB flasha z jej MD5 (przywraca fabryczne oprogramowanie) |
| `tools/hwtest/twatch_screens.py PORT --lang pl` | zrzuty ekranów zegarka czytane z jego bufora ramki do `shots/twatch/<lang>/` (zapisuje przykładową checklistę i znów ją usuwa) |
| `tools/hwtest/ble_e2e.py WATCH CARDPUTER` | synchronizacja Bluetooth od początku do końca przez ekrany obu aplikacji; `--link` z szyfrowaniem łącza, `--mem` pamięć co pół sekundy, `--head-files` szef uruchamia pakiet `ble/` z PC (jako `.mpy`) zamiast zamrożonego |
| `tools/hwtest/panic_record.py PORT` | przyczyna i ślad ostatniej awarii albo zawieszenia Cardputera z pamięci RTC (jego konsola TinyUSB nic nie pokazuje przy awarii) |
| `tools/ble_pc_head.py` | PC jako szef, do testowania zegarka bez Cardputera (potrzebny `bleak`) |

Na działającym urządzeniu: `import sq_info; sq_info.report()` (build, przesłaniające pliki, czcionka) i log startowy
`/flash/boot_log.txt` (Cardputer) albo `/boot_log.txt` (zegarek).

## 4. Przed wydaniem

1. Testy na PC, `check.py`, `--stage-only` dla każdego portu.
2. `compare.sh` względem ostatniego wydania tam, gdzie zachowanie nie powinno się zmienić.
3. Zbudować i wgrać oba urządzenia; kilka razy `ble_e2e.py`; synchronizacja z ekranu każdego urządzenia.
4. Zrzuty w każdym języku (Cardputer z symulatora, zegarek z urządzenia), a potem **obejrzeć je jak użytkownik**: czy
   każdy tekst się mieści, czy jest przetłumaczony, czy brzmi jak reszta?
