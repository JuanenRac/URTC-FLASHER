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
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/Licence-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Langage-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Tkinter%20%7C%20Qt%20Quick-38d4e6.svg" alt="Tkinter and Qt Quick">
  <img src="https://img.shields.io/badge/Protocole-CAN--OTA-orange.svg" alt="CAN-OTA">
</p>


**Version :** 0.1.0 (la version de cet outil - affichée dans la bannière
de la fenêtre et la barre de titre, suivie séparément de la version du
firmware de la carte URTC qu'il écrit. Suit un schéma X.Y.Z où le numéro
de patch augmente automatiquement à chaque build réel via
build_exe.bat/build_exe.sh - voir CHANGELOG.md pour l'historique des
versions et bump_version.py pour la règle exacte de report)

**Auteur :** JuanenRac (Electro Hobby 3D) &lt;electrohobby3d@gmail.com&gt;

Licence : **GPL-3.0** pour le code source, **CC BY-SA 4.0** pour cette
documentation - voir `LICENSE` dans ce dépôt, ou la section « Licence
et Avis de Copyright » à la fin de ce document.

Un petit outil graphique multiplateforme pour mettre à jour le firmware
de la carte URTC via le bus CAN. Il implémente exactement le protocole
du bootloader de `docs/CANBUS.TXT` : la vérification du HardwareID, la
signature HMAC-SHA256, le flux de mise à jour avec emplacement de
sauvegarde à image dorée, la progression en direct via les messages de
battement de cœur du bootloader, et une requête de version (identifie si
l'application *ou* le bootloader de cette carte s'annonce via CAN) pour
que vous puissiez voir ce qui est actuellement installé avant de
décider quoi flasher.

Deux façons de parler à la carte, toutes deux utilisant le même
protocole en dessous :

- **Série / SLCAN** — fonctionne sur Windows et Linux. Nécessite un
  adaptateur USB-CAN exécutant le firmware SLCAN, connecté comme port
  série virtuel.
- **SocketCAN** — **Linux uniquement**, et affiché uniquement dans
  l'interface de l'outil sous Linux. Parle directement à une interface
  réseau du noyau `can0`/`slcan0`. Si votre adaptateur exécute déjà le
  firmware `gs_usb`/candleLight (la plupart des cartes CANable le font
  d'origine), ce chemin **ne nécessite aucun reflash de l'adaptateur**
  — le pilote natif de Linux le gère directement.

**État :** le calcul de CRC32 et HMAC-SHA256 dans cet outil a été
vérifié octet par octet contre l'implémentation C propre du bootloader,
et l'empaquetage des trames SocketCAN a été vérifié contre la mise en
page `struct can_frame` de Linux avec un test d'empaquetage/
désempaquetage aller-retour. Ce qui n'a **pas** été testé sur l'une ou
l'autre des 2 plateformes est une carte réelle sur du matériel réel -
traitez la première vraie tentative de flash avec la même prudence que
vous accorderiez à tout nouvel outil parlant à un bootloader : gardez le
JTAG à portée de main comme solution de repli.

## 1. 🔌 Faites parler CAN à votre adaptateur
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

## 2. 💻 Installation et exécution
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

Le panneau de connexion affiche également la marque officielle HYDRA-UMC
animée. Sa source SVG maintenue est `assets/HYDRA_UMC_ICON.svg` ; douze
images PNG incluses conservent l’animation dans Tkinter et dans l’exécutable
autonome sans ajouter de dépendance graphique à l’exécution. L’icône native
URTC de fenêtre/barre des tâches reste volontairement statique.

### Console visuelle de contrôle

La console de commandes partagée **Qt Quick** est disponible pour le flux
CAN-OTA réel :
~~~
python urtc_flasher.py --qtquick
~~~
Elle utilise les mêmes transports de production, validations et code de
flashage signé que l'interface établie. Tkinter reste l'interface par défaut
tant que les écrans avancés SWD/JTAG et de configuration de carte n'ont pas
atteint la parité fonctionnelle ; n'utilisez pas encore Qt Quick pour ces
opérations avancées.

Le flux CAN-OTA et SWD/JTAG établi est conservé sur une surface de contrôle
bleu nuit/cyan : en-tête produit, carte de connexion contrastée, tableaux de
firmware lisibles, journal de vérification sombre et progression visible.
Cette amélioration visuelle et d’accessibilité ne modifie ni le protocole du
bootloader ni le comportement de sécurité matériel.

### Barre de menu

- **Fichier** - Enregistrer les journaux (le journal à l'écran en texte
  brut ; pour un paquet plus complet incluant les diagnostics système et
  le fichier de firmware actuellement sélectionné, voir "Diagnostics"
  plus bas), et Quitter.
- **Langue** - basculer entre les 7 langues disponibles (voir "Langue"
  plus bas pour savoir comment fonctionnent les traductions).
- **Aide** - Lisez-moi (ouvre ce fichier dans une fenêtre visualiseur en
  lecture seule ; récupère automatiquement une version traduite dès
  qu'il en existe une pour la langue actuelle), GitHub d'URTC (ouvre le
  dépôt du projet dans votre navigateur), Licence (la licence GPL-3.0 de
  cet outil, lue depuis le fichier `LICENSE` du dépôt lui-même), et À
  propos (version et auteur).

**Au démarrage**, la bannière s'affiche centrée à l'écran pendant 5
secondes avant que la fenêtre principale n'apparaisse - elle ne fait pas
partie de la fenêtre principale elle-même (c'est pourquoi la fenêtre
est plutôt compacte pour tout ce qu'elle fait réellement). L'icône de
fenêtre/barre des tâches est un petit design autonome
(`assets/urtc_icon.png`/`.ico`), pas la bannière rétrécie - l'illustration
complète de la bannière ne tient pas bien à 16-32px.

**Langue** : anglais par défaut.
Se change via le menu **Langue** (dans la barre de menu en haut de la
fenêtre) plutôt qu'une liste déroulante dans la fenêtre principale -
enregistre immédiatement dans `urtc_config.json` (le même fichier
utilisé pour les remplacements techniques du matériel — la préférence
de langue vit simplement à côté de ceux-ci), appliqué au prochain
démarrage. Les traductions vivent dans des fichiers texte brut sous
`language/` (`english.lng`, `spanish.lng`, `italian.lng`, `french.lng`,
`german.lng`) sous forme de paires simples `CLE=Valeur`, une par ligne -
les lignes commençant par `#` et les lignes vides sont ignorées, et un
`\n` littéral dans une valeur devient un vrai saut de ligne (utilisé par
la poignée de messages de dialogue multi-lignes). Modifiable
directement si une traduction nécessite une correction, ou comme point
de départ pour une autre langue (ajoutez `language/<nom>.lng`, ajoutez
`("<nom>", "Nom Natif")` à `AVAILABLE_LANGUAGES` près du début de
`flasher_config.py`, et définissez `"language": "<nom>"` dans
`urtc_config.json`). Une clé manquante d'un fichier de langue retombe
sur l'affichage du nom de cette clé même plutôt que de planter, et un
fichier de langue manquant ou illisible (mauvaise modification, mauvais
nom de fichier) retombe sur l'anglais pour toute l'interface - dans les
deux cas l'outil reste utilisable pendant que le décalage se règle.

Tkinter (la boîte à outils graphique) est fourni avec Python sous
Windows, mais sur les distributions de la famille Debian/Ubuntu c'est un
paquet système séparé :
```
sudo apt install python3-tk
```
(Fedora : `sudo dnf install python3-tkinter`. Arch : `sudo pacman -S
tk`.) `build_exe.sh` vérifie cela lui-même et vous prévient si c'est
manquant plutôt que d'échouer à mi-chemin.

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

## 3. 📁 Où vont les fichiers de firmware
Cet outil s'attend à un dossier `firmware/` juste à côté de
`urtc_flasher.py`, à la racine de ce même dépôt :

```
├── assets/
│   ├── URTC_LOGO_FLASHER.svg      <- source de la banniere (vectorielle)
│   └── urtc_banner.png            <- affichee en haut de la fenetre, rendue depuis le .svg ci-dessus
├── firmware/
│   ├── URTC_V1.1_F303CC.bin      <- placez les nouveaux fichiers .bin ici
│   └── URTC_SLAVE_APP.bin        <- application du chip esclave d'extension, le cas echeant
├── logs/                          <- cree automatiquement, un fichier par session
├── urtc_config.json               <- optionnel, non inclus par defaut (voir "Changer la cle HMAC" ci-dessous)
├── urtc_flasher.py                <- point d'entree : arguments CLI, ecran de demarrage, configuration de la fenetre principale
├── flasher_config.py              <- E/S du fichier de configuration, chargement de la langue, constantes du protocole
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- wrappers STM32CubeProgrammer / pyOCD
├── flasher_validation.py          <- validation des fichiers firmware (.bin/.hex/.elf)
├── flasher_protocol.py            <- la machine a etats CAN OTA elle-meme, tant pour la carte principale que (relayee via son propre pont I2C) l'esclave d'extension
├── flasher_github.py               <- telecharge le firmware depuis le propre depot GitHub de ce projet
├── flasher_gui.py                 <- la fenetre principale (FlasherGUI) et sa barre de menu
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

`assets/urtc_banner.png` est optionnel - s'il manque, l'outil démarre
simplement sans bannière plutôt que d'échouer. Il est chargé via le
support PNG natif de tkinter (Tk 8.6+, inclus avec chaque version
actuelle de Python), pas Pillow, donc cela n'ajoute pas de nouvelle
dépendance. `build_exe.bat` et `build_exe.sh` empaquettent déjà
`assets/` dans l'exécutable autonome via le `--add-data` de
PyInstaller, donc cela fonctionne de la même manière que vous exécutiez
depuis la source ou depuis un binaire construit.

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
| URTC_V1.1_F303CC.bin | 30.9 KB | ✓ semble valide |
| URTC_SLAVE_APP.bin | 12.4 KB | ✓ semble valide |
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
  → **Télécharger depuis GitHub...** récupère la liste de fichiers
  actuelle directement depuis le propre dossier `firmware/` de ce
  projet (`github.com/JuanenRac/URTC/tree/main/firmware`) et vous
  permet d'en choisir un à télécharger directement dans votre propre
  dossier `firmware/` local - il apparaît ensuite dans la liste
  ci-dessus comme n'importe quel autre fichier, sans redémarrage
  nécessaire. Utilise la propre API publique de GitHub (non
  authentifiée, donc soumise à la propre limite de fréquence de GitHub
  de 60 requêtes/heure si vous l'utilisez beaucoup en peu de temps) -
  rien ici ne nécessite un compte GitHub ou un jeton.

**`<nomdefichier>.manifest.json` optionnel, à côté d'un fichier
firmware** (p. ex. `URTC_V1.1_F303CC.bin.manifest.json`), ajoute une
vérification de bon sens supplémentaire et non bloquante : si présent,
son champ `sha256` est comparé au fichier réel juste avant de flasher,
avec `version`/`build_date` enregistrés à côté pour référence.

```json
{"version": "1.1", "build_date": "2024-01-15", "sha256": "e5a4918c..."}
```

Une discordance est enregistrée comme un avertissement clair, pas un
arrêt forcé - ceci est une vérification de commodité pour attraper tôt
un fichier évidemment erroné ou corrompu, pas un substitut à la propre
vérification HMAC du bootloader pendant le transfert réel, qui reste la
vérification faisant autorité de toute façon.

Ajouter une nouvelle build plus tard : déposez-la simplement dans
`firmware/` et cliquez sur **Actualiser** - aucun redémarrage
nécessaire.

## 4. 🔍 Vérifier ce qui est actuellement installé
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

Ce que vous verrez :

- **`v1.1 (application, HardwareID 0x0303CC01)`** - cas normal,
  application en cours d'exécution, tout correspond.
- **`Bootloader running, no valid firmware currently installed,
  bootloader v1.1.2`** - la carte est coincée dans le bootloader sans
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

## 5. ⚡ Flasher
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
   puce esclave (les propres `0x210`-`0x218` de `CANBUS.TXT`), pas une
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
qu'un fichier silencieusement vide.

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

## 6. 🛠️ Programmer la puce complète via SWD/JTAG (avancé)
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

## 7. ⌨️ Mode CLI (sans affichage, pas de GUI)
Pour les pipelines CI, bancs de test, ou scripting de ligne de
production où il n'y a pas d'écran :

```
python3 urtc_flasher.py --cli --port /dev/ttyACM0 --file firmware.bin
```

```
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan}] --port PORT
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

## 8. 🔄 Fiabilité pendant une mise à jour CAN, et journaux de session
Si l'ACK d'une page n'arrive pas dans la fenêtre normale de 3s pendant
une mise à jour CAN, l'outil retente l'*attente* (pas un renvoi des
données de la page) jusqu'à deux fois de plus avec un court délai
croissant avant d'abandonner, se remettant d'un ACK retardé ou perdu sur
un bus bruyant sans que les données sous-jacentes soient perdues. Il ne
renvoie délibérément pas les données de page sur un timeout - si les
données originales sont réellement bien arrivées et que seul l'ACK a
été perdu, renvoyer ferait lire au bootloader ces octets comme le début
de la *prochaine* page, désynchronisant le transfert. Chaque nouvelle
tentative vérifie aussi le battement de cœur propre du bootloader
(envoyé environ une fois par seconde) contre ce qu'impliquerait avoir
reçu la page actuelle en entier - quand ils sont cohérents, le journal
le dit, ce qui est une preuve réelle que les données sont passées et
que seul l'ACK a été perdu, pas juste une attente plus longue et un
espoir.

Chaque session écrit aussi un fichier journal horodaté dans
`logs/` (`urtc_flasher_YYYYMMDD_HHMMSS.log`),
indépendant du journal à l'écran - utile pour remettre une trace
complète à celui qui a écrit le firmware si quelque chose ne va pas sur
le terrain. Ce dossier est créé automatiquement et est sûr à
supprimer ; rien ne relit d'anciens journaux.

## 9. 📊 Diagnostics — activité du bus, débit binaire, et paquets de débogage
**Sélecteur de débit binaire + détection automatique** (Série/SLCAN
uniquement) : le bus d'URTC est fixé à 500 kbit/s, qui reste la valeur
par défaut - ceci est pour un adaptateur mal configuré ou pour déboguer
une carte non standard. **Détection automatique** essaie chaque débit
binaire SLCAN standard à tour de rôle contre une requête de version et
s'arrête au premier qui obtient une vraie réponse ; pas encore connecté
quand vous cliquez dessus. Le débit binaire de SocketCAN est défini au
niveau du système d'exploitation (`ip link`), donc ce contrôle est
désactivé pour ce transport - il n'y a rien ici à essayer.

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

## 10. 🔬 SWD/JTAG — formats de fichiers, vérification d'emplacement, et sélection de sonde
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
gestionnaires de reset sont `0x080030F1` et `0x0800C725`
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

## 11. 📡 Télémétrie de transfert et détail d'échec de vérification
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

## 12. 🧹 Effacement optionnel de la F-RAM avant de flasher
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

## 🔑 Changer la clé HMAC / le HardwareID

La clé de signature partagée vit à 2 endroits qui doivent toujours
correspondre : le tableau `HMAC_KEY` de `bootloader_common.h`, et la constante
`HMAC_KEY` de cet outil près du début de `flasher_config.py`. Si vous en
changez une, changez l'autre et reconstruisez/reflashez le bootloader
avant d'essayer de signer quoi que ce soit avec la nouvelle clé - une
image signée avec une clé que le bootloader n'a pas échouera toujours
la vérification, en sécurité, laissant l'emplacement principal
intact.

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
pour une faute de frappe. **Ce mécanisme de remplacement ne s'applique
qu'aux constantes propres de la carte principale** - les équivalents
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

## 📸 Photos

<p align="center">
  <img src="images/URTC_FLASHER_V1_1.png" alt="Fenêtre URTC Flasher" width="700">
</p>

## 📂 Structure du dépôt

Le répertoire `assets/` contient aussi `HYDRA_UMC_ICON.svg`, la source
vectorielle animée maintenue, et `hydra_umc_icon_frames/`, ses douze
images PNG groupées pour Tkinter. `tools/render_hydra_umc_icon_frames.py`
les régénère depuis le SVG pendant le développement ; ce n'est pas requis
pour exécuter l'application.

```
├── assets/
│   ├── URTC_APP_ICON.svg          <- icône partagée app/barre des tâches (vectorielle)
│   ├── URTC_LOGO_FLASHER.svg      <- source de la bannière (vectorielle), affichée centrée 5s au démarrage
│   ├── HYDRA_UMC_ICON.svg         <- source vectorielle animée HYDRA-UMC maintenue
│   ├── hydra_umc_icon_frames/     <- douze images PNG pour Tkinter rendues depuis le SVG ci-dessus
│   ├── qml/
│   │   └── FlasherDeck.qml        <- UI Qt Quick du command deck CAN-OTA `--qtquick`
│   ├── urtc_banner.png            <- rendue à partir du .svg ci-dessus, affichée en haut de la fenêtre
│   ├── urtc_icon.ico              <- icône barre des tâches/fenêtre sous Windows
│   └── urtc_icon.png              <- icône barre des tâches/fenêtre sous Linux
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v0.2.5.bin     <- firmware applicatif actuel de la carte principale
│   ├── URTC_MAIN_BOOTLOADER_v0.3.4.bin   <- bootloader de la carte principale (SWD/JTAG uniquement, exclu de la
│   │                                         liste de firmware CAN-OTA - voir section 3 ci-dessus)
│   ├── URTC_SLAVE_FIRMWARE_v0.1.4.bin    <- application de la puce esclave d'extension (cartes d'extension avancées uniquement)
│   └── URTC_SLAVE_BOOTLOADER_v0.1.7.bin  <- bootloader de la puce esclave d'extension
├── images/
│   ├── URTC_FLASHER_BANNER.svg    <- bannière du logo affichée en haut de ce README
│   └── URTC_FLASHER_V1_1.png      <- capture d'écran réelle de la fenêtre, affichée dans la section Photos ci-dessus
├── language/
│   ├── english.lng                <- langue par défaut, paires KEY=Value en texte brut
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   └── chinese.lng
├── logs/                           <- créé automatiquement, un fichier par session
├── urtc_config.json.example        <- modèle pour le fichier optionnel de surcharge urtc_config.json
│                                       (voir "Changer la clé HMAC / le HardwareID" ci-dessus) - copiez-le
│                                       en urtc_config.json et modifiez-le, plutôt que de repartir de zéro
├── urtc_flasher.py                <- point d'entrée : arguments CLI, écran de démarrage, configuration de la fenêtre principale
├── qt_flasher.py                  <- front end Qt Quick - command deck CAN-OTA `--qtquick` réel,
│                                       réutilise les mêmes classes de transport/validation/protocole ci-dessous
├── hydra_umc_animation.py         <- widget d'identité HYDRA-UMC animé pour Tkinter
├── hydra_umc_deck_widgets.py      <- widgets arrondis du command deck HYDRA-UMC partagés par les
│                                       surfaces de diagnostic en direct
├── flasher_config.py              <- E/S du fichier de configuration, chargement de la langue, constantes du protocole
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- wrappers STM32CubeProgrammer / pyOCD
├── flasher_validation.py          <- validation des fichiers firmware (.bin/.hex/.elf)
├── flasher_protocol.py            <- la machine à états CAN OTA elle-même
├── flasher_github.py              <- télécharge le firmware depuis le dépôt GitHub d'URTC
├── flasher_gui.py                 <- la fenêtre principale (FlasherGUI) et sa barre de menus
├── requirements.txt                <- pyserial>=3.5 (tester Tkinter) + PySide6>=6.8,<7 (deck `--qtquick`)
├── build_exe.bat                  <- build autonome pour Windows
├── build_exe.sh                   <- build autonome pour Linux
├── build-test.bat                 <- contrôle build/compilation sans gestion de version
├── build-test.sh                  <- le même, pour Linux
├── bump_version.py                <- incrément de version type compteur kilométrique, exécuté par les scripts de build
├── bump_manifest_version.py       <- synchronise la version de hydra-umc.project.json avec la version native (--sync)
├── URTC_Flasher.spec              <- spec PyInstaller utilisée par les deux scripts de build ci-dessus
├── docs/
│   └── CLI_REFERENCE.md           <- référence des options de ligne de commande
├── tools/
│   ├── ci_validate.py                    <- validation manifest/CHANGELOG/docs utilisée par la CI
│   └── render_hydra_umc_icon_frames.py   <- régénère assets/hydra_umc_icon_frames/ depuis le SVG (développement uniquement)
├── README.md                      <- (version anglaise)
├── README_fra.md                  <- ce fichier
├── README_spa.md / README_ita.md / README_deu.md / README_zho.md / README_jpn.md  <- autres traductions
├── LICENSE
├── .gitattributes
└── .gitignore
```

Cet outil est organisé dans les modules `flasher_*.py` ci-dessus par
responsabilité, purement pour la lisibilité - il n'y a aucune différence
fonctionnelle entre les avoir comme fichiers séparés ou comme un seul
gros fichier.

## 🔗 Projets Liés

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Projet Parent**
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware pour la carte physique Universal Robot Tool Controller, plus de 25 profils d'outil sur bus CAN ; le parent dont ce dépôt est un outil spécifique, au sein de sa propre famille d'outils CAN-bus.

**Projets Frères** — les autres outils de la propre famille d'outils CAN-bus d'URTC
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic CAN-bus en direct pour cartes URTC, un panneau par profil d'outil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative basée navigateur à URTC-TESTER via la Web Serial API, sans installation locale.

**Directement Liés**
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flotte avec un vrai contrat de codes de sortie stable, un vrai client en direct de la propre API de HYDRA-UMC-SERVER — fait à l'échelle de la flotte (la commande `flash-all`) ce que cet outil fait pour une seule carte.

**Fait Également Partie de l'Écosystème**

*Matériel & Plateforme de Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère physique du bras robotique : hôte CM5 + coprocesseur STM32H745 double cœur, coordonnant jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — couche produit reproductible sur Raspberry Pi OS pour le CM5 : agent en lecture seule, config/profils validés, provisionnement WiFi de premier contact.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — le contrat JSON-Schema partagé et la barrière de sécurité contre laquelle chaque bridge valide ses commandes.

*Backend Central & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le vrai backend headless (REST/WebSocket) auquel parle réellement chaque client de contrôle.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande d'essaim de bureau (PySide6) pour plusieurs serveurs à la fois, empaqueté en exécutable autonome.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et un compagnon Wear OS jumelé.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran tactile DSI 7" embarqué, intégrée directement sur le CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour URDF qui envoie les modèles terminés vers le propre catalogue de STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — frontière de coordination pour les flottes AGV/AMR via un éditeur MQTT VDA 5050 réel.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur haut niveau pour cellules CNC avec accès réel au statut/octets de contrôle GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — frontière de coordination pour droïdes à pattes/humanoïdes, avec un véritable émetteur de commandes Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de sécurité pour cellules laser lisant 3 vraies sécurités GPIO de clé/enceinte/verrouillage.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur haut niveau sûr pour le flux de cartes du pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — frontière de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec de vraies commandes de tâche contrôlées.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur de sécurité avec un vrai transport ROS 2 rclpy à importation paresseuse.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — frontière de coordination pour UAV équipés de caméra, avec un véritable émetteur de commandes MAVLink.

*Nœud IA de Vision (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration pour le pipeline de vision Hailo-8, avec une vraie vérification de disponibilité matérielle par étape.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification de chargement sécurisé par architecture Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — générateur réel de pipeline GStreamer + config MediaMTX, avec une vraie frontière d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — vraie loi de correction Position-Based Visual Servoing, verrouillée sur l'état de zone en amont.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vraie vérification de violation de zone et demande d'E-STOP, avec application de la fraîcheur de calibration.

*Nœud IA Cognitif (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub d'intégration pour le pipeline cognitif Hailo-10 (orchestration LLM/VLA/voix).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vrai encodage/décodage de jetons d'action et génération de trajectoire pour un modèle Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vrai front-end vocal (VAD + analyseur d'intention) avec un relais Watch borné et soumis à confirmation.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vraie décomposition de tâches basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vraie recherche documentaire TF-IDF (bibliothèque standard uniquement) sur les propres documents Markdown de cet écosystème.

*Orchestration & Essaim*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un vrai contrat de rapport de santé gRPC/Protobuf et une machine à états de mission.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vraie file de tâches basée sur la priorité avec déduplication, via une vraie API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vrai chien de garde de santé de flotte basé sur gRPC, avec retry/backoff et détection d'incohérence d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vrai planificateur de trajectoire 3D basé sur RRT, avec vraie validation des collisions obstacle/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vraie synchronisation d'état CRDT LWW-Element-Map, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration pour le moteur de jumeau numérique, avec un vrai contrat de synchronisation par compatibilité de version.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — vrai verrouillage de sécurité hardware-in-the-loop routant les commandes entre simulation et matériel réel.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vraie cinématique directe et validation des limites articulaires sur un vrai sous-ensemble URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vrai générateur procédural de scènes 2D avec export d'annotations YOLO/COCO.

*Données & Analytique*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vrai magasin de séries temporelles basé sur sqlite3, avec une vraie API HTTP d'ingestion/requête.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vrai détecteur d'anomalies FFT + ligne de base statistique, avec surveillance de dérive.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vrai calcul OEE/disponibilité sur l'historique de DATALAKE, avec export CSV reproductible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vrai pipeline d'ingestion CAN/WebSocket vers DATALAKE, avec déduplication par séquence.

*Passerelle Industrielle*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub d'intégration relayant vers les protocoles industriels, avec une vraie couche de liste blanche de commandes/contre-pression.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vrai espace d'adressage OPC-UA, vérifié avec une vraie session client du protocole binaire.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vrai broker MQTT avec authentification par client optionnelle et ACL de sujets.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — vrais points de terminaison XML MTConnect `/probe` et `/current`, avec sortie en mode dégradé.

*Outils Complémentaires & Opérations de l'Écosystème*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — panneaux Smart Summaries et Anomaly Highlighting sur DATALAKE/ANOMALY-DETECTOR, avec un repli statistique honnête.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec de vraies alertes haptiques et un relais vocal vers le téléphone jumelé.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware pour un rack de montage de cartes avec décodage réel d'ID d'outil et logique de préchauffage Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus un vrai compagnon de vision Python pour une tête d'outil d'inspection thermique/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — outil administratif de bureau qui découvre, clone et met à jour chaque dépôt de cet écosystème.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — outil de bureau Windows/Linux qui construit une image de la CM5 prête à graver, préchargée avec les versions les plus actuelles de l'écosystème, avec une configuration de premier démarrage Wi-Fi/utilisateur/SSH façon Raspberry Pi Imager.

## 📜 LICENCE

URTC Flasher est (c) 2026 JuanenRac (Electro Hobby 3D). Cet avis doit
être inclus dans toute distribution de ce projet ou de ses travaux
dérivés.

Ce projet consiste en du code source et sa propre documentation,
disponibles sous des licences différentes - chacune adaptée à ce
qu'elle couvre réellement :

1. Le code source (`urtc_flasher.py` et chaque module `flasher_*.py`)
   et tout binaire construit à partir de celui-ci via
   `build_exe.bat`/`build_exe.sh` sont disponibles sous la
   **GNU General Public License v3.0 (GPL-3.0)**. Texte complet sur
   https://www.gnu.org/licenses/gpl-3.0.html.

2. La documentation (ce README et ses propres traductions -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`)
   est disponible sous **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Texte complet sur
   https://creativecommons.org/licenses/by-sa/4.0/.

Cet outil est le compagnon de flashage CAN-OTA/SWD-JTAG du projet
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
- voir le propre dépôt de ce projet pour le firmware de la carte, les
conceptions matérielles, et la documentation complète du protocole
contre lequel cet outil fonctionne. Le propre firmware d'URTC est
GPL-3.0 et ses conceptions matérielles sont CERN-OHL-S v2 ; la propre
licence de cet outil ici ne s'étend pas à ce projet séparé, et
vice-versa. Une alternative basée sur le web couvrant un terrain
similaire existe aussi sur
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Si vous construisez sur ce projet, gardez la séparation des licences à
l'esprit : les modifications de code devraient rester GPL-3.0, les
dérivés de documentation devraient rester CC BY-SA - chacun avec une
attribution à ce projet et son auteur.

---

## 📚 Documentation & Communauté

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pile technologique et lignes directrices de codage pour une pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — les normes de comportement attendues dans cette communauté.
- **[SECURITY.md](SECURITY.md)** — comment signaler une vulnérabilité, et les véritables axes de sécurité de ce projet.
- **[SUPPORT.md](SUPPORT.md)** — où poser des questions et signaler des bugs.
- **[LICENSE.md](LICENSE.md)** — la licence propre de ce projet.

## 👤 AUTEUR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
