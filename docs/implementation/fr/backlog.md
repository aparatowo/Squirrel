# Backlog

*[English](../en/backlog.md) · [Polski](../pl/backlog.md) · Français · [Deutsch](../de/backlog.md)*

Ce qu'on sait ne pas aller, ce qui n'est pas encore construit, et ce qui était prévu puis a été fait autrement. État de
la version 2.0. Les utilisateurs voient la première partie comme les limites connues des
[notes de version](../../releases/README.md).

## Problèmes connus

### A. Le chiffrement de la liaison est désactivé

Les enregistrements Bluetooth passent dans les airs en clair ; seul l'appairage avec un code dans l'application les
protège contre une modification (voir [bluetooth.md](bluetooth.md) §6). LE Secure Connections est dans le code
(`nuts.BLE_LINK_PAIRING = False`, `ble/secrets.py`, `firmware_patches/0001-nimble-central-passkey.patch`) et a marché
sur les appareils, mais le Cardputer se réinitialisait pendant certaines sessions.

Ces réinitialisations se sont révélées être un autre bug (2026-10-13) : le gestionnaire IRQ du chef mettait en file
`tuple(data)`, et en MicroPython `tuple()` d'un tuple renvoie **le même objet** - le tuple de l'IRQ, sur la pile de la
tâche NimBLE, écrasé par la radio avant que `tick()` ne le lise. Corrigé (`tuple(list(data))`) ; 55 synchronisations
sans réinitialisation depuis. Avec le chiffrement de la liaison après la correction : 5 synchronisations sur 5, puis un
blocage à la sixième (pas de panique, l'USB n'acceptait plus de données).

Suite : une série avec `tools/hwtest/ble_e2e.py --link`, expliquer le blocage, puis `BLE_LINK_PAIRING = True`
(l'appairage dans l'application reste, comme preuve que c'est ton chef ; le chiffrement ferme l'écoute et le cassage
du code hors ligne). Vérifier au passage si `radio_gc` (pas de ramasse-miettes automatique pendant une session) est
encore nécessaire.

### B. Un blocage rare du Cardputer

Environ une fois sur 70 synchronisations (2026-10-13) : `mp_task` attendait dans
`spi_flash_disable_interrupts_caches_and_other_cpu` (une lecture ordinaire de la flash) le cœur 0, qui servait les
interruptions mais pas les tâches. La cause n'est pas connue ; le contrôleur Bluetooth tourne sur le cœur 0.

Atténuation : le chien de garde de la boucle principale (`nuts.WATCHDOG_S`, 60 s) redémarre l'appareil ; les données
restent. Le firmware enregistre alors ce que faisait le cœur 0 (`firmware_patches/0002-panic-record.patch`) ; la
prochaine fois, le lire avec `tools/hwtest/panic_record.py` et chercher la cause.

### C. "pas de réponse" juste après la connexion

Parfois le chef n'obtient pas de réponse à la découverte des services (7 sur 30 dans une série, 0 sur 25 dans la
suivante). Le message dit quels événements il attendait. Atténuation : la deuxième passe d'une synchronisation
réessaie les appareils qui ont échoué.

### D. Les captures du Cardputer utilisent la police de la montre

`tools/sim/render_shots.py` dessine le texte avec la police 6 × 8 de `drivers/glcdfont.py` (+ `glcdfont_latin.py`),
alors qu'un Cardputer dans une autre langue que l'anglais utilise `squirrel.vlw`. Les images des guides sont justes
pour la mise en page et les mots, un peu différentes pour la forme des lettres. Correction : dessiner les glyphes
`.vlw` dans `render_shots.py` (`vlw.py` sait les lire).

### E. Un nœud garde une seule clé d'appairage

`ble/peripheral.py` garde une clé par nœud (`"head"` dans `ble_auth.json`) : appairer la page web avec la montre
remplace la clé du Cardputer, et le Cardputer demande un nouveau code à sa prochaine synchronisation (et inversement).
Documenté pour les utilisateurs ; une correction garderait quelques clés et accepterait la preuve de n'importe laquelle
- sans changement dans les airs ni dans la page.

## Pas encore construit

- **Modifications sur un nœud** (un téléphone relié à la montre) : gardées comme propositions avec la version sur
  laquelle elles ont été faites ; le chef décide à la synchronisation suivante. Un `SYNC_MODE` *auto* / *ask* avec un
  écran des différences (envoyer / prendre / passer par catégorie). L'ensemble `0x0B` est réservé
  ([bluetooth.md](bluetooth.md) §10).
- **Un nouveau chef** : reprendre une copie complète des enregistrements depuis n'importe quel nœud, avec identifiants
  et compteurs, et appairer à nouveau les nœuds.
- **La page Web Bluetooth** (`Squirrel!/tools/web/`) : son codec est vérifié contre `protocol.py` sur le PC ; avec la
  montre (Chrome, la page ouverte depuis le disque), connexion, appairage et lecture marchent (`tools/hwtest/web_e2e.py`) ;
  la modification depuis la page n'est pas encore essayée. Publication sur GitHub Pages pour les téléphones :
  `.github/workflows/web-page.yml`, prête, pas activée.
- **La montre ESP32-S3 générique** (`ports/generic_s3_watch`) : se compile, pas encore essayée sur une montre.
- **Le son et le micro de la montre, l'accéléromètre** (toujours seulement éteint au démarrage).
- **Idées de la feuille de route :**
  - le filtre *Aujourd'hui* sur la liste des tâches ;
  - des étiquettes d'émotion sur une entrée (🔥 urgent, 💡 idée, 😰 stress, 🕑 un jour) ;
  - une vue de concentration sur une seule tâche (*Ce que je fais maintenant* : une tâche, en grand) ;
  - des horodatages automatiques sur les notes ;
  - revenir à la dernière note ouverte après un redémarrage ;
  - un mode clé USB (la carte SD vue depuis un ordinateur) ;
  - un mode ultra-économie.

## Fait autrement

| Prévu | Comment c'est fait |
|---|---|
| Quick Capture (FN+SPACE depuis l'horloge) | le menu TAB de l'horloge : **TAB, M** - Vide-tête, **TAB, T / N** - une tâche / une note ; **G0** enregistre une note vocale aussitôt |
| Un micro serveur web sur la montre, pour les routines depuis un téléphone | la page Web Bluetooth : pas de serveur Wi-Fi, elle parle directement aux appareils |
| Un port vers les montres programmables | le port T-Watch 2020 V3 (2.0), le port expérimental ESP32-S3 générique |
| La coopération avec le Cardputer | la synchronisation Bluetooth (2.0) |
