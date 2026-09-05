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
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Lenguaje-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Tkinter%20%7C%20Qt%20Quick-38d4e6.svg" alt="Tkinter and Qt Quick">
  <img src="https://img.shields.io/badge/Protocolo-CAN--OTA-orange.svg" alt="CAN-OTA">
</p>


**Versión:** 0.1.0 (la versión de esta herramienta - se muestra en el banner
de la ventana y en la barra de título, se controla por separado de la
versión del firmware de la placa URTC que escribe. Sigue un esquema X.Y.Z
donde el número de parche sube automáticamente en cada build real via
build_exe.bat/build_exe.sh - ver CHANGELOG.md para el historial de
versiones y bump_version.py para la regla exacta de acarreo)

**Autor:** JuanenRac (Electro Hobby 3D) &lt;electrohobby3d@gmail.com&gt;

Licencia: **GPL-3.0** para el código fuente, **CC BY-SA 4.0** para esta
documentación - ver `LICENSE` en este repositorio, o la sección
"Licencia y Avisos de Copyright" al final de este documento.

Una pequeña herramienta GUI multiplataforma para actualizar el firmware
de la placa URTC por bus CAN. Implementa exactamente el protocolo del
bootloader de `docs/CANBUS.TXT`: la verificación de HardwareID, la firma
HMAC-SHA256, el flujo de actualización con slot de respaldo de imagen
dorada, el progreso en vivo mediante los mensajes de latido del
bootloader, y una consulta de versión (identifica si la aplicación *o*
el bootloader de esta placa se anuncia por CAN) para que puedas ver qué
hay instalado actualmente antes de decidir qué flashear.

Dos formas de hablar con la placa, ambas usando el mismo protocolo por
debajo:

- **Serie / SLCAN** — funciona en Windows y Linux. Necesita un adaptador
  USB-CAN con firmware SLCAN, conectado como puerto serie virtual.
- **SocketCAN** — **solo Linux**, y solo se muestra en la interfaz de la
  herramienta en Linux. Habla directamente con una interfaz de red del
  kernel `can0`/`slcan0`. Si tu adaptador ya ejecuta firmware
  `gs_usb`/candleLight (la mayoría de las placas CANable lo hacen de
  fábrica), esta ruta **no necesita reflashear el adaptador en
  absoluto** — el propio driver de Linux lo gestiona de forma nativa.

**Estado:** el cálculo de CRC32 y HMAC-SHA256 en esta herramienta se ha
verificado byte a byte contra la propia implementación en C del
bootloader, y el empaquetado de tramas SocketCAN se verificó contra el
formato `struct can_frame` de Linux con una prueba de empaquetado/
desempaquetado de ida y vuelta. Lo que **no** se ha probado en ninguna
de las 2 plataformas es una placa real sobre hardware real — trata el
primer intento real de flasheo con la misma precaución que darías a
cualquier herramienta nueva que hable con un bootloader: ten JTAG a mano
como respaldo.

## 1. 🔌 Consigue que tu adaptador hable CAN
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

## 2. 💻 Instalar y ejecutar
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

Dentro del panel de conexión, la aplicación también muestra la marca animada
oficial de HYDRA-UMC. Su fuente SVG mantenida es
`assets/HYDRA_UMC_ICON.svg`; doce fotogramas PNG incluidos conservan la
animación en Tkinter y en el ejecutable autónomo sin añadir una dependencia
gráfica en tiempo de ejecución. El icono nativo URTC de ventana/barra de
tareas se mantiene estático por diseño.

### Panel visual de control

El panel compartido de comandos **Qt Quick** está disponible para el flujo
real completo, no solo CAN-OTA:
~~~
python urtc_flasher.py --qtquick
~~~
Utiliza el mismo transporte de producción, validación y código de flasheo
firmado que la interfaz establecida - CAN-OTA, descubrimiento SWD/JTAG de
solo lectura, Board Snapshot, las 4 escrituras de configuración de
dispositivo y la programación completa SWD/JTAG (borrado/escritura, dry
run, copia de seguridad antes de borrar, comprobación RDP) son todas reales
aquí, no un subconjunto. La interfaz predeterminada sigue siendo Tkinter,
pero ya nada es exclusivo de Tkinter.

El flujo consolidado CAN-OTA y SWD/JTAG se conserva, ahora sobre una
superficie de control azul marino/cian: cabecera de producto, tarjeta de
conexión de alto contraste, tablas de firmware legibles, registro de
verificación oscuro y canal de progreso visible. Es una mejora visual y de
accesibilidad; no modifica el protocolo de bootloader ni la seguridad física.

### Barra de menú

- **Archivo** - Guardar registros (el registro en pantalla como texto
  plano; para un paquete más completo que incluya diagnósticos del
  sistema y el archivo de firmware seleccionado actualmente, ver
  "Diagnósticos" más abajo), y Salir.
- **Idioma** - cambia entre los 7 idiomas disponibles (ver "Idioma" más
  abajo para saber cómo funcionan las traducciones).
- **Ayuda** - Readme (abre este archivo en una ventana de solo lectura;
  recoge automáticamente una versión traducida en cuanto exista una para
  el idioma actual), GitHub de URTC (abre el repositorio del proyecto en
  tu navegador), Licencia (la licencia GPL-3.0 de esta herramienta,
  leída desde el propio archivo `LICENSE` del repositorio), y Acerca de
  (versión y autor).

**Al arrancar**, el banner se muestra centrado en pantalla durante 5
segundos antes de que aparezca la ventana principal - no forma parte de
la ventana principal en sí (por eso la ventana es bastante compacta para
todo lo que realmente hace). El icono de ventana/barra de tareas es un
diseño pequeño independiente (`assets/urtc_icon.png`/`.ico`), no el
banner reducido - la ilustración completa del banner no se sostiene bien
a 16-32px.

**Idioma**: inglés por defecto.
Se cambia mediante el menú **Idioma** (en la barra de menú en la parte
superior de la ventana) en vez de un desplegable en la ventana principal
- se guarda inmediatamente en `urtc_config.json` (el mismo archivo usado
para los overrides técnicos de hardware — la preferencia de idioma
simplemente vive junto a esos), y se aplica en el siguiente arranque.
Las traducciones viven en archivos de texto plano bajo `language/`
(`english.lng`, `spanish.lng`, `italian.lng`, `french.lng`,
`german.lng`) como pares simples `CLAVE=Valor`, uno por línea - las
líneas que empiezan con `#` y las líneas en blanco se ignoran, y un `\n`
literal dentro de un valor se convierte en un salto de línea real (usado
por el puñado de mensajes de diálogo multilínea). Editable directamente
si una traducción necesita corregirse, o como punto de partida para otro
idioma (añade `language/<nombre>.lng`, añade `("<nombre>", "Nombre
Nativo")` a `AVAILABLE_LANGUAGES` cerca del principio de
`flasher_config.py`, y pon `"language": "<nombre>"` en
`urtc_config.json`). Una clave que falte en un archivo de idioma cae de
vuelta a mostrar el nombre de esa misma clave en vez de fallar, y un
archivo de idioma ausente o ilegible (edición defectuosa, nombre de
archivo equivocado) cae de vuelta al inglés para toda la interfaz - de
cualquier forma la herramienta se mantiene usable mientras se resuelve
el desajuste.

Tkinter (el toolkit de la GUI) viene incluido con Python en Windows,
pero en distros de la familia Debian/Ubuntu es un paquete del sistema
operativo separado:
```
sudo apt install python3-tk
```
(Fedora: `sudo dnf install python3-tkinter`. Arch: `sudo pacman -S tk`.)
`build_exe.sh` comprueba esto por sí mismo y te avisa si falta en vez de
fallar a mitad de camino.

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

## 3. 📁 Dónde van los archivos de firmware
Esta herramienta espera una carpeta `firmware/` justo al lado de
`urtc_flasher.py`, en la raíz de este mismo repositorio:

```
├── assets/
│   ├── URTC_LOGO_FLASHER.svg      <- fuente del banner (vectorial)
│   └── urtc_banner.png            <- se muestra en la parte superior de la ventana, renderizado desde el .svg de arriba
├── firmware/
│   ├── URTC_V1.1_F303CC.bin      <- pon los archivos .bin nuevos aqui
│   └── URTC_SLAVE_APP.bin        <- app del chip esclavo de expansion, si aplica
├── logs/                          <- se crea automaticamente, un archivo por sesion
├── urtc_config.json               <- opcional, no incluido por defecto (ver "Cambiar la clave HMAC" mas abajo)
├── urtc_flasher.py                <- punto de entrada: argumentos CLI, pantalla de bienvenida, configuracion de la ventana principal
├── flasher_config.py              <- E/S del archivo de configuracion, carga de idioma, constantes del protocolo
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- envoltorios de STM32CubeProgrammer / pyOCD
├── flasher_validation.py          <- validacion de archivos de firmware (.bin/.hex/.elf)
├── flasher_protocol.py            <- la propia maquina de estados de CAN OTA, tanto para la placa principal como (relevado a traves de su propio puente I2C) el chip esclavo de expansion
├── flasher_github.py               <- descarga firmware desde el propio repositorio de GitHub de este proyecto
├── flasher_gui.py                 <- la ventana principal (FlasherGUI) y su barra de menu
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

`assets/urtc_banner.png` es opcional - si falta, la herramienta
simplemente arranca sin banner en vez de fallar. Se carga mediante el
soporte nativo de PNG de tkinter (Tk 8.6+, que incluye toda versión
actual de Python), no Pillow, así que no añade una dependencia nueva.
Tanto `build_exe.bat` como `build_exe.sh` ya empaquetan `assets/` en el
ejecutable independiente mediante el `--add-data` de PyInstaller, así
que funciona igual tanto si ejecutas desde el código fuente como desde
un binario compilado.

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
| URTC_V1.1_F303CC.bin | 30.9 KB | ✓ parece válido |
| URTC_SLAVE_APP.bin | 12.4 KB | ✓ parece válido |
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
  **Descargar de GitHub...** obtiene el listado de archivos actual
  directamente desde la propia carpeta `firmware/` de este proyecto
  (`github.com/JuanenRac/URTC/tree/main/firmware`) y te permite elegir
  uno para descargarlo directamente en tu propia carpeta `firmware/`
  local - luego aparece en la lista de arriba como cualquier otro
  archivo, sin necesidad de reiniciar. Usa la propia API pública de
  GitHub (sin autenticar, así que sujeta al propio límite de tasa de
  GitHub de 60 peticiones/hora si la usas mucho en poco tiempo - nada
  aquí necesita una cuenta de GitHub ni un token.

**`<nombredearchivo>.manifest.json` opcional, junto a un archivo de
firmware** (p. ej. `URTC_V1.1_F303CC.bin.manifest.json`), añade una
comprobación de cordura extra y no bloqueante: si está presente, su
campo `sha256` se compara contra el archivo real justo antes de
flashear, con `version`/`build_date` registrados junto a ello como
referencia.

```json
{"version": "1.1", "build_date": "2024-01-15", "sha256": "e5a4918c..."}
```

Un desajuste se registra como una advertencia clara, no como una parada
forzosa - esta es una comprobación de conveniencia para detectar
temprano un archivo obviamente equivocado o corrupto, no un sustituto de
la propia verificación HMAC del bootloader durante la transferencia
real, que sigue siendo la comprobación autoritativa de cualquier forma.

Añadir una compilación nueva más tarde: solo suéltala en `firmware/` y
haz clic en **Actualizar** - no hace falta reiniciar.

## 4. 🔍 Comprobar qué hay instalado actualmente
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

Lo que verás:

- **`v1.1 (application, HardwareID 0x0303CC01)`** - caso normal,
  aplicación en ejecución, todo coincide.
- **`Bootloader running, no valid firmware currently installed,
  bootloader v1.1.2`** - la placa está atascada en el bootloader sin
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

## 5. ⚡ Flasheando
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
   propios `0x210`-`0x218` de `CANBUS.TXT`), no una conexión física
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
un timeout claro en vez de un archivo silenciosamente vacío.

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

## 6. 🛠️ Programar el chip completo por SWD/JTAG (avanzado)
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

## 7. ⌨️ Modo CLI (sin interfaz gráfica)
Para pipelines de CI, bancos de pruebas, o scripting de línea de
producción donde no hay pantalla:

```
python3 urtc_flasher.py --cli --port /dev/ttyACM0 --file firmware.bin
```

```
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan}] --port PORT
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

## 8. 🔄 Fiabilidad durante una actualización CAN, y registros de sesión
Si el ACK de una página no llega dentro de la ventana normal de 3s
durante una actualización CAN, la herramienta reintenta la *espera* (no
un reenvío de los datos de la página) hasta dos veces más con una breve
espera creciente antes de rendirse, recuperándose de un ACK que se
retrasó o se perdió en un bus ruidoso sin que los datos subyacentes se
hayan perdido. Deliberadamente no reenvía los datos de la página en un
timeout - si los datos originales realmente llegaron bien y solo se
perdió el ACK, reenviar haría que el bootloader leyera esos bytes como
el inicio de la *siguiente* página, desincronizando la transferencia.
Cada reintento también comprueba el propio latido del bootloader
(enviado aproximadamente una vez por segundo) contra lo que implicaría
haber recibido la página actual por completo - cuando son consistentes,
el registro lo dice, lo cual es evidencia real de que los datos pasaron
y solo se perdió el ACK, no solo una espera más larga y una esperanza.

Cada sesión también escribe un archivo de registro con marca de tiempo
en `logs/` (`urtc_flasher_YYYYMMDD_HHMMSS.log`),
independiente del registro en pantalla - útil para entregarle una traza
completa a quien escribió el firmware si algo sale mal en el campo. Esta
carpeta se crea automáticamente y es segura de borrar; nada vuelve a
leer registros antiguos.

## 9. 📊 Diagnósticos — actividad de bus, bitrate, y paquetes de depuración
**Selector de bitrate + autodetección** (solo Serie/SLCAN): el bus de
URTC está fijo a 500 kbit/s, que sigue siendo el valor por defecto -
esto es para un adaptador mal configurado o para depurar una placa no
estándar. **Autodetección** prueba cada bitrate SLCAN estándar por turno
contra una consulta de versión y se detiene en el primero que obtiene
una respuesta real; no conectado todavía cuando haces clic en él. El
bitrate de SocketCAN se establece a nivel del sistema operativo
(`ip link`), así que este control está deshabilitado para ese
transporte - no hay nada aquí para que lo intente.

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

## 10. 🔬 SWD/JTAG — formatos de archivo, verificación de slot, y selección de sonda
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
sus manejadores de reset son `0x080030F1` y `0x0800C725`
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

## 11. 📡 Telemetría de transferencia y detalle de fallo de verificación
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

## 12. 🧹 Borrado opcional de la F-RAM antes de flashear
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

## 🔑 Cambiar la clave HMAC / el HardwareID

La clave de firma compartida vive en 2 lugares que siempre deben
coincidir: el array `HMAC_KEY` de `bootloader_common.h`, y la constante
`HMAC_KEY` de esta herramienta cerca del principio de
`flasher_config.py`. Si cambias una, cambia la otra y reconstruye/reflashea
el bootloader antes de intentar firmar nada con la clave nueva - una
imagen firmada con una clave que el bootloader no tiene siempre fallará
la verificación, de forma segura, dejando el slot principal intacto.

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
herramienta por una errata. **Este mecanismo de sustitución solo aplica
a las constantes de la propia placa principal** - los equivalentes
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

## 📸 Fotos

<p align="center">
  <img src="images/URTC_FLASHER_V1_1.png" alt="Ventana de URTC Flasher" width="700">
</p>

## 📂 Estructura del Repositorio

El directorio `assets/` también contiene `HYDRA_UMC_ICON.svg`, el origen
vectorial animado mantenido, y `hydra_umc_icon_frames/`, sus doce fotogramas
PNG empaquetados para Tkinter. `tools/render_hydra_umc_icon_frames.py` los
regenera a partir del SVG durante el desarrollo; no es necesario para
ejecutar la aplicación.

```
├── assets/
│   ├── URTC_APP_ICON.svg          <- icono compartido de app/barra de tareas (vectorial)
│   ├── URTC_LOGO_FLASHER.svg      <- fuente del banner (vectorial), se muestra centrado 5s al arrancar
│   ├── HYDRA_UMC_ICON.svg         <- origen vectorial animado HYDRA-UMC mantenido
│   ├── hydra_umc_icon_frames/     <- doce fotogramas PNG para Tkinter renderizados del SVG anterior
│   ├── qml/
│   │   └── FlasherDeck.qml        <- UI Qt Quick del deck de comandos CAN-OTA `--qtquick`
│   ├── urtc_banner.png            <- renderizado desde el .svg de arriba, se muestra en la parte superior de la ventana
│   ├── urtc_icon.ico              <- icono de la barra de tareas/ventana en Windows
│   └── urtc_icon.png              <- icono de la barra de tareas/ventana en Linux
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v0.2.5.bin     <- firmware de aplicación actual de la placa principal
│   ├── URTC_MAIN_BOOTLOADER_v0.3.4.bin   <- bootloader de la placa principal (solo SWD/JTAG, se filtra de la
│   │                                         lista de firmware CAN-OTA - ver sección 3 arriba)
│   ├── URTC_SLAVE_FIRMWARE_v0.1.4.bin    <- aplicación del chip esclavo de expansión (solo placas de expansión avanzadas)
│   └── URTC_SLAVE_BOOTLOADER_v0.1.7.bin  <- bootloader del chip esclavo de expansión
├── images/
│   ├── URTC_FLASHER_BANNER.svg    <- banner del logo mostrado en la parte superior de este README
│   └── URTC_FLASHER_V1_1.png      <- captura real de la ventana, mostrada en la sección Fotos de arriba
├── language/
│   ├── english.lng                <- idioma por defecto, pares KEY=Value en texto plano
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   └── chinese.lng
├── logs/                           <- se crea automáticamente, un archivo por sesión
├── urtc_config.json.example        <- plantilla del archivo opcional urtc_config.json de sobreescritura
│                                       (ver "Cambiar la clave HMAC / el HardwareID" arriba) - cópiala
│                                       a urtc_config.json y edítala, en vez de empezar desde cero
├── urtc_flasher.py                <- punto de entrada: argumentos CLI, pantalla de bienvenida, configuración de la ventana principal
├── qt_flasher.py                  <- front end Qt Quick - deck real de comandos CAN-OTA `--qtquick`,
│                                       reutiliza las mismas clases de transporte/validación/protocolo de abajo
├── hydra_umc_animation.py         <- widget animado de identidad HYDRA-UMC para Tkinter
├── hydra_umc_deck_widgets.py      <- widgets redondeados del command-deck HYDRA-UMC compartidos por
│                                       las superficies de diagnóstico en vivo
├── flasher_config.py              <- E/S del archivo de configuración, carga de idioma, constantes del protocolo
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- envoltorios de STM32CubeProgrammer / pyOCD
├── flasher_validation.py          <- validación de archivos de firmware (.bin/.hex/.elf)
├── flasher_protocol.py            <- la propia máquina de estados de CAN OTA
├── flasher_github.py              <- descarga firmware desde el propio repositorio de GitHub de URTC
├── flasher_gui.py                 <- la ventana principal (FlasherGUI) y su barra de menú
├── requirements.txt                <- pyserial>=3.5 (tester Tkinter) + PySide6>=6.8,<7 (deck `--qtquick`)
├── build_exe.bat                  <- compilación independiente para Windows
├── build_exe.sh                   <- compilación independiente para Linux
├── build-test.bat                 <- comprobación de build/compilación sin subir versión
├── build-test.sh                  <- lo mismo, para Linux
├── bump_version.py                <- incremento de versión tipo cuentakilómetros, ejecutado por los scripts de build
├── bump_manifest_version.py       <- sincroniza la versión de hydra-umc.project.json con la nativa (--sync)
├── URTC_Flasher.spec              <- especificación de PyInstaller usada por ambos scripts de compilación de arriba
├── docs/
│   └── CLI_REFERENCE.md           <- referencia de flags de línea de comandos
├── tools/
│   ├── ci_validate.py                    <- validación de manifest/CHANGELOG/docs usada por la CI
│   └── render_hydra_umc_icon_frames.py   <- regenera assets/hydra_umc_icon_frames/ desde el SVG (solo desarrollo)
├── README.md                      <- (versión en inglés)
├── README_spa.md                  <- este archivo
├── README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  <- otras traducciones
├── LICENSE
├── .gitattributes
└── .gitignore
```

Esta herramienta está organizada en los módulos `flasher_*.py` de arriba
por responsabilidad, puramente por legibilidad - no hay ninguna
diferencia funcional entre tenerlos como archivos separados o como uno
grande.

## 🔗 Proyectos Relacionados

Este proyecto es parte del ecosistema de robótica HYDRA-UMC del mismo autor (JuanenRac / Electro Hobby 3D). Vale la pena conocerlo, ya que una petición podría en realidad ser sobre alguno de estos en vez de sobre este repositorio.

**Proyecto Padre**
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware para la placa física del Universal Robot Tool Controller, más de 25 perfiles de herramienta por bus CAN; el padre del que este repositorio es una herramienta específica, dentro de su propia familia de herramientas CAN-bus.

**Proyectos Hermanos** — las demás herramientas de la propia familia de herramientas CAN-bus de URTC
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — herramienta de escritorio de diagnóstico CAN-bus en vivo para placas URTC, un panel por perfil de herramienta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa basada en navegador a URTC-TESTER mediante la Web Serial API, sin instalación local.

**Directamente Relacionados**
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flota con un contrato real y estable de códigos de salida, cliente real y en vivo de la propia API de HYDRA-UMC-SERVER — hace a escala de flota (el comando `flash-all`) lo que esta herramienta hace para una sola placa.

**También Forma Parte del Ecosistema**

*Hardware y Plataforma Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la placa madre física del brazo robótico: host CM5 + coprocesador STM32H745 de doble núcleo, coordinando hasta 8 brazos herramienta por CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — capa de producto reproducible sobre Raspberry Pi OS para el CM5: agente de solo lectura, config/perfiles validados, aprovisionamiento WiFi de primer contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — el contrato JSON-Schema compartido y la barrera de seguridad contra la que cada bridge valida sus comandos.

*Backend Central y Clientes*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — el backend headless real (REST/WebSocket) con el que habla de verdad cada cliente de control.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — panel de control web con visualización 3D multi-robot en tiempo real.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de mando de enjambre de escritorio (PySide6) para varios servidores a la vez, empaquetado como ejecutable independiente.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app nativa de control para Android con inicio de sesión biométrico y un compañero Wear OS emparejado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app de control para iOS/iPadOS (Flutter) con sincronización en tiempo real por WebSocket.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaz táctil nativa para la pantalla táctil DSI de 7" a bordo, embebida en el propio CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creador/editor gráfico de URDF de escritorio que envía los modelos terminados al propio catálogo de STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barrera de coordinación para flotas AGV/AMR mediante un publicador MQTT VDA 5050 real.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinador de alto nivel para celdas CNC con acceso real a estado/bytes de control GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barrera de coordinación para droides con patas/humanoides, con un emisor de comandos real para Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinador de seguridad para celdas láser que lee 3 salvaguardas GPIO reales de llave/carcasa/enclavamiento.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinador de alto nivel seguro para el flujo de placas de pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — barrera de coordinación segura para impresoras 3D Moonraker/Klipper, con comandos de trabajo reales y controlados.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinador de seguridad con un transporte ROS 2 rclpy real, importado de forma perezosa.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barrera de coordinación para UAV equipados con cámara, con un emisor de comandos MAVLink real.

*Nodo IA de Visión (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — nodo de integración para el pipeline de visión Hailo-8, con una comprobación real de disponibilidad de hardware por etapa.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro real de modelos compilados con verificación de carga segura por arquitectura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generador real de pipeline GStreamer + config MediaMTX, con una frontera de integración HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ley de corrección real de Position-Based Visual Servoing, con puerta de seguridad según el estado de zona previo.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — comprobación real de invasión de zona y solicitud de E-STOP, con exigencia de vigencia de calibración.

*Nodo IA Cognitivo (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — nodo de integración para el pipeline cognitivo Hailo-10 (orquestación de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificación/decodificación real de tokens de acción y generación de trayectoria para un modelo Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analizador de intención) con un relé a Watch acotado y con confirmación.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — descomposición real de tareas basada en reglas y recuperación semántica de errores sobre códigos de error del MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — búsqueda real de documentos TF-IDF (solo librería estándar) sobre los propios documentos Markdown de este ecosistema.

*Orquestación y Enjambre*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — nodo de integración con un contrato real de informe de salud gRPC/Protobuf y una máquina de estados de misión.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — cola de trabajos real basada en prioridad con deduplicación, sobre una API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — watchdog de salud de flota real basado en gRPC, con reintento/backoff y detección de discrepancia de identidad.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planificador de rutas 3D real basado en RRT, con validación real de colisión de obstáculos/espacio de trabajo.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronización de estado real mediante CRDT LWW-Element-Map, con pruebas de propiedades para convergencia multi-celda.

*Gemelo Digital y Simulación*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — nodo de integración para el motor de gemelo digital, con un contrato real de sincronización por compatibilidad de versión.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — enclavamiento de seguridad real hardware-in-the-loop que enruta comandos entre simulación y hardware real.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática directa real y validación de límites articulares sobre un subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — generador real de escenas 2D procedurales con exportación de anotaciones YOLO/COCO.

*Datos y Analítica*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — almacén de series temporales real respaldado por sqlite3, con una API HTTP real de ingesta/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detector de anomalías real basado en FFT + línea base estadística, con monitorización de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidad sobre el histórico de DATALAKE, con exportación CSV reproducible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingesta CAN/WebSocket hacia DATALAKE, con deduplicación por secuencia.

*Pasarela Industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — nodo de integración que retransmite a protocolos industriales, con una capa real de lista blanca de comandos/contrapresión.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espacio de direcciones OPC-UA real, verificado con una sesión de cliente real del protocolo binario.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real con autenticación por cliente opcional y ACL de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML reales `/probe` y `/current` de MTConnect, con salida en modo degradado.

*Herramientas Complementarias y Operaciones del Ecosistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — paneles de Resúmenes Inteligentes y Resaltado de Anomalías sobre DATALAKE/ANOMALY-DETECTOR, con un respaldo estadístico honesto.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compañera de WearOS con alertas hápticas reales y un relé de voz al teléfono emparejado.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware para un rack de montaje de placas con decodificación real de ID de herramienta y lógica de precalentamiento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware más un compañero de visión real en Python para un cabezal de inspección térmica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — herramienta administrativa de escritorio que descubre, clona y actualiza cada repositorio de este ecosistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — herramienta de escritorio Windows/Linux que construye una imagen de la CM5 lista para grabar, precargada con las versiones más actuales del ecosistema, con configuración de primer arranque de Wi-Fi/usuario/SSH al estilo de Raspberry Pi Imager.

## 📜 LICENCIA

URTC Flasher es (c) 2026 JuanenRac (Electro Hobby 3D). Este aviso debe
incluirse en cualquier distribución de este proyecto o trabajos
derivados.

Este proyecto consiste en código fuente y su propia documentación,
disponibles bajo licencias distintas - cada una adecuada a lo que
realmente cubre:

1. El código fuente (`urtc_flasher.py` y cada módulo `flasher_*.py`)
   y cualquier binario compilado a partir de él vía
   `build_exe.bat`/`build_exe.sh` están disponibles bajo la
   **GNU General Public License v3.0 (GPL-3.0)**. Texto completo en
   https://www.gnu.org/licenses/gpl-3.0.html.

2. La documentación (este README y sus propias traducciones -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`)
   está disponible bajo **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Texto completo en
   https://creativecommons.org/licenses/by-sa/4.0/.

Esta herramienta es el compañero de flasheo CAN-OTA/SWD-JTAG del
proyecto [URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
- ver el propio repositorio de ese proyecto para el firmware de la
placa, los diseños de hardware, y la documentación completa del
protocolo contra la que trabaja esta herramienta. El propio firmware de
URTC es GPL-3.0 y sus diseños de hardware son CERN-OHL-S v2; la propia
licencia de esta herramienta aquí no se extiende a ese proyecto
separado, y viceversa. También existe una alternativa basada en web que
cubre terreno similar en
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Si construyes sobre este proyecto, ten en cuenta la separación de
licencias: los cambios de código deberían mantenerse GPL-3.0, los
derivados de documentación deberían mantenerse CC BY-SA - cada uno con
atribución de vuelta a este proyecto y su autor.

---

## 📚 Documentación y Comunidad

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnológico y pautas de codificación para un pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — los estándares de comportamiento esperados en esta comunidad.
- **[SECURITY.md](SECURITY.md)** — cómo reportar una vulnerabilidad, y las áreas reales de enfoque en seguridad de este proyecto.
- **[SUPPORT.md](SUPPORT.md)** — dónde hacer preguntas y reportar errores.
- **[LICENSE.md](LICENSE.md)** — la licencia propia de este proyecto.

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
