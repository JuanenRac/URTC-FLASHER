# =============================================================================
# URTC-COMMON - src/urtc_common/help_text.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The quick guide inside the programs ("Help"): a few short steps for the flasher, the tester and the updater, in the eight languages.

Written once here (one guide for the flasher, one for the tester and one for the updater) and shown by ``help_qt.HelpModel`` through ``HelpDialog.qml``; the README of each program keeps the long version. A guide is a
list of ``(title, text)`` pairs. The same sections, in the same order, exist in every language (a test holds it), and a section never promises
more than the program does: nothing here has run on a board.
"""
from __future__ import annotations

LANGUAGES = ("english", "spanish", "italian", "french", "german", "chinese", "japanese", "portuguese")

# GUIDES[app][language] = ((title, text), ...)
GUIDES: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {
    "flasher": {
        "english": (
            ("Connect", "Choose the serial port of the SLCAN adapter (or a SocketCAN interface on Linux) and the bit rate, then press Connect. Auto-detect only listens to the bus, sends nothing and finds the bit rate."),
            ("Pick an image", "Choose the application image (.bin, .hex or .elf) from the firmware folder, or browse for one. The program checks the file (size, vector table, signature) before it lets you flash; an image that fails the check is never sent."),
            ("Flash over CAN", "With the board connected, press Start CAN-OTA and confirm. The program enters the signed bootloader, sends the image and checks it, and the board copies it. Do not unplug the adapter or the power while it runs; Cancel stops the transfer safely."),
            ("Without a board", "No hardware? Run python -m urtc_can.virtual_board, set URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 and start the program: the virtual board appears in the list of ports and takes a complete update. In the command line, --scenario FILE makes the simulated bus lose, repeat, delay or cut frames, or the node stay silent or refuse; the record then says it was a simulation."),
            ("History", "The History button next to Help lists the records of the operations that the program wrote (evidence), newest first, each one checked: one edited after it was written is shown as not valid. You can filter by result and by text. It only reads: nothing on disk is changed."),
            ("Several heads", "If more than one tool head shares the bus, open Tool heads, press Find heads and select the one to work with. The program asks you to confirm and only then sends anything to it. The multinode extension of the firmware is off by default: with it off, the bus counts as one head and everything works as before. If the selected head is lost, every head is put in its safe state (you can switch that off in the same window)."),
            ("Updates", "Check for updates asks GitHub once. A newer package is installed only after you confirm it and only if its signature is valid; the previous version is kept so you can go back."),
        ),
        "spanish": (
            ("Conectar", "Elige el puerto serie del adaptador SLCAN (o una interfaz SocketCAN en Linux) y la velocidad, y pulsa Conectar. Autodetectar solo escucha el bus, no envía nada y encuentra la velocidad."),
            ("Elegir una imagen", "Elige la imagen de la aplicación (.bin, .hex o .elf) de la carpeta firmware, o búscala. El programa comprueba el archivo (tamaño, tabla de vectores, firma) antes de dejarte flashear; una imagen que no pasa la comprobación nunca se envía."),
            ("Flashear por CAN", "Con la placa conectada, pulsa Iniciar CAN-OTA y confirma. El programa entra en el bootloader firmado, envía la imagen y la comprueba, y la placa la copia. No desconectes el adaptador ni la alimentación mientras corre; Cancelar detiene la transferencia con seguridad."),
            ("Sin placa", "¿Sin hardware? Ejecuta python -m urtc_can.virtual_board, define URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 y arranca el programa: la placa virtual aparece en la lista de puertos y admite una actualización completa. En la línea de comandos, --scenario ARCHIVO hace que el bus simulado pierda, repita, retrase o recorte tramas, o que el nodo calle o rechace; el registro dirá entonces que fue una simulación."),
            ("Historial", "El botón Historial, junto a Ayuda, lista los registros de las operaciones que escribió el programa (evidencia), el más reciente primero, cada uno comprobado: el que se editó después de escribirse aparece como no válido. Puedes filtrar por resultado y por texto. Solo lee: no se cambia nada en el disco."),
            ("Varios cabezales", "Si más de un cabezal comparte el bus, abre Cabezales, pulsa Buscar cabezales y selecciona el que quieras usar. El programa te pide confirmación y solo entonces le envía algo. La extensión multinodo del firmware viene desactivada: así, el bus cuenta como un solo cabezal y todo funciona como antes. Si se pierde el cabezal seleccionado, todos los cabezales pasan a su estado seguro (puedes desactivarlo en la misma ventana)."),
            ("Actualizaciones", "Buscar actualización pregunta una vez a GitHub. Un paquete más nuevo se instala solo si lo confirmas y solo si su firma es válida; se conserva la versión anterior para poder volver."),
        ),
        "italian": (
            ("Collegare", "Scegli la porta seriale dell'adattatore SLCAN (o un'interfaccia SocketCAN su Linux) e la velocità, poi premi Connetti. Il rilevamento automatico ascolta soltanto il bus, non invia nulla e trova la velocità."),
            ("Scegliere un'immagine", "Scegli l'immagine dell'applicazione (.bin, .hex o .elf) dalla cartella firmware, oppure cercala. Il programma controlla il file (dimensione, tabella dei vettori, firma) prima di permetterti di programmare; un'immagine che non supera il controllo non viene mai inviata."),
            ("Programmare via CAN", "Con la scheda collegata, premi Avvia CAN-OTA e conferma. Il programma entra nel bootloader firmato, invia l'immagine e la controlla, e la scheda la copia. Non scollegare l'adattatore né l'alimentazione mentre è in corso; Annulla ferma il trasferimento in sicurezza."),
            ("Senza scheda", "Niente hardware? Esegui python -m urtc_can.virtual_board, imposta URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 e avvia il programma: la scheda virtuale compare nell'elenco delle porte e accetta un aggiornamento completo. Dalla riga di comando, --scenario FILE fa perdere, ripetere, ritardare o accorciare frame al bus simulato, oppure fa tacere o rifiutare il nodo; il record dirà allora che era una simulazione."),
            ("Storico", "Il pulsante Storico, accanto a Guida, elenca i record delle operazioni scritti dal programma (evidenze), dal più recente, ciascuno controllato: uno modificato dopo la scrittura compare come non valido. Puoi filtrare per risultato e per testo. Legge soltanto: sul disco non cambia nulla."),
            ("Più teste", "Se più di una testa utensile condivide il bus, apri Teste, premi Cerca teste e seleziona quella con cui lavorare. Il programma chiede conferma e solo dopo le invia qualcosa. L'estensione multinodo del firmware è disattivata per impostazione predefinita: così il bus conta come una sola testa e tutto funziona come prima. Se la testa selezionata si perde, tutte le teste passano allo stato sicuro (puoi disattivarlo nella stessa finestra)."),
            ("Aggiornamenti", "Cerca aggiornamenti interroga GitHub una sola volta. Un pacchetto più recente viene installato solo dopo la tua conferma e solo se la sua firma è valida; la versione precedente resta disponibile per tornare indietro."),
        ),
        "french": (
            ("Se connecter", "Choisissez le port série de l'adaptateur SLCAN (ou une interface SocketCAN sous Linux) et le débit, puis appuyez sur Connecter. La détection automatique écoute seulement le bus, n'envoie rien et trouve le débit."),
            ("Choisir une image", "Choisissez l'image de l'application (.bin, .hex ou .elf) dans le dossier firmware, ou parcourez. Le programme vérifie le fichier (taille, table des vecteurs, signature) avant de vous laisser programmer ; une image qui échoue à la vérification n'est jamais envoyée."),
            ("Programmer par CAN", "La carte étant connectée, appuyez sur Démarrer CAN-OTA et confirmez. Le programme entre dans le bootloader signé, envoie l'image et la vérifie, puis la carte la copie. Ne débranchez ni l'adaptateur ni l'alimentation pendant l'opération ; Annuler arrête le transfert en toute sécurité."),
            ("Sans carte", "Pas de matériel ? Lancez python -m urtc_can.virtual_board, définissez URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 et démarrez le programme : la carte virtuelle apparaît dans la liste des ports et accepte une mise à jour complète. En ligne de commande, --scenario FICHIER fait perdre, répéter, retarder ou tronquer des trames au bus simulé, ou fait taire ou refuser le nœud ; l'enregistrement indiquera alors qu'il s'agissait d'une simulation."),
            ("Historique", "Le bouton Historique, à côté d'Aide, liste les enregistrements des opérations que le programme a écrits (preuves), du plus récent au plus ancien, chacun vérifié : celui qui a été modifié après son écriture apparaît comme non valide. Vous pouvez filtrer par résultat et par texte. Il ne fait que lire : rien n'est modifié sur le disque."),
            ("Plusieurs têtes", "Si plusieurs têtes d'outil partagent le bus, ouvrez Têtes, appuyez sur Chercher les têtes et sélectionnez celle avec laquelle travailler. Le programme demande confirmation et ne lui envoie rien avant. L'extension multinœud du firmware est désactivée par défaut : le bus compte alors comme une seule tête et tout fonctionne comme avant. Si la tête sélectionnée est perdue, toutes les têtes passent à leur état sûr (vous pouvez le désactiver dans la même fenêtre)."),
            ("Mises à jour", "Rechercher une mise à jour interroge GitHub une seule fois. Un paquet plus récent n'est installé qu'après votre confirmation et seulement si sa signature est valide ; la version précédente est conservée pour pouvoir revenir en arrière."),
        ),
        "german": (
            ("Verbinden", "Wählen Sie den seriellen Port des SLCAN-Adapters (unter Linux auch eine SocketCAN-Schnittstelle) und die Bitrate und drücken Sie Verbinden. Die automatische Erkennung hört den Bus nur ab, sendet nichts und findet die Bitrate."),
            ("Image wählen", "Wählen Sie das Anwendungs-Image (.bin, .hex oder .elf) aus dem Ordner firmware oder suchen Sie eines. Das Programm prüft die Datei (Größe, Vektortabelle, Signatur), bevor Sie flashen dürfen; ein Image, das die Prüfung nicht besteht, wird nie gesendet."),
            ("Über CAN flashen", "Drücken Sie bei verbundener Platine CAN-OTA starten und bestätigen Sie. Das Programm wechselt in den signierten Bootloader, sendet das Image und prüft es, und die Platine kopiert es. Trennen Sie währenddessen weder Adapter noch Stromversorgung; Abbrechen stoppt die Übertragung sicher."),
            ("Ohne Platine", "Keine Hardware? Starten Sie python -m urtc_can.virtual_board, setzen Sie URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 und starten Sie das Programm: Die virtuelle Platine erscheint in der Portliste und nimmt ein vollständiges Update an. In der Befehlszeile lässt --scenario DATEI den simulierten Bus Frames verlieren, wiederholen, verzögern oder verkürzen oder den Knoten schweigen oder ablehnen; der Nachweis hält dann fest, dass es eine Simulation war."),
            ("Verlauf", "Die Schaltfläche Verlauf neben Hilfe listet die Datensätze der Vorgänge auf, die das Programm geschrieben hat (Nachweise), die neuesten zuerst, jeden geprüft: ein nach dem Schreiben bearbeiteter erscheint als ungültig. Sie können nach Ergebnis und Text filtern. Es wird nur gelesen: auf dem Datenträger ändert sich nichts."),
            ("Mehrere Köpfe", "Teilen sich mehrere Werkzeugköpfe den Bus, öffnen Sie Köpfe, drücken Sie Köpfe suchen und wählen Sie den aus, mit dem Sie arbeiten. Das Programm fragt nach einer Bestätigung und sendet erst danach etwas an ihn. Die Multinode-Erweiterung der Firmware ist standardmäßig aus: Dann zählt der Bus als ein Kopf und alles funktioniert wie bisher. Geht der ausgewählte Kopf verloren, wechseln alle Köpfe in ihren sicheren Zustand (im selben Fenster abschaltbar)."),
            ("Updates", "Nach Updates suchen fragt GitHub einmal. Ein neueres Paket wird nur nach Ihrer Bestätigung und nur bei gültiger Signatur installiert; die vorherige Version bleibt zum Zurückgehen erhalten."),
        ),
        "chinese": (
            ("连接", "选择 SLCAN 适配器的串口（Linux 上也可选 SocketCAN 接口）和波特率，然后点击连接。自动检测只监听总线，不发送任何内容，并找出波特率。"),
            ("选择镜像", "从 firmware 文件夹选择应用镜像（.bin、.hex 或 .elf），或浏览选择。程序会先检查文件（大小、向量表、签名）才允许刷写；未通过检查的镜像绝不会被发送。"),
            ("通过 CAN 刷写", "连接开发板后，点击开始 CAN-OTA 并确认。程序会进入已签名的引导程序，发送并校验镜像，由开发板完成复制。运行期间请勿拔掉适配器或断电；取消可安全地停止传输。"),
            ("没有开发板", "没有硬件？运行 python -m urtc_can.virtual_board，设置 URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 并启动程序：虚拟开发板会出现在端口列表中，并可接受完整更新。 在命令行中，--scenario 文件 会让模拟总线丢失、重复、延迟或截短帧，或让节点保持沉默或拒绝；记录随后会注明这是模拟。"),
            ("历史", "帮助旁边的历史按钮按最新在前列出程序写入的操作记录（证据），并逐条检查：写入后被编辑的记录会显示为无效。可按结果和文本筛选。它只读取，不会更改磁盘上的任何内容。"),
            ("多个工具头", "如果多个工具头共用同一条总线，请打开“工具头”，按“查找工具头”，再选择要使用的那个。程序会先请您确认，之后才会向它发送任何内容。固件的多节点扩展默认关闭：关闭时总线按单个工具头处理，一切与以前相同。如果所选工具头丢失，所有工具头都会进入安全状态（可在同一窗口中关闭此行为）。"),
            ("更新", "检查更新只会向 GitHub 查询一次。较新的包只有在您确认且签名有效时才会安装；上一版本会保留，以便退回。"),
        ),
        "japanese": (
            ("接続", "SLCAN アダプターのシリアルポート（Linux では SocketCAN インターフェースも可）とビットレートを選び、接続を押します。自動検出はバスを聞くだけで何も送信せず、ビットレートを見つけます。"),
            ("イメージを選ぶ", "firmware フォルダーからアプリケーションイメージ（.bin、.hex、.elf）を選ぶか、参照して選びます。書き込み前にプログラムがファイル（サイズ、ベクターテーブル、署名）を検査し、検査に通らないイメージは送信されません。"),
            ("CAN で書き込む", "ボードを接続した状態で CAN-OTA 開始を押して確認します。プログラムは署名付きブートローダーに入り、イメージを送って検証し、ボードがコピーします。実行中はアダプターも電源も外さないでください。キャンセルで転送を安全に止められます。"),
            ("ボードなしで", "ハードウェアがない場合は python -m urtc_can.virtual_board を実行し、URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 を設定してプログラムを起動します。仮想ボードがポート一覧に現れ、完全な更新を受け付けます。 コマンドラインで --scenario ファイル を使うと、シミュレートされたバスがフレームを失ったり、繰り返したり、遅らせたり、短くしたりし、ノードが無応答になったり拒否したりします。記録にはシミュレーションだったことが記されます。"),
            ("履歴", "ヘルプの隣の履歴ボタンは、プログラムが書き込んだ操作の記録（証跡）を新しい順に一覧にし、一つずつ検査します。書き込み後に編集された記録は無効と表示されます。結果やテキストで絞り込めます。読み取りのみで、ディスクには何も書き込みません。"),
            ("複数のヘッド", "複数のツールヘッドが同じバスを共有している場合は「ヘッド」を開き、「ヘッドを探す」を押して、使うヘッドを選びます。確認を求められ、それからはじめて何かが送信されます。ファームウェアのマルチノード拡張は初期状態でオフです。オフのときバスは1つのヘッドとして扱われ、これまでどおり動作します。選択中のヘッドを見失うと、すべてのヘッドが安全状態になります（同じウィンドウでオフにできます）。"),
            ("更新", "更新を確認は GitHub に一度だけ問い合わせます。新しいパッケージは、確認し、署名が有効な場合にだけインストールされ、前のバージョンは戻れるように残ります。"),
        ),
        "portuguese": (
            ("Ligar", "Escolha a porta série do adaptador SLCAN (ou uma interface SocketCAN no Linux) e o débito, e carregue em Ligar. A deteção automática só escuta o barramento, não envia nada e encontra o débito."),
            ("Escolher uma imagem", "Escolha a imagem da aplicação (.bin, .hex ou .elf) da pasta firmware, ou procure uma. O programa verifica o ficheiro (tamanho, tabela de vetores, assinatura) antes de o deixar gravar; uma imagem que não passa a verificação nunca é enviada."),
            ("Gravar por CAN", "Com a placa ligada, carregue em Iniciar CAN-OTA e confirme. O programa entra no bootloader assinado, envia a imagem e verifica-a, e a placa copia-a. Não desligue o adaptador nem a alimentação enquanto decorre; Cancelar pára a transferência em segurança."),
            ("Sem placa", "Sem hardware? Execute python -m urtc_can.virtual_board, defina URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 e arranque o programa: a placa virtual aparece na lista de portas e aceita uma atualização completa. Na linha de comandos, --scenario FICHEIRO faz o barramento simulado perder, repetir, atrasar ou cortar tramas, ou o nó calar-se ou recusar; o registo dirá então que foi uma simulação."),
            ("Histórico", "O botão Histórico, junto de Ajuda, lista os registos das operações que o programa escreveu (evidência), do mais recente para o mais antigo, cada um verificado: o que foi editado depois de escrito aparece como não válido. Pode filtrar por resultado e por texto. Só lê: nada no disco é alterado."),
            ("Várias cabeças", "Se mais do que uma cabeça de ferramenta partilhar o barramento, abra Cabeças, prima Procurar cabeças e selecione aquela com que vai trabalhar. O programa pede confirmação e só depois lhe envia alguma coisa. A extensão multinó do firmware vem desativada por defeito: assim, o barramento conta como uma só cabeça e tudo funciona como antes. Se a cabeça selecionada se perder, todas as cabeças passam ao estado seguro (pode desativá-lo na mesma janela)."),
            ("Atualizações", "Procurar atualizações pergunta uma vez ao GitHub. Um pacote mais recente só é instalado depois de o confirmar e só se a sua assinatura for válida; a versão anterior é guardada para poder voltar atrás."),
        ),
    },
    "tester": {
        "english": (
            ("Connect", "Choose the serial port of the SLCAN adapter (or a SocketCAN interface on Linux) and the bit rate, then press Connect. Listen-only mode never transmits; the active mode is needed for anything that sends."),
            ("Read and query", "Querying the version, the active tool, the F-RAM state and the thermal statistics only reads. The bus monitor shows every frame without sending; its trace can be saved as .trc or .asc."),
            ("Move or heat with care", "Anything that moves or heats needs the active mode, the profile of the tool and a second confirmation. Heaters and motors switch off if the program stops talking to them, and Stop is always one press away."),
            ("Black box and replay", "After an error, read the black box or open a saved record: the chart shows the temperature before the error. Replay plays a saved bus trace in a list of its own; it never transmits and it pauses while a board is connected."),
            ("History", "The History button next to Help lists the records of the operations that the program wrote (evidence), newest first, each one checked: one edited after it was written is shown as not valid. You can filter by result and by text. It only reads: nothing on disk is changed."),
            ("Several heads", "If more than one tool head shares the bus, open Tool heads, press Find heads and select the one to work with. The program asks you to confirm and only then sends anything to it. The multinode extension of the firmware is off by default: with it off, the bus counts as one head and everything works as before. If the selected head is lost, every head is put in its safe state (you can switch that off in the same window)."),
            ("Without a board", "No head? Run python -m urtc_can.virtual_board, set URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 and start the program: the virtual board appears in the list of ports. Check for updates asks GitHub once and installs only a signed package after you confirm it. In the command line, --scenario FILE makes the simulated bus lose, repeat, delay or cut frames, or the node stay silent or refuse; the record then says it was a simulation."),
        ),
        "spanish": (
            ("Conectar", "Elige el puerto serie del adaptador SLCAN (o una interfaz SocketCAN en Linux) y la velocidad, y pulsa Conectar. El modo solo escucha nunca transmite; para todo lo que envía hace falta el modo activo."),
            ("Leer y consultar", "Consultar la versión, la herramienta activa, el estado de la F-RAM y las estadísticas térmicas solo lee. El monitor del bus muestra cada trama sin enviar; su traza se puede guardar como .trc o .asc."),
            ("Mover o calentar con cuidado", "Todo lo que mueve o calienta necesita el modo activo, el perfil de la herramienta y una segunda confirmación. Los calentadores y motores se apagan si el programa deja de hablarles, y Detener siempre está a una pulsación."),
            ("Caja negra y reproducción", "Tras un error, lee la caja negra o abre un registro guardado: la gráfica muestra la temperatura antes del error. La reproducción pasa una traza del bus guardada por una lista propia; nunca transmite y se pausa mientras haya una placa conectada."),
            ("Historial", "El botón Historial, junto a Ayuda, lista los registros de las operaciones que escribió el programa (evidencia), el más reciente primero, cada uno comprobado: el que se editó después de escribirse aparece como no válido. Puedes filtrar por resultado y por texto. Solo lee: no se cambia nada en el disco."),
            ("Varios cabezales", "Si más de un cabezal comparte el bus, abre Cabezales, pulsa Buscar cabezales y selecciona el que quieras usar. El programa te pide confirmación y solo entonces le envía algo. La extensión multinodo del firmware viene desactivada: así, el bus cuenta como un solo cabezal y todo funciona como antes. Si se pierde el cabezal seleccionado, todos los cabezales pasan a su estado seguro (puedes desactivarlo en la misma ventana)."),
            ("Sin placa", "¿Sin cabezal? Ejecuta python -m urtc_can.virtual_board, define URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 y arranca el programa: la placa virtual aparece en la lista de puertos. Buscar actualización pregunta una vez a GitHub e instala solo un paquete firmado tras tu confirmación. En la línea de comandos, --scenario ARCHIVO hace que el bus simulado pierda, repita, retrase o recorte tramas, o que el nodo calle o rechace; el registro dirá entonces que fue una simulación."),
        ),
        "italian": (
            ("Collegare", "Scegli la porta seriale dell'adattatore SLCAN (o un'interfaccia SocketCAN su Linux) e la velocità, poi premi Connetti. La modalità solo ascolto non trasmette mai; per tutto ciò che invia serve la modalità attiva."),
            ("Leggere e interrogare", "Interrogare la versione, l'utensile attivo, lo stato della F-RAM e le statistiche termiche significa solo leggere. Il monitor del bus mostra ogni frame senza inviare; la sua traccia si può salvare come .trc o .asc."),
            ("Muovere o scaldare con cautela", "Tutto ciò che muove o scalda richiede la modalità attiva, il profilo dell'utensile e una seconda conferma. Riscaldatori e motori si spengono se il programma smette di parlare con loro, e Stop è sempre a un tocco."),
            ("Scatola nera e riproduzione", "Dopo un errore, leggi la scatola nera o apri una registrazione salvata: il grafico mostra la temperatura prima dell'errore. La riproduzione passa una traccia del bus salvata in un elenco proprio; non trasmette mai e va in pausa finché una scheda è collegata."),
            ("Storico", "Il pulsante Storico, accanto a Guida, elenca i record delle operazioni scritti dal programma (evidenze), dal più recente, ciascuno controllato: uno modificato dopo la scrittura compare come non valido. Puoi filtrare per risultato e per testo. Legge soltanto: sul disco non cambia nulla."),
            ("Più teste", "Se più di una testa utensile condivide il bus, apri Teste, premi Cerca teste e seleziona quella con cui lavorare. Il programma chiede conferma e solo dopo le invia qualcosa. L'estensione multinodo del firmware è disattivata per impostazione predefinita: così il bus conta come una sola testa e tutto funziona come prima. Se la testa selezionata si perde, tutte le teste passano allo stato sicuro (puoi disattivarlo nella stessa finestra)."),
            ("Senza scheda", "Niente testina? Esegui python -m urtc_can.virtual_board, imposta URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 e avvia il programma: la scheda virtuale compare nell'elenco delle porte. Cerca aggiornamenti interroga GitHub una volta e installa solo un pacchetto firmato dopo la tua conferma. Dalla riga di comando, --scenario FILE fa perdere, ripetere, ritardare o accorciare frame al bus simulato, oppure fa tacere o rifiutare il nodo; il record dirà allora che era una simulazione."),
        ),
        "french": (
            ("Se connecter", "Choisissez le port série de l'adaptateur SLCAN (ou une interface SocketCAN sous Linux) et le débit, puis appuyez sur Connecter. Le mode écoute seule ne transmet jamais ; tout ce qui envoie demande le mode actif."),
            ("Lire et interroger", "Interroger la version, l'outil actif, l'état de la F-RAM et les statistiques thermiques ne fait que lire. Le moniteur de bus montre chaque trame sans envoyer ; sa trace peut être enregistrée en .trc ou .asc."),
            ("Déplacer ou chauffer avec prudence", "Tout ce qui déplace ou chauffe demande le mode actif, le profil de l'outil et une seconde confirmation. Les chauffages et les moteurs s'éteignent si le programme cesse de leur parler, et Arrêt est toujours à un appui."),
            ("Boîte noire et relecture", "Après une erreur, lisez la boîte noire ou ouvrez un enregistrement sauvegardé : le graphique montre la température avant l'erreur. La relecture joue une trace de bus sauvegardée dans une liste à part ; elle ne transmet jamais et se met en pause tant qu'une carte est connectée."),
            ("Historique", "Le bouton Historique, à côté d'Aide, liste les enregistrements des opérations que le programme a écrits (preuves), du plus récent au plus ancien, chacun vérifié : celui qui a été modifié après son écriture apparaît comme non valide. Vous pouvez filtrer par résultat et par texte. Il ne fait que lire : rien n'est modifié sur le disque."),
            ("Plusieurs têtes", "Si plusieurs têtes d'outil partagent le bus, ouvrez Têtes, appuyez sur Chercher les têtes et sélectionnez celle avec laquelle travailler. Le programme demande confirmation et ne lui envoie rien avant. L'extension multinœud du firmware est désactivée par défaut : le bus compte alors comme une seule tête et tout fonctionne comme avant. Si la tête sélectionnée est perdue, toutes les têtes passent à leur état sûr (vous pouvez le désactiver dans la même fenêtre)."),
            ("Sans carte", "Pas de tête ? Lancez python -m urtc_can.virtual_board, définissez URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 et démarrez le programme : la carte virtuelle apparaît dans la liste des ports. Rechercher une mise à jour interroge GitHub une fois et n'installe qu'un paquet signé après votre confirmation. En ligne de commande, --scenario FICHIER fait perdre, répéter, retarder ou tronquer des trames au bus simulé, ou fait taire ou refuser le nœud ; l'enregistrement indiquera alors qu'il s'agissait d'une simulation."),
        ),
        "german": (
            ("Verbinden", "Wählen Sie den seriellen Port des SLCAN-Adapters (unter Linux auch eine SocketCAN-Schnittstelle) und die Bitrate und drücken Sie Verbinden. Der Nur-Hören-Modus sendet nie; für alles, was sendet, braucht es den aktiven Modus."),
            ("Lesen und abfragen", "Das Abfragen von Version, aktivem Werkzeug, F-RAM-Zustand und Wärmestatistik liest nur. Der Bus-Monitor zeigt jeden Frame ohne zu senden; seine Aufzeichnung lässt sich als .trc oder .asc speichern."),
            ("Mit Vorsicht bewegen oder heizen", "Alles, was bewegt oder heizt, braucht den aktiven Modus, das Profil des Werkzeugs und eine zweite Bestätigung. Heizungen und Motoren schalten ab, wenn das Programm nicht mehr mit ihnen spricht, und Stopp ist immer einen Druck entfernt."),
            ("Blackbox und Wiedergabe", "Lesen Sie nach einem Fehler die Blackbox oder öffnen Sie einen gespeicherten Datensatz: Das Diagramm zeigt die Temperatur vor dem Fehler. Die Wiedergabe spielt einen gespeicherten Bus-Trace in eine eigene Liste ein; sie sendet nie und pausiert, solange eine Platine verbunden ist."),
            ("Verlauf", "Die Schaltfläche Verlauf neben Hilfe listet die Datensätze der Vorgänge auf, die das Programm geschrieben hat (Nachweise), die neuesten zuerst, jeden geprüft: ein nach dem Schreiben bearbeiteter erscheint als ungültig. Sie können nach Ergebnis und Text filtern. Es wird nur gelesen: auf dem Datenträger ändert sich nichts."),
            ("Mehrere Köpfe", "Teilen sich mehrere Werkzeugköpfe den Bus, öffnen Sie Köpfe, drücken Sie Köpfe suchen und wählen Sie den aus, mit dem Sie arbeiten. Das Programm fragt nach einer Bestätigung und sendet erst danach etwas an ihn. Die Multinode-Erweiterung der Firmware ist standardmäßig aus: Dann zählt der Bus als ein Kopf und alles funktioniert wie bisher. Geht der ausgewählte Kopf verloren, wechseln alle Köpfe in ihren sicheren Zustand (im selben Fenster abschaltbar)."),
            ("Ohne Platine", "Kein Kopf? Starten Sie python -m urtc_can.virtual_board, setzen Sie URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 und starten Sie das Programm: Die virtuelle Platine erscheint in der Portliste. Nach Updates suchen fragt GitHub einmal und installiert nur ein signiertes Paket nach Ihrer Bestätigung. In der Befehlszeile lässt --scenario DATEI den simulierten Bus Frames verlieren, wiederholen, verzögern oder verkürzen oder den Knoten schweigen oder ablehnen; der Nachweis hält dann fest, dass es eine Simulation war."),
        ),
        "chinese": (
            ("连接", "选择 SLCAN 适配器的串口（Linux 上也可选 SocketCAN 接口）和波特率，然后点击连接。仅监听模式从不发送；凡是要发送的操作都需要主动模式。"),
            ("读取与查询", "查询版本、当前工具、F-RAM 状态和热统计只是读取。总线监视器显示每一帧而不发送；其跟踪可保存为 .trc 或 .asc。"),
            ("谨慎移动或加热", "任何会移动或加热的操作都需要主动模式、该工具的配置以及第二次确认。如果程序不再与它们通信，加热器和电机会关闭，而停止始终只需按一下。"),
            ("黑匣子与回放", "出错后，读取黑匣子或打开已保存的记录：图表显示错误发生前的温度。回放把已保存的总线跟踪放入单独的列表中；它从不发送，并在连接开发板期间暂停。"),
            ("历史", "帮助旁边的历史按钮按最新在前列出程序写入的操作记录（证据），并逐条检查：写入后被编辑的记录会显示为无效。可按结果和文本筛选。它只读取，不会更改磁盘上的任何内容。"),
            ("多个工具头", "如果多个工具头共用同一条总线，请打开“工具头”，按“查找工具头”，再选择要使用的那个。程序会先请您确认，之后才会向它发送任何内容。固件的多节点扩展默认关闭：关闭时总线按单个工具头处理，一切与以前相同。如果所选工具头丢失，所有工具头都会进入安全状态（可在同一窗口中关闭此行为）。"),
            ("没有开发板", "没有工具头？运行 python -m urtc_can.virtual_board，设置 URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 并启动程序：虚拟开发板会出现在端口列表中。检查更新只向 GitHub 查询一次，并且只在您确认后安装已签名的包。 在命令行中，--scenario 文件 会让模拟总线丢失、重复、延迟或截短帧，或让节点保持沉默或拒绝；记录随后会注明这是模拟。"),
        ),
        "japanese": (
            ("接続", "SLCAN アダプターのシリアルポート（Linux では SocketCAN インターフェースも可）とビットレートを選び、接続を押します。リッスン専用モードは決して送信しません。送信を伴う操作にはアクティブモードが必要です。"),
            ("読み取りと照会", "バージョン、アクティブなツール、F-RAM の状態、熱統計の照会は読み取りだけです。バスモニターは送信せずにすべてのフレームを表示し、そのトレースは .trc または .asc として保存できます。"),
            ("動かす・加熱するときは慎重に", "動かしたり加熱したりする操作には、アクティブモード、ツールのプロファイル、2 回目の確認が必要です。プログラムが話しかけなくなるとヒーターとモーターは切れ、停止はいつでもワンプッシュです。"),
            ("ブラックボックスとリプレイ", "エラーの後は、ブラックボックスを読み取るか保存した記録を開きます。グラフにエラー前の温度が表示されます。リプレイは保存したバストレースを専用の一覧に再生し、送信は決してせず、ボードが接続されている間は一時停止します。"),
            ("履歴", "ヘルプの隣の履歴ボタンは、プログラムが書き込んだ操作の記録（証跡）を新しい順に一覧にし、一つずつ検査します。書き込み後に編集された記録は無効と表示されます。結果やテキストで絞り込めます。読み取りのみで、ディスクには何も書き込みません。"),
            ("複数のヘッド", "複数のツールヘッドが同じバスを共有している場合は「ヘッド」を開き、「ヘッドを探す」を押して、使うヘッドを選びます。確認を求められ、それからはじめて何かが送信されます。ファームウェアのマルチノード拡張は初期状態でオフです。オフのときバスは1つのヘッドとして扱われ、これまでどおり動作します。選択中のヘッドを見失うと、すべてのヘッドが安全状態になります（同じウィンドウでオフにできます）。"),
            ("ボードなしで", "ツールヘッドがない場合は python -m urtc_can.virtual_board を実行し、URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 を設定してプログラムを起動します。仮想ボードがポート一覧に現れます。更新を確認は GitHub に一度だけ問い合わせ、確認した後に署名付きパッケージだけをインストールします。 コマンドラインで --scenario ファイル を使うと、シミュレートされたバスがフレームを失ったり、繰り返したり、遅らせたり、短くしたりし、ノードが無応答になったり拒否したりします。記録にはシミュレーションだったことが記されます。"),
        ),
        "portuguese": (
            ("Ligar", "Escolha a porta série do adaptador SLCAN (ou uma interface SocketCAN no Linux) e o débito, e carregue em Ligar. O modo só de escuta nunca transmite; para tudo o que envia é preciso o modo ativo."),
            ("Ler e consultar", "Consultar a versão, a ferramenta ativa, o estado da F-RAM e as estatísticas térmicas só lê. O monitor do barramento mostra cada trama sem enviar; o seu rastreio pode ser guardado como .trc ou .asc."),
            ("Mover ou aquecer com cuidado", "Tudo o que move ou aquece precisa do modo ativo, do perfil da ferramenta e de uma segunda confirmação. Os aquecedores e os motores desligam-se se o programa deixar de lhes falar, e Parar está sempre a um toque."),
            ("Caixa negra e reprodução", "Depois de um erro, leia a caixa negra ou abra um registo guardado: o gráfico mostra a temperatura antes do erro. A reprodução passa um rastreio do barramento guardado numa lista própria; nunca transmite e fica em pausa enquanto houver uma placa ligada."),
            ("Histórico", "O botão Histórico, junto de Ajuda, lista os registos das operações que o programa escreveu (evidência), do mais recente para o mais antigo, cada um verificado: o que foi editado depois de escrito aparece como não válido. Pode filtrar por resultado e por texto. Só lê: nada no disco é alterado."),
            ("Várias cabeças", "Se mais do que uma cabeça de ferramenta partilhar o barramento, abra Cabeças, prima Procurar cabeças e selecione aquela com que vai trabalhar. O programa pede confirmação e só depois lhe envia alguma coisa. A extensão multinó do firmware vem desativada por defeito: assim, o barramento conta como uma só cabeça e tudo funciona como antes. Se a cabeça selecionada se perder, todas as cabeças passam ao estado seguro (pode desativá-lo na mesma janela)."),
            ("Sem placa", "Sem cabeça? Execute python -m urtc_can.virtual_board, defina URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 e arranque o programa: a placa virtual aparece na lista de portas. Procurar atualizações pergunta uma vez ao GitHub e só instala um pacote assinado depois de o confirmar. Na linha de comandos, --scenario FICHEIRO faz o barramento simulado perder, repetir, atrasar ou cortar tramas, ou o nó calar-se ou recusar; o registo dirá então que foi uma simulação."),
        ),
    },
    "updater": {
        "english": (
            ("The list", "The window shows every URTC program that the manifests of your workspace describe, with the version on your disk and the one on GitHub. Refresh asks GitHub again; Offline skips that and only reads your disk. Looking never changes anything."),
            ("Install or update", "Select a project and press Install selected or Update selected; Preview update shows first what would change. Every action asks you to confirm, runs the project's own build and test, and never touches more than the project you chose."),
            ("Go back", "Restore previous version puts the newest kept previous installation back. The installation in use is kept too, so the restore can be undone."),
            ("Packages", "Packages lists the signed packages of FLASHER, TESTER and this updater. Check for updates asks GitHub once; Download and verify checks the size, the SHA-256 and the signature; Install asks you first and keeps the previous version; Go back to the previous version restores it. A package that fails a check is deleted."),
            ("Security and updates", "Security holds the protections of the updater and Check for updates does the same for this program. Neither contacts the network until you ask, the signature of the key of the releases is always required, and lowering a protection asks you first."),
            ("History", "The History button in the top bar lists the install and update attempts of the workspace as records, newest first, each one checked, with filters by result and by text. It only reads: the evidence file stays as it is."),
            ("Firmware", "The Firmware button asks for a firmware image, checks its release signature and opens the installed Flasher with the image selected. A missing or wrong signature is refused with the reason. Nothing is written to a board from here: you confirm in the Flasher."),
        ),
        "spanish": (
            ("La lista", "La ventana muestra cada programa URTC que describen los manifiestos de tu espacio de trabajo, con la versión que tienes en el disco y la de GitHub. Actualizar vuelve a preguntar a GitHub; Sin conexión lo omite y solo lee tu disco. Mirar nunca cambia nada."),
            ("Instalar o actualizar", "Selecciona un proyecto y pulsa Instalar seleccionado o Actualizar seleccionado; Vista previa de la actualización muestra antes qué cambiaría. Cada acción te pide confirmar, ejecuta el build y las pruebas del propio proyecto y nunca toca más que el proyecto elegido."),
            ("Volver atrás", "Restaurar versión anterior devuelve su sitio a la instalación anterior más reciente que se conserva. La instalación en uso también se conserva, así que la restauración se puede deshacer."),
            ("Paquetes", "Paquetes lista los paquetes firmados de FLASHER, TESTER y de este actualizador. Buscar actualización pregunta una vez a GitHub; Descargar y verificar comprueba el tamaño, el SHA-256 y la firma; Instalar te pregunta antes y conserva la versión anterior; Volver a la versión anterior la restaura. Un paquete que falla una comprobación se borra."),
            ("Seguridad y actualizaciones", "Seguridad reúne las protecciones del actualizador y Buscar actualización hace lo mismo con este programa. Ninguna contacta con la red hasta que lo pidas, la firma de la clave de las versiones es siempre obligatoria y bajar una protección te lo pregunta antes."),
            ("Historial", "El botón Historial de la barra superior lista como registros los intentos de instalación y de actualización del espacio de trabajo, el más reciente primero, cada uno comprobado, con filtros por resultado y por texto. Solo lee: el archivo de evidencia no cambia."),
            ("Firmware", "El botón Firmware pide una imagen de firmware, comprueba su firma de versión y abre el Flasher instalado con la imagen seleccionada. Una firma ausente o incorrecta se rechaza con el motivo. Desde aquí no se escribe nada en ninguna placa: confirmas en el Flasher."),
        ),
        "italian": (
            ("L'elenco", "La finestra mostra ogni programma URTC descritto dai manifest del tuo spazio di lavoro, con la versione sul disco e quella su GitHub. Aggiorna interroga di nuovo GitHub; Offline lo salta e legge solo il disco. Guardare non cambia mai nulla."),
            ("Installare o aggiornare", "Seleziona un progetto e premi Installa selezionato o Aggiorna selezionato; Anteprima dell'aggiornamento mostra prima cosa cambierebbe. Ogni azione chiede conferma, esegue il build e i test del progetto stesso e non tocca mai più del progetto scelto."),
            ("Tornare indietro", "Ripristina la versione precedente rimette a posto l'installazione precedente conservata più recente. Anche l'installazione in uso viene conservata, quindi il ripristino si può annullare."),
            ("Pacchetti", "Pacchetti elenca i pacchetti firmati di FLASHER, TESTER e di questo updater. Cerca aggiornamenti interroga GitHub una sola volta; Scarica e verifica controlla dimensione, SHA-256 e firma; Installa chiede prima conferma e conserva la versione precedente; Torna alla versione precedente la ripristina. Un pacchetto che non supera un controllo viene eliminato."),
            ("Sicurezza e aggiornamenti", "Sicurezza raccoglie le protezioni dell'updater e Cerca aggiornamenti fa lo stesso per questo programma. Nessuna contatta la rete finché non lo chiedi, la firma con la chiave delle versioni è sempre obbligatoria e abbassare una protezione chiede prima conferma."),
            ("Storico", "Il pulsante Storico nella barra in alto elenca come record i tentativi di installazione e aggiornamento dell'area di lavoro, dal più recente, ciascuno controllato, con filtri per risultato e per testo. Legge soltanto: il file di evidenza resta com'è."),
            ("Firmware", "Il pulsante Firmware chiede un'immagine firmware, controlla la sua firma di rilascio e apre il Flasher installato con l'immagine selezionata. Una firma mancante o errata viene rifiutata con il motivo. Da qui non si scrive nulla su una scheda: confermi nel Flasher."),
        ),
        "french": (
            ("La liste", "La fenêtre montre chaque programme URTC décrit par les manifestes de votre espace de travail, avec la version sur votre disque et celle de GitHub. Actualiser interroge de nouveau GitHub ; Hors ligne l'ignore et ne lit que votre disque. Regarder ne change jamais rien."),
            ("Installer ou mettre à jour", "Sélectionnez un projet et appuyez sur Installer la sélection ou Mettre à jour la sélection ; Aperçu de la mise à jour montre d'abord ce qui changerait. Chaque action demande une confirmation, lance le build et les tests du projet lui-même et ne touche jamais plus que le projet choisi."),
            ("Revenir en arrière", "Restaurer la version précédente remet en place l'installation précédente conservée la plus récente. L'installation en cours est conservée aussi : la restauration peut donc être annulée."),
            ("Paquets", "Paquets liste les paquets signés de FLASHER, TESTER et de cet outil de mise à jour. Rechercher une mise à jour interroge GitHub une seule fois ; Télécharger et vérifier contrôle la taille, le SHA-256 et la signature ; Installer demande d'abord confirmation et conserve la version précédente ; Revenir à la version précédente la restaure. Un paquet qui échoue à un contrôle est supprimé."),
            ("Sécurité et mises à jour", "Sécurité regroupe les protections de l'outil et Rechercher une mise à jour fait de même pour ce programme. Aucune ne contacte le réseau avant que vous le demandiez, la signature de la clé des versions est toujours exigée et abaisser une protection demande d'abord confirmation."),
            ("Historique", "Le bouton Historique de la barre du haut liste comme enregistrements les tentatives d'installation et de mise à jour de l'espace de travail, du plus récent au plus ancien, chacun vérifié, avec des filtres par résultat et par texte. Il ne fait que lire : le fichier de preuve reste tel quel."),
            ("Firmware", "Le bouton Firmware demande une image de firmware, vérifie sa signature de version et ouvre le Flasher installé avec l'image sélectionnée. Une signature absente ou fausse est refusée avec le motif. Rien n'est écrit sur une carte depuis ici : vous confirmez dans le Flasher."),
        ),
        "german": (
            ("Die Liste", "Das Fenster zeigt jedes URTC-Programm, das die Manifeste Ihres Arbeitsbereichs beschreiben, mit der Version auf Ihrer Platte und der auf GitHub. Aktualisieren fragt GitHub erneut; Offline überspringt das und liest nur Ihre Platte. Ansehen ändert nie etwas."),
            ("Installieren oder aktualisieren", "Wählen Sie ein Projekt und drücken Sie Auswahl installieren oder Auswahl aktualisieren; Vorschau des Updates zeigt vorher, was sich ändern würde. Jede Aktion verlangt eine Bestätigung, führt Build und Tests des Projekts selbst aus und berührt nie mehr als das gewählte Projekt."),
            ("Zurückgehen", "Vorherige Version wiederherstellen stellt die jüngste aufbewahrte frühere Installation wieder her. Die genutzte Installation bleibt ebenfalls erhalten, die Wiederherstellung lässt sich also rückgängig machen."),
            ("Pakete", "Pakete listet die signierten Pakete von FLASHER, TESTER und diesem Updater. Nach Updates suchen fragt GitHub einmal; Herunterladen und prüfen kontrolliert Größe, SHA-256 und Signatur; Installieren fragt vorher und behält die vorherige Version; Zur vorherigen Version zurückkehren stellt sie wieder her. Ein Paket, das eine Prüfung nicht besteht, wird gelöscht."),
            ("Sicherheit und Updates", "Sicherheit fasst die Schutzfunktionen des Updaters zusammen, Nach Updates suchen tut dasselbe für dieses Programm. Keines greift auf das Netz zu, bevor Sie es verlangen, die Signatur mit dem Schlüssel der Versionen ist immer Pflicht und das Senken eines Schutzes fragt vorher nach."),
            ("Verlauf", "Die Schaltfläche Verlauf in der oberen Leiste listet die Installations- und Update-Versuche des Arbeitsbereichs als Datensätze auf, die neuesten zuerst, jeden geprüft, mit Filtern nach Ergebnis und Text. Es wird nur gelesen: die Nachweisdatei bleibt unverändert."),
            ("Firmware", "Die Schaltfläche Firmware fragt nach einem Firmware-Image, prüft dessen Release-Signatur und öffnet den installierten Flasher mit dem ausgewählten Image. Eine fehlende oder falsche Signatur wird mit Begründung abgelehnt. Von hier aus wird nichts auf eine Platine geschrieben: Sie bestätigen im Flasher."),
        ),
        "chinese": (
            ("列表", "窗口显示工作区清单所描述的每个 URTC 程序，以及磁盘上的版本和 GitHub 上的版本。刷新会再次询问 GitHub；离线会跳过这一步，只读取磁盘。查看永远不会改变任何东西。"),
            ("安装或更新", "选择一个项目，按安装所选项或更新所选项；更新预览会先显示将发生的变化。每个操作都会请你确认，运行该项目自己的构建和测试，并且绝不会触及你所选项目之外的内容。"),
            ("退回", "恢复上一个版本会把保留的最近一次旧安装放回原位。正在使用的安装也会保留，因此这次恢复可以撤销。"),
            ("软件包", "软件包列出 FLASHER、TESTER 和本更新器的已签名软件包。检查更新只询问 GitHub 一次；下载并验证会检查大小、SHA-256 和签名；安装会先征求你的同意并保留上一个版本；退回上一版本会恢复它。未通过任何检查的软件包会被删除。"),
            ("安全与更新", "安全集中了更新器的各项保护，检查更新对本程序也是如此。两者都要等你提出请求才会联网，必须始终带有发布密钥的签名，降低任何保护都会先询问你。"),
            ("历史", "顶部栏的历史按钮把工作区的安装和更新尝试作为记录按最新在前列出，并逐条检查，可按结果和文本筛选。它只读取，证据文件保持不变。"),
            ("固件", "固件按钮会询问固件镜像，检查其发布签名，并在选中该镜像的情况下打开已安装的 Flasher。签名缺失或错误会连同原因一起被拒绝。从这里不会向开发板写入任何内容：您在 Flasher 中确认。"),
        ),
        "japanese": (
            ("一覧", "ワークスペースのマニフェストが記述するすべての URTC プログラムを、ディスク上のバージョンと GitHub のバージョンとともに表示します。更新は GitHub にもう一度問い合わせ、オフラインはそれを省いてディスクだけを読みます。見るだけでは何も変わりません。"),
            ("インストールと更新", "プロジェクトを選んで選択項目をインストールまたは選択項目を更新を押します。更新のプレビューは、何が変わるかを先に示します。どの操作も確認を求め、そのプロジェクト自身のビルドとテストを実行し、選んだプロジェクト以外には触れません。"),
            ("元に戻す", "前のバージョンに戻すは、保存されている直前の旧インストールのうち最新のものを元の場所に戻します。使用中のインストールも保存されるので、この復元は取り消せます。"),
            ("パッケージ", "パッケージは FLASHER、TESTER、およびこの更新ツールの署名付きパッケージを一覧にします。更新を確認は GitHub に一度だけ問い合わせ、ダウンロードして検証はサイズ、SHA-256、署名を調べ、インストールは先に確認を求めて前のバージョンを残し、前のバージョンに戻すはそれを復元します。検査に通らないパッケージは削除されます。"),
            ("セキュリティと更新", "セキュリティは更新ツールの保護をまとめ、更新を確認はこのプログラムについて同じことをします。どちらも要求するまでネットワークに接続せず、リリース鍵による署名は常に必須で、保護を下げるときは先に確認します。"),
            ("履歴", "上部バーの履歴ボタンは、ワークスペースのインストールと更新の試行を記録として新しい順に一覧にし、一つずつ検査します。結果やテキストで絞り込めます。読み取りのみで、証跡ファイルは変更されません。"),
            ("ファームウェア", "Firmware ボタンはファームウェアイメージを尋ね、そのリリース署名を検査して、イメージを選択した状態でインストール済みの Flasher を開きます。署名がない、または誤っている場合は理由とともに拒否されます。ここからボードには何も書き込まれず、確認は Flasher で行います。"),
        ),
        "portuguese": (
            ("A lista", "A janela mostra cada programa URTC que os manifestos do seu espaço de trabalho descrevem, com a versão que tem no disco e a do GitHub. Atualizar volta a perguntar ao GitHub; Offline ignora isso e só lê o seu disco. Olhar nunca altera nada."),
            ("Instalar ou atualizar", "Selecione um projeto e carregue em Instalar selecionado ou Atualizar selecionado; Pré-visualizar a atualização mostra primeiro o que mudaria. Cada ação pede-lhe confirmação, executa o build e os testes do próprio projeto e nunca toca em mais do que o projeto escolhido."),
            ("Voltar atrás", "Restaurar a versão anterior repõe a instalação anterior guardada mais recente. A instalação em uso também é guardada, por isso a reposição pode ser desfeita."),
            ("Pacotes", "Pacotes lista os pacotes assinados do FLASHER, do TESTER e deste atualizador. Procurar atualizações pergunta uma vez ao GitHub; Transferir e verificar confere o tamanho, o SHA-256 e a assinatura; Instalar pergunta-lhe primeiro e guarda a versão anterior; Voltar à versão anterior repõe-na. Um pacote que falhe uma verificação é apagado."),
            ("Segurança e atualizações", "Segurança reúne as proteções do atualizador e Procurar atualizações faz o mesmo para este programa. Nenhuma contacta a rede até o pedir, a assinatura da chave das versões é sempre obrigatória e baixar uma proteção pergunta-lhe primeiro."),
            ("Histórico", "O botão Histórico da barra superior lista como registos as tentativas de instalação e de atualização da área de trabalho, do mais recente para o mais antigo, cada um verificado, com filtros por resultado e por texto. Só lê: o ficheiro de evidência mantém-se como está."),
            ("Firmware", "O botão Firmware pede uma imagem de firmware, verifica a sua assinatura de versão e abre o Flasher instalado com a imagem selecionada. Uma assinatura em falta ou errada é recusada com o motivo. Daqui não se escreve nada numa placa: confirma no Flasher."),
        ),
    },
}

TITLES = {
    "english": "Help", "spanish": "Ayuda", "italian": "Aiuto", "french": "Aide",
    "german": "Hilfe", "chinese": "帮助", "japanese": "ヘルプ", "portuguese": "Ajuda",
}


def guide(app: str, language: str) -> tuple[tuple[str, str], ...]:
    """The sections of the guide of a program in a language (English when the language is not one of the eight); an unknown program has none."""
    sections = GUIDES.get(app)
    if sections is None:
        return ()
    return sections.get(language) or sections["english"]


def title(language: str) -> str:
    return TITLES.get(language) or TITLES["english"]
