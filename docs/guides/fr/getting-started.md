# Premiers pas

*[English](../en/getting-started.md) · [Polski](../pl/getting-started.md) · Français · [Deutsch](../de/getting-started.md)*

D'un appareil neuf à Squirrel! dessus. Version 2.0.

## Les appareils

| Appareil | Ce que c'est | Ce qu'il te faut |
|---|---|---|
| **M5Stack Cardputer ADV** | un ordinateur de poche avec clavier (ESP32-S3) - l'appareil principal de Squirrel!, le *chef* de la synchronisation Bluetooth | une carte microSD (FAT32) pour tes données |
| **M5Stack Cardputer** (le premier, v1.0 / v1.1) | *expérimental* : le même ordinateur de poche avant l'ADV - pas encore essayé sur un appareil | une carte microSD (FAT32) ; pour l'heure sans Wi-Fi, un module DS3231 sur son port Grove |
| **LilyGo T-Watch 2020 V3** | une montre à écran tactile (ESP32) - lit et coche ce que le Cardputer lui donne, routines et minuteurs au poignet | rien de plus |
| **Une montre ESP32-S3 générique** | *expérimental* : les montres bon marché vendues comme "ESP32-S3 smartwatch" - pas encore essayé sur un appareil | vérifier d'abord ses broches ([ports](../../implementation/fr/ports.md)) |

Ce qui marche où : le Cardputer a tout ; la montre n'a pas de clavier (elle n'écrit ni notes ni tâches - elle les lit
et les coche), ni encore de son ou de micro, mais elle vibre, dort profondément et a une horloge matérielle. Le
premier Cardputer a tout sauf le buzzer (pas de broche libre pour lui) ; d'un sommeil léger, seule une rangée de
touches le réveille (Aa, S, F, H, K, UP, ENTER).

## Sur ton ordinateur

- **Linux** (macOS et Windows devraient marcher, mais les instructions ci-dessous sont pour Linux), **Python 3.10+**,
  **git**.
- Un **câble USB-C** (la montre : micro-USB) qui transporte les données, pas seulement la charge.

```bash
git clone https://github.com/aparatowo/Squirrel.git
cd "Squirrel/Squirrel!"
python3 build_firmware.py --install-idf     # ESP-IDF 5.4.2 (~1 GB), once
python3 build_firmware.py --check           # is everything in place? (changes nothing)
```

Le Cardputer demande une étape de plus, une seule fois : `python3 build_firmware.py --setup` (il faut
`sudo apt install quilt`).

## Compiler et flasher

Ferme Thonny (ou tout ce qui occupe le port USB), puis :

```bash
# Cardputer ADV (the default device)
python3 build_firmware.py --flash /dev/ttyACM0

# T-Watch 2020 V3
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0

# Cardputer (the first one, not ADV) - experimental
python3 build_firmware.py --port cardputer --flash /dev/ttyACM0
```

La première compilation compile tout ESP-IDF et prend plusieurs minutes ; les suivantes sont plus rapides. Le script
construit l'image (dans `dist/`), la flashe et prépare l'appareil : Squirrel! démarre tout seul.

**Quel port ?** `ls /dev/serial/by-id/` les nomme : le Cardputer est `...Espressif...` ou `...M5Stack...`, la montre
`...1a86...`.

**Le Cardputer refuse d'être flashé ?** Sa console USB fait partie de l'application, et une réinitialisation coupe
l'USB. Maintiens **G0** en branchant le câble : le Cardputer attend alors en mode téléchargement (écran noir) et le
flashage marche. Il démarre ensuite le nouveau firmware tout seul.

**La montre la première fois :** elle arrive avec un autre logiciel. Garde-en d'abord une copie :
`tools/hwtest/twatch_phase0.sh /dev/ttyACM0` (16 Mo, quelques minutes).

## Le premier démarrage

- **Cardputer :** insère une carte microSD (FAT32) ; Squirrel! y crée lui-même son dossier `/Squirrel`.
- **L'heure :** le Cardputer règle son horloge par Wi-Fi au démarrage - ajoute ton réseau dans *Réglages →
  Connexions → Réseaux WiFi* (le partage de connexion d'un téléphone convient ; 2,4 GHz). Ou règle-la à la main
  (*Réglages → Heure et date → Régler l'heure*), ou prends-la de la montre par Bluetooth.
- **Un module d'horloge** (DS3231 / DS1302) garde l'heure sans Wi-Fi : branche-le, puis choisis-le dans *Réglages →
  Heure et date → Réglages de l'heure → Module d'horloge* (il est désactivé jusque-là).
- **La langue :** *Réglages → Personnaliser → Écran → Langue* - English, Polski, Français, Deutsch.
- **La montre et le Cardputer ensemble :** appaire-les une fois ([synchronisation Bluetooth](bluetooth.md)).

Ensuite : [fonctions](features.md) pour ce qu'il y a, [raccourcis](shortcuts.md) pour les touches.

## Tes données

Tout est en fichiers simples : notes et tâches en `.txt`, notes vocales en `.wav`, statistiques, routines et
`config.txt` (tes réglages, chacun avec un commentaire). Sur le Cardputer, ils sont sur la carte SD dans `/Squirrel` ;
sur la montre, dans `/Squirrel` sur sa mémoire flash interne. Flasher une nouvelle version les garde.

Rien ne quitte ton appareil - sauf par la synchronisation Bluetooth avec tes propres appareils appairés, et le Wi-Fi
seulement pour l'heure.

## Mettre à jour

```bash
cd Squirrel
git pull
cd "Squirrel!"
python3 build_firmware.py --flash /dev/ttyACM0          # (--port twatch2020_v3 for the watch)
```

Une version précise : `git checkout 2.0` (les versions sont des tags git), puis compiler comme ci-dessus.

## Quand quelque chose ne va pas

| Problème | Que faire |
|---|---|
| `port not found`, le port est occupé | Ferme Thonny ; vérifie `ls /dev/serial/by-id/` ; sous Linux il faut parfois `sudo usermod -aG dialout $USER` (puis se reconnecter). |
| Le Cardputer refuse d'être flashé | Maintiens G0 en branchant le câble (ci-dessus). |
| Écran noir après le flashage | Débranche et rebranche le câble ; vérifie qu'il transporte les données. |
| L'application ne démarre pas | `python3 build_firmware.py --setup-device PORT` prépare l'appareil à nouveau ; dans Thonny : `import sq_info; sq_info.report()`. |
| Les notes ne sont pas enregistrées (Cardputer) | La carte microSD est-elle insérée, formatée en FAT32 ? |
| Il redémarre tout seul de temps en temps | Un chien de garde redémarre un appareil figé au bout d'une minute ; tes données restent. Si cela arrive souvent, signale-le. |

Pour ceux qui compilent et modifient Squirrel! : [les documents d'implémentation](../../implementation/fr/).
