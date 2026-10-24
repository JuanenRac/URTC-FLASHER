<p align="center">
  <img src="/images/URTC_FLASHER_BANNER.svg" alt="URTC Flasher Logo" width="100%">
</p>

# URTC Flasher (Windows / Linux)

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  🇵🇹 <b>Português</b>
</p>


<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Protocol-CAN--OTA-orange.svg" alt="CAN-OTA">
</p>


**Versão:** 0.4.0 (a versão desta própria ferramenta - mostrada no banner da
janela e na barra de título, acompanhada separadamente da versão do firmware
da placa URTC que escreve. Segue um esquema X.Y.Z em que o número de patch
é subido pelo passo explícito `python bump.py` (compilar nunca o altera)
- consulte CHANGELOG.md para o histórico de versões e bump_version.py para a
regra exata de transporte)

**Autor:** JuanenRac (Electro Hobby 3D) &lt;electrohobby3d@gmail.com&gt;

Licença: **GPL-3.0-or-later** para o código-fonte, **CC BY-SA 4.0** para esta
documentação - consulte `LICENSE` neste repositório, ou a secção "License and
Copyright Notices" no fim deste documento.

Uma pequena ferramenta GUI multiplataforma para atualizar o firmware das
placas URTC através do barramento CAN. Implementa o protocolo exato do
bootloader descrito em `docs/CANBUS.TXT` (no repositório irmão
[URTC](https://github.com/JuanenRac/URTC) contra o qual esta ferramenta é
implementada - consulte "Projetos Relacionados" perto do fim deste documento;
todas as outras referências a `docs/*.TXT` neste README apontam também para
lá): a verificação do HardwareID, o HMAC-SHA256 de chave partilhada (não uma assinatura assimétrica), o fluxo de
atualização golden-image com slot de backup, o progresso em direto através das
mensagens de heartbeat do bootloader, e uma consulta de versão (se a aplicação
*ou* o bootloader desta placa se identifica através do CAN) para que possa ver
o que está atualmente instalado antes de decidir o que escrever.

**Procurar atualizações.** O botão «Procurar atualizações» pergunta ao GitHub uma vez pela versão mais recente e só propõe a transferência se esta tiver um pacote para este sistema mais recente do que a versão instalada. O pacote só é aceite se o SHA-256 e a assinatura Ed25519 (a chave das versões, fixada no programa) forem válidos; só é instalado depois de o confirmar, nunca durante uma transferência, e a versão anterior é guardada para poder voltar atrás (e é reposta sozinha se a nova não arrancar). Nada é verificado nem instalado por si só: a verificação ao abrir é uma opção, desligada por defeito, e a confirmação só se desliga na mesma janela, depois de um aviso.

Duas formas de comunicar com a placa, ambas a falar o mesmo protocolo por baixo:

- **Serial / SLCAN** — funciona em Windows e Linux. Precisa de um adaptador
  USB-CAN com firmware SLCAN, ligado como porta série virtual.
  - Sem adaptador nem hardware, uma placa virtual faz as vezes: execute `python -m urtc_can.virtual_board`, indique o seu endereço na variável de ambiente `URTC_VIRTUAL_PORT` (por exemplo `socket://127.0.0.1:7777`) antes de iniciar o programa, ou passe-o a `--port` na linha de comandos. Aparece na lista de portas e responde como uma placa, aplicação e bootloader.
- **SocketCAN** — **apenas Linux**, e só é mostrado na UI da ferramenta em
  Linux. Comunica diretamente com uma interface de rede `can0`/`slcan0` do
  kernel. Se o seu adaptador já corre firmware `gs_usb`/candleLight (a maioria
  das placas CANable fá-lo de origem), este caminho **não precisa de qualquer
  reflash do adaptador** — o próprio driver do Linux trata disso nativamente.

**Estado:** o cálculo de CRC32 e HMAC-SHA256 nesta ferramenta foi verificado
byte a byte contra a própria implementação em C do bootloader, e o
empacotamento das tramas SocketCAN foi verificado contra o layout de `struct
can_frame` do Linux com um teste de pack/unpack de ida e volta. O que **não**
foi testado em nenhuma das plataformas é uma placa real com hardware real —
trate uma primeira tentativa de flash no mundo real com o mesmo cuidado que
daria a qualquer ferramenta nova a comunicar com um bootloader: tenha um JTAG à
mão como alternativa. Tudo o resto descrito aqui foi exercitado apenas contra `MockCAN`, um bootloader simulado, nunca contra uma placa real.

**Verificação de honestidade - o que realmente corre hoje:** `tests/` contém 41 ficheiros pytest (478 testes: todos passam; 76 deles são ignorados sem PySide6) - o protocolo CAN-OTA contra um transporte `MockCAN` real (`flasher_transports.py`) que reproduz uma sequência completa de bootloader simulado (start/erase/receive, dados de página + PAGE_ACK, blocos HMAC, end-update com um sucesso real ou um `VERIFY_FAIL_REASON` específico), as regras de assinatura (assinatura publicada enviada sem qualquer chave, imagem sem assinatura recusada, discrepância de sha256 do manifesto recusada antes de qualquer tráfego no barramento), as verificações de integridade da imagem e o `firmware/` incluído contra os seus manifestos. O GitHub Actions (`.github/workflows/ci.yml`) corre esta suite em cada push, e `tools/build_test.py` corre-a em `build-test.sh`/`.bat`. Os dois scripts `verify_qt_*.py` na raiz do repositório são verificações reais de ponta a ponta mantidas fora do pytest (precisam de um loop de eventos Qt real; execute-os com `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`); `verify_qt_swd_full_chip_flash.py` apenas constrói os comandos `PyOCDCLI`/`CubeProgrammerCLI` com `dry_run=True`. Nada disto foi executado contra uma placa real com hardware real neste ambiente. Consulte `CHANGELOG.md` para saber exatamente o que foi entregue até agora. O bootloader simulado (`MockCAN`) é apenas um modelo escrito a partir da descrição do protocolo: reproduz os ACK de página, a última página parcial e as tramas de leitura, mas não é o bootloader real, pelo que uma execução de testes a verde não substitui um ensaio numa placa real (a imagem oficial de 73476 bytes não se conseguia instalar e a última trama de uma cópia perdia-se enquanto os testes passavam, precisamente porque a simulação era mais permissiva do que o bootloader real).

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado e ainda não existe nenhuma placa URTC montada. Os bootloaders verificam as imagens de firmware com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica (prevista); as imagens de aplicação publicadas estão assinadas com a chave pública de desenvolvimento (`signing_key_kind: dev`), pelo que qualquer pessoa pode produzir uma imagem que o bootloader aceita; nada foi transmitido a uma placa real. Leia a [base de segurança](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

## 📋 Num relance

| | |
|---|---|
| Versão | `0.4.0` |
| Maturidade | Funcional |
| Testes | 488 |
| Tecnologia | Python / PySide6 / Qt Quick / CAN-OTA / SWD/JTAG |
| Destino | O PC de quem o usa |
| Em hardware real | Só simulado: testado com emuladores, dublês de teste ou simuladores; não há registo de execução em hardware real para esta versão |

## 1. 🔌 Fazer o seu adaptador falar CAN

O que precisa de entre isto depende da sua plataforma e do transporte que vai
usar:

**Linux, caminho SocketCAN (recomendado se o seu adaptador o suportar):**
Nada para gravar no próprio adaptador. Ative a interface uma vez por arranque
(ou adicione-a à sua configuração de rede para persistir):
```
sudo modprobe can vcan gs_usb   # gs_usb covers most CANable-family boards
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up
```
Se o seu adaptador for enumerado com outro nome que não `can0`, verifique `ip
link show` (ou `dmesg` logo depois de o ligar) para obter o nome real. Alguns
adaptadores precisam de `slcand` em vez de um driver nativo — se `ip link show`
não mostrar qualquer interface CAN depois de ligar o adaptador, este é
provavelmente o seu caso; consulte a documentação do seu adaptador para a
invocação de `slcand`, que cria uma interface `slcan0` que depois ativa da
mesma forma que acima.

**Windows, ou Linux através do caminho Serial/SLCAN:**
Um CANable Pro v2 vem por defeito com firmware **candleLight**, que comunica
com o anfitrião através do protocolo `gs_usb` - o mesmo que o driver `gs_usb`
do SocketCAN do Linux espera nativamente (ver acima). Esse protocolo **não** se
apresenta como porta série, que é o que este caminho precisa. Para usar
Serial/SLCAN em vez disso (obrigatório em Windows; opcional em Linux):

1. Descarregue firmware compatível com SLCAN para o seu adaptador (pesquise
   "canable slcan firmware" — existem alguns forks mantidos; use aquele para o
   qual a própria documentação do seu adaptador aponta).
2. Coloque o adaptador em modo DFU/bootloader (normalmente um botão BOOT
   premido durante o arranque, ou um jumper — consulte a documentação do seu
   adaptador).
3. Grave o firmware SLCAN com a ferramenta de gravação do fabricante do seu
   adaptador ou com `dfu-util`.
4. Volte a ligar — deverá agora ser enumerado como porta série: uma porta COM
   em Windows, ou ao estilo `/dev/ttyACM0`/`/dev/ttyUSB0` em Linux.

Se o seu adaptador já corre firmware SLCAN, avance diretamente para o passo 2
abaixo.

Uma linha SLCAN recebida cujo comprimento real não corresponde ao que o seu
próprio DLC declarado implica é tratada como malformada e ignorada, em vez de
ser interpretada a partir dos seus primeiros N caracteres hexadecimais
independentemente do que se segue - útil saber se estiver a depurar com um
adaptador ruidoso ou não standard.

## 2. 💻 Instalar e executar

**Windows:**
```
python -m pip install -r requirements.txt
python urtc_flasher.py
```
Ou crie um `.exe` autónomo com `build_exe.bat` (consulte esse ficheiro).

**Linux:**
```
python3 -m pip install -r requirements.txt
python3 urtc_flasher.py
```
Ou crie um binário autónomo com `./build_exe.sh` (faça-lhe `chmod +x` primeiro).

Ambos os scripts passam `--noconfirm` ao PyInstaller, pelo que reconstruir por
cima de um `dist/URTC_Flasher` existente o substitui diretamente, em vez de
ficar à espera de uma pergunta "substituir?" fácil de perder na saída de um
script.

### Painel de comando visual

O painel **Qt Quick** é a única janela do programa (testado apenas contra o simulador; as verificações de imagem usam um HMAC-SHA256 de chave partilhada). Inicia-se com:
~~~
python urtc_flasher.py
~~~
Tem uma superfície escura azul-marinho/ciano com um cartão de ligação, tabelas de firmware legíveis, um registo de verificação escuro e um canal de progresso visível, e cobre todo o fluxo: a atualização CAN-OTA da placa principal ou do escravo de expansão (a escolha do destino; a opção «a placa está a executar a aplicação», o apagamento da F-RAM e a autorização de descida de versão são só para a placa principal), uma cópia de segurança por CAN do firmware instalado, o seletor de velocidade do bus com a pesquisa só de escuta, a transferência de uma release do GitHub, um seletor de ficheiros para qualquer `.bin`, a verificação da atividade do bus, o Board Snapshot, as 4 escritas de configuração do dispositivo, a descoberta SWD/JTAG só de leitura e a programação do chip completo por SWD/JTAG (apagar/escrever, ensaio, cópia de segurança antes de apagar, verificação RDP). Cada ação que escreve na placa pede confirmação antes, a autorização de descida de versão pede uma segunda, e fechar a janela durante uma transferência volta a perguntar. Nada disto foi experimentado numa placa real. `python urtc_flasher.py --cli` é o modo sem interface (secção 7).

### Cabeçalho e ferramentas

- **Cabeçalho** - o estado da ligação, o seletor de idioma (a escolha é guardada e aplica-se no próximo arranque) e a versão.
- **Guardar registos...** e **Guardar pacote de depuração** - o registo do ecrã como texto simples, ou um zip mais completo com o diagnóstico do sistema e o ficheiro de firmware selecionado (ver «Diagnóstico» abaixo). Cada sessão é também escrita em `logs/`, e as mais recentes são mantidas.
- **Acerca do URTC Flasher** - versão e autor, com botões para **Readme** (no idioma da interface, quando existe tradução), **Licença** e a página **GitHub do URTC** do projeto.

**Idioma**: inglês por defeito.
Alterado com o seletor de idioma no cabeçalho da janela - guarda em `urtc_config.json` imediatamente (o mesmo ficheiro usado para as substituições
técnicas de hardware — a preferência de idioma fica simplesmente a seu lado),
aplicado no próximo arranque. As traduções vivem em ficheiros de texto simples
em `language/` (`english.lng`, `spanish.lng`, `italian.lng`,
`french.lng`, `german.lng`, `japanese.lng`, `chinese.lng`, `portuguese.lng`) como simples pares `KEY=Value`, um por linha -
as linhas que começam por `#` e as linhas em branco são ignoradas, e um `\n`
literal dentro de um valor torna-se uma quebra de linha real (usado pelas
poucas mensagens de diálogo de várias linhas). Gerados a partir do catálogo do URTC-COMMON (uma tradução corrige-se lá e os ficheiros são escritos de novo, nunca à mão), ou como ponto de partida para outro idioma
(adicione `language/<name>.lng`, adicione `("<name>", "Native Name")` a
`AVAILABLE_LANGUAGES` perto do topo de `flasher_config.py`, e defina
`"language": "<name>"` em `urtc_config.json`). Uma chave em falta num ficheiro
de idioma recorre a mostrar o próprio nome da chave em vez de falhar, e um
ficheiro de idioma em falta ou ilegível (edição errada, nome de ficheiro
errado) recorre ao inglês para toda a interface - em qualquer dos casos a
ferramenta continua utilizável enquanto a discrepância é resolvida.

**Permissões série em Linux:** se estiver a usar o caminho Serial/SLCAN e a
ligação falhar com "Permission denied", o seu utilizador precisa de pertencer
ao grupo que é dono dos dispositivos série (`dialout` em Debian/Ubuntu; varia
noutras distribuições):
```
sudo usermod -a -G dialout $USER
```
Termine sessão e volte a iniciá-la (a pertença a grupos é lida no início de
sessão), e depois tente novamente. A ferramenta deteta este erro específico e
mostra esta mesma solução num diálogo, mas vale a pena saber de antemão. O
SocketCAN não tem esta armadilha em particular — o acesso a uma interface ao
estilo `can0` não é controlado pelo grupo `dialout` — mas ativar a interface em
primeiro lugar (passo 1 acima) precisa de `sudo`, uma vez que é uma alteração
de configuração de um dispositivo de rede.

Usar `python -m pip`/`python3 -m pip` em vez de um `pip` simples evita um
problema comum em ambas as plataformas: o script wrapper do próprio `pip` nem
sempre está no PATH mesmo logo após uma instalação bem-sucedida, enquanto
`-m pip` encontra diretamente o módulo instalado.

## 3. 📁 Onde colocar os ficheiros de firmware

**A pasta começa vazia.** As imagens de firmware não ficam neste repositório: são os ficheiros das releases do [URTC](https://github.com/JuanenRac/URTC). A janela descarrega-as da release escolhida, e `python tools/sync_firmware.py` preenche a pasta a partir da última release oficial (ou `--release ETIQUETA`). Cada ficheiro é verificado com a assinatura da release (`.sig`, Ed25519) e os seus resumos antes de ser usado. Enquanto não existir uma release oficial, o «latest» do GitHub responde 404 e `firmware_release.json` indica a release usada em seu lugar (hoje a pré-release de bancada); apague-o, ou mude a sua etiqueta, quando for publicada uma oficial.

Esta ferramenta espera uma pasta `firmware/` mesmo ao lado de `urtc_flasher.py`,
na raiz deste mesmo repositório:

```
├── assets/
│   └── URTC_LOGO_FLASHER.svg      <- banner source (vector)
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v<version>.bin  <- put new .bin files here
│   └── URTC_*  <- tools/sync_firmware.py substitui os ficheiros URTC_* desta pasta pelos de uma release; os outros ficheiros ficam
├── logs/                          <- created automatically, one file per session
├── urtc_config.json               <- optional, not included by default (see "Changing the HMAC key" below)
├── urtc_flasher.py                <- ponto de entrada: argumentos da CLI e arranque da janela Qt Quick
├── flasher_config.py              <- config file I/O, language loading, protocol constants
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- STM32CubeProgrammer / pyOCD wrappers
├── flasher_validation.py          <- firmware file validation (.bin/.hex/.elf)
├── flasher_protocol.py            <- the CAN OTA state machine itself
├── flasher_github.py               <- lista e descarrega os assets de uma release do GitHub do URTC
├── flasher_records.py             <- registos de sessão (localização, retenção) e relatórios de atualização
├── pytest.ini / ruff.toml          <- definições do pytest e do ruff (verificações estáticas)
├── requirements.txt
├── build_exe.bat                  <- Windows standalone build
├── build_exe.sh                   <- Linux standalone build
└── README.md
```

Esta ferramenta está organizada nos módulos acima por responsabilidade,
puramente por legibilidade - não há diferença funcional entre os ter como
ficheiros separados ou como um único ficheiro grande.

Isto é deliberado: todo este repositório é autossuficiente. Se apenas quiser
gravar uma placa — num PC de chão de fábrica, a partir de uma pen USB, onde
for — pode copiar este repositório sozinho, e continua a funcionar.

**Pode manter mais do que um `.bin` aí dentro.** Cada ficheiro de firmware de
aplicação é verificado e listado - a ferramenta não se limita a agarrar no que
encontra, e os binários de bootloader (qualquer coisa com "BOOTLOADER" no nome
do ficheiro - `URTC_BOOTLOADER.bin`, `URTC_SLAVE_BOOTLOADER.bin`) são
completamente filtrados desta lista, uma vez que o CAN-OTA só grava firmware de
aplicação; uma atualização do bootloader precisa antes de SWD/JTAG (secção 6
abaixo). No arranque (e sempre que clicar em **Refresh**), cada `.bin`
restante em `firmware/` é verificado com o mesmo teste de plausibilidade que o
próprio bootloader aplica a uma imagem nova (os seus primeiros 4 bytes têm de
parecer um verdadeiro stack pointer inicial para a RAM deste chip, e o seu
tamanho tem de caber no slot principal). Cada ficheiro aparece na lista com um
✓ ou ✗ claro e o motivo:

| Ficheiro | Tamanho | Estado |
|---|---|---|
| URTC_MAIN_FIRMWARE_v<version>.bin | 71.8 KB | ✓ parece válido |
| URTC_SLAVE_FIRMWARE_v0.1.9.bin | 33.9 KB | ✓ parece válido |
| notes.txt.bin | 0.1 KB | ✗ a primeira palavra não parece um stack pointer válido |

- **Exatamente um ficheiro passa na verificação** → é selecionado por si no
  momento em que a ferramenta arranca. Um ficheiro inválido sozinho na pasta
  *não* é selecionado automaticamente só porque não há mais nada a competir
  com ele.
- **Mais do que um ficheiro válido** → nada é selecionado automaticamente;
  escolha da lista o que pretende.
- **Seleciona um ficheiro de aspeto inválido mesmo assim** → a ferramenta pede
  primeiro confirmação. Esta verificação existe para apanhar erros óbvios
  (ficheiro errado, transferência truncada, um marcador vazio) - não consegue
  apanhar tudo (um ficheiro corrompido mas plausível, ou um assinado com a
  chave errada), que é para o que servem as próprias verificações CRC32/HMAC do
  bootloader durante a transferência real.
- **Nada encontrado, ou quer um ficheiro de um local completamente diferente**
  → use o botão **Browse .bin...**, que funciona independentemente de onde o
  ficheiro realmente esteja (e executa a mesma verificação de validação em
  qualquer dos casos).
- **Quer a build mais recente sem a procurar por si** → **Download
  from GitHub...** lista os ficheiros anexados à última release do GitHub
  do repositório URTC (`github.com/JuanenRac/URTC/releases`; os binários de
  firmware são publicados como assets da release, não são guardados no
  git) e deixa-o escolher um para descarregar diretamente para a sua pasta
  `firmware/` local - aparece depois na lista acima como qualquer outro
  ficheiro, sem necessidade de reiniciar. Escreva uma etiqueta de release
  (por exemplo `v0.3.5`) na caixa no topo da janela e prima **Carregar**
  para listar outra release em vez da última. O `.sha256` e o
  `.manifest.json` da imagem são descarregados juntamente com ela. Só são
  aceites ficheiros dos servidores do próprio GitHub (`github.com` e os
  servidores de armazenamento de assets para onde redireciona), e um
  ficheiro cujo tamanho difira do anunciado pela release é descartado.
  Usa a API pública do próprio GitHub (sem autenticação, pelo que sujeita
  ao limite de 60 pedidos/hora do GitHub se a usar muito num curto
  intervalo; uma variável de ambiente `GITHUB_TOKEN` aumenta-o) - nada
  aqui precisa de uma conta GitHub.

Cada ficheiro de uma release oficial tem uma assinatura de release (`<ficheiro>.sig`, Ed25519): o flasher verifica-a quando existe e recusa uma errada. Um conjunto sem assinaturas, como uma pré-release de bancada, só é aceite por `tools/sync_firmware.py` com `--allow-unsigned`.

**`<filename>.manifest.json` e `<filename>.sha256`, ao lado de cada ficheiro
de firmware** - publicados pela build do URTC para cada imagem (e
descarregados juntamente com ela do GitHub). O manifesto contém a versão, o
`sha256` e, para imagens de aplicação, o valor `hmac_sha256` que o bootloader espera (um HMAC-SHA256 de chave partilhada, não uma assinatura assimétrica; `signing_key_kind: dev` indica a chave pública de desenvolvimento):

```json
{"component": "main_application", "version": "<version>", "sha256": "b48d4cd5...", "hmac_sha256": "b63a701e...", "signing_key_kind": "dev"}
```

Ambos os digests são verificados mesmo antes da gravação e uma discrepância
**recusa a gravação** antes de qualquer coisa ser enviada para o barramento
(ficheiro errado, transferência corrompida ou manifesto desatualizado). A
assinatura publicada é a que é enviada ao bootloader, e a versão do manifesto
é a que lhe é reportada. Um ficheiro sem manifesto (a sua própria build) só é
gravado se uma chave de assinatura estiver definida em `urtc_config.json` -
consulte "Changing the HMAC key" abaixo.

Adicionar uma nova build mais tarde: basta largá-la em `firmware/` e clicar em
**Refresh** - sem necessidade de reiniciar.

## 4. 🔍 Verificar o que está atualmente instalado

> No painel Qt Quick, as portas dos dois transportes (adaptadores série e, em Linux, interfaces SocketCAN) estão numa só lista, e as consultas desta secção são feitas por **LER ESTADO DA PLACA**, que pede de uma vez a versão, os contadores de erro CAN, o tipo de placa de expansão, a variante MLX9064x e a informação do periférico e os mostra no instantâneo da placa. Os guardados da secção de configuração do dispositivo escrevem os valores.

Se estiver em Linux e o SocketCAN estiver disponível, verá uma escolha de
**Transport** no topo - escolha Serial/SLCAN ou SocketCAN antes de ligar. Em
Windows esta linha nem sequer aparece; Serial/SLCAN é a única opção.

Clique em **Connect**, e a ferramenta pergunta automaticamente à placa o que
está atualmente a correr (CAN ID `0x7F8` → `0x7F9` - consulte
`docs/CANBUS.TXT`). Isto funciona quer a placa esteja a correr a sua aplicação
normalmente *quer* esteja parada no bootloader, pelo que não precisa de
provocar um reset só para descobrir. Clique em **Query** a qualquer momento
depois para verificar novamente (útil logo após a conclusão de uma gravação,
para confirmar que a nova versão realmente ficou).

**Quando é o próprio bootloader que responde** (placa parada no bootloader, sem
correr a sua aplicação), reporta também a sua própria versão - algo separado
da versão da aplicação instalada, acompanhada através dos seus próprios
`BOOTLOADER_VERSION_MAJOR/MINOR/PATCH` em `bootloader_common.h` e enviada como
uma segunda trama (`0x7FA`) logo a seguir a `0x7F9`. A aplicação em execução
nunca a envia - não tem forma de saber a versão de um bootloader atualmente
gravado a não ser perguntando ao próprio bootloader, pelo que isto só aparece
quando a placa está efetivamente parada aí (logo após `0x7F0`, ou num arranque
limpo antes de saltar para a aplicação).

**O número de patch.** Uma placa com firmware 0.3.5 ou posterior envia
também o número de patch da aplicação instalada (trama `0x7E9`, logo a
seguir a `0x7F9`), pelo que a janela e o registo mostram o
`maior.menor.patch` completo (por exemplo `v0.3.5`) em vez de
`maior.menor`; o patch de uma imagem é a terceira parte da versão do seu
manifesto. Antes de uma atualização, o registo mostra `instalada -> nova`
nesse formato, e o patch só entra no aviso "mais antiga do que a
instalada" quando ambos os lados o têm. Uma placa anterior ao patch
responde sem ele e é mostrada exatamente como antes. Quando o bootloader
anuncia (indicador na mesma trama) que lê o patch, a trama de fim de
atualização transporta-o no byte alto do campo menor; qualquer outro
bootloader, e qualquer imagem sem patch, recebem a trama de dois números
inalterada. A resposta de versão do escravo de expansão (`0x218`) tem a
mesma extensão opcional. Isto segue a descrição do protocolo e só foi
testado com o simulador; não foi experimentado numa placa real.

O que verá:

- **`v0.2 (application, HardwareID 0x0303CC01)`** - caso normal, aplicação em
  execução, tudo coincide.
- **`Bootloader running, no valid firmware currently installed, bootloader
  v0.1.2`** - a placa está presa no bootloader sem nada para onde saltar
  (chip em branco, ou todas as verificações do slot principal falharam). Esta
  é exatamente a situação que esta ferramenta existe para resolver - grave.
  A versão do bootloader mostrada aqui é a do próprio bootloader, sem relação
  com a versão da aplicação cujas verificações falharam.
- **`⚠ HardwareID mismatch!`** mostrado a vermelho - algo respondeu, mas o seu
  HardwareID não coincide com o que esta ferramenta espera. Não grave sem
  perceber primeiro porquê; o bootloader rejeitaria a atualização de qualquer
  forma, mas uma discrepância aqui pode também significar que está a apontar
  para a placa completamente errada.
- **Sem resposta** (vermelho) - placa sem resposta, bitrate errado, ou não
  realmente ligada. Verifique a ligação física e, no caminho SocketCAN, que a
  interface está realmente ativa (`ip link show`).

**Placa de expansão:** uma lista pendente e um par Query/Save separados,
mesmo abaixo da verificação de versão. Lê e define qual das 7 configurações
possíveis de `CONN_EXPANSION` (nenhuma, ou uma de 6 variantes reais - consulte
`EXPANSION.TXT`) está fisicamente instalada, através do CAN
(`0x1A0`/`0x1A1`). Não existe forma elétrica de a placa detetar isto por si,
pelo que tem de lhe ser indicado - isto vive aqui (e não apenas no `URTC
Tester`) uma vez que é um passo único de configuração de hardware mais
naturalmente feito juntamente com uma atualização de firmware. **Save** pede
primeiro confirmação, uma vez que isto persiste entre ciclos de alimentação
até ser explicitamente alterado outra vez.

**Variante do sensor MLX9064x:** com a mesma forma que o controlo da placa de
expansão logo acima - uma lista pendente e um par Query/Save que lê/define qual
dos 3 sensores térmicos da família MLX9064x (ou nenhum) está realmente
montado, através do CAN (`0x1A6`/`0x1A7` - consulte `CANBUS.TXT`). Só tem
significado quando a placa de expansão acima está definida para uma variante
Advanced ou para Basic+MLX9064x; o próprio firmware da placa ignora
totalmente esta definição em qualquer outro tipo de placa de expansão. "None
installed" (o valor seguro por defeito) deliberadamente não recorre a assumir
MLX90640 - uma placa com um MLX90640 real ligado precisa que isto seja
definido explicitamente, uma vez, da mesma forma que o próprio tipo de placa de
expansão.

## 5. ⚡ Gravação

1. **Connect**: escolha Serial/SLCAN ou SocketCAN (apenas Linux), depois a
   porta/interface, e clique em Connect. Para Serial/SLCAN isto abre o canal
   CAN a 500 kbit/s (a velocidade fixa do barramento do URTC); para SocketCAN
   espera-se que a interface já esteja a esse bitrate (passo 1 acima) - esta
   ferramenta não o define. Em ambos os casos, a versão atual é consultada
   automaticamente - consulte a secção 4 acima.
2. **Escolha um alvo de gravação**: "This board (main)" ou "Expansion slave" -
   por defeito a placa principal, o caso de longe mais comum. A opção slave
   só alcança alguma coisa numa variante de placa de expansão Advanced
   (TMC2209+STM32F303CBT6 ou TMC5160A+STM32F303CBT6) - a atualização é
   retransmitida através da própria ponte I2C da placa principal para o chip
   slave (os próprios `0x210`-`0x219` de `CANBUS.TXT`), não por uma ligação
   física separada. "Erase F-RAM before flashing" (passo 4 abaixo) desativa-se
   automaticamente quando Slave é escolhido - o chip slave não tem F-RAM
   própria para apagar.
3. **Selecione o firmware**: escolha da lista detetada, ou use Browse -
   consulte a secção 3 acima para saber exatamente como funcionam a deteção e
   a validação.
4. **Flash**:
   - Deixe "Board is currently running the application" marcado se a placa
     estiver ligada e a funcionar normalmente - a ferramenta envia primeiro o
     trigger de payload mágico `0x7F0` (ou `0x210`, retransmitido ao slave, se
     Slave for o alvo selecionado), que desliga em segurança todos os
     atuadores antes de reiniciar para o bootloader.
   - Desmarque-o se a placa já estiver parada no bootloader (logo após uma
     gravação JTAG nova, ou se a verificação de versão acima mostrou "no
     valid firmware currently installed").
   - Clique em **Flash Firmware** e confirme - o diálogo de confirmação indica
     qual o alvo que está prestes a gravar, por isso confirme duas vezes que
     corresponde ao que realmente pretendia selecionar. O registo mostra cada
     passo do protocolo; a barra de progresso acompanha o progresso da escrita
     página a página durante a transferência, e depois o progresso da cópia
     durante a cópia final do backup para o slot principal.

Se a verificação falhar em qualquer ponto (CRC32, HMAC, ou discrepância de
HardwareID), o slot principal do bootloader nunca é tocado - a placa continua a
correr o firmware que já tinha. É sempre seguro simplesmente tentar outra vez.

**Back up Firmware (CAN)**: lê de volta, através do barramento e sem
modificações, o firmware atualmente instalado e guarda-o como um ficheiro
`.bin` - o equivalente CAN do próprio "back up entire flash before erasing" da
secção SWD (secção 6 abaixo), pela mesma razão. Vale a pena fazê-lo antes de
qualquer atualização, especialmente antes de um downgrade deliberado (abaixo),
uma vez que é a única forma de recuperar mais tarde os bytes exatos de hoje se
já não tiver o ficheiro que os produziu. Apenas placa principal, e apenas
enquanto a placa está efetivamente parada no bootloader - requer um bootloader
que implemente `0x7FE`/`0x7FF` (consulte `docs/CANBUS.TXT`); um mais antigo
simplesmente nunca responde, o que se manifesta como um timeout claro em vez
de um ficheiro silenciosamente vazio. Na prática, isto significa que a cópia funciona numa placa sem aplicação válida ou que ficou a meio de uma atualização: com uma aplicação válida o bootloader salta para ela cerca de 600 ms depois do reset, a menos que chegue uma trama de início de atualização (`0x7F1`), e esta ferramenta não tem nenhum botão que mantenha o bootloader à espera (isso exigiria uma alteração no bootloader). Para uma placa a funcionar normalmente, faça a cópia da flash por SWD/JTAG (secção 6).

**Avisos de versão e de assinatura**: antes da transferência a ferramenta pergunta à placa o que está instalado e regista "instalada vX.Y -> nova vA.B"; se a versão nova for mais antiga, avisa que o bootloader a recusará a menos que o downgrade seja permitido e sugere fazer primeiro uma cópia de segurança. Uma imagem cujo manifesto diz estar assinada com a chave de desenvolvimento PÚBLICA (as imagens oficiais incluídas estão) mostra um aviso a vermelho por baixo do nome do ficheiro; defina `"require_production_signature": true` em `urtc_config.json` para recusar totalmente essas imagens. Quando a placa responde a partir do bootloader sem firmware válido, é selecionada a imagem oficial mais recente da placa principal encontrada em `firmware/`, para a verificar e gravar. Depois de cada atualização bem-sucedida é escrito um pequeno relatório (`logs/urtc_update_report_*.json`: versão da ferramenta, operador, nome, tamanho e SHA-256 da imagem, versões antes e depois); leva o seu próprio SHA-256 para que uma edição se note, mas não é uma assinatura.

**Instalar deliberadamente uma versão mais antiga**: o bootloader normalmente
rejeita uma imagem validamente assinada se esta declarar uma versão mais antiga
do que a já instalada (motivo de falha de verificação "rollback rejected") -
isto impede que uma versão com uma vulnerabilidade entretanto descoberta seja
reintroduzida. Se precisar genuinamente de reverter para uma versão mais
antiga e ainda de confiança, marque **"Allow downgrade (bypass anti-rollback)
for this update"** (Target: apenas placa principal) antes de gravar - aparece
um segundo diálogo de confirmação, uma vez que isto contorna deliberadamente
uma verificação de segurança. Isto continua a enviar a imagem antiga completa
através da transferência normal, apenas levanta a verificação da ordem de
versões para essa única tentativa (`0x7FD` - consulte `docs/CANBUS.TXT`); o
número de versão reportado à placa vem do próprio `.manifest.json` do
ficheiro quando existe um ao lado dele (consulte a secção 3 acima), recorrendo
em caso contrário à versão atualmente configurada desta própria ferramenta,
registado claramente em qualquer dos casos para que nunca seja um palpite
silencioso.

## 6. 🛠️ Programar o chip completo através de SWD/JTAG (avançado)

O painel "Program complete chip via SWD/JTAG (advanced)" do separador **SWD/JTAG
Programming** faz uma gravação completa de bring-up - apaga o chip inteiro
(mass-erase), e depois escreve de novo as imagens do bootloader e da
aplicação, nos endereços reais do chip que correspondem à seleção de **Target
chip** (ver abaixo). Isto é um **tipo de operação diferente** das secções 1-5
acima:

|  | Atualização CAN OTA (secções 1-5) | SWD/JTAG de chip completo (secção 6) |
|---|---|---|
| Autorrecuperação se interrompida | Sim - o slot de backup golden-image garante que o firmware em execução sobrevive | Não - não corre nada até ser reprogramado |
| Recuperável | Automaticamente, sem necessidade de ação | Sim - basta voltar a ligar e gravar de novo por SWD; a porta de depuração não depende do conteúdo da flash. Só um verdadeiro bloqueio permanente (byte de opção RDP2) o impediria, e nada nesta ferramenta define bytes de opção |
| Toca no bootloader | Nunca | Sim, por design |
| Precisa de | Um adaptador USB-CAN | Uma sonda SWD/JTAG (ST-Link ou semelhante) |
| Uso típico | Atualizações de firmware de rotina | Primeiro bring-up num chip em branco, ou recuperar uma placa inutilizada (bricked) |

**Target chip:** "This board (main)" ou "Expansion slave" - as mesmas 2 opções
do seletor do próprio separador CAN-OTA, mas uma escolha genuinamente separada
aqui: o SWD/JTAG precisa de uma sonda fisicamente ligada ao chip para o qual
isto está definido, uma vez que não há uma ponte (ao contrário do CAN-OTA) que
permita a uma ligação alcançar ambos. Mudar isto altera automaticamente os
endereços de flash usados:

| | Placa principal (STM32F303CC) | Slave de expansão (STM32F303CBT6) |
|---|---|---|
| Endereço do bootloader | `0x08000000` (região de 32K) | `0x08000000` (região de 18K) |
| Endereço da aplicação | `0x08008000` (região de 112K) | `0x08005000` (região de 54K) |
| String de alvo pyOCD | `stm32f303cc` | `stm32f303cb` |

Ambas as strings de alvo acima são a melhor estimativa do próprio projeto para
o nome real do alvo pyOCD de cada chip, não confirmadas contra uma instalação
pyOCD real enquanto isto foi escrito (a cobertura STM32 no pyOCD vem em grande
parte através de CMSIS-Packs em vez de alvos incorporados) - se a gravação
falhar com um erro do tipo "target not found", execute manualmente `pyocd list
--targets --name stm32f303` e `pyocd pack install <the real name>` obtém o
CMSIS-Pack certo.

**Requer um de** (a ferramenta deteta automaticamente qual está disponível e
só ativa os que encontra):
- **pyOCD** - `pip install pyocd`. Gratuito, open-source, sem instalação
  separada além do pacote pip.
- **STM32CubeProgrammer** - a ferramenta oficial da ST, instalada em separado a
  partir de [st.com](https://www.st.com). Se já a tem para outro trabalho com
  STM32, não é necessária nenhuma instalação adicional aqui.

Ambos são acionados como subprocessos de linha de comandos, não importados como
bibliotecas Python - verá o comando exato registado antes de ser executado.

**Formatos de ficheiro:** `.bin` (precisa do endereço fixo que esta ferramenta
já conhece - não o introduz) ou `.hex` (traz o seu próprio endereço, usado tal
como está). Misturar é aceitável - bootloader como `.hex` e aplicação como
`.bin`, ou vice-versa, ambos funcionam. Ambos os seletores de ficheiro validam
o ficheiro selecionado (tamanho plausível para o slot de destino e - onde o
formato permite verificá-lo com confiança - um stack pointer inicial
plausível) antes de o deixar prosseguir, tal como o seletor de firmware do
caminho CAN já fazia.

**A ligação é verificada antes de qualquer operação destrutiva**, exigindo
**prova positiva** de uma sonda/alvo real em vez de apenas a ausência de um
erro - o próprio código de saída do STM32CubeProgrammer não é um sinal fiável
de sucesso/falha por si só, pelo que uma verificação de ligação dedicada
(`pyocd list --probes`, ou um `-c port=SWD` só de ligação para o
STM32CubeProgrammer) corre antes de o passo de mass-erase alguma vez correr.
A saída de cada comando subsequente é também filtrada à procura de texto de
falha conhecido como segunda camada, caso o código de saída de uma ferramenta
por si só não seja de confiança noutra situação qualquer.

**O dry run vem ativado por defeito.** Na primeira vez, deixe-o marcado e
clique em "Flash Complete Chip" - imprime os comandos exatos no registo sem
tocar na placa. Leia-os, confirme que os caminhos e os endereços parecem
certos, *e só depois* desmarque o dry run e faça-o a sério.

**"Back up entire flash before erasing"** lê primeiro toda a região de flash
de 256KB para um ficheiro `.bin`, através do comando de leitura de memória
para ficheiro da própria ferramenta (`-r` para o STM32CubeProgrammer,
`commander savemem` para o pyOCD) - um seguro real aqui, uma vez que, ao
contrário de uma atualização CAN OTA (que o slot de backup golden-image já
protege), um apagamento do chip completo não tem outra forma de desfazer.
Desativado por defeito, uma vez que acrescenta 10-30s e não é necessário num
chip em branco/novo; vale a pena marcar antes de sobrescrever uma placa que já
está a correr alguma coisa. Se a leitura não produzir realmente um ficheiro, o
apagamento é recusado em vez de prosseguir sem o backup que pediu.

**Estado dos testes:** a lógica de verificação de ligação acima foi verificada
contra saída real do STM32CubeProgrammer (tanto um registo genuíno de ligação
bem-sucedida como uma falha documentada de "No target connected", ambos
obtidos do fórum comunitário da própria ST) e contra o cenário exato de falso
sucesso em que um utilizador real caiu. A sequência completa de
apagar/programar/verificar contra um ST-Link real e um STM32F303CC real ainda
não foi exercitada de ponta a ponta - o ambiente que escreveu isto não tem
acesso USB. Trate uma primeira tentativa real completa com a devida cautela -
uma placa de reserva/teste primeiro se tiver uma, e tenha em mente um plano de
contingência (a própria ferramenta de gravação do STM32CubeIDE, ou `st-flash`)
caso algo na sua versão específica do pyOCD ou na sua sonda não corresponda ao
que isto assume.

## 7. ⌨️ Modo CLI (headless, sem GUI)

Para pipelines de CI, bancadas de teste, ou scripting de linha de produção
onde não há ecrã:

```
python3 urtc_flasher.py --cli --port /dev/ttyACM0 --file firmware.bin
```

```
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan,python-can,mock}] --port PORT
                             --file FILE [--no-trigger] [--force]
```

Códigos de saída: `0` sucesso, `1` erro de protocolo/ligação, `2` argumentos
inválidos ou um ficheiro de firmware que falha a validação (passe `--force`
para o gravar mesmo assim), `130` cancelado com Ctrl+C. Cobre apenas o caminho
de atualização CAN OTA (secções 1-3) - o caminho SWD/JTAG de chip completo é
deliberadamente apenas GUI por agora, dado o muito mais que está em jogo se
uma execução por script errar uma combinação de ficheiro/alvo sem ninguém a
observar.

**`--transport python-can`** usa o pacote opcional `python-can` (`pip install python-can`) para PCAN, Kvaser, gs_usb/candleLight e as outras interfaces que suporta, pelo que o adaptador não tem de ser regravado com SLCAN: `--port` passa a ser `<interface>:<canal>` (por exemplo `pcan:PCAN_USBBUS1`) e o barramento abre-se a 500 kbit/s. Só está disponível na linha de comandos.

**`--transport mock`** executa toda a sequência de atualização contra um
bootloader simulado em memória em vez de uma placa real - sem adaptador, sem
porta, nada físico envolvido:

```
python3 urtc_flasher.py --cli --transport mock --file firmware.bin --no-trigger
```

Útil para testar a lógica da própria ferramenta (comportamento de repetição,
tratamento de timeouts, códigos de saída) num pipeline de CI ou antes de tocar
em hardware real - não é algo que comunique com uma placa verdadeira.
`--mock-fail 0x03` (ou qualquer outro valor `VERIFY_FAIL_REASON_*` de
`docs/CANBUS.TXT`) faz a atualização simulada falhar a verificação em vez de ter
sucesso, para testar o caminho de falha da mesma forma.

## 8. 🔄 Fiabilidade durante uma atualização CAN, e registos de sessão

Se o ACK de uma página não chegar dentro da janela normal de 3s durante uma
atualização CAN, a ferramenta volta a esperar (não reenvia os dados da
página) até mais duas vezes com um curto backoff antes de desistir. Isto só
ajuda com um ACK que apenas se atrasou: o bootloader envia cada ACK de
página uma única vez e nunca o repete, pelo que um ACK realmente perdido não
pode ser recuperado e a atualização é abortada com um erro (a placa fica no
seu bootloader e a atualização pode simplesmente ser iniciada de novo). A
ferramenta deliberadamente não reenvia os dados da página num timeout - se os
dados tivessem chegado bem, o reenvio faria o bootloader ler esses bytes como
o início da página *seguinte*, dessincronizando a transferência. Enquanto
espera, o heartbeat do próprio bootloader (enviado aproximadamente uma vez
por segundo) é comparado com o progresso que a página implicaria e o registo
indica quando coincidem; o heartbeat é uma percentagem inteira, pelo que é
apenas uma pista, não uma prova de que a página chegou, e nunca altera o
resultado.

Cada sessão escreve também um ficheiro de registo com data e hora em `logs/`
(`urtc_flasher_YYYYMMDD_HHMMSS.log`), independente do registo do ecrã - útil
para entregar um rasto completo a quem escreveu o firmware se algo correr mal
no terreno. Esta pasta é criada automaticamente e é seguro apagá-la; nada lê
registos antigos de volta. Só são conservados os 30 registos de sessão mais recentes; se não for possível escrever na pasta junto ao programa (instalação só de leitura), usa-se uma pasta por utilizador (`%LOCALAPPDATA%\URTC-Flasher\logs` no Windows, `~/.local/state/urtc-flasher/logs` nos outros sistemas).

## 9. 📊 Diagnostics — atividade do barramento, bitrate e pacotes de depuração

**Seletor de bitrate + auto-deteção** (apenas Serial/SLCAN): o barramento do
URTC é fixo a 500 kbit/s, que continua a ser o valor por defeito - isto serve
para um adaptador mal configurado ou para diagnosticar uma placa não standard.
**Auto-detect** apenas *escuta*: abre o adaptador no modo de apenas escuta do
SLCAN (`L`) em cada bitrate standard por vez e pára no primeiro em que ouve
uma trama CAN válida, pelo que nunca transmite e não pode perturbar um
barramento em funcionamento. Por isso precisa que outros nós estejam a enviar
e que o adaptador suporte o modo de apenas escuta; num barramento em silêncio
(ou com um adaptador sem esse modo) não encontra nada e escolhe-se o bitrate
manualmente. Ainda sem ligação quando clica nele. O bitrate do SocketCAN é
definido ao nível do SO (`ip link`), pelo que este controlo está desativado
para esse transporte - não há nada aqui para ele experimentar.

**Atividade do barramento** ("Check (2s)", ao lado de Query): conta as tramas
de protocolo reais efetivamente vistas durante uma janela fixa de 2 segundos
no transporte que estiver ligado. Isto deliberadamente **não** é a mesma coisa
que uma verdadeira percentagem de carga do barramento CAN - isso precisaria de
uma consulta netlink (SocketCAN) ou de extensões específicas do adaptador
(SLCAN) para as quais esta ferramenta não tem uma forma standard e sem
dependências de obter para o controlador *do próprio adaptador*. O que dá: um
sinal genuíno e medido diretamente de "há algo a falar neste barramento, e
aproximadamente com que frequência", em qualquer dos transportes. Para o
SocketCAN em particular, mostra também o delta de 2 segundos das estatísticas
de interface do próprio Linux (`/sys/class/net/<iface>/statistics/`) -
contadores básicos de rx/tx/erro/drop que toda a interface expõe, lidos como
ficheiros simples, sem dependências adicionais. Ligar por SocketCAN lê também
`/sys/class/net/<iface>/carrier` - um ficheiro simples 0/1 que toda a
interface Linux expõe. Quando um controlador CAN entra em bus-off, o driver do
kernel chama `netif_carrier_off()`, pelo que "no carrier" aqui é prova real de
um bus-off ou de uma ligação igualmente morta, registada como aviso com o
comando de recuperação exato (`sudo ip link set <iface> down && sudo ip link
set <iface> up type can bitrate 500000 restart-ms 100`). Esta ferramenta não
executa esse comando por si - limpar um bus-off real precisa de a interface
ser desligada e voltar a ligar ao nível do kernel, o que precisa de root e
conta como alterar a configuração de rede do sistema, não algo a fazer
silenciosamente no seu nome.

**Contadores de erro (TEC/REC)** (ao lado de Bus activity): ao contrário dos
contadores do lado do adaptador acima, isto pergunta à **própria placa** pelo
Transmit/Receive Error Counter do seu controlador CAN (`0x7FB`/`0x7FC` -
consulte `docs/CANBUS.TXT`), respondido por quem estiver em execução, a
aplicação ou o bootloader. Verde significa que ambos os contadores estão a 0
(error-active, saudável); laranja significa que um ou ambos são diferentes de
zero mas inferiores a 128 (ainda error-active, mas algo está a causar
retransmissões); vermelho significa 128 ou mais (error-passive ou pior) ou
nenhuma resposta (firmware/bootloader mais antigo que ainda não implementa
`0x7FB`, ou placa não ligada). Um TEC a subir de forma constante com um REC
estável aponta tipicamente para as transmissões da própria placa a não serem
reconhecidas - nenhum outro nó no barramento, ou um problema de
cablagem/terminação/bitrate específico da ligação desta placa.

**Export Debug Bundle** (acima do registo): guarda um `.zip` com o registo
atual do ecrã, diagnósticos básicos do sistema (SO, versão do Python, que
ferramentas foram encontradas, transporte/porta/bitrate atuais), e o ficheiro
de firmware CAN atualmente selecionado - útil para entregar um quadro completo
a quem escreveu o firmware se algo correr mal no terreno, em vez de copiar o
texto do registo à mão.

## 10. 🔬 SWD/JTAG — formatos de ficheiro, verificação de slot e seleção de sonda

**Formatos de ficheiro**: os seletores de bootloader/aplicação da secção SWD
aceitam `.bin`, `.hex`, e `.elf`/`.axf`. O ELF/AXF é interpretado com uma
pequena quantidade de struct-unpacking escrito à mão (cabeçalho ELF + program
headers apenas - sem símbolos, sem section headers), deliberadamente sem usar
`pyelftools`: este projeto mantém-se com zero dependências fora da stdlib, e a
análise completa de ELF é mais do que esta verificação de plausibilidade
específica precisa. Verificado contra os `BOOTLOADER.elf`/`APP.elf` realmente
compilados a partir da build do próprio projeto - ambos validam corretamente
nos seus endereços de carga reais (`0x08000000`/`0x08008000`), e não apenas em
ficheiros de teste sintéticos. Apenas ARM de 32 bits little-endian, que é tudo
o que um alvo Cortex-M alguma vez é. O tamanho declarado de um ficheiro `.hex`
é a contagem real de bytes ocupados, não o intervalo de endereços entre o seu
registo mais baixo e o mais alto - pelo que um ficheiro esparso (um pequeno
bloco de firmware real mais um bloco distante e separado de bytes de opção ou
dados de calibração, que algumas toolchains STM32 juntam numa única
exportação) valida pelo seu conteúdo real e não pelo intervalo entre eles. Uma
imagem de firmware em bruto com uma extensão que não `.bin` (`.img`, `.rom`, ou
sem qualquer extensão - selecionável através da opção "All files" do seletor
de ficheiros) obtém o seu endereço base a partir do slot para o qual a está a
carregar, tal como um `.bin` obteria.

**Verificação de slot do bootloader/aplicação**: os seletores de ficheiro
verificam que cada imagem se destina ao slot onde está a ser colocada, e não
apenas que parece *algum* firmware válido. Uma imagem de bootloader e uma
imagem de aplicação têm ambas um stack pointer igualmente plausível - mesmo
chip, mesma RAM - pelo que essa verificação sozinha não as consegue distinguir
se uma acabar no slot da outra. O que consegue: o **reset handler** de uma
imagem ligada (linked) é um endereço real e absoluto fixado em tempo de
link, e só aponta para dentro da região para a qual foi realmente ligada.
Verificado contra os `BOOTLOADER.bin`/`APP.bin` realmente compilados do
próprio projeto: os seus reset handlers são `0x08000785` e `0x0800C0CD`
respetivamente, cada um corretamente dentro do intervalo de endereços do seu
próprio slot e fora do do outro - pelo que colocar qualquer um deles no slot
errado é apanhado e bloqueado, não aceite silenciosamente. A mesma lógica
aplica-se a `.hex`/`.elf`, verificada contra o seu próprio endereço de carga
embutido.

**Check Option Bytes** (mesmo separador SWD/JTAG Programming, apenas
STM32CubeProgrammer - o pyOCD não expõe isto da mesma forma através da CLI):
um dump `-ob displ` só de leitura, sem apagar/escrever. Assinala o nível de
RDP com o mesmo cuidado que toda esta ferramenta tem em torno do risco SWD:
- **RDP0** - sem proteção, normal para uma placa de desenvolvimento.
- **RDP1** - reversível através do Read Unprotect do CubeProgrammer, mas isso
  faz mass-erase do chip como parte da remoção - não é algo que esta
  ferramenta faça por si automaticamente.
- **RDP2** - o único bloqueio genuinamente **permanente** em todo este
  projeto. Ao contrário de todos os outros riscos documentados acima (todos
  recuperáveis por SWD), o RDP2 desativa a porta de depuração para sempre por
  desenho da própria ST. Esta verificação existe para o apanhar antes de uma
  operação de chip completo, não depois.

**Seleção de sonda** (mesmo separador): se mais do que um ST-Link/sonda estiver
ligado ao mesmo tempo, todos os comandos exigem escolher uma explicitamente na
lista pendente Probe - não existe "a que o SO calhar enumerar primeiro". Com
exatamente uma sonda ligada, é selecionada automaticamente; com zero ou várias,
clique em Refresh e escolha. Isto aplica-se tanto à gravação do chip completo
como à verificação dos bytes de opção, uma vez que ambas são suficientemente
próximas do destrutivo para que adivinhar a placa errada seja um risco real
numa bancada com vários dispositivos.

**As escritas do pyOCD são verificadas com uma leitura de volta explícita**, e
não apenas confiadas no código de saída. O próprio comando `flash` do pyOCD
salta a reescrita de páginas que já coincidem (uma otimização de velocidade,
não um relatório de verificação), pelo que esta ferramenta acrescenta um passo
`commander compare` contra ambas as imagens depois de escrever - uma
verificação genuína byte a byte, igual ao que a flag `-v` do
STM32CubeProgrammer já faz. Apenas para `.bin`: o `compare` verifica o
conteúdo da flash contra os bytes em bruto do ficheiro, o que não
corresponderia corretamente à codificação própria de um ficheiro `.hex`/`.elf`
mesmo após uma gravação bem-sucedida, pelo que esses dois formatos saltam este
passo específico e dependem da verificação interna em tempo de escrita do
próprio pyOCD.

## 11. 📡 Telemetria de transferência e detalhe de falha de verificação

**Telemetria de transferência**: o registo mostra KB/s efetivos e tempo
decorrido por página durante uma atualização CAN, mais uma linha de resumo no
fim (tempo total, KB/s médios, quantas repetições de ACK de página
ocorreram). Puramente informativo - não altera o comportamento de gravação,
apenas facilita distinguir "isto é só lento" de "algo está realmente errado"
num relance.

**Motivos específicos de falha de verificação**: se a verificação falhar durante
uma atualização CAN, o `bootloader_protocol.c` envia um byte de motivo junto
com o estado `0x05` (verify failed) - transferência incompleta, discrepância de
CRC32, discrepância de HMAC, ou discrepância de HardwareID, em vez de todas as
falhas parecerem idênticas. Consulte `docs/CANBUS.TXT` para o formato exato da
trama (`0x7F5`, DLC 2 para este estado específico). Esta ferramenta e o
bootloader concordam neste formato de trama, pelo que grave ambos em conjunto
se estiver a construir um bootloader personalizado com uma versão diferente do
protocolo.

**O mesmo detalhe para o slave de expansão**: uma atualização de slave falhada
(Target: "Expansion slave") consulta `0x219` logo depois de `0x215` reportar
`STATUS_VERIFY_FAIL`, retransmitindo o `REG_VERIFY_FAIL_REASON` do próprio
bootloader do slave - os mesmos 5 motivos que acima, apenas alcançados através
da ponte I2C em vez de lidos diretamente de uma trama CAN. Requer um
bootloader de slave que implemente `0x219` (acrescentado juntamente com o
suporte desta própria ferramenta para ele); um bootloader de slave mais antigo
simplesmente não responde a essa consulta, e esta ferramenta recorre à
mensagem genérica "verification failed".

## 12. 🧹 Apagamento opcional da F-RAM antes de gravar

A secção 3 tem uma caixa de seleção, **"Also erase the persistence F-RAM before
flashing"** - desligada por defeito. Se marcada, envia o comando de
apagamento de payload mágico (`0x192` - consulte `docs/CANBUS.TXT`) à F-RAM de
persistência FM24CL64B integrada na placa antes de a sequência de atualização
começar, apagando qualquer estado de parâmetros da ferramenta que tivesse
guardado.

**Não é necessário numa atualização normal.** Uma discrepância de versão no
layout do próprio registo guardado já é detetada e ignorada em segurança no
arranque seguinte (consulte a secção de persistência de parâmetros de
`src/F303-master/README.md`) - esta caixa existe para uma ardósia
genuinamente limpa, não porque saltá-la deixasse algo avariado.

**Só funciona enquanto a aplicação está em execução** - o próprio bootloader
não trata de todo o `0x192`, apenas o `firmware_can_global_post.c` o faz. Esta
caixa é silenciosamente ignorada (com uma linha de registo a explicar porquê)
se a caixa "board is currently running the application" acima dela estiver
desmarcada, uma vez que nesse caso se assume que a placa já está parada no
bootloader.

**Uma confirmação em falta não interrompe a gravação.** Se a trama de
confirmação do próprio comando de apagamento não voltar dentro de 2 segundos,
isto é registado como aviso e a atualização de firmware propriamente dita
prossegue na mesma - apagar é um passo secundário e opcional ao lado do
verdadeiro objetivo desta ferramenta, não algo que deva abortar uma
atualização que de outra forma teve sucesso por a sua própria trama de
confirmação se ter perdido. Verifique o estado da F-RAM em separado (o próprio
botão Query State do `URTC Tester`) se isso lhe importar.

## 🔑 Alterar a chave HMAC / HardwareID

Esta ferramenta **não guarda qualquer chave de assinatura**. A build do URTC
assina cada imagem de aplicação e publica a assinatura ao lado dela, em
`<image>.manifest.json` (`hmac_sha256`, mais `<image>.sha256`); o flasher envia
essa assinatura publicada e recusa uma imagem cujo sha256 não coincida com o
seu manifesto. Descarregar uma imagem do GitHub descarrega também ambos os
ficheiros, e `python tools/sync_firmware.py` atualiza a pasta `firmware/`
incluída a partir da build do URTC (`--check` verifica-a). Por omissão, obtém o conjunto dos assets da última release do URTC (`--release TAG` escolhe outra); em alternativa, pode passar-se como argumento uma pasta local, por exemplo uma build local do URTC. Apenas uma imagem
compilada por si, sem manifesto, numa placa de bancada, precisa de uma chave:
defina `hmac_key_hex` / `slave_hmac_key_hex` em `urtc_config.json` abaixo - sem
uma, essa imagem é recusada em vez de ser assinada com uma chave que o
bootloader não pode ter. Consulte `docs/FIRMWARE_SIGNING.TXT` do URTC. As imagens publicadas são assinadas com a chave pública de desenvolvimento (`signing_key_kind: dev`); trata-se por isso de uma verificação de chave partilhada: mostra que a imagem foi produzida por quem possui essa chave, não de quem se trata; a assinatura assimétrica (Ed25519) está prevista, não implementada.

**Ou substitua qualquer um destes valores sem tocar no script:** um
`urtc_config.json` opcional ao lado de `firmware/` pode definir a chave de
assinatura, o HardwareID, e os valores do mapa de memória - útil para uma
revisão de placa diferente, uma chave rodada, ou (para os campos do mapa de
memória) adaptar esta ferramenta a uma variante de chip ou esquema de partições
diferente, sem precisar de uma nova versão do script por implementação:
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
Todos os campos são opcionais - substitua apenas o que realmente está a mudar.
Os campos em falta recorrem aos valores por defeito incorporados desta
ferramenta. **As substituições do mapa de memória e do HardwareID aplicam-se apenas às constantes da própria placa principal** (a única exceção é `slave_hmac_key_hex`, a chave de assinatura do escravo de expansão, que também pode ser definida aqui) - os equivalentes do próprio chip slave de expansão
(`SLAVE_BOOTLOADER_FLASH_ADDR`, `SLAVE_APP_FLASH_ADDR`, `SLAVE_HARDWARE_ID`,
etc.) estão fixos no próprio `flasher_config.py`, uma vez que os valores reais
desse hardware já estão confirmados contra os seus próprios linker scripts, em
vez de precisarem de uma substituição em tempo de implementação como os
valores por defeito da placa principal. Um ficheiro presente mas avariado
regista um aviso e também recorre aos valores por defeito, em vez de fazer a
ferramenta falhar por causa de um erro de digitação. Qualquer que seja a fonte
ativa, é registada no arranque, pelo que é sempre visível quais os valores que
uma dada sessão realmente usou. `hardware_id` aceita uma string JSON
(`"0x0303CC01"`) ou um número JSON simples (`50580689`) - o que for mais
natural para a forma como o ficheiro é gerado. `app_max_size`,
`bootloader_max_size`, `flash_page_size`, `bootloader_flash_addr`, e
`app_flash_addr` também podem ser substituídos aqui, juntamente com a chave de
assinatura e o HardwareID acima - útil se esta ferramenta for alguma vez
adaptada a uma variante de chip ou esquema de partições diferente.

## 📸 Fotografias

<p align="center">
  <img src="images/URTC_FLASHER_V1_1.png" alt="Janela do URTC Flasher" width="700">
</p>

## 📂 Estrutura do Repositório

```
├── assets/
│   ├── URTC_APP_ICON.svg          <- shared app/taskbar icon source (vector)
│   ├── URTC_LOGO_FLASHER.svg      <- banner source (vector)
│   ├── qml/
│   │   └── FlasherDeck.qml        <- Qt Quick UI for the CAN-OTA command deck
│   ├── urtc_icon.ico              <- Windows taskbar/window icon
│   └── urtc_icon.png              <- Linux taskbar/window icon
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v<version>.bin     <- current main-board application firmware
│   ├── URTC_MAIN_BOOTLOADER_v0.3.8.bin   <- main-board bootloader (SWD/JTAG only, filtered out of
│   │                                         the CAN-OTA firmware list - see section 3 above)
│   ├── URTC_SLAVE_FIRMWARE_v0.1.9.bin    <- expansion slave application (advanced expansion boards only)
│   ├── URTC_SLAVE_BOOTLOADER_v0.2.2.bin  <- expansion slave bootloader
│   └── *.bin.sha256, *.bin.manifest.json  <- published digest + manifest (version, sha256, signature) of each image
├── images/
│   ├── URTC_FLASHER_BANNER.svg    <- logo banner shown at the top of this README
│   └── URTC_FLASHER_V1_1.png      <- real window screenshot, shown in the Photos section above
├── language/
│   ├── english.lng                <- default language, plain KEY=Value pairs
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   ├── chinese.lng
│   └── portuguese.lng
├── logs/                           <- created automatically, one file per session
├── urtc_config.json.example        <- template for the optional urtc_config.json override file
│                                       (see "Changing the HMAC key / HardwareID" above) - copy it
│                                       to urtc_config.json and edit, rather than starting from
│                                       scratch
├── urtc_flasher.py                <- ponto de entrada: argumentos da CLI e arranque da janela Qt Quick
├── qt_flasher.py                  <- Qt Quick front end - real CAN-OTA command deck,
│                                       reuses the same transport/validation/protocol classes below
├── flasher_config.py              <- config file I/O, language loading, protocol constants
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- STM32CubeProgrammer / pyOCD wrappers
├── flasher_validation.py          <- firmware file validation (.bin/.hex/.elf)
├── flasher_protocol.py            <- the CAN OTA state machine itself
├── flasher_github.py              <- lista e descarrega os assets de uma release do GitHub do URTC
├── flasher_records.py             <- registos de sessão (localização, retenção) e relatórios de atualização
├── verify_qt_device_config.py     <- real, outside-pytest end-to-end check of the Qt Quick config writes (needs a real Qt event loop)
├── verify_qt_swd_full_chip_flash.py <- real, outside-pytest end-to-end check of the Qt Quick full-chip SWD/JTAG panel (dry-run only)
├── verify_qt_can_options.py       <- verificação real, fora do pytest, de que o painel Qt Quick carrega e de que as opções CAN-OTA se comportam (destino, descida de versão, cópia)
├── tests/
│   ├── conftest.py                 <- gives the protocol tests a bench signing key
│   ├── test_firmware_signature.py  <- 7 tests: published signature, unsigned image refused, preflight digests, bundled firmware/
│   ├── test_flash_protocol_dispatch.py <- 8 tests, against a real simulated MockCAN bootloader
│   ├── test_flash_verify_fail_reporting.py <- 8 tests
│   ├── test_flasher_integrity.py   <- 14 tests
│   ├── test_flasher_protocol_clock.py <- 4 tests
│   ├── test_qt_flash_preflight.py  <- 2 tests (skipped without PySide6) - all run by GitHub Actions CI
│   ├── test_bitrate_listen_only.py
│   ├── test_bootloader_entry.py
│   ├── test_can_conformance.py   <- shared CAN vectors (tests/fixtures/can_conformance_vectors.json)
│   ├── test_github_download.py
│   ├── test_pinned_release.py
│   ├── test_language_files.py
│   ├── test_manifest_target.py
│   ├── test_mock_readback.py
│   ├── test_ota_partial_page.py
│   ├── test_patch_number.py
│   ├── test_python_can_transport.py
│   ├── test_qt_bridge_log.py
│   ├── test_qt_connection.py
│   ├── test_qt_firmware_files.py
│   ├── test_qt_flash_options.py
│   ├── test_qt_log_translation.py
│   ├── test_readback_odd_size.py
│   ├── test_records.py
│   ├── test_signing_policy.py
│   ├── test_slave_entry_check.py
│   ├── test_slave_flash.py
│   ├── test_swd_tools.py
│   ├── test_sync_firmware.py
│   ├── test_validation_ccm_stack.py
│   ├── test_validation_formats.py
│   └── test_version_report.py
├── requirements.txt                <- pyserial>=3.5 + PySide6>=6.8,<7
├── build_exe.bat                  <- Windows standalone build
├── build_exe.sh                   <- Linux standalone build
├── build-test.bat                 <- non-versioning build/compile check
├── build-test.sh                  <- same, for Linux
├── bump.py                        <- Comando explícito para subir a versão (compilar nunca a sobe)
├── bump_version.py                <- odometer-style version bump, called by bump.py
├── bump_manifest_version.py       <- syncs urtc.project.json's version to the native one (--sync)
├── docs/
│   └── CLI_REFERENCE.md           <- command-line flags reference
├── tools/
│   ├── build_test.py                     <- non-versioning compile + Qt Quick deck source check
│   ├── ci_validate.py                    <- manifest/CHANGELOG/docs validation used by CI
│   └── sync_firmware.py                  <- atualiza firmware/ a partir dos assets de uma release do URTC ou de uma pasta local (resumos verificados; --check verifica)
├── README.md                      <- (English version)
├── README_por.md                  <- este ficheiro
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md / README_por.md  <- outras traduções
├── LICENSE
├── NOTICE                      Aviso de direitos de autor e licença da documentação
├── .gitattributes
└── .gitignore
```

Esta ferramenta está organizada nos módulos `flasher_*.py` acima por
responsabilidade, puramente por legibilidade - não há diferença funcional
entre os ter como ficheiros separados ou como um único ficheiro grande.

## 🔗 Projetos Relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, uma vez que um pedido pode, na verdade, ser sobre um destes e não sobre este repositório.

**Projeto Principal**
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware para a PCB física Universal Robot Tool Controller, mais de 25 perfis de ferramenta sobre barramento CAN; o projeto principal de que este repositório é uma ferramenta específica, dentro da sua própria família de ferramentas para o barramento CAN.

**Projetos Irmãos** — as outras ferramentas da própria família de ferramentas CAN do URTC
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — ferramenta de desktop de diagnóstico CAN em direto para placas URTC, um painel por perfil de ferramenta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa baseada em navegador ao URTC-TESTER através da Web Serial API, sem necessidade de instalação local.

**Diretamente Relacionado**
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de frota com um contrato real e estável de códigos de saída, um cliente genuíno em direto da própria API do HYDRA-UMC-SERVER — faz à escala da frota (o comando `flash-all`) o que esta ferramenta faz para uma única placa.

**Também Parte do Ecossistema**

*Hardware e Plataforma Principais*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — o desenho da placa-mãe do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, pensado para orquestrar até 8 braços de ferramenta por CAN-OTA/SPI-OTA (firmware numa fase inicial; ainda sem placa montada).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — camada de produto reprodutível de Raspberry Pi OS para o CM5: agente só de leitura, configuração/perfis validados, provisionamento Wi-Fi de primeiro contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado e a fronteira de software de controlo de trabalhos contra a qual cada bridge valida os seus comandos (não é uma função de segurança certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registo declarativo de manifestos de adaptador e validador para conectores de máquinas externas; estende a própria ideia de contrato do SDK a máquinas externas sem substituir os projetos de gateway industrial.

*Backend e Clientes Principais*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — o verdadeiro backend headless (REST/WebSocket) com que todos os clientes de controlo realmente comunicam.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — painel de controlo web com visualização 3D multirrobô em tempo real.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de comando de enxame (swarm) para desktop (PySide6) para vários servidores em simultâneo, empacotado como executável autónomo.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação de controlo nativa para Android com início de sessão biométrico e uma aplicação companheira Wear OS emparelhada.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — UI tátil nativa para o ecrã tátil DSI de 7" integrado, embutida no próprio CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — criador/editor gráfico de URDF para desktop que envia os modelos concluídos para o catálogo do próprio STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de modelos STL para desktop, que transforma/substitui/remove/adiciona peças reais no mesmo catálogo de modelos que o HYDRA-UMC-EDITOR-URDF também edita.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 (testado apenas contra uma frota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso ao estado GRBL e aos bytes de controlo (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor de comandos para o Boston Dynamics Spot (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de células laser que lê 3 sinais GPIO (chave, caixa e interlock) (testado apenas contra um chip simulado; não pode armar nem disparar um laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de alto nível do fluxo de placas para pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — fronteira de coordenação segura para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais protegidos por gate.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador com um transporte ROS 2 baseado em rclpy importado sob demanda (ainda não executado contra uma instalação ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor de comandos MAVLink (testado apenas contra um emulador).

*Nó de IA de Visão (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub de integração para o pipeline de visão Hailo-8, com uma verdadeira verificação de prontidão de hardware por fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação de carregamento seguro de arquitetura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real + gerador de configuração MediaMTX com uma verdadeira fronteira de integração HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção de servovisão baseada em posição com autorização condicionada ao estado da zona; ainda sem estimativa de pose por câmara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de violação de zonas, atualidade da calibração e pedido de E-STOP que lê as posições dos objetos de um ficheiro; nenhum detetor a alimenta e ainda não há E-STOP físico ligado.

*Nó de IA Cognitiva (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub de integração para o pipeline cognitivo Hailo-10 (orquestração de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificação/descodificação real de tokens de ação e geração de trajetórias para um modelo Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — verdadeiro front-end de voz (VAD + intent parser) com um relay Watch limitado e protegido por confirmação.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — decomposição real de tarefas baseada em regras e recuperação semântica de erros sobre códigos de erro de MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — pesquisa real de documentos TF-IDF, apenas com stdlib, sobre os próprios documentos Markdown deste ecossistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de manutenção de IA local, protegido por políticas, para o próprio ecossistema - observa, diagnostica e propõe correções; os dois níveis de risco mais elevados deliberadamente ainda não estão implementados.

*Orquestração e Enxame (Swarm)*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub de integração com um verdadeiro contrato de relatório de saúde gRPC/Protobuf e máquina de estados de missão.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — fila real de trabalhos baseada em prioridades com deduplicação, sobre uma verdadeira API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — verdadeiro watchdog de saúde da frota baseado em gRPC, com retry/backoff e deteção de discrepância de identidade.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planeador real de trajetórias 3D baseado em RRT com validação real de colisões com obstáculos/espaço de trabalho.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronização real de estado CRDT LWW-Element-Map, testada por propriedades para convergência multicélula.

*Gémeo Digital e Simulação*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub de integração para o motor de gémeo digital, com um verdadeiro contrato de sincronização de compatibilidade de versões.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — encaminhador hardware-in-the-loop com um interlock de software de colisão entre a simulação e o hardware real (testado sem hardware real).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática direta real e validação de limites de juntas sobre um subconjunto URDF real.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — gerador procedimental real de cenas 2D com exportação de anotações YOLO/COCO.

*Dados e Análise*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — armazém real de séries temporais sobre sqlite3 com uma verdadeira API HTTP de ingestão/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detetor real de anomalias com FFT + linha de base estatística, com monitorização de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidade sobre o histórico do DATALAKE, com exportação CSV reprodutível.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingestão CAN/WebSocket para o DATALAKE, com deduplicação por sequência.

*Gateway Industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub de integração que retransmite para protocolos industriais, com uma verdadeira camada de lista de comandos permitidos/backpressure.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espaço de endereços OPC-UA real, verificado com uma verdadeira sessão de cliente de protocolo binário.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real com autenticação opcional por cliente e ACLs de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML reais MTConnect `/probe` e `/current` com saída em modo degradado.

*Ferramentas Complementares e Operações do Ecossistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — painéis Smart Summaries e Anomaly Highlighting sobre o DATALAKE/ANOMALY-DETECTOR, com um recurso estatístico honesto.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com padrões de alerta tátil e um relé de voz para o telemóvel emparelhado (ainda não executada num relógio físico).
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — uma gateway à frente do barramento CAN que só deixa passar identificadores de uma lista, limita a sua taxa e pede uma chave de sessão.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware para um rack de montagem de placas com descodificação real de ID de ferramenta e lógica de pré-aquecimento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware mais um verdadeiro companheiro de visão em Python para uma cabeça de ferramenta de inspeção térmica/RGB.
- **[URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)** — ferramenta de ambiente de trabalho que deteta, instala e atualiza os repositórios da família URTC, uma ação explícita de cada vez.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — ferramenta de desktop administrativa que descobre, clona e atualiza todos os repositórios deste ecossistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — ferramenta de desktop Windows/Linux que constrói uma imagem CM5 pronta a gravar, pré-carregada com as versões mais atuais do ecossistema, com configuração de primeiro arranque de Wi-Fi/utilizador/SSH ao estilo do Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordenador de incidentes de manutenção: um papel edge de baixos privilégios recolhe um instantâneo sanitizado de inventário/saúde, um papel de control-plane apresenta-o só para leitura e pede a um fornecedor de IA que sugira um diagnóstico - nunca aplica um patch nem implementa nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reprodutível (Raspberry Pi 5 / CM5) que armazena o código-fonte do ecossistema e executa tarefas limitadas de build/teste sob uma fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.

## 🖼️ A janela, passo a passo

Estas imagens são a janela real, desenhada sem ecrã tal como abre (nada ligado, nada enviado). O guia percorre o painel, a janela de Ajuda e a de atualização.

![A janela, passo a passo](docs/screenshots/flasher-deck.png)

[Guia com imagens](docs/WINDOW_GUIDE.md)

<!-- urtc-section:updates -->
## 🔄 Como se atualiza

Este programa pode procurar uma versão mais recente de si próprio: o botão «Procurar atualizações» pergunta uma vez ao GitHub e só propõe um pacote assinado se for para o seu sistema e mais recente. Nada é verificado nem instalado por si só, a não ser que ative a verificação, e uma atualização precisa da sua confirmação. O pacote tem de coincidir com o seu SHA-256 e com a assinatura da chave das versões fixada no programa; a versão anterior é guardada e reposta sozinha se a nova não arrancar. `urtc-updater --cli package list|check|install|rollback` faz o mesmo na linha de comandos para o flasher e o tester, e `install --file` funciona sem rede.
<!-- /urtc-section:updates -->

<!-- urtc-section:first_flash -->
## 🚦 Primeira gravação sem hardware

1. Arranque a placa virtual: `python -m urtc_can.virtual_board`.
2. Noutro terminal defina `URTC_VIRTUAL_PORT=socket://127.0.0.1:7777` e arranque o flasher: a placa virtual está na lista de portas.
3. Selecione-a, carregue em Ligar, escolha uma imagem de `firmware/` (ou procure uma) e carregue em Iniciar CAN-OTA.
4. A placa virtual aceita a atualização completa, com as mesmas verificações de tamanho, assinatura e versão de uma real. É um modelo: nada disto correu numa placa.
<!-- /urtc-section:first_flash -->

<!-- urtc-section:heads -->
## 🧭 Várias cabeças de ferramenta num barramento

O firmware pode fazer várias cabeças de ferramenta partilharem um barramento CAN (a extensão multinó). Vem **desativada por defeito**, e um barramento com uma só cabeça funciona exatamente como antes. A janela **Cabeças** encontra as cabeças, lista cada uma com o seu endereço, ferramenta e número de série, e mostra o seu estado: pronta, selecionada, conflito de endereço, falha retida, no seu bootloader ou perdida. Seleciona uma, o programa pede confirmação e só depois lhe envia alguma coisa; enquanto houver várias cabeças no barramento, um comando é recusado até uma estar selecionada e o ter confirmado. Se a cabeça selecionada se perder, todas as cabeças passam ao estado seguro (uma caixa da janela desativa-o). Só foi testada contra um modelo do barramento, não com placas. Veja `docs/MULTINODE.md` em URTC-COMMON.
<!-- /urtc-section:heads -->

<!-- urtc-section:compatibility -->
## 🧩 Compatibilidade

As versões dos programas URTC que funcionam em conjunto, e a versão do protocolo que cada uma fala, constam da tabela de compatibilidade que o URTC-COMMON gera: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 📜 LICENÇA

URTC Flasher é (c) 2026 JuanenRac (Electro Hobby 3D). Este aviso tem de ser
incluído em quaisquer distribuições deste projeto ou trabalhos derivados.

Este projeto é constituído por código-fonte e pela sua própria documentação,
disponibilizados sob licenças diferentes - cada uma adequada ao que
efetivamente cobre:

1. O código-fonte (`urtc_flasher.py` e todos os módulos `flasher_*.py`)
   e qualquer binário compilado a partir dele através de
   `build_exe.bat`/`build_exe.sh` estão disponíveis sob a
   **GNU General Public License v3.0 or later (GPL-3.0-or-later)**. Texto completo em
   https://www.gnu.org/licenses/gpl-3.0.html.

2. A documentação (este README e as suas próprias traduções -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`)
   está disponível sob **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Texto completo em
   https://creativecommons.org/licenses/by-sa/4.0/.

Esta ferramenta é a companheira de gravação CAN-OTA/SWD-JTAG do projeto
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
- consulte o repositório próprio desse projeto para o firmware da placa, os
desenhos de hardware, e a documentação completa do protocolo contra o qual
esta ferramenta é implementada. O firmware do próprio URTC é GPL-3.0-or-later e os seus
desenhos de hardware são CERN-OHL-S v2; a licença desta própria ferramenta
aqui não se estende a esse projeto separado, e vice-versa. Existe também uma
alternativa baseada na web que cobre terreno semelhante em
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Se construir sobre este projeto, tenha em mente a divisão de licenciamento:
as alterações de código devem permanecer GPL-3.0-or-later, os derivados da documentação
devem permanecer CC BY-SA - cada um com atribuição de volta a este projeto e
ao seu autor.

---

## 📚 Documentação e Comunidade

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnológica e diretrizes de código para um pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — as normas de comportamento esperadas nesta comunidade.
- **[SECURITY.md](SECURITY.md)** — como reportar uma vulnerabilidade, e as áreas reais de foco de segurança deste projeto.
- **[SUPPORT.md](SUPPORT.md)** — onde colocar questões e reportar erros.
- **[LICENSE.md](LICENSE.md)** — a licença deste próprio projeto.

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
