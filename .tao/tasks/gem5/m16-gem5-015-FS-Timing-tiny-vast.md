# m16-gem5-015: gem5 FS + Timing（tiny 与 vast 两种机型）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-006`（Timing 访存 + `--wuming-cycles`）、`m16-gem5-014`（Vast TLB）
**可并行分片**：否
**预估**：2–4 天
**档位**：大改
**状态**：待验收

## 背景（用户 2026-11-19 裁定）

「**`gem5` 的 `TimingSimpleCPU` 也要做 Vast**」。现状：

- `fs.py`（FS）**只有 Atomic**：`tiny → DadaoFsAtomicSimpleCPU`、`vast → DadaoNodeAtomicSimpleCPU`；
- `se_timing.py`（SE）才有 `DadaoTimingSimpleCPU`（`m16-gem5-006` 交付，含 `NoncoherentXBar` + `SimpleMemory` + `--wuming-cycles`）。

⇒ 缺的是 **FS 模式的 Timing 变体**，且要**两种机型都能跑**（Tiny 与 Vast 共用一套机制，几何由 profile 决定）。

## 目标

1. **在 `configs/dadao/fs.py` 上加 `--cpu-type {atomic,timing}`**（默认 `atomic` 保持现状）——**不新建 `fs_timing.py`**（用户 2026-11-19 裁定：按模式命名 + CPU 类型参数化，与 gem5 上游 `--cpu-type` 惯例一致）；`timing` 分支用 `DadaoTimingSimpleCPU` + `NoncoherentXBar` + `SimpleMemory`；
2. **`translateTiming` 落地**：`fs_tlb.cc`（Tiny）与 `node_tlb.cc`（Vast）现在的 `translateTiming` 是 **stub/未实现**（忽略 `translation` 参数）；需按各 TLB 的解析逻辑实现，使 timed 访问能正确翻译并回填；
3. **`--wuming-cycles` 在 FS 下仍生效**（逐指令延迟钩子是 arch 侧，与 SE/FS 无关，确认即可）；
4. **Vast 的 TLB/PTW 时序口径**：若 TLB miss 的走查代价暂时不建模，必须在文件头**显式声明**（「PTW 走查按 0 延迟，由周期表另行记账」），并给出后续接入点；
5. **数据侧访存的既有折衷沿用**：`m16-gem5-006` 已声明「DADAO 执行核同步读内存 ⇒ 数据侧 functional、ld/st 由周期模型记账」；FS 侧同样处理，并在文档写清。

## 验收

1. `make build-gem5` rc=0；**Tiny**：`fs_timing.py --profile tiny` 跑 `tests/inst` 首册 + 至少一条 `k0` 镜像，退出码与 Atomic 一致；
2. **Vast**：`fs_timing.py --profile vast` 跑既有 Vast 冒烟（`run_m5_e2e.py --profile vast`），功能与 Atomic 一致；
3. **周期一致性**：同一 ELF 在 `fs_timing --profile tiny` 与 `se_timing` 下，**逐指令拍数一致**（同一 `--wuming-cycles` 表）；
4. **可达 FAIL**：把 `translateTiming` 改回 stub ⇒ 用例红（`cp`+md5 还原 + 重建）；
5. 不回归：`fs.py`（Atomic）与 `se_timing.py` 行为不变；`check-gem5-decode`/`check-index-blobs`/`check-patch-tree`（gem5 段）rc=0；合并态（`Process-07 §5a`）。

## 待裁定

- **PTW 走查的延迟**是否要建模（现在是 atomic/0）；若建模，需要先定「TLB miss 的拍数来源」（实测还是估算）——建议**先按 0 延迟并在文档声明**，等 RTL 实测再回填。

## 完成区

**测试结果**：证据脚本 14/14 检查全绿；`--inject` 3 路注入 21/21 全绿（各转红 + `cp`+md5 还原 + 重建回绿）；
合并态（master `55109817`）下重跑全绿。门控：`check-gem5-decode` rc=0、`check-index-blobs` rc=0、`check-patch-tree` gem5 段 **0 problem**（全仓 8 problem 全在 chipyard，属并行任务在途）。

**修改文件**（仓库侧）：
- `components/gem5/patches/configs/dadao/fs.py.patch`、`.../src/arch/dadao/{fs_tlb.cc,node_tlb.cc,inst.cc}.patch`、`.../decode/{decode_table,decode_assertions}.inc.patch`（`make_patch.py gem5` 重导出，107 份、0 written 幂等）
- `components/gem5/README.md`（FS 构成 + `--cpu-type` + 两项时序口径）、`components/gem5/changelog.md`
- `tests/ee-tiny/run_inst_tiny.py`（新增 `--gem5-args`）、`tools/testcases/parity/qemu_gem5_shim.py`（新增 `PARITY_GEM5_ARGS`）
- 组件源码树：1 个提交（`c8222cc + 1`），工作树干净

**验收结果**（`bash <运行期证据目录>/run.sh` 与 `--inject`）
1. `make build-gem5` rc=0；**Tiny**：`tests/inst` 01 册 **38/38** 镜像通过（`fs.py --cpu-type timing --profile tiny`），`--cpu-type atomic` 同册亦 38/38；k0 镜像两模型 `rc=125 / cause="a thread reached the max instruction count"` 一致、均到达内核入口 `0x10_0000`、折叠延时环后的 PC 序列一方为另一方前缀（2999 vs 3183 步）。
2. **Vast**：`run_m5_e2e.py --profile vast` 经 shim 打到 `fs.py --cpu-type timing` **10/10**，atomic 同批亦 10/10。
3. **周期一致性**：同一 ELF（`tiny_smoke.elf`）在 FS tiny 与 `se_timing` 下，**逐指令** `(cyc_on−cyc_off)` 步差 **40/40 条完全相同**（隔离了 126 条 BootROM 前缀，前缀数由两次运行指令数现场相减得出）；模型总贡献 51 拍 > 0（钩子确实在计费）。
4. **可达 FAIL**：`fs_tlb.cc` 与 `node_tlb.cc` 的 `translateTiming` 改回 `finish(NoFault,…)` stub ⇒ tiny 侧 `rc=-6`（取指按 paddr 0 走，内存系统终止）、vast 侧 `rc=125`（非 guest 退出、无 `-d cpu` 块）；`inst.cc` 的 FS functional 分支关掉 ⇒ tiny `rc=-6`（旧 SE 代理在 FS 下 `did not translate` panic）；三路均 `cp`+md5 还原、重建后回绿。
5. 不回归：`fs.py` atomic 路径 38/38 与 10/10 不变（几何 dump 两模型逐行相同）；`se_timing` 仍到同一 guest 退出；上述三门控 rc=0；合并态重跑全绿。

**新发现/坑**：
- **任务前提有误**：`fs_tlb.cc`/`node_tlb.cc` 的 `translateTiming` 在 HEAD 上**已经是** `translation->finish(translate(...))`（不是忽略 `translation` 的 stub）；本任务实际缺的是**FS 下的数据侧功能访问**——原 `SETranslatingPortProxy` 在 FS 上把首个数据访问变成 panic（`did not translate`），已由 `functionalFsAccess()` 修好。注入证据表明两条 `translateTiming` 仍是承重路径（改回 stub 即红）。
- `check_tiny_hmon` **既有红**：33/201，`expected.yaml` 仍是子原因编码（`CFXMEM|Sub…`）之前的口径；用 HEAD 原版 `fs.py` 跑同样 33/201，与本任务无关。
- gem5 启动时 `--cpu-type timing` 的访存延迟**必须**有来源（`--cycle-table` / `DADAO_WUMING_CYCLE_TABLE` / 三个显式值）；shim 与 tiny 驱动都只认 `--gem5-config`，故给两者各加一个转发口（`PARITY_GEM5_ARGS` / `--gem5-args`）。
- k0 镜像在 gem5 FS 下**跑不完全程**（atomic 与 timing 都一样）：镜像落到 hmon 后卡在 `hmon_dma_poll`（DMA 完成按模拟时间推进，两种 CPU 每拍推进的指令数不同）⇒ k0 判据按「同退出因 + 同架构序列（折叠连续重复 PC）」比，不按指令数对齐。
- 与 `m16-gem5-017` 的接口：`fs.py` 按**文件存在性**从 `se_timing.py`（现在）或 `se.py`（017 之后）取 `DadaoTimingSimpleCPU`/`read_memory_system`，两种顺序都不会断。

**遗留问题**：
- **decode 表漂移已连带修正，需架构师确认归属**：`decode_{table,assertions}.inc` 在 HEAD 落后于当前 `contracts/`（上次导出后 contracts 前进），不修则 `check-gem5-decode` 与 `check-patch-tree` 的 E6 基线必红。本任务用 `tools/gem5/gen_decode_table.py` **机械重生成**（幂等，md5 不变）并纳入本任务提交；若该漂移另有归属任务，请拆出。
- `fs_tlb.cc`/`node_tlb.cc` 的 PTW 走查仍是 **0 延迟**（按任务书「先按 0 延迟并声明」）；建模时在 `translateTiming` 内把 `finish` 改为按走查延迟调度，拍数待 RTL 实测回填。

## 审阅记录

### 第 1 轮 engineer 自审

范围：`configs/dadao/fs.py`（`--cpu-type` 分支、几何复用、退出路径抽取）、`src/arch/dadao/inst.cc`（`functionalFsAccess`）、`fs_tlb.cc`/`node_tlb.cc`（注释与接入点）、两份测试驱动的小改动、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. `translateTiming` 在 HEAD 已是实现，任务前提不成立（若照抄「实现它」会交空活） | ✅已修（改落点+披露） | 保留两处为接入点注释，把实际缺口（FS 数据侧功能访问）补上 | 注入 I1/I2 转红证明承重；完成区显式披露 |
| 2. 原 `inst.cc` 在 FS+timing 下用 `SETranslatingPortProxy` ⇒ 首个数据访问 panic（`did not translate`），并**丢掉 guest 故障语义** | ✅已修 | 新增 `functionalFsAccess()`：先 `translateFunctional` 取 fault（与 atomic 同源），再走 `system.physProxy`；SE 路径不动 | tiny 01 册 38/38（含 197 个故障链例）、vast 10/10；注入 I3 转红 |
| 3. 新配置若另建文件会与 `fs.py` 几何两处维护（漂移风险） | ✅已修 | 按用户裁定改为 `fs.py --cpu-type`，几何/CLI/退出路径单点 | 几何 dump 两模型逐行相同 |
| 4. 证据脚本 C4/C5 一度 `rc=75`（并行任务占 gem5 写者锁），会把调度冲突报成失败 | ✅已修 | `run_with_retry()`：仅对 `rc=75` 重试，且逐次打印 | 复跑 C4/C5 转绿 |
| 5. 注入「转红」曾把**用法错误**当反例（`--id` 被塞进 `--gem5-args`） | ✅已修 | 拆分 `driver`/`gem5_extra` 两个参数；`usage_error()` 扫描日志拒收用法错误 | I1/I3 红因变为模型终止（`rc=-6`），绿回正常 |
| 6. `fs.py` 的 `se_timing` 导入用 `try/except ImportError` 会吞掉真实导入错误 | ✅已修 | 改按 `se_timing.py` 是否存在选择模块 | `--cpu-type timing` 正常起跑 |
| 7. 功能访问按「一次翻译 + 一次 blob」实现，须证明不会跨页 | ✅已修（加断言性说明） | 注释写明「元素 ≤8 B 且自然对齐 ⇒ 不跨 64 KiB 页」（`b1.cc` 先判 MALIGN 再访存） | 代码阅读 + 38/38 含宽度/对齐例 |
| 8. `--cpu-type timing` 缺延迟来源时抛 Python traceback（gem5 对 `sys.exit(str)` 会二次崩） | ✅已修 | 捕获 `OSError`，`stderr` 打印指引后 `exit(2)` | `--cycle-table /nonexistent.yaml` 得到两行指引、非零退出 |
| 9. `--dump-mem`/`--dump-semihost-services` 在退出路径重构后可能失效 | ✅已修（验证） | 无需改动 | 两者均实测可用（16 B dump 落盘、服务表 1 行） |

**判决**：9 条 finding 全部已修并复验；证据脚本 14/14 与 `--inject` 21/21 全绿，门控与合并态全绿 ⇒ 可标「待验收」。

