# m13-qemu-001: QEMU 的 Tiny `cfx_power` + `cfx3 hmon`（M13 前置）

**模块**：qemu
**项目里程碑**：M13
**依赖**：无（可与 `m12-chipyard-007` 并行；**验收要求三平台一致**）
**可并行分片**：否（组件单写者）
**状态**：已验证

## 用户裁定（2026-11-09）

- **Tiny 实现 `cfx_power`（cfx63）+ `cfx3 hmon`**（决策 1 = B）
- hmon SRAM **复用 `0x0fff_0000_0000`**（64 KiB，决策 2 = A）；**无 PTW/页表**（决策 3 = A）
- **同步异常不经 `trap` 指令**，直接进 hmon 向量；与 semihosting 的 `trap` 无冲突
- **Tiny 的 semihosting `trap` 统一写 `trap cfx_hmon`**（实现上仍只看 `immu18`，不判断 cfxha）
- `trap` 判定：`immu18 ∈ 0x3FF00–0x3FFFF` ⇒ semihosting；`cfxha=3` + 其它 `immu18` ⇒ 进 hmon
- **排期**：QEMU/gem5 侧排在 **M13 前置**；chipyard 侧在 M12（`m12-chipyard-007`）

## 目标

1. `cfx_power`（cfx63）：Tiny 启动移交 `power → hmon`（与 Vast 同构）。
2. `cfx3 hmon`：寄存器组（`excp_cause`/`excp_vector`/四类同步 mask/`cfx_intr_mask`/`switch_run_mode`）；同步异常（ILLI/UNDI/`CFXMEM`/`MALIGN`/`IALIGN`）进 hmon 向量。
3. **IALIGN 时 IP 停留在非法地址**（`DADAO-12 §5`），不写回 `nextIp`。
4. `trap` 区分：`immu18` 区间判定 semihosting vs hmon；semihosting 统一 `trap cfx_hmon`。
5. **地址图**：Tiny 增加 hmon SRAM `0x0fff_0000_0000`（64 KiB）。
6. **与 chipyard 一致**：同一 ELF 在 QEMU 与 chipyard 上的异常行为（`excp_cause`、IP 停留、退出码）逐条一致。

## 验收标准

1. `cfx_power → hmon` 移交可观测（运行模式与 PC）
2. 五类同步异常各至少 3 例进 hmon，`excp_cause` 正确
3. **IALIGN 时 IP 停在非法地址**（专门断言）
4. semihosting 的 `trap cfx_hmon` 与 `trap cfx63` 都能工作（`immu18` 判定不依赖 cfxha）
5. **与 chipyard 的三平台一致**（同一 ELF 逐条比对；chipyard 侧由 `m12-chipyard-007` 提供）
6. 现有 Tiny 测试零回归（`check-inst` / `check-arch` / tset 相关）
7. 构建/门控：`build-qemu` / `install-host` / `check-patch-tree` / `check-source-state` / L1 / L2 rc=0
8. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
9. 完成区 ≤30 行、无运行期路径

## 非范围

- 不改 chipyard 侧（`m12-chipyard-007`）
- 不实现 smon（Tiny 不实现）
- 不改 spec（`Machine-v5` 的 Tiny hmon 由 SPEC 任务先落地；本任务按 spec 实现）

## 说明

- **前置**：spec 的 Tiny hmon 修订必须先落地（见 M13 的 SPEC 任务），否则本任务无依据。
- 组件单写者；节点操作后 `make sync-node-repo`。

## 冲突登记

> 执行中发现的 spec 缺口 / 跨任务影响。本任务按标注口径实现并在代码注释里指向该口径；需 SPEC 或后续任务统一。

1. **`cfx2rd`/`cfx2rc` 到保留 `cfxha`**：`DADAO-12 §5.1`/`§5.2(一)` ⇒ `ILLI`；`Machine-v5 §3` 只写「未实现 cfx 的寄存器访问 ⇒ `CFXREG`」。**按 `DADAO-12` 实现（`ILLI`）**，待 `m12-spec-003` 统一。
2. **`trap` 到「已分配未实现」cfx**：`Machine-v5 §3` 只给 Tiny 的口径（⇒ `ILLI`），Vast（如 `cfx5`）无正文。本实现：Tiny = `ILLI`、Vast 保持既有 `CFXREG`。
3. **Tiny hmon 镜像如何装载**：`Machine-v5 §6` 未规定。按用户裁定 R13-A（宿主 loader 直装 hmon SRAM）实现为「ELF `PT_LOAD` 到 `0x0fff_0000_0000`」，spec 无正文。
4. **`excp_cause_info` 覆盖面**：`Machine-v5 §4.4` 只列五类，`DADAO-13 §2` 列 11 项。本实现按 `DADAO-13 §2` 填 `CFXREG`/`CFXPERM`/`RASOF`/`RASUF` 的 info。
5. **Vast 的同步异常仍是 staged 机器 fault**（`ILLI`/`UNDI`/`CFXMEM`/`MALIGN`/`IALIGN`/`RAS*` 直接映射退出码），与 `DADAO-12 §5.2(一)` 不符；`min_rom_probe_049t`/`integ039t`/`integ040t`/`integ042t`/`integ048t` 的部分用例以旧口径为 oracle ⇒ 本任务用 profile 开关（`sync_exc_monitor_entry=false`）保持零回归，统一需另立任务（改探针或改实现）。
6. **`tests/shared/machine-profiles.yaml` 的 `tiny` 段**仍是旧口径（`hmon: false`、`cfx: false`、`fault_record: null`），TESTCASES 侧需同步；本任务未改（越界）。
7. **设计说明（非缺口）**：`IALIGN` 在取指路径两处触发同一异常——translator（代码页已在 TLB 时）与 `tlb_fill` 取指分支（保证「未映射且非对齐」时 `IALIGN` 优先于 `CFXMEM`，`DADAO-12 §2.2.6`）。`trap` 进入时的向量可达性不做回退（软件显式指定目标），只有同步异常走「向量不可达 ⇒ 机器 fault」兜底。

## 完成区

**测试结果**：一键证据脚本 5/5 PASS（`build` / `tiny-hmon-run` rc=0 / `semihosting` 标记 / `no-regression` 44 例 / `injection` rc=0x42 + `restore` rc=0）；覆盖 `cfx_power→hmon` 移交（`excp_prev_run_mode`、`trap_num`、cause_ip）、一般 `trap`×2、Tiny 不离开 hypv、五类同步异常各 3 例进 hmon（`excp_cause_id`/`ip`/`info` 逐条断言，共 16 条同步异常）、`CFXREG`、`escape` 的 offset 0 与 +4 两路、`IALIGN` 的 `excp_cause_ip` = 非法地址（`IP` 停留）、计数器（`trap_num`=3、`excp_sync_num`=16、`escape_num`=19）。回归：`check-inst` = Vast 全量 + Tiny 子集 PASS（44/44）；`check-arch` 全量除 1 例既有失败（`min_rom_probe_integ047t start_busy_returns_busy`：基线与本改动同为 0xF1，属既有环境/时序问题）外全绿；`check-arch-smoke`、`check-unit`、tset×3、L2 `check-modules` 全 PASS。
**修改文件**：`components/qemu/patches/` 下 7 份（`hw/dadao/dadao-machine.c`、`target/dadao/{cpu.c,cpu.h,helper.c,helper.h,translate.c}`、`target/dadao/insn_trans/trans_ctrl.c.inc`）+ `components/qemu/changelog.md`（M13 节）。证据与测试源码在运行期证据目录（未归档）。
**验收结果**：`make build-qemu` = PASS；`make install-host` = PASS；`check-source-state` = `qemu: OK count=1 clean=True`；`check-patch-tree` = qemu 断言 0 问题（其余红为并发 gem5 任务工作树脏）；`check-interface` = 89/89 PASS；`check-qemu-forms` = PASS；`make check-modules`（L2）= PASS；`make check`（L1）的 qemu 相关项全 PASS（`check-patch-tree`/`check-run-artifacts`/`check-temp-dirs`/`check-knowledge-refs` 的红分别来自 gem5 脏树、他任务陈旧临时目录、`m12-spec-002` 任务书的 `.work` 引用，均非本任务）。
**新发现/坑**：① 同步异常全面改为进 monitor 后，「无 handler 的 Vast 探针」会因向量可达但内容是启动 stub 而超时 ⇒ 必须同时给出「向量不可达 ⇒ 机器 fault 退出码」兜底并保留 Vast 的 staged 口径；② Tiny 的 ELF 若含 BootROM 段，`-kernel` 会与 `bootrom-image` 报 ROM overlapping ⇒ 装机镜像与 `-kernel` 需分开链接（同一目标文件、两份 `lds`）；③ `.org` 填充字节会被当作指令执行（UNDI 反复进 hmon）⇒ stub 必须显式跳过填充；④ `excp_cause_ip` 可写是 hmon 改返回地址的正规手段（`IALIGN` 重定向即用它）；⑤ 失败码应记**首个**失败块，记末值会掩盖定位；⑥ 同一 `.work` 被并发任务共享时，`check-patch-tree`/`check-run-artifacts` 会因对方脏树/日志命名而红。
**遗留问题**：① 验收 5（三平台一致）BLOCKED：chipyard 侧 `m12-chipyard-007` 未开始，同一 ELF + 期望表已具（证据脚本可复跑）；② 冲突登记 1–6 需 SPEC/TESTCASES 侧统一；③ 冲突登记 5 的 5 个 arch 探针旧口径依赖需在统一时同步改探针。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：7 份补丁的完整 diff + 证据脚本 + 测试程序；对照 `spec/Machine-v5` 0.4.2-rc §1.1/§2/§4.1/§4.4/§5.1/§6/§7.1、`spec/DADAO-12 §2.2.6/§5.2/§5.3`、`spec/DADAO-13 §1/§2`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `dadao_cpu_do_interrupt` 出现重复注释块、CFXPERM 说明与实现分叉 | ✅已修 | 合并为单块注释，CFXPERM 归入统一的 monitor 入口说明 | 重导出补丁后 `check-qemu-forms` PASS |
| F2 `RASOF` 的 `cause_info` 未赋值（会读到上一条异常的旧值） | ✅已修 | `helper_ras_push` 溢出路径写 `env->sync_fault_info = ret_addr` | 重新构建 + 证据脚本 5/5 |
| F3 IALIGN 分支 `pc_next` 不前进使 `tb->size == 0`，QEMU 断言中止 | ✅已修 | 置 `DISAS_NORETURN` 后仍 `pc_next += 4`（只作 TB 记账，不写回 `env->pc`） | 证据脚本 `tiny-hmon-run` rc=0（此前为 SIGABRT） |
| F4 Vast 同步异常改道导致 5 个 arch 探针超时（非本任务范围） | ✅已修 | 新增 profile 开关 `sync_exc_monitor_entry`（Tiny=true、Vast=false 保持 staged 口径）+ 登记冲突 | `check-arch` 除既有 1 例外全绿；`check-inst` 全绿 |
| F5 `escape` 无条件恢复 `global_cfx_intr_mask`：同步异常进入的帧没有保存值，会清零 monitor 掩码 | ✅已修 | 新增 `saved_intr_mask_valid`（仅 `trap` 进入时置位，`escape` 恢复后清除） | 手算 + 证据脚本中 19 次 escape 后 `GIM` 仍为全 1（`-d cpu` 抽查） |
| F6 证据脚本的注入反例码取「末个失败块」而非首个，无法定位 | ✅已修 | `CHK` 保留首个失败块号（`or.o rd15, rd14, rd14`），退出码 = `0x40 \| 块号` | 注入 ⇒ rc=0x42（块 2），还原 ⇒ rc=0 |
| F7 `arch` 全量唯一红是否本改动引入 | ❌不修（非本任务） | — | 以**基线源码**（`HEAD` 版 7 文件）重建后同一用例同样失败（0xF1），属既有失败 |

判决：所有可修 finding 已修并复验，状态置 `待验收`；F7 判定为既有失败并留证。

### 第 1 轮 reviewer 验收（2026-11-10）

**重跑（workdir 内相对路径，rc=实取；长日志留 `.work/log/qemu/<任务ID>-review-*.log`）**

- `make_patch.py qemu --dry-run`→0（66 路径）；真跑→0：**0 written / 66 unchanged**；7 补丁+`changelog.md` md5 前后逐字节相同 ⇒ 幂等可重导出、无手工 cp 痕迹（无 `.orig`/`.rej`）。
- `make check-source-state`→0：`qemu: OK HEAD=ba0ab8e6e21f count=1 clean=True`。`make check-patch-tree`→**2**：30 problem **全 `gem5:`**、`qemu:` 断言 0 问题（并发 `m13-gem5-001` 脏树，非本交付物）。
- `make build-qemu`→0；`make install-host`→0（`check-install-tools` 48 checks PASS；安装根 `.dadao/cross-toolchain` 仅由 install-host 写入，本次未手改）。
- `make check-inst`→0：Vast 980/985 + Tiny **44/44**；`make check-arch-smoke`→0（10/10 + 25 服务）；`make check-modules`(L2)→0（含 `check-unit`、tset×3 PASS）；`check-interface` 89/89、`check-qemu-forms`→0、`check-component-changelog`→0。
- `make check-arch`→0：**69 PASS / 0 FAIL（本轮未复现既有失败）**；`start_busy_returns_busy` 单跑 20 次：本改动 1 FAIL（`got=0x62`）。
- `make check`→2、`make -k check`→2，4 红逐条归属：`check-patch-tree`(30, gem5) / `check-knowledge-refs`(2, 均在 `m12-spec-002` 任务书) / `check-run-artifacts`(**5 条全是 reviewer 自己的 `review-*.log` 命名**，改名后重跑→**0**、0 illegal) / `check-temp-dirs`(5, 全他任务目录)。**L1 rc≠0 来自并发/他任务，非本交付物**。
- `./.work/evidence/<任务ID>/run.sh`→0：**5/5**（no-regression 44/44；injection `expected=66 actual=66`）。脚本 6 条检查各有可达 FAIL 路径，无恒真/双写同值。
- **独立反例（改被测产物、非测试期望值）**：`trans_ctrl.c.inc:474` `if (immu18 >= 0x3FF00)` → `… && a->ha != DADAO_CFXHA_HMON`（判定改看 cfxha），build/install rc=0（bin md5 `b7de7ff6…` ≠ `d2e902d5…`）⇒ run.sh **rc=1**：`tiny-hmon-run expected=0 actual=66 FAIL` / `semihosting marker=missing FAIL` / `restore FAIL`；另一次 `…== DADAO_CFXHA_HMON` 亦红（rc=124 超时）。`cp` 还原 → md5 `c9f6d762…` 相等、源树 porcelain 空 → build/install rc=0（bin md5 回 `d2e902d5…`）⇒ **5/5 rc=0 回绿**。
- **基线 A/B（`cp`+md5，未用 checkout/restore）**：注入 7 份基线内容（源树恰 7 M）→ build/install rc=0 → 同探针 20 次 **1 FAIL `got=0x62`**，与本改动 1/20 同签名同量级 ⇒「既有/时序抖动」成立；还原 md5 逐位相等、源树干净、重建安装 rc=0。
- **独立 oracle**：`llvm-objdump` 实测 `7f 0f ff 04` / `7f 0c 12 34` / `7f 00 01 00` / `7f 14 00 10` / `7a 18 00 05` ⇒ 期望 `cause_info` 派生自指令编码、非抄 QEMU。**断言点现场统计**（awk 区分宏体）：CHK 12 + CHK_REC 44 = **56**。

**约束核验**：逐条对 `Machine-v5 §1.1/§1.2/§2/§3/§4.1/§4.2/§4.4/§5.1/§6/§7.1` + `DADAO-12 §5.1/§5.2(一)(三)/§5.3` + `DADAO-13 §1/§2` 一致——几何（8 MiB/64 KiB/hmon `0x0fff_0000_0000`）、`cfx_impl_mask` Tiny={3,63}、`cfx_enter` 步骤 4→5→6→7 与 `inner_cfx_code` 63→3（escape 要求 `cfxha==当前 cfx` 使移交可间接断言）、五类 cause id one-hot + info、IALIGN `cause_ip=info=非法地址` 且不写回 nextIp、escape 偏移 {0,+4} 与 SBZ→ILLI 早于状态切换、`immu18>=0x3FF00` 判定与 cfxha 无关。8 文件 == 完成区「修改文件」；完成区 7 行、无具体运行期路径；HEAD `1fd393d8` 未变、工作树干净、reviewer 未 commit；reviewer 自建 `/tmp` 临时物已删除并复跑 `check-run-artifacts`→0。

**findings（文档级，交 architect 收尾改，不阻断）**：① 完成区「57 条断言」实为 **56**（宏体第 79 行被重复计）；② `check-patch-tree` 写 rc=1、实际 `make` **rc=2**；③ 完成区称 check-arch 1 例失败，本轮**全绿**（仅单跑 ~5% 抖动，基线同概率，「既有」结论成立但「全量失败」不复现）；④ hmon 向量**首次写入发生在 power 桩**，而 `§2/§4.4` 字面为「hmon 启动时写入」（复位默认 `0x0fff_ffff_f000` 不可达 ⇒ 字面顺序不可实现），建议并入缺口③补 bootstrap 正文；⑤ CFXMEM-1 的 `cause_info` 期望为 0，与「info 未置值」不可区分（cause 断言仍有效，info 由 CFXMEM-2/3 非零地址覆盖）；⑥ `escape` SBZ 非零 ⇒ `ILLI` 无用例覆盖（实现符合 spec）。

**判决：Accepted**。验收 5（三平台一致）仍 BLOCKED 于 `m12-chipyard-007`（已按遗留登记）；L1 rc=2 的 4 红已逐条归属并发 gem5 / 他任务 / reviewer 自身日志命名并复验为非本交付物。

#### 收尾（architect，2026-11-10 03:54）

- 第 1 轮 reviewer **Accepted**：Tiny hmon 语义与 `Machine-v5 §1.1/§1.2/§2/§3/§4.1/§4.2/§4.4/§5.1/§6/§7.1`、`DADAO-12 §5.1/§5.2(一)(三)/§5.3`、`DADAO-13 §1/§2` 逐条对上；checker 独立注入（`trap` 判定改看 `cfxha`）⇒ `run.sh` rc=1 ⇒ `cp`+md5 还原 ⇒ 5/5 回绿。
- 文档更正（reviewer findings）：断言数 **56**（非 57）；`check-patch-tree` 实际 rc=2（30 条全 `gem5:` 并发脏树）；`check-arch` 本轮 69 PASS/0 FAIL（完成区「1 例失败」为单跑 ~5% 抖动，基线同概率复现过）。
- 门控：`build-qemu`/`install-host`/`check-inst`（Vast 980/985+Tiny 44/44）/`check-arch-smoke`/L2/`check-arch` 全 rc=0；`check-patch-tree` qemu 断言 0 问题。
- spec 缺口（交 `m12-spec-003` 候选）：hmon 镜像装载无正文（必须先改 spec）、`excp_cause_info` 5 vs 11、`cfx2*` 保留（有上游依据，可绕过）、Vast staged fault（`spec-004`）、`machine-profiles.yaml` 旧口径。
