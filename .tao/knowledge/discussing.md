# 讨论项

> **组织方式（用户 2026-11-08）**：按 **M12 / M13 / M14** 三个里程碑分节；**不在这三个里程碑内**的事项集中到「三个里程碑之外」。
> 只记**当前未决/待裁定**与**仍然生效的口径**；任务流水看 `milestones.md`（M11 及以前）/ `milestones-m12.md`（M12 起），历史与已落地项见 `.tao/archive/`。

---

# M12：chipyard 上跑 `Machine-v5-Tiny` + 单周期 `dadao-wuming`

## 范围与编号（用户裁定）

- **三线 = 三个里程碑，分开进行**：`M12`（chipyard-tiny）/ `M13`（inst-golden）/ `M14`（linux-bootup）；**讨论清楚一个就开一个**，不并行开三个。
- **M12 测试范围**：只用 `inst`/`tset` 中**已被 qemu/gem5 验证过的子集**；**riscv-tests 移出 M12**，移植与调整放 M13。
- **任务编号**：`m12-<module>-<NNNN>`（模块小写，3–4 位序号，**无 k/t/m 后缀**）；M12 用独立台账 `milestones-m12.md`。
- **chipyard 构建/运行/调试全部在 `server207`**，串行；**所有对仓库的修改仍在主控机**（已写入 `AGENTS.md` 与 `nodes.md`）。
- **m 册门控取消**（用户选 B）：由 `m12-infra-002` 执行；M11 收口改用 `INTEG-061t` 核验（无 m 后缀）。
- **判据**：Tiny 阶段不涉及 syscall；测试判据 = 与 qemu/gem5 一致，**不用独立 oracle**。

## 机器命名定稿（用户裁定）

- **机器名**：`dadao-tiny` / **`dadao-vast`**（不再用 `dadao-m1`，也不再考虑 `dadao-node`/`mega`/`huge`）。
- **范围 B（一次到位）**：profile 概念同步改名 **Tiny / Vast**（`Machine-v5 §1`、`profile=tiny|vast`、`DADAO_TEST_PROFILE=tiny|vast`、qemu profile 字符串、contracts、docs）。
- **不改**：已 Accepted 的 ADR 原文（历史记录）、历史任务书、组件 changelog。
- **已授权**：`spec/Machine-v5` 的机器名/profile 改名 + 同笔更新只读锁；contracts 命令行示例同步。
- **排期**：改名波次**优先于** M11 的 `103t`/`104t`（避免 104t 二次返工，用户选 A）。

## 改名波次（5 任务，已立册 `待开始`）

| 任务 | 内容 | 预估 |
| --- | --- | --- |
| `m12-spec-001` | spec `Node`→`Vast`（约 22 处）+ 定位行机器名 + `0.4.1-rc` 段 + 锁；三份契约 + `spec/README` + `docs/Machine-00` | 1–2 h |
| `m12-qemu-001` | 拆 `dadao-tiny`/`dadao-vast`、去 `profile=`、**暂留 `dadao-m1` 别名** | 2–3 h |
| `m12-gem5-001` | gem5 FS `--profile vast`，**暂留 `node` 别名** | 0.5–1 h |
| `m12-testcases-001` | `machine-profiles.yaml`（`node`→`vast`）、`machine-vast.inc`、`DADAO_TEST_PROFILE`、46 个测试文件机器名、Makefile | 2–3 h |
| `m12-integ-001` | 删两处过渡别名；`-M dadao-m1` / `--profile node` 明确报错 | 0.5–1 h |

- **为什么留别名**：测试迁移尚未完成，中间提交必须保持 L1 绿；最后一步统一删。
- **顺序**：`spec-001` → `qemu-001` → `gem5-001` → `testcases-001` → `integ-001`。

## chipyard 实现方案（待用户确认拆分）

### `loadmem` 与 TSI 的关系（实测）

- **`+loadmem=<elf>` 是「预载捷径」**：chipyard 生成的 `SimDRAM.cc` 在 `memory_init` 里解析该参数，用 `load_elf()` 直接把 ELF 段写进 **backing memory**（其 `memif_t::write` 就是 `memcpy`）——**不经总线、不跑仿真**，零开销。
- **TSI 是「运行时通道」**：`SimTSI.v` 通过 DPI 调 `tsi_tick` → fesvr 的 `tsi_t`（32 位串行命令：READ=0/WRITE=1、2 字地址、2 字长度），程序跑起来之后供宿主**读写内存、代理 syscall**（htif `tohost/fromhost`）。
- **两者有交集**：`testchip_tsi.cc` 也解析 `+loadmem=`，置 `has_loadmem` ⇒ `is_loadmem` 时 memif 读写走 `load_mem_write/read`（绕开 TSI 的逐字写与 cache flush）；否则走 `tsi_t::write_chunk`。
- **对 M12 的含义**：不含 syscall 的 Tiny 测试用 `loadmem` 就够（`bss` 由 loader 零填）；TSI 只用于「guest 要请求宿主」的场景，属可选增强（原拟的 `012/013`）。

### semihosting 应答者：开发方式（建议）

- **分层**：应答者放 **harness 侧 C++**，与 qemu 的 `semihosting/arm-compat-semi.c`、gem5 的 `src/arch/dadao/semihosting.cc` **同层**；**核内不实现宿主 I/O**。
- **核内只做「抬到边界」**：命中 `trap <any cfxha>, 0x3FF00+op`（判定只依赖 `immu18[17:8]`）时，把 `(op, 参数寄存器, 返回寄存器号)` 通过一个可观测通道（导出端口或 MMIO）交给 harness；harness 执行宿主调用后把返回值写回 guest 返回寄存器（`§5.2` 的 `rd8`）。这与 FS/SE 无关、与 profile 无关。
- **最小集先行**：Tiny 阶段只需 `SYS_WRITEC(0x03)` / `SYS_WRITE0(0x04)` / `SYS_WRITE(0x05)` / `SYS_EXIT(0x18)` / `SYS_CLOCK(0x10)`；完整 25 服务按 `spec/Machine-v5 §5.3` 表后补。
- **不复用现成实现的原因**：qemu 共享层依赖 glib 与 qemu CPU 状态；gem5 那份依赖 gem5 `ThreadContext`；二者都无法直接链入 harness。可行做法是 harness 侧写一份 table-driven 的薄应答器（约 300 行），语义**从 spec §5.3 表派生**。
- **验证方式**：同一 ELF 在 qemu / gem5 / chipyard 三平台的 stdout 与退出码一致（M12 判据）；不写独立 oracle。
- **备选（不推荐首选）**：接 fesvr 的 syscall proxy（TSI 已具备）——但 fesvr 实现的是 RISC-V newlib syscall ABI，不是 Arm semihosting，需要一层映射，语义易漂。

### 实现任务拆分（待确认）

拟 11–13 个任务（`001` 骨架+`WumingTinyConfig` → `002` BootROM+loadmem 最小闭环 → `003` semihosting 应答者 → `004` 解码+整数 ALU+寄存器堆 → `005` 访存 → `006` 控制流+RAS → `007` 位操作与整数补齐 → `008` 浮点算术/比较/FMA → `009` 浮点转换/分类/特殊值 → `010` T0 冒烟（三平台比对）→ `011` T1 适配集+M12 验收 → `012` TSI 硬件端点 → `013` fesvr 接入+极简 htif 运行时）。

- **待用户确认**：粒度是否合适（FP 拆两个、TSI 拆两个）；`012/013` 是否真放 M12（也可挪 M13）。

## chipyard 定位与技术结论

- **用户原话**：「chipyard --help 的事情：我们没有必要去调试！！！我们不需要去测试 chipyard 本身，这只是我们要用的平台和工具」⇒ 撤销 `INFRA-136t/137t`（零源码改动），`INFRA-133t` 不再验证 `--help`。
- **`--help`/`+help`/无参数都崩溃的根因（已定，不再投入）**：`htif_t::parse_arguments`（fesvr）→ `htif_t` → `tsi_t` → `testchip_tsi_t` → `SimTSI.cc::tsi_tick()`（**首个时钟 tick 才构造**）→ Verilator `--main` 生成的 `main()`（**无 try/catch**）；`--help` 为 `User queried htif_t help text`，无参数为 `No binary specified`，rc=255。属**上游行为**，非环境偏离（chipyard `0acc1e1` clean、testchipip 与 riscv-isa-sim 均为锁定态、Verilator 5.022 符合 conda-reqs）。
- **命名/补丁方式（用户裁定）**：按**实现**分类——`dadao-wuming`（单周期）/ `dadao-wuqing`（五周期）/ `dadao-wuxing`（超标量），每种实现内部再按 Tiny / Vast 做测试配置；**补丁方式 A**（全部进 chipyard 补丁集，newfiles 也写成补丁）。
- **参考实现**：`.cache/refs/DADAO/SOC-chipyard/`（`chipyard-0111-newfiles/generators/dadao-wuming` + 5 个接线补丁 + `chipyard.mk`）；riscv-sodor 为第二参考；PR #4 仅参考。

## M12 未决

- 实现任务拆分与 `012/013` 归属（见上）。
- Tiny 的 SRAM 基址与 `loadmem` 目标窗口需在 `002` 定稿（`load_elf` 目标基址必须与 Tiny 地址图一致）。

---

# M13：三平台差分对齐（qemu / gem5 / chipyard，含浮点）

## 范围

- **三平台差分**：qemu / gem5 / chipyard 的**指令语义**对齐，**尤其是浮点**语义。
- **riscv-tests**：移植与调整在 M13 完成（M12 不用）。
- 判据仍是「实现之间一致 + 与 spec 逐条核对」；**不允许把「两个实现一致」当正确**（多数表决 ≠ 真值）。

## golden / Sail 定位（结论，待落流程）

- **前提**：SimRISC/DADAO 持续变更、不留历史包袱；内核/FPGA 阶段同样如此。工具按「高频变更」取舍，不按「稳定期资产」取舍。
- **Sail：搁置**。形式化模型是稳定期资产；0628 实测只做 6–8 条切片、其余 `SKIP-unsupported`；「权威性」在自有扩展上不成立。重启触发条件：ISA 冻结 / 流片前 / 需要 RTL tandem 或定理证明。
- **golden：不做全量第四实现**。只保留三个窄用途：① 歧义探测（未明处 `SpecificationGap`/`UNSPECIFIED` 显式阻断，不猜默认值）；② 精确计算（FP/位宽/舍入）；③ 裁定回归（把用户裁定固化成向量/断言，防漂移）。PR#5 的全量模型 + 万行 `INSTRUCTION_REFERENCE.md` 属稳定期资产，不并入日常门控。
- **裁判只能是用户**：工具只做「发现歧义 + 举证（各解释下的结果/依据）+ 回归」，不做拍板；差分/fuzz 的分歧须聚类归因后再上报，不把原始分歧直接丢给用户。
- **投资顺序**：规范一致性/歧义探测 > 差分 fuzz + legality 矩阵 > 精确 FP > 轻量边界生成；解释器只在「需要算给看」时写。
- **三条禁忌**：向量里写未记录来源的期望值；模型对未明处选默认值；把「两个实现一致」当正确。
- **依据（0628 / PR#5）**：0628 四方差分（interp/QEMU/gem5/Sail）AGREE 198 / DIVERGE 0，`check-golden` 故意不进 `make check`；golden 仅整数 87 条，语义取自 `spec.md`（与 ADR-0009「wiki 直派」的要求不一致）。PR#5：标量 + 66 条 FP，回放 730（173/500/0/57），49 单测，`check-golden` 进 L1；无差分运行器，FP 向量只有 `scaleb`。
- **待落地**：① 「歧义登记 → 用户裁定 → ADR/向量 → 回归」的流程；② 是否把「歧义探测」并入现有 spec 门控；③ chipyard 是否已有 DADAO 核（决定 RTL 对拍是否成为主差分）。

## M13 未决

- 差分矩阵的判据、参与引擎、失败归因口径（启动 M13 时专门讨论）。

---

# M14：Linux bring-up

> 2026-11-01 用户裁定：Linux 开发延至 M12 或后续；**现定为 M14**（三线分开进行）。此前方向沿用。

## 已确认方向（2026-11-01，用户逐条确认）

- **模块归属**：新建 `linux` 模块，任务前缀 `LINUX-`；目录 `.tao/tasks/linux/`。
- **内核基线**：Linux **7.2.10**，commit `7b20d05f…`；不采用 5.4。
- **平台**：恢复时只做 QEMU system 模式，单核；**不纳入 gem5**。
- **MVP**：内核日志 → built-in initramfs 的静态 `/init` → 至少一次 Linux 系统调用往返；不要求 login/shell。
- **控制台**：**semihosting** 负责控制台输出与测试退出闭环；**不引入 UART**，不新增 cfx。
- **initramfs**：先放静态 musl 自定义 init（write/getpid/brk + 错误路径），**busybox 到 K4 之后再决定**。
- **TLB**：当前**没有规范定义**（DDLN 只是讲义，不是规范）；K3 先定义 fill/invalidate/ASID/fault 语义，再实现；K0 不定义。
- **cache/LLC**：该阶段不引入，留到后续。
- **0628**：只参考阶段划分、踩坑和测试思路；不复制 `arch/dadao`、补丁或实现代码。

## 补丁策略（待 K0 落任务书）

- 当前 `manifests/components.lock.toml` 的 `linux` 条目是 `patchless = true`，角色仅为 syscall 号表参考。
- 恢复时复用同一 7.2.10 commit，转为受补丁组件：`patch_dir = components/linux/patches`、`patch_series = components/linux/series`，角色改为「Linux 内核移植目标 + syscall 参考」。
- 按 `docs/Process-01`：干净 git 基线；一文件一补丁；新增 `arch/dadao/**` 也用 `new file mode` 补丁；`make apply-series` + `check-source-state`。
- 不直接改源树作为真源，不复制 0628 的补丁集。

## 阶段与任务量（K0 后校准）

- K0 基线与契约：5–7 个任务（补丁组件、工具链缺口、启动 ABI、syscall/errno/TLS、initramfs/semihosting、门控）。
- K1 启动与控制台：4–6 个。
- K2 异常与时间：5–7 个。
- K3 内存与 TLB：6–8 个（含 TLB 规范定义）。
- K4 进程与上下文：5–7 个。
- K5 用户态闭环：5–7 个。
- 合计约 30–42 个任务；收口只到 K5，busybox/UART/cache/LLC/gem5 等不阻塞。

## K0 兼容性缺口（待矩阵化）

- 缺口：`arch/dadao`、`llvm-ar/ranlib/strip`、`asm goto` 输出、栈保护、`.quad/.long/.short/.byte`、inline asm 约束、`-mcmodel=kernel`。
- 入口判据：spike 清单归零或有规避法 + 工具链就位 + `arch/dadao` 最小骨架能 `make ARCH=dadao` 出 vmlinux。
- 详细兼容性记录 K0 落任务书/矩阵后移入对应文档。

## 待办

- Linux 启动前：立定义与 K0 任务书（`linux` 模块）；拟议 ADR 的 decision 逐条确认。
- K0 前不写内核代码；先冻结补丁策略、启动 ABI、工具链缺口和测试门控。

## 待裁定 ADR：Linux bring-up charter（未落文件）

- **状态**：方向已确认；ADR decision 文本待逐条确认（尚未落 ADR 文件）。
- 已确认方向见上（7.2.10、单核 QEMU MVP、semihosting、不引入 UART/cache/LLC、TLB 在 K3、busybox 后置、0628 只参考）。
- **下一步**：把上述方向写成 D1–D7，逐条确认后再落正式 ADR。

---

# 三个里程碑之外

## M11 收尾（未完成）

### 剩余任务

- `TESTCASES-103t`（3–4 h）：SE 基线预算 120s→按套件 600s，`timeout` 单列并重跑。
- `TESTCASES-104t`（5–8 h）：SE 动态档驱动 + QEMU dynamic 基线刷新 + 全量对照。
- `INTEG-059t`（10–16 h）：G3 完整 tset 双向一致性（static+dynamic）+ 矩阵重生成。
- `INTEG-061t`（2–3 h）：**M11 里程碑核验与归档**（无 m 后缀；查任务状态 + 按 `docs/Process-04` 归档）。依赖以上三件。

### 仍然生效的口径

- **执行顺序**：改名波次优先于 `103t`/`104t`（用户 2026-11-08 选 A）。
- **QEMU/gem5 一致性方向**：QEMU 已实现的 syscall，gem5 必须有等价实现；差异不是「可接受限制」；gem5 通过而 QEMU 未通过不得直接接受，须定位到一致。
- **环境缺口（2026-11-07 裁定）**：`popen`/`spawn`/`vfork`/`execle-env`/`unix-smail` 5 例需要 guest 根内的 DADAO `/bin/sh`、`echo`；SE 返回 `ENOEXEC` 正确。QEMU 侧「通过」是执行宿主 x86-64 二进制，**非同架构 baseline**，不计 gem5 能力欠账；不采纳宿主原生执行旁路。
- **动态线范围**：`mprotect` 真权限不纳入（另立任务）；主程序 `-pie`/`ET_DYN` 不支持，用非 PIE `ET_EXEC+PT_INTERP`；语料按 `ADR-0048 D4` 全量（libc-test 337 + llvm-ts 214 + embench 38）；单线程 TLS 由 musl 完成、gem5 0 改动。
- **picolibc `math_test` 已知 BLOCKED**：Tiny 在 gem5 上 `238/76404 errors`（QEMU 0 errors），归因 B7 浮点数值差异；报告须保留 blocked 计数，不得计 PASS；修复另立差分任务（M13）。
- **退出码定稿**：guest `0x00–0x3F` = PASS、`0x40–0x7F` = FAIL；机器 fault `0xC0–0xFF` = monitor（`bit7=1,bit6=1,bit5:4=模式,bit3:0=DADAO 异常位索引`）、`0x80–0xBF` = 其它 cfx（`bit7=1,bit6=0,bit5:0=cfxHA`）；`PTWERR`/`unmapped`/旧 `0x84`/`0xE1` 已删。
- **`SYS_TICKFREQ`**：统一 `1e9` ticks/秒，QEMU/gem5 同模式一致（spec 未定义具体值，暂按此对照）。
- **m 册门控取消**（用户选 B）：M11 不建 `m` 册，`make check-milestone` 报「无 m 册」属预期；改由 `INTEG-061t` 核验。`check_milestone_tasks.py` 的处置归 `m12-infra-002`。

### M11 历史裁定（仍有效）

- **1B**：M11 按「含实现」收口；5 个屏蔽寄存器实现 + 退出码实现完成才算完成。
- **2B**：实现拆 2 个 INTEG 任务（`INTEG-054t` 5 寄存器、`INTEG-055t` 退出码），各含 QEMU→gem5→tests 三阶段。
- **批次授权（2026-11-01）**：M11 gem5 批次 B0 + B1–B7 + `SPEC-181t`；批次内可直接建任务书/派单/验证/合并，不逐任务确认；停止点 = 批次外新任务、新增或改变 SPEC/契约语义、跨模块修改、push、破坏性/硬件操作、验收标准变更。
- **`convert_f2i` 定稿**：`ADR-0050` Accepted（D1–D7）；15 条六档 one-hot / 3 条 SBZ / 4 条复制计数；汇编层 18 条单寄存器、无花括号、第三操作数显式。版本保持 `0.5.6-rc（未发布）`，M11 收口时再决定是否去 `-rc`。
- **`AT_UID/EUID/GID/EGID` 口径（2026-11-08，用户选 A）**：gem5 SE 取 `::getuid()/geteuid()/getgid()/getegid()`，与 `getuid` syscall 同源；探针改跨引擎逐值相等。
- **M11 收口旧记录**：`make check-full` 曾 PASS 8/8、`check-night` 4/4；`TESTCASES-100t` 修正 `malloc-brk-fail`；`ISS-343`（QEMU guest rlimit no-op，P3）仍开。

## 待用户裁定：ADR

### `SPEC-180t` 的 ADR

- 状态：待用户裁定。
- 结论：escape 合法偏移集 `{0,+4}` + `imms18[17:1]` SBZ ⇒ ILLI，按 `docs/Process-03` 命中外部契约变更/多方案/结论固化。
- 下一步：逐条确认 decision 后再立 ADR；未确认前只保留为遗留。

### ADR 状态（其余）

- `ADR-0043`/`0045`：已 `Accepted`。
- `ADR-0046`：仍 `Proposed`，等 Linux 实测后再收口。
- 不再改 0043/0045 的 decision；0046 保持 `Proposed`。

## 架构未决项

### cfx 范围（M10 后）

- 已实现：umon/jmon/smon/hmon/ptw/pmem/time/hart/power。
- 后置：cache/llc/uart、PMEM 区域分配、IPI、多 hart。
- 下一步：按 Linux 需求拆任务（M14 启动时）。

### U-mode / cg5 / 异步帧

- 状态：待讨论。
- 结论：U-mode 的 cfx 目标不设 ISA 限制，由 OS 策略决定；cg5 单帧、同步/异步分离、递归/重入尚未定。
- 下一步：等 cg7 与 escape 收口后再讨论。

### SBI 生产 provider / W1C

- 状态：后置。
- 结论：当前只有测试专用 provider；生产 provider、`DONE/ERROR` W1C、`WAIT` 属 Linux 集成阶段。
- 下一步：不在 M10/M11 通路内实现。

### CFX 审计保留的未决项

- IPI：只有接收端，没有发送服务/寄存器。
- TLB：当前**无规范定义**（此前实现只覆盖 invalid，没有 fill）；按 Linux K3 先定义再实现。
- `cfx_pmem_exist`：SEE 与 SBI 语义不一致。
- UART：实例号/索引语义未定义（Linux 阶段暂缓）。
- 下一步：确认哪些进入 Linux 前任务；不恢复已删除的审计文件。

### `TESTCASES-089t` 遗留

- `reserved.yaml` 是否拆册（当前同册承载「保留编码 ⇒ UNDI」与「reserved cfx 地址空间 ⇒ CFXMEM」两类语义）。
- `trap`/`escape` → reserved cfx 的 active 向量仍 deferred（`TESTCASES-033t`）。

### 异常/中断入口模型（已定 A）

- **执行过程中的同步异常和异步中断，先进入当前运行模式的 monitor**；monitor 是**第一处理者**（拥有异步来源屏蔽、pending、分发决策；可自行 `escape`，也可 `trap` 到源 cfx；处理期间的新事件置 pending，不嵌套 monitor）。
- 显式指令仍直接到 cfx：`trap cfx` → 目标 cfx（`CFXTRAP`）；`escape cfx` → 当前 cfx（`CFXESC`）。
- 第 3 项选 **A1**：删除 `inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask`/`excp_cause_mask`/`excp_cause_nonmaskable`；编号保留为 reserved，不重排；monitor 用 `cfx_intr_mask` + `excp_pending`；`global_cfx_intr_mask` 保留。
- 落点：`SPEC-186t`（§5.2+§1）→ `SPEC-188t`（寄存器定义删除）→ `SPEC-189t`（§2.2.6/§3.6/§4.5 + `DADAO-22 §5.3` + `contract-see`）→ `SPEC-187t`（退出码）；188t/189t 同改 `DADAO-12`，严格串行。

## 基础设施与规则

### `/tmp` 改回磁盘（推迟，用户自理）

- 现状：主控机 `/tmp` 由 `/etc/fstab` 配成 16G tmpfs；节点 `/tmp` 已在 ext4 磁盘上。
- 用户决定改回磁盘，**推迟到明天，由用户自行找时间执行**；`sudo` 由用户操作。
- **不要再主动提醒重启**；切换前置 = `/tmp/opencode` 下无活动 worktree（届时由主会话清理/迁移）。

### 两台构建节点

- 两台 64C/128G 节点已完成引导（软件包、仓库同步、`fetch` → `apply-series` → `install-host`），工具链与主控机同版本；chipyard/Verilator（5.022）/openjdk 20/riscv gcc 13.2/firtool 1.75 就绪，`RocketConfig` 构建通过。
- 就绪验证：`make check`（L1）两机均 rc=0（各约 64s）；`make check-inst` 两机均 rc=0（44/44、载体 23 册），结果行逐字一致 ⇒ 可作确定性对比基线。
- **节点只承担 chipyard 的构建/运行/调试**；仓库修改只在主控机；**冲突必须串行**。
- **与节点交互的中转文件禁止放 `/tmp`**（tmpfs 耗光会断任务链）：主控机侧放 `.work/`，节点侧放仓库内或家目录持久路径。

### 并发与派单纪律

- **同一组件同一时刻只允许一个写者**；共享 `.work` 的任务必须串行。
- 历史事故（2026-11-07）：另一会话自行派 `GEM5-027t` 并开始 `make build-gem5`，与本会话共用 gem5 源树 ⇒ 中断该子会话、终止构建、删其 clean worktree。
- **收到「完成」通知先核盘上事实**（`git log` / `*.EXIT` / 任务书状态），再续链。

### `check-knowledge-refs` 判据（用户裁定 A）

- **具体 `.work/**` 引用一律 FAIL**，不看本机是否存在（fresh clone 不可复现；主控机会假绿）。
- 空转判据：`found == 0`（没有任何 `.work/**` 引用）才判空转失败。
- `<>`/`*`/`$` 形与以 `-` 结尾的前缀截断引用不可判定 ⇒ 跳过；`.work/build/**`、`.work/source/**` 显式豁免。
- 被引用的材料须改为运行期措辞，或升格到 `.tao/knowledge/refs/`。

### 已处置教训：脚本假绿（2026-11-07）

- `INFRA-130t` 验收全绿，但真实节点第一次 `remote.py status` 报 rc=0 PASS 而仓库根本没进去。
- 根因：`cd <repo> && <多行脚本>` 中换行等价 `;`，`&&` 只护住首行；叠加 `shlex.quote("~/x")` 使 `~` 不展开。
- 处置：`INFRA-131t` 修 cd 语义、`~/` 展开与 rc 传播；要求**每个前置步骤都要有可达 FAIL 断言**。

### QEMU `SS_AUTODISARM` 补丁（已批准保留）

- `GEM5-029t` 为使 QEMU 与 Linux 一致，改了 `components/qemu/linux-user/{signal.c,dadao/signal.c}`；用户「同意」保留，属「给 QEMU 补 Linux 已有语义」，不改变对照方向。

## 现行约定（非讨论项）

- 任务流水体例由 `make check-milestones-fresh` 机械校验（状态一致 / 覆盖 / ≤120 字符 / 倒序 / 格式），不在本文复述。
- 双台账：M11 及以前 → `milestones.md`；M12 起 → `milestones-m12.md`（按任务书 `**项目里程碑**` 路由）。
