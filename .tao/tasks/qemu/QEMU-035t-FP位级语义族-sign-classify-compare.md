# QEMU-035t: FP 位级语义族（sign 4 + classify 2 + compare 4 = 10 条）

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：`QEMU-034t`（**必须先 `已验证`**：提供 `trans_fp.c.inc` 骨架、`load_rf`/`store_rf`、`dst_rf0` 检查 helper、探针范式）。相关：`SPEC-087t`（合约）、`LLVM-029t`/`LLVM-030t`（编码/汇编期对照）。
**状态**：待开始

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。

---

## 0. 背景与范围

- 本棒 4 任务之一：把 `scope: fp` 60 条从 ILLI 桩换成真实执行（拆分见 `QEMU-034t §0`）。
- 本任务实现 **位级语义**的 10 条（**不需要 softfloat**）：`sign` 4 + `classify` 2 + `compare` 4。全部可用 TCG 位运算 + 比较表达；期望值可逐位手算。
- 只改 `trans_fp.c.inc`（及必要时的 `helper.c`/`helper.h`，若实现者选择 helper 化 classify/compare，须在完成区披露）。

---

## 1. 事实核实（本轮 architect 实测）

### 1.1 现有桩（`trans_fp.c.inc` 由 `QEMU-034t` 建立后，本任务填充其中 10 条）
- `trans_arith.c.inc` 原桩：`ftsgnj/ftsgnn/fosgnj/fosgnn`（sign 4）、`ftcls/focls`（classify 2）、`ftqcmp/foqcmp`（qcmp 2）。
- `trans_compare.c.inc` 原桩：`ftscmp/foscmp`（scmp 2）。
- `QEMU-034t` 已把这 10 条搬入 `trans_fp.c.inc`，本任务只改该文件。

### 1.2 字段/编码（`contracts/opcodes.yaml`）
| 指令 | 格式 | 目的 | 源 |
|---|---|---|---|
| `ftsgnj/ftsgnn/fosgnj/fosgnn_orrr_rf` | orrr | `rfhb`=a->hb | `rfhc`=a->hc、`rfhd`=a->hd |
| `ftqcmp/ftscmp/foqcmp/foscmp_orrr_rf` | orrr | `rdhb`=a->hb | `rfhc`=a->hc、`rfhd`=a->hd |
| `ftcls/focls_orri_rf` | orri | `rdhb`=a->hb | `rfhc`=a->hc（起始）、`immu6`=a->hd（1–63） |

### 1.3 语义（`.tao/knowledge/contract-fp.md §7/§8/§9`；`spec/SimRISC-07 §浮点符号位操作指令 / §浮点比较指令 / §浮点分类指令`）
- **sign**：`sgnj = copySign(rfHC, rfHD)`（取 rfHC 除符号位外全部位，与 rfHD 符号位组合）；`sgnn` 用 **rfHD 符号位取反**。特例：`rfHD=rf0` ⇒ `sgnj=abs(rfHC)`、`sgnn=−abs(rfHC)`；`rfHC==rfHD` ⇒ `sgnj=copy`、`sgnn=negate`。`ft` 用符号位 bit31，`fo` 用 bit63。
- **classify**：对 ft（32 位）/fo（64 位）置位 `[9:0]`：0 negInf、1 negNormal、2 negSubnormal、3 negZero、4 posZero、5 posSubnormal、6 posNormal、7 posInf、8 sNaN、9 qNaN；`[63:10]` 清零；块形式 `immu6` 1–63 逐对递增、先读后写；`immu6==0` 或起始+`immu6>64` ⇒ ILLI。
- **compare**：`>`→1、`=`→0、`<`→−1；unordered：**Quiet Compare 返回 qNaN、Signaling Compare 返回 sNaN，符号位为 0**。结果写 rdHB（`rd` 组，不受 `dst_rf0` 约束）。`compare` 族**不置异常标志**（spec 未要求）。
- 三条族的目的：sign 目的 rf（⇒ `dst_rf0` 检查 `a->hb==0`）；classify/compare 目的 rd（无需检查）。

### 1.4 未明点（spec 开放，须按选定口径实现并记录）
- **`ft` 结果高 32 位**：spec「只使用低 32 位，高 32 位不做特殊规定」⇒ 本任务须固定一个口径（建议：sign 按**完整 64 位**做符号注入并保持非符号位；classify/compare 结果按 64 位整数写 rd）。`QEMU-034t §8-决策 3` 已请示用户；本任务沿用其裁定。
- **sNaN 的具体 payload**：spec 只说「Signaling Compare 结果为 sNaN，符号位为 0」，未给尾数 payload。建议取 **`0x7F800001`（ft）/`0x7FF0000000000001`（fo）**（符号 0、指数全 1、尾数最低位 1、MSB=0 ⇒ 确为 sNaN），并在完成区记录该选定。
- **NaN 检测与 qNaN/sNaN 区分**：按 IEEE754 位级判据（指数全 1：尾数 MSB=1 ⇒ qNaN；指数全 1 且尾数非 0、MSB=0 ⇒ sNaN）。

---

## 2. 设计

### 2.1 实现要点（`trans_fp.c.inc`）
- **sign（TCG）**：读取 `load_rf`（完整 64 位），按格式取符号位（ft bit31 / fo bit63），与 rfHC 的其余位组合；`sgnn` 取反 rfHD 符号位。**特例无需特判**（`rfHD=rf0` 的符号位为 0 自然给出 abs；`rfHC==rfHD` 自然给出 copy/negate）——须用探针证明。
  - 目的 rf0 ⇒ ILLI（`dst_rf0`）。
- **classify（TCG 或 helper）**：逐条按位提取符号/指数/尾数，判 10 类并映射为 `1<<k`；`[63:10]` 清零；块形式循环 `i` 递增、先读后写；起始/计数检查（`mreg_zero`/`mreg_range_overflow`）用 `QEMU-034t` 的 helper。
- **compare（TCG 或 helper）**：按格式判定 `>`/`=`/`<`；unordered 检测（任一方为 NaN）⇒ 写 qNaN（quiet）或 sNaN（signaling）常量。**qcmp 与 scmp 的唯一差异在 unordered 返回值**；其余（1/0/−1）相同。
  - 结果写 `store_rd(a->hb, …)`。
- 若 classify/compare 选择 helper 化：在 `helper.h` 加 `DEF_HELPER_*`，`helper.c` 实现（**不引入 softfloat**，纯位运算），并在完成区记录该选择与理由。

### 2.2 不改动
- 不动 `cpu.h`/`cpu.c`/`meson.build`/`insn.decode`；不动 `opcodes.yaml`；不加 FP 向量/lit。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `target/dadao/insn_trans/trans_fp.c.inc` | 10 条 stub → 真实实现 |
| 2 | `target/dadao/helper.h` / `helper.c` | **仅当** classify/compare helper 化时增声明/实现（否则不改） |
| 3 | `components/qemu/patches/**` + `series` | `make_patch qemu` 导出（预期**无新增**补丁，仍 32/69） |
| 4 | `components/qemu/changelog.md` | 追加一条 |
| 5 | `tools/qemu/min_rom_probe_035t.py` | 新建探针（§6.2） |
| 6 | `.work/evidence/QEMU-035t/run.sh` | 一键证据脚本（含 `--inject`） |
| 7 | `.work/log/qemu/QEMU-035t-*.log` | 构建/探针/回归完整输出 |

**明确不改**：`contracts/**`、`spec/**`、`tests/**`、`components/llvm-project/**`、`insn.decode`。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `contracts/opcodes.yaml`（10 条 id 的 `fields`/`op`/`ha`）
- `.tao/knowledge/contract-fp.md §7/§8/§9`、`spec/SimRISC-07 §浮点符号位操作指令 / §浮点比较指令 / §浮点分类指令`、`spec/SimRISC-00 §浮点寄存器`
- `QEMU-034t` 产出的 `trans_fp.c.inc`、`load_rf`/`store_rf`、legality helper、`tools/qemu/min_rom_probe_034t.py`

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围，越界须披露；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make prepare` + `make build-qemu`（**预计 2–5 分钟**；单 `.c.inc` 增量）。
- 临时目录 `/tmp/opencode/QEMU-035t/`；日志 `.work/log/qemu/`；证据 `.work/evidence/QEMU-035t/`。
- 补丁纪律同 `QEMU-034t §5`。

---

## 6. 验收标准（可执行、可失败，含反例注入）

1. **构建**：`make prepare && make build-qemu` EXIT 0（留日志）。
2. **探针全绿**：`python3 tools/qemu/min_rom_probe_035t.py` EXIT 0。用例至少覆盖：
   - **sign**：`sgnj` 正常组合（rfHC 正/负 × rfHD 正/负四象限）；`sgnn` 同四象限；`rfHD=rf0` ⇒ abs / −abs（特例）；`rfHC==rfHD` ⇒ copy / negate；`ft`（bit31）与 `fo`（bit63）各一组；目的 rf0 ⇒ ILLI 0x88。
   - **classify**：对 ft/fo 各构造 **10 类**输入（±Inf、±Normal、±Subnormal、±Zero、sNaN、qNaN）逐位置位且 `[63:10]=0`；块形式（如 `{rd4:rd6},{rf8:rf10}`）逐对结果；`immu6==0` ⇒ ILLI 0x88；起始+`immu6>64` ⇒ ILLI 0x88。
   - **compare**：`>`/`=`/`<` 三值；unordered 在 `ftqcmp`/`foqcmp` 返回 qNaN、`ftscmp`/`foscmp` 返回 sNaN（**符号位 0**，payload 与选定口径一致）；正常结果与 qcmp/scmp 无关。
   - **NaN 区分**：qNaN 与 sNaN 输入下 compare 表现一致（unordered），但返回值按指令类型区分。
3. **反例可失败（承重证明）**：至少注入并**重建**后 FAIL、还原后**重建**回绿：
   - (a) `sgnn` 漏取反符号位 ⇒ sign 用例 FAIL；
   - (b) `ft` 符号位误用 bit63 ⇒ ft sign/classify 用例 FAIL；
   - (c) classify 类位顺序错（如 negZero/posZero 互换）⇒ 对应用例 FAIL；
   - (d) `ftscmp` 复用 qcmp 的 qNaN 返回 ⇒ scmp unordered 用例 FAIL；
   - (e) 去掉 classify 的 `mreg_range_overflow` ⇒ 越界用例由 0x88 变其它。
   注入 `git diff --name-only` 非空；还原须**源码 + 重建**。
4. **不误伤 M1**：既有 M1 探针失败集与基线逐条一致；`_034t` 保持全绿。
5. **编码门控不回归**：`check_qemu_trans` `227/227 (M1 152/152)` EXIT 0。
6. **`make check` 全绿**：`check-qemu-semantics` 149、`check-lit` 29/29、`check-patch-tree` 69 OK、`check-scope`/`check-fp-contract` PASS。
7. **残留/越界/不变量**：`git status --untracked-files=all` 干净；`check-no-residue` PASS；`.work/source/qemu` base+1 干净；改动与 §3 对齐。

### 6.1 独立期望值来源
同上，10 条可**逐位手算**；期望值独立派生并写死探针，禁「跑 QEMU 反填期望」。qNaN/sNaN 常量按 §1.4 选定口径手算。

### 6.2 探针构造注意
同 `QEMU-034t §6.2`（分支双向验证、位宽回读校验、可达 FAIL 路径）。classify 的 10 类输入须各自独立构造（用 `set.zw`/`rd2rf`，不可只测「=0」）。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-035t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
7. 复杂命令输出留存 `.work/log/qemu/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/QEMU-035t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

1. **`ft` 高 32 位口径**（§1.4-未明）：须与 `QEMU-034t` 的裁定一致；请在 `034t` 一并拍板。
2. **sNaN payload 选定**（§1.4）：建议 `0x7F800001`/`0x7FF0000000000001`，请确认（不改 spec，仅在实现/探针中固定）。
3. **ADR**：延续「FP 不立 ADR」；本任务无新跨模块合约变更，**建议不立**（承 `QEMU-034t §8-决策 4`）。请用户确认。
4. helper 化 classify/compare 与否属实现选择，不涉合约，由 engineer 定并披露。

## 9. 与现有门控/不变量的关系

| 门控 | 期望变化 |
|---|---|
| `check_qemu_trans` | 不变 `227/227` |
| `check-qemu-semantics` | 不变 149 |
| `check-lit` | 不变 29/29 |
| `check-patch-tree` | 不变 **69**（无新增补丁） |
| `check-scope`/`check-fp-contract`/`validate-encoding` | 不变 PASS |
| 探针群 | 新增 `_035t`；M1 探针与 `_034t` 零新增失败 |

---

## 10. 后续衔接
`QEMU-036t`（softfloat 转换）、`QEMU-037t`（softfloat 算术）。本任务的 `load_rf`/`store_rf`/`store_rd`/legality helper 被后续复用。

## 完成区

**测试结果**：
（待填写）

**修改文件**：
（待填写）

**验收结果**：
（待填写）

**新发现/坑**：
（待填写）

**遗留问题**：
（待填写）

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）
