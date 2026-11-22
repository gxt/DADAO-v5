# m16-qemu-003: cfx5 命令接线（clean/invalidate/flush）

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-qemu-002`（影子 D-Cache 数据通路）、`m18-qemu-002`（monitor-first 异步仲裁与 pending 迁移；**必须先合入**，否则本任务会基于 target-first 的 QEMU 异步路径，与 `spec/DADAO-12 §5.2` 不一致）
**可并行分片**：否
**预估**：3–4 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景

`m16-qemu-001` 已落 cfx5 寄存器面，`m16-qemu-002` 已落影子 D-Cache 数据通路。本任务把 `cache_ctrl` 命令接到影子 cache，语义按 `m16-spec-001`/`spec/Kaiwu §3.2`。

## 要做

1. **命令解码**：`cache_ctrl` 的 `[1:0]` 操作（none/clean/invalidate/flush）、`[3:2]` 范围（all/PA 单行/PA 区间/reserved）、`[15:14]` 选择（I/D）；`cache_addr_start`/`cache_addr_size` 按 56 位 PA。
2. **D 侧效果**：
   - clean：脏行写回，保留行；
   - invalidate：丢弃脏数据（不写回）、删除行；
   - flush：写回 + 删除；
   - 范围匹配、使能位为 0 时不维护、不可缓存/MMIO 无效果不报异常。
3. **I 侧**：clean 为 no-op；invalidate/flush 调 `tb_invalidate_phys_range`（复用 ARM `IC_IVAU` 的写法），保证后续取指重取；不做 I 阵列。
4. **异常**：保留编码/`size=0` 等按契约报 `CFXREG`；不得 panic。
5. **off 模式**：cfx5 命令仍按 `CFXREG`（`m16-qemu-001` 口径）。

## 不做

- 不改影子数据通路（qemu-002）；
- 不改 RTL/gem5；不写新用例（`m16-testcases-009`）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. D 侧：脏行 `invalidate` 后底层 RAM 仍旧值（DMA 读可见）；`clean` 后底层 RAM 新值；`flush` 后行不存在但内存新值；
2. I 侧：改写代码后 `invalidate`，取指执行新代码；
3. 范围：all / 单行 / 区间 / reserved 的编码与异常逐条；
4. **可达 FAIL**：注入「invalidate 先写回」⇒ 旧值判据红；注入「I 侧误用 D 动作」⇒ 红（「I 侧不调 tb invalidate」在 QEMU 上不可达：写 RAM 自动失效 TB，改记已知不可达）；`cp`+md5 还原后回绿；
5. `check-patch-tree` qemu 段 0 problem、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` rc=0 **26/26**（build 1 + 19 例 probe + static 6：make_patch 导出/幂等、check-patch-tree qemu 段、check-index-blobs、check-component-changelog、check-tasks）；`run.sh --inject` rc=0 **46/46**（3 路注入各「md5 变→重建→判据红→`cp` 还原→md5 相等→重建→回绿」：invalidate 写回 ⇒ `on_d_invalidate_discards` 红 rc=227；PA 区间忽略范围 ⇒ `on_d_range_span` 红 rc=234；I 侧误用 D 动作 ⇒ `on_i_leaves_d` 红 rc=243；收尾 patches 树 md5 `2f14b9a2` 不变、组件源树 `git status` 空）。19 例覆盖：D 侧 clean 写回+保留行（DMA 直读新值、再 DMA 改写底层 RAM 后 guest 读仍命中旧缓存）、invalidate 丢弃不写回（DMA 直读旧值、行删除后重填）、flush 写回+删除、单行/区间/all、区间外不写回、56 位 PA 不截断、使能位门控、不可缓存 PA 无效果、I 侧 invalidate 后取指重取、I 侧命令不碰 D、sel/op 无条件 no-op、非法编码 `CFXREG`（on/off 各例，guest 内校验 cause_id）；off 下合法命令 no-op 且数据直通。
**修改文件**（5）：`components/qemu/patches/target/dadao/{cpu.h,helper.c}.patch`、`components/qemu/{README.md,changelog.md}`、本任务书。
**验收结果**（真实 rc）：`make build-qemu` 0（softmmu + linux-user 两支均过，新增代码 0 warning）；`run.sh` 26/26 rc=0、`run.sh --inject` 46/46 rc=0（日志 `run-final.log`/`run-inject-final.log`）；`min_rom_probe_integ042t.py --qemu <构建二进制>`（`DADAO_TEST_PROFILE=vast`）**25/25** rc=0（cfx5 寄存器面与合法 no-op 未回归）；`make_patch.py qemu` 0 且二跑 `0 written`（幂等）；`check_patch_tree.py` rc=0、qemu **69 patch / 0 problem**、全仓 458 patches OK；`check-index-blobs`/`check-component-changelog`/`make check-tasks`/`check-dirs`/`check-no-residue`/`check-spec-refs`/`check-contracts-dir`/`check-manifests-guard` 均 0。组件源树 HEAD `fe6f37f`（`base..HEAD` 恰 1 commit、工作树干净）；未改 `spec/`、契约正文、RTL/gem5、影子数据通路语义，未升版本号，未提交仓库 git。
**新发现/坑**：① **I 侧的「不调 tb invalidate ⇒ 旧指令红」在本 QEMU 上不可达**：系统模式任何写 RAM 的 `address_space_write` 都会经 `invalidate_and_set_dirty()` 的 `DIRTY_MEMORY_CODE` 调用 `tb_invalidate_phys_range()`，而影子里的新代码必须先由 D clean/flush 写回 RAM 才能被取指看到 ⇒ 去掉 I 侧 invalidation 后 `on_i_invalidate_refetch` 仍绿（实测注入日志 `inject-i-noop.log`：基线与注入后均 PASS）。另试 `-d in_asm` 的重译计数作替代判据：**无任何命令**时同一 RAM 函数第二次调用也会重译（每指令一 TB + 主循环查找），计数不可判别 ⇒ 该判据已弃用。故 I 侧按契约实现并以「取指重取」端到端例 + 「I 命令不碰 D」例覆盖，注入反例改用「I 侧误用 D 动作」。② 系统模式 `tb_page_addr_t` = **RAMBlock 偏移**、不是 guest PA：必须先 `address_space_translate()` 再 `memory_region_get_ram_addr() + xlat`（ARM 的 `IC IVAU` 只在 user 模式，不能照抄）。③ `cache_ctrl[15:14]` 的字段值是 **2=I / 1=D**（bit15=I）；`m16-qemu-001` 探针里 `SEL_I/SEL_D` 写反了（该处只验合法/非法，无效果断言，未暴露）。④ 原始 RAM 的独立观测通道 = `cfx_pmem` DMA（PA→SRAM / SRAM→PA，SRAM 在 56 位 PA 之外、不受影子影响）；「clean 保留行」用「DMA 改写底层 RAM 后 guest 读仍返回缓存旧值」证实。⑤ 失败时的进程退出码应透传 guest 的 `SYS_EXIT` 码，否则证据脚本无法断言「红在哪一条」（本轮已改 probe 透传 227/234/243）。
**遗留问题**：① 任务书「可达 FAIL：注入 I 侧不调 tb invalidate」与 QEMU 机制冲突（见新发现①），需 architect/user 决定是否改写该条口径或登记为已知不可达；② I 侧 `all` 折叠到影子 RAM 窗口（代码只可能在 RAM 内被改写；pmem/hmon SRAM 的代码若经 DMA 更新，已由 RAM 写的自动失效兜底），无 I 阵列/几何；③ `cache_enable` D 位为 0 仍不旁路数据访存（沿用 `m16-qemu-002` 与 chipyard-017 口径，本任务只门控维护命令）；④ 正式用例留 `m16-testcases-009`。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：ctrl 判序与使能/模型解耦、`[15:14]` 位映射、三档范围匹配（含 56 位比较与 64 位加法饱和）、D 侧 clean/invalidate/flush 的写回与删除、遍历只及影子窗口（MMIO 天然 no-op）、I 侧 `tb_invalidate_phys_range` 的 ram_addr 换算与 `all` 折叠、两侧顺序、user-mode 编译支、证据脚本每条断言的可达 FAIL 与还原纪律。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 I 侧探针用 `rd20` 作 `call rbha`（应 RB 寄存器组）⇒ 目标算错、QEMU TIMEOUT | ✅已修 | `_call_code` 改用 `load_rb(20, pa)` | 修前 rc=None TIMEOUT，修后 `on_i_invalidate_refetch` PASS |
| F2 cache 维护代码落在 `CONFIG_USER_ONLY` 之外，而影子存储/`address_space_memory` 在系统支 ⇒ linux-user 编译失败 | ✅已修 | D 侧匹配/维护与新增 include 加 `#ifndef CONFIG_USER_ONLY`，user 模式给空桩 | 首次构建 error（implicit declaration）；guarded 后 `make build-qemu` 0 |
| F3 任务书指定的 I 侧注入不可达（QEMU 写 RAM 自动失效 TB；`-d in_asm` 重译计数在无命令时也为 2，不可判别） | ❌不修（机制限制）＋替代覆盖 | I 侧仍按 CACHE-19 调 `tb_invalidate_phys_range`；注入反例改为「I 侧误用 D 动作」；诊断日志落证据目录 | 注入「I 不失效」后 probe 仍 PASS（`inject-i-noop.log`）；「I 碰 D」⇒ rc=243 红 |
| F4 probe 失败恒返回 1 ⇒ 证据脚本无法断言红的具体用例 | ✅已修 | `probe.py` 透传 guest `SYS_EXIT` 码 | `--inject` 三路分别实测 rc=227/234/243 |
| F5 `run.sh` 的 `restore_src` 打印空路由名；注入锚点失败未判 | ✅已修 | 先存 `route` 再清 `INJ_ROUTE`；python 替换 rc 非 0 即判红并还原 | `--inject` 46/46，含 `restore … (cp + md5) md5 3bf64174 equal` |
| F6 `cpu.h` cfx5 行注释仍称 off 下 `CFXREG`，与 CACHE-27/现实现相反 | ✅已修 | 改为「两模型都存在、off 下 `cache_exist` 读 0」 | `check-patch-tree` 断言⑥ 通过、qemu 段 0 problem |
| F7 I 侧 `all` 只覆盖影子 RAM 窗口（未覆盖 SRAM 代码） | ❌不修（记录限制） | 无 | SRAM 代码更新必经 RAM 写，QEMU 已自动失效；证据未构造该场景，列遗留② |

**约束核验**：`git status -uall` = 2 补丁 + `README.md` + `changelog.md` + 本任务书（5 项）；组件源树干净、`base..HEAD` 恰 1 commit；未改 `spec/`、契约正文、`src/cpu/simple/**`、RTL/gem5、影子数据通路；未升版本号；未提交仓库 git；本记录与完成区无运行期具体路径；术语「寄存器组」。
**判决**：**待验收**（F1/F2/F4/F5/F6 已修；F3/F7 为机制限制并已记录，F3 有替代可达 FAIL 覆盖）。

### 第 2 轮 reviewer 验收

**重跑（仓库根执行运行期证据目录内的 `run.sh`，均本人输出）**：`run.sh` rc=0 `checks: PASS=26 FAIL=0 (cases=19, qemu_patches=69)`；`run.sh --inject` rc=0 `checks: PASS=46 FAIL=0`，三路注入 `probe rc=227/234/243`、`restore … md5 3bf64174 equal`、patches 树 `2f14b9a2` 不变、组件源树 `git status` 空；`min_rom_probe_integ042t.py --qemu <构建二进制>`（`DADAO_TEST_PROFILE=vast`）rc=0 `25/25`；`make_patch.py qemu` 0 且二跑幂等、`check-patch-tree` qemu `69 patch / 0 problem`、`check-knowledge-refs`/`check-dirs`/`check-no-residue`/`check-spec-refs`/`check-contracts-dir`/`check-manifests-guard` 均 0；helper.c 6 条 warning 全在 104/379/2520/2526/2805（非本次 2849–3140 段）⇒「新增代码 0 warning」成立。

**独立注入（`cp` 备份 + md5 对账，审前=审后 `3bf64174`；未用 `git checkout/restore/stash`；每路重建后复跑同一脚本）**：
- INJ-1 去掉 I 侧 `tb_invalidate_phys_range`（任务书指定那一路）⇒ **仍绿**：19/19 probe 全 PASS（`on_i_invalidate_refetch` rc=0）⇒ 遗留 1 判定属实；
- INJ-2 `RANGE_LINE` 恒真 ⇒ `on_d_start_56bit` **rc=236**、`run.sh` rc=1（`[FAIL] probe on_d_start_56bit`）；
- INJ-3 `invalidate` 不删行 ⇒ `on_d_invalidate_discards` **rc=228**（`on_d_flush_writeback_drops` 仍 0）；
- INJ-4 I 侧改跑 D `flush`（自选锚点）⇒ `on_i_leaves_d` **rc=243**；INJ-5 `clean` 不写回 ⇒ `on_d_clean_keeps_line` **rc=225**；
- 还原后 md5 相等、组件源树 `git status` 空、`run.sh` 回 26/26、`run.sh --inject` 回 46/46。

**I 侧不可观测判定：属实，不阻断。** 机制（本人核 QEMU 源）：TCG 下 `memory_region_get_dirty_log_mask()` 恒含 `DIRTY_MEMORY_CODE`，写 RAM 的 `address_space_write → write_memory_region → invalidate_and_set_dirty()` 必调 `tb_invalidate_phys_range()`；而影子里的新代码须先经 D clean/flush 写回 RAM 才对取指可见 ⇒ 该注入在可达路径上总被自动失效覆盖（INJ-1 实测绿）。

**应登记口径**：「QEMU 系统模式下 I 侧 `tb_invalidate_phys_range` 在功能模型上不可独立观测——凡使新代码对取指可见的写入（D clean/flush 写回、DMA、镜像装载）都经 `invalidate_and_set_dirty()` 自动失效 TB；I 侧按 CACHE-19 实现，由『取指重取』端到端例与『I 命令不碰 D』例（可达 FAIL rc=243）覆盖，『I 侧不调 tb invalidate ⇒ 旧指令红』登记为已知不可达。」

**附加发现（强于遗留 1，供 architect 定夺）**：INJ-5/INJ-6（`clean` 不写回 ± I 侧失效关闭）下 `on_i_invalidate_refetch` 仍 rc=0 ⇒ 该例 `I_REFETCH_2` 断言在本模型下**不判别**（数据先填 TLB 后取指由影子供给、TB 不复用），不能充当 I 侧失效的正向证据；I 侧唯一可达 FAIL 是 `on_i_leaves_d`（243）。建议与遗留 1 合并改写该条验证口径。

**约束核验**：审前/审后 `git status --porcelain -uall` 逐行相同且 = 完成区「修改文件（5）」，补丁 + README + changelog 4 文件 md5 与审前一致（本任务书仅由本轮审阅记录改写）；组件源树 `git status` 空，分支头仍为派单 commit `562dd4c5`（未提交 git）；diff 仅 `cache_ctrl` 维护实现 + 2 个 include + `cpu.h` 注释订正，未动 `spec/`、契约正文、RTL/gem5、影子数据通路，未升版本号；任务书无运行期路径，术语「寄存器组」；档位笔误（任务书「中改（复核 ≤40 min）」vs 派单大改 ≤60 min）记 finding。

**判决：Accepted**（遗留 1 不阻断；上述 finding 由 architect 收尾处理，不另开一轮）
