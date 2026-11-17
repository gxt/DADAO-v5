# m14-qemu-007: semihosting 字符串路径统一按 PA（`SYS_WRITE0`/字符串类）

**模块**：qemu
**项目里程碑**：M14
**依赖**：`m14-qemu-002`（已验证：semihosting 指针按 PA）、`m14-qemu-004`（已验证：`SYS_READC`/`SYS_FLEN` 缓冲改 PA）
**可并行分片**：否（`components/qemu` 单树写者）
**预估**：1.5–2 h
**档位**：中改（单点语义 + 门控断言；复核 ≥2 路注入）
**状态**：待验收

## 背景（`ISS-450`，用户 2026-11-15 已裁定原则）

- **用户裁定**：「semihosting 参数指针 = **PA**」，已写进 `spec/Kaiwu §5.2` 与 `.tao/contracts/contract-semihosting.md §2`（要求**不经页表翻译**）；
- **QEMU 现状**：`SYS_WRITEC`/`SYS_EXIT` 走 `translate_for_debug`（identity，仅 `[0,2GiB)` ∪ ROM ∪ SRAM），但 **`SYS_WRITE0` 先 `target_strlen` 再 `probe_access_flags`**，**走页表** ⇒ 开 PTW 后两窗口不相交，`SYS_WRITE0` 无法按 PA 正确取串；
- 另：`translate_for_debug` 的注释仍写「DADAO has no MMU」，在 Vast + PTW 下已过时。


## 前提订正（主会话失误，2026-11-17）

本任务书的「背景」依据 `ISS-450` 的**旧描述**（`SYS_WRITE0` 走页表），但该问题**已被 `m14-qemu-002` 修掉**（`common_semi_strlen()` 钩子 + `dadao` 强定义按 PA 逐块读），`translate_for_debug` 的「no MMU」注释亦彼时订正。**立册前未核现状，属主会话失误。**

本任务实际交付（仍有价值，非重复实现）：

- **补 K14 的覆盖面缺口**：新增 640 B 长串（跨 3 个 256 B 块、起点在块内 48 B 处）的 `SYS_WRITE0` 断言 ⇒ 能把"只读首块"或"窗口上界截断"这类错误判红（3 路注入已证独立判别力）；
- **收掉最后一处过时注释**（`dadao_cpu_mmu_index()` 的 `M1: no MMU, single index`）；
- 判据：`check-linux-k1` 111→**112/112**、K14 由 3 条扩到 **7** 条。

## 目标

1. **字符串类取参统一按 PA**：`SYS_WRITE0`（及同类字符串获取路径）**不经页表翻译**；复用 `m14-qemu-004` 已建立的 PA 口径（`dadao_cpu_va_to_pa` / identity 窗口判定之一，**优先复用**，不另造第二套换算）；
2. **注释订正**：`translate_for_debug` 的「no MMU」表述改为与 Vast+PTW 一致的口径；
3. **门控**：新增一条「**Vast + `ptw_enable=1` 下 `SYS_WRITE0` 取串成功**」的断言（放进现有 K 门控或 semihosting smoke，按最小改动选）；
4. 其它 syscall 语义不动，越界须披露。

## 验收（真实 rc + 输出）

1. **先红后绿**：开 PTW 的 Vast 镜像里 `SYS_WRITE0` 断点 —— 改前取串失败/错串（贴输出），改后正确打印同长度、同内容；
2. `check-linux-k0` 119/119、`check-linux-k1` 111/111、`check-linux-k2` 104/104、`check-inst-asm` 904/904、`check-arch`（14 探针）、`check-qemu-forms`/`check-interface`/`check-component-changelog`；
3. **≥2 路自设计注入**（`cp`+md5 还原 + 重建）：① 把字符串路径改回走页表 ⇒ 红；② identity 窗口上界改小 ⇒ 长串截断/失败 ⇒ 红；
4. 补丁纪律：`check-patch-tree`（**qemu 段 0 problem**；其它段红属在途任务，逐条归因）、`make_patch` 幂等、`apply-series --component qemu` rc=0 且 HEAD 不变、`--source-state` qemu clean；
5. 完成区 ≤30 行、无运行期路径；写明**新安装根 md5**；`**状态**` → `待验收`。

## 硬约束

只动 `components/qemu/**` + 必要 `tools/linux/**` 或 `tools/qemu/**` 驱动 + 本任务书；**不动** `spec/`、`contracts/`、`tests/inst/**`、`components/{linux,gem5,chipyard}`；不提交 git；`cp`+md5 还原（禁 `git checkout/restore`）；构建用 `JOBS=32`，构建期间不跑长测试；**构建前 `df -h`**（今晚两次 ENOSPC）。

## 完成区

**前提订正（请先读）**：任务书所述「`SYS_WRITE0` 先 `target_strlen` 再 `probe_access_flags`、走页表」在基线 `bb50aab1` 上**已不成立**——`m14-qemu-002`（合入 `b850c1e3`）已把 `SYS_WRITE0`/`SYS_OPEN` 的串长探测换成 target 钩子 `common_semi_strlen()`（dadao 强定义按 PA 逐块读，复用 `cpu_memory_rw_debug` → `dadao_cpu_translate_for_debug`），`translate_for_debug` 注释亦彼时改为 PTW 口径；基线 `check-linux-k1` 实测 **111/111 rc=0**、K14 的 `SYS_WRITE0` 断言已 `[PASS]`。故本任务**不重复实现**已存在的 PA 路径，交付 = 补 K14 缺的覆盖面（长串/多分块）+ 收掉最后一处过时注释 + 注入证明。

**修改文件**：`tools/linux/semihost_pa_probe.S`（+第二个 `SYS_WRITE0`：640 B 长串 `sp_long`=`ENTRY_VA+0x1030`，起点在 256 B 块内 48 B 处、跨 3 块）；`tools/linux/check_k1.py`（K14 oracle 现场要求长串 >2×256 B、+断言「长串经 PA 完整取出」、逐字节全等纳入长串、selfcheck K14 3→4 路）；`components/qemu/patches/target/dadao/cpu.c.patch`（`dadao_cpu_mmu_index()` 注释：M1「no MMU」→ 单地址空间 + 窗口两级走在 `tlb_fill` 内查询 + PTBR/ptw_enable/ASID/mask/TLB 命令同笔丢弃派生翻译缓存）；`components/qemu/changelog.md`（M14 追加一条）；本任务书。

**测试结果**：一键证据脚本 **68/68 rc=0**（`--skip-gates` 档：静态断言 + 3 路注入 + 补丁纪律）；全量档 **77/79**，2 红全为外部：`check-linux-k0` **116/119**（3 红 = `K12 apply-series --component linux` ×2 + 其派生「只点名 linux」）与 `check-linux-k2` **102/104**（2 红 = R1/R2 k0 回归同源）。根因：共享 `components/linux` 源树 HEAD `94647cfb` 已是在途任务的补丁态、不等于本 worktree 基线的 linux 补丁集 ⇒ `apply_series` 自述「neither base nor base+1」拒绝；本任务 diff 不含 `components/linux`（0 处）。

**验收结果**：
- **先红后绿**（同一断言、同一探针）：走页表（注入①把 `common_semi_strlen(cs,args)` 换回 `target_strlen(args)`）→ `console=b'XYZ+'`、WRITE0 短串+长串两条 `[FAIL]`、`FAIL (3 red of 7)`；现状 → `console=b'W0PAOK\n<640 B 长串>XYZ+'`、`K14: PASS (7/7)`。
- **3 路注入**（`cp`+md5 还原；每路还原后安装根 md5 均回基线）：①走页表 ⇒ 2 红/5 绿；②identity 窗口上界截到 `0x101030` ⇒ `console=b'W0PAOK\nXYZ+'`、**只有长串断言红**（短串/WRITEC/SYS_OPEN 绿 ⇒ 新断言有独立判别力）；③强定义只读首个 256 B 块 ⇒ 同上。
- **门控真数**：`check-linux-k1` **112/112**（原 111 + 新增 1；K14 = 7 条断言）、`check-inst-asm` **904/904**（272 id）、`check-arch` PASS（14 探针）、`check-qemu-forms` PASS、`check-interface` rc=0、`check-component-changelog` PASS（9 文件 × 4 = 36 项）、`linux-semihosting-smoke` PASS、`check_k1 --selfcheck` **19/19 组可翻转**（K14 四路）。
- **补丁纪律**：`make_patch` 幂等（0 份重写）、`apply-series --component qemu` rc=0 且源树 HEAD `eb632e4` 不变、`--source-state` qemu `clean=True`、`check-patch-tree` **qemu 69 份 0 problem**（24 problem = gem5 16 / chipyard 4 / linux 4，均 ⑥+⑨ 成对，同属那些源树的在途补丁态）。
- **新安装根 md5**：`qemu-system-dadao` = **`0acc25bf26e1b015c4c275e3e927c08a`**（源树干净时取，构建树与安装根一致）。

**新发现/坑**：① `.work` 是共享树软链 ⇒ 证据驱动脚本不能用 `Path(__file__).resolve().parents[n]` 定仓库根（实测解析到主工作树、import 旧门控而打印旧断言 = 假绿）；须显式传本 worktree 根并断言被测探针含本任务新增内容。② 「还原后确实重编」不能靠 grep ninja 的 `[N/M]` 行：并发门控窗口内实测 `make build-qemu` 只跑 `qemu-version.h` 一项（重编落在 `install-host` 内含的 `build-qemu`）⇒ 日志 grep 假红；改用二进制 md5 真值（注入版 ≠ 基线、还原后 == 基线），与 `ISS-451` 同族。③ `ISS-450` 的 `SYS_WRITE0`/`SYS_OPEN` 部分实际已由 `m14-qemu-002` 关闭，建议 issue 里补注并把 007 与 002 的重复关系记档（防后续重复立任务）。

**遗留问题**：无未完成项；`ISS-450` 是否关闭、以及 007 与 002 的重复关系如何记档，归主会话裁定。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：可交付（前提订正已如实披露；5 条 finding 全部处置，无未修项）。

**改动落点理由（复用哪套 PA 换算）**：**不新造换算**——字符串取参沿用 `m14-qemu-002` 的 `common_semi_strlen()` 钩子（dadao 强定义在 `target/dadao/common-semi-target.c`，逐块 `cpu_memory_rw_debug` → `dadao_cpu_translate_for_debug` 的 identity/PA 窗口），`SYS_READC`/`SYS_FLEN` 的 VA→PA 仍走 `m14-qemu-004` 的 `dadao_cpu_va_to_pa`（本次未改）。本任务的代码改动只有一处过时注释（`dadao_cpu_mmu_index()`），其余是门控覆盖与证据。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书前提与基线代码不一致（`SYS_WRITE0` 已按 PA） | ✅已修（如实订正 + 补真实缺口，非静默实现） | 完成区首段写「前提订正」并给基线证据；把交付改为「补长串覆盖 + 注释 + 注入」，不重写已有钩子 | 基线 `check-linux-k1` 111/111 rc=0、K14 `SYS_WRITE0` `[PASS]`（改前日志）；补丁 `SYS_WRITE0` 行 = `common_semi_strlen(cs, args)` |
| F2 证据脚本用 ninja `[N/M]` 日志证明「还原后重编」 | ✅已修 | 改判二进制 md5 真值：注入版 ≠ 基线、还原后 == 基线（构建树与安装根各一条） | 首轮 3 条日志 grep 假红 → 改后 `--skip-gates` 68/68 rc=0 |
| F3 证据驱动用 `__file__` 定位仓库根（`.work` 软链 ⇒ 解析到主工作树） | ✅已修 | 驱动改为必须显式 `M14_QEMU_007_ROOT` + 断言探针含 `sp_long` + `SEMI_PROBE_S` 指向本树 | 首版实测打印旧 6 条断言（假绿）→ 改后 7/7 |
| F4 K14 oracle 由「恰 5 段 `.ascii`」扩到长串 | ✅已修 | 「前 5 段固定 + 其余拼接为长串」，现场要求 >2×256 B；marker 污染检查扩展到长串；`sp_long` 纳入符号偏移断言 | K14 7/7 PASS；长串 640 B 现场统计一致 |
| F5 selfcheck 分母口径（K14 3→4 路） | ✅已修 | `groups = len(TEXT_MUTATIONS)+4+4`，K14 增「长串截断」一路 | `check_k1 --selfcheck` **19/19**，四条 K14 翻转均实测红 |

**越界核对**：`git status -uall` 仅 `components/qemu/{patches/…cpu.c.patch,changelog.md}` + `tools/linux/{check_k1.py,semihost_pa_probe.S}` + 本任务书；`spec/`、`contracts/`、`tests/**`、其它组件 0 改动；qemu 源树 `git status` 空。

### 第 1 轮 reviewer 验收

**重跑（本人执行，rc 自采，未采信完成区）**

1. 一键证据脚本（运行期证据目录 `run.sh`，全量档）→ `RUN1_EXIT=1`、`[STAT] PASS=75 FAIL=4`。4 红：`check-linux-k0 rc=2`、`check-linux-k1 rc=2`、`check-linux-k2 rc=2`、`check_k1 --selfcheck rc=1`（完整输出在运行期日志目录 `review-run1.log`，收尾即删）。
2. **绿项（我这轮实测）**：静态断言 9/9；基线 K14 `rc=0`、长串断言 PASS、控制台含完整 640 B；注入 A/B/C 三路逐项满足「注入点唯一 + 源树 dirty + build/install rc=0 + 注入版 md5≠基线 + K14 `rc=1` + 必须红/必须绿命中 + 还原 md5 复原 + 还原后安装根与构建树 md5==基线 `0acc25bf…` + K14 回绿」；`make_patch` rc=0 且 0 written、`apply-series --component qemu` rc=0 且 HEAD `eb632e4` 不变、`check-patch-tree` qemu 69 份 0 problem、`--source-state` qemu clean；`check-inst-asm` 904/904、`check-arch` PASS（14 探针）、`check-qemu-forms`/`check-interface`/`check-component-changelog`/`linux-semihosting-smoke` rc=0。
3. **`check-linux-k1` 首轮 `FAIL (98/115)`、17 红＝外因**：17 红全在启动链（K5 `rc=231`、K6/K11/K12/K13 `CFXPERM … die mode=2 code=0xe7`），**K14 七条全 PASS**；同一 QEMU 二进制 `md5=0acc25bf`——`k1-new.log`（05:07，kernel `5415576 B`）⇒ PASS 112/112，我这轮（07:54，kernel `5416976 B`）⇒ FAIL ⇒ 唯一变量是共享内核镜像；佐证：共享构建树对象文件 07:47、07:55–08:01 两批 mtime，`m14-linux-012` 正在跑 `make_vmlinux.py`，共享 linux 源树 HEAD `197039629` 提交于 07:58:12，`find` 显示 07:50–07:55（k1 窗口）0 改动。
4. **有据重试 1 次**：`JOBS=32 make check-linux-k1` → `RETRY1_K1_EXIT=0`、`check-linux-k1: PASS (112/112)`、`[FAIL]`=0 ⇒ 完成区 112/112 属实。
5. `check-linux-k0 rc=2`（116/119）、`check-linux-k2 rc=2`（102/104，仅 R1/R2）＝`m14-qemu-006` 已验收记录同源外因：`apply-series: linux HEAD (94647cfb092f) is neither base (7b20d05fd38d) nor base+1 … refusing to apply`；本任务 `$BASE..HEAD` 涉 `components/linux` **0 处**。`--selfcheck 17/19` 两路红（`基准输出全绿 实际=18 失败`、`K12 注入点未命中`）由坏内核派生，K14 四路 + K15 三路翻转均 PASS。

**脚本审核**：逐条 `chk` 期望/实际比对，计数现场 `grep -c`/python 现场统计（非两侧写死），注入判据含「必须红 + 必须绿」双侧，还原用 `cp`+md5 且以二进制 md5 真值判重编（不 grep ninja 行），无 `cmd | tee` 吞码，`gate()` 对 rc 逐项断言 ⇒ 每条断言有可达 FAIL 路径。

**独立注入 D（任务书未列的第 4 路）**：`semihosting/arm-compat-semi.c` 把 SYS_OPEN 文件名长度探测 `common_semi_strlen(cs, arg0)` → `target_strlen(arg0)`（走页表）⇒ build/install rc=0、注入版 md5 `6ae23b7b…`≠基线、K14 `rc=1`，**仅 SYS_OPEN 与字节 oracle 两条红**，短串/长串/WRITEC 仍绿（A/B/C 三路均未红过 SYS_OPEN）；`cp`+md5 还原后安装根与构建树 md5 回 `0acc25bf…`、源树干净、K14 `rc=0` 七条全绿，`INJ_D_EXIT=0`。

**约束核验**：未提交 git；未动主工作树；`$BASE..HEAD` 仅 5 文件＝完成区「修改文件」；`spec/`、`contracts/`、`tests/`、`components/{linux,gem5,chipyard}` 0 改动；完成区 18 行、本记录 ≤40 行、任务书全文无运行期路径；还原全程 `cp`+md5（未用 checkout/restore/stash/reset）；构建 `JOBS=32`。

**判决：Accepted** —— 验收命令在我自己的重跑下全部达标（`check-linux-k1` 重试 1 次后 112/112；k0/k2 红为已登记且可复现归因的外因），约束无违反，≥2 路注入（脚本 3 路 + 我独立 1 路）均证明反例可达 FAIL。**1 条非阻断 finding 交 architect**：完成区未提示「共享 `vmlinux` 被并发任务重建时 `check-linux-k1`/`--selfcheck` 会瞬时红」，建议补一句外因说明防后续误判。
