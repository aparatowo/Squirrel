# Compiler le firmware

*[English](../en/building.md) · [Polski](../pl/building.md) · Français · [Deutsch](../de/building.md)*

`Squirrel!/build_firmware.py` construit une image de firmware avec toute l'application **figée** dedans : le code est du
bytecode en flash, pas des fichiers sur l'appareil ni une compilation en RAM au démarrage. Il n'a besoin que de la
bibliothèque standard de Python. La version courte pour les utilisateurs est dans
[guides/fr/getting-started.md](../../guides/fr/getting-started.md) ; ici, toute l'histoire. Les appareils et leur
`port.toml` : [ports.md](ports.md).

Lance chaque commande dans `Squirrel!/`.

## 1. Une fois par ordinateur

```bash
python3 build_firmware.py --install-idf          # ESP-IDF 5.4.2 (~1 GB) into ~/esp-idf-v5.4.2 (or: --install-idf DIR)
python3 build_firmware.py --check                # what is in place, what is missing - changes nothing
```

- **ESP-IDF 5.4.x seulement.** Le firmware du Cardputer est corrigé pour 5.4.2 ; avec 5.5 son micro enregistre du
  silence, les plus anciennes ne le compilent pas. Le script trouve 5.4.x tout seul, même quand `IDF_PATH` dans ton
  shell pointe ailleurs.
- **Cardputer, une fois :** `sudo apt install quilt`, puis `python3 build_firmware.py --setup` (sous-modules, correctifs,
  littlefs, mpy-cross du dépôt UIFlow ; marqueur `.build/setup.done`, `--force` le refait).
- **Les montres** n'ont besoin de rien de plus : la première compilation clone MicroPython v1.25.0 dans
  `vendor/micropython` et applique elle-même les correctifs du port.

Le dépôt du firmware du Cardputer (`cardputer-adv-micropython`) est cloné dans `vendor/` au premier lancement. Un autre
emplacement : `--repo`, la variable `SQUIRREL_FW_REPO` ou `build_config.json` :

```json
{"repo": "/path/to/cardputer-adv-micropython", "idf": "/path/to/esp-idf-v5.4.2", "port": "twatch2020_v3", "exclude": []}
```

## 2. Au quotidien

```bash
python3 build_firmware.py --stage-only                    # seconds: collect the sources, check imports, compile them
python3 build_firmware.py                                 # full image -> dist/squirrel-<board>-<git>-<time>.bin (+ .txt)
python3 build_firmware.py --flash /dev/ttyACM0            # build and flash
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0     # another device
```

Le `.txt` à côté de l'image liste ce qu'elle contient. La compilation se fait dans un environnement propre (sans les
variables `IDF_*` de ton shell) et repart de zéro quand la précédente a utilisé un autre ESP-IDF.

**Ce que fait une compilation :** elle lit `ports/<port>/port.toml` et `features.toml`, écrit `port_config.py` pour cet
appareil, laisse de côté les modules des fonctions que l'appareil n'a pas, les pilotes que son `port.toml` ne nomme pas
et les dossiers des autres ports, s'arrête si un module importe quelque chose qui n'est pas dans cette compilation,
compile tout avec le `mpy-cross` du firmware lui-même, et fige le tout dans une définition de carte à elle (les
fichiers du dépôt du firmware ne sont pas modifiés : une carte dérivée, listée dans `.git/info/exclude` ; `--clean` la
supprime). `lang/<code>.py` (les traductions, construites depuis `translations/*.tsv` par `tools/i18n/build.py`) est
figé comme n'importe quel module, et la police du Cardputer va dans la partition système de l'image.

## 3. Flasher

```bash
python3 build_firmware.py --flash-image <file from dist/> --flash /dev/ttyACM0    # an image built earlier
python3 build_firmware.py --setup-device /dev/ttyACM0                            # only prepare a device
python3 build_firmware.py --flash /dev/ttyACM0 --no-device-setup                 # flash, do not prepare
```

- Ferme Thonny (ou tout ce qui occupe le port). `ls /dev/serial/by-id/` nomme les appareils : `...Espressif...` /
  `...M5Stack...` est le Cardputer, `...1a86...` la T-Watch (CH9102).
- **Cardputer :** sa console USB est TinyUSB, une partie de l'application, et une réinitialisation coupe la connexion
  - flasher un Cardputer en marche échoue souvent. Maintiens **G0** en branchant le câble : il attend en mode
  téléchargement (écran noir, le port s'appelle alors `...Espressif_USB_JTAG...`). Après le flashage, il démarre tout
  seul et revient sous son nom d'application ; le message "did not come back" veut alors seulement dire que le nom a
  changé.
- L'image du Cardputer est toute la flash depuis 0x0 (les réglages NVS d'UIFlow sont remplacés ; tes données sont sur
  la carte SD) ; les images des montres ne touchent pas la partition des données (`/Squirrel` reste).

**Préparer l'appareil** (fait tout seul après `--flash PORT`, chaque étape seulement si nécessaire, et seulement sur un
appareil dont `sys.implementation._machine` contient le `[port] machine` du port) :

1. `/flash/main.py` (ou `/main.py`) = `device/main.py`, qui démarre Squirrel! ; un plus ancien est gardé sous
   `main.py.old` ;
2. Cardputer : le `/flash/boot.py` d'UIFlow est renommé `boot.py.uiflow` quand il importe `startup`, que ce firmware
   n'a pas (lui rendre son nom ramène le menu d'UIFlow) ;
3. Cardputer : l'option de démarrage d'UIFlow `boot_option = 0` (lancer `main.py` tout de suite).

## 4. Vérifier un appareil

```python
import sq_info; sq_info.report()       # in Thonny
```

Il montre la version, le nombre de modules figés, les fichiers qui **masquent** des modules figés, si `main.py` démarre
l'application, la police, et d'où vient `nuts`. Le journal de démarrage (`/flash/boot_log.txt` sur le Cardputer,
`/boot_log.txt` sur la montre) a une ligne `[MAIN] frozen build <id> (N modules)`.

Ne laisse pas de modules `.py` / `.mpy` dans la flash de l'appareil (à part `main.py`) : ils masqueraient les modules
figés du même nom.

## 5. Mode DEV : changer le code sans nouveau firmware

Crée un fichier vide `/flash/DEV` (la montre : `/DEV`) et mets les fichiers `.py` modifiés dans `/flash/apps/Squirrel/`
(sous-dossiers comme dans les sources). Ils l'emportent maintenant sur les figés ; supprime `DEV` pour revenir. Un
dossier (`screens/`, `hw/`, `drivers/`, `ports/`) sur l'appareil masque **tout** le paquet figé de ce nom : copie-le en
entier. Un `.mpy` l'emporte sur un `.py` du même nom.

Aide rapide quand un appareil manque de mémoire en compilant des fichiers `.py` : `--build-mpy-cross`, puis `--mpy`
écrit des fichiers `.mpy` dans `dist/mpy/` (pas besoin d'ESP-IDF).

## 6. Autres options

| Option | Ce qu'elle fait |
|---|---|
| `--target build` | l'application seule (`micropython.bin`) - pas une image complète |
| `--target pack_all` | l'image avec un système de fichiers utilisateur **vide** : efface `/flash` |
| `--gen-port-config` | écrit `port_config.py` à côté des sources (pour le mode DEV et le simulateur) ; le port par défaut sauf `--port` |
| `--exclude FILE` | laisser un fichier hors de l'image (répétable ; les scripts PC comme `vlw.py` sont laissés de côté d'eux-mêmes) |
| `--prefer newer\|flat\|screens` | le même écran à deux endroits avec un contenu différent : lequel l'emporte |
| `--update-repo` | `git pull` dans le dépôt du firmware |
| `--reset-deps` | supprimer `dependencies.lock` et `managed_components` (résolus à nouveau à la compilation suivante) |
| `--diagnose` | expliquer la dernière compilation ratée à partir de `.build/make.log` |
| `--allow-any-idf` | compiler avec un autre ESP-IDF (pas pour `--setup` ; déconseillé) |
| `--allow-missing` | compiler même si le manifeste de la carte de base nomme un fichier manquant |

Le `port_config.py` à côté des sources appartient au port par défaut (le Cardputer) ; après `--gen-port-config --port
X`, remets-le avant de committer. Une compilation écrit toujours le sien.

## 7. Correctifs du firmware

Le firmware n'est modifié que par des correctifs gardés dans le dépôt, appliqués à une copie temporaire en pile :

| Correctif | Ce qu'il fait |
|---|---|
| `firmware_patches/0001-nimble-central-passkey.patch` | NimBLE : les événements passkey du central (chiffrement de la liaison, désactivé pour l'instant) |
| `firmware_patches/0002-panic-record.patch` | un rapport de panique ou du chien de garde des tâches gardé en mémoire RTC à travers la réinitialisation (`tools/hwtest/panic_record.py` le lit) : la console TinyUSB du Cardputer ne montre rien quand il plante |
| `ports/<port>/firmware/patches/*.patch` | pour chaque montre : ce dont sa compilation de MicroPython a besoin |

## 8. Quand quelque chose ne va pas

| Message | Que faire |
|---|---|
| `No ESP-IDF 5.4.x found` | `--install-idf` |
| `quilt is not installed` | `sudo apt install quilt` |
| `mpy-cross is not built` | `--setup` (le dépôt du Cardputer n'est pas encore préparé) |
| `Two different copies of the same screen module` | supprime le fichier périmé, ou `--prefer newer` |
| `... does not compile with the firmware's mpy-cross` | ce fichier utilise une syntaxe que MicroPython n'a pas |
| `imports ..., which is not in the sources (of this port)` | un module a besoin d'une fonction ou d'un pilote que ce port laisse de côté : importe-le dans la fonction qui en a besoin, ou ajoute-le au port |
| `CFG_TUD_CDC_EP_BUFSIZE undeclared` | composants TinyUSB incompatibles : fixe `espressif/tinyusb` à `0.15.0~10` dans `m5stack/main/idf_component.yml`, puis `--reset-deps` |
| `Cannot stat .../firmware_info.py` | le script le génère pour la carte de base avant la compilation ; si cela échoue, il dit quoi vérifier (`--allow-missing` saute la vérification) |
| le flashage échoue | ferme Thonny ; Cardputer : maintiens G0 en branchant ; Linux : `sudo usermod -aG dialout $USER` et reconnecte-toi |
| pas d'application après le flashage | depuis la 2.1 le firmware écrit lui-même `/flash/main.py` au premier démarrage (image complète par M5Burner, puce effacée) ; sinon `--setup-device PORT` ; vérifie `/flash/main.py` |
| autre chose | toute la sortie est dans `.build/make.log` ; `--diagnose` reconnaît les cas connus |
