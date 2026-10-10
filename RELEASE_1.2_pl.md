# 🐿️ Squirrel! 1.2

*[English version](RELEASE_1.2_en.md)*

Wersja 1.2 przenosi Squirrel na drugie urządzenie: zegarek **LilyGo T-Watch 2020 V3** z ekranem dotykowym. Żeby było
to możliwe, kod aplikacji został oddzielony od sprzętu, a każde urządzenie stało się **portem** opisanym jednym plikiem
konfiguracyjnym. Cardputer ADV jest teraz pierwszym z portów i działa tak samo jak w wersji 1.1. Zegarek potrafi
zasnąć naprawdę i budzić się sam na rutyny i kukułkę. Do tego doszło kilka poprawek, które dotyczą także Cardputera.

---

## Nowości

### ⌚ Port na LilyGo T-Watch 2020 V3

Squirrel działa na zegarku zbudowanym na czystym MicroPythonie 1.25.0, bez UIFlow. Wszystko poniżej sprawdzono na
urządzeniu.

**Działa:**
- **Tarcza:** duże cyfry na cały ekran, data, dzień tygodnia i linia stanu (bateria, skupienie).
- **Sterowanie dotykiem:**

  | Gest | Działanie |
  |---|---|
  | stuknięcie | otwiera / wybiera (ENTER) |
  | przesunięcie w górę / w dół | poprzednia / następna pozycja |
  | przesunięcie w prawo | wstecz (ESC) |
  | przesunięcie w lewo | dalej (RIGHT) |
  | przytrzymanie | akcja dodatkowa, np. odhaczenie To-Do albo przywrócenie wartości domyślnej |
  | boczny przycisk | wstecz; na tarczy tylko budzi ekran |
  | stuknięcie w nagłówek „<” | wstecz |

- **Menu dotykowe:** wiersze o wysokości ~6 mm, łatwe do trafienia palcem.
- **Ustawianie czasu dotykiem:** przyciski + i − nad i pod każdym polem; przytrzymanie zmienia wartość coraz szybciej.
- **Personalizacja dotykiem:**
  - on/off przełączane stuknięciem;
  - kolory i opcje wybierane z listy, kolory z próbką;
  - liczby, godziny i dni tygodnia zmieniane przyciskami.
- **To-Do:** przeglądanie listy, podgląd zadania, odhaczanie przytrzymaniem.
- **Narzędzia skupienia:** Pomodoro, Trening, metronom, oddychanie, rutyny, kukułka i statystyki.
- **Wibracja zamiast brzęczyka:** silnik wibracyjny działa jak brzęczyk z wersji 1.1, ze wszystkimi trybami. Domyślnie
  jest wyłączony; włączysz go w *Settings → Personalize → Buzzer*.
- **Zegar sprzętowy PCF8563:** podtrzymywany baterią, więc godzina nie ginie po restarcie.
- **Bateria:** poziom, napięcie i stan ładowania odczytywane z układu zasilania AXP202.
- **Deep sleep z alarmami zegara** — patrz niżej.
- **Dane:** zapisywane w wewnętrznej pamięci zegarka (`/Squirrel`, ok. 14 MB); aktualizacja firmware ich nie usuwa.

**Jeszcze nie działa:**
- **Dźwięk:** głośnik działa w testach sprzętu, ale aplikacja jeszcze z niego nie korzysta. Sygnały to na razie
  wibracja.
- **Nagrania głosowe:** mikrofon PDM wymaga sterownika, którego MicroPython nie ma.
- **Pisanie:** bez klawiatury nie da się tworzyć notatek, To-Do ani Mind Dump, a menu notatek jest ukryte. Zadania
  można dodać jako pliki `.txt` w `/Squirrel/todo`, np. przez Thonny.
- **Synchronizacja czasu przez Wi-Fi:** wyłączona, bo czas podtrzymuje zegar sprzętowy. Ustawiasz go ręcznie w
  *Settings → Time and date → Set Time*.
- **Akcelerometr:** wyłączany przy starcie; krokomierz i gesty nadgarstka są w planach.
- **Część ekranów** (tryb cichy, Pomodoro, Trening, metronom, oddychanie, statystyki, podgląd To-Do) ma jeszcze układ
  Cardputera 240×135, wyśrodkowany na ekranie zegarka. Kolejne będą przerabiane na pełną wysokość i dotyk.

**Instalacja:** [PORTY_PL.md](PORTY_PL.md), część 2. W skrócie:

```bash
cd Squirrel!
python3 build_firmware.py --install-idf                          # raz
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0
```

Przed pierwszym wgraniem warto zrobić kopię fabrycznego oprogramowania: `tools/hwtest/twatch_phase0.sh /dev/ttyACM0`.

### 😴 Deep sleep z alarmami zegara

Na urządzeniu, którego zegar sprzętowy ma alarm (dziś T-Watch), Squirrel może zasnąć naprawdę: ekran, dotyk i
wzmacniacz są wyłączone, a procesor pobiera kilka mikroamperów.

- **Włączenie:** *Settings → Personalize → Power → Sleep mode* = `deep`.
- **Kiedy zasypia:** po *Deep sleep after* minutach przy przygaszonym ekranie, domyślnie 10 minut, do ustawienia od 1
  do 120.
- **Co budzi:**
  - boczny przycisk;
  - alarm zegara ustawiony na najbliższe zdarzenie: rutynę, kukułkę (także kwadranse) albo odłożoną rutynę.
- **Lista alarmów:** po każdym zdarzeniu do zegara trafia następne. Kolejne alarmy pokazuje ekran *Settings → Time and
  date → Upcoming alarms*.
- **Po wybudzeniu alarmem** zdarzenie odbywa się jak zwykle, a zegarek zasypia ponownie po 30 sekundach przygaszenia
  zamiast po pełnym czasie.
- **Co jest zachowane:** odliczanie skupienia dolicza przespany czas, a odłożone rutyny czekają dalej.
- **Kiedy nie zasypia:** gdy działa albo jest wstrzymane Pomodoro, Trening lub metronom, gdy na ekranie jest
  powiadomienie, a także w trakcie dźwięku, sygnału albo synchronizacji czasu.
- **Szybkość:** godzina pojawia się ok. 1,7 s po wybudzeniu, cała aplikacja jest gotowa po ok. 4,4 s (wcześniej ok. 7 s).
- **Pozostałe tryby:** `light` usypia procesor przy przygaszonym ekranie i budzi go przyciskiem albo dotykiem; `off`
  wyłącza usypianie.

Cardputer ADV ma dziś tylko tryby `off` i `light`, bo moduł DS1302 nie ma alarmu. Mechanizm jest gotowy na zegar z
alarmem, gdyby taki pojawił się w Cardputerze.

### 🧩 Porty: jeden kod, wiele urządzeń

- **Opis urządzenia:** każde urządzenie ma folder `Squirrel!/ports/<nazwa>/` z plikiem `port.toml`, który zawiera piny,
  adresy, sterowniki i wybór funkcji, oraz z modułem `board.py`.
- **Funkcje zależne od sprzętu:** opisuje je `features.toml`. Funkcja, której urządzenie nie obsłuży, nie trafia do
  firmware, a jej menu, ekrany i ustawienia są ukryte. Przykłady: notatki bez klawiatury, nagrania bez mikrofonu, dioda
  bez diody.
- **Sterowniki:** nazwane od układów (`st7789_fb`, `ft6336`, `pcf8563`, `axp202` ...), więc mogą służyć kolejnym
  urządzeniom z tymi samymi układami.
- **Dotyk w warstwach:** układ dotyku → gesty → widżety. Rozmiary liczone są w milimetrach, więc ten sam interfejs
  zadziała na innym zegarku z innym ekranem.
- **Instrukcja dla nowego urządzenia:** [PORTY_PL.md](PORTY_PL.md).

---

## Poprawki (dotyczą też Cardputera)

- **Dzień tygodnia po ręcznym ustawieniu czasu:** *Set Time* zapisywał zawsze poniedziałek. Teraz zapisuje właściwy
  dzień.
- **Zegar cofany przy zapisie:** *Set Time* zerował sekundy także wtedy, gdy godzina i minuta nie były zmieniane, więc
  zegar cofał się nawet o 59 sekund. Teraz zachowuje bieżący czas, jeśli zmieniona była tylko data albo nic.
- **„Restart to apply”:** po zmianie *Use font* pojawia się informacja, że czcionka zmieni się po ponownym
  uruchomieniu.
- **Szybkie nagranie na świeżej karcie:** G0 na nowo sformatowanej karcie kończył się błędem „rec error”, dopóki
  nie nagrano czegoś z menu. Teraz folder nagrań tworzy się sam.

---

## Pozostałe zmiany

- **Ustawienie usypiania:** *Light sleep* (on/off) zastąpiło *Sleep mode* z wartościami `off`, `light` i (tam, gdzie
  jest dostępny) `deep`. Dawne ustawienie jest przenoszone automatycznie.
- **Plik `config.txt`** nie jest wczytywany ponownie, jeśli nie zmienił się od ostatniego odczytu.
- **Instrukcje instalacji:** krok 5 opisuje automatyczne przygotowanie urządzenia zamiast ręcznego wgrywania plików.

---

## Aktualizacja z poprzedniej wersji

- **Cardputer:** build i wgranie jak dotąd, `python3 build_firmware.py --flash PORT`. Po wgraniu skrypt sam przygotowuje
  urządzenie (`main.py`, `boot.py` UIFlow, opcja startu).
- **Ustawienia:** `config.txt` zostaje. `POWER_LIGHT_SLEEP = true` zamienia się w `POWER_SLEEP = light`, a `false` w
  `off`.
- **Pliki w `/flash/apps/Squirrel`:** jeśli według starej instrukcji wgrywałeś tam pliki `.py`, możesz je usunąć.
  Firmware korzysta z kodu wbudowanego, a pliki z tego folderu są używane tylko w trybie DEV.
- **Notatki, zadania, nagrania i statystyki** pozostają bez zmian.

---

## Dla osób budujących firmware

- **`--port NAZWA`** wybiera urządzenie; domyślnie `cardputer_adv`, można go też ustawić w `build_config.json`
  (`{"port": "..."}`).
- **Drugi przepis firmware, `micropython-esp32`:**
  - czysty MicroPython v1.25.0, klonowany automatycznie do `vendor/micropython`;
  - definicja płytki trzymana w porcie (`ports/<port>/firmware/`, budowana przez `BOARD_DIR`);
  - łatki portu nakładane przez `git apply`;
  - obraz wgrywany od 0x1000.
- **Szybszy start zegarka:**
  - procesor 240 MHz;
  - bez testu PSRAM przy każdym starcie;
  - cichy bootloader;
  - kod zamrożony na początku `sys.path`.

  Po zmianie konfiguracji płytki skrypt sam generuje `sdkconfig` od nowa.
- **`--gen-port-config`** zapisuje `port_config.py` z `port.toml`. Kopia obok źródeł należy do Cardputera.
- **`--setup-device PORT`** przygotowuje urządzenie bez wgrywania; po `--flash` dzieje się to automatycznie
  (`--no-device-setup` to wyłącza).
- **Klient REPL:**
  - tryb raw-paste z kontrolą przepływu (wolny UART zegarka);
  - opcja opuszczenia DTR/RTS dla mostków z auto-resetem (`[port] reset_lines_low`).
- **Kontrola importów i kompilacji:** obejmuje wszystkie pakiety; kod viper kompilowany z `-march=xtensawin`.
- **`tools/sim/`:** symulator, czyli aplikacja pod MicroPython unix z atrapami sprzętu. `compare.sh` porównuje dwie
  wersje (ślad rysowania, log, pliki). Każda zmiana w tym wydaniu dała na Cardputerze identyczny ślad jak wersja 1.1.
- **`tools/hwtest/`:** testy sprzętu uruchamiane przez REPL, z instrukcjami na ekranie urządzenia: T-Watch (ekran,
  dotyk, przycisk, wibracja, głośnik, zegar, bateria) i akcelerometry obu urządzeń. Wyniki:
  `tools/hwtest/README_PL.md`.
- **Usunięte:** stary `main.py` z głównego folderu (omijał `squirrel_boot`); launcher to `device/main.py`.

---

## Znane ograniczenia

- **T-Watch:** patrz „Jeszcze nie działa” wyżej.
- **Menu *Time and date* na zegarku** pokazuje pozycję „Sync RTC (DS1302)”, choć zegarek ma układ PCF8563. Pozycja
  odczytuje czas z PCF8563, mylący jest tylko napis.
- **Menu *Silent mode*** pokazuje kanały Buzzer i LED także na urządzeniach, które ich nie mają.
- **Usypianie i konsola USB:** w trybach `light` i `deep` uśpione urządzenie nie odpowiada na REPL (Cardputer dodatkowo
  znika z USB). Do pracy z Thonny ustaw *Sleep mode* = `off`.
- **Ograniczenia Cardputera z wersji 1.1** (dioda a podświetlenie, nieznany stan ładowania, wgrywanie przy działającej
  aplikacji) obowiązują nadal.
