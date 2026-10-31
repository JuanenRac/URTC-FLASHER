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
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Aktualisiert die Firmware einer URTC-Platine über CAN (CAN-OTA) und programmiert den ganzen Chip über SWD/JTAG, unter Windows und Linux

<p align="center">
  <img src="https://img.shields.io/badge/Lizenz-GPL%203.0-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Sprache-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Protokoll-CAN--OTA-orange.svg" alt="CAN-OTA">
</p>

---

**Ehrlichkeitscheck - was heute wirklich läuft:** `tests/` enthält 51 pytest-Dateien (602 Tests: alle bestehen; 73 davon werden ohne PySide6 übersprungen) - das CAN-OTA-Protokoll gegen einen echten `MockCAN`-Transport (`flasher_transports.py`), der eine vollständige simulierte Bootloader-Sequenz abspielt (Start/Löschen/Empfang, Seitendaten + PAGE_ACK, HMAC-Blöcke, Update-Ende mit echtem Erfolg oder einem bestimmten `VERIFY_FAIL_REASON`), die Signaturregeln (veröffentlichte Signatur ohne Schlüssel gesendet, unsigniertes Image abgelehnt, nicht passender Manifest-sha256 vor jedem Busverkehr abgelehnt), die Image-Integritätsprüfungen und den mitgelieferten Ordner `firmware/` gegen seine Manifeste. GitHub Actions (`.github/workflows/ci.yml`) führt diese Suite bei jedem Push aus, und `tools/build_test.py` führt sie in `build-test.sh`/`.bat` aus. Außerdem führt sie `ruff check` und `python -m mypy` aus (eine Typprüfung des Programms und der Kopien des gemeinsamen Codes). Die drei Skripte `verify_qt_*.py` im Wurzelverzeichnis sind echte End-to-End-Prüfungen außerhalb von pytest (sie brauchen eine echte Qt-Ereignisschleife; Aufruf mit `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`); `verify_qt_swd_full_chip_flash.py` baut die Befehle für `PyOCDCLI`/`CubeProgrammerCLI` nur mit `dry_run=True`. Nichts davon wurde in dieser Umgebung gegen eine echte Platine ausgeführt. Siehe `CHANGELOG.md` für den genauen Stand. Der simulierte Bootloader (`MockCAN`) ist nur ein aus der Protokollbeschreibung gebautes Modell: Er bildet die Seiten-ACKs, die teilweise letzte Seite und die Readback-Frames nach, ist aber nicht der echte Bootloader, daher ersetzt ein grüner Testlauf keinen Versuch an einer echten Platine (das offizielle Image mit 73476 Byte ließ sich nicht installieren und der letzte Frame einer Sicherung ging verloren, während die Tests bestanden, gerade weil die Simulation nachsichtiger war als der echte Bootloader).

---

> **Stand von Sicherheit (Safety) und Security:** Dieses Ökosystem ist kein zertifiziertes Sicherheitssystem, und es existiert noch keine bestückte URTC-Platine. Die Bootloader prüfen Firmware-Images mit CRC32 und einem HMAC-SHA256 mit gemeinsamem Schlüssel, nicht mit einer asymmetrischen Signatur (geplant); die veröffentlichten Anwendungs-Images sind mit dem öffentlichen Entwicklungsschlüssel signiert (`signing_key_kind: dev`), sodass jeder ein vom Bootloader akzeptiertes Image erzeugen kann; an eine echte Platine wurde noch nichts gesendet. Lesen Sie die [Sicherheitsbasis](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) und das [Bedrohungsmodell](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md), bevor Sie sich für die Sicherheit einer Person auf eine Aussage hier verlassen.

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.4.3` |
| Reifegrad | Funktionsfähig |
| Tests | 602 (`python -m pytest tests -q`) |
| Technik | Python / PySide6 / Qt Quick / CAN-OTA / SWD/JTAG |
| Ziel | Der PC der Person, die es benutzt |
| Auf echter Hardware | Nur simuliert: gegen Emulatoren, Attrappen oder Simulatoren getestet; für diese Version ist kein Lauf auf echter Hardware vermerkt |

**Springe zu:** [Überblick](#-überblick) · [Architektur](#-architektur) · [Funktionen](#-funktionen) · [Sicherheit](#-sicherheit-und-schutz) · [Schnittstellen](#-schnittstellen) · [Konfiguration](#-konfiguration) · [Schnellstart](#-schnellstart) · [Tests](#-tests) · [Struktur](#-struktur-des-repositorys) · [Verwandte](#-verwandte-projekte)

<!-- urtc-section:status_flasher -->
## 🚦 Projektstatus

🟢 fertig und überprüft · 🟡 funktioniert, mit bekannten Grenzen · 🟠 halb fertig oder nicht überprüft · 🔴 nicht gemacht oder funktioniert nicht. Nichts ist grün, wenn es nie auf echter Hardware lief.

| Teil | Status | Was das Repository belegen kann |
| --- | :---: | --- |
| Software | 🟡 | Läuft am PC und gegen den Simulator; nie an einer echten Platine ausgeführt. |
| Oberfläche | 🟡 | Das Fenster läuft und wird gegen eine simulierte Platine geprüft; nicht mit einem echten Adapter probiert. |
| Tests | 🟢 | Die Testsuite besteht bei jedem Push in der CI. |
| Echte Hardware | 🟠 | Noch kein Lauf an einer echten Platine: der Bankversuch steht noch aus. |
| Sicherheit | 🟡 | Releases werden mit Ed25519 signiert und vor der Nutzung geprüft; der Umgang mit den Schlüsseln wurde von niemand anderem geprüft. |
| Dokumentation | 🟡 | README in acht Sprachen und Referenzdokumente; die Übersetzungen wurden nicht von Muttersprachlern geprüft. |

<!-- /urtc-section:status_flasher -->

## 🎯 Überblick

Ein kleines plattformübergreifendes GUI-Tool zum Aktualisieren der
URTC-Platinen-Firmware über den CAN-Bus. Es implementiert genau das
Bootloader-Protokoll aus `docs/CANBUS.TXT` (im Schwester-Repository [URTC](https://github.com/JuanenRac/URTC), gegen das dieses Werkzeug implementiert ist - siehe «Verwandte Projekte» gegen Ende dieses Dokuments; jeder andere Verweis auf `docs/*.TXT` in diesem README zeigt ebenfalls dorthin): die HardwareID-Prüfung, das HMAC-SHA256 mit gemeinsamem Schlüssel (keine asymmetrische Signatur), den Golden-Image-Backup-Slot-Update-Ablauf, den
Live-Fortschritt über die Heartbeat-Nachrichten des Bootloaders, und
eine Versionsabfrage (identifiziert, ob sich die Anwendung *oder* der
Bootloader dieser Platine über CAN meldet), damit Sie sehen können, was
aktuell installiert ist, bevor Sie entscheiden, was geflasht werden
soll.

**Nach Updates suchen.** Die Schaltfläche „Nach Updates suchen“ fragt GitHub einmal nach dem neuesten Release und bietet den Download nur an, wenn es ein Paket für dieses System enthält, das neuer als die installierte Version ist. Das Paket wird nur akzeptiert, wenn SHA-256 und Ed25519-Signatur (der im Programm angeheftete Schlüssel der Releases) gültig sind; es wird erst nach Ihrer Bestätigung installiert, nie während einer Übertragung, und die vorherige Version bleibt zum Zurückgehen erhalten (und wird von selbst wiederhergestellt, wenn die neue nicht startet). Nichts wird von selbst geprüft oder installiert: die Prüfung beim Start ist eine Option, standardmäßig aus, und die Bestätigung lässt sich nur im selben Fenster nach einer Warnung abschalten.

Zwei Wege, mit der Platine zu sprechen, beide sprechen darunter dasselbe
Protokoll:

- **Seriell / SLCAN** — funktioniert unter Windows und Linux. Benötigt
  einen USB-CAN-Adapter mit SLCAN-Firmware, verbunden als virtueller
  serieller Port.
  - Ohne Adapter und ohne Hardware springt eine virtuelle Platine ein: `python -m urtc_can.virtual_board` ausführen, ihre Adresse vor dem Start des Programms in der Umgebungsvariable `URTC_VIRTUAL_PORT` angeben (zum Beispiel `socket://127.0.0.1:7777`) oder in der Befehlszeile an `--port` übergeben. Sie erscheint in der Portliste und antwortet wie eine Platine, Anwendung und Bootloader.
- **SocketCAN** — **nur Linux**, und nur in der Benutzeroberfläche des
  Tools unter Linux angezeigt. Spricht direkt mit einer
  Kernel-Netzwerkschnittstelle `can0`/`slcan0`. Wenn Ihr Adapter
  bereits `gs_usb`/candleLight-Firmware ausführt (die meisten
  CANable-Platinen tun dies ab Werk), benötigt dieser Weg
  **überhaupt kein Reflashen des Adapters** — der native Treiber von
  Linux übernimmt dies direkt.

## 🧩 Rolle in URTC

URTC-FLASHER ist das Programm, das Firmware auf eine URTC-Platine bringt. Es spricht das Bootloader-Protokoll von URTC (`docs/CANBUS.TXT` jenes Repositorys) über einen USB-CAN-Adapter, als serielle SLCAN-Schnittstelle oder als SocketCAN unter Linux: die HardwareID-Prüfung, HMAC-SHA256-Blöcke mit gemeinsamem Schlüssel, den Golden-Image-Ablauf mit Sicherungsslot und eine Versionsabfrage, damit man sieht, was installiert ist, bevor man entscheidet, was geflasht wird. Für eine Platine ohne funktionierenden Bootloader oder um den ganzen Chip zu programmieren, bereitet es die SWD/JTAG-Befehle für pyOCD oder STM32CubeProgrammer vor. Es ist der Update-Begleiter von URTC-TESTER, teilt seinen CAN-Code über URTC-COMMON mit ihm, und URTC-UPDATER kann ihm ein Firmware-Image übergeben, dessen Release-Signatur schon geprüft wurde.

## 🏛️ Architektur

<p align="center">
  <img src="images/architecture.svg" alt="Architektur von URTC-FLASHER: wer es nutzt, was es enthält und wovon es abhängt" width="100%">
</p>

Wie die Teile dieses Repositorys zusammenpassen: wer es nutzt, was es enthält und wovon es abhängt. Das Bild wird aus `docs/architecture.json` gezeichnet und gegen den Code geprüft.

<!-- urtc-section:updates -->
### So wird aktualisiert

Dieses Programm kann nach einer neueren Version seiner selbst suchen: Die Schaltfläche „Nach Updates suchen“ fragt GitHub einmal und bietet ein signiertes Paket nur an, wenn es für Ihr System ist und neuer. Nichts wird von selbst geprüft oder installiert, solange Sie die Prüfung nicht einschalten, und ein Update braucht Ihre Bestätigung. Das Paket muss zu seinem SHA-256 und zur Signatur des im Programm angehefteten Release-Schlüssels passen; die vorherige Version bleibt erhalten und wird von selbst wiederhergestellt, wenn die neue nicht startet. `urtc-updater --cli package list|check|install|rollback` macht dasselbe auf der Kommandozeile für Flasher und Tester, und `install --file` funktioniert ohne Netzwerk.
<!-- /urtc-section:updates -->

## 🖼️ Screenshots

<!-- urtc-shots -->
Aufgenommen mit 1920×1080 auf einem Prüfstand, mit Beispieldaten und ohne eine echte Anlage dahinter.

<table>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/deck.png" alt="Das Fenster beim Öffnen: die Verbindung, das Firmware-Inventar, die vier Kontrollpunkte einer CAN-OTA-Aktualisierung und die Gerätekonfiguration." width="100%"><br><sub>Das Fenster beim Öffnen: die Verbindung, das Firmware-Inventar, die vier Kontrollpunkte einer CAN-OTA-Aktualisierung und die Gerätekonfiguration.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/heads.png" alt="Werkzeugköpfe am Bus: ein modellierter Bus mit sechs Köpfen, jeder in einem anderen möglichen Zustand (gewählt, Adresskonflikt, Fehler gehalten, im Bootloader, verloren und bereit)." width="100%"><br><sub>Werkzeugköpfe am Bus: ein modellierter Bus mit sechs Köpfen, jeder in einem anderen möglichen Zustand (gewählt, Adresskonflikt, Fehler gehalten, im Bootloader, verloren und bereit).</sub></td>
</tr>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/help.png" alt="Das Hilfefenster: die Schritte zur Benutzung des Programms, in der Sprache des Fensters." width="100%"><br><sub>Das Hilfefenster: die Schritte zur Benutzung des Programms, in der Sprache des Fensters.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/updates.png" alt="Das Update-Fenster: ein neueres signiertes Paket wird erst nach deiner Bestätigung installiert." width="100%"><br><sub>Das Update-Fenster: ein neueres signiertes Paket wird erst nach deiner Bestätigung installiert.</sub></td>
</tr>
</table>
<!-- /urtc-shots -->

Diese Bilder zeigen das echte Fenster, ohne Bildschirm gezeichnet, so wie es sich öffnet (nichts verbunden, nichts gesendet). Die Anleitung führt durch das Deck, das Hilfefenster und das Update-Fenster.

[Anleitung mit Bildern](docs/WINDOW_GUIDE.md)

## ✨ Funktionen

### Prüfen, was aktuell installiert ist

> Im Qt-Quick-Steuerpult stehen die Ports beider Transporte (serielle Adapter und unter Linux SocketCAN-Schnittstellen) in einer Liste, und die Abfragen dieses Abschnitts erledigt **PLATINENSTATUS LESEN**: Es fragt Version, CAN-Fehlerzähler, Erweiterungsplatinentyp, MLX9064x-Variante und Peripherieinfo auf einmal ab und zeigt sie im Board-Snapshot. Die Speichern-Schaltflächen der Gerätekonfiguration schreiben die Werte.
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

**Die Patch-Nummer.** Eine Platine mit Firmware 0.3.5 oder neuer sendet
zusätzlich die Patch-Nummer der installierten Anwendung (Frame `0x7E9`,
direkt nach `0x7F9`), sodass das Fenster und das Protokoll die vollständige
Version `Major.Minor.Patch` (zum Beispiel `v0.3.5`) statt `Major.Minor`
anzeigen; der Patch eines Images ist der dritte Teil der Version in seinem
Manifest. Vor einem Update zeigt das Protokoll `installiert -> neu` in
dieser Form, und der Patch fließt nur dann in die Warnung "älter als
installiert" ein, wenn beide Seiten einen haben. Eine Platine, die älter
als der Patch ist, antwortet ohne ihn und wird genau wie bisher angezeigt.
Meldet der Bootloader (Flag im selben Frame), dass er den Patch liest,
trägt der Frame zum Ende des Updates ihn im oberen Byte des Minor-Felds;
jeder andere Bootloader und jedes Image ohne Patch erhalten den
unveränderten Frame mit zwei Zahlen. Die Versionsantwort des
Erweiterungs-Slaves (`0x218`) hat dieselbe optionale Erweiterung. Das
folgt der Protokollbeschreibung und ist nur gegen den Simulator getestet;
auf einer echten Platine wurde es nicht ausprobiert.

Was Sie sehen werden:

- **`v0.2 (application, HardwareID 0x0303CC01)`** - normaler Fall,
  Anwendung läuft, alles stimmt überein.
- **`Bootloader running, no valid firmware currently installed,
  bootloader v0.1.2`** - die Platine steckt im Bootloader fest, ohne
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

### Flashen

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
   weitergeleitet (die eigenen `0x210`-`0x219` von `CANBUS.TXT`), keine
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
stillschweigend leere Datei. In der Praxis heißt das: Die Sicherung funktioniert bei einer Platine ohne gültige Anwendung oder bei einer mitten im Update stehengebliebenen Platine. Mit gültiger Anwendung springt der Bootloader etwa 600 ms nach dem Reset dorthin, sofern kein Start-Update-Frame (`0x7F1`) eintrifft, und dieses Tool hat keine Schaltfläche, die den Bootloader warten lässt (dafür wäre eine Änderung im Bootloader nötig). Für eine normal laufende Platine sichern Sie den Flash stattdessen über SWD/JTAG (Abschnitt 6).

**Hinweise zu Version und Signatur**: Vor der Übertragung fragt das Tool die Platine, was installiert ist, und protokolliert „installiert vX.Y -> neu vA.B“; ist die neue Version älter, warnt es, dass der Bootloader sie ohne erlaubtes Downgrade ablehnt, und empfiehlt zuerst eine Sicherung. Ein Image, dessen Manifest angibt, mit dem ÖFFENTLICHEN Entwicklungsschlüssel signiert zu sein (die mitgelieferten offiziellen Images sind es), zeigt unter dem Dateinamen eine rote Warnung; mit `"require_production_signature": true` in `urtc_config.json` werden solche Images ganz abgelehnt. Antwortet die Platine aus dem Bootloader ohne gültige Firmware, wird das neueste offizielle Hauptplatinen-Image aus `firmware/` zur Prüfung und zum Flashen vorausgewählt. Nach jedem erfolgreichen Update wird ein kleiner Bericht geschrieben (`logs/urtc_update_report_*.json`: Tool-Version, Bediener, Name, Größe und SHA-256 des Images, Versionen vorher und nachher); er trägt seine eigene SHA-256, damit eine Änderung auffällt, ist aber keine Signatur.

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

### Den kompletten Chip via SWD/JTAG programmieren (fortgeschritten)

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

### Diagnose — Busaktivität, Bitrate, und Debug-Pakete

**Bitrate-Auswahl + Auto-Erkennung** (nur Seriell/SLCAN): der Bus von
URTC ist fest auf 500 kbit/s, was der Standard bleibt - dies ist für
einen falsch konfigurierten Adapter oder zur Fehlersuche bei einer
nicht standardmäßigen Platine gedacht. **Auto-Erkennung** hört nur *zu*:
Sie öffnet den Adapter im SLCAN-Nur-Hören-Modus (`L`) nacheinander bei
jeder Standard-Bitrate und stoppt bei der ersten, bei der sie einen
gültigen CAN-Frame hört; sie sendet also nie und kann einen laufenden Bus
nicht stören. Deshalb müssen andere Knoten senden und der Adapter muss den
Nur-Hören-Modus unterstützen; bei ruhigem Bus (oder mit einem Adapter ohne
diesen Modus) findet sie nichts, und Sie wählen die Bitrate von Hand. Noch
nicht verbunden, wenn Sie darauf klicken. Die Bitrate von SocketCAN wird
auf Betriebssystemebene festgelegt (`ip link`), daher ist dieses
Steuerelement für diesen Transport deaktiviert - es gibt hier nichts zu
versuchen.

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

### SWD/JTAG — Dateiformate, Slot-Verifizierung, und Sondenauswahl

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
Reset-Handler sind `0x08000785` bzw. `0x0800C0CD`, jeweils korrekt
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

### Übertragungstelemetrie und Verifizierungsfehler-Details

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

### Optionales F-RAM-Löschen vor dem Flashen

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

<!-- urtc-section:heads -->
### Mehrere Werkzeugköpfe an einem Bus

Die Firmware kann mehrere Werkzeugköpfe an einem CAN-Bus betreiben (die Multinode-Erweiterung). Sie ist **standardmäßig aus**, und ein Bus mit einem Kopf arbeitet genau wie bisher. Das Fenster **Köpfe** findet die Köpfe, listet jeden mit Adresse, Werkzeug und Seriennummer und zeigt seinen Zustand: bereit, ausgewählt, Adresskonflikt, Fehler gespeichert, im Bootloader oder verloren. Sie wählen einen aus, das Programm fragt nach einer Bestätigung und sendet erst danach etwas an diesen Kopf; solange mehrere Köpfe am Bus hängen, wird ein Befehl abgelehnt, bis einer ausgewählt ist und es bestätigt hat. Geht der ausgewählte Kopf verloren, wechseln alle Köpfe in ihren sicheren Zustand (ein Kontrollkästchen des Fensters schaltet das ab). Getestet wurde nur gegen ein Modell des Busses, nicht mit Platinen. Siehe `docs/MULTINODE.md` in URTC-COMMON.
<!-- /urtc-section:heads -->

<!-- urtc-section:bus_scenarios -->
### Fehler des simulierten Busses

Ein Plan oder eine Aktualisierung kann ohne Hardware gegen einen simulierten Bus laufen, der sich so schlecht benimmt wie ein echter. Ein Szenario ist eine JSON-Datei (`urtc-scenario/1`), die die Fehler aufzählt: Frames gehen verloren, werden wiederholt, vertauscht, verzögert, in Bursts verloren oder verkürzt, ein Knoten schweigt oder lehnt einen Befehl ab und nennt den Grund, und ein Kopf in freier Konfiguration (`0x1F`) antwortet auf `0x1A3` und `0x1A2` auf unterschiedliche Weise. Nichts ändert sich, wenn Sie es nicht verlangen: Die Option ist `--scenario DATEI` (mit dem simulierten Kopf des Testers oder dem Mock-Transport des Flashers); die Datei wird streng geprüft und abgelehnt, wenn etwas darin nicht verstanden wird, und ein echter Adapter nimmt nie eines an. Dasselbe Szenario mit demselben Seed ergibt dieselben Frames in derselben Reihenfolge, und `bus_scenario.py generate --seed N` schreibt Testszenarien, die die Fehler kombinieren. Der Lauf hinterlässt den üblichen Nachweis (`urtc-evidence/1`), der festhält, dass der Bus eine Simulation war und mit welchem Szenario und Seed. Ein Szenario kann Frames wegnehmen, wiederholen oder verschieben, aber es kann einen Knoten nicht sagen lassen, dass etwas funktioniert hat. Format und Regeln: [Bus-Szenarien](https://github.com/JuanenRac/URTC-COMMON/blob/main/docs/BUS_SCENARIOS.md).
<!-- /urtc-section:bus_scenarios -->

## 🔒 Sicherheit und Schutz

| Risiko | Abwehr |
|---|---|
| Ein Image auf die falsche Platine flashen | Die HardwareID-Prüfung des Bootloader-Protokolls, durchgeführt, bevor etwas geschrieben wird |
| Ein beschädigtes, unsigniertes oder manipuliertes Image | Die Integritätsprüfungen des Images; ein Manifest, dessen `sha256` nicht zur Datei passt, wird vor jedem Busverkehr abgelehnt, ein unsigniertes Image wird abgelehnt, und die veröffentlichte Signatur wird ohne jeden Schlüssel gesendet; die Release-Signatur (Ed25519) wird geprüft, bevor ein Image eines Releases verwendet wird |
| Versehentlich ein älteres Image installieren | Die Anti-Rollback-Prüfung des Bootloaders; ein bewusstes Zurückgehen braucht die Downgrade-Autorisierung |
| Ein fehlgeschlagenes Update, das die Platine unbrauchbar macht | Das Golden-Image-Modell: Der Sicherungsslot behält die vorherige Firmware, ein verlorener Bestätigungs-Frame wird durch erneute Versionsabfrage behoben statt einen falschen Fehler zu melden, und der Hauptslot kann vorher zurückgelesen werden |
| Ein manipuliertes Update dieses Programms | „Nach Updates suchen“ akzeptiert nur ein Paket mit gültigem SHA-256 und gültiger Ed25519-Signatur (der im Programm festgelegte Schlüssel der Releases), installiert nur nach einer Bestätigung und nie während einer Übertragung und behält die vorherige Version |

Der Bootloader prüft Images mit CRC32 und einem HMAC-SHA256 mit gemeinsamem Schlüssel, nicht mit einer asymmetrischen Signatur; die veröffentlichten Anwendungs-Images sind mit dem öffentlichen Entwicklungsschlüssel signiert, sodass jeder ein Image bauen kann, das der Bootloader akzeptiert. Nichts davon lief auf einer echten Platine.

### Zuverlässigkeit während eines CAN-Updates, und Sitzungsprotokolle

Wenn das ACK einer Seite nicht innerhalb des normalen 3s-Fensters
während eines CAN-Updates ankommt, wartet das Tool erneut (es sendet die
Seitendaten nicht noch einmal) bis zu zweimal mehr mit einer kurzen
zunehmenden Verzögerung, bevor es aufgibt. Das hilft nur bei einem ACK,
das lediglich verspätet ist: Der Bootloader sendet jedes Seiten-ACK genau
einmal und wiederholt es nie, ein wirklich verlorenes ACK lässt sich also
nicht wiederherstellen, und das Update wird mit einem Fehler abgebrochen
(die Platine bleibt in ihrem Bootloader, und das Update kann einfach neu
gestartet werden). Das Tool sendet absichtlich keine Seitendaten bei einem
Timeout erneut - wären die Daten gut angekommen, würde ein erneutes Senden
den Bootloader diese Bytes als Anfang der *nächsten* Seite lesen lassen
und die Übertragung desynchronisieren. Während des Wartens wird der eigene
Heartbeat des Bootloaders (ungefähr einmal pro Sekunde gesendet) mit dem
Fortschritt verglichen, den die Seite ergeben würde, und das Protokoll
vermerkt, wenn beide übereinstimmen; der Heartbeat ist ein ganzer
Prozentwert, also nur ein Hinweis und kein Beweis, dass die Seite
angekommen ist, und er ändert nie das Ergebnis.

Jede Sitzung schreibt auch eine zeitgestempelte Protokolldatei nach
`logs/` (`urtc_flasher_YYYYMMDD_HHMMSS.log`),
unabhängig vom Bildschirmprotokoll - nützlich, um eine vollständige
Spur an denjenigen weiterzugeben, der die Firmware geschrieben hat,
falls im Feld etwas schiefgeht. Dieser Ordner wird automatisch erstellt
und ist sicher zu löschen; nichts liest alte Protokolle zurück. Es werden nur die neuesten 30 Sitzungsprotokolle behalten; kann der Ordner neben dem Programm nicht beschrieben werden (schreibgeschützte Installation), wird stattdessen ein Benutzerordner verwendet (`%LOCALAPPDATA%\URTC-Flasher\logs` unter Windows, sonst `~/.local/state/urtc-flasher/logs`).

## 🔌 Schnittstellen

Für CI-Pipelines, Testbänke, oder Produktionslinien-Skripting, wo es
keinen Bildschirm gibt:

```
python3 urtc_flasher.py --cli --port /dev/ttyACM0 --file firmware.bin
```

```
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan,python-can,mock}] --port PORT
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

**`--transport python-can`** nutzt das optionale Paket `python-can` (`pip install python-can`) für PCAN, Kvaser, gs_usb/candleLight und die anderen unterstützten Schnittstellen, sodass der Adapter nicht auf SLCAN umgeflasht werden muss: `--port` ist dann `<Schnittstelle>:<Kanal>` (zum Beispiel `pcan:PCAN_USBBUS1`), und der Bus wird mit 500 kbit/s geöffnet. Das Fenster bietet dieselben Adapter an, wenn `python-can` installiert ist: die, die es für PCAN, Kvaser und gs_usb findet, und die in der Umgebungsvariable `URTC_PYTHON_CAN` genannten (`<Schnittstelle>:<Kanal>`, durch Kommas getrennt), aufgelistet als `python-can:<Schnittstelle>:<Kanal>`; die Busgeschwindigkeit dieser Verbindung ist fest 500 kbit/s. Das Fenster lässt sich auch mit `--firmware PFAD` starten, damit schon ein Image ausgewählt ist (auf eine Platine wird erst geschrieben, wenn Sie verbinden und das Update bestätigen).

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

- **Verlauf der Vorgänge.** Die Schaltfläche **Verlauf** neben Hilfe öffnet die Nachweisdatensätze (`urtc-evidence/1`), die URTC-FLASHER in seinem Protokollordner geschrieben hat. Jede Zeile zeigt die Art, das Ergebnis, das Werkzeug, die Platine und die Versionen, die neuesten zuerst; ein nach dem Schreiben bearbeiteter Eintrag, eine Datei, die kein JSON ist, oder ein Eintrag eines anderen Formats wird als ungültig angezeigt, mit dem, was nicht stimmt. Die Liste lässt sich nach Ergebnis und Text filtern oder auf die fehlgeschlagenen Einträge beschränken; sie liest den Ordner bei jedem Öffnen neu, zeigt höchstens 500 Zeilen (und nennt die Gesamtzahl) und ändert nichts auf dem Datenträger. Es ist dasselbe Fenster in URTC-FLASHER, URTC-TESTER und URTC-UPDATER, aus URTC-COMMON geteilt, in den acht Sprachen. Auf der Kommandozeile listet `python urtc_flasher.py --history FOLDER [--json]` die Einträge eines Ordners auf, prüft jeden und endet mit Status 1, wenn einer ungültig ist; es öffnet keinen Bus.

## ⚙️ Konfiguration

Dieses Werkzeug enthält **keinen Signierschlüssel**. Der URTC-Build signiert
jedes Anwendungs-Image und veröffentlicht die Signatur daneben, in
`<image>.manifest.json` (`hmac_sha256`, dazu `<image>.sha256`); der Flasher
sendet diese veröffentlichte Signatur und lehnt ein Image ab, dessen sha256
nicht zu seinem Manifest passt. Beim Herunterladen eines Images von GitHub
werden beide Dateien mitgeladen, und `python tools/sync_firmware.py`
aktualisiert den mitgelieferten Ordner `firmware/` aus dem URTC-Build
(`--check` prüft ihn). Standardmäßig nimmt es den Satz aus den Assets des neuesten URTC-Releases (`--release TAG` wählt ein anderes); stattdessen kann ein lokaler Ordner, etwa ein lokaler URTC-Build, als Argument übergeben werden. Nur ein selbst gebautes Image ohne Manifest auf einer
Testplatine braucht einen Schlüssel: `hmac_key_hex` / `slave_hmac_key_hex`
in `urtc_config.json` (unten) setzen - ohne ihn wird ein solches Image
abgelehnt, statt mit einem Schlüssel signiert zu werden, den der Bootloader
nicht haben kann. Siehe `docs/FIRMWARE_SIGNING.TXT` in URTC. Die veröffentlichten Images sind mit dem öffentlichen Entwicklungsschlüssel signiert (`signing_key_kind: dev`); es handelt sich also um eine Prüfung mit gemeinsamem Schlüssel: Sie zeigt, dass das Image von jemandem mit diesem Schlüssel erzeugt wurde, nicht von wem; asymmetrisches Signieren (Ed25519) ist geplant, nicht implementiert.

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
wegen eines Tippfehlers abstürzen zu lassen. **Die Überschreibungen von Speicherplan und HardwareID gelten nur für die eigenen Konstanten der Hauptplatine** (die einzige Ausnahme ist `slave_hmac_key_hex`, der Signaturschlüssel des Erweiterungs-Slaves, der hier ebenfalls gesetzt werden kann) - die eigenen Äquivalente des Erweiterungs-Slave-Chips
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

- **Eine `hardware_id` außerhalb des Bereichs.** Eine `hardware_id` über 32 Bit wird als übersprungen gemeldet, und die eingebaute HardwareID bleibt gültig, wie bei jedem anderen ungültigen Wert.

## 🚀 Schnellstart

### Bringen Sie Ihren Adapter zum CAN-Sprechen

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

### Installation und Ausführung

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

#### Visuelles Steuerpult

Das **Qt-Quick**-Steuerpult ist das einzige Fenster des Programms (nur gegen den Simulator getestet; die Image-Prüfungen nutzen ein HMAC-SHA256 mit gemeinsamem Schlüssel). Start mit:
~~~
python urtc_flasher.py
~~~
Es hat eine dunkle marineblau/cyanfarbene Oberfläche mit Verbindungskarte, gut lesbaren Firmware-Tabellen, dunklem Verifizierungsprotokoll und sichtbarem Fortschrittskanal und deckt den gesamten Ablauf ab: das CAN-OTA-Update der Hauptplatine oder des Erweiterungs-Slaves (die Zielauswahl; die Option „Platine führt die Anwendung aus“, das F-RAM-Löschen und die Downgrade-Freigabe gelten nur für die Hauptplatine), eine Sicherung der installierten Firmware über CAN, die Bitraten-Auswahl mit der Nur-Hören-Suche, den Download eines GitHub-Releases, eine Dateiauswahl für jede `.bin`, die Busaktivitätsprüfung, den Board Snapshot, die 4 Gerätekonfigurations-Schreibvorgänge, die schreibgeschützte SWD/JTAG-Erkennung und die Programmierung des kompletten Chips per SWD/JTAG (Löschen/Schreiben, Probelauf, Sicherung vor dem Löschen, RDP-Prüfung). Jede Aktion, die auf die Platine schreibt, fragt vorher nach, die Downgrade-Freigabe fragt ein zweites Mal, und das Schließen des Fensters während einer Übertragung fragt noch einmal. Nichts davon wurde an einer echten Platine erprobt. `python urtc_flasher.py --cli` ist der Headless-Modus (Abschnitt 7).

#### Kopfzeile und Werkzeuge

- **Kopfzeile** - der Verbindungsstatus, die Sprachauswahl (die Wahl wird gespeichert und gilt ab dem nächsten Start) und die Version.
- **Protokolle speichern...** und **Debug-Paket speichern** - das Bildschirmprotokoll als reiner Text bzw. ein ausführlicheres Zip mit Systemdiagnose und der gewählten Firmware-Datei (siehe „Diagnose“ unten). Jede Sitzung wird außerdem in `logs/` geschrieben; die neuesten bleiben erhalten.
- **Über URTC Flasher** - Version und Autor, mit Schaltflächen für **Readme** (in der Sprache der Oberfläche, wenn eine Übersetzung existiert), **Lizenz** und die **URTC GitHub**-Seite des Projekts.

**Sprache**: Englisch als Standard.
Wird mit der Sprachauswahl in der Kopfzeile des Fensters gewechselt - speichert sofort in `urtc_config.json` (dieselbe Datei, die für die technischen
Hardware-Überschreibungen verwendet wird — die Spracheinstellung lebt
einfach neben diesen), angewendet beim nächsten Start. Übersetzungen
leben in reinen Textdateien unter `language/` (`english.lng`,
`spanish.lng`, `italian.lng`, `french.lng`, `german.lng`, `japanese.lng`, `chinese.lng`, `portuguese.lng`) als einfache
`SCHLÜSSEL=Wert`-Paare, eines pro Zeile - Zeilen, die mit `#` beginnen,
und leere Zeilen werden ignoriert, und ein wörtliches `\n` innerhalb
eines Werts wird zu einem echten Zeilenumbruch (verwendet von der
Handvoll mehrzeiliger Dialognachrichten). Aus dem Katalog von URTC-COMMON erzeugt (eine Übersetzung wird dort korrigiert und die Dateien werden neu geschrieben, nie von Hand bearbeitet), oder als Ausgangspunkt für eine andere Sprache (fügen Sie `language/<name>.lng` hinzu, fügen Sie
`("<name>", "Eigener Name")` zu `AVAILABLE_LANGUAGES` nahe dem Anfang
von `flasher_config.py` hinzu, und setzen Sie `"language": "<name>"` in
`urtc_config.json`). Ein fehlender Schlüssel aus einer Sprachdatei fällt
darauf zurück, den Namen dieses Schlüssels selbst anzuzeigen, statt
abzustürzen, und eine fehlende oder unlesbare Sprachdatei (fehlerhafte
Bearbeitung, falscher Dateiname) fällt für die gesamte Oberfläche auf
Englisch zurück - so oder so bleibt das Tool nutzbar, während die
Unstimmigkeit behoben wird.

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

### Wohin die Firmware-Dateien gehören

**Der Ordner ist anfangs leer.** Die Firmware-Images liegen nicht in diesem Repository: Sie sind die Dateien der Releases von [URTC](https://github.com/JuanenRac/URTC). Das Fenster lädt sie aus dem gewählten Release herunter, und `python tools/sync_firmware.py` füllt den Ordner aus dem neuesten offiziellen Release (oder `--release TAG`). Jede Datei wird vor der Verwendung gegen die Release-Signatur (`.sig`, Ed25519) und ihre Prüfsummen geprüft. Solange es kein offizielles Release gibt, antwortet GitHubs „latest“ mit 404, und `firmware_release.json` nennt das stattdessen verwendete Release (heute das Bench-Pre-Release); löschen Sie die Datei oder ändern Sie ihren Tag, wenn ein offizielles veröffentlicht wird.
Dieses Tool erwartet einen `firmware/`-Ordner direkt neben
`urtc_flasher.py`, im Wurzelverzeichnis dieses Repositorys:

```
├── assets/
│   └── URTC_LOGO_FLASHER.svg      <- Banner-Quelle (Vektor)
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v<version>.bin  <- neue .bin-Dateien hier ablegen
│   ├── URTC_*  <- tools/sync_firmware.py ersetzt die URTC_*-Dateien dieses Ordners durch die eines Releases; andere Dateien bleiben
│   └── URTC_SLAVE_FIRMWARE_v<version>.bin    <- Anwendung des Erweiterungs-Slave-Chips, falls zutreffend
├── logs/                          <- automatisch erstellt, eine Datei pro Sitzung
├── urtc_config.json               <- optional, nicht standardmaessig enthalten (siehe "Den HMAC-Schluessel aendern" unten)
├── urtc_flasher.py                <- Einstiegspunkt: CLI-Argumente und Start des Qt-Quick-Fensters
├── flasher_config.py              <- Konfigurationsdatei-E/A, Sprachladen, Protokollkonstanten
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- STM32CubeProgrammer / pyOCD Wrapper
├── flasher_validation.py          <- Firmware-Dateivalidierung (.bin/.hex/.elf)
├── flasher_protocol.py            <- die CAN-OTA-Zustandsmaschine selbst, sowohl für die Hauptplatine als auch (über deren eigene I2C-Bridge weitergeleitet) den Erweiterungs-Slave
├── flasher_github.py               <- listet die Assets eines URTC-GitHub-Releases auf und lädt sie herunter
├── flasher_records.py             <- Sitzungsprotokolle (Ort, Aufbewahrung) und Update-Berichte
├── flasher_scenario.py            <- eine Aktualisierung hinter einem simulierten Bus-Szenario, mit virtueller Uhr und ihrem Nachweis
├── pytest.ini / ruff.toml          <- Einstellungen für pytest und ruff (statische Prüfungen)
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
| URTC_MAIN_FIRMWARE_v<version>.bin | 71.8 KB | ✓ sieht gültig aus |
| URTC_SLAVE_FIRMWARE_v<version>.bin | 33.9 KB | ✓ sieht gültig aus |
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
  **Von GitHub herunterladen...** listet die Dateien auf, die am neuesten
  GitHub-Release des URTC-Repositorys hängen
  (`github.com/JuanenRac/URTC/releases`; die Firmware-Binärdateien werden
  als Release-Assets veröffentlicht und nicht in git gehalten), und lässt
  Sie eine Datei zum direkten Herunterladen in Ihren eigenen lokalen
  `firmware/`-Ordner auswählen - sie erscheint dann in der obigen Liste
  wie jede andere Datei, kein Neustart nötig. Geben Sie ein Release-Tag
  (zum Beispiel `v0.3.5`) in das Feld oben im Fenster ein und drücken Sie
  **Laden**, um statt des neuesten ein anderes Release aufzulisten. Die
  `.sha256`- und `.manifest.json`-Datei des Images werden zusammen mit
  ihm heruntergeladen. Dateien werden nur von GitHubs eigenen Hosts
  akzeptiert (`github.com` und die Asset-Speicher-Hosts, auf die
  weitergeleitet wird), und eine Datei, deren Größe von der des Releases
  abweicht, wird verworfen. Verwendet die eigene öffentliche API von
  GitHub (nicht authentifiziert, daher dem Ratenlimit von 60
  Anfragen/Stunde unterworfen, falls Sie es viel in kurzer Zeit nutzen;
  eine Umgebungsvariable `GITHUB_TOKEN` hebt es an) - nichts hier
  benötigt ein GitHub-Konto.

Jede Datei eines offiziellen Releases hat eine Release-Signatur (`<Datei>.sig`, Ed25519): Der Flasher prüft sie, wenn sie vorhanden ist, und lehnt eine falsche ab. Ein Satz ohne Signaturen, etwa eine Bench-Vorabversion, wird von `tools/sync_firmware.py` nur mit `--allow-unsigned` akzeptiert.

**`<dateiname>.manifest.json` und `<dateiname>.sha256`, neben jeder
Firmware-Datei** - vom URTC-Build für jedes Image veröffentlicht (und von
GitHub zusammen damit heruntergeladen). Das Manifest enthält die Version,
den `sha256` und bei Anwendungs-Images den `hmac_sha256`-Wert, den der Bootloader erwartet (ein HMAC-SHA256 mit gemeinsamem Schlüssel, keine asymmetrische Signatur; `signing_key_kind: dev` kennzeichnet den öffentlichen Entwicklungsschlüssel):

```json
{"component": "main_application", "version": "<version>", "sha256": "b48d4cd5...", "hmac_sha256": "b63a701e...", "signing_key_kind": "dev"}
```

Beide Prüfsummen werden direkt vor dem Flashen geprüft, und eine
Abweichung **verweigert das Flashen**, bevor irgendetwas auf den Bus geht
(falsche Datei, beschädigter Download oder veraltetes Manifest). Gesendet
wird die veröffentlichte Signatur, und dem Bootloader wird die Version aus
dem Manifest gemeldet. Eine Datei ohne Manifest (ein eigener Build) wird nur
geflasht, wenn in `urtc_config.json` ein Signierschlüssel gesetzt ist -
siehe weiter unten zum Ändern des HMAC-Schlüssels.

Später einen neuen Build hinzufügen: einfach in `firmware/` ablegen und
auf **Aktualisieren** klicken - kein Neustart nötig.

<!-- urtc-section:first_flash -->
### Erster Start ohne Hardware

1. Starten Sie die virtuelle Platine: `python -m urtc_can.virtual_board`.
2. Setzen Sie in einem anderen Terminal `URTC_VIRTUAL_PORT=socket://127.0.0.1:7777` und starten Sie den Flasher: Die virtuelle Platine steht in der Portliste.
3. Wählen Sie sie, drücken Sie Verbinden, wählen Sie ein Image aus `firmware/` (oder suchen Sie eines) und drücken Sie CAN-OTA starten.
4. Die virtuelle Platine nimmt das ganze Update an, mit denselben Prüfungen von Größe, Signatur und Version wie eine echte. Sie ist ein Modell: Nichts davon lief auf einer Platine.
<!-- /urtc-section:first_flash -->

<!-- urtc-section:compatibility -->
### Voraussetzungen und Kompatibilität

Welche Versionen der URTC-Programme zusammenarbeiten und welche Protokollversion jede spricht, steht in der Kompatibilitätstabelle, die URTC-COMMON erzeugt: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md). Die Notizen einer Version der Repositories, die `tools/changelog_section.py` mitführen (die Firmware, der Flasher, der Tester und der Updater), sind der Abschnitt des CHANGELOG dieser Version, gefolgt von dieser Tabelle: `python tools/changelog_section.py VERSION --compat`.
<!-- /urtc-section:compatibility -->

## 🧪 Tests

Die Suite hat 602 Tests in 51 Dateien (`python -m pytest tests -q`; mit Qt auf einem Rechner ohne Bildschirm `QT_QPA_PLATFORM=offscreen`; die 73, die PySide6 brauchen, werden ohne übersprungen): das CAN-OTA-Protokoll gegen einen echten `MockCAN`-Transport, der einen vollständigen simulierten Bootloader abspielt (Start, Löschen, Empfang, Seitendaten und ACK, HMAC-Blöcke, End-Update mit echtem Erfolg oder einem bestimmten `VERIFY_FAIL_REASON`), die Signaturregeln, die Integritätsprüfungen des Images, die in `firmware/` mitgelieferte Firmware gegen ihre Manifeste, die mit `dry_run` gebauten SWD/JTAG-Befehle, die Sprachdateien und die Qt-Quick-Panels. Drei Skripte im Wurzelverzeichnis (`verify_qt_*.py`) steuern die Qt-Panels durchgängig an. Die CI führt außerdem `ruff check`, `python -m mypy` und `tools/ci_validate.py` aus. `MockCAN` ist nur ein aus dem Protokoll geschriebenes Modell: Es ist nachsichtiger als der echte Bootloader, ein grüner Lauf ersetzt also keinen Versuch an einer echten Platine.

## 🏗️ Build und Veröffentlichung

`build_exe.bat` / `build_exe.sh` bauen mit PyInstaller ein eigenständiges Programm (beide übergeben `--noconfirm`, ein Neubau über ein vorhandenes `dist/URTC_Flasher` ersetzt es also direkt); `build-test.sh` / `build-test.bat` prüfen alles, ohne etwas zu bauen oder eine Version zu ändern. Die Version des Programms (`FLASHER_VERSION` in `flasher_config.py`, sichtbar im Fensterbanner und in der Titelleiste) ändert sich nur durch den ausdrücklichen Schritt `python bump.py`; das Ausführen aus dem Quelltext und das Bauen berühren sie nie. Den Versionsverlauf siehe `CHANGELOG.md`.

## 📂 Struktur des Repositorys

<p align="center">
  <img src="images/repository-structure.svg" alt="Struktur des Repositorys URTC-FLASHER" width="100%">
</p>

<details>
<summary>Textversion des Baums</summary>

```text
URTC-FLASHER/
├── urtc_flasher.py                                    Einstiegspunkt
├── qt_flasher.py                                      das Qt-Quick-Deck
├── flasher_*.py                                       Protokoll, Prüfungen, Transporte, SWD, Protokolle
├── verify_qt_*.py                                     End-to-End-Prüfungen der Qt-Panels
├── urtc_can/                                          Protokoll, Transporte und Updates (Kopie)
├── urtc_ui/                                           Oberflächen-Helfer (Kopie)
├── firmware/                                          wohin die Images kommen (anfangs leer)
├── tests/                                             47 Testdateien, eine je Bereich
├── language/                                          die acht .lng-Sprachdateien
├── assets/                                            QML, Banner und Symbol
├── docs/                                              Architektur, Build und Betrieb
├── logs/                                              Sitzungsprotokolle (nicht in Git)
├── tools/                                             Build-Prüfung, Firmware-Sync, gemeinsame Werkzeuge
├── images/                                            Banner und Bilder dieses READMEs
├── .github/                                           CI-Workflow sowie Vorlagen für Issues und Pull Requests
├── test.sh test.bat                                   führen die Tests aus
├── run.sh run.bat                                     starten das Programm
├── build-test.sh build-test.bat                       Build- und Testskripte, die im Repository nichts ändern
├── urtc.project.json                                  Manifest: Version, Rolle, Reifegrad und Build-Befehl
├── CHANGELOG.md                                       was sich in jeder Version geändert hat
├── SECURITY.md SUPPORT.md LICENSE                     Sicherheitsrichtlinie, Support und Lizenz
├── CONTRIBUTING.md CODE_OF_CONDUCT.md                 wie man mitwirkt, und der Verhaltenskodex
├── .gitattributes .gitignore                          Git-Einstellungen
├── build_exe.sh build_exe.bat                         eigenständiges Programm (PyInstaller)
├── bump.py bump_version.py bump_manifest_version.py   Skripte, die die Version erhöhen
├── requirements*.txt requirements*.lock               Abhängigkeiten, mit ihren Sperren
├── mypy.ini pytest.ini ruff.toml                      Einstellungen für Typen, Tests und Lint
├── urtc_config.json.example                           Beispiel der Hardware-Einstellungen und der Sprache
├── urtc_i18n.lock.json                                Sperre der erzeugten Sprachdateien
└── NOTICE LICENSE.md                                  Urheberrechtshinweis und Dokumentationslizenz
```

</details>

Die kommentierte Liste jeder Quelldatei, eine Zeile je Datei, steht in [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## 🗺️ Roadmap und bekannte Grenzen

**Status:** die CRC32- und HMAC-SHA256-Berechnung in diesem Tool wurde
Byte für Byte gegen die eigene C-Implementierung des Bootloaders
verifiziert, und das SocketCAN-Frame-Packing wurde gegen das
`struct can_frame`-Layout von Linux mit einem Hin-und-Rück-Pack/Unpack-
Test verifiziert. Was auf keiner der 2 Plattformen getestet wurde, ist
eine echte Platine auf echter Hardware - behandeln Sie einen ersten
echten Flash-Versuch mit derselben Vorsicht, die Sie jedem neuen Tool
entgegenbringen würden, das mit einem Bootloader spricht: halten Sie
JTAG als Rückfalloption bereit. Alles Übrige hier Beschriebene wurde nur gegen `MockCAN`, einen simulierten Bootloader, erprobt, nie gegen eine echte Platine.

## 🌍 Sprachen

README und Texte gibt es auf Englisch, Spanisch, Französisch, Italienisch, Deutsch, Chinesisch, Japanisch und europäischem Portugiesisch.

## 🔗 Verwandte Projekte

URTC besteht aus unabhängigen Repositories mit jeweils eigener Version, eigenen Tests und eigenem README. Das ist die Familie, nach Gruppen:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - Firmware der Werkzeugkopf-Platine (25 Werkzeugprofile, CAN-Bootloader) und die Referenz des CAN-Protokolls.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - das CAN-Protokoll einmal als Daten geschrieben (Spezifikation, erzeugte Tabellen, Konformitätsvektoren) und der Code, den die Programme teilen.
  * **URTC-FLASHER** (dieses Repository) - Desktop-Werkzeug, das die Platinen-Firmware über CAN oder über SWD/JTAG aktualisiert.
  * [URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY) - Gateway vor dem CAN-Bus: lässt nur gelistete Kennungen durch, begrenzt ihre Rate und verlangt einen Sitzungsschlüssel.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - hardwareunabhängige C-Logik und Befehlsprotokoll für eine Werkzeugablage mit Vorheizen und Lebenszyklusverfolgung.
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - Desktop-Live-Tester für den CAN-Bus, der die Bedienelemente und die Telemetrie des von einer Platine gemeldeten Werkzeugprofils zeigt.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - Sensorrahmen-Protokoll in C und ein Python-Thermo-/RGB-Begleiter für einen Inspektions-Werkzeugkopf.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - Browser-App, die die Platine über Web Serial und SLCAN flasht und testet, ohne Installation.
* **Ecosystem Operations:**
  * [URTC-DEVTOOLS](https://github.com/JuanenRac/URTC-DEVTOOLS) - die gemeinsamen Repository-Werkzeuge der Familie als versionierter Satz, mit einer Sperrdatei, die eine bearbeitete von einer veralteten Kopie unterscheidet.
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - Architektur, Schnittstellen, Sicherheitsbasis und erzeugter Katalog des Ökosystems sowie die Werkzeuge, die alle Repositories vergleichen.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - Desktop-Werkzeug, das die Repositories der URTC-Familie erkennt, installiert und aktualisiert, jeweils eine ausdrückliche Aktion.

**Schwesterprojekte (unabhängig, mit derselben Basis und denselben Werkzeugen):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - Schwesterprojekt: das Dokumentationszentrum von HYDRA-UMC, einem unabhängigen Ökosystem, das Basis und Werkzeuge mit diesem teilt
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Schwesterprojekt: das Dokumentationszentrum von A.R.M.O.R., dem Sicherheits-Ökosystem, ebenfalls unabhängig und auf derselben Basis
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - das Profil und das Status-Dashboard aller Ökosysteme

## 📚 Dokumentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technologie-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieses Projekts.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Fehler meldet.
- **[LICENSE.md](LICENSE.md)** — die eigene Lizenz dieses Projekts.

## 🤝 Mitwirken und Community

* Führe vor einem Pull Request `URTC_CI=1 python tools/ci_validate.py` aus: es muss bestehen. Siehe [CONTRIBUTING.md](CONTRIBUTING.md) und den [Verhaltenskodex](CODE_OF_CONDUCT.md).
* Das README gibt es in acht Sprachen: Eine Textänderung wird in allen acht Dateien vorgenommen, und die mit anderen Repositorys geteilten Abschnitte schreibt `tools/readme_sections.py` von URTC-COMMON.
* Eine Änderung am CAN-Protokoll beginnt in URTC-COMMON (`spec/can_protocol.json`) und gelangt über die geprüfte Kopie in dieses Repository.
* Beschreibe nichts als auf einer Platine funktionierend, was nur gebaut wurde.
* Melde eine Schwachstelle privat: [SECURITY.md](SECURITY.md). Fragen, Ideen und Meldungen: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ

Lizenz: **GPL-3.0-or-later** für den Quellcode, **CC BY-SA 4.0** für diese
Dokumentation - siehe `LICENSE` in diesem Repository, oder den
Abschnitt „Lizenz und Urheberrechtshinweise" am Ende dieses Dokuments.

URTC Flasher ist (c) 2026 JuanenRac (Electro Hobby 3D). Dieser Hinweis
muss in jeder Verteilung dieses Projekts oder abgeleiteter Werke
enthalten sein.

Dieses Projekt besteht aus Quellcode und seiner eigenen Dokumentation,
die unter verschiedenen Lizenzen verfügbar gemacht werden - jede
passend zu dem, was sie tatsächlich abdeckt:

1. Der Quellcode (`urtc_flasher.py` und jedes `flasher_*.py`-Modul)
   und jedes daraus über `build_exe.bat`/`build_exe.sh` erstellte
   Binary sind unter der **GNU General Public License v3.0 or later (GPL-3.0-or-later)**
   verfügbar. Vollständiger Text unter
   https://www.gnu.org/licenses/gpl-3.0.html.

2. Die Dokumentation (dieses README und seine eigenen Übersetzungen -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`, `README_por.md`)
   ist unter **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)** verfügbar. Vollständiger Text unter
   https://creativecommons.org/licenses/by-sa/4.0/.

Dieses Tool ist der CAN-OTA/SWD-JTAG-Flash-Begleiter des
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
-Projekts - siehe das eigene Repository dieses Projekts für die
Platinen-Firmware, Hardware-Designs und die vollständige
Protokolldokumentation, gegen die dieses Tool implementiert. Die eigene
Firmware von URTC ist GPL-3.0-or-later und ihre Hardware-Designs sind CERN-OHL-S
v2; die eigene Lizenz dieses Tools erstreckt sich hier nicht auf dieses
separate Projekt, und umgekehrt. Eine webbasierte Alternative, die
ähnliches Terrain abdeckt, existiert ebenfalls unter
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Wenn Sie auf diesem Projekt aufbauen, denken Sie an die Lizenztrennung:
Codeänderungen sollten GPL-3.0-or-later bleiben, Dokumentationsableitungen
sollten CC BY-SA bleiben - jeweils mit Zuschreibung zurück an dieses
Projekt und seinen Autor.
