# TESTCASES-097t: smon/hmon 页表同步到 D10

**模块**：testcases
**项目里程碑**：M11
**依赖**：`SPEC-184t`（已验证；`Machine-v5 §6` D10：`PTBR=0`、L1 `0–3`、4×512 MiB、VA `[0, 2 GiB) → PA [0, 2 GiB)`、`H=1/S=1/U=J=0`、`SPF=0xFF`）
**状态**：待开始

## 执行环境
本地；只改测试 bootrom 资产，不改 spec/QEMU/gem5。

## 问题根源

`SPEC-184t` 已把 Node D10 订正为低地址 4 超页、`U=J=0`；测试资产仍是旧口径：

- `tests/shared/bootrom/step5/smon.S`：L1 index `0x1000` 一个 512 MiB 超页，VA `0x0200_0000_0000` 起，PTE `H=0`；与 D10 的 L1 `0–3`、VA `[0, 2 GiB)`、`H=1` 不一致。
- `tests/shared/bootrom/step5/hmon.S`：已按 L1 `0–3`、4 超页建表，但 PTE `HSJU=0xF`（`U=J=1`），D10 要求 `U=J=0`（`HSJU=0xC`）。

M11 不执行 smon（`machine-profiles.yaml` 的 `smon: reserved`），但测试资产必须与现行 spec 一致，避免后续 smon 任务沿用旧几何。

## 目标

1. `hmon.S`：4 个 PTE 的 `HSJU` 由 `0xF` 改为 `0xC`（`H=1`、`S=1`、`U=0`、`J=0`）；`PPN`、`SPF=0xFF`、`R/W/X/P/SP/A/D/G` 不变；注释同步。
2. `smon.S`：页表模板改为 D10 的 4 个 512 MiB 超页（L1 index `0–3`，`PPN=0/0x2000/0x4000/0x6000`），`HSJU=0xC`、`SPF=0xFF`；DMA 拷贝长度与 PTE 读回断言同步改为 4 项（或至少覆盖 PTE0 + 逐项静态断言）。
3. `smon.S` 中所有旧高地址 VA（`0x0200_...`）改为 D10 覆盖的低地址（如 `0x0000_0001_2000` 等），保持原有测试语义（同一 PA、同一 magic、同一观察寄存器）。
4. 注释/观察寄存器说明与实现一致；不删测试点、不改 magic/退出码。

## 接口规范

### 1. `tests/shared/bootrom/step5/hmon.S`

- 4 个 PTE 的 64 位常量中 `HSJU` 字段由 `0xF` → `0xC`；其余字段逐字不变。
- 顶部 PTE 注释 `HSJU=0xF` → `HSJU=0xC`（`U=J=0`）。
- 不改 PTE 数量、L1 index、PPN、DMA 长度、PTBR/PTW 流程。

### 2. `tests/shared/bootrom/step5/smon.S`

- 页表模板：4 个 PTE，L1 `0–3`，PPN `0/0x2000/0x4000/0x6000`；每个 PTE `HSJU=0xC`、`SPF=0xFF`、`P/SP/D/A/G/X/W/R` 与 hmon 一致。
- DMA：模板在 `cfx_pmem` SRAM 的偏移不变（`0x8000`），拷贝长度由 8 字节改为 32 字节；`cfx_ptw` 的 PTBR/PTW 流程不变。
- PTE 读回：`rd14` 至少断言 PTE0；若保留单寄存器观察，追加对 PTE1–3 的静态/构建期断言（脚本解析 `smon.o`/bootrom 镜像中的 4 个 PTE 常量）。
- VA 常量：所有 `0x0200_0000_0000` 基址的访问改为 `0x0000_0000_0000` 基址；偏移（`0x12000`、`0x11000`、`0x10000` 等）与 PA 保持一致。逐个核对 `LD64 rb4/rb1/...`，不得只改页表不改访问地址。
- 注释中的「L1 index 0x1000」「VA 0x0200...」全部改为 D10 口径。

### 3. 不变项

- 不改 `tests/shared/machine-profiles.yaml`、链接脚本、`tests/shared/asm/machine-node.inc` 的几何宏。
- 不改 QEMU/gem5、spec、contracts、Makefile、门控脚本。
- 不改 `tests/parity/matrix-M11.md`（M11 收口时另案重生成）。

## 文件范围

**修改**（仅 4 个入库文件）：
- `tests/shared/bootrom/step5/hmon.S`
- `tests/shared/bootrom/step5/smon.S`
- 本任务书
- `.tao/knowledge/milestones.md`（本行）

**不改**：`tests/**` 其它文件、`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`Makefile`、`manifests/**`。

## 验收标准

1. **hmon PTE**：源码中 4 个 PTE 的 `HSJU` 均为 `0xC`；`grep -n '0xffef' hmon.S` 的常量与 `PPN` 字段不变；`make build-bootrom` rc=0。
2. **smon PTE**：源码恰有 4 个 PTE，L1 `0–3`、PPN `0/0x2000/0x4000/0x6000`、`HSJU=0xC`、`SPF=0xFF`；`grep -n '0x0200' smon.S` 为 0；`make build-bootrom` rc=0。
3. **构建期断言（可 FAIL）**：证据脚本从 `smon.o`/bootrom 镜像解析 4 个 PTE 常量，断言 L1 `0–3`、PPN、`HSJU=0xC`、`SPF=0xFF`；注入一处 `0xF`/旧 PPN ⇒ FAIL；还原后回绿（`cp`+`md5sum -c`）。
4. **Node 回归**：`make check-arch` rc=0、`make check-inst` rc=0（Node 965/970、Tiny 44/44 量级）；hmon 改动后 Node arch/inst 不退化。
5. **smon 执行**：若现场有可执行 smon 的入口，跑一次并断言观察寄存器；若 `smon: reserved` 不可执行，记 **BLOCKED** 并给静态构建期断言证据，不得伪 PASS。
6. **门控**：`make check`（L1）rc=0；`make check-milestones-fresh` rc=0。
7. **范围**：`git status --porcelain -uall` 仅含上述 4 个文件；无临时残留。
8. **体例**：完成区 ≤30 行；证据落运行期临时目录（已清理，未归档）；状态置 `待验收`。

## 证据

- 一键证据脚本：`build-bootrom` + PTE 解析断言 + `check-arch`/`check-inst` + 门控，输出 `RUN_EXIT`。
- 注入脚本：改一处 PTE（`0xC`→`0xF` 或 PPN 旧值）⇒ FAIL ⇒ `cp`+`md5sum -c` 还原 ⇒ 回绿，输出 `INJECT_EXIT`。
- 完成区只写结论 + 命令 rc + “运行期证据已清理，未归档”。

## 说明

- 本任务只同步测试资产到 D10，不新增 smon 执行路径；M11 仍不验收 smon。
- `hmon.S` 的 `U=J=0` 改动可能影响依赖 U/J 访问的 Node 用例；若 `check-arch`/`check-inst` 出现退化，先定位是测试资产错误还是 spec 口径问题，保留现场后报告。
- 不改 `smon` 的退出码/magic/观察寄存器布局。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
