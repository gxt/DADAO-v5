# QEMU-061t: `rela.si` 的解码与语义（`0x5A` / `rbHA = PC + (imms18 << 12)` / 目的 `rb0` ⇒ ILLI）

**模块**：qemu
**项目里程碑**：M8
**依赖**：`ADR-0029`（**`Accepted`**，2026-10-16 用户逐条确认 —— 本册 = `D1`（语义 / 目的 `rb0` ⇒ ILLI）/ `D7③` 的执行落点）、**`SPEC-145t`**（**前置**：编码 / 语义**冻结**后才可动译码与执行 ⇒ 其 `已验证` 前**不得开工**）、**`LLVM-095t`**（**串行在前**：与 `tests/vectors/**` 共用载体，`AGENTS.md`「同改共享文件一律串行」）、`ADR-0012 D5`（**被本册回退**的解码项：`0x5A` → UNDI）、`ADR-0019 D3`（`rb0` = 当前指令地址）/ `D6`（越界报错口径的同族「禁静默」纪律）；契约真源 = `.tao/contracts/contract-isa.md §1.3.2`（`rb0`）/ `contract-fp` 无关；现场来源 = `QEMU-060t`（本模块最近落地的回退任务）、`ISS-230`；纪律 = `ISS-210`（改组件后安装根须同步）/ `ISS-229`（重建串行）、`docs/Process-01`（组件补丁树）、`docs/Process-05`（L2 冒烟 / L3 语义）
**状态**：待开始

> **本册边界** ✗：只做 **QEMU 侧解码 + 语义 + 本模块向量 / 证据**；**不改** `spec/` ✗（归 `SPEC-145t`）、**不改** LLVM / lld ✗（归 `LLVM-095t`）、**不建**重定位类型 ✗。判据 = **执行语义**（L3 + 独立 oracle），**非**「能编译」。

## 执行环境
**执行环境**：本地

## 目标（交付物）

1. **解码**：`0x5A` 由「保留（UNDI）」变为**合法指令** `rela.si`（`riii`）；`components/qemu/patches/target/dadao/insn.decode.patch` 与 `contracts/opcodes.yaml`（`SPEC-145t` 冻结）**逐条一致**。
2. **语义**：`rbHA = PC + (sign_extend(imms18) << 12)`；其中 **`PC` = 该指令自身地址** = `rb0` 读出值（**非下一条**）；**`<< 12` = 4 KB 块、无 `<< 2`**；`imms18` **有符号**；**PC 低位不清零**。
3. **合法性与异常**：目的 `ha == rb0` ⇒ **ILLI**（= `dst_rb0` 规则；与既有 `rb0` 只读语义同形）；**「`0x5A` ⇒ UNDI」路径消失**（回归面：既有「未知编码 ⇒ UNDI」类向量须同步）。
4. **向量 / 证据**：QEMU 语义向量（`docs/Process-05`：**L3** 全量 + **L2** 冒烟代表集，机械派生）；一键证据**可达 FAIL**。

## 现场事实（**architect 只读预核，2026-10-16**；执行时逐条复核）

1. **解码补丁现状**：`components/qemu/patches/target/dadao/insn.decode.patch:78` 现为
   `# 0x5A: rela.si deleted (ADR-0012 D5) → reserved → UNDI`（**手写注释行**，位于 `add_si_riii_rd`(`0x59`) 与 `add_si_riii_rb`(`0x5B`) 之间）⇒ 本册须把它替换为 `rela.si` 的合法 pattern（命名 / 函数名由生成器定，见 3）。
2. **生成器与产物计数不一致（⚠️ 现场核实项）**：补丁头写 `# 234 patterns; blank cells trigger UNDI`，而生成器 `tools/qemu/generate_decodetree.py:105` 写死 `# 256 patterns`（现场核：该行为字面量，非派生）⇒ **重生成后须以产物为准**，并**核对 / 订正**该计数文案（**不留漂移**；`SPEC-145t` 后正确值应为 **235**）。
3. **生成 / 校验工具链**（复用优先，不另造）：`tools/qemu/generate_decodetree.py`（由 `contracts/opcodes.yaml` 生成）/ `tools/qemu/validate_decodetree.py`（补丁 ↔ `opcodes.yaml` 一致性、pattern 与 `trans_*` 对应）/ `tools/qemu/check_qemu_trans.py`（每条 insn 是否有 `trans_*` 定义；**默认 rc=0、`--strict` 非零**；扫不到补丁时**无条件非零**）。
4. **`rb0` / ILLI 现状**：`translate.c.patch` 已有「`rb0` = `PC` = current instruction address」（翻译期计算）与「写 `rb0` 触发 ILLI（`rb0` = PC、只读）」的既有实现（现场核：`Load rb[n] into a TCG temp. rb0 = PC` / `Writes to rb0 trigger ILLI`）⇒ 本册**复用**，不新引入寄存器模型。
5. **历史探针**：`tools/qemu/min_rom_probe_009t.py` 明标 **OBSOLETE**（`rela.si` 已删、`0x5A` = UNDI；保留为历史产物）⇒ **不改它** ✗；本册**新建** `tools/qemu/min_rom_probe_061t.py`（命名随任务号；**生成器 / 探针随产物保留**）。
6. **门控载体**：`check-qemu-semantics`（**L3**）现取 `tests/vectors/isa/{reg-shift-extend,reg-compare}.yaml` **全量**；`check-qemu-smoke`（**L2**）按 (class, mnemonic) **机械派生**代表集 ⇒ 新指令进代表集的路径由派生规则决定（**不手工挑**）。

## 范围（做项）

1. **解码**：重生成 / 更新 `insn.decode.patch` ⇒ `0x5A` 为 `rela.si`（`@main`，`ha` / `imms18` 字段位与 `add.si` 同族）；删去 `0x5A … UNDI` 手写注释；**头部 pattern 计数与产物一致**（见「现场事实 2」）。
2. **语义**：在新 `trans_*`（或既有地址运算转译）内实现 `rbHA = PC + (sign_extend(imms18) << 12)`；`PC` 取**该指令自身地址**（复用既有 `rb0` 计算口径）；`imms18` 符号扩展；目的 `rb0` ⇒ **ILLI**（复用既有检查）。
3. **异常 / 回归面**：确认「保留编码 ⇒ UNDI」路径不再覆盖 `0x5A`；排查既有把 `0x5A` 当 UNDI 的测试 / 探针（**逐条处置或登记**，不留静默悬挂）。
4. **向量**：
   - **L1 编码**（与 `SPEC-145t` 共用载体 ⇒ **串行在后**）：如需在本地复跑编码向量，复用 `SPEC-145t` 产物，**不重复造**；
   - **L3 语义**：`tests/vectors/isa/**` 增 `rela.si` 语义例（**独立 oracle**：按 `ADR-0029 D1` 公式在 host 侧派生期望值，**不从 QEMU 反推**；边界 = PC 基准是**自身地址**、`<<12`、负立即数、目的 `rb0` ⇒ ILLI、大端）；
   - **L2 冒烟**：确认机械派生代表集纳入新指令（**不手工挑**）。
5. **一键证据** `.work/evidence/<任务ID>/run.sh`（含**反例注入 ⇒ FAIL ⇒ 还原 ⇒ 回绿**；还原用 `cp` 备份 + md5 对账，**禁** `git checkout`/`restore`/`stash`）。
6. **重建与安装**：改 `components/qemu/patches/**` ⇒ `make build-qemu` rc=0 + `make install-host` rc=0（**安装根须与构建树同步**，否则 `check-qemu-semantics` 读**旧二进制** ⇒ **假绿**，`ISS-210` 同类纪律）。

## 验收标准

1. **解码**：`0x5A` 在 QEMU 侧解为 `rela.si`（无 UNDI）；`python3 tools/qemu/validate_decodetree.py <生成物>` rc=0；`python3 tools/qemu/check_qemu_trans.py --strict` rc=0（`rela.si` 有对应 `trans_*`）；补丁 ↔ `contracts/opcodes.yaml` **逐条一致**。
2. **语义（L3 + 独立 oracle）**：`rela.si` 语义例全通过；期望值**独立派生**（`ADR-0029 D1` 公式 + host 侧计算），**不从 QEMU / LLVM 反推**；覆盖 = **正 / 负** `imms18`、`ha != rb0`、**PC 基准 = 自身地址**（**关键**：与 0628 的 `PC + 4` 口径**不同** ✗）、大端。
3. **目的 `rb0` ⇒ ILLI**：≥1 例断言 ILLI（**可达 FAIL**：把检查关掉应转红）。
4. **UNDI 路径消失**：原「`0x5A` ⇒ UNDI」断言已改指向（**新目标现场派生**，禁按记忆挑）；其余保留编码仍 UNDI（**不回归**）。
5. **门控**：`make check-qemu-smoke`（L2）rc=0；`make check-qemu-semantics`（L3）rc=0 且计数**现场派生**（不写死）；`make check`（L1）rc=0；`check-patch-tree` / `check-index-blobs` / `check-no-residue` rc=0。
6. **证据**：`.work/evidence/<任务ID>/run.sh` 跑通 + 反例注入节；日志 `.work/log/qemu/QEMU-061t-*.log`。
7. **重建留痕**：`build-qemu` / `install-host` 的 rc + **申报耗时 vs 实测耗时** + 安装根二进制 mtime 晚于源码改动（防假绿）。

## 前置申报（**必读**）

- **本册必改 `components/qemu/patches/**`**（编译输入变化）⇒ **须 `make build-qemu` + `make install-host`**；**启动前现场评估并申报预计耗时**；**`JOBS=8`、禁全核**；**单跑一个长任务**、日志落 `.work/log/qemu/`、`setsid nohup` 脱离 + 落 `XXX_EXIT=$rc`（长任务由**主会话**发起；**子代理不得在会话内等待**）。
- **不得**与 `build-*` / L2 / L3 / 其它会话的重建**并发**（`ISS-229`）。
- **串行**：本册**在 `SPEC-145t` 与 `LLVM-095t` 之后**（同改 `tests/vectors/**` 载体）。
- 补丁纪律 = `docs/Process-01`（树形补丁集 / 一文件一补丁 / `git apply`）+ `check-patch-tree`。

## 不做项（显式）

1. **改 `spec/`** ✗（归 `SPEC-145t`）；**LLVM / lld / CodeGen** ✗（归 `LLVM-095t`）；**重定位类型**（`PCREL_HI`/`PCREL_LO`）✗。
2. **改 `tools/qemu/min_rom_probe_009t.py`** ✗（明标 OBSOLETE 的历史产物；新建 `…_061t.py` 代替）。
3. **`dadao-m1` 的 syscall 服务** ✗（用户 2026-10-15 裁定撤回，`QEMU-060t`；不重引入）；**`qemu-user`** ✗（`P3`）。
4. **relaxation** / **`ABS48` 两段式** / **自写 `ld.so`** ✗。
5. 跳过「重建 + 安装」直接改门控期望值 ✗（**假绿**）。
6. `ISS-222` / `ISS-223` 收口 ✗（撞上即登记 + 转出，**不得**静默跳过）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
