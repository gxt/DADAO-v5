# 讨论项

> **组织方式（用户 2026-11-08）**：按里程碑分节，**M12 / M13 / M14** 各为一级标题，M11 已归档（其仍有效的口径见「跨期口径」）；**不在这些里程碑内**的事项集中到「三个里程碑之外」。
> 只记**当前未决/待裁定**与**仍然生效的口径**；任务流水看 `milestones.md`（M11 及以前）/ `milestones-m12.md`（M12 起），历史与已落地项见 `.tao/archive/`。

---

# 跨期口径（M11 收口后仍有效，M12/M13 共用）

> M11 已于 2026-11-09 归档（`.tao/archive/M11/`，114 册）；其任务与历史裁定不再在此保留。

- **QEMU/gem5 一致性方向**：QEMU 已实现的 syscall，gem5 必须有等价实现；差异不是「可接受限制」；gem5 通过而 QEMU 未通过不得直接接受，须定位到一致。
- **环境缺口（5 例）**：`popen`/`spawn`/`vfork`/`execle-env`/`unix-smail` 需要 guest 根内的 DADAO `/bin/sh`、`echo`；SE 返回 `ENOEXEC` 正确。QEMU 侧「通过」是执行宿主 x86-64 二进制，**非同架构 baseline**，不计 gem5 能力欠账；不采纳宿主原生执行旁路。
- **SE 动态线边界**：`mprotect` 真权限不建模；主程序 `-pie`/`ET_DYN` 不支持（用非 PIE `ET_EXEC+PT_INTERP`）；语料按 `ADR-0048 D4` 全量；单线程 TLS 由 musl 完成。
- **`SYS_TICKFREQ`**：统一 `1e9` ticks/秒（spec 未定义具体值，暂按此对照；M13 差分时可固化）。
- **`SYS_chmod` 不新增号段**：`chmod()` 经 musl 走 `fchmodat`，不虚构 ABI 号。
- **输出捕获的 stdout/stderr 顺序（`ISS-357`）**：至少 4 例受影响，修复必须保留 fd1/fd2 写序，不能只交换拼接方向。

# M12：chipyard 上跑 `Machine-v5-Tiny` + 单周期 `dadao-wuming`

## 范围与编号（用户裁定）

- **三线 = 三个里程碑，分开进行**：`M12`（chipyard-tiny）/ `M13`（inst-golden）/ `M14`（linux-bootup）；**讨论清楚一个就开一个**，不并行开三个。
- **M12 测试范围**：只用 `inst`/`tset` 中**已被 qemu/gem5 验证过的子集**；**riscv-tests 移出 M12**，移植与调整放 M13。
- **任务编号**：`m12-<module>-<NNNN>`（模块小写，3–4 位序号，**无 k/t/m 后缀**）；M12 用独立台账 `milestones-m12.md`。
- **chipyard 构建/运行/调试全部在 `server207`**，串行；**所有对仓库的修改仍在主控机**（已写入 `AGENTS.md` 与 `nodes.md`）。
- **m 册门控取消**（用户选 B）：由 `m12-infra-002` 执行；M11 收口改用 `INTEG-061t` 核验（无 m 后缀）。
- **判据**：Tiny 阶段不涉及 syscall；测试判据 = 与 qemu/gem5 一致，**不用独立 oracle**。
- **rocket 边界 = A（用户 2026-11-08）**：抛开 **Rocket 核**与 RISC-V 语义（CSR/misa/PMP/MMU/TLB/异常码），**保留** rocket-chip 库（Diplomacy / TileLink / `BaseTile`）与 chipyard 仿真基础设施（Verilator harness / BootROM / 内存模型 / `loadmem`）；核完全自研，只挂在 TL 上。
- **`dadao-wuming` 外壳 = B（用户 2026-11-08）**：自写最小 Tile（只用 `BaseTile` 接口 + 自己声明 TL 端口），**不继承 `CoreParams`** 的 RISC-V 语义（misa/PMP/mtvec/断点/异常码）；参考实现虽走 `BaseTile + CoreParams`，但本仓库不沿用其语义壳。

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

### 实现任务拆分（用户 2026-11-08 裁定）

**范围收缩**：Tiny 只用 `loadmem` 预载；**TSI 不在 M12 实现**；**M12 不考虑 fesvr/pk**；semihosting 应答者在 **harness 侧**（`003`）。

拟 14 个任务（正式编号 `m12-chipyard-001`…`014`），每件 ≤2–3 h：

- `001` 骨架 + `build.sbt` + `WumingTinyConfig`（接线 + 编译）✅
- `002` Tiny 地址图落地（48 位核内地址）✅
- `003` BootROM + `loadmem` 最小闭环 ✅
- `004` harness 侧 semihosting 应答者 ✅
- `005` 解码器 + 整数 ALU + 寄存器堆（进行中）
- `006` 多周期状态机设计分析（**待用户裁定**：逐类指令周期 + 状态机推荐方案）
- `007`–`016` 已全部立册（访存含 `ldm`/`stm` / 控制流 / 位·原子·杂项 / FP 五组 / T0 / T1）
- `002` BootROM + `loadmem` 最小闭环（Tiny SRAM 基址与 `load_elf` 目标窗口对齐）
- `003` harness 侧 semihosting 应答者（最小 5 服务 + 核内 `trap` 抬边界）
- `004` 解码器 + 整数 ALU + 寄存器堆
- `005` 访存
- `006` 控制流 + RAS
- `007` 位操作 + 原子 + 杂项（用户 2026-11-08 确认）：位操作与整数补齐 + `lr`/`sc`/`swym`（`SimRISC-12`）+ `fence`（`SimRISC-11 §5`：`hb!=0` 或保留 `cfxha` ⇒ ILLI，其余 no-op；单周期核天然满足屏障语义）
- `008` FP 基础设施：recFN 编解码 + 六档舍入 + 异常标志 + 分类/符号（hardfloat `recFNFromFN`/`fNFromRecFN`/`RoundAnyRawFNToRecFN`/`classifyRecFN`）
- `009` FP 转换：`ft2i*`/`fo2i*`/`fo2ft`/SBZ/复制（hardfloat `INToRecFN`/`RecFNToIN`/`RecFNToRecFN`/`resizeRawFloat`）
- `010` FP 算术：加/乘/FMA/比较/最小最大（hardfloat `AddRecFN`/`MulRecFN`/`MulAddRecFN`/`CompareRecFN`）
- `011` FP 除法/开方/取余（hardfloat `DivSqrtRecFN_small`）
- `012` FP 取整/缩放/符号操作（`fornd`/`fosclb`/`fosgnj`）
- `013` T0 冒烟：inst（全部非 cfx）+ tset 已验证子集，qemu/gem5/chipyard 三平台比对
- `014` T1 适配集 + M12 验收

- **FP 覆盖范围（用户 2026-11-08）**：**全做 5 组**；原则是「所有非 cfx 指令都应实现」。
- **M12 指令覆盖（用户 2026-11-08）**：**全部非 cfx 指令**（不再只是 inst 子集），含 `fence`、`lr`/`sc`、`swym`；cfx 本身（`trap`/`escape`/`cfx2rd`/`cfx2rc`）不在 Tiny 实现，`trap` 仅用于 semihosting。
- **FP 实现方式（用户 2026-11-09）**：**参考** berkeley-hardfloat 的 recFN 语义、**自写**组合逻辑，**不引入 `hardfloat` 子模块依赖**；代码与任务书**逐处注明来源**。
- **「单周期」= 无流水线，不是「每条指令一个周期」**（用户 2026-11-09）：多寄存器/ldm/stm 本就多周期；**FP 除法/开方允许走多周期状态机**。
- **M12/M13 边界（用户 2026-11-09）**：M12 = **功能性**（pass/fail/exit/board markers 一致）；M13 第一阶段 = **完整准确的语义定义 + 重新生成边界向量**，做**语义性**差分。
- **M12 纳入 embench 全量**（38 例；裸机 semihosting 5 服务足够：`WRITE0`/`WRITE` + `EXIT` + 可选 `CLOCK`）。
- **T1 范围（用户 2026-11-09）**：`tests/inst` 全量（非 cfx）+ tset（embench 全量 + libc-test/llvm-ts 无文件 I/O 子集）；**不含 `tests/arch`**（`tiny.arch=false`）。
- **`fence` 已确认纳入 M12（用户 2026-11-08）**：`fence` 属核芯功能扩展（`SimRISC-11 §5`，`fence_ciii_cfx`），但 **inst 测试集含 fence 用例**（`tests/inst/atomics/atomics-fence.yaml`，生成自 `contracts/opcodes.yaml` + spec）；qemu（`trans_fence_ciii_cfx`：`hb!=0` 或保留 cfxa ⇒ ILLI、`pred==succ==0` ⇒ no-op）与 gem5（`b6_test.cc` 同判据）均已实现。单周期核无 cache/store buffer/乱序，非零掩码的屏障语义天然满足 ⇒ 实现成本 ≈ 20 行。**建议 M12 实现**（否则 T0 子集缺一条指令，M13 也要补）。
- **FP 分组依据（用户建议参考 berkeley-hardfloat）**：按 hardfloat 的原语边界切——转换 / 算术 / 除法开方 / 取整缩放，每组对应一组 `RecFN` 原语，便于复用 IP 与逐组比对（本地 chipyard 子模块 `generators/hardfloat/hardfloat` 即该库）。
- **DADAO FP 指令集共 47 条**（`spec/SimRISC-07`）：转换、运算（加/乘/FMA/除/余/开方/取整/缩放/最小最大）、符号位、比较、分类。

## chipyard 子模块补丁与 loadmem 路径（2026-11-09 用户质疑 + reviewer 复核）

- **用户三点质疑的查证结果**：
  - ① `MEM_BASE` **override 后不截断**（reviewer 用 Verilator 5.020 最小复现：`#(.MEM_BASE(48'hffffff000000))` ⇒ `bits=48`、值正确）；「未声明位宽默认 32」只在不 override 时成立。
  - ② fesvr 大端**可开**（`riscv.ac` 的 `--enable-dual-endian`），但**开了还不够**：`SimDRAM.cc` 的 `get_target_endianness()` 仍返回 `little`，dual-endian 分支仍 throw ⇒ 须同时改 testchipip 的 `SimDRAM.cc`。
  - ③ 子模块补丁**应该做**（用户原话「现在不做，以后也要做」），已立 `m12-infra-003`，量级约 0.5–1 天。
- **关键反转（reviewer 读码 + 实测）**：**stock `+loadmem` 写不到 Tiny 的 SRAM**——
  - `+loadmem` 的写入目标是 SimDRAM 的 host mmap backing，只在 `WithBlackBoxSimMem` 绑到 AXI4MemPort 时存在；
  - Tiny 主存是 `BankedScratchpadKey → ScratchpadBank → TLRAM`（on-chip TL slave），**不经 AXI**；
  - 当前设计**没有 SimDRAM 实例**（elab/构建日志 `SimDRAM` 0 次、链接行 `SimDRAM.o`=0）。
  - ⇒ **`m12-chipyard-003` 的 tile 内 loader 不是绕路，是当前设计下唯一能写 SRAM 的路径**（写总线 = 写 SRAM），方案保留。
- **修正我此前的错误判断**：此前记「tile 内 loader 属绕路、应回到 stock loadmem」是**错的**；已按 reviewer 证据撤回。
- 子模块补丁机制的价值不因此消失（fesvr/SimDRAM.cc、将来 Vast 的反备内存、其它子模块改动）。

## chipyard 骨架实测结论（`m12-chipyard-001`，待 reviewer 复核）

- **`BaseTile` 自写端口的抽象成员**：`intInwardNode` / `intOutwardNode` / `masterNode` / `slaveNode` / `module`；`halt`/`cease`/`wfi` 由 `SourcesExternalNotifications` 提供；`HartidKey` / `TileVisibilityNodeKey` / `LookupByHartId` 由 `BaseTile` 构造器自动注入。
- **`TileParams.core: CoreParams` 是绕不开的 RISC-V 形状** ⇒ 用一层 `private[common] WumingCompatCoreParams` 做**形状兼容适配**，`WumingCoreParams` 本身无 RISC-V 字段（这是「外壳 B」的实际代价，需在 M12 后续保持）。
- **地址宽度实测**：`xLen=64` + `useVM=false` ⇒ `maxPAddrBits=64`；`paddrBits` 取 TL 协商值，**stock chipyard 地址图实测为 32** ⇒ `m12-002` 要靠改地址图把它推上去，不是改 `PAddrBits`。
- **`common.mk` 偏离**：chipyard 1.14 全树已无 `BOOTROM_TARGETS`/`BOOTROM_FILES_DIR`（0 命中），BootROM 改走 classpath 资源 ⇒ 用 `WithBootROM(contentFileName=...)` 等价接线。
- **构建**：`sbt compile` rc=0；Verilator `CONFIG=WumingTinyConfig` rc=0（产物 10 MB，`server207`）；有界运行打印 `PutFull 0x80000000 <= 0xdeadbeefcafebabe`（core 桩跑通，随后有界超时 rc=255 属预期）。

## chipyard 定位与技术结论

- **用户原话**：「chipyard --help 的事情：我们没有必要去调试！！！我们不需要去测试 chipyard 本身，这只是我们要用的平台和工具」⇒ 撤销 `INFRA-136t/137t`（零源码改动），`INFRA-133t` 不再验证 `--help`。
- **`--help`/`+help`/无参数都崩溃的根因（已定，不再投入）**：`htif_t::parse_arguments`（fesvr）→ `htif_t` → `tsi_t` → `testchip_tsi_t` → `SimTSI.cc::tsi_tick()`（**首个时钟 tick 才构造**）→ Verilator `--main` 生成的 `main()`（**无 try/catch**）；`--help` 为 `User queried htif_t help text`，无参数为 `No binary specified`，rc=255。属**上游行为**，非环境偏离（chipyard `0acc1e1` clean、testchipip 与 riscv-isa-sim 均为锁定态、Verilator 5.022 符合 conda-reqs）。
- **命名/补丁方式（用户裁定）**：按**实现**分类——`dadao-wuming`（单周期）/ `dadao-wuqing`（五周期）/ `dadao-wuxing`（超标量），每种实现内部再按 Tiny / Vast 做测试配置；**补丁方式 A**（全部进 chipyard 补丁集，newfiles 也写成补丁）。
- **参考实现**：`.cache/refs/DADAO/SOC-chipyard/`（`chipyard-0111-newfiles/generators/dadao-wuming` + 5 个接线补丁 + `chipyard.mk`）；riscv-sodor 为第二参考；PR #4 仅参考。

## M12 未决

- **Tiny 的 SRAM 基址与 `loadmem` 目标窗口**需在 `002` 定稿（`load_elf` 目标基址必须与 Tiny 地址图一致）。→ 已定（`002` 地址图 hmon SRAM 段），本条可删。
- ~~`006` 的 R12/R13/R14~~ **已裁定（2026-11-10）**：R12=A 扩展+大改、R13=hmon 编入 BootROM+power 搬运、R14=最小 handler；R1–R16 全部落纸（`refs/m12-006-cycle-design.md §8.1–8.3`）。
- ~~`spec-003` 候选范围~~ **已立册并完成**（`m12-spec-003` 口径统一、`m12-spec-004` hmon 装载契约）。残留项：
  - #9 `cfx2rd`/`cfx2rc` 到**保留** cfxha ⇒ `ILLI`（`Machine-v5` 现只说「不存在 cfx 寄存器 ⇒ `CFXREG`」，与 `DADAO-12 §5.2(一)` 冲突）
  - #10 reserved 集统一（正文 `19–61` vs 附录 0.4.0 `16–31、35–61`）
  - #6 退出码由 hmon handler 生成（`§7.1` 只定编码、未定生成方）
  - #3 Tiny 的 hmon 镜像装载路径（与 R13 绑定）
  - （`m13-qemu-001` 新增）`excp_cause_info` 覆盖：`Machine-v5 §4.4` 5 项 vs `DADAO-13 §2` 11 项
  - （`m13-gem5-001` 新增）`escape` 返回 cfx 取自「异常帧」，但寄存器表无 `prev_cfx` 保存寄存器（实现镜像 QEMU/Node 保持目标 cfx）
  - （`m13-gem5-001` 新增）Tiny `cfx_power` 的 cg7（BootROM start/size）与 `cg8 rc1`（power ctrl，WO）无正文
  - （`m13-gem5-001` 新增）Tiny `switch_run_mode` 写非 hypv 值：寄存器 RW 但无强制路径
- **`spec-004` 候选**：Vast 的同步异常仍是 staged 机器 fault（`DADAO-12 §5.2(一)` 要求进向量），5 个 arch 探针 oracle 依赖旧口径；统一需同步改 qemu/gem5 + 探针。

---

# M13：三平台差分对齐（qemu / gem5 / chipyard，含浮点）

## 范围

- **三平台差分**：qemu / gem5 / chipyard 的**指令语义**对齐，**尤其是浮点**语义。
- **riscv-tests**：移植与调整在 M13 完成（M12 不用）。
- 判据仍是「实现之间一致 + 与 spec 逐条核对」；**不允许把「两个实现一致」当正确**（多数表决 ≠ 真值）。

## M13 起点：gem5 超时与运行时间可比性（用户 2026-11-09 裁定）

- **用户原话**：「M13准备专门进行多方测试的差分对比，可以先从gem5的超时问题做起，放到208节点机上，48并行（甚至60并行，你觉得呢）；建立专门的任务，跑3600s，甚至7200s，我们测试一下qemu和gem5的运行时间的比率，对不同的任务是否具有可比性。该任务（或者你可以分解多个任务）不修改源码，不做调试，只记录结果；我来对结果进行分析和裁定。」
- **并行度结论**：**48**（留 16 核给内核/IO）；60 会引入调度/带宽争用，污染时间测量。若 3 例 × 2 次方差 < 5%，再考虑提高。
- **任务分解**：`m13-testcases-001`（static 72 例 × 3600s）、`m13-testcases-002`（dynamic 93 例 × 3600s）、`m13-testcases-003`（3600s 仍超时的例 × 7200s）。
- **只记录不改源码**：这三个任务不做根因分析、不调试；结果由用户分析裁定。
- **M13 台账**：新建 `.tao/knowledge/milestones-m13.md`（`项目里程碑 = M13`），Makefile 的 `check-milestones-fresh` 扩展为校验 M11 + M12 + M13。

## M13 待梳理：差分产物的归属（用户 2026-11-09）

- **对象**：`docs/TestReports/M11-三平台一致矩阵.md`（矩阵快照）、`.tao/knowledge/refs/*-parity-summary.*`（逐例报告）、`tools/testcases/parity/{run_parity,se_tset_matrix}.py`（生成器）、各基线 summary JSON。
- **问题**：矩阵与报告混在 `tests/`、`.tao/knowledge/refs/` 两处；矩阵内含运行期绝对路径（`/tmp/opencode/<任务>/...`），fresh clone 上不可复现；「哪份是快照、哪份是原始数据、哪份是生成物」的边界靠 README 口头约定。
- **处置**：M13 开始差分对齐时统一梳理（不在当前任务里改），原则先定两条：① 生成器随产物入库；② 快照只含 md5/版本等身份指纹，不写运行期路径。

## golden / Sail 定位（结论，待落流程）

- **前提**：SimRISC/DADAO 持续变更、不留历史包袱；内核/FPGA 阶段同样如此。工具按「高频变更」取舍，不按「稳定期资产」取舍。
- **Sail：搁置**。形式化模型是稳定期资产；0628 实测只做 6–8 条切片、其余 `SKIP-unsupported`；「权威性」在自有扩展上不成立。重启触发条件：ISA 冻结 / 流片前 / 需要 RTL tandem 或定理证明。
- **golden：不做全量第四实现**。只保留三个窄用途：① 歧义探测（未明处 `SpecificationGap`/`UNSPECIFIED` 显式阻断，不猜默认值）；② 精确计算（FP/位宽/舍入）；③ 裁定回归（把用户裁定固化成向量/断言，防漂移）。PR#5 的全量模型 + 万行 `INSTRUCTION_REFERENCE.md` 属稳定期资产，不并入日常门控。
- **裁判只能是用户**：工具只做「发现歧义 + 举证（各解释下的结果/依据）+ 回归」，不做拍板；差分/fuzz 的分歧须聚类归因后再上报，不把原始分歧直接丢给用户。
- **投资顺序**：规范一致性/歧义探测 > 差分 fuzz + legality 矩阵 > 精确 FP > 轻量边界生成；解释器只在「需要算给看」时写。
- **三条禁忌**：向量里写未记录来源的期望值；模型对未明处选默认值；把「两个实现一致」当正确。
- **依据（0628 / PR#5）**：0628 四方差分（interp/QEMU/gem5/Sail）AGREE 198 / DIVERGE 0，`check-golden` 故意不进 `make check`；golden 仅整数 87 条，语义取自 `spec.md`（与 ADR-0009「wiki 直派」的要求不一致）。PR#5：标量 + 66 条 FP，回放 730（173/500/0/57），49 单测，`check-golden` 进 L1；无差分运行器，FP 向量只有 `scaleb`。
- **待落地**：① 「歧义登记 → 用户裁定 → ADR/向量 → 回归」的流程；② 是否把「歧义探测」并入现有 spec 门控；③ chipyard 是否已有 DADAO 核（决定 RTL 对拍是否成为主差分）。

## 第一阶段目标（用户 2026-11-09）

- **先定义每条指令的完整且准确的语义**（尤其浮点：舍入方向、异常标志、NaN 传播、边界值）。
- **再重新生成 `tests/inst` 的测试程序**，重点是各种边界。
- 之后才做三平台差分（`m13-integ-002`/`003`）。

## M13 未决

- 差分矩阵的判据、参与引擎、失败归因口径（启动 M13 时专门讨论）。
- **3600s 长尾结论（2026-11-10，`m13-testcases-001` 全量）**：72/72 例 gem5 SE 仍超时，qemu 72/72 全 pass；最小例（qemu 0.0 s）也吃满 3600 s ⇒ 疑挂死而非慢（`ISS-361`）。
  ~~待用户定 7200s 还是定位挂死~~ **已定（2026-11-10）**：按 qemu 时耗 30 s 分 A/B 组——A 组 7200 s（60 例，已出结果 40 pass/17 blocked/3 fail），B 组无上限（90 例，进行中）。
- **3600s 长尾结论（2026-11-10，`m13-testcases-002` 全量 dynamic）**：93 例中 gem5 **78 blocked / 14 pass / 1 fail**，比值 `n=12`（min 172、median 289、max 1942）；
  qemu 93/93 pass。⇒ dynamic 有一小部分可测、static 全不可测。`neural` 为 gem5 侧 oracle mismatch（`ISS-362`）。

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

## 发布与回归（不阻塞 M11 收口）

- **回归运行（原「夜跑」）加 gem5（用户 2026-11-08）**：「夜跑」是**全量回归成员集**的意思，不是只在夜里跑；成员应含 **gem5 SE + gem5 FS**。拟立 `TESTCASES-105t`。
- **SimRISC 发布 `0.5.6`（用户 2026-11-08）**：可以发布；须**重新整理版本与变更记录**（13 册册头统一、变更记录按重要性/主题归并、去 `-rc`）。拟立 `SPEC-196t`。
- 两者均**不是 M11 收口条件**（收口判据见 M11 节）。

## 待用户裁定：ADR

### chipyard 集成（已裁定 B，2026-11-08）

- **用户裁定**：选 **B**（就地修订 `ADR-0024 D1`），并对四处修订文本回「可以」。
- **已落地**：`ADR-0024` 的 D1、Rationale 被否方案、Consequences 约束、状态说明修订记录同步改为「做（2）+ 补丁集」；`D2`–`D5` 不变。
- **待随 `m12-001` 落地**：`manifests/components.lock.toml` 去掉 `patchless`、加 `patch_dir`/`patch_series`；建 `components/chipyard/patches/` + `series`（同笔，避免「ADR 说打补丁、锁说 patchless」的过渡态门控红）。

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

## 队列状态（2026-11-10 巡检）

**在跑**：`m13-gem5-002`（Tiny 恒 hypv + cg3）、`m13-infra-001`（ISS-355/356）。

**待开始但被阻塞**（阻塞原因，非队列空）：

| 任务 | 阻塞源 | 归谁 |
| --- | --- | --- |
| `m13-gem5-003`（ISS-358/359） | 组件单写者：与 `m13-gem5-002` 串行 | 主会话（002 收口后立刻派） |
| `m12-chipyard-007` | 需裁定 R12/R13/R14（改造范围、hmon 镜像装载、handler 出退出码）+ `spec-003` 的 §9 七条 | 用户 |
| `m12-chipyard-008`–`017` | 依赖 `007`（同一 `WumingCore` 单写者） | 主会话（007 收口后） |
| `m13-testcases-003` | 需裁定「7200s 加预算」还是「转定位挂死」（`ISS-361`） | 用户 |
| `m13-integ-001`–`005` | 任务书声明依赖 `m12-chipyard-015`（M13 主体待 M12 核完成） | 用户（若要提前，需改依赖） |
| ~~`m12-spec-003`/`spec-004`~~ | **已立册并完成** | — |

**open 但暂无对应任务**：`ISS-345`（语料不可达）、`ISS-357`（stdout/stderr 写序，属 SE 驱动口径）、`ISS-360`（流程缺陷）、`ISS-361`/`362`（随 `testcases-003` 一并处置）。

## 磁盘水位与构建瘦身（2026-11-10）

- **触发**：用户要求「安排评测类任务前先查磁盘，> 90% 报警」。实测主控机 `/mnt/tao` **92%**（424G/492G）。
- **已清理**（用户同意）：归档 M11 任务的 `runtime/`/`review/` 逐例目录（8 个任务 ≈250G）+ 三份一次性 gem5 构建副本（≈72G）⇒ **92% → 23%**。
- **已落地**：`make check-disk`（主控机，> 90% FAIL）+ `remote.py status` 的 `disk_use_pct`/`disk_alert`（节点）+ `AGENTS.md` 预检第 ⑥ 项改为「并行度与磁盘」。
- **gem5 体积事实**：`build/DADAO` 4.5G；`gem5.opt` 702 MB，其中 `size` 实测 text+data 仅 34 MB，**662 MB 是 DWARF 符号**；`strip --strip-debug` 后 **40 MB**（行为不变）。`gem5.fast` 关闭 assert ⇒ 差分测试不宜盲用。
- **逐指令信息不是大头**：跑批未使用 `--debug-flags`，每例 `m5out` 仅 280 KB；250G 来自重复的逐例运行目录。**规则**：常规跑批永不开 `--debug-flags`；需要时用 `--debug-start/--debug-end` 卡窗口并即删。
- **待用户定**：① `docs/Process-08` 增「收尾只留 `run.sh` + 汇总 JSON + 日志（≤10MB），删逐例目录」；② `.work/build/` 只允许 `gem5`/`qemu`/`llvm` 规范名，派生构建用完即删，`gem5.debug` 按需临时建。

## spec-003 / spec-004 拆分与 hmon 装载契约（用户 2026-11-10 裁定）

- **选 B 拆两册**：`m12-spec-003`（题 1–5 口径统一，纯文字）+ `m12-spec-004`（题 6–8 新契约）。
- **hmon 装载契约（用户原话）**：「hmon的代码/数据应该是放在bootrom中，然后由bootrom代码存放到相应位置；先在qemu中进行验证，然后gem5/chipyard可共用」。
  ⇒ 废弃「宿主 loader 直装 hmon 段」的现行实现口径；**宿主只为应用下发 `PT_LOAD`**，hmon 随 BootROM 镜像走。
- **`cfx2*` 口径（用户原话）**：「reserved cfx引发ILLI，非reserved cfx的未定义cg/rc引发CFXREG，没有冲突，只是Machine-v5文档没写清楚」⇒ 只需把文档写清。
- **退出码（用户原话）**：「7.1写的不对，只定编码，谁产生是代码设计要决定的」⇒ spec 删除「由 handler/硬件产生」类表述。
- **连带影响**：`m13-qemu-001`/`m13-gem5-001` 已按旧口径（直装）合入，需按新契约返工；`m12-chipyard-007` 直接按新契约实现。建议合并为一个「三平台 hmon 装载对齐」任务（待 spec-004 合并后立）。

## spec-003 三点裁定（用户 2026-11-10）

- **reserved cfx 不写编号**：编号列表以后会变，`Machine-v5` 只写规则并指向 `DADAO-12 §1`（单一真源），不重复列举。
- **Tiny `switch_run_mode`**：写入即 3、读回 3（用户原话「Tiny下，写入3，读回3」）。
  ⇒ QEMU/gem5 现为「保存写入值」需改；与「hmon 装载契约」一起归并到后续「三平台 Tiny 对齐」任务。
- **`DADAO-12 §2.1` 笔误**：确认并修正（`0x3_ffff_0000`→`0x3ff_ffff_0000`、`0x3_ffc0_0000`→`0x3ff_ffc0_0000`），用户授权本次 `spec/` 改动。


## 执行顺序（2026-11-10 定稿，按依赖串行）

用户：「这是正常依赖关系导致的串行，确定好顺序串行即可」。

**M12 主链（严格串行，单写者 chipyard）**
```
020 预取 4 槽 → 019 cfx 寄存器 + 五类异常进 hmon
  → 008 访存(ld/st/ldm/stm) → 009 控制流+RAS → 010 位操作+原子+杂项
  → 011 FP 基础设施 → 012 FP 转换 → 013 FP 算术 → 014 FP 除法/开方/取余
  → 015 FP 取整/缩放/符号 → 016 T0 冒烟 → 017 T1 + M12 验收
```

**M13 前置（与主链并行，独立组件）**
```
qemu-002 ‖ gem5-005（Tiny 装载契约对齐；以 QEMU 结论为准）
```

**M13 差分（必须等 015 + qemu/gem5 对齐后，串行）**
```
integ-002 FP 差分 → integ-003 整数/访存差分 → integ-004 riscv-tests → integ-005 收口
```

**后台常驻（不占串行槽位）**
```
testcases-003（207 原计划）+ 008（208 差集）→ 长尾计时；结果待合并
```

规则：每一步**先合并再进下一步**；并行只允许「不同组件」或「节点上的用例执行」，不允许同组件两写者。

- **`m12-testcases-002` 已取消（2026-11-10）**：原打算单独做「E2E 适配固定固件契约」；`m13-qemu-002` 的实现已覆盖（11 个 lit 用例 + `lit.cfg.py` + `picolibc-tiny.ld` + `Makefile` + `tools/testcases/**` 的 trampoline/E2E 驱动），且其 L2 `check-modules` rc=0 ⇒ 判重复，不另立册（任务书已删，仅此记录）。
