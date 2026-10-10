# 🐿️ Squirrel! — Instrukcja instalacji (PL)

---

## Zanim zaczniesz — co musisz mieć

### Na komputerze

| Co? | Po co? | Jak sprawdzić? |
|---|---|---|
| **Python 3.10+** | Buduje firmware i uruchamia skrypt | W terminalu wpisz: `python3 --version` |
| **Git** | Pobiera kod źródłowy | W terminalu wpisz: `git --version` |
| **Thonny** | Wgrywa pliki na urządzenie | Otwórz aplikację Thonny |
| **Kabel USB-C** | Łączy Cardputer z komputerem | Fizycznie sprawdź |
| **Karta microSD** | Przechowuje notatki | Musi być włożona w Cardputer |

> 💡 **Linux / macOS:** Python i Git są zazwyczaj już zainstalowane.
> **Windows:** Pobierz Python z [python.org](https://python.org) i Git z [git-scm.com](https://git-scm.com).

---

## Krok 1 — Pobierz kod Squirrel!

Otwórz terminal i wpisz te komendy **jedną po drugiej**:

```bash
cd ~
```

```bash
git clone https://github.com/aparatowo/Squirrel.git
```

```bash
cd Squirrel
```

---

## Krok 2 — Zainstaluj wymagane biblioteki Pythona

```bash
pip3 install esptool
```

To jedyna zewnętrzna biblioteka potrzebna do zbudowania i wgrania firmware.

---

## Krok 3 — Zbuduj firmware

> ⚠️ Ten krok może zająć **kilka–kilkanaście minut**. Spokojnie, komputer pracuje.

```bash
cd apps
```

```bash
python3 build_firmware.py
```

Skrypt sam pobierze wszystko, co potrzebne, i zbuduje plik `.bin` z zamrożonymi modułami Squirrel!.

Po zakończeniu w folderze `apps/` pojawi się plik `squirrel_firmware.bin` (lub podobna nazwa — sprawdź, co skrypt wypisał na końcu).

---

## Krok 4 — Wgraj firmware na Cardputer

### 4a. Podłącz urządzenie w trybie flash

1. Wyłącz Cardputer.
2. Przytrzymaj klawisz **`G0`** (mały przycisk boczny).
3. Trzymając `G0` — podłącz kabel USB-C do komputera.
4. Puść `G0`. Ekran pozostanie czarny — to normalne.

### 4b. Wgraj plik

```bash
python3 build_firmware.py --flash /dev/ttyACM0
```

> Jeśli skrypt pyta o port, wpisz:
> - **Linux:** `/dev/ttyUSB0` lub `/dev/ttyACM0`
> - **macOS:** `/dev/cu.usbserial-*` (sprawdź: `ls /dev/cu.*`)
> - **Windows:** `COM3` (lub inna litera — sprawdź Menedżer urządzeń)

Wgrywanie zajmuje około **1–2 minut**.

### 4c. Uruchom ponownie

Po zakończeniu odłącz i podłącz ponownie kabel (lub naciśnij przycisk reset na urządzeniu). Cardputer uruchomi się normalnie.

---

## Krok 5 — Przygotowanie urządzenia (automatycznie)

Nic nie trzeba wgrywać ręcznie. Cała aplikacja jest **zamrożona** w firmware, a `build_firmware.py --flash PORT` po wgraniu
sam przygotowuje urządzenie:

1. wgrywa `/flash/main.py` (z `Squirrel!/device/main.py`; 5 linii, uruchamia aplikację z firmware);
2. zmienia nazwę UIFlow-owego `/flash/boot.py` na `/flash/boot.py.uiflow`, jeśli nie może on działać z tym firmware;
3. ustawia opcję startu UIFlow na „uruchom `main.py`”.

Jeśli wgrywałeś bez podania portu (albo wcześniej), zrób to osobno (zamknij Thonny — trzyma port):

```bash
python3 build_firmware.py --setup-device /dev/ttyACM0
```

> ⚠️ **Nie wgrywaj** plików `.py` aplikacji do `/flash/apps/Squirrel/` ani do `/flash/` — przesłoniłyby kod zamrożony w firmware.
> Wyjątek: tryb DEV (patrz `Squirrel!/BUILD.md`).

---

## Krok 6 — Przygotuj kartę microSD

Karta musi być sformatowana jako **FAT32**.

Squirrel! sam stworzy folder `/Squirrel/` przy pierwszym uruchomieniu.
Nic nie musisz robić ręcznie.

---

## Gotowe! 🎉

Uruchom ponownie Cardputer — Squirrel! startuje od razu (bez menu UIFlow2).

---

## Coś nie działa?

| Problem | Co zrobić |
|---|---|
| Ekran czarny po wgraniu | Sprawdź kabel USB-C, spróbuj innego portu w komputerze |
| Thonny nie widzi urządzenia | Sprawdź, czy urządzenie jest włączone i nie jest w trybie flash |
| Błąd `port not found` | Sprawdź port w Menedżerze urządzeń (Windows) lub `ls /dev/tty*` (Linux/Mac) |
| Aplikacja nie startuje | Uruchom `python3 build_firmware.py --setup-device /dev/ttyACM0`; w Thonny: `import sq_info; sq_info.report()` |
| Notatki nie zapisują się | Sprawdź, czy karta microSD jest włożona i sformatowana jako FAT32 |

---

*Squirrel! © Rafał Nitychoruk (Ijon Tichy) — licencja MIT*
