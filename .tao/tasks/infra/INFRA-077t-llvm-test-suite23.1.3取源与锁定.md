# INFRA-077t: llvm-test-suite 23.1.3 取源与锁定

**模块**：infra
**项目里程碑**：M8
**依赖**：无（用户 2026-10-14 裁定取源 URL 与版本）；消费方 = 未来 M8 **基线 / benchmark 跑**（触发条件见「§基线跑触发条件」）
**状态**：待验收

## 执行环境
**执行环境**：本地

## 问题根源 / 立项来源

- **用户裁定（2026-10-14，原话）**：
  - 「**取源：https://github.com/llvm/llvm-test-suite**」；
  - 「**取源，tag：23.1.3**」；取得渠道 = **经主会话问答**。
- **动机**：M8 需要 LLVM 官方 **test-suite** 作为**基线 / benchmark 语料**（可与 Embench / Chipyard 跑分对照）。按 v5 约定「**组件源一律 git 基线**」（`AGENTS.md`「工作区落点」/`lessons §3.19`），须先在本仓库内**取源 + 锁定**，使其**可 `git diff`**（tarball 不作组件源）。
- **取源通道（实测，见「§实测记录」）**：`ghfast.top` / `gitclone.com` / 直连在 **`ls-remote` 可用**，但**大包**（≈294 MB shallow packfile）全部失败（HTTP 504 / curl 124）；**`gh-proxy.com` 成功**。
- **基线跑暂缓**：用户 **2026-10-14** 裁定「**暂缓，等 musl 跑通**」⇒ 本任务**只取源 + 锁定**，**不跑基线**（触发条件见「§基线跑触发条件」）。

## 接口规范

- **输入**：用户裁定（源 URL、tag `23.1.3`）；代理通道（见上）。
- **输出**：
  1. `.cache/<name>.git`（**bare 裸仓库**，`--depth 1 --branch <tag>` 浅克隆）；
  2. `.work/source/<name>/`（**git 检出**，detached at 锁 `commit`，**可 `git diff`**；**不入 git** —— `.work/` 已 gitignore）；
  3. `manifests/components.lock.toml` 新增 **`llvm-test-suite`** 条目（**体例对齐 `linux`/`qemu`**：`repository` + 40-hex `commit`〔**annotated tag peel 后 commit**〕+ `shallow = true` + `shallow_ref = "llvmorg-23.1.3"` + `enabled = true` + `patchless = true`〔**无 v5 补丁集**〕+ `role` + `[[component.source]]`）；
  4. 本任务书「实测记录」+「§参考对照（`DADAO-0628` 教训）」。
- **约束**：**不**改组件补丁 / `spec/` / `contracts/`；**不**写契约正文；sha / 体积 / 耗时 / tag 形态**现场取证**；正文引用 `.work/**` 一律用 `<>` 占位。

## 验收标准

1. `.cache/<name>.git` 为 **bare**（`git rev-parse --is-bare-repository` = `true`）+ **shallow**（`--is-shallow-repository` = `true`），含锁 `commit`。
2. **tag 形态核**（参照 `INFRA-075t` 的 `tag≠commit` 经验）：`git cat-file -t refs/tags/llvmorg-23.1.3`（**annotated ⇒ `tag`**）+ tag object sha + `git rev-parse 'refs/tags/llvmorg-23.1.3^{}'`（**peel 后 commit**）⇒ 锁 `commit` 记 **peel 后 commit**（**对齐 `qemu`/`linux` 体例**；tag object sha 记注释、**不入 `commit` 字段**）。
3. `.work/source/<name>/` 为 **git 检出**，`rev-parse HEAD` = 锁 `commit`、`describe --tags` = `llvmorg-23.1.3`、`status --porcelain` 空。
4. **`git diff` 可用性证明**：向工作树任一源文件注入探针行 ⇒ `status --porcelain` 报 ` M`、`git diff` **非空**；还原用 `cp` 备份回写 + **md5 逐位对账**（**禁** `git checkout`/`restore`/`stash`）⇒ `status` 回空。
5. `manifests/components.lock.toml` 新增 **`llvm-test-suite`** 条目（字段见上「输出 3」）；`make check`(L1) **rc=0**。
6. **记录**：体积 / 耗时 / 顶层构成 ✓、**`External/`（含 `SPEC/`）须排除** ✗、与 `llvm-project`（= `llvmorg-23.1.1`）的**版本关系**如实标注 ✓（见「§版本关系」「§构成与排除」）。
7. **参考对照落纸**：`DADAO-0628` 对 llvm-test-suite 的用法与**教训清单**（**只借教训、不复制实现**）。
8. 门控：`make check`(L1) / `check-modules`(L2) / `check-no-residue` / `check-knowledge-refs` / `check_issues.py` 各 **rc=0**。
9. `milestones.md`：`INFRA-077t` 流水行 + M8 规划区登记。

## 实测记录

| 项 | 值（现场取证，2026-10-14） |
|---|---|
| 源 URL（用户裁定） | `https://github.com/llvm/llvm-test-suite.git` |
| tag（实际存在者） | **`llvmorg-23.1.3`**（LLVM 惯例；`refs/tags/23.1.3` **不存在**） |
| tag 形态 | **annotated**（`cat-file -t` = `tag`，PGP 签名） |
| tag object sha | `7fa03005193c4cc9b882e0b70f9f43a088c52033` |
| **peel 后 commit（锁值）** | **`2919e55176a572ee085cb46b291c47b7092c363e`** |
| commit 日期 / 标题 | `2026-07-14` / `[Fortran] Dsiable the declare-variant-6.f90 test for now (#448)` |
| 默认分支 | `main`（HEAD = `624469628023f75fe320e431aaea038e23018d80`，**非本任务锁值**） |
| bare 体积 | **294 MB**（`.cache/<name>.git`） |
| 工作树体积 | **2.4 GB**（`.work/source/<name>`，检出后） |
| 耗时 | **≈252 s**（`gh-proxy.com` 浅克隆，START `03:08:06Z` → END `03:12:18Z`） |
| **实际所用通道** | **`gh-proxy.com`**（主）；`ghfast.top` ✗ / `gitclone.com` ✗ / 直连 ✗（见「§取源通道实测」） |
| `RC` | clone `rc=0`；工作树 clone `rc=0` |

### 取源通道实测（口径 = **大包 packfile**，非 `ls-remote`）

| 通道 | `ls-remote` | 浅克隆（≈294 MB packfile） | 结论 |
|---|---|---|---|
| `gh-proxy.com` | ✓ | **✓ `rc=0`，252 s** | **采用（source[0]）** |
| `ghfast.top` | ✓ | ✗ `HTTP 504`（`rc=128`，两次） | 备 |
| `gitclone.com` | ✓ | ✗ `HTTP 504`（`rc=128`） | 备 |
| 直连 `github.com` | ✗ `timeout 124` | 未试 | 不可用 |

> **教训**：`ls-remote` 可用 **≠** 大包可取；镜像选了就会试，须先试**真正的 packfile**（`lessons §3.19` 精神）。

## 版本关系（如实标注；**不臆断影响**）

- 我们的 `llvm-project` = **`llvmorg-23.1.1`**（`manifests` 现场核）；本套件 = **`llvmorg-23.1.3`** ⇒ **tag 小版本差**（23.1.1 vs 23.1.3）。
- **实测（关键）**：test-suite 的 **`llvmorg-23.1.{0,1,2,3}` 四个 tag 全部 peel 到同一 commit `2919e551…`** ⇒ 取 **23.1.3** 与取 **23.1.1** 得到**完全相同的树** ⇒ 该「小版本差」在 test-suite 内容上**不产生任何差异**。此为**事实**，非推测。

## 构成与排除

- **顶层**：`ABI-Testsuite`(1.5 G) / `Bitcode`(303 M) / `MultiSource`(173 M) / `Fortran`(50 M) / `External`(34 M) / `SingleSource`(32 M) / `MicroBenchmarks`(6.9 M) / `ClangAnalyzer` / `CTMark` / `LNTBased` / `tools` / `utils` / `lit.cfg` 等。
- **排除项**：**`External/`** 内含 **`SPEC/`（CFP2006 / CFP2017rate 等）** 及其它依赖外部下载的套件（`CUDA`/`HIP`/`POCL` 类），**须排除**（外部 SPEC CPU 源不可自由分发/不可得）✗ —— 基线跑**只从 `SingleSource`/`MultiSource`/`MicroBenchmarks` 等自足子集选**。

## 基线跑触发条件

- 用户 **2026-10-14** 裁定「**暂缓，等 musl 跑通**」⇒ **基线跑不做**。
- **触发（解禁）条件**：**musl 静态链 / 动态链跑通**（M8 主线 `P1 musl 静态` → `P2 动态链接`，`ADR-0025 D6`）**之后**另立任务执行基线跑。本任务**只取源 + 锁定**。

## 参考对照（`DADAO-0628`；**只读、只借教训、不复制实现**）

> 来源：`.cache/refs/DADAO-0628/`（只读参考树；`内容溯源，非执行必需`）。

- 0628 把 llvm-test-suite **既登记为 component**（`components.lock.toml`：`commit = 68d03c39d62c2ef9ec663530066bdb66ca5cc4f6`、`enabled`，但 `patch_series` 指向的 `series` 文件**只有注释、无补丁**），**又登记为 reference**（`references.toml`：`head = a3f72bf9dd1355c57dce2c8e015796c8d9998196`、`dirty = 1`、`selected_paths = ["SingleSource/", "MultiSource/"]`）。
- **教训清单（借判断，不搬实现）**：
  1. **不跑上游 CMake/lit harness**：0628 明确「fetched as a source-only reference (SingleSource pure-compute `.c` files) — we do not build its own CMake/lit harness」（`role` = 「thin lit wrapper, not upstream CMake/lit harness」）⇒ 我们将来跑基线须**先定子集 + 用薄 wrapper**，而非整套件 CMake。
  2. **子集口径**：0628 `selected_paths = SingleSource/ + MultiSource/`（pure-compute）⇒ 与「`External/` 排除」方向一致。
  3. **不继承旧结果**：0628 `reuse = "Upstream tests may be fetched clean; old PASS results are not inherited"` ⇒ 上游测试可干净取用、**旧 PASS 结果不可继承**（独立 oracle 口径）。
  4. **无补丁**：0628 该组件 `series` 为空 ⇒ 我们用 `patchless = true` **与之一致**。
  5. **我们更干净**：0628 取到的是 `dirty = 1` 的**快照**；我们 = **annotated tag 的 peel commit（干净、可复现）**。

## 硬约束

1. 临时目录 `/tmp/opencode/INFRA-077t/`；命令一律在 workdir（= 仓库根）内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不**用 `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. 文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
4. **只动**：`.cache/<name>.git`、`.work/source/<name>/**`、`.work/log/<模块>/`、`manifests/components.lock.toml`、本任务书、`.tao/knowledge/milestones.md`。**不跑基线**。
5. 完成区与真实输出逐条对齐；**禁** `cmd | tail` 接进 `&&`。
6. 大文件（裸仓库 / 工作树）**不得**入 git（`.cache/`、`.work/` gitignored）。
7. **不提交**（提交权归 architect）。

## 完成区
**测试结果**：
- `make manifest-check` rc=0（`enabled components: …, linux, llvm-test-suite`）。
- `make check`(L1) **rc=0**（末行 `repository checks (L1): PASS`；日志见 `.work/log/infra/<L1 log>`）。
- `make check-modules`(L2) **rc=0**（日志 `.work/log/infra/<L2 log>`）。
- `make check-no-residue` / `check-knowledge-refs` / `check_issues.py` 各 **rc=0**（`PASS` / `PASS (0 悬空引用)` / `check_issues: 25 open, 2 closed (0 blocking)`）。
- tag 形态：`cat-file -t refs/tags/llvmorg-23.1.3` = `tag`（**annotated**，PGP 签名）；`…^{}` = `2919e55176a572ee085cb46b291c47b7092c363e`。
- 工作树：`rev-parse HEAD` = `2919e551…`、`describe --tags` = `llvmorg-23.1.3`、`status --porcelain` 空、`is-shallow` = `true`。
- `git diff` 可用性：注入探针行 ⇒ `status` 报 ` M README.txt`、`diff --quiet` rc=1；`cp` 回写 + `md5sum -c` = `OK` ⇒ `status` 回空。
- 取源：`gh-proxy.com` 浅克隆 rc=0（**252 s / 294 MB**）；`ghfast.top`·`gitclone.com` 大包 **HTTP 504**、直连 curl **124**（三者 `ls-remote` 均 ✓）。
**修改文件**：`manifests/components.lock.toml`（+`llvm-test-suite` 条目）；`.tao/knowledge/milestones.md`（+INFRA-077t 流水行 + M8 区条目）；本任务书。
**验收结果**：（待 reviewer / 主会话）由 architect 按主会话指示「立并执行」完成，**未走独立 reviewer 轮次**。
**新发现/坑**：
- **`ls-remote` ✓ ≠ 大包可取**：`ghfast.top`/`gitclone.com` 探测正常，但 ≈294 MB 单 tag packfile 皆 `HTTP 504`；唯 `gh-proxy.com` 成功。
- **版本关系（证伪担忧）**：test-suite `llvmorg-23.1.{0,1,2,3}` **四 tag 同 peel commit** ⇒ 与 `llvm-project 23.1.1` **无内容差**（原记「小版本差」实为**不存在**，如实标注）。
- **工作树 2.4 GB**（≫ bare 294 MB）：`ABI-Testsuite` 独占 1.5 G、`Bitcode` 303 M。
- **共享工作树并发写**：`milestones.md` 被兄弟会话（`LLVM-091t`/`SPEC-139t`）**并发修改** ⇒ 本任务提交**只 stage 本任务 hunk**（`update-index --cacheinfo` 手术），**未混入**他任务改动。
**遗留问题**：① **基线跑**待 **musl 静态/动态链跑通**后另立任务（`External/` 含 `SPEC` 须排除）；② `milestones.md` 中他会话改动仍留工作区，待其各自提交。

## 审阅记录

#### 第 1 轮 architect 执行（主会话直派，无独立 engineer/reviewer 轮次）
（本任务由 architect 按主会话指示「立并执行」完成取源 + 锁定；记录见下「完成区」与会话回报。）
