# Le format de données commun

*[English](../en/data-format.md) · [Polski](../pl/data-format.md) · Français · [Deutsch](../de/data-format.md)*

Les enregistrements de toute la famille Squirrel! : le Cardputer, la T-Watch et toute application future (sur
téléphone, par exemple). Version du format : **1**. Implémentation de référence : `Squirrel!/ble/protocol.py` (et son
jumeau JavaScript `Squirrel!/tools/web/squirrel_protocol.js`, vérifié octet par octet par
`tools/tests/test_web_protocol.py`). Comment la synchronisation s'en sert : [bluetooth.md](bluetooth.md).

## 1. Le principe

- **Le modèle canonique est JSON.** Chaque enregistrement a une seule définition : noms des champs, types, plages
  (section 3). C'est ainsi qu'il apparaît dans les fichiers JSON sur l'ESP32, dans une application téléphone, dans les
  tests.
- **Le Bluetooth transporte un codage binaire** du même modèle (section 4) - champ pour champ, sans perte. Un petit
  appareil n'a pas besoin d'analyser du JSON : il garde des structures C qui correspondent au codage binaire.
- Chaque appareil peut stocker les données à sa façon (fichiers texte, `done.dat`, structures C). Cette spécification
  ne dit que ce qui est à l'extérieur ; la correspondance avec les fichiers de l'ESP32 est en section 5.
- Les champs inconnus sont ignorés, pas refusés (une version plus récente sur un appareil ne casse pas une plus
  ancienne sur un autre). Les nouveaux champs n'arrivent que comme facultatifs. Un changement de sens d'un champ est une
  nouvelle version du format.

## 2. Champs et règles communs

| Champ | Type | Sens |
|---|---|---|
| `id` | int 1-65535 | L'identifiant de l'enregistrement. Bits 15-13 : le **slot** de l'auteur - 0 = un enregistrement du **chef**, 1-6 = un enregistrement **local** du nœud de ce slot, 7 = réservé. Bits 12-0 : le compteur de l'auteur. Le chef attribue les slots quand les nœuds rejoignent l'ensemble. |
| `e` | int | Heure de la dernière **modification du contenu** - la version du contenu (comparée pour les propositions, 3.8). |
| `c` | int | Heure du dernier **changement d'état** (activé / fait / coché). Une modification du contenu ne le change pas. |
| `del` | bool | Réservé (une pierre tombale). Pas utilisé avec un chef : le chef supprime par sa liste. |

- **L'heure** = secondes depuis le 1970-01-01 00:00 en **heure locale** de l'appareil (pas UTC ; le décalage est dans
  `TIME`). 0 = "jamais".
- **Le texte** = UTF-8. Les limites sont en caractères (comme sur les écrans) ; dans le codage binaire, en octets
  (section 4).
- **Le chef et les nœuds.** Un appareil de l'ensemble est le **chef** (le Cardputer par défaut) : le seul auteur du
  contenu des enregistrements de slot 0. Les autres sont des **nœuds**. Fusion de deux copies (`ble/merge.py`), pour
  chaque `id` :
  - le contenu des enregistrements du chef - toujours du chef ; un enregistrement du chef absent de la liste du chef
    est supprimé sur le nœud ;
  - l'état - de la copie avec le plus grand `c` (une coche sur la montre arrive au chef et repart de là) ;
  - les enregistrements locaux d'un nœud (slot ≠ 0) - le chef ne les modifie pas, ne les supprime pas et ne les prend
    pas (adoption : 3.8).
  Les horloges ne décident donc que de l'état ; le chef décide du contenu, et la version `e` détecte les conflits de
  modification (3.8).
- **Le jour de la semaine** est calculé à partir de la date, jamais pris dans `localtime()[6]` (les firmwares ESP32 ne
  sont pas d'accord là-dessus).

## 3. Les enregistrements (JSON)

### 3.1 Routine - `routine`

```json
{"id": 8193, "t": "Pills", "h": 8, "m": 0, "d": 63, "on": true, "to": 255, "e": 1760259600, "c": 1760259600}
```

| Champ | Type | Plage | Sens |
|---|---|---|---|
| `t` | str | ≤ 50 caractères | le texte du rappel |
| `h`, `m` | int | 0-23, 0-59 | l'heure |
| `d` | int | 0-127 | les jours de la semaine, bit 0 = lundi ... bit 6 = dimanche |
| `on` | bool | | activée (état : un changement met à jour `c`) |
| `to` | int | 0-255 | les appareils où elle apparaît : bit n = slot n ; 255 = tous |

### 3.2 Tâche - `todo` (aussi une liste à cocher)

```json
{"id": 2, "t": "Shopping\n> milk\n> bread", "done": false, "e": 1760259600, "c": 0,
 "items": [{"t": "milk", "done": true, "c": 1760260000}]}
```

| Champ | Type | Plage | Sens |
|---|---|---|---|
| `t` | str | ≤ 500 caractères | tout le texte ; la première ligne est le titre |
| `done` | bool | | faite (état) |
| `items` | list | ≤ 64 | listes à cocher seulement : l'état de leurs éléments (les lignes `>`) |
| `items[].t` | str | ≤ 100 caractères | le texte de l'élément - la clé qui le désigne |
| `items[].done`, `items[].c` | bool, int | | l'état de l'élément et l'heure de son changement (fusionnés par élément, comme les enregistrements) |

**Une liste à cocher** (une liste de courses, les étapes d'une tâche ...) : les lignes après le titre qui commencent par
`>` sont des éléments cochés un par un (le texte de l'élément = la ligne sans le `>` ni les espaces autour). Les autres
lignes sont du texte simple. Une tâche sans lignes `>` se coche en entier. Quand chaque élément est coché, `done` =
true.

### 3.3 Note - `note`

```json
{"id": 3, "t": "Remarks\nthe first line is the title", "e": 1760259600}
```

| Champ | Type | Plage | Sens |
|---|---|---|---|
| `t` | str | ≤ 2000 caractères | tout le texte ; la première ligne est le titre |

Une note n'a pas d'état (`c`).

### 3.4 Statistique d'un jour - `stat`

```json
{"day": "2026-10-12", "k": "focus_min", "n": 95}
```

| Champ | Type | Sens |
|---|---|---|
| `day` | str `YYYY-MM-DD` | le jour |
| `k` | str | `routines` (routines faites), `todos` (tâches faites), `focus_min` (minutes de concentration), `steps` |
| `n` | int 0-65535 | la valeur de ce jour sur cet appareil |

Les statistiques ne sont pas fusionnées : chaque appareil est la seule source des siennes ; le chef les garde à part
par slot.

### 3.5 Réglages - `settings`

Un objet `{KEY: value}` avec les noms de clés du schéma des réglages (`appconfig_schema.py`). Seulement les clés
synchronisées (`ble/protocol.py: SYNCED_KEYS`) :

| Clés | Type |
|---|---|
| `CUCKOO_ENABLED`, `CUCKOO_QUARTERS` | bool |
| `CUCKOO_QUARTER_VOLUME` | int 0-100 |
| `POMODORO_WORK_MIN` (1-90), `POMODORO_BREAK_MIN` (1-30), `POMODORO_LONG_BREAK_MIN` (1-60), `POMODORO_CYCLES` (1-8) | int |
| `ROUTINE_SNOOZE_MIN` | int 1-60 |
| `QUIET_SOUND_FROM`, `QUIET_SOUND_TO` | str `HH:MM` |
| `QUIET_SOUND_DAYS` | str de 7 caractères, `MTWTFSS`, `.` = un jour non coché |
| `TRAINING_PLAN` | une liste `[[colour, seconds], ...]`, ≤ 16 blocs, couleurs : `blue yellow orange red green` |
| `BLE_AUTO_SYNC_MIN` | int 0-240 (0 = synchronisation sur demande seulement) |

Les réglages forment un tout pour l'appareil, sans `id` ; ceux du chef sont écrits sur les nœuds.

### 3.6 Événement de routine - `event` (le journal des routines)

```json
{"r": 8193, "at": 1760259600, "res": "done"}
```

| Champ | Type | Sens |
|---|---|---|
| `r` | int | l'`id` de la routine |
| `at` | int | l'heure prévue de la routine (heure locale) |
| `res` | str | `done`, `skip` (passée), `missed` (pas de réponse, même après les reports) |

Un nœud garde les événements 60 jours et les rapporte au chef ; le chef ne prend que ceux d'après la dernière
synchronisation. Les événements ne sont pas fusionnés : chacun a une seule source (le nœud) ; le chef les garde à part
par slot.

### 3.7 Heure - `time`, l'appareil - `info`, l'état - `status`

```json
{"time": 1760270400, "offset": 120, "source": "rtc", "age": 10, "has_rtc": true, "rtc_valid": true}
{"version": 1, "kind": "twatch", "caps": ["rtc", "routines", "todo", "stats", "steps"], "name": "T-Watch", "app": "2.0", "slot": 1}
```

`source` : `soft`, `manual`, `rtc`, `ntp`, `peer`. `kind` : `cardputer`, `twatch`, `web` (le code 3 est réservé).
`caps` : `rtc todo routines stats pomodoro breathing cuckoo steps hub notes`. `status` (mode, minuteur) : réservé.

### 3.8 Proposition - `proposal` (réservé, une étape ultérieure)

Un changement de contenu fait sur un nœud (un éditeur relié directement au nœud) : il agit tout de suite sur le nœud et
attend la décision du chef.

```json
{"op": "edit", "set": "routine", "id": 1, "base": 1760259600, "rec": {"...": "a record of 3.1"}}
```

| Champ | Sens |
|---|---|
| `op` | `edit` (un enregistrement du chef), `new` (un nouvel enregistrement - local jusque-là), `delete` |
| `base` | le `e` de l'enregistrement du chef sur lequel le changement a été fait. Le chef l'accepte sans demander si son propre `e` est toujours le même ; sinon c'est un conflit (auto : le chef gagne ; "ask" : l'utilisateur décide) |

Le codage binaire viendra avec l'implémentation (l'ensemble `0x0B` est réservé).

## 4. Le codage binaire (Bluetooth)

Petit-boutiste. `str8` = longueur u8 en octets + UTF-8 ; `str16` = u16 + UTF-8. Le texte n'est coupé que sur une
limite de caractère. Heure = u32. Drapeaux communs : bit 7 = `del` (une pierre tombale : après les drapeaux seulement
`e`, le reste à zéro / vide).

```
routine   u16 id | u8 flags (b0 on, b7 del) | u8 h | u8 m | u8 d | u8 to | u32 e | u32 c | str8 t
todo      u16 id | u8 flags (b0 done, b7 del) | u32 e | u32 c | str16 t
          | u8 number of items | item: u8 flags (b0 done) | u32 c | str8 t
note      u16 id | u8 flags (b7 del) | u32 e | str16 t
stat      u16 day (days since 1970-01-01) | u8 k (0 routines, 1 todos, 2 focus_min, 3 steps) | u16 n
event     u16 r | u32 at | u8 res (0 done, 1 skip, 2 missed)
list      u16 id | u8 flags (b7 del) | u32 e | u32 c           - one entry per record, no content
time      u32 time | i16 offset | u8 source (0 soft, 1 manual, 2 rtc, 3 ntp, 4 peer) | u32 age
          | u8 flags (b0 has_rtc, b1 rtc_valid)
info      u8 version | u8 kind (1 cardputer, 2 twatch, 3 reserved, 4 web) | u16 caps (bits in the order of 3.7)
          | u8 slot | str8 name | str8 app
settings  UTF-8 text, lines KEY=value (as in config.txt); TRAINING_PLAN = "blue:120,yellow:180,..."
```

### Le canal `CONTROL` - déplacer les enregistrements

```
request (write):        u8 cmd  | u8 set | u16 id | u16 part | u8 flags (b0 last) | data
answer (notification):  u8 code | u8 set | u16 id | u16 part | u8 flags (b0 last) | data

cmd   0x01 LIST   - a set's list: a header (u8 format, u32 revision, u16 count) + "list" entries
      0x02 GET    - one record (id)
      0x03 PUT    - one record (id) in parts; taken after the last part, whole or not at all
      0x04 DELETE - a boss record (id) removed from a node; from the boss only, never a node's local records
      0x05 AUTH_HELLO     - pairing: data 16 B boss nonce -> DATA 16 B node nonce; the node shows 6 digits
      0x06 AUTH_CONFIRM   - pairing: data 16 B proof (below) -> ACK or ERR 7; the node keeps the key
      0x07 AUTH_CHALLENGE - every session: -> DATA 16 B challenge (used once)
      0x08 AUTH_PROVE     - every session: data 16 B answer -> ACK or ERR 6
      (the AUTH_* requests have set 0x01 and id 0)
code  0x10 DATA (the answer to LIST / GET, in parts), 0x11 ACK, 0x12 ERR (data: u8 error code)
errors 1 unknown set, 2 a part out of order, 3 too big, 4 bad data, 5 no such record,
       6 not paired (no AUTH_PROVE in this session), 7 a wrong code when pairing
set   0x01 info (PUT with id = slot: the node joins), 0x03 settings (GET / PUT with id 0; text as above),
      0x04 routines, 0x05 To-Dos, 0x06 statistics, 0x09 notes, 0x0A events, 0x0B proposals (reserved)
```

Les statistiques et les événements n'ont pas d'`id` : la réponse à `LIST` contient les enregistrements eux-mêmes
(`stat` : les 60 derniers jours ; `event` : ceux d'après l'heure donnée dans les données de la requête `LIST`, u32 - le
chef se souvient de jusqu'où il a lu). Les routines peuvent aussi être obtenues par un seul `GET` d'`id` 0 (tous les
enregistrements dans une réponse) - elles sont petites.

### Appairage et preuve d'une session (`ble/auth.py`)

HMAC = HMAC-SHA256 coupé à 16 octets ; textes en ASCII, `+` joint des octets.

```
key      K   = HMAC(the code as 6 ASCII digits, "squirrel-pair" + boss nonce + node nonce)
CONFIRM      = HMAC(K, "confirm" + node nonce)
PROVE        = HMAC(K, "session" + challenge)
```

Le code ne passe jamais dans les airs. Un nœud garde une clé (`"head"`), le chef une clé par nœud (par adresse) ; les
deux dans `ble_auth.json` sur la flash interne. Tant que `AUTH_PROVE` n'a pas réussi dans une session, un nœud répond
ERR 6 à toute autre requête et ignore une écriture de `TIME` ; `INFO` et `TIME` se lisent sans appairage. **Les
enregistrements passent en clair** - voir [bluetooth.md](bluetooth.md) §6.

## 5. Correspondance avec les fichiers de l'ESP32

| Enregistrement | Fichier | Remarques |
|---|---|---|
| routine | `routines.json` - une liste des objets JSON de 3.1 | les fichiers plus anciens sans `id`, `to`, `e`, `c` : à la lecture, ils reçoivent un `id` (un compteur du chef), `to` = 255, `e` = `c` = 0 |
| event | `focus/events.txt` - lignes `r,at,res` | 60 jours ; sur le chef : `focus/peers/<slot>/events.txt` |
| todo | `todo/<name>.txt` (le texte), `todo/done.dat` (`name,date` = faite ; `name#item,date` = un élément coché), `todo/meta.json` (`{name: {id, e, c, items: {item: c}}}`) | les fichiers sans entrée dans `meta.json` (d'avant 2.0, copiés par USB) : `e` = `c` = 0, l'`id` donné à la première liste |
| note | `notes/<name>.txt`, `notes/meta.json` (`{name: {id, e}}`) | |
| stat | `focus/routines.txt`, `focus/todos.txt`, `focus/focus.txt` (secondes -> minutes), pas | `focus/peers/<slot>/` - les statistiques des autres appareils sur le chef |
| settings | `config.txt` | |

Pas des enregistrements (pas encore) : le journal des réussites, `wins/AAAA-MM-JJ.txt` (un jour : la date, puis des
lignes `-` / `>` = choses faites) reste sur l'appareil. `focus/focus.txt` peut avoir des lignes négatives
(`2026-10-19,-900`) : du temps de concentration retiré ; les lignes d'un jour s'additionnent, jamais sous zéro.
