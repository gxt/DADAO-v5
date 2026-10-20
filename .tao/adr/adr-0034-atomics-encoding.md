# ADR-0034: 原子指令编码与命名（`fence` 迁 `100-000` / `lr`·`sc` 四宽度重排命名）

**状态**：Accepted（2026-10-20；`D1`–`D7` 由用户裁定原话逐条定向，见 `## 状态说明`）
**日期**：2026-10-20
**决策者**：用户（2026-10-20 裁定，原话见 `## Context`）
**关联**：`ADR-0014`（`fence` 首次列入 `excluded`）、`ADR-0012 D3.5`（`fence` 移入 `000-000`、`swym` 移 `100-010`）、`ADR-0032`（ISA 编码再分配先例：`spec/` 授权 + 只读锁重算 + 生成物重生成）、`spec/SimRISC-00 §4.1`（MISC-AMO 子表）、`spec/SimRISC-12 §3`（原子指令）、`spec/SimRISC-11`（`excluded` 清单）、`contracts/opcodes.yaml`、`manifests/spec-readonly.lock.toml`；issue = `ISS-307`

> **边界（本笔）**：本 ADR 只定**编码与命名**（`docs/Process-03`「ADR 不承载规范正文」）。
> `fence`/`lr`/`sc` 的 `scope` **仍为 `excluded`**（执行 ⇒ ILLI），**未实现**任何执行语义；
> **未改** `components/llvm-project/**` 的 `.td` ✗、**未改**任何任务书 `**状态**` ✗、**未改** `.tao/archive/**` ✗。

## Context（背景）

### 用户裁定（原话，**逐字引录**；渠道 = 经主会话问答，2026-10-20）

> 「1、fence指令的opx编码改为100_000，hb是fm，hc是pred，hd是succ，写法上仍然是18位无符号立即数，不拆成三段，但额外增加 PRED_R PRED_W PRED_I PRED_O SUCC_R/W/I/O，然后用 | 连接；2、lr/sc指令四种数据宽度，后缀为.b/.w/.t/.o，nn/an/nr/ar四种类型放在数据宽度后面，中间用 `.` 分隔开，opx 从000-000 排到 011-111；顺序从 .o 排到 .b（也就是说，现在的64位的8条指令向上移动两行）；然后，从中删除 lr.*.nr和sc.*.an」

> 「A」（= 采用本 ADR `D5` 的落位表）

**命名顺序纠正（同日，逐字引录）**：

> 「`lr/sc` 的后缀顺序是 **先数据宽度、再存储序** ⇒ 形如 **`lr.o.nn`**，**不是** `lr.nn.o`」

### 现场事实（2026-10-20 核）

1. **MISC-AMO（`op = 0x77`）现状**：`fence` = `000-000`（`ha=0x00`，`oiii`）；`lr_{nn,nr,an,ar}.o` = `010-000`…`010-011`（`ha=0x10`…`0x13`）；`sc_{nn,nr,an,ar}.o` = `011-000`…`011-011`（`ha=0x18`…`0x1B`）；`swym` = `100-010`（`ha=0x22`），均为 `orrr`/`oiii`。
2. **三条指令族均 `scope: excluded`**（`cfxld`/`cfxst`/`fence`/`lr`/`sc` 共 11 条）⇒ **无实现、无执行面**，改编码的迁移成本只在规范/合约/生成物层（无旧二进制/旧汇编源兼容包袱），故可一次重排。
3. **`lr`/`sc` 的语义已按 RISC-V RV64A 口径写定**（`SimRISC-12 §3.2`）：`lr` 的 `hb` 恒为 `rd0`（`hb ≠ rd0` ⇒ ILLI）；`sc` 成功写 `rdHB=0`、失败写 `1` 并清本 hart 全部保留；地址须 8 字节自然对齐，否则 **MALIGN**（`o` 宽度语义；见 `D6`）。
4. **`fence` 的现渲染面**：`SimRISC-12 §3.1` 现按「低 4 位 = IO/W/R/RW、`[17:4]` SBZ」描述单个屏障类型位图，与 `D2` 的 `fm/pred/succ` 三段位域**不一致**，须改写。
5. **`fence` 已在 LLVM/QEMU 生成面留下痕迹**：LLVM `DADAOInstrInfo.td` 有 `fence`（仅 MC 层、`Pattern = []`、`ha = 0x00`）；QEMU `insn.decode` 有 `fence_oiii_imm` 与 8 条 `lr/sc`（`@misc`，`trans_*` 桩 = ILLI）。**改 `ha`/改名必须同步这些生成面**，否则门控与补丁集漂移（见 `D7` 与 `Consequences`）。

### 命中 ADR 判据（`docs/Process-03`）

**高代价**（ISA 编码 + 助记符命名重排，波及规范/合约/生成器/生成物）、**跨模块 / 需一致**（spec / llvm / qemu / testcases）、**多方案且需记录取舍**（`lr/sc` 24 条落位方案 A vs 其他）、**外部契约**（汇编语言与机器码契约）⇒ 立本 ADR。

## Decision（决策）

### D1 — `fence` 编码：`op = 0x77`，`opx(ha) = 100-000 = 0x20`

`fence` 由 `000-000`（`ha=0x00`）迁至 **`100-000`**（`ha=0x20`）；`op` 仍为 `0x77`；格式仍 `oiii`；`value = 0x77800000`、`mask = 0xFFFC0000`；`id` 保持 **`fence_oiii_imm`**（不改名）。语义面不变的只有「屏障」这一职责本身，位域解释见 `D2`。

**理由**：用户原话「fence指令的opx编码改为100_000」；`100-000` 在 MISC-AMO 子表现场为空，且 `swym` 已在 `100-010`，同族相邻。

**被否**：保留 `000-000` —— `D5` 方案 A 需要 `000-000`…`001-011` 共 12 个连续格位给 `lr`，`fence` 占着首格则整族必须错位或跨行断开。

### D2 — `fence` 立即数位域：`fm`/`pred`/`succ` + 符号常量（书写**仍是 18 位无符号立即数**）

`immu18` 三段（**不拆成三段操作数**，汇编层仍写「一个 18 位无符号立即数」）：

| 字段 | 位 | 含义 |
| --- | --- | --- |
| `fm` | `immu18[17:12]` | 屏障模式（fence mode） |
| `pred` | `immu18[11:6]` | 前序（predecessor）访问类型集合 |
| `succ` | `immu18[5:0]` | 后序（successor）访问类型集合 |

**符号常量**（汇编便利，`|` 组合）：`PRED_R = 1<<6`、`PRED_W = 1<<7`、`PRED_I = 1<<8`、`PRED_O = 1<<9`、`SUCC_R = 1<<0`、`SUCC_W = 1<<1`、`SUCC_I = 1<<2`、`SUCC_O = 1<<3`。

**合法性**：
- 每个 6 位字段的**高 2 位 SBZ**——`pred` 的 `[11:10]`、`succ` 的 `[5:4]`；非零 ⇒ 保留（`ILLI`）。
- `fm = 0` 为**唯一已定义值**；其余取值**保留 ⇒ ILLI**；其中 `fm = 8` 标注为「**TSO 预留、当前未定义**」（预留说明，不给语义）。

**理由**：用户原话「hb是fm，hc是pred，hd是succ，写法上仍然是18位无符号立即数，不拆成三段，但额外增加 PRED_R PRED_W PRED_I PRED_O SUCC_R/W/I/O，然后用 | 连接」。

**被否**：拆成三段操作数（`fence fm, pred, succ`）—— 用户明确「不拆成三段」；保留旧「低 4 位类型位图」—— 与 `fm/pred/succ` 三段口径不兼容，且旧口径无法表达 pred/succ 各自独立的 R/W/I/O 集合。

### D3 — `lr/sc` 命名：`<lr|sc>.<b|w|t|o>.<nn|an|nr|ar>`

**宽度在前、存储序在后**，两段之间用 `.` 分隔；`id = <助记符>_orrr_rd`（例 `lr.o.nn_orrr_rd`）。

- 位宽集：`.o`(64) / `.t`(32) / `.w`(16) / `.b`(8)；**组内顺序 `.o → .t → .w → .b`**。
- 存储序：`nn`（无）/`nr`（释放 release）/`an`（获取 acquire）/`ar`（两者兼有）。

**理由**：用户原话（命名顺序纠正）「先数据宽度、再存储序 ⇒ 形如 `lr.o.nn`，不是 `lr.nn.o`」。

**被否**：旧写法 `lr_nn.o` / 用户首版 `lr.nn.o` —— 均被同日纠正取代（前者用下划线分族、后者顺序相反）。**不做旧名别名**（与 `ADR-0032 D3` 同一口径：旧写法不再受理）。

### D4 — `lr/sc` 保留集：`lr` 仅 `nn/an/ar`；`sc` 仅 `nn/nr/ar`

**删除 `lr.*.nr` 与 `sc.*.an`**（各 4 条 × 4 宽度 = 各删 4 条）。理由：`lr` 是读侧「获取」语义、`sc` 是写侧「释放」语义，反方向的组合在 RV64A 亦不存在（`lr` 只有 `.aq/.aqrl`，`sc` 只有 `.rl/.aqrl` 的对应关系在本设计映射为 `an/ar` 与 `nr/ar`）。用户原话「从中删除 lr.*.nr和sc.*.an」。

### D5 — `lr/sc` 编码落位（**方案 A**，逐条）

`op` 一律 `0x77`；`value = (0x77 << 24) | (ha << 18)`；`mask = 0xFFFC0000`；格式 `orrr`；`fields` 保持三字段 `rdhb`/`rdhc`/`rbhd`（bank `rd`/`rd`/`rb`）。

| ha（opx） | 助记符 | id |
| --- | --- | --- |
| `000-000` `0x00` | `lr.o.nn` | `lr.o.nn_orrr_rd` |
| `000-001` `0x01` | `lr.t.nn` | `lr.t.nn_orrr_rd` |
| `000-010` `0x02` | `lr.w.nn` | `lr.w.nn_orrr_rd` |
| `000-011` `0x03` | `lr.b.nn` | `lr.b.nn_orrr_rd` |
| `000-100` `0x04` | `lr.o.an` | `lr.o.an_orrr_rd` |
| `000-101` `0x05` | `lr.t.an` | `lr.t.an_orrr_rd` |
| `000-110` `0x06` | `lr.w.an` | `lr.w.an_orrr_rd` |
| `000-111` `0x07` | `lr.b.an` | `lr.b.an_orrr_rd` |
| `001-000` `0x08` | `lr.o.ar` | `lr.o.ar_orrr_rd` |
| `001-001` `0x09` | `lr.t.ar` | `lr.t.ar_orrr_rd` |
| `001-010` `0x0A` | `lr.w.ar` | `lr.w.ar_orrr_rd` |
| `001-011` `0x0B` | `lr.b.ar` | `lr.b.ar_orrr_rd` |
| `010-000` `0x10` | `sc.o.nn` | `sc.o.nn_orrr_rd` |
| `010-001` `0x11` | `sc.t.nn` | `sc.t.nn_orrr_rd` |
| `010-010` `0x12` | `sc.w.nn` | `sc.w.nn_orrr_rd` |
| `010-011` `0x13` | `sc.b.nn` | `sc.b.nn_orrr_rd` |
| `010-100` `0x14` | `sc.o.nr` | `sc.o.nr_orrr_rd` |
| `010-101` `0x15` | `sc.t.nr` | `sc.t.nr_orrr_rd` |
| `010-110` `0x16` | `sc.w.nr` | `sc.w.nr_orrr_rd` |
| `010-111` `0x17` | `sc.b.nr` | `sc.b.nr_orrr_rd` |
| `011-000` `0x18` | `sc.o.ar` | `sc.o.ar_orrr_rd` |
| `011-001` `0x19` | `sc.t.ar` | `sc.t.ar_orrr_rd` |
| `011-010` `0x1A` | `sc.w.ar` | `sc.w.ar_orrr_rd` |
| `011-011` `0x1B` | `sc.b.ar` | `sc.b.ar_orrr_rd` |

保留空格：`001-100`…`001-111`、`011-100`…`011-111`（不新增记录）。`swym` **不动**（仍在 `100-010` = `ha=0x22`）。

**理由**：用户原话「A」；`lr` 占 `000/001` 两行（每组一行、组内 `.o→.b`）、`sc` 占 `010/011` 两行，两族各 12 条、族内连续，保留字 `excluded` 格位后无空洞。

**被否**：按存储序分行（`nn`/`an`/`nr`/`ar` 各一行）—— 用户要求「顺序从 `.o` 排到 `.b`」，宽度必须是最内层变化轴；`lr.nr`/`sc.an` 保留 —— 见 `D4`（用户要求删除）。

### D6 — 语义不变（只改编码与命名）

- `lr` 的 `hb`（`rdHB`）**必须为 `rd0`**；手工编码 `hb ≠ 0` ⇒ **ILLI**；汇编只写两个操作数。
- `sc` 成功写 `rdHB = 0`、失败写 `rdHB = 1`，且**无论成败都清本 hart 全部保留标记**。
- **对齐**：`lr/sc` 的地址须**按数据宽度自然对齐**（`.b`=1 / `.w`=2 / `.t`=4 / `.o`=8 字节），不满足 ⇒ **MALIGN**。
  > 修订（2026-10-21，用户裁定「甲」）：原「一律 8 字节」在引入多宽度后与「按数据宽度」冲突，现按后者；`.o` 仍为 8 字节。
- 四种存储序 `nn`/`nr`/`an`/`ar` = 无 / 释放 / 获取 / 两者兼有。
- `fence` 的职责（对设备 I/O 与内存访问的串行化）不变。

**理由**：用户原话只涉及编码/命名与 `fence` 位域，未改语义；语义正文仍是 `SimRISC-12 §3`。

### D7 — 未实现声明：`scope` 仍为 `excluded`；实现归后续任务册

本 ADR **只定义编码与命名**。`fence`、24 条 `lr/sc` 的 `scope` 保持 `excluded`（`decode: ILLI`），**执行即非法指令**；执行语义实现（含 `lr.t`/`sc.t` 等窄宽度落地与原子后端）归**后续任务册**，本笔不实现、不重建后端。

**执行前置（2026-10-20 现场核实，须与实现册同批处理）**：`fence` 的 `ha` 变更会使下列**生成面/编译面**滞后，本笔按「不改组件源码」边界**未触碰**：
1. LLVM `DADAOInstrInfo.td` 的 `let ha = 0x00;`（仅 MC 层 `oiii` def）须改 `0x20`，并**重建 `llvm-mc`**（`install-host`）；否则 `check-instrinfo`（orphan/allow-list）与 `check-isa-coverage`（编码复核 mismatch）**红**。
2. QEMU `insn.decode` + `insn_trans/*.c.inc` 的 `trans_*` 桩名（`lr/sc` 8 条 → 24 条）须随 `id` 重生成；QEMU 侧 `excluded` 桩全为 ILLI，语义无变化。

## Rationale（理由）

1. **零迁移成本窗口**：三族均 `excluded`（无实现、无执行语义），此刻重排编码只动规范/合约/生成物，不产生旧二进制/旧汇编源的兼容包袱。
2. **`lr/sc` 一次排满两行**：`lr` 独占 `000`/`001`（`nn`/`an`/`ar` × 四宽度），`sc` 独占 `010`/`011`（`nn`/`nr`/`ar` × 四宽度），族内连续、跨族不交叠，人工编码/阅读成本最低。
3. **命名与位宽轴一致**：宽度做最内层变化轴（`.o→.b`），与本项目「子表 ⇔ 位宽后缀」惯例同向，且宽度信息靠近助记符词首，便于按宽度扫描汇编清单。
4. **`fence` 迁 `100-000`**：既给 `lr` 腾出 `000-000`，又与 `swym`（`100-010`）同族相邻。

## Consequences（影响）

1. **汇编源不兼容**：`lr_nn.o` 等 8 条旧写法不再受理，改为 24 条新写法；`fence` 仍写「18 位无符号立即数」，但其位域解释与合法常量集变了（旧「低 4 位类型位图 + 其余 SBZ」口径作废）。
2. **机器码不兼容**：`fence` 编码 `0x77000000 → 0x77800000`；`lr/sc` 全部换格（`0x77000000` 现归 `lr.o.nn`）。因两族均 `excluded`（ILLI），不影响任何可执行产物。
3. **`opcodes.yaml` 计数**：`excluded` 11 → **27**（8 → 24，净 +16）；总数 243 → **259**（现场派生，不写死）；`tools/spec/check_scope.py` 的期望计数须同步。
4. **生成物 / 引用面**：`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`、`tests/llvm/lit/MC/DADAO{-gen}/gen-*.s`、`spec/SimRISC-12` 生成区（汇编速查 / 合法性检查）、`.tao/contracts/contract-asm-list.md` 已重生成；`.tao/contracts/contract-isa.md`（§14.2 + 附录 A 编码矩阵）、`contract-asm.md`（§LR-SC 书写规则）、`spec/Toolchain-01 §5` 的旧名示例已同步为 `lr.o.nn`/`sc.o.nn`（仅名字）；QEMU `insn.decode` + `insn_trans/*` 待重生成（见 `D7` 执行前置 2）。
5. **只读锁**：`spec/SimRISC-00`/`SimRISC-12`（及若改动的 `SimRISC-11`）须在**用户授权**下重算 `sha256`（`manifests/spec-readonly.lock.toml`）。
6. **后端/模拟器滞后**：LLVM `.td` 的 `fence.ha` 与 QEMU `trans_*` 桩名未随本笔同步（`D7` 执行前置），故 `check-instrinfo`/`check-isa-coverage` 在本笔内**不可绿**——须由实现册（含 `install-host`）收口。

## 状态说明

- **逐条定向（2026-10-20）**：用户以裁定原话定向 `D1`/`D2`（fence 编码与位域）、`D3`/`D4`（`lr/sc` 命名与保留集）、并选定 `D5` 方案「A」；`D6`（语义不变）与 `D7`（未实现声明）为上述裁定的直接推论，无新增语义。**`**状态**` = Accepted**。
- **命名顺序纠正**：用户同日将 `lr.nn.o` 类命名纠正为 `lr.o.nn`（宽度在前），本 ADR `D3`/`D5` 已按纠正版落纸；`.o→.b` 组内顺序与 24 条落位**不变**。
- **`spec/` 授权**：本笔 `spec/SimRISC-00 §4.1`、`spec/SimRISC-12 §3` 的改动由用户 2026-10-20 裁定「落规范面」直接授权（`docs/Process-06`）。
- **已核事实的时效**：`Context` 的 5 条事实来自 2026-10-20 现场；执行册须现场复核，不复核不得作为验收依据。
- **执行前置收口（2026-10-21，非决策变更）**：`D7` 的两项执行前置**已落** —— `fence` 的 `let ha = 0x20`（`.td` 补丁重导）+ `make install-host` 重建（`check-isa-coverage` 259/233/26 复核不符 0）+ QEMU `insn.decode` 重生成（259 pattern）与 `trans_*` 桩 8→24；`check-instrinfo` / `check-isa-coverage` / `check-patch-tree`(185) / L1 已绿。**`D7` 的「未实现」结论不变**：`scope` 仍 `excluded`、执行仍 ILLI，语义实现归 `ISS-307` 的 4 册。
