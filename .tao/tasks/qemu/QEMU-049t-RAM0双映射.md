# QEMU-049t: RAM@0 双映射（C1 step1；`ADR-0004 R3` / `ADR-0020 D15`）

**模块**：qemu
**项目里程碑**：M5
**依赖**：`QEMU-044t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **定位**：实现 `ADR-0004 R3`（**RAM 基址改为全 0**）的 **C1 双映射过渡 step1（M5）** 与 `ADR-0020 D15`（核内地址空间划分 + **越界访问/取指异常**）的机器模型部分。**step1 = 过渡态**：QEMU 机器模型**同时映射 RAM@0（新，供 bootrom/SEE）+ 保留旧 RAM 段（`0xffff_0000_0000`，供既有测试）**；`check-interface` 断言**新增** RAM@0 段（**旧断言保留**）⇒ **每任务门控保持全绿**。**step2**（旧向量/harness 迁到 `0` + 删旧 RAM 段 + 收紧断言）**另立、M5 之外**（不在本任务）。
- **输入（自包含）**：
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，**D15**）+ `adr-0004` 修订（**R3**：RAM 基址改全 0 + C1 双映射两步；**D1** 内存映射、**D5.6** 内存区域×访问矩阵、**D5.8** fault 码表〔**已冻结、不得重排**〕）。
  - `spec/DADAO-12-SEE-主管系统运行环境.md §2.1`（核内地址空间：地址高 6 位 `bits[47:42]` = cfxha；`cfxha 63 = power` 段含复位向量 `0xffff_ffff_0000`；`L73` 核内地址空间非法访问 ⇒ **CFXMEM**）、`§2.2`（PTBR 权限）。
  - `spec/DADAO-12` 异常原因表（`CFXMEM = 1<<1`）。
  - `QEMU-044t`（cfx 寄存器/掩码/权限/**异常进入流程**：CFXMEM 等同步异常的进入路由归其提供，本任务只**检测并抛出** `CFXMEM`）。
  - 组件现状（实测，`.work/source/qemu` + `components/qemu/patches/`）：
    - `components/qemu/patches/target/dadao/cpu.h.patch:63-64`：`DADAO_RAM_BASE 0xffff00000000ULL` / `DADAO_RAM_SIZE (16 * 1024 * 1024)`；`:65` `DADAO_EXIT_PORT_BASE 0xffff80000000ULL`。
    - `components/qemu/patches/target/dadao/helper.c.patch:103`：`addr >= DADAO_RAM_BASE && addr < DADAO_RAM_BASE + DADAO_RAM_SIZE`（RAM 判定）。
    - `components/qemu/patches/hw/dadao/dadao-machine.c.patch:183`（`{ "RAM", DADAO_RAM_BASE, DADAO_RAM_SIZE }`）、`:485-486`（`memory_region_init_ram(... DADAO_RAM_SIZE ...)` + `memory_region_add_subregion(system_memory, DADAO_RAM_BASE, ram)`）。
    - 门控 `check-interface`（∈ `make check`，`tools/integ/check_interface_alignment.py`）：**硬断言** `RAM_BASE`（`:319` `ram_base_exp = 0xFFFF_0000_0000`）、`RAM_SIZE`（`:320` `16 * 1024 * 1024`）、exit port（`:351` 起）。
- **输出**：
  1. **机器模型双映射（`hw/dadao/dadao-machine.c` + `target/dadao/cpu.h`）**：**新增 RAM@0 段**（`0x0000_0000_0000` 起，cfxha 0 = `umon` 段；供 bootrom/SEE）——新增宏（如 `DADAO_RAM0_BASE`/`DADAO_RAM0_SIZE`）+ `memory_region_init_ram` + `memory_region_add_subregion(system_memory, <RAM0 base>, ...)`；**保留旧 RAM 段**（`DADAO_RAM_BASE`/`DADAO_RAM_SIZE`，`0xffff_0000_0000`，16 MiB，供既有测试）。**两段并存、互不重叠**。
  2. **RAM@0 链接基址**：为 bootrom/SEE 的**链接脚本片段**提供 RAM@0 基址（`0x0000_0000_0000`），供 `QEMU-047t` 链接 bootrom 栈/数据用；**ROM 段（`0xffff_ffff_0000`）链接脚本仍归 `QEMU-047t`**。
  3. **`check-interface` 断言增补**（`tools/integ/check_interface_alignment.py`）：**新增** RAM@0 段断言（基址 `0x0000_0000_0000` + 大小 + `hw/dadao` 注册点）；**旧 `RAM_BASE=0xFFFF_0000_0000` / `RAM_SIZE=16MiB` 断言保留**（过渡态）。
  4. **越界（访问/取指）异常语义（`ADR-0020 D15`）**：按 `ADR-0020 D15` 写定的口径实现机器模型侧检测——**核内地址空间越界访问**与**越界取指**均须报异常（**含取指路径**）；语义区分 **`CFXMEM`**（spec 核内地址空间非法访问；`DADAO-12 §2.1:73`，`1<<1` ⇒ 退出码 `0x81`）vs **测试机约定 `unmapped 0x87`**（`ADR-0004 D5.8`）。**`ADR-0004 D5.8` fault 码表已冻结、不得重排**（不得改动 `0x87`–`0x8D` 既有码；`CFXMEM` 落表中已保留的 `0x81`）。**异常进入流程归 `QEMU-044t`**（本任务只检测/抛出，不改其路由）。
  5. **探针/证据**：`tools/qemu/min_rom_probe_049t.py`（或 `.work/evidence/QEMU-049t/`）——RAM@0 可读写、旧 RAM 段仍可读写、两段互不干扰、越界访问/取指报对应异常。
- **约束（硬）**：
  - **旧 RAM 段（`0xffff_0000_0000`）必须保留**（过渡态；删段/迁移属 **step2、另立**，不在本任务）。
  - **不改 guest 标量指令执行语义**；**不改 exit port / fault→退出码既有映射**（`ADR-0004`/`ADR-0011`）；**不改 `0x87`–`0x8D` 码**。
  - **补丁纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/qemu`；导出补丁写 `/tmp`、非空 blob；`make check-patch-tree`（含断言⑥）通过；不手改补丁。
  - **门控不得红**：`make check`（含 `check-interface`，**新断言 + 旧断言都过**）EXIT=0。
  - **重建成本申报**：`make build-qemu`（**5–20 分钟**）；开工前写明预计耗时；受 `JOBS`（默认 8）限制；失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/QEMU-049t/`；**不提交 git**；复杂命令输出留存 `.work/log/qemu/`（**禁 `tee`**）。
  - **注入/还原纪律**：注入后**还原须含重建**；用 `cp`+`md5` 对账，**禁 `git checkout`/`git restore`/`git stash`**。

## 验收标准

1. **构建**：`make build-qemu` EXIT=0；给真实输出。
2. **双映射**：RAM@0（`0x0000_0000_0000`）可读写、**旧 RAM 段（`0xffff_0000_0000`）仍可读写**、两段互不干扰（探针真实输出，≥2 例）。
3. **`check-interface`**：断言**新增** RAM@0 段且**保留**旧 RAM 段断言；`make check` **EXIT=0**（给真实输出；改前/改后 `check-interface` 逐项）。
4. **越界异常**：按 `ADR-0020 D15` 口径——**越界访问**与**越界取指**均报对应异常（`CFXMEM` ∈ 表中已保留 `0x81` / 测试机约定 `unmapped 0x87`），且**含取指路径**（探针真实输出，≥2 例含取指）；**未重排 `0x87`–`0x8D`**。
5. **不回归**：`make test-codegen` 15/15、`make test-elf` 5/5、`make check-qemu-semantics` EXIT=0；`check-patch-tree` EXIT=0。
6. **一键证据脚本**：`.work/evidence/QEMU-049t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（去掉 RAM@0 映射 / 改 RAM@0 基址 / 删越界取指检测 ⇒ 期望 **FAIL** ⇒ 还原 + **重建** ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
7. **无残留**：`git status --untracked-files=all` 仅组件补丁 + `tools/integ/check_interface_alignment.py` + 探针 + 本任务书；`.work/source/qemu` worktree clean。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**（去 RAM@0 映射/删越界取指检测 → 重建 → FAIL → 还原+重建 → 回绿）+ 核双映射/`check-interface` 新旧断言/越界取指 + 判决）
