# QEMU-049t: RAM@0 双映射（C1 step1；`ADR-0004 R3` / `ADR-0020 D15`）

**模块**：qemu
**项目里程碑**：M5
**依赖**：`QEMU-044t`
**状态**：已验证

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

**测试结果**：探针 `tools/qemu/min_rom_probe_049t.py` **9/9 PASS**（`RESULT: PASS`，EXIT=0）；一键证据脚本 `.work/evidence/QEMU-049t/run.sh` **EVIDENCE: PASS**（`SCRIPT_EXIT=0`；含合并注入自检：3 反例 → 各自对应检查 FAIL → `cp`+`md5` 还原（相等）→ **重建** → 回绿）；`make check` EXIT=0（含 `check-interface` **86/86 PASS**、`check-qemu-semantics` **149/149**、`check-patch-tree` 90 patches）；`make test-codegen` **15/15** EXIT=0；`make test-elf` **5/5** EXIT=0。

**修改文件**（与 `git status --untracked-files=all` 一致）：
- `components/qemu/patches/hw/dadao/dadao-machine.c.patch`（M）— RAM@0 映射（`memory_region_init_ram("dadao-ram0")` + `add_subregion(system_memory, DADAO_RAM0_BASE, ram0)`）；旧 RAM 段保留；文件头内存图注释更新。
- `components/qemu/patches/target/dadao/cpu.h.patch`（M）— `DADAO_RAM0_BASE`/`DADAO_RAM0_SIZE`；`DADAO_EXIT_CFXMEM=0x81`；内部异常 `DADAO_EXCP_CFXMEM`；cfxha 宏（`DADAO_CFXHA_SHIFT/MASK/UMON`、`DADAO_ADDR_CFXHA`）。
- `components/qemu/patches/target/dadao/helper.c.patch`（M）— `dadao_excp_to_exit_code` 增 `CFXMEM→0x81`；`dadao_cpu_tlb_fill` 增 RAM@0 分支 + 越界故障按 cfxha 分类（umon 段越界 ⇒ `CFXMEM`；其余 ⇒ `unmapped`）。
- `components/qemu/changelog.md`（M，+1 行；`Process-01 §10` 要求，**非**残留）。
- `tools/integ/check_interface_alignment.py`（M）— **新增** RAM@0（基址/大小/`hw/dadao` 注册点）+ `EXIT_CFXMEM=0x81`/`CFXHA_UMON=0` 断言；**旧 RAM 断言保留**。
- `tools/qemu/min_rom_probe_049t.py`（新增，**随产物入库**）。
- `.work/evidence/QEMU-049t/run.sh`（gitignored，非入库）。
- 本任务书（完成区/自审/状态）。
- 组件源码改在 `.work/source/qemu`（本地收敛 commit〔amend `dadao: qemu patch series`〕，**不入 DADAO 库**）。

**验收结果**（真实命令输出/rc，日志在 `.work/log/qemu/`）：
1. **构建**：`make build-qemu JOBS=8` → `build-qemu: PASS` **EXIT=0**（`.work/log/qemu/QEMU-049t-build.log`）。
2. **双映射**：探针 `ram0_rw`（RAM@0 0x1000 读写 `0xCAFEF00D`）、`old_ram_rw`（旧 RAM 0xffff_0000_1000 读写）、`no_interference`（同偏移 0x2000 两段各自 `0xAAAA5555`/`0x13579BDF` 互不干扰）、`ram0_top`（RAM@0 顶 8B）、`ram0_exec`（写入代码到 RAM@0 并跳去除执行 → exit 0x5A）全 PASS（≥2 例满足）。
3. **`check-interface`**：**改前**（`HEAD` 版脚本）80 项 0 FAIL（旧 `RAM_BASE`/`RAM_SIZE`/`harness.BINARY_BASE` 断言）；**改后** 86 项 0 FAIL（`RAM0_BASE=0x0`/`RAM0_SIZE=16MiB`/`RAM0 hw registration (init_ram)`/`(add_subregion)`/`EXIT_CFXMEM=0x81`/`CFXHA_UMON=0` 六项新增 **PASS**，旧断言仍 PASS）；`make check` **EXIT=0**。
4. **越界异常**：`oob_data_cfxmem`（cfxha0 越界数据访问 0x0100_0000 ⇒ **0x81**）、`oob_fetch_cfxmem`（cfxha0 越界取指 ⇒ **0x81**）、`oob_data_unmapped`（cfxha63 越界数据 0xFC00_0000_0000 ⇒ **0x87**）、`oob_fetch_unmapped`（cfxha63 越界取指 ⇒ **0x87**）全 PASS（**取指 2 例**）；**未重排 `0x87`–`0x8D`**（`DADAO_EXIT_*` 逐项未改，`CFXMEM` 用已保留 `0x81`）。
5. **不回归**：`make check` EXIT=0、`check-qemu-semantics` **149/149** EXIT=0、`test-codegen` **15/15** EXIT=0、`test-elf` **5/5** EXIT=0、`check-patch-tree` **90 patches OK** EXIT=0（`.work/log/qemu/QEMU-049t-final-gates.log`）。
6. **一键证据脚本**：`.work/evidence/QEMU-049t/run.sh` **EVIDENCE: PASS**（`SCRIPT_EXIT=0`，`.work/log/qemu/QEMU-049t-evidence.log`）：合并注入 3 反例（去 RAM@0 机器映射 / 改导出补丁中 RAM@0 基址 / 去越界取指分类）→ 对应 `ram0_rw`、`check-interface`(`RAM0_BASE=0x0` FAIL)、`oob_fetch_cfxmem` **EXIT=1/1/1（FAIL）** → `cp`+`md5` 还原（相等）→ **重建** → 全绿；无 `tee`。
7. **无残留**：`git status --untracked-files=all` = 组件补丁 3 + `changelog.md` + `check_interface_alignment.py` + 新探针 + 本任务书；`.work/source/qemu` worktree **clean**；无 `*.orig`/`*.rej`/`*.preinject` 残留。

**新发现/坑**：
1. **既有「EA=0 ⇒ unmapped 0x87」向量/探针在 R3 下失效（需 step2 迁移）**：`tests/vectors/isa/{mem-rd,mem-rb,mem-ra,ctrl-*}.yaml` 与历史探针（如 `tools/qemu/min_rom_probe_010t.py` 的 T6/T18）以 EA=0 作「unmapped」用例；RAM@0 落在 0 后 EA=0 变为合法 RAM。**当前不在任何 `make` 门控内**（`check-qemu-semantics` 只跑 `reg-shift-extend`/`reg-compare`）⇒ 门控保持全绿；但属 **step2** 迁移范围（跨 testcases 向量 + qemu 探针）。建议登记跨模块影响。
2. **取指路径经同一 `tlb_fill`**：核内非法取指经 `get_page_addr_code`（probe）失败后由 `cpu_ldl_code_mmu`（`MMU_INST_FETCH`，probe=false）进入 `dadao_cpu_tlb_fill` ⇒ 在 `tlb_fill` 内按 `cfxha` 分类即**天然覆盖数据+取指两条路径**，无需另设取指钩子（基线实测 `jump` 到非法地址即得 `0x87`）。建议沉淀。
3. **越界路由口径（`QEMU-049t` 落地，`ADR-0020 D15` 授权）**：**umon 段（`addr[47:42]==0`）越界 ⇒ `CFXMEM`（0x81）**；其余（含旧 power 段 63）⇒ 测试机约定 `unmapped`（0x87）——保住既有 M1–M4 的 0x87 语义，同时给 SEE 新段 spec 正确的 `CFXMEM`。**RAM@0 容量 = 16 MiB**（与旧 RAM 对称，`ADR-0020 D15` 留白由本任务定并写 `check-interface`）。
4. **`0x81` 复用冻结表保留区**：`CFXMEM=1<<1` ⇒ `0x80|1=0x81`，落在 `ADR-0004 D5.8` 已保留 `0x81`–`0x86`，**无需新码/重排**；`check-interface` 的 `expected_fault_codes`/harness `FAULT_NAMES` **有意未扩**（harness 迁移归 step2，避免此刻误报）。
5. **注入 B 的落点**：`check-interface` 读的是**导出补丁**（`components/qemu/patches/**`），非编译源 ⇒ 「改基址」注入须落在补丁文件（且不移动二进制内 RAM@0 范围）；落在源 `cpu.h` 会同时移动二进制范围而与注入 C 相互干扰。建议沉淀（`make check` 门控类任务的反例注入落点 = 权威载体）。

**遗留问题**：
- **step2 迁移（另立、M5 之外）**：旧向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 + 收紧 `check-interface` 断言；含新发现 1 的「EA=0 unmapped」向量/探针更新。不在本任务。
- **ELF 加载器未扩 RAM@0**：`hw/dadao/dadao-machine.c` 的 `dadao_load_regions[]` 仍仅列旧 RAM + ROM ⇒ 链接进 RAM@0 的 **ELF 镜像段**暂不可加载。本任务范围（输出 1/2）只要求机器映射 + 提供 RAM@0 链接基址；`QEMU-047t`（应用加载/可达）若把应用 ELF 链进 RAM@0，需在其任务内扩该表（并加对应验证）。
- 其它 M5 项（PTBR 权限层、semihosting、`SYS_EXIT`）归各自任务。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

**自审范围**：逐行审查改动源码（`.work/source/qemu/{hw/dadao/dadao-machine.c, target/dadao/cpu.h, target/dadao/helper.c}`）+ 导出补丁 + `tools/integ/check_interface_alignment.py` + 探针 + 证据脚本；核对 Spec-first（`ADR-0004 D1/D5.8/R3`、`ADR-0020 D15`、`spec/Machine-01 §1.1/§1.2`、`spec/DADAO-12 §2.1`）、边界（旧 RAM 保留/码表不重排/不改标量语义）、防造假（真实执行）。

**结论**：逻辑正确、边界受控、门控全绿；发现并处理 2 处（1 修 + 1 记录），其余为已证伪/已记录。判决：**可置「待验收」**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本注入 B 落在**源** `cpu.h`：`check-interface` 读**导出补丁**（非编译源）⇒ B 不使 `check-interface` FAIL；且移动二进制内 RAM@0 范围致与注入 C 相互干扰（`oob_fetch_cfxmem` 注入后得 `0x89` 而非预期 `0x87`） | ✅已修 | `run.sh`：注入 B 改落**导出补丁** `components/qemu/patches/target/dadao/cpu.h.patch`（不移动二进制范围）；备份/还原与 md5 对账纳入该补丁 | 重跑 `run.sh` → `EVIDENCE: PASS`；`check_interface` 注入后 `RAM0_BASE=0x0 FAIL（实际 0x100000）` EXIT=1；`oob_fetch_cfxmem` 注入后 `exit exp=0x81 got=0x87` EXIT=1；还原 md5 相等 → 重建 → 86/86 全绿 |
| F2 `oob_fetch_cfxmem` 注入后退出码 | ⏸记录（并入 F1 说明） | 无（F1 修复后不复现） | 见 F1 |
| F3 边界：ELF 加载器 `dadao_load_regions[]` 未纳入 RAM@0 | ⏸记录（判为范围外+下游可控） | 无 | 完成区「遗留问题」；本任务输出 1/2 不含加载器；`QEMU-047t` 若需可扩 |
| F4 旧的「EA=0 ⇒ 0x87」向量/探针在 R3 下失效 | ⏸记录（step2 范围，非本任务门控） | 无 | 完成区「新发现 1」；`make check`/`check-qemu-semantics` 全绿（该批非门控） |
| F5 断言可达 FAIL | ✅已证 | 无（设计即含 FAIL 路径） | `run.sh` 三注入各自使 `ram0_rw`/`check-interface`/`oob_fetch_cfxmem` FAIL；还原+重建后回绿 |

**边界核查**：仅改任务书列出的文件（补丁 3 + `changelog.md` + `check_interface_alignment.py` + 探针 + 任务书）；`spec/` 交集空；旧 RAM 段保留（探针 `old_ram_rw` PASS）；`0x87`–`0x8D` 码未改（`check-interface` 旧码断言全 PASS）。**状态**：无未修 finding ⇒ 置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**（改 RAM@0 size 16→8 MiB → 重建 → FAIL → 还原+md5+重建 → 回绿）+ 核双映射/`check-interface` 新旧断言/越界取指/码表 + 判决）

**审查环境**：mimo-v2.5-pro；工作目录 `/mnt/tao/DADAO-v5`；临时目录 `/tmp/opencode/QEMU-049t-review/`。

##### 1. 证据脚本审核（`.work/evidence/QEMU-049t/run.sh`）

逐行审核 193 行脚本：
- `set -u`（行19）✓；所有 `rc=$?` 直接捕获退出码（非 `tee`）✓
- 注入 A（源 `dadao-machine.c`：去 RAM@0 映射 `init_ram`+`add_subregion`）✓
- 注入 B（导出补丁 `cpu.h.patch`：改 RAM0_BASE `0x0→0x100000`，**不移动二进制范围**）✓
- 注入 C（源 `helper.c`：加 `access_type != MMU_INST_FETCH` 条件使取指不走 CFXMEM）✓
- 注入后验证 `git diff --name-only` **非空**（行111-115）✓
- 三反例各自 FAIL：`ram0_rw` EXIT=1 / `check_interface` EXIT=1 / `oob_fetch_cfxmem` EXIT=1 ✓
- 还原用 `cp`+`md5sum` 对账（行147-156）✓；还原后 **重建**（行161）✓
- `fail` 累积器 + 最终 `exit 0/1`（行187-193）✓
- **可达 FAIL 路径**：三条注入各自独立命中不同检查项，无恒真 ✓
- **结论**：脚本合格，无需返工。

##### 2. 重跑证据脚本

```
$ bash .work/evidence/QEMU-049t/run.sh
...
[2/5] probe (all cases):
  [PASS] ram0_rw / old_ram_rw / no_interference / ram0_top / ram0_exec
  [PASS] oob_data_cfxmem / oob_data_unmapped / oob_fetch_cfxmem / oob_fetch_unmapped
  RESULT: PASS, probe(all) EXIT=0
[3/5] injection self-check:
  inject EXIT=0; rebuild(after inject) EXIT=0
  inject-check ram0_rw EXIT=1 (expected NON-zero) ✓
  inject-check check_interface EXIT=1 (expected NON-zero) — RAM0_BASE=0x0 FAIL ✓
  inject-check oob_fetch_cfxmem EXIT=1 (expected NON-zero) ✓
[4/5] restore:
  md5 equality: OK; rebuild(after restore) EXIT=0
  probe(all, post-restore) 9/9 PASS EXIT=0
  check_interface 86/86 PASS EXIT=0
  check_patch_tree 90 patches OK EXIT=0
[5/5] EVIDENCE: PASS
SCRIPT_EXIT=0
```

##### 3. 独立注入（reviewer 自行执行，与 engineer 不同）

**注入方式**：改源 `cpu.h` 的 `DADAO_RAM0_SIZE` 从 `16 * 1024 * 1024` → `8 * 1024 * 1024`（使 RAM@0 仅 8 MiB，`ram0_top` 写到 16 MiB 顶时越界）。

**注入前快照**：
```
md5: .work/source/qemu/target/dadao/cpu.h = 685644d9b4bd3f03ba47f6eb911c244a
git -C .work/source/qemu diff --name-only: (空)
```

**注入后验证**：
```
$ git -C .work/source/qemu diff --name-only
target/dadao/cpu.h          ← 非空 ✓
$ make build-qemu JOBS=8    ← BUILD_EXIT=0
$ python3 tools/qemu/min_rom_probe_049t.py --only ram0_top
  [FAIL] ram0_top → exit exp=0x0 got=0x81; rd5 exp=0xdeadbeef got=0x0
  PROBE_EXIT=1              ← 注入有效，ram0_top 因越界得 CFXMEM(0x81) ✓
$ python3 tools/qemu/min_rom_probe_049t.py --only old_ram_rw
  [PASS] old_ram_rw → ok   ← 注入特异，旧 RAM 不受影响 ✓
```

**还原**：
```
$ cp /tmp/opencode/QEMU-049t-review/cpu.h.orig .work/source/qemu/target/dadao/cpu.h
  md5 orig=685644d9b4bd3f03ba47f6eb911c244a restored=685644d9b4bd3f03ba47f6eb911c244a
  MD5_MATCH ✓
$ git -C .work/source/qemu diff --name-only: (空) ✓
$ make build-qemu JOBS=8    ← BUILD_EXIT=0（含重建）
$ python3 tools/qemu/min_rom_probe_049t.py
  9/9 PASS, RESULT: PASS, PROBE_EXIT=0 ← 回绿 ✓
```

**最终工作区对账**：
```
md5: dadao-machine.c.patch = 5b0cde3557f87d951a1d15465246f973 (与注入前一致)
md5: cpu.h.patch = 1cc1af2313ac272b5633df97f9cf1b20 (与注入前一致)
md5: helper.c.patch = df4b35b2428f012ab0b67c1c0e7fa30a (与注入前一致)
git status --porcelain -uall: (空)
git -C .work/source/qemu status --porcelain: (空)
```

##### 4. 验收 1–7 逐条

| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 构建 `make build-qemu` EXIT=0 | ✅ | 证据脚本 [1/5] + 独立注入重建均 EXIT=0 |
| 2 | 双映射：RAM@0 可读写 + 旧 RAM 可读写 + 互不干扰（≥2 例） | ✅ | `ram0_rw`(0xCAFEF00D) + `old_ram_rw`(0x0BADC0DE) + `no_interference`(0xAAAA5555/0x13579BDF) + `ram0_top`(0xDEADBEEF) + `ram0_exec`(exit 0x5A) 全 PASS |
| 3 | `check-interface`：改前 80→改后 86（新增 6 项 PASS，旧断言保留） | ✅ | 86/86 PASS（RAM0_BASE=0x0 / RAM0_SIZE=16MiB / init_ram / add_subregion / EXIT_CFXMEM=0x81 / CFXHA_UMON=0 六项新增 + 旧 RAM_BASE/RAM_SIZE 保留） |
| 4 | 越界异常：cfxha0⇒0x81 + cfxha63⇒0x87 + 含取指 + 未重排 | ✅ | `oob_data_cfxmem`⇒0x81 / `oob_fetch_cfxmem`⇒0x81 / `oob_data_unmapped`⇒0x87 / `oob_fetch_unmapped`⇒0x87（取指 2 例）；`0x87–0x8D` 码序不变（逐项核对 cpu.h.patch） |
| 5 | 不回归：`make check` / `check-qemu-semantics` 149/149 / `test-codegen` 15/15 / `test-elf` 5/5 / `check-patch-tree` 90 patches | ✅ | 独立重跑全部 EXIT=0 |
| 6 | 一键证据脚本：非交互 + 失败非零 + 逐项打印 + 注入自检 + 禁 tee | ✅ | 审核通过 + 重跑 SCRIPT_EXIT=0 + 独立注入验证 |
| 7 | 无残留：git status 干净 + `.work/source/qemu` clean + `spec/` 交集空 | ✅ | 最终快照对账一致 |

##### 5. 补丁集与探针

- `Process-01` 合规：3 份补丁（一文件一补丁）+ `changelog.md` + `series` ✓
- 补丁 blob 非空（新建文件，完整 diff）✓
- `tools/qemu/min_rom_probe_049t.py` 已入库 ✓
- `.work/source/qemu` clean ✓

##### 6. 文件集核验

`git diff --name-only 00c9540..HEAD` = 10 文件：
```
.tao/knowledge/issues.yaml          ← ISS-165/166 登记
.tao/knowledge/milestones.md        ← step2 迁移跨模块待办
.tao/tasks/qemu/QEMU-047t-新bootrom.md ← ELF 加载器前置风险追加
.tao/tasks/qemu/QEMU-049t-RAM0双映射.md ← 本任务书
components/qemu/changelog.md        ← Process-01 §10
components/qemu/patches/hw/dadao/dadao-machine.c.patch
components/qemu/patches/target/dadao/cpu.h.patch
components/qemu/patches/target/dadao/helper.c.patch
tools/integ/check_interface_alignment.py
tools/qemu/min_rom_probe_049t.py
```
- `spec/` 交集 **空** ✓
- `.work/**` 未入库 ✓

##### 7. 遗留处置复核

| 遗留 | 核验 | 结论 |
|------|------|------|
| ISS-165 step2 迁移 | issues.yaml 行370-376：scope `[testcases, qemu, integ, M5]`、含「EA=0 ⇒ 0x87 向量/探针在 R3 下失效」、**非门控**（当前不在任何 `make` 门控内） | ✅ 登记准确 |
| QEMU-047t ELF 加载器前置风险 | QEMU-047t 任务书行19+行36：`dadao_load_regions[]` 未纳入 RAM@0、标注「前置风险 `lessons.md §7.6`」 | ✅ 已写入 |
| ISS-166 Machine-01 §1 差异 | issues.yaml 行378-384：差异 A（RAM@0 大小占位 `【待 QEMU-049t 定】`）+ 差异 B（精确路由歧义）+ **未改 `spec/`**（`git diff` 确认 spec/ 交集空）+ 拟改文本在任务书审阅记录 | ✅ 如实登记，未遗漏 |

##### 8. 判决

**Accepted** — 验收命令块全部通过（证据脚本 SCRIPT_EXIT=0 + 独立注入 FAIL→还原→回绿 + 门控全绿）；约束无违反；遗留处置准确。

#### 第 1 轮 architect 提交（WIP）

**档位**：reviewer **尚未验收**（状态 `待验收`）⇒ **`WIP:`** 本地提交，信息 `WIP: QEMU-049t RAM@0 双映射 + 越界/取指异常（C1 step1）（待 reviewer 验收）`。**只 `commit`，绝不 `push`**。

**文件集审核**（只核「提交哪些文件是否合适」，逐个路径**显式 staging**、**禁 `git add -A`**）：
- **staged（7）** = `components/qemu/patches/hw/dadao/dadao-machine.c.patch`、`components/qemu/patches/target/dadao/cpu.h.patch`、`components/qemu/patches/target/dadao/helper.c.patch`、`components/qemu/changelog.md`、`tools/integ/check_interface_alignment.py`、`tools/qemu/min_rom_probe_049t.py`（新增，随产物入库）、`.tao/tasks/qemu/QEMU-049t-RAM0双映射.md`。
- **对账结论**：staged 与「完成区 · 修改文件」声明**一致**（补丁 3 + `changelog.md` + `check_interface_alignment.py` + 新探针 + 任务书）⇒ **无漏提、无多提、无越界**。`spec/` 交集**空**；`.work/**`（gitignored，含 `evidence/QEMU-049t/run.sh`、`source/qemu`）**未入库**。
- 判据：`.work/source/qemu` 收敛 commit **不入** DADAO 库（`Process-01` 补丁纪律，权威载体 = 导出补丁）；`changelog.md` **非残留**（`Process-01 §10` 要求）。

**遗留处置（4 项）**：
1. **step2 迁移（另立、M5 之外）** ⇒ 登记为**跨模块影响/待办**：`milestones.md` M5 段 + **`ISS-165`**（新号）。**受影响对象类别** = `tests/vectors/**`（如 `isa/{mem-rd,mem-rb,mem-ra,ctrl-*}.yaml` 的 `EA=0 ⇒ unmapped` 用例）+ `tools/qemu/*.py` 探针（如 `min_rom_probe_010t.py` T6/T18）；**含「既有 `EA=0 ⇒ unmapped 0x87` 向量/探针在 R3 下失效」**（RAM@0 落在 `0`）。**当前非任何 `make` 门控**（门控全绿），**不阻塞 M5 门槛**。
2. **ELF 加载器 `dadao_load_regions[]` 未纳入 RAM@0** ⇒ **只追加**写入 `QEMU-047t` 任务书「输入」（组件现状）与「约束」（**前置风险**，`lessons.md §7.6`）：若 047t 应用/bootrom ELF 链进 RAM@0，须扩该表并加验证。
3. **越界路由口径（`ADR-0020 D15` 落地）** ⇒ 核 `spec/Machine-01 §1` ⇒ **未完全覆盖**（详见下「Machine-01 差异清单」）；**未改 `spec/`**，作 **`ISS-166`** 登记，交主会话提请用户授权。
4. **`0x81` 复用冻结表保留区、`0x87`–`0x8D` 未重排、`FAULT_NAMES` 未扩** ⇒ 记录于 **`ISS-165`**（同归 step2）。

**Machine-01 §1 差异清单（未改 `spec/`；交主会话提请用户授权）**——核 `spec/Machine-01-测试机运行环境.md §1` 现行措辞对三条口径（umon 段越界 ⇒ `0x81`；其余含旧 `power` 段 63 ⇒ `0x87`；RAM@0 = 16 MiB）的覆盖结论 = **未完全覆盖**：
- **差异 A（RAM@0 容量缺）**：`§1.1` 表 RAM@0 行「大小」列现为占位 `【待 QEMU-049t 定】`。
  - **拟改文本**：`| **RAM@0（新）** | \`0x0000_0000_0000\` | 16 MiB | 0 / \`umon\` | 供 bootrom/SEE（C1 step1 双映射引入） |`
- **差异 B（精确路由未写、且与已落地口径歧义）**：`§1.2` 末条现把「精确路由与 RAM@0 容量」**委派**给 `QEMU-049t`（未写口径）；且 `§1.2`「层次与适用」条「`CFXMEM`（`0x81`）适用于核内地址空间模型内的非法访问/取指（cfxha 段内的非法子区间、越界访问/取指）」按字面**也覆盖 `power` 段 63 的越界**，与已落地路由（`power` 段 63 越界 ⇒ `0x87`）**歧义**。
  - **拟改文本（新增一条，「层次与适用」条之后、末条之前）**：`- **精确路由（\`QEMU-049t\` 已按 \`ADR-0020 D15\` 落地）**：**\`umon\` 段（\`addr[47:42]==0\`）的越界访问/越界取指 ⇒ \`CFXMEM\`（\`0x81\`）**；**其余段（含旧 \`power\` 段 63）的越界访问/越界取指 ⇒ 测试机约定 \`unmapped\`（\`0x87\`）**。[ADR-0020 D15]`
  - **拟改文本（末条，改为落地陈述）**：`- 精确路由与 RAM@0 容量由 \`QEMU-049t\` 落地（\`umon\` 段 ⇒ \`0x81\`、其余 ⇒ \`0x87\`；RAM@0 = 16 MiB），并以 \`check-interface\` 断言固化。[ADR-0020 D15]`
- **（以上仅提案；`spec/` 改动须用户事先授权〔`lessons §8.5`/`Process-06`〕，未获授权前不得落地。）**

#### 第 1 轮 architect 提交（正常）

**档位**：**正常提交**（reviewer 判 `Accepted` ⇒ `**状态**` 置 `已验证`；**不加 `WIP:`**）。**只 `commit`，绝不 `push`**（push 归主会话 `/complete` 后；须把 WIP `cd8e1e6` + 本次正常提交 + 收尾台账 squash/amend 为单一「已验证」提交）。

**交叉复核判决**：**通过**（reviewer `Accepted` 成立，不推翻/不补充 Needs Revision）。独立核（architect 自跑，真实输出）：
- **reviewer 独立注入有鉴别力、还原含重建** ✓：注入改源 `DADAO_RAM0_SIZE 16→8 MiB`（`git -C .work/source/qemu diff --name-only` 非空）⇒ **重建** ⇒ `ram0_top` FAIL（`exit exp=0x0 got=0x81`）而 `old_ram_rw` PASS（特异）；`cp`+`md5` 还原（相等）⇒ **重建** ⇒ 9/9；终态 3 补丁 md5 与注入前一致、`git status` 空。
- **两段不重叠** ✓：`DADAO_RAM0_BASE=0x0` + `DADAO_RAM0_SIZE=16 MiB` ⇒ `[0x0, 0x1000000)`；`DADAO_RAM_BASE=0xffff00000000` + 16 MiB ⇒ 与 `exit port`（`0xffff80000000`）/ROM（`0xffffffff0000`）均不相交。
- **`check-interface` 80→86** ✓：`python3 tools/integ/check_interface_alignment.py` EXIT=0，类计数 `5+32+41+8=86`、0 FAIL；6 新增项（`RAM0_BASE=0x0`/`RAM0_SIZE=16MiB`/`init_ram`/`add_subregion`/`EXIT_CFXMEM=0x81`/`CFXHA_UMON=0`）均 PASS，旧 RAM/exit-port 断言保留。
- **越界路由** ✓：`oob_data/fetch_cfxmem`（cfxha0）⇒ `0x81`、`oob_data/fetch_unmapped`（cfxha63）⇒ `0x87`（探针）；源代码按 `DADAO_ADDR_CFXHA(addr)==DADAO_CFXHA_UMON` 分类，数据与取指同经 `tlb_fill`。
- **`0x87`–`0x8D` 未重排** ✓：`cpu.h.patch` 中 `UNMAPPED=0x87`/`ILLI=0x88`/`UNDI=0x89`/`RASOF=0x8A`/`RASUF=0x8B`/`MALIGN=0x8C`/`IALIGN=0x8D` 逐项未改；`CFXMEM=0x81` 落 `D5.8` 冻结表已保留区，`EXCP_CFXMEM=8` 追加于末位。
- **`check-patch-tree` 90 patches** ✓：`python3 tools/infra/check_patch_tree.py` EXIT=0（`2 component(s), 90 patches OK`）；`.work/source/qemu` `git status --porcelain` 空（clean）。
- **未越界** ✓：**WIP 交付集**（基线 `00c9540`..WIP）＝ **10 文件**（组件补丁 3 + `components/qemu/changelog.md` + `check_interface_alignment.py` + 新探针 + 本任务书 + `issues.yaml` + `milestones.md` + `QEMU-047t` 任务书）；**含本轮知识沉淀的完整收尾集** ＝ **13 文件**（+ `MEMORY.md`/`lessons.md`/`.tao/knowledge/changelog.md`）；两组对 `spec/` 交集**均为空**。
- **遗留处置落纸完整** ✓：`ISS-165`（step2 迁移，`open`）、`ISS-166`（`Machine-01 §1` 覆盖缺口 + 拟改文本，`open`）、`QEMU-047t` 任务书「组件现状/前置风险」（`dadao_load_regions[]` 未纳 RAM@0）均已落纸；`spec/` 确未改动。

**文件集对账（只核「提交哪些文件是否合适」；逐个路径显式 staging，禁 `git add -A`）**：
- **staged（5）**：本任务书（`**状态**=已验证` + reviewer/architect 记录）、`.tao/knowledge/lessons.md`（§7.16/§8.10）、`.tao/knowledge/changelog.md`（+1 行）、`.tao/knowledge/milestones.md`（QEMU-049t 落地条目）、`.tao/knowledge/MEMORY.md`（M5 摘要行 + QEMU-049t 项）。
- **对账结论**：staged 与「完成区 · 修改文件」声明 + 本轮「知识沉淀 / 收尾」追加**一致** ⇒ **无漏提、无多提、无越界**。`spec/` 交集**空**（`git diff --cached --name-only` 与 `spec/` 无交集）；`.work/**`（gitignored，含 `source/qemu`、`evidence/QEMU-049t/run.sh`、`log/qemu/`）**未入库**。
- 判据：组件补丁 3 + `changelog.md` + `check_interface_alignment.py` + 新探针已在 **WIP 提交 `cd8e1e6`** 内；本轮正常提交只含「状态 + 审阅记录 + 知识沉淀」。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **reviewer**：`Accepted`。证据脚本重跑 **SCRIPT_EXIT=0**（探针 9/9；3 处注入各自 FAIL ⇒ `cp`+`md5` 还原 ⇒ **重建** ⇒ 回绿）；**独立注入**（改 `DADAO_RAM0_SIZE` 16→8 MiB）⇒ **重建** ⇒ `ram0_top` **FAIL**（`0x81` vs `0x0`，且 `old_ram_rw` 仍 PASS ⇒ **特异、非广域**）⇒ 还原 ⇒ 重建 ⇒ 9/9。
- **architect 交叉复核**：**通过**。独立核：两段**不重叠**（`[0x0,0x1000000)` vs `0xffff_0000_0000`+16MiB）；`check-interface` **80→86**（新增 6 项 + **旧断言保留**、0 FAIL）；越界路由 `umon ⇒ CFXMEM(0x81)` / 其余 ⇒ `unmapped(0x87)`（含取指 2 例）；**`0x87`–`0x8D` 逐项未改**（`CFXMEM=0x81` 落 `D5.8` 保留区）；`check-patch-tree` **90 patches**（断言⑥）；`.work/source/qemu` clean；`spec/` 交集**空**。
- **交付**：**C1 step1 双映射**（RAM@0 新段 + 旧 RAM 段保留、互不重叠）+ **越界访问/取指异常**（含取指路径）+ `check-interface` 断言增补 + 探针 `tools/qemu/min_rom_probe_049t.py` **随产物入库**；补丁集 3 改 + `changelog.md`。
- **遗留处置（已落纸）**：① **`ISS-165`**（**step2** 迁移：旧向量/harness/`crt0`/e2e 迁 `0` + 删旧 RAM 段 + 收紧断言；含「既有 `EA=0 ⇒ 0x87` 向量/探针在 R3 下失效」——**当前非任何 `make` 门控、不阻塞 M5**，跨模块待办留 M6/另立）；② `QEMU-047t` 已增「ELF 加载器 `dadao_load_regions[]` 未含 RAM@0」**前置风险**（避免重演 `lessons §7.6`）；③ **`ISS-166`** = `spec/Machine-01 §1` 覆盖缺口（**未改 `spec/`**，拟改文本 3 条 → **待用户授权**）。
- **补充发现（非阻塞）**：`check-interface` 读的是**导出补丁**而非编译源 ⇒ 「改基址」类反例注入须落**补丁**（门控载体性质，已在完成区登记）。
- **收尾检查**：`make check` / `check-qemu-semantics` 149/149 / `test-codegen` 15/15 / `test-elf` 5/5 / `check-patch-tree` EXIT=0；`git status --porcelain -uall` 干净。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
