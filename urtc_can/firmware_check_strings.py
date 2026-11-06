# =============================================================================
# URTC-COMMON - src/urtc_common/firmware_check_strings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The texts of the firmware check (the images a program carries against the newest official release), in the eight languages.

The keys are the same in every language (a test holds it), the placeholders too (``{name}``, ``{local}``, ``{latest}``,
``{tag}``, ``{board}``, ``{kind}``, ``{minutes}``, ``{text}``). The codes of the languages are the ones the programs store
(``english``, ``spanish`` ...). ``error_key`` maps the stable code of a ``FirmwareCheckError`` to the key that says it.
"""
from __future__ import annotations

LANGUAGES = ("english", "spanish", "italian", "french", "german", "chinese", "japanese", "portuguese")

STRINGS: dict[str, dict[str, str]] = {
    "english": {
        "FWC_TITLE": "Firmware check",
        "FWC_NAME": "{board} - {kind}",
        "FWC_BOARD_MAIN": "main board",
        "FWC_BOARD_SLAVE": "expansion slave",
        "FWC_KIND_FIRMWARE": "application",
        "FWC_KIND_BOOTLOADER": "bootloader",
        "FWC_CURRENT": "{name}: up to date ({local}).",
        "FWC_OUTDATED": "{name}: you have {local}, the release {tag} has {latest}.",
        "FWC_AHEAD": "{name}: {local} is newer than the release ({latest}); it is not a published version.",
        "FWC_ABSENT": "{name}: the release {tag} has {latest} and you have no image for it.",
        "FWC_NOT_RELEASED": "{name}: the release {tag} has no image for it.",
        "FWC_ALL_CURRENT": "All the firmware matches the release {tag}.",
        "FWC_CACHED": "(answer kept from a check made {minutes} min ago)",
        "FWC_ERR_RATE_LIMIT": "The request limit of GitHub was reached. Try again later.",
        "FWC_ERR_NETWORK": "The release could not be read: {text}",
        "FWC_ERR_NO_RELEASE": "There is no official release to compare with.",
        "FWC_ERR_BAD_RELEASE": "The release listing cannot be used (unexpected content).",
        "FWC_ERR_TOO_SOON": "The last check failed a moment ago. Wait a minute before trying again.",
    },
    "spanish": {
        "FWC_TITLE": "Comprobación del firmware",
        "FWC_NAME": "{board} - {kind}",
        "FWC_BOARD_MAIN": "placa principal",
        "FWC_BOARD_SLAVE": "esclava de expansión",
        "FWC_KIND_FIRMWARE": "aplicación",
        "FWC_KIND_BOOTLOADER": "bootloader",
        "FWC_CURRENT": "{name}: al día ({local}).",
        "FWC_OUTDATED": "{name}: tienes la {local}, la release {tag} trae la {latest}.",
        "FWC_AHEAD": "{name}: la {local} es más nueva que la release ({latest}); no es una versión publicada.",
        "FWC_ABSENT": "{name}: la release {tag} trae la {latest} y no tienes imagen para ella.",
        "FWC_NOT_RELEASED": "{name}: la release {tag} no trae imagen para ella.",
        "FWC_ALL_CURRENT": "Todo el firmware coincide con la release {tag}.",
        "FWC_CACHED": "(respuesta guardada de una comprobación hecha hace {minutes} min)",
        "FWC_ERR_RATE_LIMIT": "Se alcanzó el límite de peticiones de GitHub. Inténtalo más tarde.",
        "FWC_ERR_NETWORK": "No se pudo leer la release: {text}",
        "FWC_ERR_NO_RELEASE": "No hay ninguna release oficial con la que comparar.",
        "FWC_ERR_BAD_RELEASE": "El listado de la release no se puede usar (contenido inesperado).",
        "FWC_ERR_TOO_SOON": "La última comprobación falló hace un momento. Espera un minuto antes de intentarlo de nuevo.",
    },
    "italian": {
        "FWC_TITLE": "Verifica del firmware",
        "FWC_NAME": "{board} - {kind}",
        "FWC_BOARD_MAIN": "scheda principale",
        "FWC_BOARD_SLAVE": "slave di espansione",
        "FWC_KIND_FIRMWARE": "applicazione",
        "FWC_KIND_BOOTLOADER": "bootloader",
        "FWC_CURRENT": "{name}: aggiornato ({local}).",
        "FWC_OUTDATED": "{name}: hai la {local}, la release {tag} ha la {latest}.",
        "FWC_AHEAD": "{name}: la {local} è più recente della release ({latest}); non è una versione pubblicata.",
        "FWC_ABSENT": "{name}: la release {tag} ha la {latest} e non hai un'immagine per essa.",
        "FWC_NOT_RELEASED": "{name}: la release {tag} non ha un'immagine per essa.",
        "FWC_ALL_CURRENT": "Tutto il firmware corrisponde alla release {tag}.",
        "FWC_CACHED": "(risposta conservata da una verifica fatta {minutes} min fa)",
        "FWC_ERR_RATE_LIMIT": "È stato raggiunto il limite di richieste di GitHub. Riprova più tardi.",
        "FWC_ERR_NETWORK": "Impossibile leggere la release: {text}",
        "FWC_ERR_NO_RELEASE": "Non esiste alcuna release ufficiale con cui confrontare.",
        "FWC_ERR_BAD_RELEASE": "L'elenco della release non è utilizzabile (contenuto inatteso).",
        "FWC_ERR_TOO_SOON": "L'ultima verifica è fallita poco fa. Attendi un minuto prima di riprovare.",
    },
    "french": {
        "FWC_TITLE": "Vérification du firmware",
        "FWC_NAME": "{board} - {kind}",
        "FWC_BOARD_MAIN": "carte principale",
        "FWC_BOARD_SLAVE": "esclave d'extension",
        "FWC_KIND_FIRMWARE": "application",
        "FWC_KIND_BOOTLOADER": "bootloader",
        "FWC_CURRENT": "{name} : à jour ({local}).",
        "FWC_OUTDATED": "{name} : vous avez la {local}, la release {tag} contient la {latest}.",
        "FWC_AHEAD": "{name} : la {local} est plus récente que la release ({latest}) ; ce n'est pas une version publiée.",
        "FWC_ABSENT": "{name} : la release {tag} contient la {latest} et vous n'avez pas d'image pour elle.",
        "FWC_NOT_RELEASED": "{name} : la release {tag} n'a pas d'image pour elle.",
        "FWC_ALL_CURRENT": "Tout le firmware correspond à la release {tag}.",
        "FWC_CACHED": "(réponse conservée d'une vérification faite il y a {minutes} min)",
        "FWC_ERR_RATE_LIMIT": "La limite de requêtes de GitHub est atteinte. Réessayez plus tard.",
        "FWC_ERR_NETWORK": "Impossible de lire la release : {text}",
        "FWC_ERR_NO_RELEASE": "Il n'existe aucune release officielle avec laquelle comparer.",
        "FWC_ERR_BAD_RELEASE": "La liste de la release est inutilisable (contenu inattendu).",
        "FWC_ERR_TOO_SOON": "La dernière vérification a échoué à l'instant. Attendez une minute avant de réessayer.",
    },
    "german": {
        "FWC_TITLE": "Firmware-Prüfung",
        "FWC_NAME": "{board} - {kind}",
        "FWC_BOARD_MAIN": "Hauptplatine",
        "FWC_BOARD_SLAVE": "Erweiterungs-Slave",
        "FWC_KIND_FIRMWARE": "Anwendung",
        "FWC_KIND_BOOTLOADER": "Bootloader",
        "FWC_CURRENT": "{name}: aktuell ({local}).",
        "FWC_OUTDATED": "{name}: Sie haben {local}, das Release {tag} enthält {latest}.",
        "FWC_AHEAD": "{name}: {local} ist neuer als das Release ({latest}); es ist keine veröffentlichte Version.",
        "FWC_ABSENT": "{name}: Das Release {tag} enthält {latest}, und Sie haben dafür kein Image.",
        "FWC_NOT_RELEASED": "{name}: Das Release {tag} enthält dafür kein Image.",
        "FWC_ALL_CURRENT": "Die gesamte Firmware entspricht dem Release {tag}.",
        "FWC_CACHED": "(Antwort einer Prüfung von vor {minutes} Min. wiederverwendet)",
        "FWC_ERR_RATE_LIMIT": "Das Anfragelimit von GitHub wurde erreicht. Versuchen Sie es später erneut.",
        "FWC_ERR_NETWORK": "Das Release konnte nicht gelesen werden: {text}",
        "FWC_ERR_NO_RELEASE": "Es gibt kein offizielles Release zum Vergleichen.",
        "FWC_ERR_BAD_RELEASE": "Die Liste des Releases ist nicht verwendbar (unerwarteter Inhalt).",
        "FWC_ERR_TOO_SOON": "Die letzte Prüfung ist soeben fehlgeschlagen. Warten Sie eine Minute, bevor Sie es erneut versuchen.",
    },
    "chinese": {
        "FWC_TITLE": "固件检查",
        "FWC_NAME": "{board} - {kind}",
        "FWC_BOARD_MAIN": "主板",
        "FWC_BOARD_SLAVE": "扩展从板",
        "FWC_KIND_FIRMWARE": "应用程序",
        "FWC_KIND_BOOTLOADER": "引导程序",
        "FWC_CURRENT": "{name}：已是最新（{local}）。",
        "FWC_OUTDATED": "{name}：你的版本是 {local}，发布版本 {tag} 的版本是 {latest}。",
        "FWC_AHEAD": "{name}：{local} 比发布版本（{latest}）更新；它不是已发布的版本。",
        "FWC_ABSENT": "{name}：发布版本 {tag} 的版本是 {latest}，而你没有对应的镜像。",
        "FWC_NOT_RELEASED": "{name}：发布版本 {tag} 没有对应的镜像。",
        "FWC_ALL_CURRENT": "所有固件都与发布版本 {tag} 一致。",
        "FWC_CACHED": "（沿用 {minutes} 分钟前检查的结果）",
        "FWC_ERR_RATE_LIMIT": "已达到 GitHub 的请求上限，请稍后再试。",
        "FWC_ERR_NETWORK": "无法读取发布版本：{text}",
        "FWC_ERR_NO_RELEASE": "没有可供比较的正式发布版本。",
        "FWC_ERR_BAD_RELEASE": "发布版本的列表无法使用（内容异常）。",
        "FWC_ERR_TOO_SOON": "上一次检查刚刚失败。请等待一分钟后再试。",
    },
    "japanese": {
        "FWC_TITLE": "ファームウェアの確認",
        "FWC_NAME": "{board} - {kind}",
        "FWC_BOARD_MAIN": "メインボード",
        "FWC_BOARD_SLAVE": "拡張スレーブ",
        "FWC_KIND_FIRMWARE": "アプリケーション",
        "FWC_KIND_BOOTLOADER": "ブートローダー",
        "FWC_CURRENT": "{name}：最新です（{local}）。",
        "FWC_OUTDATED": "{name}：お使いのバージョンは {local} で、リリース {tag} は {latest} です。",
        "FWC_AHEAD": "{name}：{local} はリリース（{latest}）より新しく、公開されたバージョンではありません。",
        "FWC_ABSENT": "{name}：リリース {tag} には {latest} があり、対応するイメージをお持ちではありません。",
        "FWC_NOT_RELEASED": "{name}：リリース {tag} には対応するイメージがありません。",
        "FWC_ALL_CURRENT": "すべてのファームウェアがリリース {tag} と一致しています。",
        "FWC_CACHED": "（{minutes} 分前の確認結果を再利用しています）",
        "FWC_ERR_RATE_LIMIT": "GitHub のリクエスト上限に達しました。しばらくしてからもう一度お試しください。",
        "FWC_ERR_NETWORK": "リリースを読み取れませんでした：{text}",
        "FWC_ERR_NO_RELEASE": "比較できる公式リリースがありません。",
        "FWC_ERR_BAD_RELEASE": "リリースの一覧を使用できません（想定外の内容です）。",
        "FWC_ERR_TOO_SOON": "直前の確認が失敗しました。1 分待ってからもう一度お試しください。",
    },
    "portuguese": {
        "FWC_TITLE": "Verificação do firmware",
        "FWC_NAME": "{board} - {kind}",
        "FWC_BOARD_MAIN": "placa principal",
        "FWC_BOARD_SLAVE": "escrava de expansão",
        "FWC_KIND_FIRMWARE": "aplicação",
        "FWC_KIND_BOOTLOADER": "bootloader",
        "FWC_CURRENT": "{name}: atualizado ({local}).",
        "FWC_OUTDATED": "{name}: tem a {local}, a release {tag} traz a {latest}.",
        "FWC_AHEAD": "{name}: a {local} é mais recente do que a release ({latest}); não é uma versão publicada.",
        "FWC_ABSENT": "{name}: a release {tag} traz a {latest} e não tem imagem para ela.",
        "FWC_NOT_RELEASED": "{name}: a release {tag} não traz imagem para ela.",
        "FWC_ALL_CURRENT": "Todo o firmware coincide com a release {tag}.",
        "FWC_CACHED": "(resposta guardada de uma verificação feita há {minutes} min)",
        "FWC_ERR_RATE_LIMIT": "Foi atingido o limite de pedidos do GitHub. Tente novamente mais tarde.",
        "FWC_ERR_NETWORK": "Não foi possível ler a release: {text}",
        "FWC_ERR_NO_RELEASE": "Não existe nenhuma release oficial com que comparar.",
        "FWC_ERR_BAD_RELEASE": "A lista da release não pode ser usada (conteúdo inesperado).",
        "FWC_ERR_TOO_SOON": "A última verificação falhou há instantes. Aguarde um minuto antes de tentar de novo.",
    },
}

_ERROR_KEYS = {
    "rate_limit": "FWC_ERR_RATE_LIMIT",
    "network": "FWC_ERR_NETWORK",
    "no_release": "FWC_ERR_NO_RELEASE",
    "bad_release": "FWC_ERR_BAD_RELEASE",
    "too_soon": "FWC_ERR_TOO_SOON",
}


def error_key(code: str) -> str:
    """The key that says the error with this code (an unknown code reads as a network failure)."""
    return _ERROR_KEYS.get(code, "FWC_ERR_NETWORK")


def text(language: str, key: str, **values: object) -> str:
    """The text of ``key`` in ``language`` (English when the language or the key is missing) with the placeholders filled."""
    table = STRINGS.get(language) or STRINGS["english"]
    template = table.get(key) or STRINGS["english"][key]
    return template.format(**values)
