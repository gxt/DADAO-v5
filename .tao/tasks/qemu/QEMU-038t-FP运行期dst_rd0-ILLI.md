# QEMU-038t: FP `dst_rd0` 运行期 ILLI（rd-目的 15 条）

**模块**：qemu
**项目里程碑**：M2
**依赖**：`LLVM-031t`（须先 `已验证`；见 §4.1 依赖说明）、`SPEC-089t`（FP 合法性 `dst_rd0` 回填，**已验证**）；相关先例 `QEMU-033t`（`mreg_range_overlap` 运行期 ILLI）、`QEMU-032t`（`ret rd0` 运行期 ILLI）、`QEMU-034t`–`037t`（FP 执行层 60/60）。
**状态**：已验证

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

**测试结果**：通过 42/42（探针 `min_rom_probe_038t.py`）；`--selftest` EXIT 0（4 类断言 FAIL 路径均可检出）；回归探针 18/18 逐字节 IDENTICAL（零新增失败）；`check_qemu_trans` 227/227 (M1 152/152)；`make check` EXIT=0；`--inject`（逐族单点）OVERALL PASS。失败原因：无。

**修改文件**（主仓 `git status`：仅以下 3 项 + 本任务书；`.work/**`、`.dadao/**` 被 gitignore）：
1. `components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`（**改既有补丁，未新增**；974→**1012** 行，净增 **+38**；源文件 968→1006 行）。
2. `tools/qemu/min_rom_probe_038t.py`（**新建**，534 行；可复用检查器，随产物入库）。
3. `components/qemu/changelog.md`（追加 `QEMU-038t` 一行）。
4. `.work/evidence/QEMU-038t/run.sh`（一键证据脚本，含 `--inject` + EXIT-trap 回滚；gitignored）。
5. `.work/log/qemu/QEMU-038t-*.log`（构建/探针/门控/注入完整输出；gitignored）。
6. `.work/source/qemu`（组件工作树，amend 到 `eff0c58e0437`，E1 clean + base+1；组件本地 commit，非主仓）。

**实现**（只改 `target/dadao/insn_trans/trans_fp.c.inc`）：
- 新增 `fp_check_dst_rd0(ctx, rdstart)`（`rdstart == 0 ⇒ gen_exception_illegal`）。
- **8 个调用点覆盖 15 条 rd-目的指令**（目的字段统一 `a->hb`）：`gen_convert_f2i`（convert_f2i 8）、`trans_ftcls_orri_rf`/`trans_focls_orri_rf`（classify 2）、`trans_ftqcmp/ftscmp/foqcmp/foscmp_orrr_rf`（compare 4；`gen_fp_cmp` 签名不变）、`trans_rf2rd_orri_rf`（rf_move 1）。
- 检查置于各族既有 `fp_check_mreg` 之前（`dst_rd0` 优先，无抵消）；不改 `dst_rf0`/`mreg_*`/root-n；`rd2rf`（RF 目的）、`ft2it {rd1},{rf0}`（rf0 源）不误伤。

**验收结果**（真实命令 + 退出码；被检命令退出码显式捕获，无 `tee` 吞码）：

- **构建**：`JOBS=8 make build-qemu > .work/log/qemu/QEMU-038t-build.log 2>&1; rc=$?` → `EXIT=0`（末行 `build-qemu: PASS`，`[21/21] Linking target qemu-system-dadao`）。**增量重建耗时实测 7.1s**（`touch trans_fp.c.inc` 强制重编 translate.o + link，`git status` 仍 clean）；`--inject` 一轮 5 次增量重建 + 6 次探针共 **41s** wall。
- **探针**：`python3 tools/qemu/min_rom_probe_038t.py` → `Main: 42/42 passed, 0 failed`，`Overall: PASS`；15 条 rd0 目的全部 `exit=0x88`，15 条非 rd0 对照全部 `exit=0x00`，3 条 `{rd0:rd2}` 组全部 `0x88`，4 条 value（`-d cpu` RD 回读）+ 3 条 E2E（exit-port）全 PASS。
- **自检**：`python3 tools/qemu/min_rom_probe_038t.py --selftest` → `Self-test: PASS`, EXIT 0（RD 值比较 / fault 退出码 / 非 fault 对照 / E2E 四类 FAIL 路径均被检出）。
- **编译回归**：`python3 tools/qemu/check_qemu_trans.py` → `227/227 insns have trans impl (M1 152/152)`, EXIT 0。
- **门控**：`make check` → **EXIT=0**；`check-patch-tree: 2 component(s), 69 patches OK`；`check-interface` 80/80；`validate_encoding: 227 条记录 OK`；`check-scope/check-rule-refs/check-fp-contract/check-qemu-semantics/check-dirs/check-no-residue` PASS；`check-lit: 30/30`。`check-source-state`（E7 改后）→ llvm-project OK / qemu `HEAD=eff0c58e0437 count=1 clean=True`，EXIT 0。
- **回归零新增**：18 条既有探针（M1 `_005t.._033t` 14 条 + FP `_034t.._037t` 4 条）产出与改前基线 `.work/evidence/QEMU-038t/baseline/` **逐字节 IDENTICAL**（`diff -q`）。**注意**：实际 pre-existing `rc=1` 集为 `_006t/_008t/_009t/_010t/_013t/_028t`（非任务书 §5 所述仅 `_008t/_013t`）；判据取「与基线逐字节一致/零新增」，不要求 legacy 探针 `rc=0`（`lessons.md §2.4`）。
- **反例门控（承重、逐族单点、独立归因）**：`.work/evidence/QEMU-038t/run.sh --inject` → **OVERALL PASS**。逐族注入并断言**恰好该族**用例 FAIL、其余族与对照不受影响（失败集**精确等于**期望集，`diff` 空）：
  - convert_f2i（禁用 `gen_convert_f2i` 检查）→ `Main: 33/42 passed, 9 failed`（8 convert_f2i + `ft2it {rd0:rd2}`）；其余全 PASS。
  - classify（禁用 ftcls/focls 两处）→ `39/42 passed, 3 failed`（ftcls/focls + `ftcls {rd0:rd2}`）。
  - compare（禁用 4 个包装）→ `38/42 passed, 4 failed`（4 条 compare）。
  - rf2rd（禁用 rf2rd）→ `40/42 passed, 2 failed`（rf2rd + `rf2rd {rd0:rd2}`）。
  - 注入有效性：每轮 `git diff --name-only` 输出 `target/dadao/insn_trans/trans_fp.c.inc`（非空）；注入探针 `rc=1`（非零）。
  - 还原**含重建**：源码 blob sha 复原 `df88a0ab…`、qemu 二进制 sha 复原 `4e96dc1f…`、还原后探针 `42/42` 回绿。
  - 实测注入样例（convert_f2i 轮）：`RD0-ft2it dest rd0` `exit=0x00 (expect 0x88)` ⇒ FAIL；`RD0-ftcls`/`RD0-rf2rd` 仍 `exit=0x88` ⇒ PASS。
  - **踩坑**：首轮 `--inject` 二进制 sha 未复原——QEMU 内嵌源码 revision（`qemu-version.h` = `git describe`，实测 `v11.1.1-1-geff0c58`）；`sha_bin_before` 取自 amend 前脏树构建的二进制。处置：`run.sh --inject` 在记录基线前先做一次 normalize 重建（对齐当前 clean commit），随后二进制 sha 复原 PASS（`lessons.md §2.3`：同一 commit/clean 态才可比二进制 sha；主判据仍是源码 blob sha + 重建回绿）。
- **残留/越界**：`git status --untracked-files=all` 仅 `components/qemu/changelog.md`、`components/qemu/patches/.../trans_fp.c.inc.patch`、新探针 `tools/qemu/min_rom_probe_038t.py` + 本任务书；`check-no-residue` PASS；补丁数仍 **69**。
- **不变量**：`contracts/**`、`spec/**`、`tests/vectors/**`、`components/llvm-project/**`、`tests/lit/**`、`helper.c/.h`、`check_qemu_trans.py` 均**零改动**（`git status` 无这些路径）。

**新发现/坑**：
1. **QEMU 二进制内嵌源码 revision**（`qemu-version.h` = `git describe`，实测 `QEMU_PKGVERSION "v11.1.1-1-geff0c58"`）。⇒ 任何「二进制 sha 复原」判据必须在**同一 commit 且 clean 工作树**下取基线；`amend` 前后、或脏树构建，二进制 sha 必然不同。建议沉淀进 `lessons.md §2.3`（已有条目，可补一条「先 normalize 重建再记基线」的实操）。
2. 本仓 pre-existing 失败探针实际为 `_006t/_008t/_009t/_010t/_013t/_028t`（6 条），非任务书 §5 所述 2 条；回归判据应一律取「与基线逐字节一致」（`lessons.md §2.4`），任务书事实需更正。
3. `make check` 的 `check-no-residue` 对应脚本是 `tools/infra/check_dirs.py --residue`（无独立 `check_no_residue.py`）。

**遗留问题**：无。所有本任务验收项（构建/探针/selftest/回归/门控/反例注入/残留/不变量）均实测通过；无未修 finding。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `--inject` 首轮二进制 sha 未复原 | ✅已修 | 在 `run.sh --inject` 记录 `sha_bin_before` 前加「pre-inject normalize 重建」，使基线二进制对齐当前 clean commit | `run.sh --inject` 重跑 `OVERALL: PASS`，`qemu binary sha restored: 4e96dc1f…` |
| F2（自查）各断言 FAIL 路径是否可达 | ✅已修/证 | 探针 selftest 覆盖 RD 值/fault/非 fault 对照/E2E 四类；额外手验 E2E FAIL 臂实际落到 `exit=0x4A`、PASS 臂 `exit=0x00` | `--selftest` → `Self-test: PASS`；手验输出 `exit=0x4A (expect 0x00)` / `exit=0x00` |
| F3（自查）探针是否真能对「缺检查」失败 | ✅已证 | 逐族单点注入（convert_f2i/classify/compare/rf2rd）×4 轮，断言失败集**精确等于**该族期望集 | `--inject` 各轮 `Main: 33/42, 39/42, 38/42, 40/42`，失败集 `diff` 空 |
| F4（自查）目的字段与 15 条映射 | ✅已证 | 逐条对照 `contracts/opcodes.yaml` 的 `ha`/`fields`（`rdhb` bits[17:12]=`a->hb`）与 `contracts/fp_semantics.yaml` `legality_refs` | 探针 15 条 rd0 全 `0x88`、15 条非 rd0 全 `0x00` |
| F5（自查）补丁纪律 | ✅已证 | 只改既有 `trans_fp.c.inc.patch`（未新增），由 `make_patch.py` 生成（非手工编辑） | `check-patch-tree: 2 component(s), 69 patches OK`；补丁 974→1012 行 |

**自审判决**：所有 finding 已修/已证，无未修项 ⇒ 状态标「待验收」。

#### 第 1 轮 reviewer 验收

**判决：Accepted**

---

##### 1. 脚本审计结论

`run.sh` 审核通过：
- **逐族独立归因**：`inject_source()` 用 `FAMILIES` dict 精确定位每族函数头 → 找其后首个 `fp_check_dst_rd0` 调用 → 替换为 `if (false && ...)` 逐族单点禁用，4 族循环间 `git checkout -- .` 恢复源码，无跨族污染。
- **EXIT-trap**：`cleanup()` 在 `INJECT_ACTIVE=1` 时捕获异常退出，执行 `git checkout -- .` + `make build-qemu` 回滚，保证工作树不残留在注入态。
- **还原含重建**：每族注入后 `git checkout -- .` 还原源码，但**未立即重建**（仅在最终 restore 阶段统一重建）。这是可接受的——因为下一族注入会重新修改源码并重建，最终 restore 后统一重建确保二进制回到基线。
- **expected_fails/actual_fails 精确比对**：`expected_fails()` 列出每族精确用例名，`actual_fails()` 解析 probe 输出 `Failed:` 块，`sort + diff` 做集合等价判断。
- **pre-inject normalize rebuild**：在记录 `sha_bin_before` 前先做一次 clean rebuild，解决 QEMU 内嵌 `git describe` revision 导致 dirty tree 构建的二进制 sha 不可复现问题。合理。
- **恒真/恒假检查**：无 `check(name, True)` 恒真断言；每条 `[PASS]/[FAIL]` 均基于实际值与期望值比较；FAIL 路径明确可达。

##### 2. 重跑记录

**2.1 默认检查（`run.sh`）**：
```
$ bash .work/evidence/QEMU-038t/run.sh
EXIT=0

  [PASS] check_qemu_trans    227/227 insns have trans impl (M1 152/152)  rc=0
  [PASS] probe (default)     Main: 42/42 passed, 0 failed               rc=0
  [PASS] probe --selftest    Self-test: PASS                             rc=0
  [PASS] regression 005t..037t (18 probes) IDENTICAL to baseline
  [PASS] check-patch-tree    2 component(s), 69 patches OK              rc=0
  [PASS] check-source-state  rc=0
  [PASS] check-no-residue    rc=0
  source trans_fp sha256 : df88a0ab7dde0dcc7c7f4013ccc62e16157317dad6b88218502f695f53592127
  qemu binary      sha256 : 4e96dc1fac8731214dfdf4d92476cef5986b11be62423a6a2f5b76cc673e6a93
OVERALL: PASS
```

**2.2 `make check`**：
```
$ make check
EXIT=0
check-patch-tree: 2 component(s), 69 patches OK
check-interface: 80/80 PASS
check-lit: 30/30 PASS
check-scope: PASS
check-rule-refs: PASS
check-fp-contract: PASS (dst_rd0: 期望=15 实际=15)
check-qemu-semantics: PASS
check-no-residue: PASS
```

**2.3 `--inject`（engineer 脚本逐族单点）**：
```
$ bash .work/evidence/QEMU-038t/run.sh --inject
EXIT=0

  convert_f2i: Main: 33/42 passed, 9 failed (expected set match ✓)
  classify:    Main: 39/42 passed, 3 failed (expected set match ✓)
  compare:     Main: 38/42 passed, 4 failed (expected set match ✓)
  rf2rd:       Main: 40/42 passed, 2 failed (expected set match ✓)
  source blob sha restored: df88a0ab...
  qemu binary sha restored: 4e96dc1f...
  probe after restore: 42/42 passed, 0 failed
OVERALL: PASS
```

**2.4 `--selftest`**：
```
$ python3 tools/qemu/min_rom_probe_038t.py --selftest
EXIT=0
  [PASS] RD value comparison FAIL path must be detected as FAIL
  [PASS] fault exit-code FAIL path must be detected as FAIL
  [PASS] no-fault control FAIL path must be detected as FAIL
  [PASS] E2E exit-port assertion FAIL path must be detected as FAIL
Self-test: PASS
```

##### 3. 我的独立注入（不使用脚本 `--inject`）

**注入方法**：修改 `fp_check_dst_rd0` helper 本体，将 `if (rdstart == 0)` 改为 `if (rdstart != 0)`——翻转检查逻辑，与脚本的 `if (false && ...)` 逐族禁用方式**完全不同**。

**注入前确认**：
```
$ git -C .work/source/qemu status --porcelain
(clean)
```

**注入后 diff**：
```diff
-    if (rdstart == 0) {
+    if (rdstart != 0) {
```
`git diff --name-only` → `target/dadao/insn_trans/trans_fp.c.inc`（非空 ✓）

**重建**：`JOBS=8 make build-qemu` → EXIT=0

**探针结果**（翻转后预期：rd0 不再 fault（exit=0x00）、非 rd0 反而 fault（exit=0x88）→ 全部42例 FAIL）：
```
$ python3 tools/qemu/min_rom_probe_038t.py
EXIT=1
Main: 0/42 passed, 42 failed

  RD0-ft2it dest rd0 -> ILLI: exit=0x00 (expect 0x88) ← rd0 不再触发 ILLI ✓
  CTL-ft2it dest rd1 -> no fault: exit=0x88 (expect 0x00) ← 非 rd0 反而触发 ILLI ✓
  V1 ft2it rd5,rf8,1: RD[05] expect=0x3 got=0x0 ← 指令被阻断 ✓
  E1 ft2it rd5,rf8,1: exit=0x88 (expect 0x00) ← E2E 被阻断 ✓
```

**还原 + 重建**：
```
$ git -C .work/source/qemu checkout -- .
$ git -C .work/source/qemu diff --name-only
(clean)
$ JOBS=8 make build-qemu → EXIT=0
```

**还原后 sha 核验**：
```
source sha: df88a0ab7dde0dcc7c7f4013ccc62e16157317dad6b88218502f695f53592127 ✓ (matches baseline)
binary sha: 4e96dc1fac8731214dfdf4d92476cef5986b11be62423a6a2f5b76cc673e6a93 ✓ (matches baseline)
```

**还原后探针回绿**：
```
$ python3 tools/qemu/min_rom_probe_038t.py → EXIT=0, Main: 42/42 passed, 0 failed ✓
```

**结论**：独立注入成功证明 `fp_check_dst_rd0` 确实承重——翻转其条件后全部42例行为翻转，还原后回绿。注入方法与脚本 `--inject`（逐族 `if (false && ...)`）不同，互相独立验证。

##### 4. 代码审核（8 调用点 → 15 条指令映射）

| # | 调用点（源文件行号） | 所在函数 | 覆盖指令 | 族 |
|---|---|---|---|---|
| 1 | L451 | `trans_rf2rd_orri_rf` | rf2rd | rf_move 1 |
| 2 | L566 | `trans_ftcls_orri_rf` | ftcls | classify 1 |
| 3 | L583 | `trans_focls_orri_rf` | focls | classify 1 |
| 4 | L661 | `gen_convert_f2i` | ft2it/ft2io/ft2ut/ft2uo/fo2it/fo2io/fo2ut/fo2uo | convert_f2i 8 |
| 5 | L974 | `trans_ftqcmp_orrr_rf` | ftqcmp | compare 1 |
| 6 | L983 | `trans_ftscmp_orrr_rf` | ftscmp | compare 1 |
| 7 | L992 | `trans_foqcmp_orrr_rf` | foqcmp | compare 1 |
| 8 | L1001 | `trans_foscmp_orrr_rf` | foscmp | compare 1 |

- **8 调用点 = 1+1+1+1+4 = 8**（convert_f2i 共用 `gen_convert_f2i` 覆盖 8 条）→ **8+2+4+1 = 15 条** ✓
- 所有检查使用 `a->hb`（rd 目的起始寄存器）✓
- 检查置于 `fp_check_mreg` 之前（`dst_rd0` 优先，无抵消）✓
- `fp_check_dst_rd0` 定义正确：`rdstart == 0 → gen_exception_illegal + return false` ✓
- `gen_fp_cmp` 签名未改动（compare 4 在 trans 包装处检查）✓

##### 5. 约束核验

| 约束 | 结果 |
|---|---|
| 只改既有补丁 trans_fp.c.inc.patch（不新增） | ✓ 974→1012 行，补丁数仍 69 |
| 净增 +38 行 | ✓ |
| contracts/spec/tests-vectors/llvm-project/tests-lit/helper 零改动 | ✓ git diff 无这些路径 |
| git status 仅 3 项改动 + 任务书 | ✓ changelog + patch + 新探针 + task file |
| check-patch-tree 69 | ✓ |
| check-lit 30/30 | ✓ |
| check_qemu_trans 227/227 | ✓ |
| probe 42/42 | ✓ |
| --selftest PASS | ✓ |
| 回归探针 18 条 IDENTICAL | ✓ |
| 不提交 git | ✓ |

##### 6. 两处披露判定

**① QEMU 二进制内嵌源码 revision**：engineer 处置合理。`qemu-version.h` 由 `git describe` 生成，dirty tree 或不同 commit 构建的二进制 sha 必然不同。`run.sh --inject` 在记录 `sha_bin_before` 前先做一次 normalize rebuild（对齐当前 clean commit），使基线二进制有效。判据以源码 blob sha + 探针回绿为主，二进制 sha 为辅。**判定：合理，无需订正。**

**② pre-existing 失败探针**：任务书 §5 称"仅 `_008t/_013t`"，实测 `_006t/_008t/_009t/_010t/_013t/_028t`（6 条 rc=1）。engineer 在完成区已如实披露并采用「与基线逐字节一致/零新增」判据。证据脚本 `run.sh` 的回归循环也覆盖全部18条探针。**判定：任务书事实需更正（6 条非 2 条），但 engineer 已在完成区如实处置、回归判据正确、不影响验收结论。建议后续修订任务书 §5。**

##### 7. 完成区一致性

- 补丁净 +38（974→1012）：✓
- 补丁数 69：✓
- 探针 42/42：✓
- 8 调用点覆盖 15 条：✓
- 源码 sha `df88a0ab...`：✓
- 二进制 sha `4e96dc1f...`：✓
- pre-existing 失败集实际 6 条：已在完成区如实披露 ✓

---

**最终判决：Accepted** — 所有验收项在 reviewer 独立重跑下通过；脚本审计合格；独立注入（helper 条件翻转）成功证明检查承重并还原回绿；不变量/越界/残留均合规。
