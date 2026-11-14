# m14-linux-005: K1 收口门控 `check-linux-k1`（Vast 端到端）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-003`、`m14-linux-004`
**可并行分片**：否
**预估**：2–3 h
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「smon的时候应该就开启了PTBR，能进入start_kernel，开启时钟之前打印信息退出，我觉得K1就算完成」

⇒ K1 的判据 = **Vast 上跑完 `power → hmon → smon → 内核 → start_kernel → （自建表/写 PTBR）→ 打印 → 开时钟前 `SYS_EXIT(0)`**，不作为 K1 判据的部分（init/syscall/中断）不纳入。

## 背景

K0 已有 `make check-linux-k0`（119 项、10 路注入、入 L2，`m14-infra-003`）。K1 需要同规格的收口门控，否则 K0/K1 的边界无法机械判定。

## 范围

1. 新增 `tools/linux/check_k1.py` + `make check-linux-k1`，纳入 **L2**（`_locked-check-modules`），`docs/Process-07` 组合表与 `Makefile` help 同步；
2. 检查项（现场派生，不写死计数）：
   - **端到端**：`bootrom-image`（Vast 固定固件）+ `-kernel <vmlinux>` → guest `rc=0`；
   - **阶段顺序**：`power` → `hmon` → `smon` → 内核入口 → `start_kernel` 标记 → 退出，**顺序正确且各出现 1 次**（用 semihosting 输出/探针记录，不用 `-d` 逐指令日志）；
   - **boot info**：15 字段里至少 `magic/version/size/kernel_base/entry/hart_id` 与构建参数一致；
   - **PTBR**：打印并校验「内核自建表」生效（PTBR 值与 PTE 索引 4096），且切换后仍有输出；
   - **退出点**：`SYS_EXIT(0)` 出现在**任何时钟/中断开启之前**（以输出顺序或探针记录判定）；
   - **反向断言**：不得出现 `panic/CFXMEM` 等异常路径痕迹（若出现 ⇒ FAIL 并列出）。
3. **可达 FAIL 注入 ≥4 路**（`cp`+md5 还原）：① 破坏 boot info magic；② 把 PTBR 指向未映射基址；③ 把退出码改成 1；④ 删 `start_kernel` 标记 ⇒ 各自命中对应断言；
4. 与 `check-linux-k0` 不重复：K0 查"能否交接"，K1 查"内核跑起来并退出"。

## 验收（逐条贴真实 rc）

1. `make check-linux-k1` **rc=0**；检查项计数现场打印；
2. 4 路注入逐条「注入→红→还原→绿」，还原后 md5 与注入前一致；
3. `make check-linux-k0` 仍 rc=0（K0 不回归）；`make check-modules` **不跑**（共享安装根）——按模块单独跑 `check-linux-k1`；
4. `docs/Process-07` 的 L2 组成表含新目标；`Makefile` help 有对应行；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；禁 `install-host`/`check-modules`；`build-linux` 用 `JOBS=32`；禁边构建边测试。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tools/linux/**`、`Makefile`（目标 + L2 接线）、`docs/Process-07`、任务书；**不改** `spec/`、`contracts/`、`components/**`。
5. 只在 `qemu-system vast` 上验收；Vast 固件/镜像用共享产物，不重建 QEMU。

## 追加范围（`m14-linux-004` 复核 finding，2026-11-15）

复核 Accepted，但留了两条**必须在本任务内闭合**的 finding（不阻断 004 合入，但属于 K1 收口的一部分）：

1. **F1（真缺陷，需改代码）**：`components/linux/.../arch/dadao/include/asm/ptw.h` 的 `dadao_tlb_invalidate_all()` 写 `0x2`，注释称「drop every entry」，但按 `spec/DADAO-12 §4.5`：
   - `[1:0]=10` invalid、`[3:2]=00` all、`bit4=ASID_ANY`；
   - **`ASID_ANY=0` 只处理 `G=0` 且 ASID 匹配的条目、不碰 `G` 条目**；`ASID_ANY=1` 才包含 `G=1`。
   - 内核 `_PAGE_KERNEL` 含 `G=1` ⇒ 写 `0x2` **不会失效内核映射**，与注释矛盾。K1 实测无害（切换前只可能缓存 index 4096 且新旧同映射），但接口语义是错的。
   - **处置（二选一，必须给 spec 依据）**：① 写值改 `0x12`（invalid + all + ASID_ANY），注释保持「drop every entry」；② 保留 `0x2` 但把注释/函数名收窄为「drop non-global entries of the current ASID」。
   - 无论选哪个，都要用 `m14-linux-004` 的探针复跑证明**切换后仍能执行**（`post ptbr` / `done` / `start_kernel` 俱在），并在完成区贴 spec 原文依据。
2. **F2（文档数字）**：`components/linux/changelog.md` 的 004 条目、探针 `run.sh` 注释、probe docstring 三处写「三路注入」，实为 **4 路**（完成区 `4/4` 是对的）⇒ 改为 4 路。

**范围扩展**：本任务因此允许改 `components/linux/**`（仅上述 ptw.h 一处 + changelog 一条）与 `tools/linux/k1_pt_probe.py` 的注释/docstring；改后须 `make_patch.py linux` 重导出、`check-patch-tree` **linux 段 0 问题**、`--source-state` linux OK、`check-component-changelog` rc=0。

**附加验收**：`m14-linux-004` 的一键证据脚本在改后仍 **58/58 PASS rc=0**（含 `--selfcheck` 15/15、`--inject` 4 路），否则说明 F1 的改动破坏了 K1。

## 待裁定

无（实现中未产生需用户裁定的问题）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 注入中途异常/重建失败会留下「注入版内核」，后续步骤可能对脏构建树判定 | ✅已修 | `run_inject` 改 try/except→finally 还原 + **无条件还原后重建**，再判回绿 | 4 路注入各「还原 md5 == 注入前 + 还原后回绿」，证据脚本末段 ptw.h md5 前后一致 |
| `Ctx` 有 4 个字段（RAM 基址/大小/页大小/boot info VA）派生后未使用 = 孤儿 | ✅已修 | 新增检查：表覆盖的 RAM 基址/大小/超页数/L1 区间、`page_size_log2 == log2(页大小)`、两处 VA→PA | `make check-linux-k1` 由 95 → **102** 项全绿 |
| `run_kernel` 的 `if "-d" in cmd` 是恒假死代码 | ✅已修 | 删掉死分支；「无 `-d`」由 K5 的两条断言承担（命令行 + 输出无转储标记） | selfcheck 里 K5 由 rc 注入翻转；正常跑 K5 两条 PASS |
| 初版 power 窗口切片偏移表达式写错（重复减基址） | ✅已修 | 改 `reset_offset = reset_pc − bootrom_base` 后切 64 KiB | K3「power 窗口非空」+「复位向量落点」均 PASS |
| 误以为 profile 的 `hmon`/`smon` 是地址字典（实为布尔） | ✅已修 | 改用 `spec/Machine-v5 §1.1` 的两个 SRAM 窗口常量（加注释与引文） | K4 四条 PASS；selfcheck K4 用移植 BootROM 副本翻转成功 |
| 证据脚本用 `grep -P` 负向前瞻（不可移植）+ `.bak` 检查写法绕 | ✅已修 | 删除前瞻行；`.bak` 改为在 scratch 下 `find` 计数 | 脚本 `bash -n` 通过并 9/9 步全 PASS rc=0 |
| F2 数字修完后仍有第 4 处「三路」（probe 段注释行） | ✅已修 | 三处 + 段注释 + 004 证据脚本注释一并改 4 路 | `grep -n "three\|三路"` 无命中 |

### 第 1 轮 reviewer 验收（2026-11-15，独立重跑）

**重跑（全部本人执行、rc 实测）**：① `make check-linux-k1` → `PASS (102/102)` rc=0（`[PASS]` 102 / `[FAIL]` 0，qemu md5=725c5da7）；② 本任务证据脚本 `run.sh` → rc=0（102/102、`--selfcheck` 12/12、`--inject` 4/4 还原+回绿、`make check-linux-k0` PASS、`check-patch-tree` linux 0 问题/61 patch 且整树 10 红全在 gem5、`--source-state` linux OK、`check-component-changelog` PASS、004 探针 58/58 + selfcheck 15/15）；③ 004 证据脚本（`REPO_ROOT` 指本 worktree）→ rc=0：build + 58 项 + selfcheck 15 组 + **inject 4 路（pte-sp/ptbr-ppn/ptbr-live/no-expect，md5 `6dc6895b` 还原并回绿）** + k0 PASS；④ `make help` 有 `check-linux-k1` 行，`_locked-check-modules` 与 `GATE_LOCKED_TARGETS`/PHONY 均含之，`docs/Process-07` L2 表 1 行；未跑 `check-modules`/`install-host`。

**我自设计的注入（`cp`+md5，独立于其 4 路）**：① BootROM 构建器 MAGIC `…54→…55` ⇒ 红，`K3 index-table magic 期望=0x44424f54 实际=0x44424f55`（机器同时拒启，粗红）；② 内核 `setup.c` 重复 `start_kernel` 行 ⇒ **100/102，仅 2 FAIL**（`K11 阶段 start_kernel 期望=1 实际=2`、`K11 行 marker`）；③ 内核 `k1_pt.c` 索引区间改打 `first+pages` ⇒ **101/102，仅 1 FAIL**（`K9 期望=['4096','4099'] 实际=['4096','4100']`，证明期望侧现场派生、非抄输出）；④ machine profile `bootrom_size +0x10000` ⇒ K3 复位向量红（连带镜像变 0x410000 被 QEMU 拒，非隔离，弃用）。**证据脚本本身可红**：注入②后重跑同一 `run.sh` ⇒ **rc=1、11 项 FAIL**（含 `K 项检查失败数 期望=0 实际=2`、source-state FAIL），还原后重跑 rc=0。全部还原后 `git status -uall` 0 行、7 个声明文件 md5 与审前快照逐一相等、HEAD 仍 `b58ed761`（reviewer 未提交）。

**期望值独立复算（本人算、不读脚本）**：ELF `max(vaddr+memsz)−e_entry` = `0x4bb5f9` == K6 `kernel_size`；`llvm-nm` `swapper_pg_dir 0x20000570000` ⇒ `0x570000` == K9 PTBR，`start_kernel 0x20000110348` / next `0x200001105e8` == K12 ra 界；`0x80000000/0x20000000` ⇒ 4 超页、索引 `4096..4099`；`kernel_start>>29`=4096；`log2(0x10000)`=16。无写死总项数（grep：仅 PTE 数 `2`、SPF `0xff` 与 spec 常量），计数类期望均为 `1`。

**F1 判定**：`ptw.h` 实写 `0x12`、注释引 `§4.5`；spec 原文（`DADAO-12` 寄存器表 + §4.5）`[1:0]=10 invalid`、`[3:2]=00 all`、`bit4=ASID_ANY`，且「`ASID_ANY=0` 只处理 `G=0` 且 ASID 匹配的条目，不碰 `G` 条目」；`_PAGE_KERNEL` 含 `_PAGE_GLOBAL` ⇒ **`0x12` 正确、`0x2` 确为缺陷**；改后 004 探针复跑 58/58，`post ptbr`/`done`/`start_kernel` 俱在。

**阶段顺序证据（判定：够用但非直接观测，不阻断）**：内核段 8 锚点严格递增 + 17 类一次性行是真观测；power/hmon/smon 无打印，改用「镜像索引表（各 1 条、hmon<smon）+ 各阶段唯一产物（boot info 15 字段 / `ptw_enable`+传入 PTBR+1 超页+rb16/17）」⇒ 能证三阶段**都跑过**、不能直接观测**三阶段相对顺序**（完成区已披露）。补强方案 = 固件三阶段各打一行 semihosting 标记，需改共享 BootROM 固件、超出本任务硬约束 4 的可改范围 ⇒ 建议另立任务，由 architect 定夺。

**反向断言严密度**：`CFXMEM` 恰 1 次且须匹配 `probed … (resumed)`；未声明/二次 CFXMEM 走 `K1 ptw fault: …`，被 `^K1 ptw fault: ` 抓住（004 `no-expect` 注入实测打印该行）⇒ 非 flaky 包裹；panic/具名 fault/拒绝行/POST_K1 四组只可能误报不会漏报，绿跑零误报。

**Findings（均不阻断，交 architect）**：F-a 完成区/自审「`grep three|三路` 无命中」缺范围——全 `components/+tools/` 仍命中 llvm changelog「三路径」与 k1_trap.S.patch 英文 `three data`（`components/linux`+`tools/linux` 内 0 命中，F2 实质已闭合）；F-b `K9 SPF` 期望写死 `0xff`、K3 magic/窗口/SRAM 为脚本内 spec 常量 ⇒ `docs/Process-07`「期望值全部现场派生」略过头，建议 SPF 由 `superpage_size` 推导；F-c `--selfcheck` 12 组不含 K1 构建组（其 FAIL 路径 build rc≠0 未演示）。

**判决：Accepted**（验收命令块本人重跑全绿、硬约束逐条守住、其 4 路注入与证据脚本均经我独立反例翻转）

## 完成区

**测试结果**：`make check-linux-k1` **102/102 PASS rc=0**（计数现场打印）；`--selfcheck` 12/12 组可翻转；`--inject` 4/4 路；`make check-linux-k0` rc=0；004 探针 58/58 + `--selfcheck` 15/15。
**修改文件**：`tools/linux/check_k1.py`（新增）；`tools/linux/k1_pt_probe.py`（F2 注释/docstring）；`Makefile`（PHONY/help/`_locked-`/`GATE_LOCKED_TARGETS`/L2 列表+注释）；`docs/Process-07-门控分层规范.md`（目标-层表新增一行）；`components/linux/patches/arch/dadao/include/asm/ptw.h.patch`（F1）；`components/linux/changelog.md`（004 数字 + 005 条目）；本任务书；运行期证据脚本（非跟踪）。
**验收结果**：
- `make check-linux-k1` → `check-linux-k1: PASS (102/102)` rc=0；K 项 PASS 数 == 总项数、失败 0。
- 4 路注入逐条「注入→红→还原→绿」：`bootinfo-magic` rc=0xe1（K5/K11/K13 红，具名 `K1 bootinfo invalid: magic code=0xe1`）；`ptbr-unmapped` rc=1（K9/K11 红，具名 `dadao: page-table access outside physical memory`）；`exit-code` rc=1（K5 红）；`no-start-marker` rc=0（K11 红）。每路还原后源码 md5 == 注入前，且还原后重建回绿（`cp`+md5，未用 checkout/restore/stash）。
- `make check-linux-k0` → PASS rc=0（K0 不回归）。
- `check-patch-tree`：linux 段 **0 问题**（61 patch）；整树 10 项红全在 gem5 段（`m16-gem5-005` 在途，非本任务）。
- `check-patch-tree --source-state`：linux **OK**（clean=True，base+1）；`check-component-changelog` rc=0。
- F1：`dadao_tlb_invalidate_all()` 写值 `0x2` → **`0x12`**，保持「drop every entry」注释并写明依据。spec 原文（`spec/DADAO-12 §4.5`）：「`ASID_ANY = 1` 时包含 `G = 1` 的条目；`ASID_ANY = 0` 时只处理 `G = 0` 且 ASID 匹配的条目，**不碰 `G` 条目**」；`_PAGE_KERNEL` 含 `G=1` ⇒ 旧值不失效内核映射、与注释矛盾。改后 004 探针复跑 **58/58**、`--selfcheck` 15/15、`--inject` 4 路，输出中 `post ptbr` / `done` / `start_kernel` 俱在。
- F2：004 changelog 条目、probe docstring（2 处）、probe 注入段注释、004 证据脚本注释 —— 全部「三路」→「4 路」；`grep "three\|三路"` 无命中。
**新发现/坑**：① 共享固件的 power/hmon/smon **不打印**，且本任务禁 `-d` ⇒ 三阶段顺序无法用日志行判定；门控改判「镜像配置 + 移交态」（power=复位向量落点且窗口有代码；hmon=索引表 type1 + boot info 15 字段唯一写者；smon=`ptw_enable`/传入 PTBR/预建表仅 1 超页/`rb16`+`rb17` 移交值）。要更硬的顺序证据需固件打 semihosting 标记（改共享固件，另立任务）。② machine profile 缺 hmon/smon 的 SRAM 窗口（只有布尔）⇒ K4 用 `spec/Machine-v5 §1.1` 常量；建议后续给 profile 加字段。③ 安装根 qemu（`725c5da7`）的 PTW/TLB 语义齐备，Vast K1 无需重建。
**遗留问题**：无。整树 `check-patch-tree` 的 10 项红全在 gem5 段（并行任务在途），不计入本任务。
