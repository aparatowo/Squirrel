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

### F. Der Leichtschlaf ist auf dem Cardputer ADV ausgeschaltet (zu lösen)

Seit 2026-10-22 hat der Port `cardputer_adv` in seiner `port.toml` `[power_mgmt] light_sleep = false`: der *Schlafmodus*
ist aus den Einstellungen verschwunden, und `hw/power.py` schläft nicht, selbst mit `POWER_SLEEP = light` in
`config.txt`. Der Code des Leichtschlafs bleibt (der erste Cardputer und die Uhr nutzen ihn). Was der Cardputer ADV mit
ihm tat:

- **die Hintergrundbeleuchtung** - statt beim Dimmen dunkel zu werden, wurde sie heller und blitzte bei jedem
  Schlafzyklus (~0,8 s): die PWM der Beleuchtung steht im Leichtschlaf, ihr Pin bleibt in einem zufälligen Zustand;
- **G0** - im Schlaf und kurz danach als gedrückt gelesen (gemessen: 500 von 500 Lesungen low, IO-MUX-Register richtig,
  3,3 V nur am Akku bei ausgeschaltetem Schlaf): das Schnell-Diktiergerät startete von selbst (`[BTN0] quick recorder
  from ClockScreen, dimmed (pin 0)` im Log), daher auch der blitzende Bildschirm; im Schlaf tat G0 gar nichts;
- **der Lautsprecher** - nach dem ersten Ton ein Ticken bei jedem Einschlafen und Aufwachen; `Speaker.end()` vor dem
  Schlaf dämpft es auf das, was man am Ohr hört, den ES8311 per Register auszuschalten macht ihn still, aber der
  Lautsprecher kommt erst nach einer Stromunterbrechung zurück;
- **USB** - die Konsole antwortet im Schlaf nicht, und nach einer Reihe von Schlafzyklen wird USB bis zu einem Reset
  nicht mehr erkannt;
- mit G0 als Weckquelle (ext0) ging sein Pad zum RTC und verlor den Pull-up (schon geändert: die Tastatur, G11, weckt).

Zu versuchen: die Pin-Konfiguration für den Schlaf (`gpio_sleep_sel` / Schlaf-Pulls für G0 und den Beleuchtungs-Pin,
`gpio_hold` der Beleuchtung auf 0), den ES8311 nach dem Aufwachen neu initialisieren, `esp_sleep_pd_config` für die
Versorgungsdomänen. Werkzeuge: die Zeilen `[POWER] light sleep` und `[BTN0]` in `boot_log.txt`.

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
- **Der erste Cardputer** (`ports/cardputer`): lässt sich bauen, noch nicht auf einem Gerät ausprobiert. Zuerst zu
  prüfen: die Pins des Grove-Ports (G2 = SDA, G1 = SCL), die LED an G21 und ihre Versorgung, jede Taste
  (Einstellungen → Tastenkalibrierung zeigt die Codes), das Aufwachen aus dem leichten Schlaf, Ton und Aufnahme über
  M5.Speaker / M5.Mic.
- **Der DS3231** (`drivers/ds3231.py`): an einem nachgebildeten Bus getestet (`tools/tests/test_cardputer_hw.py`),
  noch nicht an einem Modul. Das Uhrmodul wird in den Einstellungen gewählt (`RTC_CHIP`, standardmäßig aus).
- **Die LED braucht einen hellen Bildschirm** (Cardputer ADV, gemessen am 2026-10-20 mit
  `tools/hwtest/cardputer_hw.py t09_screen_off`): sie bekommt Strom über den Schalter der Hintergrundbeleuchtung, bleibt
  also bei ausgeschaltetem Bildschirm dunkel, und ein schwaches Signal (Laden, schwacher Akku) würde den Bildschirm
  mit einschalten. Verworfen: Laden ist ein Zeichen neben dem Akkubalken, ein schwacher Akku eine Benachrichtigung mit
  einem normalen LED-Signal.
- **Die Ladeerkennung** (Cardputer, experimentell): die Schwellen von ChargeGuess in `hw/battery.py` stammen aus dem
  üblichen Verhalten einer Li-Ion-Zelle, nicht aus Messungen - mit `cardputer_hw.py t06_charging` und dem Akku-Log
  prüfen.
- **Das Laden der Uhr**: als nicht funktionierend gemeldet; die Bits des AXP202 werden jetzt zusammen mit der
  USB-Anwesenheit gelesen - mit `tools/hwtest/twatch_hw.py t14_charging` prüfen.
- **Module, die der Nutzer einschaltet** (standardmäßig eine einfache Version, *Einstellungen → Funktionen*): ein
  Vorschlag mit Analyse, [modules-proposal.md](../en/modules-proposal.md) (auf Englisch).
- **Das Erfolgstagebuch über Bluetooth**: seine Tage (`wins/`) bleiben auf dem Cardputer; die Uhr zeigt sie nicht, die
  Erfolge sind noch nicht in der synchronisierten Statistik.
- **Lautsprecher und Mikrofon der Uhr, der Beschleunigungssensor**: die T-Watch hat einen Lautsprecher (I2S, über
  LDO4 versorgt), aber die Signale - das Metronom (Piep / Klick), Benachrichtigungen, die Sanduhr - vibrieren auf der
  Uhr bisher nur; der Beschleunigungssensor wird nur beim Start ausgeschaltet.
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
