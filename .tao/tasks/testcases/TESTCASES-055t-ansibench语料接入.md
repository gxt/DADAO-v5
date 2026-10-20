# TESTCASES-055t: ansibench 语料接入（第一步：下载 → 锁定 → 8 基准跑起来）

**模块**：testcases
**项目里程碑**：M9
**依赖**：无（前置 = 主会话执行 `make install-host` 刷新安装根 `clang`/`qemu-dadao`；同模块改 `tools/testcases/**` 的册**串行**：`TESTCASES-053t`/`TESTCASES-054t`）
**状态**：待开始

> **编号（现场取号，2026-10-20）**：`find .tao -name 'TESTCASES-055t*'` = **0** 命中；全仓 `grep -ri ansibench .tao manifests` = **0** 命中 ⇒ 取 **`055`**，无同名册。

## 执行环境
**执行环境**：本地

## 用户原话（逐字，渠道 = 主会话派单 2026-10-20）

> 「创建任务，下载并测试：https://github.com/nfinit/ansibench；就用这个仓库最新的commit锁定即可」

> 「testcases，先走通第一步，是否能做基线对比，分析后再说」

（模块归属 = **testcases**，已由用户指定，无需再问；本册**只做第一步**。）

## 已核事实（主会话/architect 已实测，**不要重查**）

- 仓库 `https://github.com/nfinit/ansibench.git`；**HEAD = `ef90abd09d7b7bb1f2809f896d6f67fb9724bebe`**（`refs/heads/master` 同值；最新提交 2026-01-12「Fixed makefile argument patterns…」）。
- 体量 **1.8 MB**、**23 个 `.c`**；顶层目录 = `coremark` `dhrystone` `hint` `linpack` `nbench` `stream` `tripforce` `whetstone` `utilities` `mk`（**前 8 个** = 待跑基准；`utilities`/`mk` = 支撑）。
- **构建方式**：每个基准目录是**小写 `makefile`**，用 `cc=` 变量，形如 `-include ../mk/$(cc)/{stdflags.mk,opt/$(opt).mk,<bench>/stdflags.mk}`；仓库内**只有 `mk/gcc`、`mk/hp-c`、`mk/vac` 三套** ⇒ **不改语料**也能驱动：`make CC=<安装根 clang> …`（缺失的 `-include` 片段被静默跳过，不影响构建）。
- **仓库内无任何 golden / expected 输出**（0 个期望值文件）。
- **只有 CoreMark 自带校验**（CRC 自校验 ⇒ **唯一真 oracle**）；`dhrystone`/`whetstone`/`linpack`/`stream`/`nbench`/`hint`/`tripforce` **只打印计时数字** ⇒ 只能判「跑完 / 崩 / 超时」。

## 接口规范

- **输入**：上游仓库（见「已核事实」）；安装根工具链 `.dadao/cross-toolchain/bin/{clang,qemu-dadao}`（**主会话** `install-host` 前置，engineer **不跑**）；`manifests/components.lock.toml`；`tools/infra/fetch.py`（`make fetch`）。
- **输出**：
  1. **锁条目**：`manifests/components.lock.toml` 新增
     ```
     [[component]]
     name = "ansibench"
     enabled = true
     repository = "https://github.com/nfinit/ansibench.git"
     commit = "ef90abd09d7b7bb1f2809f896d6f67fb9724bebe"
     shallow = false
     patchless = true
     role = "ANSI C benchmark corpus"
     ```
     **不写** `patch_dir`/`patch_series`（`patchless` 组件声明它们会被 `make manifest-check` 直接判错）；**不写** `shallow_ref`（pin = 分支 tip，无 tag）。
     ⚠ **披露**：派单建议 `shallow = true`；本册按 `lessons §1.48` 取 **`false`**（无 tag 且 pin = 分支 tip ⇒ 浅镜像只跟随被跟踪 ref，上游一推进即丢锁 commit；体量 1.8 MB，全量代价可忽略）。若主会话坚持 `true`，须在完成区写明 `shallow_ref` 取哪个 ref 及其可再生性依据。
  2. **取源**：`make fetch` ⇒ 裸仓库 `.cache/ansibench.git` + 干净检出 `.work/source/ansibench`（detached 在 pin commit）；**tarball 不作组件源**（AGENTS：组件源一律 git 基线）。
  3. **8 基准构建 + 运行**：逐基准「构建（安装根 `clang`）→ `qemu-dadao` 跑 → 记录 exit code / stdout 关键行 / 是否自校验通过」；需要参数时**只用命令行变量**（如 `make CC=… CFLAGS=…`、CoreMark 的迭代数/seed 变量），**不改语料文件**。
  4. **证据**：证据脚本 `.work/evidence/<任务ID>/run.sh`（`default` + `--inject`）、日志 `.work/log/testcases/<任务ID>-*.log`、结果表逐项（**计数现场统计**）。
  5. **基线对比分析（只分析，不实现）**：见验收标准 5。
- **约束**：
  - **不改语料**（`ansibench` 树零修改；`check-source-state` 须显示 clean）——确需改语料 ⇒ **停下报告**。
  - **不改** `spec/` / `contracts/` / `.tao/contracts/**` / `tests/vectors/**` / `components/**`；**不动**既有驱动（新 runner 可新增，须在完成区披露）。
  - **不跑** `install-host` / `build-*` / L2 / L3；不 commit/push（提交权归 architect）。

## 验收标准

1. **锁定可复现**：`make manifest-check` rc=0；`make fetch` 后 `.cache/ansibench.git` 的 `git cat-file -e <pin>^{commit}` rc=0、`.work/source/ansibench` 的 `git rev-parse HEAD` = pin、`git status --porcelain` **空**（clean 检出）；`check-patch-tree` **不变**（5 组件 **185** patches，`patchless` 组件被跳过）。
2. **8 基准逐个构建**：`coremark` `dhrystone` `hint` `linpack` `nbench` `stream` `tripforce` `whetstone` **逐项**给出构建结果（rc + 产物路径）；构建失败的**照实登记**（原因 + 日志指针），不得跳过不记。
3. **8 基准 `qemu-dadao` 实跑**：逐项给 `exit code` / stdout 关键行 / 分类（`跑完` / `崩`（信号+地址侧证据）/ `超时`（`timeout` 用满且 `124`））；表内**计数现场统计**（禁写死「N/8」）。
4. **CoreMark 自校验必须 PASS**：给出**校验输出原文**（CRC 自校验通过字样），且 `qemu-dadao` 跑的是 pin commit 构建出的 ELF（写明二进制路径 + sha256）。
5. **基线对比 = 只分析**（用户原话「分析后再说」）：逐条回答 ①仓库内**有无** oracle（**无**）②**哪些**基准有自校验（**只有 CoreMark**）③可用的**替代**基线（宿主同源跑的比值 / 公开参考值 / 与 `llvm-test-suite` 的关系）④**必须写明**：`qemu` 用户态计时**不代表真机性能**、只可作**相对**比较。结论只写「**可行 / 不可行 / 部分可行 + 依据**」，**禁**开始实现。
6. **可达 FAIL ≥2**（真实输出 + `cp` + md5 还原后回绿）：(a) 用**错误 seed / 极小迭代数**跑 CoreMark ⇒ 自校验（或「运行时长 ≥10 s」硬判据）**必须** FAIL；(b) 把 pin commit 改一位（或人为删 `mk` 片段依赖）⇒ `manifest-check`/取源断言 FAIL。每条须「注入→FAIL→还原→回绿」闭合。
7. **门控**：`make check`（L1）rc=0（含 `manifest-check`/`check-patch-tree`/`check-no-residue`/`check-knowledge-refs`/`check-milestones-fresh`）；**不跑** L2/L3。
8. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行（本册已立行，勿重加）；`issues.yaml` 按实况回填（新缺陷才登记）。
9. **不跑** `git commit`/`push`；越界改动须披露。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/TESTCASES-055t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout`/`restore`/`stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围（`manifests/components.lock.toml` + 新增证据脚本/runner + 本册）；越界须披露。
5. **不改语料**：`ansibench` 树上零修改；构建参数只走命令行变量。
6. 长跑（CoreMark 默认要求 ≥10 s/轮）先申报耗时；`timeout` 用满即 `124` 判超时，不得当「跑完」。
7. 复杂命令输出留 `.work/log/testcases/`；运行产物按 `docs/Process-08`。
8. 失败保留现场并继续推进；**只在需用户语义裁定**（如是否接受改语料、是否引入 ADR）时留问。

## 待用户裁定（architect 提示，不阻断第一步）

- **ADR**：新增外部组件（上游选择 + commit 锁定）按惯例应有 ADR（先例 = `ADR-0022` embench / `ADR-0023` picolibc）。用户原话已含「URL + 用最新 commit 锁定」，但 ADR 的 decision 须**逐条确认**方能 `Accepted` ⇒ 本册**不代拟 ADR**，由主会话决定「补 `adr-0033`（ansibench 上游选择 + pin）」或「以用户原话直接授权、免 ADR」。
- **基线对比第二步**（是否实现、拿什么做基线）须在第一步结果与 §验收 5 的分析之上再裁定。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）
