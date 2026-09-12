# INFRA-005t: 环境与状态工具

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-003t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`manifests/components.lock.toml`、`manifests/references.lock.toml`（`INFRA-003t` 产出）、宿主环境
- 输出：`scripts/doctor.py`、`scripts/status.py`、`scripts/clean_work.py`
- 约束：脚本只用 Python 标准库（`shutil` / `subprocess` / `tomllib` / `pathlib`）；`clean_work.py` 只删 `.work/`，**不碰 `.cache/`**（持久对象库）

## 背景（完整）

### 目标

提供宿主环境自检、组件/参考状态展示、以及安全清理 `.work/` 的三个辅助工具，支撑 `make doctor` / `make status` / `make clean-work`。

### 设计理由

- 可复现性要求在任何干净主机或开发容器上先做环境自检（`doctor`），并区分原生构建路径与容器构建路径。
- `status` 把 manifest 中锁定的 component/reference 与实际 checkout 对照，暴露 commit 漂移（DRIFT）。
- `clean_work.py` 以最小且防误删的方式移除一次性数据。

### 关键概念 / 数据

- `doctor.py`（0628 逻辑）：
  - required 工具：`git` / `make` / `cmake` / `python3`；native 工具：`ninja` / `clang`；另检测 `docker`。
  - 逐项打印 `OK`/`MISSING` 与版本首行。
  - required 缺失 → FAIL；native 缺失且无 docker → FAIL；否则按是否缺 native 报告 `native` 或 `container` 构建路径可用。
- `status.py`（0628 逻辑）：
  - 打印 Components：`name` / `enabled|disabled` / `commit`（未设显示 `UNSET`）。
  - 打印 References：对每个 reference 的 `path` 执行 `git rev-parse HEAD` 与 `git status --porcelain`，输出 `MATCH|DRIFT` 与 dirty 计数；路径不存在显示 `missing`。
- `clean_work.py`（0628 逻辑）：解析 `ROOT/.work`，断言其父目录为仓库根且名称为 `.work`，存在则 `shutil.rmtree`，否则提示不存在；防误删。

### 上游引用

- DADAO-0628 `scripts/doctor.py`（完整转述见上）。
- DADAO-0628 `scripts/status.py`（完整转述见上）。
- DADAO-0628 `scripts/clean_work.py`（完整转述见上）。
- DADAO-0628 `docs/repository-layout.md`：`.work/` 为一次性工作区，可整体清理。
- DADAO-0628 `code-agent/designs/0002-detailed-roadmap.md`：M0 交付要求 `make doctor` / `make status` 可用。

## 交付物

- `scripts/doctor.py`：宿主/容器构建前提自检。
- `scripts/status.py`：component 与 reference 的锁定/漂移状态。
- `scripts/clean_work.py`：安全删除 `.work/`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- `status.py` 读取 `references.lock.toml`（v5 文件名），而 0628 读取 `references.toml`。
- reference 集合不同：v5 为 DADAO-0628 / DADAO，`path` 指向 `.work/DADAO-0628` 等实际位置。
- `doctor.py` 的工具清单可扩展（如 gem5 需要 `scons`，见 `INFRA-007t`），但保持"required / native / container"三段式判定。

## 已知坑 / 结论

- `doctor.py` 在原生缺 `ninja`/`clang` 时仍可通过，前提是有 docker（走容器构建路径）。
- `status.py` 对 reference 的 `path` 做 git 查询；路径错误会显示 `missing`（0628 指向其原作者的本地绝对路径，v5 必须改指向本项目内的真实位置）。
- `clean_work.py` 的路径断言（父目录 + 名称）是防误删的关键，不可省略。
- **`clean_work.py` 不得删除 `.cache/`**：`.cache/<name>.git` 是持久对象库（`INFRA-004t`），删除它会导致重新下载大仓库；`clean_work` 只清 `.work/`。
- 三个脚本均须在 `python3 -m compileall scripts` 下无语法错误。

## 参考

- DADAO-0628：`.work/DADAO-0628/scripts/doctor.py`
- DADAO-0628：`.work/DADAO-0628/scripts/status.py`
- DADAO-0628：`.work/DADAO-0628/scripts/clean_work.py`
- DADAO-0628：`.work/DADAO-0628/docs/repository-layout.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `doctor.py` 正确判定 required/native 工具并报告可用的构建路径，退出码语义正确
2. `status.py` 输出 component 锁定状态与 reference 的 `MATCH`/`DRIFT`，无异常退出
3. `clean_work.py` 只删除 `.work/`（不删除 `.cache/`），对异常路径拒绝执行
4. 三脚本通过 `python3 -m compileall scripts`

## 完成区

**测试结果**：通过 9/9（A–I）；失败原因：无

**修改文件**：
- `scripts/doctor.py`（新增，可执行）
- `scripts/status.py`（新增，可执行）
- `scripts/clean_work.py`（新增，可执行）

**验收结果**（真实命令 + 真实退出码；完整输出见 `.tao/logs/INFRA-005t-*.log`）：

1. **`doctor.py` 判定与退出码语义** — 通过
   - 真实宿主 `python3 scripts/doctor.py` → required 全 OK，native `ninja` MISSING / `clang` OK，`docker` MISSING → `doctor: FAIL; native tools incomplete and Docker unavailable`，**EXIT=1**（本机无 ninja 且无 docker，FAIL 为正确语义）
   - 合成 PATH（required OK + native 缺 + docker OK）→ `doctor: PASS (container build path available)`，**EXIT=0**
   - 合成 PATH（required OK + native OK）→ `doctor: PASS (native build path available)`，**EXIT=0**
   - 合成 PATH（空 PATH）→ `doctor: FAIL; missing required tools: git, make, cmake, python3`，**EXIT=1**
2. **`status.py` component/reference 状态** — 通过
   - 真实仓库 `python3 scripts/status.py` → components `llvm/qemu/gem5 disabled UNSET`；references `dadao-0628 MATCH dirty=0 2d2706…`、`dadao MATCH dirty=0 f9bde0…`，**EXIT=0**
   - 合成仓库（good=MATCH / bad=DRIFT dirty=1 / gone=missing）→ 输出 `MATCH`/`DRIFT`/`missing` 正确，**EXIT=0**
3. **`clean_work.py` 安全删除** — 通过
   - 正常树：`removed …/.work`，`.work` 消失而 `.cache/refs/DADAO-0628.git` 仍在，**EXIT=0**
   - `.work` 不存在：提示 does not exist，**EXIT=0**
   - `.work` 为指向仓库外部的符号链接：`refusing to remove unexpected path`，**EXIT=1**，外部目标完好
   - `.work` 为普通文件：`refusing to remove non-directory`，**EXIT=1**，文件完好
4. **`python3 -m compileall scripts`** — 通过，**EXIT=0**（三个脚本均编译成功）

**新发现/坑**：
- v5 的 reference `path` 是**项目相对路径**（`.work/DADAO-0628`），`status.py` 必须 `ROOT / reference["path"]`；0628 直接 `Path(path)` 因其为绝对路径。已验证真实仓库两 reference 均 MATCH。
- `status.py` 对路径不存在输出 `missing`（0628 会落成 `DRIFT`），符合 v5 验收标准；`ROOT / <absolute>` 在 pathlib 下仍返回绝对路径，兼容未来绝对 path。
- `clean_work.py` 的父目录+名称断言在 `.work` 为**符号链接**时真正生效（`resolve()` 后父目录/名称不匹配即拒绝），这是防误删关键，已用合成测试覆盖。
- 宿主当前缺 `ninja` 与 `docker`，故真实 `doctor` 返回 FAIL/exit 1；这是正确判定，非缺陷。
- 本任务不创建 Makefile（由 `INFRA-006t` 负责）；脚本路径 `scripts/doctor.py` / `scripts/status.py` / `scripts/clean_work.py` 与 `INFRA-006t` 约定一致。
- `doctor.py` 版本探测用 `subprocess.check_output(..., stderr=STDOUT)`，非零退出/命令缺失统一返回 `unavailable`，不抛异常。

**遗留问题**：无

## 审阅记录

### 第 1 轮 engineer 自审（自主自审，嵌套受限）

`task(general)` 返回 `Subagent depth limit reached (1)`，按 engineer 规则降级为**自主逐行自审**（逐行读三个脚本 diff + 全部真实/合成测试证据）。

| 检查项 | 结论 | 证据 |
|--------|------|------|
| 仅用 Python 标准库 | ✅ | doctor: `shutil`/`subprocess`；status: `subprocess`/`tomllib`/`pathlib`；clean_work: `shutil`/`sys`/`pathlib` |
| doctor 三段式与退出码 | ✅ | 真实 FAIL exit1；合成 container PASS exit0 / native PASS exit0 / required FAIL exit1 |
| doctor 版本首行打印 | ✅ | 真实输出含 `git version 2.43.0`、`GNU Make 4.3` 等 |
| status 相对路径解析 | ✅ | `ROOT / reference["path"]`；真实仓库两 ref MATCH |
| status `missing` 分支 | ✅ | 合成 `gone` → `missing`，EXIT=0 |
| status dirty 计数 | ✅ | 合成 `bad` → `dirty=1` |
| clean_work 防误删断言 | ✅ | 测试 C/D 拒绝 EXIT=1；符号链接场景覆盖 |
| clean_work 不碰 `.cache/` | ✅ | 测试 A 后 `.cache/refs/DADAO-0628.git` 仍存在 |
| 无破坏性副作用 | ✅ | 唯一删除动作 `shutil.rmtree(work)`，路径经断言且已 `resolve()` |
| 函数签名/接口一致 | ✅ | 脚本名与 `INFRA-006t` 的 `python3 scripts/<name>.py` 约定一致 |
| 语法编译 | ✅ | `compileall` EXIT=0 |

**判决**：本轮无 finding，所有验收标准通过，状态置「待验收」。

**非阻塞备查（不修）**：`status.py` 在 `manifests/*.toml` 缺失时会抛 `FileNotFoundError`（0628 同行为）。当前 manifest 由 `INFRA-003t` 交付且存在，验收「无异常退出」在本仓库满足；按最小修改原则不在本任务增加容错，如后续需要可作为独立任务。

### 第 1 轮 reviewer 验收

独立重跑全部验收命令，不采信完成区。日志存 `.tao/logs/INFRA-005t-review-all.log`。

#### 1. 语法编译

```
$ python3 -m compileall scripts
Listing 'scripts'...
EXIT=0
```

三个脚本（`doctor.py` / `status.py` / `clean_work.py`）编译成功，`__pycache__/` 下均有 `.pyc`。✅

#### 2. doctor.py — 真实宿主

```
required
  git        OK       git version 2.43.0
  make       OK       GNU Make 4.3
  cmake      OK       cmake version 3.28.3
  python3    OK       Python 3.12.3
native
  ninja      MISSING  
  clang      OK       Ubuntu clang version 18.1.3 (1ubuntu1)
container
  docker     MISSING  
doctor: FAIL; native tools incomplete and Docker unavailable
EXIT=1
```

**判定正确**：本机 `ninja` 缺失且无 `docker`，native 路径不可用，container 路径不可用 → FAIL exit=1。非脚本 bug。

#### 3. doctor.py — 合成 PATH 隔离测试

| 场景 | PATH 配置 | 预期 | 实际 | 退出码 |
|------|-----------|------|------|--------|
| A: 全 OK | stubs: git/make/cmake/ninja/clang/docker + 真实 python3 | PASS (native) | `PASS (native build path available)` | 0 ✅ |
| B: container | stubs: git/make/cmake/docker + 真实 python3（无 ninja/clang） | PASS (container) | `PASS (container build path available)` | 0 ✅ |
| C: required 缺 | 仅真实 python3（无 git/make/cmake） | FAIL | `FAIL; missing required tools: git, make, cmake` | 1 ✅ |
| D: native 部分缺 | stubs: git/make/cmake/clang + 真实 python3（无 ninja/docker） | FAIL | `FAIL; native tools incomplete and Docker unavailable` | 1 ✅ |

退出码语义：0=至少一条构建路径可用，1=无可用路径。正确。

#### 4. status.py — 真实仓库

```
Components
  llvm     disabled UNSET
  qemu     disabled UNSET
  gem5     disabled UNSET
References
  dadao-0628       MATCH   dirty=0   2d270604b778d609e1a09b4047271b5309005ffc
  dadao            MATCH   dirty=0   f9bde0481668ffab325db8d8c5d8c4cc791c6232
EXIT=0
```

- Components: 三行 `disabled UNSET`（commit 为空字符串，`enabled=false`）。✅
- References: `dadao-0628` HEAD `2d270604…` 与 lock 文件一致 → MATCH；`dadao` HEAD `f9bde048…` 与 lock 文件一致 → MATCH。✅
- 独立验证 `git -C .work/DADAO-0628 rev-parse HEAD` 确实返回 `2d270604…`，`git -C .work/DADAO rev-parse HEAD` 确实返回 `f9bde048…`。

#### 5. status.py — 合成仓库（DRIFT / missing）

```
Components
  llvm     disabled UNSET
References
  good-ref         MATCH   dirty=0   3802f0747fff2c16e63d3e5bcc1e105dbf400e59
  bad-ref          DRIFT   dirty=1   3802f0747fff2c16e63d3e5bcc1e105dbf400e59
  gone-ref         missing dirty=-   -
EXIT=0
```

- `good-ref`: HEAD 与 lock 匹配 → MATCH，无 dirty 文件 → dirty=0。✅
- `bad-ref`: HEAD 与 lock 不匹配（lock 为 `0000…dead`）→ DRIFT，有未跟踪文件 → dirty=1。✅
- `gone-ref`: 路径不存在 → `missing`。✅

#### 6. clean_work.py — 隔离树安全测试

| 测试 | 场景 | 预期 | 实际 | 退出码 |
|------|------|------|------|--------|
| A | `.work` 存在（正常目录） | 删除 `.work`，保留 `.cache` | `.work` 消失，`.cache` 及 `.cache/refs/test.git` 仍在 | 0 ✅ |
| B | `.work` 不存在 | 提示不存在 | `does not exist` | 0 ✅ |
| C | `.work` 为指向外部的符号链接 | 拒绝 | `refusing to remove unexpected path`，外部目标完好 | 1 ✅ |
| D | `.work` 为普通文件 | 拒绝 | `refusing to remove non-directory`，文件完好 | 1 ✅ |

关键验证：Test A 后 `.cache` 目录及其内容完整保留，确认 `clean_work.py` **不碰 `.cache/`**。

#### 7. manifest_check.py 回归

```
enabled components: none
references: 2
manifest validation: PASS
EXIT=0
```

不受本次修改影响，仍 PASS。✅

#### 8. 约束核验

| 约束 | 核验结果 |
|------|----------|
| 只用 Python 标准库 | ✅ doctor: `shutil`/`subprocess`；status: `subprocess`/`tomllib`/`pathlib`；clean_work: `shutil`/`sys`/`pathlib` |
| `clean_work` 不碰 `.cache/` | ✅ 隔离树 Test A 验证 `.cache` 完好 |
| reference path 为项目内相对路径 | ✅ lock 文件中 `path = ".work/DADAO-0628"` 等，非绝对路径 |
| 修改文件清单一致 | ✅ `git status` 显示三个新文件：`scripts/doctor.py` / `scripts/status.py` / `scripts/clean_work.py` |
| 脚本可执行权限 | ✅ 三个文件均为 `755` |

#### 9. 与完成区自审结论的差异

无差异。reviewer 独立重跑的所有命令与工程师完成区报告一致。工程师因 `subagent_depth=1` 降级为自主自审，其逐行审查结论均被 reviewer 独立验证确认。

#### 判决

**Accepted**。四个验收标准全部满足，所有约束无违反，所有退出码语义正确。真实宿主 `doctor.py` 返回 FAIL（缺 `ninja` 且无 `docker`）是正确诊断。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 的 **Accepted**；交付物满足任务书全部「交付物/验收标准/约束」，无遗漏。

**独立核对**：真实宿主 + 合成 PATH 三路径重跑 doctor；status 真实 MATCH + 合成 DRIFT/missing/非 git 仓库；clean_work 8 个隔离用例（含多种符号链接/普通文件拒绝），`.cache/` 全程未被触碰；AST 核对仅标准库；与 `INFRA-006t`/`INFRA-004t` 接口自洽。

**补充发现**：

- **F1（中，跨模块规划矛盾，非本任务缺陷）**：`INFRA-007t` 验收标准 4「容器内 `make doctor` 报告 `container` 路径可用」**不可达**——其 Dockerfile 仅装 `build-essential`（gcc，不含 clang）+ `ninja`，容器内无 docker CLI；而 doctor 规则为「native 缺失且无 docker → FAIL」。加 clang → 报 `native`（仍非 container）；不加 → FAIL。建议处置：(a) 改标准 4 为「容器内报告 `native`」并给 Dockerfile 补 clang；(b) 改标准 4 为宿主侧「有 docker、缺 native 的宿主上报 `container`」；(c) 改 doctor native 判据（clang→通用编译器，属改 INFRA-005t spec，另开任务）。
- F2（低，环境前提）：~~真实宿主缺 `ninja`/`docker`，M1 期间 `make doctor` 将持续 FAIL（正确诊断）。~~ **已解决**：宿主已安装 `ninja`(1.11.1) 与 `docker`(29.1.3)，`python3 scripts/doctor.py` 现输出 `PASS (native build path available)`，exit=0。
- F3（低，非阻塞）：`status.py` 对「路径存在但非 git 仓库」输出 `DRIFT dirty=0 unavailable`，`dirty=0` 易被误读。

**统一判决**：**Accepted**（INFRA-005t 自身无缺陷）；F1 作跨模块规划问题另行处置。
