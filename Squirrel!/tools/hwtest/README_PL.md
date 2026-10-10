# tools/hwtest — testy sprzętu (T-Watch 2020 V3, akcelerometry)

Skrypty wykonywane **na urządzeniu** przez jego REPL; uruchamia je `run.py` z PC i pokazuje wyniki na żywo.
Każda linia wyniku: `RESULT|test|PASS / FAIL / INFO / ASK / SKIP|szczegóły`. **ASK** = potwierdzasz, co widziałeś / słyszałeś / czułeś.
Log każdego przebiegu: `.build/hwtest/<skrypt>-<czas>.log`.

```bash
python3 tools/hwtest/run.py PORT SKRYPT [TEST ...]      # bez TEST: domyślny zestaw skryptu
python3 tools/hwtest/run.py PORT SKRYPT --list          # lista testów
```

Zabezpieczenie: pierwsza linia skryptu (`# EXPECT_MACHINE: ...`) musi pasować do `sys.implementation._machine` urządzenia,
inaczej nic nie jest uruchamiane. Testy zegarka dodatkowo sprawdzają, że na I2C 21/22 odpowiada AXP202 — na innej płytce
nie robią nic. Zamknij Thonny przed uruchomieniem (trzyma port).

Porty dziś: Cardputer `/dev/ttyACM0`, T-Watch `/dev/ttyACM1` (USB-serial CH9102, producent 1a86).

---

## T-Watch 2020 V3

### Faza 0 — tylko odczyt (nic nie jest zapisywane w zegarku)

```bash
tools/hwtest/twatch_phase0.sh /dev/ttyACM1
```
Identyfikacja układu i flasha (esptool `chip_id`, `flash_id`), potem **pełna kopia flasha** (16 MB, kilka minut) z sumą MD5 do
`.build/hwtest/twatch-backup-<MAC>-<czas>.bin`. Ta kopia przywraca fabryczne firmware zegarka 1:1:
`esptool.py --chip esp32 -p /dev/ttyACM1 -b 921600 write_flash 0x0 <plik>`.

### Faza 1 — wgranie MicroPythona (zapis: cały flash)

Testy faz 2–3 działają na zwykłym MicroPythonie dla ESP32 z PSRAM (płytka `ESP32_GENERIC`, wariant `SPIRAM`), bez kodu
Squirrel!. Ta sama wersja co na Cardputerze: **1.25.0**. Źródło do wyboru:
- **A (proponuję):** oficjalny obraz v1.25.0, wariant SPIRAM, ze strony micropython.org/download/ESP32_GENERIC;
- **B:** zbudowany lokalnie z `micropython/` repozytorium firmware (ESP-IDF 5.4.2) — dłużej, a drzewo ma łatki pod Cardputera.

Wgranie: `esptool.py --chip esp32 -p /dev/ttyACM1 erase_flash`, potem `write_flash -z 0x1000 <obraz>`.

### Faza 2 — uruchamianie sprzętu: `twatch_hw.py`

| Test | Co robi / co zmienia | Co potwierdzasz |
|---|---|---|
| `t01_system` | czyta: wersja, CPU, pamięć (PSRAM?), rozmiar flasha | — |
| `t02_i2c` | skanuje obie magistrale: AXP202 0x35, BMA423 0x19, PCF8563 0x51 / dotyk FT6336 0x38 | — |
| `t03_axp` | czyta AXP202: USB, bateria, ładowanie, które wyjścia włączone, ustawione napięcia, czas wyłączenia przyciskiem | — |
| `t08_rtc` | czyta PCF8563: data/godzina, bit „czas nieważny”, czy chodzi | — |
| `t13_mic` | sprawdza, czy `machine.I2S` ma PDM (mikrofon V3) | — |
| `t04_backlight` | włącza LDO2 (po sprawdzeniu, że jest ustawione na 3,0–3,3 V), PWM na GPIO15: 3 pulsy | **czy podświetlenie pulsowało** |
| `t04b_backlight_pin12` | to samo na GPIO12 (gdyby V3 miał podświetlenie jak V1) | jw. |
| `t05_display` | ST7789: wypełnienia CZERWONY, ZIELONY, NIEBIESKI, BIAŁY (po 1,5 s), potem znaczniki | **kolory w tej kolejności? żółty kwadrat w lewym górnym rogu, turkusowy w prawym dolnym, czerwony pasek u góry? pas śmieci?** |
| `t06_display_rot180` | to samo obrócone o 180° (przesunięcie 80 wierszy) | jw. — który wariant jest właściwy |
| `t07_touch` | 15 s odczytu dotyku (start: 1 wibracja, koniec: 2) | stuknij: lewy górny, prawy górny, lewy dolny, prawy dolny, środek — **czy współrzędne się zgadzają** |
| `t09_vibration` | GPIO4: 3 krótkie, 1 długa | **czy czułeś** |
| `t10_button` | przerwanie przycisku w AXP202, 12 s (start: 1 wibracja) | 2× krótko, 1× ~2 s — **nigdy dłużej niż 3 s** (wyłącza zegarek) |
| `t11_speaker` | włącza LDO3 (po sprawdzeniu napięcia), I2S: dwa ciche tony, potem LDO3 wyłączone z powrotem | **czy słyszałeś niski i wyższy ton** |
| `t12_battery` | włącza przetworniki ADC w AXP202, czyta napięcie baterii, USB, prądy, wskaźnik % | — |

Bez podania testów `run.py` wykonuje tylko te czytające (`t01 t02 t03 t08 t13`).
Zapisywane mogą być wyłącznie rejestry AXP202: 0x12 (bity LDO2/LDO3), 0x82 (ADC), 0x42/0x4A (przerwanie przycisku) —
lista w kodzie, każdy inny zapis kończy test błędem. Napięcia i zasilanie samego ESP32 (DCDC2/DCDC3) są tylko czytane.

Proponowana kolejność: `t01…t03, t08, t13` → `t04` (ew. `t04b`) → `t05`, `t06` → `t09` → `t07` → `t10` → `t11` → `t12`.

### Faza 3 — akcelerometr: `twatch_accel.py`

Wskazówki wibracją (ekran może jeszcze nie działać): **1 krótka** = ustaw następną pozycję (6 s), **2 krótkie** = zmierzone,
**3 krótkie** = potrząsaj.

| Test | Co robisz |
|---|---|
| `t01_identify` | — (chip id BMA423 = 0x13) |
| `t02_still` | zegarek płasko, tarczą do góry |
| `t03_orientation` | 1) tarczą do góry, 2) tarczą w dół, 3) pionowo, „12” u góry, 4) na boku, przyciskiem do góry |
| `t04_shake` | potrząsaj 5 s |
| `t05_temperature` | — |
| `t06_off` | — (akcelerometr wyłączony z powrotem) |

Tylko „goły” akcelerometr: licznik kroków, wykrycie podniesienia nadgarstka i podwójne stuknięcie wymagają wgrania do układu
pliku konfiguracyjnego (~6 KB) — następny krok, gdy podstawy zadziałają.

---

## Cardputer ADV — akcelerometr: `cardputer_accel.py`

```bash
python3 tools/hwtest/run.py /dev/ttyACM0 cardputer_accel.py
```
Działa na firmware Squirrel!: `run.py` zatrzymuje aplikację (Ctrl-C), po testach restartuje urządzenie. Instrukcje z odliczaniem
pojawiają się **na ekranie Cardputera**. Konfigurację BMI270 wgrywa już `M5.begin()`; Squirrel! tylko wyłącza mu zasilanie —
test je włącza, mierzy i wyłącza z powrotem.

| Test | Co robisz |
|---|---|
| `t01_identify` | — (chip id 0x24, czy konfiguracja wgrana, typ w `M5.Imu`, stan zasilania) |
| `t02_still` | połóż płasko, ekranem do góry (porównanie rejestrów z `M5.Imu.getAccel`) |
| `t03_orientation` | 1) ekranem do góry, 2) ekranem w dół, 3) pionowo, ekran do Ciebie, klawiatura na dole, 4) na lewym boku |
| `t04_shake` | potrząsaj 5 s |
| `t05_off` | — (wyłączony, jak zostawia go aplikacja) |

Wynik `t03` (która oś i z jakim znakiem wskazuje „ekran w dół”) to dane do przyszłej funkcji „ekranem w dół = cisza” na obu
urządzeniach.

---

## Wyniki: T-Watch 2020 V3, 2026-10-10 (MicroPython 1.25.0 ESP32_GENERIC SPIRAM)

Układ ESP32-D0WDQ6-V3, flash 16 MB (Winbond), PSRAM działa (~4 MB sterty). Wcześniej był CircuitPython 10.2.1 — pełna kopia
flasha i wyciągnięte pliki projektu: `.build/hwtest/` (kopia zweryfikowana; różniła się tylko partycja NVS, którą CircuitPython
zapisuje przy starcie).

| Element | Wynik | Co z tego wynika dla portu |
|---|---|---|
| piny | zgodne z definicją płytki CircuitPythona i biblioteką LilyGo | + `TOUCH_RST` = GPIO14 (impuls resetu przed użyciem dotyku) |
| AXP202 | id 0x41, bateria 4,19 V / 100 %, odczyty ADC | |
| ekran ST7789 | **PASS** w wariancie: MADCTL 0xC0, przesunięcie 80 wierszy, inwersja | SPI **26,67 MHz, `miso=None`** — przy 40 MHz MicroPython 1.25 wywraca się (panika zamiast wyjątku), bo MOSI=GPIO19 idzie przez macierz GPIO; cały ekran 78 ms |
| podświetlenie | **PASS**, GPIO15 (PWM), zasilanie LDO2 3,3 V | |
| dotyk FT6336U | **PASS** 7/7 (rogi, środek, 2× stuknięcie, przytrzymanie) | współrzędne pokrywają się z obrazem (bez przeliczania) |
| wibracja | **PASS**, GPIO4 | |
| przycisk boczny | **PASS** (AXP202, klawisz zasilania) | AXP sam zgłasza krótkie/długie naciśnięcie (0x4A bity 1/0) i zbocza (0x4C bity 5/6); przed użyciem skasować zaległe przerwania (0x48–0x4C), inaczej linia INT (GPIO35) stoi nisko |
| głośnik MAX98357A | **PASS** | zasilanie **LDO4 = 3,3 V** (było 1,8 V!), jak w bibliotece LilyGo; LDO3 w V3 nieużywane; I2S **stereo** (BCK 26, WS 25, DOUT 33) |
| zegar PCF8563 | chodzi, ale **bit VL** (czas nieważny, 2026-09-30) | port musi zapisać czas przy pierwszym ustawieniu i skasować VL |
| akcelerometr BMA423 | **PASS** bez pliku konfiguracyjnego (szum ~0,001 g) | tarcza do góry −z, w dół +z, „12” u góry −x, przycisk do góry −y; „ekranem w dół” = z > ~+0,8 g |
| mikrofon PDM | SKIP — `machine.I2S` nie ma PDM | moduł C (etap 3) |
