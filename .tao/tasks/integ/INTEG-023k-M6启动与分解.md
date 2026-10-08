# INTEG-023k: M6 启动与分解（目标/边界 + 待裁定；长叙述见 `.work/log/integ/INTEG-023k-detail.md`）

**模块**：integ
**项目里程碑**：M6
**依赖**：`INTEG-021m`（M5 integ 里程碑，`里程碑`）、`INTEG-022t`（M5 归档，`已验证`）；无硬前置
**状态**：待开始

> **定位**：用户 2026-10-08 已给 M6 方向（4 点，见 detail §用户裁定落纸）；**任务分解、门槛、关键取舍待用户裁定**。**不预设** `milestones.md` 门槛/任务清单，**不占编号**。原文全文（318 行）**逐字**见 `.work/log/integ/INTEG-023k-detail.md`。

## 目标 / 边界

**M6 定位**：完整 LLVM（**编译正确性**为重点）+ QEMU **直接加载 ELF** 测试 + **链接器更完善** + **RAM@0 起、1–4 GiB**（按测试实际需求定）。
- **主线**：编译正确性；核心问题 = **如何进行大量测试**（测试策略/规模/自动化 = 设计主线，非附属）。
- **测试路径**：QEMU 直接加载 ELF（非 `objdump` bin + bootrom）。
- **边界（待裁定）**：`clang` 前端 / 最小 `libc` / OS-syscall 是否纳入；`-bios`+ELF 组合是否保留；「完整 LLVM」内涵。
- **纪律**：**不改 `spec/`**；`spec/Machine-01 §1`（只读册）尺寸改动**须先经用户授权**。

## 三根钉子（M6 **前三项具体交付**，生态接入式）

> **口径更正（2026-10-08）**：本节原写「RAM@0 尺寸 / 完整 LLVM 内涵边界 / 测试策略」系**误读**；主会话原话语境 = **M6 前三项具体交付**（下列 ①②③）。原三项**属待用户裁定**，已移入 §需用户裁定。

1. **DADAO clang target**：`TargetInfo` / DataLayout / ABI / driver / sysroot；**模板** = RISC-V64 形状 + PPC64BE 端序/DL + AArch64 CC。**当前唯一硬缺口**（无 clang 二进制、补丁集无 clang 侧 `TargetInfo`）。
2. **QEMU 改走 `load_elf()`**：复用**生态现成件** `hw/core/loader.c`（**36 处复用**）⇒ **一次**解决 ELF 直载 / 多段 / 入口，并**取消**「扩 `dadao_load_regions[]`」这类**自建 loader** 的后续工作。
3. **Embench 接入**：board shim 3 函数（`initialise_board`/`start_trigger`/`stop_trigger`）+ 最小运行时（见 §关键结论）+ `md5sum` 大端适配。**首验收** = 最小基准在 QEMU 打出**正确退出码**（`main` 返回 `!correct`）。

## 需用户裁定（结论式）

> **口径更正（2026-10-08）**：原「三根钉子」误含下列三项；三项**实为待用户裁定**（非 M6 交付）。

### 原被误置为「三根钉子」的三项

1. **RAM 尺寸 / 地址空间**：维持 16 MiB 还是 1/2/4 GiB？是否授权改只读册 `spec/Machine-01 §1` + 锁？（配套见下 §其余裁定项 #1、#2）
2. **「完整 LLVM」内涵边界**：完整调用约定（整数）/ FP-RF codegen / intrinsic / llvm 欠账收口 / clang-libc，逐项纳入与否（detail §D.1，20 项；见下 #3）。
3. **测试策略（如何大量测试）**：golden（独立 oracle）/ 上游 IR 素材复用 / lit 量产 / fuzz / C 程序链路，选组合（detail §D.2 两轴）。

### 其余裁定项

1. **RAM@0 尺寸**：实测最大单程序 `.o`=1128 B、`m5-e2e` 10 bin 合计 980 B ⇒ **建议维持 16 MiB**（免 `spec`/锁/ADR/断言/补丁连带）；1 GiB 起步为备选。
2. **`spec/Machine-01 §1` 授权**：与 #1 配套——**维持 16 MiB 则无须授权**。
3. **内涵逐项**（detail §D.1 第 1–20 项）：逐项裁定（保留 / 修改 / 否决）。
4. **clang 前端 / 最小 libc**：**建议均不引**（M4 已留后，大依赖）。
5. **`-bios` + ELF 组合**（`ISS-168`）：**建议不需要**（纯 ELF 直载 + semihosting）。
6. **8 项归属存疑**（`ISS-019/026/047/074/081/163/164/167`）：逐条选（归 M6 / 另立里程碑 / 保留待规划 / 继续暂登记）；`ISS-163/167` 未授权改上游只读册前 **BLOCKED**。
7. **ADR 决策**（逐条确认）：`REL12` 新增 / RAM@0 尺寸变更 / 组合加载语义 / `RELA_PAGE`·`RELA_LO` 启用。
8. **是否合并 `ISS-165`（step2）与 RAM@0 尺寸变更**：建议合并（否则仅 step2）。

## 关键结论

- **RAM 实测**：RAM 为**单次运行**口径；16 MiB 已远超（余量 ≥250×）⇒ **维持 16 MiB，撞上限再改**。
- **Embench 分析要点**（详 `.work/log/integ/embench-analysis.md`）：平台接入面极窄（仅 3 函数）；端序唯一坑 `md5sum`（大端 FAIL）；无需 varargs（printf 均在宏内）；BEEBS 自带 bump 堆 ≤8 KiB（无 libc malloc）；纯整数但 `wikisort` 需 double `sqrt`；最小运行时 = memcpy/memset/memmove/memcmp/strlen/strchr + ctype + sqrt；单最大基准 ≈64 KB；无 OS/syscall（semihosting `SYS_EXIT` 停机）。
- **clang 缺口**：无可用的 C 前端 `clang`（`.work/build/llvm/bin/` 无 clang；`components/llvm-project/patches/` 无 clang 侧补丁）⇒ Embench（C 源码）需 clang `TargetInfo` 或等价 C→IR 通道；与「clang 不纳入 M6」存在张力。

## Embench 接入（M6 待办）

① 建 **ADR**（记录 Embench 上游选择 + 精确 commit）⇒ 翻 `manifests/components.lock.toml` 的 `enabled = true`；② 建 `components/embench-iot/{patches/**,series,changelog.md}`（board shim 3 函数、`md5sum` 大端适配、最小运行时）；③ 工作树由既有 `make fetch` 生成到 `.work/source/embench-iot`。

## 说明

- **性质**：用户方向已定、方案已出、**任务拆解待裁定**；不自行定门槛/清单、不写 `milestones.md` M6 行、不建 `t`/`m`、**不占编号**。
- **交付**：主会话将 §三根钉子（交付三项）+ §需用户裁定（含原「钉子」三项）+ §关键结论 转呈用户**逐条裁定**；裁定后按 `spec/Process-04 §1` + `INTEG-019k` 体例出任务分解表 + 分波串行链 + `k↔m` 对应 + 前置 ADR。

## 审阅记录

#### 第 1 轮 architect 口径更正（2026-10-08）

- **误读更正**：本任务书原 §「三根钉子」写为「M6 分组前必须先钉死：① RAM@0 尺寸/地址空间 ② 完整 LLVM 内涵边界 ③ 测试策略」= **误读**。
- **依据 = 主会话原话语境**：**「三根钉子」= M6 前三项具体交付（生态接入式）**：① **DADAO clang target**（`TargetInfo`/DL/ABI/driver/sysroot；模板 = RISC-V64 形状 + PPC64BE 端序/DL + AArch64 CC）——**当前唯一硬缺口**；② **QEMU 改走 `load_elf()`**（复用 `hw/core/loader.c`，36 处）⇒ 一次解决 ELF 直载/多段/入口，并**取消**「扩 `dadao_load_regions[]`」自建 loader 后续工作；③ **Embench 接入**（board shim 3 函数 + 最小运行时 + `md5sum` 大端适配）⇒ **首验收** = 最小基准在 QEMU 打出正确退出码（`main` 返回 `!correct`）。
- **处置**：§三根钉子 改写为上述三项；「RAM 尺寸 / 内涵边界 / 测试策略」三项**移入 §需用户裁定**（另列小节「原被误置为『三根钉子』的三项」）；`.work/log/integ/INTEG-023k-detail.md` **未含**该误读段落（经 `grep` 核实：全文无「钉/必须先/分组前」），故**未改动**该文件。
