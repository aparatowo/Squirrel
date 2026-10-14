# Backlog

*[English](../en/backlog.md) · Polski · [Français](../fr/backlog.md) · [Deutsch](../de/backlog.md)*

Co wiadomo, że jest nie tak, czego jeszcze nie zbudowano, i co było w planach, a zrobiło się inaczej. Stan wersji 2.0.
Użytkownicy widzą pierwszą część jako znane ograniczenia w [informacjach o wydaniach](../../releases/README.md).

## Znane problemy

### A. Szyfrowanie łącza jest wyłączone

Rekordy Bluetooth idą w powietrzu nieszyfrowane; przed zmianą chroni je tylko parowanie z kodem w aplikacji (zobacz
[bluetooth.md](bluetooth.md) §6). LE Secure Connections jest w kodzie (`nuts.BLE_LINK_PAIRING = False`,
`ble/secrets.py`, `firmware_patches/0001-nimble-central-passkey.patch`) i działało na urządzeniach, ale Cardputer
resetował się w części sesji.

Resety okazały się innym błędem (2026-10-13): handler IRQ szefa odkładał do kolejki `tuple(data)`, a w MicroPythonie
`tuple()` z krotki zwraca **ten sam obiekt** - krotkę z IRQ leżącą na stosie zadania NimBLE, nadpisywaną przez radio,
zanim `tick()` ją przeczytał. Poprawione (`tuple(list(data))`); od tego czasu 55 synchronizacji bez resetu. Z
szyfrowaniem łącza po poprawce: 5 z 5 synchronizacji, potem zawieszenie w szóstej (bez paniki, USB przestał przyjmować
dane).

Dalej: seria z `tools/hwtest/ble_e2e.py --link`, wyjaśnić zawieszenie, potem `BLE_LINK_PAIRING = True` (parowanie w
aplikacji zostaje jako dowód, że to Twój szef; szyfrowanie zamyka podsłuch i łamanie kodu offline). Przy okazji
sprawdzić, czy `radio_gc` (bez automatycznego odśmiecania w trakcie sesji) jest jeszcze potrzebne.

### B. Rzadkie zawieszenie Cardputera

Mniej więcej raz na 70 synchronizacji (2026-10-13): `mp_task` czekał w
`spi_flash_disable_interrupts_caches_and_other_cpu` (zwykły odczyt flasha) na rdzeń 0, który obsługiwał przerwania,
ale nie zadania. Przyczyna nieznana; kontroler Bluetooth działa na rdzeniu 0.

Złagodzenie: watchdog pętli głównej (`nuts.WATCHDOG_S`, 60 s) restartuje urządzenie; dane zostają. Firmware zapisuje
wtedy, co robił rdzeń 0 (`firmware_patches/0002-panic-record.patch`); następnym razem odczytać to
`tools/hwtest/panic_record.py` i szukać przyczyny.

### C. "brak odpowiedzi" tuż po połączeniu

Czasem szef nie dostaje odpowiedzi na odkrywanie usług (raz 7 z 30, raz 0 z 25). Komunikat mówi, na które zdarzenia
czekał. Złagodzenie: druga runda synchronizacji ponawia nieudane urządzenia.

### D. Zrzuty ekranu Cardputera używają czcionki zegarka

`tools/sim/render_shots.py` rysuje tekst czcionką 6 × 8 z `drivers/glcdfont.py` (+ `glcdfont_latin.py`), a Cardputer z
językiem innym niż angielski używa `squirrel.vlw`. Zdjęcia w przewodnikach zgadzają się układem i słowami, trochę
różnią się kształtem liter. Poprawka: rysować glify `.vlw` w `render_shots.py` (`vlw.py` umie je czytać).

### E. Node trzyma jeden klucz parowania

`ble/peripheral.py` trzyma jeden klucz na noda (`"head"` w `ble_auth.json`): sparowanie strony www z zegarkiem zastępuje
klucz Cardputera, a Cardputer przy następnej synchronizacji prosi o nowy kod (i odwrotnie). Opisane dla użytkowników;
poprawka trzymałaby kilka kluczy i przyjmowała dowód któregokolwiek - bez zmian w powietrzu i na stronie.

## Jeszcze niezbudowane

- **Edycja na nodzie** (telefon połączony z zegarkiem): zapisywana jako propozycje z wersją, na której powstały; szef
  decyduje przy następnej synchronizacji. `SYNC_MODE` *auto* / *ask* z ekranem różnic (wyślij / weź / pomiń dla każdej
  kategorii). Zestaw `0x0B` jest zarezerwowany ([bluetooth.md](bluetooth.md) §10).
- **Nowy szef**: przejęcie pełnej kopii rekordów z dowolnego noda, z identyfikatorami i licznikami, i ponowne
  sparowanie nodów.
- **Strona Web Bluetooth** (`Squirrel!/tools/web/`): jej kodek jest sprawdzony z `protocol.py` na PC; z zegarkiem
  (Chrome, strona otwarta z dysku) łączenie, parowanie i odczyt działają (`tools/hwtest/web_e2e.py`); edycji ze strony
  jeszcze nie sprawdzano. Publikacja na GitHub Pages dla telefonów: `.github/workflows/web-page.yml`, gotowa, niewłączona.
- **Ogólny zegarek z ESP32-S3** (`ports/generic_s3_watch`): buduje się, jeszcze niesprawdzony na zegarku.
- **Dźwięk i mikrofon zegarka, akcelerometr** (nadal tylko wyłączany przy starcie).
- **Pomysły z planów:**
  - filtr *Dziś* na liście zadań;
  - tagi emocjonalne na wpisie (🔥 pilne, 💡 pomysł, 😰 stres, 🕑 kiedyś);
  - widok skupienia na jednym zadaniu (*Teraz robię*: jedno zadanie, duże);
  - automatyczne znaczniki czasu na notatkach;
  - powrót do ostatnio otwartej notatki po restarcie;
  - tryb dysku USB (karta SD widziana z komputera);
  - tryb hiperoszczędny.

## Zrobione inaczej

| W planach | Jak to jest zrobione |
|---|---|
| Quick Capture (FN+SPACE z zegara) | menu TAB na zegarze: **TAB, M** - Mind dump, **TAB, T / N** - zadanie / notatka; **G0** od razu nagrywa notatkę głosową |
| Mikro serwer www na zegarku, do rutyn z telefonu | strona Web Bluetooth: bez serwera Wi-Fi, rozmawia z urządzeniami bezpośrednio |
| Port na programowalne smartwatche | port T-Watch 2020 V3 (2.0), eksperymentalny port ogólnego ESP32-S3 |
| Współpraca z Cardputerem | synchronizacja Bluetooth (2.0) |
