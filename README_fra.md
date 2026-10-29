<p align="center">
  <img src="/images/URTC_FLASHER_BANNER.svg" alt="URTC Flasher Logo" width="100%">
</p>

# URTC Flasher (Windows / Linux)

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  🇫🇷 <b>Français</b> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Met à jour le firmware d'une carte URTC par CAN (CAN-OTA) et programme la puce entière par SWD/JTAG, sous Windows et Linux

<p align="center">
  <img src="https://img.shields.io/badge/Licence-GPL%203.0-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Langage-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Tests-500-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Protocole-CAN--OTA-orange.svg" alt="CAN-OTA">
</p>

---

**Vérification d'honnêteté - ce qui fonctionne réellement aujourd'hui :** `tests/` contient 47 fichiers pytest (500 tests : tous réussis ; 79 d'entre eux sont ignorés sans PySide6) - le protocole CAN-OTA face à un vrai transport `MockCAN` (`flasher_transports.py`) qui rejoue une séquence complète de bootloader simulé (démarrage/effacement/réception, données de page + PAGE_ACK, blocs HMAC, fin de mise à jour avec un vrai succès ou un `VERIFY_FAIL_REASON` précis), les règles de signature (signature publiée envoyée sans aucune clé, image non signée refusée, sha256 du manifeste non conforme refusé avant tout trafic sur le bus), les contrôles d'intégrité d'image et le dossier `firmware/` fourni par rapport à ses manifestes. GitHub Actions (`.github/workflows/ci.yml`) exécute cette suite à chaque push, et `tools/build_test.py` l'exécute dans `build-test.sh`/`.bat`. Elle exécute aussi `ruff check` et `python -m mypy` (un contrôle des types du programme et des copies du code partagé). Les trois scripts `verify_qt_*.py` à la racine sont de vrais contrôles de bout en bout hors pytest (ils nécessitent une vraie boucle d'événements Qt ; lancement avec `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`) ; `verify_qt_swd_full_chip_flash.py` construit seulement les commandes `PyOCDCLI`/`CubeProgrammerCLI` avec `dry_run=True`. Rien de tout cela n'a été exécuté sur une vraie carte dans cet environnement. Voir `CHANGELOG.md` pour ce qui a réellement été publié. Le bootloader simulé (`MockCAN`) n'est qu'un modèle écrit à partir de la description du protocole : il reproduit les ACK de page, la dernière page partielle et les trames de relecture, mais ce n'est pas le vrai bootloader, donc une exécution de tests au vert ne remplace pas un essai sur une vraie carte (l'image officielle de 73476 octets ne pouvait pas être installée et la dernière trame d'une sauvegarde était perdue alors que les tests passaient, justement parce que la simulation était plus indulgente que le vrai bootloader).

---

> **État de la sûreté et de la cybersécurité :** cet écosystème n'est pas un système de sécurité certifié et aucune carte URTC assemblée n'existe encore. Les bootloaders contrôlent les images de firmware par CRC32 et un HMAC-SHA256 à clé partagée, pas par une signature asymétrique (prévue) ; les images d'application publiées sont signées avec la clé publique de développement (`signing_key_kind: dev`), si bien que n'importe qui peut produire une image acceptée par le bootloader ; rien n'a été transmis à une carte réelle. Lisez la [base de sécurité](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) et le [modèle de menaces](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) avant de vous fier à une affirmation d'ici pour la sécurité d'une personne.

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.4.1` |
| Maturité | Fonctionnel |
| Tests | 500 (`python -m pytest tests -q`) |
| Technologie | Python / PySide6 / Qt Quick / CAN-OTA / SWD/JTAG |
| Cible | Le PC de la personne qui l'utilise |
| Sur matériel réel | Simulé seulement : testé avec des émulateurs, des doubles de test ou des simulateurs ; aucune exécution sur du matériel réel n'est consignée pour cette version |

**Aller à :** [Présentation](#-présentation) · [Architecture](#-architecture) · [Fonctionnalités](#-fonctionnalités) · [Sécurité](#-sécurité-et-protection) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Démarrage rapide](#-démarrage-rapide) · [Tests](#-tests) · [Structure](#-structure-du-dépôt) · [Liés](#-projets-liés)

<!-- urtc-section:status_flasher -->
## 🚦 État du projet

🟢 fait et vérifié · 🟡 fonctionne, avec des limites connues · 🟠 à moitié fait ou non vérifié · 🔴 non fait ou non fonctionnel. Rien n'est vert si cela n'a jamais tourné sur du vrai matériel.

| Partie | État | Ce que le dépôt peut démontrer |
| --- | :---: | --- |
| Logiciel | 🟡 | Fonctionne sur un PC et face au simulateur ; jamais utilisé avec une vraie carte. |
| Interface | 🟡 | La fenêtre fonctionne et est vérifiée face à une carte simulée ; non essayée avec un vrai adaptateur. |
| Tests | 🟢 | La suite de tests passe dans la CI à chaque push. |
| Matériel réel | 🟠 | Pas encore d'essai sur une vraie carte : l'essai au banc reste à faire. |
| Sécurité | 🟡 | Les versions sont signées en Ed25519 et vérifiées avant usage ; la gestion des clés n'a été relue par personne d'autre. |
| Documentation | 🟡 | README en huit langues et documents de référence ; les traductions n'ont pas été relues par des locuteurs natifs. |

<!-- /urtc-section:status_flasher -->

## 🎯 Présentation

Un petit outil graphique multiplateforme pour mettre à jour le firmware
de la carte URTC via le bus CAN. Il implémente exactement le protocole
du bootloader de `docs/CANBUS.TXT` (dans le dépôt frère [URTC](https://github.com/JuanenRac/URTC) auquel cet outil se conforme - voir « Projets Liés » vers la fin de ce document ; toute autre référence à `docs/*.TXT` dans ce README y renvoie aussi) : la vérification du HardwareID, le HMAC-SHA256 à clé partagée (pas une signature asymétrique), le flux de mise à jour avec emplacement de
sauvegarde à image dorée, la progression en direct via les messages de
battement de cœur du bootloader, et une requête de version (identifie si
l'application *ou* le bootloader de cette carte s'annonce via CAN) pour
que vous puissiez voir ce qui est actuellement installé avant de
décider quoi flasher.

**Rechercher une mise à jour.** Le bouton « Rechercher une mise à jour » interroge GitHub une fois sur la dernière release et ne propose le téléchargement que si elle contient un paquet pour ce système plus récent que la version installée. Le paquet n'est accepté que si son SHA-256 et sa signature Ed25519 (la clé des releases, épinglée dans le programme) sont valides ; il n'est installé qu'après votre confirmation, jamais pendant un transfert, et la version précédente est conservée pour revenir en arrière (et rétablie d'elle-même si la nouvelle ne démarre pas). Rien n'est jamais vérifié ni installé tout seul : la vérification à l'ouverture est une option, désactivée par défaut, et la confirmation ne se désactive que dans la même fenêtre, après un avertissement.

Deux façons de parler à la carte, toutes deux utilisant le même
protocole en dessous :

- **Série / SLCAN** — fonctionne sur Windows et Linux. Nécessite un
  adaptateur USB-CAN exécutant le firmware SLCAN, connecté comme port
  série virtuel.
  - Sans adaptateur ni matériel, une carte virtuelle prend le relais : lancez `python -m urtc_can.virtual_board`, indiquez son adresse dans la variable d'environnement `URTC_VIRTUAL_PORT` (par exemple `socket://127.0.0.1:7777`) avant de démarrer le programme, ou donnez-la à `--port` en ligne de commande. Elle apparaît dans la liste des ports et répond comme une carte, application et bootloader.
- **SocketCAN** — **Linux uniquement**, et affiché uniquement dans
  l'interface de l'outil sous Linux. Parle directement à une interface
  réseau du noyau `can0`/`slcan0`. Si votre adaptateur exécute déjà le
  firmware `gs_usb`/candleLight (la plupart des cartes CANable le font
  d'origine), ce chemin **ne nécessite aucun reflash de l'adaptateur**
  — le pilote natif de Linux le gère directement.

## 🧩 Rôle dans URTC

URTC-FLASHER est le programme qui met du firmware sur une carte URTC. Il parle le protocole du bootloader d'URTC (`docs/CANBUS.TXT` de ce dépôt) via un adaptateur USB-CAN, comme port série SLCAN ou comme SocketCAN sous Linux : le contrôle du HardwareID, des blocs HMAC-SHA256 à clé partagée, le flux d'image dorée avec slot de secours et une requête de version pour voir ce qui est installé avant de décider quoi flasher. Pour une carte sans bootloader fonctionnel, ou pour programmer la puce entière, il prépare les commandes SWD/JTAG de pyOCD ou STM32CubeProgrammer. C'est le compagnon de mise à jour d'URTC-TESTER, partage son code CAN avec lui via URTC-COMMON, et URTC-UPDATER peut lui remettre une image de firmware dont la signature de release a déjà été vérifiée.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="Architecture de URTC-FLASHER : qui l'utilise, ce qu'il contient et de quoi il dépend" width="100%">
</p>

Comment les parties de ce dépôt s'articulent : qui l'utilise, ce qu'il contient et de quoi il dépend. L'image est dessinée à partir de `docs/architecture.json` et vérifiée par rapport au code.

<!-- urtc-section:updates -->
### Comment il se met à jour

Ce programme peut chercher une version plus récente de lui-même : le bouton « Rechercher une mise à jour » interroge GitHub une fois et ne propose un paquet signé que s'il est pour votre système et plus récent. Rien n'est vérifié ni installé tout seul tant que vous n'activez pas la vérification, et une mise à jour demande votre confirmation. Le paquet doit correspondre à son SHA-256 et à la signature de la clé des releases épinglée dans le programme ; la version précédente est conservée et rétablie d'elle-même si la nouvelle ne démarre pas. `urtc-updater --cli package list|check|install|rollback` fait la même chose en ligne de commande pour le flasher et le testeur, et `install --file` fonctionne sans réseau.
<!-- /urtc-section:updates -->

## 🖼️ Captures d'écran

<p align="center">
  <img src="images/URTC_FLASHER_V1_1.png" alt="Fenêtre URTC Flasher" width="700">
</p>

Ces images montrent la vraie fenêtre, dessinée sans écran telle qu'elle s'ouvre (rien de connecté, rien d'envoyé). Le guide parcourt le panneau, la fenêtre d'aide et celle de mise à jour.

![La fenêtre, pas à pas](docs/screenshots/flasher-deck.png)

[Guide avec images](docs/WINDOW_GUIDE.md)

## ✨ Fonctionnalités

### Vérifier ce qui est actuellement installé

> Dans la console Qt Quick, les ports des deux transports (adaptateurs série et, sous Linux, interfaces SocketCAN) sont dans une seule liste, et les interrogations de cette section sont faites par **LIRE L'ETAT DE LA CARTE**, qui demande d'un coup la version, les compteurs d'erreurs CAN, le type de carte d'extension, la variante MLX9064x et les infos du périphérique, et les affiche dans l'instantané de la carte. Les enregistrements de la section de configuration de l'appareil écrivent les valeurs.
Si vous êtes sous Linux et que SocketCAN est disponible, vous verrez un
choix de **Transport** en haut - choisissez Série/SLCAN ou SocketCAN
avant de vous connecter. Sous Windows cette ligne n'apparaît pas du
tout ; Série/SLCAN est la seule option.

Cliquez sur **Connecter**, et l'outil demande automatiquement à la
carte ce qu'elle exécute actuellement (CAN ID `0x7F8` → `0x7F9` - voir
`docs/CANBUS.TXT`). Cela fonctionne que la carte exécute son
application normalement *ou* soit dans le bootloader, donc vous n'avez
pas besoin de provoquer une réinitialisation juste pour le savoir.
Cliquez sur **Interroger** à tout moment après pour revérifier (utile
juste après qu'un flash se termine, pour confirmer que la nouvelle
version a bien pris).

**Quand le bootloader lui-même répond** (carte assise dans le
bootloader, n'exécutant pas son application), il rapporte aussi sa
propre version - une chose séparée de la version de l'application
installée, suivie via son propre
`BOOTLOADER_VERSION_MAJOR/MINOR/PATCH` dans `bootloader_common.h` et envoyée
comme deuxième trame (`0x7FA`) juste à côté de `0x7F9`. L'application en
cours d'exécution n'envoie jamais ceci - elle n'a aucun moyen de
connaître la version d'un bootloader actuellement flashé autrement qu'en
demandant au bootloader lui-même, donc cela n'apparaît que lorsque la
carte est effectivement là (juste après `0x7F0`, ou à un démarrage
frais avant de sauter vers l'application).

**Le numéro de correctif.** Une carte avec un firmware 0.3.5 ou plus
récent envoie aussi le numéro de correctif de l'application installée
(trame `0x7E9`, juste après `0x7F9`) : la fenêtre et le journal affichent
donc le `majeur.mineur.correctif` complet (par exemple `v0.3.5`) au lieu
de `majeur.mineur` ; le correctif d'une image est la troisième partie de
la version de son manifeste. Avant une mise à jour, le journal affiche
`installée -> nouvelle` sous cette forme, et le correctif n'intervient
dans l'avertissement « plus ancienne que l'installée » que si les deux
côtés en ont un. Une carte antérieure au correctif répond sans lui et
s'affiche exactement comme avant. Lorsque le bootloader annonce (indicateur
dans la même trame) qu'il lit le correctif, la trame de fin de mise à jour
le porte dans l'octet de poids fort du champ mineur ; tout autre
bootloader, et toute image sans correctif, reçoivent la trame à deux
nombres inchangée. La réponse de version de l'esclave d'extension
(`0x218`) a la même extension facultative. Cela suit la description du
protocole et n'a été testé qu'avec le simulateur ; cela n'a pas été essayé
sur une carte réelle.

Ce que vous verrez :

- **`v0.2 (application, HardwareID 0x0303CC01)`** - cas normal,
  application en cours d'exécution, tout correspond.
- **`Bootloader running, no valid firmware currently installed,
  bootloader v0.1.2`** - la carte est coincée dans le bootloader sans
  rien vers quoi sauter (puce vierge, ou chaque vérification sur
  l'emplacement principal a échoué). C'est exactement la situation pour
  laquelle cet outil existe - flashez-la. La version de bootloader
  affichée ici est celle du bootloader lui-même, sans rapport avec
  quelque version d'application ayant échoué ses vérifications.
- **`⚠ HardwareID mismatch!`** affiché en rouge - quelque chose a
  répondu, mais son HardwareID ne correspond pas à ce que cet outil
  attend. Ne flashez pas sans comprendre pourquoi d'abord ; le
  bootloader rejetterait la mise à jour de toute façon, mais une
  discordance ici peut aussi signifier que vous visez complètement la
  mauvaise carte.
- **Aucune réponse** (rouge) - carte ne répondant pas, mauvais débit
  binaire, ou pas réellement connectée. Vérifiez la connexion physique
  et, sur le chemin SocketCAN, que l'interface est réellement active
  (`ip link show`).

**Carte d'extension :** une liste déroulante séparée et une paire
Interroger/Enregistrer, juste sous la vérification de version. Lit et
définit laquelle des 7 configurations possibles de `CONN_EXPANSION`
(aucune, ou l'une des 6 variantes réelles - voir `EXPANSION.TXT`)
est physiquement installée, via CAN (`0x1A0`/`0x1A1`). Il n'y a aucun
moyen électrique pour la carte de le détecter elle-même, donc il faut le
lui dire - cela vit ici (pas seulement dans `URTC Tester`) puisque
c'est une étape de configuration matérielle ponctuelle faite plus
naturellement aux côtés d'une mise à jour de firmware. **Enregistrer**
demande d'abord confirmation, puisque cela persiste à travers les
cycles d'alimentation jusqu'à ce que ce soit explicitement changé à
nouveau.

**Variante de capteur MLX9064x :** même forme que le contrôle de carte
d'extension ci-dessus - une liste déroulante et une paire
Interroger/Enregistrer qui lit/définit lequel des 3 capteurs thermiques
de la famille MLX9064x (ou aucun) est réellement installé, via CAN
(`0x1A6`/`0x1A7` - voir `CANBUS.TXT`). Pertinent uniquement lorsque la
carte d'extension ci-dessus est configurée comme une variante Advanced
ou Basic+MLX9064x ; le propre firmware de la carte ignore complètement
ce réglage sur tout autre type de carte d'extension. « Aucun installé »
(la valeur par défaut sûre) ne retombe délibérément pas sur l'hypothèse
MLX90640 - une carte avec un vrai MLX90640 câblé nécessite que cela
soit défini explicitement, une fois, de la même manière que le type de
carte d'extension lui-même le requiert déjà.

### Flasher

1. **Connecter** : choisissez Série/SLCAN ou SocketCAN (Linux
   uniquement), puis le port/interface, puis cliquez sur Connecter.
   Pour Série/SLCAN ceci ouvre le canal CAN à 500 kbit/s (la vitesse de
   bus fixe d'URTC) ; pour SocketCAN on s'attend à ce que l'interface
   soit déjà à ce débit (étape 1 ci-dessus) - cet outil ne le définit
   pas. Dans les deux cas, la version actuelle est interrogée
   automatiquement - voir section 4 ci-dessus.
2. **Choisissez une cible de flashage** : « Cette carte (principale) »
   ou « Esclave d'extension » - par défaut la carte principale, le cas
   de loin le plus courant. L'option esclave n'atteint quelque chose
   que sur une variante de carte d'extension Advanced
   (TMC2209+STM32F303CBT6 ou TMC5160A+STM32F303CBT6) - la mise à jour
   est relayée via le propre pont I2C de la carte principale vers la
   puce esclave (les propres `0x210`-`0x219` de `CANBUS.TXT`), pas une
   connexion physique séparée. « Effacer F-RAM avant de flasher »
   (étape 4 ci-dessous) se désactive automatiquement en choisissant
   Esclave - la puce esclave n'a pas de F-RAM propre à effacer.
3. **Sélectionner le firmware** : choisissez dans la liste détectée, ou
   Parcourir - voir la section 3 ci-dessus pour savoir exactement
   comment fonctionnent la détection et la validation.
4. **Flasher** :
   - Laissez coché "La carte exécute actuellement l'application" si la
     carte est allumée et fonctionne normalement - l'outil envoie
     d'abord le déclencheur à charge utile magique `0x7F0` (ou `0x210`,
     relayé vers l'esclave, si Esclave est la cible sélectionnée), qui
     éteint en sécurité chaque actionneur avant de réinitialiser vers le
     bootloader.
   - Décochez si la carte est déjà dans le bootloader (juste après un
     flash JTAG frais, ou si la vérification de version ci-dessus a
     montré "no valid firmware currently installed").
   - Cliquez sur **Flasher le Firmware** et confirmez - la boîte de
     dialogue de confirmation nomme quelle cible vous êtes sur le point
     de flasher, alors vérifiez que cela correspond à ce que vous
     vouliez réellement sélectionner. Le journal montre
     chaque étape du protocole ; la barre de progression suit la
     progression d'écriture page par page pendant le transfert, puis la
     progression de copie pendant la copie finale de sauvegarde vers
     principal.

Si la vérification échoue à n'importe quel point (discordance CRC32,
HMAC, ou HardwareID), l'emplacement principal du bootloader n'est
jamais touché - la carte continue d'exécuter le firmware qu'elle avait
déjà. Il est toujours sûr de simplement réessayer.

**Sauvegarder le Firmware (CAN)** : lit le firmware actuellement installé
via le bus, inchangé, et l'enregistre sous forme de fichier `.bin` -
l'équivalent CAN de la propre fonctionnalité SWD « back up entire flash
before erasing » (section 6 ci-dessous), pour la même raison. Utile
avant toute mise à jour, surtout avant un downgrade délibéré
(ci-dessous), car c'est le seul moyen de récupérer les octets exacts
d'aujourd'hui plus tard si vous n'avez plus le fichier qui les a
produits. Carte principale uniquement, et seulement pendant que la carte
est réellement dans le bootloader - nécessite un bootloader qui
implémente `0x7FE`/`0x7FF` (voir `docs/CANBUS.TXT`) ; un ancien ne
répond simplement jamais, signalé comme un délai dépassé clair plutôt
qu'un fichier silencieusement vide. En pratique, cela signifie que la sauvegarde fonctionne sur une carte sans application valide ou restée à mi-chemin d'une mise à jour : avec une application valide, le bootloader y saute environ 600 ms après le reset sauf si une trame de démarrage de mise à jour (`0x7F1`) arrive, et cet outil n'a aucun bouton qui maintienne le bootloader en attente (cela demanderait une modification du bootloader). Pour une carte qui fonctionne normalement, sauvegardez la flash par SWD/JTAG (section 6).

**Indications de version et de signature** : avant le transfert, l'outil demande à la carte ce qui est installé et journalise « installée vX.Y -> nouvelle vA.B » ; si la nouvelle version est plus ancienne, il avertit que le bootloader la refusera sans downgrade autorisé et suggère de faire d'abord une sauvegarde. Une image dont le manifeste indique qu'elle est signée avec la clé de développement PUBLIQUE (les images officielles incluses le sont) affiche un avertissement rouge sous le nom du fichier ; mettez `"require_production_signature": true` dans `urtc_config.json` pour refuser totalement ces images. Quand la carte répond depuis son bootloader sans firmware valide, l'image officielle de la carte principale la plus récente trouvée dans `firmware/` est sélectionnée pour que vous la vérifiiez et la flashiez. Après chaque mise à jour réussie, un petit rapport est écrit (`logs/urtc_update_report_*.json` : version de l'outil, opérateur, nom, taille et SHA-256 de l'image, versions avant et après) ; il porte son propre SHA-256 pour qu'une modification soit visible, mais ce n'est pas une signature.

**Installer délibérément une version antérieure** : le bootloader
refuse normalement une image valablement signée si elle déclare une
version antérieure à celle déjà installée (raison d'échec de
vérification « rollback refusé ») - cela empêche qu'une version avec
une vulnérabilité déjà découverte soit réinstallée. Si vous avez
vraiment besoin de revenir à une version antérieure en laquelle vous
avez confiance, cochez **« Autoriser le downgrade (contourner
l'anti-rollback) pour cette mise à jour »** (carte principale
uniquement) avant de flasher - une seconde boîte de dialogue de
confirmation apparaît puisque cela contourne délibérément une
vérification de sécurité. Ceci charge quand même l'image antérieure
complète via le transfert normal, cela ne fait que lever la vérification
de l'ordre des versions pour cette tentative (`0x7FD` - voir
`docs/CANBUS.TXT`) ; le numéro de version signalé à la carte provient du
propre `.manifest.json` du fichier lorsqu'il en existe un à côté (voir
section 3 ci-dessus), retombant sur la version actuellement configurée
de cet outil sinon, journalisé clairement dans tous les cas afin que ce
ne soit jamais une supposition silencieuse.

### Programmer la puce complète via SWD/JTAG (avancé)

La section "4. Program complete chip via SWD/JTAG" dans l'outil fait un
flash complet de mise en route - efface en masse toute la puce, puis
écrit à neuf à la fois l'image du bootloader et celle de l'application,
aux adresses réelles de la puce correspondant à la sélection **Puce
cible** (voir ci-dessous). Ceci est un **type d'opération
différent** des sections 1-5 ci-dessus :

|  | Mise à jour CAN OTA (sections 1-5) | Puce complète SWD/JTAG (section 6) |
|---|---|---|
| Auto-réparateur si interrompu | Oui - l'emplacement de sauvegarde à image dorée garantit que le firmware en cours d'exécution survit | Non - n'exécutera rien tant qu'il n'est pas reprogrammé |
| Récupérable | Automatiquement, aucune action nécessaire | Oui - reconnectez simplement et flashez à nouveau via SWD ; le port de débogage ne dépend pas du contenu de la flash. Seul un véritable verrouillage permanent (option byte RDP2) empêcherait ceci, et rien dans cet outil ne définit d'option bytes |
| Touche le bootloader | Jamais | Oui, par conception |
| Nécessite | Un adaptateur USB-CAN | Une sonde SWD/JTAG (ST-Link ou similaire) |
| Usage typique | Mises à jour de firmware routinières | Première mise en route sur une puce vierge, ou récupération d'une carte briquée |

**Puce cible :** « Cette carte (principale) » ou « Esclave d'extension »
- mêmes 2 options que le propre sélecteur de l'onglet CAN-OTA, mais un
choix véritablement séparé ici : SWD/JTAG nécessite une sonde
physiquement câblée à la puce correspondant à cette sélection, puisqu'il
n'existe aucun pont (contrairement à CAN-OTA) qui permette à une seule
connexion d'atteindre les deux. Changer ceci modifie automatiquement les
adresses flash utilisées :

| | Carte principale (STM32F303CC) | Esclave d'extension (STM32F303CBT6) |
|---|---|---|
| Adresse bootloader | `0x08000000` (région 32K) | `0x08000000` (région 18K) |
| Adresse application | `0x08008000` (région 112K) | `0x08005000` (région 54K) |
| Chaîne cible pyOCD | `stm32f303cc` | `stm32f303cb` |

Les deux chaînes cibles ci-dessus sont la meilleure estimation de ce
projet pour le vrai nom de cible pyOCD de chaque puce, non confirmée
face à une installation pyOCD réelle lors de la rédaction (la
couverture STM32 dans pyOCD passe en grande partie par les CMSIS-Packs
plutôt que par des cibles intégrées) - si le flashage échoue avec une
erreur du type « target not found », exécutez vous-même `pyocd list
--targets --name stm32f303` et `pyocd pack install <le vrai nom>`
télécharge le bon CMSIS-Pack.

**Nécessite l'un de** (l'outil détecte automatiquement lequel est
disponible et n'active que ceux qu'il trouve) :
- **pyOCD** - `pip install pyocd`. Libre, open-source, aucune
  installation séparée au-delà du paquet pip.
- **STM32CubeProgrammer** - l'outil officiel de ST, installé séparément
  depuis [st.com](https://www.st.com). Si vous l'avez déjà pour d'autres
  travaux STM32, aucune installation supplémentaire n'est nécessaire
  ici.

Les deux sont pilotés comme des sous-processus en ligne de commande, pas
importés comme des bibliothèques Python - vous verrez la commande exacte
enregistrée avant qu'elle ne s'exécute.

**Formats de fichiers :** `.bin` (nécessite l'adresse fixe que cet outil
connaît déjà - vous ne l'entrez pas) ou `.hex` (porte sa propre adresse,
utilisée telle quelle). Mélanger est correct - bootloader en `.hex` et
application en `.bin`, ou vice versa, les deux fonctionnent. Les deux
sélecteurs de fichiers valident le fichier sélectionné (taille plausible
pour l'emplacement cible, et - là où le format permet de le vérifier
avec confiance - un pointeur de pile initial plausible) avant de vous
laisser continuer, de la même manière que le sélecteur de firmware du
chemin CAN le faisait déjà.

**La connexion est vérifiée avant que quoi que ce soit de destructeur
ne s'exécute**, exigeant une **preuve positive** d'une vraie
sonde/cible plutôt que la simple absence d'une erreur - le code de
sortie propre de STM32CubeProgrammer n'est pas un signal fiable de
succès/échec à lui seul, donc une vérification de connexion dédiée
(`pyocd list --probes`, ou un `-c port=SWD` de connexion seule pour
STM32CubeProgrammer) s'exécute avant que l'étape d'effacement en masse
ne le fasse jamais. La sortie de chaque commande suivante est aussi
examinée pour du texte d'échec connu comme seconde couche, au cas où le
code de sortie d'un outil à lui seul ne serait pas fiable dans une autre
situation non plus.

**Le dry run est activé par défaut.** La première fois, laissez-le
coché et appuyez sur "Flash Complete Chip" - il imprime les commandes
exactes dans le journal sans toucher la carte. Lisez-les, confirmez que
les chemins et adresses semblent corrects, *puis* décochez le dry run et
faites-le pour de vrai.

**"Back up entire flash before erasing"** lit d'abord toute la région
flash de 256KB dans un fichier `.bin`, via la commande propre de
lecture-mémoire-vers-fichier du même outil (`-r` pour
STM32CubeProgrammer, `commander savemem` pour pyOCD) - une vraie
assurance ici, puisque contrairement à une mise à jour CAN OTA (que
l'emplacement de sauvegarde à image dorée protège déjà), un effacement
complet de puce n'a pas d'autre annulation. Désactivé par défaut car
cela ajoute 10-30s et n'est pas nécessaire sur une puce neuve/vierge ;
vaut la peine de cocher avant d'écraser une carte qui exécute déjà
quelque chose. Si la lecture ne produit pas réellement un fichier,
l'effacement est refusé plutôt que de procéder sans la sauvegarde que
vous avez demandée.

**État des tests :** la logique de vérification de connexion ci-dessus a
été vérifiée contre une sortie réelle de STM32CubeProgrammer (à la fois
un vrai journal de connexion réussie et un échec documenté "No target
connected", tous deux provenant du propre forum communautaire de ST) et
contre le scénario exact de faux succès qu'un utilisateur réel a
rencontré. La séquence complète d'effacement/programmation/vérification
contre un vrai ST-Link et un vrai STM32F303CC n'a pas encore été
exercée de bout en bout - l'environnement qui a écrit ceci n'a pas
d'accès USB. Traitez une première vraie tentative complète avec la
prudence appropriée - une carte de rechange/test d'abord si vous en
avez une, et gardez à l'esprit un plan de secours (l'outil de flash
propre de STM32CubeIDE, ou `st-flash`) au cas où quelque chose dans
votre version spécifique de pyOCD ou votre sonde ne correspondrait pas
à ce qui est supposé ici.

### Diagnostics — activité du bus, débit binaire, et paquets de débogage

**Sélecteur de débit binaire + détection automatique** (Série/SLCAN
uniquement) : le bus d'URTC est fixé à 500 kbit/s, qui reste la valeur
par défaut - ceci est pour un adaptateur mal configuré ou pour déboguer
une carte non standard. **Détection automatique** se contente d'*écouter* :
elle ouvre l'adaptateur en mode écoute seule SLCAN (`L`) à chaque débit
standard à tour de rôle et s'arrête au premier où elle entend une trame
CAN valide, donc elle ne transmet jamais et ne peut pas perturber un bus
en marche. Elle nécessite donc que d'autres nœuds émettent et que
l'adaptateur prenne en charge le mode écoute seule ; sur un bus silencieux
(ou avec un adaptateur sans ce mode) elle ne trouve rien et vous choisissez
le débit à la main. Pas encore connecté quand vous cliquez dessus. Le débit
binaire de SocketCAN est défini au niveau du système d'exploitation
(`ip link`), donc ce contrôle est désactivé pour ce transport - il n'y a
rien ici à essayer.

**Activité du bus** ("Vérifier (2s)", à côté d'Interroger) : compte les
vraies trames de protocole réellement vues pendant une fenêtre fixe de
2 secondes sur le transport connecté. Ceci n'est délibérément **pas** la
même chose qu'un vrai pourcentage de charge de bus CAN - cela
nécessiterait une requête netlink (SocketCAN) ou des extensions
spécifiques à l'adaptateur (SLCAN) que cet outil n'a pas de moyen
standard et sans dépendance d'obtenir pour le contrôleur du *propre
adaptateur*. Ce que ça donne : un signal genuine, directement
mesuré, de "quelque chose parle sur ce bus, et environ à quelle
fréquence", sur l'un ou l'autre des 2 transports. Pour SocketCAN
spécifiquement, cela montre aussi le delta de 2 secondes des propres
statistiques d'interface de Linux
(`/sys/class/net/<iface>/statistics/`) - compteurs de base
rx/tx/error/drop que chaque interface expose, lus comme fichiers plats,
aucune dépendance supplémentaire. Se connecter via SocketCAN lit aussi
`/sys/class/net/<iface>/carrier` - un simple fichier 0/1 que chaque
interface Linux expose. Quand un contrôleur CAN passe en bus-off, le
pilote du noyau appelle `netif_carrier_off()`, donc "pas de porteuse"
ici est une preuve réelle d'un bus-off ou d'un lien similairement mort,
enregistré comme avertissement avec la commande exacte de récupération
(`sudo ip link set <iface> down && sudo ip link set <iface> up type can
bitrate 500000 restart-ms 100`). Cet outil n'exécute pas cette commande
lui-même - nettoyer un vrai bus-off nécessite de baisser et remonter
l'interface au niveau du noyau, ce qui nécessite root et compte comme
changer la configuration réseau système, pas quelque chose à faire
silencieusement en votre nom.

**Compteurs d'erreur (TEC/REC)** (à côté d'Activité du bus) : contrairement
aux compteurs de l'adaptateur ci-dessus, ceci interroge **la carte
elle-même** pour son propre Transmit/Receive Error Counter du contrôleur
CAN (`0x7FB`/`0x7FC` - voir `docs/CANBUS.TXT`), répondu par ce qui
tourne actuellement, application ou bootloader. Vert signifie que les 2
compteurs sont à 0 (error-active, sain) ; orange signifie que l'un ou
l'autre est non nul mais en dessous de 128 (toujours error-active, mais
quelque chose cause des retransmissions) ; rouge signifie 128 ou plus
(error-passive ou pire) ou aucune réponse du tout (firmware/bootloader
ancien qui n'implémente pas encore `0x7FB`, ou carte non connectée). Un
TEC qui grimpe régulièrement avec un REC stable indique généralement que
les propres transmissions de cette carte ne sont pas acquittées - aucun
autre nœud sur le bus, ou un problème de câblage/terminaison/débit
binaire spécifique à la connexion de cette carte.

**Exporter le paquet de débogage** (au-dessus du journal) : enregistre
un `.zip` avec le journal actuel à l'écran, des diagnostics système de
base (OS, version Python, quels outils ont été trouvés,
transport/port/débit binaire actuel), et le fichier de firmware CAN
actuellement sélectionné - utile pour remettre une image complète à
celui qui a écrit le firmware si quelque chose ne va pas sur le
terrain, plutôt que de copier le journal
à la main.

### SWD/JTAG — formats de fichiers, vérification d'emplacement, et sélection de sonde

**Formats de fichiers** : les sélecteurs bootloader/application de la
section SWD acceptent `.bin`, `.hex`, et `.elf`/`.axf`. ELF/AXF est
analysé avec une petite quantité de désempaquetage de structure écrit à
la main (seulement l'en-tête ELF + les en-têtes de programme - pas de
symboles, pas d'en-têtes de section), délibérément sans utiliser
`pyelftools` : ce projet reste à zéro dépendance hors bibliothèque
standard, et l'analyse ELF complète est plus que ce dont a besoin cette
vérification de plausibilité spécifique. Vérifié contre le
`BOOTLOADER.elf`/`APP.elf` compilé réel propre de ce projet - les deux
valident correctement à leurs adresses de chargement réelles
(`0x08000000`/`0x08008000`), pas seulement des fichiers de test
synthétiques. Seulement ARM little-endian 32 bits, ce qui est tout ce
qu'une cible Cortex-M est jamais. La taille déclarée d'un fichier `.hex`
est le compte réel d'octets occupés, pas la plage d'adresses de son
enregistrement le plus bas au plus haut - donc un fichier épars (un
petit bloc de firmware réel plus un bloc distant et séparé d'option
bytes ou de données de calibration, que certaines chaînes d'outils STM32
regroupent en un seul export) valide sur son contenu réel plutôt que
sur l'écart entre eux. Une image firmware brute sous une extension
autre que `.bin` (`.img`, `.rom`, ou pas d'extension du tout -
sélectionnable via l'option "Tous les fichiers" du sélecteur de
fichiers) obtient son adresse de base de dans quel emplacement vous le
chargez, de la même manière qu'un `.bin` le ferait.

**Vérification d'emplacement bootloader/application** : les sélecteurs
de fichiers vérifient que chaque image est destinée à l'emplacement
dans lequel elle est mise, pas seulement qu'elle ressemble à du firmware
valide de *quelque* type. Une image bootloader et une application ont
un pointeur de pile également plausible - même puce, même RAM - donc
cette vérification seule ne peut pas les distinguer si l'une finit dans
l'emplacement de l'autre. Ce qui le peut : le **gestionnaire de reset**
d'une image liée est une adresse absolue et réelle figée au moment de
la liaison, et elle ne pointe jamais qu'à l'intérieur de la région pour
laquelle elle a été réellement liée. Vérifié contre le
`BOOTLOADER.bin`/`APP.bin` compilé réel propre de ce projet : leurs
gestionnaires de reset sont `0x08000785` et `0x0800C0CD`
respectivement, chacun correctement à l'intérieur de la plage
d'adresses de son propre emplacement et en dehors de celle de l'autre -
donc mettre l'un ou l'autre dans le mauvais emplacement est détecté et
bloqué, pas silencieusement accepté. La même logique s'applique à
`.hex`/`.elf`, vérifiés contre leur propre adresse de chargement
intégrée à la place.

**Vérifier les Option Bytes** (section 4, STM32CubeProgrammer
uniquement - pyOCD n'expose pas ceci de la même manière via CLI) : un
dump en lecture seule `-ob displ`, sans effacement/écriture. Signale le
niveau RDP avec le même soin que tout cet outil prend autour du risque
SWD :
- **RDP0** - aucune protection, normal pour une carte de développement.
- **RDP1** - réversible via le Read Unprotect de CubeProgrammer, mais
  cela efface la puce en masse dans le cadre de sa suppression - pas
  quelque chose que cet outil fait pour vous automatiquement.
- **RDP2** - le seul verrouillage genuinement **permanent** de tout ce
  projet. Contrairement à tout autre risque documenté ci-dessus (tous
  récupérables via SWD), RDP2 désactive le port de débogage pour
  toujours par conception propre de ST. Cette vérification existe pour
  l'attraper avant une opération de puce complète, pas après.

**Sélection de sonde** (section 4) : si plus d'un ST-Link/sonde est
connecté à la fois, chaque commande exige d'en choisir un
explicitement dans la liste déroulante Sonde - pas de "celui que l'OS
énumère en premier". Avec exactement une sonde connectée, elle est
auto-sélectionnée ; avec zéro ou plusieurs, appuyez sur Actualiser et
choisissez. Ceci s'applique à la fois au flash de puce complète et à la
vérification d'option bytes, puisque les deux sont suffisamment proches
du destructeur pour que deviner la mauvaise carte soit un risque réel
sur un banc à plusieurs appareils.

**Les écritures de pyOCD sont vérifiées avec une relecture explicite**,
pas seulement faisant confiance au code de sortie. La propre commande
`flash` de pyOCD saute la réécriture des pages qui correspondent déjà
(une optimisation de vitesse, pas un rapport de vérification), donc cet
outil ajoute une étape `commander compare` contre les deux images
après l'écriture - une vraie vérification octet par octet, correspondant
à ce que fait déjà le flag `-v` de STM32CubeProgrammer. Seulement pour
`.bin` : `compare` vérifie le contenu de la flash contre les octets
bruts du fichier, ce qui ne correspondrait pas correctement à
l'encodage propre d'un fichier `.hex`/`.elf` même après un flash
réussi, donc ces 2 formats sautent cette étape spécifique et comptent
sur la propre vérification interne au moment de l'écriture de pyOCD à
la place.

### Télémétrie de transfert et détail d'échec de vérification

**Télémétrie de transfert** : le journal montre les KB/s effectifs et le
temps écoulé par page pendant une mise à jour CAN, plus une ligne de
résumé à la fin (temps total, KB/s moyen, combien de nouvelles
tentatives d'ACK de page se sont produites). Purement informatif - ne
change pas le comportement de flash, rend juste plus facile de
distinguer d'un coup d'œil "ça va juste lentement" de "quelque chose ne
va vraiment pas".

**Raisons spécifiques d'échec de vérification** : si la vérification
échoue pendant une mise à jour CAN, `bootloader_protocol.c` envoie un octet de
raison à côté du statut `0x05` (vérification échouée) - transfert
incomplet, discordance CRC32, discordance HMAC, ou discordance
HardwareID, plutôt que chaque échec paraisse identique. Voir
`docs/CANBUS.TXT` pour le format exact de trame (`0x7F5`, DLC 2 pour ce
statut spécifique). Cet outil et le bootloader s'accordent sur ce
format de trame, donc flashez les deux ensemble si vous construisez un
bootloader personnalisé avec une version différente du protocole.

**Le même détail pour l'esclave d'extension** : une mise à jour
échouée de l'esclave (Cible : « Esclave d'extension ») interroge
`0x219` juste après que `0x215` signale `STATUS_VERIFY_FAIL`, relayant
le propre `REG_VERIFY_FAIL_REASON` du bootloader esclave - les mêmes 5
raisons que ci-dessus, atteintes cette fois via le pont I2C plutôt que
lues directement sur une trame CAN. Nécessite un bootloader esclave qui
implémente `0x219` (ajouté en même temps que le support de cet outil
pour celui-ci) ; un bootloader esclave plus ancien ne répond simplement
pas à cette requête, et cet outil retombe alors sur le message
générique « échec de vérification ».

### Effacement optionnel de la F-RAM avant de flasher

La section 3 a une case à cocher, **"Effacer aussi la F-RAM de
persistance avant de flasher"** - désactivée par défaut. Si cochée,
elle envoie la commande d'effacement à charge utile magique (`0x192` -
voir `docs/CANBUS.TXT`) à la F-RAM de persistance FM24CL64B de la carte
avant que la séquence de mise à jour ne commence, effaçant tout état de
paramètres d'outil qu'elle avait sauvegardé.

**Pas nécessaire pour une mise à jour normale.** Une discordance de
version dans la mise en page propre de l'enregistrement sauvegardé est
déjà détectée et ignorée en sécurité au prochain démarrage (voir la
section de persistance des paramètres de
`src/F303-master/README.md`) - cette case existe pour un
nettoyage genuinement complet, pas parce que la sauter laisserait
quelque chose de cassé.

**Fonctionne seulement pendant que l'application est en cours
d'exécution** - le bootloader lui-même ne gère pas du tout `0x192`,
seul `firmware_can_global_post.c` le fait. Cette case est sautée silencieusement
(avec une ligne de journal expliquant pourquoi) si la case "la carte
exécute actuellement l'application" au-dessus n'est pas cochée,
puisque dans ce cas on suppose que la carte est déjà dans le
bootloader.

**Une confirmation manquante n'arrête pas le flash.** Si la propre
trame de confirmation de la commande d'effacement ne revient pas dans
les 2 secondes, ceci est enregistré comme un avertissement et la mise à
jour de firmware réelle procède quand même - effacer est une étape
secondaire et optionnelle à côté du véritable but de cet outil, pas
quelque chose qui devrait interrompre une mise à jour par ailleurs
réussie à cause de l'absence de sa propre trame de confirmation.
Vérifiez l'état de la F-RAM séparément (le propre bouton Interroger
l'État de `URTC Tester`) si cela vous importe.

<!-- urtc-section:heads -->
### Plusieurs têtes d'outil sur un bus

Le firmware peut faire partager un bus CAN à plusieurs têtes d'outil (l'extension multinœud). Elle est **désactivée par défaut**, et un bus avec une seule tête fonctionne exactement comme avant. La fenêtre **Têtes** trouve les têtes, liste chacune avec son adresse, son outil et son numéro de série, et affiche son état : prête, sélectionnée, conflit d'adresse, défaut mémorisé, dans son bootloader ou perdue. Vous en sélectionnez une, le programme demande confirmation et ne lui envoie rien avant ; tant que plusieurs têtes sont sur le bus, une commande est refusée jusqu'à ce qu'une soit sélectionnée et l'ait confirmé. Si la tête sélectionnée est perdue, toutes les têtes passent à leur état sûr (une case de la fenêtre le désactive). Testé seulement contre un modèle du bus, pas avec des cartes. Voir `docs/MULTINODE.md` dans URTC-COMMON.
<!-- /urtc-section:heads -->

## 🔒 Sécurité et protection

| Risque | Défense |
|---|---|
| Flasher une image sur la mauvaise carte | Le contrôle du HardwareID du protocole du bootloader, fait avant d'écrire quoi que ce soit |
| Une image corrompue, non signée ou manipulée | Les contrôles d'intégrité de l'image ; un manifeste dont le `sha256` ne correspond pas au fichier est refusé avant tout trafic sur le bus, une image non signée est refusée et la signature publiée est envoyée sans aucune clé ; la signature de release (Ed25519) est vérifiée avant d'utiliser l'image d'une release |
| Installer une image plus ancienne par erreur | Le contrôle anti-retour arrière du bootloader ; un retour volontaire exige l'autorisation de rétrogradation |
| Une mise à jour ratée qui laisse la carte inutilisable | Le modèle d'image dorée : le slot de secours garde le firmware précédent, une trame de confirmation perdue se rattrape en redemandant la version au lieu de signaler un faux échec, et le slot principal peut être relu avant |
| Une mise à jour manipulée de ce programme | « Rechercher une mise à jour » n'accepte qu'un paquet avec un SHA-256 et une signature Ed25519 valides (la clé des releases, figée dans le programme), n'installe qu'après confirmation et jamais pendant un transfert, et garde la version précédente |

Le bootloader vérifie les images avec un CRC32 et un HMAC-SHA256 à clé partagée, pas avec une signature asymétrique ; les images d'application publiées sont signées avec la clé publique de développement, si bien que n'importe qui peut faire une image que le bootloader accepte. Rien de tout cela n'a tourné sur une vraie carte.

### Fiabilité pendant une mise à jour CAN, et journaux de session

Si l'ACK d'une page n'arrive pas dans la fenêtre normale de 3s pendant
une mise à jour CAN, l'outil attend de nouveau (il ne renvoie pas les
données de la page) jusqu'à deux fois de plus avec un court délai
croissant avant d'abandonner. Cela n'aide que pour un ACK simplement en
retard : le bootloader envoie chaque ACK de page une seule fois et ne le
répète jamais, donc un ACK réellement perdu ne peut pas être récupéré et
la mise à jour est abandonnée avec une erreur (la carte reste dans son
bootloader et la mise à jour peut simplement être relancée). L'outil ne
renvoie délibérément pas les données de page sur un timeout - si les
données étaient bien arrivées, renvoyer ferait lire au bootloader ces
octets comme le début de la *prochaine* page, désynchronisant le
transfert. Pendant l'attente, la pulsation propre du bootloader (envoyée
environ une fois par seconde) est comparée à la progression qu'impliquerait
la page et le journal signale quand elles concordent ; la pulsation est un
pourcentage entier, donc ce n'est qu'un indice, pas une preuve que la page
est arrivée, et elle ne change jamais le résultat.

Chaque session écrit aussi un fichier journal horodaté dans
`logs/` (`urtc_flasher_YYYYMMDD_HHMMSS.log`),
indépendant du journal à l'écran - utile pour remettre une trace
complète à celui qui a écrit le firmware si quelque chose ne va pas sur
le terrain. Ce dossier est créé automatiquement et est sûr à
supprimer ; rien ne relit d'anciens journaux. Seuls les 30 journaux de session les plus récents sont conservés ; si le dossier à côté du programme n'est pas accessible en écriture (installation en lecture seule), un dossier par utilisateur est utilisé à la place (`%LOCALAPPDATA%\URTC-Flasher\logs` sous Windows, `~/.local/state/urtc-flasher/logs` ailleurs).

## 🔌 Interfaces

Pour les pipelines CI, bancs de test, ou scripting de ligne de
production où il n'y a pas d'écran :

```
python3 urtc_flasher.py --cli --port /dev/ttyACM0 --file firmware.bin
```

```
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan,python-can,mock}] --port PORT
                             --file FILE [--no-trigger] [--force]
```

Codes de sortie : `0` succès, `1` erreur de protocole/connexion, `2`
arguments incorrects ou un fichier firmware échouant la validation
(passez `--force` pour le flasher quand même), `130` annulé avec
Ctrl+C. Couvre seulement le chemin de mise à jour CAN OTA (sections
1-3) - le chemin complet SWD/JTAG de la puce est délibérément GUI
uniquement pour l'instant, étant donné ce qui est bien plus en jeu si
une exécution scriptée obtient une mauvaise combinaison fichier/cible
sans que personne ne surveille.

**`--transport python-can`** utilise le paquet optionnel `python-can` (`pip install python-can`) pour PCAN, Kvaser, gs_usb/candleLight et les autres interfaces qu'il prend en charge, de sorte qu'il n'est pas nécessaire de reflasher l'adaptateur en SLCAN : `--port` est alors `<interface>:<canal>` (par exemple `pcan:PCAN_USBBUS1`) et le bus est ouvert à 500 kbit/s. La fenêtre propose les mêmes adaptateurs lorsque `python-can` est installé : ceux qu'il trouve pour PCAN, Kvaser et gs_usb et ceux nommés dans la variable d'environnement `URTC_PYTHON_CAN` (`<interface>:<canal>` séparés par des virgules), listés sous la forme `python-can:<interface>:<canal>` ; la vitesse du bus de cette connexion est fixée à 500 kbit/s. La fenêtre peut aussi être lancée avec `--firmware CHEMIN` pour qu'une image soit déjà choisie (rien n'est écrit sur une carte tant que vous ne vous connectez pas et ne confirmez pas la mise à jour).

**`--transport mock`** exécute toute la séquence de mise à jour contre
un bootloader simulé, en mémoire, plutôt qu'une vraie carte - aucun
adaptateur, aucun port, rien de physique impliqué :

```
python3 urtc_flasher.py --cli --transport mock --file firmware.bin --no-trigger
```

Utile pour tester la logique propre de cet outil (comportement de
nouvelle tentative, gestion des timeouts, codes de sortie) dans un
pipeline CI ou avant de toucher du matériel réel - pas quelque chose qui
parle à une vraie carte. `--mock-fail 0x03` (ou toute autre valeur
`VERIFY_FAIL_REASON_*` de `docs/CANBUS.TXT`) fait échouer la
vérification de la mise à jour simulée au lieu de réussir, pour tester
le chemin d'échec de la même manière.

## ⚙️ Configuration

Cet outil ne contient **aucune clé de signature**. Le build URTC signe
chaque image d'application et publie la signature à côté, dans
`<image>.manifest.json` (`hmac_sha256`, plus `<image>.sha256`) ; le flasher
envoie cette signature publiée et refuse une image dont le sha256 ne
correspond pas à son manifeste. Télécharger une image depuis GitHub
télécharge aussi ces deux fichiers, et `python tools/sync_firmware.py` met à
jour le dossier `firmware/` fourni à partir du build URTC (`--check` le
vérifie). Par défaut, il prend l'ensemble dans les assets de la dernière release d'URTC (`--release TAG` en choisit une autre) ; on peut aussi passer en argument un dossier local, par exemple un build URTC local. Seule une image compilée soi-même sans manifeste, sur une carte de
banc, a besoin d'une clé : définir `hmac_key_hex` / `slave_hmac_key_hex`
dans `urtc_config.json` (ci-dessous) - sans elle, une telle image est
refusée au lieu d'être signée avec une clé que le bootloader ne peut pas
avoir. Voir `docs/FIRMWARE_SIGNING.TXT` dans URTC. Les images publiées sont signées avec la clé publique de développement (`signing_key_kind: dev`) ; c'est donc une vérification à clé partagée : elle montre que l'image a été produite par quelqu'un qui détient cette clé, pas de qui il s'agit ; la signature asymétrique (Ed25519) est prévue, pas implémentée.

**Ou remplacez tout ceci sans toucher le script :** un
`urtc_config.json` optionnel à côté de `firmware/` peut définir la clé
de signature, le HardwareID, et les valeurs de la carte mémoire - utile
pour une révision de carte différente, une clé pivotée, ou (pour les
champs de carte mémoire) adapter cet outil à une variante de puce ou un
schéma de partition différent, sans avoir besoin d'une nouvelle version
de script par déploiement :
```json
{
  "hardware_id": "0x0303CC01",
  "hmac_key_hex": "555254432D4859445241...",
  "app_max_size": 114688,
  "bootloader_max_size": 32768,
  "flash_page_size": 2048,
  "bootloader_flash_addr": "0x08000000",
  "app_flash_addr": "0x08008000"
}
```
Chaque champ est optionnel - ne remplacez que ce qui change réellement.
Un fichier manquant retombe silencieusement sur les valeurs par défaut
compilées ; un fichier présent mais cassé enregistre un avertissement
et retombe aussi sur ces valeurs, plutôt que de faire planter l'outil
pour une faute de frappe. **Les remplacements du plan mémoire et du HardwareID ne s'appliquent qu'aux constantes propres de la carte principale** (la seule exception est `slave_hmac_key_hex`, la clé de signature de l'esclave d'extension, qui peut aussi être définie ici) - les équivalents
propres de la puce esclave d'extension (`SLAVE_BOOTLOADER_FLASH_ADDR`,
`SLAVE_APP_FLASH_ADDR`, `SLAVE_HARDWARE_ID`, etc.) sont fixes dans le
propre `flasher_config.py`, puisque les valeurs réelles de ce matériel
sont déjà confirmées face à ses propres scripts d'édition de liens
réels plutôt que de nécessiter un remplacement au moment du déploiement
comme le nécessitent les valeurs par défaut propres de la carte
principale. Quelle source est active est enregistré au
démarrage, donc il est toujours visible quelles valeurs une session
donnée a réellement utilisées. `hardware_id` accepte soit une chaîne
JSON (`"0x0303CC01"`) soit un nombre JSON simple (`50580689`) - selon ce
qui est plus naturel pour la façon dont le fichier est généré.
`app_max_size`, `bootloader_max_size`, `flash_page_size`,
`bootloader_flash_addr`, et `app_flash_addr` sont aussi remplaçables
ici, aux côtés de la clé de signature et du HardwareID ci-dessus - utile
si cet outil est un jour adapté à une variante de puce ou un schéma de
partition différent.

## 🚀 Démarrage rapide

### Faites parler CAN à votre adaptateur

Ce dont vous avez besoin dépend de votre plateforme et du transport que
vous utiliserez :

**Linux, chemin SocketCAN (recommandé si votre adaptateur le prend en
charge) :**
Rien à flasher sur l'adaptateur lui-même. Activez l'interface une fois
par démarrage (ou ajoutez-la à votre configuration réseau pour qu'elle
persiste) :
```
sudo modprobe can vcan gs_usb   # gs_usb couvre la plupart des cartes de la famille CANable
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up
```
Si votre adaptateur s'énumère sous un nom autre que `can0`, vérifiez `ip
link show` (ou `dmesg` juste après l'avoir branché) pour le nom réel.
Certains adaptateurs nécessitent `slcand` au lieu d'un pilote natif - si
`ip link show` ne montre aucune interface CAN du tout après le
branchement, c'est probablement votre cas ; consultez la documentation
de votre adaptateur pour l'invocation de `slcand`, qui crée une
interface `slcan0` que vous activez ensuite de la même manière que
ci-dessus.

**Windows, ou Linux via le chemin Série/SLCAN :**
Une CANable Pro v2 est livrée par défaut avec le firmware
**candleLight**, qui parle à l'hôte en utilisant le protocole `gs_usb` -
le même que le pilote `gs_usb` de SocketCAN sous Linux attend
nativement (voir ci-dessus). Ce protocole ne se présente **pas** comme
un port série, ce dont ce chemin a besoin. Pour utiliser Série/SLCAN à
la place (obligatoire sous Windows ; optionnel sous Linux) :

1. Téléchargez un firmware compatible SLCAN pour votre adaptateur
   (cherchez "canable slcan firmware" — il existe quelques forks
   maintenus ; utilisez celui indiqué par la documentation de votre
   propre adaptateur).
2. Mettez l'adaptateur en mode DFU/bootloader (généralement un bouton
   BOOT maintenu pendant la mise sous tension, ou un cavalier - vérifiez
   la documentation de votre adaptateur).
3. Flashez le firmware SLCAN en utilisant l'outil de flash du fabricant
   de votre adaptateur ou `dfu-util`.
4. Reconnectez - il devrait maintenant s'énumérer comme port série : un
   port COM sous Windows, ou au style `/dev/ttyACM0`/`/dev/ttyUSB0` sous
   Linux.

Si votre adaptateur exécute déjà le firmware SLCAN, passez directement
à l'étape 2 ci-dessous.

Une ligne SLCAN reçue dont la longueur réelle ne correspond pas à ce
que son propre DLC déclaré implique est traitée comme malformée et
ignorée, plutôt qu'analysée à partir de ses premiers N caractères
hexadécimaux quoi qu'il suive - utile à savoir si vous déboguez contre
un adaptateur bruyant ou non standard.

### Installation et exécution

**Windows :**
```
python -m pip install -r requirements.txt
python urtc_flasher.py
```
Ou construisez un `.exe` autonome avec `build_exe.bat` (voir ce
fichier).

**Linux :**
```
python3 -m pip install -r requirements.txt
python3 urtc_flasher.py
```
Ou construisez un binaire autonome avec `./build_exe.sh` (`chmod +x`
d'abord).

Les deux scripts passent `--noconfirm` à PyInstaller, donc reconstruire
par-dessus un `dist/URTC_Flasher` déjà existant le remplace directement
au lieu d'attendre une invite "remplacer ?" facile à manquer dans la
sortie d'un script.

#### Console visuelle de contrôle

La console **Qt Quick** est la seule fenêtre du programme (testée uniquement contre le simulateur ; les vérifications d'image utilisent un HMAC-SHA256 à clé partagée). On la lance avec :
~~~
python urtc_flasher.py
~~~
Elle a une surface sombre bleu marine/cyan avec une carte de connexion, des tableaux de firmware lisibles, un journal de vérification sombre et un canal de progression visible, et couvre tout le flux : la mise à jour CAN-OTA de la carte principale ou de l'esclave d'extension (le choix de la cible ; l'option « la carte exécute l'application », l'effacement de la F-RAM et l'autorisation de retour à une version antérieure ne concernent que la carte principale), une sauvegarde du firmware installé via CAN, le sélecteur de débit du bus avec la recherche en écoute seule, le téléchargement d'une release GitHub, un sélecteur de fichier pour n'importe quel `.bin`, le contrôle de l'activité du bus, le Board Snapshot, les 4 écritures de configuration de l'appareil, la découverte SWD/JTAG en lecture seule et la programmation de la puce complète via SWD/JTAG (effacement/écriture, essai à blanc, sauvegarde avant effacement, contrôle RDP). Toute action qui écrit dans la carte demande d'abord une confirmation, l'autorisation de retour à une version antérieure en demande une seconde, et fermer la fenêtre pendant un transfert redemande. Rien de tout cela n'a été essayé sur une vraie carte. `python urtc_flasher.py --cli` est le mode sans interface (section 7).

#### En-tête et outils

- **En-tête** - l'état de la connexion, le sélecteur de langue (le choix est enregistré et s'applique au prochain démarrage) et la version.
- **Enregistrer les journaux...** et **Enregistrer le paquet de débogage** - le journal affiché en texte brut, ou un zip plus complet avec les diagnostics système et le fichier de firmware sélectionné (voir « Diagnostics » plus bas). Chaque session est aussi écrite dans `logs/`, et les plus récentes sont conservées.
- **À propos d'URTC Flasher** - version et auteur, avec des boutons pour **Lisez-moi** (dans la langue de l'interface si une traduction existe), **Licence** et la page **GitHub d'URTC** du projet.

**Langue** : anglais par défaut.
Se change avec le sélecteur de langue de l'en-tête de la fenêtre - enregistre immédiatement dans `urtc_config.json` (le même fichier
utilisé pour les remplacements techniques du matériel — la préférence
de langue vit simplement à côté de ceux-ci), appliqué au prochain
démarrage. Les traductions vivent dans des fichiers texte brut sous
`language/` (`english.lng`, `spanish.lng`, `italian.lng`, `french.lng`,
`german.lng`, `japanese.lng`, `chinese.lng`, `portuguese.lng`) sous forme de paires simples `CLE=Valeur`, une par ligne -
les lignes commençant par `#` et les lignes vides sont ignorées, et un
`\n` littéral dans une valeur devient un vrai saut de ligne (utilisé par
la poignée de messages de dialogue multi-lignes). Générés depuis le catalogue d'URTC-COMMON (une traduction s'y corrige et les fichiers sont réécrits, jamais modifiés à la main), ou comme point de départ pour une autre langue (ajoutez `language/<nom>.lng`, ajoutez
`("<nom>", "Nom Natif")` à `AVAILABLE_LANGUAGES` près du début de
`flasher_config.py`, et définissez `"language": "<nom>"` dans
`urtc_config.json`). Une clé manquante d'un fichier de langue retombe
sur l'affichage du nom de cette clé même plutôt que de planter, et un
fichier de langue manquant ou illisible (mauvaise modification, mauvais
nom de fichier) retombe sur l'anglais pour toute l'interface - dans les
deux cas l'outil reste utilisable pendant que le décalage se règle.

**Permissions série sous Linux :** si vous utilisez le chemin
Série/SLCAN et que la connexion échoue avec "Permission denied", votre
utilisateur doit être dans le groupe propriétaire des périphériques
série (`dialout` sur Debian/Ubuntu ; varie sur d'autres distributions) :
```
sudo usermod -a -G dialout $USER
```
Déconnectez-vous et reconnectez-vous (l'appartenance au groupe est lue à
la connexion), puis réessayez. L'outil détecte cette erreur spécifique
et affiche cette même solution dans une boîte de dialogue, mais cela
vaut la peine de le savoir à l'avance. SocketCAN n'a pas ce problème
particulier — l'accès à une interface de type `can0` n'est pas
contrôlé par le groupe `dialout` — mais activer l'interface en premier
lieu (étape 1 ci-dessus) nécessite quand même `sudo`, puisque c'est une
modification de configuration de périphérique réseau.

Utiliser `python -m pip`/`python3 -m pip` plutôt qu'un simple `pip`
évite un problème courant sur les deux plateformes : le script wrapper
de `pip` lui-même n'est pas toujours dans le PATH même juste après une
installation réussie, alors que `-m pip` trouve le module installé
directement.

### Où vont les fichiers de firmware

**Le dossier commence vide.** Les images de firmware ne sont pas conservées dans ce dépôt : ce sont les fichiers des releases d'[URTC](https://github.com/JuanenRac/URTC). La fenêtre les télécharge depuis la release choisie, et `python tools/sync_firmware.py` remplit le dossier depuis la dernière release officielle (ou `--release TAG`). Chaque fichier est vérifié avec la signature de la release (`.sig`, Ed25519) et ses empreintes avant d'être utilisé. Tant qu'aucune release officielle n'existe, le « latest » de GitHub répond 404 et `firmware_release.json` indique la release utilisée à la place (aujourd'hui la pré-release de banc) ; supprimez le fichier, ou changez son tag, quand une release officielle sera publiée.
Cet outil s'attend à un dossier `firmware/` juste à côté de
`urtc_flasher.py`, à la racine de ce même dépôt :

```
├── assets/
│   └── URTC_LOGO_FLASHER.svg      <- source de la banniere (vectorielle)
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v<version>.bin  <- placez les nouveaux fichiers .bin ici
│   ├── URTC_*  <- tools/sync_firmware.py remplace les fichiers URTC_* de ce dossier par ceux d'une release ; les autres fichiers restent
│   └── URTC_SLAVE_FIRMWARE_v<version>.bin    <- application du chip esclave d'extension, le cas echeant
├── logs/                          <- cree automatiquement, un fichier par session
├── urtc_config.json               <- optionnel, non inclus par defaut (voir "Changer la cle HMAC" ci-dessous)
├── urtc_flasher.py                <- point d'entrée : arguments CLI et démarrage de la fenêtre Qt Quick
├── flasher_config.py              <- E/S du fichier de configuration, chargement de la langue, constantes du protocole
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- wrappers STM32CubeProgrammer / pyOCD
├── flasher_validation.py          <- validation des fichiers firmware (.bin/.hex/.elf)
├── flasher_protocol.py            <- la machine a etats CAN OTA elle-meme, tant pour la carte principale que (relayee via son propre pont I2C) l'esclave d'extension
├── flasher_github.py               <- liste et télécharge les assets d'une release GitHub d'URTC
├── flasher_records.py             <- journaux de session (emplacement, conservation) et rapports de mise à jour
├── pytest.ini / ruff.toml          <- réglages de pytest et ruff (contrôles statiques)
├── requirements.txt
├── build_exe.bat                  <- build autonome pour Windows
├── build_exe.sh                   <- build autonome pour Linux
└── README.md
```

Cet outil est organisé dans les modules ci-dessus par responsabilité,
purement pour la lisibilité - il n'y a aucune différence fonctionnelle
entre les avoir comme fichiers séparés ou comme un seul gros fichier, et
il n'existe pas de forme monolithique à garder synchronisée comme c'est
le cas pour le firmware (ceci est un outil PC, pas quelque chose de
flashé sur la carte, donc il n'y a jamais qu'une seule forme).

Ceci est délibéré : ce dépôt entier est autonome. Si vous voulez juste
flasher une carte — sur un PC d'atelier, depuis une clé USB, n'importe
où — vous pouvez copier ce dépôt seul, et cela fonctionne quand même.

**Vous pouvez en garder plus d'un `.bin` là-dedans.** Chaque fichier de
firmware applicatif est vérifié et listé - l'outil ne prend pas
simplement le premier qu'il trouve, et les binaires de bootloader
(tout fichier avec "BOOTLOADER" dans le nom - `URTC_BOOTLOADER.bin`,
`URTC_SLAVE_BOOTLOADER.bin`) sont entièrement filtrés de cette liste,
puisque CAN-OTA ne flashe jamais que du firmware applicatif ; une mise
à jour du bootloader nécessite SWD/JTAG à la place (section 6
ci-dessous). Au démarrage (et chaque fois que vous cliquez sur
**Actualiser**), chaque `.bin` restant dans `firmware/` est vérifié
contre le même test de plausibilité que le bootloader lui-même applique
à une image fraîche (ses 4 premiers octets doivent ressembler à un vrai
pointeur de pile initial pour la RAM de cette puce, et sa taille doit
tenir dans l'emplacement principal). Chaque fichier apparaît dans la
liste avec un ✓ ou ✗ clair et la raison :

| Fichier | Taille | Statut |
|---|---|---|
| URTC_MAIN_FIRMWARE_v<version>.bin | 71.8 KB | ✓ semble valide |
| URTC_SLAVE_FIRMWARE_v<version>.bin | 33.9 KB | ✓ semble valide |
| notes.txt.bin | 0.1 KB | ✗ le premier mot ne ressemble pas a un pointeur de pile valide |

- **Exactement un fichier passe la vérification** → il est sélectionné
  pour vous au moment où l'outil démarre. Un fichier invalide seul dans
  le dossier n'est *pas* auto-sélectionné juste parce que rien d'autre
  ne le concurrence.
- **Plus d'un fichier valide** → rien n'est auto-sélectionné ; choisissez
  celui que vous voulez dans la liste.
- **Vous sélectionnez quand même un fichier semblant invalide** →
  l'outil vous demande de confirmer d'abord. Cette vérification existe
  pour attraper des erreurs évidentes (mauvais fichier, téléchargement
  tronqué, un espace réservé vide) - elle ne peut pas tout attraper (un
  fichier corrompu mais plausible, ou un signé avec la mauvaise clé), ce
  à quoi sert la propre vérification CRC32/HMAC du bootloader pendant le
  transfert réel.
- **Rien trouvé, ou vous voulez un fichier venant d'ailleurs
  entièrement** → utilisez le bouton **Parcourir .bin...**, qui
  fonctionne peu importe où le fichier vit réellement (et exécute la
  même vérification de validation dans les deux cas).
- **Vous voulez la dernière build sans avoir à la chercher vous-même**
  → **Télécharger depuis GitHub...** liste les fichiers joints à la
  dernière release GitHub du dépôt URTC
  (`github.com/JuanenRac/URTC/releases` ; les binaires du firmware sont
  publiés comme assets de la release, ils ne sont pas conservés dans git)
  et vous permet d'en choisir un à télécharger directement dans votre
  propre dossier `firmware/` local - il apparaît ensuite dans la liste
  ci-dessus comme n'importe quel autre fichier, sans redémarrage
  nécessaire. Saisissez un tag de release (par exemple `v0.3.5`) dans le
  champ en haut de la fenêtre et appuyez sur **Charger** pour lister une
  autre release que la dernière. Le `.sha256` et le `.manifest.json` de
  l'image sont téléchargés avec elle. Seuls les fichiers provenant des
  hôtes propres à GitHub (`github.com` et les hôtes de stockage des assets
  vers lesquels il redirige) sont acceptés, et un fichier dont la taille
  diffère de celle annoncée par la release est écarté. Utilise la propre
  API publique de GitHub (non authentifiée, donc soumise à la limite de
  60 requêtes/heure de GitHub si vous l'utilisez beaucoup en peu de
  temps ; une variable d'environnement `GITHUB_TOKEN` la relève) - rien
  ici ne nécessite un compte GitHub.

Chaque fichier d'une release officielle a une signature de release (`<fichier>.sig`, Ed25519) : le flasher la vérifie lorsqu'elle est présente et refuse une signature incorrecte. Un jeu sans signatures, comme une pré-release de banc, n'est accepté par `tools/sync_firmware.py` qu'avec `--allow-unsigned`.

**`<nomdefichier>.manifest.json` et `<nomdefichier>.sha256`, à côté de
chaque fichier firmware** - publiés par le build URTC pour chaque image (et
téléchargés avec elle depuis GitHub). Le manifeste contient la version, le
`sha256` et, pour les images d'application, la valeur `hmac_sha256` attendue par le bootloader (un HMAC-SHA256 à clé partagée, pas une signature asymétrique ; `signing_key_kind: dev` désigne la clé publique de développement) :

```json
{"component": "main_application", "version": "<version>", "sha256": "b48d4cd5...", "hmac_sha256": "b63a701e...", "signing_key_kind": "dev"}
```

Les deux empreintes sont vérifiées juste avant le flashage et une
différence **refuse le flashage** avant tout envoi sur le bus (mauvais
fichier, téléchargement corrompu ou manifeste périmé). C'est la signature
publiée qui est envoyée au bootloader, et la version du manifeste qui lui
est annoncée. Un fichier sans manifeste (votre propre build) n'est flashé
que si une clé de signature est définie dans `urtc_config.json` - voir plus
bas la modification de la clé HMAC.

Ajouter une nouvelle build plus tard : déposez-la simplement dans
`firmware/` et cliquez sur **Actualiser** - aucun redémarrage
nécessaire.

<!-- urtc-section:first_flash -->
### Premier démarrage sans matériel

1. Démarrez la carte virtuelle : `python -m urtc_can.virtual_board`.
2. Dans un autre terminal, définissez `URTC_VIRTUAL_PORT=socket://127.0.0.1:7777` et démarrez le flasher : la carte virtuelle est dans la liste des ports.
3. Sélectionnez-la, appuyez sur Connecter, choisissez une image de `firmware/` (ou parcourez) et appuyez sur Démarrer CAN-OTA.
4. La carte virtuelle accepte toute la mise à jour, avec les mêmes vérifications de taille, de signature et de version qu'une vraie. C'est un modèle : rien de cela n'a tourné sur une carte.
<!-- /urtc-section:first_flash -->

<!-- urtc-section:compatibility -->
### Prérequis et compatibilité

Les versions des programmes URTC qui fonctionnent ensemble, et la version du protocole que parle chacune, figurent dans le tableau de compatibilité que génère URTC-COMMON : [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Tests

La suite compte 500 tests dans 47 fichiers (`python -m pytest tests -q` ; avec Qt sur une machine sans écran, `QT_QPA_PLATFORM=offscreen` ; les 79 qui ont besoin de PySide6 sont ignorés sans lui) : le protocole CAN-OTA face à un vrai transport `MockCAN` qui rejoue un bootloader simulé complet (démarrage, effacement, réception, données de page et ACK, blocs HMAC, fin de mise à jour avec un vrai succès ou un `VERIFY_FAIL_REASON` précis), les règles de signature, les contrôles d'intégrité de l'image, le firmware inclus dans `firmware/` face à ses manifestes, les commandes SWD/JTAG construites avec `dry_run`, les fichiers de langue et les panneaux Qt Quick. Trois scripts à la racine (`verify_qt_*.py`) pilotent les panneaux Qt de bout en bout. La CI exécute aussi `ruff check`, `python -m mypy` et `tools/ci_validate.py`. `MockCAN` n'est qu'un modèle écrit à partir du protocole : il est plus indulgent que le vrai bootloader, donc une exécution verte ne remplace pas un essai sur une vraie carte.

## 🏗️ Compilation et publication

`build_exe.bat` / `build_exe.sh` construisent un programme autonome avec PyInstaller (les deux passent `--noconfirm`, donc reconstruire par-dessus un `dist/URTC_Flasher` existant le remplace directement) ; `build-test.sh` / `build-test.bat` vérifient tout sans rien construire ni changer de version. La version du programme (`FLASHER_VERSION` dans `flasher_config.py`, affichée dans la bannière de la fenêtre et la barre de titre) ne change que par l'étape explicite `python bump.py` ; lancer depuis les sources et compiler n'y touchent jamais. Voir `CHANGELOG.md` pour l'historique des versions.

## 📂 Structure du dépôt

<p align="center">
  <img src="images/repository-structure.svg" alt="Structure du dépôt URTC-FLASHER" width="100%">
</p>

<details>
<summary>Version texte de l'arborescence</summary>

```text
URTC-FLASHER/
├── urtc_flasher.py                                    point d'entrée
├── qt_flasher.py                                      le tableau Qt Quick
├── flasher_*.py                                       protocole, contrôles, transports, SWD, journaux
├── verify_qt_*.py                                     contrôles de bout en bout des panneaux Qt
├── urtc_can/                                          protocole, transports et mises à jour (copie)
├── urtc_ui/                                           aides d'interface (copie)
├── firmware/                                          où vont les images (vide au départ)
├── tests/                                             47 fichiers de test, un par domaine
├── language/                                          les huit fichiers de langue .lng
├── assets/                                            QML, bannière et icône
├── docs/                                              architecture, compilation et exécution
├── logs/                                              journaux de session (hors de Git)
├── tools/                                             contrôle de compilation, synchro du firmware, outils partagés
├── images/                                            bannière et images de ce README
├── .github/                                           workflow de CI et modèles d'issues et de pull requests
├── test.sh test.bat                                   lancent les tests
├── run.sh run.bat                                     lancent le programme
├── build-test.sh build-test.bat                       scripts de compilation et de test qui ne changent rien dans le dépôt
├── urtc.project.json                                  manifeste : version, rôle, maturité et commande de compilation
├── CHANGELOG.md                                       ce qui a changé à chaque version
├── SECURITY.md SUPPORT.md LICENSE                     politique de sécurité, assistance et licence
├── CONTRIBUTING.md CODE_OF_CONDUCT.md                 comment contribuer et code de conduite
├── .gitattributes .gitignore                          réglages Git
├── build_exe.sh build_exe.bat                         programme autonome (PyInstaller)
├── bump.py bump_version.py bump_manifest_version.py   scripts qui augmentent la version
├── requirements*.txt requirements*.lock               dépendances, avec leurs verrous
├── mypy.ini pytest.ini ruff.toml                      réglages des types, des tests et du lint
├── urtc_config.json.example                           exemple des réglages matériels et de la langue
├── urtc_i18n.lock.json                                verrou des fichiers de langue générés
└── NOTICE LICENSE.md                                  avis de droit d'auteur et licence de la documentation
```

</details>

La liste annotée de chaque fichier source, une ligne par fichier, est dans [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## 🗺️ Feuille de route et limites connues

**État :** le calcul de CRC32 et HMAC-SHA256 dans cet outil a été
vérifié octet par octet contre l'implémentation C propre du bootloader,
et l'empaquetage des trames SocketCAN a été vérifié contre la mise en
page `struct can_frame` de Linux avec un test d'empaquetage/
désempaquetage aller-retour. Ce qui n'a **pas** été testé sur l'une ou
l'autre des 2 plateformes est une carte réelle sur du matériel réel -
traitez la première vraie tentative de flash avec la même prudence que
vous accorderiez à tout nouvel outil parlant à un bootloader : gardez le
JTAG à portée de main comme solution de repli. Tout le reste décrit ici n'a été exercé que contre `MockCAN`, un bootloader simulé, jamais contre une vraie carte.

## 🌍 Langues

Le README et les textes existent en anglais, espagnol, français, italien, allemand, chinois, japonais et portugais européen.

## 🔗 Projets liés

URTC est fait de dépôts indépendants, chacun avec sa version, ses tests et son README. Voici la famille, par groupes :

* **URTC Tool Platform:** [URTC](https://github.com/JuanenRac/URTC), [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON), **URTC-FLASHER** (ce dépôt), [URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY), [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)
* **Ecosystem Operations:** [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS), [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)

**Projets frères (indépendants, avec la même base et les mêmes outils) :**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - projet frère : le centre de documentation de HYDRA-UMC, un écosystème indépendant qui partage la base et les outils de celui-ci
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - projet frère : le centre de documentation d'A.R.M.O.R., l'écosystème de sécurité, lui aussi indépendant et construit sur la même base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - le profil et le tableau d'état de tous les écosystèmes

## 📚 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pile technologique et lignes directrices de codage pour une pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — les normes de comportement attendues dans cette communauté.
- **[SECURITY.md](SECURITY.md)** — comment signaler une vulnérabilité, et les véritables axes de sécurité de ce projet.
- **[SUPPORT.md](SUPPORT.md)** — où poser des questions et signaler des bugs.
- **[LICENSE.md](LICENSE.md)** — la licence propre de ce projet.

## 🤝 Contribuer et communauté

* Avant une pull request, lancez `URTC_CI=1 python tools/ci_validate.py` : il doit réussir. Voir [CONTRIBUTING.md](CONTRIBUTING.md) et le [code de conduite](CODE_OF_CONDUCT.md).
* Le README existe en huit langues : une modification du texte se fait dans les huit fichiers, et les sections partagées avec d'autres dépôts sont écrites par `tools/readme_sections.py` d'URTC-COMMON.
* Un changement du protocole CAN commence dans URTC-COMMON (`spec/can_protocol.json`) et arrive dans ce dépôt par la copie vérifiée.
* Ne décrivez pas comme fonctionnant sur une carte ce qui a seulement été compilé.
* Signalez une vulnérabilité en privé : [SECURITY.md](SECURITY.md). Questions, idées et rapports : electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTEUR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCE

Licence : **GPL-3.0-or-later** pour le code source, **CC BY-SA 4.0** pour cette
documentation - voir `LICENSE` dans ce dépôt, ou la section « Licence
et Avis de Copyright » à la fin de ce document.

URTC Flasher est (c) 2026 JuanenRac (Electro Hobby 3D). Cet avis doit
être inclus dans toute distribution de ce projet ou de ses travaux
dérivés.

Ce projet consiste en du code source et sa propre documentation,
disponibles sous des licences différentes - chacune adaptée à ce
qu'elle couvre réellement :

1. Le code source (`urtc_flasher.py` et chaque module `flasher_*.py`)
   et tout binaire construit à partir de celui-ci via
   `build_exe.bat`/`build_exe.sh` sont disponibles sous la
   **GNU General Public License v3.0 or later (GPL-3.0-or-later)**. Texte complet sur
   https://www.gnu.org/licenses/gpl-3.0.html.

2. La documentation (ce README et ses propres traductions -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`, `README_por.md`)
   est disponible sous **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Texte complet sur
   https://creativecommons.org/licenses/by-sa/4.0/.

Cet outil est le compagnon de flashage CAN-OTA/SWD-JTAG du projet
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
- voir le propre dépôt de ce projet pour le firmware de la carte, les
conceptions matérielles, et la documentation complète du protocole
contre lequel cet outil fonctionne. Le propre firmware d'URTC est
GPL-3.0-or-later et ses conceptions matérielles sont CERN-OHL-S v2 ; la propre
licence de cet outil ici ne s'étend pas à ce projet séparé, et
vice-versa. Une alternative basée sur le web couvrant un terrain
similaire existe aussi sur
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Si vous construisez sur ce projet, gardez la séparation des licences à
l'esprit : les modifications de code devraient rester GPL-3.0-or-later, les
dérivés de documentation devraient rester CC BY-SA - chacun avec une
attribution à ce projet et son auteur.
