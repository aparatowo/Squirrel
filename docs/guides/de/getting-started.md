# Erste Schritte

*[English](../en/getting-started.md) · [Polski](../pl/getting-started.md) · [Français](../fr/getting-started.md) · Deutsch*

Von einem neuen Gerät zu Squirrel! darauf. Version 2.0.

## Die Geräte

| Gerät | Was es ist | Was du brauchst |
|---|---|---|
| **M5Stack Cardputer ADV** | ein Taschencomputer mit Tastatur (ESP32-S3) - das Hauptgerät von Squirrel!, der *Chef* der Bluetooth-Synchronisation | eine microSD-Karte (FAT32) für deine Daten |
| **M5Stack Cardputer** (der erste, v1.0 / v1.1) | *experimentell*: derselbe Taschencomputer vor dem ADV - noch nicht auf einem Gerät ausprobiert | eine microSD-Karte (FAT32); für die Zeit ohne WLAN ein DS3231-Modul am Grove-Port |
| **LilyGo T-Watch 2020 V3** | eine Uhr mit Touchscreen (ESP32) - liest und hakt ab, was der Cardputer ihr gibt, Routinen und Timer am Handgelenk | nichts weiter |
| **Eine allgemeine ESP32-S3-Smartwatch** | *experimentell*: die günstigen Uhren, die als "ESP32-S3 smartwatch" verkauft werden - noch nicht auf einem Gerät ausprobiert | zuerst ihre Pins prüfen ([Ports](../../implementation/de/ports.md)) |

Was wo funktioniert: Der Cardputer hat alles; die Uhr hat keine Tastatur (sie schreibt keine Notizen oder Aufgaben -
sie liest und hakt sie ab) und noch keinen Ton und kein Mikrofon, dafür vibriert sie, schläft tief und hat eine
Hardware-Uhr. Der erste Cardputer hat alles außer dem Summer (kein freier Pin dafür); aus dem leichten Schlaf weckt
ihn nur eine Tastenreihe (Aa, S, F, H, K, UP, ENTER).

## Auf deinem Computer

- **Linux** (macOS und Windows sollten gehen, aber die Anleitung unten ist für Linux), **Python 3.10+**, **git**.
- Ein **USB-C-Kabel** (die Uhr: Micro-USB), das Daten überträgt, nicht nur lädt.

```bash
git clone https://github.com/aparatowo/Squirrel.git
cd "Squirrel/Squirrel!"
python3 build_firmware.py --install-idf     # ESP-IDF 5.4.2 (~1 GB), once
python3 build_firmware.py --check           # is everything in place? (changes nothing)
```

Der Cardputer braucht einmal einen Schritt mehr: `python3 build_firmware.py --setup` (dafür
`sudo apt install quilt`).

## Bauen und flashen

Schließe Thonny (oder alles andere, was den USB-Port belegt), dann:

```bash
# Cardputer ADV (the default device)
python3 build_firmware.py --flash /dev/ttyACM0

# T-Watch 2020 V3
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0

# Cardputer (the first one, not ADV) - experimental
python3 build_firmware.py --port cardputer --flash /dev/ttyACM0
```

Der erste Build kompiliert das ganze ESP-IDF und dauert einige Minuten; spätere gehen schneller. Das Skript baut das
Image (in `dist/`), flasht es und bereitet das Gerät vor, sodass Squirrel! von selbst startet.

**Welcher Port?** `ls /dev/serial/by-id/` nennt sie: der Cardputer ist `...Espressif...` oder `...M5Stack...`, die
Uhr `...1a86...`.

**Der Cardputer lässt sich nicht flashen?** Seine USB-Konsole ist Teil der App, und ein Reset trennt die
USB-Verbindung. Halte **G0** gedrückt, während du das Kabel einsteckst: der Cardputer wartet dann im Download-Modus
(schwarzer Bildschirm), und das Flashen klappt. Danach startet er die neue Firmware von selbst.

**Die Uhr zum ersten Mal:** sie kommt mit anderer Software. Sichere sie zuerst:
`tools/hwtest/twatch_phase0.sh /dev/ttyACM0` (16 MB, ein paar Minuten).

## Der erste Start

- **Cardputer:** stecke eine microSD-Karte (FAT32) ein; Squirrel! legt darauf selbst seinen Ordner `/Squirrel` an.
- **Die Uhrzeit:** der Cardputer stellt seine Uhr beim Start über WLAN - füge dein Netz in *Einstellungen →
  Verbindungen → WLAN-Netze* hinzu (ein Handy-Hotspot geht auch; 2,4 GHz). Oder stelle sie von Hand (*Einstellungen →
  Zeit und Datum → Zeit stellen*), oder hole sie per Bluetooth von der Uhr.
- **Ein Uhrmodul** (DS3231 / DS1302) hält die Zeit ohne WLAN: anstecken und in *Einstellungen → Zeit und Datum →
  Zeiteinstellungen → Uhrmodul* auswählen (bis dahin ist es aus).
- **Die Sprache:** *Einstellungen → Anpassen → Anzeige → Sprache* - English, Polski, Français, Deutsch.
- **Uhr und Cardputer zusammen:** koppele sie einmal ([Bluetooth-Synchronisation](bluetooth.md)).

Dann: [Funktionen](features.md) für das, was es gibt, [Tastenkürzel](shortcuts.md) für die Tasten.

## Deine Daten

Alles sind einfache Dateien: Notizen und Aufgaben als `.txt`, Sprachnotizen als `.wav`, Statistik, Routinen und
`config.txt` (deine Einstellungen, jede mit einem Kommentar). Auf dem Cardputer liegen sie auf der SD-Karte in
`/Squirrel`; auf der Uhr in `/Squirrel` in ihrem internen Flash. Eine neue Version zu flashen behält sie.

Nichts verlässt dein Gerät - außer über die Bluetooth-Synchronisation mit deinen eigenen gekoppelten Geräten, und WLAN
nur für die Uhrzeit.

## Aktualisieren

```bash
cd Squirrel
git pull
cd "Squirrel!"
python3 build_firmware.py --flash /dev/ttyACM0          # (--port twatch2020_v3 for the watch)
```

Eine bestimmte Version: `git checkout 2.0` (Versionen sind Git-Tags), dann bauen wie oben.

## Wenn etwas nicht klappt

| Problem | Was tun |
|---|---|
| `port not found`, der Port ist belegt | Schließe Thonny; prüfe `ls /dev/serial/by-id/`; unter Linux braucht es vielleicht `sudo usermod -aG dialout $USER` (und neu anmelden). |
| Der Cardputer lässt sich nicht flashen | Halte G0 beim Einstecken des Kabels (oben). |
| Schwarzer Bildschirm nach dem Flashen | Kabel ab- und wieder anstecken; prüfen, ob es Daten überträgt. |
| Die App startet nicht | `python3 build_firmware.py --setup-device PORT` bereitet das Gerät neu vor; in Thonny: `import sq_info; sq_info.report()`. |
| Notizen werden nicht gespeichert (Cardputer) | Steckt die microSD-Karte, ist sie FAT32-formatiert? |
| Er startet ab und zu von selbst neu | Ein Watchdog startet ein hängendes Gerät nach einer Minute neu; deine Daten bleiben. Wenn es oft passiert, melde es bitte. |

Mehr für alle, die Squirrel! bauen und ändern: [die Implementierungsdokumente](../../implementation/de/).
