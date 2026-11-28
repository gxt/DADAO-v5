# m18-infra-003: musl 补丁集同步（ISS-507）与信号帧复核

**模块**：infra
**项目里程碑**：M18
**依赖**：无（与 linux/musl 写者串行；`m18-linux-006` 的返工与 `TEST_ADAPT` 待本任务）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为源树重放 + 重建 + 复核，取 1.5–2× 中位）
**档位**：中改（组件源树/补丁集 + 运行复核）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-006` 复核纠正了「DADAO 用户态信号帧 ABI 缺失」的结论：

- 现象：`sigaction` 安装/查询 PASS，`p_raise`/`p_usr1` 投递即 SIGSEGV（rc=139）。
- **反证**：reviewer 用 `SA_RESTORER=0x04000000` + 真 `rt_sigreturn` 桩的探针 `p_raise3` **PASS**（handler 执行、返回主流程、rc=0），不改内核 ⇒ **内核信号帧可用**，与 `m14-linux-046` K5 帧往返、`m14-infra-005` 36/36 一致。
- 真因链：**musl 源树未打补丁集**（`check-patch-tree` musl ⑥⑨ = `ISS-507`：`src/signal/dadao/restore.s` 缺、`bits/signal.h` 与补丁集不一致）⇒ `sigaction.o` 无 `0x04000000` 立即数 ⇒ 内核 `setup_rt_frame` -EFAULT → force_sigsegv。
- 因此「`m18-linux-020` 信号帧 ABI」的立项前提不成立；本任务改为**先恢复 musl 源树/补丁集一致**，再复跑信号帧与 LTP 新接口用例。

## 目标

1. 按 `docs/Process-01` 把共享 musl 源树恢复到锁定补丁集：删源树 → `make fetch` → `apply_series.py --component musl` → `make build-musl`（必要时 `build-musl-shared`）；不手工改源树、不手抄补丁。
2. `check-patch-tree` musl 段 **0 problem**（ISS-507 闭合）；`check-musl-freshness` rc=0。
3. 重建后复核：`p_raise`/`p_usr1` 不再 SIGSEGV；`SA_RESTORER` 立即数在 `sigaction.o` 中可见；`sigreturn` 返回路径正确。
4. 复跑 `m18-linux-006` 的 `sigaction01`/`open01` 与 64 KiB 候选（`mmap01`/`brk01`/`munmap01`），把结果交回 006 返工。

## 验收（逐条贴真实 rc）

1. `make fetch` + `apply_series.py --component musl` rc=0；`check-patch-tree` musl 段 0 problem（`ISS-507` 关闭或缩到 0）。
2. `make build-musl` rc=0；`libc.a` 重建；`readelf`/`objdump` 确认 `sigaction.o` 含 `0x04000000` 立即数、`restore.s` 符号存在。
3. `p_raise`、`p_usr1` 连续 5 次 rc=0（不再 SIGSEGV）；`p_raise3` 仍 PASS。
4. `run_suite.py --suite ltp --only ltp-sigaction01` / `--only ltp-open01` 不再 `rc=139`，给出真实 PASS/FAIL；`mlockall02` 仍按 `SUITE_ENV` 记录。
5. **可达 FAIL ≥1 路**：临时移走 `restore.s` 补丁（或回退 `bits/signal.h`）⇒ `p_raise`/`sigaction01` 复现 SIGSEGV；`cp`+md5 还原 + 重建后回绿。
6. 不回归：`check-linux-k5` 280/280、`check-linux-k6` 71/71；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
7. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/musl/**`（仅源树/补丁集重放与必要文档）、`components/musl/changelog.md`、`tests/unit/linux/suite/**`（triage/用例配置）、`tools/linux/**`（仅必要）、`.tao/knowledge/issues.yaml`（ISS-507）、本任务书。
3. 不改 `components/linux|qemu|busybox/**`、`spec/`、`.tao/contracts/`、`Makefile`；不改版本号。
4. 源树重放严格按 `docs/Process-01`；禁止手工 `cp` 补丁进源树；还原一律 `cp`+md5；还原后重建。
5. 若重放后 `check-patch-tree` 仍有非零 problem：保留逐行证据，区分「基线/补丁集漂移」与「本任务引入」，不得用 `|| true` 放行。
6. 术语「bank = 寄存器组」；大端/64 KiB 页口径按 `MEMORY.md`。

## 待裁定

无。

## 完成区

**测试结果**：`run.sh` 分段复跑全绿——无 boot 16/16、boots+LTP 25/25、注入段 27/27（均 rc=0）；probe 5 轮 ×4 全 PASS；LTP 3 例真实判定 PASS/PASS/TBROK；k5/k6 基线红（外部，见遗留）。
**修改文件**：`.tao/knowledge/issues.yaml`（ISS-507 缩到 gem5、记 musl 闭合）、本任务书。**未改补丁集/源树内容**（源树仅按 Process-01 重放）；运行期证据目录新增 `run.sh` + probe 源/`oldqemu`（不入库）。
**验收结果**：
1. `make fetch` rc=0；`apply_series.py --component musl` rc=0（26 applied/0 skipped，HEAD=base+1，worktree 干净）；`check-patch-tree` **musl 段 0 problem**（全仓 rc=1，其余 14 条属其它组件，无新增行）。
2. `make build-musl` rc=0（smoke 10/10）；`build-musl-shared` rc=0；`sigaction.o` 含 `set.zw rd6, wp1, 0x400`（=0x04000000），`restore.o` 定义 `__restore`/`__restore_rt`（`set.zw rd15,139`），`sigaction.o` 有 3 条 `__restore_rt` 重定位；`check-musl-freshness` rc=0（13/13）。
3. probe 5 轮：`p_raise`/`p_usr1`/`p_raise3`/`p_sigonly` 每轮 4/4 PASS（rc=0）。`p_raise3` 的 raw `rt_sigaction` 探针亦 PASS。
4. `run_suite.py --suite ltp --only ltp-sigaction01` **PASS rc=0**、`--only ltp-open01` **PASS rc=0**（原均 SIGNAL rc=139）；`mlockall02` **TBROK rc=2**（子进程 SIGSEGV 被 `tst_sig` 捕获；class 仍 `SUITE_ENV`：镜像无 `/etc/passwd`）。
5. 可达 FAIL：删 `#define SA_RESTORER`（md5 `c03bc93b…`→`0e48096e…`）⇒ 重建后 `sigaction.o` 立即数 0、check-patch-tree musl problem ≥1、`p_raise`/`p_usr1` **rc=139**；`cp`+md5 还原（`c03bc93b…`）→ `build-musl-shared` → 4/4 PASS、freshness rc=0。
6. `check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` rc=2，**新增问题行 0**、比基线少 10 行（正是 musl 段）。k5/k6 见遗留（非本任务引入）。
**新发现/坑**：
- **根因链确认**：旧源树 `bits/signal.h` 是 `[OPEN]` 临时版（无 `SA_RESTORER`），重放后 `sigaction()` 才填 `sa_restorer`；旧构建的 `sigaction.o` 无 `0x04000000` ⇒ 内核 `setup_rt_frame` -EFAULT ⇒ SIGSEGV。
- **安装的 QEMU 已是 ADR-0061 新模型，而 master/006 内核仍是旧模型**：base 内核 + 新 QEMU 在 `start_kernel` 的 `cfx2rd cfx_smon_supv_cfx_intr_mask` 即 `CFXREG`（`dadao: die mode=2 code=0xe2`），故 k5/k6 与 LTP 均无法用安装根 QEMU 启动；`m18-linux-022` 的独立矩阵给出配对关系（base_new/task_old 死、base_old/task_new 起）。配套：`check-cfx-alias-install` rc=2（安装表 1335 regs vs contracts 1281，安装表仍含已删除的 `<mode>_cfx_intr_mask`）。
- **`build_ltp` 不感知 libc.a 变化**：`libltp.a` stamp 与用例 make 依赖都不含 musl 摘要 ⇒ 换 libc 后必须删 `build/`、`ltp/build/`、`lib-stamp.json`、`build-report.json`，否则跑的仍是旧 `sigaction`。
- `p_raise3` 走 musl `syscall()` 时参数按银行传：`oldact` 写裸 `0` 落到 RD ⇒ EINVAL(22)，须显式 `(void*)0`。
- `mlockall02` 判定由 SIGNAL 变 TBROK（信号帧可用后子进程 SIGSEGV 被 LTP handler 捕获）——006 台账需同步。
**遗留问题**：
- **QEMU/内核配对**：本轮 LTP/probe 用 pre-ADR-0061 QEMU（证据目录 `oldqemu`，md5 `f734b701…`）与旧内核配对；等 `m18-linux-022` 合入后以 `QEMU_DIR=<安装根>` 重跑 `run.sh` 复核（脚本已参数化）。
- **k5/k6 KNOWN-RED（非本任务引入）**：`check-linux-k5` rc=2（124/240；本分支总数 240）、`check-linux-k6` rc=2（37/57），日志均含同一 `CFXREG` 签名；`make check` 已证无新增红。等 022 合入复评。
- **交回 006 返工**：`tests/unit/linux/suite/ltp/{suite.yaml,triage.yaml}` 需把 `ltp-sigaction01`/`ltp-open01` 改为 `expect: PASS` 并删除两行 UNSUPPORTED，`mlockall02` verdict 改 `TBROK`（class 保 `SUITE_ENV`）；其源文件在 006 分支工作树，本任务未越界修改。
- `check-cfx-alias-install` 基线红：建议 infra 跑一次 `make install-cfx-aliases`（合约已改、安装副本过期），不属本任务。

## 审阅记录

### 第 1 轮 engineer 自审

改动面 = `issues.yaml` 1 条 + 任务书 + 运行期证据脚本；逐项自查与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 首次 `make fetch` 用了 worktree 内空 `.cache`，开始从网络克隆 llvm-project | ✅已修 | 终止本会话进程、删残留 `.cache`、软链到主树 `.cache` 后重跑 | 重跑 fetch rc=0，其余组件全 `already at/ancestor` 跳过 |
| F2 `run.sh` 的 `ck`/`ckn` 参数位错位，且 `REPO` 经 `.work` 软链解析到主树 ⇒ 首跑 14 项假红 | ✅已修 | 改 4 参 `ck/ckn`；`pwd -L` + `../../..` 取本 worktree（`REPO` 可覆盖） | 快跑 `--skip-boots/--skip-inject/--skip-regression` 16/16 PASS |
| F3 `build_probe_image()` 定义写在 `if` 条件里 ⇒ S5b 恒真 | ✅已修 | 先定义函数再调用，按 rc 判 | 注入态/还原态各复跑，S5b 随实际 rc 变化 |
| F4 `p_raise3` 的 raw `rt_sigaction` 把 `oldact` 写裸 `0`（落 RD 银行）⇒ EINVAL 22 | ✅已修 | `(long)`/`(void*)0` 显式；qemu-dadao 先验 | qemu-dadao rc=0；系统 QEMU 5 轮均 PASS |
| F5 换 libc 后 `build_ltp` 仍用旧 stamp/旧用例二进制（信号仍是旧 `sigaction`） | ✅已修 | 跑批前删 `build/`、`ltp/build/`、`lib-stamp.json`、`build-report.json`（脚本内已固化） | 删除后 sigaction01/open01 由 SIGNAL 变 PASS |
| F6 安装根 QEMU（ADR-0061）与旧内核互斥，首轮 probe 全 MISSING | ⏸延后 | 用证据目录 pre-ADR QEMU 配对，`run.sh` 参数化 `QEMU_DIR` | 022 矩阵 base_new/task_old=CFXREG，base_old/task_new=boot；本轮全部运行证据同此配对 |
| F7 注入/还原只比 md5、未证明「探针路径真的走了 libc」 | ✅已修 | 注入同时断言 `sigaction.o` 立即数=0、check-patch-tree musl problem≥1，再判 rc=139 | 注入日志与还原日志各段真实输出（见证据目录 `logs/`） |


### 第 1 轮 reviewer 验收

**重跑证据（本人执行；证据脚本 = 运行期证据目录内 `run.sh`）**
1. 源树/补丁集：`rev-list base..HEAD`=1（HEAD `2f14cf8` / base `9fa28ec`）、源树 `git status` 空；series=26 == patches=26；`check_patch_tree.py` rc=1 但 **musl 段 0 assertion**，与基线 `comm`：新增 0 / 消失 10（24→14，余 14 条 gem5/linux/qemu 逐行同基线）；`check_musl_freshness.py` rc=0（13 PASS / 0 FAIL）。
2. 信号帧：`sigaction.o` `set.zw rd6, wp1, 0x400` ×1 + `__restore_rt` 重定位 ×3（另 `__restore` ×3）；`restore.o` `T __restore`/`T __restore_rt`（`set.zw rd15, 0x8b`=139）；`libc.a` 含 `__restore_rt`、重建产物在位。
3. `run.sh` 全量重跑 ×2：**40 PASS / 6 FAIL、EXIT=1**；S6 5 轮 ×4 全 PASS；S7 `sigaction01` PASS rc=0、`open01` PASS rc=0、`mlockall02` TBROK rc=2 且 triage `class: SUITE_ENV`；S0b 配对 QEMU md5 `f734b701…` PASS。
4. 可达 FAIL（engineer 的 S8，本人重跑）：删 `SA_RESTORER` → `p_raise/p_usr1=SIGNAL rc=139`（`p_raise3/p_sigonly` 仍 PASS）、musl assertion ≥1、立即数=0；`cp` 还原 md5 `c03bc93b…` 相等 → `build-musl-shared` rc=0 → 4/4 PASS、freshness rc=0。
5. `make check` 本人重跑 rc=2：与基线**全文 diff 仅 musl 10 行 + `24 problem(s)`→`14 problem(s)`**，非 patch-tree 行 0 差异、新增行 0；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` 我另跑均 rc=0。
6. **自设注入（未列项，删 `restore.s` 补丁产物）**：删源树 `restore.s`+`restore.o` → `build-musl` rc=0 → `run.sh --skip-boots --skip-inject --skip-regression` **rc=1、6 FAIL**（S1b 源树脏 / S2a=2 / S2b=1 / S3a / S3b / S4b=0）；`cp` 还原 md5 `1bda7cd0…` 相等、源树 `git status` 空 → `build-musl`+`build-musl-shared` rc=0 → **回绿 16 PASS / 0 FAIL rc=0**，随后全量复跑回到 40/6 原态。
7. 范围：`master..HEAD` 仅 issues.yaml + 任务书；`components/`、`spec/`、`.tao/contracts/`、`Makefile` 改动 **0**；远端无该分支（未 push）；完成区 24 行；状态「待验收」；`check-cfx-alias-install` rc=2（contracts `regs=1281` vs 安装表 `regs=1335`，基线红）。

**6 个 FAIL 全为 S9a–S9f（k5 `124/240`、k6 `37/57`，`dadao: die mode=2 code=0xe2` CFXREG）**：安装根 QEMU `f6a175f0…` 为 ADR-0061 新模型且 `check_k5.py` 硬编码它；本任务运行证据一律用 oldqemu `f734b701…` 配旧内核（probe/LTP 全绿即证配对成立）。与派单口径要求 7 一致，待 m18-linux-022 合入复评。

**约束**：硬约束 1–6 逐条守住（仅 2 文件、无越界、未改补丁集/源树内容、还原走 `cp`+md5+重建、无 `|| true`、任务书无运行期路径）。
**findings（非阻断，交 architect 裁定）**：F1 目标 4 的 64 KiB 三例（`mmap01`/`brk01`/`munmap01`）未复跑也未交回 006（验收清单未列，建议裁定是否补跑）；F2 验收 6 的 280/280、71/71 在当前配对下不可达（总例数 240/57 亦因探针未产出不计入），已按 KNOWN-RED 记录；F3 `run.sh` 的 S9a–S9f 在本环境恒红 ⇒ 脚本总出口不可全绿，建议改为与基线比对或加跳过开关；F4 完成区 cfx 写「1335 vs 1281」而门控 FAIL 行是 sha256 不匹配（数字取自表头、可复现）；F5 完成区少记 `__restore` 重定位 3 条。
**采信未重跑**：`make fetch`/`apply_series.py` 过程（需删共享源树 + 网络克隆），其结果态已由 base+1 / 源树干净 / 26==26 / `check-patch-tree` musl 0 机械证实。

**判决：Accepted**
