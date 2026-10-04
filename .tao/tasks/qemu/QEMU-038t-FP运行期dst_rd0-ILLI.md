# QEMU-038t: FP `dst_rd0` 运行期 ILLI（rd-目的 15 条）

**模块**：qemu
**项目里程碑**：M2
**依赖**：`LLVM-031t`（须先 `已验证`；见 §4.1 依赖说明）、`SPEC-089t`（FP 合法性 `dst_rd0` 回填，**已验证**）；相关先例 `QEMU-033t`（`mreg_range_overlap` 运行期 ILLI）、`QEMU-032t`（`ret rd0` 运行期 ILLI）、`QEMU-034t`–`037t`（FP 执行层 60/60）。
**状态**：待开始

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。
> **范围边界**：只做 **QEMU translate 期运行期 ILLI**（`gen_exception_illegal`，机器 fault 退出码 `0x88`）。**不含** LLVM 汇编期检查（`LLVM-031t`，串行其前）、**不含**向量/生成器（`TESTCASES-*`）、**不含**合约/生成物改动（`SPEC-089t` 已完成）。

---

## 0. 背景与本任务判断

`SPEC-089t`（`已验证`）已在**合约层**为 FP 的 **rd-目的 15 条指令**补 `dst_rd0`（用户裁定 R2b = (A) 全补 15 条）：

- `convert_f2i` 8：`ft2it`/`ft2io`/`ft2ut`/`ft2uo`/`fo2it`/`fo2io`/`fo2ut`/`fo2uo`（orri，目的 `rdhb`）
- `classify` 2：`ftcls`/`focls`（orri，目的 `rdhb`）
- `compare` 4：`ftqcmp`/`ftscmp`/`foqcmp`/`foscmp`（orrr，单目的 `rdhb`）
- `rf_move` 1：`rf2rd`（orri，目的 `rdhb`）

**但 QEMU 当前不检 `dst_rd0@FP`**（`SPEC-089t §1.6` 已确认）：`QEMU-034t`–`037t` 只做了 `dst_rf0`/`mreg_*`/`encode_fp_root_n` 的运行时检查，这 15 条目的为 `rd0` 时**不报 ILLI**、静默执行。⇒ **合约要求 ILLI，实现不报** ⇒ 必须补齐（**不得回退合约**）。

**判断（供用户确认）**：`dst_rd0` 是 `active` 规则，M1 侧运行期已由 `QEMU-032t`/`QEMU-033t` 体例落地（`trans_arith` 等处 `if (a->hb == 0) { gen_exception_illegal(ctx); return true; }`）；FP 侧按同一体例补 translate 期 ILLI。（若用户裁定 FP 运行期不检，本任务取消并登记遗留——**不得**改回合约。）

---

## 1. 事实核实（本轮 architect 实测；file:line 为 `.work/source/qemu/` 当前行号，执行时以重跑为准）

### 1.1 规则来源与逐条映射（Spec-first）
- `contracts/legality_rules.yaml` `dst_rd0`（`active`）：描述已由 `SPEC-089t` 扩写覆盖本次 15 条；`.tao/knowledge/contract-fp.md §3/§8/§9/§12/§15` 为叙述投影。
- `contracts/fp_semantics.yaml` 15 条 `legality_refs` 含 `dst_rd0`。
- `contracts/opcodes.yaml` 同 15 条 `rule_refs` 含 `dst_rd0`；实测 **`ha`/value**：`ft2it`=0x44/0x30、`ft2io`=0x31、`ft2ut`=0x32、`ft2uo`=0x33、`fo2it`=0x38、`fo2io`=0x39、`fo2ut`=0x3A、`fo2uo`=0x3B、`ftcls`=0x44/0x00、`focls`=0x08、`ftqcmp`=0x44/0x20、`ftscmp`=0x21、`foqcmp`=0x28、`foscmp`=0x29、`rf2rd`=0x40/0x3E（`ha` = bits[23:18]；`encode_orri(op,ha,hb,hc,hd)`）。

### 1.2 `trans_fp.c.inc` 结构（源 968 行；15 条 trans 的分布）
| 族 | trans | 行 | 目的字段 | 备注 |
|---|---|---|---|---|
| `convert_f2i` 8 | `trans_{ft2it,ft2io,ft2ut,ft2uo,fo2it,fo2io,fo2ut,fo2uo}_orri_rf` | L757–795 | `a->hb`（rd 起始） | 8 条均 `return gen_convert_f2i(ctx, a, KIND)` |
| `classify` 2 | `trans_ftcls_orri_rf`/`trans_focls_orri_rf` | L547–573 | `a->hb`（rd 起始） | 各有独立函数体 |
| `compare` 4 | `trans_{ftqcmp,ftscmp,foqcmp,foscmp}_orrr_rf` | L946–968 | `a->hb`（rd） | 4 条均 `gen_fp_cmp(a, isdbl, nan_const)` |
| `rf_move` 1 | `trans_rf2rd_orri_rf` | L434–448 | `a->hb`（rd 起始） | 既有 `fp_check_mreg` |

### 1.3 现有 FP 合法性 helper 与先例
- `fp_check_dst_rf0(ctx, rfidx)`（L33–40）：`rfidx==0 ⇒ gen_exception_illegal + return false`。
- `fp_check_mreg(ctx, start, count)`（L46–53）：`count==0 || start+count>64 ⇒ ILLI`。
- `gen_convert_f2i`（L636–651）：先 `fp_check_mreg(ctx, a->hb, a->hd)`（目的 rdHB）再 `fp_check_mreg(ctx, a->hc, a->hd)`（源 rfHC），循环 `store_rd(a->hb+i, ...)`。
- `gen_fp_cmp`（L246–310，返回 `void`）：末尾 `store_rd(a->hb, res)`；4 个 `trans_*_cmp` 直接调用它——**无 ctx、无返回值**，故 `dst_rd0` 检查须在 4 个 trans 包装处（或改 `gen_fp_cmp` 签名，见 §2.1）。
- M1 先例：`trans_arith.c.inc` 等处 `if (a->hb == 0) { gen_exception_illegal(ctx); return true; }`。
- 探针体例：`tools/qemu/min_rom_probe_034t.py`–`_037t.py`（`_probe_artifact_dir()` → `.dadao/tests/probes/`；`-d cpu` 回读 / fault 退出码 / E2E exit-port 三通道；`--selftest`；`.work/evidence/<ID>/run.sh` 含 `--inject`）。

### 1.4 基线（须在执行时复测记录）
- 补丁 **69**（llvm 37 + qemu 32）；`check_qemu_trans` **227/227 (M1 152/152)**；`make check-lit` 29/29（`LLVM-031t` 后应为 30/30）。
- FP 探针群 `_034t` 59/59、`_035t` 77/77、`_036t` 113/113、`_037t` 91/91；M1 探针（`_005t`…`_033t`）已知 pre-existing 失败仅 `min_rom_probe_008t`/`_013t` 的既有失败集。

---

## 2. 设计（全部在 `trans_fp.c.inc`）

### 2.1 新增 helper `fp_check_dst_rd0`
在 `fp_check_dst_rf0` 附近新增：

```c
/* dst_rd0 (SPEC-089t): the FP rd-destination forms (convert_f2i 8, classify 2,
 * compare 4, rf2rd 1) must not write rd0 (the hard-wired zero register).
 * rf0 as a *source* is unaffected; rd2rf's destination is RF and is not
 * checked here. */
static bool fp_check_dst_rd0(DisasContext *ctx, int rdstart)
{
    if (rdstart == 0) {
        gen_exception_illegal(ctx);
        return false;
    }
    return true;
}
```

### 2.2 逐族插入检查（目的起始寄存器统一为 `a->hb`）
1. **convert_f2i（8 条，共用 `gen_convert_f2i`）**：在函数体开头（`fp_check_mreg` 之前）加
   `if (!fp_check_dst_rd0(ctx, a->hb)) { return true; }`。
2. **classify（2 条）**：在 `trans_ftcls_orri_rf` 与 `trans_focls_orri_rf` 函数体开头各加
   `if (!fp_check_dst_rd0(ctx, a->hb)) { return true; }`。
3. **compare（4 条）**：`gen_fp_cmp` 返回 `void`，故在 4 个 `trans_{ftqcmp,ftscmp,foqcmp,foscmp}_orrr_rf` 包装开头各加同一检查（在调用 `gen_fp_cmp` 之前）。**不**改 `gen_fp_cmp` 签名（最小改动；如需可改，属实现选择，但须保持 4 条一致）。
4. **rf2rd（1 条）**：在 `trans_rf2rd_orri_rf` 函数体开头加
   `if (!fp_check_dst_rd0(ctx, a->hb)) { return true; }`。

> **顺序**：`dst_rd0` 检查置于各族既有 `fp_check_mreg` 之前（规则名优先；`a->hb==0, count==1` 仅 `dst_rd0` 触达，无相互抵消）。**不**改 `dst_rf0`/`mreg_*`/root-n 既有检查。
> **不误伤**：`rd1` 等非 0 目的照常执行；`rd2rf`（RF 目的）、`ft2it {rd1}, {rf0}`（rf0 源）不受影响。

### 2.3 探针（新建 `tools/qemu/min_rom_probe_038t.py`）
- **hand-encode**（独立 oracle，不经 LLVM）：编码取自 `contracts/opcodes.yaml`（`ha`/value 见 §1.1）；复用 `encode_orri` + `set_zw_rd`/`or_w_rd`/`rd2rf`/`rf2rd` 等 trusted M1 helper。
- **反例（rd0 目的，期望 fault `0x88`）**：15 条各 1 例（`ft2it(0,…)`…`foscmp(0,…)`、`rf2rd(0,…)`）+ 3 条多寄存器组（`ft2it {rd0:rd2}`、`ftcls {rd0:rd2}`、`rf2rd {rd0:rd2}`）。
- **正例对照（非 rd0，期望**不**fault，退出 `0x00`）**：15 条各 1 例（`rd1` 目的）；证明检查**只**针对 `rd0`、不过宽。
- **E2E 对照（≥2 条）**：非 rd0 目的执行后经 exit-port 断言结果（如 `rf2rd rd1, rf4` 值回读、`ftqcmp rd1, rf2, rf3`），证明 `dst_rd0` 检查不破坏正常执行路径。
- **通道**：fault 用进程退出码；值用 `-d cpu` 最后一条 `RF[]/RD[]` dump；E2E 用 ROM 内比较 + exit-port。
- **FAIL 路径可达**：fault 用例用「body + PASS 收尾」的 ROM（`build_fault_rom` 体例）——若未 fault 则写 exit `0x00` ≠ 期望 `0x88` ⇒ FAIL；正例用同一收尾（不 fault ⇒ 退出 `0`）。
- **产物落点**：`_probe_artifact_dir()`（`.dadao/tests/probes/`，D6 合规）。
- 探针须打印 `Main: N/N passed, 0 failed` 并附 `--selftest`（证明 RF/RD 值比较、fault 退出码、E2E 断言三类均有可达 FAIL 路径）。

### 2.4 补丁纪律（**不新增补丁**）
- 只改**既有** `components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`（当前 974 行）；补丁总数**仍 69**（llvm 37 + qemu 32），`check-patch-tree` 仍 `2 component(s), 69 patches OK`。
- 按 `spec/Process-01 §6/§8` E1–E8：动组件前 `make check-source-state`（E1：`.work/source/qemu` clean + HEAD=base+1）；E3 补丁写 `/tmp`、非空 blob；E4 收敛为恰好 1 commit；E6 `check-patch-tree` 断言⑦⑧⑨+⑥；E7 改动前后各查一次 `--source-state`；E8 裸 `git diff`。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch` | 加 `fp_check_dst_rd0` + 15 条检查（**不新增补丁**） |
| 2 | `tools/qemu/min_rom_probe_038t.py` | 新建探针（可复用检查器，随产物入库） |
| 3 | `components/qemu/changelog.md` | 追加本任务行 |
| 4 | `.work/evidence/QEMU-038t/run.sh` | 一键证据脚本（含 `--inject`） |
| 5 | `.work/log/qemu/QEMU-038t-*.log` | 构建/探针/门控/注入完整输出 |

**明确不改**：`contracts/**`、`spec/**`、`tests/vectors/**`、`components/llvm-project/**`、`tests/lit/**`、`helper.c`/`helper.h`、`check_qemu_trans.py`。

## 4. 执行环境
**执行环境**：本地

### 4.1 依赖说明（与 `LLVM-031t` 串行；`QEMU-038t` 依赖 `LLVM-031t` 先 `已验证`）
- **写法**：`**依赖**：LLVM-031t（须先 已验证）`。理由：① `AGENTS.md`「长构建一次只跑一个」「避免同工作树并发 `make check`/构建污染证据」——`LLVM-031t` 需 `make build-mc`，本任务需 `make build-qemu`，且共用 `make check` 门控，并行会互相污染证据；② 同一 15 条两侧检查，先汇编期（LLVM）后运行期（QEMU），逐条对照便于审计与文档一致性。
- **性质**：**非功能硬前置**——本任务探针 hand-encode，不依赖 `llvm-mc`；串行是为**构建/证据纪律**与**顺序可审计**，不是能力依赖。故若用户明确要求并行，仅需保证两者不同时执行构建/`make check`；否则一律串行。

## 5. 接口规范

### 输入
- `components/qemu/patches/.../trans_fp.c.inc.patch`（`QEMU-037t` 后版本，源 968 行）。
- `contracts/legality_rules.yaml`（`dst_rd0`）、`contracts/fp_semantics.yaml`（15 条）、`contracts/opcodes.yaml`（编码）、`.tao/knowledge/contract-fp.md §3/§8/§9/§12/§15`。
- 先例：`tools/qemu/min_rom_probe_034t.py`–`_037t.py`、`.work/evidence/QEMU-037t/run.sh`。

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make build-qemu`（增量，预计 **5–20 分钟**；`JOBS=8`，禁全核并行）。`--inject` 若做多轮单点注入，每轮一次增量重建，**先申报**。
- 临时目录 `/tmp/opencode/QEMU-038t/`；日志 `.work/log/qemu/`；证据 `.work/evidence/QEMU-038t/`。
- **Spec-first**：15 条清单以 `fp_semantics.yaml` 的 `legality_refs` 含 `dst_rd0` 为准，**不从 QEMU 现有实现反推**；探针期望值为 hand-derive 的 ILLI 语义（本任务无值计算期望）。

---

## 6. 验收标准（可执行、可失败、含反例注入）

> 通用：完成区贴**真实命令输出与退出码**；被检命令自身退出码须显式捕获（`cmd > log 2>&1; rc=$?`，**禁** `cmd | tee log` 后取 `$?`）；复杂命令留 `.work/log/qemu/`；engineer 交付一键证据脚本 `.work/evidence/QEMU-038t/run.sh`（非交互、任一失败即非零退出、逐项打印「检查名 + 期望/实际 + 退出码」、内置 `--inject`）。

1. **构建**：`make build-qemu` EXIT 0（留 `QEMU-038t-build.log`）。
2. **探针**：`python3 tools/qemu/min_rom_probe_038t.py` → 全 PASS（15 rd0 fault + 15 非 rd0 对照 + ≥3 多寄存器 + ≥2 E2E）；`--selftest` → 三类断言 FAIL 路径均可检出（EXIT 0）。
3. **反例硬报错**：15 条 rd0 目的均退出 `0x88`；**非 rd0 对照**均退出 `0x00`（不过宽）。
4. **编译回归**：`check_qemu_trans` **227/227 (M1 152/152)**；`make check` EXIT=0（`check-patch-tree` **69**、`check-lit` **30/30**（`LLVM-031t` 后）、`check-interface` 80/80、`check-qemu-semantics` PASS、`check-no-residue` PASS）。
5. **FP 探针群 + M1 探针零新增失败**：`_034t` 59/59、`_035t` 77/77、`_036t` 113/113、`_037t` 91/91 逐字节 IDENTICAL；M1 探针（`_005t`…`_033t`）失败集与**改前基线**逐条一致（仅 `_008t`/`_013t` 既有 pre-existing 失败），零新增。
6. **反例可失败（承重，独立归因）**：见 §6.1；注入须 `git diff --name-only` 非空；还原**含重建**、源码/二进制 sha 复原后回绿。
7. **残留与越界**：`git status --untracked-files=all` 仅应改文件 + 本任务书 + 新探针；`check-no-residue` PASS；补丁数仍 **69**。
8. **不变量**：`contracts/**`/`spec/**`/`tests/vectors/**`/`components/llvm-project/**`/`tests/lit/**` **零改动**；`helper.c/.h`、`check_qemu_trans.py` 零改动；`.work/source/qemu` base+1 clean（E1）。

### 6.1 反例注入（逐条真实 FAIL→还原→回绿，**独立归因**、避免互相抵消）
- **(a) convert_f2i**：令 `fp_check_dst_rd0` 在 `gen_convert_f2i` 处失效（或仅注释该调用）⇒ 8 条 `ft2it..fo2uo` rd0 用例 + `ft2it {rd0:rd2}` **停止 fault（退出 0）**，其余族仍 `0x88`。
- **(b) classify**：仅失效 `trans_ftcls_orri_rf`/`trans_focls_orri_rf` 两处 ⇒ 仅 `ftcls/focls` rd0 用例（含组）停止 fault。
- **(c) compare**：仅失效 4 个 `trans_*_cmp` 包装处 ⇒ 仅 `ftqcmp/ftscmp/foqcmp/foscmp` rd0 用例停止 fault。
- **(d) rf2rd**：仅失效 `trans_rf2rd_orri_rf` 处 ⇒ 仅 `rf2rd` rd0 用例（含组）停止 fault。
- **要求**：`--inject` 须**逐族单点**执行 (a)–(d)（每族：改单点 → 重建 → 跑探针 → 断言**该族**用例 FAIL 且**其余族 + 非 rd0 对照**仍 PASS → 还原），以证明每族检查各自承重、无跨族抵消；末轮还原重建后探针全绿。注入须 `git diff --name-only` 非空；还原后源码/二进制 sha256 复原并回绿。
- **成本控制**：若逐族 4 轮重建成本过高，可先申报并经用户同意后改为「一次合并 4 点注入（1 次重建）+ 至少 1 轮单族单点注入（证明无抵消）」；但**单族单点注入不可省**（防「多注入互相抵消」，参 `QEMU-035t` 教训）。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-038t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. **补丁导出纪律**（`spec/Process-01 §6/§8` E1–E8）：动组件前 `make check-source-state` 自检 E1；E2 起点不干净先收敛；E3 导出前校验 E1、补丁写 `/tmp`、非空 blob、无 0 行/空 hunk；E4 收敛为恰好 1 commit；E5 `apply_series` 幂等；E6 `check-patch-tree` 断言⑦⑧⑨+⑥；E7 改动前后各查一次 `--source-state`；E8 补丁为裸 `git diff`。
7. 复杂命令输出留存 `.work/log/qemu/`（捕获被检命令自身退出码）。
8. 一键证据脚本：engineer 产 `.work/evidence/QEMU-038t/run.sh` 并跑通；reviewer 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

1. **是否需要 FP 运行期 `dst_rd0` 检查**：本任务建议实现（§0）。若用户裁定只在 LLVM 侧，本任务取消并登记遗留（**不得**回退合约）。
2. **注入轮数/成本**：§6.1 逐族 4 轮单点重建 vs 合并 1 轮 + 单族 1 轮——默认逐族单点（最稳）；如成本敏感须**用户拍板**。
3. **`gen_fp_cmp` 签名**：默认不改（在 4 个 trans 包装处检查）；若 engineer 改为 `gen_fp_cmp` 收 `ctx` 并返回 `bool`，属等价的实现选择，但须 4 条一致且探针覆盖不变。
4. **`{rd0:rd2}` 多寄存器组**：目的起始 `rd0` ⇒ ILLI（覆盖）；engineer 须实测。
5. **与 `mreg_range_overflow` 组合非法**：`{rd0:rd63}` 同时触两规则，报哪一个取决于检查顺序；本任务反例**不**依赖该组合，确保单独触达 `dst_rd0`。
6. **串行**：见 §4.1。

## 9. ADR 判断（须主动提醒）
- **建议：不立 ADR**（与 `SPEC-089t` 及 FP 系列此前裁定一致）。理由：本任务是**机械落地** `SPEC-089t` 已 `Accepted`/已 `active` 的合约事实（`dst_rd0@FP`），属既有规则框架内的实现棒（先例 `QEMU-032t`/`QEMU-033t` 均未立 ADR），非新架构决策、无多方案分歧、无跨组件合约变更。判据（`spec/Process-03`：高代价/跨模块/多方案/外部契约/结论固化/定位）均不满足新增门槛。

## 10. 范围边界与后续
- **不在本棒**：LLVM 汇编期检查（`LLVM-031t`，串行其前）；FP 向量/独立 oracle（`TESTCASES-*`/`GOLDEN-*`）；FP E2E（`INTEG-*`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
