# QEMU-048m: M5 qemu 里程碑

**模块**：qemu
**项目里程碑**：M5
**状态**：里程碑
**目标**：QEMU 支持 M5——① **SEE/HEE 运行环境**：四运行模式、cfx 寄存器/掩码/权限/`switch_run_mode`/异常进入流程（`DADAO-12 §5`）；**权限范围 = `cfx0/1/2/3/63`**；未实现 cfx ⇒ **`CFXREG`**，reserved ⇒ ILLI；② **`trap`/`escape` 语义**（一般 trap 进入向量、escape 退出恢复/步进）+ **`cfx2rd`/`cfx2rc` 执行**；③ **semihosting**：`immu18[17:16]==2'b11` 译码层短路 + `common-semi-target.c` 钩子（按 `n` 选 bank：`n=0`→`rd16`、`n=1`→`rb16`、返回→`rd31`）+ 复用 `do_common_semihosting` + **完整 25 服务** + `SYS_EXIT` 替代 exit port；④ **新 bootrom**（`-bios`、复位向量不变 `0xffff_ffff_0000`、hypv→user、含链接脚本）+ 端到端启动（LLVM 新指令首个真实用户）；⑤ **RAM@0 双映射**（`ADR-0004 R3`/`ADR-0020 D15`，C1 **step1**：**RAM@0 新段 + 旧 RAM 段并存** + `check-interface` 新断言〔旧断言保留〕+ 越界访问/取指异常语义；**step2 迁移另立、M5 之外**）。
**关联任务**：`QEMU-044t`、`QEMU-045t`、`QEMU-046t`、`QEMU-049t`、`QEMU-047t`（5 个；`QEMU-049t` = C1 step1 RAM@0 双映射）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`components/qemu/patches/target/dadao/**` + `hw/dadao/**`（模式/cfx/权限/异常/trap/escape/cfx2*/semihosting/bootrom/**RAM@0 双映射**）+ 探针 `tools/qemu/min_rom_probe_04{4,5,6,7,9}t.py`（或 `.work/evidence/`）
- `make build-qemu` EXIT=0
- **RAM@0 双映射（`ADR-0004 R3`/`ADR-0020 D15`，C1 step1）**：RAM@0（`0x0000_0000_0000`）**与旧 RAM 段（`0xffff_0000_0000`）并存**；`check-interface` **新增 RAM@0 断言 + 旧断言保留**；越界访问/取指异常（`CFXMEM`/测试机约定 `unmapped 0x87`，含取指）语义按 `ADR-0020 D15`（**step2 迁移另立、M5 之外**）
- 四运行模式/cfx 寄存器/mask 屏蔽/`switch_run_mode`/权限反例（**cfx 级**：`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕；**`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `DADAO-12 §2.2` PTBR 权限层、不在 M5**〔`ADR-0020 D9`〕）/reserved ⇒ ILLI（真实探针）
- 一般 trap 进向量 + escape 返回（含负偏移）；`cfx2rd`/`cfx2rc` 读写
- semihosting：判定短路（不进入向量、PC 步进）；钩子 bank（`rd16`/`rb16`/`rd31`）；**25 服务各 ≥1 例**；`SYS_EXIT` 码传播；`SYSTEM`/D2 文件档
- 新 bootrom：`-bios`、复位 PC `0xffff_ffff_0000`、初始化生效、hypv→user、端到端 EXIT=0（**M5 正向 = bootrom(`-bios`) + bin**；**「`-bios`+ELF」组合 / ELF loader 扩表〔`dadao_load_regions[]`+RAM@0〕移 M6**——用户 2026-10-08 裁定，见 `INTEG-019k` §第 8 轮、`ISS-168`）
- 不回归：`make check`/`check-qemu-semantics` EXIT=0；`test-codegen` 15/15、`test-elf` 5/5；`check-patch-tree` EXIT=0；`.work/source/qemu` clean

## 核验记录（主会话）

**M5 qemu 里程碑核验（2026-10-08，architect 代主会话）**　**判决：满足，置 `里程碑`**

证据来源：`QEMU-044t/045t/046t/047t/049t` 完成区/审阅记录、`.work/log/qemu/QEMU-04{4,5,6,7,9}t-*.log`、`.work/log/integ/INTEG-020t-test-semihost.log`、`.work/log/integ/INTEG-020t-check.log`；独立只读复核（`ls`/`git -C .work/source/qemu`/`check_patch_tree.py --source-state`/`check_interface_alignment.py`）。

| # | 核验项 | 证据（真实） | 结论 |
| --- | --- | --- | --- |
| 1 | 关联任务 5 个均 `已验证` | `QEMU-044t/045t/046t/047t/049t` 头部均 `**状态**：已验证` | ✅ |
| 2 | 产出：`components/qemu/patches/{target/dadao,hw/dadao}/**` + 探针 `tools/qemu/min_rom_probe_04{4,5,6,7,9}t.py` | `ls`：`patches/target/dadao/`（`cpu.c.patch`/`helper.c.patch`/`insn_trans/`…）、`patches/hw/dadao/`（`dadao-machine.c.patch`…）；5 个探针均在 `tools/qemu/`（随产物入库） | ✅ |
| 3 | `make build-qemu` EXIT=0 | `QEMU-049t-build.log` 末 `build-qemu: PASS` | ✅ |
| 4 | **RAM@0 双映射**（`ADR-0004 R3`/`ADR-0020 D15`，C1 step1） | `check_interface` 含 `RAM0_BASE=0x0`/`RAM0_SIZE=16MiB`/`RAM0 hw registration`（`init_ram`+`add_subregion`）+ 旧 RAM 断言保留；探针 `min_rom_probe_049t.py` **9/9**（`ram0_rw`/`old_ram_rw`/`no_interference`/`ram0_top`/`ram0_exec`） | ✅ |
| 5 | 越界访问/取指异常（`CFXMEM 0x81` / 测试机约定 `unmapped 0x87`，含取指） | `049t` 探针：`oob_data_cfxmem`/`oob_fetch_cfxmem` ⇒ `0x81`；`oob_data_unmapped`/`oob_fetch_unmapped` ⇒ `0x87`；`reserved` 亦 | ✅ |
| 6 | 四运行模式/cfx 寄存器/mask/`switch_run_mode`/权限反例（cfx 级 `ILLI`/`CFXREG`）/reserved ⇒ ILLI | 探针 `min_rom_probe_044t.py` **13/13**（reserved ⇒ `ILLI`；未实现 cfx / scratch 越界 / RO 写 ⇒ `CFXREG`） | ✅ |
| 7 | 一般 trap 进向量 + escape 返回（含负偏移）；`cfx2rd`/`cfx2rc` 读写 | 探针 `min_rom_probe_045t.py` **14/14**（含负偏移回退、跨 cfx、cg0–cg7 全寄存器面） | ✅ |
| 8 | semihosting：判定短路（不进向量、PC 步进）；钩子 bank（`rd16`/`rb16`/`rd31`）；25 服务各 ≥1；`SYS_EXIT` 码传播；`SYSTEM`/D2 文件档 | 探针 `min_rom_probe_046t.py` **32/32**；`INTEG-020t-test-semihost.log:443` `service coverage: all 25 service ids exercised` / `RESULT: PASS` | ✅ |
| 9 | 新 bootrom：`-bios`、复位 PC `0xffff_ffff_0000`、初始化生效、hypv→user、端到端 EXIT=0（M5 正向 = bootrom+bin） | 探针 `min_rom_probe_047t.py` **13/13**（reset PC / 7 项初始化 / hypv→user `MODE=0` / 无 supv / 栈在 RAM@0 / E2E `$?=0`）；门控 `run_m5_e2e` `m5_trap_escape` 等端到端通过 | ✅ |
| 10 | 不回归：`make check`/`check-qemu-semantics` EXIT=0；`test-codegen` 15/15、`test-elf` 5/5；`check-patch-tree` EXIT=0；`.work/source/qemu` clean | `INTEG-020t-test-semihost.log`：`check-qemu-semantics: PASS`（149/149）、`check-no-residue: PASS`、test-elf 5/5、test-codegen 15/15、`repository checks: PASS`；本次跑 `check-patch-tree: 92 patches OK`、`--source-state`：`qemu: OK HEAD=26010f599dfb count=1 clean=True` | ✅ |

**`check-interface` 计数说明（85 vs 86，非回归）**：`QEMU-049t` 时点 `check-interface` = **86**（80→86，新增 6 条 RAM@0/越界断言，`QEMU-049t-check-interface.log:95`）；其后 `TESTCASES-034t`（exit-port→`SYS_EXIT` 迁移）**移除 1 条** `harness.EXIT_PORT=EXIT_PORT_BASE` 断言（harness 已不再使用 `EXIT_PORT`）⇒ 现为 **85**（`INTEG-020t-check.log:149`；本次独立跑 `check_interface_alignment.py` 亦 85）。RAM@0 全部断言保留，属**已披露的正常迁移**。

**跨模块影响处置**：

| 项 | 性质 | 处置 | 是否阻断 |
| --- | --- | --- | --- |
| `ISS-164`（cfx mask 步骤 3/4/5 屏蔽路径不可观测，`scope[qemu,M5]`） | 测试机可观测性局限 | **登记跟踪**：当后续里程碑实现带可屏蔽 cause 的 cfx 后须补验；M5 门槛不受影响 | 否 |
| `ISS-165`（RAM@0 C1 step2 迁移，`scope: M6`） | 跨模块（testcases/qemu/integ） | 用户 2026-10-08 裁定随 M6；step1 双映射保门控全绿 | 否 |
| `ISS-167`（`DADAO-12 §5` prose/伪代码张力） | 文档措辞（实现按伪代码、正确） | 登记 + 建议另立 spec 任务（待授权） | 否 |
| `ISS-168`（`-bios`+ELF 组合 / loader 扩展 / 组合 ADR，`scope: M6`） | 加载模型 | 用户 2026-10-08 裁定移 M6（M5 正向 = bootrom+bin） | 否 |
| `ISS-169`（6 探针保留 exit-port，`scope[qemu,testcases,M6]`） | 测试侧迁移例外 | 已披露（`006t/008t/009t/010t/012t/013t`），不影响 M5 门槛（进门控项均迁 `SYS_EXIT`） | 否 |

**无未处置跨模块项。**

## 审阅记录

#### 口径全局对齐（architect，2026-10-08）

- **改动**：核验「权限反例」行由「`NU/J/SP/HPERM` 或 `CFXREG`」对齐为 **cfx 级 `ILLI`/`CFXREG`**（保留 `NUPERM…` 出处说明）。
- **依据**：已确认的 **`ADR-0020 D9`**——M5 权限范围只做 `cfx0/1/2/3/63`；**`NUPERM/NJPERM/NSPERM/NHPERM` 属 `DADAO-12 §2.2` PTBR 权限层、不在 M5**；**M5 可观测的权限反例 = cfx 级**：`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕。
- **性质**：与既定决策的一致性修正，非新增范围。同批口径对齐见 `INTEG-019k`/`INTEG-020t`/`INTEG-021m`（提交 `33c36a2`）及 `QEMU-044t` 审阅记录留痕（本提交）。**`spec/` 零改动。**

#### M5 模块里程碑核验（architect，2026-10-08）

**判决**：**满足 ⇒ `**状态**` 置 `里程碑`**。5 关联任务全 `已验证`；10 项核验逐条通过（SEE/HEE 四模式/cfx 权限、`trap`/`escape`/`cfx2*`、semihosting 判定短路+钩子 bank+25 服务+`SYS_EXIT`、新 bootrom `-bios`、RAM@0 双映射 C1 step1、门控不回归）。跨模块项（`ISS-164/165/167/168/169`）均已登记/M6，无未处置项。逐条证据见上「核验记录（主会话）」。

**核对说明**：`check-interface` 计数 86（`QEMU-049t` 时点）→ **85**（现）= `TESTCASES-034t` 移除 1 条 `harness.EXIT_PORT` 断言（exit-port 迁移之正常结果），非本模块回归。

**边界**：本次仅改本文件（`**状态**` 字段 + `## 核验记录（主会话）` + 本记录）；**`spec/` 交集为空**；未触 `components/**`/`contracts/**`/`Makefile`/`tools/**`；未新增/删除任务。
