# m16-testcases-003: `lr`/`sc` 保留语义三平台对齐

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（`m15-qemu-002`/`m15-gem5-002` 已合入）
**可并行分片**：否
**预估**：3–4 天
**档位**：中改
**状态**：已验证

## 背景（issues 三条同源）

- `ISS-443`【P1】`sc` 的「**异常/中断进入 ⇒ 清保留**」三平台均不实现（`spec/SimRISC-12 §1` 明列为清除事件）：四条路径实测 `MALIGN`/`CFXMEM`/`ILLI` 后 `sc` = chipyard `1` / qemu `1` / **gem5 `0`**；`CFXTRAP` = `1` / **`0`** / **`0`**（spec 全为 1 = 清除）。后果：该清除事件写不成正式向量（写 1 挡 L2、写 0 = 以实现反推，任务书明禁）。
- `ISS-435`【P2】`sc` 保留**粒度**：`spec/SimRISC-12 §1` / `ADR-0034 D6` = **精确地址 + 宽度**；实测 QEMU 按 8 B 整字判成功、chipyard 按整字值比较，均与 spec 相反/不符；gem5 与 spec 一致。
- `ISS-440`【P2】「另一 hart 对同址同宽 store ⇒ 清保留」三平台无实现路径；单 hart 无观测载体。

## 目标

1. **实现对齐 spec**（不是改 spec）：三平台补「异常/中断进入 ⇒ 清保留」；QEMU 与 chipyard 改「精确地址 + 宽度」匹配；
2. `ISS-440` 记 **GAP**（多 hart 前必须补），不硬造单 hart 载体；
3. 向量：`tests/inst/12-misc/sc.*` 补两类点——「异常进入后 `sc` 失败」与「同字异址写不清保留」。

## 验收（逐条贴真实 rc）

1. 三平台同一 ELF 的 `sc` 结果**逐字节相等**（含 4 条异常路径）；
2. **可达 FAIL ≥3 路**：三平台各注入一次（去掉清除动作 / 改回整字粒度 / 异常路径漏清），各自回红，`cp`+md5 还原后回绿；
3. `check-inst-asm` 272/272；`check-patch-tree` qemu/gem5/chipyard 三段各自 0 问题；
4. 完成后在 `issues.yaml` 给 `ISS-443`/`ISS-435` 填 `resolved_by`（`ISS-440` 保持 open 并记 GAP 理由）。

## 约束

独立 `git worktree`；**不提交 git**；**不改 spec**（要改须用户授权）；改三平台源码时按组件补丁树（`docs/Process-01`）导出；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-22，自主逐行）

范围：三平台保留清除点、向量点 17-26 与册/文件宏、证据脚本四模式、issues/changelog/补丁导出。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书背景「三平台均未实现/粒度全错」与现盘不符（chipyard 自 `m12-chipyard-010` 已清、自 `m13-chipyard-002` 已精确） | ✅已修（按实测落点） | 只改 qemu（CFXTRAP 缺口）与 gem5（四路径缺口）；chipyard 源码 0 改动 | 改前探针 chipyard `1,1,1,1` / qemu `1,1,1,0` / gem5 `0,0,0,0`；改后三方 `1,1,1,1` |
| F2 qemu 原清除点在 `dadao_cpu_do_interrupt`，同时命中 semihosting 短接（非 spec 清除事件） | ✅已修 | 清除收敛到 `cfx_enter()` 进入向量处，删钩子顶部清除 | 四路径探针全 1；semihosting 路径不再清（无既有载体依赖） |
| F3 chipyard 共享源树落后于本分支补丁集（缺 `WumingCache.scala`）⇒ `check-patch-tree` ⑥⑨ 红 | ✅已修 | 对 chipyard 源树 `reset` 到 manifest base 后重放补丁集并重编 Tiny sim | `--source-state` chipyard OK base+1 clean；目标三段 assertion=0 |
| F4 chipyard 重建环境未固化（JDK21 ⇒ sbt `bad constant pool`；缺 conda PATH ⇒ firtool/`fesvr` 头缺失） | ✅已修 | 证据脚本固化 JDK17 + `.conda-env/bin` + `RISCV` + `LD_LIBRARY_PATH`，并强制删 `.fir`/模型目录 | `make verilog`+`make` 各 rc=0（注入版与还原版各一次） |
| F5 首版宽度注入锚点写在 `helper.c`（实际 `gen_sc` 在 `translate.c`）⇒ apply rc=1 | ✅已修 | 锚点改 `translate.c`，备份独立 | `inj.qemu.width` apply/red(26)/green(0) 全 PASS |
| F6 `check-patch-tree` 总 rc=1（linux/musl 共享源树同样落后，非本任务组件） | ⏸延后（环境） | 不改他组件；证据脚本只断言 qemu/gem5/chipyard 三段 0 assertion 并打印归属 | 目标三段 0 assertion；INFO 列出 linux/musl |
| F7 点 26 只测宽度键、未覆盖「sc 偶发失败」 | ❌不修（有据） | 偶发失败允许实现自由，spec 不要求可构造 | spec/SimRISC-12 §1 只允许多种非 0；不进向量 |

未修 finding：无（F6 为环境、F7 为明确不修）。

### 第 1 轮 reviewer 验收（2026-11-22，判决：Accepted）

**重跑（仓库根执行运行期证据目录内的 `run.sh`，不带参数）**：真实输出 `证据结果: PASS=36 FAIL=0`、`EXIT=0`；含 `probe.{chipyard,qemu,gem5}.slots 期望=1,1,1,1 实际=1,1,1,1`、`probe.3plat_identical 逐槽相同`、四 id `3plat_bytes 逐字节相同`、点 17-26 逐点 oracle 全 PASS、`bin.stable_during_run` PASS。四路径同 ELF：探针只 build 一次、三平台共用该镜像。

**独立注入 2 路（`cp` 备份 + md5 对账 + 重建回绿；未用 git checkout/restore/stash）**
- qemu 去清除：源 `target/dadao/helper.c` md5 `c904e1b7…`→`5cca0451…`，`make build-qemu` rc=0，跑同一脚本 `EXIT=1`：`probe.qemu.slots 期望=1,1,1,1 实际=0,0,0,0`、`probe.3plat_identical 有差异`、向量 `qemu rc={22,18,18,18}`（恰停在异常进入点 22/18）、`suite_rc=1`、`patch-tree.qemu.assertions 期望=0 实际=2`。还原 md5 回 `c904e1b7…`，重建后构建树与安装根同为 `128c87b9…`。
- gem5 去清除：源 `src/arch/dadao/tiny_cfx.cc` md5 `f7d72835…`→`49b62aad…`，`make build-gem5` rc=0，跑同一脚本 `EXIT=1`：`probe.gem5.slots 期望=1,1,1,1 实际=0,0,0,0`、向量 `gem5 rc={22,18,18,18}`、`patch-tree.gem5.assertions 期望=0 实际=2`。还原 md5 回 `f7d72835…`。
- 还原后整脚本回绿 `证据结果: PASS=36 FAIL=0`、`EXIT=0`（三段 patch-tree assertion 全回 0）。副作用披露：gem5 重建后 `gem5.opt` md5 `36ddbe73…`→`2769e46a…`（gem5 链接非确定性；源码已还原、行为回绿），qemu 源与二进制均还原。

**向量与派生数据**：`sc.b.nn` 新点 22-26、`sc.{w,t,o}.nn` 新点 17-18 与 `12-misc.inc` 的 `__PT_SC_EXC_ENTRY` 逐条核对（四路径期望全 1、粒度点期望 0）；`case-ledger.tsv`、`inst-signature/{expected.tsv,inputs.sha256}` 用 `make inst-signature-data` 与 `check_case_ledger.py --write` 重生成，三文件 md5 与入库逐字节相同（`80a260b0…`/`02b9ae3f…`/`1fc022ac…`）⇒ 工具派生、非手改。

**门控（本人重跑，非采信完成区）**：`check-inst-asm` 272/272（链例+故障链 632 例）rc=0；`check-inst-sig` 272/272、静态槽 4501 逐槽一致 rc=0；`check-case-ledger`（现场 5692 条）/`check-inst-macro-scope`/`check-index-blobs`/`check-component-changelog`/`check-issues` 均 rc=0；`check-patch-tree` qemu 69 / gem5 106 / chipyard 26 patch、三段 assertion=0（26 个 problem 全在 linux/musl，总 rc=1 属环境）。

**源码判断**：QEMU 清除点唯一（`helper.c` 内 `lock_valid = 0` 仅 1 处，落在 `cfx_enter` step 7、`*entered = true` 之前；`ci<0` 与 async 被掩码的早退在其前，semihosting 短接不经 `cfx_enter`，sync/PTW/trap/异步四类全经它）；gem5 Tiny 单入口 `tinyCfxRaise` 清、Node 三处（fault/async/trap）均在 `entered` 后清、返回路径 `setPc` 不清；chipyard 源码 0 改动，清除在补丁集 `WumingCore.scala.patch` 的 `enterHmon`（由 `m12-chipyard-010` 引入），`scHit` 为 `resvAddr && resvWidth` 精确键 ⇒ 不是「本来就没实现」（chipyard 全量重建约 1 h，本轮按任务书允许的**静态确认**，未做第 3 路注入）。

**约束**：`spec/` 0 改动；`git status` 15 个文件全在任务范围，注入前后快照逐行相同；`ISS-443`/`ISS-435` 已 `status: closed` + `resolved_by`，`ISS-440` 仍 open 且追加 GAP 理由；未提交 git、未改实现与完成区。

**Accepted**。非阻断 finding（记档不返工）：`bin.qemu.install_eq_build` 在用 `QEMU=` 覆盖时两侧取同一路径、退化为恒真，默认态（安装根 vs 构建树）才是有效比对。

## 完成区

**测试结果**：证据脚本默认 36/36 PASS（rc=0）；`--inject` 24/24 PASS（rc=0）；`check-inst-asm` 272/272 PASS；四路径探针三平台均 `slots=1,1,1,1` 且逐槽相同；`sc.{b,w,t,o}.nn` 三平台 `.out` 逐字节相同、逐点 oracle 全 PASS。
**修改文件**：`components/qemu/patches/target/dadao/helper.c.patch`、`components/qemu/changelog.md`、`components/gem5/patches/src/arch/dadao/{tiny_cfx,node_cfx}.cc.patch`、`components/gem5/changelog.md`、`tests/inst/12-misc/12-misc.inc`、`tests/inst/12-misc/sc.{b,w,t,o}.nn_orrr_rd.S`、`tests/case-ledger.tsv`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`（均 `--write`/重生成派生）、`.tao/knowledge/issues.yaml`、本任务书。
**验收结果**：
- 改前/改后同一探针（`exc4.S`，MALIGN/CFXMEM/ILLI/CFXTRAP）：chipyard `1,1,1,1`→`1,1,1,1`；qemu `1,1,1,0`→`1,1,1,1`；gem5 `0,0,0,0`→`1,1,1,1`。
- 正式向量：`sc.b.nn` 26 点（新增 17-19 粒度、22-25 四路径、26 同址异宽）、`sc.w/t/o.nn` 各 18 点（新增 17 粒度、18 MALIGN 进入）；三平台 `.out` `cmp` 逐字节相同，oracle 逐点 `17:0 18:0 19:0 20:1 21:1 22:1 23:1 24:1 25:1 26:1`。
- 注入 4 路（`cp`+md5 还原，还原后重建）：qemu 去清除 `0,0,0,0`→回绿；qemu 去宽度键点 26 `rc=26`→回绿；gem5 去清除 `0,0,0,0`→回绿；chipyard 去清除 `0,0,0,0`→回绿（还原源码 md5 一致、sim 重建）。
- 门控：`check-inst-asm` 272/272（链例+故障链 632 例）；`check-patch-tree` qemu 69 / gem5 106 / chipyard 26 patch，三段 assertion=0（总 rc=1 仅 linux/musl 共享源树落后，已披露）；`check-inst-sig` 272/272（静态槽 4501 逐槽一致）、`check-index-blobs`/`check-component-changelog`/`check-case-ledger`/`check-inst-macro-scope`/`check-issues` rc=0。
- 二进制：qemu 安装根=构建树 `128c87b9…`；gem5 `36ddbe73…`；chipyard Tiny `6da0d97e…`；bootrom `a5d78816…`；运行前后 md5 不变。
- `spec/` 0 改动；未提交 git；chipyard 组件无源码改动（0 补丁变更）。
**新发现/坑**：① chipyard 重建必须 JDK17（21 触发 sbt `bad constant pool`）+ `.conda-env/bin`/`RISCV`（否则 firtool、`fesvr/tsi.h` 缺失）；删 `.fir` 与模型目录才能强制 re-elaborate。② chipyard sim 每次干净重建 md5 不同（`ISS-453`），行为判据不取 md5。③ `check-patch-tree` 的总 rc 会被 linux/musl 共享源树拖红——判目标组件须按段解析 assertion。④ 异常进入探针依赖 hmon `+0xF8` 返回槽（框架既有约定），四路径落点用 `.org` 钉在 `.text` 0x3000-0x3300。⑤ semihosting 短接按 spec 不算「异常/中断进入」，清除点放 `cfx_enter` 后不再误清。
**遗留问题**：`ISS-440`（多 hart 同址同宽 store 清保留）保持 open（GAP 已写入 issues）；`check-patch-tree` 总 rc=1 的 linux/musl 共享源树落后属环境、未处置；Node/Vast 的 gem5 清除路径已实现但本任务仅以 Tiny FS 验证（无既有 Node 向量覆盖该事件）。
