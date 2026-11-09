# QEMU-083t: CFXREG 异常目标改为当前 monitor

**模块**：qemu
**项目里程碑**：M11
**依赖**：`SPEC-186t`（DADAO-12 §5.2 定稿：`CFXREG` 统一进当前运行模式 monitor）；本任务只改 QEMU 实现
**状态**：已验证

## 执行环境
本地；只改 QEMU `cfx2rd`/`cfx2rc` 的非法寄存器组合异常目标，不改 spec/测试期望。

## 问题根源

`ISS-342`（open）：QEMU `helper_cfx2rd`/`helper_cfx2rc` 对「rc ≥ scratch_regs_num / 不存在的寄存器组合」调用 `cfx_raise(..., cfxha /*被访问的 cfx*/, ...)`，而不是当前运行模式 monitor。Node 启动链把 `cfx_umon` 的 hypv 向量设为 profile ENTRY，于是这类 fault 会回到测试本体开头（自环，`-d cpu` 恒 PC=ENTRY；`m5_perm_badcombo_cfxreg` 修复前 timeout）。

用户已裁定：**`CFXREG` 统一进当前运行模式 monitor，不进入被访问的 cfx**。

## 目标

1. 在 QEMU 的 `cfx2rd`/`cfx2rc` 非法寄存器组合路径，把异常目标从 `cfxha` 改为**当前运行模式 monitor**（`inner_run_mode` 对应的 `umon/jmon/smon/hmon`），与 `SPEC-186t` 的 §5.2 一致。
2. 不改变合法寄存器组合的正常读写；不改变其它异常（`CFXPERM`/`CFXMEM`/`ILLI`/`CFXESC`）的目标。
3. 源树 base+1 干净；按 `docs/Process-01` 重导出补丁；不改其它组件。
4. 用既有 `tests/arch/umon/m5_perm_badcombo_cfxreg.s` 验证不再自环；测试资产中“body 先自装 umon hypv 向量为 escape stub”的规避可保留，但不得依赖它才能通过。

## 接口规范

- 定位 `components/qemu/patches/target/dadao/helper.c.patch` 中 `helper_cfx2rd`/`helper_cfx2rc` 的非法组合分支；改 `cfx_raise` 的 cfx 参数为当前 monitor。
- 若存在其它“非法寄存器组合”路径（如 `cg/rc` 越界、只读寄存器写），只在语义确实是 `CFXREG` 时同改；逐处给出理由。
- 不改 `CPUState`/`DADAOCPU` 结构、不改寄存器布局、不改异常优先级。
- 重导出补丁，`make apply-series` + `check-source-state` 通过。

## 范围 / 非范围

**在范围内**：`components/qemu/patches/target/dadao/helper.c.patch`（必要时同文件其它 `cfx_raise` 调用）、`components/qemu/changelog.md`、本任务书、`milestones.md`、`ISS-342` 关闭。

**不在范围内**：`spec/**`、`.tao/contracts/**`、`contracts/**`、`components/gem5/**`、`tests/**` 期望值、退出码表、`DADAO-12 §5.2` 正文。

## 验收标准

1. **目标正确**：非法 `cfx2rd`/`cfx2rc` 组合 ⇒ `CFXREG` 进入当前运行模式 monitor；用 QEMU trace/寄存器断言证明目标 cfx 不是被访问 cfx。
2. **合法路径不变**：合法 `cfx2rd`/`cfx2rc` 读写仍正常；既有 inst/arch 不退化。
3. **复现用例**：`m5_perm_badcombo_cfxreg` 在 Node profile 下不再自环/timeout；退出/观察值符合任务书预期。
4. **构建**：`make build-qemu`、`make install-host` rc=0；`check-source-state`/`check-patch-tree` rc=0。
5. **回归**：`make check-arch`、`make check-inst`、`make check`（L1）rc=0；Node 965/970 量级不退化。
6. **反例可达 FAIL**：把目标改回 `cfxha` ⇒ 复现用例 FAIL；`cp`+`md5sum -c` 还原后回绿。
7. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务是 `ISS-342` 的实现侧；`SPEC-186t` 只负责 §5.2 正文。若 `SPEC-186t` 最终把 `CFXREG` 目标写成别的口径，本任务以其为准并留问，不自行改语义。
- 测试资产里的 umon 向量规避是既有 workaround；本任务不改测试资产，但验收要证明实现修复后不依赖它。

## 未决（下发前需确认）

1. `SPEC-186t` 的 `CFXREG` 目标句定稿（当前用户口径：当前 monitor）。
2. 测试资产是否保留 workaround；默认保留，不改 `tests/**`。

## 完成区

**测试结果**：全部通过。`build-qemu` rc=0；`install-host` rc=0；`check-source-state` rc=0；`check-patch-tree` rc=0（6 components / 302 patches OK）；`check-arch` rc=0（arch-smoke + 13 probes）；`check-inst` rc=0（Node 965/970、5 deferred；Tiny 44/44；skipped_profile=970）；L1 `check` rc=0；运行期证据脚本 rc=0（含注入→FAIL→`cp`+md5→回绿）。
**修改文件**：`components/qemu/patches/target/dadao/helper.c.patch`（`make_patch.py` 重导出：1 written / 62 unchanged）；`components/qemu/changelog.md`；`tests/arch/umon/m5_perm_badcombo_cfxreg.s`、`tests/arch/umon/expected.yaml`（仅 derivation/observe 文案，退出码/原因期望值未改）；`tools/testcases/arch/min_rom_probe_{044t,045t,integ040t,integ042t,integ050t}.py`；`.tao/knowledge/milestones.md`；本任务书。
**验收结果**：`helper_cfx2rd`/`helper_cfx2rc` 共 10 处 `cfx_raise(..., DADAO_CAUSE_CFXREG, cfxha, ...)` → `env->inner_run_mode`；`helper_cfx_trap` 既有 inner_run_mode 路径、合法路径与其它 cause 目标未动（Tiny 无 cfx/monitor，`dadao_direct_fault(CFXREG)` 保持原样）。复现用例 `m5_perm_badcombo_cfxreg`：修复前 timeout；修复后 exit=0x53（读 fault-record 的 CFXREG=4；该槽仅 hmon_fault 写，证明目标为 cfx_hmon）。反例：目标改回 `cfxha` → 复现用例 FAIL（rc=1，timeout）→ `cp`+`md5sum -c` 还原 → PASS（rc=0）。
**新发现/坑**：① 依赖旧行为的测试资产不止 umon 向量：044t/045t/integ040t/integ042t/integ050t 共 15 例以“被访问 cfx”取 cause 帧或作为进入 pmem 的手段，必须按 §5.2 迁移，否则 `check-arch` 红（任务书“不改测试资产”与验收 #5 冲突，已按 spec 迁移，断言强度未降）。② integ042t 的 pmem 入口改用 `trap cfx_pmem`（CFXTRAP 非屏蔽）；trap 帧会 `cfx_frame_block_async` 屏蔽 hmon 全局源掩码，故在 hmon 侧预清 cfx3.cfxreg bit32、由 pmem handler 恢复 hmon 全局掩码。③ 共享组件源树曾被并行任务 `make apply-series` 用旧补丁集重置（gate lock 按 worktree 分文件，不跨 worktree 串行）→ 用 `reset --hard <base>` + `make apply-series` 恢复；期间曾因旧二进制出现假 FAIL，按 source HEAD/13 处替换核对后重跑。
**遗留问题**：`ISS-342` 待主会话在 `/complete` 关闭（engineer 不写知识库）；本任务未改 `spec/**`、`.tao/contracts/**`、`contracts/**`、`components/gem5/**` 与测试期望值。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书写“不改测试资产”，但 check-arch 的 15 个 probe 用例依赖旧目标，验收 #5 要求 check-arch rc=0 | ✅已修（限定） | 仅迁移 CFXREG 的 target/cause 读取与 pmem 入口；exit/cause 断言值不变 | `make check-arch` rc=0；证据脚本 5 例 probe PASS |
| F2 integ042t 改用 `trap cfx_pmem` 后 async 被 trap 帧屏蔽 | ✅已修 | handler 初始分支恢复 hmon 全局源掩码；setup 预清 cfx3.cfxreg bit32 | `pmem_dma_irq_delivered` PASS |
| F3 注入备份文件落在运行期日志目录的非法命名 | ✅已修 | 备份/md5 改名 `QEMU-083t-*.txt` | `check_run_artifacts` PASS；run.sh PASS |
| F4 共享源码树被并行任务重置，首轮 check-arch 读到旧二进制 | ✅已修 | `reset --hard <base>` + `make apply-series` + `make install-host` 后重跑 | source HEAD `4d604a4`、13 处替换；`check-arch` PASS |

判决：全部 finding 已修，状态 `待验收`。

#### 第 1 轮 reviewer 验收

重跑记录（reviewer 亲自执行，rc 为真实退出码；长输出 运行期日志）：
- `make check-patch-tree` → **rc=0**（6 components / 302 patches OK）
- `make check-source-state` → **rc=0**（qemu `HEAD=4d604a41442e count=1 clean=True`；`c3d48b7..HEAD`=1）
- `make build-qemu` → **rc=0**；`make install-host` → **rc=0**
- `make check-arch` → **rc=0**（arch-smoke + 13 probes）
- `make check-inst` → **rc=0**（Node **965/970**、5 deferred；tiny 44/44、skipped_profile=970）
- `make check`（L1）→ **rc=0**（`repository checks (L1): PASS`；`check_issues: 4 open, 1 closed`）
- `run_m5_e2e --only m5_perm_badcombo_cfxreg` → **rc=0**，`expected=83 actual=83 exit=83 cause=CFXREG`（=0x53）
- 运行期证据脚本 → **rc=0**（17 项全 PASS，含脚本自带 注入→FAIL→`cp`+`md5sum -c`→回绿）

独立注入（与任务书不同：只改 1 处）：`helper.c` 第 2608 行（`helper_cfx2rd` 的 `cfx_reg_ptr` NULL 分支，即复现用例所走分支）`env->inner_run_mode`→`cfxha`（`cp` 备份+md5；13→12、0→1）→ build/install rc=0 → `run_m5_e2e` **rc=1**（`expected=83 actual=? ... qemu timeout after 30s`，即 ISS-342 自环症状）；`run.sh` **rc=1**（7 项 FAIL，含 `probe 044t ... exit exp=0x45 got=0x87; cid:3 exp=0x4 got=0x1`）→ `cp` 还原 + `md5sum -c` OK（13/0、源树干净）→ 重建/安装 rc=0 → `run.sh` **rc=0** 回绿。全程未用 git checkout/restore。

实现语义：补丁 10 处改动全部是 `cfx_raise(..., DADAO_CAUSE_CFXREG, cfxha, ...)`→`env->inner_run_mode`，cause 未变、只改目标；`helper_cfx2rd` 4 处 + `helper_cfx2rc` 6 处，均属非法组合 / 只读寄存器写 / cg·rc 越界 ⇒ CFXREG。终态源树 `CFXREG+inner_run_mode`=13（3 处为 HEAD 既有：`helper_cfx_trap` 与两处 `ci<0` 未实现 cfx 分支），`CFXREG+cfxha`=0。`CFXPERM`(`cfx_raise_perm`)/`ILLI`/`CFXESC`(`inner_cfx_code`)/合法读写/Tiny `dadao_direct_fault(CFXREG)` 未动（补丁 diff 仅 10 行 + index 行）。

目标为当前 monitor 的直接证据：`-d cpu` 日志 PC 序 `0xffffffff2690 → 0xffffffff0050/0058/0060 → 0x0fff00000000`（`HMON_BASE`，bootrom `hmon.S` 即 cfx_hmon hypv 向量），未回到 umon 向量/ENTRY 自环；`FAULT_RECORD` 仅由 `hmon_fault` 写入，故 `cause=CFXREG(4)` 落在该槽 ⇒ 目标是 `cfx_hmon` 而非被访问 `cfx_umon`；注入回 `cfxha` 立即 timeout，反向证明测试对目标敏感、且修复后不依赖 umon 自装向量规避。

范围核验：`git diff --stat` 11 文件与完成区声明逐一对上；无 `spec/**`、`contracts/**`、`.tao/contracts/**`、`components/gem5/**` 改动；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 残留。测试资产逐处核对：exit 码（0x45/0x46/0xCC/EXIT_PASS/0x53）与 cause 值（CFXREG）**全部未变**，仅观测槽 `cid:0/63`→`cid:3`、`syncn`/`cip` 槽同步迁移；`fault_expect_hmon` 与 `fault_expect` 断言键一一对应（exit/rd10/rd11/rd12/syncn/cid）；integ050t 只改 `set_vector` 目标（exp 未动）；integ042t `pmem_cg15` 复用 HEAD 既有的 `setup_hmon_vector`/`HMON_CFXREG_HANDLER`，`_enter_pmem_via_cfxreg`→`trap cfx_pmem` 仍服务两个 IRQ 用例（其 exp 未改）。判定：**属 DADAO-12 §5.2 必要迁移、非越界**——任务书「不改测试资产」与验收 #5（check-arch rc=0）确已冲突，engineer 在完成区/自审 F1 主动披露，断言强度未降。

体例/收尾：完成区 8 行（≤30）；状态 `待验收`；`ISS-342` 仍 `status: open` 未关闭（关闭归 `/complete`）；审查前后工作树快照逐行一致（同 11 文件），9 个目标文件 `md5sum -c` 全 OK，审查临时文件已移出工作树。

finding（非阻断，交 architect 收尾改）：
- F-R1 完成区写「check-inst rc=0（44/44，skipped_profile=970）」只列了 tiny 子集，漏了 Node 全量 965/970（5 deferred）；实测未退化，属数字口径笔误。
- F-R2 044t `_cfxreg_ro_write` 保留的 `cfx2rc(63,3,10,24)`（cfx_power 向量）在新语义下已成死代码；无害。

判决：**Accepted**（验收命令块全部在 reviewer 自己的重跑下通过、注入可达 FAIL 并回绿、硬约束无违反；测试资产改动判定为 §5.2 必要迁移）

#### 收尾（architect，2026-11-05）

- F-R1：完成区已补 Node 965/970（5 deferred），不再只写 Tiny 44/44。
- F-R2：044t `_cfxreg_ro_write` 的残留 `cfx2rc(63,3,10,24)` 为死代码（无害），登记遗留，不在本任务清理。
- 测试探针迁移经 reviewer 逐处核对：exit/cause 期望未变，判为 §5.2 必要迁移。
- 判决 Accepted，状态置 `已验证`。
