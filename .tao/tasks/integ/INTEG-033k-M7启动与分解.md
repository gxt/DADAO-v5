# INTEG-033k: M7 启动与分解（用户 10 条裁定落纸 + 参考仓库检索 + 任务分解草案）

**模块**：integ
**项目里程碑**：M7
**依赖**：`INTEG-026m`（M6 integ 里程碑，`里程碑`，= 项目里程碑 M6 达成）；无硬前置
**状态**：待开始

> 用户 **2026-10-11 授权**：把 M7 相关裁定落盘 + 立任务（分任务/避坑）+ **先查参考仓库**。本 `k` 只**落纸裁定 + 参考经验 + 出任务分解表（含 Wave/串行）**，**不改 `spec/`、不改实现**（`spec/` 正文同步归各 `t`）。**本 `k` 的裁定已逐条来自用户原话**（`AGENTS.md`「ADR decision 逐条确认」；`lessons §7.3`）。

## 问题根源

- M6 已交付「整数完整调用约定 + LLVM 欠账收口 + ELF 直载 + clang target + Embench」，但**真实 C 程序（需 libc）与 FP 完备性仍不可用**：`ISS-188`（FP 完备性缺口：`setcc` 取值 / `fabs`/`copysign`/`frem` / 取整类 / `fmin`/`fmax` / `bitcast`(FP↔RD) 等——**全部显式失败、不产错码**）遗留给 M7；`TESTCASES-039t` 首验收暴露的 6 类后端缺口（`ISS-175`–`ISS-180`）中 FP 类未收口。
- **test 重心**从基准（Embench）转向 **picolibc 自带 test**：需先把 libc（picolibc）真正移植到 `dadao`（cross file / machine-board dir / syscall stub / 构建集成），并以其自带 test 作为门控——但**后端/执行环境尚有硬缺口**（FP 完备、地址段口径）。
- **执行环境与地址段口径未定**：当前 RAM@0（核内全 0 段，cfxha 0）在没有其它 cfx 支持的阶段不满足「有效地址须在 `[47:42]` 全 1」的口径；须改到 cfxha 63 段内。
- **ISA↔后端覆盖缺机械真源**：现有 lit 只证「汇编器可受理」，**未证「ISel 用得上」**；需生成式矩阵以 `contracts/opcodes.yaml` 全量为真源，两层分列。

## 目的

- 落纸用户 **10 条 M7 裁定**（含 `adr-0023` 立、`ADR-0004` RAM 基址修订、RAM 基址改 `0xFC00_0000_0000`）。
- 出 **M7 任务分解**（含依赖/串行/Wave），使 M7 = **picolibc 移植（自带 test 100%）+ FP 后端完备（P0/P1）+ ISA↔后端覆盖矩阵 + 过渡 oracle**，并**明确排除**动态链接 / linux-user / pk / Chipyard / golden。
- 产出**参考仓库检索**（`DADAO`/`DADAO-0628`）供 M7 移植/半托管口径/地址段/测速 harness **溯源与避坑**（**内容溯源，非执行依赖**）。

## 对照关系

- **借鉴 0628 `ADR-0014`（libc/syscall charter）**的**分阶段与最小路径**思路：picolibc 先行（tinystdio + 最小 syscall stub）、musl 后置；**差异**：v5 M7 走 **semihosting（`SYS_*` 服务）**而非 0628 的 SEE `trap cfx_smon`+cfx_uart/cfx_power（v5 测试机不启用 `supv`、M7 不引入 pk/kernel）。
- **借鉴 0628 的「小 libc 先趟后端」结论**（`ADR-0014 D5.1`：卡关 80% 是 DADAO 后端 codegen 缺口）：v5 据此把 **FP 后端完备（P0/P1）**与 picolibc 移植**并行推进**（后端侧任务串行）。
- **借鉴官方 Embench 测速模块**（`DADAO-testset/embench-iot/{config/dadao/**,pylib/run_qemu.py}`）的返回码+耗时记录方式。
- **对照**：0628 的 `crt0` auxv 自合成 / `__heap_start/__heap_end`（不在 `PT_LOAD` `memsz` 内）经验，用于 v5 `dadao.lds`/堆段的避坑（v5 无 argv 需求，argv 走 semihosting `SYS_GET_CMDLINE`）。

## 参考经验（**只读 `.cache/refs/**`，内容溯源，非执行必需；不复制代码**）

1. **picolibc 先行 + tinystdio + 最小 syscall stub**（`DADAO-0628/docs/adr/0014-libc-syscall-charter.md` D5/D5.1/D5.2；**溯源**）→ v5 M7 以 picolibc 自带 test 为重心；**差异** = v5 用 semihosting（`_write`→`SYS_WRITE`、`_exit`→`SYS_EXIT`、`_sbrk`→堆）而非 0628 的 `trap cfx_smon`；**建议落点** = `INFRA-057t`/`TESTCASES-042t`。
2. **卡关 80% 是后端 codegen 缺口**（同上 `D5.1` 实施发现：mem* intrinsic / varargs / 跳转表 / 间接调用）→ v5 M6 已收口（`setcc`/大常量/跳转表/尾调用），M7 剩 **FP 完备**；**差异** = v5 用 lit + `picolibc-probe-*` 探针量化；**建议落点** = `LLVM-079t`/`080t`/`081t`。
3. **官方 Embench 测速模块**（`DADAO/DADAO-testset/embench-iot/config/dadao/{arch.cfg,boards/**,chips/**}` + `pylib/run_qemu.py`：`sh -c 'time -p qemu-dadao ./bench; echo RET=$?'` 解析 `RET=`/`real`；**溯源**）→ v5 M6 已接 Embench（`TESTCASES-039t`）；M7 benchmark 视需参考其返回码+耗时记录；**建议落点** = `INTEG-033k §说明`（M7 不新建测速套件）。
4. **旧工具链 = linux-user / gem5 loader（史实）**（`DADAO/SIM-qemu/qemu.mk`：`TARGETS=dadao-softmmu,dadao-linux-user` + `qemu-0801-newfiles/linux-user/dadao/*` 17 文件 linux-user 支持；`ENV-proxylinux/` = `riscv-pk` fork〔`v1.0.0`/branch `dadao`〕；**溯源**）→ v5 M7 **排除** linux-user/pk；**差异** = v5 只做 system-mode + semihosting；**建议落点** = 本 `k §排除项`。
5. **`crt0` auxv 自合成 + `__heap_start/__heap_end` 不在 `PT_LOAD` `memsz` 内**（`DADAO-0628/docs/development-roadmap.md` Phase B/ML-008a；picolibc sbrk fallback；**溯源**）→ 地址变更后须核 heap 段与 `PT_LOAD`/RAM 16 MiB 关系；**差异** = v5 无 argv/auxv 需求（semihosting）；**建议落点** = `INFRA-057t` 避坑清单。
6. **bootrom + bootaddr SCR / `linker.ld`（`ROM_BASE=0x10000`）**（`DADAO/DADAO-runtime/bootrom/{bootrom.dadao.S,linker.ld}`；**溯源**）→ v5 M5/M6 已用 `-bios` bootrom + hypv→user；**差异** = v5 用 semihosting 停机；**建议落点** = `QEMU-056t` 避坑清单。
7. **sail 参考模型**（`DADAO-0628/sail/dadao_{main,insts,state,types}.sail`；**溯源**）→ M7 **不涉**（golden 模块整体排除，见 `milestones.md`「GOLDEN-*」候选）。

## 裁定汇总（用户 2026-10-11，10 条；原话要点）

| # | 裁定 | 落点 |
|---|---|---|
| 1 | **`adr-0023` 立**：D1 上游 `https://github.com/picolibc/picolibc`；D2 commit `2ae376c6cdf4fef90ca2388ecf7a07457fa63cff`（= tag `1.8.12`；「**保持 1.8.12**」）；D3 `shallow_ref` 用 **tag**（用户澄清 = tag `1.8.12`）；状态说明引用原话，标 `Accepted` | `.tao/adr/adr-0023-picolibc-upstream.md` |
| 2 | **picolibc test 验收 = 100%**（原话「**要求 100%**」） | `TESTCASES-042t` |
| 3 | **加 `clang++`** + 核 **2 个 `.cpp`** 测试需求 | `INFRA-056t` |
| 4 | **P0 后端纳入 M7**：`f32→f64 anyext` 载入 / FP 比较取值 `setcc` / `f64↔i64 bitcast` / `f64 select_cc` / `i64 cttz`；**优先用 ISA 现成指令**（如 `ft2fo`） | `LLVM-079t` |
| 5 | **「ISA↔后端覆盖矩阵」立即立项**（生成式；`contracts/opcodes.yaml` **全量**为真源；**两层分列**：汇编器可受理？／**ISel 是否用得上**？现有 lit 只证汇编器） | `LLVM-081t` |
| 6 | **P1 后端纳入 M7**：`floor/ceil/trunc/round/rint/nearbyint`、`fmin/fmax`、`fabs`/`copysign` 双精度 | `LLVM-080t` |
| 7 | **过渡 oracle 采用**：宿主机结果作参照 + **明确边界**（端序／`long double`=f64 vs 宿主 80-bit／`fenv`／UB／实现定义），**登记「非判据真源」**（将来 `GOLDEN-*` 替换） | `SPEC-131t` |
| 8 | **M7 明确排除**：动态链接 / linux-user / pk / Chipyard / golden | 本 `k §排除项` |
| 9 | **执行环境 `hypv`**；semihosting 用 `trap cfx3, 0x30000`（原话）；**须核 M6 探针 `cfx_umon` 是否为 cfx3，不一致要登记** | 本 `k §避坑`；`QEMU-056t`/`SPEC-131t` |
| 10 | **RAM 基址改 `0xFC00_0000_0000`**（`[47:42]≡63` 的 cfx63 段；加 cfx 后不变）；**16 MiB 够用 ⇒ 不改大** | `ADR-0004` 就地修订 + `QEMU-056t` |

## 排除项（用户 2026-10-11 裁定 #8）

- **动态链接**（`.so`/`ld.so`/`GOT`/`PLT`/`-fPIC`/`-shared` + `PT_INTERP`/`.dynamic`）——独立后置。
- **linux-user（qemu-user）**——后置（旧工具链史实见 §参考经验 4）。
- **pk（proxy kernel）**——排除（`INTEG-032t` 候选之一，本次裁定不入 M7）。
- **Chipyard**（RTL SoC）——排除。
- **golden**（Python 黄金模型 / 结果级 FP 独立 oracle）——**另立 `GOLDEN-*` 里程碑**，M7 不涉（`milestones.md`）。
- **musl**——不在 M7（M7 = picolibc；musl 待后续里程碑）。

## 任务分解

| 编号 | 任务 | 模块 | 范围（草案） | 依赖 |
|---|---|---|---|---|
| `INTEG-033k` | M7 启动与分解（本文件） | integ | 本 `k` + `adr-0023` + `ADR-0004` 修订 + `milestones.md` 裁定落纸 | 无 |
| `INFRA-056t` | `clang++` 接入 + 2 个 `.cpp` 需求核实 | infra | cross-toolchain 落点加 `clang++`（随 `INFRA-050t` 构建）+ 实测 picolibc `test/` 中 2 个 `.cpp` 的编译需求（是否需 C++ 头/库）+ 证据 | `INFRA-050t`（已验证） |
| `INFRA-057t` | picolibc 移植补丁集 + 构建集成 | infra | `components/picolibc/patches/**`（cross file / machine-board dir / syscall stub `_write`/`_exit`/`_sbrk`）+ `Makefile` 编 picolibc 库 + 落安装点；**真移植主任务** | `INFRA-055t`、`QEMU-056t`、`INFRA-056t` |
| `SPEC-131t` | 过渡 oracle 约定 + semihosting `cfxha` 口径 + 锁同步 | spec | ① 过渡 oracle 约定（宿主参照 + 边界 + 「非判据真源」）正文/合约；② `trap` 的 `cfxha` 口径澄清（`contract-semihosting §1`/`Machine-01 §5.1`）与 `cfx3` vs `cfx_umon`(cfx0) 一致性处置；③ 相关 `sha256` 锁同步 | 无（RAM 相关项随 `QEMU-056t`） |
| `LLVM-079t` | P0 后端补齐 | llvm | `f32→f64 anyext` 载入 / FP 比较取值 `setcc` / `f64↔i64 bitcast` / `f64 select_cc` / `i64 cttz`（**优先 ISA 现成指令**如 `ft2fo`）；范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**` | 无 |
| `LLVM-080t` | P1 后端补齐 | llvm | `floor/ceil/trunc/round/rint/nearbyint`、`fmin/fmax`、`fabs`/`copysign` 双精度；同范围 | `LLVM-079t` |
| `LLVM-081t` | ISA↔后端覆盖矩阵（生成式） | llvm | 落 `tools/llvm/**`（入库）；以 `contracts/opcodes.yaml` 全量为真源、**两层分列**（汇编器可受理／ISel 可用）、**禁手工挑拣** | `LLVM-079t`/`080t` |
| `QEMU-056t` | RAM 基址 → `0xFC00_0000_0000` | qemu | QEMU 机器映射 + `tests/scripts/dadao.lds`/`codegen_crt0.s`/异常向量 + harness（`tools/testcases/build_test_binary.py`、`tools/qemu/gen_trampoline.py`）+ `check-interface` 断言 + **`spec/Machine-01` 与锁同步** | 无 |
| `TESTCASES-042t` | picolibc 自带 test 接入 + 100% 验收 | testcases | 以 picolibc 自带 test 为重心编/链/跑（QEMU semihosting），验收 = **100%**；harness 落 `tools/testcases/**`/`tests/**` | `INFRA-057t`、`QEMU-056t`、`LLVM-079t` |
| `INFRA-058m` / `SPEC-132m` / `LLVM-082m` / `QEMU-057m` / `TESTCASES-043m` / `INTEG-034m` | 各模块 `m` / M7 里程碑（`INTEG-034m` ↔ 本 `k` 一一对应） | 各模块 | 轻量 `m` 文件；**待 `/plan` 交叉审查通过后建** | 各模块 `t` |

> **编号说明**：各模块**实测顺延**（`infra` 现最大 `055` → `056`；`spec` `130` → `131`；`llvm` `078` → `079`；`qemu` `055` → `056`；`testcases` `041` → `042`；`integ` 历史最大 `032` → `033`）。`INFRA-056t`/`QEMU-056t` **跨模块同 `nnn`**——**完整编号含模块前缀、全局唯一**（`INTEG-023k §E-1` 同款说明）。`m` 文件**不写死计数**：各模块任务数**现场统计**。

## Wave / 串行 / 依赖

- **Wave 0（infra；同改 `Makefile`/`manifests` ⇒ 串行）**：`INFRA-056t` → `INFRA-057t`。
- **Wave 1（spec；同改 `spec/`/锁 ⇒ 串行）**：`SPEC-131t`。
- **Wave 2（llvm；同改 `components/llvm-project/patches` ⇒ 串行）**：`LLVM-079t` → `LLVM-080t` → `LLVM-081t`（`081t` 依赖 `079t`/`080t` 的已构建后端）。
- **Wave 3（qemu；同改 `components/qemu/patches` + `tests/scripts` ⇒ 串行）**：`QEMU-056t`。
- **Wave 4（testcases）**：`TESTCASES-042t`（依赖 `INFRA-057t`/`QEMU-056t`/`LLVM-079t`）。
- **Wave 5（integ）**：`INTEG-034m`。
- **关键串行**：**RAM 变更（`QEMU-056t`）先于 picolibc 移植（`INFRA-057t`/`TESTCASES-042t`）**；**LLVM 侧任务串行**（同改补丁集）。**ADR 未 `Accepted` 前不进实现**（`Process-03`；`adr-0023` 已 `Accepted`）。
- **并行上限**：同 `Makefile`/`spec/`/`components/*/patches` 的任务**一律串行**（`AGENTS.md`）。

## 避坑（M7 起步清单）

- **cfxha 不一致（裁定 #9，实测已核）**：用户原话「semihosting 用 `trap cfx3, 0x30000`」；但 M6/v5 实测用的是 **`trap cfx_umon, 0x30000`**——**`cfx_umon` = cfxha 0**（`spec/DADAO-12 §1`：0=`umon`/1=`jmon`/2=`smon`/**3=`hmon`**/…/63=`power`），而 **`cfx3` = `hmon`**，**二者不一致**。`contract-semihosting §1` 明确 tag 判定（`immu18[17:16]==2'b11`）**与 `cfxha` 无关**；QEMU 实现（`components/qemu/patches/…/trans_ctrl.c.inc`）**只查 `immu18[17:16]`、不查 `cfxha`** ⇒ 功能上 `cfx0/1/2/3` 均可。**结论**：不一致**已登记**，**须用户裁定**保留 `cfx0`（现状）还是改 `cfx3`（口径/文档统一）；处置归 `SPEC-131t`（口径）+ `QEMU-056t`（如改则含 crt0/向量/harness）。
- **blast radius（RAM 基址）**：M6 `QEMU-053t` 刚把 RAM@0 收口（唯一 RAM 段），**本次要再改一遍**到 `0xFC00_0000_0000`；受影响面 = QEMU 机器映射/`cpu.h`/`helper.c`/`cpu.c`、`tests/scripts/{dadao.lds,codegen_crt0.s,bootrom*.S}`、`tools/testcases/build_test_binary.py`、`tools/qemu/min_rom_probe_*`/`gen_trampoline.py`、`tools/integ/check_interface_alignment.py`（断言 `RAM_BASE`）、`spec/Machine-01 §1` + 锁。**既有向量地址**须逐一跟改、**语义门控**须重跑。
- **地址段语义**：新基址 `0xFC00_0000_0000` 与 boot ROM `0xffff_ffff_0000` **同属 cfxha 63 段**但**不同偏移**；越界分类（`umon` 段 `addr[47:42]==0` ⇒ `0x81`，其余含 power 段 ⇒ `0x87`）须随新基址复核——**旧「RAM@0 在 umon 段」的越界断言会失效**。
- **`check-interface` 硬断言**：`tools/integ/check_interface_alignment.py` 现断言 `RAM_BASE=0`、`RAM_SIZE=16MiB`、旧 RAM 段已删；须改为新基址断言（**计数/地址派生自单一真源，不写死**）。
- **picolibc 移植**：`INFRA-055t` 的「验收③与 `HEAD==锁定 commit` 同刻不可并存」教训（`check_patch_tree` 断言⑧要求 `base+1`）；真移植补丁须 ≥1 且 `apply-series`。`long double`=f64（`sizeof(long double)=8`）⇒ 与宿主 80-bit 不同（过渡 oracle 边界，裁定 #7）。
- **过渡 oracle 边界**（裁定 #7）：宿主机结果只作参照；**端序**（`ELFDATA2MSB` 大端 vs 宿主小端）、**`long double`**（f64 vs 宿主 80-bit）、**`fenv`**（v5 `machine/fenv.h` 退化为仅 `FE_TONEAREST`）、**UB/实现定义** 均须排除在判据外；登记为**「非判据真源」**。
- **失败保留现场并继续推进**（`AGENTS.md`「最小安全设计」；用户 2026-10-10 裁定）：依据不足时保留现场、自行处置（查证/绕行/有据重试并记录次数）；**只在需用户语义裁定**（如 cfxha 口径）时留问。
- **计数不写死**（`INTEG-023k §E-4`）：文档/注释/任务书/验收**不硬编码计数**；由脚本/门控**现场统计**或写「不下降/逐项相等」。

## 说明

- 本 `k` 为**规划/分解**；`/plan` 交叉审查通过后，各 `t`/`m` 任务书落地 `.tao/tasks/<module>/`（`m` 文件**本 `k` 未建**，待 `/plan` 后建）。
- **M7 不新建 benchmark 套件**（Embench 已在 M6 接入）；picolibc 自带 test 为 M7 test 重心。
- **ADR**：`adr-0023`（picolibc 上游）已 `Accepted`（用户逐条确认）；`ADR-0004` 经授权就地修订；`trap` `cfxha` 口径是否需更动**待用户裁定**（若需，另行处置）。
- 参考仓库检索**只读 `.cache/refs/**`、不写回、不复制代码**；引用项均标「**内容溯源，非执行必需**」。

## 审阅记录

#### 第 1 轮 architect 规划（2026-10-11）
- 依用户 2026-10-11 授权落纸 **10 条裁定** + **参考仓库检索**（7 条，标注溯源）+ **任务分解表（8 `t` + 6 `m`）** + **Wave/串行** + **避坑清单**（含 cfxha 不一致实测）。
- 立 `adr-0023-picolibc-upstream.md`（`Accepted`，逐条引用用户原话）；`ADR-0004` 就地修订（RAM 基址 `0 → 0xFC00_0000_0000`）。
- **待 `/plan` 交叉审查**。
