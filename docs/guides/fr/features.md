# Fonctions

*[English](../en/features.md) · [Polski](../pl/features.md) · Français · [Deutsch](../de/features.md)*

Ce que fait Squirrel!, écran par écran. Version 2.0. Les touches et gestes pour tout cela : [raccourcis](shortcuts.md).
Images : le Cardputer à gauche, la montre à droite (là où elle a cet écran).

---

## 🕐 L'horloge

L'écran d'accueil est une horloge : de grands chiffres, la date et une ligne à toi en bas (*no need to go nuts* sur
le Cardputer, *Squirrel! is watching* sur la montre - à changer dans Personnaliser, ou à laisser). Les barres sur les
bords sont la batterie (à gauche) et le temps de concentration du jour par rapport à ton objectif (à droite). La
montre affiche aussi le jour de la semaine et, en mots, le temps de concentration et la batterie - chacun dans la
couleur de sa barre.

<img src="../../../shots/cardputer/fr/clock.png" width="360"> <img src="../../../shots/twatch/fr/clock.png" width="240">

Depuis l'horloge : toute touche ouvre le menu, **OPT** lance ou met en pause le compteur de concentration, **Aa**
synchronise tes appareils, **TAB** ouvre un petit menu de ce dont tu te sers le plus :

<img src="../../../shots/cardputer/fr/tab-menu.png" width="360">

L'heure vient d'une horloge matérielle quand il y en a une (le PCF8563 de la montre, un DS1302 optionnel sur le
Cardputer), du Wi-Fi au démarrage, ou d'un autre appareil Squirrel! par Bluetooth (*Réglages → Heure et date → Heure
d'un appareil*).

## ✅ Tâches et listes à cocher

Une liste de choses à faire qui ne te juge pas. Une tâche, c'est un titre et, si tu veux, plus de texte. **OPT** la
marque comme faite (sur la montre : appui long). Les tâches faites restent une semaine (`TODO_KEEP_DAYS`), puis
partent d'elles-mêmes.

<img src="../../../shots/cardputer/fr/todo-list.png" width="360"> <img src="../../../shots/twatch/fr/menu_todo.png" width="240">

**Listes à cocher.** Les lignes qui commencent par `>` sont des éléments à cocher - une liste de courses, les étapes
d'une tâche :

```
Courses du samedi
> lait
> pain
> noix
ne pas oublier le sac
```

Une telle tâche s'ouvre comme une liste à cocher ; la liste montre l'avancement (`[1/3]`) ; quand tout est coché, la
tâche entière est faite. Le texte du fichier ne change jamais - les coches sont gardées à part.

<img src="../../../shots/cardputer/fr/checklist-ticked.png" width="360"> <img src="../../../shots/twatch/fr/checklist.png" width="240">

Les tâches s'écrivent sur le Cardputer (il a le clavier) ; sur la montre, tu les lis et tu les coches.

## 📋 Notes texte

Un endroit pour ce qui doit sortir de ta tête tout de suite : un titre (la première ligne) et le texte, enregistrés
aussitôt sur la carte SD en simples fichiers `.txt` lisibles sur n'importe quel ordinateur. **CTRL+S** enregistre,
**ESC** abandonne les modifications.

<img src="../../../shots/cardputer/fr/editor.png" width="360"> <img src="../../../shots/cardputer/fr/note-viewer.png" width="360">

Supprimer demande d'appuyer trois fois sur DEL - un doigt qui glisse ne peut pas effacer une note.

<img src="../../../shots/cardputer/fr/delete-confirm.png" width="360">

## 🧠 Vide-tête

Pour la pensée qui tourne en rond. TAB, puis M sur l'horloge : écris-la (jusqu'à 200 caractères - assez pour l'attraper,
trop peu pour s'y perdre), ENTER, et te voilà de retour où tu étais. Les pensées du vide-tête ont leur propre liste
(*Notes → Vide-tête*) ; modifies-en une et elle devient une vraie note.

<img src="../../../shots/cardputer/fr/mind-dump.png" width="360">

## 🎙️ Notes vocales

Quand taper est trop lent : **G0** sur l'horloge ou dans un menu lance l'enregistrement tout de suite, G0 à nouveau
l'enregistre. Ce sont des fichiers `.wav` sur la carte SD ; tu les réécoutes dans *Notes → Notes vocales* (pause,
10 s en arrière / en avant, volume).

<img src="../../../shots/cardputer/fr/recorder.png" width="360"> <img src="../../../shots/cardputer/fr/voice-notes.png" width="360">

## 🔄 Routines

Des rappels récurrents : un texte, une heure, les jours de la semaine. Quand c'est l'heure, l'écran le dit - **OPT** :
fait (compte dans les statistiques), **DEL** : passer. Pas de réponse pendant 30 secondes : il revient après un report
(`ROUTINE_SNOOZE_MIN`). En rater une ne change rien - pas de rouge, pas de série perdue ; la fois suivante arrive
simplement.

<img src="../../../shots/cardputer/fr/routines.png" width="360"> <img src="../../../shots/cardputer/fr/routine-due.png" width="360">

Avec des appareils synchronisés, une routine a un champ *Appareils* : elle n'apparaît que sur ceux que tu coches (les
vitamines sur la montre, les plantes sur le Cardputer). Sur la montre, on active et désactive les routines d'un
toucher ; on les écrit sur le Cardputer.

## 🦅 Horloge à coucou

Un signal discret à chaque heure pile - et, si tu veux, un tic plus doux à chaque quart d'heure. Pas une alarme : une
tape sur l'épaule, *le temps passe*. Il continue écran éteint. Son, buzzer, LED ou vibration, comme tu les règles ; le
mode silencieux le fait taire la nuit.

## 🍅 Pomodoro et entraînement

Travailler un bloc, se reposer, recommencer : le Pomodoro montre le bloc (*Travail*, *Pause*, *Longue pause*), le
temps restant et la rangée des blocs à venir. Il tourne en arrière-plan - quitte l'écran, il continue de compter ; le
temps de concentration va dans les statistiques. *Entraînement*, c'est le même minuteur avec des blocs que tu composes
toi-même (préparation, léger, normal, intense, repos).

<img src="../../../shots/cardputer/fr/pomodoro-running.png" width="360"> <img src="../../../shots/twatch/fr/pomodoro_running.png" width="240">

## 🥁 Métronome et 🫁 respiration

Le métronome bat de toutes les 1/8 s à toutes les 2 minutes - quelque chose de régulier à suivre, en arrière-plan. La
respiration te guide à travers *Carré 4-4-4-4*, *Détente 4-7-8* ou *Calme 5-5* : un cercle grandit à l'inspiration et
rétrécit à l'expiration (la LED le suit, si tu en as une).

<img src="../../../shots/cardputer/fr/metronome.png" width="360"> <img src="../../../shots/cardputer/fr/breathing.png" width="360">

## 📊 Statistiques

Le temps de concentration du jour par rapport à ton objectif, et les 7 derniers jours. Pas d'objectif à rater, pas de
comparaisons - une image paisible de tes journées. Avec des appareils synchronisés : LEFT / RIGHT montre cet appareil,
chaque appareil synchronisé, ou tous ensemble.

<img src="../../../shots/cardputer/fr/statistics.png" width="360"> <img src="../../../shots/twatch/fr/focus_stats.png" width="240">

## 🔗 Synchronisation Bluetooth

Le Cardputer et la montre se tiennent à jour : routines, tâches, notes et réglages vont à la montre ; les coches, le
journal des routines et les statistiques reviennent. **Aa** sur l'horloge du Cardputer synchronise tout de suite ; ou
laisse-les se synchroniser seuls, de toutes les 15 minutes à toutes les 4 heures. Tout à ce sujet :
[synchronisation Bluetooth](bluetooth.md).

<img src="../../../shots/cardputer/fr/bluetooth.png" width="360"> <img src="../../../shots/twatch/fr/ble_sync.png" width="240">

## 🔕 Mode silencieux

Les heures et les jours où le son, le buzzer ou la LED se taisent - chacun à part (*Réglages → Mode silencieux*). Une
nuit compte pour le jour où elle commence.

<img src="../../../shots/cardputer/fr/silent-mode.png" width="360"> <img src="../../../shots/twatch/fr/silent_sound.png" width="240">

## 🎨 Personnaliser et langues

Les couleurs, le texte sous l'horloge, les durées du Pomodoro et de la concentration, les signaux, la veille - tout est
dans *Réglages → Personnaliser*, chacun avec une ligne d'aide, et tout est gardé dans `config.txt` sur l'appareil (un
simple fichier texte que tu peux aussi modifier).

Les écrans parlent **anglais, polonais, français ou allemand** (*Personnaliser → Écran → Langue*) ; toute langue autre
que l'anglais active la police avec les lettres accentuées. Un texte que tu formulerais autrement se change sur
l'appareil, sans nouveau firmware : [Squirrel!/translations/README.md](../../../Squirrel!/translations/README.md).

<img src="../../../shots/cardputer/fr/personalize.png" width="360"> <img src="../../../shots/cardputer/fr/personalize-language.png" width="360">

## 🔋 Énergie

L'écran baisse après un moment sans touche ; avec le *Mode veille*, l'appareil dort pendant qu'il est assombri (la
montre dort profondément et se réveille pour ses routines, le coucou et ses heures de synchronisation). Les radios ne
sont allumées que lorsqu'elles travaillent : le Wi-Fi pour l'heure au démarrage, le Bluetooth pour une synchronisation.
