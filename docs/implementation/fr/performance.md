# Mémoire, vitesse et énergie

*[English](../en/performance.md) · [Polski](../pl/performance.md) · Français · [Deutsch](../de/performance.md)*

Squirrel! doit tenir sur le plus faible de ses appareils : un ESP32-S3 **sans PSRAM** (le Cardputer ADV, beaucoup de
montres bon marché) donne à MicroPython environ **160 Ko** de tas pour tout. Ce que cela coûte aujourd'hui, et comment
on garde cela petit.

## 1. Mesuré (2.0)

| Quoi | Valeur |
|---|---|
| Le tas de l'application sur le Cardputer (sans PSRAM), sur l'horloge | 54 Ko sur 160 Ko |
| dont les réglages (95) | 7,4 Ko |
| Une langue autre que l'anglais | moins de 1 Ko de RAM (les tables restent en flash) |
| Chercher un texte sur la montre (ESP32 à 80 MHz) | 91 µs (763 µs sans le cache) ; dessiner un écran environ 2 % plus lent qu'en anglais |
| L'écran de la montre, tampon complet / bandes | menu 132 / 141 ms, horloge 292 / 366 ms |
| Tampon d'image pour 240 × 240 / 240 × 280, en bandes | 115 / 134 Ko, 19 Ko |
| Une synchronisation Bluetooth automatique, sur la montre | environ 1 mAh (sa batterie : environ 380 mAh) |

## 2. Comment on garde cela petit

- **Code figé.** Tous les modules sont du bytecode en flash (`build_firmware.py`) : rien n'est compilé sur
  l'appareil, et le code ne prend pas de tas. Les tables constantes (traductions, glyphes, police) restent aussi en
  flash.
- **Les réglages en lignes.** `appconfig` garde une référence à chaque ligne `SETTINGS` de `appconfig_schema.py` au
  lieu d'une copie par réglage, et prend les valeurs par défaut directement dans `nuts`.
- **Les traductions** sont un tuple trié par langue, cherché par dichotomie ; un cache des 200 derniers textes, et les
  textes propres de l'utilisateur (`lang_<code>.tsv`) sont les seuls en RAM. Voir [i18n.md](i18n.md).
- **L'écran en bandes** sans PSRAM (`drivers/st7789_fb.py`) : les appels de dessin d'une image sont gardés et rejoués
  dans un tampon de 40 lignes, une bande à la fois. Choisi tout seul : l'image entière seulement si elle prend au plus
  un quart du tas libre ; `[display] buffer_rows` force les bandes. Voir [ports.md](ports.md).
- **Écrans déchargés** (`POWER_UNLOAD_SCREENS`) : les objets d'un écran rarement utilisé partent quand tu le quittes.
- **Imports paresseux** de ce dont un seul écran ou une seule fonction a besoin ; une fonction que l'appareil n'a pas
  n'est pas du tout dans son firmware (`features.toml`).
- **Bluetooth :** seulement pendant une session ; un enregistrement en mémoire à la fois (envoyé et reçu par
  morceaux) ; le ramasse-miettes automatique est coupé pendant une session et `tick()` ramasse depuis la boucle
  principale - un ramassage déclenché par une allocation dans l'IRQ de la radio tournait sur sa petite pile.

## 3. Énergie

- Les radios ne sont allumées que lorsqu'elles travaillent : le Wi-Fi pour l'heure au démarrage, le Bluetooth pour une
  session de synchronisation (un ESP32 ne peut pas faire de veille légère avec le contrôleur BT allumé).
- L'écran baisse après un moment sans action ; `POWER_SAVE` ralentit le processeur pendant qu'il est assombri.
- `POWER_SLEEP` : `light` (expérimental) dort pendant que l'écran est assombri et se réveille sur une touche, un bouton
  ou un toucher ; `deep` (la montre) dort profondément et se réveille par l'alarme de son horloge pour la prochaine
  routine, le coucou ou le créneau de synchronisation (`alarms.py` tient la file, `deep_sleep.py` enregistre et
  restaure l'état). Après un réveil, le cadran est dessiné avant que le reste de l'application ne démarre
  (`EARLY_CLOCK`).
- Les créneaux de synchronisation automatique suivent l'horloge, pour que les appareils se retrouvent sans se parler
  avant : la montre écoute 90 s par créneau, le chef se connecte 20 s après son début.

## 4. Filets de sécurité

- **Chien de garde** (`WATCHDOG_S`, 60 s) : si la boucle principale ne revient pas, l'appareil redémarre ; les données
  restent.
- **Trace de plantage** (`firmware_patches/0002-panic-record.patch`) : la cause et la pile d'un plantage, ou ce que
  faisait le cœur 0 quand le chien de garde des tâches s'est déclenché, survivent au redémarrage en mémoire RTC ;
  `tools/hwtest/panic_record.py` les lit.
- `LOW_HEAP` dans `hw/power.py` : un ramassage avant que le tas ne manque.

## 5. Le vérifier à nouveau

```python
import gc, micropython; gc.collect(); micropython.mem_info()      # in the REPL of a running app (DEV mode)
```

`tools/hwtest/ble_e2e.py --mem` affiche la mémoire du Cardputer toutes les demi-secondes pendant une
synchronisation ; `tools/hwtest/twatch_gfx_bench.py` chronomètre le dessin de la montre.
