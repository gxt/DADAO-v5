# INFRA-040t: 历史/归档类 issue 核实与关闭（moot 判定）

**模块**：infra
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（核实 + 台账收口；**禁止改动 `.tao/archive/**`**）

## 目标与 resolved_by

下列 issue 或涉及**已归档/已验证**的历史任务，或已因后续任务消解。本任务独立复核后**关闭为 moot/resolved**（或在可动范围内处置）。预期关闭：

| ISS | 架构初判（须独立复核） |
| --- | --- |
| ISS-051 | `v11.x` 目录变更（`target/riscv/translate.c`→`tcg/`）与本仓 DADAO 无补丁交集（补丁树仅 `target/dadao/**`）⇒ moot |
| ISS-052 | harness 跨任务依赖：`QEMU-005t/006t/008t` 均 `已验证`，`ADR-0010 D1 修法 a` 已落地 ⇒ resolved |
| ISS-053 | `andn.w-rb` 归属：architect 裁定保留在 `006t` 且已登记（`006t` `已验证`）⇒ resolved |
| ISS-068 | mem-rd 窄 load 归因：由 `QEMU-023t`（`build_loader()` 按宽度写）修复、`已验证` ⇒ resolved |
| ISS-080 | `SPEC-066t/067t` 完成区「修改文件」回填：两任务书**已归档**（`.tao/archive/M2/spec/`），archive 只读 ⇒ moot（回填不可行） |
| ISS-111 | `QEMU-033t` 任务书措辞订正：任务书**已归档**（`.tao/archive/M2/qemu/`），改 archive 不可行 ⇒ 措辞部分 moot；探针保留问题按现状评估处置 |

`resolved_by`：历史类填**实际修复任务**（如 `QEMU-023t`）；moot 类填本任务 `INFRA-040t`，`notes` 注明「moot：归档只读/无交集」。

## 接口规范

- **输入**：
  - `.tao/archive/M1/qemu/QEMU-005t/006t/008t/023t*.md`（只读）；
  - `.tao/archive/M2/qemu/QEMU-033t-mreg_range_overlap运行期ILLI.md`（只读）；
  - `.tao/archive/M2/spec/SPEC-066t*.md`、`SPEC-067t*.md`（只读）；
  - `tools/qemu/min_rom_probe_033t.py`、`.work/build/qemu/qemu-system-dadao`（若可用）。
- **输出**：`issues.yaml` 中对应条目 `status: closed` + `resolved_by` + `notes`（moot 理由）。
- **约束**：
  - **禁止修改 `.tao/archive/**`**（已归档 = 只读）。ISS-080/111 的「订正归档任务书」诉求**不可执行**，只能按 moot 关闭或转「遗留问题」。
  - ISS-111 的**探针保留**部分：运行 `min_rom_probe_033t.py` 记录现状；若失败项与本改动无关且无价值，可提出退役/保留建议（**不改探针代码**，仅建议；如需改另立任务）。
  - 只改 `issues.yaml` 的 `status`/`resolved_by`/`notes`，不删条目、不改 title/scope。
  - 关闭后 `check_issues.py` 无 INVALID STATUS。

## 验收标准

1. 逐条给出**可复现证据**：
   - ISS-051：`find components/qemu/patches -path '*riscv*'` 为空；补丁树仅 `target/dadao/**`。
   - ISS-052/053：对应归档任务书 `**状态**：已验证` + `ADR-0010` 落地条目。
   - ISS-068：`QEMU-023t` 完成区「24 条窄 load FAIL→PASS」证据行 + 现状 harness 宽度逻辑（若有改动须说明）。
   - ISS-080/111：确认对应任务书位于 `.tao/archive/` 且 M2 已归档。
2. **探针现状**（ISS-111）：若 `.work/build/qemu/qemu-system-dadao` 可用，运行 `python3 tools/qemu/min_rom_probe_033t.py` 记录真实结果与退出码；不可用则标注 BLOCKED（原因 + 替代证据）。
3. 反例思路：对 ISS-051，证明「若补丁树含 riscv 路径则本结论不成立」——给出 `grep -rl riscv components/qemu/patches` 实测；对 ISS-068，给出 QEMU-023t 的改前/改后对比行。
4. `python3 tools/infra/check_issues.py` **EXIT=0**；open 数减少至下界。
5. `git diff .tao/knowledge/issues.yaml` 仅含上述字段变更。

## 硬约束

- 临时目录 `/tmp/opencode/INFRA-040t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件（含 `issues.yaml`），越界须披露；**不触碰 `.tao/archive/**`**。
- 复杂命令输出留存 `.work/log/infra/INFRA-040t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/INFRA-040t/`。

## 完成区

**测试结果**：通过 **43/43**（`bash .work/evidence/INFRA-040t/run.sh`，EXIT=0）；**编辑前基线**（同一脚本、未改 issues.yaml）EXIT=1、43 项中 4 项 FAIL（ledger 6 条未关闭 + open=53），证明脚本非恒真。6 条逐条独立复核：**ISS-051/080/111 = moot；ISS-052/053/068 = resolved**。`check_issues.py` EXIT=0（**47 open / 33 closed**；初筛 53 open，减 6）。失败原因：无。

**修改文件**：
- `.tao/knowledge/issues.yaml`（6 条：`status: open→closed`、`resolved_by: null→…`、`notes` 追记复核证据；`id/title/scope/blocks` **零改动**）
- `.tao/tasks/infra/INFRA-040t-历史归档issue核实与关闭.md`（完成区 + 自审 + `**状态**`）
- `.work/evidence/INFRA-040t/{run.sh,checks.py}`（一键证据脚本，gitignored）
- `.work/log/infra/INFRA-040t-*.log`（命令输出留存，gitignored）

**验收结果**（逐条：issue → 独立验证命令/输出/退出码 → 判定 → `resolved_by`；`cmd > log 2>&1; rc=$?`，无 tee）：

| ISS | 独立验证（真实输出 / 退出码） | 判定 | resolved_by |
|---|---|---|---|
| 051 | `find components/qemu/patches -path '*riscv*'` **空**；`target/*` 唯一子目录 = `dadao`；`grep -rl riscv components/qemu/patches`→仅 `qapi/machine.json.patch`（内容为 arch 字符串 `'riscv32'/'riscv64'`，非 riscv 补丁）。反例注入：临时树放 `target/riscv/translate.c.patch` → 路径扫描 **检出**（1 命中） | **moot**（归档/无交集） | INFRA-040t |
| 052 | `QEMU-005t/006t/008t` 归档任务书 `**状态**：已验证`（3/3）；`tests/scripts/build_test_binary.py` 实测含 `if dump_mode:` + `build_dumper_section()` 守卫（ADR-0010 D1(a) 已落地）。反例注入：删守卫 → 断言 FAIL | **resolved** | QEMU-005t/006t/008t |
| 053 | `trans_imm.c.inc.patch::trans_andn_w_rwii_rb` 存在；`QEMU-006t` `**状态**：已验证`；其「遗留问题」已登记 andn.w-rb 归属。反例注入：改错符号名 → 断言 FAIL | **resolved** | QEMU-006t |
| 068 | 功能实测（import `build_test_binary`）：`build_loader('ld.ub')` 末条 store op=**0x18**（st.b）、`('ld.o')`=**0x21**（st.o）；`derive_width('ld.ub')=1`。反例注入：`_ST_WIDTH_MAP`→全 st.o → `ld.ub` 变 **0x21**（承重）、还原回 0x18。`QEMU-023t` 完成区含「24/24 窄 load FAIL→PASS」+ `**状态**：已验证` | **resolved** | QEMU-023t |
| 080 | `SPEC-066t`/`SPEC-067t` 均位于 `.tao/archive/M2/spec/`、**不在**活 `.tao/tasks/spec/`；M2 `README.md` 记 2026-10-04 归档（只读） | **moot**（归档只读） | INFRA-040t |
| 111 | `QEMU-033t` 位于 `.tao/archive/M2/qemu/`、不在活 `tasks/qemu/`、`**状态**：已验证`；探针实测 `min_rom_probe_033t.py` **9/9 PASS EXIT=0**；pre-existing：`_008t.py` T20（36/37，EXIT=1）、`_013t.py` X1/X4（20/22，EXIT=1），与本改动无关 | **moot**（措辞订正归档只读）+ 探针保留 | INFRA-040t |

**台账收口**：`git diff .tao/knowledge/issues.yaml` = 18 insertions / 14 deletions = 6×(`status`+`resolved_by`) + 4 新增 notes + 2 notes 追加；`grep` 核对 `id/title/scope/blocks` **零改动**。`python3 tools/infra/check_issues.py` → `47 open, 33 closed` **EXIT=0**。`git status --porcelain --untracked-files=all` 仅 ` M .tao/knowledge/issues.yaml`（无残留）。

**新发现/坑**：
1. **初筛「补丁树仅 `target/dadao/**`」不精确**：`components/qemu/patches/target/` 下另有 `Kconfig.patch`、`meson.build.patch` 两个**文件**（非目录）；唯一 target **子目录**为 `dadao`。判定按「无 riscv 目标路径」成立。
2. **「无 riscv 交集」须按路径判、不能按内容判**：`grep -rl riscv` 非空（`qapi/machine.json.patch` 的 arch 清单含 `riscv32/64` 字符串），但该补丁作用于 `qapi/machine.json`，与 `target/riscv/**` 结构变更无交集。反例以「路径」为准。
3. **ISS-052 无单一修复任务**：`resolved_by` 取复合值（依赖链 3 任务）；D1(a) 守卫自 `QEMU-014t` 起的 harness 即存在（ADR-0010 记其实施载体为 `QEMU-015t`）。
4. **ISS-111 的 pre-existing 失败已有 open issue 承接**（`ISS-120`），本任务仅评估、**未改探针代码**（按任务约束）。
5. **建议沉淀**：历史/归档类 issue 的关闭三分类——① 归档只读 ⇒ moot；② 依赖/诉求已被后续任务消解 ⇒ resolved（`resolved_by` 填实际任务或复合链）；③ 无法核实 ⇒ 保持 open；且 moot 须给出「具体归档文件 + 为何不可动」。

**遗留问题**：无（6/6 独立复核并关闭）。说明：ISS-080 的「台账回填」与 ISS-111 的「归档任务书措辞订正」因 M2 已归档（archive 只读）**不可执行**，按 moot 关闭并留存理由；ISS-111 的 pre-existing 探针失败已由 `ISS-120`（open）继续跟踪。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`.tao/knowledge/issues.yaml` 6 条字段改动 + `.work/evidence/INFRA-040t/{run.sh,checks.py}` + 完成区逐条对齐。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `checks.py` ledger 反例注入用硬编码 `status: closed` 替换；编辑前（open）不改变文本，导致「inject 未生效」 | ✅已修 | 改为按 `- id: ISS-051` 块定位、把 status 行改为 `INJECTED-BOGUS`（恒与现值不同且 ≠ closed） | 编辑后 `ledger [inject] text actually changed=True`；注入后 violations=1；还原回绿 |
| 2 | ISS-080/111 的 notes 直接覆盖会丢原 backlog 出处 | ✅已修 | 改为在原文后**追加**复核结论（保留 L50/L142 原注） | `git diff` 显示两处 notes 为「原文 + 追加」，非整段替换 |
| 3 | 完成区「补丁树仅 `target/dadao/**`」沿用初筛表述，与实测不符 | ✅已修 | 完成区/notes 改为「唯一 `target/*` 子目录 = `dadao`」并披露两处 target 级文件 | 证据行 `qemu patches target/* subdirs = ['dadao']` |
| 4 | 注入是否污染工作区 | ✅已核 | ISS-051 注入用 `/tmp` 临时树（非仓库）；ledger 注入 `try/finally` 写回原字节 | 末次 `git status --porcelain -uall` 仅 ` M issues.yaml`；`/tmp/opencode/INFRA-040t` 已清理 |
| 5 | ledger 断言是否恒真（初始必失败） | ✅已核 | 编辑前跑 `run.sh` → 4 FAIL / EXIT=1 | `.work/log/infra/INFRA-040t-evidence-pre.log`（EXIT=1）vs `-evidence.log`（EXIT=0） |
| 6 | 完成区结论是否与真实输出逐条对齐 | ✅已核 | 表格逐条抄录脚本/命令真实输出与退出码 | 对照 `-evidence.log` 全文 43/43 |
| 7 | 是否越界（title/scope/blocks/条目、archive） | ✅已核 | 仅改 status/resolved_by/notes；未触碰 `.tao/archive/**` | `git diff` 无 `id/title/scope/blocks` 命中；`git status` 无 archive 改动 |

**判决**：无未修 finding；证据脚本 43/43 全绿、可失败（预编辑态 4 FAIL；4 类注入 → FAIL/injection-detected → 还原 → 回绿）。状态置「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：`.work/evidence/INFRA-040t/{run.sh,checks.py}` 审阅 + 重跑 + 独立复核 3 条 + 独立注入反例 + `issues.yaml`/`git diff`/archive 未动确认。

**1. 证据脚本审阅**

- `run.sh`：`exec python3 ...`，退出码直传，无 `tee` 吞退出码 ✅
- `checks.py`：
  - `check()` 非恒真——用 `ok` 参数做真实比较 ✅
  - `main()` 失败时 `sys.exit(1)`、成功时 `sys.exit(0)` ✅
  - 每条断言均有可达 FAIL 路径（注入→FAIL→还原→回绿）✅
  - 注入均在 `try/finally` 中，还原后确认回绿 ✅
  - 无 `check(name, True)` 恒真结构 ✅
  - 反例注入覆盖 4 类（ISS-051 路径、ISS-052 守卫删除、ISS-053 符号篡改、ISS-068 宽度映射 + ledger status）✅

**2. 重跑记录**

```
$ bash .work/evidence/INFRA-040t/run.sh > /tmp/opencode/INFRA-040t-review/evidence.log 2>&1; echo "EXIT=$?"
EXIT=0
```

43/43 PASS，输出见 `/tmp/opencode/INFRA-040t-review/evidence.log`。

**3. 独立复核（3 条，不照抄 checks.py）**

| 条目 | 独立验证命令 | 真实输出 | 判定 |
|------|-------------|---------|------|
| ISS-051 | `find components/qemu/patches -path '*riscv*'` + `ls -d components/qemu/patches/target/*/` | find 无输出（FIND_EXIT=0）；`target/dadao/` 唯一子目录 | ✅ moot 确认 |
| ISS-068 | `python3 -c "import build_test_binary; build_loader('ld.ub')→op=0x18; build_loader('ld.o')→op=0x21; derive_width('ld.ub')=1"` | `ld.ub → st.b op = 0x18`；`ld.o → st.o op = 0x21`；`derive_width(ld.ub) = 1` | ✅ resolved 确认 |
| ISS-052/053 | `grep '状态' .tao/archive/M1/qemu/QEMU-{005t,006t,008t}*.md` | 005t: `**状态**：已验证`；006t: `**状态**：已验证`；008t: `**状态**：已验证` | ✅ resolved 确认 |

**4. 独立注入反例（ISS-053，与 engineer 不同）**

engineer 的 ISS-053 注入是字符串级（`tpatch.replace(...)` 不落盘）。reviewer 注入是**真实文件篡改**：

```bash
# 注入：sed 替换 trans_imm.c.inc.patch 中的符号名
$ sed -i 's/trans_andn_w_rwii_rb/trans_andn_w_rwii_XX/' components/qemu/patches/target/dadao/insn_trans/trans_imm.c.inc.patch
$ grep -c 'trans_andn_w_rwii_rb' ...  # → 0
$ python3 checks.py (ISS-053 部分) → FAIL (CHECKS_EXIT=1)

# 还原
$ cp /tmp/opencode/INFRA-040t-review/trans_imm_backup.patch ...  # 还原
$ grep -c 'trans_andn_w_rwii_rb' ...  # → 1
$ git diff --name-only  # → 仅 issues.yaml + 任务文件，无 trans_imm 残留
$ bash .work/evidence/INFRA-040t/run.sh  # → EXIT=0, 43/43 PASS
```

**5. issues.yaml 复核**

- `git diff .tao/knowledge/issues.yaml`：仅 6 条 `status`/`resolved_by`/`notes` 变更（18 insertions / 14 deletions），`id/title/scope/blocks` **零改动** ✅
- `python3 tools/infra/check_issues.py` → `47 open, 33 closed` **EXIT=0** ✅
- 6 条 `resolved_by` 正确：moot 项填 `INFRA-040t`（051/080/111），resolved 项填实际任务（052→`QEMU-005t/006t/008t`，053→`QEMU-006t`，068→`QEMU-023t`）✅
- moot 项 `notes` 均含「moot」字样及具体归档文件+理由 ✅

**6. archive 未动确认**

```
$ git status --porcelain --untracked-files=all
 M .tao/knowledge/issues.yaml
 M .tao/tasks/infra/INFRA-040t-历史归档issue核实与关闭.md
```

`.tao/archive/**` **无任何改动** ✅

**7. 「无证据即保持 open」判据**

- 无以 `git log` 叙述代替实测的情况——每条均有实际命令/代码级验证
- moot 项（051/080/111）依据具体：051 补丁树无 riscv 路径（实测 find+grep）、080/111 归档文件存在且活目录不存在（实测 os.path.isfile + M2 README 归档日期）

**判决**：**Accepted**

43/43 证据全绿、可失败；独立复核 3 条均确认；独立注入 ISS-053 反例→FAIL→还原→回绿；`issues.yaml` 仅改 status/resolved_by/notes；archive 零改动；`check_issues.py` EXIT=0。
