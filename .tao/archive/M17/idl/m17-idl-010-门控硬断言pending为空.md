# m17-idl-010: 门控硬断言——收口后 `pending` 必须为空

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-009`
**可并行分片**：否
**预估**：30–60 min
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（`m17-idl-009` 复核发现）

`tools/idl/check_four_way.py` 的集合断言是 `主清单 == 现场派生 − pending`。因此「把一条主清单镜像一致地移进 `pending`」仍然 rc=0（主清单 221 / pending 1 / 派生 222，实测）。阶段一已收口（222 例全绿、`pending`=0）；若日后有人把红例移进 `pending`，L2 仍绿，**覆盖会静默缩水**——这正是本任务要堵的口子。

## 要做

1. `tools/idl/check_four_way.py`：在清单断言之后加一条硬断言——`[[pending]]` **必须为空**（段不存在或空数组）；非空 ⇒ rc=2，文案写明「阶段一已收口：能力缺口另立任务，不得用 pending 静默降覆盖」。
2. `docs/idl-four-way.md` §4 与 `idl/README.md` 同步该口径（删掉「一致地暂缓一条允许」的表述）。
3. 保留现成的 `pending` 解析代码，只加断言，不重构。

## 不做

- 不改任何 instruction 语义、不改 `idl/idl_exec_cases.toml` 的 222 条主清单；
- 不改 `tests/inst`、`.idl` 源、`spec/`、`contracts/`、QEMU/gem5/RTL。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动上述 3 个文件 + 本任务书；计数现场派生；完成区 ≤30 行。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl` rc=0（222/222）；
2. **可达 FAIL**：临时给 `idl/idl_exec_cases.toml` 加一条 `[[pending]]`（引用一条已在主清单的镜像的**另一条**合法镜像）⇒ rc=2 且文案含「pending 必须为空」；`cp`+md5 还原后 rc=0；
3. `check-idl-parse`/`check-idl-sync` rc=0；
4. 确认断言**不吃**正常路径：无 pending 时 222/222 仍绿、耗时无明显变化。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` ⇒ **rc=0，22 项检查 PASS / 0 FAIL**（逐项已打印期望/实际/rc）。注入两路均可达 FAIL：A（给主清单内合法镜像加 `[[pending]]`）⇒ **rc=2**；B（一致地把主清单一条移进 `pending`，旧断言下 rc=0 的真口子）⇒ **rc=2**，B 的唯一问题项即「pending 必须为空…阶段一已收口：能力缺口另立任务…」——证明新断言**独力**拦截。两路均先核注入非空（`git diff --name-only -- idl/idl_exec_cases.toml`），`cp` 还原后 md5 `69ef0b45…` 与备份相等、`[[pending]]` 0 条、回绿。
**修改文件**：`tools/idl/check_four_way.py`（仅加 pending 为空断言 + 文档串/模块注释同步）、`docs/idl-four-way.md` §4、`idl/README.md`、`idl/idl_exec_cases.toml`（**仅头部注释**，不动 `[[case]]` 数据；用户 2026-11-22 追加）、本任务书。
**验收结果**：`make check-idl` **rc=0**，`check_four_way: 222/222 例四方一致（parties=idl,qemu；主清单 222 / pending 0 / 现场派生 222）`，且独立现场统计（glob 222、tomllib 主清单 222、pending 0）与日志四项逐项相等；`make check-idl-parse` **rc=0**、`make check-idl-sync` **rc=0**。无 pending 时新断言仅一次 `if pend` 判空，耗时无可测变化（断言 O(1)；本机 `make check-idl` 实测 32.6 s，与 009 记录的 19.6 s 同量级，差值随机器负载浮动）。
**新发现/坑**：① 新断言**不可**在 `if problems: raise` 之后单独 raise——注入 A（pending 复用主清单镜像）会先命中「同一镜像同时在主清单与 pending」，新口径文案不出现；须并入同一 `problems` 列表（不早退），两路注入才都命中。② 任务 worktree 默认无 `.dadao`/`.work`，L2 需按既有做法软链主工作树的同名目录（两者已被 `.gitignore` 忽略）；软链后 `make check-idl` 走共享 `gate.lock` 串行。③ 本机 `make check-idl-parse`/`-sync` 须在仓库根跑（证据脚本首版在证据目录跑 ⇒ 「No rule to make target」，已改 `run_make` 带 `cd`）；④ `idl/idl_exec_cases.toml` 头部注释原写旧公式（无「pending 必须为空」）——已按用户 2026-11-22 追加要求**仅改注释**同步现口径（`[[case]]` 数据 0 改动；改后 `make check-idl` rc=0 222/222 确认解析未被破坏）。
**遗留问题**：无未完成项；未改任何 instruction 语义、未改 222 条主清单（`idl_exec_cases.toml` 仅改头部注释）、未碰 `tests/inst`/`.idl`/`spec`/`contracts`/仿真器。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 断言位置：放在 `problems` 之后单独 raise 会让注入 A 不命中新文案 | ✅已修 | 改为与集合断言并列 `problems.append`，顺序在 surplus 之后、`raise` 之前（既「在清单断言之后」又不掩盖文案） | 注入 A/B 日志均含「pending 必须为空」+「阶段一已收口：能力缺口另立任务」 |
| 证据脚本首版在证据目录跑 `make check-idl-parse/-sync` ⇒ rc=2（无 Makefile） | ✅已修 | 改用 `run_make`（内部 `cd` 到仓库根）并落 `logs/{parse,sync}.log` | 两项 rc=0 PASS |
| 失败计数打印的是标志位而非失败项数（2 项失败显示 1） | ✅已修 | 独立 `nfail` 计数 | 输出「22 项检查，失败 0 项」 |
| 空注入假绿风险：`git diff --name-only` 未限定清单文件，源码改动即可满足 | ✅已修 | 限定 `-- idl/idl_exec_cases.toml` 并另查 `[[pending]]` 条数=1 | 注入 A 输出「非空变更：idl/idl_exec_cases.toml」 |
| 自审核对范围：是否误改语义/主清单/其它文件 | ✅无问题 | 未改 | `git status --porcelain` 仅 3 个允许文件；清单 md5 与备份相同；`--platforms qemu` 222/222 绿 |

### 第 1 轮 reviewer 复核

- **重跑**：仓库根执行运行期证据目录内的 `run.sh` ⇒ **rc=0，22 项 PASS / 0 FAIL**；`make check-idl` **rc=0**（`check_four_way: 222/222 例四方一致（…主清单 222 / pending 0 / 现场派生 222）`）；`make check-idl-parse` **rc=0**、`make check-idl-sync` **rc=0**。
- **独立注入①**（给主清单内另一条合法镜像加 `[[pending]]`）：`make check-idl` **rc=2**，原文含「pending 必须为空（当前 1 条…）」；**注入②**（一致地移一条进 pending，现场 `tomllib` 主清单 221 / pending 1）：**rc=2**，且该次输出**仅**新断言文案（旧类「主清单多/少/相交」0 条）⇒ 新断言独力堵住旧口子；`cp`+md5 还原（`c051d90f…` 与备份相等）后 rc=0。
- **反例注入**：临时禁用该断言后重跑**同一** `run.sh` ⇒ **rc=1，5 项 FAIL**（注入 B 退回 rc=0，证明断言是唯一拦截者）；`cp`+md5 还原（`dec0bcb0…`）后回绿 **rc=0，22/22**。
- **断言位置**：`check_manifest` 的 `problems` 列表内、`raise` 之前收集，无早退（diff 核对）。
- **数据零改动**：现场 `tomllib` cases **222** / pending **0**；`git diff -- idl/idl_exec_cases.toml` 全部增删行以 `#` 起，仅头部注释。
- **文档一致**：`docs/idl-four-way.md` §4、`idl/README.md`、toml 头注释均改「必须为空」；grep「暂缓一条/一致地暂缓/暂缓允许」0 命中。
- **越界**：`git status -uall` 恰 5 文件，与完成区「修改文件」逐行对账一致；`tests/inst`、`.idl`、`spec/`、`.tao/contracts/` diff 为空。
- **基线红**：`make check-knowledge-refs` rc=2，1 悬空（`milestones-m18.md:39 ADR-0059`）；`git archive HEAD` 导出树重跑**逐行相同**（非本任务引入，维持 KNOWN-RED）。
- **判决：Accepted**（无阻断项；未改 `**状态**`）
