# m13-qemu-014: `sc` 保留粒度改为「精确地址 + 访问宽度」（严格按 spec）

**模块**：qemu
**项目里程碑**：M13
**依赖**：无
**可并行分片**：否（改 `target/dadao/` 的 LR/SC 路径）
**预估**：2–3 h
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「ISS-435：严格按spec来」

- 落地含义：保留标记粒度 = **精确地址 + 访问宽度**（`spec/SimRISC-12 §1`「保留机制」段原文：以 `lr` 的地址与 `.b`/`.w`/`.t`/`.o` 宽度为键；**不按 cache line 扩大，也不因不同地址或不同宽度的访问清除**）。
- 同一裁定也覆盖 chipyard（`m13-chipyard-002`，RTL 侧）与测试（`m13-testcases-037`，把探针升为正式向量）；gem5 已合规，无需改。

## 现状（现场，`m13-testcases-028` 实测）

- QEMU 现按 **8 字节对齐字 + 整字值 CAS** 实现（`target/dadao/cpu.h` 的 `lock_addr`/`lock_val` + `translate.c` 的 `gen_lr`/`gen_sc`）⇒ `lr.b [A]` 后另一处写 `[A+1]`（同字异址）会因**字值改变**而让 `sc.b [A]` 失败（返回 1）。
- spec 要求的清除事件只有：**另一 hart 对同一精确地址、相同访问宽度的 store**、当前 hart 执行另一条 `lr`、异常/中断进入（`sc` 自身成败都清）。
- 实测差异：`probe_gran.S` 同 ELF，`rc {chipyard: 2, qemu: 1, gem5: 0}`（gem5 三点全过）。

## 目标

1. 保留记录改为 **(精确地址, 访问宽度)** 二元键：`lr.<w>` 记 `{addr, w}`；`sc.<w>` 仅当 `addr`/`w` 与记录**逐位相等**时成功（返回 0），否则失败（返回 1）；成败都清除记录。
2. **删除整字值比较**（`lock_val` 及 CAS 路径）：同字异址、同字同址不同宽度、同 hart 对邻居字节的写入**都不得**使 `sc` 失败。
3. 清除事件严格按 spec：另一条 `lr`（同 hart）、异常/中断进入、`sc` 自身。**同一 hart 的普通 store 不清除**（spec 未列；多 hart 场景属 GAP，见下）。
4. `sc` 的 `rdHB` 结果方向与 MALIGN 检查不变（成功 0、失败 1；`rdHB=rd0 ⇒ ILLI`）。

## 验收（逐条贴真实 rc）

1. **反例复现（改前正证）**：用改前二进制跑 `probe_gran.S` 等价的 3 点探针 ⇒ 点 1（同字异址）**红**（`sc` 返回 1）；贴真实输出与二进制 md5。
2. **改后**：点 1 转绿（`sc` 返回 0）；点 2（同 hart 改同字另一字节）绿；点 3（同精确地址同宽度写后 `sc`）按 spec 仍为「同 hart 写不清除」⇒ `sc` 成功（若你判断该点应失败，停下写「待裁定」，不要私自改口径）。
3. **既有 `lr`/`sc` 用例全绿**：`tests/inst/12-misc/` 的 24 个原子 id 三平台（chipyard/qemu/gem5）逐字节；`check-inst` 红集**不扩大**。
4. 探针 `probe_gran.S` 的 5 个观测点（同字异址 / 同字另一字节 / 同地址同宽度 / 另一条 lr 后 / 异常进入后）逐点给 QEMU 实测值与 spec 期望的对照表。
5. 补丁 `make_patch.py qemu` 导出；`check_qemu_trans` 264/264；`check-patch-tree` qemu 段 0 问题；`--source-state` qemu OK；`check-component-changelog` rc=0（M13 一条）。
6. ≥2 路可达 FAIL 注入 + `cp`+md5 还原。
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`**状态**` → `待验收`；不改台账/`discussing.md`。

## GAP（不伪造，写进完成区）

- **多 hart 对同一精确地址+宽度 store 的清除**：Tiny 当前单 hart，无观测载体 ⇒ 只写实现（记录键 + 清除时机），不造用例。
- 宿主线程级真并发（TCG 多线程）不可达 ⇒ 以功能语义为准。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host` / `check-modules` / 真 `build-chipyard`**；`build-qemu` 可（先 `pgrep -af "build-qemu|install-host|build-gem5|build-chipyard"` 确认无并发写者）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `target/dadao/{cpu.h,translate.c}`（必要时 `helper.c` 的清除点）+ `components/qemu/patches/**` + `components/qemu/changelog.md`；**不改** `spec/`、`contracts/`、`tests/**`。
5. 大文件落 `/tmp/opencode/m13-qemu-014/` 并测完即删。

## 待裁定

（无：用户 2026-11-14 裁定已明确「严格按 spec」，实现按该口径落地；多 hart 清除属 GAP，已登记遗留）

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14）

审查：`gen_lr`/`gen_sc` 的键比较与清除时机、`lrsc_memop` 宽度映射、`cpu.h`/`cpu.c`
字段增删、`helper.c` 清除点、补丁导出与任务书口径；另跑 8 点探针、24 id 三平台、
门控四件、注入两路。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 派单「点 1（同字异址）改前=1、改后=0」与「点 2（同 hart 改同字另一字节）改后=0」在语义上重叠，单一探针点无法同时钉住「写入者地址」与「sc 地址」两轴 | ✅已修（探针拆分，不改实现） | 探针拆 8 点并逐点给 spec 期望：P1 同字另一字节 `st.b` 后 `sc.b`（0）、P2 整字重写但保留 A 字节（0）、P3 同址同宽写（0）、P4 另一条 `lr`（1）、P5 自消费（0）、P6 再 `sc`（1）、P7 同址不同宽（1）、P8 同字异址 `sc`（1） | `probe_expect.tsv` + 改前/改后原始输出 |
| F2 共享组件源树带其它在途任务（`m13-qemu-011`）对 `hw/dadao/dadao-machine.c` 的改动，`make_patch` 会把它一并导出到本分支 | ✅已修 | 本分支只保留本任务 4 份 patch；该文件 patch 用基线版本（`cp` + md5 对账）；`check-patch-tree` 改在「pinned base + 本分支 series」干净源树验证 | clean-tree 门控 rc=0；`git status` 仅 5 个文件 |
| F3 注入自检首版把「期望 FAIL」的探针调用留在主 shell，其内部 FAIL 污染全局判决；另一处 must-fail 判据期望串写错 | ✅已修 | 注入探针改子 shell 执行；must-fail 判据统一 `cond → chk(0,cond,cond)` | `run.sh inject` 全 PASS，EXIT=0 |

未修 finding：无。

### 第 2 轮 reviewer 验收（2026-11-14，独立重跑）

**脚本审核**：`chk()` 期望≠实际即 FAIL（可达）；探针期望表独立于实现（spec 推导）；suite/gates 取被检命令自身退出码，无 `| tee` 吞码；注入两路改的是真被测物（期望表 / 删宽度比较）且 `cp`+md5 还原。

**重跑（全部由 reviewer 执行，`<运行期证据目录>/run.sh` 未改一字）**
1. `run.sh probe`（本任务构建树二进制 md5 `49174499…`）：P1..P8 = `0 0 0 1 0 1 1 1`，`EXIT=0`。
2. `QEMU_BIN=<安装根二进制 md5 b34ed7f9…>`（mtime 早于本改动）`run.sh probe`：`1 1 1 1 0 1 0 0`，P1/P2/P3/P7/P8 红，`EXIT=1`；改前期望由 reviewer 先按 spec+旧实现独立推出，与实测逐点一致 ⇒ 改前正证成立。
3. 独立 10 点偏移探针（reviewer 自写、期望手算，覆盖字内 k=2/4/5/6）：两二进制 Q1..Q7/Q9/Q10 完全相同（`4567 / 89ABCDEF / 0123456789ABCDEF / AB / 01234567 / CDEF / 0 / 0 / 0123456711223344`），仅 Q8（同字异址写后 `sc.t[A+4]`）改前 1 → 改后 0 ⇒ `.b/.w/.t/.o` 大端装/存（宽度 1/2/4/8、`lrsc_memop` MO_* 与 ALIGN）未回归。
4. `run.sh suite`：`66/66`（24 id；链 24+故障 42）× chipyard/qemu/gem5，JSON 198 次平台运行的 rc/字节逐条相符，`EXIT=0`；墙钟 24 s、`--jobs 64`（见 F1）。改前二进制同跑 `66/66`、`EXIT=0`、23 s。
5. `run.sh gates`：`check_qemu_trans 264/264`、`--source-state qemu: OK`、`check-component-changelog PASS`、干净源树 `check-patch-tree qemu 66 patch / 395 patches OK / 0 problem`，`EXIT=0`；`run.sh inject` 9 项全 PASS，`EXIT=0`。
6. `make check-inst`（安装根=改前）`1141/1135/1 failed(divrem.yaml[23])/5 deferred`、`RC=2`、27 s；`make check-inst QEMU_BIN=<本任务构建树二进制>`（改后）同数同红、`RC=2`、27 s ⇒ 红集不扩大。
7. 独立注入（reviewer 自设计，非其两路：`gen_sc` 侧地址改按 8 B 对齐比较）：注入 md5 `037f80d8…` ⇒ `P8 expected=1 actual=0`、`probe EXIT=1`；`cp` 还原 md5 `2665ee79…`==备份、组件源树 `git status` 0 行、重建 `RC=0`（2 s）后构建树 md5 回 `49174499…`、探针回绿 `EXIT=0`。
8. 并行度/资源：注入与重建前 `pgrep` 无并发写者，且未与跑批同时；构建 `JOBS=32`、测试 `--jobs 64`（应 62，见 F1）；`make check-disk` `RC=0`（4%）、可用内存 119 G；无节点派发（节点状态查询 N/A）。跑批/干净树克隆等大件已删，余下小日志随收尾清理。

**约束核验**：主工作树未动（`git status -uall` 0 行、仍 master）；未提交；未跑 `install-host`/`check-modules`/`build-chipyard`；相对基线 `7981b12a` 仅 6 个在范围文件，无 `spec/`、`contracts/`、`tests/`、`Makefile`、台账改动；`git show --stat 2ab1b11f` 只列 6 个文件、`git diff 7981b12a HEAD -- components/qemu/patches/hw/` 输出为空 ⇒ 在途 `m13-qemu-011` 的 `dadao-machine.c` 未被带入本分支；完成区 14 行、本记录 ≤40 行；GAP（多 hart / 异常载体 / 宿主并发）如实写。

**finding（均非阻断）**：F1 证据脚本测试写死 `--jobs "$(nproc)"`=64，违 2026-11-14「测试=全量核−2」，建议删该参数改用默认；F2 任务书硬约束第 5 行含临时目录路径（architect 立册文本；`check-knowledge-refs` `RC=0` 不门控，属文档级）；F3 GAP「只写实现（记录键 + 清除时机）」易读作「另一 hart 同址同宽 store 清除已实现」——新实现**无该代码路径**（旧整字 CAS 曾免费覆盖），单 hart 无载体故不阻断，上多 hart 前须补 store 侧失效钩子，请 architect 定夺是否立 ADR/后续任务；F4 `target/dadao/cpu.c` 在硬约束枚举外（删 `lock_val` 后必需，完成区已披露）。

**另记（环境，非本 diff 所致）**：`make check` L1 `RC=2`（15 s），`check-patch-tree` 12 problem——chipyard 10 项为在途任务并发写者；qemu 2 项（`dadao-machine.c` 断言⑥⑨）因基线落后：本分支该 patch 还原出 `7756efb7…` ≠ 共享源树 `17222089…`，而 master 版还原出 `17222089…` = 源树 ⇒ 合并后应转绿，architect 收尾复跑。另 master 已由 `m13-testcases-032` 退役 `divrem.yaml[23]`（该册 32→36 例），合并后红集须复跑确认。

**判决：Accepted** —— 8 点改前/改后、24 id 三平台、四门控、`check-inst` 红集、其两路注入与本 reviewer 一路独立注入，均由 reviewer 亲自重跑，输出与退出码与完成区逐条一致；无越界、无凑绿。

## 完成区

**测试结果**：8/8 探针点、66/66 镜像 × 3 平台、门控 4/4、注入 2/2 全过；`check-inst` 红集恰 `divrem.yaml[23]`（改前/改后相同）。
**修改文件**：`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c,translate.c}.patch`、`components/qemu/changelog.md`、本任务书；组件源树的 4 个文件改动仅经补丁承载（主仓库未提交）。
**验收结果**：
- 改前（md5 `b34ed7f…`）：P1=1 P2=1 P3=1 P4=1 P5=0 P6=1 P7=0 P8=0 ⇒ P1/P2/P3/P7/P8 与 spec 不符（红），EXIT=1。
- 改后（构建树二进制）：P1..P8 = `0 0 0 1 0 1 1 1`，与 spec 全符，EXIT=0。
- 24 个 lr/sc id：**66/66 镜像三平台通过**（链例 24 + 故障例 42，逐字节）；qemu 显式用本任务构建树二进制；改前 qemu-only 同样 66/66（既有用例未覆盖分歧轴）。
- `check_qemu_trans` 264/264；`--source-state` qemu OK；`check-component-changelog` rc=0；`check-patch-tree`（干净树）qemu 66 patch / 0 问题 rc=0。
- `make check-inst`：1141 total / 1135 passed / **1 failed（`divrem.yaml[23]`）** / 5 deferred；改前/改后红集相同（rc=2 为既有 pin）。
- 注入 2 路：期望表 P7 `1→0` ⇒ 探针 FAIL；实现删 `lock_width==width` 比较 ⇒ 重建后 P7 转 0 ⇒ 探针 FAIL；均 `cp`+md5 还原后回绿。
**新发现/坑**：① 共享组件源树会带在途任务改动（`m13-qemu-011` 的 `dadao-machine.c`）⇒ 本分支补丁只取本任务文件，并用「pinned base + 本分支 series」干净树跑 `check-patch-tree`；② 同一源码重复重建的 qemu 二进制 md5 会变（构建元数据），判据须用探针/套件而非二进制相等；③ 探针要拆「写入者地址 / sc 地址 / 宽度」三轴才能分辨字粒度与宽度粒度。
**遗留问题**：GAP——多 hart 对同一精确地址+宽度的 store 清标记：Tiny 单 hart、TCG 无并发观测载体，只落实现与清除时机，不造用例；异常/中断进入清标记同样无载体（沿用既有实现）；宿主线程级真并发不可达。无未修 finding。

