# Wspólny format danych

*[English](../en/data-format.md) · Polski · [Français](../fr/data-format.md) · [Deutsch](../de/data-format.md)*

Rekordy całej rodziny Squirrel!: Cardputer, T-Watch i każda przyszła aplikacja (na przykład na telefon). Wersja
formatu: **1**. Implementacja wzorcowa: `Squirrel!/ble/protocol.py` (i jej bliźniak w JavaScripcie
`Squirrel!/tools/web/squirrel_protocol.js`, sprawdzany bajt w bajt przez `tools/tests/test_web_protocol.py`). Jak
korzysta z nich synchronizacja: [bluetooth.md](bluetooth.md).

## 1. Zasada

- **Model kanoniczny = JSON.** Każdy rekord ma jedną definicję: nazwy pól, typy, zakresy (§3). Tak wygląda
  w plikach JSON na ESP32, w aplikacji na telefon i w testach.
- **Przez BLE idzie kodowanie binarne** tego samego modelu (§4) — pole w pole, bez utraty informacji.
  Małe urządzenie nie musi parsować JSON-a: trzyma struktury C odpowiadające kodowaniu binarnemu.
- Każde urządzenie może przechowywać dane po swojemu (pliki tekstowe, `done.dat`, struktury C). Specyfikacja
  mówi tylko, co jest na zewnątrz — mapowanie na własny zapis jest w §5.
- Pola nieznane są pomijane, nie odrzucane (nowsza wersja na jednym urządzeniu nie psuje starszej na drugim).
  Nowe pola dochodzą tylko jako opcjonalne. Zmiana znaczenia pola = nowa wersja formatu.

## 2. Wspólne pola i reguły

| Pole | Typ | Znaczenie |
|---|---|---|
| `id` | int 1–65535 | Identyfikator rekordu. Bity 15–13: **slot** twórcy — 0 = rekord **szefa**, 1–6 = rekord **lokalny** noda w tym slocie, 7 = zarezerwowany. Bity 12–0: licznik twórcy. Sloty nadaje szef przy parowaniu. |
| `e` | int | Czas ostatniej **edycji treści** — wersja treści (porównywana przy propozycjach, §3.8). |
| `c` | int | Czas ostatniej **zmiany stanu** (aktywna / zrobione / kupione). Edycja treści go nie zmienia. |
| `del` | bool | Zarezerwowane (nagrobek: rekord usunięty). W modelu z szefem nieużywane — szef usuwa przez spis. |

- **Czas** = sekundy od 1970-01-01 00:00 w **czasie lokalnym** urządzenia (nie UTC; strefa jest w `TIME`).
  0 = „nigdy”.
- **Tekst** = UTF-8. Limity są w znakach (jak na ekranach), a w kodowaniu binarnym — w bajtach (§4).
- **Szef i nody.** W komplecie urządzeń jeden jest **szefem** (domyślnie Cardputer): jedynym autorem treści
  rekordów ze slotem 0. Pozostałe to **nody**. Łączenie kopii (`ble/merge.py`), osobno dla każdego `id`:
  - treść rekordów szefa — zawsze od szefa; rekord szefa, którego nie ma w spisie szefa, node usuwa;
  - stan — z kopii o większym `c` (odklikanie na zegarku trafia do szefa i dalej);
  - rekordy lokalne noda (slot ≠ 0) — szef ich nie zmienia, nie usuwa i nie przejmuje (adopcja: §3.8).
  Zegary decydują więc tylko o stanie; o treści decyduje szef, a konflikty edycji wykrywa wersja `e` (§3.8).
- **Dzień tygodnia** liczy się z daty, nigdy z `localtime()[6]` (firmware ESP32 różnią się konwencją).

## 3. Rekordy (JSON)

### 3.1 Rutyna — `routine`

```json
{"id": 8193, "t": "Leki", "h": 8, "m": 0, "d": 63, "on": true, "to": 255, "e": 1760259600, "c": 1760259600}
```

| Pole | Typ | Zakres | Znaczenie |
|---|---|---|---|
| `t` | str | ≤ 50 znaków | tekst powiadomienia |
| `h`, `m` | int | 0–23, 0–59 | godzina |
| `d` | int | 0–127 | dni tygodnia, bit 0 = poniedziałek … bit 6 = niedziela |
| `on` | bool | | aktywna (stan: zmiana ustawia `c`) |
| `to` | int | 0–255 | urządzenia, na których się pojawia: bit n = slot n; 255 = wszystkie |

### 3.2 TODO — `todo` (także checklista)

```json
{"id": 2, "t": "Zakupy\n> mleko\n> chleb", "done": false, "e": 1760259600, "c": 0,
 "items": [{"t": "mleko", "done": true, "c": 1760260000}]}
```

| Pole | Typ | Zakres | Znaczenie |
|---|---|---|---|
| `t` | str | ≤ 500 znaków | cała treść; pierwsza linia = tytuł |
| `done` | bool | | zrobione (stan) |
| `items` | lista | ≤ 64 | tylko checklista: stan jej pozycji (linii `>`) |
| `items[].t` | str | ≤ 100 znaków | tekst pozycji — klucz, pod którym pozycja jest rozpoznawana |
| `items[].done`, `items[].c` | bool, int | | stan pozycji i czas jego zmiany (łączone per pozycja, jak rekordy) |

**Checklista** (lista zakupów, kroki zadania…): linie treści po tytule, które zaczynają się od `>`, to pozycje
odklikiwane osobno (tekst pozycji = linia bez `>` i spacji wokół). Pozostałe linie to zwykły opis. TODO bez linii `>`
odklikuje się w całości. Gdy wszystkie pozycje są odklikane, `done` = true.

### 3.3 Notatka — `note`

```json
{"id": 3, "t": "Uwagi\npierwsza linia to tytuł", "e": 1760259600}
```

| Pole | Typ | Zakres | Znaczenie |
|---|---|---|---|
| `t` | str | ≤ 2000 znaków | cała treść; pierwsza linia = tytuł |

Notatka nie ma stanu (`c`).

### 3.4 Statystyka dnia — `stat`

```json
{"day": "2026-10-12", "k": "focus_min", "n": 95}
```

| Pole | Typ | Znaczenie |
|---|---|---|
| `day` | str `YYYY-MM-DD` | dzień |
| `k` | str | `routines` (rutyny zrobione), `todos` (TODO zrobione), `focus_min` (minuty skupienia), `steps` (kroki) |
| `n` | int 0–65535 | wartość tego dnia na tym urządzeniu |

Statystyk się nie łączy: każde urządzenie jest jedynym źródłem swoich, hub trzyma je osobno per slot.

### 3.5 Ustawienia — `settings`

Obiekt `{KLUCZ: wartość}` z nazwami kluczy ze schematu ustawień (`appconfig_schema.py`). Tylko klucze z listy
synchronizowanych (`ble/protocol.py: SYNCED_KEYS`):

| Klucze | Typ |
|---|---|
| `CUCKOO_ENABLED`, `CUCKOO_QUARTERS` | bool |
| `CUCKOO_QUARTER_VOLUME` | int 0–100 |
| `POMODORO_WORK_MIN` (1–90), `POMODORO_BREAK_MIN` (1–30), `POMODORO_LONG_BREAK_MIN` (1–60), `POMODORO_CYCLES` (1–8) | int |
| `ROUTINE_SNOOZE_MIN` | int 1–60 |
| `QUIET_SOUND_FROM`, `QUIET_SOUND_TO` | str `HH:MM` |
| `QUIET_SOUND_DAYS` | str 7 znaków, `MTWTFSS`, `.` = dzień nie zaznaczony |
| `TRAINING_PLAN` | lista `[[kolor, sekundy], ...]`, ≤ 16 bloków, kolory: `blue yellow orange red green` |

Ustawienia są całością urządzenia, bez `id`; synchronizacja: późniejszy zapis wygrywa.

### 3.6 Zdarzenie rutyny — `event` (log rutyn)

```json
{"r": 8193, "at": 1760259600, "res": "done"}
```

| Pole | Typ | Znaczenie |
|---|---|---|
| `r` | int | `id` rutyny |
| `at` | int | czas, na który rutyna była ustawiona (czas lokalny) |
| `res` | str | `done` (zrobiona), `skip` (pominięta), `missed` (bez reakcji, także po drzemkach) |

Node trzyma zdarzenia 60 dni i raportuje je szefowi; szef pobiera tylko te po ostatniej synchronizacji.
Zdarzeń się nie łączy: każde ma jedno źródło (node), szef trzyma je osobno per slot.

### 3.7 Czas — `time`, opis urządzenia — `info`, stan — `status`

```json
{"time": 1760270400, "offset": 120, "source": "rtc", "age": 10, "has_rtc": true, "rtc_valid": true}
{"version": 1, "kind": "twatch", "caps": ["rtc", "routines", "todo", "stats", "steps"], "name": "T-Watch", "app": "2.0", "slot": 1}
```

`source`: `soft`, `manual`, `rtc`, `ntp`, `peer`. `kind`: `cardputer`, `twatch`, `web` (kod 3 jest zarezerwowany).
`caps`: `rtc todo routines stats pomodoro breathing cuckoo steps hub notes`.
`status` (tryb, timer) — do ustalenia przy fazie 1, tylko do odczytu.

### 3.8 Propozycja — `proposal` (zarezerwowane, kolejny etap)

Zmiana treści zrobiona na nodzie (edytor połączony bezpośrednio z nodem, albo node z własnym edytorem):
działa na nodzie od razu i czeka na decyzję szefa.

```json
{"op": "edit", "set": "routine", "id": 1, "base": 1760259600, "rec": {...rekord z §3.1...}}
```

| Pole | Znaczenie |
|---|---|
| `op` | `edit` (rekord szefa), `new` (nowy rekord — dotąd lokalny), `delete` |
| `base` | `e` rekordu szefa, na którym zmianę zrobiono. Szef przyjmuje ją bez pytania, jeśli jego `e` jest wciąż takie samo; inaczej to konflikt (auto: wygrywa szef; tryb „pytaj”: decyduje użytkownik) |

Kodowanie binarne zostanie ustalone razem z implementacją (zestaw `0x0B` jest zarezerwowany).

## 4. Kodowanie binarne (BLE)

Little-endian. `str8` = u8 długość w bajtach + UTF-8; `str16` = u16 + UTF-8. Tekst jest przycinany tylko na
granicy znaku. Czas = u32. Flagi wspólne: bit 7 = `del` (nagrobek: po flagach tylko `e`, reszta zerami / pusta).

```
routine   u16 id | u8 flagi (b0 on, b7 del) | u8 h | u8 m | u8 d | u8 to | u32 e | u32 c | str8 t
todo      u16 id | u8 flagi (b0 done, b7 del) | u32 e | u32 c | str16 t
          | u8 liczba pozycji | pozycja: u8 flagi (b0 done) | u32 c | str8 t
note      u16 id | u8 flagi (b7 del) | u32 e | str16 t
stat      u16 dzień (dni od 1970-01-01) | u8 k (0 routines, 1 todos, 2 focus_min, 3 steps) | u16 n
event     u16 r | u32 at | u8 res (0 done, 1 skip, 2 missed)
spis      u16 id | u8 flagi (b7 del) | u32 e | u32 c           — jeden wpis na rekord, bez treści
time      u32 time | i16 offset | u8 source (0 soft, 1 manual, 2 rtc, 3 ntp, 4 peer) | u32 age
          | u8 flagi (b0 has_rtc, b1 rtc_valid)
info      u8 version | u8 kind (1 cardputer, 2 twatch, 3 reserved, 4 web) | u16 caps (bity w kolejności z §3.7)
          | u8 slot | str8 name | str8 app
settings  tekst UTF-8, linie KLUCZ=wartość (jak config.txt); TRAINING_PLAN = "blue:120,yellow:180,..."
```

### Kanał `CONTROL` — przesyłanie rekordów

```
polecenie (zapis):   u8 cmd | u8 zestaw | u16 id | u16 część | u8 flagi (b0 ostatnia) | dane
odpowiedź (notyf.):  u8 kod | u8 zestaw | u16 id | u16 część | u8 flagi (b0 ostatnia) | dane

cmd   0x01 LIST  — spis zestawu: nagłówek (u8 format, u32 rewizja, u16 liczba) + wpisy „spis”
      0x02 GET   — jeden rekord (id)
      0x03 PUT   — jeden rekord (id) w częściach; zatwierdzany po ostatniej części, w całości albo wcale
      0x04 DELETE — usunięcie rekordu szefa (id) z noda; tylko od szefa, rekordów lokalnych noda nie usuwa
      0x05 AUTH_HELLO     — parowanie: dane 16 B nonce szefa → DATA 16 B nonce noda; node pokazuje 6 cyfr
      0x06 AUTH_CONFIRM   — parowanie: dane 16 B dowodu (niżej) → ACK albo ERR 7; node zapisuje klucz
      0x07 AUTH_CHALLENGE — każda sesja: → DATA 16 B wyzwania (jednorazowe)
      0x08 AUTH_PROVE     — każda sesja: dane 16 B odpowiedzi → ACK albo ERR 6
      (polecenia AUTH_* mają zestaw 0x01 i id = 0)
kod   0x10 DATA (odpowiedź na LIST / GET, w częściach), 0x11 ACK, 0x12 ERR (dane: u8 kod błędu)
błędy 1 nieznany zestaw, 2 część poza kolejnością, 3 za duże, 4 uszkodzone dane, 5 brak rekordu,
      6 niesparowany (w tej sesji brak AUTH_PROVE), 7 zły kod przy parowaniu
zestaw 0x03 ustawienia (GET / PUT z id = 0; tekst jak w §4), 0x04 rutyny, 0x05 TODO, 0x06 statystyki,
       0x09 notatki, 0x0A zdarzenia, 0x0B propozycje (zarezerwowane)
```

Statystyki i zdarzenia nie mają `id`: odpowiedź na `LIST` zawiera od razu rekordy (`stat`: ostatnie 60 dni;
`event`: te po czasie podanym w danych polecenia `LIST`, u32 — szef pamięta, dokąd doczytał).
Zestaw rutyn można też pobrać jednym `GET` z `id` = 0 (wszystkie rekordy w jednej odpowiedzi) — są małe.

### Parowanie i dowód sesji (`ble/auth.py`)

HMAC = HMAC-SHA256 obcięty do 16 bajtów; teksty w ASCII, `+` to sklejenie bajtów.

```
klucz    K   = HMAC(kod jako 6 cyfr ASCII, "squirrel-pair" + nonce szefa + nonce noda)
CONFIRM      = HMAC(K, "confirm" + nonce noda)
PROVE        = HMAC(K, "session" + wyzwanie)
```

Kod nie idzie w powietrzu. Node trzyma jeden klucz (`"head"`), szef — klucz na każdy node (po adresie); oba
w `ble_auth.json` na wewnętrznym flashu. Dopóki w sesji nie przejdzie `AUTH_PROVE`, node odpowiada ERR 6 na każde
inne polecenie i ignoruje zapis `TIME`; `INFO` i `TIME` można czytać bez parowania. **Rekordy idą
nieszyfrowane** — zob. [bluetooth.md](bluetooth.md) §6.

## 5. Odwzorowanie na zapis urządzeń (ESP32)

| Rekord | Plik | Uwagi |
|---|---|---|
| routine | `routines.json` — lista obiektów JSON z §3.1 | starsze pliki bez `id`, `to`, `e`, `c`: przy odczycie dostają `id` (licznik szefa), `to` = 255, `e` = `c` = 0 |
| event | `focus/events.txt` — linie `r,at,res` | 60 dni; na szefie: `focus/peers/<slot>/events.txt` |
| todo | `todo/<nazwa>.txt` (treść), `todo/done.dat` (`nazwa,data` = zrobione; `nazwa#pozycja,data` = pozycja kupiona), `todo/meta.json` (`{nazwa: {id, e, c, items: {pozycja: c}}}`) | pliki bez wpisu w `meta.json` (sprzed 2.0, skopiowane przez USB): `e` = `c` = 0, `id` nadawane przy pierwszym spisie |
| note | `notes/<nazwa>.txt`, `notes/meta.json` (`{nazwa: {id, e}}`) | |
| stat | `focus/routines.txt`, `focus/todos.txt`, `focus/focus.txt` (sekundy → minuty), kroki | `focus/peers/<slot>/` — statystyki innych urządzeń na hubie |
| settings | `config.txt` | |

Nie są rekordami (jeszcze): dziennik sukcesu, `wins/RRRR-MM-DD.txt` (jeden dzień: data, potem linie `-` / `>` =
zrobione rzeczy) zostaje na urządzeniu. `focus/focus.txt` może mieć ujemne linie (`2026-10-19,-900`): odjęty czas
skupienia; linie dnia się sumują, nigdy poniżej zera.
