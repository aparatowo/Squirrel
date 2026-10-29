# Propozycja: Squirrel! z modułów włączanych przez użytkownika

*[English](../en/modules-proposal.md)*

Propozycja i jej analiza, **niezbudowana**. Napisana 2026-10-19 do decyzji; link w [backlogu](backlog.md).

## 1. Pomysł

- Squirrel! startuje jako **prosta wersja**: zegar i narzędzia skupienia, nic więcej.
- Cała reszta to **moduły**, które użytkownik włącza w *Ustawienia → Funkcjonalności* (notatki, zadania, notatki głosowe,
  rutyny, Bluetooth, czas z Wi-Fi ...).
- Moduły wyłączone są w menu **wygaszone** (widać je, ale nie działają: „włącz w Ustawienia → Funkcjonalności”).
- Moduł włączony startuje **po restarcie** i ładuje się do pamięci tak jak dziś.

Dwa cele naraz: mniej pamięci na to, czego się nie używa, i spokojniejsze urządzenie dla osoby, którą dwadzieścia pozycji
menu przytłacza pierwszego dnia.

## 2. Co jest dziś

| Warstwa | Kiedy | O czym decyduje |
|---|---|---|
| `features.toml` + `port.toml` | **budowanie** | na co pozwala sprzęt: funkcji bez jej sprzętu w ogóle nie ma w firmware, jej menu, ekrany i ustawienia są ukryte (`port_config.HIDDEN_*`) |
| `_LAZY_SCREENS` | pierwsze użycie | każdy ekran poza zegarem i menu jest kompilowany i tworzony dopiero przy otwarciu, a potem oddawany (`POWER_UNLOAD_SCREENS`) |
| leniwe usługi | pierwsze użycie | Pomodoro / Trening, metronom, klepsydra; od tej gałęzi także ostrzeżenia o baterii i sterownik modułu zegara |
| ustawienia | od razu | wiele części nic nie robi, gdy ich ustawienie jest wyłączone (kukułka, auto-synchronizacja, dziennik baterii) - ale są załadowane |

Przy starcie Cardputer ADV importuje **44 moduły** i tworzy kilkanaście obiektów dla funkcji, z których użytkownik może
nigdy nie skorzystać: `StorageManager`, `TodoEditor`, `NoteEditor`, dwa `DayCounter`, `RoutineStore` + `Scheduler`,
`TimeSyncService` (Wi-Fi), `AutoSync` (Bluetooth), `BatteryLogger`, drzewo menu ze wszystkimi pozycjami.

## 3. Jak to zbudować

### 3.1 Rejestr modułów

Jeden nowy plik, `modules.py`, opisuje każdy moduł jako dane (tak jak `features.toml` opisuje sprzęt):

```python
MODULES = (
    # nazwa       potrzebuje (cech firmware)  zależy od    moduły pythona, które wnosi  menu / ekrany / ustawienia
    ("todo",      (),                         (),          ("todo_editor",),            ...),
    ("notes",     ("notes",),                 (),          ("note_editor",),            ...),
    ("voice",     ("voice_notes",),           (),          (),                          ...),
    ("routines",  (),                         (),          ("scheduler",),              ...),
    ("bluetooth", ("ble_sync",),              (),          ("ble.auto",),               ...),
    ("wifi_time", ("wifi_ntp",),              (),          ("time_sync", "wifi_ntp"),   ...),
    ...
)
BASE = ("clock", "focus")            # zawsze włączone: zegar, narzędzia skupienia, Ustawienia
```

Ustawienie `MODULES` w `config.txt` (lista nazw, jak dni godzin ciszy) mówi, które są włączone. `features` dostaje drugie
pytanie obok `has(name)` (zbudowane?): `enabled(name)` - zbudowane **i** włączone.

### 3.2 Start

`SquirrelApp.__init__` tworzy każdą część tylko `if enabled(...)` - ten sam wzór co dziś `if has("wifi_ntp")`, poziom
wyżej. Moduł wyłączony nigdy nie jest importowany: jego obiekty, bufory i usługi nie istnieją.

### 3.3 Menu: wygaszone, nie ukryte

`menu_tree.py` dostaje przy pozycji jeszcze jeden opcjonalny element: moduł, którego ona potrzebuje. `MenuScreen` rysuje
taką pozycję na szaro, a po ENTER pokazuje „Włącz w Ustawienia → Funkcjonalności” zamiast ją otwierać. Brakujący sprzęt
zostaje ukryty jak dziś (nie ma czego włączyć). Lista dotykowa (zegarek) robi to samo.

### 3.4 Ustawienia → Funkcjonalności

Ekran z jednym wierszem na każdy moduł, który ma firmware: wł. / wył., linijka o tym, co robi, i przybliżony koszt
pamięci. Wyjście po zmianie pyta „Uruchomić ponownie?”. Wyłączenie modułu **zostawia** jego pliki i ustawienia: ponowne
włączenie przywraca wszystko.

### 3.5 Profile (później)

Gotowe zestawy - *Tylko skupienie*, *Skupienie + zadania*, *Wszystko* - proponowane przy pierwszym starcie, żeby nikt nie
musiał rozumieć listy modułów, zanim zacznie używać urządzenia.

## 4. Analiza

### 4.1 Ile pamięci to oszczędza - uczciwie

Sam kod jest **zamrożony w firmware**: leży we flashu i nie kosztuje sterty, czy jest używany, czy nie. Moduł wyłączony
oszczędza tylko to, co jego import i jego obiekty budują w RAM: zmienne modułu, słowniki i listy, instancje, bufory,
otwarte pliki, usługę w pętli głównej. Na moduł to mniej więcej **1-10 KB** (do zmierzenia: zob. 4.4). Najwięksi
konsumenci i tak już ładują się na żądanie: radia (NimBLE i Wi-Fi: dziesiątki KB, tylko w czasie synchronizacji),
bufory dźwięku (tylko przy nagrywaniu / odtwarzaniu), ekrany (leniwe).

Czyli: na Cardputerze ADV (~160 KB sterty) start „Tylko skupienie” mógłby zyskać **15-30 KB** - przydatne przeciw
fragmentacji i dla ekranów ładowanych później, ale to nie inna klasa urządzenia. Większy zysk to drugi cel: **mniej
rzeczy na ekranie** dla kogoś, kto nie powinien musieć ich ignorować.

### 4.2 Co się komplikuje

| Punkt | Dlaczego | Co trzeba zdecydować |
|---|---|---|
| Synchronizacja Bluetooth | szef wysyła zadania, notatki, rutyny; węzeł z wyłączonym modułem - trzymać pliki (to tylko pliki) czy odmawiać? | **synchronizacja niezależna od modułów**: dane płyną, wyłącza się interfejs |
| Rutyny wyłączone | brak przypomnień, brak „Zaplanowanych alarmów” na zegarku, głęboki sen ma mniej alarmów | jasna linijka na ekranie Funkcjonalności |
| Zależności | statystyki liczą zrobione rutyny i zadania; menu TAB i skróty (CTRL+T, CTRL+N) wskazują na moduły | każdy skrót sprawdza `enabled()`; statystyki pokazują zero dla wyłączonego modułu |
| Ustawienia wyłączonego modułu | pokazywać czy ukryć? | ukryte w Personalizacji, zachowane w `config.txt` |
| Testy | każda kombinacja modułów | `compare.sh` z 2-3 profilami; test, że każda pozycja menu ma swój moduł albo żaden |
| Restart | MicroPython nie umie naprawdę wyładować modułu: wyłączanie w biegu zostawiałoby fragmenty | restart, jak w pomyśle - uczciwe i proste |
| Dwie warstwy „funkcji” | sprzęt (budowanie) i wybór użytkownika (w biegu) łatwo pomylić | rozdzielić nazwy: `has()` = zbudowane, `enabled()` = włączone |

### 4.3 Nakład (z grubsza)

| Etap | Praca | Rozmiar |
|---|---|---|
| 0. Pomiar | wolna sterta po starcie dla każdej części, na urządzeniu (linie `[MEM]`, `sq_info.report()`) | mały |
| 1. Tylko interfejs | `modules.py`, ustawienie `MODULES`, Ustawienia → Funkcjonalności, wygaszone pozycje, pytanie o restart; nadal wszystko ładowane | średni |
| 2. Prawdziwe ładowanie | `SquirrelApp` tworzy części tylko włączone; sprawdzone skróty, menu TAB, statystyki, synchronizacja | średni-duży |
| 3. Profile | wybór przy pierwszym starcie, gotowe zestawy | mały |

Sam etap 1 daje już spokojniejsze urządzenie; etap 2 daje pamięć; etap 0 mówi, czy etap 2 jest tego wart.

### 4.4 Jak mierzyć (etap 0)

Na urządzeniu, w trybie DEV: wykomentować tworzenie jednej części naraz w `SquirrelApp.__init__`, restart, odczytać
`[MEM] free heap after start-up` z dziennika startu; po trzy próby (sterta się waha). Różnica to koszt tej części. Tabela
tych liczb trafia na ekran Funkcjonalności („ok. 6 KB”).

## 5. Rekomendacja

1. Najpierw **etap 0**: dziesięć pomiarów na Cardputerze ADV rozstrzyga, czy część pamięciowa jest warta pracy.
2. **Etap 1** w każdym razie: wygaszone moduły i *Ustawienia → Funkcjonalności* służą ludziom, dla których jest Squirrel!,
   cokolwiek powie pamięć.
3. **Synchronizacja Bluetooth i dane na dysku niezależne od modułów**: wyłączenie modułu go ukrywa; nigdy nie usuwa, nie
   odrzuca i nie zmienia danych.
4. Domyślnie na nowym urządzeniu: *Skupienie + zadania* (lista zadań to to, po co większość przychodzi), *Wszystko*
   jednym dotknięciem.

Pytania otwarte do autora: co dokładnie jest w prostej wersji (lista zadań?); wygaszone czy ukryte na małym ekranie
zegarka; czy wyłączony moduł nadal wysyła swoje dane w synchronizacji (rekomendacja: tak).
