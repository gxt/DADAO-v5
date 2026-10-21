# QEMU-068t: `clmul.o` 执行语义（64×64 无进位乘 → 128 位；`rd0` 单侧丢弃 + ILLI）

**模块**：qemu
**项目里程碑**：M9
**依赖**：`LLVM-122t`（`.td` 已定义 ⇒ MC 层可编码）、`INFRA-099t`（门控互斥；门控串行）。**scope 翻转归 `SPEC-155t`，本册不翻**（`excluded` 期间先落 trans，`check_qemu_trans` 计数照样绿 ⇒ 翻转册落地时 L2 全绿）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源（`ADR-0035` D2/D4/D6 + `spec/SimRISC-04 §3.5`）

- `clmul.o {rdHA, rdHB}, rdHC, rdHD`：`rdHC`/`rdHD` 视为 GF(2) 上 64 次多项式，做**无进位乘**（逐位与 + 异或累加、无跨位进位）⇒ 127 次多项式 = **128 位结果**；**`rdHA` = 高 64 位、`rdHB` = 低 64 位**（与 `mul.uo` 同型）。
- **不分符号**、**仅 `.o`**（窄宽度只是结果的掩码子集，`ADR-0035 D2/D4`）。
- `rd0` 规则：**单侧可为 `rd0`**（丢弃该半）、**不得双侧 `rd0`**、**不得同一非 `rd0` 寄存器**（`dst_dual_same`）⇒ 违者 **ILLI**。

### 现场事实（2026-10-21 核，执行前须复核）

- QEMU 侧**尚无** `insn.decode` pattern、**尚无** `trans_clmul_o_rrrr_rd` ⇒ `python3 tools/qemu/check_qemu_trans.py --strict` = **259/260**（`ISS-317`）。
- `ADR-0035 D7` 指定的「实现后落」两步：`scope` 翻转（**`SPEC-155t`**）+ 执行语义（**本册**）。
- `contracts/opcodes.yaml` 由 `SPEC-155t` 翻转后应为：`clmul.o` 无 `decode` 字段、`scope: m9`、`rule_refs: [dst_dual_same]`（**以现场输出为准**，本册不自行翻转）。
- 既有先例：`QEMU-067t`（`fence` + `lr/sc` 24 条）的 decode/trans/向量/门控注册结构，本册照同一节奏。

## ✅ 已裁定（2026-10-21）

- 4 册拆分（用户选定）：`scope` 翻转归 `SPEC-155t`，本册**只做执行语义**，不改 `contracts/`、不改 `spec/`。
- 语义按 `ADR-0035 D2`（高/低 128 位，`rd0` 单侧丢弃），不设 `clmulh`/`clmulr`/窄宽度/符号变体。

## 目标

1. QEMU 正确执行 `clmul.o`：128 位无进位乘、高/低两半分别写回、`rd0` 单侧丢弃；
2. `dst_dual_same` 反例在**真跑**中触发 ILLI；
3. L3 语义向量（独立 oracle 对拍）入 `tests/vectors` 并纳入 `check-qemu-semantics`。

## 接口规范

- **输入**：`components/qemu/patches/**`（`insn.decode`、`translate.c`）、`tests/vectors/**`、`tools/qemu/semantics_gate.py`、`tools/qemu/check_qemu_trans.py`。
- **输出**：
  1. `insn.decode` 增 `clmul_o_rrrr_rd`（`01010110` + 四字段），`trans_clmul_o_rrrr_rd` 实现真实语义（**不得**留 ILLI 桩）；
  2. 语义向量 + `semantics_gate` 注册（计数现场派生）；
  3. 证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `contracts/`/`spec/`（`SPEC-155t` 已翻）；不改门控判定语义；不动其它指令；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 解码与翻译

- pattern 命名/字段顺序照 `mul.uo` 先例：`rdha`(dst) / `rdhb`(dst) / `rdhc`(src) / `rdhd`(src)，全 `rd` bank。
- `trans_*` 覆盖：普通双写、**`{rd0, rdL}`**（丢高）、**`{rdH, rd0}`**（丢低）；写 `rd0` 时**不得**写入任何寄存器。
- 实现可用 `__uint128_t` 朴素循环（正确性优先）或分块 Karatsuba（须与朴素实现逐例对拍）；任何快路径都须自证等价。

### B. 向量（独立 oracle，**不得**从 QEMU/LLVM 反推）

- 覆盖：`0`、`1`、`1<<0`、`1<<63`、全 1、`(1<<63)*(1<<63)`（最高位进位边界）、随机 ≥ 64 组（种子固定落盘）。
- 期望值由 **Python 逐位 carry-less 乘**独立实现（先自检恒等式：`a*1==a`、`(1<<k)*(1<<m)==1<<(k+m)`、交换律/结合律各 ≥3 组）。
- `rd0` 两个方向各 ≥ 2 例（确认丢弃侧寄存器未被写）。

### C. 门控注册与计数

- 向量接入 `tools/qemu/semantics_gate.py`（册数/例数**现场派生**，禁写死）；`check-qemu-semantics` 归属 L3（`check-full`），本册至少单跑该目标绿。

## 验收标准

1. `python3 tools/qemu/check_qemu_trans.py --strict` ⇒ **260/260**（现场输出粘入完成区）。
2. 语义向量全绿（计数现场派生）；`check-qemu-semantics` rc=0。
3. ILLI 面：`{rd0, rd0}` 与同一非 `rd0` 寄存器两例 ⇒ **真跑 QEMU** 观察到非法指令异常（不得只看解码表）。
4. `make build-qemu` rc=0；`make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥ 2**（真实注入 → 红 → `cp`+md5 还原 → 绿）：(a) 高/低半写反 ⇒ 向量红；(b) 把 trans 降回 ILLI 桩 ⇒ 向量红 / `check_qemu_trans` 失败（须说明该桩是否仍被视为"有 trans"）。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；`ISS-317` 关闭（`resolved_by: QEMU-068t`）。

## 做（阶段）

1. 现场复核（`insn.decode` 结构与先例、`semantics_gate` 注册方式、当前 259/260）。
2. decode + trans + 朴素实现自测（先自证，再对拍）。
3. 向量 + 门控注册。
4. 反例注入 + 还原。
5. L1/L2 + 完成区 + `ISS-317` 关闭。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 高/低半写反（临时改 trans）⇒ 向量/对拍红；`cp` 备份 + md5 还原 ⇒ 绿。
- trans 降回 ILLI 桩 ⇒ 向量红（如桩仍算"有 trans"，须在完成区说明该判据的边界，并以向量红为主证据）。

## 已知边界（**披露，不自行扩面**）

- 不做常量折叠/性能模型（QEMU 非性能模型）。
- 不评估 `clmulr`（`rev∘clmul∘rev` 组合即可，`ADR-0035 D4`）。
- 不改 `scope`/`contracts/`/`spec/`（`SPEC-155t`）；不做集成用例（`TESTCASES-057t`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
