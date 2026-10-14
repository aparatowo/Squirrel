# Synchronisation Bluetooth - conception

*[English](../en/bluetooth.md) · [Polski](../pl/bluetooth.md) · Français · [Deutsch](../de/bluetooth.md)*

Comment les appareils Squirrel! se synchronisent par Bluetooth Low Energy, tel que construit en 2.0. Les enregistrements
et leur codage : [data-format.md](data-format.md). Pour les utilisateurs :
[guides/fr/bluetooth.md](../../guides/fr/bluetooth.md). Questions ouvertes : [backlog.md](backlog.md).

## 1. Les choix, et pourquoi

| Choix | Pourquoi |
|---|---|
| Le module `bluetooth` brut de MicroPython (gestionnaire IRQ + `tick()`), pas `aioble` | `aioble` n'est pas dans le firmware, et l'application n'a pas d'asyncio : elle tourne sur une seule boucle principale de services appelés tour à tour. Un gestionnaire IRQ qui ne fait que mettre en file, et un `tick()` qui fait le travail, vont avec cette boucle et demandent moins de RAM. |
| Un seul protocole dans `ble/` pour chaque appareil ; le rôle vient de `features.toml` | La pile Bluetooth (NimBLE) est la même sur l'ESP32 et l'ESP32-S3 ; les appareils ne diffèrent que par leur rôle (chef / nœud) et par les données qu'ils ont. |
| Un modèle JSON canonique + un seul codage binaire dans les airs | Chaque implémentation - l'application téléphone, une version en C sur une petite montre - a les mêmes enregistrements ; dans les airs, un codec compact sans besoin d'analyseur JSON. |
| Un seul ensemble `SETTINGS` sous la forme texte de `config.txt` | L'application a déjà un schéma avec validation (`appconfig_schema.py`) ; un nouveau réglage n'a pas besoin d'une nouvelle caractéristique. |
| Des sessions de synchronisation, pas une radio toujours allumée | Un ESP32 ne peut pas faire de veille légère avec le contrôleur BT allumé, et un sommeil profond coupe la radio : annoncer en permanence mangerait la batterie de la montre. La radio n'est allumée que pour une session, comme le Wi-Fi pour l'heure. |
| La meilleure horloge règle la moins bonne | Le Cardputer n'a souvent pas d'horloge matérielle ; la montre en a une. L'heure va de l'heure Wi-Fi > horloge matérielle > réglée à la main > l'horloge logicielle. |
| Un appairage avec un code dans l'application, pas (encore) le chiffrement de la liaison | Voir la section 6. |

## 2. Les rôles

Un appareil de l'ensemble est le **chef** (`head` dans le code : `BleHead`, `ble_head_screen.py`, `features.toml`
`ble_hub` ; sur les écrans : les nœuds attendent *l'écureuil*, qui cherche des *noisettes*) - le seul auteur du contenu
(le Cardputer : il a le clavier). Les autres sont des **nœuds**. Un nœud accepte une connexion à la fois.

```
   Web Bluetooth page (phone / computer)
            │  connects to the boss (or to a node)
            ▼
   BOSS: Cardputer - central towards the nodes; peripheral towards the page ("Be visible")
    ├── T-Watch        - node (peripheral)
    └── (other watches later - nodes too)
```

| Données | Chef | Nœud (montre) | Page web |
|---|---|---|---|
| Contenu des tâches / listes à cocher | écrit | lit | écrit (par le chef) |
| Coches des tâches et des éléments | ✅ | ✅ | ✅ |
| Routines : texte, heure, jours, appareils | écrit | lit | écrit (par le chef) |
| Routine activée / désactivée | ✅ | ✅ | ✅ |
| Statistiques, journal des routines | les siennes / celles de chaque nœud / ensemble | les siennes, rapportées | - |
| Réglages synchronisés | ✅ | du chef | ✅ |
| Heure | selon la qualité de l'horloge | selon la qualité de l'horloge | la règle depuis le téléphone |

## 3. Profil GATT

Un seul service pour toute la famille ; les caractéristiques partagent la base et diffèrent par le deuxième groupe de
chiffres. Base : `beeaXXXX-f159-4fd4-b434-1d8d3db5b0bc`.

| `XXXX` | Nom | Propriétés | Contenu |
|---|---|---|---|
| `0000` | service Squirrel! | - | annoncé : c'est ainsi qu'un scanner reconnaît la famille |
| `0001` | `INFO` | R | version du protocole, type d'appareil, masque des capacités, slot, nom, version de l'application |
| `0002` | `TIME` | R / W | heure locale, décalage UTC, source et âge de l'horloge ; rafraîchi chaque seconde ; une écriture règle l'horloge (chefs appairés seulement) |
| `0003` | `SETTINGS` | R | la révision des réglages (les réglages eux-mêmes par `CONTROL`, ensemble `0x03`) |
| `0004` | `ROUTINES` | R | révision des routines |
| `0005` | `TODO` | R | révision des tâches |
| `0006` | `STATS` | R | révision des statistiques |
| `0007` | `STATUS` | R / N | réservé : mode, état du minuteur, batterie |
| `0008` | `CONTROL` | W / N | requêtes et réponses : liste, lire, écrire, supprimer, appairage ([data-format.md](data-format.md) §4) |
| `0009` | `NOTES` | R | révision des notes (appareils avec notes seulement) |
| `000a` | `EVENTS` | R | révision du journal des routines |

Bits de capacité dans `INFO` : 0 horloge matérielle, 1 tâches, 2 routines, 3 statistiques, 4 Pomodoro, 5 respiration,
6 coucou, 7 pas, 8 hub, 9 notes. Le chef ne synchronise que ce qu'un nœud annonce.

## 4. Une session

1. Le nœud annonce le service pendant une fenêtre (2 minutes depuis son écran Bluetooth, 90 s pour une
   synchronisation automatique).
2. Le chef se connecte tour à tour à chaque nœud connu (il les garde dans `ble.json` : adresse, slot, dernière
   synchronisation).
3. Échange de MTU, découverte des services, `INFO` (version du protocole), notifications sur `CONTROL`.
4. **Appairage / preuve** (section 6).
5. **L'horloge :** la meilleure règle l'autre (pas d'écriture si elles sont d'accord à 2 secondes près).
6. **Rejoindre :** un nœud dont le slot diffère reçoit son slot (`PUT` sur l'ensemble `INFO`). Ses enregistrements
   d'avant - copiés par USB, par exemple - passent sur ce slot et deviennent ses enregistrements locaux.
7. **Réglages :** le chef écrit les clés synchronisées qui diffèrent (`ble/protocol.SYNCED_KEYS`).
8. **Enregistrements** - routines, tâches, notes : d'abord la liste de chaque ensemble chez le nœud (id, heure de
   modification `e`, heure d'état `c`), puis seulement les enregistrements qui diffèrent, dans les deux sens
   (section 5).
9. **Rapports :** les statistiques du nœud (les 60 derniers jours) et son journal des routines depuis la dernière
   synchronisation ; le chef les garde par nœud dans `focus/peers/<slot>/`.
10. Déconnexion. Le nœud reste visible encore 15 s, pour une deuxième passe.

**La deuxième passe :** après la première, le chef a tout, mais le nœud synchronisé en premier ne connaît pas encore les
changements d'état apportés par les suivants (une coche sur la montre, pour l'appareil suivant). Le chef se reconnecte
aux nœuds dont les listes diffèrent encore - et à ceux qui ont échoué à la première passe.

Un enregistrement passe en morceaux et est pris en entier ou pas du tout : une connexion coupée n'abîme rien, et un
seul enregistrement est en mémoire à la fois.

## 5. Qui a raison

Pour chaque enregistrement (`ble/merge.py`) :

- **Le contenu** des enregistrements du chef (slot 0 dans l'id) vient toujours du chef. Un enregistrement du chef absent
  de la liste du chef est supprimé sur le nœud.
- **L'état** - une routine activée / désactivée, une tâche faite, un élément coché - vient de la copie où il a changé
  le plus tard (`c`). Chaque élément d'une liste a son heure à lui, donc cocher des éléments différents sur deux
  appareils ne crée pas de conflit.
- **Les enregistrements locaux d'un nœud** (son slot dans l'id) ne sont jamais modifiés, supprimés ni pris par le chef.

Les horloges ne décident que de l'état (un conflit, ce sont deux coches différentes d'un même enregistrement : rare et
sans gravité) ; le contenu ne dépend pas de l'heure, une horloge fausse ne peut donc pas écraser une modification.

**Listes à cocher :** les lignes d'une tâche qui commencent par `>` sont ses éléments. On les reconnaît au contenu, pas
au titre, elles marchent donc pareil sur chaque appareil ; les coches sont gardées à côté du fichier (`todo/done.dat`),
le texte ne change donc jamais.

**Routines sur certains appareils :** le champ `to` d'une routine est un masque de bits des slots (bit n = slot n ;
255 = chaque appareil, y compris ceux ajoutés plus tard). Chaque appareil ne déclenche que les routines qui ont son bit.

## 6. Appairage et sécurité

**En 2.0 : appairage dans l'application** (`ble/auth.py` ; les commandes dans [data-format.md](data-format.md) §4).

- **Appairage (une fois) :** le chef envoie un nonce aléatoire (`AUTH_HELLO`) ; le nœud répond avec le sien et affiche
  un code à 6 chiffres ; l'utilisateur le tape sur le chef ; les deux dérivent
  `K = HMAC-SHA256(code, "squirrel-pair" + nonces)[:16]`, et le chef prouve qu'il l'a (`AUTH_CONFIRM`). Le code
  lui-même ne passe jamais dans les airs.
- **Chaque session :** le nœud donne un nouveau défi à usage unique (`AUTH_CHALLENGE`) ; le chef répond
  `HMAC(K, "session" + challenge)` (`AUTH_PROVE`). Jusque-là, le nœud refuse tout (erreur 6) sauf la lecture de `INFO`
  et `TIME`, et ignore une écriture de l'heure.
- **Clés :** `ble_auth.json` sur la flash interne - jamais sur une carte amovible. Oublier un appareil sur le chef
  supprime sa clé ; un nœud qui a perdu sa clé demande un nouveau code. La page Web Bluetooth garde sa clé dans le
  `localStorage` du navigateur, par appareil.

> ⚠️ **Ce que cela ne protège pas.** Les enregistrements passent **en clair** : quelqu'un à portée radio avec du
> matériel d'écoute BLE peut les lire pendant une synchronisation (pas les modifier, ni synchroniser un appareil sans
> la clé). Un appairage intercepté permet de retrouver la clé hors ligne (le code a 6 chiffres). Les guides disent aux
> utilisateurs d'appairer loin des inconnus et de ne pas mettre de secrets dans les notes synchronisées.

**Le chiffrement de la liaison (LE Secure Connections)** est dans le code mais désactivé
(`nuts.BLE_LINK_PAIRING = False`) : un passkey affiché sur le nœud, des liaisons gardées par l'application
(`ble/secrets.py`, `GET_SECRET` / `SET_SECRET` de l'IRQ), et une correction de NimBLE pour les événements passkey du
central (`firmware_patches/0001-nimble-central-passkey.patch`). Cela marchait, mais le Cardputer se réinitialisait
pendant certaines sessions - ce qui s'est révélé être un autre bug (backlog A).

## 7. Synchronisation automatique

`BLE_AUTO_SYNC_MIN` (0 = sur demande ; 15 ... 240) - `ble/auto.py`. Les sessions sont alignées sur l'horloge : les
minutes de la journée divisibles par la période. Le nœud est une source d'alarmes (`alarms.py`), donc une montre en
sommeil profond se réveille pour chaque créneau et annonce pendant 90 s ; le chef commence 20 s après le début du
créneau. Un créneau est sauté quand la radio est occupée (un écran Bluetooth, la synchronisation de l'heure par Wi-Fi)
ou quand un nœud doit être appairé (cela demande l'utilisateur). Un écran Bluetooth ouvert pendant une session
automatique l'arrête. Le réglage est synchronisé depuis le chef, les nœuds le suivent donc.

## 8. MicroPython sur l'ESP32 : à savoir

- Le gestionnaire IRQ tourne sur la pile de la tâche NimBLE, au milieu de son travail. Les données qu'il reçoit - le
  tuple, les adresses, les tampons, **les objets UUID** - ne sont valables que pendant l'appel : tout ce qu'on garde est
  copié (`bytes(...)`, `bluetooth.UUID(...)`). **`tuple(data)` n'est pas une copie** : MicroPython renvoie le même
  tuple, et le garder réinitialisait le Cardputer à des moments aléatoires d'une synchronisation jusqu'à ce qu'on le
  trouve (`tuple(list(data))` copie).
- Pas de générateurs ni d'analyse dans le gestionnaire ; c'est `tick()` qui le fait. Le gestionnaire doit répondre à
  `GET_SECRET` / `SET_SECRET` (ne rien renvoyer à `SET_SECRET` réinitialisait le Cardputer).
- Pendant que la radio travaille, le ramasse-miettes automatique est coupé et `tick()` ramasse depuis la boucle
  principale (`radio_gc`) : un ramassage déclenché par une allocation dans l'IRQ tournait sur la petite pile de la
  tâche NimBLE.
- Les services en arrière-plan sont suspendus pendant une session (`ServiceManager.paused`), pour que la boucle
  principale réponde vite à la radio.
- Couper la radio juste après une session entrait en concurrence avec les minuteurs de NimBLE : `_settle()` attend
  d'abord 100 ms.

## 9. Le code

```
ble/protocol.py     UUIDs, record codecs, frames, SYNCED_KEYS - plain Python, tested on the PC
ble/merge.py        boss copy + node copy -> the result (content from the boss, state by time, local untouched)
ble/peripheral.py   the node: GATT server, IRQ, parts, pairing answers, tick()
ble/central.py      the boss: scan, connect, the session as a generator driven by tick()
ble/node_data.py    the app's data as records (routines, To-Dos, notes, settings, statistics, time)
ble/peers.py        the boss's devices (ble.json) and their reports (focus/peers/<slot>/)
ble/auth.py         pairing with a code, the proof of every session, the key store
ble/secrets.py      the bonds of link pairing (off)
ble/auto.py         automatic sync on the clock
screens/ble_head_screen.py   the boss's Bluetooth screen (devices, Add device, Sync now, Auto sync, quick sync)
screens/ble_sync_screen.py   the node's Bluetooth screen (waiting, the pairing code)
tools/web/                   the Web Bluetooth page and its JavaScript codec
```

`features.toml` : `ble_sync` (chaque port avec `[radio] ble = true` : la partie nœud), `ble_hub` (un port qui a aussi
un clavier : la partie chef).

## 10. Pas encore construit

- **Modifications sur un nœud** (un téléphone relié à la montre) : appliquées tout de suite, gardées comme
  *propositions* avec la version sur laquelle elles ont été faites ; le chef décide à la synchronisation suivante -
  acceptée s'il n'a pas changé cet enregistrement entre-temps, conflit sinon ; les nouveaux enregistrements restent
  locaux ou sont adoptés. Un `SYNC_MODE` *auto* / *ask* avec un écran des différences (envoyer / prendre / passer par
  catégorie). L'ensemble `0x0B` lui est réservé.
- **Un nouveau chef :** reprendre une copie complète des enregistrements du chef depuis n'importe quel nœud, avec les
  identifiants et les compteurs, et appairer à nouveau les nœuds.
- **Petits appareils :** le protocole est pensé pour pouvoir être implémenté en C sans allocation dynamique.
