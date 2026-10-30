<p align="center">
  <img src="/images/URTC_FLASHER_BANNER.svg" alt="URTC Flasher Logo" width="100%">
</p>

# URTC Flasher（Windows / Linux）

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  🇨🇳 <b>简体中文</b> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### 通过 CAN（CAN-OTA）更新 URTC 板的固件，并通过 SWD/JTAG 编程整颗芯片，支持 Windows 和 Linux

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Tests-500-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Protocol-CAN--OTA-orange.svg" alt="CAN-OTA">
</p>

---

**诚实核查 - 今天真正能运行的部分：** `tests/` 下有 47 个 pytest 文件（500 个测试：全部通过，其中 79 个在没有 PySide6 时跳过）——针对真实 `MockCAN` 传输（`flasher_transports.py`）的 CAN-OTA 协议测试，它会回放完整的模拟引导程序序列（开始／擦除／接收、页数据 + PAGE_ACK、HMAC 分块、以真实成功或特定 `VERIFY_FAIL_REASON` 结束更新）；签名规则（无需任何密钥即发送已发布的签名、拒绝未签名镜像、清单 sha256 不符时在任何总线通信前拒绝）；镜像完整性检查；以及随附 `firmware/` 与其清单的核对。GitHub Actions（`.github/workflows/ci.yml`）在每次推送时运行这套测试，`tools/build_test.py` 也会在 `build-test.sh`/`.bat` 中运行。它还会运行 `ruff check` 和 `python -m mypy`（对程序及共享代码副本的类型检查）。根目录下的三个 `verify_qt_*.py` 脚本是 pytest 之外的真实端到端检查（需要真实的 Qt 事件循环；用 `QT_QPA_PLATFORM=offscreen python verify_qt_*.py` 运行）；`verify_qt_swd_full_chip_flash.py` 只以 `dry_run=True` 构造 `PyOCDCLI`/`CubeProgrammerCLI` 命令。这些都没有在本环境中针对真实板卡运行过。已发布的内容请参见 `CHANGELOG.md`。 模拟的引导程序（`MockCAN`）只是根据协议说明编写的模型：它能重现页确认、不完整的最后一页和回读帧，但它不是真正的引导程序，所以测试全部通过并不能代替在真实板卡上的试验（官方 73476 字节镜像曾无法安装、备份的最后一帧曾被丢弃，而测试却是通过的，正是因为模拟比真正的引导程序更宽松）。

---

> **安全与安防现状:**本生态系统不是经认证的安全系统,目前也不存在已组装的 URTC 电路板。引导程序使用 CRC32 和共享密钥的 HMAC-SHA256 校验固件映像,而非非对称签名(计划中);已发布的应用映像使用公开的开发密钥签名(`signing_key_kind: dev`),因此任何人都可以生成引导程序接受的映像;尚未向任何真实电路板发送过任何内容。在依赖此处任何说法来保障人身安全之前,请先阅读[安全基线](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md)和[威胁模型](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md)。

## 📋 速览

| | |
|---|---|
| 版本 | `0.4.2` |
| 成熟度 | 可用 |
| 测试 | 500 (`python -m pytest tests -q`) |
| 技术栈 | Python / PySide6 / Qt Quick / CAN-OTA / SWD/JTAG |
| 目标 | 使用者的电脑 |
| 真实硬件 | 仅模拟：使用模拟器、替身或仿真测试；此版本没有在真实硬件上运行的记录 |

**跳转到：** [概述](#-概述) · [架构](#-架构) · [功能](#-功能) · [安全](#-安全与防护) · [接口](#-接口) · [配置](#-配置) · [快速开始](#-快速开始) · [测试](#-测试) · [结构](#-仓库结构) · [相关项目](#-相关项目)

<!-- urtc-section:status_flasher -->
## 🚦 项目状态

🟢 已完成并已验证 · 🟡 可用，但有已知限制 · 🟠 做了一半或未验证 · 🔴 未完成或不能用。从未在真实硬件上运行过的内容不会是绿色。

| 部分 | 状态 | 仓库能够证明的内容 |
| --- | :---: | --- |
| 软件 | 🟡 | 可在电脑上和模拟器上运行；从未在真实板子上运行过。 |
| 界面 | 🟡 | 窗口可运行，并用模拟板子检查；未用真实适配器试过。 |
| 测试 | 🟢 | 每次推送时测试套件都会在 CI 中通过。 |
| 真实硬件 | 🟠 | 尚未在真实板子上运行：台架测试仍待进行。 |
| 安全 | 🟡 | 发布版使用 Ed25519 签名，并在使用前检查；密钥的处理没有他人审阅过。 |
| 文档 | 🟡 | 提供八种语言的 README 和参考文档；翻译未经母语者审阅。 |

<!-- /urtc-section:status_flasher -->

## 🎯 概述

一款小型的跨平台 GUI 工具，用于通过 CAN 总线更新 URTC 板卡固件。它实现了
`docs/CANBUS.TXT` 中的确切引导程序协议（位于本工具所对接的同级
[URTC](https://github.com/JuanenRac/URTC) 仓库中——见本文档末尾附近的
“相关项目”；本 README 中提到的每一个其他 `docs/*.TXT` 引用也都指向该处）：
HardwareID 检查、共享密钥的 HMAC-SHA256（并非非对称签名）、黄金镜像备份槽更新流程、通过引导程序心跳
消息实现的实时进度，以及一次版本查询（本板卡的应用程序*或*引导程序是否通过
CAN 自我标识），以便你在决定要刷写什么之前，先看看当前已安装的内容。

**检查更新。** “检查更新”按钮向 GitHub 查询一次最新发布版，只有当它带有适用于此系统且比已安装版本更新的包时，才会提供下载。只有当包的 SHA-256 和 Ed25519 签名（程序中固定的发布密钥）都有效时才会接受；只有在您确认之后、且没有传输进行时才会安装，并保留上一版本以便退回（新版本无法启动时会自动恢复）。程序绝不会自行检查或安装：启动时检查是一个选项，默认关闭，而确认步骤只能在同一窗口中经过警告后才能关闭。

有两种方式与板卡通信，底层使用的是同一套协议：

- **串口 / SLCAN** —— 在 Windows 和 Linux 上均可使用。需要一个运行 SLCAN
  固件的 USB-CAN 适配器，作为虚拟串口连接。
  - 没有适配器和硬件时，可由虚拟板代替：运行 `python -m urtc_can.virtual_board`，在启动程序之前把它的地址写入环境变量 `URTC_VIRTUAL_PORT`（例如 `socket://127.0.0.1:7777`），或在命令行中传给 `--port`。它会出现在端口列表中，并像真实板子一样响应，包括应用程序和引导程序。
- **SocketCAN** —— **仅限 Linux**，且仅在 Linux 上于工具界面中显示。直接与
  内核的 `can0`/`slcan0` 网络接口通信。如果你的适配器已经运行
  `gs_usb`/candleLight 固件（大多数 CANable 板卡开箱即用如此），这条路径
  **完全无需重新刷写适配器**——Linux 自身的驱动会原生处理它。

## 🧩 在 URTC 中的角色

URTC-FLASHER 是把固件写入 URTC 板的程序。它通过 USB-CAN 适配器（SLCAN 串口，或 Linux 上的 SocketCAN）使用 URTC 的引导程序协议（该仓库的 `docs/CANBUS.TXT`）：HardwareID 检查、共享密钥 HMAC-SHA256 数据块、带备份槽的黄金镜像流程，以及版本查询，让你在决定刷写什么之前先看到已安装的内容。对于没有可用引导程序的板子，或要编程整颗芯片时，它为 pyOCD 或 STM32CubeProgrammer 准备 SWD/JTAG 命令。它是 URTC-TESTER 的更新搭档，通过 URTC-COMMON 与其共享 CAN 代码，URTC-UPDATER 可以把已核对发布签名的固件镜像交给它。

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="URTC-FLASHER 的架构：谁在使用、包含什么、依赖什么" width="100%">
</p>

本仓库各部分如何协作：谁在使用它、它包含什么、它依赖什么。图片由 `docs/architecture.json` 绘制，并与代码核对。

<!-- urtc-section:updates -->
### 如何更新

本程序可以查找自身的较新版本：“检查更新”按钮只向 GitHub 查询一次，只有当包适用于您的系统且更新时才会提供已签名的包。除非您打开检查，否则不会自行检查或安装，更新需要您的确认。包必须与其 SHA-256 以及程序中固定的发布密钥签名一致；上一版本会保留，新版本无法启动时会自动恢复。`urtc-updater --cli package list|check|install|rollback` 可在命令行中为刷写器和测试器完成同样的操作，`install --file` 无需网络即可使用。
<!-- /urtc-section:updates -->

## 🖼️ 屏幕截图

<!-- urtc-shots -->
在测试台上以 1920×1080 截取，使用示例数据，背后没有真实的安装。

<table>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/deck.png" alt="刚打开时的窗口：连接、固件清单、CAN-OTA 更新的四个检查点以及设备配置。" width="100%"><br><sub>刚打开时的窗口：连接、固件清单、CAN-OTA 更新的四个检查点以及设备配置。</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/heads.png" alt="总线上的工具头：一条模拟总线上的六个工具头，每个处于一种可能的状态（已选择、地址冲突、故障锁定、处于引导程序、丢失和就绪）。" width="100%"><br><sub>总线上的工具头：一条模拟总线上的六个工具头，每个处于一种可能的状态（已选择、地址冲突、故障锁定、处于引导程序、丢失和就绪）。</sub></td>
</tr>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/help.png" alt="帮助窗口：使用该程序的各个步骤，使用窗口的语言显示。" width="100%"><br><sub>帮助窗口：使用该程序的各个步骤，使用窗口的语言显示。</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/updates.png" alt="更新窗口：只有在你确认之后，才会安装较新的已签名软件包。" width="100%"><br><sub>更新窗口：只有在你确认之后，才会安装较新的已签名软件包。</sub></td>
</tr>
</table>
<!-- /urtc-shots -->

这些图片是真实的窗口，在没有屏幕的情况下按打开时的样子绘制（未连接任何设备，未发送任何内容）。指南依次介绍面板、帮助窗口和更新窗口。

[图文指南](docs/WINDOW_GUIDE.md)

## ✨ 功能

### 检查当前已安装的内容

> 在 Qt Quick 控制台中，两种传输方式的端口（串口适配器，以及 Linux 上的 SocketCAN 接口）都在同一个列表里，本节的查询由 **读取控制板状态** 完成：它一次性查询版本、CAN 错误计数器、扩展板类型、MLX9064x 型号和外设信息，并显示在板子快照中。设备配置一节中的保存按钮会写入这些值。

如果你在 Linux 上且 SocketCAN 可用，你会在顶部看到一个**传输方式**选项——
在连接之前选择串口/SLCAN 或 SocketCAN。在 Windows 上根本不会出现这一行；
串口/SLCAN 是唯一的选项。

点击**连接**，工具会自动询问板卡当前正在运行什么（CAN ID `0x7F8` →
`0x7F9`——见 `docs/CANBUS.TXT`）。无论板卡是在正常运行其应用程序，*还是*
处于引导程序中，这都能正常工作，因此你无需为了查明这一点而触发一次复位。
之后可以随时点击**查询**再次检查（在刷写完成后立即使用很有用，以确认新
版本确实生效了）。

**当引导程序本身应答时**（板卡处于引导程序中，而非运行其应用程序），它也会
报告自身的版本——这是与已安装应用程序版本分开的另一件事，通过
`bootloader_common.h` 中它自身的 `BOOTLOADER_VERSION_MAJOR/MINOR/PATCH`
跟踪，并作为一个紧挨着 `0x7F9` 的第二个帧（`0x7FA`）发送。正在运行的
应用程序从不发送此内容——除了询问引导程序本身，它没有办法知道当前已刷写的
引导程序的版本，因此这只会在板卡确实处于引导程序中时出现（紧跟在 `0x7F0`
之后，或在新的启动中它跳转到应用程序之前）。

**补丁号。** 固件为 0.3.5 或更新版本的板卡还会发送已安装应用程序的补丁号
（帧 `0x7E9`，紧跟在 `0x7F9` 之后），因此窗口和日志会显示完整的
`主版本.次版本.补丁`（例如 `v0.3.5`），而不只是 `主版本.次版本`；镜像的补丁号
是其清单中版本的第三部分。更新前，日志会以这种形式显示"已安装 -> 新版本"，
只有当双方都带有补丁号时，补丁号才会参与"比已安装版本更旧"的警告。早于补丁号
功能的板卡不带补丁号应答，显示方式与以前完全相同。当引导程序（在同一帧的标志位
中）声明它会读取补丁号时，更新结束帧会把补丁号放在次版本字段的高字节中；任何
其他引导程序以及任何不带补丁号的镜像，收到的仍是原来的两个数字的帧。扩展从机
的版本应答（`0x218`）有同样的可选扩展。这是按协议说明实现的，仅在模拟器上
测试过，没有在真实板卡上尝试过。

你会看到以下内容：

- **`v0.2（应用程序，HardwareID 0x0303CC01）`** —— 正常情况，应用程序
  正在运行，一切匹配。
- **`引导程序正在运行，当前没有安装有效固件，引导程序版本 v0.1.2`** ——
  板卡卡在引导程序中，没有可以跳转的目标（空白芯片，或主槽的所有检查都
  失败了）。这正是本工具存在的目的所要解决的情况——刷写它。这里显示的
  引导程序版本是引导程序自身的版本，与未通过检查的应用程序版本无关。
- **以红色显示的 `⚠ HardwareID 不匹配！`** —— 有东西应答了，但其
  HardwareID 与本工具预期的不一致。在先弄清楚原因之前不要刷写；引导程序
  反正也会拒绝这次更新，但这里的不匹配也可能意味着你完全指向了错误的
  板卡。
- **无响应**（红色）—— 板卡无响应、比特率错误，或实际未连接。检查物理
  连接，以及在 SocketCAN 路径下，检查接口是否确实已启用（`ip link show`）。

**扩展板：** 版本检查正下方的一对独立下拉框和查询/保存控件。通过 CAN
（`0x1A0`/`0x1A1`）读取和设置 7 种可能的 `CONN_EXPANSION` 配置（无，或
6 种真实变体之一——见 `EXPANSION.TXT`）中的哪一种实际安装。板卡本身没有
电气方式来自行感知这一点，因此必须被告知——这个功能放在这里（而不仅仅在
`URTC Tester` 中）是因为它是一项一次性的硬件配置步骤，与固件更新一起
进行最为自然。**保存**会先要求确认，因为这会一直持续到明确再次更改之前，
跨越电源循环持久保留。

**MLX9064x 传感器变体：** 与其正上方的扩展板控件形状相同——一对下拉框和
查询/保存控件，通过 CAN（`0x1A6`/`0x1A7`——见 `CANBUS.TXT`）读取/设置 3 种
MLX9064x 系列热传感器（或完全没有）中实际装配的是哪一种。仅当上方的扩展板
设置为 Advanced 变体或 Basic+MLX9064x 时才有意义；板卡自身的固件在任何其他
扩展板类型上都会完全忽略此设置。“未安装”（安全的默认值）刻意不会回退为
假定 MLX90640——一块实际接有 MLX90640 的板卡需要明确设置一次，与扩展板
类型本身相同。

### 刷写

1. **连接**：选择串口/SLCAN 或 SocketCAN（仅限 Linux），然后选择端口/接口，
   然后点击连接。对于串口/SLCAN，这会以 500 kbit/s（URTC 固定的总线速度）
   打开 CAN 通道；对于 SocketCAN，接口应已处于该比特率（上文第 1 步）——
   本工具不会设置它。无论哪种方式，当前版本都会被自动查询——见上方第 4 节。
2. **选择刷写目标**：“本板卡（主）”或“扩展从属”——默认为主板，这是更常见
   的情况。从属选项只能到达 Advanced 扩展板变体（TMC2209+STM32F303CBT6
   或 TMC5160A+STM32F303CBT6）上的任何东西——该更新是通过主板自身的 I2C
   桥中继到从属芯片的（`CANBUS.TXT` 自身的 `0x210`-`0x219`），而非一条
   独立的物理连接。当选择“从属”时，“刷写前擦除 F-RAM”（下方第 4 步）
   会自动禁用自身——从属芯片没有自己的 F-RAM 可以擦除。
3. **选择固件**：从检测到的列表中选择，或点击浏览——检测和验证的确切
   工作方式见上方第 3 节。
4. **刷写**：
   - 如果板卡已上电且正常运行，请保持勾选“板卡当前正在运行应用程序”——
     工具会先发送 `0x7F0` 魔术负载触发指令（如果选定目标是“从属”，则为
     `0x210`，中继至从属），它会在复位进入引导程序之前安全地关闭每一个
     执行器。
   - 如果板卡已经处于引导程序中（刚完成一次全新的 JTAG 刷写，或上方的
     版本检查显示“当前没有安装有效固件”），请取消勾选它。
   - 点击**刷写固件**并确认——确认对话框会说明你即将刷写的具体目标，
     请再次确认这与你实际打算选择的内容一致。日志显示每一个协议步骤；
     进度条在传输期间逐页跟踪写入进度，然后在最后的备份到主槽复制期间
     跟踪复制进度。

如果验证在任何时刻失败（CRC32、HMAC 或 HardwareID 不匹配），引导程序的
主槽绝不会被触碰——板卡会继续运行它已有的任何固件。随时重试都是安全的。

**备份固件（CAN）**：通过总线原样读回当前已安装的固件，并将其保存为一个
`.bin` 文件——这是 SWD 章节自身“擦除前备份整个闪存”功能（见下方第 6 节）
的 CAN 版本，出于相同的原因。值得在任何更新之前进行，尤其是在一次刻意的
降级之前（见下文），因为如果你不再持有生成这些字节的原始文件，这是日后
取回今天确切字节内容的唯一方法。仅限主板，且仅在板卡确实处于引导程序中
时才能使用——需要一个实现了 `0x7FE`/`0x7FF` 的引导程序（见
`docs/CANBUS.TXT`）；一个较旧的引导程序只会从不应答，表现为一次明确的
超时，而非一个静默的空文件。 实际上，这意味着该备份适用于没有有效应用程序、或更新进行到一半被中断的板卡：板卡有有效应用程序时，除非收到开始更新帧（`0x7F1`），引导程序会在复位约 600 ms 后跳转到应用程序，而本工具没有让引导程序持续等待的按钮（那需要修改引导程序）。对于正常运行的板卡，请改用 SWD/JTAG（第 6 节）备份闪存。

**版本与签名提示**：传输之前，工具会询问板卡当前安装了什么，并记录“已安装 vX.Y -> 新版本 vA.B”；如果新版本更旧，会警告除非允许降级，否则引导程序将拒绝，并建议先做备份。如果某个镜像的清单表明它使用公开的开发密钥签名（随附的官方镜像就是如此），文件名下方会显示红色警告；在 `urtc_config.json` 中设置 `"require_production_signature": true` 即可完全拒绝此类镜像。当板卡从没有有效固件的引导程序中应答时，会自动选中 `firmware/` 中找到的最新官方主板镜像，供你检查后烧录。每次更新成功后会写入一份小报告（`logs/urtc_update_report_*.json`：工具版本、操作员、镜像名称、大小与 SHA-256、更新前后的版本）；报告带有自己的 SHA-256，因此被修改时能够察觉，但它不是签名。

**刻意安装一个更旧的版本**：引导程序通常会拒绝一个签名有效、但声明的版本
比当前已安装版本更旧的镜像（验证失败原因“rollback rejected”）——这可以
阻止一个已发现漏洞的版本被重放。如果你确实需要恢复到一个更旧的、仍受信任
的发布版本，请在刷写之前勾选**“允许降级（绕过防回滚）用于本次更新”**
（目标：仅限主板）——由于这是刻意绕过一项安全检查，会出现第二个确认对话框。
这仍然会通过正常的传输上传完整的旧镜像，它只是为那一次尝试解除了版本顺序
检查（`0x7FD`——见 `docs/CANBUS.TXT`）；报告给板卡的版本号来自该文件旁边
存在的 `.manifest.json`（如果存在——见上方第 3 节），否则回退为本工具自身
当前配置的版本，无论哪种情况都会清晰记录在日志中，因此这绝不是一次静默的
猜测。

### 通过 SWD/JTAG 编程整个芯片（高级）

**SWD/JTAG 编程**选项卡中的“通过 SWD/JTAG 编程整个芯片（高级）”面板执行
一次完整的初始烧录刷写——批量擦除整个芯片，然后在与**目标芯片**选择（见下文）
相匹配的该芯片自身的真实地址处，全新写入引导程序和应用程序镜像。这与上方
第 1-5 节是一种**不同类型的操作**：

|  | CAN OTA 更新（第 1-5 节） | 完整芯片 SWD/JTAG（第 6 节） |
|---|---|---|
| 中断后自我修复 | 是——黄金镜像备份槽保证正在运行的固件得以保留 | 否——在重新编程之前不会运行任何东西 |
| 可恢复 | 自动恢复，无需操作 | 是——只需重新连接并再次通过 SWD 刷写；调试端口不依赖闪存内容。只有真正的永久锁定（RDP2 选项字节）才会阻止这一点，而本工具中没有任何内容会设置选项字节 |
| 触碰引导程序 | 从不 | 是，设计如此 |
| 需要 | 一个 USB-CAN 适配器 | 一个 SWD/JTAG 探针（ST-Link 或类似设备） |
| 典型用途 | 常规固件更新 | 空白芯片的首次初始烧录，或恢复一块变砖的板卡 |

**目标芯片：** “本板卡（主）”或“扩展从属”——与 CAN-OTA 选项卡自身的
选择器相同的 2 个选项，但这里是一个真正独立的选择：SWD/JTAG 需要一个探针
物理接线到设置为该项的那颗芯片，因为不像 CAN-OTA 那样，没有桥接可以让
一条连接同时到达两者。切换此项会自动改变所使用的闪存地址：

| | 主板（STM32F303CC） | 扩展从属（STM32F303CBT6） |
|---|---|---|
| 引导程序地址 | `0x08000000`（32K 区域） | `0x08000000`（18K 区域） |
| 应用程序地址 | `0x08008000`（112K 区域） | `0x08005000`（54K 区域） |
| pyOCD 目标字符串 | `stm32f303cc` | `stm32f303cb` |

以上两个目标字符串都是本项目自身对每颗芯片真实 pyOCD 目标名称的最佳猜测，
在编写本文档时并未针对一个实际存在的 pyOCD 安装进行确认（pyOCD 中对 STM32
的覆盖主要来自 CMSIS-Pack，而非内置目标）——如果刷写因“target not found”
类的错误而失败，请自行运行 `pyocd list --targets --name stm32f303`，
`pyocd pack install <真实名称>` 会拉取正确的 CMSIS-Pack。

**需要以下之一**（工具会自动检测哪一个可用，并只启用它找到的那些）：
- **pyOCD** —— `pip install pyocd`。免费、开源，除了 pip 包之外无需单独
  安装。
- **STM32CubeProgrammer** —— ST 官方工具，从 [st.com](https://www.st.com)
  单独安装。如果你已经因为其他 STM32 工作而拥有它，这里无需额外安装。

两者都作为命令行子进程驱动，而非作为 Python 库导入——你会在运行前看到
日志中记录的确切命令。

**文件格式：** `.bin`（需要本工具已经知道的固定地址——你无需输入）或
`.hex`（携带自身的地址，按原样使用）。混用是可以的——引导程序用 `.hex`、
应用程序用 `.bin`，反之亦然，都可以正常工作。两个文件选择器都会在让你
继续之前验证所选文件（针对目标槽是否合理的大小，以及——在格式允许自信
检查的情况下——一个合理的初始堆栈指针），方式与 CAN 路径的固件选择器
已经做过的相同。

**在任何破坏性操作运行之前都会检查连接**，需要**积极证据**证明存在一个
真实的探针/目标，而不仅仅是没有错误——STM32CubeProgrammer 自身的退出码
本身并不是一个可靠的成功/失败信号，因此在批量擦除步骤运行之前，会先运行
一次专门的连接检查（`pyocd list --probes`，或针对 STM32CubeProgrammer 的
一次仅连接的 `-c port=SWD`）。此后每一条命令的输出也会作为第二层进行已知
失败文本的筛查，以防在某些其他情况下工具的退出码本身也不可信。

**演练模式默认开启。** 第一次使用时，保持勾选状态并点击“烧写完整芯片”——
它会将确切的命令打印到日志中，而不触碰板卡。仔细阅读它们，确认路径和地址
看起来正确，*然后*取消勾选演练模式，真正执行。

**“擦除前备份整个闪存”**会首先通过同一工具自身的内存读取到文件命令
（STM32CubeProgrammer 为 `-r`，pyOCD 为 `commander savemem`）将整个 256KB
闪存区域读取到一个 `.bin` 文件——这里是真正的保险，因为与一次 CAN OTA
更新（黄金镜像备份槽已经对其提供保护）不同，一次完整芯片擦除没有其他撤销
手段。默认关闭，因为它会增加 10-30 秒，而在一块空白/全新芯片上并非必需；
在覆盖一块已经运行着某些内容的板卡之前，值得勾选它。如果读取实际上没有
生成文件，擦除操作会被拒绝，而不是在没有你所要求的备份的情况下继续进行。

**测试状态：** 上述连接检查逻辑已针对真实的 STM32CubeProgrammer 输出
（一次真实的连接成功日志和一次有据可查的“No target connected”失败，两者
都来自 ST 自身的社区论坛）以及一个真实用户遇到的确切假成功场景进行了验证。
针对一个真实 ST-Link 和一颗真实 STM32F303CC 的完整擦除/编程/验证序列尚未
端到端地执行过——编写本文档的环境没有 USB 访问权限。请对首次真实的完整
尝试给予适当的谨慎——如果有的话，先在一块备用/测试板上进行，并考虑一个
后备方案（STM32CubeIDE 自身的刷写工具，或 `st-flash`），以防你特定的
pyOCD 版本或探针与本文档假设的内容不匹配。

### 诊断——总线活动、比特率和调试包

**比特率选择器 + 自动检测**（仅限串口/SLCAN）：URTC 的总线固定为
500 kbit/s，这仍是默认值——本功能用于配置错误的适配器或排查非标准板卡的
故障。**自动检测**只*监听*：它以 SLCAN 只听模式（`L`）依次在每种标准比特率
下打开适配器，并在第一个听到有效 CAN 帧的比特率处停止，因此从不发送数据，
也不会干扰正在运行的总线。所以它需要其他节点正在发送数据，且适配器必须
支持只听模式；总线静默（或适配器不支持该模式）时它什么也找不到，此时请
手动选择比特率。点击它时尚未连接。SocketCAN 的比特率在操作系统层面设置
（`ip link`），因此对于该传输方式此控件被禁用——这里没有什么可以让它
尝试的。

**总线活动**（“检查（2秒）”，位于查询旁边）：统计在已连接的传输方式上，
一个固定的 2 秒窗口内实际看到的真实协议帧数。这刻意**不是**与真正的 CAN
总线负载百分比相同的东西——那需要一次 netlink 查询（SocketCAN）或
适配器特定的扩展（SLCAN），而本工具没有一种标准的、无需额外依赖的方式
来为*适配器自身*的控制器获取这些信息。它确实提供的是：无论在哪种传输
方式上，都能给出一个真实的、直接测量的“这条总线上是否有东西在通信，
大致频率如何”的信号。具体到 SocketCAN，它还会显示 Linux 自身接口统计
信息（`/sys/class/net/<iface>/statistics/`）的 2 秒增量——每个接口都暴露
的基本 rx/tx/error/drop 计数器，以纯文件形式读取，无需额外依赖。通过
SocketCAN 连接时还会读取 `/sys/class/net/<iface>/carrier`——每个 Linux
接口都暴露的一个纯粹的 0/1 文件。当一个 CAN 控制器进入总线关闭状态时，
内核驱动会调用 `netif_carrier_off()`，因此这里的“无载波”是总线关闭或
类似死链路的真实证据，会作为警告记录，并附带确切的恢复命令
（`sudo ip link set <iface> down && sudo ip link set <iface> up type can
bitrate 500000 restart-ms 100`）。本工具本身不会运行该命令——清除一次
真正的总线关闭需要在内核层面将接口关闭再启用，这需要 root 权限，且属于
更改系统网络配置的范畴，不是应该在你不知情的情况下默默代劳的事情。

**错误计数器（TEC/REC）**（位于总线活动旁边）：与上面的适配器侧计数器
不同，这会向**板卡本身**询问其自身 CAN 控制器的发送/接收错误计数器
（`0x7FB`/`0x7FC`——见 `docs/CANBUS.TXT`），由当前正在运行的应用程序或
引导程序中的任意一方应答。绿色表示两个计数器都为 0（错误主动状态，健康）；
橙色表示一个或两个非零但低于 128（仍处于错误主动状态，但有什么东西正在
导致重传）；红色表示 128 或以上（错误被动状态或更严重）或完全无响应
（尚未实现 `0x7FB` 的旧版固件/引导程序，或板卡未连接）。TEC 持续攀升而
REC 保持平稳，通常指向本板卡自身的发送未被确认——总线上没有其他节点，
或是本板卡自身连接特有的接线/终端电阻/比特率问题。

**导出调试包**（日志上方）：将当前屏幕上的日志、基本系统诊断信息
（操作系统、Python 版本、找到了哪些工具、当前的传输方式/端口/比特率），
以及当前选定的 CAN 固件文件保存为一个 `.zip` 文件——如果现场出了问题，
便于将完整情况交给编写固件的人，而不是手动复制日志文本。

### SWD/JTAG——文件格式、槽验证与探针选择

**文件格式**：SWD 部分的引导程序/应用程序选择器接受 `.bin`、`.hex` 和
`.elf`/`.axf`。ELF/AXF 通过少量手写的结构体解包进行解析（仅 ELF 头 +
程序头——没有符号，没有节头），刻意不使用 `pyelftools`：本项目保持零
非标准库依赖，而完整的 ELF 解析超出了这项特定合理性检查所需要的内容。
已针对本项目自身构建产出的实际编译的 `BOOTLOADER.elf`/`APP.elf` 进行了
验证——两者都在其真实的加载地址（`0x08000000`/`0x08008000`）正确通过
验证，而不仅仅是合成的测试文件。仅支持 32 位小端序 ARM，这也是 Cortex-M
目标唯一可能的形式。一个 `.hex` 文件声明的大小是实际占用的字节数，而非
从其最低到最高记录的地址跨度——因此一个稀疏文件（一小块真实固件加上一块
遥远的、独立的选项字节或校准数据块，某些 STM32 工具链会将它们捆绑进一次
导出中）会根据其真实内容而非两者之间的间隔进行验证。一个采用非 `.bin`
扩展名（`.img`、`.rom`，或完全没有扩展名——可通过文件选择器的“所有文件”
选项选中）的原始固件镜像，其基地址取自你将它加载到哪个槽中，与 `.bin`
的处理方式相同。

**引导程序/应用程序槽验证**：文件选择器会验证每个镜像是否适用于它被放入
的那个槽，而不仅仅是它看起来像*某种*有效固件。一个引导程序镜像和一个
应用程序镜像都具有同样合理的堆栈指针——相同的芯片、相同的 RAM——因此仅凭
这一项检查，如果其中一个最终进了另一个的槽，是无法区分它们的。能够区分的
是：一个已链接镜像的**复位处理程序**是一个在链接时烘焙进去的真实的、
绝对的地址，它永远只会指向它实际所链接的那个区域内部。已针对本项目自身
真实编译的 `BOOTLOADER.bin`/`APP.bin` 进行了验证：它们的复位处理程序分别
为 `0x08000785` 和 `0x0800C0CD`，各自正确地位于其自身槽的地址范围内、
并在另一个槽的范围之外——因此将任意一个放入错误的槽都会被捕获并阻止，
而非被静默接受。相同的逻辑也适用于 `.hex`/`.elf`，只是改为针对它们自身
嵌入的加载地址进行检查。

**检查选项字节**（同一个 SWD/JTAG 编程选项卡，仅限 STM32CubeProgrammer——
pyOCD 没有以相同方式通过 CLI 公开这一功能）：一次只读的 `-ob displ`
转储，不涉及擦除/写入。以本工具在 SWD 风险方面一贯的谨慎态度标记 RDP 级别：
- **RDP0** —— 无保护，对开发板而言正常。
- **RDP1** —— 可通过 CubeProgrammer 的读出解除保护逆转，但那会作为解除
  保护的一部分批量擦除芯片——本工具不会为你自动执行此操作。
- **RDP2** —— 整个项目中唯一真正**永久性**的锁定。与上文记录的每一项
  其他风险（都可通过 SWD 恢复）不同，RDP2 依据 ST 自身的设计永久禁用
  调试端口。这项检查的存在是为了在一次完整芯片操作之前捕获它，而不是
  之后。

**探针选择**（同一选项卡）：如果同时连接了多个 ST-Link/探针，每一条命令
都需要从探针下拉框中明确选择一个——不存在“操作系统碰巧先枚举到哪一个
就用哪一个”这种情况。恰好连接了一个探针时，会自动选中；连接了零个或
多个时，点击刷新并选择。这同样适用于完整芯片刷写和选项字节检查，因为
两者都足够接近破坏性操作，在一个多设备工作台上猜错板卡是一项真实的风险。

**pyOCD 的写入会通过一次显式的读回进行验证**，而不仅仅是信任退出码。
pyOCD 自身的 `flash` 命令会跳过重写已经匹配的页面（这是一种速度优化，
而非验证报告），因此本工具在写入之后为两个镜像都添加了一个
`commander compare` 步骤——一次真正的逐字节检查，与 STM32CubeProgrammer
的 `-v` 标志已经做的相同。仅适用于 `.bin`：`compare` 会将闪存内容与文件
的原始字节进行比对，这即使在成功刷写之后也不会正确匹配 `.hex`/`.elf`
文件自身的编码，因此这两种格式会跳过这一特定步骤，转而依赖 pyOCD 自身
内部的写入时验证。

### 传输遥测与详细的验证失败原因

**传输遥测**：日志在一次 CAN 更新期间显示每页的有效 KB/s 和耗时，以及
末尾的一行摘要（总耗时、平均 KB/s、发生了多少次页 ACK 重试）。纯粹是
信息性的——不会改变刷写行为，只是让人更容易一眼分辨出“这只是慢”还是
“确实出了问题”。

**具体的验证失败原因**：如果在一次 CAN 更新期间验证失败，
`bootloader_protocol.c` 会随状态 `0x05`（验证失败）一起发送一个原因字节——
传输不完整、CRC32 不匹配、HMAC 不匹配，或 HardwareID 不匹配，而不是每一次
失败看起来都一样。确切的帧格式见 `docs/CANBUS.TXT`（`0x7F5`，此特定状态
下 DLC 为 2）。本工具与引导程序在这个帧格式上是一致的，因此如果你正在
构建一个带有不同版本协议的自定义引导程序，请将两者一起刷写。

**扩展从属的相同细节**：一次失败的从属更新（目标：“扩展从属”）会在
`0x215` 报告 `STATUS_VERIFY_FAIL` 之后立即查询 `0x219`，中继从属引导程序
自身的 `REG_VERIFY_FAIL_REASON`——与上文相同的 5 种原因，只是通过 I2C
桥而非直接从一个 CAN 帧读取。需要一个实现了 `0x219` 的从属引导程序
（与本工具自身对它的支持同时添加）；一个较旧的从属引导程序对该查询根本
不会应答，本工具会转而回退到通用的“验证失败”消息。

### 刷写前的可选 F-RAM 擦除

第 3 节有一个复选框，**“刷写前同时擦除持久化 F-RAM”**——默认关闭。如果
勾选，它会在更新序列开始之前，向板卡板载的 FM24CL64B 持久化 F-RAM 发送
魔术负载擦除指令（`0x192`——见 `docs/CANBUS.TXT`），清除它已保存的任何
工具参数状态。

**正常更新不需要此项。** 已保存记录自身布局中的版本不匹配已经在下次启动
时被检测并安全地忽略了（见 `src/F303-master/README.md` 的参数持久化
一节）——这个复选框的存在是为了实现一次真正的全新开始，而不是因为跳过它
会留下任何损坏的东西。

**仅在应用程序运行时有效**——引导程序本身根本不处理 `0x192`，只有
`firmware_can_global_post.c` 处理。如果其上方的“板卡当前正在运行应用程序”
复选框未勾选，本复选框会被静默跳过（并附带一行说明原因的日志），因为
在那种情况下，板卡被假定已经处于引导程序中。

**缺少确认不会停止刷写。** 如果擦除指令自身的确认帧未在 2 秒内返回，
这会被记录为一条警告，实际的固件更新仍会继续进行——擦除是本工具真正
目的旁边的一个次要的、可选的步骤，不应该因为其自身的确认帧丢失而中止
一次原本会成功的更新。如果这对你很重要，请单独检查 F-RAM 状态
（`URTC Tester` 自身的查询状态按钮）。

<!-- urtc-section:heads -->
### 一条总线上的多个工具头

固件可以让多个工具头共用一条 CAN 总线（多节点扩展）。它**默认关闭**，只有一个工具头的总线与以前完全一样地工作。**工具头**窗口会查找工具头，列出每个工具头的地址、工具和序列号，并显示其状态：就绪、已选择、地址冲突、故障已锁定、处于引导程序或已丢失。您选择一个后，程序会先请您确认，之后才向该工具头发送任何内容；只要总线上有多个工具头，在选中一个并得到它的确认之前，命令都会被拒绝。如果所选工具头丢失，所有工具头都会进入安全状态（窗口中的复选框可关闭此行为）。目前只针对总线模型测试过，没有在电路板上试过。参见 URTC-COMMON 中的 `docs/MULTINODE.md`。
<!-- /urtc-section:heads -->

## 🔒 安全与防护

| 风险 | 防御 |
|---|---|
| 把镜像刷到错误的板子上 | 引导程序协议的 HardwareID 检查，在写入任何内容之前进行 |
| 损坏、未签名或被篡改的镜像 | 镜像完整性检查；清单的 `sha256` 与文件不符会在任何总线通信之前被拒绝，未签名的镜像被拒绝，已发布的签名在不使用任何密钥的情况下发送；使用发布版镜像之前会核对发布签名（Ed25519） |
| 误装较旧的镜像 | 引导程序的防回滚检查；有意回退需要降级授权 |
| 更新失败让板子变砖 | 黄金镜像模型：备份槽保留之前的固件，丢失的确认帧通过再次询问版本来恢复，而不是报告错误的失败，并且可先回读主槽 |
| 本程序的更新被篡改 | “检查更新”只接受 SHA-256 和 Ed25519 签名都有效的软件包（程序中固定的发布密钥），确认后才安装，绝不在传输期间安装，并保留之前的版本 |

引导程序用 CRC32 和共享密钥 HMAC-SHA256 检查镜像，而不是非对称签名；已发布的应用镜像用公开的开发密钥签名，所以任何人都可以做出引导程序接受的镜像。这一切都没有在真实的板子上运行过。

### CAN 更新期间的可靠性，以及会话日志

如果在一次 CAN 更新期间，某一页的 ACK 未在正常的 3 秒窗口内到达，工具会在
放弃之前，以短暂的退避再次等待（不会重发该页的数据）最多两次。这只对仅仅
延迟到达的 ACK 有帮助：引导程序对每一页的 ACK 只发送一次，绝不重复，因此
真正丢失的 ACK 无法恢复，更新会以错误中止（板卡停留在其引导程序中，可直接
重新开始更新）。工具刻意不会在超时时重发页面数据——如果数据其实已正常到达，
重发会让引导程序将那些字节读取为*下一页*的开头，导致传输失步。等待期间，
引导程序自身的心跳（大约每秒发送一次）会与该页所应对应的进度进行比对，
一致时日志会注明；心跳是整数百分比，因此这只是一个提示，并不能证明该页
已到达，也绝不会改变结果。

每个会话还会向 `logs/`（`urtc_flasher_YYYYMMDD_HHMMSS.log`）写入一个带
时间戳的日志文件，独立于屏幕上的日志——如果现场出了问题，便于将完整的
追踪记录交给编写固件的人。这个文件夹会自动创建，删除也是安全的；没有任何
东西会读回旧日志。 只会保留最新的 30 个会话日志；如果无法写入程序旁边的文件夹（只读安装），则改用每用户文件夹（Windows 上为 `%LOCALAPPDATA%\URTC-Flasher\logs`，其他系统为 `~/.local/state/urtc-flasher/logs`）。

## 🔌 接口

适用于没有显示器的 CI 流水线、测试台或生产线脚本：

```
python3 urtc_flasher.py --cli --port /dev/ttyACM0 --file firmware.bin
```

```
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan,python-can,mock}] --port PORT
                             --file FILE [--no-trigger] [--force]
```

退出码：`0` 成功，`1` 协议/连接错误，`2` 参数错误或固件文件未通过验证
（传入 `--force` 仍可强制刷写），`130` 通过 Ctrl+C 取消。仅覆盖 CAN OTA
更新路径（第 1-3 节）——SWD/JTAG 完整芯片路径目前刻意仅限 GUI 使用，
考虑到如果一次脚本化运行在无人监视的情况下弄错了文件/目标组合，风险会
大得多。

**`--transport python-can`** 使用可选的 `python-can` 包（`pip install python-can`），支持 PCAN、Kvaser、gs_usb/candleLight 及其支持的其他接口，因此无需把适配器重刷为 SLCAN：此时 `--port` 为 `<接口>:<通道>`（例如 `pcan:PCAN_USBBUS1`），总线以 500 kbit/s 打开。安装了 `python-can` 时，窗口也提供同样的适配器：python-can 为 PCAN、Kvaser 和 gs_usb 找到的适配器，以及环境变量 `URTC_PYTHON_CAN`（以逗号分隔的 `<接口>:<通道>`）中列出的适配器，显示为 `python-can:<接口>:<通道>`；该连接的总线速度固定为 500 kbit/s。窗口也可以用 `--firmware 路径` 启动，使镜像已被选中（在您连接并确认更新之前，不会向板子写入任何内容）。

**`--transport mock`** 针对一个模拟的、内存中的引导程序运行整个更新序列，
而非真实板卡——不涉及适配器、端口，或任何物理设备：

```
python3 urtc_flasher.py --cli --transport mock --file firmware.bin --no-trigger
```

适用于在 CI 流水线中测试本工具自身的逻辑（重试行为、超时处理、退出码），
或在接触真实硬件之前进行测试——不会与实际板卡通信。`--mock-fail 0x03`
（或 `docs/CANBUS.TXT` 中任何其他 `VERIFY_FAIL_REASON_*` 值）会让模拟更新
验证失败而非成功，以便同样方式测试失败路径。

## ⚙️ 配置

本工具**不包含任何签名密钥**。URTC 构建为每个应用镜像签名，并把签名发布在
镜像旁边的 `<image>.manifest.json`（`hmac_sha256`，另有 `<image>.sha256`）中；
刷写工具发送该已发布的签名，并拒绝 sha256 与清单不符的镜像。从 GitHub 下载
镜像时会同时下载这两个文件，`python tools/sync_firmware.py` 会根据 URTC 构建
更新随附的 `firmware/` 文件夹（`--check` 用于校验）。默认从 URTC 最新发布版本的资源（assets）中获取这一组文件（`--release TAG` 可选择其他版本）；也可以改为传入本地文件夹作为参数，例如本地的 URTC 构建。只有在测试板上刷写没有
清单的自建镜像时才需要密钥：在下方的 `urtc_config.json` 中设置
`hmac_key_hex` / `slave_hmac_key_hex`——没有密钥时，此类镜像会被拒绝，而不是
用引导程序不可能拥有的密钥签名。参见 URTC 的 `docs/FIRMWARE_SIGNING.TXT`。 已发布的镜像使用公开的开发密钥（`signing_key_kind: dev`）签名，因此这只是共享密钥校验：它表明镜像由持有该密钥的人生成，而不表明对方是谁；非对称签名（Ed25519）仍在计划中，尚未实现。

**或者在不改动脚本的情况下覆盖这一切：** 一个位于 `firmware/` 旁边的
可选 `urtc_config.json` 可以设置签名密钥、HardwareID，以及内存映射值——
适用于不同的板卡修订版本、一个轮换的密钥，或者（对于内存映射字段）
将本工具适配到不同的芯片变体或分区方案，而无需为每次部署都发布一个
新的脚本版本：
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
每个字段都是可选的——只覆盖实际需要更改的内容。缺失的字段会回退到本工具
自身内置的默认值。**内存映射和 HardwareID 的覆盖仅适用于主板自身的常量**（唯一的例外是扩展从属芯片的签名密钥 `slave_hmac_key_hex`，它也可以在这里设置）——扩展从属芯片
自身的等效常量（`SLAVE_BOOTLOADER_FLASH_ADDR`、`SLAVE_APP_FLASH_ADDR`、
`SLAVE_HARDWARE_ID` 等）固定在 `flasher_config.py` 自身中，因为该硬件
自身的真实值已经根据其自身的链接脚本得到确认，而不像主板自身的默认值
那样需要一个部署时的覆盖。一个存在但损坏的文件会记录一条警告，同样会
回退，而不会因为一个拼写错误就使工具崩溃。当前处于活动状态的来源会在
启动时被记录，因此某个会话实际使用了哪些值始终是可见的。`hardware_id`
既接受一个 JSON 字符串（`"0x0303CC01"`），也接受一个纯粹的 JSON 数字
（`50580689`）——无论文件生成方式哪种更自然。`app_max_size`、
`bootloader_max_size`、`flash_page_size`、`bootloader_flash_addr` 和
`app_flash_addr` 在这里也都可以覆盖，与上方的签名密钥和 HardwareID
一起——如果本工具日后被适配到不同的芯片变体或分区方案，这会很有用。

## 🚀 快速开始

### 让你的适配器与 CAN 通信

你需要哪些内容取决于你的平台以及你将使用的传输方式：

**Linux，SocketCAN 路径（如果你的适配器支持，推荐使用）：**
适配器本身无需刷写任何内容。每次启动时启用一次接口（或将其添加到网络配置中
使其持久生效）：
```
sudo modprobe can vcan gs_usb   # gs_usb 覆盖大多数 CANable 系列板卡
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up
```
如果你的适配器枚举出的接口名并非 `can0`，请查看 `ip link show`（或插入设备后
立即查看 `dmesg`）以获取实际名称。有些适配器需要 `slcand` 而非原生驱动——
如果插入设备后 `ip link show` 根本没有显示任何 CAN 接口，很可能就是这种情况；
请参见你适配器的文档以获取 `slcand` 的调用方式，它会创建一个 `slcan0` 接口，
随后你按上述相同方式启用它。

**Windows，或通过串口/SLCAN 路径的 Linux：**
CANable Pro v2 默认出厂运行 **candleLight** 固件，它使用 `gs_usb` 协议与主机
通信——这与 Linux SocketCAN 的 `gs_usb` 驱动原生所期望的协议相同（见上文）。
该协议**不会**呈现为一个串口，而这正是这条路径所需要的。若要改用串口/SLCAN
（Windows 上必需；Linux 上可选）：

1. 为你的适配器下载兼容 SLCAN 的固件（搜索“canable slcan firmware”——有几个
   维护中的分支；使用你适配器自身文档所指向的那一个）。
2. 将适配器置于 DFU/引导程序模式（通常是在上电时按住 BOOT 按钮，或使用一个
   跳线——请查看你适配器的文档）。
3. 使用你适配器厂商的刷写工具或 `dfu-util` 刷写 SLCAN 固件。
4. 重新连接——它现在应该会枚举为一个串口：Windows 上是一个 COM 端口，
   Linux 上则类似 `/dev/ttyACM0`/`/dev/ttyUSB0`。

如果你的适配器已经运行 SLCAN 固件，直接跳到下方的第 2 步。

一条接收到的 SLCAN 行，如果其实际长度与其自身声明的 DLC 所暗示的长度不匹配，
会被视为格式错误并跳过，而不是不管后面跟着什么都从其前 N 个十六进制字符解析——
如果你正在针对一个嘈杂或非标准的适配器进行调试，这一点值得了解。

### 安装与运行

**Windows：**
```
python -m pip install -r requirements.txt
python urtc_flasher.py
```
或使用 `build_exe.bat` 构建一个独立的 `.exe`（见该文件）。

**Linux：**
```
python3 -m pip install -r requirements.txt
python3 urtc_flasher.py
```
或使用 `./build_exe.sh`（先 `chmod +x` 它）构建一个独立的二进制文件。

两个脚本都向 PyInstaller 传递了 `--noconfirm`，因此在已存在的
`dist/URTC_Flasher` 上重新构建会直接替换它，而不会等待一个在脚本输出中容易
被忽略的“是否替换？”提示。

#### 可视化控制台

**Qt Quick** 控制台是程序唯一的窗口（仅针对模拟器测试；镜像检查使用共享密钥的 HMAC-SHA256）。使用以下命令启动：
~~~
python urtc_flasher.py
~~~
它采用深海军蓝/青色界面，包含连接卡片、易读的固件表格、深色验证日志和清晰可见的进度条，并覆盖完整流程：对主板或扩展从机进行 CAN-OTA 更新（可选择目标；“板子正在运行应用程序”选项、F-RAM 擦除和降级授权仅适用于主板）、通过 CAN 备份已安装的固件、带仅监听搜索的总线速率选择器、下载 GitHub 发布版本、可选任意 `.bin` 的文件选择器、总线活动检查、Board Snapshot、4 项设备配置写入、只读的 SWD/JTAG 发现，以及通过 SWD/JTAG 对整个芯片编程（擦除/写入、试运行、擦除前备份、RDP 检查）。凡是写入板子的操作都会先请求确认，降级授权会再确认一次，传输过程中关闭窗口也会再次询问。这些都尚未在真实板子上试过。`python urtc_flasher.py --cli` 为无界面模式（第 7 节）。

#### 标题栏与工具

- **标题栏** - 连接状态、语言选择器（选择会被保存，并在下次启动时生效）和版本号。
- **保存日志...** 和 **保存调试包** - 以纯文本保存屏幕日志，或保存包含系统诊断和所选固件文件的更完整 zip（见下文“诊断”）。每次会话也会写入 `logs/`，并保留最新的几份。
- **关于 URTC Flasher** - 版本和作者，带有 **自述文件**（有翻译时使用界面语言）、**许可证** 和项目 **URTC GitHub** 页面的按钮。

**语言**：默认为英语。
通过窗口顶部的语言选择器切换——立即保存到`urtc_config.json`（与技术性硬件覆盖设置所使用的是同一个文件——语言偏好
只是存放在这些设置旁边），在下次启动时应用。翻译文件以纯文本形式存放在
`language/` 下（`english.lng`、`spanish.lng`、`italian.lng`、`french.lng`、
`german.lng`, `japanese.lng`, `chinese.lng`, `portuguese.lng`），采用简单的 `KEY=Value` 键值对，一行一个——以 `#` 开头的行
和空行会被忽略，值内部的字面 `\n` 会变成真正的换行符（用于少数几个多行
对话框消息）。这些文件由 URTC-COMMON 的目录生成（翻译在那里修正后重新写入文件，从不手工编辑），也可以将其作为新增另一种语言的起点（添加 `language/<name>.lng`，在 `flasher_config.py` 顶部附近的
`AVAILABLE_LANGUAGES` 中添加 `("<name>", "本地语言名称")`，并在
`urtc_config.json` 中设置 `"language": "<name>"`）。语言文件中缺失的键会
回退为显示该键自身的名称而不是崩溃，缺失或无法读取的语言文件（编辑错误、
文件名错误）会为整个界面回退到英语——无论哪种情况，工具在问题被解决之前
都能保持可用。

**Linux 串口权限：** 如果你使用串口/SLCAN 路径，且连接失败并显示“权限被拒绝”，
你的用户需要加入拥有串行设备的用户组（Debian/Ubuntu 上为 `dialout`；
其他发行版可能不同）：
```
sudo usermod -a -G dialout $USER
```
注销并重新登录（用户组成员身份在登录时读取），然后重试。本工具会检测这一
特定错误，并在对话框中展示同样的解决方法，但提前了解这一点是值得的。
SocketCAN 没有这个特定的坑——访问一个类似 `can0` 的接口不受 `dialout` 组
的限制——但首先启用该接口（上文第 1 步）确实需要 `sudo`，因为那是一项
网络设备配置更改。

使用 `python -m pip`/`python3 -m pip` 而非裸的 `pip` 可以避开两个平台上
一个常见问题：即使刚成功安装之后，`pip` 自身的包装脚本也并不总是在 PATH
中，而 `-m pip` 则直接找到已安装的模块。

### 固件文件存放位置

**该文件夹一开始是空的。** 固件镜像不保存在本仓库中：它们是 [URTC](https://github.com/JuanenRac/URTC) 各版本发布的附件。窗口会从你选择的发布版本下载，`python tools/sync_firmware.py` 会从最新的正式发布版本（或 `--release TAG`）填充该文件夹。每个文件在使用前都会用发布签名（`.sig`，Ed25519）和摘要进行校验。在没有正式发布版本期间，GitHub 的 “latest” 会返回 404，由 `firmware_release.json` 指定改用的发布版本（目前是台架预发布版）；发布正式版本后，请删除该文件或修改其标签。

本工具期望在 `urtc_flasher.py` 旁边、也就是本仓库自身的根目录下，存在一个
`firmware/` 文件夹：

```
├── assets/
│   └── URTC_LOGO_FLASHER.svg      <- 横幅源文件（矢量图）
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v<version>.bin  <- 将新的 .bin 文件放在这里
│   └── URTC_*  <- tools/sync_firmware.py 会用某个发布版本的文件替换此文件夹中的 URTC_* 文件；其他文件保持不变
├── logs/                          <- 自动创建，每个会话一个文件
├── urtc_config.json               <- 可选，默认不包含（见下方“更改 HMAC 密钥”）
├── urtc_flasher.py                <- 入口：CLI 参数与 Qt Quick 窗口的启动
├── flasher_config.py              <- 配置文件 I/O、语言加载、协议常量
├── flasher_transports.py          <- SLCAN、SocketCAN、MockCAN
├── flasher_swd_tools.py           <- STM32CubeProgrammer / pyOCD 包装器
├── flasher_validation.py          <- 固件文件验证（.bin/.hex/.elf）
├── flasher_protocol.py            <- CAN OTA 状态机本身
├── flasher_github.py               <- 列出并下载 URTC GitHub 发布版本的资源（assets）
├── flasher_records.py             <- 会话日志（位置、保留）与更新报告
├── pytest.ini / ruff.toml          <- pytest 和 ruff（静态检查）的设置
├── requirements.txt
├── build_exe.bat                  <- Windows 独立构建
├── build_exe.sh                   <- Linux 独立构建
└── README.md
```

本工具按职责被组织为上述模块，纯粹是为了可读性——将它们作为独立文件与作为
一个大文件，在功能上没有任何区别。

这是刻意为之的：整个仓库都是自包含的。如果你只是想刷写一块板卡——在车间的
电脑上、从一个 U 盘上，任何地方——你可以单独复制这个仓库，它依然可以正常
工作。

**你可以在其中保留不止一个 `.bin` 文件。** 每一个应用固件文件都会被检查
并列出——本工具不会随便抓取找到的第一个文件，且引导程序二进制文件
（文件名中带有“BOOTLOADER”的任何文件——`URTC_BOOTLOADER.bin`、
`URTC_SLAVE_BOOTLOADER.bin`）会被完全从这个列表中过滤掉，因为 CAN-OTA
永远只刷写应用固件；引导程序更新需要改用 SWD/JTAG（见下方第 6 节）。
在启动时（以及每次点击**刷新**时），`firmware/` 中每一个剩余的 `.bin`
文件都会针对引导程序自身应用于一个全新镜像的相同合理性测试进行检查（其
前 4 个字节必须看起来像该芯片 RAM 的一个真实初始堆栈指针，且其大小必须
适合主槽）。每个文件都会在列表中显示清晰的 ✓ 或 ✗ 以及原因：

| 文件 | 大小 | 状态 |
|---|---|---|
| URTC_MAIN_FIRMWARE_v<version>.bin | 71.8 KB | ✓ 看起来有效 |
| URTC_SLAVE_FIRMWARE_v<version>.bin | 33.9 KB | ✓ 看起来有效 |
| notes.txt.bin | 0.1 KB | ✗ 第一个字看起来不像一个有效的堆栈指针 |

- **恰好有一个文件通过检查** → 工具启动的那一刻就会为你选中它。文件夹中
  孤零零一个无效文件并*不会*仅仅因为没有其他文件与之竞争就被自动选中。
- **多个有效文件** → 不会自动选中任何一个；从列表中挑选你想要的那一个。
- **你仍然选择了一个看起来无效的文件** → 工具会先要求你确认。这项检查的
  存在是为了捕获明显的错误（错误的文件、下载不完整、一个空的占位符）——
  它不能捕获所有情况（一个损坏但看似合理的文件，或一个用错误密钥签名的
  文件），这正是引导程序自身在真实传输过程中的 CRC32/HMAC 检查所要做的事。
- **什么都没找到，或你想要一个完全来自其他地方的文件** → 使用**浏览 .bin...**
  按钮，无论该文件实际存放在哪里都可以使用（并且同样会运行相同的验证检查）。
- **想要最新构建版本又不想自己去找** → **从 GitHub 下载...** 会列出
  URTC 仓库最新 GitHub 发布版本（release）所附带的文件
  （`github.com/JuanenRac/URTC/releases`——固件二进制文件作为发布版本的
  资源（assets）发布，不再保存在 git 中），让你选择一个直接下载到你自己
  本地的 `firmware/` 文件夹中——它随后会像任何其他文件一样出现在上方列表
  中，无需重启。在窗口顶部的输入框中填写发布标签（例如 `v0.3.5`）并点击
  **加载**，即可列出最新版本以外的其他发布版本。镜像的 `.sha256` 和
  `.manifest.json` 会随它一同下载。只接受来自 GitHub 自身主机的文件
  （`github.com` 以及它重定向到的资源存储主机），大小与发布版本所声明的
  不一致的文件会被丢弃。使用 GitHub 自身的公共 API（未经身份验证，因此
  如果短时间内频繁使用会受限于 GitHub 每小时 60 次请求的限制；设置环境
  变量 `GITHUB_TOKEN` 可以提高该限制）——这里的任何内容都不需要 GitHub
  账户。

正式发布的每个文件都有发布签名（`<文件>.sig`，Ed25519）：刷写器在签名存在时会验证，并拒绝错误的签名。没有签名的文件集（例如试验台预发布版）只有加上 `--allow-unsigned` 才会被 `tools/sync_firmware.py` 接受。

**与每个固件文件放在一起的 `<filename>.manifest.json` 和
`<filename>.sha256`**——由 URTC 构建为每个镜像发布（从 GitHub 下载时会一并
下载）。清单包含版本、`sha256`，对于应用镜像还包含引导程序期望的
`hmac_sha256` 值（共享密钥的 HMAC-SHA256，并非非对称签名；`signing_key_kind: dev` 表示公开的开发密钥）：

```json
{"component": "main_application", "version": "<version>", "sha256": "b48d4cd5...", "hmac_sha256": "b63a701e...", "signing_key_kind": "dev"}
```

刷写前会立即校验这两个摘要，不一致时会在向总线发送任何数据之前**拒绝刷写**
（文件错误、下载损坏或清单过期）。发送给引导程序的是已发布的签名，报告给它
的是清单中的版本。没有清单的文件（自建镜像）只有在 `urtc_config.json` 中设置
了签名密钥时才会刷写——参见下文更改 HMAC 密钥。

以后添加新的构建版本：只需将其放入 `firmware/` 并点击**刷新**——无需重启。

<!-- urtc-section:first_flash -->
### 无硬件的首次运行

1. 启动虚拟开发板：`python -m urtc_can.virtual_board`。
2. 在另一个终端设置 `URTC_VIRTUAL_PORT=socket://127.0.0.1:7777` 并启动刷写器：虚拟开发板会出现在端口列表中。
3. 选中它，点击连接，从 `firmware/` 选择镜像（或浏览选择），然后点击开始 CAN-OTA。
4. 虚拟开发板会接受完整更新，并像真实开发板一样检查大小、签名和版本。它只是一个模型：以上均未在开发板上运行过。
<!-- /urtc-section:first_flash -->

<!-- urtc-section:compatibility -->
### 要求与兼容性

哪些版本的 URTC 程序可以配合使用、各自使用哪个协议版本，列在 URTC-COMMON 生成的兼容性表中：[docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md)。
<!-- /urtc-section:compatibility -->

## 🧪 测试

测试套件在 47 个文件中共有 500 个测试（`python -m pytest tests -q`；在没有屏幕的机器上使用 Qt 时设置 `QT_QPA_PLATFORM=offscreen`；其中 79 个需要 PySide6，没有它时会被跳过）：针对真实 `MockCAN` 传输层的 CAN-OTA 协议（它回放完整的模拟引导程序：开始、擦除、接收、页数据和 ACK、HMAC 数据块、带真实成功或特定 `VERIFY_FAIL_REASON` 的更新结束）、签名规则、镜像完整性检查、`firmware/` 中内置的固件与其清单的核对、用 `dry_run` 构造的 SWD/JTAG 命令、语言文件和 Qt Quick 面板。根目录下的三个脚本（`verify_qt_*.py`）对 Qt 面板做端到端驱动。CI 还会运行 `ruff check`、`python -m mypy` 和 `tools/ci_validate.py`。`MockCAN` 只是根据协议写成的模型：它比真实的引导程序宽容，所以测试全绿并不能代替在真实板子上的试验。

## 🏗️ 构建与发布

`build_exe.bat` / `build_exe.sh` 用 PyInstaller 构建独立程序（两者都传入 `--noconfirm`，因此在已有的 `dist/URTC_Flasher` 上重新构建会直接替换它）；`build-test.sh` / `build-test.bat` 检查所有内容，但不构建任何东西，也不改变版本。程序的版本（`flasher_config.py` 中的 `FLASHER_VERSION`，显示在窗口横幅和标题栏）只会通过明确的 `python bump.py` 步骤改变；从源码运行和构建都不会触碰它。版本历史见 `CHANGELOG.md`。

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="URTC-FLASHER 的仓库结构" width="100%">
</p>

<details>
<summary>目录树的文本版</summary>

```text
URTC-FLASHER/
├── urtc_flasher.py                                    入口
├── qt_flasher.py                                      Qt Quick 面板
├── flasher_*.py                                       协议、检查、传输、SWD、记录
├── verify_qt_*.py                                     Qt 面板的端到端检查
├── urtc_can/                                          协议、传输和更新（副本）
├── urtc_ui/                                           界面辅助（副本）
├── firmware/                                          镜像存放处（起初为空）
├── tests/                                             47 个测试文件，每个领域一个
├── language/                                          八个 .lng 语言文件
├── assets/                                            QML、横幅和图标
├── docs/                                              架构、构建与运行
├── logs/                                              会话日志（不进入 Git）
├── tools/                                             构建检查、固件同步、共用工具
├── images/                                            横幅和本 README 的图片
├── .github/                                           CI 工作流以及 Issue 和 Pull Request 模板
├── test.sh test.bat                                   运行测试
├── run.sh run.bat                                     启动程序
├── build-test.sh build-test.bat                       构建并测试的脚本，不会修改仓库内容
├── urtc.project.json                                  清单：版本、角色、成熟度和构建命令
├── CHANGELOG.md                                       每个版本的变更
├── SECURITY.md SUPPORT.md LICENSE                     安全政策、支持和许可证
├── CONTRIBUTING.md CODE_OF_CONDUCT.md                 如何参与贡献和行为准则
├── .gitattributes .gitignore                          Git 设置
├── build_exe.sh build_exe.bat                         独立程序 (PyInstaller)
├── bump.py bump_version.py bump_manifest_version.py   提升版本号的脚本
├── requirements*.txt requirements*.lock               依赖及其锁文件
├── mypy.ini pytest.ini ruff.toml                      类型检查、测试和 lint 设置
├── urtc_config.json.example                           硬件覆盖设置和语言的示例
├── urtc_i18n.lock.json                                生成语言文件的锁文件
└── NOTICE LICENSE.md                                  版权声明和文档许可证
```

</details>

每个源文件的带注释清单（每个文件一行）见 [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md)。

## 🗺️ 路线图与已知限制

**状态：** 本工具中的 CRC32 和 HMAC-SHA256 计算已针对引导程序自身的 C 实现
逐字节验证，SocketCAN 帧打包也已通过一次往返打包/解包测试针对 Linux 的
`struct can_frame` 布局进行了验证。在这两个平台上**尚未**经过测试的是，
针对真实硬件的真实板卡——请以对待任何与引导程序通信的新工具同样的谨慎态度
对待首次真实刷写尝试：手边备好 JTAG 作为后备手段。 这里描述的其他功能都只针对模拟引导程序 `MockCAN` 测试过，从未针对真实板卡测试过。

## 🌍 语言

README 和文本提供英语、西班牙语、法语、意大利语、德语、汉语、日语和欧洲葡萄牙语版本。

## 🔗 相关项目

URTC 由相互独立的仓库组成，每个仓库都有自己的版本、测试和 README。以下是按组划分的家族：

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - 工具头电路板的固件(25 个工具配置、CAN 引导程序)以及 CAN 协议参考。
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - 只写一次的 CAN 协议数据(规范、生成的表格、一致性向量)以及各程序共享的代码。
  * **URTC-FLASHER** (本仓库) - 通过 CAN 或 SWD/JTAG 更新电路板固件的桌面工具。
  * [URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY) - 位于 CAN 总线前的网关:只放行列表中的标识符,限制其速率,并要求会话密钥。
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - 用于带预热和生命周期跟踪的工具架的、与硬件无关的 C 逻辑和命令协议。
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - 桌面实时 CAN 总线测试器,显示电路板所报告工具配置的控件和遥测。
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - C 语言的传感器帧协议,以及用于检测工具头的 Python 热成像/RGB 配套程序。
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - 通过 Web Serial 和 SLCAN 烧录并测试电路板的浏览器应用,无需安装。
* **Ecosystem Operations:**
  * [URTC-DEVTOOLS](https://github.com/JuanenRac/URTC-DEVTOOLS) - 家族共用的仓库工具，作为带版本的整套工具，并用锁文件区分被改动的副本和已过时的副本。
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - 生态系统的架构、接口、安全基线和生成的目录,以及比较所有仓库的工具。
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - 检测、安装并更新 URTC 家族仓库的桌面工具,每次只执行一个明确的操作。

**姊妹项目（相互独立，共用同一基础和工具）：**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - 姊妹项目：HYDRA-UMC 的文档中心，一个独立的生态，与本生态共用基础和工具
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - 姊妹项目：A.R.M.O.R. 安全生态的文档中心，同样独立，建立在同一基础上
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - 所有生态的个人主页和状态面板

## 📚 文档

- **[CONTRIBUTING.md](CONTRIBUTING.md)** —— 提交 Pull Request 所需的技术栈和编码规范。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** —— 本社区所期望的行为准则。
- **[SECURITY.md](SECURITY.md)** —— 如何报告漏洞，以及本项目真实的安全关注重点。
- **[SUPPORT.md](SUPPORT.md)** —— 在哪里提问和报告缺陷。
- **[LICENSE.md](LICENSE.md)** —— 本项目自身的许可证。

## 🤝 参与贡献与社区

* 提交 Pull Request 之前请运行 `URTC_CI=1 python tools/ci_validate.py`：必须通过。参见 [CONTRIBUTING.md](CONTRIBUTING.md) 和[行为准则](CODE_OF_CONDUCT.md)。
* README 有八种语言：修改文字时要同步修改全部八个文件，与其他仓库共用的章节由 URTC-COMMON 的 `tools/readme_sections.py` 写入。
* 对 CAN 协议的修改从 URTC-COMMON（`spec/can_protocol.json`）开始，并通过经过核对的副本进入本仓库。
* 不要把仅仅构建过的东西描述为已在板子上运行。
* 请私下报告漏洞：[SECURITY.md](SECURITY.md)。问题、想法和报告：electrohobby3d@gmail.com（[SUPPORT.md](SUPPORT.md)）。

## 👤 作者

**JuanenRac**（Electro Hobby 3D）
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 许可证

许可证：源代码为 **GPL-3.0-or-later**，本文档为 **CC BY-SA 4.0**——见本仓库中的
`LICENSE`，或本文档末尾的“许可证与版权声明”一节。

URTC Flasher 版权所有 (c) 2026 JuanenRac（Electro Hobby 3D）。分发本项目
或其衍生作品时必须包含此声明。

本项目由源代码及其自身的文档组成，两者依据不同的许可证提供——各自适合
其实际所涵盖的内容：

1. 源代码（`urtc_flasher.py` 及每一个 `flasher_*.py` 模块）以及通过
   `build_exe.bat`/`build_exe.sh` 从中构建的任何二进制文件，依据
   **GNU 通用公共许可证 v3.0（GPL-3.0-or-later）** 提供。完整文本见
   https://www.gnu.org/licenses/gpl-3.0.html。

2. 文档（本 README 及其自身的翻译版本——`README_spa.md`、`README_ita.md`、
   `README_fra.md`、`README_deu.md`、`README_zho.md`、`README_jpn.md`, `README_por.md`）
   依据 **知识共享 署名-相同方式共享 4.0 国际许可协议（CC BY-SA 4.0）**
   提供。完整文本见 https://creativecommons.org/licenses/by-sa/4.0/。

本工具是 [URTC（Universal Robot Tool Controller）](https://github.com/JuanenRac/URTC)
项目的 CAN-OTA/SWD-JTAG 刷写配套工具——本工具所对接的板卡固件、硬件设计和
完整协议文档见该项目自身的仓库。URTC 自身的固件为 GPL-3.0-or-later，其硬件设计为
CERN-OHL-S v2；本工具自身的许可证并不延伸至那个独立的项目，反之亦然。
一个覆盖类似功能范围的基于网页的替代方案也存在，位于
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)。

如果你基于本项目进行开发，请留意这种许可证划分：代码更改应保持 GPL-3.0-or-later，
文档衍生品应保持 CC BY-SA——每一项都需附带指向本项目及其作者的署名。
