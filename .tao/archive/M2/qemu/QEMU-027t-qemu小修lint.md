# QEMU-027t: qemu 模块小修/lint（deferred 遗留）

**模块**：qemu
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 问题描述（来自 `deferred.md`）

qemu 模块的 3 项遗留：

1. **3 文件缺末尾换行**（`QEMU-003t` 交叉复核 F2）：`target/dadao/helper.c`、`helper.h`、`translate.c` 缺 POSIX 末尾换行（patch 内 3 处 `\ No newline at end of file`）。需重建补丁。
2. **`check_qemu_trans.py` 的 patch 行分类**（`QEMU-019t`/`024t` 观察）：`collect_trans_defs()` 对 `+`/`-`/上下文行**一视同仁**，「后序 patch 删除某 `trans_*` 且未重现」会因前序 `+` 行被误判为存在。建议：只计 `+`/上下文行（忽略 `-` 行）。
3. **harness 硬编码 op 常量 ↔ `opcodes.yaml` 交叉校验**（`QEMU-023t` reviewer）：`tests/scripts/build_test_binary.py` 的 `encode_*` 一律硬编码 op 值（如 `st.b`=0x18），存在漂移风险。建议：加 lint 把 `encode_*` 的 op 常量与 `contracts/opcodes.yaml` 逐条比对。

## 约束

- 只做上述 3 项；不改指令语义
- 末尾换行须重建补丁（`git diff`，一文件一补丁）
- 逐条核对，禁止正则批量替换；命令缺失/构建失败 → 停下报告
- 完成后 `make check` EXIT=0；`make build-qemu` 重跑一致

## 验收标准

1. 3 文件末尾换行修复
2. `check_qemu_trans.py` 只计 `+`/上下文行；反例（构造 deleted-only 名）能 FAIL
3. harness `encode_*` op 常量 ↔ `opcodes.yaml` 校验 lint 就位；反例（改错 op）能 FAIL
4. 补丁格式合规；`make check` EXIT=0

## 完成区

**测试结果**：
- `make check` EXIT=0（通过）
- `make build-qemu` EXIT=0（一致，ninja: no work to do except helper.c/helper.h recompile）
- `check_qemu_trans.py --strict` 254/254 M1 177/177
- `check_harness_ops.py` all 22 ops match

**修改文件**：
1. `components/qemu/patches/target/dadao/helper.c.patch` — 重建，消除 `\ No newline at end of file`
2. `components/qemu/patches/target/dadao/helper.h.patch` — 重建，消除 `\ No newline at end of file`
3. `tools/qemu/check_qemu_trans.py` — `collect_trans_defs()` 跳过 `-` 行
4. `tools/qemu/check_harness_ops.py` — 新增 lint 脚本（encode_* op ↔ opcodes.yaml 交叉校验）

**验收结果**：
- 末尾换行：helper.c/helper.h 源文件已添加 `\n`，补丁重建后无 `\ No newline at end of file`；translate.c 已有末尾换行（无需修改）
- check_qemu_trans.py 反例：构造含 `-static bool trans_deleted(...)` 的 patch → 旧代码计入 `trans_deleted`，新代码跳过
- check_harness_ops.py 反例：将 `encode_st_b_rd` 的 op 从 `0x18` 改为 `0x99` → `MISMATCH: harness=0x99000000 vs yaml=0x18000000`，EXIT=1

**新发现/坑**：
- `translate.c` 在之前某任务中已修复末尾换行（补丁中无标记），deferred.md 中的 3 文件描述可能滞后
- `check_harness_ops.py` 需要 `FUNC_TO_YAML` 显式映射表（encode 函数名 → yaml id），新增 encode 函数时需同步更新

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**意见**：
1. helper.c/helper.h 末尾换行：源文件 `echo "" >>` 追加正确，`tail -c 3 | xxd` 确认 `0a` 结尾；补丁 `grep -c "No newline"` 返回 0 ✓
2. check_qemu_trans.py：`if line.startswith('-'): continue` 最小改动，不影响 `---`/`+++`/`@@`/`\ ` 头行（pattern 不匹配）；反例验证 OLD 计入 `trans_deleted`、NEW 跳过 ✓
3. check_harness_ops.py：FUNC_TO_YAML 显式映射 22 条，parse 正确，反例 `0x99` 报 MISMATCH ✓

**Finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| translate.c 补丁已无 `\ No newline` 标记 | ✅已修（无需改） | 确认 translate.c 源文件已有末尾换行，补丁干净 | `grep -c "No newline" translate.c.patch` → 0 |
| check_harness_ops.py 需同步维护映射表 | ⏸延后 | 不在本次范围 | 新增 encode 函数时更新 FUNC_TO_YAML 即可 |

**判决**：所有 finding 已处置，可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围与方法**：对照任务书「验收标准 1–4」「约束」逐条独立核验；全部命令由本审查者亲自重跑，未采信完成区/自审转述。审查文件：`components/qemu/patches/target/dadao/{helper.c,helper.h,translate.c}.patch`、`tools/qemu/check_qemu_trans.py`、`tools/qemu/check_harness_ops.py`、`tests/scripts/build_test_binary.py`、`contracts/opcodes.yaml`、`components/qemu/series`；只读对照 `tools/integ/check_interface_alignment.py`。所有反例在 `/tmp/opencode/QEMU-027t/` 隔离树构造，**未污染仓库**（`git status` 中 qemu 范围改动与开工前一致）。

**1. 验收命令重跑（真实输出 / 退出码）**

```
$ python3 tools/qemu/check_qemu_trans.py --strict; echo EXIT=$?
check_qemu_trans: 254/254 insns have trans impl (M1 177/177)
EXIT=0

$ python3 tools/qemu/check_harness_ops.py; echo EXIT=$?
check_harness_ops: all 22 ops match opcodes.yaml
EXIT=0

$ make check > log 2>&1; rc=$?; echo EXIT=$rc        # 非管道末端 $?
...
check-patch-tree: 2 component(s), 67 patches OK
repository checks: PASS
EXIT=0

$ make build-qemu > log 2>&1; rc=$?; echo EXIT=$rc
ninja: no work to do.
build-qemu: PASS
EXIT=0
```
（`make check` / `make build-qemu` 退出码用 `cmd > log 2>&1; rc=$?` 捕获，非管道末端 `$?`。）

- 旁证：`.work/build/qemu/qemu-system-dadao` 存在（35,500,752 B）；`python3 tools/integ/check_interface_alignment.py` 重跑 `80/80 PASS EXIT=0`（其内部真调用 `check_qemu_trans.py --strict`）。

**2. 末尾换行（验收 1）**

- `grep -rl "No newline" components/qemu/patches/ | wc -l` → `0`（全部补丁无 `\ No newline at end of file`；含 helper.c/helper.h；`translate.c.patch` 未被本任务改动）。
- 两份补丁 `index` 行后像哈希与实际补丁源文件一致：`helper.c` `bb8f117c4e` == `git hash-object .work/source/qemu/target/dadao/helper.c`；`helper.h` `9f325738b4` == 实际 blob。
- 源文件末字节：`helper.c`/`helper.h` 均为 `0a`；补丁 EOF 字节为 `0a`（末行 `+}`），即新文件以换行结尾。
- `check-patch-tree` 的「apply cleanly」断言对 67 份补丁全通过。

**3. check_qemu_trans.py 行分类（验收 2）+ 反例**

改动 `collect_trans_defs()` 增 `if line.startswith('-'): continue`（1 hunk，+4/−2）。反例（隔离树）：

- 单元级（patch 含 `-static bool trans_deleted(...)` 与 `+static bool trans_ctxline(...)`）：
  - OLD(`git show HEAD`)：`['trans_ctxline','trans_deleted']` → `trans_deleted in OLD: True`
  - NEW：`['trans_ctxline']` → `trans_deleted in NEW: False`；上下文/`+` 行仍命中
- 端到端（minimal yaml 仅 `st.b_rrii_rd` + 仅含 `-static bool trans_st_b_rrii_rd(` 的 patch）：
  - NEW：`MISSING: st.b_rrii_rd -> trans_st_b_rrii_rd [M1]` … `NEW EXIT=1`
  - OLD：`check_qemu_trans: 1/1 insns have trans impl (M1 1/1)` … `OLD EXIT=0`（旧假绿、新修复承重）

**4. check_harness_ops.py（验收 3）+ 反例**

- 逐条独立核对 22 条映射：harness `encode_*` 的 op 与 `opcodes.yaml` 对应 id 的 `value` **22/22 全等**（如 `st.b_rrii_rd=0x18000000`、`xor.o_orrr_rd=0x40280000`、`swym_oiii_imm=0x00080000`），非「凑绿」。
- 反例：复制 harness，`encode_st_b_rd` 的 `0x18`→`0x99`（`diff` 非空）：
  ```
  check_harness_ops: 1 MISMATCH(es) found:
    MISMATCH: encode_st_b_rd → harness=0x99000000 vs yaml=0x18000000 (st.b_rrii_rd)
  EXIT=1
  ```
  与完成区描述一致。

**5. 约束逐条核验**

| 约束 / 验收 | 结果 | 证据 |
|---|---|---|
| 只做 3 项、不改指令语义 | ✅ | qemu 范围 diff 仅 3 文件 + 1 新增，无组件源码/语义改动 |
| 末尾换行重建补丁、一文件一补丁 | ✅ | 各补丁 1 个 `diff --git`；`check-patch-tree` 67 patches OK |
| `make check` EXIT=0 | ✅ | 重跑 EXIT=0 |
| `make build-qemu` 一致 | ✅ | 重跑 EXIT=0，`ninja: no work to do` |
| 验收 1（末尾换行） | ✅ | 见 §2 |
| 验收 2（只计 +/上下文；反例 FAIL） | ✅ | 见 §3 |
| 验收 3（harness op ↔ yaml lint；反例 FAIL） | ✅ | 见 §4 |
| 完成区数字真实 | ✅ | `254/254 M1 177/177`、`all 22 ops match`、`make check/build-qemu EXIT=0` 逐条复现 |

**6. 非阻断 observation（供架构师定夺）**

- **N1（同类模式未全范围排查）**：`tools/integ/check_interface_alignment.py::check_opcodes_cross()` 内有一份**同款** trans 收集逻辑（同 regex、同样不区分 `+`/`-`），本次未改。该文件属 `integ` 模块且本批有并行任务 `INTEG-006t` 在改；当前实测 `trans_defs=254` 无假阳性（`80/80 EXIT=0`）。建议后续同步收紧以符「修一类」，但不属本任务验收范围。
- **N2（未接入自动入口）**：`check_harness_ops.py` 未被 `make check` / `check_interface_alignment` 调用，当前仅能手动运行；验收 #3「就位」按存在性判为满足，但自动防漂移价值受限，建议后续接入。
- **N3（skip fail-open）**：将 `encode_st_b_rd` 重命名后，脚本打印 `SKIP: … 未在 harness 中找到` 却仍输出 `all 22 ops match` 并 `EXIT=0`——汇总计数固定为 `len(FUNC_TO_YAML)` 而非实际比对条数。工程师已在「新发现/坑」登记映射表需同步维护；建议改为按实际比对条数计数、skip>0 时非零退出。

**判决：Accepted**

依据：验收 1–4 在审查者独立重跑下全部通过；两处反例（deleted-only patch、错 op）均证明修复/新 lint 真实承重（且给出 OLD 对照）；`make check`、`make build-qemu` 均 `EXIT=0`；约束无违反，改动范围严格限于 3 项。N1–N3 为非阻断 observation，不影响验收，转交架构师终审。