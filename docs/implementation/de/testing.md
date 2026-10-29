# Testen

*[English](../en/testing.md) · [Polski](../pl/testing.md) · [Français](../fr/testing.md) · Deutsch*

Drei Ebenen: Tests auf dem PC (ohne Gerät), die ganze App in einem Simulator (ohne Gerät), und Skripte, die über USB
auf den Geräten laufen. Starte alles aus `Squirrel!/`.

## 1. Tests auf dem PC

```bash
for t in tools/tests/test_*.py; do python3 "$t" || echo "FAILED: $t"; done
python3 -m unittest tools/tests/test_i18n.py         # (any of them also runs this way)
```

| Test | Was er abdeckt |
|---|---|
| `test_ble_protocol.py`, `test_ble_merge.py` | die Codecs der Bluetooth-Datensätze, die Rahmen und die Regeln "wer hat recht" |
| `test_ble_node.py`, `test_ble_head.py` | eine ganze Synchronisation Chef ↔ Knoten über den nachgebildeten Funk (`tools/sim/fakes/bluetooth.py` verbindet zwei Funkmodule "durch die Luft"), mit Koppeln |
| `test_ble_auto.py` | die automatische Synchronisation: Zeitfenster nach der Uhr, der Knoten als Alarmquelle, Überspringen bei belegtem Funk |
| `test_web_protocol.py` | der JavaScript-Codec der Web-Bluetooth-Seite ergibt dieselben Bytes wie `ble/protocol.py` (braucht `node`) |
| `test_checklist.py`, `test_routines.py` | Checklisten (`>`-Zeilen, Haken getrennt gespeichert), Routinen und ihre Tage |
| `test_cardputer_hw.py`, `test_hourglass_bars.py`, `test_battery.py`, `test_focus_wins.py` | die Tastenmatrix des ersten Cardputers und der DS3231 an Nachbildungen; die Sanduhr und die Zeitbalken der Uhr; `test_battery.py`: das aus der Spannung erratene Laden, die Akku-Warnungen, das Leuchten der LED; `test_focus_wins.py`: abgezogene Fokuszeit, das Erfolgstagebuch, doppeltes / dreifaches Tippen auf der Uhr |
| `test_appconfig.py` | `config.txt`: lesen, schreiben, Kommentare, Standardwerte, die eine neuere Version geändert hat |
| `test_i18n.py` | Suche, Rückfall auf Englisch, Vorlagen (`fill`), die eigene `lang_<code>.tsv` des Nutzers |
| `test_st7789_strips.py` | das in Streifen gezeichnete Display ergibt dasselbe Bild wie der volle Framebuffer (nur MicroPython: `framebuf`, viper - unter CPython übersprungen) |

Dazu `python3 tools/i18n/check.py` (jeder Text übersetzt, dieselben Platzhalter, Beschriftungen kurz genug) und
`python3 build_firmware.py --stage-only --port <port>` für jeden Port (Importe, Kompilierung).

## 2. Der Simulator

`tools/sim/` lässt die ganze App auf dem PC unter dem **Unix-Port von MicroPython** laufen (demselben MicroPython wie
die Firmware), mit Nachbildungen von `M5`, `machine`, `esp32`, `network`, `bluetooth` ..., einer Uhr, die nur läuft,
wenn der Code schläft, und `/sd` und `/flash` des Geräts in einem Ordner. Den Unix-Port einmal bauen:
[tools/sim/README.md](../../../Squirrel!/tools/sim/README.md).

- **Zwei Versionen vergleichen:** eine Umstrukturierung, die das Verhalten nicht ändert, ergibt eine identische Spur -
  jeden Display-Aufruf, jede Protokollzeile, jede geschriebene Datei:

  ```bash
  mkdir -p /tmp/base && git archive HEAD "Squirrel!" | tar -x -C /tmp/base
  tools/sim/compare.sh <micropython> "/tmp/base/Squirrel!" "$PWD" /tmp/simwork      # IDENTICAL / DIFFERENT
  ```

- **Jeder Bildschirm, in die Tiefe** (nach einer Änderung der Oberfläche oder einer Übersetzung): `crawl_scenario.py`
  öffnet jeden Menüeintrag, jeden Bildschirm mit ein paar Tasten, jede Einstellung von Anpassen, jedes Listenelement und
  die Benachrichtigungen; mit `SQUIRREL_SIM_TOUCH=1` dieselbe App wie auf einem 240 x 240-Touchscreen, jeder Knopf getippt
  (Rendern mit `--height 240`). `check_trace.py` listet Text außerhalb des Bildschirms und Englisch in einer anderen
  Sprache:

  ```bash
  SQUIRREL_SIM_SCENARIO=tools/sim/crawl_scenario.py <micropython> -X heapsize=16M tools/sim/run_sim.py "$PWD" /tmp/c /tmp/c.txt
  python3 tools/sim/check_trace.py /tmp/c.txt --lang de                        # OFF / ENGLISH / ERROR findings
  python3 tools/sim/render_shots.py /tmp/c.txt /tmp/c-shots                    # the pictures, named by place
  ```

- **Screenshots des Cardputers** für die Anleitungen: ein Szenario mit 34 Zuständen, mit Beispielinhalt in der Sprache
  der `config.txt` des Arbeitsordners (`LANGUAGE=de` ...), umgewandelt in PNG-Dateien:

  ```bash
  mkdir -p /tmp/w/sd/Squirrel /tmp/w/flash/fonts && cp squirrel.vlw /tmp/w/flash/fonts/
  echo "LANGUAGE=de" > /tmp/w/sd/Squirrel/config.txt
  SQUIRREL_SIM_SCENARIO=tools/sim/shots_scenario.py <micropython> -X heapsize=8M tools/sim/run_sim.py "$PWD" /tmp/w /tmp/trace.txt
  python3 tools/sim/render_shots.py /tmp/trace.txt ../shots/cardputer/de
  ```

  Die Schrift in `/flash/fonts/` zählt: ohne sie zeigt die App Umlaute und Akzente als einfache Buchstaben. Die Bilder
  werden mit der 6 × 8-Schrift der Uhren gezeichnet, nicht mit der `.vlw` des Cardputers ([Backlog](backlog.md) D).

## 3. Auf den Geräten

Schließe zuerst Thonny (es belegt den Port). `ls /dev/serial/by-id/` nennt die Ports.

| Werkzeug | Was es tut |
|---|---|
| `tools/hwtest/run.py PORT SCRIPT [TEST ...]` | startet ein Hardware-Testskript über den REPL und zeigt seine Ergebnisse live: `RESULT\|test\|PASS / FAIL / INFO / ASK / SKIP\|details` (ASK: bestätige, was du gesehen, gehört oder gespürt hast); ein Protokoll in `.build/hwtest/`. `PORT` kann `auto` sein. Ein Skript läuft nur auf dem Gerät, das in seiner ersten Zeile steht (`# EXPECT_MACHINE: ...`) |
| `twatch_hw.py`, `twatch_accel.py`, `cardputer_accel.py`, `cardputer_hw.py` | die Skripte: die Chips der Uhr nacheinander (PMU, Display, Touch, Uhr, Vibration), die Beschleunigungssensoren; `cardputer_hw.py`: der DS3231 am Grove-Port (beide Cardputer), Tasten und LED des ersten Cardputers |
| `twatch_gfx_bench.py` | die Zeichengeschwindigkeit des Display-Treibers der Uhr |
| `tools/hwtest/twatch_phase0.sh PORT` | vor dem ersten Flashen einer Uhr: Chip- und Flash-ID, eine volle 16-MB-Kopie des Flashs mit ihrer MD5 (stellt die Werkssoftware wieder her) |
| `tools/hwtest/twatch_screens.py PORT --lang de` | Screenshots der Bildschirme der Uhr, aus ihrem Framebuffer nach `shots/twatch/<lang>/` gelesen (es schreibt eine Beispiel-Checkliste und löscht sie wieder) |
| `tools/hwtest/ble_e2e.py WATCH CARDPUTER` | eine Bluetooth-Synchronisation von Anfang bis Ende über die Bildschirme beider Apps; `--link` mit Verschlüsselung der Verbindung, `--mem` den Speicher jede halbe Sekunde, `--head-files` der Chef nutzt das `ble/`-Paket des PCs (als `.mpy`) statt seines eingefrorenen |
| `tools/hwtest/panic_record.py PORT` | die Ursache und der Backtrace des letzten Absturzes oder Hängens des Cardputers, aus dem RTC-Speicher (seine TinyUSB-Konsole zeigt bei einem Absturz nichts) |
| `tools/ble_pc_head.py` | der PC als Chef, um eine Uhr ohne Cardputer zu testen (braucht `bleak`) |

Auf einem laufenden Gerät: `import sq_info; sq_info.report()` (der Build, verdeckende Dateien, die Schrift), und das
Startprotokoll `/flash/boot_log.txt` (Cardputer) oder `/boot_log.txt` (Uhr).

## 4. Vor einer Version

1. Die PC-Tests, `check.py`, `--stage-only` für jeden Port.
2. `compare.sh` gegen die letzte Version, wo sich das Verhalten nicht ändern sollte.
3. Beide Geräte bauen und flashen; `ble_e2e.py` ein paar Mal; eine Synchronisation vom Bildschirm jedes Geräts.
4. Screenshots in jeder Sprache (der Cardputer aus dem Simulator, die Uhr vom Gerät), dann **sie als Nutzer
   ansehen**: passt jeder Text, ist er übersetzt, klingt er wie der Rest?
