<p align="center">
  <img src="/images/URTC_FLASHER_BANNER.svg" alt="URTC Flasher Logo" width="100%">
</p>

# URTC Flasher (Windows / Linux)

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  🇪🇸 <b>Español</b> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Actualiza el firmware de una placa URTC por CAN (CAN-OTA) y programa el chip completo por SWD/JTAG, en Windows y Linux

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Lenguaje-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Tests-500-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Protocolo-CAN--OTA-orange.svg" alt="CAN-OTA">
</p>

---

**Comprobación de honestidad - lo que realmente funciona hoy:** `tests/` contiene 47 archivos de pytest (500 tests: todos pasan; 79 de ellos se omiten sin PySide6) - el protocolo CAN-OTA contra un transporte `MockCAN` real (`flasher_transports.py`) que reproduce una secuencia completa de bootloader simulado (inicio/borrado/recepción, datos de página + PAGE_ACK, trozos HMAC, fin de actualización con un éxito real o un `VERIFY_FAIL_REASON` concreto), las reglas de firma (firma publicada enviada sin ninguna clave, imagen sin firmar rechazada, sha256 del manifiesto que no coincide rechazado antes de cualquier tráfico en el bus), las comprobaciones de integridad de imagen y la carpeta `firmware/` incluida contra sus manifiestos. GitHub Actions (`.github/workflows/ci.yml`) ejecuta esta suite en cada push, y `tools/build_test.py` la ejecuta en `build-test.sh`/`.bat`. También ejecuta `ruff check` y `python -m mypy` (una comprobación de tipos del programa y de las copias del código compartido). Los tres scripts `verify_qt_*.py` de la raíz son comprobaciones de extremo a extremo reales fuera de pytest (necesitan un bucle de eventos Qt real; se ejecutan con `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`); `verify_qt_swd_full_chip_flash.py` solo construye los comandos de `PyOCDCLI`/`CubeProgrammerCLI` con `dry_run=True`. Nada de esto se ha probado contra una placa real en este entorno. Ver `CHANGELOG.md` para saber exactamente qué se ha publicado. El bootloader simulado (`MockCAN`) es solo un modelo escrito a partir de la descripción del protocolo: reproduce los ACK de página, la última página parcial y las tramas de lectura, pero no es el bootloader real, así que una pasada de tests en verde no sustituye una prueba en una placa real (la imagen oficial de 73476 bytes no se podía instalar y la última trama de una copia se perdía mientras los tests pasaban, justamente porque la simulación era más permisiva que el bootloader real).

---

> **Estado de seguridad física y de ciberseguridad:** este ecosistema no es un sistema de seguridad certificado y todavía no existe ninguna placa URTC poblada. Los bootloaders comprueban las imágenes de firmware con CRC32 y un HMAC-SHA256 de clave compartida, no con una firma asimétrica (prevista); las imágenes de aplicación publicadas están firmadas con la clave pública de desarrollo (`signing_key_kind: dev`), así que cualquiera puede producir una imagen que el bootloader acepte; no se ha transmitido nada a una placa real. Lee la [línea base de seguridad](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) y el [modelo de amenazas](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de fiarte de cualquier afirmación de aquí para la seguridad de una persona.

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.4.2` |
| Madurez | Funcional |
| Tests | 500 (`python -m pytest tests -q`) |
| Tecnología | Python / PySide6 / Qt Quick / CAN-OTA / SWD/JTAG |
| Destino | El PC de quien lo usa |
| En hardware real | Solo simulado: probado con emuladores, dobles de prueba o simuladores; no consta ninguna ejecución en hardware real para esta versión |

**Ir a:** [Resumen](#-resumen) · [Arquitectura](#-arquitectura) · [Funciones](#-funciones) · [Seguridad](#-seguridad-y-protección) · [Interfaces](#-interfaces) · [Configuración](#-configuración) · [Inicio rápido](#-inicio-rápido) · [Pruebas](#-pruebas) · [Estructura](#-estructura-del-repositorio) · [Relacionados](#-proyectos-relacionados)

<!-- urtc-section:status_flasher -->
## 🚦 Estado del proyecto

🟢 hecho y verificado · 🟡 funciona, con límites conocidos · 🟠 a medias o sin verificar · 🔴 sin hacer o sin funcionar. Nada es verde si nunca corrió en hardware real.

| Parte | Estado | Lo que el repositorio puede demostrar |
| --- | :---: | --- |
| Software | 🟡 | Funciona en un PC y contra el simulador; nunca se ha usado con una placa real. |
| Interfaz | 🟡 | La ventana funciona y se comprueba contra una placa simulada; no se ha probado con un adaptador real. |
| Pruebas | 🟢 | La batería de pruebas pasa en la CI en cada subida. |
| Hardware real | 🟠 | Aún no se ha ejecutado con una placa real: la prueba de banco sigue pendiente. |
| Seguridad | 🟡 | Las versiones se firman con Ed25519 y se comprueban antes de usarlas; el manejo de las claves no lo ha revisado nadie más. |
| Documentación | 🟡 | README en ocho idiomas y documentos de referencia; las traducciones no las ha revisado ningún hablante nativo. |

<!-- /urtc-section:status_flasher -->

## 🎯 Resumen

Una pequeña herramienta GUI multiplataforma para actualizar el firmware
de la placa URTC por bus CAN. Implementa exactamente el protocolo del
bootloader de `docs/CANBUS.TXT` (en el repositorio hermano [URTC](https://github.com/JuanenRac/URTC) contra el que implementa esta herramienta - ver «Proyectos Relacionados» cerca del final de este documento; cualquier otra referencia a `docs/*.TXT` en este README apunta allí también): la verificación de HardwareID, el HMAC-SHA256 de clave compartida (no una firma asimétrica), el flujo de actualización con slot de respaldo de imagen
dorada, el progreso en vivo mediante los mensajes de latido del
bootloader, y una consulta de versión (identifica si la aplicación *o*
el bootloader de esta placa se anuncia por CAN) para que puedas ver qué
hay instalado actualmente antes de decidir qué flashear.

**Buscar actualización.** El botón «Buscar actualización» pregunta una vez a GitHub por la última release y solo ofrece descargarla si trae un paquete para este sistema más nuevo que la versión instalada. El paquete solo se acepta si su SHA-256 y su firma Ed25519 (la clave de las releases, fijada en el programa) son válidos; se instala únicamente tras tu confirmación, nunca mientras hay una transferencia en marcha, y se conserva la versión anterior para poder volver (y se restaura sola si la nueva no arranca). Nada se comprueba ni se instala por su cuenta: la comprobación al abrir es una opción, apagada por defecto, y la confirmación solo se desactiva en la misma ventana tras un aviso.

Dos formas de hablar con la placa, ambas usando el mismo protocolo por
debajo:

- **Serie / SLCAN** — funciona en Windows y Linux. Necesita un adaptador
  USB-CAN con firmware SLCAN, conectado como puerto serie virtual.
  - Sin adaptador ni hardware, una placa virtual hace su papel: ejecuta `python -m urtc_can.virtual_board`, indica su dirección en la variable de entorno `URTC_VIRTUAL_PORT` (por ejemplo `socket://127.0.0.1:7777`) antes de iniciar el programa, o pásala a `--port` en la línea de comandos. Aparece en la lista de puertos y responde como una placa, aplicación y bootloader.
- **SocketCAN** — **solo Linux**, y solo se muestra en la interfaz de la
  herramienta en Linux. Habla directamente con una interfaz de red del
  kernel `can0`/`slcan0`. Si tu adaptador ya ejecuta firmware
  `gs_usb`/candleLight (la mayoría de las placas CANable lo hacen de
  fábrica), esta ruta **no necesita reflashear el adaptador en
  absoluto** — el propio driver de Linux lo gestiona de forma nativa.

## 🧩 Papel en URTC

URTC-FLASHER es el programa que pone firmware en una placa URTC. Habla el protocolo del bootloader de URTC (`docs/CANBUS.TXT` de ese repositorio) a través de un adaptador USB-CAN, como puerto serie SLCAN o como SocketCAN en Linux: la comprobación del HardwareID, fragmentos con HMAC-SHA256 de clave compartida, el flujo de imagen dorada con ranura de respaldo y una consulta de versión para que veas lo que hay instalado antes de decidir qué flashear. Para una placa sin bootloader que funcione, o para programar el chip completo, prepara los comandos SWD/JTAG de pyOCD o STM32CubeProgrammer. Es el compañero de actualización de URTC-TESTER, comparte con él su código CAN a través de URTC-COMMON, y URTC-UPDATER puede entregarle una imagen de firmware cuya firma de release ya se comprobó.

## 🏛️ Arquitectura

<p align="center">
  <img src="images/architecture.svg" alt="Arquitectura de URTC-FLASHER: quién lo usa, qué contiene y de qué depende" width="100%">
</p>

Cómo encajan las partes de este repositorio: quién lo usa, qué contiene y de qué depende. La imagen se dibuja desde `docs/architecture.json` y se comprueba contra el código.

<!-- urtc-section:updates -->
### Cómo se actualiza

Este programa puede buscar una versión más nueva de sí mismo: el botón «Buscar actualización» pregunta una vez a GitHub y ofrece un paquete firmado solo si es para tu sistema y más nuevo. Nada se comprueba ni se instala por su cuenta salvo que actives la comprobación, y una actualización necesita tu confirmación. El paquete debe coincidir con su SHA-256 y con la firma de la clave de las releases fijada en el programa; la versión anterior se conserva y se restaura sola si la nueva no arranca. `urtc-updater --cli package list|check|install|rollback` hace lo mismo desde la línea de órdenes para el flasher y el tester, y `install --file` funciona sin red.
<!-- /urtc-section:updates -->

## 🖼️ Capturas de pantalla

<p align="center">
  <img src="images/URTC_FLASHER_V1_1.png" alt="Ventana de URTC Flasher" width="700">
</p>

Estas imágenes son la ventana real, dibujada sin pantalla tal como se abre (nada conectado, nada enviado). La guía recorre el panel, la ventana de Ayuda y la de actualización.

![La ventana, paso a paso](docs/screenshots/flasher-deck.png)

[Guía con imágenes](docs/WINDOW_GUIDE.md)

## ✨ Funciones

### Comprobar qué hay instalado actualmente

> En el panel Qt Quick los puertos de ambos transportes (adaptadores serie y, en Linux, interfaces SocketCAN) están en una sola lista, y las consultas de esta sección las hace **LEER ESTADO DE PLACA**, que pide de una vez la versión, los contadores de error CAN, el tipo de placa de expansión, la variante MLX9064x y la información del periférico y los muestra en la instantánea de la placa. Los guardados de la sección de configuración del dispositivo escriben los valores.
Si estás en Linux y SocketCAN está disponible, verás una opción de
**Transporte** en la parte superior - elige Serie/SLCAN o SocketCAN
antes de conectar. En Windows esta fila no aparece en absoluto;
Serie/SLCAN es la única opción.

Haz clic en **Conectar**, y la herramienta le pregunta automáticamente a
la placa qué está ejecutando actualmente (CAN ID `0x7F8` → `0x7F9` - ver
`docs/CANBUS.TXT`). Esto funciona tanto si la placa está ejecutando su
aplicación normalmente *como* si está en el bootloader, así que no
necesitas provocar un reinicio solo para averiguarlo. Haz clic en
**Consultar** en cualquier momento después para volver a comprobar (útil
justo después de que termine un flasheo, para confirmar que la versión
nueva realmente se aplicó).

**Cuando el propio bootloader responde** (la placa está en el
bootloader, sin ejecutar su aplicación), también informa de su propia
versión - algo separado de la versión de la aplicación instalada,
controlada mediante su propio `BOOTLOADER_VERSION_MAJOR/MINOR/PATCH` en
`bootloader_common.h` y enviada como una segunda trama (`0x7FA`) justo junto a
`0x7F9`. La aplicación en ejecución nunca envía esto - no tiene forma de
saber la versión de un bootloader actualmente flasheado salvo
preguntándole al propio bootloader, así que esto solo aparece cuando la
placa realmente está ahí sentada (justo después de `0x7F0`, o en un
arranque nuevo antes de saltar a la aplicación).

**El número de parche.** Una placa con firmware 0.3.5 o posterior envía
además el número de parche de la aplicación instalada (trama `0x7E9`,
justo después de `0x7F9`), así que la ventana y el registro muestran el
`mayor.menor.parche` completo (por ejemplo `v0.3.5`) en lugar de
`mayor.menor`; el parche de una imagen es la tercera parte de la versión
de su manifiesto. Antes de una actualización el registro muestra
`instalada -> nueva` con ese formato, y el parche solo interviene en el
aviso de "más antigua que la instalada" cuando ambos lados lo tienen. Una
placa anterior al parche responde sin él y se muestra exactamente como
antes. Cuando el bootloader anuncia (indicador en la misma trama) que lee
el parche, la trama de fin de actualización lo lleva en el byte alto del
campo menor; cualquier otro bootloader, y cualquier imagen sin parche,
reciben la trama de dos números sin cambios. La respuesta de versión del
esclavo de expansión (`0x218`) tiene la misma extensión opcional. Esto
sigue la descripción del protocolo y solo se ha probado con el simulador;
no se ha probado en una placa real.

Lo que verás:

- **`v0.2 (application, HardwareID 0x0303CC01)`** - caso normal,
  aplicación en ejecución, todo coincide.
- **`Bootloader running, no valid firmware currently installed,
  bootloader v0.1.2`** - la placa está atascada en el bootloader sin
  nada a lo que saltar (chip en blanco, o cada comprobación en el slot
  principal falló). Esta es exactamente la situación para la que existe
  esta herramienta - flashéalo. La versión de bootloader mostrada aquí
  es la del propio bootloader, sin relación con la versión de aplicación
  que haya fallado sus comprobaciones.
- **`⚠ HardwareID mismatch!`** mostrado en rojo - algo respondió, pero
  su HardwareID no coincide con lo que espera esta herramienta. No
  flashees sin entender por qué primero; el bootloader rechazaría la
  actualización de todas formas, pero un desajuste aquí también puede
  significar que apuntas a la placa equivocada por completo.
- **Sin respuesta** (rojo) - placa no responde, bitrate equivocado, o no
  está realmente conectada. Revisa la conexión física y, en la ruta
  SocketCAN, que la interfaz realmente esté activa (`ip link show`).

**Placa de expansión:** un desplegable separado y un par
Consultar/Guardar, justo debajo de la comprobación de versión. Lee y
establece cuál de las 7 configuraciones posibles de `CONN_EXPANSION`
(ninguna, o una de las 6 variantes reales - ver `EXPANSION.TXT`)
está instalada físicamente, por CAN (`0x1A0`/`0x1A1`). No hay forma
eléctrica de que la placa detecte esto por sí misma, así que hay que
decírselo - esto vive aquí (no solo en `URTC Tester`) ya que es un paso
de configuración de hardware de una sola vez que se hace de forma más
natural junto con una actualización de firmware. **Guardar** pide
confirmación primero, ya que esto persiste entre ciclos de encendido
hasta que se cambie explícitamente de nuevo.

**Variante de sensor MLX9064x:** misma forma que el control de placa de
expansión de arriba - un desplegable y un par Consultar/Guardar que
lee/establece cuál de los 3 sensores térmicos de la familia MLX9064x (o
ninguno) está realmente instalado, por CAN (`0x1A6`/`0x1A7` - ver
`CANBUS.TXT`). Solo relevante cuando la placa de expansión de arriba
está configurada como una variante Advanced o Basic+MLX9064x; el propio
firmware de la placa ignora por completo este ajuste en cualquier otro
tipo de placa de expansión. "Ninguno instalado" (el valor por defecto
seguro) deliberadamente no cae de vuelta a asumir MLX90640 - una placa
con un MLX90640 real conectado necesita esto establecido
explícitamente, una vez, de la misma forma que el propio tipo de placa
de expansión ya lo requiere.

### Flasheando

1. **Conectar**: elige Serie/SLCAN o SocketCAN (solo Linux), luego el
   puerto/interfaz, luego haz clic en Conectar. Para Serie/SLCAN esto
   abre el canal CAN a 500 kbit/s (la velocidad de bus fija de URTC);
   para SocketCAN se espera que la interfaz ya esté a esa velocidad
   (paso 1 de arriba) - esta herramienta no la establece. De cualquier
   forma, la versión actual se consulta automáticamente - ver sección 4
   de arriba.
2. **Elige un objetivo de flasheo**: "Esta placa (principal)" o
   "Esclavo de expansión" - por defecto la placa principal, el caso más
   común con diferencia. La opción de esclavo solo alcanza algo en una
   variante de placa de expansión Advanced (TMC2209+STM32F303CBT6 o
   TMC5160A+STM32F303CBT6) - la actualización se relevada a través del
   propio puente I2C de la placa principal hacia el chip esclavo (los
   propios `0x210`-`0x219` de `CANBUS.TXT`), no una conexión física
   separada. "Borrar F-RAM antes de flashear" (paso 4 abajo) se
   deshabilita automáticamente al elegir Esclavo - el chip esclavo no
   tiene F-RAM propia que borrar.
3. **Seleccionar firmware**: elige de la lista detectada, o Buscar - ver
   sección 3 de arriba para saber exactamente cómo funcionan la
   detección y la validación.
4. **Flashear**:
   - Deja marcado "La placa está ejecutando actualmente la aplicación"
     si la placa está encendida y funcionando con normalidad - la
     herramienta envía primero el disparador de payload mágico `0x7F0`
     (o `0x210`, relevado al esclavo, si Esclavo es el objetivo
     seleccionado), que apaga de forma segura cada actuador antes de
     reiniciar hacia el
     bootloader.
   - Desmárcalo si la placa ya está en el bootloader (justo después de
     un flasheo JTAG nuevo, o si la comprobación de versión de arriba
     mostró "no valid firmware currently installed").
   - Haz clic en **Flashear Firmware** y confirma - el diálogo de
     confirmación nombra qué objetivo estás a punto de flashear, así
     que verifica que coincide con lo que realmente pretendías
     seleccionar. El registro muestra cada paso del protocolo; la barra
     de progreso sigue el progreso de escritura página a página durante
     la transferencia, y luego el progreso de copia durante la copia
     final de respaldo a principal.

Si la verificación falla en cualquier punto (desajuste de CRC32, HMAC, o
HardwareID), el slot principal del bootloader nunca se toca - la placa
sigue ejecutando el firmware que ya tenía. Siempre es seguro simplemente
volver a intentarlo.

**Respaldar Firmware (CAN)**: lee el firmware actualmente instalado por
el bus, sin modificar, y lo guarda como un archivo `.bin` - el
equivalente CAN de la propia función SWD "back up entire flash before
erasing" (sección 6 más abajo), por la misma razón. Vale la pena hacerlo
antes de cualquier actualización, especialmente antes de un downgrade
deliberado (abajo), ya que es la única forma de recuperar los bytes
exactos de hoy más adelante si ya no tienes el archivo que los generó.
Solo board principal, y solo mientras la placa está realmente en el
bootloader - requiere un bootloader que implemente `0x7FE`/`0x7FF` (ver
`docs/CANBUS.TXT`); uno antiguo simplemente nunca responde, mostrado como
un timeout claro en vez de un archivo silenciosamente vacío. En la práctica, esto significa que la copia funciona en una placa sin aplicación válida o que quedó a medias de una actualización: con una aplicación válida el bootloader salta a ella unos 600 ms después del reinicio salvo que llegue una trama de inicio de actualización (`0x7F1`), y esta herramienta no tiene ningún botón que mantenga al bootloader esperando (eso requeriría un cambio en el bootloader). Para una placa que funciona con normalidad, haz la copia de la flash por SWD/JTAG (sección 6).

**Avisos de versión y de firma**: antes de la transferencia la herramienta pregunta a la placa qué hay instalado y registra "instalada vX.Y -> nueva vA.B"; si la versión nueva es más antigua, avisa de que el bootloader la rechazará salvo que se permita el downgrade y sugiere hacer antes una copia de seguridad. Una imagen cuyo manifiesto dice que está firmada con la clave de desarrollo PÚBLICA (las imágenes oficiales incluidas lo están) muestra un aviso en rojo bajo el nombre del archivo; pon `"require_production_signature": true` en `urtc_config.json` para rechazar por completo esas imágenes. Cuando la placa responde desde su bootloader sin firmware válido, se selecciona la imagen oficial más reciente de la placa principal que haya en `firmware/` para que la compruebes y la grabes. Tras cada actualización correcta se escribe un pequeño informe (`logs/urtc_update_report_*.json`: versión de la herramienta, operador, nombre, tamaño y SHA-256 de la imagen, versiones anterior y posterior); lleva su propio SHA-256 para que una edición se note, pero no es una firma.

**Instalar deliberadamente una versión anterior**: el bootloader
normalmente rechaza una imagen válidamente firmada si declara una
versión anterior a la ya instalada (razón de fallo de verificación
"rollback rechazado") - esto evita que se reenvíe una versión con una
vulnerabilidad ya descubierta. Si genuinamente necesitas revertir a una
versión anterior en la que confíes, marca **"Permitir downgrade
(saltarse el anti-rollback) para esta actualización"** (solo para el
board principal) antes de flashear - aparece un segundo diálogo de
confirmación, ya que esto salta deliberadamente una comprobación de
seguridad. Esto sigue subiendo la imagen antigua completa a través de
la transferencia normal, solo levanta la comprobación de orden de
versión para ese intento (`0x7FD` - ver `docs/CANBUS.TXT`); el número de
versión reportado a la placa viene del propio `.manifest.json` del
archivo cuando existe uno junto a él (ver sección 3 arriba), recayendo
en la versión actualmente configurada de esta herramienta en caso
contrario, registrado claramente en cualquier caso para que nunca sea
una suposición silenciosa.

### Programar el chip completo por SWD/JTAG (avanzado)

La sección "4. Program complete chip via SWD/JTAG" en la herramienta
hace un flasheo de puesta en marcha completo - borra todo el chip por
completo, luego escribe desde cero tanto la imagen del bootloader como
la de la aplicación, en las direcciones reales del chip que corresponda
según la selección de **Chip objetivo** (ver abajo). Esto es un
**tipo de operación distinto** de las secciones 1-5 de arriba:

|  | Actualización CAN OTA (secciones 1-5) | SWD/JTAG chip completo (sección 6) |
|---|---|---|
| Auto-reparable si se interrumpe | Sí - el slot de respaldo de imagen dorada garantiza que el firmware en ejecución sobrevive | No - no ejecutará nada hasta que se reprograme |
| Recuperable | Automáticamente, sin acción necesaria | Sí - solo reconecta y flashea de nuevo por SWD; el puerto de depuración no depende del contenido de la flash. Solo un bloqueo verdaderamente permanente (option byte RDP2) impediría esto, y nada en esta herramienta establece option bytes |
| Toca el bootloader | Nunca | Sí, por diseño |
| Necesita | Un adaptador USB-CAN | Una sonda SWD/JTAG (ST-Link o similar) |
| Uso típico | Actualizaciones de firmware rutinarias | Primera puesta en marcha en un chip en blanco, o recuperar una placa inutilizada |

**Chip objetivo:** "Esta placa (principal)" o "Esclavo de expansión" -
mismas 2 opciones que el propio selector de la pestaña CAN-OTA, pero
una elección genuinamente separada aquí: SWD/JTAG necesita una sonda
cableada físicamente al chip que corresponda según esta selección, ya
que no hay ningún puente (a diferencia de CAN-OTA) que permita que una
sola conexión alcance ambos. Cambiar esto cambia automáticamente las
direcciones de flash usadas:

| | Placa principal (STM32F303CC) | Esclavo de expansión (STM32F303CBT6) |
|---|---|---|
| Dirección de bootloader | `0x08000000` (región de 32K) | `0x08000000` (región de 18K) |
| Dirección de aplicación | `0x08008000` (región de 112K) | `0x08005000` (región de 54K) |
| Cadena de target pyOCD | `stm32f303cc` | `stm32f303cb` |

Ambas cadenas de target de arriba son la mejor conjetura de este
proyecto sobre el nombre real de target de pyOCD para cada chip, no
confirmado contra una instalación real de pyOCD mientras se escribía
esto (la cobertura de STM32 en pyOCD llega en gran parte a través de
CMSIS-Packs en vez de targets integrados) - si el flasheo falla con un
error del estilo "target not found", ejecuta tú mismo `pyocd list
--targets --name stm32f303` y `pyocd pack install <el nombre real>`
descarga el CMSIS-Pack correcto.

**Requiere uno de** (la herramienta autodetecta cuál está disponible y
solo habilita las que encuentra):
- **pyOCD** - `pip install pyocd`. Libre, de código abierto, sin
  instalación separada más allá del paquete pip.
- **STM32CubeProgrammer** - la herramienta oficial de ST, instalada por
  separado desde [st.com](https://www.st.com). Si ya la tienes para otro
  trabajo con STM32, no necesitas instalar nada extra aquí.

Ambas se ejecutan como subprocesos de línea de comandos, no se importan
como bibliotecas de Python - verás el comando exacto registrado antes de
que se ejecute.

**Formatos de archivo:** `.bin` (necesita la dirección fija que esta
herramienta ya conoce - no la introduces tú) o `.hex` (lleva su propia
dirección, se usa tal cual). Mezclar está bien - bootloader como `.hex`
y aplicación como `.bin`, o viceversa, ambos funcionan. Ambos selectores
de archivo validan el archivo elegido (tamaño plausible para el slot de
destino, y - donde el formato permite comprobarlo con confianza - un
puntero de pila inicial plausible) antes de dejarte continuar, de la
misma forma que ya lo hacía el selector de firmware de la ruta CAN.

**La conexión se comprueba antes de que se ejecute nada destructivo**,
exigiendo **evidencia positiva** de una sonda/objetivo real en vez de
solo la ausencia de un error - el propio código de salida de
STM32CubeProgrammer no es una señal fiable de éxito/fallo por sí solo,
así que una comprobación de conexión dedicada (`pyocd list --probes`, o
un `-c port=SWD` de solo conexión para STM32CubeProgrammer) se ejecuta
antes de que el paso de borrado masivo lo haga jamás. La salida de cada
comando posterior también se examina en busca de texto de fallo conocido
como una segunda capa, por si el código de salida de una herramienta por
sí solo no fuera fiable en alguna otra situación tampoco.

**El simulacro (dry run) está activado por defecto.** La primera vez,
déjalo marcado y pulsa "Flash Complete Chip" - imprime los comandos
exactos en el registro sin tocar la placa. Léelos, confirma que las
rutas y direcciones parecen correctas, *luego* desmarca el simulacro y
hazlo de verdad.

**"Back up entire flash before erasing"** lee toda la región de flash de
256KB a un archivo `.bin` primero, mediante el propio comando de
lectura-de-memoria-a-archivo de la misma herramienta (`-r` para
STM32CubeProgrammer, `commander savemem` para pyOCD) - un seguro real
aquí, ya que a diferencia de una actualización CAN OTA (que el slot de
respaldo de imagen dorada ya protege), un borrado completo de chip no
tiene otro deshacer. Desactivado por defecto ya que añade 10-30s y no es
necesario en un chip nuevo/en blanco; vale la pena marcarlo antes de
sobrescribir una placa que ya está ejecutando algo. Si la lectura
realmente no produce un archivo, el borrado se rechaza en vez de
proceder sin el respaldo que pediste.

**Estado de las pruebas:** la lógica de comprobación de conexión de
arriba se verificó contra salida real de STM32CubeProgrammer (tanto un
registro genuino de conexión exitosa como un fallo documentado de "No
target connected", ambos obtenidos del propio foro comunitario de ST) y
contra el escenario exacto de falso-éxito que encontró un usuario real.
La secuencia completa de borrado/programación/verificación contra un
ST-Link real y un STM32F303CC real todavía no se ha ejercitado de
principio a fin - el entorno que escribió esto no tiene acceso USB. Trata
un primer intento real completo con la precaución apropiada - una placa
de repuesto/prueba primero si tienes una, y ten en mente un plan de
respaldo (la propia herramienta de flasheo de STM32CubeIDE, o
`st-flash`) por si algo de tu versión específica de pyOCD o sonda no
coincide con lo que se asume aquí.

### Diagnósticos — actividad de bus, bitrate, y paquetes de depuración

**Selector de bitrate + autodetección** (solo Serie/SLCAN): el bus de
URTC está fijo a 500 kbit/s, que sigue siendo el valor por defecto -
esto es para un adaptador mal configurado o para depurar una placa no
estándar. **Autodetección** solo *escucha*: abre el adaptador en modo
solo escucha de SLCAN (`L`) en cada bitrate estándar por turno y se
detiene en el primero donde oye una trama CAN válida, así que nunca
transmite y no puede perturbar un bus en marcha. Por eso necesita que
otros nodos estén enviando y que el adaptador admita el modo solo
escucha; con el bus en silencio (o con un adaptador sin ese modo) no
encuentra nada y eliges el bitrate a mano. No conectado todavía cuando
haces clic en él. El bitrate de SocketCAN se establece a nivel del
sistema operativo (`ip link`), así que este control está deshabilitado
para ese transporte - no hay nada aquí para que lo intente.

**Actividad de bus** ("Comprobar (2s)", junto a Consultar): cuenta
tramas de protocolo reales realmente vistas durante una ventana fija de
2 segundos en el transporte que esté conectado. Esto deliberadamente
**no** es lo mismo que un porcentaje real de carga de bus CAN - eso
necesitaría una consulta netlink (SocketCAN) o extensiones específicas
del adaptador (SLCAN) que esta herramienta no tiene una forma estándar y
sin dependencias de obtener para el controlador del *propio adaptador*.
Lo que sí da: una señal genuina, directamente
medida, de "hay algo hablando en este bus, y aproximadamente con qué
frecuencia", en cualquiera de los 2 transportes. Para SocketCAN en
concreto, también muestra el delta de 2 segundos de las propias
estadísticas de interfaz de Linux
(`/sys/class/net/<iface>/statistics/`) - contadores básicos de
rx/tx/error/drop que expone toda interfaz, leídos como archivos planos,
sin dependencia extra. Conectar por SocketCAN también lee
`/sys/class/net/<iface>/carrier` - un archivo plano 0/1 que expone toda
interfaz de Linux. Cuando un controlador CAN entra en bus-off, el driver
del kernel llama a `netif_carrier_off()`, así que "sin portadora" aquí
es evidencia real de un bus-off o un enlace igualmente muerto, registrado
como advertencia con el comando exacto de recuperación (`sudo ip link
set <iface> down && sudo ip link set <iface> up type can bitrate 500000
restart-ms 100`). Esta herramienta no ejecuta ese comando por sí misma -
limpiar un bus-off real necesita bajar y volver a subir la interfaz a
nivel del kernel, lo cual necesita root y cuenta como cambiar la
configuración de red del sistema, no algo para hacer silenciosamente en
tu nombre.

**Contadores de error (TEC/REC)** (junto a Actividad de bus): a
diferencia de los contadores del adaptador de arriba, esto le pregunta a
**la propia placa** por el Transmit/Receive Error Counter de su propio
controlador CAN (`0x7FB`/`0x7FC` - ver `docs/CANBUS.TXT`), respondido
por lo que esté ejecutándose en ese momento, aplicación o bootloader.
Verde significa que ambos contadores están en 0 (error-active,
saludable); naranja significa que uno o ambos son distintos de cero pero
por debajo de 128 (todavía error-active, pero algo está causando
retransmisiones); rojo significa 128 o más (error-passive o peor) o
ninguna respuesta en absoluto (firmware/bootloader antiguo que aún no
implementa `0x7FB`, o la placa no conectada). Un TEC que sube de forma
constante con un REC plano suele apuntar a que las propias transmisiones
de esta placa no reciben confirmación - ningún otro nodo en el bus, o un
problema de cableado/terminación/bitrate específico de la conexión de
esta placa.

**Exportar paquete de depuración** (arriba del registro): guarda un
`.zip` con el registro actual en pantalla, diagnósticos básicos del
sistema (SO, versión de Python, qué herramientas se encontraron,
transporte/puerto/bitrate actual), y el archivo de firmware CAN
seleccionado actualmente - útil para entregar un panorama completo a
quien escribió el firmware si algo sale mal en el campo, en vez de
copiar el registro
por mano.

### SWD/JTAG — formatos de archivo, verificación de slot, y selección de sonda

**Formatos de archivo**: los selectores de bootloader/aplicación de la
sección SWD aceptan `.bin`, `.hex`, y `.elf`/`.axf`. ELF/AXF se analiza
con una pequeña cantidad de desempaquetado de estructuras escrito a mano
(solo cabecera ELF + cabeceras de programa - sin símbolos, sin cabeceras
de sección), deliberadamente sin usar `pyelftools`: este proyecto se
mantiene con cero dependencias fuera de la biblioteca estándar, y el
análisis ELF completo es más de lo que necesita esta comprobación de
plausibilidad específica. Verificado contra el propio
`BOOTLOADER.elf`/`APP.elf` compilado real de este proyecto - ambos
validan correctamente en sus direcciones de carga reales
(`0x08000000`/`0x08008000`), no solo archivos de prueba sintéticos. Solo
ARM little-endian de 32 bits, que es todo lo que un objetivo Cortex-M es
alguna vez. El tamaño declarado de un archivo `.hex` es el recuento real
de bytes ocupados, no el rango de direcciones desde su registro más bajo
hasta el más alto - así que un archivo disperso (un pequeño bloque de
firmware real más un bloque distante y separado de option bytes o datos
de calibración, que algunos toolchains de STM32 agrupan en una sola
exportación) valida sobre su contenido real en vez de sobre el hueco
entre ellos. Una imagen de firmware en bruto bajo una extensión que no
sea `.bin` (`.img`, `.rom`, o sin extensión en absoluto - seleccionable
mediante la opción "Todos los archivos" del selector de archivos) obtiene
su dirección base de en qué slot la estés cargando, igual que lo haría
un `.bin`.

**Verificación de slot de bootloader/aplicación**: los selectores de
archivo verifican que cada imagen está pensada para el slot en el que se
está poniendo, no solo que parece firmware válido de *algún* tipo. Una
imagen de bootloader y una de aplicación tienen un puntero de pila
igualmente plausible - mismo chip, misma RAM - así que esa comprobación
por sí sola no puede distinguirlas si una termina en el slot de la otra.
Lo que sí puede: el **manejador de reset** de una imagen enlazada es una
dirección absoluta y real fijada en tiempo de enlazado, y solo apunta
dentro de la región para la que realmente se enlazó. Verificado contra
el propio `BOOTLOADER.bin`/`APP.bin` compilado real de este proyecto:
sus manejadores de reset son `0x08000785` y `0x0800C0CD`
respectivamente, cada uno correctamente dentro del rango de direcciones
de su propio slot y fuera del de la otra - así que poner cualquiera de
las 2 en el slot equivocado se detecta y se bloquea, no se acepta en
silencio. Se aplica la misma lógica a `.hex`/`.elf`, comprobados contra
su propia dirección de carga embebida en su lugar.

**Comprobar Option Bytes** (sección 4, solo STM32CubeProgrammer -
pyOCD no expone esto de la misma forma por CLI): un volcado de solo
lectura `-ob displ`, sin borrado/escritura. Marca el nivel RDP con el
mismo cuidado que toma toda esta herramienta en torno al riesgo de SWD:
- **RDP0** - sin protección, normal para una placa de desarrollo.
- **RDP1** - reversible mediante el Read Unprotect de CubeProgrammer,
  pero eso borra el chip por completo como parte de quitarlo - no algo
  que esta herramienta haga por ti automáticamente.
- **RDP2** - el único bloqueo genuinamente **permanente** de todo este
  proyecto. A diferencia de cualquier otro riesgo documentado arriba
  (todos recuperables por SWD), RDP2 deshabilita el puerto de depuración
  para siempre por diseño del propio ST. Esta comprobación existe para
  detectarlo antes de una operación de chip completo, no después.

**Selección de sonda** (sección 4): si hay más de un ST-Link/sonda
conectado a la vez, todo comando exige elegir uno explícitamente del
desplegable de Sonda - no hay "el que sea que el sistema operativo
enumere primero". Con exactamente una sonda conectada, se auto-selecciona;
con cero o varias, pulsa Actualizar y elige. Esto se aplica tanto al
flasheo de chip completo como a la comprobación de option bytes, ya que
ambos son lo bastante cercanos a destructivos como para que adivinar la
placa equivocada sea un riesgo real en un banco con varios dispositivos.

**Las escrituras de pyOCD se verifican con una relectura explícita**,
no solo se confía en el código de salida. El propio comando `flash` de
pyOCD se salta reescribir páginas que ya coinciden (una optimización de
velocidad, no un informe de verificación), así que esta herramienta
añade un paso `commander compare` contra ambas imágenes tras escribir -
una comprobación genuina byte a byte, igual que ya hace el flag `-v` de
STM32CubeProgrammer. Solo para `.bin`: `compare` comprueba el contenido
de la flash contra los bytes en bruto del archivo, lo cual no
coincidiría correctamente con la propia codificación de un archivo
`.hex`/`.elf` incluso tras un flasheo exitoso, así que esos 2 formatos
se saltan este paso específico y confían en la propia verificación
interna en tiempo de escritura de pyOCD en su lugar.

### Telemetría de transferencia y detalle de fallo de verificación

**Telemetría de transferencia**: el registro muestra los KB/s efectivos
y el tiempo transcurrido por página durante una actualización CAN, más
una línea de resumen al final (tiempo total, KB/s promedio, cuántos
reintentos de ACK de página ocurrieron). Puramente informativo - no
cambia el comportamiento de flasheo, solo hace más fácil distinguir de
un vistazo "esto simplemente va lento" de "algo realmente va mal".

**Motivos específicos de fallo de verificación**: si la verificación
falla durante una actualización CAN, `bootloader_protocol.c` envía un byte de
motivo junto al estado `0x05` (verificación fallida) - transferencia
incompleta, desajuste de CRC32, desajuste de HMAC, o desajuste de
HardwareID, en vez de que todo fallo parezca idéntico. Ver
`docs/CANBUS.TXT` para el formato exacto de trama (`0x7F5`, DLC 2 para
este estado específico). Esta herramienta y el bootloader coinciden en
este formato de trama, así que flashea ambos juntos si estás
construyendo un bootloader personalizado con una versión distinta del
protocolo.

**El mismo detalle para el esclavo de expansión**: una actualización
fallida del esclavo (Objetivo: "Esclavo de expansión") consulta `0x219`
justo después de que `0x215` reporte `STATUS_VERIFY_FAIL`, relevando el
propio `REG_VERIFY_FAIL_REASON` del bootloader esclavo - los mismos 5
motivos de arriba, solo que alcanzados a través del puente I2C en vez de
leídos directamente de una trama CAN. Requiere un bootloader esclavo que
implemente `0x219` (añadido junto con el soporte de esta herramienta para
ello); un bootloader esclavo más antiguo simplemente no responde a esa
consulta, y esta herramienta cae de vuelta al mensaje genérico de
"verificación fallida".

### Borrado opcional de la F-RAM antes de flashear

La sección 3 tiene una casilla, **"También borrar la F-RAM de
persistencia antes de flashear"** - desactivada por defecto. Si está
marcada, envía el comando de borrado con payload mágico (`0x192` - ver
`docs/CANBUS.TXT`) a la F-RAM de persistencia FM24CL64B de la placa
antes de que empiece la secuencia de actualización, borrando cualquier
estado de parámetros de herramienta que tuviera guardado.

**No es necesario para una actualización normal.** Un desajuste de
versión en el propio formato del registro guardado ya se detecta y se
ignora de forma segura en el siguiente arranque (ver la sección de
persistencia de parámetros de `src/F303-master/README.md`) - esta
casilla existe para una limpieza genuinamente completa, no porque
saltársela vaya a dejar algo roto.

**Solo funciona mientras la aplicación está en ejecución** - el propio
bootloader no maneja `0x192` en absoluto, solo lo hace `firmware_can_global_post.c`.
Esta casilla se salta en silencio (con una línea de registro explicando
por qué) si la casilla "la placa está ejecutando actualmente la
aplicación" de arriba no está marcada, ya que en ese caso se asume que
la placa ya está en el bootloader.

**Una confirmación ausente no detiene el flasheo.** Si la propia trama
de confirmación del comando de borrado no vuelve dentro de 2 segundos,
esto se registra como una advertencia y la actualización de firmware
real procede de todas formas - borrar es un paso secundario y opcional
junto al propósito real de esta herramienta, no algo que deba abortar
una actualización por lo demás exitosa por la ausencia de su propia
trama de confirmación. Comprueba el estado de la F-RAM por separado (el
propio botón Consultar Estado de `URTC Tester`) si eso te importa.

<!-- urtc-section:heads -->
### Varios cabezales en un bus

El firmware puede hacer que varios cabezales compartan un bus CAN (la extensión multinodo). Viene **desactivada por defecto**, y un bus con un solo cabezal funciona exactamente como antes. La ventana **Cabezales** encuentra los cabezales, lista cada uno con su dirección, herramienta y número de serie, y muestra su estado: listo, seleccionado, conflicto de dirección, fallo retenido, en su bootloader o perdido. Seleccionas uno, el programa pide confirmación y solo entonces le envía algo; mientras haya varios cabezales en el bus, un comando se rechaza hasta que uno esté seleccionado y lo haya confirmado. Si se pierde el cabezal seleccionado, todos los cabezales pasan a su estado seguro (una casilla de la ventana lo desactiva). Se ha probado solo contra un modelo del bus, no con placas. Véase `docs/MULTINODE.md` en URTC-COMMON.
<!-- /urtc-section:heads -->

## 🔒 Seguridad y protección

| Riesgo | Defensa |
|---|---|
| Flashear una imagen en la placa equivocada | La comprobación del HardwareID del protocolo del bootloader, hecha antes de escribir nada |
| Una imagen corrupta, sin firmar o manipulada | Las comprobaciones de integridad de la imagen; un manifiesto cuyo `sha256` no coincide con el archivo se rechaza antes de cualquier tráfico en el bus, una imagen sin firmar se rechaza y se envía la firma publicada sin ninguna clave; la firma de release (Ed25519) se comprueba antes de usar la imagen de una release |
| Instalar una imagen más antigua por error | La comprobación anti-retroceso del bootloader; volver a una versión anterior a propósito necesita la autorización de bajada |
| Una actualización fallida que deja la placa muerta | El modelo de imagen dorada: la ranura de respaldo conserva el firmware anterior, una trama de confirmación perdida se recupera preguntando de nuevo la versión en lugar de informar de un fallo falso, y la ranura principal puede leerse antes |
| Una actualización manipulada de este programa | «Buscar actualización» solo acepta un paquete con SHA-256 y firma Ed25519 válidos (la clave de las releases, fijada en el programa), instala solo tras una confirmación y nunca durante una transferencia, y conserva la versión anterior |

El bootloader comprueba las imágenes con CRC32 y un HMAC-SHA256 de clave compartida, no con una firma asimétrica; las imágenes de aplicación publicadas se firman con la clave pública de desarrollo, así que cualquiera puede hacer una imagen que el bootloader acepte. Nada de esto se ha ejecutado en una placa real.

### Fiabilidad durante una actualización CAN, y registros de sesión

Si el ACK de una página no llega dentro de la ventana normal de 3s
durante una actualización CAN, la herramienta vuelve a esperar (no
reenvía los datos de la página) hasta dos veces más con una breve espera
creciente antes de rendirse. Esto solo ayuda con un ACK que simplemente
llega tarde: el bootloader envía cada ACK de página una sola vez y nunca
lo repite, así que un ACK realmente perdido no se puede recuperar y la
actualización se aborta con un error (la placa se queda en su bootloader
y la actualización se puede volver a lanzar sin más). La herramienta
deliberadamente no reenvía los datos de la página en un timeout - si los
datos hubieran llegado bien, reenviar haría que el bootloader leyera esos
bytes como el inicio de la *siguiente* página, desincronizando la
transferencia. Mientras espera, se compara el propio latido del
bootloader (enviado aproximadamente una vez por segundo) con el progreso
que implicaría la página y el registro indica cuándo coinciden; el latido
es un porcentaje entero, así que es solo una pista, no una prueba de que
la página llegara, y nunca cambia el resultado.

Cada sesión también escribe un archivo de registro con marca de tiempo
en `logs/` (`urtc_flasher_YYYYMMDD_HHMMSS.log`),
independiente del registro en pantalla - útil para entregarle una traza
completa a quien escribió el firmware si algo sale mal en el campo. Esta
carpeta se crea automáticamente y es segura de borrar; nada vuelve a
leer registros antiguos. Solo se conservan los 30 registros de sesión más recientes; si no se puede escribir en la carpeta junto al programa (una instalación de solo lectura), se usa una carpeta por usuario (`%LOCALAPPDATA%\URTC-Flasher\logs` en Windows, `~/.local/state/urtc-flasher/logs` en el resto).

## 🔌 Interfaces

Para pipelines de CI, bancos de pruebas, o scripting de línea de
producción donde no hay pantalla:

```
python3 urtc_flasher.py --cli --port /dev/ttyACM0 --file firmware.bin
```

```
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan,python-can,mock}] --port PORT
                             --file FILE [--no-trigger] [--force]
```

Códigos de salida: `0` éxito, `1` error de protocolo/conexión, `2`
argumentos incorrectos o un archivo de firmware que falla la validación
(pasa `--force` para flashearlo de todas formas), `130` cancelado con
Ctrl+C. Solo cubre la ruta de actualización CAN OTA (secciones 1-3) - la
ruta completa SWD/JTAG del chip es deliberadamente solo-GUI por ahora,
dado lo mucho más que está en juego si una ejecución con script obtiene
una combinación equivocada de archivo/objetivo sin que nadie esté
observando.

**`--transport python-can`** usa el paquete opcional `python-can` (`pip install python-can`) para PCAN, Kvaser, gs_usb/candleLight y las demás interfaces que admite, de modo que no hace falta regrabar el adaptador con SLCAN: `--port` es entonces `<interfaz>:<canal>` (por ejemplo `pcan:PCAN_USBBUS1`) y el bus se abre a 500 kbit/s. La ventana ofrece los mismos adaptadores cuando `python-can` está instalado: los que encuentra para PCAN, Kvaser y gs_usb y los nombrados en la variable de entorno `URTC_PYTHON_CAN` (`<interfaz>:<canal>` separados por comas), listados como `python-can:<interfaz>:<canal>`; la velocidad del bus de esa conexión es fija, 500 kbit/s. La ventana también puede arrancar con `--firmware RUTA` para tener ya elegida una imagen (no se escribe nada en una placa hasta que conectes y confirmes la actualización).

**`--transport mock`** ejecuta toda la secuencia de actualización contra
un bootloader simulado, en memoria, en vez de una placa real - sin
adaptador, sin puerto, nada físico involucrado:

```
python3 urtc_flasher.py --cli --transport mock --file firmware.bin --no-trigger
```

Útil para probar la lógica propia de esta herramienta (comportamiento de
reintentos, manejo de timeouts, códigos de salida) en un pipeline de CI
o antes de tocar hardware real - no algo que hable con una placa real.
`--mock-fail 0x03` (o cualquier otro valor `VERIFY_FAIL_REASON_*` de
`docs/CANBUS.TXT`) hace que la actualización simulada falle la
verificación en vez de tener éxito, para probar la ruta de fallo de la
misma manera.

## ⚙️ Configuración

Esta herramienta **no lleva ninguna clave de firma**. El build de URTC firma
cada imagen de aplicación y publica la firma a su lado, en
`<imagen>.manifest.json` (`hmac_sha256`, más `<imagen>.sha256`); el flasher
envía esa firma publicada y rechaza una imagen cuyo sha256 no coincide con
su manifiesto. Al descargar una imagen desde GitHub también se descargan
ambos archivos, y `python tools/sync_firmware.py` actualiza la carpeta
`firmware/` incluida a partir del build de URTC (`--check` la verifica). Por defecto toma el conjunto de los assets de la última release de URTC (`--release TAG` elige otra); en su lugar se puede pasar como argumento una carpeta local, por ejemplo un build local de URTC.
Solo una imagen compilada por ti sin manifiesto, en una placa de banco,
necesita clave: define `hmac_key_hex` / `slave_hmac_key_hex` en
`urtc_config.json` (abajo); sin ella esa imagen se rechaza en lugar de
firmarse con una clave que el bootloader no puede tener. Ver
`docs/FIRMWARE_SIGNING.TXT` de URTC. Las imágenes publicadas están firmadas con la clave pública de desarrollo (`signing_key_kind: dev`), así que es una comprobación de clave compartida: muestra que la imagen la hizo alguien que posee esa clave, no quién es; la firma asimétrica (Ed25519) está prevista, no implementada.

**O sustituye cualquiera de esto sin tocar el script:** un
`urtc_config.json` opcional junto a `firmware/` puede establecer la
clave de firma, el HardwareID, y los valores del mapa de memoria - útil
para una revisión de placa distinta, una clave rotada, o (para los
campos del mapa de memoria) adaptar esta herramienta a una variante de
chip o esquema de particiones distinto, sin necesitar una versión de
script nueva por despliegue:
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
Todo campo es opcional - solo sustituye lo que realmente esté
cambiando. Un archivo ausente vuelve en silencio a los valores por
defecto compilados; un archivo presente pero roto registra una
advertencia y también vuelve a esos valores, en vez de hacer fallar la
herramienta por una errata. **Las sustituciones del mapa de memoria y del HardwareID solo aplican a las constantes de la propia placa principal** (la única excepción es `slave_hmac_key_hex`, la clave de firma del esclavo de expansión, que también puede fijarse aquí) - los equivalentes
propios del chip esclavo de expansión (`SLAVE_BOOTLOADER_FLASH_ADDR`,
`SLAVE_APP_FLASH_ADDR`, `SLAVE_HARDWARE_ID`, etc.) están fijos en el
propio `flasher_config.py`, ya que los valores reales de ese hardware
ya están confirmados contra sus propios scripts de enlazado en vez de
necesitar una sustitución en tiempo de despliegue como sí necesitan los
valores por defecto de la placa principal. Se registra qué fuente está
activa al arrancar, así que siempre es visible qué valores usó realmente
una sesión dada. `hardware_id` acepta tanto una cadena JSON (`"0x0303CC01"`)
como un número JSON plano (`50580689`) - lo que sea más natural según
cómo se genere el archivo. `app_max_size`, `bootloader_max_size`,
`flash_page_size`, `bootloader_flash_addr`, y `app_flash_addr` también
se pueden sustituir aquí, junto a la clave de firma y el HardwareID de
arriba - útil si esta herramienta alguna vez se adapta a una variante de
chip o esquema de particiones distinto.

## 🚀 Inicio rápido

### Consigue que tu adaptador hable CAN

Cuál de estos necesitas depende de tu plataforma y de qué transporte
vayas a usar:

**Linux, ruta SocketCAN (recomendada si tu adaptador la soporta):**
Nada que flashear en el adaptador mismo. Levanta la interfaz una vez por
arranque (o añádela a tu configuración de red para que persista):
```
sudo modprobe can vcan gs_usb   # gs_usb cubre la mayoria de placas de la familia CANable
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up
```
Si tu adaptador se enumera con un nombre distinto de `can0`, revisa `ip
link show` (o `dmesg` justo después de conectarlo) para ver el nombre
real. Algunos adaptadores necesitan `slcand` en vez de un driver nativo
— si `ip link show` no muestra ninguna interfaz CAN en absoluto tras
conectarlo, este es probablemente tu caso; consulta la documentación de
tu adaptador para la invocación de `slcand`, que crea una interfaz
`slcan0` que luego levantas de la misma forma que arriba.

**Windows, o Linux por la ruta Serie/SLCAN:**
Una CANable Pro v2 viene de fábrica con firmware **candleLight**, que
habla con el host usando el protocolo `gs_usb` - el mismo que el driver
`gs_usb` de SocketCAN en Linux espera de forma nativa (ver arriba). Ese
protocolo **no** se presenta como puerto serie, que es lo que necesita
esta ruta. Para usar Serie/SLCAN en su lugar (obligatorio en Windows;
opcional en Linux):

1. Descarga firmware compatible con SLCAN para tu adaptador (busca
   "canable slcan firmware" — hay varios forks mantenidos; usa el que
   indique la propia documentación de tu adaptador).
2. Pon el adaptador en modo DFU/bootloader (normalmente un botón BOOT
   mantenido durante el encendido, o un jumper — revisa la documentación
   de tu adaptador).
3. Flashea el firmware SLCAN usando la herramienta de flasheo del
   fabricante de tu adaptador o `dfu-util`.
4. Reconecta — ahora debería enumerarse como puerto serie: un puerto COM
   en Windows, o al estilo `/dev/ttyACM0`/`/dev/ttyUSB0` en Linux.

Si tu adaptador ya ejecuta firmware SLCAN, salta directamente al paso 2
de abajo.

Una línea SLCAN recibida cuya longitud real no coincida con lo que
implica su propio DLC declarado se trata como malformada y se descarta,
en vez de analizarse desde sus primeros N caracteres hexadecimales sin
importar lo que sigue - vale la pena saberlo si estás depurando contra
un adaptador ruidoso o no estándar.

### Instalar y ejecutar

**Windows:**
```
python -m pip install -r requirements.txt
python urtc_flasher.py
```
O compila un `.exe` independiente con `build_exe.bat` (ver ese archivo).

**Linux:**
```
python3 -m pip install -r requirements.txt
python3 urtc_flasher.py
```
O compila un binario independiente con `./build_exe.sh` (`chmod +x`
primero).

Ambos scripts pasan `--noconfirm` a PyInstaller, así que reconstruir
sobre un `dist/URTC_Flasher` ya existente lo reemplaza directamente en
vez de esperar un aviso de "¿reemplazar?" que es fácil pasar por alto en
la salida de un script.

#### Panel visual de control

El panel de control **Qt Quick** es la única ventana del programa (probado solo contra el simulador; las comprobaciones de imagen usan un HMAC-SHA256 de clave compartida). Se inicia con:
~~~
python urtc_flasher.py
~~~
Tiene una superficie oscura azul marino/cian con una tarjeta de conexión, tablas de firmware legibles, un registro de verificación oscuro y un canal de progreso visible, y cubre todo el flujo: la actualización CAN-OTA de la placa principal o del esclavo de expansión (la elección de destino; la opción «la placa está ejecutando la aplicación», el borrado de la F-RAM y la autorización de bajada de versión son solo para la placa principal), una copia de seguridad por CAN del firmware instalado, el selector de velocidad del bus con la búsqueda en solo escucha, la descarga de una release de GitHub, un selector de archivos para cualquier `.bin`, la comprobación de actividad del bus, el Board Snapshot, las 4 escrituras de configuración del dispositivo, el descubrimiento SWD/JTAG de solo lectura y la programación del chip completo por SWD/JTAG (borrado/escritura, simulacro, copia de seguridad antes de borrar, comprobación de RDP). Cada acción que escribe en la placa pide confirmación antes, la autorización de bajada de versión pide una segunda, y cerrar la ventana durante una transferencia vuelve a preguntar. Nada de esto se ha probado en una placa real. `python urtc_flasher.py --cli` es el modo sin interfaz (sección 7).

#### Cabecera y herramientas

- **Cabecera** - el estado de la conexión, el selector de idioma (la elección se guarda y se aplica en el siguiente arranque) y la versión.
- **Guardar registros...** y **Guardar paquete de depuración** - el registro de la pantalla como texto plano, o un zip más completo con diagnósticos del sistema y el archivo de firmware seleccionado (ver «Diagnósticos» más abajo). Cada sesión también se escribe en `logs/`, y se conservan las más recientes.
- **Acerca de URTC Flasher** - versión y autor, con botones para el **Readme** (en el idioma de la interfaz cuando existe traducción), la **Licencia** y la página **GitHub de URTC** del proyecto.

**Idioma**: inglés por defecto.
Se cambia con el selector de idioma de la cabecera de la ventana - se guarda inmediatamente en `urtc_config.json` (el mismo archivo usado
para los overrides técnicos de hardware — la preferencia de idioma
simplemente vive junto a esos), y se aplica en el siguiente arranque.
Las traducciones viven en archivos de texto plano bajo `language/`
(`english.lng`, `spanish.lng`, `italian.lng`, `french.lng`,
`german.lng`, `japanese.lng`, `chinese.lng`, `portuguese.lng`) como pares simples `CLAVE=Valor`, uno por línea - las
líneas que empiezan con `#` y las líneas en blanco se ignoran, y un `\n`
literal dentro de un valor se convierte en un salto de línea real (usado
por el puñado de mensajes de diálogo multilínea). Generados desde el catálogo de URTC-COMMON (una traducción se corrige allí y los archivos se escriben de nuevo, nunca a mano), o como punto de partida para otro idioma (añade `language/<nombre>.lng`, añade `("<nombre>", "Nombre
Nativo")` a `AVAILABLE_LANGUAGES` cerca del principio de
`flasher_config.py`, y pon `"language": "<nombre>"` en
`urtc_config.json`). Una clave que falte en un archivo de idioma cae de
vuelta a mostrar el nombre de esa misma clave en vez de fallar, y un
archivo de idioma ausente o ilegible (edición defectuosa, nombre de
archivo equivocado) cae de vuelta al inglés para toda la interfaz - de
cualquier forma la herramienta se mantiene usable mientras se resuelve
el desajuste.

**Permisos de serie en Linux:** si estás usando la ruta Serie/SLCAN y la
conexión falla con "Permission denied", tu usuario necesita estar en el
grupo propietario de los dispositivos serie (`dialout` en
Debian/Ubuntu; varía en otras distros):
```
sudo usermod -a -G dialout $USER
```
Cierra sesión y vuelve a entrar (la pertenencia a grupos se lee al
iniciar sesión), luego inténtalo de nuevo. La herramienta detecta este
error específico y muestra esta misma solución en un diálogo, pero vale
la pena saberlo de antemano. SocketCAN no tiene este problema particular
— el acceso a una interfaz tipo `can0` no está controlado por el grupo
`dialout` — pero levantar la interfaz en primer lugar (paso 1 de arriba)
sí necesita `sudo`, ya que es un cambio de configuración de dispositivo
de red.

Usar `python -m pip`/`python3 -m pip` en vez de un `pip` a secas evita
un problema común en ambas plataformas: el propio script wrapper de
`pip` no siempre está en el PATH incluso justo después de una
instalación exitosa, mientras que `-m pip` encuentra el módulo instalado
directamente.

### Dónde van los archivos de firmware

**La carpeta empieza vacía.** Las imágenes de firmware no se guardan en este repositorio: son los ficheros de las releases de [URTC](https://github.com/JuanenRac/URTC). La ventana las descarga de la release que elijas, y `python tools/sync_firmware.py` rellena la carpeta desde la última release oficial (o `--release ETIQUETA`). Cada fichero se comprueba con la firma de la release (`.sig`, Ed25519) y sus resúmenes antes de usarse. Mientras no exista una release oficial, el «latest» de GitHub responde 404 y `firmware_release.json` indica qué release se usa en su lugar (hoy la pre-release de banco); bórralo, o cambia su etiqueta, cuando se publique una oficial.
Esta herramienta espera una carpeta `firmware/` justo al lado de
`urtc_flasher.py`, en la raíz de este mismo repositorio:

```
├── assets/
│   └── URTC_LOGO_FLASHER.svg      <- fuente del banner (vectorial)
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v<version>.bin  <- pon los archivos .bin nuevos aqui
│   ├── URTC_*  <- tools/sync_firmware.py sustituye los archivos URTC_* de esta carpeta por los de una release; los demás archivos se quedan
│   └── URTC_SLAVE_FIRMWARE_v<version>.bin    <- app del chip esclavo de expansion, si aplica
├── logs/                          <- se crea automaticamente, un archivo por sesion
├── urtc_config.json               <- opcional, no incluido por defecto (ver "Cambiar la clave HMAC" mas abajo)
├── urtc_flasher.py                <- punto de entrada: argumentos de la CLI e inicio de la ventana Qt Quick
├── flasher_config.py              <- E/S del archivo de configuracion, carga de idioma, constantes del protocolo
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- envoltorios de STM32CubeProgrammer / pyOCD
├── flasher_validation.py          <- validacion de archivos de firmware (.bin/.hex/.elf)
├── flasher_protocol.py            <- la propia maquina de estados de CAN OTA, tanto para la placa principal como (relevado a traves de su propio puente I2C) el chip esclavo de expansion
├── flasher_github.py               <- lista y descarga los assets de una release de GitHub de URTC
├── flasher_records.py             <- registros de sesión (ubicación, retención) e informes de actualización
├── pytest.ini / ruff.toml          <- ajustes de pytest y ruff (comprobaciones estáticas)
├── requirements.txt
├── build_exe.bat                  <- compilacion independiente para Windows
├── build_exe.sh                   <- compilacion independiente para Linux
└── README.md
```

Esta herramienta está organizada en los módulos de arriba por
responsabilidad, puramente por legibilidad - no hay ninguna diferencia
funcional entre tenerlos como archivos separados o como uno grande, y no
existe una forma monolítica que mantener sincronizada como sí ocurre con
el firmware (esto es una herramienta de PC, no algo que se flashea en la
placa, así que solo hay una forma).

Esto es deliberado: este repositorio entero es autocontenido. Si solo
quieres flashear una placa — en un PC de taller, desde una memoria USB,
donde sea — puedes copiar este repositorio por sí solo, y sigue
funcionando.

**Puedes tener más de un `.bin` ahí.** Cada archivo de firmware de
aplicación se revisa y se lista - la herramienta no coge simplemente lo
primero que encuentra, y los binarios de bootloader (cualquiera con
"BOOTLOADER" en el nombre - `URTC_BOOTLOADER.bin`,
`URTC_SLAVE_BOOTLOADER.bin`) se filtran por completo de esta lista, ya
que CAN-OTA solo flashea firmware de aplicación; una actualización de
bootloader necesita SWD/JTAG en su lugar (sección 6 abajo). Al arrancar
(y cada vez que hagas clic en **Actualizar**), cada `.bin` restante en
`firmware/` se revisa contra la misma prueba de plausibilidad que
aplica el propio bootloader a una imagen nueva (sus primeros 4 bytes
tienen que parecer un puntero de pila inicial real para la RAM de este
chip, y su tamaño tiene que caber en el slot principal). Cada archivo
aparece en la lista con un ✓ o ✗ claro y el motivo:

| Archivo | Tamaño | Estado |
|---|---|---|
| URTC_MAIN_FIRMWARE_v<version>.bin | 71.8 KB | ✓ parece válido |
| URTC_SLAVE_FIRMWARE_v<version>.bin | 33.9 KB | ✓ parece válido |
| notes.txt.bin | 0.1 KB | ✗ la primera palabra no parece un puntero de pila válido |

- **Exactamente un archivo pasa la revisión** → se selecciona por ti en
  el momento en que arranca la herramienta. Un archivo inválido que esté
  solo en la carpeta *no* se auto-selecciona solo porque nada más
  compite con él.
- **Más de un archivo válido** → no se auto-selecciona nada; elige el
  que quieras de la lista.
- **Seleccionas un archivo que parece inválido de todas formas** → la
  herramienta te pide confirmar primero. Esta revisión existe para
  detectar errores obvios (archivo equivocado, descarga truncada, un
  marcador de posición vacío) - no puede detectarlo todo (un archivo
  corrupto pero plausible, o uno firmado con la clave equivocada), que
  es para lo que sirve la propia revisión de CRC32/HMAC del bootloader
  durante la transferencia real.
- **No se encuentra nada, o quieres un archivo de otro sitio por
  completo** → usa el botón **Buscar .bin...**, que funciona sin
  importar dónde viva realmente el archivo (y ejecuta la misma revisión
  de validación de cualquier forma).
- **Quieres la última compilación sin tener que buscarla tú mismo** →
  **Descargar de GitHub...** lista los archivos adjuntos a la última
  release de GitHub del repositorio de URTC
  (`github.com/JuanenRac/URTC/releases`; los binarios de firmware se
  publican como assets de la release, no se guardan en git) y te permite
  elegir uno para descargarlo directamente en tu propia carpeta
  `firmware/` local - luego aparece en la lista de arriba como cualquier
  otro archivo, sin necesidad de reiniciar. Escribe una etiqueta de
  release (por ejemplo `v0.3.5`) en el cuadro de la parte superior de la
  ventana y pulsa **Cargar** para listar otra release en lugar de la
  última. El `.sha256` y el `.manifest.json` de la imagen se descargan
  junto con ella. Solo se aceptan archivos de los propios servidores de
  GitHub (`github.com` y los servidores de almacenamiento de assets a los
  que redirige), y un archivo cuyo tamaño difiere del que anuncia la
  release se descarta. Usa la propia API pública de GitHub (sin
  autenticar, así que sujeta al límite de 60 peticiones/hora de GitHub si
  la usas mucho en poco tiempo; una variable de entorno `GITHUB_TOKEN` lo
  eleva) - nada aquí necesita una cuenta de GitHub.

Cada archivo de una release oficial tiene una firma de release (`<archivo>.sig`, Ed25519): el flasher la verifica cuando existe y rechaza una incorrecta. Un conjunto sin firmas, como una pre-release de banco, solo lo acepta `tools/sync_firmware.py` con `--allow-unsigned`.

**`<nombredearchivo>.manifest.json` y `<nombredearchivo>.sha256`, junto a
cada archivo de firmware** - los publica el build de URTC para cada imagen
(y se descargan junto con ella desde GitHub). El manifiesto lleva la
versión, el `sha256` y, en las imágenes de aplicación, el valor `hmac_sha256` que espera el bootloader (un HMAC-SHA256 de clave compartida, no una firma asimétrica; `signing_key_kind: dev` indica la clave pública de desarrollo):

```json
{"component": "main_application", "version": "<version>", "sha256": "b48d4cd5...", "hmac_sha256": "b63a701e...", "signing_key_kind": "dev"}
```

Ambos resúmenes se comprueban justo antes de flashear y una discrepancia
**rechaza la grabación** antes de enviar nada por el bus (archivo
equivocado, descarga corrupta o manifiesto desactualizado). La firma
publicada es la que se envía al bootloader, y la versión del manifiesto es
la que se le informa. Un archivo sin manifiesto (un build propio) solo se
graba si hay una clave de firma en `urtc_config.json` - ver "Cambiar la
clave HMAC" más abajo.

Añadir una compilación nueva más tarde: solo suéltala en `firmware/` y
haz clic en **Actualizar** - no hace falta reiniciar.

<!-- urtc-section:first_flash -->
### Primer arranque sin hardware

1. Arranca la placa virtual: `python -m urtc_can.virtual_board`.
2. En otra terminal define `URTC_VIRTUAL_PORT=socket://127.0.0.1:7777` y arranca el flasher: la placa virtual está en la lista de puertos.
3. Selecciónala, pulsa Conectar, elige una imagen de `firmware/` (o búscala) y pulsa Iniciar CAN-OTA.
4. La placa virtual admite la actualización completa, con las mismas comprobaciones de tamaño, firma y versión que una real. Es un modelo: nada de esto ha corrido en una placa.
<!-- /urtc-section:first_flash -->

<!-- urtc-section:compatibility -->
### Requisitos y compatibilidad

Qué versiones de los programas de URTC funcionan juntas, y qué versión del protocolo habla cada una, figura en la tabla de compatibilidad que genera URTC-COMMON: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Pruebas

La suite tiene 500 pruebas en 47 archivos (`python -m pytest tests -q`; con Qt en un equipo sin pantalla, `QT_QPA_PLATFORM=offscreen`; las 79 que necesitan PySide6 se omiten sin él): el protocolo CAN-OTA contra un transporte `MockCAN` real que reproduce un bootloader simulado completo (inicio, borrado, recepción, datos de página y ACK, fragmentos HMAC, fin de actualización con un éxito real o un `VERIFY_FAIL_REASON` concreto), las reglas de firma, las comprobaciones de integridad de la imagen, el firmware incluido en `firmware/` frente a sus manifiestos, los comandos SWD/JTAG construidos con `dry_run`, los archivos de idioma y los paneles Qt Quick. Tres scripts en la raíz (`verify_qt_*.py`) manejan los paneles Qt de extremo a extremo. La CI ejecuta además `ruff check`, `python -m mypy` y `tools/ci_validate.py`. `MockCAN` es solo un modelo escrito a partir del protocolo: es más permisivo que el bootloader real, así que una ejecución en verde no sustituye una prueba en una placa real.

## 🏗️ Compilación y publicación

`build_exe.bat` / `build_exe.sh` construyen un programa independiente con PyInstaller (ambos pasan `--noconfirm`, así que recompilar sobre un `dist/URTC_Flasher` existente lo sustituye directamente); `build-test.sh` / `build-test.bat` comprueban todo sin construir nada ni cambiar una versión. La versión del programa (`FLASHER_VERSION` en `flasher_config.py`, visible en el banner de la ventana y la barra de título) solo cambia con el paso explícito `python bump.py`; ejecutar desde el código y compilar nunca la tocan. Consulta `CHANGELOG.md` para el historial de versiones.

## 📂 Estructura del repositorio

<p align="center">
  <img src="images/repository-structure.svg" alt="Estructura del repositorio URTC-FLASHER" width="100%">
</p>

<details>
<summary>Versión en texto del árbol</summary>

```text
URTC-FLASHER/
├── urtc_flasher.py                                    punto de entrada
├── qt_flasher.py                                      el panel Qt Quick
├── flasher_*.py                                       protocolo, comprobaciones, transportes, SWD, registros
├── verify_qt_*.py                                     comprobaciones de extremo a extremo de los paneles Qt
├── urtc_can/                                          protocolo, transportes y actualizaciones (copia)
├── urtc_ui/                                           ayudas de interfaz (copia)
├── firmware/                                          dónde van las imágenes (empieza vacía)
├── tests/                                             47 archivos de prueba, uno por área
├── language/                                          los ocho archivos de idioma .lng
├── assets/                                            QML, banner e icono
├── docs/                                              arquitectura, compilación y ejecución
├── logs/                                              registros de sesión (fuera de Git)
├── tools/                                             comprobación de compilación, sincronización del firmware, herramientas compartidas
├── images/                                            banner e imágenes de este README
├── .github/                                           flujo de CI y plantillas de issues y pull requests
├── test.sh test.bat                                   ejecutan las pruebas
├── run.sh run.bat                                     arrancan el programa
├── build-test.sh build-test.bat                       scripts de compilación y pruebas que no cambian nada en el repositorio
├── urtc.project.json                                  manifiesto: versión, papel, madurez y comando de compilación
├── CHANGELOG.md                                       qué cambió en cada versión
├── SECURITY.md SUPPORT.md LICENSE                     política de seguridad, soporte y licencia
├── CONTRIBUTING.md CODE_OF_CONDUCT.md                 cómo contribuir y código de conducta
├── .gitattributes .gitignore                          ajustes de Git
├── build_exe.sh build_exe.bat                         programa independiente (PyInstaller)
├── bump.py bump_version.py bump_manifest_version.py   scripts que suben la versión
├── requirements*.txt requirements*.lock               dependencias, con sus bloqueos
├── mypy.ini pytest.ini ruff.toml                      ajustes de tipos, pruebas y lint
├── urtc_config.json.example                           ejemplo de los ajustes de hardware y del idioma
├── urtc_i18n.lock.json                                bloqueo de los archivos de idioma generados
└── NOTICE LICENSE.md                                  aviso de copyright y licencia de la documentación
```

</details>

La lista anotada de cada archivo de código, una línea por archivo, está en [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## 🗺️ Hoja de ruta y límites conocidos

**Estado:** el cálculo de CRC32 y HMAC-SHA256 en esta herramienta se ha
verificado byte a byte contra la propia implementación en C del
bootloader, y el empaquetado de tramas SocketCAN se verificó contra el
formato `struct can_frame` de Linux con una prueba de empaquetado/
desempaquetado de ida y vuelta. Lo que **no** se ha probado en ninguna
de las 2 plataformas es una placa real sobre hardware real — trata el
primer intento real de flasheo con la misma precaución que darías a
cualquier herramienta nueva que hable con un bootloader: ten JTAG a mano
como respaldo. Todo lo demás descrito aquí se ha ejercitado solo contra `MockCAN`, un bootloader simulado, nunca contra una placa real.

## 🌍 Idiomas

El README y los textos existen en inglés, español, francés, italiano, alemán, chino, japonés y portugués de Portugal.

## 🔗 Proyectos relacionados

URTC se compone de repositorios independientes, cada uno con su versión, sus pruebas y su README. Esta es la familia, por grupos:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - firmware de la placa del cabezal de herramienta (25 perfiles de herramienta, bootloader CAN) y la referencia del protocolo CAN.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - el protocolo CAN escrito una sola vez como datos (especificación, tablas generadas, vectores de conformidad) y el código que comparten los programas.
  * **URTC-FLASHER** (este repositorio) - herramienta de escritorio que actualiza el firmware de la placa por CAN o por SWD/JTAG.
  * [URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY) - pasarela delante del bus CAN: solo deja pasar los identificadores de una lista, limita su frecuencia y pide una clave de sesión.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - lógica en C independiente del hardware y protocolo de órdenes para un soporte de herramientas con precalentamiento y seguimiento del ciclo de vida.
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - probador de escritorio del bus CAN en vivo que muestra los controles y la telemetría del perfil de herramienta que informa una placa.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - protocolo de tramas de sensor en C y un acompañante en Python térmico/RGB para un cabezal de inspección.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - aplicación de navegador que graba y prueba la placa por Web Serial y SLCAN, sin instalar nada.
* **Ecosystem Operations:**
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - arquitectura, interfaces, línea base de seguridad y catálogo generado del ecosistema, más las herramientas que comparan todos los repositorios.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - herramienta de escritorio que detecta, instala y actualiza los repositorios de la familia URTC, una acción explícita cada vez.

**Proyectos hermanos (independientes, con la misma base y herramientas):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - proyecto hermano: el centro de documentación de HYDRA-UMC, un ecosistema independiente que comparte base y herramientas con este
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - proyecto hermano: el centro de documentación de A.R.M.O.R., el ecosistema de seguridad, también independiente y sobre la misma base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - el perfil y el panel de estado de todos los ecosistemas

## 📚 Documentación

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnológico y pautas de codificación para un pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — los estándares de comportamiento esperados en esta comunidad.
- **[SECURITY.md](SECURITY.md)** — cómo reportar una vulnerabilidad, y las áreas reales de enfoque en seguridad de este proyecto.
- **[SUPPORT.md](SUPPORT.md)** — dónde hacer preguntas y reportar errores.
- **[LICENSE.md](LICENSE.md)** — la licencia propia de este proyecto.

## 🤝 Contribuir y comunidad

* Antes de una pull request ejecuta `URTC_CI=1 python tools/ci_validate.py`: debe pasar. Consulta [CONTRIBUTING.md](CONTRIBUTING.md) y el [código de conducta](CODE_OF_CONDUCT.md).
* El README existe en ocho idiomas: un cambio en el texto se hace en los ocho archivos, y las secciones compartidas con otros repositorios las escribe `tools/readme_sections.py` de URTC-COMMON.
* Un cambio en el protocolo CAN empieza en URTC-COMMON (`spec/can_protocol.json`) y llega a este repositorio mediante la copia comprobada.
* No describas como funcionando en una placa lo que solo se ha compilado.
* Informa de una vulnerabilidad en privado: [SECURITY.md](SECURITY.md). Preguntas, ideas e informes: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCIA

Licencia: **GPL-3.0-or-later** para el código fuente, **CC BY-SA 4.0** para esta
documentación - ver `LICENSE` en este repositorio, o la sección
"Licencia y Avisos de Copyright" al final de este documento.

URTC Flasher es (c) 2026 JuanenRac (Electro Hobby 3D). Este aviso debe
incluirse en cualquier distribución de este proyecto o trabajos
derivados.

Este proyecto consiste en código fuente y su propia documentación,
disponibles bajo licencias distintas - cada una adecuada a lo que
realmente cubre:

1. El código fuente (`urtc_flasher.py` y cada módulo `flasher_*.py`)
   y cualquier binario compilado a partir de él vía
   `build_exe.bat`/`build_exe.sh` están disponibles bajo la
   **GNU General Public License v3.0 or later (GPL-3.0-or-later)**. Texto completo en
   https://www.gnu.org/licenses/gpl-3.0.html.

2. La documentación (este README y sus propias traducciones -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`, `README_por.md`)
   está disponible bajo **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Texto completo en
   https://creativecommons.org/licenses/by-sa/4.0/.

Esta herramienta es el compañero de flasheo CAN-OTA/SWD-JTAG del
proyecto [URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
- ver el propio repositorio de ese proyecto para el firmware de la
placa, los diseños de hardware, y la documentación completa del
protocolo contra la que trabaja esta herramienta. El propio firmware de
URTC es GPL-3.0-or-later y sus diseños de hardware son CERN-OHL-S v2; la propia
licencia de esta herramienta aquí no se extiende a ese proyecto
separado, y viceversa. También existe una alternativa basada en web que
cubre terreno similar en
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Si construyes sobre este proyecto, ten en cuenta la separación de
licencias: los cambios de código deberían mantenerse GPL-3.0-or-later, los
derivados de documentación deberían mantenerse CC BY-SA - cada uno con
atribución de vuelta a este proyecto y su autor.
