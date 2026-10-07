# QEMU-048m: M5 qemu 里程碑

**模块**：qemu
**项目里程碑**：M5
**状态**：待开始
**目标**：QEMU 支持 M5——① **SEE/HEE 运行环境**：四运行模式、cfx 寄存器/掩码/权限/`switch_run_mode`/异常进入流程（`DADAO-12 §5`）；**权限范围 = `cfx0/1/2/3/63`**；未实现 cfx ⇒ **`CFXREG`**，reserved ⇒ ILLI；② **`trap`/`escape` 语义**（一般 trap 进入向量、escape 退出恢复/步进）+ **`cfx2rd`/`cfx2rc` 执行**；③ **semihosting**：`immu18[17:16]==2'b11` 译码层短路 + `common-semi-target.c` 钩子（按 `n` 选 bank：`n=0`→`rd16`、`n=1`→`rb16`、返回→`rd31`）+ 复用 `do_common_semihosting` + **完整 25 服务** + `SYS_EXIT` 替代 exit port；④ **新 bootrom**（`-bios`、复位向量不变 `0xffff_ffff_0000`、hypv→user、含链接脚本）+ 端到端启动（LLVM 新指令首个真实用户）；⑤ **RAM@0 双映射**（`ADR-0004 R3`/`ADR-0020 D15`，C1 **step1**：**RAM@0 新段 + 旧 RAM 段并存** + `check-interface` 新断言〔旧断言保留〕+ 越界访问/取指异常语义；**step2 迁移另立、M5 之外**）。
**关联任务**：`QEMU-044t`、`QEMU-045t`、`QEMU-046t`、`QEMU-049t`、`QEMU-047t`（5 个；`QEMU-049t` = C1 step1 RAM@0 双映射）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`components/qemu/patches/target/dadao/**` + `hw/dadao/**`（模式/cfx/权限/异常/trap/escape/cfx2*/semihosting/bootrom/**RAM@0 双映射**）+ 探针 `tools/qemu/min_rom_probe_04{4,5,6,7,9}t.py`（或 `.work/evidence/`）
- `make build-qemu` EXIT=0
- **RAM@0 双映射（`ADR-0004 R3`/`ADR-0020 D15`，C1 step1）**：RAM@0（`0x0000_0000_0000`）**与旧 RAM 段（`0xffff_0000_0000`）并存**；`check-interface` **新增 RAM@0 断言 + 旧断言保留**；越界访问/取指异常（`CFXMEM`/测试机约定 `unmapped 0x87`，含取指）语义按 `ADR-0020 D15`（**step2 迁移另立、M5 之外**）
- 四运行模式/cfx 寄存器/mask 屏蔽/`switch_run_mode`/权限反例（`NU/J/SP/HPERM` 或 `CFXREG`）/reserved ⇒ ILLI（真实探针）
- 一般 trap 进向量 + escape 返回（含负偏移）；`cfx2rd`/`cfx2rc` 读写
- semihosting：判定短路（不进入向量、PC 步进）；钩子 bank（`rd16`/`rb16`/`rd31`）；**25 服务各 ≥1 例**；`SYS_EXIT` 码传播；`SYSTEM`/D2 文件档
- 新 bootrom：`-bios`、复位 PC `0xffff_ffff_0000`、初始化生效、hypv→user、端到端 EXIT=0
- 不回归：`make check`/`check-qemu-semantics` EXIT=0；`test-codegen` 15/15、`test-elf` 5/5；`check-patch-tree` EXIT=0；`.work/source/qemu` clean

## 核验记录（主会话）

（核验命令、输出与退出码；结论）
