# Ports : les appareils et en ajouter un

*[English](../en/ports.md) · [Polski](../pl/ports.md) · Français · [Deutsch](../de/ports.md)*

Squirrel! tourne sur plusieurs appareils à partir d'un seul code. Chaque appareil est un **port** : un dossier
`Squirrel!/ports/<nom>/` avec une description du matériel (`port.toml`) et un module qui assemble ce matériel pour
l'application (`board.py`). Installer sur un appareil : [guides/fr/getting-started.md](../../guides/fr/getting-started.md) ;
compiler en détail : [building.md](building.md).

## 1. Les ports

| Port (`--port`) | Appareil | Firmware de base | Image à |
|---|---|---|---|
| `cardputer_adv` (par défaut) | M5Stack Cardputer ADV (ESP32-S3, sans PSRAM) | `cardputer-adv-micropython` - UIFlow 2 avec le module `M5` | 0x0 |
| `cardputer` | *expérimental, pas encore essayé sur un appareil* : M5Stack Cardputer, le premier (ESP32-S3, sans PSRAM ; une matrice de touches derrière un 74HC138 au lieu du TCA8418) | `cardputer-adv-micropython` - UIFlow 2, carte `M5STACK_Cardputer` | 0x0 |
| `twatch2020_v3` | LilyGo T-Watch 2020 V3 (ESP32, 16 Mo de flash, 8 Mo de PSRAM) | `micropython-esp32` - MicroPython v1.25.0 simple | 0x1000 |
| `generic_s3_watch` | *expérimental, pas encore essayé sur un appareil* : les montres vendues comme "ESP32-S3 smartwatch" (ST7789, CST816, batterie sur une broche ADC) | `micropython-esp32` | 0x0 |

Ce que chaque appareil a :

| | Cardputer ADV | Cardputer | T-Watch 2020 V3 | montre S3 générique |
|---|---|---|---|---|
| entrée | clavier | clavier | tactile, un bouton | tactile, un bouton |
| écrire notes et tâches | ✅ | ✅ | - (lit et coche) | - |
| notes vocales | ✅ | ✅ | - | - |
| son / buzzer / vibration | haut-parleur, buzzer (optionnel) | haut-parleur | vibration | - |
| LED | WS2812 (optionnelle) | WS2812 | - | - |
| horloge matérielle | DS3231 ou DS1302 (optionnelle) | DS3231 (optionnelle) | PCF8563 avec alarme | - (heure par Wi-Fi ou Bluetooth) |
| sommeil profond | - | - | ✅ (se réveille pour les routines, le coucou, la synchronisation) | - |
| Bluetooth | chef | chef | nœud | nœud |
| données | carte microSD | carte microSD | flash interne | flash interne |

Les broches de la montre générique sont celles d'une carte 1,69" courante : vérifie-les toutes sur ta montre (son
schéma, ou les scans de `tools/hwtest/`) avant la première compilation - chacune est marquée `CHECK` dans son
`port.toml`.

## 2. De quoi un port est fait

```
Squirrel!/
  features.toml          hardware-dependent features: what they need, what to hide and leave out without it
  ports/<port>/
    port.toml            the device's hardware: pins, addresses, drivers, feature choices (read on the PC only)
    board.py             puts the drivers together for the app (the only module that knows which device this is)
    firmware/            MicroPython board definition and patches (micropython-esp32 recipe only)
    keymap.py ...        other files of the port
  drivers/               drivers named after the CHIP (st7789_fb, ft6336, cst816, pcf8563, ds3231, axp202 ...);
                         pins come as arguments
  hw/                    device-independent logic: touch -> gestures, battery, sleep, buzzer, LED, clock
  ui/                    touch widgets (ui/touch.py) shared by every touch screen
  port_config.py         GENERATED from port.toml and features.toml - do not edit by hand
```

**Ce qui se passe pendant une compilation :**

1. `build_firmware.py --port X` lit `ports/X/port.toml` et `features.toml`.
2. Chaque section de `port.toml` est un élément du matériel ; chaque clé à `true` en est une propriété (par ex.
   `input.touch`). Une fonction de `features.toml` est compilée quand le port a tout ce qui est dans ses `requires` et
   que le `[features]` du port ne la désactive pas.
3. `port_config.py` est écrit : chaque clé devient une constante nommée d'après son chemin (`[display] ppi = 220` →
   `DISPLAY_PPI = 220`, `[i2c.sys] sda = 21` → `I2C_SYS_SDA = 21`), plus `HARDWARE`, `FEATURES` et des listes de ce que
   l'application doit cacher (`HIDDEN_MENUS`, `HIDDEN_SCREENS`, `HIDDEN_ACTIONS`, `HIDDEN_GROUPS`, `HIDDEN_KEYS`).
4. Seuls les pilotes nommés dans `port.toml` (`driver = "..."`) vont dans le firmware, avec les modules de `drivers/`
   qu'ils importent ; les modules des fonctions que le port n'a pas, et les dossiers des autres ports, sont laissés de
   côté.
5. Une vérification des imports arrête la compilation si du code importe un module qui ne fait pas partie de cette
   compilation.

---

## 3. Un nouveau port pas à pas

Hypothèse : les pilotes des puces de l'appareil sont déjà dans `drivers/` (ou tu les écris en suivant les interfaces de
la section 5).

### Étape 1 — le dossier

`Squirrel!/ports/<nom>/` avec `__init__.py` (vide), `port.toml` et `board.py`. Le nom du dossier doit être égal à
`[port] name`.

### Étape 2 — `port.toml`

Copie le port le plus proche par le matériel et change les valeurs. Toutes les clés : section 4. Minimum requis :

```toml
[port]
name     = "my_watch"
title    = "My Watch"
mcu      = "esp32"
firmware = "micropython-esp32"
board    = "firmware"
idf      = "v5.4.2"
machine  = "My Watch"             # part of sys.implementation._machine

[display]
driver = "st7789_fb"
width  = 240
height = 240

[storage]
driver   = "flash_storage"
base_dir = "/Squirrel"
flash_root = ""
```

Confirme d'abord chaque valeur matérielle (broche, adresse, fréquence, rotation de l'écran) sur l'appareil. Les tests de
`tools/hwtest/` tournent par le REPL sur MicroPython simple, avant que Squirrel! n'entre en jeu ; voir `twatch_hw.py`.

### Étape 3 — `board.py`

Un module de fonctions que l'application appelle dans cet ordre. Il lit les valeurs de `port_config` et les passe aux
pilotes. Exemples : `ports/twatch2020_v3/board.py` (tactile, horloge avec alarme, sommeil profond),
`ports/cardputer_adv/board.py` (clavier, carte SD, module `M5`) et `ports/generic_s3_watch/board.py` (le plus petit :
tactile, batterie sur ADC, un bouton).

| Fonction | Quand | Renvoie / fait |
|---|---|---|
| `begin()` | en premier, dans `squirrel_boot.py` | met sous tension et démarre l'écran (par ex. le PMU avant le panneau) |
| `begin_buzzer(buzzer, quiet)` | la première chose dans l'application | `buzzer.begin(...)` ; sans buzzer `buzzer.begin(quiet=quiet)` |
| `make_storage()` | avant la lecture des réglages | un objet avec `mount()`, `remount()`, `is_mounted` |
| `make_input()` | | un clavier, ou `hw.touch_input.TouchInput(chip, ACTIONS, ...)` |
| `make_buttons()` | | `{role: button}` ; rôles : `"quick"` (dictaphone rapide), `"back"` (= ESC, réveille l'écran) |
| `clock_chip(choice)` | | `(factory, name)` ou `(None, None)` ; `factory()` → l'objet de l'horloge matérielle ; `choice` = le réglage `RTC_CHIP` (un module optionnel ; ignoré quand l'horloge est fixe) |
| `make_audio()` | | `hw.audio_manager.AudioManager(backend)` ; `AudioManager(None)` = pas de son |
| `power_source()` | | un objet avec `level()`, `charging()`, `millivolts()` (chacun peut renvoyer `None`) |
| `begin_led(led, battery)` | | `led.begin(battery=battery)` sans LED ; avec une LED, aussi `pin` et le pilote |
| `motion_off()` | | éteint l'accéléromètre ; renvoie son adresse I2C ou `None` |
| `i2c(name)` | | l'objet `machine.I2C` actuel du bus `name`, ou `None` |

Facultatif (l'application vérifie s'ils existent) :

| Nom | Rôle |
|---|---|
| `EARLY_CLOCK = True` | le cadran montre l'heure avant que le reste de l'application ne soit construit (plus rapide après un réveil) |
| `arm_light_sleep_wake()` | des sources de réveil de veille légère à soi (ESP32 classique : ext0/ext1), au lieu de `[power_mgmt] wake_pins` |
| `wake_reason()` | après un sommeil profond : `"alarm"`, `"button"` ou `None` — requis par la fonction `deep_sleep` |
| `deep_sleep(alarm, touch=None)` | règle l'alarme de l'horloge (`(year, month, day, hour, minute)` ou `None`), éteint l'écran et les périphériques, `machine.deepsleep()` — requis par `deep_sleep` |

Écran tactile : le dictionnaire `ACTIONS` de `board.py` transforme les gestes en actions de l'application. Sur la
montre :

```python
ACTIONS = {"tap": "ENTER", "swipe_up": "UP", "swipe_down": "DOWN", "swipe_right": "ESC", "swipe_left": "RIGHT",
           "long": "OPT"}
```

### Étape 4 — firmware

**Un appareil avec UIFlow 2 (le module `M5`)** — recette `cardputer-adv-micropython` ; `[port] board` est la carte de
base dans le dépôt du firmware.

**Tout autre ESP32 ou ESP32-S3** — recette `micropython-esp32`. `ports/<nom>/firmware/` (nommé par `[port] board`)
contient la définition de carte pour `make BOARD_DIR=...` :

| Fichier | Contenu |
|---|---|
| `mpconfigboard.cmake` | `SDKCONFIG_DEFAULTS` (par ex. `boards/sdkconfig.base`, `sdkconfig.spiram`, `sdkconfig.240mhz`, ton propre `sdkconfig.board`) et `MICROPY_FROZEN_MANIFEST` |
| `mpconfigboard.h` | `MICROPY_HW_BOARD_NAME` (source de `sys.implementation._machine`, comparé à `[port] machine`) et `MICROPY_HW_MCU_NAME` |
| `sdkconfig.board` | taille de la flash, table des partitions, démarrage plus rapide |
| `manifest.py` | `include("$(PORT_DIR)/boards/manifest.py")` et `freeze("$(BOARD_DIR)/squirrel")` |
| `patches/*.patch` | correctifs de MicroPython v1.25.0, appliqués avec `git apply` (facultatif) |

Le script copie ce dossier avec les sources dans `.build/board-<port>/` ; l'arbre `vendor/micropython` reste intact (à
part les correctifs). Après un changement de `sdkconfig*` ou de `mpconfigboard.cmake`, le script régénère `sdkconfig`
lui-même.

Une puce autre qu'ESP32 / ESP32-S3 (par ex. RP2040) demande une nouvelle recette dans `build_firmware.py`.

### Étape 5 — fonctions

Les fonctions s'activent d'elles-mêmes selon le matériel. Dans `[features]`, tu peux seulement en désactiver une
(`wifi_ntp = false`) ou l'exiger (`true`). Exiger une fonction que le matériel ne peut pas assurer arrête la
compilation avec une erreur.

| Fonction | A besoin de | Sans elle |
|---|---|---|
| `text_edit` | `input.keyboard` | pas d'éditeur pour les notes, les tâches et le vide-tête |
| `notes` | `input.keyboard` | menu des notes caché |
| `key_calibration` | `input.keyboard` | pas de calibrage des touches |
| `voice_notes` | `audio_in`, `storage.removable` | pas d'enregistrements |
| `wifi_ntp` | `radio.wifi` | heure seulement à la main ou par l'horloge matérielle |
| `hw_clock` | `clock` | pas de "Sync RTC" |
| `led` | `signal.led` | réglages et tests de la LED cachés |
| `buzzer` | `signal.buzzer` | réglages et test du buzzer cachés |
| `clock_module` | `clock.optional` | pas de choix du module d'horloge (`RTC_CHIP`) : l'horloge est fixe, ou il n'y en a pas |
| `charge_guess` | `power.voltage_only` | pas de *Détection de la charge* (charge devinée d'après la tension) |
| `deep_sleep` | `clock.alarm`, `power_mgmt.deep_sleep` | pas de mode de veille `deep` ni d'écran "Alarmes prévues" |
| `ble_sync` | `radio.ble` | pas de synchronisation Bluetooth (la partie nœud) |
| `ble_hub` | `radio.ble`, `input.keyboard` | l'appareil ne peut pas être le chef d'une synchronisation |

Une nouvelle fonction dépendant du matériel est une nouvelle section dans `features.toml` : `requires`, `modules`
(fichiers laissés hors de la compilation), `screens`, `menus`, `actions`, `settings` (groupes de réglages) et `keys`
(réglages isolés).

### Étape 6 — vérifier

```bash
python3 build_firmware.py --port my_watch --gen-port-config   # port.toml errors; port_config.py to inspect
python3 build_firmware.py --port my_watch --stage-only        # file selection, imports, mpy-cross compile
python3 build_firmware.py --gen-port-config                   # restores the Cardputer's port_config.py
python3 build_firmware.py --port my_watch --flash /dev/ttyACM0
```

Le `port_config.py` à côté des sources appartient au port par défaut (le Cardputer). Après `--gen-port-config` pour un
autre port, remets-le toujours avant de committer. Une compilation génère toujours sa propre copie et ignore celle à
côté des sources.

Premier démarrage : `/boot_log.txt` (montre) ou `/flash/boot_log.txt` (Cardputer) montre quelles parties ont démarré
(`[TOUCH]`, `[RTC]`, `[POWER]` ...). Rapport dans Thonny : `import sq_info; sq_info.report()`.

Si tu changes du code partagé, vérifie que le Cardputer se comporte toujours pareil : `tools/sim/compare.sh` compare la
trace de dessin, le journal et les fichiers de deux versions dans le simulateur (`tools/sim/README.md`).

---

## 4. `port.toml` — référence des clés

Règles :
- une section = un élément du matériel ; `installed = false` dans une section veut dire qu'il est absent (la section
  reste comme note de câblage) ;
- une clé à `true` = une propriété du matériel que les fonctions peuvent exiger (`input.touch`, `clock.alarm`) ;
- `driver = "x"` = le fichier `drivers/x.py`, qui doit exister ;
- les nombres peuvent s'écrire `0x38` et `400_000`.

La compilation vérifie : `[port]`, `[display]` avec `driver`, `width`, `height`, `[storage]` avec `base_dir`, que chaque
pilote et `board.py` existent. Les autres clés sont lues par `board.py`, leurs noms sont donc libres, mais garder ceux
ci-dessous rend les ports semblables.

### `[port]`
| Clé | Sens |
|---|---|
| `name` | le nom du dossier du port |
| `title` | nom affiché |
| `mcu` | `esp32`, `esp32s3` |
| `firmware` | recette : `micropython-esp32` ou `cardputer-adv-micropython` |
| `board` | dossier de définition de carte dans le port (`micropython-esp32`) ou la carte de base UIFlow |
| `idf` | version d'ESP-IDF (`v5.4.2`) |
| `machine` | partie de `sys.implementation._machine` ; la préparation de l'appareil refuse tout autre appareil |
| `reset_lines_low` | `true` pour un pont USB-série avec réinitialisation automatique (CH9102, CP210x) : DTR/RTS baissés à l'ouverture du REPL |

### `[display]`
| Clé | Sens |
|---|---|
| `driver` | `m5_display` (M5.Lcd) ou `st7789_fb` (tampon d'image + envoi du rectangle modifié ; voir plus bas) |
| `width`, `height` | taille du panneau en pixels |
| `layout_height` | la hauteur pour laquelle dessinent les écrans pas encore refaits (135 = la mise en page du Cardputer, centrée) |
| `ppi` | pixels par pouce ; les zones tactiles et les gestes sont dimensionnés en millimètres à partir de cela |
| `fonts` | `vlw` (polices M5) ou `bitmap` |
| `spi_id`, `sck`, `mosi`, `cs`, `dc`, `rst`, `baud`, `backlight`, `madctl`, `row_offset` | câblage et orientation du panneau (`st7789_fb`) |
| `buffer_rows` | `st7789_fb` en bandes de ce nombre de lignes (par défaut : tout le panneau s'il prend au plus un quart de la RAM libre, sinon des bandes de 40 lignes) |
| `clock_footer` | le texte par défaut sous l'horloge (jamais traduit) |

**Mode bandes.** Un tampon d'image complet, c'est 2 octets par pixel : 115 Ko pour 240 × 240. Un module sans PSRAM a
environ 160 Ko de tas pour tout, donc là `st7789_fb` ne garde pas d'image complète : il enregistre les appels de dessin
d'une image et les rejoue pour chaque bande de 40 lignes dans un tampon de 19 Ko, envoyant chaque bande quand elle est
prête. L'image est la même (`tools/tests/test_st7789_strips.py`), le dessin un peu plus lent.

### `[i2c.<nom>]`
`id`, `sda`, `scl`, `freq`. D'autres sections désignent un bus par `bus = "<nom>"`.

### `[input]`
| Clé | Sens |
|---|---|
| `driver` | `tca8418_keypad` (clavier), `hc138_keypad` (une matrice de touches sur GPIO derrière un 74HC138 : `lines`, `cols`) ou une puce tactile (`ft6336`, `cst816`) |
| `keyboard` | `true` = on peut taper du texte (fonctions `text_edit`, `notes`) |
| `touch` | `true` = écrans tactiles en pleine hauteur |
| `swap_xy`, `mirror_x`, `mirror_y` | transformation des coordonnées de la puce tactile vers l'image |
| `bus`, `addr`, `int`, `rst` | câblage |

### `[buttons.<rôle>]`
`driver` (`gpio_button`, `axp_pek`) et par ex. `pin`. Rôles : `quick`, `back`.

### `[storage]`
| Clé | Sens |
|---|---|
| `driver` | `sd_spi` ou `flash_storage` |
| `removable` | `true` = une carte (requis par `voice_notes`) |
| `base_dir` | le dossier des données de Squirrel! (`/sd/Squirrel`, `/Squirrel`) |
| `flash_root` | où la flash interne est montée : `/flash` (UIFlow), `""` (MicroPython simple) |
| `slot`, `width`, `sck`, `miso`, `mosi`, `cs`, `freq` | carte SD |

### `[clock]`
`driver` (`ds1302`, `ds3231`, `pcf8563`), `bus` ou broches, `int`, `alarm = true` si l'alarme de la puce peut
réveiller l'appareil. Une horloge en module optionnel : `optional = true` dans `[clock]` et une sous-section par puce que
l'appareil accepte, `[clock.<puce>]` avec son `driver` et son câblage (le Cardputer ADV : `[clock.ds3231]` sur le port
Grove, `[clock.ds1302]` sur le connecteur EXT). L'utilisateur dit laquelle est branchée (le réglage `RTC_CHIP`, "off"
par défaut - fonction `clock_module`), et `board.clock_chip(choice)` n'ouvre que celle-là ; aucun driver n'est importé
avant.

### `[power]`
`driver` (`m5_power`, `axp202`, `adc_battery`), `bus`, `irq` ; `adc_battery` : `pin`, `divider` ; `voltage_only = true`
quand la batterie est seulement mesurée et la charge illisible (les Cardputer : la *Détection de la charge* la devine).

### `[audio_out]`, `[audio_in]`
`driver` (`m5_audio`). Sans ces sections, pas de son ni d'enregistrement.

### `[signal.led]`, `[signal.buzzer]`
LED : `driver = "ws2812"`, `pin`, `min_backlight`, `max_sum`. Buzzer ou moteur de vibration : `driver = "pin_pulser"`,
`pin`, `pwm_freq` (0 = marche/arrêt, sinon une tonalité en Hz), `installed`.

### `[motion]`
`driver` (`bmi270`, `bma423`), `bus`, `addrs` — pour l'instant, l'accéléromètre est seulement éteint au démarrage.

### `[radio]`
`wifi = true`, `ble = true` (la synchronisation Bluetooth).

### `[power_mgmt]`
| Clé | Sens |
|---|---|
| `wake_pins` | broches qui réveillent de la veille légère (actives à l'état bas) |
| `slow_cpu_hz` | fréquence du processeur pendant que l'écran est assombri |
| `deep_sleep` | `true` = l'appareil peut vraiment dormir (avec `clock.alarm`, active la fonction `deep_sleep`) |
| `wake_button`, `wake_alarm` | broches qui réveillent du sommeil profond : le bouton et la ligne INT de l'horloge |

### `[features]`
`<fonction> = false | true` — voir l'étape 5.

---

## 5. Interfaces des pilotes

Un nouveau pilote n'a pas besoin d'hériter de quoi que ce soit ; il lui faut seulement les mêmes appels. Décrits dans
le code : `Squirrel!/hw/ports.py`.

| Partie | Appels requis |
|---|---|
| écran (`drivers/<x>.py` avec un objet `lcd`) | les appels de M5.Lcd : `fillScreen`, `fillRect`, `drawRect`, `drawLine`, `fillCircle`, `drawCircle`, `drawPixel`, `drawString`, `setTextColor`, `setTextSize`, `textWidth`, `fontHeight`, `setBrightness`, `getBrightness`, `setFont` (lève une exception sans polices) ; couleurs `0xRRGGBB`. Tampon d'image : `_needs_flush = True` et `flush()` ; pleine hauteur pour les écrans tactiles : `_can_layout = True`, `set_layout(h)`, `layout_origin()` ; avant un sommeil profond : `sleep()` |
| puce tactile | `read_point()` → `(x, y)` ou `None` (`OSError` sur une erreur de bus), `reopen()` ; avant un sommeil profond : `hibernate()`. Les gestes, les seuils en millimètres et les transformations sont faits par `hw/touch_input.py` |
| clavier | `get_pressed_action()` → `(action, modifier_changed)`, `set_text_mode(on)`, `acknowledge()` |
| bouton | `pressed()` — `True` une fois par appui |
| stockage | `mount()`, `remount()`, `is_mounted` |
| alimentation | `level()`, `charging()`, `millivolts()` — `None` si inconnu |
| horloge matérielle | `hw.rtc_base.TimeProvider` : `is_available`, `get_datetime()`, `set_datetime(dt)` (tuples comme `time.localtime()`) ; avec une alarme aussi `set_alarm(dt or None)`, `alarm_fired()`, `clear_alarm_flag()` |
| buzzer / vibration | une classe avec `set(on)` (et `pwm` pour une tonalité), passée comme `pulser` à `buzzer.begin` |

---

## 6. Pièges connus (du port T-Watch)

- **Pas de REPL après l'ouverture du port** : le pont CH9102 tient l'ESP32 en réinitialisation par DTR/RTS →
  `reset_lines_low = true`.
- **Panique avec un SPI rapide** : sur un ESP32 classique, les broches hors IO_MUX limitent le SPI à ~26,67 MHz ;
  utilise `miso=None` si le MISO par défaut entre en conflit avec une autre broche.
- **Code viper** : `mpy-cross` a besoin de `-march=xtensawin` (la compilation le passe).
- **Le code figé a la priorité** sur les fichiers de la flash. Les fichiers `.py` dans `<flash>/apps/Squirrel` ne le
  remplacent qu'en mode DEV (fichier marqueur `<flash>/DEV`) — pratique pour des essais rapides sans recompiler le
  firmware.
- **`BUILD=` sur la ligne de commande de `make`** casse la compilation de MicroPython — ne le passe pas.
- **Périphériques alimentés par un PMU** (AXP202) : l'écran, le son et le tactile peuvent avoir besoin d'un LDO précis à
  une tension précise avant que le pilote n'envoie quoi que ce soit.
- **Des interruptions en attente** de la puce d'alimentation ou d'horloge tiennent la ligne INT à l'état bas et
  empêchent le réveil — efface-les dans `begin()`.
