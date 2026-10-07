# QEMU-047t: 新 bootrom（构建 + 链接 + 端到端启动）

**模块**：qemu
**项目里程碑**：M5
**依赖**：`LLVM-060t`、`QEMU-044t`、`INFRA-047t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `LLVM-060t`（自有工具链能编 `trap`/`escape`/`cfx2rd`/`cfx2rc`）；`QEMU-044t`（cfx 寄存器/权限/异常进入流程）；`INFRA-047t`（install 根可执行）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，**D12**）+ `adr-0004` 修订（**R1**：`-bios` 加载、复位向量不变 `0xffff_ffff_0000`；bootrom **hypv→user 直跳、本版不启用 supv**）。
  - `spec/DADAO-12 §2.1`（复位向量 `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`，64 KiB）；`§3`（cfx 寄存器初始化：异常向量 `cfx_umon_user_excp_vector`、`global_cfx_mask` 清除对应位等，`DADAO-22 §3` 初始化范式）；`spec/DADAO-22 §1`（调用/返回约定，`escape cfxha,[excp_cause_ip,4]`）。
  - `.tao/knowledge/contract-elf.md §5/§6`（`EM_DADAO=0x0DA0`、`e_flags=1`、段对齐 `.text 4B`、VA=PA；ELF 路径 `-kernel image.elf` 取 `e_entry`；raw-bin 双镜像路径 `-bios rom.bin -kernel test.bin`）；`tests/scripts/dadao.lds`（M4 链接脚本，地址布局参考）。
  - `spec/Process-01`（补丁纪律，若涉 `components/**`）。
- **输出**：
  1. **bootrom 固件源码**（自有汇编 + 自有工具链）：初始化——设置各 cfx（至少 `cfx_umon`/`cfx_power`）的异常向量、`global_cfx_mask`/指令类型 mask 允许所需调用；**初始化完成后 hypv → user 直跳**（设置 `switch_run_mode` + 经 `escape` 或等价路径进入 user；**本版不启用 supv、不涉及 smon**）。**落点（用户裁定 2026-10-07）：固件源码放 `tests/scripts/`**。
  2. **构建/链接接入（`Makefile`）**：用自有工具链（`llvm-mc`/`ld.lld` + `dadao.lds` 式链接脚本）汇编/链接 bootrom；**含 bootrom 链接脚本**——地址布局对齐 `0xffff_ffff_0000` 的 **64 KiB ROM 区**、段序/对齐依 `ADR-0004`/`contract-elf`；产物 = bootrom 镜像（`-bios` 加载格式）。**生成物落点（用户裁定 2026-10-07）：放 `.dadao/` 下**——按落点规则：**运行产物默认 `.dadao/tests/`**；能靠配置解决的不算"难"，一律放 `.dadao/`（建议 `.dadao/tests/bootrom/`）。
  3. **加载模型**：**`-bios` 加载 bootrom**、**复位向量不变 `0xffff_ffff_0000`**；bootrom 跳应用（应用为 ELF 或 raw-bin，据 `adr-0004` 修订后的路径关系，与 `QEMU-042t` 加载器并存）。
  4. **端到端启动证据**：`qemu-system-dadao -M dadao-m1 -bios <bootrom> -kernel <app>`（或以修订后约定）启动 → bootrom 完成初始权限/向量配置 → 跳 user 应用执行（**LLVM 新指令 `trap`/`escape`/`cfx2*` 的首个真实用户**）。
  5. **探针/证据**：`tools/qemu/min_rom_probe_047t.py`（或 `.work/evidence/QEMU-047t/`）——bootrom 装载于 `0xffff_ffff_0000`、复位 PC 正确、初始化后寄存器/mask 生效、hypv→user 跳转、应用可达。
- **约束（硬）**：
  - **bootrom 用自有工具链编**（不得用外部/宿主汇编器绕过 `LLVM-060t`）——bootrom 就是新指令的第一个真实用户。
  - **复位向量不变 `0xffff_ffff_0000`、`-bios` 加载、hypv→user 直跳、本版不启用 supv**（`INTEG-019k` 裁定 5/6）。
  - **不回归**：M1–M4 的 raw-bin 双镜像与 ELF 路径（`make test-codegen`/`test-elf`）**不回归**；如与 bootrom 加载模型冲突，**停下报告**（属 `adr-0004` 修订范围，不得自行改契约）。
  - **补丁纪律（`spec/Process-01`）**：若改动 `components/qemu/**` 的 bootrom 内建/加载 → 只能在 `.work/source/qemu`；**bootrom 固件源码入库落 `tests/scripts/`**（用户裁定 2026-10-07）；**生成器/脚本随产物保留**（`AGENTS.md`「临时目录」）。
  - **落点（用户裁定 2026-10-07）**：**固件源码放 `tests/scripts/`**；**生成物放 `.dadao/` 下**（运行产物默认 `.dadao/tests/`；能靠配置解决的不算"难"，必须放 `.dadao/`，不得退到模块目录）。
  - **重建成本申报**：`make build-qemu`（**5–20 分钟**）+ `build-mc`/`build-lld`（增量）；开工前写明预计耗时；受 `JOBS` 限制；失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/QEMU-047t/`；**不提交 git**；复杂命令输出留存 `.work/log/qemu/`（**禁 `tee`**）。
  - **注入/还原纪律**：注入后**还原须含重建**；`cp`+`md5` 对账，**禁 `git checkout`/`git restore`/`git stash`**。

## 验收标准

1. **构建**：`make build-qemu` EXIT=0；bootrom 经自有工具链汇编/链接 EXIT=0（给真实输出，含 `llvm-mc`/`ld.lld` 命令）。
2. **链接脚本**：bootrom 链接脚本存在，地址布局对齐 `0xffff_ffff_0000` 的 64 KiB ROM 区（`llvm-readobj -h/-l` 证明 `e_entry`/段 VA 正确；真实输出）。
3. **加载**：`-bios <bootrom>` EXIT=0；复位 PC = `0xffff_ffff_0000`（探针/`-d cpu` 真实输出）。
4. **初始化生效**：bootrom 运行后目标 cfx 的异常向量/`global_cfx_mask` 按预期生效（探针真实输出）。
5. **hypv→user**：bootrom 初始化后跳 user 应用执行到完成（真实输出）；未启用 supv（可观测）。
6. **端到端**：bootrom + 一个应用（可含 `trap`/semihosting 的简单程序）端到端 EXIT=0。
7. **不回归**：`make test-codegen` 15/15、`make test-elf` 5/5、`make check` EXIT=0；`check-patch-tree` EXIT=0。
8. **一键证据脚本**：`.work/evidence/QEMU-047t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（改链接基址/去掉一段初始化 ⇒ 期望 **FAIL** ⇒ 还原 + **重建** ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
9. **无残留/落点**：`git status --untracked-files=all` 仅 bootrom 源码（**`tests/scripts/`**）/链接脚本 + 构建接入（`Makefile`）+ 组件补丁（若涉）+ 探针 + 本任务书；**生成物均在 `.dadao/tests/`**（不得残留于模块目录/仓库其它位置）。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**（改链接基址/初始化 → 重建 → FAIL → 还原+重建 → 回绿）+ 核 `-bios`/复位向量/hypv→user/不回归 + 判决）
