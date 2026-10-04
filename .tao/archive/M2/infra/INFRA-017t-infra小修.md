# INFRA-017t: infra 模块小修（deferred 遗留）

**模块**：infra
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 问题描述（来自 `deferred.md`）

1. **`fetch.py` 选源标签逻辑重复（DRY）**（`INFRA-009t` 遗留）：`main()` 为打印实际使用的源，**重新解析**了一遍 `COMPONENT_SOURCE_<NAME>` 与 `source[0]["name"]`，与 `select_source()` 内部逻辑重复（未来可能不同步）。建议：`select_source()` 返回 `(url, label)`，或在 `main()` 复用其解析结果。
2. **`check_spec_drift.py --test-mode` 判别力不足**（`INFRA-012t` reviewer）：4 个负测试中 `source_missing`/`source_bad_format` 在函数入口无条件 `return ("error", …)`，`version_mismatch`/`unknown_adr` 的注入点也在真实比对之前 ⇒ 只证明「能打印 FAIL」，**不证明能识别该 4 类真实缺陷**。建议：改为**基于临时 fixture 的真实负测试**（构造真实缺陷合约而非注入分支）。

## 约束

- 只做上述 2 项；不改 `fetch.py`/`check_spec_drift.py` 的正常行为
- 命令缺失 → 停下报告，禁止自行安装/下载
- 逐条核对，禁止正则批量替换
- 完成后 `make check` EXIT=0

## 验收标准

1. `fetch.py` 选源解析单一来源（无重复逻辑）；行为不变（`make fetch` 幂等/选源标签打印正确）
2. `check_spec_drift.py --test-mode` 的 4 类负测试改为**真实 fixture**；每类「构造真实缺陷 → exit 1」可复现
3. `make check` EXIT=0

## 完成区

**测试结果**：通过 4/4（fixture 负测试）；`make check` EXIT=0；`make fetch` 幂等 EXIT=0

**修改文件**：
- `tools/infra/fetch.py` — `select_source()` 改为返回 `(url, label)` 元组；`main()` 复用元组解包，移除重复的标签解析逻辑
- `tools/infra/check_spec_drift.py` — 移除 `classify_contract()` 的 `test_mode` 参数及全部 4 处注入短路代码；移除 `--test-mode`/`--test-contract` CLI 参数；更新 docstring
- `tools/infra/test_spec_drift_fixtures.py`（新建）— 独立 fixture 负测试脚本，构造真实缺陷合约验证 4 类检测

**验收结果**：
```
$ python3 tools/infra/test_spec_drift_fixtures.py
  [PASS] source_missing: exit=1 (缺陷被正确检测)
  [PASS] source_bad_format: exit=1 (缺陷被正确检测)
  [PASS] version_mismatch: exit=1 (缺陷被正确检测)
  [PASS] unknown_adr: exit=1 (缺陷被正确检测)
结果: 4/4 通过
spec drift fixture tests: ALL PASS

$ make check
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
repository checks: PASS
EXIT=0

$ make fetch
fetch: llvm-project using source 'sjtu' (https://mirror.sjtu.edu.cn/git/llvm-project.git)
fetch: mirror llvm-project.git already has 6dfe1677ab8d; skipping fetch
fetch: llvm-project already at 6dfe1677ab8dffbc6ec13d53a1e0215d75147689
fetch: qemu using source 'sjtu' (https://mirror.sjtu.edu.cn/git/qemu.git)
fetch: mirror qemu.git already has c3d48b7d1e89; skipping fetch
fetch: qemu already at c3d48b7d1e89604920e5b81b91140c2ad39a1943
EXIT=0
```

**新发现/坑**：
- fetch.py `select_source()` 之前只返回 url，导致 main() 为打印标签重复了整个 env/source 解析链；改为返回元组是最小修改
- check_spec_drift.py 的 `--test-mode` 注入代码在 classify_contract 入口无条件 return，绕过了实际检测逻辑；fixture 方式通过临时目录 + `--repo-root`/`--contract-dir` 等参数构造隔离环境，让真实代码路径运行
- fixture 测试脚本放在 `tools/infra/`（非 /tmp），因为它是可复用的验收工具

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：fetch.py select_source() 返回值改动 + check_spec_drift.py 注入代码移除 + test_spec_drift_fixtures.py 新建

**Findings**：

| # | 文件 | finding | 处置 | 改了什么 | 复验证据 |
|---|------|---------|------|---------|---------|
| 1 | check_spec_drift.py | docstring 仍引用 `--test-mode` | ✅已修 | 移除 Usage 中的 `--test-mode` 行 | 重新读取文件确认 |
| 2 | fetch.py | select_source() 所有路径均返回 tuple | ✅确认 | 无需改动 | 3 条 return 路径逐一核对 |
| 3 | check_spec_drift.py | classify_contract 4 处注入全清 | ✅确认 | 无需改动 | grep 确认无 test_mode 残留 |
| 4 | test_spec_drift_fixtures.py | 4 类 fixture 构造正确 | ✅确认 | 无需改动 | 运行 4/4 PASS |

**判决**：全部 finding 已修/确认，可标待验收。

#### 第 1 轮 reviewer 验收

**审查范围**：`tools/infra/fetch.py`（diff）、`tools/infra/check_spec_drift.py`（diff）、`tools/infra/test_spec_drift_fixtures.py`（新建，未跟踪）、任务书「完成区」与验收标准逐条比对。

##### 1. 重跑记录（全部为审查者本人执行；退出码用 `cmd; echo $?` 方式捕获）

**(a) fixture 负测试**
```
$ python3 tools/infra/test_spec_drift_fixtures.py
  [PASS] source_missing: exit=1 (缺陷被正确检测)
  [PASS] source_bad_format: exit=1 (缺陷被正确检测)
  [PASS] version_mismatch: exit=1 (缺陷被正确检测)
  [PASS] unknown_adr: exit=1 (缺陷被正确检测)

==================================================
结果: 4/4 通过
spec drift fixture tests: ALL PASS
EXIT=0
```

**(b) 逐类核对「exit=1 是因其自身缺陷，而非环境级失败」**（复用 fixture 生成函数，独立跑真实 checker 并打印 stdout）——每类错误信息均来自真实检测路径（**无** `负测试注入` 字样）：
```
### source_missing  EXIT=1
README 版本表: {'SimRISC': '0.5.4', 'AEE / ABI': '0.9.2'}
[FAIL] contract-empty.md
  ERROR: 无版本头（spec-sourced）且无 ADR 引用（adr-sourced）— 来源缺失

### source_bad_format  EXIT=1
[FAIL] contract-bad.md
  ERROR: 版本头找到 (0.5.4) 但无 spec 引用 [XXX-NN §...]

### version_mismatch  EXIT=1
[FAIL] contract-mismatch.md
  ERROR: 版本不匹配 — contract-mismatch.md: 合约版本 99.99.99 ≠ README 'SimRISC' 版本 0.5.4（映射: SimRISC-00 → README 组件 'SimRISC'）

### unknown_adr  EXIT=1
[FAIL] contract-unknown-adr.md
  ERROR: ADR 文件 adr-9999-*.md 不存在于 .../unknown_adr/.tao/knowledge
```

**(c) 正向控制（正常合约 → exit 0）**：审查者独立构造合法 fixture（spec-sourced `> **版本：0.5.4** [SimRISC-00 §测试]` + 存在 spec 文件；ADR-sourced 引用 `adr-9001-test.md` 状态 Accepted）：
```
[PASS] contract-ok-adr.md   ADR-sourced: adr-9001-test.md (状态: Accepted)
[PASS] contract-ok-spec.md  spec-sourced: 版本 0.5.4
── 结果: 检查 2 个合约，排除 1 个，错误 0 个 ──
spec drift check: PASS
EXIT=0
```
⇒ 证明 4 类 fixture 的 exit=1 具有判别力（不是「恒 1」）。

**(d) fixture 脚本「可达 FAIL 路径」证伪注入**：复制脚本、将 `CHECKER` 指向一个恒 `exit 0` 的桩：
```
  [FAIL] source_missing: exit=0 (期望 1)
  [FAIL] source_bad_format: exit=0 (期望 1)
  [FAIL] version_mismatch: exit=0 (期望 1)
  [FAIL] unknown_adr: exit=0 (期望 1)
结果: 0/4 通过
EXIT=1
```
⇒ 脚本能对「检测失效」报 FAIL 并 exit 非 0，非恒真脚本。

**(e) `make check`**
```
manifest validation: PASS
validate_vectors: 177/177 M1 identities covered OK
spec drift check: PASS          （3 合约全 PASS，0 错误）
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check_issues: 65 open, 9 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
```

**(f) `make fetch` 幂等 + 选源标签**
```
fetch: llvm-project using source 'sjtu' (https://mirror.sjtu.edu.cn/git/llvm-project.git)
fetch: mirror llvm-project.git already has 6dfe1677ab8d; skipping fetch
fetch: llvm-project already at 6dfe1677ab8dffbc6ec13d53a1e0215d75147689
fetch: qemu using source 'sjtu' (https://mirror.sjtu.edu.cn/git/qemu.git)
fetch: mirror qemu.git already has c3d48b7d1e89; skipping fetch
fetch: qemu already at c3d48b7d1e89604920e5b81b91140c2ad39a1943
EXIT=0
```
（重复运行幂等；标签 `'sjtu'` 与 URL 一致，行为与改动前相同。）

**(g) `select_source()` 返回值/标签逐路径核对**（直接导入模块调用，独立验证）：
```
default: ('https://mirror.sjtu.edu.cn/git/llvm-project.git', 'sjtu')
env=tuna: ('https://mirror.tuna/llvm.git', 'tuna')
env=canonical: ('https://canonical/llvm.git', 'canonical')
bad env: SystemExit -> fetch: COMPONENT_SOURCE_LLVM-PROJECT='nope' does not match any source ... (available: ['sjtu','tuna'])
no-sources: ('https://canonical/x.git', 'canonical')
no-sources env=canonical: ('https://canonical/x.git', 'canonical')
```
⇒ 3 条 return 路径（env 命中 / `source[0]` / 兜底 canonical）全部返回 `(url,label)` 元组，label 语义与旧 `main()` 内联解析完全一致。

**(h) 静态核对**：`python3 -m py_compile` 三文件 → OK；`grep` 全仓（排除 `.work`）无 `test_mode`/`--test-mode`/`--test-contract` 残留、无 `select_source` 其它调用点；`os` 仍在 fetch.py L107 使用（无孤儿导入）。

##### 2. 约束核验（逐条）

| 约束 | 结论 | 证据 |
|------|------|------|
| 只做 2 项，不改正常行为 | ✅ | `check_spec_drift.py` diff 仅删除 `--test-mode`/`--test-contract` CLI 与 4 处 `if test_mode==...` 短路分支，核心分类逻辑（版本头/spec 引用/版本比对/ADR 存在性）零改动；`fetch.py` 仅 `select_source` 改返回元组 + `main` 解包，打印逻辑语义等价（(g)） |
| `fetch.py` 解析单一来源（DRY） | ✅ | `main()` 中重复的 `env_key`/`env_val`/`sources[0]["name"]` 解析已删除（diff 确认），label 来自 `select_source()` 返回值 |
| 4 类负测试改真实 fixture，各自 exit=1 可复现 | ✅ | (a)(b) 真实缺陷合约 + 真实代码路径，非注入短路 |
| 反例可复原（不污染仓库） | ✅ | fixture 全程在 `tempfile.TemporaryDirectory` 内，未触碰仓库；审查者 `git status` 复核无新增改动 |
| 留证捕获被检命令自身退出码 | ✅ | 脚本用 `subprocess.run(...).returncode`，无管道；本审查用 `cmd; echo $?` |
| `make check` EXIT=0 | ✅ | (e) |
| 命令缺失停下报告 / 禁安装 | ✅ | 本轮无命令缺失，无安装行为 |
| 逐条核对、禁正则批量替换 | ⚠️无法完全证明 | diff 为逐条可读修改（非机械替换特征），无残留 |

##### 3. 非阻断观察（供架构师/后续参考，不影响本次判定）

- `test_spec_drift_fixtures.py` **未内置正向控制用例**（正常合约 → exit 0）。验收标准 #2 只要求 4 类负例，正向路径已由 `make check` 的真实合约（3 合约 PASS）与本审查 (c) 独立覆盖，故不构成失败；但若希望脚本自证判别力，建议补 1 个「合法合约 → exit 0」用例。
- 该 fixture 脚本**未接入 `make check`**（Makefile `check` 仅含 `check-spec-drift`）。任务未要求接入，仅作提示。
- 任务书「完成区」的 `make check` 输出为**节选**（省略 manifest/validate_vectors/check_issues 等行）。审查者逐行核对：所示各行（`spec drift check: PASS`、`check-patch-tree … 67 patches OK`、`check-asm-list-consistency … 12 spec files OK`、`repository checks: PASS`、`EXIT=0`）均与 (e) 真实输出一致，无捏造/矛盾。

##### 4. 判决

**Accepted**。验收标准 1/2/3 在审查者独立重跑下全部通过；改动范围与任务约束一致，核心检测逻辑未被削弱，4 类反例真实可复现且可证伪。非阻断观察项已登记，不影响「工程师达标」。最终接受由架构师终审。