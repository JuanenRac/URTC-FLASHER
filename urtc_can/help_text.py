# =============================================================================
# URTC-COMMON - src/urtc_common/help_text.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The quick guide inside the programs ("Help"): a few short steps for the flasher and for the tester, in the eight languages.

Written once here and shown by ``help_qt.HelpModel`` through ``HelpDialog.qml``; the README of each program keeps the long version. A guide is a
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
            ("Without a board", "No hardware? Run python -m urtc_can.virtual_board, set URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 and start the program: the virtual board appears in the list of ports and takes a complete update."),
            ("Updates", "Check for updates asks GitHub once. A newer package is installed only after you confirm it and only if its signature is valid; the previous version is kept so you can go back."),
        ),
        "spanish": (
            ("Conectar", "Elige el puerto serie del adaptador SLCAN (o una interfaz SocketCAN en Linux) y la velocidad, y pulsa Conectar. Autodetectar solo escucha el bus, no envía nada y encuentra la velocidad."),
            ("Elegir una imagen", "Elige la imagen de la aplicación (.bin, .hex o .elf) de la carpeta firmware, o búscala. El programa comprueba el archivo (tamaño, tabla de vectores, firma) antes de dejarte flashear; una imagen que no pasa la comprobación nunca se envía."),
            ("Flashear por CAN", "Con la placa conectada, pulsa Iniciar CAN-OTA y confirma. El programa entra en el bootloader firmado, envía la imagen y la comprueba, y la placa la copia. No desconectes el adaptador ni la alimentación mientras corre; Cancelar detiene la transferencia con seguridad."),
            ("Sin placa", "¿Sin hardware? Ejecuta python -m urtc_can.virtual_board, define URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 y arranca el programa: la placa virtual aparece en la lista de puertos y admite una actualización completa."),
            ("Actualizaciones", "Buscar actualización pregunta una vez a GitHub. Un paquete más nuevo se instala solo si lo confirmas y solo si su firma es válida; se conserva la versión anterior para poder volver."),
        ),
        "italian": (
            ("Collegare", "Scegli la porta seriale dell'adattatore SLCAN (o un'interfaccia SocketCAN su Linux) e la velocità, poi premi Connetti. Il rilevamento automatico ascolta soltanto il bus, non invia nulla e trova la velocità."),
            ("Scegliere un'immagine", "Scegli l'immagine dell'applicazione (.bin, .hex o .elf) dalla cartella firmware, oppure cercala. Il programma controlla il file (dimensione, tabella dei vettori, firma) prima di permetterti di programmare; un'immagine che non supera il controllo non viene mai inviata."),
            ("Programmare via CAN", "Con la scheda collegata, premi Avvia CAN-OTA e conferma. Il programma entra nel bootloader firmato, invia l'immagine e la controlla, e la scheda la copia. Non scollegare l'adattatore né l'alimentazione mentre è in corso; Annulla ferma il trasferimento in sicurezza."),
            ("Senza scheda", "Niente hardware? Esegui python -m urtc_can.virtual_board, imposta URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 e avvia il programma: la scheda virtuale compare nell'elenco delle porte e accetta un aggiornamento completo."),
            ("Aggiornamenti", "Cerca aggiornamenti interroga GitHub una sola volta. Un pacchetto più recente viene installato solo dopo la tua conferma e solo se la sua firma è valida; la versione precedente resta disponibile per tornare indietro."),
        ),
        "french": (
            ("Se connecter", "Choisissez le port série de l'adaptateur SLCAN (ou une interface SocketCAN sous Linux) et le débit, puis appuyez sur Connecter. La détection automatique écoute seulement le bus, n'envoie rien et trouve le débit."),
            ("Choisir une image", "Choisissez l'image de l'application (.bin, .hex ou .elf) dans le dossier firmware, ou parcourez. Le programme vérifie le fichier (taille, table des vecteurs, signature) avant de vous laisser programmer ; une image qui échoue à la vérification n'est jamais envoyée."),
            ("Programmer par CAN", "La carte étant connectée, appuyez sur Démarrer CAN-OTA et confirmez. Le programme entre dans le bootloader signé, envoie l'image et la vérifie, puis la carte la copie. Ne débranchez ni l'adaptateur ni l'alimentation pendant l'opération ; Annuler arrête le transfert en toute sécurité."),
            ("Sans carte", "Pas de matériel ? Lancez python -m urtc_can.virtual_board, définissez URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 et démarrez le programme : la carte virtuelle apparaît dans la liste des ports et accepte une mise à jour complète."),
            ("Mises à jour", "Rechercher une mise à jour interroge GitHub une seule fois. Un paquet plus récent n'est installé qu'après votre confirmation et seulement si sa signature est valide ; la version précédente est conservée pour pouvoir revenir en arrière."),
        ),
        "german": (
            ("Verbinden", "Wählen Sie den seriellen Port des SLCAN-Adapters (unter Linux auch eine SocketCAN-Schnittstelle) und die Bitrate und drücken Sie Verbinden. Die automatische Erkennung hört den Bus nur ab, sendet nichts und findet die Bitrate."),
            ("Image wählen", "Wählen Sie das Anwendungs-Image (.bin, .hex oder .elf) aus dem Ordner firmware oder suchen Sie eines. Das Programm prüft die Datei (Größe, Vektortabelle, Signatur), bevor Sie flashen dürfen; ein Image, das die Prüfung nicht besteht, wird nie gesendet."),
            ("Über CAN flashen", "Drücken Sie bei verbundener Platine CAN-OTA starten und bestätigen Sie. Das Programm wechselt in den signierten Bootloader, sendet das Image und prüft es, und die Platine kopiert es. Trennen Sie währenddessen weder Adapter noch Stromversorgung; Abbrechen stoppt die Übertragung sicher."),
            ("Ohne Platine", "Keine Hardware? Starten Sie python -m urtc_can.virtual_board, setzen Sie URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 und starten Sie das Programm: Die virtuelle Platine erscheint in der Portliste und nimmt ein vollständiges Update an."),
            ("Updates", "Nach Updates suchen fragt GitHub einmal. Ein neueres Paket wird nur nach Ihrer Bestätigung und nur bei gültiger Signatur installiert; die vorherige Version bleibt zum Zurückgehen erhalten."),
        ),
        "chinese": (
            ("连接", "选择 SLCAN 适配器的串口（Linux 上也可选 SocketCAN 接口）和波特率，然后点击连接。自动检测只监听总线，不发送任何内容，并找出波特率。"),
            ("选择镜像", "从 firmware 文件夹选择应用镜像（.bin、.hex 或 .elf），或浏览选择。程序会先检查文件（大小、向量表、签名）才允许刷写；未通过检查的镜像绝不会被发送。"),
            ("通过 CAN 刷写", "连接开发板后，点击开始 CAN-OTA 并确认。程序会进入已签名的引导程序，发送并校验镜像，由开发板完成复制。运行期间请勿拔掉适配器或断电；取消可安全地停止传输。"),
            ("没有开发板", "没有硬件？运行 python -m urtc_can.virtual_board，设置 URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 并启动程序：虚拟开发板会出现在端口列表中，并可接受完整更新。"),
            ("更新", "检查更新只会向 GitHub 查询一次。较新的包只有在您确认且签名有效时才会安装；上一版本会保留，以便退回。"),
        ),
        "japanese": (
            ("接続", "SLCAN アダプターのシリアルポート（Linux では SocketCAN インターフェースも可）とビットレートを選び、接続を押します。自動検出はバスを聞くだけで何も送信せず、ビットレートを見つけます。"),
            ("イメージを選ぶ", "firmware フォルダーからアプリケーションイメージ（.bin、.hex、.elf）を選ぶか、参照して選びます。書き込み前にプログラムがファイル（サイズ、ベクターテーブル、署名）を検査し、検査に通らないイメージは送信されません。"),
            ("CAN で書き込む", "ボードを接続した状態で CAN-OTA 開始を押して確認します。プログラムは署名付きブートローダーに入り、イメージを送って検証し、ボードがコピーします。実行中はアダプターも電源も外さないでください。キャンセルで転送を安全に止められます。"),
            ("ボードなしで", "ハードウェアがない場合は python -m urtc_can.virtual_board を実行し、URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 を設定してプログラムを起動します。仮想ボードがポート一覧に現れ、完全な更新を受け付けます。"),
            ("更新", "更新を確認は GitHub に一度だけ問い合わせます。新しいパッケージは、確認し、署名が有効な場合にだけインストールされ、前のバージョンは戻れるように残ります。"),
        ),
        "portuguese": (
            ("Ligar", "Escolha a porta série do adaptador SLCAN (ou uma interface SocketCAN no Linux) e o débito, e carregue em Ligar. A deteção automática só escuta o barramento, não envia nada e encontra o débito."),
            ("Escolher uma imagem", "Escolha a imagem da aplicação (.bin, .hex ou .elf) da pasta firmware, ou procure uma. O programa verifica o ficheiro (tamanho, tabela de vetores, assinatura) antes de o deixar gravar; uma imagem que não passa a verificação nunca é enviada."),
            ("Gravar por CAN", "Com a placa ligada, carregue em Iniciar CAN-OTA e confirme. O programa entra no bootloader assinado, envia a imagem e verifica-a, e a placa copia-a. Não desligue o adaptador nem a alimentação enquanto decorre; Cancelar pára a transferência em segurança."),
            ("Sem placa", "Sem hardware? Execute python -m urtc_can.virtual_board, defina URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 e arranque o programa: a placa virtual aparece na lista de portas e aceita uma atualização completa."),
            ("Atualizações", "Procurar atualizações pergunta uma vez ao GitHub. Um pacote mais recente só é instalado depois de o confirmar e só se a sua assinatura for válida; a versão anterior é guardada para poder voltar atrás."),
        ),
    },
    "tester": {
        "english": (
            ("Connect", "Choose the serial port of the SLCAN adapter (or a SocketCAN interface on Linux) and the bit rate, then press Connect. Listen-only mode never transmits; the active mode is needed for anything that sends."),
            ("Read and query", "Querying the version, the active tool, the F-RAM state and the thermal statistics only reads. The bus monitor shows every frame without sending; its trace can be saved as .trc or .asc."),
            ("Move or heat with care", "Anything that moves or heats needs the active mode, the profile of the tool and a second confirmation. Heaters and motors switch off if the program stops talking to them, and Stop is always one press away."),
            ("Black box and replay", "After an error, read the black box or open a saved record: the chart shows the temperature before the error. Replay plays a saved bus trace in a list of its own; it never transmits and it pauses while a board is connected."),
            ("Without a board", "No head? Run python -m urtc_can.virtual_board, set URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 and start the program: the virtual board appears in the list of ports. Check for updates asks GitHub once and installs only a signed package after you confirm it."),
        ),
        "spanish": (
            ("Conectar", "Elige el puerto serie del adaptador SLCAN (o una interfaz SocketCAN en Linux) y la velocidad, y pulsa Conectar. El modo solo escucha nunca transmite; para todo lo que envía hace falta el modo activo."),
            ("Leer y consultar", "Consultar la versión, la herramienta activa, el estado de la F-RAM y las estadísticas térmicas solo lee. El monitor del bus muestra cada trama sin enviar; su traza se puede guardar como .trc o .asc."),
            ("Mover o calentar con cuidado", "Todo lo que mueve o calienta necesita el modo activo, el perfil de la herramienta y una segunda confirmación. Los calentadores y motores se apagan si el programa deja de hablarles, y Detener siempre está a una pulsación."),
            ("Caja negra y reproducción", "Tras un error, lee la caja negra o abre un registro guardado: la gráfica muestra la temperatura antes del error. La reproducción pasa una traza del bus guardada por una lista propia; nunca transmite y se pausa mientras haya una placa conectada."),
            ("Sin placa", "¿Sin cabezal? Ejecuta python -m urtc_can.virtual_board, define URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 y arranca el programa: la placa virtual aparece en la lista de puertos. Buscar actualización pregunta una vez a GitHub e instala solo un paquete firmado tras tu confirmación."),
        ),
        "italian": (
            ("Collegare", "Scegli la porta seriale dell'adattatore SLCAN (o un'interfaccia SocketCAN su Linux) e la velocità, poi premi Connetti. La modalità solo ascolto non trasmette mai; per tutto ciò che invia serve la modalità attiva."),
            ("Leggere e interrogare", "Interrogare la versione, l'utensile attivo, lo stato della F-RAM e le statistiche termiche significa solo leggere. Il monitor del bus mostra ogni frame senza inviare; la sua traccia si può salvare come .trc o .asc."),
            ("Muovere o scaldare con cautela", "Tutto ciò che muove o scalda richiede la modalità attiva, il profilo dell'utensile e una seconda conferma. Riscaldatori e motori si spengono se il programma smette di parlare con loro, e Stop è sempre a un tocco."),
            ("Scatola nera e riproduzione", "Dopo un errore, leggi la scatola nera o apri una registrazione salvata: il grafico mostra la temperatura prima dell'errore. La riproduzione passa una traccia del bus salvata in un elenco proprio; non trasmette mai e va in pausa finché una scheda è collegata."),
            ("Senza scheda", "Niente testina? Esegui python -m urtc_can.virtual_board, imposta URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 e avvia il programma: la scheda virtuale compare nell'elenco delle porte. Cerca aggiornamenti interroga GitHub una volta e installa solo un pacchetto firmato dopo la tua conferma."),
        ),
        "french": (
            ("Se connecter", "Choisissez le port série de l'adaptateur SLCAN (ou une interface SocketCAN sous Linux) et le débit, puis appuyez sur Connecter. Le mode écoute seule ne transmet jamais ; tout ce qui envoie demande le mode actif."),
            ("Lire et interroger", "Interroger la version, l'outil actif, l'état de la F-RAM et les statistiques thermiques ne fait que lire. Le moniteur de bus montre chaque trame sans envoyer ; sa trace peut être enregistrée en .trc ou .asc."),
            ("Déplacer ou chauffer avec prudence", "Tout ce qui déplace ou chauffe demande le mode actif, le profil de l'outil et une seconde confirmation. Les chauffages et les moteurs s'éteignent si le programme cesse de leur parler, et Arrêt est toujours à un appui."),
            ("Boîte noire et relecture", "Après une erreur, lisez la boîte noire ou ouvrez un enregistrement sauvegardé : le graphique montre la température avant l'erreur. La relecture joue une trace de bus sauvegardée dans une liste à part ; elle ne transmet jamais et se met en pause tant qu'une carte est connectée."),
            ("Sans carte", "Pas de tête ? Lancez python -m urtc_can.virtual_board, définissez URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 et démarrez le programme : la carte virtuelle apparaît dans la liste des ports. Rechercher une mise à jour interroge GitHub une fois et n'installe qu'un paquet signé après votre confirmation."),
        ),
        "german": (
            ("Verbinden", "Wählen Sie den seriellen Port des SLCAN-Adapters (unter Linux auch eine SocketCAN-Schnittstelle) und die Bitrate und drücken Sie Verbinden. Der Nur-Hören-Modus sendet nie; für alles, was sendet, braucht es den aktiven Modus."),
            ("Lesen und abfragen", "Das Abfragen von Version, aktivem Werkzeug, F-RAM-Zustand und Wärmestatistik liest nur. Der Bus-Monitor zeigt jeden Frame ohne zu senden; seine Aufzeichnung lässt sich als .trc oder .asc speichern."),
            ("Mit Vorsicht bewegen oder heizen", "Alles, was bewegt oder heizt, braucht den aktiven Modus, das Profil des Werkzeugs und eine zweite Bestätigung. Heizungen und Motoren schalten ab, wenn das Programm nicht mehr mit ihnen spricht, und Stopp ist immer einen Druck entfernt."),
            ("Blackbox und Wiedergabe", "Lesen Sie nach einem Fehler die Blackbox oder öffnen Sie einen gespeicherten Datensatz: Das Diagramm zeigt die Temperatur vor dem Fehler. Die Wiedergabe spielt einen gespeicherten Bus-Trace in eine eigene Liste ein; sie sendet nie und pausiert, solange eine Platine verbunden ist."),
            ("Ohne Platine", "Kein Kopf? Starten Sie python -m urtc_can.virtual_board, setzen Sie URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 und starten Sie das Programm: Die virtuelle Platine erscheint in der Portliste. Nach Updates suchen fragt GitHub einmal und installiert nur ein signiertes Paket nach Ihrer Bestätigung."),
        ),
        "chinese": (
            ("连接", "选择 SLCAN 适配器的串口（Linux 上也可选 SocketCAN 接口）和波特率，然后点击连接。仅监听模式从不发送；凡是要发送的操作都需要主动模式。"),
            ("读取与查询", "查询版本、当前工具、F-RAM 状态和热统计只是读取。总线监视器显示每一帧而不发送；其跟踪可保存为 .trc 或 .asc。"),
            ("谨慎移动或加热", "任何会移动或加热的操作都需要主动模式、该工具的配置以及第二次确认。如果程序不再与它们通信，加热器和电机会关闭，而停止始终只需按一下。"),
            ("黑匣子与回放", "出错后，读取黑匣子或打开已保存的记录：图表显示错误发生前的温度。回放把已保存的总线跟踪放入单独的列表中；它从不发送，并在连接开发板期间暂停。"),
            ("没有开发板", "没有工具头？运行 python -m urtc_can.virtual_board，设置 URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 并启动程序：虚拟开发板会出现在端口列表中。检查更新只向 GitHub 查询一次，并且只在您确认后安装已签名的包。"),
        ),
        "japanese": (
            ("接続", "SLCAN アダプターのシリアルポート（Linux では SocketCAN インターフェースも可）とビットレートを選び、接続を押します。リッスン専用モードは決して送信しません。送信を伴う操作にはアクティブモードが必要です。"),
            ("読み取りと照会", "バージョン、アクティブなツール、F-RAM の状態、熱統計の照会は読み取りだけです。バスモニターは送信せずにすべてのフレームを表示し、そのトレースは .trc または .asc として保存できます。"),
            ("動かす・加熱するときは慎重に", "動かしたり加熱したりする操作には、アクティブモード、ツールのプロファイル、2 回目の確認が必要です。プログラムが話しかけなくなるとヒーターとモーターは切れ、停止はいつでもワンプッシュです。"),
            ("ブラックボックスとリプレイ", "エラーの後は、ブラックボックスを読み取るか保存した記録を開きます。グラフにエラー前の温度が表示されます。リプレイは保存したバストレースを専用の一覧に再生し、送信は決してせず、ボードが接続されている間は一時停止します。"),
            ("ボードなしで", "ツールヘッドがない場合は python -m urtc_can.virtual_board を実行し、URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 を設定してプログラムを起動します。仮想ボードがポート一覧に現れます。更新を確認は GitHub に一度だけ問い合わせ、確認した後に署名付きパッケージだけをインストールします。"),
        ),
        "portuguese": (
            ("Ligar", "Escolha a porta série do adaptador SLCAN (ou uma interface SocketCAN no Linux) e o débito, e carregue em Ligar. O modo só de escuta nunca transmite; para tudo o que envia é preciso o modo ativo."),
            ("Ler e consultar", "Consultar a versão, a ferramenta ativa, o estado da F-RAM e as estatísticas térmicas só lê. O monitor do barramento mostra cada trama sem enviar; o seu rastreio pode ser guardado como .trc ou .asc."),
            ("Mover ou aquecer com cuidado", "Tudo o que move ou aquece precisa do modo ativo, do perfil da ferramenta e de uma segunda confirmação. Os aquecedores e os motores desligam-se se o programa deixar de lhes falar, e Parar está sempre a um toque."),
            ("Caixa negra e reprodução", "Depois de um erro, leia a caixa negra ou abra um registo guardado: o gráfico mostra a temperatura antes do erro. A reprodução passa um rastreio do barramento guardado numa lista própria; nunca transmite e fica em pausa enquanto houver uma placa ligada."),
            ("Sem placa", "Sem cabeça? Execute python -m urtc_can.virtual_board, defina URTC_VIRTUAL_PORT=socket://127.0.0.1:7777 e arranque o programa: a placa virtual aparece na lista de portas. Procurar atualizações pergunta uma vez ao GitHub e só instala um pacote assinado depois de o confirmar."),
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
