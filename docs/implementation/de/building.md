# Die Firmware bauen

*[English](../en/building.md) · [Polski](../pl/building.md) · [Français](../fr/building.md) · Deutsch*

`Squirrel!/build_firmware.py` baut ein Firmware-Image mit der ganzen App darin **eingefroren**: der Code ist Bytecode im
Flash, keine Dateien auf dem Gerät und keine Kompilierung ins RAM beim Start. Es braucht nur die Standardbibliothek von
Python. Die kurze Fassung für Nutzer steht in [guides/de/getting-started.md](../../guides/de/getting-started.md); hier
ist die ganze Geschichte. Die Geräte und ihre `port.toml`: [ports.md](ports.md).

Starte jeden Befehl in `Squirrel!/`.

## 1. Einmal pro Computer

```bash
python3 build_firmware.py --install-idf          # ESP-IDF 5.4.2 (~1 GB) into ~/esp-idf-v5.4.2 (or: --install-idf DIR)
python3 build_firmware.py --check                # what is in place, what is missing - changes nothing
```

- **Nur ESP-IDF 5.4.x.** Die Firmware des Cardputers ist für 5.4.2 gepatcht; mit 5.5 nimmt sein Mikrofon Stille auf,
  ältere bauen sie nicht. Das Skript findet 5.4.x selbst, auch wenn `IDF_PATH` in deiner Shell woanders hinzeigt.
- **Cardputer, einmal:** `sudo apt install quilt`, dann `python3 build_firmware.py --setup` (Submodule, Patches,
  littlefs, mpy-cross des UIFlow-Repositorys; Markierung `.build/setup.done`, `--force` wiederholt es).
- **Die Uhren** brauchen nichts weiter: der erste Build klont MicroPython v1.25.0 nach `vendor/micropython` und wendet
  die Patches des Ports selbst an.

Das Firmware-Repository des Cardputers (`cardputer-adv-micropython`) wird beim ersten Lauf nach `vendor/` geklont. Ein
anderer Ort: `--repo`, die Variable `SQUIRREL_FW_REPO` oder `build_config.json`:

```json
{"repo": "/path/to/cardputer-adv-micropython", "idf": "/path/to/esp-idf-v5.4.2", "port": "twatch2020_v3", "exclude": []}
```

## 2. Im Alltag

```bash
python3 build_firmware.py --stage-only                    # seconds: collect the sources, check imports, compile them
python3 build_firmware.py                                 # full image -> dist/squirrel-<board>-<git>-<time>.bin (+ .txt)
python3 build_firmware.py --flash /dev/ttyACM0            # build and flash
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0     # another device
```

Die `.txt` neben dem Image listet, was darin ist. Der Build läuft in einer sauberen Umgebung (ohne die `IDF_*`-Variablen
deiner Shell) und beginnt von vorn, wenn der vorige ein anderes ESP-IDF benutzt hat.

**Was ein Build tut:** er liest `ports/<port>/port.toml` und `features.toml`, schreibt `port_config.py` für dieses
Gerät, lässt die Module der Funktionen weg, die das Gerät nicht hat, die Treiber, die seine `port.toml` nicht nennt,
und die Ordner anderer Ports, hält an, wenn ein Modul etwas importiert, das nicht in diesem Build ist, kompiliert
alles mit dem eigenen `mpy-cross` der Firmware und friert es in eine eigene Board-Definition ein (die Dateien des
Firmware-Repositorys werden nicht geändert: ein abgeleitetes Board, eingetragen in `.git/info/exclude`; `--clean`
entfernt es). `lang/<code>.py` (die Übersetzungen, von `tools/i18n/build.py` aus `translations/*.tsv` gebaut) wird wie
jedes Modul eingefroren, und die Schrift des Cardputers kommt in die Systempartition des Images.

## 3. Flashen

```bash
python3 build_firmware.py --flash-image <file from dist/> --flash /dev/ttyACM0    # an image built earlier
python3 build_firmware.py --setup-device /dev/ttyACM0                            # only prepare a device
python3 build_firmware.py --flash /dev/ttyACM0 --no-device-setup                 # flash, do not prepare
```

- Schließe Thonny (oder was sonst den Port belegt). `ls /dev/serial/by-id/` nennt die Geräte: `...Espressif...` /
  `...M5Stack...` ist der Cardputer, `...1a86...` die T-Watch (CH9102).
- **Cardputer:** seine USB-Konsole ist TinyUSB, Teil der App, und ein Reset trennt die Verbindung - einen laufenden
  Cardputer zu flashen scheitert oft. Halte **G0** beim Einstecken des Kabels: er wartet im Download-Modus (schwarzer
  Bildschirm, der Port heißt dann `...Espressif_USB_JTAG...`). Nach dem Flashen startet er von selbst und kommt unter
  seinem App-Namen zurück; die Meldung "did not come back" heißt dann nur, dass sich der Name geändert hat.
- Das Image des Cardputers ist der ganze Flash ab 0x0 (UIFlows NVS-Einstellungen werden ersetzt; deine Daten sind auf
  der SD-Karte); die Images der Uhren berühren die Datenpartition nicht (`/Squirrel` bleibt).

**Das Gerät vorbereiten** (nach `--flash PORT` von selbst, jeder Schritt nur wenn nötig, und nur auf einem Gerät,
dessen `sys.implementation._machine` die `[port] machine` des Ports enthält):

1. `/flash/main.py` (oder `/main.py`) = `device/main.py`, das Squirrel! startet; ein älteres bleibt als `main.py.old`;
2. Cardputer: UIFlows `/flash/boot.py` wird in `boot.py.uiflow` umbenannt, wenn es `startup` importiert, das diese
   Firmware nicht hat (der alte Name bringt das UIFlow-Menü zurück);
3. Cardputer: UIFlows Startoption `boot_option = 0` (`main.py` sofort starten).

## 4. Ein Gerät prüfen

```python
import sq_info; sq_info.report()       # in Thonny
```

Es zeigt den Build, die Zahl der eingefrorenen Module, Dateien, die eingefrorene Module **verdecken**, ob `main.py` die
App startet, die Schrift, und woher `nuts` kam. Das Startprotokoll (`/flash/boot_log.txt` auf dem Cardputer,
`/boot_log.txt` auf der Uhr) hat eine Zeile `[MAIN] frozen build <id> (N modules)`.

Lass keine `.py`- / `.mpy`-Module im Flash des Geräts (außer `main.py`): sie würden die eingefrorenen gleichen Namens
verdecken.

## 5. DEV-Modus: Code ändern ohne neue Firmware

Lege eine leere Datei `/flash/DEV` an (die Uhr: `/DEV`) und lege die geänderten `.py`-Dateien nach
`/flash/apps/Squirrel/` (Unterordner wie in den Quellen). Sie gewinnen jetzt gegen die eingefrorenen; lösche `DEV`, um
zurückzukehren. Ein Ordner (`screens/`, `hw/`, `drivers/`, `ports/`) auf dem Gerät verdeckt das **ganze**
eingefrorene Paket dieses Namens, also kopiere ihn ganz. Eine `.mpy` gewinnt gegen eine `.py` gleichen Namens.

Schnelle Hilfe, wenn einem Gerät beim Kompilieren von `.py`-Dateien der Speicher ausgeht: `--build-mpy-cross`, dann
`--mpy` schreibt `.mpy`-Dateien nach `dist/mpy/` (kein ESP-IDF nötig).

## 6. Weitere Optionen

| Option | Was sie tut |
|---|---|
| `--target build` | nur die App (`micropython.bin`) - kein vollständiges Image |
| `--target pack_all` | das Image mit einem **leeren** Nutzer-Dateisystem: löscht `/flash` |
| `--gen-port-config` | schreibt `port_config.py` neben die Quellen (für den DEV-Modus und den Simulator); der Standardport, außer `--port` |
| `--exclude FILE` | eine Datei aus dem Image lassen (wiederholbar; PC-Skripte wie `vlw.py` werden von selbst weggelassen) |
| `--prefer newer\|flat\|screens` | derselbe Bildschirm an zwei Orten mit verschiedenem Inhalt: welcher gewinnt |
| `--update-repo` | `git pull` im Firmware-Repository |
| `--reset-deps` | `dependencies.lock` und `managed_components` löschen (beim nächsten Build neu aufgelöst) |
| `--diagnose` | den letzten gescheiterten Build aus `.build/make.log` erklären |
| `--allow-any-idf` | mit einem anderen ESP-IDF bauen (nicht für `--setup`; nicht empfohlen) |
| `--allow-missing` | bauen, auch wenn das Manifest des Basis-Boards eine fehlende Datei nennt |

Die `port_config.py` neben den Quellen gehört zum Standardport (dem Cardputer); stelle sie nach
`--gen-port-config --port X` vor dem Commit wieder her. Ein Build schreibt immer seine eigene.

## 7. Patches an der Firmware

Die Firmware wird nur durch Patches geändert, die im Repository liegen und als Stapel auf eine temporäre Kopie
angewendet werden:

| Patch | Was er tut |
|---|---|
| `firmware_patches/0001-nimble-central-passkey.patch` | NimBLE: die Passkey-Ereignisse der Central (Verschlüsselung der Verbindung, vorerst aus) |
| `firmware_patches/0002-panic-record.patch` | ein Bericht über eine Panik oder den Task-Watchdog, im RTC-Speicher über den Reset gehalten (`tools/hwtest/panic_record.py` liest ihn): die TinyUSB-Konsole des Cardputers zeigt bei einem Absturz nichts |
| `ports/<port>/firmware/patches/*.patch` | für jede Uhr: was ihr MicroPython-Build braucht |

## 8. Wenn etwas nicht klappt

| Meldung | Was tun |
|---|---|
| `No ESP-IDF 5.4.x found` | `--install-idf` |
| `quilt is not installed` | `sudo apt install quilt` |
| `mpy-cross is not built` | `--setup` (das Repository des Cardputers ist noch nicht vorbereitet) |
| `Two different copies of the same screen module` | die veraltete Datei löschen, oder `--prefer newer` |
| `... does not compile with the firmware's mpy-cross` | diese Datei benutzt Syntax, die MicroPython nicht hat |
| `imports ..., which is not in the sources (of this port)` | ein Modul braucht eine Funktion oder einen Treiber, den dieser Port weglässt: importiere es in der Funktion, die es braucht, oder füge es dem Port hinzu |
| `CFG_TUD_CDC_EP_BUFSIZE undeclared` | nicht passende TinyUSB-Komponenten: `espressif/tinyusb` in `m5stack/main/idf_component.yml` auf `0.15.0~10` festlegen, dann `--reset-deps` |
| `Cannot stat .../firmware_info.py` | das Skript erzeugt sie vor dem Build für das Basis-Board; wenn das scheitert, sagt es, was zu prüfen ist (`--allow-missing` überspringt die Prüfung) |
| Flashen scheitert | Thonny schließen; Cardputer: G0 beim Einstecken halten; Linux: `sudo usermod -aG dialout $USER` und neu anmelden |
| keine App nach dem Flashen | seit 2.1 schreibt die Firmware `/flash/main.py` beim ersten Start selbst (komplettes Image aus M5Burner, gelöschter Chip); sonst `--setup-device PORT`; `/flash/main.py` prüfen |
| etwas anderes | die ganze Ausgabe steht in `.build/make.log`; `--diagnose` erkennt die bekannten Fälle |
