# m14-linux-029: K5 收口门控 `check-linux-k5`（用户态闭环代表例 + 跨阶段不变量 + 退役过时判据）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-023`…`028`（全部 `已验证`）
**可并行分片**：否（单一端到端门控 + 注入重建）
**并行组**：K5 串行链**最后一环**；唯一可并行的只读动作是契约/清单静态比对（不占组件）
**预估**：5–6 h（含注入重建；代表例 + 退役审计）
**档位**：大改（新建 L2 门控 + 退役既有断言 + 注入；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

## 背景

K0–K3 各有收口门控（`check-linux-k0/-k1/-k2/-k3`，均入 L2）。K5 交付「用户态闭环」——`init` 完整跑起来、syscall/`clone`/`futex`/信号/时钟/64 KiB ABI 各面，但边界目前只有任务书描述、**无机械判据**。本任务建 K5 收口门控，断言「阶段 K5 达成」，并按 `docs/Process-07 §4a` 退役 K4 里「用户态尚未闭环」时成立的过时断言。

DADAO 特有事实（沿 K0–K3 门控口径，**不得偏离**）：
- 门控在 `qemu-system kaiwu-vast` 上端到端断言；期望值**现场派生**（页大小 ← `.config`、号表 ← `contract-syscall §1.2` 锁定源、退码段 ← `spec/Kaiwu §7.1`）。
- `check-modules` 会装共享安装根 ⇒ 并行任务窗口内禁跑（`docs/Process-07 §2`）；本门控入 L2（`_locked-check-modules`）。
- 门控必须**能失败**：每条断言有可达 FAIL 路径；计数类期望现场派生（`docs/Process-07 §4`）。

## 范围

1. **新增** `tools/linux/check_k5.py` + `make check-linux-k5`，接线：`Makefile`（`PHONY`/`GATE_LOCKED_TARGETS`/`_locked-check-modules`/`help`/块注释）、`docs/Process-07` 目标-层表一行。
2. **检查组（现场派生，不写死项数；打印 PASS/FAIL 计数）**
   - **S 用户态闭环**（023）：`init` 跑起来 → `write`/`exit` 往返、errno 形态（`rd8` 负值 `[-4095,-1]`）、TLS `rb3` 保持、帧字段 `excp_cause_id==1<<0`/`immu18` 推导。
   - **C clone/线程**（024）：`CLONE_VM` 共享 mm/asid、`CLONE_SETTLS` 子 rbtp、子 `rd8=0`+父返 tid、`CLONE_THREAD` tgid。
   - **F futex/原子**（025）：`FUTEX_WAIT` 原子、`WAKE` 不丢唤醒、用户 `lr/sc` 不跨 syscall；**shared futex 在匿名页上可用**（`035` 修好的 rmap 成果，即 N27 的关闭判据——`K5 futex shared: wake=0 wait=-11 mapping` 带 `PAGE_MAPPING_ANON`）。
   - **T 时钟**（026）：`clocksource` 单调、`clockevent` next-event、tick 驱动、稳定性判据。
   - **G 信号**（027 + 046）：`SIGSEGV` 投递（非 `DADAO_PF_FATAL`）、`exit`、`setrlimit` 继承（027）；**信号帧往返**（`rt_sigreturn` 恢复 4 组寄存器、`ra` 栈逐位、`rf0` 架构值）与「无 handler ⇒ 默认动作终止」（046）。**用户 2026-11-20 裁定范围 B**：K5 收口**必须含 shared futex 与基本信号投递**，不含 pthread create/join（那是 K6）。
   - **P 64 KiB ABI**（028）：`AT_PAGESZ==65536`、`mmap` 对齐、ELF 段对齐、`brk`。
   - **R 反向断言**：用户态各面「不多不少」（无 monitor 段具名终止痕迹、无 `unknown cause`、无 `-d` 逐指令日志）。
3. **§4a 退役**：审计 K4 门控/探针里「用户态尚未闭环」时的过时断言（如 `016` 的「不跑用户 init」、`017` 的「内核侧双任务交替」等），逐条三态处置（保留/改限定语/删除）+ 替代判据来源，机械断言「新文案在 / 旧文案不在」。
4. **K3 整体退役（用户 2026-11-20 裁定：「内核开发不像其它模块，每进展一个阶段，原有阶段的测试可能无法再保留，随时都可以把已过时的测试退役」）**：
   - 删除 `make check-linux-k3` 目标与 `check_k3.py`、`k3_page_probe.py`、`k3_pf_selftest.c`、`k3_pt_selftest.c` 及其补丁条目（`series` 相应减少）；
   - **连带删除 `035` 为 K3 保留的 `current->mm == NULL` PA 直通窗口臂**（`arch/dadao/mm/fault.c` 的 window/frag/superpage 分支）——K3 已无判据依赖它；
   - 在 `Process-07 §4a` 记录退役（判据 → 替代 = K5 收口判据）；
   - 机械断言：退役的符号/目标在树中 0 命中；`check-patch-tree` linux 段 0 问题；K0/K1/K2/K4/K5 全绿。
4. **一键证据脚本**：一条命令跑「构建 → 门控 → selfcheck → 注入 → K0–K3 回归」，退出码如实传播。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `make check-linux-k5` rc=0，检查项计数现场打印（PASS == 总数、FAIL 0）。
2. `--selfcheck` 每组至少一次「翻转输入 ⇒ 红」（S/C/F/T/G/P/R 各一）。
3. **≥4 路可达 FAIL 注入**（`cp`+md5 还原 + 重建回绿）：① errno 写 `rd1` ⇒ S 红；② `CLONE_SETTLS` 不设 rbtp ⇒ C 红；③ `SIGSEGV` 走 `DADAO_PF_FATAL` ⇒ G 红；④ `AT_PAGESZ` 写 4096 ⇒ P 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0（不跑 `check-modules`）。
5. **端到端 pthread 代表例**（用户 2026-11-17 裁定）：initramfs 里跑一个 `pthread_create`/join/共享变量的最小程序，断言线程创建、TLS（`rb3`）、共享 `mm` 与 join 返回正确（这是 `024` 内核侧自检之外的唯一端到端覆盖）。
6. `docs/Process-07` L2 组成表含 `check-linux-k5`；`make help` 有对应行；`GATE_LOCKED_TARGETS`/`PHONY`/`_locked-check-modules` 含之（grep 取证）。
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-029/`。
2. **预计改动文件**：`tools/linux/check_k5.py`（新）、`Makefile`（目标 + L2 接线）、`docs/Process-07-门控分层规范.md`（层表一行 + §4a 处置记录）、本任务书。**不改** `components/**`（注入时临时改、用完还原）、`tests/**`、`spec/**`、`.tao/contracts/**`。
3. 不提交 git；禁 `install-host`/`check-modules`；`JOBS=32`；禁边构建边测试。
4. 门控必须**能失败**：每条断言可达 FAIL；禁恒真、禁「两支写同一结果」；计数现场派生。
5. 只在 `qemu-system kaiwu-vast` 上验收；不重建 QEMU。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~**§4a 退役边界**~~ **已裁定（用户 2026-11-17）**：按 **A「就地退役」**——本任务**同笔**改 K0–K4 门控/探针里依赖「用户态尚未闭环 / K1/K2 镜像限定」的过时断言，逐条三态处置（保留附理由 / 改限定语 / 删除并指向替代判据）；门控内加机械断言（新文案在 / 旧文案不在 / 替代判据指向 / `Process-07 §4a` 有处置记录），`--inject` 加一路「退役文案回潮」验证可 FAIL；完成区逐条披露（与 `m14-linux-015` 同口径）。
2. **K5 门控运行口径（已裁定，用户 2026-11-17）**：沿用 `m14-linux-015` 的口径——门控只跑**代表例**，全量 case 由对应探针（`k5_*_probe.py`）单独跑；不把全量塞进门控。

## 审阅记录

（待填）
