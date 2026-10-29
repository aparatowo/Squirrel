# Funktionen

*[English](../en/features.md) · [Polski](../pl/features.md) · [Français](../fr/features.md) · Deutsch*

Was Squirrel! tut, Bildschirm für Bildschirm. Version 2.0. Die Tasten und Gesten für all das:
[Tastenkürzel](shortcuts.md). Bilder: der Cardputer links, die Uhr rechts (wo sie diesen Bildschirm hat).

---

## 🕐 Die Uhr

Der Startbildschirm ist eine Uhr: große Ziffern, das Datum und eine eigene Zeile unten (*no need to go nuts* auf dem
Cardputer, *Squirrel! is watching* auf der Uhr - in Anpassen änderbar, oder lass sie so). Die Balken aus `#` rundherum
zeigen auf einen Blick, wie die Zeit vergeht:

- **links** - der Akku; **rechts** - die heutige Fokuszeit im Verhältnis zu deinem Ziel, sie steigt von unten
  (*Fokusleiste von: oben* füllt sie wie früher von oben);
- **oben** - die laufende Stunde, von links; läuft die [Sanduhr](#-sanduhr), stattdessen ihre Zeit (das vorderste
  farbige `#` blinkt);
- **unten** - die Viertelstunde, von rechts; sie beginnt um :00, :15, :30 und :45 von vorn.

Jeder kann ein voller, fester Balken sein oder ausgeschaltet werden (*Anpassen → Balken*). Die Uhr zeigt außerdem den
Wochentag und, in Worten, die Fokuszeit und den Akku - jedes in der Farbe seines Balkens.

Von 10:00 bis 19:59 beginnt die Zeit mit einer „1“, die nur rechts gezeichnet wird; die Uhr rückt dann 10 Pixel nach
links (auf der Uhr 16), damit sie mittig wirkt (*Anpassen → Anzeige → Uhr 1x:xx X*; 0 schaltet es ab).

<img src="../../../shots/cardputer/de/clock.png" width="360"> <img src="../../../shots/twatch/de/clock.png" width="240">

Von der Uhr aus: jede Taste öffnet das Menü, **OPT** startet oder pausiert den Fokus-Timer, **Aa** synchronisiert
deine Geräte, **TAB** öffnet ein kleines Menü mit dem, was du am häufigsten brauchst:

<img src="../../../shots/cardputer/de/tab-menu.png" width="360">

Auf der Uhr: **doppelt tippen** startet den Fokus-Timer, **dreifach tippen** pausiert ihn, einmal tippen öffnet das Menü - alles auf einem hellen Bildschirm (Tippen auf einen dunklen weckt ihn nur).

Die Zeit kommt von einer Hardware-Uhr, wenn es eine gibt (der PCF8563 der Uhr; am Cardputer ein optionales Uhrmodul -
ein DS3231 am Grove-Port oder ein DS1302 an der EXT-Leiste des ADV -, sobald du in *Einstellungen → Zeit und Datum →
Zeiteinstellungen → Uhrmodul* sagst, welches; bis dahin wird sein Code nicht einmal geladen), beim Start aus dem WLAN
oder per Bluetooth von einem anderen Squirrel!-Gerät (*Einstellungen → Zeit und Datum → Zeit von einem Gerät*).

## ✅ Aufgaben und Checklisten

Eine Liste von Dingen, die dich nicht verurteilt. Eine Aufgabe ist ein Titel und, wenn du willst, mehr Text. **OPT**
markiert sie als erledigt (auf der Uhr: gedrückt halten). Erledigte Aufgaben bleiben eine Woche (`TODO_KEEP_DAYS`),
dann verschwinden sie von selbst.

<img src="../../../shots/cardputer/de/todo-list.png" width="360"> <img src="../../../shots/twatch/de/menu_todo.png" width="240">

**Checklisten.** Zeilen, die mit `>` beginnen, sind Punkte zum Abhaken - eine Einkaufsliste, die Schritte einer
Aufgabe:

```
Einkauf am Samstag
> Milch
> Brot
> Nüsse
Tasche nicht vergessen
```

So eine Aufgabe öffnet sich als Checkliste; die Liste zeigt den Fortschritt (`[1/3]`); wenn alle Punkte abgehakt sind,
ist die ganze Aufgabe erledigt. Der Text der Datei ändert sich nie - die Haken werden getrennt gespeichert.

<img src="../../../shots/cardputer/de/checklist-ticked.png" width="360"> <img src="../../../shots/twatch/de/checklist.png" width="240">

Aufgaben schreibt man auf dem Cardputer (er hat die Tastatur); auf der Uhr liest du sie und hakst sie ab.

## 📋 Textnotizen

Ein Platz für Dinge, die sofort aus dem Kopf müssen: ein Titel (die erste Zeile) und der Text, sofort auf der SD-Karte
gespeichert als einfache `.txt`-Dateien, lesbar auf jedem Computer. **CTRL+S** speichert, **ESC** verwirft die
Änderungen.

<img src="../../../shots/cardputer/de/editor.png" width="360"> <img src="../../../shots/cardputer/de/note-viewer.png" width="360">

Löschen verlangt dreimal DEL - ein ausgerutschter Finger kann keine Notiz verlieren.

<img src="../../../shots/cardputer/de/delete-confirm.png" width="360">

## 🏆 Erfolgstagebuch

Eine Liste pro Tag mit dem, was gelungen ist - auch Kleines zählt. *Notizen → Erfolgstagebuch → + [Heute]* öffnet die
heutige Liste mit einer neuen Zeile: jede Zeile, die mit `-` oder `>` beginnt, ist eine erledigte Sache (wie in der
Checkliste einer Aufgabe); andere Zeilen sind einfacher Text. Die Zahl der erledigten Dinge geht in die Statistik,
getrennt von der Fokuszeit.

<img src="../../../shots/cardputer/de/success-journal.png" width="360">

## 🧠 Gedankenablage

Für den Gedanken, der immer wieder kreist. TAB, dann M auf der Uhr: schreib ihn auf (bis zu 200 Zeichen - genug, um
ihn festzuhalten, zu wenig, um sich darin zu verlieren), ENTER, und du bist zurück, wo du warst. Die Gedanken haben
ihre eigene Liste (*Notizen → Gedankenablage*); bearbeite einen dort, und er wird zu einer richtigen Notiz.

<img src="../../../shots/cardputer/de/mind-dump.png" width="360">

## 🎙️ Sprachnotizen

Wenn Tippen zu langsam ist: **G0** auf der Uhr oder in einem Menü startet sofort die Aufnahme, G0 noch einmal
speichert sie. Die Aufnahmen sind `.wav`-Dateien auf der SD-Karte; abspielen in *Notizen → Sprachnotizen* (Pause,
10 s zurück / vor, Lautstärke).

<img src="../../../shots/cardputer/de/recorder.png" width="360"> <img src="../../../shots/cardputer/de/voice-notes.png" width="360">

## 🔄 Routinen

Wiederkehrende Erinnerungen: ein Text, eine Uhrzeit, die Wochentage. Wenn es so weit ist, sagt es der Bildschirm -
**OPT**: erledigt (zählt in der Statistik), **DEL**: überspringen. 30 Sekunden keine Antwort: sie kommt nach einer
Pause wieder (`ROUTINE_SNOOZE_MIN`). Eine zu verpassen ändert nichts - kein Rot, keine verlorene Serie; das nächste
Mal kommt einfach.

<img src="../../../shots/cardputer/de/routines.png" width="360"> <img src="../../../shots/cardputer/de/routine-due.png" width="360">

Mit synchronisierten Geräten hat eine Routine ein Feld *Geräte*: sie erscheint nur auf denen, die du anhakst (die
Vitamine auf der Uhr, die Blumen am Cardputer). Auf der Uhr schaltet man Routinen mit einem Tippen ein und aus;
geschrieben werden sie auf dem Cardputer.

## 🦅 Kuckucksuhr

Ein leises Signal zu jeder vollen Stunde - und, wenn du willst, ein sanfteres Ticken jede Viertelstunde. Kein Wecker:
ein Tippen auf die Schulter, *die Zeit vergeht*. Er läuft auch bei ausgeschaltetem Bildschirm. Ton, Summer, LED oder
Vibration, wie du es einstellst; der Ruhemodus lässt ihn nachts schweigen.

## 🍅 Pomodoro und Training

Einen Block arbeiten, ausruhen, wiederholen: Pomodoro zeigt den Block (*Arbeit*, *Pause*, *Lange Pause*), die
Restzeit und die Reihe der kommenden Blöcke. Es läuft im Hintergrund - verlass den Bildschirm, und es zählt weiter;
die Fokuszeit geht in die Statistik. *Training* ist derselbe Timer mit Blöcken, die du selbst zusammenstellst
(vorbereiten, leicht, normal, hart, Ruhe).

<img src="../../../shots/cardputer/de/pomodoro-running.png" width="360"> <img src="../../../shots/twatch/de/pomodoro_running.png" width="240">

## ⏳ Sanduhr

Ein einfacher Countdown: Minuten einstellen, starten, weitermachen. Der obere Balken der Uhr füllt sich, während die
Zeit abläuft; am Ende klingelt sie - Ton, LED und Summer oder Vibration, alle paar Sekunden, bis du antwortest - auch
in der Ruhezeit, denn du hast sie selbst gestellt. Sie läuft im Hintergrund wie Pomodoro und merkt sich die Minuten
für das nächste Mal.

<img src="../../../shots/cardputer/de/hourglass-running.png" width="360"> <img src="../../../shots/cardputer/de/clock-hourglass.png" width="360">

## 🥁 Metronom und 🫁 Atmung

Das Metronom schlägt von jeder 1/8 s bis zu alle 2 Minuten - etwas Gleichmäßiges zum Folgen, im Hintergrund - mit einem kurzen Piep oder einem trockenen
Klicken wie bei einer Uhr (*Anpassen → Audio → Metronom-Klang*). Die
Atmung führt dich durch *Box 4-4-4-4*, *Entspannung 4-7-8* oder *Ruhe 5-5*: ein Kreis wächst beim Einatmen und
schrumpft beim Ausatmen (die LED folgt ihm, wenn du eine hast).

<img src="../../../shots/cardputer/de/metronome.png" width="360"> <img src="../../../shots/cardputer/de/breathing.png" width="360">

## 📊 Statistik

Die heutige Fokuszeit im Verhältnis zu deinem Ziel und die letzten 7 Tage. Keine Ziele zum Verfehlen, keine
Vergleiche - ein ruhiges Bild deiner Tage. Mit synchronisierten Geräten: LEFT / RIGHT zeigt dieses Gerät, jedes
synchronisierte oder alle zusammen.

Eine Ablenkung als Fokus gezählt? **-** zieht die letzten 15 Minuten ab (*Anpassen → Fokus → Minuten abziehen*);
zweimal DEL setzt heute auf null. Unter der heutigen Zeit: was heute und in dieser Woche gelungen ist, aus dem
Erfolgstagebuch.

<img src="../../../shots/cardputer/de/statistics.png" width="360"> <img src="../../../shots/twatch/de/focus_stats.png" width="240">

## 🔗 Bluetooth-Synchronisation

Der Cardputer und die Uhr halten sich gegenseitig auf dem Laufenden: Routinen, Aufgaben, Notizen und Einstellungen
gehen zur Uhr; Haken, das Routinen-Protokoll und die Statistik kommen zurück. **Aa** auf der Uhr des Cardputers
synchronisiert sofort; oder lass sie es selbst tun, von alle 15 Minuten bis alle 4 Stunden. Alles darüber:
[Bluetooth-Synchronisation](bluetooth.md).

<img src="../../../shots/cardputer/de/bluetooth.png" width="360"> <img src="../../../shots/twatch/de/ble_sync.png" width="240">

## 🔕 Ruhemodus

Stunden und Tage, an denen Ton, Summer oder LED schweigen - jedes für sich (*Einstellungen → Ruhemodus*). Eine Nacht
zählt zu dem Tag, an dem sie beginnt.

<img src="../../../shots/cardputer/de/silent-mode.png" width="360"> <img src="../../../shots/twatch/de/silent_sound.png" width="240">

## 🎨 Anpassen und Sprachen

Farben, der Text unter der Uhr, die Pomodoro- und Fokuszeiten, die Signale, der Schlaf - alles in *Einstellungen →
Anpassen*, jedes mit einer Hilfezeile, und alles in `config.txt` auf dem Gerät gespeichert (eine einfache Textdatei,
die du auch bearbeiten kannst).

Die Bildschirme sprechen **Englisch, Polnisch, Französisch oder Deutsch** (*Anpassen → Anzeige → Sprache*); jede
Sprache außer Englisch schaltet die Schrift mit den Umlauten und Akzenten ein. Einen Text, den du anders sagen
würdest, änderst du auf dem Gerät, ohne neue Firmware:
[Squirrel!/translations/README.md](../../../Squirrel!/translations/README.md).

<img src="../../../shots/cardputer/de/personalize.png" width="360"> <img src="../../../shots/cardputer/de/personalize-language.png" width="360">

## 🔋 Energie

Der Bildschirm wird nach einer Weile ohne Taste dunkler; mit dem *Schlafmodus* schläft das Gerät, solange er gedimmt
ist (die Uhr schläft tief und wacht für ihre Routinen, den Kuckuck und ihre Sync-Zeiten auf). Die Funkmodule sind nur
an, solange sie arbeiten: WLAN für die Uhrzeit beim Start, Bluetooth für eine Synchronisation. Der Cardputer ADV hat vorerst keinen Schlafmodus: im Leichtschlaf
blitzte die Beleuchtung und G0 startete das Diktiergerät von selbst (zu lösen); das Sparen bei gedimmtem Bildschirm
bleibt. Auf dem ersten Cardputer ist der Schlafmodus experimentell (*Einstellungen → Experimentell → Einstellungen*).

**Ein schwacher Akku** wird bei 15 %, 10 %, 5 % und kurz vor dem Ende gemeldet - auf dem Bildschirm, mit Ton und Summer
oder Vibration, wenn du willst (*Anpassen → Energie → Akku-Warnungen*, *Warnton*; *Summer → Akku schwach*). Die LED kann mit der Warnung blinken (*Anpassen → LED → Akku: Blinken*). Beim Laden
zeigt sich ein kleiner Blitz neben dem Akkubalken der Uhr (*Anpassen → Balken → Ladezeichen*).

**Laden.** Der Power-Chip der Uhr sagt, wann sie lädt (oder voll am USB hängt). Die Cardputer wissen es nicht: ihr Akku
wird nur gemessen. *Einstellungen → Experimentell → Einstellungen → Ladeerkennung* lässt sie es erraten - aus der Akkuspannung (sie
springt, wenn ein Ladegerät kommt oder geht, und steigt langsam, während der Akku voll wird) und einem Computer am USB.
Ein einfaches Ladegerät ohne Datenleitungen lässt sich anders nicht erkennen. Experimentell: sag uns, wie gut es rät.
