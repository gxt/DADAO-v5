# QEMU-068t: `clmul.o` 执行语义（64×64 无进位乘 → 128 位；`rd0` 单侧丢弃 + ILLI）

**模块**：qemu
**项目里程碑**：M9
**依赖**：`LLVM-122t`（`.td` 已定义 ⇒ MC 层可编码）、`INFRA-099t`（门控互斥；门控串行）。**scope 翻转归 `SPEC-155t`，本册不翻**（`excluded` 期间先落 trans，`check_qemu_trans` 计数照样绿 ⇒ 翻转册落地时 L2 全绿）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源（`ADR-0035` D2/D4/D6 + `spec/SimRISC-04 §1.5`）

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

**测试结果**：clmul 向量 **81/81**（计数现场派生；`run_qemu_test` rc=0）；ILLI 真跑 2/2（case[79]/[80] 均 `Exit code: 0x88` / `Expected ILLI, got ILLI`）；`check_qemu_trans --strict` **260/260**（基线独立核 `git archive HEAD` + `--src` 临时树 = 259/260 rc=1）；`check-qemu-semantics` PASS（967/978，11 既有 deferred，载体 20 册）；`build-qemu` rc=0；L1 rc=0；L2 rc=0；证据 `run.sh` 20 PASS / 0 FAIL。
**修改文件**：`components/qemu/patches/target/dadao/insn.decode.patch`、`.../insn_trans/trans_arith.c.inc.patch`；`tools/qemu/semantics_gate.py`、`tools/qemu/generate_clmul_vectors.py`（新）；`tests/vectors/clmul/clmul.yaml`（新）、`tests/vectors/inventory.md`；`.work/evidence/QEMU-068t/run.sh`；`.tao/knowledge/issues.yaml`（ISS-317）。
**验收结果**：`check_qemu_trans: 260/260 insns have trans impl (M1 156/156)` rc=0；`validate_decodetree: PASS`；`check-qemu-semantics: PASS（967/978，载体 20 册）`；`module checks (L2): PASS`；`repository checks (L1): PASS`。注入：高/低写反 ⇒ 向量 rc=1 / failed=74；trans 降 ILLI 桩 ⇒ rc=1 / failed=79（且 `check_qemu_trans` 仍 260/260）；`cp`+md5 还原 + `touch` 重建 ⇒ 均回绿 81/81。
**新发现/坑**：① 结合律自检不能用「结果再掩 64 位」的 oracle（中间积 >64 位会截断）⇒ 须用不限宽 `clmul_full`；② `cp -p` 还原会用旧 mtime，ninja 判定 up-to-date ⇒ **假绿**（首跑 restore-a/b 仍红且失败计数与注入态相同，`touch` 后回绿）——「源码还原 ≠ 二进制还原」的 mtime 变体，建议沉淀 `lessons §2.9`；③ `.work/log/**` 文件名须以任务号开头（否则 `check-run-artifacts` 红 L1）；④ `insn.decode` 头注释计数须随 pattern 数同步；⑤ 任务书「LLVM-122t `.td` 已定义」与现场不符（该册 `待开始`、无 clmul `.td`）——本册不依赖 LLVM（向量用原始编码字），ISS-317 关闭仅覆盖 QEMU 面 + L3 向量。
**遗留问题**：`milestones.md` 行已置 `待验收`（`/complete` 时改 `已验证` + 完成时间）；LLVM `.td`/ISel/builtin 归 `LLVM-122t`，`scope → m9` 归 `SPEC-155t`（已在 ISS-317 note 注明）；无其它。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-22）

逐行审查 `trans_clmul_o_rrrr_rd`、生成器与证据脚本：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| i=0 时计算 `a >> 64` 属移位 UB | ✅已修 | 高半贡献仅 `i > 0` 时发射（最大移 63） | 81/81 + 注入红 |
| 源/目的重叠须先读后写（spec §3.5） | ✅已确认 | `load_rd` 先于 `store_rd`，TCG 临时量已捕获 | 两条 `overlap` 向量（`{rd1,rd2},rd1,rd4` / `{rd1,rd2},rd3,rd1`）81/81 绿 |
| `rd0` 双侧/同寄存器 ILLI 复用正确 | ✅已确认 | 复用 `check_dual_dest_legal`（两规则精确对应） | case[79]/[80] 真跑 0x88 |
| 结合律自检用了 64 位截断 oracle | ✅已修 | 自检改用不限宽 `clmul_full`；ISA oracle 仍 64 位 | `generate_clmul_vectors.py` rc=0 |
| 注入还原 `cp -p` 后未重建（假绿） | ✅已修 | 还原后 `touch` 强制重编译 | restore-a/b 均 81/81 rc=0 |
| 64×~9 条 TCG op 的体积 | ⏸延后 | 属正确性优先的朴素实现；QEMU 非性能模型 | 本册边界（不做性能模型） |

判决：findings 全部处置（无未修项）⇒ `待验收`。

### 第 1 轮 reviewer 验收（2026-10-22）

**判决：Accepted**（下述命令均为 reviewer 独立重跑，未采信完成区）

**重跑记录**：`check_qemu_trans --strict` = `260/260 (M1 156/156)` rc=0；基线 `git archive e3449ab1`（contracts+patches → 临时树）+ `--yaml/--src` = `259/260` rc=1（`MISSING: clmul.o_rrrr_rd`）⇒ 增量属本册。`validate_decodetree` = `260 patterns / 0 错误 / PASS` rc=0。`make build-qemu` rc=0；`make check`(L1) rc=0（`repository checks (L1): PASS`）；`make check-modules`(L2) rc=0（`module checks (L2): PASS`）；`make check-qemu-semantics` rc=0（`PASS 967/978`，载体 20 册 / 978 例现场统计，含 clmul 81 例）。`run_qemu_test tests/vectors/clmul --batch` = `81 total, 81 passed, 0 failed` rc=0；case[79]/[80] 单跑均 `Exit code: 0x88 / Expected ILLI, got ILLI`。证据脚本 reviewer 两次重跑：`PASS=20 FAIL=0`，rc=0。

**语义独立性**：reviewer 另写**系数卷积** oracle（与生成器「逐位移位异或」异法；手证 `(x+1)²=x²+1`、`(1<<63)²=1<<126`），复核已提交 78 条非 ILLI 期望**全部吻合**（`rdHA`=高 / `rdHB`=低），2 条 ILLI 用例目的确为同寄存器。自造 69 条向量（独立种子 `0x5EEDBEEF`：33 随机 + 6 稀疏/密集 + 0/1/`1<<63`/全 1/`(1<<63)²` 边界 + 8 条 **hi≠lo 可判别**的 `rd0` 单侧 + 2 重叠 + 3 ILLI，含哨兵寄存器未被写断言）真跑 **69/69** rc=0。`generate_clmul_vectors.py --check` = `81 cases, byte-identical` rc=0。

**注入（reviewer 独立，`cp`+md5，未用 checkout/restore/stash）**：(a) 高/低写反（`d08a68c4→bdd20966`）+ 重建 ⇒ `81 total, 74 failed` rc=1（dump 可见两半已互换）；`cp`+`touch`+重建 ⇒ md5 复归 `d08a68c4`、二进制复归 `d7c7a35d`、81/81 rc=0。(b) 删 `check_dual_dest_legal`（`0145832b`）⇒ case[79]/[80] 红（`Expected fault ILLI, got FAIL(0x01)`）⇒ ILLI 确来自 trans 合法性检查；还原回绿 81/81。

**约束核验**：`spec/**`、`contracts/**` 零改动（`git diff --name-status e3449ab1..cadab494` 共 9 文件，无此二者）；`opcodes.yaml` 中 `clmul.o` 仍 `scope: excluded` + `decode: ILLI`；门控判定语义未改（`check_qemu_trans.py` 未动，`semantics_gate.py` 仅加 `clmul` 载体与注释）。验收前后 `git status --porcelain -uall` 均为空、HEAD 仍 `cadab494`、`.work/source/qemu` 干净；未 commit/push；临时产物只在 `/tmp/opencode/QEMU-068t-review/`。证据脚本无恒真/吞码：锚点 assert 保证注入必生效、解析失败得 `-1≠81` 判 FAIL、重建失败即 fail-closed；不依赖工作树 `git diff`（提交后可重放，本轮两次重放均证）。

**非阻塞观察（供 architect 定夺）**：① 值不匹配时 harness 走 TIMEOUT + `Unsupported SemiHosting SWI 0x00`，显示为 `Unknown exit code: 0x-6`（负数格式化缺陷），非本册交付面（同 ISS-098 族），建议另立 issue；② `run.sh` 未纳入 `generate_clmul_vectors.py --check` 漂移门（reviewer 手跑为绿）；③ `.work/` 整体 gitignore ⇒ run.sh 不入 git（全仓库既有惯例）。

