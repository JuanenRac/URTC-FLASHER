<p align="center">
  <img src="/images/URTC_FLASHER_BANNER.svg" alt="URTC Flasher Logo" width="100%">
</p>

# URTC Flasher (Windows / Linux)

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  🇩🇪 <b>Deutsch</b> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/Lizenz-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Sprache-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Tkinter%20%7C%20Qt%20Quick-38d4e6.svg" alt="Tkinter and Qt Quick">
  <img src="https://img.shields.io/badge/Protokoll-CAN--OTA-orange.svg" alt="CAN-OTA">
</p>


**Version:** 0.1.0 (die Version dieses Tools selbst - angezeigt im
Fenster-Banner und in der Titelleiste, getrennt verfolgt von der
Firmware-Version der URTC-Platine, die es schreibt. Folgt einem
X.Y.Z-Schema, bei dem die Patch-Nummer bei jedem echten Build über
build_exe.bat/build_exe.sh automatisch erhöht wird - siehe CHANGELOG.md
für den Versionsverlauf und bump_version.py für die genaue Übertragsregel)

**Autor:** JuanenRac (Electro Hobby 3D) &lt;electrohobby3d@gmail.com&gt;

Lizenz: **GPL-3.0** für den Quellcode, **CC BY-SA 4.0** für diese
Dokumentation - siehe `LICENSE` in diesem Repository, oder den
Abschnitt „Lizenz und Urheberrechtshinweise" am Ende dieses Dokuments.

Ein kleines plattformübergreifendes GUI-Tool zum Aktualisieren der
URTC-Platinen-Firmware über den CAN-Bus. Es implementiert genau das
Bootloader-Protokoll aus `docs/CANBUS.TXT`: die HardwareID-Prüfung, die
HMAC-SHA256-Signierung, den Golden-Image-Backup-Slot-Update-Ablauf, den
Live-Fortschritt über die Heartbeat-Nachrichten des Bootloaders, und
eine Versionsabfrage (identifiziert, ob sich die Anwendung *oder* der
Bootloader dieser Platine über CAN meldet), damit Sie sehen können, was
aktuell installiert ist, bevor Sie entscheiden, was geflasht werden
soll.

Zwei Wege, mit der Platine zu sprechen, beide sprechen darunter dasselbe
Protokoll:

- **Seriell / SLCAN** — funktioniert unter Windows und Linux. Benötigt
  einen USB-CAN-Adapter mit SLCAN-Firmware, verbunden als virtueller
  serieller Port.
- **SocketCAN** — **nur Linux**, und nur in der Benutzeroberfläche des
  Tools unter Linux angezeigt. Spricht direkt mit einer
  Kernel-Netzwerkschnittstelle `can0`/`slcan0`. Wenn Ihr Adapter
  bereits `gs_usb`/candleLight-Firmware ausführt (die meisten
  CANable-Platinen tun dies ab Werk), benötigt dieser Weg
  **überhaupt kein Reflashen des Adapters** — der native Treiber von
  Linux übernimmt dies direkt.

**Status:** die CRC32- und HMAC-SHA256-Berechnung in diesem Tool wurde
Byte für Byte gegen die eigene C-Implementierung des Bootloaders
verifiziert, und das SocketCAN-Frame-Packing wurde gegen das
`struct can_frame`-Layout von Linux mit einem Hin-und-Rück-Pack/Unpack-
Test verifiziert. Was auf keiner der 2 Plattformen getestet wurde, ist
eine echte Platine auf echter Hardware - behandeln Sie einen ersten
echten Flash-Versuch mit derselben Vorsicht, die Sie jedem neuen Tool
entgegenbringen würden, das mit einem Bootloader spricht: halten Sie
JTAG als Rückfalloption bereit.

## 1. 🔌 Bringen Sie Ihren Adapter zum CAN-Sprechen
Was Sie davon brauchen, hängt von Ihrer Plattform und dem verwendeten
Transport ab:

**Linux, SocketCAN-Weg (empfohlen, wenn Ihr Adapter dies
unterstützt):**
Nichts am Adapter selbst zu flashen. Aktivieren Sie die Schnittstelle
einmal pro Start (oder fügen Sie sie zu Ihrer Netzwerkkonfiguration
hinzu, damit sie bestehen bleibt):
```
sudo modprobe can vcan gs_usb   # gs_usb deckt die meisten Platinen der CANable-Familie ab
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up
```
Wenn sich Ihr Adapter unter einem anderen Namen als `can0` anmeldet,
prüfen Sie `ip link show` (oder `dmesg` direkt nach dem Anschließen)
für den tatsächlichen Namen. Manche Adapter benötigen `slcand` statt
eines nativen Treibers - wenn `ip link show` nach dem Anschließen
überhaupt keine CAN-Schnittstelle zeigt, ist dies wahrscheinlich Ihr
Fall; siehe die Dokumentation Ihres Adapters für den `slcand`-Aufruf,
der eine `slcan0`-Schnittstelle erstellt, die Sie dann auf dieselbe
Weise wie oben aktivieren.

**Windows, oder Linux über den Seriell/SLCAN-Weg:**
Eine CANable Pro v2 wird standardmäßig mit **candleLight**-Firmware
ausgeliefert, die mit dem Host über das `gs_usb`-Protokoll spricht -
dasselbe, das der `gs_usb`-Treiber von SocketCAN unter Linux nativ
erwartet (siehe oben). Dieses Protokoll präsentiert sich **nicht** als
serieller Port, was dieser Weg benötigt. Um stattdessen Seriell/SLCAN zu
verwenden (unter Windows erforderlich; unter Linux optional):

1. Laden Sie SLCAN-kompatible Firmware für Ihren Adapter herunter
   (suchen Sie nach "canable slcan firmware" — es gibt einige gepflegte
   Forks; verwenden Sie den, auf den die Dokumentation Ihres eigenen
   Adapters verweist).
2. Versetzen Sie den Adapter in den DFU/Bootloader-Modus (normalerweise
   ein BOOT-Knopf, der beim Einschalten gehalten wird, oder ein
   Jumper - prüfen Sie die Dokumentation Ihres Adapters).
3. Flashen Sie die SLCAN-Firmware mit dem Flash-Tool des Herstellers
   Ihres Adapters oder `dfu-util`.
4. Wieder verbinden - es sollte sich nun als serieller Port anmelden:
   ein COM-Port unter Windows, oder im Stil von
   `/dev/ttyACM0`/`/dev/ttyUSB0` unter Linux.

Wenn Ihr Adapter bereits SLCAN-Firmware ausführt, springen Sie direkt zu
Schritt 2 unten.

Eine empfangene SLCAN-Zeile, deren tatsächliche Länge nicht mit dem
übereinstimmt, was ihr eigenes deklariertes DLC impliziert, wird als
fehlerhaft behandelt und übersprungen, statt anhand ihrer ersten N
Hex-Zeichen unabhängig davon analysiert zu werden, was folgt - gut zu
wissen, wenn Sie gegen einen verrauschten oder nicht-standardmäßigen
Adapter debuggen.

## 2. 💻 Installation und Ausführung
**Windows:**
```
python -m pip install -r requirements.txt
python urtc_flasher.py
```
Oder erstellen Sie eine eigenständige `.exe` mit `build_exe.bat` (siehe
diese Datei).

**Linux:**
```
python3 -m pip install -r requirements.txt
python3 urtc_flasher.py
```
Oder erstellen Sie ein eigenständiges Binary mit `./build_exe.sh`
(zuerst `chmod +x`).

Beide Skripte übergeben `--noconfirm` an PyInstaller, sodass ein
Neubau über einem bereits existierenden `dist/URTC_Flasher` dieses
direkt ersetzt, statt auf eine "ersetzen?"-Eingabeaufforderung zu
warten, die in der Ausgabe eines Skripts leicht übersehen wird.

Im Verbindungsbereich erscheint außerdem die animierte offizielle
HYDRA-UMC-Marke. Ihre gepflegte SVG-Quelle ist
`assets/HYDRA_UMC_ICON.svg`; zwölf mitgelieferte PNG-Einzelbilder erhalten
die Animation in Tkinter und im eigenständigen Programm ohne zusätzliche
grafische Laufzeitabhängigkeit. Das native URTC-Fenster-/Taskleisten-Symbol
bleibt bewusst statisch.

### Visuelles Steuerpult

Das gemeinsame **Qt-Quick**-Kommandopult steht für den echten CAN-OTA-Ablauf
bereit:
~~~
python urtc_flasher.py --qtquick
~~~
Es verwendet dieselben Produktions-Transporte, Validierungen und den
signierten Flash-Code wie die bewährte Oberfläche. Tkinter bleibt die
Standardschnittstelle, bis die erweiterten SWD/JTAG- und
Platineneinstellungsseiten Funktionsparität erreicht haben; verwenden Sie Qt
Quick noch nicht für diese erweiterten Vorgänge.

Der bewährte CAN-OTA- und SWD/JTAG-Ablauf bleibt erhalten und liegt nun auf
einer dunkelblau-cyanfarbenen Steueroberfläche: Produktkopf, kontrastreiche
Verbindungskarte, lesbare Firmware-Tabellen, dunkles Prüfprotokoll und
sichtbarer Fortschritt. Dies verbessert Darstellung und Zugänglichkeit, ohne
Bootloader-Protokoll oder Hardware-Sicherheitsverhalten zu verändern.

### Menüleiste

- **Datei** - Protokolle speichern (das Protokoll auf dem Bildschirm als
  Klartext; für ein vollständigeres Paket mit Systemdiagnose und der
  aktuell ausgewählten Firmware-Datei siehe stattdessen "Diagnose"
  weiter unten), und Beenden.
- **Sprache** - zwischen den 5 verfügbaren Sprachen wechseln (siehe
  "Sprache" weiter unten, wie Übersetzungen funktionieren).
- **Hilfe** - Readme (öffnet diese Datei in einem schreibgeschützten
  Betrachterfenster; übernimmt automatisch eine übersetzte Version,
  sobald eine für die aktuelle Sprache existiert), URTC GitHub (öffnet
  das Repository des Projekts in Ihrem Browser), Lizenz (die
  GPL-3.0-Lizenz dieses Tools, gelesen aus der eigenen `LICENSE`-Datei
  des Repositorys), und Über (Version und Autor).

**Beim Start** wird das Banner 5 Sekunden lang zentriert auf dem
Bildschirm angezeigt, bevor das Hauptfenster erscheint - es ist nicht
Teil des Hauptfensters selbst (deshalb ist das Fenster für alles, was es
tatsächlich tut, recht kompakt). Das Fenster-/Taskleisten-Symbol ist ein
kleines eigenständiges Design (`assets/urtc_icon.png`/`.ico`), nicht das
verkleinerte Banner - die vollständige Banner-Grafik hält sich bei
16-32px nicht gut.

**Sprache**: Englisch als Standard.
Wird über das Menü **Sprache** (in der Menüleiste oben im Fenster)
gewechselt statt über ein Dropdown im Hauptfenster - speichert sofort in
`urtc_config.json` (dieselbe Datei, die für die technischen
Hardware-Überschreibungen verwendet wird — die Spracheinstellung lebt
einfach neben diesen), angewendet beim nächsten Start. Übersetzungen
leben in reinen Textdateien unter `language/` (`english.lng`,
`spanish.lng`, `italian.lng`, `french.lng`, `german.lng`) als einfache
`SCHLÜSSEL=Wert`-Paare, eines pro Zeile - Zeilen, die mit `#` beginnen,
und leere Zeilen werden ignoriert, und ein wörtliches `\n` innerhalb
eines Werts wird zu einem echten Zeilenumbruch (verwendet von der
Handvoll mehrzeiliger Dialognachrichten). Direkt editierbar, wenn eine
Übersetzung korrigiert werden muss, oder als Ausgangspunkt für eine
andere Sprache (fügen Sie `language/<name>.lng` hinzu, fügen Sie
`("<name>", "Eigener Name")` zu `AVAILABLE_LANGUAGES` nahe dem Anfang
von `flasher_config.py` hinzu, und setzen Sie `"language": "<name>"` in
`urtc_config.json`). Ein fehlender Schlüssel aus einer Sprachdatei fällt
darauf zurück, den Namen dieses Schlüssels selbst anzuzeigen, statt
abzustürzen, und eine fehlende oder unlesbare Sprachdatei (fehlerhafte
Bearbeitung, falscher Dateiname) fällt für die gesamte Oberfläche auf
Englisch zurück - so oder so bleibt das Tool nutzbar, während die
Unstimmigkeit behoben wird.

Tkinter (das GUI-Toolkit) wird unter Windows mit Python ausgeliefert,
aber auf Distributionen der Debian/Ubuntu-Familie ist es ein separates
Betriebssystempaket:
```
sudo apt install python3-tk
```
(Fedora: `sudo dnf install python3-tkinter`. Arch: `sudo pacman -S
tk`.) `build_exe.sh` prüft dies selbst und teilt Ihnen mit, wenn es
fehlt, statt auf halbem Weg zu scheitern.

**Serielle Berechtigungen unter Linux:** wenn Sie den Seriell/SLCAN-Weg
verwenden und die Verbindung mit "Permission denied" fehlschlägt, muss
Ihr Benutzer in der Gruppe sein, die die seriellen Geräte besitzt
(`dialout` unter Debian/Ubuntu; variiert bei anderen Distributionen):
```
sudo usermod -a -G dialout $USER
```
Melden Sie sich ab und wieder an (die Gruppenmitgliedschaft wird beim
Login gelesen), dann versuchen Sie es erneut. Das Tool erkennt diesen
spezifischen Fehler und zeigt dieselbe Lösung in einem Dialog, aber es
lohnt sich, dies vorher zu wissen. SocketCAN hat dieses spezielle
Problem nicht — der Zugriff auf eine Schnittstelle vom Typ `can0` wird
nicht von der `dialout`-Gruppe kontrolliert — aber das Aktivieren der
Schnittstelle überhaupt (Schritt 1 oben) benötigt trotzdem `sudo`, da
dies eine Änderung der Netzwerkgerätekonfiguration ist.

Die Verwendung von `python -m pip`/`python3 -m pip` statt eines bloßen
`pip` umgeht ein häufiges Problem auf beiden Plattformen: das eigene
Wrapper-Skript von `pip` ist nicht immer im PATH, selbst direkt nach
einer erfolgreichen Installation, während `-m pip` das installierte
Modul direkt findet.

## 3. 📁 Wohin die Firmware-Dateien gehören
Dieses Tool erwartet einen `firmware/`-Ordner direkt neben
`urtc_flasher.py`, im Wurzelverzeichnis dieses Repositorys:

```
├── assets/
│   ├── URTC_LOGO_FLASHER.svg      <- Banner-Quelle (Vektor)
│   └── urtc_banner.png            <- oben im Fenster angezeigt, aus dem .svg oben gerendert
├── firmware/
│   ├── URTC_V1.1_F303CC.bin      <- neue .bin-Dateien hier ablegen
│   └── URTC_SLAVE_APP.bin        <- Anwendung des Erweiterungs-Slave-Chips, falls zutreffend
├── logs/                          <- automatisch erstellt, eine Datei pro Sitzung
├── urtc_config.json               <- optional, nicht standardmaessig enthalten (siehe "Den HMAC-Schluessel aendern" unten)
├── urtc_flasher.py                <- Einstiegspunkt: CLI-Argumente, Splash-Screen, Hauptfenster-Einrichtung
├── flasher_config.py              <- Konfigurationsdatei-E/A, Sprachladen, Protokollkonstanten
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- STM32CubeProgrammer / pyOCD Wrapper
├── flasher_validation.py          <- Firmware-Dateivalidierung (.bin/.hex/.elf)
├── flasher_protocol.py            <- die CAN-OTA-Zustandsmaschine selbst, sowohl für die Hauptplatine als auch (über deren eigene I2C-Bridge weitergeleitet) den Erweiterungs-Slave
├── flasher_github.py               <- lädt Firmware aus dem eigenen GitHub-Repository dieses Projekts herunter
├── flasher_gui.py                 <- das Hauptfenster (FlasherGUI) und seine Menuleiste
├── requirements.txt
├── build_exe.bat                  <- eigenstandiger Build fuer Windows
├── build_exe.sh                   <- eigenstandiger Build fuer Linux
└── README.md
```

Dieses Tool ist aus Gründen der Lesbarkeit in die obigen Module nach
Zuständigkeit organisiert - es gibt keinen funktionalen Unterschied
zwischen separaten Dateien und einer großen Datei, und es gibt keine
monolithische Form, die synchron gehalten werden muss, wie es bei der
Firmware der Fall ist (dies ist ein PC-Tool, nichts, das auf die
Platine geflasht wird, also gibt es immer nur diese eine Form).

`assets/urtc_banner.png` ist optional - wenn sie fehlt, startet das
Tool einfach ohne Banner, statt zu scheitern. Sie wird über die native
PNG-Unterstützung von tkinter geladen (Tk 8.6+, das jede aktuelle
Python-Version mitbringt), nicht Pillow, sodass keine neue Abhängigkeit
hinzugefügt wird. Sowohl `build_exe.bat` als auch `build_exe.sh`
bündeln `assets/` bereits über PyInstallers `--add-data` in das
eigenständige Executable, sodass dies auf dieselbe Weise funktioniert,
egal ob Sie aus dem Quellcode oder aus einem erstellten Binary
ausführen.

Dies ist beabsichtigt: das gesamte Repository ist in sich geschlossen.
Wenn Sie nur eine Platine flashen wollen — auf einem Werkstatt-PC, von
einem USB-Stick, wo auch immer — können Sie dieses Repository allein
kopieren, und es funktioniert trotzdem.

**Sie können mehr als eine `.bin` dort haben.** Jede
Anwendungs-Firmware-Datei wird geprüft und aufgelistet - das Tool
greift nicht einfach nach der ersten, die es findet, und
Bootloader-Binärdateien (alles mit "BOOTLOADER" im Dateinamen -
`URTC_BOOTLOADER.bin`, `URTC_SLAVE_BOOTLOADER.bin`) werden vollständig
aus dieser Liste herausgefiltert, da CAN-OTA immer nur
Anwendungs-Firmware flasht; eine Bootloader-Aktualisierung benötigt
stattdessen SWD/JTAG (Abschnitt 6 unten). Beim Start (und jedes Mal,
wenn Sie auf **Aktualisieren** klicken) wird jede verbleibende `.bin`
in `firmware/` gegen denselben Plausibilitätstest geprüft, den der
Bootloader selbst auf ein frisches Image anwendet (ihre ersten 4 Bytes
müssen wie ein echter anfänglicher Stack-Pointer für den RAM dieses
Chips aussehen, und ihre Größe muss in den Hauptslot passen). Jede
Datei erscheint in der Liste mit einem klaren ✓ oder ✗ und dem
Grund:

| Datei | Größe | Status |
|---|---|---|
| URTC_V1.1_F303CC.bin | 30.9 KB | ✓ sieht gültig aus |
| URTC_SLAVE_APP.bin | 12.4 KB | ✓ sieht gültig aus |
| notes.txt.bin | 0.1 KB | ✗ erstes Wort sieht nicht wie ein gültiger Stack-Pointer aus |

- **Genau eine Datei besteht die Prüfung** → sie wird in dem Moment für
  Sie ausgewählt, in dem das Tool startet. Eine ungültige Datei allein
  im Ordner wird *nicht* automatisch ausgewählt, nur weil nichts anderes
  mit ihr konkurriert.
- **Mehr als eine gültige Datei** → nichts wird automatisch ausgewählt;
  wählen Sie die gewünschte aus der Liste.
- **Sie wählen trotzdem eine ungültig aussehende Datei** → das Tool
  bittet Sie zuerst um Bestätigung. Diese Prüfung existiert, um
  offensichtliche Fehler abzufangen (falsche Datei, abgebrochener
  Download, ein leerer Platzhalter) - sie kann nicht alles abfangen
  (eine beschädigte, aber plausible Datei, oder eine mit dem falschen
  Schlüssel signierte), wofür die eigene CRC32/HMAC-Prüfung des
  Bootloaders während der eigentlichen Übertragung da ist.
- **Nichts gefunden, oder Sie wollen eine Datei von ganz woanders** →
  verwenden Sie die Schaltfläche **Durchsuchen .bin...**, die unabhängig
  davon funktioniert, wo die Datei tatsächlich liegt (und in beiden
  Fällen dieselbe Validierungsprüfung ausführt).
- **Sie wollen den neuesten Build, ohne ihn selbst suchen zu müssen** →
  **Von GitHub herunterladen...** ruft die aktuelle Dateiliste direkt
  aus dem eigenen `firmware/`-Ordner dieses Projekts ab
  (`github.com/JuanenRac/URTC/tree/main/firmware`) und lässt Sie eine
  Datei zum direkten Herunterladen in Ihren eigenen lokalen
  `firmware/`-Ordner auswählen - sie erscheint dann in der obigen Liste
  wie jede andere Datei, kein Neustart nötig. Verwendet die eigene
  öffentliche API von GitHub (nicht authentifiziert, daher dem eigenen
  Ratenlimit von GitHub von 60 Anfragen/Stunde unterworfen, falls Sie
  es viel in kurzer Zeit nutzen) - nichts hier benötigt ein
  GitHub-Konto oder ein Token.

**Optionale `<dateiname>.manifest.json`, neben einer Firmware-Datei**
(z. B. `URTC_V1.1_F303CC.bin.manifest.json`), fügt eine zusätzliche,
nicht blockierende Plausibilitätsprüfung hinzu: falls vorhanden, wird
ihr `sha256`-Feld direkt vor dem Flashen mit der tatsächlichen Datei
verglichen, wobei `version`/`build_date` zur Referenz daneben protokolliert
werden.

```json
{"version": "1.1", "build_date": "2026-07-23", "sha256": "e5a4918c..."}
```

Eine Abweichung wird als klare Warnung protokolliert, kein harter
Stopp - dies ist eine Komfortprüfung, um früh eine offensichtlich
falsche oder beschädigte Datei abzufangen, kein Ersatz für die eigene
HMAC-Verifizierung des Bootloaders während der eigentlichen
Übertragung, die so oder so die maßgebliche Prüfung bleibt.

Später einen neuen Build hinzufügen: einfach in `firmware/` ablegen und
auf **Aktualisieren** klicken - kein Neustart nötig.

## 4. 🔍 Prüfen, was aktuell installiert ist
Wenn Sie unter Linux sind und SocketCAN verfügbar ist, sehen Sie oben
eine **Transport**-Auswahl - wählen Sie Seriell/SLCAN oder SocketCAN
vor dem Verbinden. Unter Windows erscheint diese Zeile überhaupt
nicht; Seriell/SLCAN ist die einzige Option.

Klicken Sie auf **Verbinden**, und das Tool fragt die Platine
automatisch, was sie aktuell ausführt (CAN-ID `0x7F8` → `0x7F9` - siehe
`docs/CANBUS.TXT`). Dies funktioniert, egal ob die Platine ihre
Anwendung normal ausführt *oder* im Bootloader sitzt, sodass Sie
keinen Reset auslösen müssen, nur um es herauszufinden. Klicken Sie
jederzeit danach auf **Abfragen**, um erneut zu prüfen (nützlich direkt
nach Abschluss eines Flashs, um zu bestätigen, dass die neue Version
tatsächlich übernommen wurde).

**Wenn der Bootloader selbst antwortet** (Platine sitzt im Bootloader,
führt ihre Anwendung nicht aus), meldet er auch seine eigene Version -
etwas Getrenntes von der Version der installierten Anwendung, verfolgt
über ihre eigene `BOOTLOADER_VERSION_MAJOR/MINOR/PATCH` in
`bootloader_common.h` und als zweiter Frame (`0x7FA`) direkt neben `0x7F9`
gesendet. Die laufende Anwendung sendet dies nie - sie hat keine
Möglichkeit, die Version eines aktuell geflashten Bootloaders zu
kennen, außer den Bootloader selbst zu fragen, sodass dies nur
auftaucht, wenn die Platine tatsächlich dort sitzt (direkt nach `0x7F0`,
oder bei einem frischen Start, bevor sie zur Anwendung springt).

Was Sie sehen werden:

- **`v1.1 (application, HardwareID 0x0303CC01)`** - normaler Fall,
  Anwendung läuft, alles stimmt überein.
- **`Bootloader running, no valid firmware currently installed,
  bootloader v1.1.2`** - die Platine steckt im Bootloader fest, ohne
  etwas, zu dem sie springen könnte (leerer Chip, oder jede Prüfung
  auf dem Hauptslot schlug fehl). Dies ist genau die Situation, für die
  dieses Tool existiert - flashen Sie sie. Die hier gezeigte
  Bootloader-Version ist die des Bootloaders selbst, ohne Bezug zu
  irgendeiner Anwendungsversion, die ihre Prüfungen nicht bestanden
  hat.
- **`⚠ HardwareID mismatch!`** in Rot angezeigt - etwas hat geantwortet,
  aber seine HardwareID stimmt nicht mit dem überein, was dieses Tool
  erwartet. Flashen Sie nicht, ohne vorher zu verstehen, warum; der
  Bootloader würde das Update sowieso ablehnen, aber eine Abweichung
  hier kann auch bedeuten, dass Sie komplett auf die falsche Platine
  zielen.
- **Keine Antwort** (Rot) - Platine reagiert nicht, falsche Bitrate,
  oder nicht tatsächlich verbunden. Prüfen Sie die physische
  Verbindung und, im SocketCAN-Weg, dass die Schnittstelle tatsächlich
  aktiv ist (`ip link show`).

**Erweiterungsplatine:** ein separates Dropdown und ein
Abfragen/Speichern-Paar, direkt unter der Versionsprüfung. Liest und
setzt, welche der 7 möglichen `CONN_EXPANSION`-Konfigurationen (keine,
oder eine der 6 echten Varianten - siehe `EXPANSION.TXT`) physisch
installiert ist, über CAN (`0x1A0`/`0x1A1`). Es gibt keine elektrische
Möglichkeit für die Platine, dies selbst zu erkennen, also muss es ihr
gesagt werden - dies lebt hier (nicht nur in `URTC Tester`), da es sich
um einen einmaligen Hardware-Konfigurationsschritt handelt, der am
natürlichsten zusammen mit einem Firmware-Update erfolgt. **Speichern**
fragt zuerst nach Bestätigung, da dies über Stromzyklen hinweg
bestehen bleibt, bis es explizit erneut geändert wird.

**MLX9064x-Sensorvariante:** gleiche Form wie die obige
Erweiterungsplatinen-Kontrolle - ein Dropdown und ein
Abfragen/Speichern-Paar, das liest/setzt, welcher der 3 Wärmesensoren
der MLX9064x-Familie (oder keiner) tatsächlich installiert ist, über
CAN (`0x1A6`/`0x1A7` - siehe `CANBUS.TXT`). Nur relevant, wenn die
obige Erweiterungsplatine als Advanced-Variante oder Basic+MLX9064x
konfiguriert ist; die eigene Firmware der Platine ignoriert diese
Einstellung bei jedem anderen Erweiterungsplatinentyp vollständig.
„Keiner installiert" (der sichere Standardwert) fällt absichtlich
nicht auf die Annahme MLX90640 zurück - eine Platine mit einem echten
angeschlossenen MLX90640 benötigt, dass dies explizit einmal gesetzt
wird, genauso wie es der Erweiterungsplatinentyp selbst bereits
erfordert.

## 5. ⚡ Flashen
1. **Verbinden**: wählen Sie Seriell/SLCAN oder SocketCAN (nur Linux),
   dann den Port/die Schnittstelle, dann klicken Sie auf Verbinden. Für
   Seriell/SLCAN öffnet dies den CAN-Kanal mit 500 kbit/s (URTCs feste
   Bus-Geschwindigkeit); für SocketCAN wird erwartet, dass die
   Schnittstelle bereits mit dieser Bitrate läuft (Schritt 1 oben) -
   dieses Tool stellt sie nicht ein. So oder so wird die aktuelle
   Version automatisch abgefragt - siehe Abschnitt 4 oben.
2. **Wählen Sie ein Flash-Ziel**: "Diese Platine (Haupt)" oder
   "Erweiterungs-Slave" - Standard ist die Hauptplatine, der mit
   Abstand häufigere Fall. Die Slave-Option erreicht nur etwas auf
   einer Advanced-Erweiterungsplatinen-Variante
   (TMC2209+STM32F303CBT6 oder TMC5160A+STM32F303CBT6) - das Update
   wird über die eigene I2C-Bridge der Hauptplatine zum Slave-Chip
   weitergeleitet (die eigenen `0x210`-`0x218` von `CANBUS.TXT`), keine
   separate physische Verbindung. „F-RAM vor dem Flashen löschen"
   (Schritt 4 unten) deaktiviert sich automatisch bei Auswahl von
   Slave - der Slave-Chip hat kein eigenes F-RAM zum Löschen.
3. **Firmware auswählen**: wählen Sie aus der erkannten Liste, oder
   Durchsuchen - siehe Abschnitt 3 oben, um genau zu erfahren, wie
   Erkennung und Validierung funktionieren.
4. **Flashen**:
   - Lassen Sie "Platine führt aktuell die Anwendung aus" markiert,
     wenn die Platine eingeschaltet ist und normal läuft - das Tool
     sendet zuerst den magischen Payload-Auslöser `0x7F0` (oder
     `0x210`, an den Slave weitergeleitet, falls Slave das gewählte
     Ziel ist), der jeden
     Aktuator sicher herunterfährt, bevor es in den Bootloader
     zurücksetzt.
   - Deaktivieren Sie es, wenn die Platine bereits im Bootloader
     sitzt (direkt nach einem frischen JTAG-Flash, oder wenn die
     Versionsprüfung oben "no valid firmware currently installed"
     zeigte).
   - Klicken Sie auf **Firmware Flashen** und bestätigen Sie - der
     Bestätigungsdialog nennt, welches Ziel Sie im Begriff sind zu
     flashen, also prüfen Sie, ob dies mit dem übereinstimmt, was Sie
     tatsächlich auswählen wollten. Das Protokoll zeigt jeden Schritt
     des Protokolls; der Fortschrittsbalken
     verfolgt den Schreibfortschritt Seite für Seite während der
     Übertragung, dann den Kopierfortschritt während der abschließenden
     Backup-zu-Haupt-Kopie.

Wenn die Verifizierung an irgendeinem Punkt fehlschlägt (CRC32-, HMAC-,
oder HardwareID-Abweichung), wird der Hauptslot des Bootloaders nie
berührt - die Platine führt weiterhin die Firmware aus, die sie bereits
hatte. Es ist immer sicher, es einfach erneut zu versuchen.

**Firmware sichern (CAN)**: liest die aktuell installierte Firmware über
den Bus zurück, unverändert, und speichert sie als `.bin`-Datei - das
CAN-Äquivalent der eigenen SWD-Funktion „back up entire flash before
erasing" (Abschnitt 6 unten), aus demselben Grund. Lohnt sich vor jedem
Update, besonders vor einem absichtlichen Downgrade (unten), da dies die
einzige Möglichkeit ist, die heutigen exakten Bytes später
zurückzuerhalten, falls Sie die Datei, aus der sie stammen, nicht mehr
besitzen. Nur Hauptplatine, und nur während die Platine sich tatsächlich
im Bootloader befindet - erfordert einen Bootloader, der `0x7FE`/`0x7FF`
implementiert (siehe `docs/CANBUS.TXT`); ein älterer antwortet einfach
nie, was als klare Zeitüberschreitung angezeigt wird statt als
stillschweigend leere Datei.

**Absichtliches Installieren einer älteren Version**: der Bootloader
lehnt normalerweise ein gültig signiertes Image ab, wenn es eine ältere
Version deklariert als die bereits installierte (Verifizierungsfehler-
Grund „Rollback abgelehnt") - dies verhindert, dass eine Version mit
einer bereits entdeckten Schwachstelle erneut installiert wird. Wenn Sie
wirklich zu einer älteren, vertrauenswürdigen Version zurückkehren
müssen, aktivieren Sie **„Downgrade erlauben (Anti-Rollback umgehen) für
dieses Update"** (nur Hauptplatine) vor dem Flashen - es erscheint ein
zweiter Bestätigungsdialog, da dies absichtlich eine Sicherheitsprüfung
umgeht. Dies lädt weiterhin das komplette ältere Image über die normale
Übertragung hoch, es hebt nur die Versionsreihenfolge-Prüfung für diesen
einen Versuch auf (`0x7FD` - siehe `docs/CANBUS.TXT`); die der Platine
gemeldete Versionsnummer stammt aus der eigenen `.manifest.json` der
Datei, falls neben ihr eine vorhanden ist (siehe Abschnitt 3 oben),
andernfalls aus der aktuell konfigurierten Version dieses Tools, in
beiden Fällen klar protokolliert, sodass es nie eine stille Vermutung
ist.

## 6. 🛠️ Den kompletten Chip via SWD/JTAG programmieren (fortgeschritten)
Der Abschnitt "4. Program complete chip via SWD/JTAG" im Tool führt
einen vollständigen Inbetriebnahme-Flash durch - löscht den gesamten
Chip komplett, schreibt dann sowohl das Bootloader-Image als auch das
Anwendungs-Image neu, an den echten Adressen des Chips, der der
**Ziel-Chip**-Auswahl entspricht (siehe unten). Dies
ist eine **andere Art von Operation** als die Abschnitte 1-5 oben:

|  | CAN-OTA-Update (Abschnitte 1-5) | Vollständiges SWD/JTAG-Chip (Abschnitt 6) |
|---|---|---|
| Selbstheilend bei Unterbrechung | Ja - der Golden-Image-Backup-Slot garantiert, dass die laufende Firmware überlebt | Nein - führt nichts aus, bis neu programmiert |
| Wiederherstellbar | Automatisch, keine Aktion nötig | Ja - einfach wieder verbinden und erneut über SWD flashen; der Debug-Port hängt nicht vom Flash-Inhalt ab. Nur eine echte permanente Sperre (Option-Byte RDP2) würde dies verhindern, und nichts in diesem Tool setzt Option-Bytes |
| Berührt den Bootloader | Nie | Ja, per Design |
| Benötigt | Einen USB-CAN-Adapter | Eine SWD/JTAG-Sonde (ST-Link oder ähnlich) |
| Typische Verwendung | Routinemäßige Firmware-Updates | Erste Inbetriebnahme auf einem leeren Chip, oder Wiederherstellung einer unbrauchbaren Platine |

**Ziel-Chip:** "Diese Platine (Haupt)" oder "Erweiterungs-Slave" -
gleiche 2 Optionen wie die eigene Auswahl im CAN-OTA-Tab, aber eine
hier wirklich separate Wahl: SWD/JTAG benötigt eine Sonde, die
physisch mit dem Chip verbunden ist, der dieser Auswahl entspricht, da
es keine Bridge gibt (im Gegensatz zu CAN-OTA), die es einer einzigen
Verbindung erlaubt, beide zu erreichen. Das Umschalten hierbei ändert
automatisch die verwendeten Flash-Adressen:

| | Hauptplatine (STM32F303CC) | Erweiterungs-Slave (STM32F303CBT6) |
|---|---|---|
| Bootloader-Adresse | `0x08000000` (32K-Region) | `0x08000000` (18K-Region) |
| Anwendungs-Adresse | `0x08008000` (112K-Region) | `0x08005000` (54K-Region) |
| pyOCD-Ziel-String | `stm32f303cc` | `stm32f303cb` |

Beide obigen Ziel-Strings sind die beste Vermutung dieses Projekts für
den echten pyOCD-Zielnamen jedes Chips, nicht gegen eine echte
pyOCD-Installation bestätigt, während dies geschrieben wurde (die
STM32-Abdeckung in pyOCD läuft größtenteils über CMSIS-Packs statt
über integrierte Ziele) - wenn das Flashen mit einem Fehler wie "target
not found" fehlschlägt, führen Sie selbst `pyocd list --targets --name
stm32f303` aus, und `pyocd pack install <der echte Name>` lädt das
richtige CMSIS-Pack herunter.

**Benötigt eines von** (das Tool erkennt automatisch, was verfügbar
ist, und aktiviert nur das Gefundene):
- **pyOCD** - `pip install pyocd`. Frei, Open Source, keine separate
  Installation über das pip-Paket hinaus.
- **STM32CubeProgrammer** - das offizielle Tool von ST, separat von
  [st.com](https://www.st.com) installiert. Wenn Sie es bereits für
  andere STM32-Arbeiten haben, ist hier keine zusätzliche Installation
  nötig.

Beide werden als Kommandozeilen-Subprozesse gesteuert, nicht als
Python-Bibliotheken importiert - Sie sehen den genauen Befehl
protokolliert, bevor er ausgeführt wird.

**Dateiformate:** `.bin` (benötigt die feste Adresse, die dieses Tool
bereits kennt - Sie geben sie nicht ein) oder `.hex` (trägt seine
eigene Adresse, wird unverändert verwendet). Mischen ist in Ordnung -
Bootloader als `.hex` und Anwendung als `.bin`, oder umgekehrt, beides
funktioniert. Beide Dateiauswähler validieren die ausgewählte Datei
(plausible Größe für den Ziel-Slot, und - wo das Format eine
zuverlässige Prüfung erlaubt - ein plausibler anfänglicher
Stack-Pointer), bevor Sie fortfahren dürfen, genau wie es der
Firmware-Auswähler des CAN-Wegs bereits tat.

**Die Verbindung wird geprüft, bevor irgendetwas Destruktives
ausgeführt wird**, wobei **positive Beweise** für eine echte
Sonde/ein echtes Ziel erforderlich sind statt nur des Fehlens eines
Fehlers - der eigene Exit-Code von STM32CubeProgrammer ist allein kein
zuverlässiges Erfolgs-/Fehlersignal, daher läuft eine dedizierte
Verbindungsprüfung (`pyocd list --probes`, oder ein reines
Verbindungs-`-c port=SWD` für STM32CubeProgrammer), bevor der
Massenlösch-Schritt jemals läuft. Die Ausgabe jedes nachfolgenden
Befehls wird auch als zweite Schicht auf bekannten Fehlertext
durchsucht, falls der Exit-Code eines Tools allein in irgendeiner
anderen Situation ebenfalls nicht vertrauenswürdig wäre.

**Der Testlauf ist standardmäßig aktiviert.** Lassen Sie ihn beim
ersten Mal markiert und drücken Sie "Flash Complete Chip" - er druckt
die genauen Befehle ins Protokoll, ohne die Platine zu berühren. Lesen
Sie sie durch, bestätigen Sie, dass Pfade und Adressen richtig
aussehen, *dann* deaktivieren Sie den Testlauf und tun es wirklich.

**"Back up entire flash before erasing"** liest zuerst die gesamte
256KB-Flash-Region in eine `.bin`-Datei, über den eigenen
Speicher-Lesen-in-Datei-Befehl desselben Tools (`-r` für
STM32CubeProgrammer, `commander savemem` für pyOCD) - eine echte
Versicherung hier, denn anders als ein CAN-OTA-Update (das der
Golden-Image-Backup-Slot bereits schützt), hat ein vollständiges
Chip-Löschen kein anderes Rückgängigmachen. Standardmäßig
deaktiviert, da es 10-30s hinzufügt und auf einem
neuen/leeren Chip nicht nötig ist; lohnt sich zu markieren, bevor eine
Platine überschrieben wird, die bereits etwas ausführt. Wenn das Lesen
tatsächlich keine Datei erzeugt, wird das Löschen verweigert, statt
ohne das angeforderte Backup fortzufahren.

**Teststatus:** die obige Verbindungsprüfungslogik wurde gegen echte
STM32CubeProgrammer-Ausgabe verifiziert (sowohl ein echtes
Erfolgsverbindungs-Log als auch ein dokumentierter "No target
connected"-Fehler, beide aus dem eigenen Community-Forum von ST
stammend) und gegen das genaue Falsch-Erfolg-Szenario, das ein echter
Benutzer erlebt hat. Die vollständige
Lösch-/Programmier-/Verifizierungssequenz gegen einen echten ST-Link
und einen echten STM32F303CC wurde noch nicht end-to-end durchgeführt -
die Umgebung, die dies geschrieben hat, hat keinen USB-Zugriff.
Behandeln Sie einen ersten echten vollständigen Versuch mit
angemessener Vorsicht - zuerst eine Ersatz-/Testplatine, falls Sie eine
haben, und behalten Sie einen Rückfallplan (das eigene Flash-Tool von
STM32CubeIDE, oder `st-flash`) im Hinterkopf, falls etwas an Ihrer
spezifischen pyOCD-Version oder Sonde nicht dem entspricht, was hier
angenommen wird.

## 7. ⌨️ CLI-Modus (headless, keine GUI)
Für CI-Pipelines, Testbänke, oder Produktionslinien-Skripting, wo es
keinen Bildschirm gibt:

```
python3 urtc_flasher.py --cli --port /dev/ttyACM0 --file firmware.bin
```

```
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan}] --port PORT
                             --file FILE [--no-trigger] [--force]
```

Exit-Codes: `0` Erfolg, `1` Protokoll-/Verbindungsfehler, `2` falsche
Argumente oder eine Firmware-Datei, die die Validierung nicht besteht
(übergeben Sie `--force`, um sie trotzdem zu flashen), `130` mit Strg+C
abgebrochen. Deckt nur den CAN-OTA-Update-Weg ab (Abschnitte 1-3) - der
vollständige SWD/JTAG-Chip-Weg ist vorerst absichtlich nur-GUI, angesichts
dessen, wie viel mehr auf dem Spiel steht, wenn ein skriptgesteuerter
Lauf eine falsche Datei-/Ziel-Kombination erwischt, ohne dass jemand
zusieht.

**`--transport mock`** führt die gesamte Update-Sequenz gegen einen
simulierten, speicherinternen Bootloader aus statt gegen eine echte
Platine - kein Adapter, kein Port, nichts Physisches beteiligt:

```
python3 urtc_flasher.py --cli --transport mock --file firmware.bin --no-trigger
```

Nützlich, um die eigene Logik dieses Tools zu testen (Wiederholungsverhalten,
Timeout-Handling, Exit-Codes) in einer CI-Pipeline oder bevor echte
Hardware berührt wird - nichts, das mit einer echten Platine spricht.
`--mock-fail 0x03` (oder jeder andere `VERIFY_FAIL_REASON_*`-Wert aus
`docs/CANBUS.TXT`) lässt das simulierte Update die Verifizierung
fehlschlagen statt erfolgreich zu sein, um den Fehlerpfad auf dieselbe
Weise zu testen.

## 8. 🔄 Zuverlässigkeit während eines CAN-Updates, und Sitzungsprotokolle
Wenn das ACK einer Seite nicht innerhalb des normalen 3s-Fensters
während eines CAN-Updates ankommt, wiederholt das Tool das *Warten*
(nicht ein erneutes Senden der Seitendaten) bis zu zweimal mehr mit
einer kurzen zunehmenden Verzögerung, bevor es aufgibt, und erholt sich
so von einem verzögerten oder verlorenen ACK auf einem verrauschten
Bus, ohne dass die zugrunde liegenden Daten verloren gehen. Es sendet
absichtlich keine Seitendaten bei einem Timeout erneut - wenn die
ursprünglichen Daten tatsächlich gut angekommen sind und nur das ACK
verloren ging, würde ein erneutes Senden den Bootloader diese Bytes als
Anfang der *nächsten* Seite lesen lassen und die Übertragung
desynchronisieren. Jeder erneute Versuch prüft auch den eigenen
Heartbeat des Bootloaders (ungefähr einmal pro Sekunde gesendet) gegen
das, was der vollständige Empfang der aktuellen Seite implizieren
würde - wenn sie übereinstimmen, sagt das Protokoll dies, was ein
echter Beweis dafür ist, dass die Daten durchgekommen sind und nur das
ACK verloren ging, nicht nur ein längeres Warten und eine Hoffnung.

Jede Sitzung schreibt auch eine zeitgestempelte Protokolldatei nach
`logs/` (`urtc_flasher_YYYYMMDD_HHMMSS.log`),
unabhängig vom Bildschirmprotokoll - nützlich, um eine vollständige
Spur an denjenigen weiterzugeben, der die Firmware geschrieben hat,
falls im Feld etwas schiefgeht. Dieser Ordner wird automatisch erstellt
und ist sicher zu löschen; nichts liest alte Protokolle zurück.

## 9. 📊 Diagnose — Busaktivität, Bitrate, und Debug-Pakete
**Bitrate-Auswahl + Auto-Erkennung** (nur Seriell/SLCAN): der Bus von
URTC ist fest auf 500 kbit/s, was der Standard bleibt - dies ist für
einen falsch konfigurierten Adapter oder zur Fehlersuche bei einer
nicht standardmäßigen Platine gedacht. **Auto-Erkennung** probiert jede
Standard-SLCAN-Bitrate der Reihe nach gegen eine Versionsabfrage und
stoppt bei der ersten, die eine echte Antwort erhält; noch nicht
verbunden, wenn Sie darauf klicken. Die Bitrate von SocketCAN wird auf
Betriebssystemebene festgelegt (`ip link`), daher ist dieses Steuerelement
für diesen Transport deaktiviert - es gibt hier nichts zu versuchen.

**Busaktivität** ("Prüfen (2s)", neben Abfragen): zählt echte
Protokoll-Frames, die tatsächlich während eines festen 2-Sekunden-Fensters
auf dem verbundenen Transport gesehen wurden. Dies ist absichtlich
**nicht** dasselbe wie ein echter CAN-Bus-Auslastungsprozentsatz - das
würde eine Netlink-Abfrage (SocketCAN) oder adapterspezifische
Erweiterungen (SLCAN) benötigen, die dieses Tool nicht auf
standardmäßige, abhängigkeitsfreie Weise für den Controller des
*eigenen Adapters* erhalten kann. Was es gibt: ein echtes, direkt gemessenes Signal
für "spricht etwas auf diesem Bus, und ungefähr wie oft", auf beiden
Transporten. Speziell für SocketCAN zeigt es auch das 2-Sekunden-Delta
der eigenen Schnittstellenstatistiken von Linux
(`/sys/class/net/<iface>/statistics/`) - grundlegende
rx/tx/error/drop-Zähler, die jede Schnittstelle bereitstellt, als
einfache Dateien gelesen, keine zusätzliche Abhängigkeit. Das Verbinden
über SocketCAN liest auch `/sys/class/net/<iface>/carrier` - eine
einfache 0/1-Datei, die jede Linux-Schnittstelle bereitstellt. Wenn ein
CAN-Controller in Bus-Off geht, ruft der Kernel-Treiber
`netif_carrier_off()` auf, daher ist "kein Träger" hier ein echter
Beweis für ein Bus-Off oder eine ähnlich tote Verbindung, als Warnung
mit dem genauen Wiederherstellungsbefehl protokolliert (`sudo ip link
set <iface> down && sudo ip link set <iface> up type can bitrate
500000 restart-ms 100`). Dieses Tool führt diesen Befehl nicht selbst
aus - ein echtes Bus-Off zu bereinigen erfordert, die Schnittstelle auf
Kernel-Ebene herunter- und wieder hochzufahren, was Root erfordert und
als Änderung der Systemnetzwerkkonfiguration zählt, nichts, das
stillschweigend in Ihrem Namen getan werden sollte.

**Fehlerzähler (TEC/REC)** (neben Busaktivität): im Gegensatz zu den
Adapter-Zählern oben fragt dies **die Platine selbst** nach ihrem
eigenen Transmit/Receive Error Counter des CAN-Controllers
(`0x7FB`/`0x7FC` - siehe `docs/CANBUS.TXT`), beantwortet von dem, was
gerade läuft, Anwendung oder Bootloader. Grün bedeutet, beide Zähler
stehen auf 0 (error-active, gesund); orange bedeutet, einer oder beide
sind ungleich null, aber unter 128 (immer noch error-active, aber etwas
verursacht Neuübertragungen); rot bedeutet 128 oder mehr (error-passive
oder schlimmer) oder gar keine Antwort (ältere Firmware/älterer
Bootloader, der `0x7FB` noch nicht implementiert, oder Platine nicht
verbunden). Ein stetig steigender TEC bei flachem REC deutet
typischerweise darauf hin, dass die eigenen Übertragungen dieser
Platine unbestätigt bleiben - kein anderer Knoten am Bus, oder ein
Verkabelungs-/Terminierungs-/Bitrate-Problem speziell bei der
Verbindung dieser Platine.

**Debug-Paket exportieren** (über dem Protokoll): speichert eine
`.zip`-Datei mit dem aktuellen Bildschirmprotokoll, grundlegender
Systemdiagnose (Betriebssystem, Python-Version, welche Tools gefunden
wurden, aktueller Transport/Port/Bitrate), und der aktuell ausgewählten
CAN-Firmware-Datei - nützlich, um ein vollständiges Bild an denjenigen
weiterzugeben, der die Firmware geschrieben hat, falls im Feld etwas
schiefgeht, statt das Protokoll
von Hand zu kopieren.

## 10. 🔬 SWD/JTAG — Dateiformate, Slot-Verifizierung, und Sondenauswahl
**Dateiformate**: die Bootloader-/Anwendungsauswähler des
SWD-Abschnitts akzeptieren `.bin`, `.hex`, und `.elf`/`.axf`. ELF/AXF
wird mit einer kleinen Menge handgeschriebenen
Struct-Unpackings analysiert (nur ELF-Header + Programm-Header - keine
Symbole, keine Section-Header), absichtlich ohne `pyelftools` zu
verwenden: dieses Projekt bleibt bei null Abhängigkeiten außerhalb der
Standardbibliothek, und vollständiges ELF-Parsing ist mehr, als diese
spezifische Plausibilitätsprüfung benötigt. Verifiziert gegen die
eigenen kompilierten `BOOTLOADER.elf`/`APP.elf` dieses Projekts - beide
validieren korrekt an ihren echten Ladeadressen
(`0x08000000`/`0x08008000`), nicht nur an synthetischen Testdateien.
Nur 32-Bit-ARM-Little-Endian, was alles ist, was ein Cortex-M-Ziel
jemals ist. Die deklarierte Größe einer `.hex`-Datei ist die
tatsächliche belegte Byteanzahl, nicht die Adressspanne von ihrem
niedrigsten bis höchsten Record - daher validiert eine spärliche Datei
(ein kleiner Block echter Firmware plus ein entfernter, separater
Block von Option-Bytes oder Kalibrierungsdaten, den manche
STM32-Toolchains in einen Export bündeln) anhand ihres tatsächlichen
Inhalts statt der Lücke dazwischen. Ein rohes Firmware-Image unter
einer anderen Erweiterung als `.bin` (`.img`, `.rom`, oder gar keine
Erweiterung - wählbar über die "Alle Dateien"-Option des
Dateiauswählers) erhält seine Basisadresse davon, in welchen Slot Sie
es laden, genauso wie es eine `.bin` täte.

**Bootloader-/Anwendungs-Slot-Verifizierung**: die Dateiauswähler
verifizieren, dass jedes Image für den Slot bestimmt ist, in den es
gesetzt wird, nicht nur, dass es wie *irgendeine* Art gültiger Firmware
aussieht. Ein Bootloader-Image und ein Anwendungs-Image haben einen
gleich plausiblen Stack-Pointer - gleicher Chip, gleicher RAM - daher
kann diese Prüfung allein sie nicht unterscheiden, wenn eines im Slot
des anderen landet. Was es kann: der **Reset-Handler** eines gelinkten
Images ist eine echte, absolute Adresse, die zur Linkzeit fest
eingebettet wird, und zeigt immer nur in die Region, für die es
tatsächlich gelinkt wurde. Verifiziert gegen die eigenen echten
kompilierten `BOOTLOADER.bin`/`APP.bin` dieses Projekts: ihre
Reset-Handler sind `0x080030F1` bzw. `0x0800C725`, jeweils korrekt
innerhalb des Adressbereichs ihres eigenen Slots und außerhalb des des
anderen - daher wird das Setzen eines der beiden in den falschen Slot
erkannt und blockiert, nicht stillschweigend akzeptiert. Dieselbe
Logik gilt für `.hex`/`.elf`, stattdessen gegen ihre eigene eingebettete
Ladeadresse geprüft.

**Option-Bytes prüfen** (Abschnitt 4, nur STM32CubeProgrammer - pyOCD
exponiert dies nicht auf dieselbe Weise über CLI): ein
schreibgeschützter `-ob displ`-Dump, kein Löschen/Schreiben. Markiert
die RDP-Stufe mit derselben Sorgfalt, die dieses gesamte Tool rund um
das SWD-Risiko walten lässt:
- **RDP0** - kein Schutz, normal für eine Entwicklungsplatine.
- **RDP1** - über den Read Unprotect von CubeProgrammer reversibel,
  aber das löscht den Chip komplett als Teil der Entfernung - nichts,
  was dieses Tool automatisch für Sie tut.
- **RDP2** - die einzige wirklich **permanente** Sperre in diesem
  ganzen Projekt. Anders als jedes andere oben dokumentierte Risiko
  (alle über SWD wiederherstellbar), deaktiviert RDP2 den Debug-Port
  für immer, per eigenem Design von ST. Diese Prüfung existiert, um
  dies vor einer Chip-Komplett-Operation zu erkennen, nicht danach.

**Sondenauswahl** (Abschnitt 4): wenn mehr als ein ST-Link/Sonde
gleichzeitig verbunden ist, erfordert jeder Befehl, dass eine
explizit aus dem Sonden-Dropdown gewählt wird - kein "welche auch immer
das Betriebssystem zuerst aufzählt". Mit genau einer verbundenen Sonde
wird sie automatisch ausgewählt; bei null oder mehreren, drücken Sie
Aktualisieren und wählen Sie. Dies gilt sowohl für den
Chip-Komplett-Flash als auch für die Option-Bytes-Prüfung, da beide
nah genug am Destruktiven sind, dass das Erraten der falschen Platine
auf einer Werkbank mit mehreren Geräten ein echtes Risiko darstellt.

**pyOCD-Schreibvorgänge werden mit einem expliziten Rücklesen
verifiziert**, nicht nur dem Exit-Code vertraut. Der eigene
`flash`-Befehl von pyOCD überspringt das Neuschreiben von Seiten, die
bereits übereinstimmen (eine Geschwindigkeitsoptimierung, kein
Verifizierungsbericht), daher fügt dieses Tool einen
`commander compare`-Schritt gegen beide Images nach dem Schreiben
hinzu - eine echte Byte-für-Byte-Prüfung, die dem entspricht, was das
`-v`-Flag von STM32CubeProgrammer bereits tut. Nur für `.bin`: `compare`
prüft den Flash-Inhalt gegen die rohen Bytes der Datei, was mit der
eigenen Kodierung einer `.hex`/`.elf`-Datei auch nach einem
erfolgreichen Flash nicht korrekt übereinstimmen würde, daher
überspringen diese 2 Formate diesen spezifischen Schritt und
verlassen sich stattdessen auf die eigene interne
Schreibzeit-Verifizierung von pyOCD.

## 11. 📡 Übertragungstelemetrie und Verifizierungsfehler-Details
**Übertragungstelemetrie**: das Protokoll zeigt die effektiven KB/s und
die verstrichene Zeit pro Seite während eines CAN-Updates, plus eine
Zusammenfassungszeile am Ende (Gesamtzeit, durchschnittliche KB/s, wie
viele Seiten-ACK-Wiederholungen aufgetreten sind). Rein informativ -
ändert das Flash-Verhalten nicht, macht es nur leichter, auf einen
Blick "das ist einfach langsam" von "da stimmt wirklich etwas nicht"
zu unterscheiden.

**Spezifische Verifizierungsfehler-Gründe**: wenn die Verifizierung
während eines CAN-Updates fehlschlägt, sendet `bootloader_protocol.c` ein
Grund-Byte zusammen mit Status `0x05` (Verifizierung fehlgeschlagen) -
unvollständige Übertragung, CRC32-Abweichung, HMAC-Abweichung, oder
HardwareID-Abweichung, statt dass jeder Fehler gleich aussieht. Siehe
`docs/CANBUS.TXT` für das genaue Frame-Format (`0x7F5`, DLC 2 für
diesen spezifischen Status). Dieses Tool und der Bootloader stimmen bei
diesem Frame-Format überein, also flashen Sie beide zusammen, wenn Sie
einen benutzerdefinierten Bootloader mit einer anderen Protokollversion
bauen.

**Dasselbe Detail für den Erweiterungs-Slave**: ein fehlgeschlagenes
Slave-Update (Ziel: „Erweiterungs-Slave") fragt `0x219` direkt ab,
nachdem `0x215` `STATUS_VERIFY_FAIL` meldet, und leitet den eigenen
`REG_VERIFY_FAIL_REASON` des Slave-Bootloaders weiter - dieselben 5
Gründe wie oben, nur über die I2C-Bridge erreicht statt direkt aus
einem CAN-Frame gelesen. Erfordert einen Slave-Bootloader, der `0x219`
implementiert (zusammen mit der Unterstützung dieses Tools dafür
hinzugefügt); ein älterer Slave-Bootloader antwortet auf diese Anfrage
einfach nicht, und dieses Tool fällt dann auf die generische Meldung
„Verifizierung fehlgeschlagen" zurück.

## 12. 🧹 Optionales F-RAM-Löschen vor dem Flashen
Abschnitt 3 hat ein Kontrollkästchen, **"Auch das persistente F-RAM vor
dem Flashen löschen"** - standardmäßig deaktiviert. Wenn markiert,
sendet es den Lösch-Befehl mit magischem Payload (`0x192` - siehe
`docs/CANBUS.TXT`) an das persistente FM24CL64B-F-RAM der Platine,
bevor die Update-Sequenz beginnt, und löscht dabei jeden gespeicherten
Werkzeugparameterzustand.

**Für ein normales Update nicht erforderlich.** Eine Versionsabweichung
im eigenen Layout des gespeicherten Datensatzes wird bereits beim
nächsten Start sicher erkannt und ignoriert (siehe den
Parameter-Persistenz-Abschnitt von
`src/F303-master/README.md`) - dieses Kontrollkästchen existiert
für einen wirklich sauberen Neuanfang, nicht weil das Überspringen
etwas kaputt lassen würde.

**Funktioniert nur, während die Anwendung läuft** - der Bootloader
selbst behandelt `0x192` überhaupt nicht, nur `firmware_can_global_post.c` tut es.
Dieses Kontrollkästchen wird stillschweigend übersprungen (mit einer
Protokollzeile, die erklärt, warum), wenn das Kontrollkästchen "Platine
führt aktuell die Anwendung aus" darüber nicht markiert ist, da in
diesem Fall angenommen wird, dass die Platine bereits im Bootloader
sitzt.

**Eine fehlende Bestätigung stoppt den Flash nicht.** Wenn der eigene
Bestätigungs-Frame des Lösch-Befehls nicht innerhalb von 2 Sekunden
zurückkommt, wird dies als Warnung protokolliert, und das eigentliche
Firmware-Update wird trotzdem fortgesetzt - Löschen ist ein
sekundärer, optionaler Schritt neben dem eigentlichen Zweck dieses
Tools, nichts, das ein ansonsten erfolgreiches Update wegen des
Fehlens seines eigenen Bestätigungs-Frames abbrechen sollte. Prüfen
Sie den F-RAM-Status separat (die eigene
Zustand-Abfragen-Schaltfläche von `URTC Tester`), falls Ihnen das
wichtig ist.

## 🔑 Den HMAC-Schlüssel / die HardwareID ändern

Der gemeinsame Signierschlüssel lebt an 2 Stellen, die immer
übereinstimmen müssen: das `HMAC_KEY`-Array von `bootloader_common.h`, und
die `HMAC_KEY`-Konstante dieses Tools nahe dem Anfang von
`flasher_config.py`. Wenn Sie eine ändern, ändern Sie die andere und
bauen/flashen Sie den Bootloader neu, bevor Sie versuchen, irgendetwas
mit dem neuen Schlüssel zu signieren - ein Image, das mit einem
Schlüssel signiert wurde, den der Bootloader nicht hat, wird die
Verifizierung immer sicher fehlschlagen lassen und den Hauptslot
unberührt lassen.

**Oder ersetzen Sie all dies, ohne das Skript zu berühren:** eine
optionale `urtc_config.json` neben `firmware/` kann den Signierschlüssel,
die HardwareID, und die Speicherkarten-Werte setzen - nützlich für eine
andere Platinenrevision, einen rotierten Schlüssel, oder (für die
Speicherkarten-Felder) die Anpassung dieses Tools an eine andere
Chip-Variante oder ein anderes Partitionsschema, ohne eine neue
Skriptversion pro Bereitstellung zu benötigen:
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
Jedes Feld ist optional - ersetzen Sie nur, was sich tatsächlich
ändert. Eine fehlende Datei fällt stillschweigend auf die kompilierten
Standardwerte zurück; eine vorhandene, aber defekte Datei protokolliert
eine Warnung und fällt ebenfalls auf diese Werte zurück, statt das Tool
wegen eines Tippfehlers abstürzen zu lassen. **Dieser
Überschreibungsmechanismus gilt nur für die eigenen Konstanten der
Hauptplatine** - die eigenen Äquivalente des Erweiterungs-Slave-Chips
(`SLAVE_BOOTLOADER_FLASH_ADDR`, `SLAVE_APP_FLASH_ADDR`,
`SLAVE_HARDWARE_ID` usw.) sind fest in der eigenen `flasher_config.py`
verankert, da die echten Werte dieser Hardware bereits gegen ihre
eigenen echten Linker-Skripte bestätigt sind, statt eine
Bereitstellungszeit-Überschreibung zu benötigen, wie es die eigenen
Standardwerte der Hauptplatine tun. Welche Quelle aktiv ist,
wird beim Start protokolliert, sodass immer sichtbar ist, welche Werte
eine bestimmte Sitzung tatsächlich verwendet hat. `hardware_id`
akzeptiert entweder eine JSON-Zeichenkette (`"0x0303CC01"`) oder eine
einfache JSON-Zahl (`50580689`) - je nachdem, was natürlicher ist, je
nachdem, wie die Datei erzeugt wird. `app_max_size`,
`bootloader_max_size`, `flash_page_size`, `bootloader_flash_addr`, und
`app_flash_addr` sind hier ebenfalls ersetzbar, neben dem
Signierschlüssel und der HardwareID oben - nützlich, falls dieses Tool
jemals an eine andere Chip-Variante oder ein anderes Partitionsschema
angepasst wird.

## 📸 Fotos

<p align="center">
  <img src="images/URTC_FLASHER_V1_1.png" alt="URTC Flasher Fenster" width="700">
</p>

## 📂 Repository-Struktur

```
├── assets/
│   ├── URTC_APP_ICON.svg          <- gemeinsames App-/Taskleisten-Symbol (Vektor)
│   ├── URTC_LOGO_FLASHER.svg      <- Banner-Quelle (Vektor), beim Start 5s zentriert angezeigt
│   ├── urtc_banner.png            <- aus dem .svg oben gerendert, oben im Fenster angezeigt
│   ├── urtc_icon.ico              <- Taskleisten-/Fenstersymbol unter Windows
│   └── urtc_icon.png              <- Taskleisten-/Fenstersymbol unter Linux
├── firmware/
│   ├── URTC_V1.1_F303CC.bin       <- aktuelle Anwendungs-Firmware der Hauptplatine
│   ├── URTC_v1.0_F303CC.bin       <- ältere Hauptplatinen-Version, als reales Beispiel für
│   │                                  "mehr als eine gültige Datei" behalten (siehe Abschnitt 3 oben)
│   ├── URTC_BOOTLOADER.bin        <- Bootloader der Hauptplatine (nur SWD/JTAG, aus der
│   │                                  CAN-OTA-Firmwareliste herausgefiltert - siehe Abschnitt 3 oben)
│   ├── URTC_SLAVE_APP.bin         <- Anwendung des Erweiterungs-Slave-Chips (nur fortgeschrittene Erweiterungsplatinen)
│   └── URTC_SLAVE_BOOTLOADER.bin  <- Bootloader des Erweiterungs-Slave-Chips
├── images/
│   ├── URTC_FLASHER_V1_1.png      <- echter Fenster-Screenshot, im Abschnitt Fotos oben gezeigt
│   └── URTC_LOGO_FLASHER.svg      <- Galerie-Kopie von assets/URTC_LOGO_FLASHER.svg oben
├── language/
│   ├── english.lng                <- Standardsprache, einfache KEY=Value-Paare
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   └── german.lng
├── logs/                           <- automatisch erstellt, eine Datei pro Sitzung
├── urtc_config.json.example        <- Vorlage für die optionale Override-Datei urtc_config.json
│                                       (siehe "Den HMAC-Schlüssel / die HardwareID ändern" oben) - kopiere sie
│                                       nach urtc_config.json und bearbeite sie, statt bei Null anzufangen
├── urtc_flasher.py                <- Einstiegspunkt: CLI-Argumente, Splash-Screen, Hauptfenster-Setup
├── flasher_config.py              <- Konfigurationsdatei-I/O, Sprachladung, Protokollkonstanten
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- STM32CubeProgrammer-/pyOCD-Wrapper
├── flasher_validation.py          <- Firmware-Dateivalidierung (.bin/.hex/.elf)
├── flasher_protocol.py            <- die eigentliche CAN-OTA-Zustandsmaschine
├── flasher_github.py              <- lädt Firmware aus dem eigenen GitHub-Repository von URTC herunter
├── flasher_gui.py                 <- das Hauptfenster (FlasherGUI) und seine Menüleiste
├── requirements.txt
├── build_exe.bat                  <- eigenständiger Build für Windows
├── build_exe.sh                   <- eigenständiger Build für Linux
├── URTC_Flasher.spec              <- PyInstaller-Spec, die von beiden Build-Skripten oben verwendet wird
├── README.md                      <- (englische Version)
├── README_deu.md                  <- diese Datei
├── README_zho.md / README_jpn.md  <- weitere Übersetzungen
├── README_spa.md / README_ita.md / README_fra.md  <- weitere Übersetzungen
├── LICENSE
├── .gitattributes
└── .gitignore
```

Dieses Tool ist aus Gründen der Lesbarkeit in die obigen `flasher_*.py`-
Module nach Zuständigkeit gegliedert - es gibt keinen funktionalen
Unterschied zwischen getrennten Dateien und einer einzigen großen Datei.

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil eines größeren Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da sich eine Anfrage eigentlich auf eines dieser Projekte statt auf dieses Repository beziehen könnte:

**Direkt mit diesem Tool verwandt**
- **[URTC](https://github.com/JuanenRac/URTC)** — genau die Firmware, die dieses Tool über CAN-OTA/SWD/JTAG flasht.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — macht im Flottenmaßstab (Befehl `flash-all`), was dieses Tool für eine einzelne Platine macht.

**HYDRA-UMC-Plattform** — die Multi-Roboter-Mikrofabrikzelle
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — die Hauptplatine selbst: Raspberry-Pi-CM5-Host + dualer STM32H745-Echtzeit-Coprozessor, der bis zu 8 verteilte Roboterarme über CAN-OTA/SPI-OTA orchestriert. Eigene Hardware + Firmware, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — webbasiertes Steuerungs-Dashboard für HYDRA-UMC: Multi-Roboter-3D-Visualisierung, Kinematik-/Trajektorienaufzeichnung, CAN-OTA-Flashing und -Testing für die gesamte Plattform. React + Vite + Three.js.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das Headless-Backend (Node/Express/WebSocket), das früher in den eigenen Prozess von HYDRA-UMC-STUDIO eingebettet war. Es besitzt die REST/WS-API zur Robotersteuerung, die settings.json-Persistenz, die JWT-Authentifizierung und die mDNS-Discovery. HYDRA-UMC-STUDIO ist jetzt ein rein statischer Frontend-Client, der über das Netzwerk mit ihm kommuniziert.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — Android-Steuerungs-App für HYDRA-UMC über Wi-Fi/Bluetooth. Echte, funktionierende App - vollständiger Funktionsumfang zur Fernsteuerung, JWT-Authentifizierung, verschlüsselte Speicherung von Zugangsdaten.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App für HYDRA-UMC über Wi-Fi, in Flutter gebaut (plattformübergreifend, unter Windows ohne Mac überprüfbar; die endgültige `.ipa`-Paketierung benötigt weiterhin Xcode). Echte, funktionierende App - gleicher Funktionsumfang wie die Android-App.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarmleitstand (Python/PySide6): Netzwerkerkennung für mehrere Controller, live-bidirektionale Synchronisierung, echtes 3D-Roboter-Viewport, andockbarer Workspace im Photoshop-Stil. Echt und funktionierend, kein Platzhalter.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor (Python/PySide6) für den eigenen Modellkatalog dieses Projekts: zieht Quelldateien von GitHub oder einem lokalen Ordner, validiert die DOF-Machbarkeit, bearbeitet Farbe/Skalierung/Kinematik mit Live-3D-Vorschau und veröffentlicht das fertige Ergebnis auf einem laufenden STUDIO-Server. Echt und funktionierend, kein Platzhalter.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Flutter-Touch-UI für HYDRA-UMCs eigenen 5"/7"-DSI-Touchscreen (1280×720, gleiche Auflösung bei beiden Größen - korrigierter Wert, nicht 1280×800) am Compute Module 5, die denselben Server direkt von der Platine aus steuert. Echtes, funktionierendes Grundgerüst mit allen 6 Katalogbildschirmen (Dashboard, manuelle Steuerung, Kamera, vereinfachte 3D-Ansicht, Systemmetriken, Login), angebunden an den Live-Server; der echte Linux-Build wurde bisher noch nicht auf echter Hardware ausgeführt (bislang nur Windows-Arbeitsumgebung - siehe das eigene README dieses Projekts).

**URTC-Plattform** — der Werkzeugkopf-Controller, den jeder HYDRA-UMC-Roboterarm trägt
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller: STM32F303-basierter CAN-Bus-Werkzeugkopf-Controller, 25 vollständig implementierte Werkzeugprofile, CAN-OTA-Firmware-Update.
- **URTC Flasher** *(dieses Repository)* — Desktop-Tool für CAN-OTA- + Full-Chip-SWD/JTAG-Flashing für URTC-Platinen (Windows/Linux).
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Tool zur Live-CAN-Bus-Diagnose für URTC-Platinen, ein Panel pro Werkzeugprofil (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu den beiden Desktop-Tools oben (Web Serial API + SLCAN), keine lokale Installation nötig.

**Rest des Ökosystems** — über die obigen Projekte hinaus umfasst das Robotik-Ökosystem desselben Autors viele weitere Projekte, gruppiert nach Bereich:

**👁️ Vision-KI-Knoten (Hailo-8):** [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE), [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER), [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF), [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES), [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)

**🧠 Kognitiver KI-Knoten (Hailo-10):** [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE), [HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE), [HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI), [HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER), [HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)

**🐝 Orchestrierung & Schwarm:** [HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR), [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC), [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D), [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER), [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)

**🎮 Digitaler Zwilling & Simulation:** [HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN), [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA), [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE), [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)

**📊 Daten & Analytik:** [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE), [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR), [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR), [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)

**🏭 Industrie-Gateway:** [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL), [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER), [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER), [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)

**🛠️ Ergänzende Werkzeuge:** [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK), [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL), [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH), [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

## 📜 LIZENZ

URTC Flasher ist (c) 2026 JuanenRac (Electro Hobby 3D). Dieser Hinweis
muss in jeder Verteilung dieses Projekts oder abgeleiteter Werke
enthalten sein.

Dieses Projekt besteht aus Quellcode und seiner eigenen Dokumentation,
die unter verschiedenen Lizenzen verfügbar gemacht werden - jede
passend zu dem, was sie tatsächlich abdeckt:

1. Der Quellcode (`urtc_flasher.py` und jedes `flasher_*.py`-Modul)
   und jedes daraus über `build_exe.bat`/`build_exe.sh` erstellte
   Binary sind unter der **GNU General Public License v3.0 (GPL-3.0)**
   verfügbar. Vollständiger Text unter
   https://www.gnu.org/licenses/gpl-3.0.html.

2. Die Dokumentation (dieses README und seine eigenen Übersetzungen -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`)
   ist unter **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)** verfügbar. Vollständiger Text unter
   https://creativecommons.org/licenses/by-sa/4.0/.

Dieses Tool ist der CAN-OTA/SWD-JTAG-Flash-Begleiter des
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
-Projekts - siehe das eigene Repository dieses Projekts für die
Platinen-Firmware, Hardware-Designs und die vollständige
Protokolldokumentation, gegen die dieses Tool implementiert. Die eigene
Firmware von URTC ist GPL-3.0 und ihre Hardware-Designs sind CERN-OHL-S
v2; die eigene Lizenz dieses Tools erstreckt sich hier nicht auf dieses
separate Projekt, und umgekehrt. Eine webbasierte Alternative, die
ähnliches Terrain abdeckt, existiert ebenfalls unter
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Wenn Sie auf diesem Projekt aufbauen, denken Sie an die Lizenztrennung:
Codeänderungen sollten GPL-3.0 bleiben, Dokumentationsableitungen
sollten CC BY-SA bleiben - jeweils mit Zuschreibung zurück an dieses
Projekt und seinen Autor.

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
