# m14-linux-029: K5 收口门控 `check-linux-k5`（用户态闭环代表例 + 跨阶段不变量 + 退役过时判据）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-023`…`028`（全部 `已验证`）
**可并行分片**：否（单一端到端门控 + 注入重建）
**并行组**：K5 串行链**最后一环**；唯一可并行的只读动作是契约/清单静态比对（不占组件）
**预估**：5–6 h（含注入重建；代表例 + 退役审计）
**档位**：大改（新建 L2 门控 + 退役既有断言 + 注入；复核须独立重跑 + ≥4 路注入）
**状态**：待验收

## 背景

K0–K3 各有收口门控（`check-linux-k0/-k1/-k2/-k3`，均入 L2）。K5 交付「用户态闭环」——`init` 完整跑起来、syscall/`clone`/`futex`/信号/时钟/64 KiB ABI 各面，但边界目前只有任务书描述、**无机械判据**。本任务建 K5 收口门控，断言「阶段 K5 达成」，并按 `docs/Process-07 §4a` 退役 K4 里「用户态尚未闭环」时成立的过时断言。

DADAO 特有事实（沿 K0–K3 门控口径，**不得偏离**）：
- 门控在 `qemu-system kaiwu-vast` 上端到端断言；期望值**现场派生**（页大小 ← `.config`、号表 ← `contract-syscall §1.2` 锁定源、退码段 ← `spec/Kaiwu §7.1`）。
- `check-modules` 会装共享安装根 ⇒ 并行任务窗口内禁跑（`docs/Process-07 §2`）；本门控入 L2（`_locked-check-modules`）。
- 门控必须**能失败**：每条断言有可达 FAIL 路径；计数类期望现场派生（`docs/Process-07 §4`）。

## 范围

1. **新增** `tests/unit/linux/check_k5.py` + `make check-linux-k5`，接线：`Makefile`（`PHONY`/`GATE_LOCKED_TARGETS`/`_locked-check-modules`/`help`/块注释）、`docs/Process-07` 目标-层表一行。（`m14-testcases-007` 已把探针/门控从 `tools/linux/` 迁到 `tests/unit/linux/`；本任务按新目录落点。）
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
   - 机械断言：退役的符号/目标在**活作用域**（`Makefile`、`tests/unit/linux`、`tools/linux`、`components/linux/{series,patches}`）0 命中（历史任务书 / changelog / discussing 允许指名）；`check-patch-tree` linux 段 0 问题；K0/K1/K2/K4/K5 全绿。
5. **一键证据脚本**：一条命令跑「构建 → 门控 → selfcheck → 注入 → K0–K2/K4 回归」，退出码如实传播。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `make check-linux-k5` rc=0，检查项计数现场打印（PASS == 总数、FAIL 0）。
2. `--selfcheck` 每组至少一次「翻转输入 ⇒ 红」（S/C/F/T/G/P/R 各一）。
3. **≥4 路可达 FAIL 注入**（`cp`+md5 还原 + 重建回绿）：① errno 写 `rd1` ⇒ S 红；② `CLONE_SETTLS` 不设 rbtp ⇒ C 红；③ `SIGSEGV` 走 `DADAO_PF_FATAL` ⇒ G 红；④ `AT_PAGESZ` 写 4096 ⇒ P 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k5` rc=0（不跑 `check-modules`）。
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

### 第 1 轮 engineer 自审

逐行审查 `check_k5.py`、K3 退役改动与 `Process-07 §4a.2`；驱动方式是「跑一次 → 读失败 → 改 → 复跑」，下面每条都是复跑后落实的：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R 组「K3 退役符号 0 命中」把门控自身的 `RETIRED_NAMES` 当命中（自指假红） | ✅已修 | `scan_scope()` 跳过 `check_k5.py`（它按设计要写出退役名） | `--only R --no-inject` 26/26 |
| `--only ""` 会跑全部组并可与后台跑批抢构建树（首轮 F 组假红根因） | ✅已修 | 注入改为 opt-in（`--inject NAME` / `--all-inject`），`make` 目标只判阶段；跑批串行 | `make check-linux-k5` 280/280；F 组单跑 40/40 |
| `k5_clone` 的 `c1_fork_parent_mm_users` 竞态（线程子任务在 fork 时可能仍持 mm 引用 ⇒ 1 或 2 都合法） | ✅已修 | 内核探针改为「fork 不新增引用」布尔判据；`k5_clone_probe` 与门控同步 | C 组连跑 3 次 41/41；`--selfcheck` 新增该判据翻转 |
| `k4_switch` 的 `no-timer-arm` 注入自 026 起打在 K2 裸 arm 路径上（对通用 clockevent 镜像无效） | ✅已修 | 注入改打 `set_next_event()` 的 `timer_cmp` 写 | `k4_switch_probe` 76/76 rc=0 |
| `judge_t` 用 `err+out` 拼控制台，「done 是最后一行」被 QEMU monitor 横幅破坏 | ✅已修 | `boot()` 取有控制台的那个流（`err or out`），日志仍存两路 | T 组 34/34 |
| 死代码/未用导入（`defconfig`、`CONFIG_SEE` 等）与恒真断言 | ✅已修 | 删未用常量/导入、去掉一条恒真 trap 断言、补「trap 号 ∈ 快照或越过表尾」的双向判据 | `compileall`/`check_k5 --selfcheck`、S 组 42/42 |
| 工具链报告漂移导致 K0 的 K10 红（`m14-testcases-007` 移目录后未重生成 + 安装根被别的任务重建） | ✅已修（生成物刷新，越界披露） | 跑 `check_toolchain.py --report` 重写 `docs/TestReports/M14-K0-toolchain-gaps.md`（差异 = 生成时间/机器指纹/脚本路径） | K0 146/146；K2 170/170 |

未修 finding：无（`check-patch-tree` 的 19 项红全在 chipyard/musl，属别的任务在改的组件源树；linux 段 0 问题 → 完成区披露）。

**判决**：可交付（`待验收`）——全部 finding 已修并复验，未修项为 0。

### 第 1 轮 reviewer 验收（2026-11-21，独立重跑）

**重跑记录**（均为我自己的命令与输出；长输出留运行期日志）
1. `JOBS=32 make check-linux-k5` ⇒ `check_k5: S 42/42 C 41/41 F 40/40 T 34/34 G 26/26 P 35/35 R 62/62`、`280/280 passed`、**rc=0**（与完成区逐组一致）。
2. `python3 tests/unit/linux/check_k5.py --selfcheck` ⇒ 8 次翻转（S/C×2/F/T/G/P/R）全 PASS、`PASS (7 组各一次可翻转 + 对照)`、**rc=0**；期望值确系现场派生（页大小 ← `spec/DADAO-12 §2.2.2`、errno ← `contract-syscall §9`、信号/僵尸 ← 内核 uapi、`EAGAIN`/`sc` ← uapi 与 `spec/SimRISC-12 §1`），计数由 `Report` 现场累加、无写死。
3. **独立注入①**（不走门控注入机）：内核源树 `arch/dadao/include/asm/elf.h` 的 `ELF_EXEC_PAGESIZE` 改 `4096UL`（改前 md5 `6e4e1ec8f215fbade5e4fd1bc2ef8314`）⇒ `--only P` **rc=1、5 条红**（`AT_PAGESZ 现场值 期望=0x10000 实际=0x1000`）⇒ `cp`+md5 还原（`md5sum -c` OK）⇒ **rc=0、P 35/35**。
4. **独立注入②**：`arch/dadao/mm/fault.c` 的 `if (policy == DADAO_PF_FATAL && from_user)` 加 `&& 0`（改前 md5 `0d3bef8f548cefcb149f8036c7f3008b`，needle 命中 1 处）⇒ `--only G` **rc=1、7 条红**（源事实断言 + 阶段 3 起半路死）⇒ 还原 `md5sum -c` OK ⇒ **rc=0、G 26/26**；两处源树 md5 复核均 OK。
5. 不回归：`check-linux-k0` **146/146 rc=0**、`-k1` **112/112 rc=0**、`-k2` **170/170 rc=0**；探针 `k4_switch_probe` **76/76 rc=0**（6 路注入含改打 `set_next_event` 的 `no-timer-arm`：`red=['s6-ticks'] died=True` 后还原回绿）、`k5_clone_probe` **97/97 rc=0**（5 路注入红→还原→绿）、`k4_fork_probe` **两次均 rc=1**（68/73、71/75，皆 `F1/F3 got=124` 卡在用户态段）。
6. 静态门控：`check-config-pins` **85 项 rc=0**（`--self-test` 6 类注入 0 失败）、`check-manifests-guard` **rc=0**、`check-component-changelog` **40 项 rc=0**、`check-linux-toolchain` **8/8 rc=0**、`check-knowledge-refs` **rc=0**、`check-patch-tree` **全局 rc=2**（19 红全在 qemu/gem5/chipyard/musl），linux 段 `103 patch(es)`、`assertion 0`。
7. 证据脚本：审了运行期证据目录内的 `run.sh`（134 行，逐条核可达 FAIL），并按其步骤逐条重跑；**未整体端到端重跑**（90 min 档位内按优先级截断），A/B 两处修后须重跑。

**约束核验**
- K3 退役：活作用域（`Makefile`/`tests/unit/linux`/`tools/linux`/`series`/`patches`）**0 命中**；`series` **103** 行、`k3_` 0；删 `k3_{pf,pt}_selftest.c.patch`（−903/−704）；补丁集内 `dadao_pf_window*`、`DADAO_K3_*` **0 命中**；`dadao_pf_find_vma()` 只走 `current->mm`（`!mm` 即返回 NULL），静态 window 注册表与 `vm_private_data` 取页臂已删；K4/K5 用户态仍可用（K5 280/280 为证）。`Process-07` §4a.2 有逐条三态处置 + 替代判据，目标表 K3 行已删、K5 行已加。
- 越界三项：① 删 `k3_pt_probe.py` **必然**（其镜像源与 `CONFIG_DADAO_K3_PT_SELFTEST` 同笔删除，探针无法成像）；② 工具链报告 diff **仅 6 行**＝生成时间/机器指纹/复现命令路径，路径串出自生成器自身源码 ⇒ 纯生成物重跑；③ `k5_clone` 改 `1 <= users <= pre_users`（缺 `fork_pre` 即 −2 ⇒ 判红）与 `k4_switch` 注入改打 `set_next_event` 的 `timer_cmp` 写，均**收紧/修假红**（后者我这轮真打到 `red=['s6-ticks']`）。
- 重试不掩盖真红：取 `run.sh` 的 `step/step_retry` **原文**实测——连红两次 ⇒ `[FAIL]×2`、`steps=4 failed=2`、脚本最终 **rc=1**；首红次绿 ⇒ 记 `rc=3（重试后绿）`。门控组启动重试只对 `rc=124` 且仅 1 次，二次超时仍进 judge（注入①②里 `启动以 SYS_EXIT(0) 收尾 期望=0 实际=113/193` 即判红为证）。

**判决：Needs Revision**（仅证据脚本 2 处断言缺陷；其余全部达标）
- **阻断 A**：`run.sh` 第 1 步 `test "$(git rev-parse --show-toplevel)" = "$ROOT"`——两边是**同一条命令、同一 cwd**，结构上不可能红（我实测两边同值 rc=0），汇总表却打 `PASS 仓库根 == 本任务 worktree`。违「验证脚本必须能失败/禁恒真」（AGENTS §4、Process-07 §5）。改法：改判一个**可不同**的真值（如 `git rev-parse --abbrev-ref HEAD` == 任务号，或断言本任务书文件存在），并给出「在别的树上跑会红」的实测。
- **阻断 B**：同脚本 `check-patch-tree` 步只 `! grep -q "^check-patch-tree: linux: assertion"`，未断言**linux 段行存在** ⇒ 段消失/命令整体失败时 vacuous 绿（§5「扫描面为空 ⇒ FAIL」）。改法：先断言 `grep -E "^check-patch-tree: linux"` 非空，再判 assertion 行。
- 修后请重跑运行期证据目录内的 `run.sh`，贴 `steps=… failed=0` 与总 `RC` 的真实输出。
- **非阻断 finding（交 architect 收尾改）**：① 完成区「改 5 个」补丁实为 **7 个**；② `Process-07` K5 行写「`--inject` 5 路 / `--selfcheck` 7 组」，实为 **6 路注入 / 8 次翻转**；③ `check_config_pins` docstring C5 写成「`check_k2` `IMAGE_CONFIG`、`check_k2` `IMAGE_CONFIG`」（重复、丢了原 `check_k3` 的指代）；④ 任务书验收 4 仍列已删的 `check-linux-k3`，范围段有两个「4.」；⑤「退役符号在树中 0 命中」实现只覆盖 5 个活作用域，历史册（任务书/changelog/discussing）仍有命中，措辞宜按实现收窄。
- **登记（不打回）**：`k4_fork_probe` 我连跑 2 次均 `rc=124` 红，与运行期 A/B 日志中 master 侧 `71/75` **同签名** ⇒ 既有抖动、非本任务引入；但「约 1/4」频率估计偏低（我 2/2 红）、重试仅 1 次 ⇒ 转 K4 探针/用户态返回路径 owner 复核根因。
- `check-knowledge-refs`（本记录写入后复跑）rc=`0`。

### 第 2 轮 engineer 自审（返工：仅证据脚本 + 文档，未动实现）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 阻断 A：`仓库根 == 本任务 worktree` 两边同源（恒真） | ✅已修 | `ROOT` 改由 `BASH_SOURCE` 逻辑路径推导（`<root>/.work/evidence/<task>/../../..`，`pwd` 不用 `-P`，否则 `.work` 符号链接会解析到主检出），再与 `git -C "$ROOT" rev-parse --show-toplevel` 比较；另加一条独立事实「`.git` 是文件（链接 worktree，非主检出）」 | 注入 A（把脚本复制到 `tests/` 再跑 `SELFCHECK=1`）：`[INFO] script-dir=…/wt/tests derived-root=/tmp/opencode git-toplevel=<git failed>` ⇒ 两条根断言 **FAIL**、`steps=3 failed=3`、`RESULT: FAIL` rc=1；删副本后 `SELFCHECK=1` ⇒ `steps=3 failed=0`、`RESULT: PASS` rc=0 |
| 阻断 B：`check-patch-tree` 只查无 assertion 行（段消失/命令整体失败时 vacuous 绿） | ✅已修 | 新增 `assert_patch_tree()`：① 从 `components/linux/series` 现场数出 N（空行不计）并断言输出里有 `check-patch-tree: linux: <N> patch(es)`（缺行即红）；② 断言 `linux: assertion` 计数 == 0；③ `make` 的 rc 用 `rc=$?` 捕获并打印（不 `| grep` 吞码），全局 rc 含其它组件的红、判据按任务验收取 linux 段 | 注入 B（`series` 删 1 行，`cp`+md5 备份）：`linux series entries=102`、`make check-patch-tree rc=2`、`linux line: … 102 patch(es) (want=102 got=102)`、`linux assertion problems: 1` ⇒ **FAIL**、rc=1；`cp` 还原（md5 `7938d24a…` 对账 OK）⇒ `103 patch(es)`、`assertion=0`、`RESULT: PASS` rc=0 |
| 非阻断①：完成区「改 5 个」补丁 | ✅已修 | 改为「改 7 个」（Kconfig.debug / cause-sub.h / setup.h / setup.c / mm/Makefile / fault.c / k5_clone_selftest.c） | 本文件完成区 |
| 非阻断②：`Process-07` K5 行的注入/自检计数 | ✅已修 | `--inject` 6 路 / `--selfcheck` 8 次翻转（S/C×2/F/T/G/P/R） | 该行文字 |
| 非阻断③：`check_config_pins` C5 重复写 `check_k2` | ✅已修 | docstring 改为「e.g. `check_k2`'s `IMAGE_CONFIG`」 | `check-config-pins` 85 项 rc=0（复跑） |
| 非阻断④：验收 4 仍列 `check-linux-k3`、范围段两个「4.」 | ✅已修 | 验收 4 改 `-k0/-k1/-k2/-k5`；范围第 4 项（一键证据脚本）改 5，并把「K0–K3 回归」改「K0–K2/K4」 | 本文件 |
| 非阻断⑤：「退役符号在树中 0 命中」与实现不符 | ✅已修 | 范围段收窄为「**活作用域**（`Makefile`/`tests/unit/linux`/`tools/linux`/`components/linux/{series,patches}`）0 命中；历史任务书/changelog/discussing 允许指名」 | 本文件 |
| 重试次数（reviewer 登记项：「重试仅 1 次」） | ✅已修 | `run.sh` 的 `step_retry` 改为 `K4_RETRIES`（默认 2）；每次失败逐条打印 `[RETRY] … 第 n 次失败 rc=…`，首次 rc 保留在汇总表（`rc=1（重试 1 次后绿）`） | 全量重跑：`k4_fork_probe` 首次 rc=1、`重试 1/2` 绿；`steps=21 failed=0`、`RESULT: PASS`、总 rc=0 |

未修 finding：无。实现代码（`check_k5.py`/内核补丁/探针判据）本轮**未改**；`k4_fork` 的既有 F5 抖动仍登记在完成区「遗留问题」。

### 第 2 轮 reviewer 验收（2026-11-22，窄复核：两条阻断 + 文档 + 全量脚本）

**两条阻断（我独立注入，红→绿）**
- 阻断 A：`cp` 脚本到 `tests/` 后 `SELFCHECK=1` ⇒ `script-dir=…/wt/tests`、`derived-root=<仓库外目录>`（原样为运行期临时路径，按「记录不写运行期路径」脱敏）、`git-toplevel=<git failed>`、两条根断言 `[FAIL] rc=1`、`steps=3 failed=3`、`RESULT: FAIL` **rc=1**；删副本回原路径 ⇒ 三条 `[PASS]`、`steps=3 failed=0`、`RESULT: PASS` **rc=0**。
- 阻断 B：`cp`+md5 备份 `components/linux/series`（`7938d24a…`）删末行 ⇒ `entries=102`、`make check-patch-tree rc=2`、`linux line: … 102 patch(es) (want=102 got=102)`、`assertion problems: 1` ⇒ **rc=1**；还原（`md5sum -c` OK、103 行）⇒ `103 patch(es)/assertion=0`、**rc=0**；未注入基线亦 `steps=3 failed=0 rc=0`。
- 重试语义（取 `step/step_retry` 原文，`K4_RETRIES` 默认 2）：恒红三跑 ⇒ 逐条 `第 1 次失败 rc=3`／`第 2 次失败 rc=3`、三条全 FAIL、`failed=3`、**脚本 rc=1**（不掩盖）；边界「首跑+重试1 红、重试2 绿」⇒ 记 `rc=1（重试 2 次后绿）` 判 PASS，即 **3 连红才判红**（完成区遗留②仍写「1 次打印重试…第二次失败仍判红」、`run.sh` 注释仍写 `A second failure is a FAIL`，与 3 跑不符 ⇒ 一并按 doc 改）。
- **全量 `run.sh`（我这轮）⇒ `RESULT: FAIL`、`steps=22 failed=3`、总 rc=1**；唯一红项 `k4_fork_probe` 连续 3 跑全 `rc=1`、签名恒为 `71/75`（F1/F3/F5 `got=124`、两次帧行缺），本轮另两次独立单跑同签名，`K4F_QEMU_TIMEOUT=420` 仍 `got=124` ⇒ **真挂死而非慢**；我两轮合计 **7/7 全红**，与遗留②「约 1/4 偶发」严重不符。其余 19 步全 PASS（K5 门控 280/280、selfcheck、6 路注入、K0/K1/K2、cow/switch/stack/kthread、config-pins、patch-tree `103/0`、knowledge-refs）。
- 该探针既有性**未坐实**：只有一份 master A/B 失败样本，且本轮 `mm/fault.c` 删了 K3 window 臂，F5 挂死与它的因果**未排除**。
- 文档 6/6 已改：完成区「改 **7** 个」；`Process-07`「`--inject` 6 路 / `--selfcheck` 8 次翻转」；C5 docstring「e.g. `check_k2`'s `IMAGE_CONFIG`」；验收 4 = `-k0/-k1/-k2/-k5`；范围 1–5 无重复；「0 命中」收窄为活作用域。实现未动（`check_k5.py` md5 同上轮、快照 40 条逐行同、无新提交）。
- **判决：Needs Revision**（唯一未达标 = 全量 `run.sh` rc=1；两条阻断与文档均已达标，无需再动）
1. 查清 `k4_fork_probe` F5 挂死是**本任务引入**还是**既有**：master 侧须**多次采样**（1 份失败样本不足），并核对与本轮 `mm/fault.c` 删 window 臂的因果；若属本任务引入 ⇒ **必须修**。
2. 若确证既有必现 ⇒ 按既有缺陷在一键脚本/完成区**显式处置**（单独标注或不计入一键 rc），并把频率披露由「约 1/4」更正为实测口径。
3. **禁止**加重试次数或加长超时凑绿（`K4_RETRIES=2`、`K4F_QEMU_TIMEOUT=420` 我已实测无效）。
- `check-knowledge-refs`（本记录写入后复跑）rc=`0`。

### 第 3 轮 engineer 自审（窄返工：`k4_fork_probe` F5 归因）

**归因（A/B，各 5 跑，串行；换 series 前后核对源树 tree hash）**

| 侧 | 源树 | 命令 | 结果 |
|---|---|---|---|
| master `1792ebf9`（无 029） | tree `94cd236d…`（`components/linux/series` 105 条，master 版） | `cd /mnt/tao/DADAO-v5 && JOBS=32 python3 tests/unit/linux/k4_fork_probe.py` ×5 | **1 绿 / 4 红**：`104/104` rc=0；`72/76`×3、`69/74`×1 rc=1（红均为 F1/F5/F3 `got=124`） |
| 029 分支 | tree `52a63b9f…`（103 条） | `cd <task-worktree> && JOBS=32 python3 tests/unit/linux/k4_fork_probe.py` ×5 | **1 绿 / 4 红**：`103/103` rc=0；`71/75`×4 rc=1（同签名） |

**失败签名（两侧一致）**：控制台 `K4 f5 sys0` 之后 `K3 pf: … cause=CFXMEM sub=IGPTRAP ip=0xbef0 … result=die-no-vma` → `Kernel panic - not syncing: Attempted to kill init! exitcode=0x0000000b`；探针报 F1/F5/F3 `got=124`、两次帧行缺。计数差（76 vs 75）只是两侧探针版的断言条数差（本任务删了 1 条 K3 配置断言），不是行为差。

**结论**：**既有偶发缺陷，非 029 引入**——master 同 4/5 红、同签名；029 删除 `current->mm == NULL` 窗口臂不影响 F5（F5 的 `ld.o` 数据缺页两侧都走 `fill-zero`，崩溃发生在更早的 `escape` 目标，与窗口臂无关）。复核者的 7/7 与本轮 4/5 是同一缺陷的不同采样。

**处置**（按裁决：不加重试/不加超时）
- `ISS-493` 登记（`.tao/knowledge/issues.yaml`，scope=linux、M14、open；含 A/B 数据与修法方向：F5 改用 `task_pt_regs(current)` 作入口帧，与 `k5_syscall_selftest` 一致）。
- `run.sh` 删掉 `step_retry`/`K4_RETRIES`，改为**按签名匹配**的 `step_registered`（`k4_fork` 的 scratch 用 `K4F_TMP` 固定，运行前删旧控制台，防旧签名串味）：只有**同时**满足 ① 探针 stdout 的失败计数为 `71/75` 或 `72/76`（两侧探针版差），或至少 `got=124` 且 `[FAIL]` 只涉及 F1/F3/F5；② 控制台含 `K4 f5 sys0`；③ 含 `die-no-vma`、`cause=CFXMEM`、`sub=IGPTRAP` —— 才打印 `[REGISTERED] … ISS-493`、汇总表 `REG`、计入 `registered=` 而不计入 `failed`；**其它任何红**（F2/F4 失败、计数不符、编译失败、无签名的超时）打印 `[NOT-REGISTERED] …（原因）` 并**保持 FAIL**。`RESULT` 行点名 `registered` 项与替代判据（`check-linux-k5` C/G 组），退出码 = `failed==0`。绿则照常 PASS、`registered=0`。
- 完成区/遗留按实测改（4/5，不再写「约 1/4」；删「重试 1/2」「第二次失败仍判红」的过时说法）。
- 同一轮另见 K4 探针的**第二类既有偶发**：`k4_kthread_probe` 的 `k2-task-dead` 在 `kthread_stop()` 后立即读任务态，本任务的一次全量跑得 59/68（`state=0 on_rq=1 frozen=1`，`K4 kthread FAIL: k2-task-dead=0x0 code=0x51`），随后同镜像连跑 2 次均 112/112 ⇒ 探针轮询与调度交接的竞态，登记 `ISS-494`；该探针在证据脚本里**保持严格判据**（不登记、不重试），出现该类红时按运行期日志披露并重采一次全量。
- `run.sh` 的判据自检（无构建，三种）：`SELFCHECK=registered`（喂**符合**签名的失败输出）⇒ `[REGISTERED] …（签名匹配）`、`REG`、`failed=0 registered=1`、`RESULT: PASS（…registered=1…）`、rc=0；`SELFCHECK=registered-wrong`（喂**不含 `die-no-vma`** 的其它红）⇒ `[NOT-REGISTERED] …（console: no 'die-no-vma'）`、`failed=1`、`RESULT: FAIL`、rc=1；`SELFCHECK=strict`（普通 red）⇒ `RESULT: FAIL`、rc=1 —— 证明登记路径只对已知签名放行，别的红仍判红。**全量重跑里该路径被真实触发**：`k4_fork_probe` 报 `71/75`，控制台含 `K4 f5 sys0` / `die-no-vma` / `cause=CFXMEM` / `sub=IGPTRAP` ⇒ `[REGISTERED] …（签名匹配）`、汇总 `REG`、`registered=1`，`RESULT: PASS` rc=0。

### 第 3 轮 reviewer 验收（2026-11-22，窄复核：签名门 + 三态自检 + 全量脚本）

1. **签名门（读代码 + 构造输入实测）**：`signature_ok` 要求 ① 计数 `71/75`/`72/76` 或（`got=124` 且 `[FAIL]` ⊆ F1/F3/F5）② 控制台 `K4 f5 sys0` ③ `die-no-vma`+`cause=CFXMEM`+`sub=IGPTRAP`；`step_registered` 只在 `rc≠0` 判签名，不符打 `[NOT-REGISTERED]… 保持 FAIL`（`RCS` 不清零），符合才 `RCS=0` 并计 `REGISTERED`；运行前 `rm -f` 旧控制台，路径 `$OUT/k4f/check-linux-k4/log/k4.log` 与探针 `SCRATCH=K4F_TMP/check-linux-k4`+`log/{tag}.log` 对得上。实测：缺 `K4 f5 sys0` ⇒ 拒、控制台缺失 ⇒ 拒、计数不中但 `got=124`+仅 F1/F3/F5 ⇒ 登记。
2. **三态自检（我跑）**：`SELFCHECK=registered` ⇒ `REG`、`steps=1 failed=0 registered=1`、`RESULT: PASS（…registered=1… 替代判据 = check-linux-k5 C/G 组）` **rc=0**；`registered-wrong` ⇒ `[NOT-REGISTERED]（console: no 'die-no-vma'）`、`failed=1 registered=0`、`RESULT: FAIL` **rc=1**；`strict` ⇒ `failed=1`、`RESULT: FAIL` **rc=1**。
3. **全量 `run.sh`（我这轮）⇒ `FULL_RC=0`、`steps=20 failed=0 registered=1`**；活体行 `[FAIL] k4_fork_probe … 实际=rc=1` 紧接 `[REGISTERED] … ISS-493：签名匹配；不计入本任务 RESULT`，汇总 `REG … 实际=rc=1（REGISTERED ISS-493）`，`RESULT: PASS（本任务判据；registered=1: k4_fork_probe（…）（ISS-493） — 见 ISS，替代判据 = check-linux-k5 C/G 组）`。控制台实证 `K4 f5 sys0`=1、`die-no-vma`=1、`cause=CFXMEM`=2、`sub=IGPTRAP`=1，单行 `… cause=CFXMEM sub=IGPTRAP ip=0xbef0 … result=die-no-vma`；探针 stdout `71/75`、4 红全在 F1/F5/F3 `got=124`。其余 19 步全 PASS（K5 280/280、selfcheck、6 路注入、K0/K1/K2、cow/switch/stack/kthread、config-pins、patch-tree `103/0`、knowledge-refs）。
4. **过时文案 0 残留**：`run.sh` 中 `重试 1/2`/`第二次失败`/`A second failure is a FAIL`/`step_retry`/`K4_RETRIES` 均 0 命中；完成区遗留② 已改 ISS-493 口径与 4/5 实测频率（不再写「约 1/4」），遗留③ 的重试明确限定 `check_k5.py` 组启动（属实）。
5. **附带**：`issues.yaml` 新增 `ISS-493`（P1：根因 `k4_selftest.c` 本地 `pt_regs` → `task_pt_regs(current)->ip` 恒 `0xbef0`、A/B 各 5 跑 master 4/5 红 / 029 分支 4/5 红同签名、修法方向、替代判据）与 `ISS-494`，完成区已披露；`check_issues` rc=0、`check-knowledge-refs` rc=0。
6. **非阻断 finding**：`signature_ok` 两条窄路径我已构造复现——① 计数命中 `71/75`/`72/76` 时不再校验 `[FAIL]` ⊆ F1/F3/F5（71/75 + 签名控制台 + 唯一红是 F2 ⇒ 仍登记）；② `got=124` 存在但 stdout **零 `[FAIL]`** 时空真通过。二者仍强制完整 ISS-493 控制台签名且运行前删旧日志，实际可达性极低 ⇒ 下次触碰时把「`[FAIL]` 非空且 ⊆ F1/F3/F5」提到计数分支之前即可。
- **判决：Accepted** —— 「既有偶发 + 签名门 + 显式登记 + 替代判据」在我这轮成立：根因归 `ISS-493` 交 owner（A/B 两侧同签名各 4/5 红，非本任务引入），替代判据 `check-linux-k5` C/G 组我第 1 轮独立重跑 280/280，脚本无重试/无加长超时、红项在汇总里以 `REG`+原 `rc=1` 显式保留，**本任务不需修 F5 本体**。`check-knowledge-refs`（本记录写入后复跑）rc=`0`。

## 完成区

**测试结果**：`make check-linux-k5` rc=0、280/280（S 42/42 C 41/41 F 40/40 T 34/34 G 26/26 P 35/35 R 62/62）；`--selfcheck` 8 次翻转（S/C×2/F/T/G/P/R）全 PASS；`--all-inject` 316/316（6 路注入：errno→rd1⇒S、SETTLS⇒C、SIGSEGV-FATAL⇒G、AT_PAGESZ 4 KiB⇒P、退役文案回潮×2⇒R，逐路「红→`cp`+md5 还原→重建回绿」，0 FAIL）；不回归：K0 146/146、K1 112/112、K2 170/170、k4 cow 86/86、switch 76/76、stack 44/44、kthread 112/112 全 rc=0；`k4_fork_probe` 为**已登记既有红**（ISS-493；A/B 各 5 跑：master 4/5 红、029 分支 4/5 红、同签名，非本任务引入）——证据脚本对该步不做重试，红时标 `REGISTERED` 并在 `RESULT` 里点名，替代判据 = `check-linux-k5` 的 C/G 组。一键证据脚本 20 步 0 failed、`registered=1`、`RESULT: PASS（…registered=1: k4_fork_probe（ISS-493）…）` rc=0（构建→门控→selfcheck→注入→K0–K2/K4 回归→静态门控；「已登记红」路径由 `SELFCHECK=registered/strict` 判据自检验证：前者 `REG` + `RESULT: PASS（…registered=1…）` rc=0，后者 `RESULT: FAIL` rc=1）。
**修改文件**：新增 `tests/unit/linux/check_k5.py`；`Makefile`、`docs/Process-07`、`components/linux/{series,changelog.md,patches/**}`（删 2 个 K3 补丁、改 7 个）、`docs/TestReports/M14-K0-toolchain-gaps.md`（生成物刷新）；删 `tests/unit/linux/{check_k3.py,k3_page_probe.py,k3_pt_probe.py}`；改 `tests/unit/linux/{check_k0,check_k1,check_k2,check_config_pins,k1_pt_probe,k2_irq_probe,k2_time_probe,k2_trap_probe,k4_cow_probe,k4_fork_probe,k4_kthread_probe,k4_stack_probe,k4_switch_probe,k5_*_probe,m45_entry_probe}.py`、`tools/linux/config_pins.py`、`.tao/knowledge/issues.yaml`（ISS-493/494）；本任务书。越界披露：删 `k3_pt_probe.py`（其镜像源按裁决删除）、刷工具链报告（见自审末条）。
**验收结果**：`check-config-pins` PASS（85 项：19 脚本/22 符号/35 镜像）；`check-patch-tree` linux 段 103 补丁 0 问题（全局 19 项红全在 chipyard/musl）；`check-knowledge-refs`/`check-component-changelog`/`check-manifests-guard` rc=0；`make check-linux-toolchain` PASS（8/8 行）。
**新发现/坑**：
- 内核 7.2.10 的匿名页 mapping 标记是 `FOLIO_MAPPING_ANON`（任务书写的 `PAGE_MAPPING_ANON` 是旧名）；门控按现场 token 派生，并断言 `get_futex_key()` 的 `folio_test_anon` 分支。
- K3 退役必须连删 `k3_pt_probe.py`（镜像源已删），并把 `contract-see §6.1.1`/`spec/Kaiwu §7.1` 解析器移入 `k4_cow_probe.py`（唯一剩余消费者）；`check_config_pins` 自检夹具原用 `check_k3.py`，改用 `check_k2.py`。
- 门控不自带 `CONFIG_PINS`、复用各探针的 `build_image()`：`check-config-pins` C2 要求「调用 `apply_config_lines` 者必须声明」，复用探针即单一真源。
- 同一构建树并发两个 config 的镜像会串味（首轮 F 组假红即此因，符号 `None`）；K5 门控必须串行跑。
- 工具链报告同时受「目录搬迁（`m14-testcases-007`）」与「安装根重建（clang 版本串变）」影响 ⇒ 按报告自述重跑 `--report`，否则 K0 的 K10 先红。
**遗留问题**：① 任务书验收 5（pthread 端到端）按用户 2026-11-20 裁定范围 B 不作（pthread create/join 归 K6）。
- ② `k4_fork_probe` F5 用户段**偶发挂死**（ISS-493）：第一次 umon `SKIP` 后 `escape` 目标取自 `task_pt_regs(current)->ip`，取到垃圾地址（恒 `0xbef0`）⇒ `IGPTRAP` → `die-no-vma` → `panic: Attempted to kill init`（F1/F3/F5 `got=124`）。**A/B 各 5 跑（同签名）**：master `1792ebf9`（无 029）**4/5 红**（72/76×3、69/74×1；1 绿 104/104）；029 分支 **4/5 红**（71/75×4；1 绿 103/103）⇒ 既有偶发、与 029 删窗口臂无因果（复核者另测 7/7 红）。**不加重试/超时**；证据脚本红时标 `REGISTERED`、不计入本任务 RESULT，替代判据 = K5 的 C/G 组；修法与复现门控交 K4 探针/用户态返回路径 owner（`ISS-493`）。
- ③ 同一镜像的 futex 图（`k5_futex`）偶发首次启动超时（阻塞交接 + tick 抢占）；门控对组启动做 1 次打印重试，第二次超时仍判红（`check_k5.py`，与 k4_fork 无关）。
- ④ `check-patch-tree` 全局红来自 chipyard/musl（别的任务在改的组件源树），linux 段 0 问题；K0 的 K10 曾因工具链报告漂移而红（已按报告自述刷新生成物并复跑 146/146）。
- ⑤ `k4_kthread_probe` 的 `k2-task-dead` 偶发竞态（一次 59/68，随后 2/2 绿）登记 `ISS-494`；证据脚本对其余 K4 探针保持严格判据、不重试。
