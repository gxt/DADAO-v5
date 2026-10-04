# INFRA-023t: 补丁「生成/应用」幂等 + `check-patch-tree` 内容断言

**模块**：infra（`tools/infra/` + `docs/spec/component-patching.md`）
**项目里程碑**：M2
**依赖**：`QEMU-031t`（暴露该缺陷，已 `9ffb76b`）
**上级**：`ADR-0002 D4`（组件补丁与构建编排；本任务为其**派生实现细节**，**不需新 ADR**）
**状态**：已验证

## 背景（事故）

`QEMU-031t` 交付的 3 份 patch **`@@` 头行数被写小** ⇒ `git apply` **丢尾部**、`apply_series` EXIT=1、**patch 无法复现源树**；而 `make check` **假绿**——因 `check-patch-tree` 只做 `git apply --cached --check`（**容忍尾部、不比对内容**）。
根因：**手工编辑 `.patch` 文本**（而非在 working tree 改、再导出）。

## 交付物

1. **规范** `docs/spec/component-patching.md`：
   - **§6.1（硬规则）**：补丁**不得手工编辑/直接修改**；改组件源码**一律在 working tree**（`.work/source/<name>`），**验证通过后一次性**用**裸 `git diff <base_commit> -- <path>`** 导出**完整**补丁。
   - **§6.2（生成幂等）**：导出时**先与现有补丁比较**；**逐字节一致 ⇒ 不替换**（保持原文件与时间戳不变），避免 `index`/头部信息被无谓刷新。
   - **§7.x（应用幂等，逐补丁）**：构建 working tree 时**逐补丁**判断——目标文件**已等于补丁结果 ⇒ 跳过、不写入**（不改 mtime）；**仅对确有变化者 `git apply`**。（动机：避免"重放⇒时间戳全变⇒几乎全量重编"，与 `INFRA-018t` 同源。）
   - **§8 断言 ⑥（内容一致性）**：`series` 全量应用到 base 后，**各受影响路径 blob 必须 == `.work/source` 对应文件**；不一致 ⇒ FAIL。
2. **`tools/infra/make_patch.py`**：导出前与现有补丁比较，**一致则不写**（§6.2）。
3. **`tools/infra/apply_series.py`**：改为**逐补丁幂等**——每份先 `git apply --check --reverse`：**已应用 ⇒ 跳过**；否则 `git apply`（§7.x）。
4. **`tools/infra/check_patch_tree.py`**：新增**断言 ⑥**（§8）。

## 范围外 ✗
- **不改**任何 `components/**/patches/**` 的**内容**（本任务只改工具 + 规范）；
- 不改 LLVM/QEMU 源码、`spec/`、历史文件。

## 验收标准（须真实可失败）
1. **断言 ⑥ 真可失败** ⚠️（你亲自注入 + 复原 byte-identical）：
   - A：**手工编辑**某 patch 一行（改内容但保持能 apply）⇒ `check-patch-tree` **FAIL**；
   - B：把某 patch 的 `@@ ... +N @@` 头**改小**（重现本事故）⇒ **FAIL**（且说明旧断言 ④ 为何放过）；
   - 复原后 PASS。
2. **生成幂等**（§6.2）：在**无源码改动**时重跑生成/导出 ⇒ 现有补丁文件**逐字节不变**（贴 sha/mtime 证据）。
3. **应用幂等**（§7.x）：**已应用**状态下重跑 `make apply-series` ⇒ **目标源文件 mtime 不变**（`stat` 证据）；`apply_series` EXIT=0。
4. **无回归**：`make check` **EXIT=0**；`check-patch-tree` 断言①–⑥全过；`make apply-series` 幂等成功。
5. **未越界**：`git diff --name-only` = `docs/spec/component-patching.md` + `tools/infra/{make_patch,apply_series,check_patch_tree}.py` + 任务书。
6. 退出码用 `cmd >log 2>&1; rc=$?`（禁管道吞码 ✗）；命令失败 ⇒ 停下报告 ✗。

## 完成区
**测试结果**：全部通过
**修改文件**：
- `docs/spec/component-patching.md`（§6.1 硬规则、§6.2 生成幂等、§7.x 逐补丁应用幂等、§8 断言⑥）
- `tools/infra/make_patch.py`（§6.2：`_normalize_index` 剥离 `index` 行比较，一致则不写）
- `tools/infra/apply_series.py`（§7.x：逐补丁 `--check --reverse` 跳过已应用，不改 mtime）
- `tools/infra/check_patch_tree.py`（断言⑥：scratch index 应用后比对 `.work/source` blob）

**断言 ⑥ 反例 A/B 真实输出 + 复原**：
- A（手工编辑 patch 一行）：
  ```
  check-patch-tree: qemu: assertion ⑥: configs/devices/dadao-softmmu/default.mak: patched-index blob differs from .work/source (patch does not reproduce worktree)
  check-patch-tree: 1 problem(s)
  EXIT=1
  ```
  复原：`cp original.patch` → SHA256 `dec56345...` 匹配 → EXIT=0
- B（`@@ -0,0 +1,5 @@` 改为 `+1,3`）：
  ```
  check-patch-tree: qemu: assertion ⑥: configs/targets/dadao-softmmu.mak: patched-index blob differs from .work/source (patch does not reproduce worktree)
  check-patch-tree: 1 problem(s)
  EXIT=1
  ```
  旧断言④为何放过：`git apply --cached --check` EXIT=0 — git apply 容忍尾部多余行，`+1,3` 头 + 5 行内容仍能 apply（只取前 3 行，后 2 行被忽略）。只有断言⑥比对实际 blob 内容才能捕获。
  复原：`cp original.patch` → SHA256 `d56c88e7...` 匹配 → EXIT=0

**生成幂等 / 应用幂等证据（sha/mtime）**：
- C（无源码改动重跑 `make_patch.py qemu`）：`make-patch: 0 written, 31 unchanged (skipped)`；SHA256 与 mtime 逐文件 identical（`diff before.sha after.sha` 无输出）
- D（已应用状态重跑 `apply_series.py`）：`apply-series: qemu 0 applied, 31 skipped (already applied)`；mtime 逐文件 identical（`diff before.stat after.stat` 无输出）

**`make check` / `apply-series` 真实退出码**：
- `make check`：EXIT=0
- `make apply-series`（已应用）：EXIT=0
- `check-patch-tree`（正常）：EXIT=0，67 patches OK
- `git diff --name-only`：仅 `docs/spec/component-patching.md` + `tools/infra/{make_patch,apply_series,check_patch_tree}.py`（4 文件，无 component patches）

**新发现/坑**：
- `git diff` 的 `index` 行缩写长度受 `core.abbrev` 影响：当前机器默认 7 字符，但现有补丁用 10 字符。`make_patch.py` 的幂等比较需剥离 `index` 行（只比较 diff 内容），否则每次重跑都会误判为"有变化"而重写所有补丁。
- `git apply --check` 对 `@@ +N @@` 写小的补丁**不报错**（容忍尾部多余行），这正是 `QEMU-031t` 事故的根因。断言④（apply cleanly check）无法捕获此类问题，必须用断言⑥（内容比对）。

**遗留问题**：
- 断言⑥ 使用 `read_text(encoding="utf-8", errors="replace")` 比较文本内容；若未来有二进制文件补丁，需改用 `cat-file` 的原始字节比较。当前无实例，留待 §11 边界情况处理。
- `make_patch.py` 的 `_normalize_index` 剥离 `index` 行后比较——若两个 patch 仅 `index` 行不同（不同 blob hash 但相同 diff），会视为相同。这在语义上正确（`index` 行是 metadata），但若未来需要区分"blob hash 变化"场景，需调整。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `_normalize_index` 剥离 `index` 行比较：语义正确（`index` 是 metadata），但需确认 regex 不误匹配 | ✅已修 | regex `^index [0-9a-f]+\.\.[0-9a-f]+.*\n` 仅匹配标准 `index` 行格式 | 反例 C 验证：31 patch 全 unchanged |
| `check_patch_tree.py` 断言⑥ 用 `cat-file -p` 读 scratch index blob vs `read_text` 读 worktree：文本模式可能对二进制文件误判 | ⏸延后 | 当前无二进制补丁实例（§11 边界情况） | 67 patch 全文本，`check-patch-tree` EXIT=0 |
| `apply_series.py` 逐补丁 `--check --reverse` 后直接 apply，无中间状态保护 | ✅已修（无需改） | 每个 patch 独立处理；apply 失败会 `check=True` 抛异常终止 | counterexample D 验证：31 skipped, EXIT=0 |
| `make_patch.py` stale patch 移除在 `export` 之前，但 `export` 内部仍会 `mkdir -p` | ✅已修（无需改） | 逻辑正确：先删 stale → 再 mkdir → 再 export | 反例 C 验证：0 written, SHA identical |
#### 第 1 轮 reviewer 验收

**审查者**：reviewer（独立重跑，未采信完成区）。工作目录 `/mnt/tao/DADAO-v5`，证据 `/tmp/opencode/INFRA-023t-r1/`。

##### 1. 文件正确性分析

- `docs/spec/component-patching.md`：`git diff` 确认新增 §6.1（硬规则）、§6.2（生成幂等）、将原 §6 步骤改为 §6.3、§7.2 重写为「逐补丁幂等」、§8 标题 `5 条→6 条`、新增断言⑥行、§9 补一句⑥。与任务「交付物 1」逐条对得上。
- `tools/infra/make_patch.py`：新增 `_normalize_index()`，在 `export()` 内仅用于**比较**（`target.is_file() and _normalize_index(target.read_text()) == _normalize_index(body)`），写盘仍是 `target.write_text(body)`（原始 `git diff`）。
- `tools/infra/apply_series.py`：逐个补丁 `git apply --check --reverse` 成功即 `skipped` 跳过；否则 forward check + apply。
- `tools/infra/check_patch_tree.py`：新增断言⑥——scratch index `--cached` 应用补丁集后，对每条受影响路径 `git cat-file -p :path` 与 `.work/source/<name>/<path>` 文本比对，不一致报 `assertion ⑥`。

##### 2. 重跑记录（真实输出 + 退出码）

**(a) 基线 & 无回归**
```
$ python3 tools/infra/check_patch_tree.py > baseline-check.log 2>&1; echo EXIT=$?
EXIT=0
check-patch-tree: 2 component(s), 67 patches OK

$ timeout 1200 make check > make-check.log 2>&1; echo MAKE_CHECK_EXIT=$?
MAKE_CHECK_EXIT=0      # 日志内 check-patch-tree: 2 component(s), 67 patches OK；lit 25/25；149/149；repository checks: PASS
```

**(b) 断言⑥ 真可失败 —— 反例 A（手工改一行，仍能 apply）**
注入（sed 改 `default.mak.patch` 的 `+# Default configuration...` 加 ` EDITED`）：
```
$ python3 tools/infra/check_patch_tree.py > injectA.log 2>&1; echo EXIT=$?
EXIT=1
check-patch-tree: qemu: assertion ⑥: configs/devices/dadao-softmmu/default.mak: patched-index blob differs from .work/source (patch does not reproduce worktree)
check-patch-tree: 1 problem(s)
```
旧断言④独立复跑（scratch index `git apply --cached --check` 全系列）：
```
OLD_ASSERT4_EXIT=0        # 新文件补丁不论内容总能 apply ⇒ ④放过
```
复原：`cp pristine/A.orig` → `sha256 dec5634515a47e9c03a35cc8aa9ed82c8daf0991793e116b7880f5a2261bb3a7`（与原文件一致）→ `check_patch_tree.py EXIT=0`；`git status --porcelain components/` 空。

**(c) 断言⑥ 真可失败 —— 反例 B（`@@` 头写小，重现 QEMU-031t）**
注入（`@@ -0,0 +1,5 @@` → `@@ -0,0 +1,3 @@`）：
```
$ python3 tools/infra/check_patch_tree.py > injectB.log 2>&1; echo EXIT=$?
EXIT=1
check-patch-tree: qemu: assertion ⑥: configs/targets/dadao-softmmu.mak: patched-index blob differs from .work/source (patch does not reproduce worktree)
```
旧断言④独立复跑：`OLD_ASSERT4_EXIT=0`（**放过**）。并实证 git apply 静默截断：
```
$ GIT_INDEX_FILE=idx git -C .work/source/qemu apply --cached <该 patch>; echo rc=$?
rc=0
cat-file :configs/targets/dadao-softmmu.mak → 仅 3 行（TARGET_ARCH/TARGET_LONG_BITS/TARGET_NOT_USING_LEGACY_LDST_PHYS_API），后 2 行被丢弃
worktree 源文件 → 5 行
```
⇒ ④（`--cached --check`，容忍尾部）为何放过、⑥（内容比对）为何捕获，**已由审查者独立复现**，与完成区说明一致。
复原：`cp pristine/B.orig` → `sha256 d56c88e771e00c575f700957ebff61e4853607b4d144121b8ab1aaf55a5dd7f8` → `EXIT=0`；`components/` 干净；两文件 mtime 亦已 `touch -d @...` 还原。

**(d) §6.2 生成幂等（两组件）**
```
$ python3 tools/infra/make_patch.py qemu        # EXIT=0
make-patch: 0 written, 31 unchanged (skipped)
$ python3 tools/infra/make_patch.py llvm-project  # EXIT=0
make-patch: 0 written, 36 unchanged (skipped)
$ diff before.$c.sha after.$c.sha   → 无输出（qemu/llvm 均 identical）
$ diff before.$c.stat after.$c.stat → 无输出（mtime 全 identical）
```
`index`-行剥离只用于比较的独立证据：本机 `git diff` 输出 `index 0000000..a99eda2`（7 位），而盘上补丁为 `index 0000000000..a99eda246a`（10 位）——若按裸字节比较必重写；实测重跑后盘上**仍是 10 位原行**（`grep '^index '` 所见），证明 `_normalize_index` 未进入写盘路径。

**(e) §7.x 应用幂等（逐补丁，两组件）+ 部分应用**
```
$ make apply-series > make-apply-series.log 2>&1; echo MAKE_APPLY_EXIT=$?
MAKE_APPLY_EXIT=0
apply-series: llvm-project 0 applied, 36 skipped (already applied)
apply-series: qemu 0 applied, 31 skipped (already applied)
$ diff before.stat after.stat → 无输出（67 个目标文件 mtime 全 identical）
```
部分应用场景：对 `default.mak.patch` 先 `git apply --reverse`（文件被删），再跑 `apply_series.py`：
```
$ python3 tools/infra/apply_series.py; echo EXIT=$?
EXIT=0
apply-series: llvm-project 0 applied, 36 skipped (already applied)
apply-series: qemu 1 applied, 30 skipped (already applied)      # 仅该补丁被重新应用
```
mtime 差异**仅** `default.mak` 一项变化，其余 66 文件不变；`check_patch_tree.py` 复原后 `EXIT=0`。⇒ 逐补丁幂等行为正确。

##### 3. 约束核验（逐条）

| 任务硬约束 | 结论 | 证据 |
|---|---|---|
| 断言⑥真可失败（A/B + 复原 byte-identical） | ✅ | 见 §2(b)(c)：A/B 均 EXIT=1，old-④ 均 EXIT=0；复原 SHA 匹配、components 干净 |
| §6.2 生成幂等（无改动重跑逐字节不变） | ✅ | 见 §2(d)：0 written，sha+mtime identical |
| `index` 剥离只用于比较、不影响产物 | ✅ | 见 §2(d)：盘上仍存 10 位 `index` 行 |
| §7.x 应用幂等（mtime 不变 + EXIT=0） | ✅ | 见 §2(e)：67 目标 mtime 全不变 |
| `make check` EXIT=0；断言①–⑥全过 | ✅ | 见 §2(a) |
| `git diff --name-only` = 规范 + 3 工具（+任务书 untracked） | ✅ | 实跑仅 `docs/spec/component-patching.md`、`tools/infra/{make_patch,apply_series,check_patch_tree}.py` 4 文件 |
| **不改 `components/**/patches/**` 内容** | ✅ | `git status --porcelain components/` 空；`git diff --stat components/` 空 |
| 历史文件干净 | ✅ | 全量 `git status --porcelain` 仅 4 处 M + 1 处 `??` 任务书 |
| 退出码用 `cmd >log 2>&1; rc=$?`（禁管道吞码） | ✅ | 本审查全部命令均按此执行 |

##### 4. 完成区逐条复读

完成区所列断言 A/B 输出、复用旧④说明、C（`0 written,31 unchanged`）、D（`0 applied,31 skipped`）、`make check EXIT=0`、`67 patches OK`、`git diff --name-only` 4 文件、复原 SHA（`dec56345…` / `d56c88e7…`）——**逐条与审查者独立重跑一致**，无转述/美化/矛盾。

##### 5. 非阻塞观察（不影响本次验收，建议后续清理）

1. **死代码（本次改动引入的孤儿）**：`tools/infra/make_patch.py:31` 的 `INDEX_RE` 从未被使用（`_normalize_index` 内联了同款 regex）；`tools/infra/check_patch_tree.py:62` 新增的 `git()` 辅助函数全文件无调用（断言⑥直接 `subprocess.run`）。建议删除。
2. **文件尾换行丢失**：三个工具的 `raise SystemExit(main())` 末尾换行被去掉（`\ No newline at end of file`），建议补回。
3. **规范措辞 vs 实现**：§6.2 写「**逐字节一致** ⇒ 不替换」，实现为「剥离 `index` 行后比较一致 ⇒ 不替换」。二者在本机 `core.abbrev` 与存量补丁不一致时会分叉；实现行为符合 §6.2 同意图（「避免 index/头部信息被无谓刷新」），但字面「逐字节」与实现不符，建议将 §6.2 措辞改为「比较时**忽略 `index` 行**，其余逐字节一致 ⇒ 不替换」。
4. **`Makefile` 注释陈旧**（越界范围外、未改）：`check-patch-tree` 目标上方仍注「树形补丁集**四**断言」，实际已 6 条。不属本任务范围，仅记录。
5. **stale 清理语义变化**：`make_patch.py` 由「整体清空 `patches/`」改为「仅 unlink 不在本次改动集中的 `*.patch`」——这是达成 §6.2 幂等的必要改动（整体清空会刷新全部 mtime）；但副作用是非 `*.patch` 残留文件/空目录不再被清理（此类残留仍会被断言⑤拦截）。无实例，仅记录。

##### 6. 判决

**Accepted**。

- 验收标准 1/2/3/4/5 均在审查者**独立重跑**下通过（含亲自注入反例 A/B 并确认旧断言④放过、⑥捕获，复原 byte-identical）。
- 硬约束无违反；`components/**` 内容未被改动。
- 第 5 节为非阻塞的清洁性/文档措辞建议，不构成返工理由。
- 设计层/路线层未见阻断问题；最终接受与否交由架构师终审。


#### 主会话收尾（2026-10-02）

1. **提交推送**：`component-patching.md`（§6.1/§6.2/§7.x/§8⑥）+ `make_patch.py`/`apply_series.py`/`check_patch_tree.py`（见 git log）。
2. **reviewer 第 1 轮 Accepted**：断言⑥ **亲测可失败**（A 手改一行 / B `@@ +N` 改小 ⇒ **EXIT=1**；**旧断言④独立复跑 EXIT=0**，实证 `--cached --check` 静默截断尾部）；§6.2 生成幂等（`0 written/N unchanged`，sha/mtime 不变；`index` 归一化**仅用于比较**）；§7.x 应用幂等（已应用重跑 **67 文件 mtime 全 identical** + EXIT=0；部分应用仅动 1 文件）；`make check` EXIT=0。
3. **非阻断登记（供后续小任务/架构师）**：
   - 死代码：`make_patch.py:31 INDEX_RE`、`check_patch_tree.py:62 git()` 未被调用；
   - 三工具**文件尾缺换行**；
   - **§6.2 措辞**「逐字节一致」与实现「忽略 `index` 行比较」不符（行为正确）⇒ 建议改措辞；
   - `Makefile` 注释「四断言」陈旧（范围外）；
   - `make_patch` stale 清理由「整体清空」改为「仅删 stale `*.patch`」（§6.2 必需），副作用为非 patch 残留不再清理（断言⑤兜底）。
