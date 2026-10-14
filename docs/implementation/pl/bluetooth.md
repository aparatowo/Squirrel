# Synchronizacja Bluetooth - projekt

*[English](../en/bluetooth.md) · Polski · [Français](../fr/bluetooth.md) · [Deutsch](../de/bluetooth.md)*

Jak urządzenia Squirrel! synchronizują się przez Bluetooth Low Energy, tak jak zbudowano to w 2.0. Rekordy i ich
kodowanie: [data-format.md](data-format.md). Dla użytkowników: [guides/pl/bluetooth.md](../../guides/pl/bluetooth.md).
Otwarte sprawy: [backlog.md](backlog.md).

## 1. Wybory i dlaczego

| Wybór | Dlaczego |
|---|---|
| Surowy moduł `bluetooth` MicroPythona (handler IRQ + `tick()`), nie `aioble` | `aioble` nie ma w firmware, a aplikacja nie ma asyncio: działa w jednej pętli głównej usług wywoływanych po kolei. Handler IRQ, który tylko kolejkuje, i `tick()`, który wykonuje pracę, pasują do tej pętli i potrzebują mniej RAM-u. |
| Jeden protokół w `ble/` dla każdego urządzenia; rola z `features.toml` | Stos Bluetooth (NimBLE) jest ten sam na ESP32 i ESP32-S3; urządzenia różnią się tylko rolą (szef / node) i tym, jakie mają dane. |
| Kanoniczny model JSON + jedno kodowanie binarne w powietrzu | Każda implementacja - aplikacja na telefon, wersja w C na małym zegarku - ma te same rekordy; w powietrzu jeden zwarty kodek, który nie potrzebuje parsera JSON. |
| Jeden zestaw `SETTINGS` w tekstowej postaci `config.txt` | Aplikacja ma już schemat z walidacją (`appconfig_schema.py`); nowe ustawienie nie potrzebuje nowej charakterystyki. |
| Sesje synchronizacji, nie radio stale włączone | ESP32 nie zaśnie lekko z włączonym kontrolerem BT, a głęboki sen wyłącza radio: ciągłe rozgłaszanie zjadłoby baterię zegarka. Radio działa tylko na czas sesji, jak Wi-Fi do czasu. |
| Lepszy zegar ustawia gorszy | Cardputer często nie ma zegara sprzętowego; zegarek go ma. Czas idzie od czasu z Wi-Fi > zegar sprzętowy > ustawiony ręcznie > zegar programowy. |
| Parowanie z kodem w aplikacji, nie (jeszcze) szyfrowanie łącza | Zobacz sekcję 6. |

## 2. Role

Jedno urządzenie w zestawie jest **szefem** (`head` w kodzie: `BleHead`, `ble_head_screen.py`, `features.toml`
`ble_hub`; na ekranach: nody czekają na *wiewiórkę*, która szuka *orzechów*) - jedynym autorem treści (Cardputer: ma
klawiaturę). Pozostałe to **nody**. Node przyjmuje jedno połączenie naraz.

```
   Web Bluetooth page (phone / computer)
            │  connects to the boss (or to a node)
            ▼
   BOSS: Cardputer - central towards the nodes; peripheral towards the page ("Be visible")
    ├── T-Watch        - node (peripheral)
    └── (other watches later - nodes too)
```

| Dane | Szef | Node (zegarek) | Strona www |
|---|---|---|---|
| Treść zadań / checklist | pisze | czyta | pisze (przez szefa) |
| Odhaczenia zadań i punktów checklist | ✅ | ✅ | ✅ |
| Rutyny: tekst, czas, dni, urządzenia | pisze | czyta | pisze (przez szefa) |
| Rutyna wł. / wył. | ✅ | ✅ | ✅ |
| Statystyki, log rutyn | swoje / każdego noda / razem | swoje, zgłaszane | - |
| Synchronizowane ustawienia | ✅ | od szefa | ✅ |
| Czas | według jakości zegara | według jakości zegara | ustawia z telefonu |

## 3. Profil GATT

Jedna usługa dla całej rodziny; charakterystyki mają wspólną bazę i różnią się drugą grupą cyfr.
Baza: `beeaXXXX-f159-4fd4-b434-1d8d3db5b0bc`.

| `XXXX` | Nazwa | Właściwości | Zawartość |
|---|---|---|---|
| `0000` | usługa Squirrel! | - | rozgłaszana: po niej skaner rozpoznaje rodzinę |
| `0001` | `INFO` | R | wersja protokołu, rodzaj urządzenia, maska możliwości, slot, nazwa, wersja aplikacji |
| `0002` | `TIME` | R / W | czas lokalny, przesunięcie UTC, źródło i wiek zegara; odświeżane co sekundę; zapis ustawia zegar (tylko sparowany szef) |
| `0003` | `SETTINGS` | R | rewizja ustawień (same ustawienia przez `CONTROL`, zestaw `0x03`) |
| `0004` | `ROUTINES` | R | rewizja rutyn |
| `0005` | `TODO` | R | rewizja zadań |
| `0006` | `STATS` | R | rewizja statystyk |
| `0007` | `STATUS` | R / N | zarezerwowane: tryb, stan timera, bateria |
| `0008` | `CONTROL` | W / N | żądania i odpowiedzi: lista, pobierz, zapisz, usuń, parowanie ([data-format.md](data-format.md) §4) |
| `0009` | `NOTES` | R | rewizja notatek (tylko urządzenia z notatkami) |
| `000a` | `EVENTS` | R | rewizja logu rutyn |

Bity możliwości w `INFO`: 0 zegar sprzętowy, 1 zadania, 2 rutyny, 3 statystyki, 4 Pomodoro, 5 oddychanie, 6 kukułka,
7 kroki, 8 hub, 9 notatki. Szef synchronizuje tylko to, co node zgłasza.

## 4. Sesja

1. Node rozgłasza usługę przez pewne okno (2 minuty z jego ekranu Bluetooth, 90 s dla automatycznej synchronizacji).
2. Szef łączy się kolejno z każdym znanym nodem (pamięta je w `ble.json`: adres, slot, ostatnia synchronizacja).
3. Wymiana MTU, odkrywanie usług, `INFO` (wersja protokołu), powiadomienia na `CONTROL`.
4. **Parowanie / dowód** (sekcja 6).
5. **Zegar:** lepszy ustawia drugi (bez zapisu, jeśli zgadzają się co do 2 sekund).
6. **Dołączenie:** node, którego slot się różni, dostaje swój slot (`PUT` na zestawie `INFO`). Jego rekordy sprzed tego
   - na przykład skopiowane przez USB - przechodzą na ten slot i stają się jego rekordami lokalnymi.
7. **Ustawienia:** szef zapisuje synchronizowane klucze, które się różnią (`ble/protocol.SYNCED_KEYS`).
8. **Rekordy** - rutyny, zadania, notatki: najpierw lista każdego zestawu u noda (id, czas edycji `e`, czas stanu `c`),
   potem tylko rekordy, które się różnią, w obie strony (sekcja 5).
9. **Raporty:** statystyki noda (ostatnie 60 dni) i jego log rutyn od ostatniej synchronizacji; szef trzyma je dla
   każdego noda w `focus/peers/<slot>/`.
10. Rozłączenie. Node zostaje widoczny jeszcze 15 s, na drugą rundę.

**Druga runda:** po pierwszej szef ma wszystko, ale node zsynchronizowany jako pierwszy nie zna jeszcze zmian stanu,
które przyniosły kolejne (odhaczenie na zegarku dla następnego urządzenia). Szef łączy się ponownie z nodami, których
listy wciąż się różnią - i z tymi, którym nie wyszło w pierwszej rundzie.

Rekord idzie w częściach i jest przyjmowany w całości albo wcale: zerwane połączenie niczego nie psuje, a w pamięci jest
naraz tylko jeden rekord.

## 5. Kto ma rację

Dla każdego rekordu (`ble/merge.py`):

- **Treść** rekordów szefa (slot 0 w id) zawsze pochodzi od szefa. Rekord szefa, którego brakuje na liście szefa, jest
  usuwany na nodzie.
- **Stan** - rutyna wł. / wył., zadanie zrobione, punkt checklisty odhaczony - pochodzi z kopii, w której zmienił się
  później (`c`). Każdy punkt checklisty ma własny czas, więc odhaczenie różnych punktów na dwóch urządzeniach się nie
  gryzie.
- **Lokalne rekordy noda** (jego slot w id) nigdy nie są zmieniane, usuwane ani przejmowane przez szefa.

Zegary decydują tylko o stanie (konflikt to dwa różne odhaczenia jednego rekordu: rzadki i niegroźny); treść nie zależy
od czasu, więc zły zegar nie nadpisze edycji.

**Checklisty:** linie zadania zaczynające się od `>` to jego punkty. Rozpoznaje się je po treści, nie po tytule, więc
działają tak samo na każdym urządzeniu; odhaczenia są trzymane obok pliku (`todo/done.dat`), więc tekst nigdy się nie
zmienia.

**Rutyny na wybranych urządzeniach:** pole `to` rutyny to maska bitowa slotów (bit n = slot n; 255 = każde urządzenie,
także dodane później). Każde urządzenie odpala tylko rutyny, które mają jego bit.

## 6. Parowanie i bezpieczeństwo

**W 2.0: parowanie w aplikacji** (`ble/auth.py`; polecenia w [data-format.md](data-format.md) §4).

- **Parowanie (raz):** szef wysyła losowy nonce (`AUTH_HELLO`); node odpowiada swoim i pokazuje 6-cyfrowy kod;
  użytkownik wpisuje go na szefie; obie strony wyprowadzają `K = HMAC-SHA256(code, "squirrel-pair" + nonces)[:16]`, a
  szef dowodzi, że go ma (`AUTH_CONFIRM`). Sam kod nigdy nie idzie w powietrzu.
- **Każda sesja:** node daje świeże jednorazowe wyzwanie (`AUTH_CHALLENGE`); szef odpowiada
  `HMAC(K, "session" + challenge)` (`AUTH_PROVE`). Do tego czasu node odmawia wszystkiego (błąd 6) poza odczytem `INFO`
  i `TIME`, i ignoruje zapis czasu.
- **Klucze:** `ble_auth.json` na wewnętrznym flashu - nigdy na wyjmowanej karcie. Zapomnienie urządzenia na szefie
  usuwa jego klucz; node, który stracił klucz, prosi o nowy kod. Strona Web Bluetooth trzyma swój klucz w `localStorage`
  przeglądarki, osobno dla każdego urządzenia.

> ⚠️ **Czego to nie chroni.** Rekordy idą **nieszyfrowane**: ktoś w zasięgu radia ze sprzętem do podsłuchu BLE może
> je przeczytać w trakcie synchronizacji (nie zmienić, nie zsynchronizować urządzenia bez klucza). Podsłuchane
> parowanie pozwala odtworzyć klucz offline (kod ma 6 cyfr). Przewodniki mówią użytkownikom, żeby parowali z dala od
> obcych i nie trzymali sekretów w synchronizowanych notatkach.

**Szyfrowanie łącza (LE Secure Connections)** jest w kodzie, ale wyłączone (`nuts.BLE_LINK_PAIRING = False`): passkey
pokazywany na nodzie, wiązania trzymane przez aplikację (`ble/secrets.py`, `GET_SECRET` / `SET_SECRET` z IRQ) i
poprawka do NimBLE dla zdarzeń passkey po stronie centrali (`firmware_patches/0001-nimble-central-passkey.patch`).
Działało, ale Cardputer resetował się w części sesji - co okazało się innym błędem (backlog A).

## 7. Automatyczna synchronizacja

`BLE_AUTO_SYNC_MIN` (0 = na żądanie; 15 ... 240) - `ble/auto.py`. Sesje są wyrównane do zegara: minuty doby podzielne
przez okres. Node jest źródłem alarmów (`alarms.py`), więc zegarek w głębokim śnie budzi się na każdą porę i rozgłasza
przez 90 s; szef startuje 20 s po początku pory. Pora jest pomijana, gdy radio jest zajęte (ekran Bluetooth,
synchronizacja czasu przez Wi-Fi) albo gdy node wymaga parowania (to wymaga użytkownika). Ekran Bluetooth otwarty w
trakcie automatycznej sesji ją przerywa. Ustawienie jest synchronizowane od szefa, więc nody za nim idą.

## 8. MicroPython na ESP32: co warto wiedzieć

- Handler IRQ działa na stosie zadania NimBLE, w środku jego pracy. Dane, które dostaje - krotka, adresy, bufory,
  **obiekty UUID** - są ważne tylko w czasie wywołania: wszystko, co zostaje, jest kopiowane (`bytes(...)`,
  `bluetooth.UUID(...)`). **`tuple(data)` nie jest kopią**: MicroPython zwraca tę samą krotkę, a jej zatrzymanie
  resetowało Cardputera w losowych momentach synchronizacji, dopóki tego nie znaleziono (`tuple(list(data))` kopiuje).
- Żadnych generatorów ani parsowania w handlerze; robi to `tick()`. Handler musi odpowiadać na `GET_SECRET` /
  `SET_SECRET` (brak odpowiedzi na `SET_SECRET` resetował Cardputera).
- Gdy radio pracuje, automatyczne odśmiecanie jest wyłączone, a `tick()` odśmieca z pętli głównej (`radio_gc`):
  odśmiecanie uruchomione przez alokację w IRQ działało na małym stosie zadania NimBLE.
- Usługi w tle są wstrzymywane na czas sesji (`ServiceManager.paused`), więc pętla główna odpowiada radiu szybko.
- Wyłączenie radia zaraz po sesji ścigało się z timerami NimBLE: `_settle()` najpierw czeka 100 ms.

## 9. Kod

```
ble/protocol.py     UUIDs, record codecs, frames, SYNCED_KEYS - plain Python, tested on the PC
ble/merge.py        boss copy + node copy -> the result (content from the boss, state by time, local untouched)
ble/peripheral.py   the node: GATT server, IRQ, parts, pairing answers, tick()
ble/central.py      the boss: scan, connect, the session as a generator driven by tick()
ble/node_data.py    the app's data as records (routines, To-Dos, notes, settings, statistics, time)
ble/peers.py        the boss's devices (ble.json) and their reports (focus/peers/<slot>/)
ble/auth.py         pairing with a code, the proof of every session, the key store
ble/secrets.py      the bonds of link pairing (off)
ble/auto.py         automatic sync on the clock
screens/ble_head_screen.py   the boss's Bluetooth screen (devices, Add device, Sync now, Auto sync, quick sync)
screens/ble_sync_screen.py   the node's Bluetooth screen (waiting, the pairing code)
tools/web/                   the Web Bluetooth page and its JavaScript codec
```

`features.toml`: `ble_sync` (każdy port z `[radio] ble = true`: część noda), `ble_hub` (port, który ma też klawiaturę:
część szefa).

## 10. Jeszcze niezbudowane

- **Edycja na nodzie** (telefon połączony z zegarkiem): stosowana od razu, zapisywana jako *propozycje* z wersją, na
  której powstała; szef decyduje przy następnej synchronizacji - przyjęta, jeśli w międzyczasie nie zmienił tego
  rekordu, inaczej konflikt; nowe rekordy zostają lokalne albo są przejmowane. `SYNC_MODE` *auto* / *ask* z ekranem
  różnic (wyślij / weź / pomiń dla każdej kategorii). Zestaw `0x0B` jest na to zarezerwowany.
- **Nowy szef:** przejęcie pełnej kopii rekordów szefa z dowolnego noda, z identyfikatorami i licznikami, i ponowne
  sparowanie nodów.
- **Małe urządzenia:** protokół jest pomyślany tak, żeby dało się go zaimplementować w C bez dynamicznej alokacji.
