# QEMU-033t: `mreg_range_overlap` M1 运行期实现（QEMU translate 期 ILLI）

**模块**：qemu
**项目里程碑**：M2
**依赖**：`SPEC-088t`（规范/合约层修复，**须先 `已验证`**）。相关：`contracts/legality_rules.yaml`（`mreg_range_overlap`，`active`）、`contracts/opcodes.yaml`（`rd2rd_orri_rd`/`rb2rb_orri_rb`）、`components/qemu/patches/target/dadao/insn_trans/trans_block.c.inc.patch`、`tools/qemu/min_rom_probe_*.py`。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。

---

## 0. 背景与用户裁定

- 用户裁定（唯一真源）：`mreg_range_overlap`（`active`/`static`）当前是「**纸面规则**」——LLVM 无静态检查、**QEMU 无运行期检查**、无探针/门控；M1 现状与 spec 相违。
- 本任务只做 **QEMU 侧 M1 运行期实现**：`rd2rd`/`rb2rb` 的源/目的范围有交集（含完全重合）⇒ `gen_exception_illegal`（测试机退出码 `0x88`）。
- LLVM 侧静态检查归 `LLVM-028t`；向量/生成器修正归 `TESTCASES-023t`。

---

## 1. 事实核实（本轮 architect 实测；执行时以重跑为准）

1. `components/qemu/patches/target/dadao/insn_trans/trans_block.c.inc.patch`：
   - `trans_rd2rd_orri_rd`（L12–28）与 `trans_rb2rb_orri_rb`（L75–90）均只查 `hd==0`、`hb==0`、`hb+hd>64 || hc+hd>64`（**源、目的都查范围**），随后按升序 `load → store`。注释明写 **「Overlap handled by ascending order read-before-write」**（L11、L74）——与 spec 相违。
   - 跨组指令 `rd2ra`/`ra2rd`/`rd2rb`/`rb2rd` 不受 `mreg_range_overlap` 约束（结构性不重叠），**不改**。
2. `contracts/legality_rules.yaml` 的 `mreg_range_overlap`（SPEC-070t 新增、`active`）：同组块赋值源/目的范围有交集 ⇒ ILLI；当前仅 `rd2rd`/`rb2rb`（FP 由 `SPEC-088t` 扩到 `convert_ff`，本任务不做 FP）。
3. `tools/qemu/` 下**无** `rd2rd`/`rb2rb` 重叠 ILLI 探针；`min_rom_probe_008t.py` 仅测 `rb2rb` 非重叠往返；`min_rom_probe_013t.py` 的 B9 明确注释「同组重叠规则对 M1 的 rd2ra/ra2rd 是 vacuous」。
4. `make check-qemu-semantics` 仅跑 `reg-shift-extend`+`reg-compare`（不含 `reg-imm-block`），故本改动**不改变其覆盖**；`reg-imm-block.yaml` 中现存的同组重叠 `class: overlap` **语义**用例由 `TESTCASES-023t` 修正。

---

## 2. 设计

### 2.1 代码改动（`trans_block.c.inc.patch`）

在 `trans_rd2rd_orri_rd` 与 `trans_rb2rb_orri_rb` 的范围检查之后、复制循环之前，插入重叠检查：

```c
    if (!(a->hb + a->hd <= a->hc || a->hc + a->hd <= a->hb)) {
        gen_exception_illegal(ctx);
        return true;
    }
```

- 语义：源区间 `[hc, hc+hd)` 与目的区间 `[hb, hb+hd)` 有交集（含 `hb==hc` 完全重合）⇒ ILLI；`hd` 为 `immu6`。等价于 `overlap ⇔ !(dst_end<=src_start || src_end<=dst_start)`。
- 同时把两处注释从「Overlap handled by ascending order read-before-write」改为「Overlap ⇒ ILLI (mreg_range_overlap)」。
- **不改**另外四条 block trans（跨组）与任何其它文件。

### 2.2 探针（新建 `tools/qemu/min_rom_probe_033t.py`）

用例（沿用既有 min_rom 探针体例，`rb/rd` 初值可回读校验）：

| # | 用例 | 期望 |
|---|---|---|
| T1 | `rd2rd {rd4:rd5}, {rd2:rd3}`（目的[4,6) ∩ 源[2,4)=∅） | PASS（正常复制） |
| T2 | `rd2rd {rd3:rd4}, {rd2:rd3}`（目的[3,5) ∩ 源[2,4)={3} 部分重叠） | **ILLI 0x88** |
| T3 | `rd2rd {rd3:rd3}, {rd3:rd3}`（完全重合，count=1） | **ILLI 0x88** |
| T4 | `rd2rd {rd2:rd3}, {rd3:rd4}`（目的在源之前，部分重叠） | **ILLI 0x88** |
| T5 | `rb2rb {rb4:rb5}, {rb2:rb3}`（非重叠） | PASS |
| T6 | `rb2rb {rb3:rb4}, {rb2:rb3}`（部分重叠） | **ILLI 0x88** |
| T7 | `rb2rb {rb3:rb3}, {rb3:rb3}`（完全重合） | **ILLI 0x88** |
| T8 | 对照：`rd2ra {ra3:ra4}, {rd3:rd4}`（跨组"同索引"，不属本规则） | PASS |

- 每条分支出/退出码须**双向验证**（目标=分支指令+偏移指向预期分支）；写操作数/期望值须在关键用例回读校验（`set.zw`+`or.w`，避免立即数位宽截断）。
- 产物落点：探针脚本入 `tools/qemu/`（可复用/审计）；ROM 等中间产物落 `TEST_ARTIFACTS_DIR`（`INFRA-025t` D6）。

### 2.3 测试机退出码约定
ILLI = `0x88`（`ADR-0004` 测试机约定）；PASS 走既有 exit port 约定。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `components/qemu/patches/target/dadao/insn_trans/trans_block.c.inc.patch` | 两条 trans 加重叠 ILLI + 注释修正 |
| 2 | `tools/qemu/min_rom_probe_033t.py` | 新建探针（T1–T8） |
| 3 | `.work/evidence/QEMU-033t/run.sh` | 一键证据脚本（不含 `tee` 吞码；含注入自检） |
| 4 | `.work/log/qemu/QEMU-033t-*.log` | 构建/探针完整输出（非易失） |

**明确不改**：`contracts/opcodes.yaml`、`spec/**`、`tests/**`、`tools/{spec,llvm,testcases}/**`、`components/llvm-project/**`。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `components/qemu/patches/target/dadao/insn_trans/trans_block.c.inc.patch`
- `contracts/legality_rules.yaml`（`mreg_range_overlap`）、`contracts/opcodes.yaml`（`rd2rd_orri_rd`/`rb2rb_orri_rb` 字段与编码）
- 既有探针体例 `tools/qemu/min_rom_probe_008t.py`/`_013t.py`、`tools/qemu/check_qemu_trans.py`

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围，越界须披露；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make prepare`（重应用补丁集、`.work/source/qemu` 保持 base+1 commit 不变量）+ `make build-qemu`（增量，预计 **2–5 分钟**；若触发 reconfigure 则更久，须先申报）。
- 临时目录 `/tmp/opencode/QEMU-033t/`；日志 `.work/log/qemu/`；证据 `.work/evidence/QEMU-033t/`。

---

## 6. 验收标准（可执行、可失败，含反例注入）

1. **构建**：`make prepare && make build-qemu` EXIT 0（留 `.work/log/qemu/QEMU-033t-build.log`）。
2. **探针全绿**：`python3 tools/qemu/min_rom_probe_033t.py`：T1/T5/T8 PASS、T2/T3/T4/T6/T7 = ILLI 0x88；每例打印「检查名 + 期望/实际 + 退出码」，进程退出码 0 仅当全部符合。
3. **反例可失败（承重证明）**：注入「移除重叠检查」的 QEMU 构建 ⇒ T2/T3/T4/T6/T7 变 FAIL（尤其 T3 完全重合）⇒ 还原源码**并重建** ⇒ 回绿。注入用 `git diff --name-only` 证明非空；还原用 `git status`/`git diff` + 重建后重跑证明。
4. **不误伤**：既有 `tools/qemu/min_rom_probe_008t.py`（含 `rb2rb` 非重叠往返）与 `_013t.py`（跨组）保持 PASS。
5. **编码门控不回归**：`python3 tools/qemu/check_qemu_trans.py` → `227/227 (M1 152/152)`、EXIT 0。
6. **`make check` 全绿**：`repository checks: PASS`（重点：`check-qemu-semantics` PASS、lit 26/26、`validate-encoding` 227 OK）。
7. **残留与越界**：`git status --untracked-files=all` 干净（除应改文件 + 本任务书）；`check-no-residue` PASS；`git diff --name-only` 与 §3 对齐。

### 6.1 反例注入
- (a) 删除 T2/T3/T4/T6/T7 的重叠检查（还原为「升序先读后写」）⇒ 探针 FAIL。
- (b) 只查部分重叠、不查完全重合（如用 `hb+hd==hc` 之类错误条件）⇒ T3 仍 PASS 但 T2/T4 应 FAIL（证明「含完全重合」断言承重）。
- 注入后须**重建**再跑，还原后亦须**重建**（源码还原 ≠ 二进制还原）。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-033t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
7. 复杂命令输出留存 `.work/log/qemu/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/QEMU-033t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

- 本任务依赖 `SPEC-088t` 先落地（至少 `contract-isa`/`SimRISC-07` 的禁则）；若 `SPEC-088t` 未完成，本任务不应下发（避免实现与合约打架）。
- `min_rom_probe_033t.py` 的寄存器/立即数构造须防位宽截断；分支须双向核对（见 AGENTS「探针的寄存器/内存值构造须回读校验」「探针分支须双向验证」）。
- 不改 `check-qemu-semantics` 覆盖范围（避免引入 `reg-imm-block` 全量用例的不确定性）；重叠 ILLI 的端到端证据由本探针 + `TESTCASES-023t` 的 `legality` 向量承担。

## 完成区

**测试结果**：
- 探针 `tools/qemu/min_rom_probe_033t.py`：**9/9 PASS，EXIT=0**（日志 `.work/log/qemu/QEMU-033t-probe-final.log`）：
  ```
  [PASS] T1 rd2rd {rd4:rd5},{rd2:rd3} disjoint -> PASS: exit=0x00
  [PASS] T2 rd2rd {rd3:rd4},{rd2:rd3} partial -> ILLI: exit=0x88
  [PASS] T3 rd2rd {rd3:rd3},{rd3:rd3} complete -> ILLI: exit=0x88
  [PASS] T4 rd2rd {rd2:rd3},{rd3:rd4} partial(dst first) -> ILLI: exit=0x88
  [PASS] T5 rb2rb {rb4:rb5},{rb2:rb3} disjoint -> PASS: exit=0x00
  [PASS] T6 rb2rb {rb3:rb4},{rb2:rb3} partial -> ILLI: exit=0x88
  [PASS] T7 rb2rb {rb3:rb3},{rb3:rb3} complete -> ILLI: exit=0x88
  [PASS] T8 rd2ra {ra3:ra4},{rd3:rd4} cross-group -> PASS: exit=0x00
  [PASS] T9 rd2rb {rb3:rb4},{rd3:rd4} cross-group -> PASS: exit=0x00
  Main: 9/9 passed, 0 failed / Overall: PASS
  ```
  T1/T5/T8/T9 均**回读校验**复制结果（`cmp.uo`/`cmp.uo-rb` + `br.nz` 走 FAIL 臂，立即数用 `set.zw` 写高位字避免位宽截断）；T2/T3/T4/T6/T7 直接 ILLI 0x88。
- **一键证据脚本** `.work/evidence/QEMU-033t/run.sh`：默认/`--inject`/`--full` **均 EXIT=0**（默认 20 项、`--inject` 42 项、`--full` 26 项 PASS，0 FAIL；日志 `.work/log/qemu/QEMU-033t-evidence-{default,inject,full}.log`）。
- 构建：`make build-qemu`（JOBS=8）**EXIT=0，实测 6s**（单 TU 变更增量）。
- 回归：`make check` **EXIT=0**（`repository checks: PASS`；lit **27/27**）；`python3 tools/qemu/check_qemu_trans.py` **EXIT=0 且 `227/227 insns have trans impl (M1 152/152)`**；`make check-qemu-semantics` **EXIT=0（149 total, 149 passed）**；`make check-patch-tree` **EXIT=0（2 component(s), 67 patches OK）**；`make check-source-state` **EXIT=0**（qemu `HEAD=b74252b count=1 clean=True`）。

**修改文件**：
1. `.work/source/qemu/target/dadao/insn_trans/trans_block.c.inc`：`trans_rd2rd_orri_rd` 与 `trans_rb2rb_orri_rb` 均在范围检查后、复制循环前插入 `if (!(a->hb + a->hd <= a->hc || a->hc + a->hd <= a->hb)) { gen_exception_illegal(ctx); return true; }`（各 6 行：2 行注释 + 4 行代码）；并把两处过时块注释改为 `Overlap ⇒ ILLI (mreg_range_overlap).`。**整文件 136→148 行（+12）**。
2. `components/qemu/patches/target/dadao/insn_trans/trans_block.c.inc.patch`：由 `python3 tools/infra/make_patch.py qemu` 导出（`1 written, 30 unchanged`）；补丁文件 `git diff` = **+16/−4（净 +12）**，142→154 行；`components/qemu/series` 内容不变（31 行）。
3. `tools/qemu/min_rom_probe_033t.py`（新增探针 T1–T9；产物经 `_probe_artifact_dir()` 落 `.dadao/tests/probes/`，自清理）。
4. `.work/evidence/QEMU-033t/run.sh`（新增一键证据脚本；仅 `.work/` 下，不入 git）。
   （`.tao/tasks/qemu/QEMU-033t-*.md` 的改动为本完成区自身。）

**验收结果**（真实命令 + 退出码；日志目录 `.work/log/qemu/`，临时产物 `/tmp/opencode/QEMU-033t/`）：

| # | 验收项 | 命令/证据 | 真实输出 | 判定 |
|---|--------|-----------|----------|------|
| 1 | 构建 | `JOBS=8 make build-qemu`（`QEMU-033t-build.log`） | `BUILD_EXIT=0`，6s | ✅ |
| 2 | 探针全绿 | `python3 tools/qemu/min_rom_probe_033t.py` | T1/T5/T8/T9=`0x00`，T2/T3/T4/T6/T7=`0x88`，`PROBE_EXIT=0` | ✅ |
| 3 | 反例门控 A（移除检查） | `run.sh --inject`（`QEMU-033t-evidence-inject.log`） | 重建后 T2/T3/T4/T6/T7=`0x89`、`PROBE_EXIT=1`；还原+重建后=`0x88`、`PROBE_EXIT=0` | ✅ |
| 3b | 反例门控 B（漏完全重合） | 同上 | 重建后 T3/T7=`0x89`、T2/T4/T6 仍 `0x88`、`PROBE_EXIT=1`；还原+重建后 `0x88`、绿 | ✅ |
| 3c | 探针断言自检（PASS 臂） | evidence 内 `probe_selftest` | 改错 T1/T5 期望 ⇒ `exit=0x42`、`PROBE_EXIT=1`（rd/rb 两支均承重） | ✅ |
| 4 | 不误伤既有探针 | `min_rom_probe_008t.py` / `_013t.py` | 相关用例 T23 `rb2rb round-trip`=`0x00`、B9 `rd2ra→ra2rd`=`0x00` **PASS**；整体 EXIT=1 系**预存在**失败（见遗留） | ✅（相关项） |
| 5 | 编码门控不回归 | `python3 tools/qemu/check_qemu_trans.py` | `227/227 insns have trans impl (M1 152/152)`，EXIT=0 | ✅ |
| 6 | `make check` 全绿 | `make check`（`QEMU-033t-make-check.log`） | `EXIT=0`；`lit 27/27`；`repository checks: PASS` | ✅ |
| 7 | 残留/越界 | `git status --untracked-files=all` | 仅 `M trans_block.c.inc.patch` + `?? min_rom_probe_033t.py`（+任务书）；`check-no-residue` 含于 `make check` 绿 | ✅ |

补丁链路证据（真命令）：
```
$ git -C .work/source/qemu status --porcelain      # 空（E1 干净）
$ git -C .work/source/qemu rev-list --count c3d48b7..HEAD
1
$ git -C .work/source/qemu rev-parse HEAD
b74252bfe2bd851cac7abad117a45c3800cdb1d8         # = base(c3d48b7)+1
$ python3 tools/infra/make_patch.py qemu
make-patch: 1 written, 30 unchanged (skipped); qemu wrote 31 patches
$ make check-patch-tree
check-patch-tree: 2 component(s), 67 patches OK   # EXIT=0
```
反例注入有效性/可复原：注入 A、B 时 `git -C .work/source/qemu diff --name-only` 均为 `target/dadao/insn_trans/trans_block.c.inc`（非空）；还原后 `git status --porcelain` 空、源文件 sha256 复原为 `ec1fc9bd02d03db983b2315ecf6893b55ad7778d72a5392dc9cb2201fd644f6f`，且**重建后**复跑探针回绿。最终源码 sha256 `ec1fc9bd…`、二进制 sha256 `0043d9136d03f393cbd4623c7a2be633268dd4ee23280326b3944f30f96ec8aa`（同源重建可复现）。

**新发现/坑**：
1. **任务书 §6.1(b) 的反例描述自相矛盾**：原文写「只查部分重叠、不查完全重合 … ⇒ T3 仍 PASS 但 T2/T4 应 FAIL（证明「含完全重合」断言承重）」。按字面逻辑，漏掉完全重合后 **T3/T7 才应不再 ILLI（探针 FAIL）**，而 T2/T4/T6 部分重叠仍应 ILLI；与「证明含完全重合承重」的意图互为矛盾。本实现按**意图**（证明含完全重合承重）取 `overlap && hb != hc` 注入：实测 **T3/T7→0x89、T2/T4/T6 仍 0x88**，探针 `EXIT=1`；还原后 T3→0x88。请审查者以本口径判定，勿按 §6.1(b) 字面（该字面与自身理由冲突）。
2. **`min_rom_probe_008t.py` / `_013t.py` 整体 EXIT=1 为预存在失败，非本次引入**：008t `T20 st.o-rb rb0 → ILLI` 实得 `0x89`（应 `0x88`）；013t `X1`（0x01 应 0x8A）、`X4`（0x8B 应 0x00，MemRAS）。**独立基线对照**：把重叠检查从同一二进制移除（= 改动前行为）重建后重跑，两探针**主测试失败集逐条一致**（008t `36/37`、013t `20/22`，`diff` 为空）。任务书 §6 验收项 4 写「保持 PASS」与现状不符，实际含义应为「本次改动零新增失败」。
3. **`git status` 只显示补丁与探针**：`.work/**` 与 `.dadao/**` 均 gitignore；探针 ROM 产物落 `.dadao/tests/probes/`，不污染工作树。
4. 建议沉淀知识：`mreg_range_overlap` 的运行期实现点在 `target/dadao/insn_trans/trans_block.c.inc::trans_rd2rd_orri_rd`/`trans_rb2rb_orri_rb`（**translate 期** `gen_exception_illegal`）；判定式 `!(hb+hd<=hc || hc+hd<=hb)`（含完全重合）；跨组 `rd2ra/ra2rd/rd2rb/rb2rd` 结构性不重叠、**不加**检查。探针 `min_rom_probe_033t.py` 可作「同组重叠 ILLI + 跨组对照 + 回读校验」模板。

**遗留问题**：
- ⏸延后（非本任务范围）：`min_rom_probe_008t.py` 的 `T20`、`_013t.py` 的 `X1/X4` 预存在失败（基线对照已证与本次改动无关；见「新发现/坑」#2）。任务书 §6 项 4 的「保持 PASS」措辞待协调者订正为「零新增失败」。
- ⏸延后（非本任务范围）：`components/qemu/changelog.md` 未按任务追加记录——任务书 §3 交付物未列该文件，按「只动任务书范围」不改（同 `QEMU-032t` 处置）。
- ✅已修：本任务范围内无未修 finding。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：QEMU 源码两处 trans（`trans_rd2rd_orri_rd`/`trans_rb2rb_orri_rb`）、导出补丁、探针 `min_rom_probe_033t.py`、证据脚本 `run.sh`，自主逐行审查 + 全流程实跑。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 判定式是否含完全重合、是否与 SPEC-088t/`legality_rules.yaml` 一致 | ✅已验 | `!(hb+hd<=hc \|\| hc+hd<=hb)`（De Morgan；`hd>0` 已由前序 `hd==0` 分支保证） | T3/T7（`hb==hc` 完全重合）实得 `0x88`；注入 B 后 T3/T7 不再 ILLI |
| 2 | 是否只作用于同组、误伤跨组 | ✅已验 | 仅改 `rd2rd`/`rb2rb` 两条；跨组四条不动 | T8 `rd2ra`/T9 `rd2rb` 跨组同索引均 `0x00`；注入 A 后 T8 仍 `0x00` |
| 3 | PASS 用例的复制断言是否双向可达（防恒真） | ✅已验 | `build_assertion`：`cmp.uo`/`cmp.uo-rb` + `br_nz`→FAIL 臂；PASS 臂写 exit 0、FAIL 臂写 `0x42` | `probe_selftest`：改错 T1/T5 期望 ⇒ `T1/T5 exit=0x42`、`PROBE_EXIT=1`；错误期望还原即回绿 |
| 4 | 立即数构造是否位宽截断 | ✅已验 | 期望值/源值一律 `set.zw`（写 bits[63:48]）、不依赖小立即数承载任意值 | T1/T5/T8/T9 回读值与期望一致（0x00 退出），错值即 0x42 |
| 5 | 反例注入是否有效、可复原（含重建） | ✅已验 | 注入 = 删检查 / 加 `hb!=hc` 守卫；还原 = `git checkout` | 注入 `git diff --name-only` 非空；还原 `git status` 空、源 sha256 `ec1fc9bd…` 复原、**重建**后探针回绿 |
| 6 | 是否存在过时注释与 spec 相违 | ✅已验 | 改两处块注释为 `Overlap ⇒ ILLI (mreg_range_overlap).` | 证据脚本静态断言：两条旧串计数 0、新串计数 2 |
| 7 | 是否引入回归 | ✅已验 | 不改其它路径 | `make check` EXIT=0（lit 27/27）；check_qemu_trans 227/227；check-qemu-semantics 149/149；008t/013t 失败集与基线逐条一致 |
| 8 | 任务书 §6.1(b) 与自身理由矛盾 | ⏸延后（文档层） | 不改任务书正文，按「证明含完全重合承重」意图实现并披露 | 见「新发现/坑」#1 与证据 `--inject` 输出 |
| 9 | `components/qemu/changelog.md` 未更新 | ⏸延后 | 任务书 §3 未列该文件，按「只动任务书范围」 | 登记遗留 |
| 10 | `make build-qemu` 同源重建的二进制是否可复现 | ✅已验 | 未改构建脚本 | `touch` 源文件后重建，二进制 sha256 不变（`0043d913…`），非环境抖动 |

**逻辑正确性核对**：
- 触发条件 `!(hb+hd<=hc \|\| hc+hd<=hb)` 等价于半开区间 `[hb,hb+hd)` 与 `[hc,hc+hd)` 有交集（含完全重合）；与 `contracts/legality_rules.yaml::mreg_range_overlap`、`SPEC-088t` 一致。ILLI 经 `gen_exception_illegal`→测试机退出码 `0x88`（ADR-0004 D5.8）。
- 判定发生在 **translate 期**（条件仅由编码字段决定，与运行期值无关），不依赖复制顺序；插入点在前序 `hd==0`/`hb==0`/越界检查之后，`hd>=1` 恒成立。
- 未改任何函数签名、未改决策语义、未引入外部依赖；`make check-patch-tree`（断言①–⑨）绿、`--source-state` E1 成立。

**判决**：本任务范围内 finding 全部 ✅已修/已验；两条跨范围项（#8 文档口径、#9 changelog）已披露并登记「遗留问题」。#8 属任务书内部矛盾，已按自身理由取实现口径并留证据，建议 reviewer/协调者裁定。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：Sat Oct 03 2026
**审查方法**：独立重跑全部验收命令 + 审核 evidence 脚本 + 独立注入反例

---

##### 一、重跑记录（逐项真实命令、输出、退出码）

| # | 验收项 | 命令 | 真实输出 | 退出码 | 判定 |
|---|--------|------|----------|--------|------|
| 1 | 探针默认 9 用例 | `python3 tools/qemu/min_rom_probe_033t.py` | T1/T5/T8/T9=0x00, T2/T3/T4/T6/T7=0x88, 9/9 PASS | 0 | ✅ |
| 2 | check_qemu_trans | `python3 tools/qemu/check_qemu_trans.py` | `227/227 insns have trans impl (M1 152/152)` | 0 | ✅ |
| 3 | check-patch-tree | `make check-patch-tree` | `2 component(s), 67 patches OK` | 0 | ✅ |
| 4 | check-qemu-semantics | `make check-qemu-semantics` | `149 total, 149 passed` | 0 | ✅ |
| 5 | make check 全量 | `make check` | `repository checks: PASS`, lit 27/27, 80 项 PASS | 0 | ✅ |
| 6 | check-source-state | `make check-source-state` | `HEAD=b74252b count=1 clean=True` | 0 | ✅ |
| 7 | run.sh 默认模式 | `bash .work/evidence/QEMU-033t/run.sh` | 20/20 PASS, source sha256=`ec1fc9bd…`, binary sha256=`0043d913…` | 0 | ✅ |
| 8 | run.sh --inject | `bash .work/evidence/QEMU-033t/run.sh --inject` | 42/42 PASS（A+B 注入/还原/重建全流程） | 0 | ✅ |

---

##### 二、脚本审计结论（`run.sh`）

**结构审计**：
- 断言函数 `check()`: 非恒真，FAIL 路径存在（`bad()` 打印 + 设 `FAIL=1`）✅
- `probe_case_exit()`: 从日志提取退出码，不吞码 ✅
- `run_probe()` / `rebuild()`: 用 `> log 2>&1` + `$?` 捕获退出码，无 `tee` 吞码 ✅
- 注入 A（删重叠检查）: Python 断言 `count(old)==2`，替换为空串，非空可还原 ✅
- 注入 B（漏完全重合）: 加 `hb!=hc` 守卫，断言 `count(old)==2`，非空可还原 ✅
- `restore_and_rebuild()`: `git checkout` + porcelain 检查 + 重建 ✅
- `injection_round()`: diff 非空验证 + 重建 + 探针 FAIL 验证 ✅
- `probe_selftest()`: 改 T1/T5 期望值 → FAIL 臂 0x42，双向验证 RD/RB ✅
- 末尾 `exit 1` / `exit 0`: 由 `$FAIL` 控制，不恒为 0 ✅

**注入 A/B 审计**：
- A 注入: 删除两处完整重叠检查块（6 行/处），`assert count(old)==2`，替换后 count=0，非空 ✅
- B 注入: 将 `if (!(hb+hd<=hc || hc+hd<=hb))` 改为 `if (hb!=hc && !(...))`，`assert count(old)==2`，非空 ✅
- 两者均可通过 `git checkout` 还原并重建 ✅

---

##### 三、我的独立注入（不使用脚本自带 A/B）

**注入 C**：将判定式 `<=` 改为 `<`（`hb+hd<=hc` → `hb+hd<hc`，`hc+hd<=hb` → `hc+hd<hb`）

| 步骤 | 命令/操作 | 真实输出 | 退出码 |
|------|-----------|----------|--------|
| 注入 | Python 替换 2 处 `<=` → `<` | `old count: 2, new count: 2` | 0 |
| diff 非空 | `git -C .work/source/qemu diff --name-only` | `target/dadao/insn_trans/trans_block.c.inc` | 0 |
| 重建 | `JOBS=8 make build-qemu` | `BUILD_EXIT=0` | 0 |
| 探针 | `python3 tools/qemu/min_rom_probe_033t.py` | **T1=0x88(expect 0x00) FAIL, T5=0x88(expect 0x00) FAIL**, T2/T3/T4/T6/T7=0x88 PASS, T8/T9=0x00 PASS, **7/9 passed, 2 failed** | **1** |
| 还原 | `git checkout` | porcelain 空 | 0 |
| 重建 | `JOBS=8 make build-qemu` | `BUILD_EXIT=0` | 0 |
| 探针回绿 | `python3 tools/qemu/min_rom_probe_033t.py` | **9/9 passed, 0 failed**, Overall: PASS | 0 |
| sha256 复原 | `sha256sum trans_block.c.inc` | `ec1fc9bd02d03db983b2315ecf6893b55ad7778d72a5392dc9cb2201fd644f6f` | — |

**注入 C 分析**：`<` 与 `<=` 的差异在「边界相触」（dst_end == src_start）场景：T1 dst=[4,6) src=[2,4) 的 6<2=false, 4<4=false → 误判重叠；T5 同理。证明判定式 `<=` 是精确的半开区间不相交条件，`<` 会过严。注入有效、承重。✅

---

##### 四、两处披露的判定

**披露 1：任务书 §6.1(b) 自相矛盾**

原文：「只查部分重叠、不查完全重合（如用 `hb+hd==hc` 之类错误条件）⇒ T3 仍 PASS 但 T2/T4 应 FAIL（证明「含完全重合」断言承重）」

**判定**：工程师的解读正确。按字面逻辑，漏掉完全重合后 T3/T7（hb==hc 的完全重合）不再 ILLI，而 T2/T4/T6（部分重叠）仍 ILLI。工程师取注入 B `hb!=hc` 守卫：实测 T3/T7→0x89（FAIL）、T2/T4/T6 仍 0x88，证明「含完全重合」承重。该解读忠于任务意图（§1 背景：「含完全重合 ⇒ ILLI」），§6.1(b) 原文的「T3 仍 PASS」是笔误（与自身理由矛盾）。**不需返工**。

**披露 2：`min_rom_probe_008t.py` / `_013t.py` 失败为预存在**

**判定**：独立确认。当前二进制下：
- 008t: T20 `st.o-rb rb0 → ILLI` exit=0x89(expect 0x88), 36/37 passed, 1 failed
- 013t: X1 exit=0x01(expect 0x8A), X4 exit=0x8B(expect 0x00), 20/22 passed, 2 failed

这些失败与 `mreg_range_overlap` 检查无关（涉及 `st.o-rb rb0` 和 MemRAS），本次改动零新增失败。**不需返工**。

---

##### 五、约束核验

| 约束 | 判定 |
|------|------|
| 探针 9/9 PASS、EXIT=0 | ✅ |
| 含完全重合（T3/T7）⇒ ILLI 0x88 | ✅ |
| 部分重叠（T2/T4/T6）⇒ ILLI 0x88 | ✅ |
| 非重叠（T1/T5）⇒ 0x00 | ✅ |
| 跨组对照（T8/T9）⇒ 0x00（不误伤） | ✅ |
| 注释修正：旧注释 count=0、新注释 count=2 | ✅ |
| `.work/source/qemu` base+1 commit、porcelain 空 | ✅ HEAD=b74252b, count=1 |
| `make check-patch-tree` 67 OK | ✅ |
| 补丁净 +12（+16/−4） | ✅ `git diff --stat` 确认 |
| `series` 未变（31 行） | ✅ |
| `components/llvm-project/**` 未动 | ✅ |
| `make check` EXIT=0、lit 27/27 | ✅ |
| `check-qemu-semantics` 149/149 | ✅ |
| `check_qemu_trans` 227/227 | ✅ |
| `check-source-state` EXIT=0 | ✅ |
| `git status --untracked-files=all` 仅预期改动 | ✅ |
| 脚本审计 + 重跑 + 独立注入 | ✅ |

---

##### 六、判决

**Accepted**

全部验收命令在 reviewer 独立重跑下通过；工程师的证据脚本审计合格（非恒真、FAIL 路径可达、注入非空可还原、含重建）；独立注入 C 证明判定式 `<=` 与 `<` 的差异承重；补丁净 +12 与实际一致；两处披露（§6.1(b) 笔误、008t/013t 预存在失败）判定均不需返工；源码不变量（base+1、porcelain、sha256）全部确认。
