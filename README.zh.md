# CSB-TUI — CubeSandbox 的树状控制台

简体中文 · [English](README.md)

> CubeSandbox 的命令行与 WebUI 只按 id 列资源，关系要自己拼；**CSB-TUI 把它补成一棵树** —— 名字、家族、序号、血缘在本机。

> [!WARNING]
> **这是实验版，可能还有 bug。**

<p align="center">
  <img src="https://raw.githubusercontent.com/Buxton1984/csbtui/v0.1.0/csb-demo.gif" width="900" alt="CSB-TUI 树状 TUI — 五种皮肤轮换">
</p>

<p align="center">
  <sub>内建五种皮肤：obsidian（默认）、synthwave、amber、matrix、paper，按 <code>T</code> 切换，选择会被记住。</sub>
</p>

<p align="center">
  <img alt="license: MIT" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="python: 3.10 或更新" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="cubesandbox SDK: 0.7.3 或更新" src="https://img.shields.io/badge/cubesandbox-%E2%89%A50.7.3-blue">
  <img alt="平台：v0.7.3" src="https://img.shields.io/badge/platform-v0.7.3-blue">
  <img alt="status: 实验版" src="https://img.shields.io/badge/status-experimental-orange">
</p>

CSB 是终端里的树状控制台；资源在集群，名字与血缘在本机。
`csb xxx` 是**命令行**、`单字母`（如 `s`、`n`）是**按键**，做同一件事。

## 目录

**快速开始** [它是什么](#它是什么能做什么) · [安装与启动](#安装与启动) · [快速上手](#快速上手)

**看懂 CSB**　[树的读法](#树的读法节点与标记) · [命名与血缘](#命名与血缘) · [沙箱生命周期](#沙箱生命周期) · [三种「快照」](#三种快照不是一回事) · [本机户籍与多人共用](#本机户籍与多人共用)

**查参考** [按键速查](#按键与操作速查) · [出网（代理）](#出网代理) · [命令行参考](#命令行参考) · [退出码与旗标](#退出码全局旗标与信号) · [环境变量](#附录环境变量) · [设定存在哪](#设定存在哪) · [节点类型总表](#附录节点类型总表)

**出问题**　[疑难排解](#疑难排解) · [授权与致谢](#授权致谢与参与)

## 它是什么、能做什么

```text
   你的终端
      │  csb                    ← 唯一的入口
      ▼
   树状控制台 csb_tui.py         ← 渲染与按键;每个键都调用下面同一套命令
      │  import csb
      ▼
   命令层 csb.py                ← 账本、血缘、安全的删除
      │  官方 Python SDK + 直打 REST
      ▼
   CubeSandbox 集群              ← 模板 / 沙箱 / 快照 / 卷
```

- **按血缘画的树**：模板 / 沙箱 / 快照 / 路标 / 未登记资源同一棵树，左侧键栏随光标换。
- **界面与命令行同源**：同一套命令 ⇒ `-o json` 与固定退出码两边都成立。
- **批量**：`m` 标记、`M` 整段；标记带类型锁（沙箱/快照不能混）；一次确认、一次汇总，失败逐台写原因，不整批回滚。
- **只用官方接口**：官方 Python SDK（健康检查打一次 REST `/health`；`csb admin` 只透传官方 `cubemastercli`）；`i` 可开 tmux / screen / Herdr。

## 安装与启动

### 前置需求

| 需要 | 为什么 |
| --- | --- |
| Python ≥ 3.10 | 纯 Python，无编译步骤 |
| cubesandbox ≥ 0.7.3 | 官方 SDK，唯一运行期依赖 |
| 真终端（TTY） | 非终端印 `csb: give me a command - "csb help" lists them` 并以 **2** 退出；`csb ls` 不需要 TTY |
| 集群地址与 key | 默认指向本机 |

官方 SDK **0.7.3**、本机集群**平台端** **v0.7.3**。默认 `http://127.0.0.1:3000` + 开发用占位 key；自签证书加 `SSL_CERT_FILE`；连别的集群时 `CUBE_API_URL` / `CUBE_API_KEY` 一起换。

没有泛域名 DNS 时**必须**设 `CUBE_PROXY_NODE_IP`（症状与做法见〈疑难排解〉的网络段）。

### 安装

从 PyPI 装：推荐 `pipx`（装在独立环境，不碰系统 Python）：

```bash
pipx install csbtui        # 推荐:独立环境,不碰系统 Python
```

惯用 `pip`、或环境已经建好（venv / 系统 Python）的话：

```bash
pip install csbtui         # 次选:装进当前环境;建议先建 venv
```

不用 `sudo`、安装时不连集群。不需要先准备配置文件：第一次执行任何命令就会建好 `~/.config/csb/`（没有 `config.json` 就用内置默认）。装好后输入 `csb` 进树（只有真终端进得去）。

### 开发者：从源码目录装

改代码、或在 PyPI 上架前，从源码目录装（在 venv 里）：

```bash
pip install .   # 在 venv 里;依赖会自动装上
python3 csb.py  # 不装也能跑(源码目录;SDK 仍必须装)
```

### 装好之后先确认三件事

```bash
csb --version  # 装上了没有(应回 csb 0.1.0)
csb tz         # 本机时区与服务器的钟差(两边时区不一致时,时间列会对不上)
csb ls         # 连得上集群没有(只读沙箱;不建户籍;会写一行审计,并顺手回收死 sbx 政策)
```

### 装完之后，程序文件是哪些

```text
csbtui/
├── csb.py                   命令层:36 条命令(CMDS 共 37 键,含 _completions;界面按的每个键都走到这里)
├── csb_tui.py               树状控制台(TUI,唯一前端)
├── pyproject.toml           打包信息
├── README.md                英文版（主）
├── README.zh.md             本文件
├── csb-demo.gif             README 里那张演示图
└── LICENSE                  MIT
```

### 升级

```bash
pipx upgrade csbtui    # pipx 装的
pip install -U csbtui  # pip 装的
```

只换程序版本；`~/.config/csb/` 与集群上的资源都不动。

### 卸载

```bash
pipx uninstall csbtui      # 只移除程序;~/.config/csb/ 留着
```

从源码 / venv 装的用 `pip uninstall csbtui`（editable 安装也一样）。

常见问题：

- 卸载只移除程序；`~/.config/csb/` 与集群上的资源都不动。
- 要清本机户籍就 `rm -rf ~/.config/csb`；`CSB_REGISTRY` 指到共用路径时，动它等于动别人的名字。
- `pipx` / `pip` 两套装法别混用，当初怎么装就按那种卸；`cubesandbox` 是另一个包，不会一起卸。

## 快速上手

在终端输入 `csb` 进树。

```text
[T] senpi (3)                                 ← 模板,底下 3 个直接子节点
  ├─ [S] senpi_02 (paused) (1)                ← 同一层里新的在上面(由上往下 = 时间倒序)
  │  └─ [S] senpi_03 (running)                ← 从 senpi_02 克隆出来的
  ├─ [S] senpi_01 (running) (1)               ← 沙箱,底下挂 1 张快照
  │  └─ [s] csb-senpi_01
  └─ [D] senpi_00 (deleted) (1)               ← 沙箱已删、快照还在,留在原位当路标
     └─ [s] csb-senpi_00
```

**第 0 步：树上有 `[T]` 才能开沙箱** —— `csb start` 收四种来源（alias / 模板 id / 快照 id / 快照名）。没有 `[T]` 就按 `B` 从容器镜像建一个；已经有匿名模板，按 `A` 起名（匿名模板怎么来的见〈没有 alias 的模板〉）。

**开一台沙箱** —— 停在模板节点按 `s`，依次问（每步 `Esc` 退回上一步，第一步 `Esc` 取消；`network` 选 `off` 跳过清单与代理两页）：

1. **名字** —— 回车取默认 `<家族>_<序号>`；自己填的**永久**。
2. **数量** —— 回车 = 1 台；超过 20 台再确认一次。
3. **network** —— `on` / `off`。
4. **allow out**（仅 `on`）—— 选最近用过的一组、`all` 或手输；`d` 删当前这组。多组用 `,` `;` `、` `|` 或空格分隔，空条目/非 CIDR 当场拒绝。选过的会记住：下次进来时游标优先停在 `(review last egress profile)`（套用整组清单与代理，跳过 proxy 页），模板有政策时停在 `(use template network policy)`，否则停在当前清单上。
5. **proxy**（仅 `on`）—— 选 URL 或 `none`；`d` 删当前这条。选过的会记住。
6. **卷** —— 选卷 → 路径（回车 `/data`）→ 只读与否；**选完就挂，没有第二次确认**；不挂选 `(do not mount a volume)`，「上次一样」贴在它上面，回车沿用。

**在里面干活** —— 沙箱节点按 `e` 运行一条命令、按 `i` 换真终端（复制命令、另开 tmux 窗；Herdr 里还能另开 Herdr 分页）；回车看完整信息，`o` 看运行日志，`?` 看全部按键。

**留一个恢复点** —— 按 `n` 拍快照，默认名字 `csb-<源沙箱名>_<日期>`；快照**独立于沙箱**（沙箱删了它还在）；拍失败显示 `(FAILED)`，不能回滚但**照样能删**（选中按 `d`）。

**复制一台** —— 按 `c` 克隆 N 台。克隆先自动拍一张临时快照共用，树上就是母沙箱底下那张 `[s] snap-xxxx`，标着 `(in use by N sandbox)`；**CSB 不替它回收** —— 副本清光后选中按 `d`（clean）清掉，或 `csb snaprm <id> --yes`。

**收尾** —— 按 `k` 删除沙箱（一次确认）；**删除沙箱不会连带删除快照**（平台设计），原位变成 `[D]` 路标、快照挂它底下。要清干净：先清空底下的快照和沙箱，再回到路标按 `d`。

**筛选器** —— `/` 输子串筛节点，`Esc` 清除（再按 `/` 输空串也行）；树每 2 秒自动刷新，`r` 立刻刷新。可筛：名字 / id / 状态 / 类型 / 家族 / 模板 / 卷名（输卷名 = 列出挂载该卷的沙箱，母节点一起显示）。**筛选与标记同时存在时，`Esc` 先清筛选、标记留着；再按一下才清标记**（状态行会写还剩几个标记）。

- **标记与批量**——`m` 标记当前节点（也是锚点）、移动光标后 `M` 整段标记 / 反选，`m` / `M` / `Esc` 只操作标记；**类型锁**：一批不能混沙箱与快照；一次确认、一次汇总。
- 对整批动手的 9 个键：`k` kill、`n` snapshot、`p` pause、`u` resume、`t` timeout、`c` clone、`d` delete snapshot / clean leftover、`A` adopt、`e` exec。
- 批量只认那 9 个键（`s` / `i` / `o` / `f` / `b` / `l` / `a` 不是）；`commit` 一次一台，回滚不能批量；命令行批量 7 个：`kill` / `pause` / `resume` / `timeout` / `clone` / `snaprm` / `exec`。

> **`A` 的批量只到无名沙箱**：无名模板不能被标记，起名一律单台。

`Ctrl-C` 与 `kill -INT` 不会转发进沙箱（`--sig` 另有 `KILL` / `HUP` / `INT` / `QUIT`）；平台自带服务（envd / jupyter）默认跳过，加 `--force` 才操作；动过这类服务的沙箱只能删除后重建。

## 树的读法：节点与标记

| 标记 | 是什么 | 从哪来 |
| --- | --- | --- |
| `[T]` | 模板 | 官方模板，alias 可改 |
| `[S]` | 沙箱 | 你建的沙箱，带名字与状态 |
| `[s]` | 快照 | 沙箱的恢复点，独立于沙箱 |
| `[U]` | 本机、服务器上都没名字 | 两边都查不到它叫什么（有名字的见〈附录：节点类型总表〉） |
| `[D]` | 路标 | **沙箱**已删、快照还在；**或**模板服务器上已经没有了（只剩本机户籍那一行） |
| `[E]` | 外部路标 | 快照记着来源 id，那台沙箱两边都查不到 |
| `[X]` | 残留 | 本机户籍有、服务器上已经没有了 |

- `(running)` / `(paused)` = 平台状态；`(deleted)` / `(external)` / `(stale)` / `(orphan)` 是 CSB 给路标 / 残留下的标签（见〈附录：节点类型总表〉「小标记」表）；名字后的 `(3)` = 底下几个**直接**子节点（路标也算）。
- 上面几种**只挑常用**，**完整 20 种见[〈附录：节点类型总表〉](#附录节点类型总表)**。
- **记号看类型、名字栏看服务器**：沙箱一律 `[S] <名字>` 或 `[S] <id8>`；写进本机户籍按 `A` 收编（`[U]` 只留给两边都没名字的那一台）。
- **克隆的临时快照标 `(in use by N sandbox)`**：N 是**当下**挂着它的沙箱数；CSB **不自动回收**，要清自己 `csb snaprm <id> --yes`。
- **`[s] unattached snapshots`**：来源两边都查不到又没本机户籍的快照集中在这列（`snap-xxxxxxxx (orphan)`）；照样能 `csb start` 开、`csb snaprm` 删。

### 六种「看起来不对」的节点

- `[D]` 是沙箱路标：服务器只留快照的来源 id(`originSandboxID`)，名字/时间由本机账本补；
  `Enter` 可查同一组字段；清它 = 清快照 → 删除克隆子沙箱 → 按 `d`。
- `[D]` 也是模板残行（服务器已无、只剩本机）；`s`/`l` 显示但不可用，按 `k` 清（`csb tpl rm <alias|id> --yes`）；确认前会印完整 alias/id。
- `[E]`：同一张快照的来源 id 两边都查不到（账本没那一行）；有快照时 `csb tree`/TUI 会补地标
（`seen:true`），最后一张快照删除就跟着走；`CSB_AUTO_NO_SEEN=1` 关闭。
- `[X]`：本机有、服务器没有；按 `d` 清（`CSB_AUTO_HIDE=1` 安静清、`CSB_AUTO_HIDE_ASK=1` 先问，只在清单完整时做）。
- `[U]`：两边都没名字；按 `A` 收编（无名模板走官方 `set-alias`）。
- 本机未登记、服务器有名字：记号照类型给（如 `[S] pi`），名字栏用服务器名。

### 排序与时间

同一层按**时间**排，**新的在最上面**；时间戳以 **UTC** 记录、显示换本地时间带偏移
（`2026-09-14 22:46:47 +08:00`），`metadata.*` 原样回传（`-o json` 仍是原值）；核对时钟打 `csb tz`。

查不到时间的行排最上面（通常是你刚做的那一步）；克隆的临时快照平台不给时间，CSB 用 clone 的时间补上。

根分组顺序：`[T]`（新→旧）→ 有本机时间戳的 `[D]` / `[E]`（新→旧）→
没有时间戳的三组按名字字母序：`[X] leftover record` → `[U] no local name yet` →
`[s] unattached snapshots`；组内按时间，`[U]` 先按类型再按时间。
其余（来源缺失 → `[E]`、平台不给来源 → unattached）见〈附录：节点类型总表〉。

## 命名与血缘

### 三层

| 层 | 是什么 | 长什么样 | 用途 |
| --- | --- | --- | --- |
| 1 | **label** | `<家族>_<序号>`，如 `senpi_03` | 人叫的名字 |
| 2 | **ts** | 服务器 `startedAt`（秒级）；从快照开的带来源时间 | 排序、还原 |
| 3 | **id** | 32 位十六进制 | 溯源唯一锚点 |

- **家族** = 根模板 alias；克隆继承。
- **序号高水位不回收**（删除 `senpi_02`，下一台仍 `senpi_03`）；存 `ledger/highwater.json`；只有 `csb label-reset` 能压回（破坏性）。户籍删了，会先用服务器上还活着的 `csb.nseq` 回填最大号；资源全删就回填不到、从 0 重数。
- **改名的计数**：每台模板的 alias 就是它的命名空间；`tpl alias A B` 把计数带到 `B`；旧名 `A` 的计数记录（旧键）**只有在旧名前缀还有沙箱/快照时保留**（改回 `A` 才续原号），没有就当场回收（`CSB_AUTO_HW_RECLAIM=0` 可强制永远保留）；commit 模板永远用自己 `…-commit-日期` 的名字起沙箱。
- **alias 与 family 不同**：模板 alias 不是 family（例如 `vd` / family `pi`）时，开沙箱用 alias 命名（`vd_01`）；只有 alias 等于 family 才用 family。
- **快照开沙箱的命名**：`csb start <快照> --label cv_02` 时，`--label` 的前缀就是它的**命名家族**（之后 clone 会接着 `cv_03`、`cv_04` 往下）；不加 `--label` 才沿用来源家族，原血缘记在 `ancestor`。
- **清理死高水位**：`csb tpl clean-hw`（默认 dry-run）列出没有任何东西指到的计数记录；`--yes` 备份 `highwater.json` 后删；`alias_history` 的旧名永远保留。
- **名字优先序**：metadata `name`/`csb.label` → 模板 alias → `<家族>_NN`；有名字的优先沿用，名字不合本地规则或撞名时退回 `<家族>_NN`。
- **有 metadata 名字的不领新号**（`nseq` 留空）；名字形如 `<家族>_NN` 时，该号**计入该家族高水位**（占号），后续自动取号不会撞回同一个；名字不含序号就不占。同一份户籍内序号只增不减（不复用）；能压回只有 `csb label-reset`（破坏性）；`tpl alias` 回收旧键、`tpl clean-hw` 删计数、整份户籍被删，都会让旧号可以再发。
- **重置**（`l` / `label-reset`，确认一次）：该家族服务器上没沙箱、本机没它的快照；有活资源会拒绝。
  TUI 的 `l` 在模板节点上按**家族 alias** 生效（不是模板 id）。
- 默认名：快照 `csb-<源名字>_<日期>`；模板 `<家族>-commit-<日期>`。

### 谁能改名（改名矩阵）

| 对象 | 何时命名 | 规则 | 能改? | 怎么做 |
| --- | --- | --- | --- | --- |
| 模板 alias | 建立时或事后 | `^[a-z0-9][a-z0-9-]{0,63}$`，不能 `tpl-` / `snap-` 开头 | 可以 | 节点按 `a` 或 `csb tpl alias`；撞名拒绝（官方接口会清掉原模板的名字） |
| 模板 id | 建立时 | `tpl-` + 24 位十六进制 | 不可以 | — |
| 沙箱 id | 建立时 | 32 位十六进制 | 不可以 | — |
| 沙箱名字 | 建立时（写 metadata） | csb 只收 `[\w-]{1,64}`（Unicode 也收；emoji / 空格 / `.` 是 csb 挡的）；**本机户籍内同家族唯一**，别的户籍或 WebUI 仍可能同名（用 `#id` 区分） | **不能**（官方无更新接口） | 删除后重建，或从快照重建 |
| 快照名字 | 拍快照时 | 自由文本（建议别 `tpl-` / `snap-` 开头） | 不可以 | — |
| 卷名 | 建立时 | 字母数字 `_` `-`，最长 128（名字即 id） | 不可以 | — |
| 家族序号 | CSB 维护 | 高水位 | 可以（只动本机） | `l` 或 `csb label-reset` |

> [!NOTE]
> **改 alias 会移动树上的东西**：模板改成已存在的家族名，那一族立刻改挂过去（`[D]` 路标、别的机器建的都算），`[E]` 不会。撞名 CSB 先拦（rc=2，动服务器之前）；服务器端没有这道守卫，别的工具直接改会让原模板掉回无名 `[T] tpl-xxxxxxxx`。

### 没有 alias 的模板

- `template commit` 不给 alias ⇒ 匿名模板，显示 `[T] tpl-<id8>`；`csb tpl ls` 的 ALIAS 栏印 `-`，完整 id 在 ID 栏。
- 起名按 `A`（或 `csb tpl alias <id> <名字>`）：名字存在服务器上；撞名拒绝，要抢先用官方 `--clear`。
- 服务器有名字、本机没登记的沙箱显示服务器名；连模板都查不到才进 `[U] no local name yet`。
- CSB 的 `f` 默认 `<家族>-commit-<日期>`，同日再 commit 变 `-2` / `-3`。

## 沙箱生命周期

```text
create ──► running ──pause──► paused ──resume──► running
              │                 │
            kill              kill
              ▼                 ▼
          terminated        terminated
```

**暂停的沙箱只接受**：`ls` / `info` / `snaps` / `logs` / `tree` 只读，`resume`、`kill` 可用（再 `pause` 是 no-op，回 0）；其余回 `rc=3`（消息带原因与修法）。**唯一例外是 `csb net`**：暂停时改网络回 `rc=2`，先印 `net: <name> is <state> - the network only changes while the sandbox is running` + `fix csb resume … --yes, then retry`。

**成功提示**：`start` / `clone` / `commit` / `snap` / `kill` / `rb` 两行
（名字 + 动作 / `id  <完整 id>`）；`resume` / `timeout` / `pause` 一行（`resume --timeout` 多一行 `idle TTL`）。
```text
pi_52  started
id  3ac4e4d59f5b4531b2b6c00da074cc9b
```

CSB 建沙箱默认 `on_timeout=pause`、`timeout` 30 天、**不传** `auto_resume`（平台默认 `false`）：闲置自动暂停；CSB 不传 `auto_resume`（平台默认 `false`），暂停后 CSB 不会自动唤醒，必须 `csb resume`；别的客户端或平台设置可能不同。按 `t` 改闲置时长（秒；`0` = 立刻，`-1` = 永不；暂停时灰键）。

- **保真度**：暂停时 CPU / 内存 / TCP 内部状态保留，对外连线断；恢复后由应用重连（参考 [Sandbox Lifecycle](https://cubesandbox.com/guide/lifecycle)）。
- `timeout` 算闲置时间：SDK 执行操作或 HTTP 直连沙箱才重置；`ls`/`info`/看面板不算。
- 平台默认 `on_timeout=kill`；CSB 默认 `pause`，避免闲置时被平台杀掉。
- 实际时限看 `csb info` 的 `end_at`（永不超时 = 平台不回这个值，CSB 印 `none`）；每次请求刷新。
- 暂停中不倒数；时间以最后一次设定为准。
- `pause` 由平台异步执行，生效前仍看旧期限；`resume` 遇节点没容量回 409，可重试。

## 三种「快照」不是一回事

| 类型 | 谁产生 | 与沙箱 | 在 CSB 里 |
| --- | --- | --- | --- |
| **用户快照** `snap-*` | 你按 `n`；克隆的临时快照也算 | 独立，沙箱删了还在 | `[s]` |
| **暂停快照** | 平台 `pause` 时内部产生 | 同生共死 | 不出现 |
| **模板快照** | 平台建模板 / 分发时内部副本 | 属于模板 | 不出现 |

CSB 的克隆比官方多三件事：副本带 `timeout` / `metadata` / `on_timeout`；临时快照记进户籍（查得到、删得掉）；CSB 不自动回收它。

> 脚本按**名字**删快照：名字唯一时可以删；名字命中多张会 **rc=2 拒绝**，只印第一张完整 id 与
> `(+N more, see csb snaps)`；请改用完整 id（多张可一次给多个 id,CLI 批量）。
> 平台还有活引用（有沙箱 runtime 从这张快照还原）时只**多问一次**，回答 `y` 就删；
> CSB 树上还挂着它（有沙箱以它为模板）时**不带 `--force` 会被拒绝**。

## 本机户籍与多人共用

官方那边沙箱只有 id；名字、家族、血缘、审计都是 CSB 补的，记在 `~/.config/csb/` 下。

> **不建议清除这些文件**：名字与 id 的对应主要记在户籍里，删了旧 id 会变孤儿（`[E]` / `[U]`，快照找不到母体）。真要动先复制一份（`cp <文件> <文件>.bak-<日期>`）。

```text
~/.config/csb/
├── config/                    ← 偏好与开关
│   ├── config.json            ← theme、时区偏移、见过名单、放行网段
│   └── switches.json          ← `csb config set` 写的开关
├── ledger/                    ← 户籍/账本(程序管;手改会坏)
│   ├── sandbox-registry.json  ← 名字 / 家族 / 血缘 / 快照来源
│   ├── highwater.json         ← 家族序号高水位(删了不回收)
│   └── .csb-snapshots.json    ← 本机快照账本
└── log/                       ← 日志
    ├── audit.log              ← 每条命令一行;超过 100 MiB 轮替
    └── tui-error.log          ← TUI 崩溃线索
```

- **审计与账本**：审计超过 `CSB_AUDIT_MAX`（默认 100 MiB）改名归档；账本坏掉先备份再继续，只丢坏行。
- **打开 TUI 就自动收编**：每次启动都跑，只收编户籍里还没有的沙箱（已有记录不重写），只写本机；`CSB_AUTO_NO_ADOPT=1` 可关。取名序与撞名规则见〈命名与血缘〉的「名字优先序」。
- **后悔药**：TUI 右下角提示时按 `U`，只撤这一轮还没定案的收编；正常退出就定案；要改可用 `csb adopt --undo`（含已定案的）或 `csb clean --ledger` 清；手动编辑 JSON 是最后手段。只读命令不建户籍，但每条命令都会写一行审计（`CSB_AUDIT=` 可关）。**下次开启会重新收编**。
- **搬家 / 备份 / 多机连同一集群 = 复制整个 `~/.config/csb/`**（三个数据文件都要带）：
  ```bash
  cp -a ~/.config/csb/ /你的备份位置/csb-$(date +%Y%m%d)/
  ```
  **多人共用**：`CSB_REGISTRY` 指同一路径（如 `/srv/shared/sandbox-registry.json`，同组可写），另外两个文件自动跟着；写入前加文件锁并重读合并。
- **CSB 不会自己删你的东西**：服务器资源只在你说的时候才动（`kill` / `snaprm` / `tpl rm` / `d` 清路标）；本机僵尸行留着等你按 `d`（`CSB_AUTO_HIDE=1` 才安静清，`CSB_AUTO_HIDE_ASK=1` 先问），还有快照指着时保留成 `[D]` 路标。清单不完整时 auto-hide 直接跳过，印 `warning: incomplete list (<原因>) - auto-hide skipped`，不会把活沙箱当 stale。闲置被平台收掉是平台规则。
- **权限**：沙箱里你是 `root`（免 sudo）；本机户籍属于运行 csb 的用户；集群侧看 API key —— 保证「不误删除别人」，不保证「删不掉别人的东西」。

## 按键与操作速查

**开场动画**：启动先播 logo（约 2 秒）；不想看用 `CSB_UI_NO_SPLASH=1 csb`，只关常驻扫光用 `CSB_UI_NO_SWEEP=1`（见[〈环境变量〉](#附录环境变量)）。

键栏固定 **26 个键（13 行 × 2）**；下面是完整速查（含不画在键栏里的：看信息、`Esc`、刷新、方向键与翻页）。有下划线 = 能用，没有 = 灰显。

| 段 | 键 | 说明 |
| --- | --- | --- |
| 导航 | `↑` `↓` move | 移动选中 |
|  | `PgUp` `PgDn` page | 上 / 下 5 个节点（可跨母节点） |
|  | `Home` `End` first/last | 同一层、同类型的第一个 / 最后一个（不跨母节点） |
|  | `F5` `r` refresh | 重新抓取（平时 2 秒自动刷新；CSB_TUI_POLL） |
| 检视 | `Enter` `Space` info | 完整信息弹窗（可滚动；按身份 / 端点 / 运行时 / 资源分段） |
|  | `?` help | help 弹窗（可滚动；完成的面板 `Enter` 也能关） |
|  | `←` `→` fold node | 折叠当前节点；无子节点则折母节点（平移模式：左右滚动） |
|  | `z` fold | 折叠 / 平移模式互切（提示 `→fold` / `→pan`） |
|  | `v` fold all | 折叠 / 展开当前模板下全部 |
|  | `/` filter | 过滤（子串匹配名字 / id / 状态 / 类型 / 家族 / 模板 / 卷名；空串清除） |
| 建立 | `s` start | 开沙箱（模板节点 / 快照节点） |
|  | `f` commit | 把沙箱固化成模板 |
|  | `c` clone | 克隆 |
|  | `B` build | 从容器镜像建模板（问镜像地址与 alias） |
|  | `V` volume | 卷面板（选 / 看信息 / 删 / 新建） |
|  | `T` theme | 切换皮肤（五种循环） |
|  | `a` alias | 改 alias（模板节点） |
|  | `A` adopt | 收编没名字的沙箱或无名模板（无名模板在服务器上起名）；快照不收编；批量：多台无名沙箱 |
| 执行 | `e` exec | 执行一条命令（等价 `csb exec`）；标记 ≥2 台 = 对这 N 台运行同一条命令 |
|  | `i` shell | 交互 shell 选单（最多四条） |
| 快照 | `n` snap | 拍快照 |
|  | `b` rb | rollback，只在快照节点上 |
|  | `o` logs | 看日志（过滤校时噪音） |
|  | `d` clean | 删快照 / 清路标（看节点类型）；**批量：删多张快照** |
| 状态 | `p` pause | 暂停 |
|  | `u` resume | 恢复 |
|  | `t` timeout | 闲置超时（0 = 立刻，-1 = 永不） |
|  | `k` kill | 删除沙箱 / 删模板（看节点类型）；**批量：删除多台沙箱** |
|  | `l` label-reset | label-reset（模板节点） |
| 批量 | `m` mark | 标记当前（设锚点）；`Esc` 清光（标记 ≥2 时非批量键会被拒：`<动作>: no bulk (Esc clears the marks)`）；**筛选开着时 `Esc` 先清筛选，标记留到下一次**；**批量执行中按 `Esc` = 整批停止（剩下的不跑），只汇总一次** |
|  | `M` range | 标记范围（再按 = 反选） |
| 弹窗 | `↑` `↓` scroll / `PgUp` `PgDn` page | 滚动 / 翻页（超一页时左下角显示当前页 / 总页数） |
|  | `Esc` close | 关闭弹窗（随时可关；完成的面板 `Enter` 也能关） |
|  | 鼠标 mouse | 点节点 / 点键栏 / 滚轮 |
| 面板 | `q` quit | 离开 |

**表里放不完的两件事：**

- `i` **shell** 选单**最多四条，视环境增减**：
  ① **复制** `csb shell <id>` 到剪贴板（没有剪贴板工具时只显示命令）；
  ② **tmux / screen**：另开一扇窗，窗名是沙箱的名字（带 `CUBE_API_URL` / `CUBE_API_KEY` / `CSB_REGISTRY`）；这一条只在 TUI 本身跑在 tmux/screen 里时出现（`$TMUX`/`$STY`），纯终端没有这一行、footer 会提示先进入 multiplexer;
  ③ **Herdr 分页**：`HERDR_ENV=1` + `herdr` 在 `PATH` + `herdr status` 回 0 ⇒ 才出现；
  ④ **只显示命令、自己手抄**。沙箱里 `exit` 回来。
- **鼠标**：点节点 = 移光标；点按键栏 = 按那个键（破坏性键仍会确认）；滚轮 = 卷动 / 移光标 3 个节点。
  **面板与输入框里点击不生效**，滚轮仍可卷动；主力 ↑↓ + `Enter` + `Esc`。

> [!NOTE]
> `B` build、`V` volume、`T` theme、`?` help、`q` quit、`z` fold、`v` fold all、`/` filter 在任何节点都能用。
> 输入框与弹窗里 `Esc` 只取消 / 关闭；离开请在树上按 `q`。
> **窗口太窄**（例如 80x24）左栏按键列表放不下时，最后一行只写 `? help` —— 按 `?` 看完整表，不会静默藏掉按键。

### 笔记本用户的按键换算

| Fn 组合 | 等效按键 |
| --- | --- |
| `Fn` + `←` | `Home` |
| `Fn` + `→` | `End` |
| `Fn` + `↑` | `Page Up` |
| `Fn` + `↓` | `Page Down` |

## 出网（代理）

建沙箱时一次决定，建好可以用 `csb net` 改（整组替换）。

| `--net` | 还要给什么 | 效果 |
| --- | --- | --- |
| `off` | 都不用给 | 全断 |
| `on` | `--allow-out` 或 `--proxy`，至少一个 | 默认全开；清单 = 只放这些（其余封锁）；代理 = 出网走代理 |
| 不写 | — | 继承模板政策（模板无 policy 时 = 平台默认）；要断网请明写 `off` |

- 明写 `--net on` 却两个都没给 → 报错（rc=2），不建沙箱。

- `--allow-out`：给清单 = **只放这些网段或域名**（`example.com` / `*.example.com`；域名需 DNS;csb 同时送 `deny_out 0.0.0.0/0`）。
  白名单默认自动放行 DNS:csb 建好后读沙箱的 `/etc/resolv.conf`，把 resolver 加进清单（读不到用 `--dns-server <ip>`）；要严格只准 IP 才用 `--no-dns`。`all` = 全部放行，但三种命令送法不同：`csb net` 送空清单、`csb tpl build` 不写 policy、`csb start` 送 `allow_out ["0.0.0.0/0"]` + `deny_out []`。
- 模板可烧网络：`tpl build --allow-out <cidr> --deny-out <cidr> --no-internet`（不收域名；`--allow-out all` = 不写入 policy，继承时按平台默认全开；模板没有 DNS 参数）。`start` **完全不给网络旗标 = 继承模板**；要全开就给 `--allow-out all`。CLI 没有记忆模式（手动）；记忆只在 TUI 的 allow-out 页两列 `(review last egress profile)` / `(use template network policy)`。
- 只给代理、没给清单 = 代理主机/32 + `0.0.0.0/0` + DNS。

### 建后改网络 `csb net`

`csb net <id> --allow-out <cidr|domain>[,...]` = 白名单；`--allow-out all` = 全开；`--net off` = 全断。平台是**整组替换**，csb 一次补齐：白名单送 allow + deny `0.0.0.0/0` + `allow_internet_access=true`，并补沙箱的 resolver（读 `/etc/resolv.conf`，读不到用 `--dns-server`）；`all` 送空清单 = 平台全开；`off` 送 `allow_internet_access=false`。`--dry-run` 先印后停；`-o json` 回 `sandbox_id`/`allow_out`/`deny_out`/`allow_internet_access`/`dns`；非 tty 要 `--yes`。沙箱要在 running（暂停先 `csb resume`）。本机户籍的 NETWORK 段多一行 `set by csb at <时间>`，别的机器看不到（平台 `get_info` 没有 network 栏位，多端同步不可行）。域名建后可行：按主机名放行，IP 直连挡。

`--proxy` 只把代理网址注入代理 env:`HTTP_PROXY` / `HTTPS_PROXY` / `http_proxy` / `https_proxy`（外加 `NO_PROXY` / `no_proxy` 白名单），不是 `csb url`；沙箱网络本身不改（要改网段用 `--allow-out` 或 `csb net`）。白名单 DNS 一律自动放行（TUI 没有 DNS 页；CLI 只有 `--no-dns` 会封）；resolver 不写死，`--dns-server` 可覆写。

TUI 的 `s` 三页：`network` → `allow out` → `proxy`（`off` 跳两页）。两页按键写在标题（`Enter=choose   d=delete   Esc=back`），并记住上次选择。

- `allow out` 顶部 `(review last egress profile)` 是细节框（清单与代理），Enter 套用并跳过 proxy;
- 模板有政策时多 `(use template network policy)`，显示 internet／allow_out／deny_out／dns／proxy 五面，Enter 套用；
- `Esc` 返回。

代理优先序：`--proxy` > `HTTPS_PROXY`/`HTTP_PROXY` > 上次记下的 `proxy_url`；都没给就直连；`CSB_AUTO_PROXY=0` 只关注入。换代理：同 IP 换端口可以，换 IP 要重开。看沙箱现状用 `csb info <id>` 的 NETWORK 段；看**模板政策**用 `csb tpl info <alias>` 的 NETWORK 段。

## 命令行参考

> [!IMPORTANT]
> **接口约定**：`-o json` 输出结构化数据；退出码 **`0` 成功 / `1` 取消 / `2` 用法错误 / `3` 运行期或远端失败**（`4` 只在界面；被信号打断是 `128+N`，见〈退出码〉）。
> 名字打错一律 **2** 退出：多数命令印 `no sandbox: X` + `fix csb ls lists them; full ids: csb ls -o json`；`kill` 印 `unknown sandbox: X (see csb ls; full ids: …)`。
> 打到快照 / 模板时，**只有 `csb info`** 会多给 `(that is a snapshot - …)` / `(that is a template - …)`。
> 沙箱目标只吃完整 id，见〈目标怎么写〉；`kill` 找不到也回 **2**，印 `unknown sandbox: ...`。
> `-o json` 不代表同意：非交互仍要 `--yes`（没给就 rc=2）。

**每个命令只给一种输出形状**：顶层是户籍身份列（`sandbox_id` / `label` / `state` / …），服务器原样对象在 `info` 下；`info -o json` 暂停时只回身份列（不查 runtime）。

`-o json` 只对会打印 JSON 的命令有效：`shell`、`vol mount` 在送出请求前就以 **2** 退出并给替代做法；`help` / `watch` / `admin` 本来就会拒绝。`csb version -o json`（与 `csb --version -o json`）回 `{"version":"0.1.0"}`，rc=0。
```bash
csb --version  # csb 0.1.0
csb help       # 命令行用法;界面里按 ? 是键位表(两份刻意分开)
```

### 谁有谁没有

- **只有命令行有**：`cp` `ls-file` `mk` `mv` `rm`、`url` `watch`、`info -o json`、`tz` `int`、`admin -- <cubemastercli 命令>`、只打印提示的 `vol mount`（一次多张 `snaprm` 也一样）。
- **控制台独有**：皮肤（`T`）、折叠与平移（`z` / `v` / `←` `→`）、标记批量（`m` / `M`）、过滤（`/`）、两秒刷新、开场动画。

### 目标怎么写（名字还是 id）

- **沙箱目标只接受 id**：完整 id 或**至少 24 位**前缀；打名字**当场拒绝**（`rc=2`），并印出该用的完整 id。
- **例外**：`kill <名字>` 可清「服务器已无、本机户籍还在」的残行；`rb` 单参数可吃唯一快照名。
- **仍用名字的 4 处**：模板 alias、`label-reset <家族>`、卷名（即 id）、快照名（`csb start`）；名字本身只用在显示与快照自动命名。
- 下文示例的 `a1` / `a2`、附录的 `zoo-01` 只是示意名，实际请填完整 id（或至少 24 位前缀）。

### 沙箱与快照

```bash
csb ls [-o json]                                    # 列沙箱；模板栏为空时表尾多一行 note
csb start <模板|模板id|alias|快照id|快照名> [--label <名>] [--n N] [--concurrency N]
          [--timeout S] [--on-timeout kill|pause] [--net on|off]
          [--allow-out <值>] [--proxy URL] [--vol 路径:卷]
          [--family <根 alias>] [--allow-dns]
          [--env K=V] [--async] [--no-net]
```

- `--family`：快照开沙箱指定命名家族的唯一入口（clone 会接着编号）；快照没家族、也没给 `--label` 时 rc=3，错误信息会叫你补。
- `--allow-dns`：白名单 DNS 已默认自动放行；显式写会印一行提醒；要严格只准 IP 用 `--no-dns`。
- `vol create --driver <名字>`：官方 SDK 的 driver，不写用平台默认。

```bash
--vol 只挂已存在的卷;只读在卷名后加 ro(/data:ztvolro),不是加 `-ro`、也不写第三段 `:ro`。
--net on 会开外网,必须同时给 --allow-out <cidr|domain>[, ...] 或 --proxy <url>,至少一个(例如 --allow-out all);两个都没给直接 rc=2,不建沙箱。
csb start <模板|alias> --n 台数 [--concurrency M] [--label <基准名>]  # 给了基准名就是 <名>_01 … <名>_0N
csb clone <id> [--n 台数] [--concurrency M]                           # 自拍临时快照给副本共用，不自动回收
csb snap <id> [快照名]                                                # 挂了卷也放行；快照不含卷数据
csb snaps [-o json]                                                   # snap ls 等价（列出快照）
csb snaprm <快照id|名字> [--yes] [--force]                            # 确认前印完整 id/名称;运行时引用只多问一次;树上的名字要 --force 才删
csb tpl rm <alias|id> [--yes] [--force]                               # 确认前印完整 id/alias;有 snapshot descendant 时 --force 才删
csb rb <id> <快照id>                                                  # 回滚（身份不变、快照保留、必须 running）；单参数可吃快照名,两参数第二个要完整 id
csb pause|resume|kill <id...>                                         # 支持多 id
csb timeout <id...> <秒数>
csb info <id>                                                         # 含 runtime_snapshot 与 allow_out（新沙箱会拿到的值）
csb exec <id...> [--env K=V] -- <命令>                                # 多 id 依次跑；批量失败 rc=1，单台失败 rc=3
                                                                      # 出网代理 env 由 csb 自动带上(CSB_AUTO_PROXY=0 关)
csb tree [-o json]
csb clean <id|快照id>                                                 # 清路标；非 TTY 要 --yes
csb clean --ledger [--yes]                                            # 清沙箱记录(entries/noauto;先备份、二次确认;--force 不适用),
                                                                      # 保留 family_highwater / templates
csb clean --ledger --hard [--yes]                                     # 连快照账本 / 高水位 / 模板一起清(先备份三份;--force 不适用)
csb prune [--entries] [--policies] [--dry-run] [--yes]                # 只清死数据(不在完整集群清单里的 entry / sbx 政策);写入前备份;--force 不适用
```

`--net` 只管出网：`on` / `off`（全断）。**写 `--net on` 时必须同时给
`--allow-out <cidr[,cidr]>` 或 `--proxy <url>`，少了会直接报错。
TUI 会记住上次的清单与代理，CLI 不记；不写 `--net` = 继承模板政策。
代理地址的来源与优先序见〈出网（代理）〉；都没给就不用代理（直连）。
`--vol` 与 `--meta` 都可重复；**`--vol` 是 CSB 命令行唯一能「建沙箱时挂卷」的入口**（`vol mount` 会 rc=2；平台/WebUI 另说；挂上卸不掉；**从快照开沙箱不要再给 `--vol`** —— 快照已带着当时的挂载，CSB 本地会在送出前挡下，给不同卷平台会静默忽略）。

### 进沙箱、看日志

```bash
csb exec <id> -- <命令>                   # 远端非 0 ⇒ csb 以 3 退出
csb exec <id> -- sh -c '...'              # 嵌套引号自己包 sh -c
csb exec <id> --env FOO=1 -- env          # 只给这一条命令带环境变量(可重复)
csb exec a b c --env HTTPS_PROXY=http://<proxy-host>:<port> -- curl -m5 https://www.google.com
                                          # 多台一起带同一组 env(批量出网用这个)
csb shell <id> [-- <命令>]                # 需要真终端；非交互用 exec
csb int <id> [-- <关键字>] [--sig KILL]   # 不带关键字只列候选
csb logs <id> [行数]                      # 平台日志；时钟噪音默认滤掉
csb url <id> [端口]                       # 默认 49983
csb ls-file <id>:/data                    # 列目录（等价 csb ls <id>:/data）
csb cp <id>:/data/a.txt ./a.txt           # 拉单个文件
csb cp <id>:/data/dir ./                  # 目录；只在真的会覆盖时问一次
csb cp ./x <id>:/data/                    # 上传；port 不通且大档（≥8 MiB）会先问 Y/N
csb cp <id>:/data/big.bin ./              # 大档下载：port 不通会先问 Y/N，N 不复制
csb cp <id>:/root/big.bin ./              # ≥8 MiB 自动走沙箱公开端口
csb cp <id>:/root/big.bin ./ --via files  # 强制官方通道
csb mk <id>:/work/logs
csb mv <id>:/a <id>:/b                    # 同一台内；两边都要写全 <id>:
csb rm <id>:/a                            # 非交互要 --yes；路径本来不存在仍 rc=0
csb watch <id>:/work                      # 只看一层；流，没有 -o json
```

`exec` 后面整串是**一条**命令，交给沙箱的 shell（参数拼成一行）；管道 / 重定向 / 嵌套引号自己包 `sh -c '…'`。

**exec 输出上限**：CSB 在沙箱内先量大小，≤64 MiB 直接回；>64 MiB 回 `CSB_OUT_TOO_BIG`（rc=2），请改用 `--out`。

`exec` 的 `--out /tmp/out` 把输出写进沙箱文件，不受 64 MiB 打印上限影响；再用 `csb cp <id>:/tmp/out ./` 取回。

上传遇到 413 或磁盘满时，CSB 会先问 Y/N；仍失败则印「does not fit in the sandbox disk」，不会只丢原始 413。

| 命令 | 运行的是什么 | 什么时候用 |
| --- | --- | --- |
| `csb exec` | 一条 shell 命令，回 stdout / stderr 与退出码 | 装包、看目录、运行脚本 |
| `csb shell` | 交互式终端（PTY），`exit` 回树 | 连续交互、REPL、vim（`i` 键就是它） |
| `csb int` | 列出沙箱里的进程；给关键字才发信号（默认 SIGTERM） | 进程失控、Ctrl-C 无法中断 |
| `csb logs` | 平台运行日志（本地时间戳，校时噪声默认滤掉，`--all` 取消） | 排查沙箱为什么起不来 |

### exec / cp / shell 的原理与对策

大文件走 envd 会把整包留在内存，所以下面各有退路与代价。

- **exec**：输出 ≤64 MiB 直接印；超过就 `--out /tmp/out` 写档再 `csb cp` 取回（串流回复同样留在内存）。代价：多一步 cp 与一份沙箱内暂存。
- **cp**：小档（<8 MiB）直接走 envd 串流；≥8 MiB 先试沙箱公开 port（要 python3、直接、首选），port 不通才降回 envd（整包留在内存，大档可能 OOM）；上传 >16 MiB 再切 16 MiB 分片（可能撞 413，沙箱磁盘要放两份）。代价依序是：兼容性、内存、磁盘。
- **shell**：累计输出超过 64 MiB（`CSB_SHELL_MAX`）只印一次警告、不中断。代价：大量输出时终端会变慢。

### 模板、卷与收编

```bash
csb commit <id> [--alias 名字]                            # 一次只提交一台(没有批量形式);
                                                          # 给了两个名字会直接 rc=2 拒绝
csb tpl ls|info|alias|rm                                  # rm 先扫全服务器血缘;有快照还依赖它会被 CSB 拒绝,
                                                          # --force 只绕过 CSB 这一关;平台仍会挡"还有活沙箱用它"
                                                          # (still in use,先 kill 那台);沙箱的模板若早已被删、
                                                          # 血缘断了,平台可能不再把它算在这颗模板下而放行
csb tpl build --image <镜像> --alias <名字> [--disk 1G] [--mem 500M] [--cpu 1000] [--allow-out <cidr[,cidr]|all>]
csb vol ls|create|mount|rm                                # mount 不动作:印警告后 rc=2;卷只能在建沙箱时挂
                                                          # create 印结果 + 短说明（--quiet 只留结果）；完整说明见 `csb help vol`（TUI: V 开卷页、? 看说明）
csb adopt <id> [--as 名字] [--family 家族]                # 把在别处建的沙箱收进树里
csb adopt --all                                           # 一次收编所有还没有名字的沙箱
csb adopt --undo                                          # 撤销所有自动收编写下的记录(含已定案的;手动收编的不动)
                                                          # TUI 的 U 只撤这一轮还没定案的那些;下次启动会再收编
                                                          # **直接执行,不另问**——先看会删什么用 `--dry-run`(删的是户籍记录,服务器上的沙箱不动)
csb label-reset <家族> [--start N] [--yes]                # 重置家族的编号基准(确认一次;**CLI 与 TUI 都能用**:模板节点上的 `l` 键,或这条命令);
                                                          # 家族还有活着的沙箱、或本机还有它的快照,会拒绝;
                                                          # 非 tty(脚本 / 管道)要加 `--yes`,否则会问而读不到答案
csb start <快照id> --label <家族>_<NN>                    # 从快照直接开沙箱(挂在快照下),再 commit 成模板
csb snap <id> <名字>                                      # 名字被占用会拒绝(名字永久；同名多张时按名字的指令 rc=2，csb 不替你猜)
csb admin -- cubemastercli <官方子命令+参数>              # 透传给官方 CLI(程序名要单独给)
csb tz [-o json]                                          # 本机时区 / 与服务器的钟差 / 时间戳怎么读
csb tpl doctor [--probe <alias>] [--fix] [--node <node>]  # 开机后体检:模板还能不能用 / 沙箱与户籍几笔;
                                                          # 默认只读;**点名** --probe <alias> 才试开一次再杀
                                                          # 坏成 130483 时,`--probe <alias> --fix` 只重做点名的那台(会问一次),成功后会自动再试开一次确认;redo 报 source_image_ref 时加 `--node <node-ip>`
```

> 模板的 CPU / 内存 / 可写层大小**建的时候一次定死**（`--disk` / `--mem` / `--cpu`）；`redo` 只是重执行一次构建，想改规格只能拿来源镜像重新 `csb tpl build`。
>
> **单位**：`--disk` 收 `1G` / `500M`（1G = 1024M）；`--mem` 收 `500M` / `1G`。
> `--cpu` 收 millicore（`2000` = 2 核）；`--mem` / `--cpu` 配对，只给一个时另一个补默认（1000 millicore / 1024 MiB）；用错值在发出请求前就被拒（rc=2）；`--cpu 0` / `--mem 0`（含负数）当场 rc=2、一个请求都不发。
>
> **`csb tpl info` 的 NETWORK 段**：除 id／alias／status／ts 外固定五面：
>
> - `internet`：模板没写 = 平台默认 on
> - `allow_out`：`all` = 不写政策
> - `deny_out`
> - `dns`：模板没有 DNS 参数，开沙箱时由 `start --dns-server` 决定
> - `proxy`：模板没有 proxy 栏位，exec／shell 才注入
>
> `-o json` 多一个 `network` 物件（无政策时 `null`），其余栏位不变。

### 批量与并发

`-o json` **不能配批量**：多个名字**当场拒绝**（rc=**2**，提示 `bulk over N labels is text-only (-o json is per sandbox; run labels one by one)`）。要 json 就一个一个运行。

```bash
csb pause a1 a2 a3
csb pause --all         # 所有 running 一起暂停(要关机的时候最省事;
                        # 会先列出整个集群的名单;非 tty 没 --yes 挡下来;
                        # --list / --dry-run 只预览,一个都不写)
csb timeout a1 a2 3600  # 最后一个参数是秒数(0 = 立即,-1 = 永不过期)
csb kill a1 a2 --yes
```

一次开多台（或克隆多份）用 `--n` 配 `--concurrency`：`csb start senpi --n 8 --concurrency 4` = 开 8 台、最多 4 台同时运行，只在 `start` / `clone` 有效，`--concurrency` 必须 ≥ 1。`--n` 收 1..20 台，>20 在 tty 再问一次（`[y/N]`），非 tty 要 `--yes`。
命令行能一次收多个**完整 id**（或至少 24 位前缀）的只有七个：`kill` / `pause` / `resume` / `timeout` / `clone` / `snaprm` / `exec`；名字只给 `start` 与 `--label`。

## 退出码、全局旗标与信号

### 退出码

| 码 | 意思 |
| --- | --- |
| `0` | 成功 |
| `1` | 取消（`Esc` / `Ctrl-C` 停止这次等待；批量中途取消也回 1）；**`exec` 批量部分失败也回 1**；其余批量子命令失败回 `3`、用法错误回 `2` |
| `2` | 用法错误 |
| `3` | 运行期或远端失败 |
| `4` | **只在界面里**：终端消失，线索在 `~/.config/csb/log/tui-error.log` |
| `128+N` | **被信号打断**（N = 信号编号，例：`143` = `SIGTERM`、`129` = `SIGHUP`、`131` = `SIGQUIT`）：csb 先还原终端设置再退出；`Ctrl-C` 是 `1`（取消），不是 128+N |

### 全局旗标

**旗标写在子命令后面**：`csb kill x --yes` 可以，`csb --yes kill x` 不行（`no such command: --yes`）。`-h` / `--h` / `--help` 放哪里都印用法（位置参数后也印，不会执行命令）；`csb help [topic]` 才是手册；`csb --version` 可以打在开头。

| 区段 | 旗标 | 作用 |
| --- | --- | --- |
| 输出 | `-o json` | 输出结构化 JSON（给脚本 / agent）；**不等于同意**，破坏性命令仍要 `--yes` |
| 确认与预演 | `--yes` | 跳过确认（破坏性命令） |
|  | `--dry-run` | 只打印「本来会做什么」就停在 `0`：**不改名、不写本机文件**（仍会读平台：查沙箱、查目标存不存在）。 |
|  | `--probe` | 只给 `tpl doctor`：点名一台模板 `--probe <alias>`，才真的试开一次再杀掉；不加就只读。非 tty 还要 `--yes` |
|  | `--node` | 只给 `tpl doctor --fix`：指定重做落在哪个节点；模板没有 `source_image_ref` 时用（错误会提示） |
|  | `--list` | 批量命令（`kill` / `pause` / `resume` / `timeout` / `clone` / `snaprm`）只打印「本来会做什么」、什么都不动；`int --list` = 列进程、`snap --list` = 预览单张（各自语义，不是全域） |
|  | `-h` / `--h` / `--help` | 印用法后结束；放哪里都有效（`csb kill <id> --h` 也印，不会执行命令）。手册与主题用 `csb help [topic]` |
| 范围 | `--all` | 全都要：`adopt` 全部收编、`pause` 全部暂停、`logs` 不滤噪音、`cp` 连跳过的文件一起拷 |
|  | `--undo` | 撤销所有自动收编写下的记录，含已定案的（`adopt --undo`；TUI 的 `U` 只撤这一轮） |
|  | `--ledger` | 清**沙箱记录**（`clean --ledger`；细节见命令区）；加 `--hard` 连快照账本/高水位/模板一起清 |
|  | `--force` | 跨依赖/强制模式（`tpl rm` / `snaprm`）；**不是确认**，非 tty 仍要 `--yes`。`csb int` 要动平台自带服务（envd / jupyter）也得加它 —— 动过就只能删掉重建。平台端的保护它挡不了 |
| 除错 | `--debug` | 在 stderr 印一行诊断（版本、命令、户籍路径） |
| 时序与通道 | `--async` | `start` / `clone` 不等就绪直接返回；两者在 `--async` 时完成行都说 `requested (--async, not waited)`，不说 `started` / `cloned` —— 没查证过状态；不是 `--async` 时才照字面说 `started` / `cloned` |
|  | `--via` | 只给 `cp`：`http` **先**走沙箱公开端口，失败会印 `note: port failed (…)` 并自动降回 envd（大文件会先问 Y/N）；`files` 才是不试端口、强制走官方通道（envd 串流 / >16 MiB 分片） |
|  | `--quiet` | 只关闭 `vol create` 的 3 行短说明；`vol mount` 与带 `--vol` 的 `start` 都仍印完整 16 行卷说明 |
| 网络 | `--no-net` | 新沙箱不联网，`allow_internet_access=False`（`start` 专用） |

**「先印后停」与「问不问」是两件事**：非交互下破坏性命令要 `--yes`；`--dry-run` 只打印，優先於確認。`vol create` / `timeout` / `clone` / `snap` / `commit` 本来就不问；`pause` / `resume` 非交互直接做；带 `--vol` 的 `start` 也不问（TUI 会自动带 `--yes`）。
**`--allow-out all`**：把本机记录的那组**清空**（`config.json` 的 `allow_out` = `[]`），但**保留「最近用过」清单**（`allow_out_hist`，TUI 那一题仍会显示）；完全不写 `--allow-out` = 不覆盖模板政策（继承）；CLI 不记住上次给过的清单。

## 疑难排解

### 出问题先看这里

| 区段 | 症状 | 大概率是 | 怎么办 |
| --- | --- | --- | --- |
| 资源与清理 | 会不会自动删除我的资源？ | 本机条目默认保留；服务器资源不会自动删除 | 服务器只在你执行 `kill` / `snaprm` / `tpl rm` / `d` 时才变动；本机失效记录保留到你按 `d`，`CSB_AUTO_HIDE=1` 才会自动清除 |
|  | 我的数据存在哪、怎么备份? | `~/.config/csb/` | 复制整个目录 |
| 名字与 id | `kill` 提示 `unknown sandbox: …`（rc=2） | 目标打错，或只给了 8 位短 id | 活沙箱只吃完整 id 或至少 24 位前缀；打名字会 rc=2 并给出完整 id；本机户籍里的名字只能清已不在服务器的残行（`kill`）；先 `csb ls` 对一下 |
| 快照 | `snaprm refused: … has N live ref(s)` | 有沙箱 runtime 从这张快照还原；平台允许删，只是多问一次 | `--force` 或先 `kill`；`--force` 的定义见〈全局旗标〉 |
|  | `snaprm refused: … is referenced` | CSB 树上还挂着它 | `csb kill <id> --yes`，或 `csb snaprm <快照> --force`；只清节点用 `d`；TUI 的 `d` 会再问一次，答 y 才带 `--force` |
| 卷 | `vol rm refused: <卷> mounted by N sandbox`（复数时尾缀 sandboxes） | 还有运行中的沙箱挂着它（CSB 本地先挡，平台端 `130409`）；卷删除**不可逆** | 先 `csb kill <id> --yes`，再 `csb vol rm <卷> --yes` |
|  | `unknown volume: <名字> (see csb vol ls)` | 名字打错或卷已删 | `csb vol ls` 对一下；卷名就是卷 id |
| 网络与代理 | `csb url` / 沙箱服务打不通，或 SDK 写入失败 | 没有泛域名 DNS 时少了 `CUBE_PROXY_NODE_IP` | 设成 CubeProxy 节点的 IP；服务要绑 `0.0.0.0` |
|  | **想让沙箱走本机代理出网** | `--allow-out` 是**白名单**：命中才放行，清单外的公网与私网都挡（csb 送 `deny_out 0.0.0.0/0`，清单外 `curl` 回 000）。只给代理、没给清单是另一种情形：代理主机 `/32` + `0.0.0.0/0` + DNS（见〈出网（代理）〉）。要全断用 `--no-net`。 | **`csb start` 一步到位**：建沙箱时把宿主代理地址并进沙箱的 `allow_out`（连同 `0.0.0.0/0`、`CSB_INTERNAL_CIDR` 里的网段），用 `Sandbox.create(network=…)` 一次带上。代理 env 不写进沙箱，由 `csb exec` / `csb shell` 逐条自动注入（`CSB_AUTO_PROXY=0` 全关）。验证：`csb exec <id> -- curl -m10 https://www.google.com` 应回 302（或 200）。建好后换网段用 `csb net <id> --allow-out …`，不用重开。 |
|  | resume 后印 `resume did not stick`，或错误里带 `130497` | 平台接受 resume 后又回滚：guest agent（`envd`）起不来，沙箱保持 paused | 先重试一次；一直失败就 `csb start <模板>` 开新的，再用 `csb cp` 把文件搬过去（旧的 paused 沙箱在你 `csb kill` 前数据都还在） |
| 模板与镜像 | 私有 registry 时 `tpl build` 回 `server gave HTTP response to HTTPS client` | 少了 `http://` 前缀（没前缀默认走 HTTPS） | 映像写 `http://registry.example.com:5000/ns/app:tag` |
|  | `tpl build` 一直逾时 | 平台建置卡住（映像/探针/分发） | `csb tpl doctor --probe <alias>`；看官方 `cubemastercli tpl status --job-id <id>` |
|  | 重开机后**模板不能用** | 节点本地模板没了 | `csb tpl doctor --probe <alias> --fix`（先点名一台；报 `source_image_ref` 时加 `--node <node-ip>`）；仍不行用官方 `template redo` 重建 |
| 平台生命周期 | 删**暂停中**的沙箱先回 `503` + `Retry-After: 2` | 正在进入 paused，或别的 lifecycle 占着锁 | 等 **2 秒**再试 |
|  | `410 Gone` | 沙箱**已被平台回收**（闲置超时） | `csb ls` 对一下，原位会留 `[D]` 路标 |
| 界面与终端 | 界面无响应了? | 看计时器还在不在走 | 面板 `running... 12s`、命令行 `waited Ns`；`Ctrl-C` / `Esc` 只停这次等待。终端里等待结束时**会留一行 `done in Ns`** |
|  | 被信号打断会不会破坏终端设置？ | 不会 | csb 先还原终端再退出（退出码 128 + 信号）；服务器上的操作不受影响 |
|  | 按了 `i` 选「复制」但剪贴板里没有 | 终端屏蔽了 OSC 52（iTerm2 默认） | tmux 里可用 `prefix + ]` 从 buffer 贴回（取决于 tmux 与终端设置）；CSB 也会把命令印在面板上 |
|  | 另开的 tmux 窗口一闪就没了 | 命令立刻失败了 | **故意**：窗口停在 `[csb] the shell exited with N` 等你按 Enter |
|  | Herdr 上 agent 一直 idle | Herdr 用该 agent 的**画面规则**判状态 | agent 真在运行就会变 `working`；`pi` 没登录 provider 时 idle 是实话 |
| 户籍与环境 | 清空户籍后，旧沙箱变 `[E]` / `[U]`、快照找不到母体 | 本机户籍负责名字 ↔ id；沙箱**建立时**也会把 `csb.label` 写进平台 metadata（平台看得到），但 `csb adopt` 无法回写，所以别的机器收编的只能留在本地 | **别在有用的户籍上清空**。要清只能走 `csb clean --ledger`（先备份、问两次，保留高水位与模板），细节见[〈本机户籍与多人共用〉](#本机户籍与多人共用) |
|  | `csb logs` 无法获取日志 | 平台日志不在这里 | 用官方 `cubemastercli` 或节点日志（路径问运维） |
### 平台行为与限制

**平台行为：**

- 宿主重启：running 会删、paused 保留（`csb resume` 救不回被删的）。要关机先 `csb pause --all`：它会先列出整个集群的 running（不只看你的户籍，共用集群会暂停到别人的）；想先看名单用 `csb pause --all --list`。开机再 `csb resume`。
- 删沙箱不连带删快照；沙箱名字/家族建完就定（只能删除重建）；能改名的只有模板 alias。
- 官方 WebUI / SDK 开出来的沙箱没有 CSB 的名字（名字在 metadata）；CSB 收编时按 metadata / 模板 alias 取名。沙箱里是 root，装包不用 sudo。

卷与快照的四种动作（卷里的数据**永不进快照**）：

| 动作 | 卷里的数据 | 新沙箱接回哪一份卷 | 谁会活过来 |
| --- | --- | --- | --- |
| `csb snap <id>`（挂载了卷） | **不进快照** | — | — |
| `csb start <快照id>` | 不还原 | **同一个活动卷**（不复制） | 该快照当时在写卷的进程 |
| `csb clone <id>` | 不复制 | **同一个活动卷** | 同上 |
| `csb rb <id> <快照id>` | 不还原 | **同一个活动卷** | 同上 |

- **两个写入进程共用同一个卷会真的写坏文件**：先停写入，或 `csb cp <id>:/data/目录 ./` 拷出来。
- 入站只到得了绑 `0.0.0.0` 的服务；只听 `127.0.0.1` 会 502；写地址时不要补 `:端口`。

## 设定存在哪

- `config/config.json` 是偏好（出网、主题、时区、`vol_last` 等），完整键用 `csb config list` 看。
- `config/switches.json` 是开关（`csb config list` 可看）；`ledger/`、`log/` 是户籍与日志。
- `vol_last` 是 TUI 上次挂载的卷与路径，下次开沙箱做成 `(same as last time: …)`。

## 附录：环境变量

**开关取值顺序**：内置默认 < `switches.json` < 环境变量。
开关名形如 `CSB_<名>`（如 `CSB_WAIT`）；平台或终端自己的变量（`CUBE_API_URL`、`TERM` 等）由外部提供，CSB 只读。
用 `csb config list / set / get / unset / where / path` 管理；坏值当场 `rc=2`，不写进文件。

| 区段 | 变量 | 作用 |
| --- | --- | --- |
| 等待与超时 | `CSB_WAIT` | 阻塞等待上限（默认 240,20–3600）；Esc 只停止等待。连线上限另见 `CSB_CONNECT_WAIT` |
|  | `CSB_CONNECT_WAIT` | 连线 / 握手上限（默认 30,5–300）；连不上就等这么久，不会无限挂住 |
|  | `CSB_HTTP_WAIT` | 只读 HTTP 上限（默认 30,10–120） |
|  | `CSB_STOP_WAIT` | 单笔命令的上限秒数（默认 120，夹 10–3600）；`snap` / `rb` / `kill` / `info` / `cp` / `vol` / `tree` |
|  | `CSB_EXEC_WAIT` | `csb exec` 的等待上限（**默认 600 秒 = 10 分钟**，夹在 10–3600）。超过就回 `rc=3`；要继续等就调大（见「超时」段） |
|  | `CSB_SHELL_MAX` | `csb shell` 累计输出超过此值只打印一次警告，不中断（默认 64 MiB；可写 `1M` / `1G`） |
|  | `CSB_FETCH_WAIT` | 界面每次抓数据的上限秒数（默认 5，夹在 0.5–3600） |
|  | `CSB_FETCH_GIVEUP` | 面板放弃一次抓取、改起新工作的秒数（默认 60） |
| 户籍与日志 | `CSB_REGISTRY` | 户籍文件路径（默认 `~/.config/csb/ledger/sandbox-registry.json`；布局见〈本机户籍与多人共用〉）；同目录放快照账本与 `highwater.json` |
|  | `CSB_AUDIT` | 审计日志路径；设成空字符串就完全不记 |
|  | `CSB_AUDIT_MAX` | 审计日志轮替上限（默认 **100 MiB**）；超过保存为 `<log>.bak.N`，不覆盖不删除 |
| 显示与主题 | `CSB_UI_COLOR` | 手动指定颜色深度：`auto` / `8` / `16` / `256` / `24`（`24` = 真彩） |
|  | `CSB_UI_BOX` | 设成 `ascii` 就用 ASCII 画框（不是 UTF-8 的终端、或想截图时用） |
|  | `CSB_UI_PANEL_BG` | 设成 `0` 就用终端自己的底色，不画面板底 |
|  | `CSB_DEV_PANEL` | 不用手设：TUI 在 `i` 面板开 shell 时自动带上 |
|  | `CSB_DEV_BOOT_MSG` | 开场显示一行你自己的话（例如登录说明） |
|  | `CSB_UI_NO_SPLASH` | 跳过开场动画 |
|  | `CSB_UI_NO_SWEEP` | 关掉每 60 秒一次的常驻扫光 |
|  | `CSB_TUI_SWEEP_FRAMES` / `CSB_TUI_SWEEP_TICK` / `CSB_TUI_SWEEP_WB` / `CSB_TUI_SWEEP_SEC` | 常驻扫光的帧数 / 帧间隔 / 波形宽度 / 两次扫光之间的间隔秒数（默认 20×0.08 与 60）；不想看常驻扫光用 `CSB_UI_NO_SWEEP=1`（`CSB_UI_NO_SPLASH=1` 只跳开场动画） |
| 行为与自动化 | `CSB_AUTO_HIDE` | 设 `1` 时，刷新把「服务器已没有、又没快照指着」的失效记录**安静清掉**；默认什么都不清（留着你按 `d`） |
|  | `CSB_AUTO_HIDE_ASK` | 设成 `1` 时**先弹面板问**要不要清（同一个问题只询问一次；隐含允许清掉） |
|  | `CSB_AUTO_NO_ADOPT` | 设成 `1` 就关掉「打开 TUI 时的自动收编」 |
|  | `CSB_AUTO_NO_SEEN` | 设 `1` 就不补「地标」行（只对「户籍没登记、服务器还有快照」的沙箱有效） |
|  | `CSB_AUTO_NO_SPIN` | 关闭「waited Ns」那行转圈提示 |
|  | `CSB_AUTO_PROXY` | 开新沙箱时自动注入宿主代理：读本进程的 `HTTP(S)_PROXY`，把 `127.0.0.1` 换成宿主 LAN IP；设 `0` 关闭。自己用 `--env` 给了代理就不覆盖。注入的地址还会并进该沙箱的 `allow_out` |
|  | `CSB_INTERNAL_CIDR` | 平台沙箱网段，逗号分隔：注入的 `NO_PROXY` 会跳过它们，走宿主代理时也会并进该沙箱的 `allow_out`（默认空，源码不写死任何网段） |
|  | `CSB_AUTO_SBX_SWEEP` | 设 `0` 关闭事件式 sbx 政策回收（`csb ls` / `csb start` 成功后的自动清理）；默认开 |
|  | `CSB_AUTO_SBX_SWEEP_COOLDOWN` | 两次目击之间至少隔几秒才回收死政策（默认 600）；设 `0` 只为测试 |
|  | `CSB_AUTO_HW_RECLAIM` | 改名时若旧名前缀已经没有沙箱/快照，删除旧名的计数记录；设 `0` 则永久保留（改回旧名可续原号） |
| TUI 节奏 | `CSB_TUI_POLL` | 界面自动刷新的间隔秒数（默认 2） |
|  | `CSB_TUI_FORCE_REDRAW` | 画面残影 / 重画不对时，强制每次都整屏重画 |
|  | `CSB_TUI_FULL_REDRAW_SECS` | 每隔几秒做一次整屏重画（默认 `0` = 不做） |
|  | `CSB_TUI_RESYNC_SEC` | 每隔几秒丢弃缓存、跟服务器重新对账一次（默认 `300`） |
|  | `CSB_TUI_ESC_WAIT` | 解析 `ESC` 开头按键时等后续字节的秒数（默认 `0.25`）；太短会**丢键** |
| 管理 | `CSB_CUBEMASTER_HOST` / `CSB_CUBEMASTER_PORT` | `csb admin` 透传官方 CLI 的地址 / 端口（默认 `127.0.0.1` / `8089`） |
|  | `CSB_CUBEMASTERCLI` | 官方 CLI 的名字或路径（默认 `cubemastercli`） |
| 外部（CSB 只读） | `CUBE_API_URL` | 集群 API 地址（默认 `http://127.0.0.1:3000`） |
|  | `CUBE_API_KEY` | API key |
|  | `CUBE_PROXY_NODE_IP` | CubeProxy 节点 IP；没有泛域名 DNS 时**必须**设 |
|  | `SSL_CERT_FILE` | 自签证书路径 |
|  | `XDG_CONFIG_HOME` | 换掉 `~/.config` 这个根：**整包搬家**（户籍 / 偏好 / 日志 / 皮肤都跟着走）；**只认绝对路径** |
|  | `NO_COLOR` | 设成 1 就关闭所有颜色（纯文本，日志可直接归档） |
|  | `TERM` / `COLORTERM` / `TERM_PROGRAM` | 判断终端支不支持颜色 / 真彩；`TERM=dumb` 就当没有颜色；`TERM_PROGRAM` 挑默认框线 |
|  | `TMUX` / `STY` | 有值就表示运行在 tmux / screen 里；`i` shell 才提供「另开一扇窗」；纯终端里菜单没有这一行，footer 提示 `start csb tui inside tmux or screen…` |
|  | `HERDR_ENV` / `HERDR_WORKSPACE_ID` | 运行在 Herdr 里时由 Herdr 带进来；`i` shell 的第三条路要靠它 |

**只认 `CUBE_API_URL` / `CUBE_API_KEY`**；自造开关一律以 CSB 开头。
`csb config set <名> <值>` 写 `switches.json`；`csb config where` 说清哪一层盖掉了什么。
`csb prune` 只清「不在完整集群清单里」的死数据：死 entry 与死 sbx 政策；`--entries` / `--policies` 可只选一种，`--dry-run` 只列计划，写入前备份 registry 与 config。
**布尔开关只认 `1` / `0`**：写 `true` / `yes` / `on` 会打印警告并按默认值处理；留空 = 默认值。

**超时**：`csb exec` 默认等 **600 秒**，超过回 `rc=3`；要更久用 `CSB_EXEC_WAIT=1200` 或 `csb config set cube_exec_wait 1200`（上限 3600）。其余等待上限见上面「等待与超时」表。

## 附录：节点类型总表

树上的每个记号都在这里定义，并标出建立方式。

| 区段 | 显示 | 类型 | 这是什么 | 怎么造出来 | 什么时候会出现 | 挂在哪 |
| --- | --- | --- | --- | --- | --- | --- |
| 模板 |  `[T] name` | `tpl-root` | 有 alias 的模板 | 平台自带的模板 / `csb tpl alias` / `csb commit --alias` | — | 树根 |
|  |  `[T] tpl-xxxxxxxx` | `tpl-raw` | 匿名模板（没有 alias） | `template commit` 不给名字；或把某模板 alias `--clear` | — | `[U] no local name yet` 底下 |
|  |  `[D] <alias>` | `tpl-root` + `deleted` | 有 alias 的模板在服务器上没了，只剩本机那一行 | 先用 `csb commit --alias` 记一行 | 之后那模板从**别处**被删 | 树根 |
|  |  `[T] tpl-xxxxxxxx` | `tpl-raw` + `deleted` | **没有** alias 的本机残行（记号照类型给，所以是 `[T]`） | 同上，但那一行没带 alias | — | `[U] no local name yet` 里 |
| 沙箱与路标 |  `[S] name (running / paused)` | `start` | 有本机名字的沙箱 | `csb start pi --label zoo-01` | — | 它的模板 / 家族模板底下 |
|  |  `[S] name` | `clone` | 克隆出来的沙箱 | `csb clone <id>` | — | 来源底下；来源没了改挂家族 |
|  |  `[S] name` | `from-snap` | 从快照开的沙箱 | `csb start zoo-01-s --label zoo-02` | — | **那张快照底下** |
|  |  `[S] name (running)` | `start` / `clone` + `nolocal` | 服务器上有名字、本机户籍没登记（记号照类型给） | 不是 csb 建的 | 别处建的 / 别的 home 命过名，或按过 `U` 撤掉收编 | 它的模板 / 家族模板底下（模板也查不到就进 `[U]` 组） |
|  |  `[U] xxxxxxxx (running)` | `unadopted` | 服务器上也没名字（**有**模板可挂） | 直接用 SDK 开、不给 label | — | 模板底下 |
|  |  `[S] name` | `nolocal`，又挂不上模板 | 服务器上有名字、本机户籍没登记 | 不是 csb 建的 | 按过 `U` 撤掉收编，而它的模板也查不到 | `[U] no local name yet` 里（记号照类型给） |
|  |  `[S] xxxxxxxx` | `unadopted` | 没名字**又**没模板可挂（记号照类型给，所以是 `[S]`） | 同上 + 它的模板没有 alias | — | `[U] no local name yet` 里 |
|  |  `[D] name (deleted)` | `dead` | 路标：**沙箱已删、快照还在** | `csb kill <id>`（快照留着） | — | 家族模板底下；查不到就树根 |
|  |  `[E] xxxxxxxx (external)` | `dead` + `external` | 外部路标：快照记着一个两边都查不到的来源 id | 不是 csb 建的 | 别台机器（另一个户籍）建的沙箱 + 快照，之后沙箱没了（还没补过地标） | 树根 |
|  |  `[X] name (stale)` | `stale` | 残留：本机户籍有、服务器没有，而且没有快照挂着 | — | 沙箱被别的途径销毁，本机那一行还在 | `[X] leftover record` 底下 |
| 快照 |  `[s] name` | `snap` | 普通快照 | `csb snap <id> zoo-01-s` | — | 来源沙箱底下 |
|  |  `[s] snap-xxxx` + `(in use by 1 sandbox)` | `snap` + `clonetemp` | 克隆自动建的临时快照；N = 当下挂着它的副本数 | `csb clone`（自动） | — | 见〈三种「快照」不是一回事〉 |
|  |  `[s] snap-xxxxxxxx (orphan)` | `snap` + `orphan` | 没有本机记录的快照 | 平台自己产的 / 账本掉了（真集群造不出来） | — | `[s] unattached snapshots` 底下 |
| 群组头 |  `[X] leftover record` | 群组头 | 装 stale 的群组 | — | 同上 | 树根，排最后 |
|  |  `[U] no local name yet` | 群组头 | 装匿名模板 + 没地方可挂的沙箱 | — | — | 树根 |
|  |  `[s] unattached snapshots` | 群组头 | 平台连来源 id 都不给、又没户籍可挂的快照 | — | 本版平台会给 `origin`，所以真集群造不出来；平台改版后此组可能出现 | 树根；只有非空才长出来 |

**小标记**（哪一种节点都可能带）：

| 标记 | 意思 |
| --- | --- |
| `(running)` / `(paused)` / `(deleting)` | 平台回报的状态 |
| `(deleted)` | 这一个是 `[D]` 路标 |
| `(external)` | 这个节点是 `[E]` |
| `(stale)` | 这个节点是 `[X]` |
| `(orphan)` | 没有本机记录的快照 |
| `(N)` | 底下有几个**直接**子节点 |
| `*` / `>` | 第 2 格的 `*` = 标记；行首的 `>` = 光标 |
| `#xxxxxxxx` | 同一个名字出现两次时的短 id 去重（只在 `csb tree` 的文字输出；TUI 不另标） |

## 授权、致谢与参与

- 授权：MIT，全文见 `LICENSE`。
- 致谢：CubeSandbox 官方 SDK 与 `cubemastercli`。
- 参与：问题与改动请开在 <https://github.com/Buxton1984/csbtui/issues>。

<p align="center">
  <sub>(๑˃ᴗ˂)و&nbsp; Keep your agents sandboxed.</sub>
</p>
