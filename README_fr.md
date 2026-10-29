![Squirrel!](squirrel.jpg)

# 🐿️ Squirrel!

**Un assistant électronique au grand cœur et à la queue touffue, qui tient dans la poche - et au poignet.**

*[English](README.md) · [Polski](README_pl.md) · Français · [Deutsch](README_de.md)*

---

Squirrel! n'a besoin ni de téléphone, ni d'internet, ni de cloud, ni d'IA. Surtout, il ne vole pas ton attention avec
mille notifications - comme le fait d'habitude ton smartphone.

On dit que les écureuils ont une mémoire terrible. Squirrel! a de la mémoire pour deux. Il se souvient de ce que tu
oublies d'habitude, te rappelle doucement à l'ordre quand tu décroches, et se réjouit avec toi quand tu y arrives. Il
ne soupire jamais, ne compte pas combien de fois tu as demandé la même chose, ne t'affiche jamais de série rouge. Il
revient simplement chaque jour, prêt à aider.

Il est fait pour les personnes avec un TDAH, une cécité temporelle ou un trouble des fonctions exécutives - et pour
quiconque a besoin d'un outil calme et patient qui ne culpabilise pas *« d'avoir pris du retard »*.

<img src="shots/cardputer/fr/clock.png" width="360"> <img src="shots/twatch/fr/clock.png" width="240">

## Ce qui le rend différent

- **Pas de punition quand on oublie.** Tu sautes ta routine du matin : rien ne devient rouge, aucune série ne repart à
  zéro. Demain, la routine t'attend, inchangée, sans commentaire.
- **Calme par conception.** Pas de fenêtres surgissantes, pas de pastilles, pas de bruit visuel. Ce dont tu as besoin
  est à l'écran ; le reste ne gêne pas.
- **Des rappels à ta façon.** Autant de routines qu'il en faut, un coucou chaque heure et, si tu veux, chaque quart
  d'heure - ou le silence, la nuit ou quand tu le choisis.
- **Hors ligne, et à toi.** Ni compte, ni abonnement, ni cloud. Tes notes et tâches sont de simples fichiers sur ton
  appareil ; la radio ne sert qu'à la synchronisation Bluetooth entre tes propres appareils appairés, et au Wi-Fi pour
  l'heure.
- **Rien ne marche ? Ce n'est pas grave non plus.** Essaie les outils et garde ce qui marche **pour toi**.

## Ce qu'il fait

| | |
|---|---|
| 🕐 **Horloge** avec la batterie et la concentration du jour en barres | 🧠 **Vide-tête** - une pensée hors de la tête en quelques secondes |
| ✅ **Tâches et listes à cocher** qui ne jugent pas | 🎙️ **Notes vocales** d'un seul bouton |
| 📋 **Notes texte**, de simples fichiers `.txt` | 🔄 **Routines** sans série à perdre |
| 🦅 **Horloge à coucou** contre la cécité temporelle | 🍅 **Pomodoro et entraînement** en arrière-plan |
| 🥁 **Métronome** et 🫁 **respiration** | 📊 **Statistiques** - une image paisible de tes journées |
| 🔗 **Synchronisation Bluetooth** entre tes appareils | 🌍 **English, Polski, Français, Deutsch** |

<img src="shots/cardputer/fr/checklist-ticked.png" width="360"> <img src="shots/twatch/fr/pomodoro_running.png" width="240">

Écran par écran : [fonctions](docs/guides/fr/features.md) · les touches : [raccourcis](docs/guides/fr/shortcuts.md).

## Appareils

| Appareil | |
|---|---|
| **M5Stack Cardputer ADV** | l'ordinateur de poche avec clavier - le Squirrel! principal, celui où l'on écrit |
| **LilyGo T-Watch 2020 V3** | au poignet : lit et coche ce que le Cardputer lui donne, routines et minuteurs, vibration |
| **M5Stack Cardputer** (le premier) | *expérimental*, pas encore essayé sur un appareil : le même Squirrel! que sur l'ADV, sans le buzzer |
| **Montres connectées ESP32-S3** | *expérimental*, pas encore essayé sur un appareil |

## Premiers pas

```bash
git clone https://github.com/aparatowo/Squirrel.git
cd "Squirrel/Squirrel!"
python3 build_firmware.py --install-idf                     # once
python3 build_firmware.py --flash /dev/ttyACM0              # Cardputer ADV
python3 build_firmware.py --port twatch2020_v3 --flash /dev/ttyACM0     # T-Watch 2020 V3
python3 build_firmware.py --port cardputer --flash /dev/ttyACM0         # Cardputer (the first one)
```

Toutes les étapes : [premiers pas](docs/guides/fr/getting-started.md).

## En savoir plus

- **Pour les utilisateurs :** [premiers pas](docs/guides/fr/getting-started.md) · [fonctions](docs/guides/fr/features.md) ·
  [raccourcis](docs/guides/fr/shortcuts.md) · [synchronisation Bluetooth](docs/guides/fr/bluetooth.md)
- **Nouveautés :** [notes de version](docs/releases/README.md) - version 2.0 : synchronisation Bluetooth, quatre
  langues, listes à cocher
- **Pour les développeurs :** [compilation](docs/implementation/fr/building.md) · [ports](docs/implementation/fr/ports.md) ·
  [tous les documents](docs/README.md)
- **Traduire :** [Squirrel!/translations](Squirrel!/translations/README.md)
- **[Mot de l'auteur](docs/author/fr.md)** - pourquoi Squirrel! existe

---

Squirrel! tourne sous MicroPython. Open source (MIT, [LICENSE.txt](LICENSE.txt) ; composants tiers :
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). Construit avec soin. Partagé librement.
