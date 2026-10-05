# QEMU-042t: QEMU ELF 加载器（`Ehdr`/`Phdr`/装载/`e_entry`）

**模块**：qemu
**项目里程碑**：M4
**依赖**：`SPEC-107t`、`SPEC-109t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-107t` 调整后的 `.tao/adr/adr-0004-test-machine.md`（ELF 加载约定：解析 `Ehdr`/`Phdr`、按 `VA=PA` 装载 LOAD 段、跳 `e_entry`；**保留 raw-bin 双镜像路径**）与 `.tao/knowledge/contract-elf.md §5/§6`。
  - 现有 `.work/source/qemu/hw/dadao/dadao-machine.c`（实测：只 `load_image_targphys_as` 把 `-bios` 载入 ROM `0xffff_ffff_0000`、`-kernel` 载入 RAM `0xffff_0000_0000`，**不解析 ELF、不读 `e_entry`**；启动经 ROM trampoline）。
  - `ADR-0004` D1（内存映射）、D2.3（双镜像协议）、D3（exit port）、D5.6（区域×访问矩阵）、D5.8（fault 退出码）。
- **输出**（组件源码改在 `.work/source/qemu`；导出补丁）：
  1. `hw/dadao/` 的 ELF 加载器：识别并解析 `Elf64_Ehdr`/`Elf64_Phdr`（大端）；校验 `EI_CLASS=ELFCLASS64`、`EI_DATA=ELFDATA2MSB`、`e_machine=EM_DADAO(0x0DA0)`、`e_flags[7:0]=1`（`contract-elf §1`）；按 `VA=PA` 将 **PT_LOAD** 段装入映射区域（RAM/ROM，按段 `p_vaddr`/`p_memsz`，`p_filesz` 数据 + `.bss` 零填充）；启动 PC = **`e_entry`**（或按 `SPEC-107t` 修订约定）。
  2. **raw-bin 兼容**：既有 `-bios`+`-kernel`(flat) 路径**不回归**（M3 `make test-codegen` 依赖）；区分方式按 `SPEC-107t` 修订约定（建议按 ELF magic `0x7F 'E' 'L' 'F'` 自动判别）。
  3. **负例（畸形 ELF 显式拒绝）**：magic/class/dataEncoding/machine/flags/`e_type` 不符、`Phdr` 越界、`p_filesz > p_memsz`、装载越出映射区域等 → **启动加载阶段报错并非零退出**，**不得**静默截断/部分加载/继续执行（对齐 `ADR-0004` D2.3「工具/加载错误」层，与 guest fault 分层）。
  4. **加载期 over-size 守卫（本任务新增）**：装载前对**尺寸**做显式上界检查——① **ROM blob > 64 KiB**（`ADR-0004` D1：ROM `0xffff_ffff_0000`–`0xffff_ffff_ffff`）；② **镜像（含 `.bss` 的 `p_memsz`）超出 RAM 16 MiB**（`0xffff_0000_0000`–`0xffff_00ff_ffff`）；③ 装载区间越出映射区域 ⇒ **显式报错、非零退出**（信息含实际尺寸与区域上限），**MUST NOT** 静默截断/部分加载。（呼应 `LLVM-056t` 的 `MEMORY`/`ASSERT` 链接期守卫：链接期拦不住的手工/异常 ELF 由加载期兜底。）
  5. 探针/证据：`tools/qemu/min_rom_probe_042t.py`（或 `.work/evidence/QEMU-042t/`）——ELF 正常装载+`e_entry` 生效、raw-bin 兼容、≥3 类畸形 ELF 拒绝、**≥2 类 over-size 拒绝**；含反例注入自检。
- **约束**：
  - **不改 guest 执行语义**（decode/trans 不动）；不动 `target/dadao/**` 指令翻译。
  - **加载错误与 guest fault 分层**：加载阶段错误走 QEMU 非零退出（非 `ADR-0004` D5.8 的 guest 码通道）。
  - **over-size 守卫（本任务新增）**：装载前校验 **ROM blob ≤ 64 KiB**、**镜像（含 `.bss` 的 `p_memsz`）≤ RAM 16 MiB**；超限 ⇒ 显式报错 + 非零退出，不得静默截断/部分加载/继续执行。上界取 `ADR-0004` D1 的 `DADAO_ROM_SIZE`/`DADAO_RAM_SIZE`（与 `LLVM-056t` 的 `MEMORY`/`ASSERT` 链接期守卫互为兜底）。
  - **补丁纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/qemu` 工作树；导出补丁写 `/tmp`、非空 blob；`make check-patch-tree`（含断言⑥）通过；不手改补丁。
  - 构建：`make build-qemu`（**5–20 分钟**，开始前写明预计耗时；`JOBS` 限制）；失败即停、不自动重试。
  - 临时目录 `/tmp/opencode/QEMU-042t/`；**不提交 git**；复杂命令输出留存 `.work/log/qemu/`。

## 验收标准

1. 构建 `make build-qemu` EXIT=0。
2. **ELF 装载**：一个 `EM_DADAO` ELF（`LLVM-056t` 产出或手工构造的等价最小 ELF）→ `qemu-system-dadao` **按 `e_entry` 进入**、执行到 exit port、`$?` 等于期望 guest 码（真实命令+输出）。
3. **段装载**：`.data`/`.rodata` 初值按 VA=PA 正确就位、`.bss` 零填充（探针读出校验，含非零数据）。
4. **raw-bin 兼容**：既有 `-bios trampoline.bin -kernel flat.bin` 路径 EXIT 与 `e_entry` 前行为一致（用一个 M3 用例复跑）。
5. **负例**：≥3 类畸形 ELF（错 magic / 错 `e_machine` / 错 `EI_DATA` / `p_filesz > p_memsz` 等）→ QEMU **非零退出**、错误信息明确；给出真实输出。
6. **over-size 负例（本任务新增）**：≥2 类尺寸超限——ROM blob > 64 KiB、镜像（含 `.bss`）> RAM 16 MiB——→ QEMU **非零退出**、错误信息含实际尺寸与区域上限；并验证**恰好填满**（边界值）**不报错**（不误杀）；给出真实输出。
7. **不回归**：`make check`/`make check-qemu-semantics` EXIT=0；`make test-codegen`（M3 15/15）EXIT=0（说明走 raw-bin 兼容路径）。
8. 一键证据脚本 `.work/evidence/QEMU-042t/run.sh`（含 `--inject`：把 `e_entry` 装载改为 RAM 基址 / 关掉某校验 / 放宽 over-size 上界 → 期望 FAIL → 还原+**重建** → 回绿；结尾无 `tee`）。
9. `<源注释/section 扫描>`：`git status` 仅本任务应有改动。

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
（审查者独立验证的重跑记录、约束核验、判决）
