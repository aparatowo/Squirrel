# Backlog

*[English](../en/backlog.md) · [Polski](../pl/backlog.md) · [Français](../fr/backlog.md) · Deutsch*

Was bekanntermaßen nicht stimmt, was noch nicht gebaut ist, und was geplant war und dann anders umgesetzt wurde. Stand
der Version 2.0. Nutzer sehen den ersten Teil als die bekannten Einschränkungen in den
[Versionshinweisen](../../releases/README.md).

## Bekannte Probleme

### A. Die Verschlüsselung der Verbindung ist ausgeschaltet

Die Bluetooth-Datensätze gehen im Klartext durch die Luft; nur das Koppeln mit einem Code in der App schützt sie vor
Änderungen (siehe [bluetooth.md](bluetooth.md) §6). LE Secure Connections ist im Code (`nuts.BLE_LINK_PAIRING = False`,
`ble/secrets.py`, `firmware_patches/0001-nimble-central-passkey.patch`) und hat auf den Geräten funktioniert, aber der
Cardputer startete in manchen Sitzungen neu.

Die Neustarts erwiesen sich als ein anderer Fehler (2026-10-13): der IRQ-Handler des Chefs reihte `tuple(data)` ein,
und in MicroPython gibt `tuple()` eines Tupels **dasselbe Objekt** zurück - das Tupel des IRQ auf dem Stack der
NimBLE-Task, vom Funk überschrieben, bevor `tick()` es las. Behoben (`tuple(list(data))`); seitdem 55
Synchronisationen ohne Neustart. Mit Verschlüsselung der Verbindung nach der Korrektur: 5 von 5 Synchronisationen,
dann ein Hängen in der sechsten (keine Panik, USB nahm keine Daten mehr an).

Weiter: eine Serie mit `tools/hwtest/ble_e2e.py --link`, das Hängen erklären, dann `BLE_LINK_PAIRING = True` (das
Koppeln in der App bleibt, als Beweis, dass es dein Chef ist; die Verschlüsselung schließt das Abhören und das
Offline-Knacken des Codes). Dabei prüfen, ob `radio_gc` (keine automatische Speicherbereinigung während einer Sitzung)
noch nötig ist.

### B. Ein seltenes Hängen des Cardputers

Etwa einmal in 70 Synchronisationen (2026-10-13): `mp_task` wartete in
`spi_flash_disable_interrupts_caches_and_other_cpu` (ein gewöhnliches Lesen aus dem Flash) auf Kern 0, der Interrupts
bediente, aber keine Tasks. Die Ursache ist unbekannt; der Bluetooth-Controller läuft auf Kern 0.

Abhilfe: der Watchdog der Hauptschleife (`nuts.WATCHDOG_S`, 60 s) startet das Gerät neu; die Daten bleiben. Die
Firmware hält dann fest, was Kern 0 tat (`firmware_patches/0002-panic-record.patch`); beim nächsten Mal mit
`tools/hwtest/panic_record.py` auslesen und nach der Ursache suchen.

### C. "keine Antwort" direkt nach dem Verbinden

Manchmal bekommt der Chef keine Antwort auf die Dienstsuche (einmal 7 von 30, einmal 0 von 25). Die Meldung sagt,
auf welche Ereignisse er gewartet hat. Abhilfe: der zweite Durchgang einer Synchronisation versucht die
fehlgeschlagenen Geräte erneut.

### D. Die Screenshots des Cardputers nutzen die Schrift der Uhr

`tools/sim/render_shots.py` zeichnet Text mit der 6 × 8-Schrift aus `drivers/glcdfont.py` (+ `glcdfont_latin.py`),
während ein Cardputer in einer anderen Sprache als Englisch `squirrel.vlw` benutzt. Die Bilder in den Anleitungen
stimmen in Layout und Worten, unterscheiden sich etwas in der Form der Buchstaben. Abhilfe: `.vlw`-Glyphen in
`render_shots.py` zeichnen (`vlw.py` kann sie lesen).

### E. Ein Knoten hält einen Kopplungsschlüssel

`ble/peripheral.py` hält einen Schlüssel pro Knoten (`"head"` in `ble_auth.json`): die Webseite mit der Uhr zu koppeln
ersetzt den Schlüssel des Cardputers, und der Cardputer verlangt bei der nächsten Synchronisation einen neuen Code (und
umgekehrt). Für Nutzer beschrieben; eine Korrektur würde ein paar Schlüssel halten und den Beweis jedes davon annehmen -
ohne Änderung in der Luft oder an der Seite.

## Noch nicht gebaut

- **Änderungen auf einem Knoten** (ein Handy, das mit der Uhr verbunden ist): als Vorschläge mit der Version
  gespeichert, auf der sie gemacht wurden; der Chef entscheidet bei der nächsten Synchronisation. Ein `SYNC_MODE`
  *auto* / *ask* mit einem Bildschirm der Unterschiede (senden / nehmen / überspringen je Kategorie). Satz `0x0B` ist
  reserviert ([bluetooth.md](bluetooth.md) §10).
- **Ein neuer Chef**: eine vollständige Kopie der Datensätze von einem beliebigen Knoten übernehmen, mit IDs und
  Zählern, und die Knoten neu koppeln.
- **Die Web-Bluetooth-Seite** (`Squirrel!/tools/web/`): ihr Codec ist auf dem PC gegen `protocol.py` geprüft; mit der
  Uhr (Chrome, die Seite von der Festplatte geöffnet) funktionieren Verbinden, Koppeln und Lesen
  (`tools/hwtest/web_e2e.py`); Bearbeiten von der Seite aus ist noch nicht ausprobiert. Veröffentlichen auf GitHub
  Pages für Handys: `.github/workflows/web-page.yml`, bereit, nicht eingeschaltet.
- **Die allgemeine ESP32-S3-Uhr** (`ports/generic_s3_watch`): lässt sich bauen, noch nicht auf einer Uhr ausprobiert.
- **Ton und Mikrofon der Uhr, der Beschleunigungssensor** (wird weiter nur beim Start ausgeschaltet).
- **Ideen aus der Planung:**
  - der Filter *Heute* in der Aufgabenliste;
  - Gefühls-Tags an einem Eintrag (🔥 dringend, 💡 Idee, 😰 Stress, 🕑 irgendwann);
  - eine Fokusansicht mit einer einzigen Aufgabe (*Was ich gerade mache*: eine Aufgabe, groß);
  - automatische Zeitstempel an Notizen;
  - nach einem Neustart zur zuletzt geöffneten Notiz zurück;
  - ein USB-Laufwerk-Modus (die SD-Karte vom Computer aus gesehen);
  - ein Ultra-Sparmodus.

## Anders umgesetzt

| Geplant | Wie es umgesetzt ist |
|---|---|
| Quick Capture (FN+SPACE von der Uhr) | das TAB-Menü auf der Uhr: **TAB, M** - Gedankenablage, **TAB, T / N** - eine Aufgabe / eine Notiz; **G0** nimmt sofort eine Sprachnotiz auf |
| Ein Mikro-Webserver auf der Uhr, für Routinen vom Handy | die Web-Bluetooth-Seite: kein WLAN-Server, sie spricht direkt mit den Geräten |
| Ein Port auf programmierbare Smartwatches | der Port für die T-Watch 2020 V3 (2.0), der experimentelle allgemeine ESP32-S3-Port |
| Zusammenarbeit mit dem Cardputer | die Bluetooth-Synchronisation (2.0) |
