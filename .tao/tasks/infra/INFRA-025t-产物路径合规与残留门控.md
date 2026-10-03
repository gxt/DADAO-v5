# INFRA-025t: 产物路径合规与残留门控

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：INFRA-019t（安装产物路径定位机制，已验证）、INFRA-020t（参考仓库迁移，已验证）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 问题背景

ADR-0016 D6 约定「测试向量运行产物根 = `.dadao/tests/`」，D7 约定「新增脚本/目标必须经 `tools/infra/paths.py`，禁止硬编码」。实测发现多处违反：

1. **QEMU harness 产物落 `/tmp`**：`tests/scripts/run_qemu_test.py:242` 用 `tempfile.mkstemp` 生成测试二进制，`:274` 用 `tempfile.mktemp` 生成 QMP socket，`:353` 硬编码 `/tmp/opencode/QEMU-014t` 做 dump 目录——全部绕过 D6。
2. **Makefile 门控落 `/tmp`**：`:287` `QEMU_SEM_DIR = /tmp/opencode/qemu-sem-gate`，`:293` 日志落 `/tmp/opencode/check-qemu-sem.log`——违反 `.tao/README.md` 的 `.work/log/<模块>/` 约定。
3. **探针脚本产物落 `/tmp`**：`tools/qemu/min_rom_probe_*.py`（至少 `031t.py:226`）用 `tempfile.mkstemp` 生成探针二进制——绕过 D6。
4. **残留门控缺失**：仓库内无机制检测非预期未跟踪临时文件（`*_tmp*`、`_gate*`、`*.orig`、`*.rej`）。
5. **`.gitignore` 不全**：缺 `*_tmp*/`、`*.orig`、`*.rej`。
6. **`check_asm_prose.py` 无 `--root`**：反例测试无法在 `/tmp/opencode/<任务ID>/` 构造，必须在仓库内创建临时文件。

## 目的

将所有 QEMU 运行产物（测试二进制、QMP dump/socket、门控临时目录、门控日志）归位到 ADR-0016 D6 合规路径，补全 `.gitignore`，新增残留门控，为 `check_asm_prose.py` 加 `--root`，并在 `AGENTS.md` 固化子代理硬约束清单。

## 接口规范

### 输入
- `tools/infra/paths.py`：`test_artifacts_dir()` → `Path`（绝对路径，`/mnt/tao/DADAO-v5/.dadao/tests`）
- `manifests/install-dirs.lock.toml`：`test_artifacts_dir = ".dadao/tests"`（D6 唯一真源）
- `.tao/README.md`：日志留存约定（`.work/log/<模块>/`）

### 输出（变更文件清单）

| # | 文件 | 变更 |
|---|------|------|
| 1 | `tests/scripts/run_qemu_test.py` | 测试二进制 → `test_artifacts_dir() / "harness" / <filename>`；QMP socket → 同目录；QMP dump → 同目录子目录；函数结束时自清理临时文件（保留 dump）。新增内部函数 `_resolve_artifact_dir()` 调用 `paths.test_artifacts_dir()`。 |
| 2 | `tools/qemu/min_rom_probe_*.py`（全部 12 个） | 探针二进制 → `test_artifacts_dir() / "probes" / <filename>`；函数结束时自清理。新增内部 helper `_probe_artifact_dir()` 调用 `paths.test_artifacts_dir()`。 |
| 3 | `Makefile` | `QEMU_SEM_DIR` 从 `/tmp/opencode/qemu-sem-gate` 改为 `$(TEST_ARTIFACTS_DIR)/harness/gate`；门控日志从 `/tmp/opencode/check-qemu-sem.log` 改为 `.work/log/qemu/check-qemu-semantics.log`；收尾/失败时 `rm -rf $(QEMU_SEM_DIR)`。 |
| 4 | `tools/spec/check_asm_prose.py` | 新增 `--root` 参数（默认 `None` = 现有行为，扫描 repo 内）；`--root` 非空时 `collect_files()` 从该根扫描（替代 `ROOT`），`--files` 解析也基于该根；`--strict` 语义不变；保持 fail-closed（`--files` 作用域外仍非零退出）。 |
| 5 | `tools/infra/check_dirs.py` | 扩展：新增 `check_residue(root)`，用 `git ls-files --others --exclude-standard` 扫非预期未跟踪文件，匹配 `*_tmp*`/`*_gate*`/`*.orig`/`*.rej`；白名单 `.tao/tasks/**`、`.work/**`。**须支持 `--root <dir>`（默认仓库根）**；反例验证一律在 `/tmp/opencode/INFRA-025t/` 下构造——**严禁在仓库内注入反例文件**（那正是本任务要禁的行为）。 |
| 6 | `Makefile` | 新增 `check-no-residue` target，调用 `check_dirs.py --residue`；可并入现有 `check-dirs`（由 `check` 统一调用）。 |
| 7 | `.gitignore` | **不**加入 `*_tmp*/`、`*.orig`、`*.rej`（否则 `git ls-files --others --exclude-standard` 看不到 → 门控漏检）；残留由 `check-no-residue` 负责检出。保留既有 `*.tmp`/`*.log`。 |
| 8 | `AGENTS.md` | 新增「子代理硬约束（下发提示必带）」节，引用既有规则、列出最小清单（见下方「子代理硬约束清单」）。 |

### 约束

- **不改测试语义**：仅变更产物/日志/临时落点与门控逻辑；`check-qemu-semantics` 仍须 149/149 或如实报差异。
- **D6 路径经 `paths.py`**：所有新增/修改的路径解析必须调用 `tools/infra/paths.py` 的 `test_artifacts_dir()`，禁止硬编码。
- **自清理**：临时文件（测试二进制、QMP socket）在函数 `finally` 块中删除；dump 文件保留（供调用方使用）。
- **串行标注**：本任务改 `Makefile`、`.gitignore`、`AGENTS.md`——与同改这些文件的任务串行。
- **临时产物**：本任务的验证/调试产物放 `/tmp/opencode/INFRA-025t/`。
- **不改 ADR / 不改 `spec/SimRISC-0.5.3/`**。

### 子代理硬约束清单（写入 AGENTS.md）

每次 `/dispatch` 提示**必须内联**的最小清单（引用既有规则，不重复定义）：

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件（→ AGENTS.md「临时目录」）
2. 不提交 git（→ AGENTS.md「提交确认」）
3. 完成区与真实输出逐条对齐（→ AGENTS.md「验证脚本反例门控 / 完成区结论须与真实输出逐条对齐」）
4. 只动任务书范围，越界须披露（→ AGENTS.md「外科手术式修改」）
5. 失败即停，禁自动重试（→ 全局「最小安全设计 / 可恢复」）
6. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥（→ AGENTS.md「组件补丁」）
7. 复杂命令输出留存 `.work/log/<模块>/`（→ `.tao/README.md`「日志留存」）

## 验收标准

1. **D6 接线验证**：
   ```bash
   # 确认 run_qemu_test.py 的产物路径在 .dadao/tests/ 下
   grep -n 'test_artifacts_dir\|paths\.test_artifacts' tests/scripts/run_qemu_test.py
   # 确认无残留的 tempfile.mkstemp/mktemp 调用（dump 用的 mkdtemp 除外）
   grep -n 'tempfile\.mkstemp\|tempfile\.mktemp' tests/scripts/run_qemu_test.py
   # 期望：0 匹配（mkstemp/mktemp 已移除；mkdtemp 仅用于 dump 且路径在 test_artifacts_dir 下）
   ```

2. **探针脚本验证**：
   ```bash
   grep -rn 'tempfile\.mkstemp\|tempfile\.mktemp' tools/qemu/min_rom_probe_*.py
   # 期望：0 匹配（已改用 paths.test_artifacts_dir()）
   ```

3. **Makefile 门控路径验证**：
   ```bash
   grep -n 'QEMU_SEM_DIR\|check-qemu-sem' Makefile
   # 期望：QEMU_SEM_DIR 引用 $(TEST_ARTIFACTS_DIR)，日志引用 .work/log/qemu/
   # 确认无 /tmp/opencode 残留
   grep -n '/tmp/opencode' Makefile
   # 期望：0 匹配
   ```

4. **`check_asm_prose.py --root` 验证**：
   ```bash
   # 创建反例目录
   mkdir -p /tmp/opencode/INFRA-025t/prose-test
   echo '```simrisc' > /tmp/opencode/INFRA-025t/prose-test/bad.md
   echo 'ld.ub rd8, rb0, 0' >> /tmp/opencode/INFRA-025t/prose-test/bad.md
   echo '```' >> /tmp/opencode/INFRA-025t/prose-test/bad.md
   # 运行 --root 指向反例目录
   python3 tools/spec/check_asm_prose.py --strict --root /tmp/opencode/INFRA-025t/prose-test
   # 期望：exit 1 + 报告 R1(访存缺[]) 违规
   echo "EXIT=$?"
   ```

5. **残留门控验证**：
   ```bash
   # 在 /tmp 下构造反例根（**不得**在仓库内注入）
   R=/tmp/opencode/INFRA-025t/residue-root
   rm -rf "$R" && mkdir -p "$R" && (cd "$R" && git init -q && git commit -q --allow-empty -m init)
   touch "$R/test_tmp_residue" "$R/test_gate_residue"
   python3 tools/infra/check_dirs.py --residue --root "$R"
   # 期望：exit 1 + 报告上述两个文件
   # 另验：仓库根（默认 root）必须是 exit 0（干净）：
   python3 tools/infra/check_dirs.py --residue ; echo "REPO_ROOT_EXIT=$?"
   # 期望：REPO_ROOT_EXIT=0
   ```

6. **`.gitignore` 验证**：
   ```bash
   grep -n '_tmp\|\.orig\|\.rej' .gitignore
   # 期望：1 匹配（不含 *_tmp*/、*.orig、*.rej；仅有 *.tmp 等既有条目）
   ```

7. **`make check` 保持绿**（不改变测试语义）：
   ```bash
   make check 2>&1 | tail -20
   # 期望：exit 0，所有门控 PASS（check-qemu-semantics 仍 149/149 或如实报差异）
   ```

8. **反例验证（check_dirs.py 残留门控能失败）**：
   ```bash
   # 注入反例
   mkdir -p /tmp/opencode/INFRA-025t/residue-test
   cd /tmp/opencode/INFRA-025t/residue-test
   git init && git commit --allow-empty -m init
   echo "test" > foo_tmp_bar
   python3 /mnt/tao/DADAO-v5/tools/infra/check_dirs.py --residue --root /tmp/opencode/INFRA-025t/residue-test
   # 期望：exit 1 + 报告 foo_tmp_bar
   # （注：如 --residue 不支持 --root，则在仓库根注入验证，见验收 5）
   ```

9. **AGENTS.md 验证**：
   ```bash
   grep -A 20 '子代理硬约束' AGENTS.md | head -25
   # 期望：包含 7 条硬约束清单，每条引用既有规则路径
   ```

## 完成区
**测试结果**：通过 149/149 QEMU 语义测试；25/25 lit 测试；所有门控 PASS
**修改文件**：18 个文件
- `tests/scripts/run_qemu_test.py` — 移除 `tempfile`，改用 `_resolve_artifact_dir("harness")` + `uuid` 直接写文件
- `tools/qemu/min_rom_probe_*.py`（12 个）— 新增 `_probe_artifact_dir()` helper，所有 `NamedTemporaryFile`/`mkstemp` 加 `dir=_probe_artifact_dir()`
- `tools/spec/check_asm_prose.py` — 新增 `--root` 参数，`collect_files(root)` 支持 `--root` 模式扫描任意目录
- `tools/infra/check_dirs.py` — 新增 `check_residue()` + `--residue`/`--root` 参数
- `Makefile` — `QEMU_SEM_DIR` → `$(TEST_ARTIFACTS_DIR)/harness/gate`；日志 → `.work/log/qemu/check-qemu-semantics.log`；收尾/失败 `rm -rf`；新增 `check-no-residue` target
- `.gitignore` — 不加入 `*_tmp*/`/`*.orig`/`*.rej`（否则门控漏检）；保留既有 `*.tmp`/`*.log`
- `AGENTS.md` — 新增「子代理硬约束（下发提示必带）」节（7 条）

**验收结果**：
```
验收 1 (D6 接线): grep -n 'tempfile\.mkstemp\|tempfile\.mktemp' tests/scripts/run_qemu_test.py → 0 匹配 ✓
验收 2 (探针脚本): grep -rn 'tempfile\.mkstemp\|tempfile\.mktemp' tools/qemu/min_rom_probe_*.py → 0 匹配 ✓
验收 3 (Makefile): grep -n '/tmp/opencode' Makefile → 0 匹配 ✓; QEMU_SEM_DIR = $(TEST_ARTIFACTS_DIR)/harness/gate ✓
验收 4 (check_asm_prose --root): --strict --root /tmp/.../bad.md → exit 1 + R1(访存缺[]) ✓
验收 5 (残留门控): --residue --root /tmp/.../residue-root → exit 1 + 报告 test_tmp_residue, test_gate_residue ✓
        --residue (repo root) → exit 0 ✓
验收 6 (.gitignore): grep '_tmp\|\.orig\|\.rej' → EXIT=1（不含这三类；仅保留 *.tmp/*.log） ✓
验收 7 (make check): exit 0, check-qemu-semantics 149/149 PASS, check-lit 25/25, check-no-residue PASS ✓
验收 8 (反例验证): --residue --root /tmp/.../residue-test (含 foo_tmp_bar) → exit 1 + 报告 ✓
验收 9 (AGENTS.md): 包含 7 条子代理硬约束清单 ✓
```

**新发现/坑**：
1. `tempfile.mkstemp`/`mktemp` 的 `dir=` 参数可以指向自定义目录，但任务要求"0 匹配"意味着不能出现这些函数名，因此改用 `uuid` + 直接写文件
2. `check_asm_prose.py` 的 `_load_opcode_formats()` 和 `_load_cfx_aliases()` 始终从 `ROOT`（repo root）加载，`--root` 只影响文件扫描范围——这是正确的设计（合约数据不在 override root 中）
3. `check_dirs.py` 的 `--residue` 模式在 `--root` 下不应用白名单（`.tao/tasks`、`.work`），因为 override root 不是仓库根
4. 探针脚本中 `NamedTemporaryFile` 仍然使用 `tempfile` 模块（只是加了 `dir=`），但 `tempfile.mkstemp`/`mktemp` 显式调用已全部移除
5. **设计矛盾修正**（reviewer 指出）：`.gitignore` 加 `*_tmp*/`/`*.orig`/`*.rej` → `git ls-files --others --exclude-standard` 看不到 → 门控静默漏检。修正：**不向 `.gitignore` 加入这三类**，残留由 `check-no-residue` 负责检出。`*.tmp`/`*.log` 是既有条目且不在门控模式内，保留不动
6. git 不追踪空目录：`*_tmp*` 目录型残留需目录内有文件才能被门控检出（路径匹配，如 `d_tmp_x/placeholder`）

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：全部 18 个修改文件的逐行审查

**发现**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `import uuid` 在函数体内（风格不佳） | ✅已修 | 移至文件顶部 import 区 | python3 -m py_compile 通过 |
| 2 | `tempfile` import 残留在 `run_qemu_test.py`（已无使用） | ✅已修 | 删除 `import tempfile` | grep -c tempfile = 1（仅注释） |
| 3 | `min_rom_probe_031t.py` `import tempfile` 残留 | ✅已修 | 替换为 `import uuid` | grep tempfile 返回空 |
| 4 | `_probe_artifact_dir` 无 docstring | ⏸延后 | — | 不影响功能，探针脚本风格一致 |
| 5 | `check_dirs.py` 白名单在 `--root` 模式下跳过 | ✅设计确认 | — | 验收 5 中 --root 正确检测仓库外反例 |

**判决**：所有 finding 已处置，可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：18 个改动文件 + 任务书验收 1–9；审查基线 = HEAD `1c2156a`（改动未提交）。
**证据留存**：`/tmp/opencode/INFRA-025t-review/`（reviewer 自建，含各命令原始输出）。
**对照基线**：为核对 `check_asm_prose.py` 改前行为，用 `git worktree add --detach /tmp/opencode/INFRA-025t-review/orig-worktree HEAD` 取纯净 HEAD 树（审查后已 `git worktree remove` + `prune`，`git worktree list` 仅剩主树），**未在仓库内注入任何反例文件**。

---

##### 1. D6 接线（关键）—— PASS

命令（清空 `.dadao/tests`，以哨兵 `TMPDIR` 证明不落系统临时目录）：
```bash
rm -rf .dadao/tests
TMPDIR=/tmp/opencode/INFRA-025t-review/tmpdir-sentinel \
  python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml
```
真实输出/退出码：
- `EXIT=0`，末行 `Result: PASS / Test passed`。
- 跑后 `find .dadao/tests` → 仅 `.dadao/tests/harness`（**空**，无 `.bin`/`.sock` 残留 ⇒ 自清理成立）。
- 哨兵 `TMPDIR` 目录仍为空；`find /tmp /var/tmp -type f \( -name 'dadao-test-*' -o -name 'dadao-qmp-*' -o -name 'dadao-probe-*' \)` → **NONE**（排除本人留证目录）⇒ **未落 `$TMPDIR`**。

dump 保留（`--case 1 --dump`）：
- `find .dadao/tests` → `.dadao/tests/harness/dumps/state.bin`（dump 按设计保留），且无 `.bin` 残留。该用例本身 `INCONCLUSIVE`（dump 模式既有行为），非本任务回归。

`make check-qemu-semantics`：
```bash
make check-qemu-semantics   # EXIT=0
# 输出：Running batch tests from /mnt/tao/DADAO-v5/.dadao/tests/harness/gate...
#       Results: 149 total, 149 passed, 0 failed, 0 deferred, 0 errors
#       check-qemu-semantics: PASS
```
跑后 `.dadao/tests/harness/gate` **不存在**（收尾 `rm -rf` 生效）；日志 `.work/log/qemu/check-qemu-semantics.log` 存在且内容为本次 149/149 结果。**验收 1 通过。**

##### 2. 探针脚本 —— PASS

```bash
python3 tools/qemu/min_rom_probe_031t.py   # EXIT=0
# Exit code: 0x00 PASS  （Probe 1、Probe 2 均 PASS）
```
跑后 `.dadao/tests/probes/` 为空（自清理）；哨兵 `TMPDIR` 为空。**12 个** `min_rom_probe_*.py` 的 diff 逐文件核对：全部为「新增 `_REPO_ROOT`+`import paths`+`_probe_artifact_dir()`；`NamedTemporaryFile(..., dir=...)` 或 `mkstemp`→`uuid` 直写」——**无逻辑/断言改动**（抽查 031t/030t/013t 的 `try/finally os.unlink` 自清理仍在）。**验收 2 通过。**

##### 3. Makefile 门控 —— PASS

```bash
grep -n '/tmp/opencode' Makefile          # 0 匹配（exit 1）
grep -n 'QEMU_SEM_DIR\|check-qemu-sem' Makefile
```
真实输出：`QEMU_SEM_DIR = $(TEST_ARTIFACTS_DIR)/harness/gate`（第 293 行，`TEST_ARTIFACTS_DIR := $(shell $(PYTHON) tools/infra/paths.py test_artifacts_dir)`）、`QEMU_SEM_LOG = .work/log/qemu/check-qemu-semantics.log`（294）、收尾与失败分支均有 `rm -rf $(QEMU_SEM_DIR)`（305/308）。`make check-qemu-semantics` **149/149**（见上）。**验收 3、验收 7（149/149 部分）通过。**

##### 4. `check_asm_prose.py --root` —— PASS

- **改前/改后默认行为一致**：在纯净 HEAD worktree 与原仓库分别跑 `python3 tools/spec/check_asm_prose.py`（及 `--strict`），stdout `diff` **IDENTICAL**，退出码均 `0`（`check-asm-prose: PASS (0 violations)`）。
- **坏例**：`--strict --root /tmp/.../prose-test`（`ld.ub rd8, rb0, 0`）→ **EXIT=1** + `L2: [R1(访存缺[])]`。
- **好例**：`--strict --root /tmp/.../prose-good`（`ld.ub rd8, [rb0, 0]`）→ **EXIT=0** PASS。
- **fail-closed 仍在**：默认 `--files README.md` → **EXIT=1** + `--files argument outside scan scope`（与 HEAD 基线除 ROOT 字样外一致）；`--root <root> --files /etc/hosts` → **EXIT=1**；`--root <root> --files bad.md`（作用域内坏例）→ **EXIT=1** + R1。
- **作用域隔离**：`--root` 指向空目录 → EXIT=0（不误扫仓库）；嵌套 `sub/deep/*.md` 递归命中且以 override root 相对路径报告。**验收 4 通过。**

##### 5. `check_dirs.py --residue` —— PASS

- 脏仓库（`/tmp/.../residue-root`，`git init` 后 `touch test_tmp_residue test_gate_residue x.orig y.rej`）：
  `python3 tools/infra/check_dirs.py --residue --root "$R"` → **EXIT=1**，逐条报告上述 4 个文件。
- 干净仓库 → **EXIT=0** `check-no-residue: PASS`。
- **白名单正确**：在临时根（拷贝 `check_dirs.py` 使 `ROOT`=该临时根，**默认模式**）放置 `.tao/tasks/infra/my_tmp_task.md`、`.work/x_gate_y`、`stray_tmp_file` → **EXIT=1，仅报告 `stray_tmp_file`**，`.tao/tasks/**`、`.work/**` 未被误报。
- 仓库根：`python3 tools/infra/check_dirs.py --residue` → **EXIT=0**；`make check-no-residue` → **EXIT=0** PASS。
- fail-closed：非 git 根 → EXIT=1（`git ls-files ... not a git repository`）；`--root` 不存在 → EXIT=1。**验收 5、验收 8 通过。**

##### 6. `.gitignore` / `AGENTS.md` —— PASS

- `.gitignore` 第 25–27 行含 `*_tmp*/`、`*.orig`、`*.rej`。
- `AGENTS.md` 第 152–162 行「子代理硬约束（下发提示必带）」含 7 条，与任务书清单逐字一致；引用锚点经核对均存在：`## 临时目录`、`提交确认`、`外科手术式修改`、`组件补丁`、`验证脚本反例门控`、全局 `最小安全设计`、`.tao/README.md`「日志留存」。**验收 6、验收 9 通过。**

##### 7. 全量回归 —— PASS

```bash
make check   # MAKE_CHECK_EXIT=0
```
日志关键行：`Results: 149 total, 149 passed, 0 failed`、`check-qemu-semantics: PASS`、`check-dirs: PASS`、`check-no-residue: PASS`、lit `Total Discovered Tests: 25 / Passed: 25 (100.00%)`、`repository checks: PASS`（`FAIL` 计数行均为 validator 的 `FAIL: 0`）。`git status` 仅 18 个改动文件 + 新增任务书，**未触及 `spec/`、`contracts/`、`tests/vectors/`** ⇒ **无测试语义改变**。**验收 7 通过。**

##### 8. 证据/范围 —— PASS（附一条设计警示）

- `git status --porcelain`：18 × `M`（`.gitignore`/`AGENTS.md`/`Makefile`/`run_qemu_test.py`/`check_dirs.py`/`check_asm_prose.py`/12 探针）+ 1 × `??`（本任务书）。`git ls-files --others --exclude-standard` 无 `*_tmp*`/`*_gate*`/`*.orig`/`*.rej` 残留；仓库内无临时注入（反例全在 `/tmp` 构造）。
- `/tmp` 及 `/var/tmp` 无 `dadao-test-*`/`dadao-qmp-*`/`dadao-probe-*` 落点。
- 完成区各条与本次独立重跑逐条对齐，未发现不实/夸大。

---

##### ⚠ 设计层矛盾（供架构师定夺，非本轮验收项失败）

发现任务书两项要求互相抵触，导致残留门控的两类图案**在仓库内实际不可达**：

- 任务要求门控用 `git ls-files --others --exclude-standard` 匹配 `*.orig`/`*.rej`/`*_tmp*`；
- 同一任务又要求 `.gitignore` 补 `*.orig`、`*.rej`、`*_tmp*/`。

`--exclude-standard` 会**排除被 .gitignore 忽略的文件**，故在采用本仓库 `.gitignore` 的仓库中：`a.orig`/`b.rej` 与 `foo_tmp_bar/` 目录**不会**出现在 `git ls-files --others --exclude-standard` 里，门控对它们**静默漏检**。我的实证（临时 git 仓库，复制仓库 `.gitignore`）：
```
$ git ls-files --others --exclude-standard
c_tmp_file
d_gate_file                        # a.orig / b.rej 未出现
$ python3 tools/infra/check_dirs.py --residue --root "$GI"
ERROR: residue: unexpected untracked file: c_tmp_file
ERROR: residue: unexpected untracked file: d_gate_file   # 未报 a.orig/b.rej
```
任务书验收 5 的 `/tmp` 反例仓库**未带 `.gitignore`**，因此四个图案“看起来”都被检出——这掩盖了上述冲突（若不复制 `.gitignore`，无法暴露）。对照问题背景第 4 条「仓库内无机制检测 … `*.orig`、`*.rej`」，门控在仓库内**并未**真正获得对这两类（及 `*_tmp*` 目录）的检测能力。

**建议处置（需架构师裁决，二选一）**：
- (a) 从 `.gitignore` 移除 `*.orig`/`*.rej`（及目录型 `*_tmp*/` 若也要求门控兜底），使它们对 `git status`/门控可见；或
- (b) 明确由 `.gitignore` 承担对 `*.orig`/`*.rej` 的处置（不可提交），接受门控对这两类的匹配为冗余死分支，并**在任务书/知识库注明**，同时精简门控图案以免误导。

---

##### 判决

**Accepted**（就任务书验收 1–9 与全部硬约束而言，逐条重跑通过；完成区结论属实）。
但附带上述**设计层矛盾**：请架构师在裁决前，勿将本任务视为「残留门控对 `*.orig`/`*.rej`（及 `*_tmp*` 目录）在仓库内具备检测能力」——当前不具备；该点建议按 (a)/(b) 收口或另立后续任务。

#### 第 2 轮 engineer 自审（返工修正）

**触发**：reviewer 指出设计矛盾——`.gitignore` 加 `*_tmp*/`/`*.orig`/`*.rej` 导致门控静默漏检。

**修法**：从 `.gitignore` 移除这 3 行（最小改动）；更新任务书 item 7 和验收 6 描述。

**改动**：
- `.gitignore`：去掉 `*_tmp*/`、`*.orig`、`*.rej`（保留既有 `*.tmp`/`*.log`）
- 任务书 item 7：改为「**不**加入这三类；残留由 `check-no-residue` 负责」
- 任务书验收 6：改为验证「**不含**这三类」

**重验结果**：

| # | 验证项 | 命令 | 真实输出 | 判定 |
|---|--------|------|---------|------|
| 1 | 门控检出 4 类残留（带 .gitignore） | `--residue --root` (a.orig, b.rej, c_gate_, d_tmp_x/placeholder) | EXIT=1, 报告全部 4 者 | ✅ |
| 2 | 仓库根无残留 | `make check-no-residue` | EXIT=0, check-no-residue: PASS | ✅ |
| 3 | 全量回归 | `make check` | EXIT=0, 149/149, 25/25 | ✅ |
| 4 | 仓库内无临时残留 | `git status --untracked-files=all` | 仅 18 个改动文件 + 任务书 | ✅ |

**判决**：设计矛盾已修正，全部重验通过。

#### 第 1 轮 reviewer 验收（复核设计矛盾修正后）

**审查范围**：`.gitignore` 去 3 行修正 + 残留门控全量重验 + `make check` 全量回归。

**核心变更**：`.gitignore` 原有 `*_tmp*/`、`*.orig`、`*.rej` 三行已移除（第 2 轮 engineer 自审返工）；残留由 `check-no-residue` 门控负责检出。

**重验**：
- `--residue --root`（带 `.gitignore` 的临时 git 仓库，含 `a.orig`/`b.rej`/`c_gate_file`/`d_tmp_x/placeholder`）→ **EXIT=1**，四类全部检出 ✓
- `make check-no-residue`（仓库根）→ **EXIT=0** PASS ✓
- `make check` → **EXIT=0**，149/149 QEMU、25/25 lit、check-no-residue PASS ✓

**判决**：**Accepted**。设计矛盾（`.gitignore` 与 `--exclude-standard` 互斥致门控漏检）已由 `.gitignore` 去 3 行修正；修正经主会话复现确认。18 个改动文件范围无夹带。

**追加记录（主会话复验，2026-10-03）**：主会话独立复现设计矛盾修正——在 `/tmp/opencode/INFRA-025t/` 构造带 `.gitignore` 的临时 git 仓库，确认 `git ls-files --others --exclude-standard` 对 `*.orig`/`*.rej`/`*_tmp*` 可见（`.gitignore` 已去这 3 行），`check_dirs.py --residue --root` 对四类残留全部 EXIT=1 报告。`make check` EXIT=0（149/149、25/25、check-no-residue PASS）。确认 Accepted。
