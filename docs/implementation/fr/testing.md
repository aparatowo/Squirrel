# Tests

*[English](../en/testing.md) · [Polski](../pl/testing.md) · Français · [Deutsch](../de/testing.md)*

Trois niveaux : des tests sur le PC (sans appareil), toute l'application dans un simulateur (sans appareil), et des
scripts qui tournent sur les appareils par USB. Lance tout depuis `Squirrel!/`.

## 1. Tests sur le PC

```bash
for t in tools/tests/test_*.py; do python3 "$t" || echo "FAILED: $t"; done
python3 -m unittest tools/tests/test_i18n.py         # (any of them also runs this way)
```

| Test | Ce qu'il couvre |
|---|---|
| `test_ble_protocol.py`, `test_ble_merge.py` | les codecs des enregistrements Bluetooth, les trames et les règles "qui a raison" |
| `test_ble_node.py`, `test_ble_head.py` | une synchronisation complète chef ↔ nœud par la radio factice (`tools/sim/fakes/bluetooth.py` relie deux radios "dans les airs"), appairage compris |
| `test_ble_auto.py` | la synchronisation automatique : créneaux sur l'horloge, le nœud comme source d'alarmes, sauter une radio occupée |
| `test_web_protocol.py` | le codec JavaScript de la page Web Bluetooth donne les mêmes octets que `ble/protocol.py` (il faut `node`) |
| `test_checklist.py`, `test_routines.py` | les listes à cocher (lignes `>`, coches gardées à part), les routines et leurs jours |
| `test_appconfig.py` | `config.txt` : lecture, écriture, commentaires, valeurs par défaut changées par une version plus récente |
| `test_i18n.py` | recherche, retour à l'anglais, modèles (`fill`), le `lang_<code>.tsv` propre à l'utilisateur |
| `test_st7789_strips.py` | l'écran dessiné en bandes donne la même image que le tampon complet (MicroPython seulement : `framebuf`, viper - ignoré sous CPython) |

Plus `python3 tools/i18n/check.py` (chaque texte traduit, mêmes marqueurs, libellés assez courts) et
`python3 build_firmware.py --stage-only --port <port>` pour chaque port (imports, compilation).

## 2. Le simulateur

`tools/sim/` fait tourner toute l'application sur le PC sous le **port unix de MicroPython** (le même MicroPython que le
firmware), avec des imitations de `M5`, `machine`, `esp32`, `network`, `bluetooth` ..., une horloge qui n'avance que
quand le code dort, et les `/sd` et `/flash` de l'appareil dans un dossier. Compiler le port unix une fois :
[tools/sim/README.md](../../../Squirrel!/tools/sim/README.md).

- **Comparer deux versions :** une refactorisation qui ne change pas le comportement donne une trace identique - chaque
  appel d'écran, chaque ligne de journal, chaque fichier écrit :

  ```bash
  mkdir -p /tmp/base && git archive HEAD "Squirrel!" | tar -x -C /tmp/base
  tools/sim/compare.sh <micropython> "/tmp/base/Squirrel!" "$PWD" /tmp/simwork      # IDENTICAL / DIFFERENT
  ```

- **Les captures du Cardputer** pour les guides : un scénario de 34 états, avec un contenu d'exemple dans la langue du
  `config.txt` du dossier de travail (`LANGUAGE=fr` ...), transformé en fichiers PNG :

  ```bash
  mkdir -p /tmp/w/sd/Squirrel /tmp/w/flash/fonts && cp squirrel.vlw /tmp/w/flash/fonts/
  echo "LANGUAGE=fr" > /tmp/w/sd/Squirrel/config.txt
  SQUIRREL_SIM_SCENARIO=tools/sim/shots_scenario.py <micropython> -X heapsize=8M tools/sim/run_sim.py "$PWD" /tmp/w /tmp/trace.txt
  python3 tools/sim/render_shots.py /tmp/trace.txt ../shots/cardputer/fr
  ```

  La police dans `/flash/fonts/` compte : sans elle, l'application affiche les lettres accentuées sans accents. Les
  images sont dessinées avec la police 6 × 8 des montres, pas le `.vlw` du Cardputer ([backlog](backlog.md) D).

## 3. Sur les appareils

Ferme d'abord Thonny (il occupe le port). `ls /dev/serial/by-id/` nomme les ports.

| Outil | Ce qu'il fait |
|---|---|
| `tools/hwtest/run.py PORT SCRIPT [TEST ...]` | lance un script de test matériel par le REPL et montre ses résultats en direct : `RESULT\|test\|PASS / FAIL / INFO / ASK / SKIP\|details` (ASK : confirme ce que tu as vu, entendu ou senti) ; un journal dans `.build/hwtest/`. `PORT` peut être `auto`. Un script ne tourne que sur l'appareil nommé dans sa première ligne (`# EXPECT_MACHINE: ...`) |
| `twatch_hw.py`, `twatch_accel.py`, `cardputer_accel.py` | les scripts : les puces de la montre une à une (PMU, écran, tactile, horloge, vibration), les accéléromètres |
| `twatch_gfx_bench.py` | la vitesse de dessin du pilote d'écran de la montre |
| `tools/hwtest/twatch_phase0.sh PORT` | avant le premier flashage d'une montre : identifiants de la puce et de la flash, une copie complète de 16 Mo de la flash avec son MD5 (restaure le logiciel d'usine) |
| `tools/hwtest/twatch_screens.py PORT --lang fr` | des captures des écrans de la montre lues dans son tampon d'image vers `shots/twatch/<lang>/` (il écrit une liste à cocher d'exemple et la supprime ensuite) |
| `tools/hwtest/ble_e2e.py WATCH CARDPUTER` | une synchronisation Bluetooth de bout en bout par les écrans des deux applications ; `--link` avec chiffrement de la liaison, `--mem` la mémoire toutes les demi-secondes, `--head-files` le chef utilise le paquet `ble/` du PC (en `.mpy`) au lieu du sien figé |
| `tools/hwtest/panic_record.py PORT` | la cause et la pile du dernier plantage ou blocage du Cardputer, depuis la mémoire RTC (sa console TinyUSB ne montre rien quand il plante) |
| `tools/ble_pc_head.py` | le PC comme chef, pour tester une montre sans Cardputer (il faut `bleak`) |

Sur un appareil en marche : `import sq_info; sq_info.report()` (la version, les fichiers qui masquent, la police), et
le journal de démarrage `/flash/boot_log.txt` (Cardputer) ou `/boot_log.txt` (montre).

## 4. Avant une version

1. Les tests sur le PC, `check.py`, `--stage-only` pour chaque port.
2. `compare.sh` par rapport à la dernière version là où le comportement ne devait pas changer.
3. Compiler et flasher les deux appareils ; `ble_e2e.py` plusieurs fois ; une synchronisation depuis l'écran de chaque
   appareil.
4. Des captures dans chaque langue (le Cardputer depuis le simulateur, la montre depuis l'appareil), puis **les
   regarder en utilisateur** : chaque texte tient-il, est-il traduit, sonne-t-il comme le reste ?
