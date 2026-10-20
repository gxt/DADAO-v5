# TESTCASES-055t: ansibench 语料接入（第一步：下载 → 锁定 → 8 基准跑起来）

**模块**：testcases
**项目里程碑**：M9
**依赖**：无（前置 = 主会话执行 `make install-host` 刷新安装根 `clang`/`qemu-dadao`；同模块改 `tools/testcases/**` 的册**串行**：`TESTCASES-053t`/`TESTCASES-054t`）
**状态**：待开始

> **编号（现场取号，2026-10-20）**：`find .tao -name 'TESTCASES-055t*'` = **0** 命中；全仓 `grep -ri ansibench .tao manifests` = **0** 命中 ⇒ 取 **`055`**，无同名册。

> **ADR（2026-10-20 已裁定，`Accepted`）**：`.tao/adr/adr-0033-ansibench-corpus.md`（`D1`–`D5` 用户逐条确认；**`D4` 为修订版** = 语料**允许最小必要补丁 + 三类归因**，取代本册原「不改语料」硬边界）。
> **锁条目已由 architect 随 `ADR-0033` 落地**（`manifests/components.lock.toml` 的 `[[component]] name = "ansibench"` + 两个 `[[component.source]]`）⇒ **执行者只需 `make fetch` 落地**（缺条目 ⇒ 停下报告，不要自行补写）。

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
  1. **锁条目（已由 architect 落地，见文首「ADR」块；执行者核对，缺则停下报告）**：`manifests/components.lock.toml` 新增
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
     ⚠ **已裁定（`ADR-0033 D2`）**：取 **`shallow = false`**（原派单曾建议 `true`；无 tag 且 pin = 分支 tip ⇒ 浅镜像只跟随被跟踪 ref，上游一推进即丢锁 commit；体量 1.8 MB，全量代价可忽略）。
  2. **取源**：`make fetch` ⇒ 裸仓库 `.cache/ansibench.git` + 干净检出 `.work/source/ansibench`（detached 在 pin commit）；**tarball 不作组件源**（AGENTS：组件源一律 git 基线）。
  3. **8 基准构建 + 运行**：逐基准「构建（安装根 `clang`）→ `qemu-dadao` 跑 → 记录 exit code / stdout 关键行 / 是否自校验通过」；需要参数时**优先只用命令行变量**（如 `make CC=… CFLAGS=…`、CoreMark 的迭代数/seed 变量）；**补丁须按 `ADR-0033 D4`（见下「约束」）**。
  4. **证据**：证据脚本 `.work/evidence/<任务ID>/run.sh`（`default` + `--inject`）、日志 `.work/log/testcases/<任务ID>-*.log`、结果表逐项（**计数现场统计**）。
  5. **基线对比分析（只分析，不实现）**：见验收标准 5。
- **约束**：
  - **语料改动按 `ADR-0033 D4`（修订版口径，取代原「不改语料」硬边界）**：原则上保持上游原样；**允许最小必要补丁**（一文件一补丁 + `series`），**仅限**因 **bank 分离 ABI（`rd`/`rb`）/ C90 UB** 导致的 `int`↔指针失配，且每个补丁必须写明「原代码为何违 C 标准或与 ABI 不兼容」；**任何失败须逐条归因三类** —— ①编译器/后端缺陷 ②语料 UB（含隐式声明、无原型）③**`rd`/`rb` bank 失配** —— **不得混类**，**不得**把 ②③ 记成 ①。改语料须在完成区**逐条列补丁 + 归因**并披露。
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
4. 只动任务范围（新增证据脚本/runner + 最小必要补丁 + 本册**之外不改**）；**锁条目已由 architect 落地**（缺则停下报告，勿自行补写）；越界须披露。
5. **语料改动按 `ADR-0033 D4`**：默认上游原样 + 命令行变量；**允许最小必要补丁**（仅 bank 分离 ABI / C90 UB 致的 `int`↔指针失配，一文件一补丁 + `series` + 写明「原代码为何违标准/ABI」）；**失败逐条归因三类、禁混类（禁把 ②③ 记成 ①）**。
6. 长跑（CoreMark 默认要求 ≥10 s/轮）先申报耗时；`timeout` 用满即 `124` 判超时，不得当「跑完」。
7. 复杂命令输出留 `.work/log/testcases/`；运行产物按 `docs/Process-08`。
8. 失败保留现场并继续推进；**只在需用户语义裁定**（如补丁范围超出 `D4` 授权、是否把 ansibench 纳入门控）时留问。

## 已裁定 / 待裁定

- **ADR（已裁定 2026-10-20）**：`.tao/adr/adr-0033-ansibench-corpus.md` **`Accepted`**（`D1`–`D5` 用户逐条确认；`D4` = 修订版，允许最小必要补丁 + 三类归因）。**锁条目由 architect 随 ADR 落地** ⇒ 本册执行者**只需 `make fetch`**。
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

#### architect ADR 落地记录（2026-10-20，非 engineer/reviewer 轮次）
- **ADR**：`.tao/adr/adr-0033-ansibench-corpus.md` 已落 **`Accepted`**（`D1`–`D5` 用户逐条确认；`D4` = 修订版）。本册边界随之改为 `D4` 口径（见「约束」/ 硬约束 5）。
- **锁条目**：`manifests/components.lock.toml` 的 `[[component]] name = "ansibench"`（`enabled`/`shallow=false`/`patchless`）+ `source[]` = `gh-proxy`(source[0]) / `github` 已由 architect 落地；依据 = 直连 `ls-remote` 超时 rc=124、`gh-proxy` rc=0 且回报 pin 一致。
- **门控现场（architect 实测，与本次改动无关的红）**：`manifest-check` **PASS**；`check-patch-tree` 报 **2 problem(s)** 全在 `llvm-project`（`.work/source/llvm-project/lld/ELF/Arch/DADAO.cpp` 被**并发会话**修改，mtime 12:03:14；改动前基线 = `5 component(s), 185 patches OK` rc=0）；`check-run-artifacts` 因并发 `libc-test-user` 跑批目录**写一半**而红（另一目录随后补齐）。ansibench 在 `--source-state` 输出 `patchless; skipped`（不参与补丁树）。
- **提交**：见 `git log`（architect 提交权；分支 `ADR-0033-ansibench`）。
