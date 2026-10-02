# INFRA-019t: 安装/产物路径定位机制（单一真源）+ 路径规范化守卫

**模块**：infra
**项目里程碑**：M2
**依赖**：无（本任务只引入机制，不移动任何东西）
**ADR**：`ADR-0016`（D7 定位机制单一真源；D8 路径 realpath）—— 已 Accepted
**状态**：待验收（**待用户确认任务书后下发**）

## 背景

`ADR-0016` 决定：`.dadao/` 为 target SDK 安装/产物根；host 工具链 prefix = `.dadao/cross-toolchain`；target sysroot = `.dadao/dadao-unknown-elf`；测试运行产物 = `.dadao/tests/`。
本任务**只**建立"**定位机制单一真源**"，使后续任务（迁移参考、install、门控接线）都从该真源取路径，**改名只改一处**；并固化"脚本一律真实路径"。

**范围外**（不要在本任务做）✗：
- 不移动 `.dadao/`、`.work/`、`.cache/` 中任何内容（迁移是 `INFRA-020t`）；
- 不新增 install 目标（`INFRA-021t`）；
- 不改门控/执行器取可执行的路径（`INFRA-022t`）；
- 不改 `tests/vectors/**`。

## 命名标准（用户 2026-10-02 裁定，方案 A）

- 清单文件：**`manifests/install-dirs.lock.toml`**
- 键名：**统一 `_dir` 后缀**（语义一致、无"`sysroot_root`"式重复）

## 交付物

1. **单一真源文件** `manifests/install-dirs.lock.toml`（新）：
   ```toml
   format = 1
   # ADR-0016 安装/产物目录根（唯一真源；改名只改这里）
   sdk_dir            = ".dadao"                    # 安装/产物根
   host_toolchain_dir = ".dadao/cross-toolchain"    # D3/D4：host 工具链（bin 含 qemu-system-dadao）
   target_sysroot_dir = ".dadao/dadao-unknown-elf"  # D5：target sysroot
   test_artifacts_dir = ".dadao/tests"              # D6：测试向量运行产物
   ```
   约束：值必须为**仓库根相对路径**（不得绝对路径）；三者（`host_toolchain_dir`/`target_sysroot_dir`/`test_artifacts_dir`）均位于 `sdk_dir` 之下 ✓。

2. **解析模块** `tools/infra/paths.py`（新）：
   - 提供函数（均返回**绝对、realpath 解析后**的 `pathlib.Path`）：`repo_root()`、`sdk_dir()`、`host_toolchain_dir()`、`host_toolchain_bin()`（= `host_toolchain_dir()/bin`）、`target_sysroot_dir()`、`test_artifacts_dir()`。
   - `repo_root()` 必须基于 `Path(__file__).resolve()`（**符号链接解析**），使经 `~/tao/…`（→ `/mnt/tao`）调用时仍返回真实路径 `/mnt/tao/…`。
   - CLI：
     - `paths.py --make`：打印 `NAME := <值>`（供 Makefile `$(eval)` 一次导入）；
     - `paths.py <key>`：打印单个值（`repo_root`/`sdk_dir`/`host_toolchain_dir`/`host_toolchain_bin`/`target_sysroot_dir`/`test_artifacts_dir`）。
   - 读 `manifests/install-dirs.lock.toml`；文件缺失/字段缺失/值为绝对路径 ⇒ 非零退出并报错。

3. **Makefile 接入**：`SDK_DIR`/`HOST_TOOLCHAIN_DIR`/`HOST_TOOLCHAIN_BIN`/`TARGET_SYSROOT_DIR`/`TEST_ARTIFACTS_DIR` 等变量**经 `paths.py --make` 导入**（不得再手写这些路径）。本任务**不改变任何现有 target 的行为**。

4. **路径守卫** `tools/infra/check_dirs.py`（新）+ `make check-dirs`，接入 `make check`：
   - 扫描**受版本控制**的脚本/构建文件（至少 `Makefile`、`tools/**/*.py`、`tests/**/*.py`、`manifests/*.toml`），禁止出现**符号链接前缀** `/home/ubuntu/tao`（须用真实路径或相对路径）✓。
   - 校验 `manifests/install-dirs.lock.toml`：四键齐全、**均为相对路径**、且 `host_toolchain_dir`/`target_sysroot_dir`/`test_artifacts_dir` 在 `sdk_dir` 之下 ✓。
   - 退出码：任一违规 ⇒ 非零（**不得** print 后 return 0 ✗）。

## 验收标准（须真实可失败）

1. `manifests/install-dirs.lock.toml` 存在且字段/相对性/包含关系自洽。
2. `paths.py` 各函数返回值正确；**经符号链接路径调用**（`cd /home/ubuntu/tao/DADAO-v5 && python3 tools/infra/paths.py repo_root`）返回**真实路径** `/mnt/tao/DADAO-v5` ✓（贴证据）。
3. `Makefile` 变量由 `paths.py` 派生（贴 `make --print`/变量证据，证明未硬编码）。
4. **`make check` EXIT=0**（含新 `check-dirs`）；既有 target 行为**未变**。
5. **反例（须真实失败 + byte-identical 复原）** ⚠️：
   - A：在某受扫脚本注入 `/home/ubuntu/tao/DADAO-v5/...` ⇒ `check-dirs` **非零** ✓；
   - B：把 `install-dirs.lock.toml` 的 `target_sysroot_dir` 改成绝对路径 `/opt/x` ⇒ **非零** ✓；
   - C：把 `target_sysroot_dir` 改到 `sdk_dir` 之外（如 `.other/x`）⇒ **非零** ✓；
   - 复原用 `cmd >log 2>&1; rc=$?` 捕获退出码（**禁止管道吞码** ✗），复原后 `make check` 回 EXIT=0 ✓。
6. **未越界**：`git diff --name-only` = 新增 `manifests/install-dirs.lock.toml`、`tools/infra/paths.py`、`tools/infra/check_dirs.py`、`Makefile`、任务书；`.dadao/`/`.work/`/`.cache/` 内容**未被移动** ✓；未改历史文件 ✓。
7. 命令缺失/失败 ⇒ 停下报告 ✗。

## 完成区
**测试结果**：通过 7/7（manifest 校验 + symlink 扫描 + 非空自检反例 + 3 守卫反例 + make check 全量）

**修改文件**：
- `manifests/install-dirs.lock.toml`（新增，单一真源）
- `tools/infra/paths.py`（新增，路径解析模块）
- `tools/infra/check_dirs.py`（新增，路径守卫）
- `Makefile`（修改：逐变量 `$(shell)` 派生 + 非空自检 + 新增 `check-dirs` target + 接入 `make check`）

**paths.py 输出证据（含符号链接场景）**：
```
# 经符号链接 ~/tao → /mnt/tao 调用：
$ cd /home/ubuntu/tao/DADAO-v5 && python3 tools/infra/paths.py repo_root
/mnt/tao/DADAO-v5                          ← realpath 解析，非 /home/ubuntu/tao
```

**Makefile 变量由 paths.py 派生的证据（第 2 轮修正）**：
```
$ cd /home/ubuntu/tao/DADAO-v5 && for v in REPO_ROOT SDK_DIR HOST_TOOLCHAIN_DIR HOST_TOOLCHAIN_BIN TARGET_SYSROOT_DIR TEST_ARTIFACTS_DIR; do val=$(make -p 2>/dev/null | grep "^$v " | head -1); echo "$v => $val"; done
REPO_ROOT => REPO_ROOT := /mnt/tao/DADAO-v5
SDK_DIR => SDK_DIR := /mnt/tao/DADAO-v5/.dadao
HOST_TOOLCHAIN_DIR => HOST_TOOLCHAIN_DIR := /mnt/tao/DADAO-v5/.dadao/cross-toolchain
HOST_TOOLCHAIN_BIN => HOST_TOOLCHAIN_BIN := /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin
TARGET_SYSROOT_DIR => TARGET_SYSROOT_DIR := /mnt/tao/DADAO-v5/.dadao/dadao-unknown-elf
TEST_ARTIFACTS_DIR => TEST_ARTIFACTS_DIR := /mnt/tao/DADAO-v5/.dadao/tests
（六变量各自独立成行、值正确，均由 paths.py 动态派生，非硬编码）
```

**非空自检反例证据**：
```
$ echo 'format = 1' > manifests/install-dirs.lock.toml && make -n check > log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=2
ERROR: missing key 'sdk_dir' in .../manifests/install-dirs.lock.toml
Makefile:23: *** SDK_DIR is empty — check manifests/install-dirs.lock.toml and tools/infra/paths.py.  Stop.
```

**反例 A/B/C 真实输出与退出码 + 复原证据（第 2 轮复验）**：

**反例 A**（注入 `/home/ubuntu/tao/DADAO-v5/test` 到 `tools/infra/doctor.py`）：
```
EXIT=1
ERROR: tools/infra/doctor.py:209: contains symlink prefix '/home/ubuntu/tao'
```
复原：`cp doctor.py.bak doctor.py` + `git diff --name-only -- tools/infra/doctor.py`（空 = byte-identical）

**反例 B**（`target_sysroot_dir = "/opt/x"` 绝对路径）：
```
EXIT=1
ERROR: install-dirs.lock.toml: target_sysroot_dir must be relative, got '/opt/x'
ERROR: install-dirs.lock.toml: target_sysroot_dir='/opt/x' is not under sdk_dir='.dadao'
```
复原：从备份还原 + `diff` 确认 byte-identical（无输出 = 无差异）

**反例 C**（`target_sysroot_dir = ".other/x"` 越界）：
```
EXIT=1
ERROR: install-dirs.lock.toml: target_sysroot_dir='.other/x' is not under sdk_dir='.dadao'
```
复原：从备份还原 + `diff` 确认 byte-identical

**复原后 make check**：
```
$ make check > log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
check-qemu-semantics: PASS
check-dirs: PASS
repository checks: PASS
```

**验收结果**：
1. ✅ `manifests/install-dirs.lock.toml` 存在且字段/相对性/包含关系自洽
2. ✅ `paths.py` 经符号链接调用返回真实路径 `/mnt/tao/DADAO-v5`
3. ✅ `Makefile` 六变量各自独立成行、值正确（逐变量 `$(shell)`，非 `$(eval)` 多行拼接）
4. ✅ `make check` EXIT=0（含新 `check-dirs`）
5. ✅ 反例 A/B/C 均非零退出 + byte-identical 复原；非空自检反例 EXIT=2
6. ✅ `git diff --name-only` = 仅 `Makefile`；新文件 3 个；`.dadao/`/`.work/`/`.cache/` 未被移动

**新发现/坑**：
- **GNU Make `$(shell)` 换行折叠**：`$(eval $(shell multi-line-output))` 不可行，`$(shell)` 把换行转空格，多行赋值被拼成一行；必须逐变量单次 `$(shell)` 调用
- `~/tao` 是 `/mnt/tao` 的符号链接，`Path(__file__).resolve()` 可正确穿透
- `check_dirs.py` 的 `git ls-files` 过滤确保只扫受版本控制的文件；新文件需 `git add` 后才被扫描
- `manifests/*.toml` 也纳入扫描范围（含 `components.lock.toml`、`references.lock.toml`）

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审
- **finding 1**：`check_symlink_prefix` 仅扫 `git ls-files` 中的文件，新创建的 `paths.py`/`check_dirs.py`/`install-dirs.lock.toml` 尚未被跟踪，暂不被扫描
  - **处置**：⏸延后 — 任务要求"受版本控制的文件"，新文件 `git add` 后自然纳入；`check_manifest` 不依赖 git 跟踪状态，始终可达
- **finding 2**：`_print_make_vars()` 中 `data` 变量在 `for key in _REQUIRED_KEYS` 循环后复用，语义正确但可读性可优化
  - **处置**：❌不修 — 功能正确，无需额外抽象
- **判决**：所有 finding 已处置，可标「待验收」

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立重跑，不采信完成区）
**证据目录**：`/tmp/opencode/INFRA-019t-r1/`

##### 1. 重跑记录（真实输出 / 退出码）

**核验点 2（符号链接穿透）— 通过 ✓**
```
$ ls -ld /home/ubuntu/tao   →  /home/ubuntu/tao -> /mnt/tao/
$ cd /home/ubuntu/tao/DADAO-v5 && pwd -P   →  /mnt/tao/DADAO-v5
$ cd /home/ubuntu/tao/DADAO-v5 && python3 tools/infra/paths.py repo_root
/mnt/tao/DADAO-v5
（sdk_dir/host_toolchain_dir/host_toolchain_bin/target_sysroot_dir/test_artifacts_dir
 均返回 /mnt/tao/DADAO-v5/... 绝对 realpath）
$ cd /tmp && python3 /home/ubuntu/tao/DADAO-v5/tools/infra/paths.py repo_root
/mnt/tao/DADAO-v5
```
（从其它 cwd、经符号链接绝对路径调用也返回真实路径）

**核验点 3（Makefile 变量由 paths.py 派生）— 失败 ✗（阻断）**
```
$ cd /mnt/tao/DADAO-v5 && make -p 2>/dev/null | grep -n 'SDK_DIR'
162:SDK_DIR := /mnt/tao/DADAO-v5/.dadao HOST_TOOLCHAIN_DIR := /mnt/tao/DADAO-v5/.dadao/cross-toolchain
     TARGET_SYSROOT_DIR := /mnt/tao/DADAO-v5/.dadao/dadao-unknown-elf
     TEST_ARTIFACTS_DIR := /mnt/tao/DADAO-v5/.dadao/tests
     REPO_ROOT := /mnt/tao/DADAO-v5 HOST_TOOLCHAIN_BIN := /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin
（整段拼接在同一物理行 = SDK_DIR 的值）
$ for v in SDK_DIR HOST_TOOLCHAIN_DIR HOST_TOOLCHAIN_BIN TARGET_SYSROOT_DIR TEST_ARTIFACTS_DIR REPO_ROOT; do
    printf '%s : %s\n' "$v" "$(grep -c "^$v :=" make-p.txt)"; done
SDK_DIR : 1
HOST_TOOLCHAIN_DIR : 0
HOST_TOOLCHAIN_BIN : 0
TARGET_SYSROOT_DIR : 0
TEST_ARTIFACTS_DIR : 0
REPO_ROOT : 0

$ make -f Makefile --eval='.PHONY: _pv
_pv:
	@echo "SDK_DIR=[$(SDK_DIR)]"
	@echo "HOST_TOOLCHAIN_DIR=[$(HOST_TOOLCHAIN_DIR)]"
	@echo "HOST_TOOLCHAIN_BIN=[$(HOST_TOOLCHAIN_BIN)]"
	@echo "TARGET_SYSROOT_DIR=[$(TARGET_SYSROOT_DIR)]"
	@echo "TEST_ARTIFACTS_DIR=[$(TEST_ARTIFACTS_DIR)]"' _pv
SDK_DIR=[/mnt/tao/DADAO-v5/.dadao HOST_TOOLCHAIN_DIR := ... HOST_TOOLCHAIN_BIN := /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin]
HOST_TOOLCHAIN_DIR=[]
HOST_TOOLCHAIN_BIN=[]
TARGET_SYSROOT_DIR=[]
TEST_ARTIFACTS_DIR=[]
```
根因：GNU Make 的 `$(shell ...)` **把换行转成空格**，因此 `$(eval $(shell ...))` 收到的是**一行**文本；make 把 `SDK_DIR :=` 之后直到行尾的全部内容当作 `SDK_DIR` 的值，其余四个变量**从未被赋值**（`HOST_TOOLCHAIN_DIR` 等为空串）。

**核验点 4（make check EXIT=0 + 既有 target 未弱化）— 通过 ✓**
```
$ time make check > make-check.log 2>&1; rc=$?; echo "EXIT=$rc"
real 0m59.274s ... EXIT=0
check-dirs: PASS
repository checks: PASS
（全量 80 项 PASS；既有 target 列表逐项保留，check-dirs 追加在 check 依赖末尾）
```

**核验点 5（守卫真实可失败）— 通过 ✓**（每例自取退出码，`>log 2>&1; rc=$?`，无管道吞码）
```
反例 A（往 tracked 文件 tools/infra/doctor.py 注入 /home/ubuntu/tao/...）:
  EXIT=1  ERROR: tools/infra/doctor.py:210: contains symlink prefix '/home/ubuntu/tao'
  复原：git checkout -- ，sha256 与注入前一致，diff -q 通过（byte-identical）

反例 B（target_sysroot_dir = "/opt/x"）:
  EXIT=1  ERROR: install-dirs.lock.toml: target_sysroot_dir must be relative, got '/opt/x'
          ERROR: install-dirs.lock.toml: target_sysroot_dir='/opt/x' is not under sdk_dir='.dadao'
  复原：sha256 = 650021ec...（与备份一致，diff -q 通过）

反例 C（target_sysroot_dir = ".other/x"）:
  EXIT=1  ERROR: install-dirs.lock.toml: target_sysroot_dir='.other/x' is not under sdk_dir='.dadao'
  复原：sha256 = 650021ec...（与备份一致，diff -q 通过）

复原后 python3 tools/infra/check_dirs.py → EXIT=0；make check → EXIT=0
```

**核验点 6（未越界）— 通过 ✓**
```
$ git status --porcelain
 M Makefile
?? .tao/tasks/infra/INFRA-019t-安装产物路径定位机制.md
?? manifests/install-dirs.lock.toml
?? tools/infra/check_dirs.py
?? tools/infra/paths.py
$ git diff --name-only        → Makefile
$ git status --porcelain tests/vectors/ → （空）
```
`.dadao/`（含 DADAO、DADAO-0628 参考树）、`.work/`（build、source）、`.cache/` 内容未被移动。

##### 2. 约束核验（逐条）

| 约束 | 结论 | 证据 |
|---|---|---|
| 命名 `install-dirs.lock.toml` + 四键统一 `_dir` | ✓ | 文件与四键正确 |
| 值仓库根相对路径、三子目录位于 `sdk_dir` 之下 | ✓ | 程序化核验：all relative=True，三个 under sdk_dir=True |
| `paths.py` 各函数绝对 realpath、符号链接穿透 | ✓ | 经 `~/tao` 与其它 cwd 均返回 `/mnt/tao/...` |
| `paths.py` 缺文件/缺字段/绝对路径 ⇒ 非零 | ✓ | 缺 key EXIT=1；绝对路径 EXIT=1 |
| 受扫脚本含 `/home/ubuntu/tao` 前缀 ⇒ 守卫非零 | ✓ | 反例 A EXIT=1（可复原） |
| manifest 绝对路径 / 越界 ⇒ 守卫非零 | ✓ | 反例 B/C EXIT=1 |
| Makefile 五个变量经 `paths.py --make` 导入 | ✗ | 仅 SDK_DIR 被定义且值被污染，其余 4 个为空 |
| `make check` EXIT=0，既有 target 未弱化 | ✓ | EXIT=0；check-dirs 为纯追加 |
| 不移动 `.dadao/`/`.work/`/`.cache/`，不改 `tests/vectors/**` | ✓ | git status / diff |
| 反例复原 byte-identical + 复原后 make check EXIT=0 | ✓ | sha256、diff -q、make check |
| 命令缺失/失败即停并报告 | ✓（本次审查未遇缺失） | — |

##### 3. 判决：**Needs Revision**

**阻断项（对应交付物 3 / 验收标准 3）**：
Makefile 的变量导入实际失效——`$(eval $(shell $(PYTHON) tools/infra/paths.py --make))` 因 `$(shell)` 把换行折成空格而**无法产生多条赋值**：
- `SDK_DIR` 的值被污染为整段拼接文本；
- `HOST_TOOLCHAIN_DIR` / `HOST_TOOLCHAIN_BIN` / `TARGET_SYSROOT_DIR` / `TEST_ARTIFACTS_DIR` / `REPO_ROOT` **均为空**。
虽然当前没有 target 使用这些变量（故 `make check` 仍 EXIT=0、行为未变），但交付物 3 明确要求这些变量经 `paths.py --make` 导入；实际未满足，且属"静默失败"（后续任务一旦引用将取到空串）。

完成区第 3 条"Makefile 变量由 `paths.py --make` 动态派生 ✅"**与真实不符**：其贴出的单行拼接输出正是该缺陷本身，却被当作通过证据。

**修改建议（改哪个文件、怎么改、预期结果）**：
1. 改 `Makefile`：放弃多行 `$(shell)→$(eval)`，改为逐变量单次 `$(shell)` 取值（或让 `paths.py` 生成 `.mk` 片段后 `include`）。最小改法示例：
   ```make
   SDK_DIR            := $(shell $(PYTHON) tools/infra/paths.py sdk_dir)
   HOST_TOOLCHAIN_DIR := $(shell $(PYTHON) tools/infra/paths.py host_toolchain_dir)
   HOST_TOOLCHAIN_BIN := $(shell $(PYTHON) tools/infra/paths.py host_toolchain_bin)
   TARGET_SYSROOT_DIR := $(shell $(PYTHON) tools/infra/paths.py target_sysroot_dir)
   TEST_ARTIFACTS_DIR := $(shell $(PYTHON) tools/infra/paths.py test_artifacts_dir)
   ```
   （仍为单一真源、无硬编码，且保留 paths.py 的 fail-closed 报错。）
2. 预期结果：`make -p` 中六个变量**各自独立成行**且值正确；`make --eval` 探针五个变量均非空。
3. 建议在 `check_dirs.py` 或一个自检断言中校验这些变量非空，防止同类静默回归；并同步修正完成区第 3 条证据。

**非阻断观察**：`check_symlink_prefix` 只扫 `git ls-files` 中受控文件，新文件在 `git add` 前不被扫描（engineer 已在自审 finding 1 记录）；`check_manifest` 不依赖 git 跟踪，始终可达，故不阻断。

**reviewer 未采信、仅核对项**：完成区其余数字（make check 结果、反例 A/B/C 输出与退出码、git 范围）经独立重跑均一致。

#### 第 2 轮 engineer 返工

**修复项**：Makefile 变量派生（阻断项 1）

**根因**：`$(eval $(shell $(PYTHON) tools/infra/paths.py --make))` 中 GNU Make 的 `$(shell)` 将多行输出折叠为单行，导致 `SDK_DIR` 被赋值为整段拼接文本，其余变量为空。

**修复**（Makefile diff）：
```diff
-$(eval $(shell $(PYTHON) tools/infra/paths.py --make))
+REPO_ROOT          := $(shell $(PYTHON) tools/infra/paths.py repo_root)
+SDK_DIR            := $(shell $(PYTHON) tools/infra/paths.py sdk_dir)
+HOST_TOOLCHAIN_DIR := $(shell $(PYTHON) tools/infra/paths.py host_toolchain_dir)
+HOST_TOOLCHAIN_BIN := $(shell $(PYTHON) tools/infra/paths.py host_toolchain_bin)
+TARGET_SYSROOT_DIR := $(shell $(PYTHON) tools/infra/paths.py target_sysroot_dir)
+TEST_ARTIFACTS_DIR := $(shell $(PYTHON) tools/infra/paths.py test_artifacts_dir)
+
+# Non-empty guard: abort if any path variable is empty (manifest missing/corrupt).
+_install_dir_vars = REPO_ROOT SDK_DIR HOST_TOOLCHAIN_DIR HOST_TOOLCHAIN_BIN TARGET_SYSROOT_DIR TEST_ARTIFACTS_DIR
+$(foreach v,$(_install_dir_vars),$(if $($v),,$(error $v is empty — check manifests/install-dirs.lock.toml and tools/infra/paths.py)))
```

**make -p 六变量证据**：
```
REPO_ROOT => REPO_ROOT := /mnt/tao/DADAO-v5
SDK_DIR => SDK_DIR := /mnt/tao/DADAO-v5/.dadao
HOST_TOOLCHAIN_DIR => HOST_TOOLCHAIN_DIR := /mnt/tao/DADAO-v5/.dadao/cross-toolchain
HOST_TOOLCHAIN_BIN => HOST_TOOLCHAIN_BIN := /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin
TARGET_SYSROOT_DIR => TARGET_SYSROOT_DIR := /mnt/tao/DADAO-v5/.dadao/dadao-unknown-elf
TEST_ARTIFACTS_DIR => TEST_ARTIFACTS_DIR := /mnt/tao/DADAO-v5/.dadao/tests
（各自独立成行、值正确）
```

**非空自检反例**：
```
$ echo 'format = 1' > manifests/install-dirs.lock.toml && make -n check > log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=2
Makefile:23: *** SDK_DIR is empty — check manifests/install-dirs.lock.toml and tools/infra/paths.py.  Stop.
```

**反例 A/B/C 复验**：
- A：`EXIT=1`（symlink prefix 检出）→ 复原 byte-identical ✅
- B：`EXIT=1`（绝对路径拒绝）→ 复原 byte-identical ✅
- C：`EXIT=1`（越界路径拒绝）→ 复原 byte-identical ✅

**make check**：
```
$ make check > log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
check-dirs: PASS
repository checks: PASS
```

**git diff --name-only**：`Makefile`（仅此一文件被修改）

**判决**：所有 finding 已修复，标「待验收」

#### 第 2 轮 reviewer 复核

**审查者**：reviewer 子代理（独立重跑，不采信完成区）
**证据目录**：`/tmp/opencode/INFRA-019t-r2-review/`
**范围**：仅复核第 1 轮唯一阻断项（Makefile 变量派生）+ 回归抽查，未重复已过项。

##### 1. 重跑记录（真实输出 / 退出码）

**核验点 1（六变量各自独立成行、值正确）— 通过 ✓**
```
$ make -p 2>/dev/null > make-p.txt; echo EXIT=$?   → EXIT=0
$ for v in REPO_ROOT SDK_DIR HOST_TOOLCHAIN_DIR HOST_TOOLCHAIN_BIN TARGET_SYSROOT_DIR TEST_ARTIFACTS_DIR; do
    n=$(grep -c "^$v *:=" make-p.txt); ... done
REPO_ROOT          : count=1 : REPO_ROOT := /mnt/tao/DADAO-v5
SDK_DIR            : count=1 : SDK_DIR := /mnt/tao/DADAO-v5/.dadao
HOST_TOOLCHAIN_DIR : count=1 : HOST_TOOLCHAIN_DIR := /mnt/tao/DADAO-v5/.dadao/cross-toolchain
HOST_TOOLCHAIN_BIN : count=1 : HOST_TOOLCHAIN_BIN := /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin
TARGET_SYSROOT_DIR : count=1 : TARGET_SYSROOT_DIR := /mnt/tao/DADAO-v5/.dadao/dadao-unknown-elf
TEST_ARTIFACTS_DIR : count=1 : TEST_ARTIFACTS_DIR := /mnt/tao/DADAO-v5/.dadao/tests
```
六变量均**独立成行**（count=1，无第 1 轮的单行拼接污染），值正确、绝对 realpath。

`--eval` 探针（引用即取值的真实路径，非 grep 假象）：
```
REPO_ROOT=[/mnt/tao/DADAO-v5]  SDK_DIR=[/mnt/tao/DADAO-v5/.dadao]
HOST_TOOLCHAIN_DIR=[/mnt/tao/DADAO-v5/.dadao/cross-toolchain]
HOST_TOOLCHAIN_BIN=[/mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin]
TARGET_SYSROOT_DIR=[/mnt/tao/DADAO-v5/.dadao/dadao-unknown-elf]
TEST_ARTIFACTS_DIR=[/mnt/tao/DADAO-v5/.dadao/tests]   PROBE_EXIT=0
```
第 1 轮阻断项（其余 5 变量为空串）确已修复。

**核验点 2（非空自检可失败）— 通过 ✓**（我亲自破坏 manifest，非采信）
```
缺失键：$ echo 'format = 1' > manifests/install-dirs.lock.toml; make -n check > log 2>&1; rc=$?; echo EXIT=$rc
  EXIT=2
  ERROR: missing key 'sdk_dir' in .../manifests/install-dirs.lock.toml  (×5)
  Makefile:23: *** SDK_DIR is empty — check manifests/install-dirs.lock.toml and tools/infra/paths.py.  Stop.
manifest 整文件缺失：$ mv ...; make -n check; echo EXIT=$?
  EXIT=2   ERROR: manifest not found: /mnt/tao/DADAO-v5/manifests/install-dirs.lock.toml
           Makefile:23: *** SDK_DIR is empty — ... Stop.
复原：diff -q 备份 通过；sha256 = 650021ecafc56c69d38c34cea2f1c0393e4a927339f855dc49609f01e1e84d0f（与改前一致，byte-identical）
```

**核验点 3（反例 A/B/C 仍可失败 + 复原）— 通过 ✓**（每例自取退出码 `>log 2>&1; rc=$?`）
```
反例 A（往 tracked tools/infra/doctor.py 追加 /home/ubuntu/tao/...）:
  EXIT=1  ERROR: tools/infra/doctor.py:210: contains symlink prefix '/home/ubuntu/tao'
  复原：git checkout -- ；sha256sum -c 通过；git status 该文件空（byte-identical）
反例 B（target_sysroot_dir = "/opt/x"）:
  EXIT=1  ERROR: ... must be relative, got '/opt/x'
          ERROR: ... '/opt/x' is not under sdk_dir='.dadao'
  复原：diff -q 通过
反例 C（target_sysroot_dir = ".other/x"）:
  EXIT=1  ERROR: ... '.other/x' is not under sdk_dir='.dadao'
  复原：diff -q 通过
复原后 manifest sha256 = 650021ec...（三例共用一个备份，最终一致）
```

**核验点 4（make check EXIT=0 + 零行为变化）— 通过 ✓**
```
$ make check > make-check.log 2>&1; rc=$?; echo EXIT=$rc   → EXIT=0
  check-dirs: PASS
  Results: 146 total, 146 passed, 0 failed, 0 errors
  总计 80 项 | PASS: 80 | FAIL: 0   repository checks: PASS
$ git diff --stat  → Makefile | 26 ++++--; 1 file changed, 24 insertions(+), 2 deletions(-)
$ git diff --name-only  → Makefile
$ git status --porcelain  → M Makefile + 3 新增(untracked) + 任务书；tests/vectors/ 空
```
Makefile 改动全为**追加**：新增 6 变量 + `_install_dir_vars` 自检、`check-dirs` 加入 `.PHONY` 与 `check` 依赖、新增 `check-dirs` 规则、help 一行。`grep` 确认这 6 个变量名在 Makefile 中**无其它既有定义/引用**（无遮蔽、无行为改变）；`.dadao/` `.work/` `.cache/` 无跟踪条目、内容未被移动。

##### 2. 约束核验（逐条）

| 第 2 轮确认项 | 结论 | 证据 |
|---|---|---|
| ① 六变量独立成行且值正确 | ✓ | `make -p` count=1×6；`--eval` 探针全非空 |
| ② 非空自检可失败 + byte-identical 复原 | ✓ | 缺键/缺文件均 EXIT=2；sha256 复原一致 |
| ③ 反例 A/B/C 可失败 + 复原；make check EXIT=0 | ✓ | A/B/C 均 EXIT=1；复原 byte-identical；make check EXIT=0 |
| ④ 仅 `Makefile`（+任务书）改动；零行为变化 | ✓ | `git diff --name-only`=Makefile；纯追加，无既有引用 |
| ⑤ 无其它返工项 | ✓ | 第 1 轮过项未回归（make check 全绿、目录未移动） |

##### 3. 判决：**Accepted**

第 1 轮唯一阻断项（`$(eval $(shell …))` 换行折叠致 5 变量为空）已按建议改为**逐变量单次 `$(shell … <key>)`**，并新增 parse-time 非空自检——我独立重跑确认六变量独立成行、探针全非空、自检在缺键/缺文件时均以 EXIT=2 fail-closed。反例 A/B/C 仍真实失败且复原 byte-identical，`make check` EXIT=0，改动范围仅 `Makefile`（纯追加、零行为变化）。**无未决阻断项，判 Accepted**；主会话可将任务状态改为 `已验证`，终审仍归架构师。

**reviewer 未采信、仅核对项**：完成区所贴 `make -p` 输出、非空自检 EXIT=2、反例 A/B/C 输出与复原、`git diff --name-only` 均与我的独立重跑一致，未发现转述/美化。


#### 主会话收尾（2026-10-02）

1. **提交推送**：`manifests/install-dirs.lock.toml` + `tools/infra/paths.py` + `tools/infra/check_dirs.py` + `Makefile`（见 git log）。
2. **过程**：reviewer 第 1 轮 Needs Revision —— `$(eval $(shell … --make))` 因 `$(shell)` 折叠换行致 **5 个变量为空（静默失败）**，且完成区把该缺陷证据当通过 ⇒ 返工为**逐变量 `$(shell … <key>)` + parse-time 非空自检**，第 2 轮 **Accepted**（六变量独立、自检可失败、A/B/C 真失败 + byte-identical 复原）。
3. **遗留**：无。
