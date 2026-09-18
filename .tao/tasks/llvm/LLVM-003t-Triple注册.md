# LLVM-003t: Triple 注册

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-002t`、`SPEC-007t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`.work/source/llvm-project`（`make fetch` 后按 ADR-0006 commit 的干净 checkout）、`components/llvm-project/patches/series`、`.tao/knowledge/contract-elf.md`（SPEC-007t，ELF header/大端/e_machine/e_flags）
- 输出：
  - `components/llvm-project/patches/0001-dadao-triple-registration.patch`
  - `components/llvm-project/patches/0002-dadao-target-skeleton.patch`
  - 更新后的 `components/llvm-project/patches/series`
  - `Makefile` 的真实 `build-mc`（`LLVM-002t` 已建立，本任务确认可用）
  - 最小 lit 冒烟 `tests/lit/MC/Dadao/triple-smoke.s` + `tests/lit/MC/Dadao/lit.cfg.py`
- 约束：不实现任何指令（不写 `DADAOInstrInfo`/`DADAORegisterInfo`/`.td` 指令）；patch 必须能被 `git am` 干净应用到 `.work/source/llvm-project`；triple 注册名精确为 `dadao`，full triple `dadao-unknown-elf`；ELF 大端；`e_machine`/`e_flags` 用命名常量或明确取自 `contract-elf.md`，不硬编码无来源数字

## 背景（完整）

### 目标

在 ADR-0006 基线上注册 DADAO triple，构建出能通过 cmake/ninja 的最小空 target，使 `llvm-mc --triple=dadao-unknown-elf` 不报 "unknown target"，并把 `build-mc` 变为真实构建。后续任务（寄存器/指令格式/汇编器/反汇编器）均在此骨架上叠加，故本任务只做注册与 build，不越界。

### 设计理由

- 以 Lanai（`llvm/lib/Target/Lanai/`）为最简完整 target 骨架参考；大型 target（RISCV）可查 MCTargetDesc 结构。
- 先注册 triple 与最小 MCTargetDesc，保证 `llvm-mc`/`llvm-objdump` 可被调用，再逐层填充寄存器与指令。

### 关键概念 / 数据

**Triple 注册**（相对 `llvm-project` 根）：

| 文件 | 改动 |
|------|------|
| `llvm/include/llvm/TargetParser/Triple.h` | `ArchType` 枚举加 `dadao` |
| `llvm/lib/TargetParser/Triple.cpp` | `getArchTypeName`、`parseArch`、`getDefaultFormat` 等补 dadao 条目 |
| `llvm/CMakeLists.txt` | `LLVM_ALL_TARGETS` 加 `DADAO` |

**最小 Target 目录** `llvm/lib/Target/DADAO/`：`CMakeLists.txt`、`DADAO.h`、`DADAOTargetMachine.{h,cpp}`、`TargetInfo/DADAOTargetInfo.{h,cpp}`（`RegisterTarget`，triple `"dadao"`，desc `"DADAO SimRISC"`）、`MCTargetDesc/CMakeLists.txt`、`MCTargetDesc/DADAOMCTargetDesc.{h,cpp}`。

**AsmInfo 存根**：`MCTargetDesc/DADAOMCAsmInfo.{h,cpp}` 继承 `MCAsmInfoELF`，`CommentString = "#"`，大端 `IsLittleEndian = false`（依据 `contract-elf.md` 的 EI_DATA）。

**ELF writer 存根**：`MCTargetDesc/DADAOELFObjectWriter.cpp` 继承 `MCELFObjectTargetWriter`，`getOSABI()`、`getEMachine()`、`needsRelocateWithSymbol()`、`getRelocType()` 按 `contract-elf.md` 取值（`getRelocType()` 可为存根）。

**最小 lit 冒烟**：`triple-smoke.s` 验证 triple 注册成功（AsmParser 缺失时可退化为 `llvm-mc --version | grep dadao`）；`lit.cfg.py` 指向已 build 的 `llvm-mc`。

**构建**：`make prepare` 先 fetch+apply，再 `make build-mc`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-007a-llvm-triple.md`（完整转述：目标、patch 内容、series、Makefile、lit、约束、验收步骤、两轮 Architecture Review）。
- DADAO-0628：`components/llvm/patches/0001-dadao-triple-registration.patch`、`0002-dadao-target-skeleton.patch`（**仅参考命名与顺序**，不复制正文）。
- DADAO-0628：`docs/adr/0003-object-abi.md`、`docs/adr/0005-llvm-baseline.md`。

## 交付物

- `components/llvm-project/patches/0001-dadao-triple-registration.patch`：Triple 注册（Triple.h/Triple.cpp/CMakeLists.txt）。**补丁必须包含 `llvm/CMakeLists.txt` 的 `LLVM_ALL_TARGETS` 增项（加入 `DADAO`）**，使 `-DLLVM_TARGETS_TO_BUILD=DADAO` 生效（依据 ADR-0007）。
- `components/llvm-project/patches/0002-dadao-target-skeleton.patch`：最小 DADAO target 骨架 + AsmInfo + ELF writer 存根。
- `components/llvm-project/patches/series`：按序写入 0001、0002。
- `Makefile`：确认 `build-mc` 真实可用（如 `LLVM-002t` 已完成则不重复改动）。
- `tests/lit/MC/Dadao/triple-smoke.s`、`tests/lit/MC/Dadao/lit.cfg.py`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **ELF 常量来源**：`e_machine`/`e_flags`/EI_DATA 以 v5 `.tao/knowledge/contract-elf.md`（SPEC-007t，归一化自 ADR-0003）为准，不照抄 0628 的 `0x0DA0`/`e_flags=0x1` 数值表述；若 v5 沿用同一 `EM_DADAO`，须由 ADR-0003/合约明确，不得在代码里硬编码无来源数字。
- **上游路径**：v5 `.work/source/llvm-project/llvm`（`INFRA-004t`），构建 `.work/build/llvm`。
- **大端**：0.5.3 指令与数据均大端（`contract-isa.md` §1.5、§2.1），AsmInfo 必须 `IsLittleEndian = false`。
- **triple 名**：v5 同为 `dadao-unknown-elf`，但注册与验证须在 0.5.3 的 AsmInfo/DataLayout 下完成。
- **不复制补丁正文**：0628 的 0001/0002 patch 属 0.4.1 实现，v5 须按 0.5.3 重新生成；只参考其命名与 series 顺序。

## 已知坑 / 结论

- **`LLVM_ALL_TARGETS` 增项必需（ADR-0007）**：DADAO 必须加入 `llvm/CMakeLists.txt` 的 `LLVM_ALL_TARGETS` 列表，否则 `-DLLVM_TARGETS_TO_BUILD=DADAO` 的 cmake configure 报 `FATAL_ERROR`（`The target 'DADAO' is not a core tier target`）。注册通道由用户裁定为加入 `LLVM_ALL_TARGETS`（否决 experimental 通道），见 ADR-0007。0001 补丁须包含此增项。
- **AsmParser 缺失时 lit 退化为 `--version | grep dadao`**：0628 `DL-007a` 因缺 AsmParser，冒烟测试改为验证 `llvm-mc --version` 输出含 `dadao`；v5 同样处理，待 `LLVM-006t` 引入汇编解析后再补 assembly 测试。
- **MCInstPrinter 存根必需**：`llvm-mc` 运行期要求非空 printer，否则崩溃。
- **`EM_DADAO` 命名常量**：0628 第二轮 N1 指出直接硬编码 `0x0DA0`；v5 应引用命名常量或合约值，避免魔数。
- **大端 DataLayout**：若 DataLayout 写成 `e`（小端）会导致字节序错误，须确认 `E`（大端）。
- **patch 必须干净 apply**：0001→0002 顺序应用后 `ninja llvm-mc` 成功。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-007a-llvm-triple.md`（内容溯源，非执行必需）
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/series`（内容溯源，非执行必需）
- DADAO-0628：`.work/DADAO-0628/docs/adr/0003-object-abi.md`（内容溯源，非执行必需）
- DADAO-0628：`.work/DADAO-0628/Makefile`（内容溯源，非执行必需）
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-elf.md`（SPEC-007t 产出后）、`contracts/opcodes.yaml`
- ADR：`.tao/knowledge/adr-0007-dadao-target-registration.md`（DADAO 注册通道决策）

## 验收标准

1. 0001、0002 两个 patch 存在，且按序写入 `components/llvm-project/patches/series`
2. `make prepare && make build-mc` PASS（cmake configure + ninja llvm-mc）
3. `llvm-mc --version` 的 Registered Targets 含 `dadao - DADAO`（或不报 unknown target）
4. 若 AsmParser 尚未实现（本任务边界）：`llvm-mc --version` 的 Registered Targets 含 `dadao`；否则 `llvm-lit tests/lit/MC/Dadao/triple-smoke.s` PASS
5. 未定义任何指令/寄存器 `.td`（本任务边界）

## 完成区

**测试结果**：5/5 验收标准通过

**修改文件**：
- `.work/source/llvm-project`（2 commits on top of `6dfe1677`）：
  - Commit 1 (0001): 3 files changed（`llvm/CMakeLists.txt`、`llvm/include/llvm/TargetParser/Triple.h`、`llvm/lib/TargetParser/Triple.cpp`）——均为修改，无新建
  - Commit 2 (0002): 15 files changed（13 个新建 `llvm/lib/Target/DADAO/` + 2 个修改 `llvm/lib/TargetParser/TargetDataLayout.cpp`、`llvm/lib/TargetParser/Triple.cpp`）
- `components/llvm-project/patches/0001-dadao-triple-registration.patch`（`git format-patch` 元数据 `From` sha = `6b7ba04d0…`，与 worktree commit sha 一致）
- `components/llvm-project/patches/0002-dadao-target-skeleton.patch`（`From` sha = `d76204f3a…`，与 worktree commit sha 一致）
- `components/llvm-project/patches/series`
- `tests/lit/MC/Dadao/triple-smoke.s`、`tests/lit/MC/Dadao/lit.cfg.py`
- `Makefile`（`build-mc` 去掉 `llvm-lit`；注释去掉过时的「Until LLVM-003t … will fail」）

**验收结果**：

1. **0001、0002 两个 patch 存在，且按序写入 series** ✅
```
$ cat components/llvm-project/patches/series
0001-dadao-triple-registration.patch
0002-dadao-target-skeleton.patch
$ ls components/llvm-project/patches/
0001-dadao-triple-registration.patch  0002-dadao-target-skeleton.patch  series
```

2. **`make prepare && make build-mc` PASS** ✅
```
$ make prepare
...
Applying: DADAO: Register dadao triple and add to LLVM_ALL_TARGETS
Applying: DADAO: Add minimal target skeleton with MC support
apply-series: llvm-project applied 2 patches

$ make build-mc
...
-- Targeting DADAO
-- Configuring done (20.4s)
...
[858/858] Linking CXX executable bin/llvm-objdump
build-mc: PASS
```
退出码：0

3. **`llvm-mc --version` 的 Registered Targets 含 `dadao - DADAO`** ✅
```
$ .work/build/llvm/bin/llvm-mc --version
LLVM (http://llvm.org/):
  LLVM version 23.1.1
  Optimized build with assertions.

  Registered Targets:
    dadao - DADAO SimRISC
```

4. **AsmParser 尚未实现，lit 退化路径验证** ✅
```
$ .work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/triple-smoke.s -v
-- Testing: 1 tests, 1 workers --
PASS: DADAO-MC :: triple-smoke.s (1 of 1)
Testing Time: 0.03s
Total Discovered Tests:
  Passed: 1 (100%)
```

5. **未定义任何指令/寄存器 `.td`** ✅
```
$ find .work/source/llvm-project/llvm/lib/Target/DADAO/ -name "*.td" | wc -l
0
```

6. **`llvm-mc --triple=dadao-unknown-elf` 不再因缺 MCRegInfo 而 abort** ✅（F2 复验）
```
$ echo "" | .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
.work/build/llvm/bin/llvm-mc: error: unable to create subtarget info
EXIT=1
```
行为从 `Assertion 'MRI && "Unable to create target register info!"' failed`（SIGABRT）改善为正常的 `error: unable to create subtarget info`（exit 1）。MCRegisterInfo 存根已生效；`unable to create subtarget info` 属预期（无 MCSubtargetInfo 实现，属后续任务边界）。

**新发现/坑**：
- **`llvm-lit` 不是 ninja 构建目标**：`bin/llvm-lit` 是 CMake `configure_file` 在 configure 阶段生成的 Python 脚本，无对应 ninja target。已在本任务中修复 Makefile。
- **LLVM 组件库命名必须全大写**：`add_llvm_component_library(LLVMDadaoInfo ...)` 创建 `LLVMDadaoInfo`（mixed case），但 `LLVM-Config.cmake` 用 `LLVM${t}Info` 查找（`t`=`DADAO`→`LLVMDADAOInfo`），大小写不匹配导致链接失败。解法：库名统一用全大写 `LLVMDADAOInfo`/`LLVMDADAODesc`。
- **`LLVMInitialize*` 函数名必须全大写**：`Targets.def` 生成 `LLVMInitializeDADAOTargetInfo`（全大写），C++ 中函数名必须精确匹配。
- **`MCInstPrinter::getMnemonic()` 是纯虚函数**：LLVM 23.1.1 中 `MCInstPrinter` 有纯虚 `getMnemonic()`，stub printer 必须实现。
- **`computeDataLayout()` 需要新增 dadao case**：Triple 的 `computeDataLayout()` 是 switch on ArchType，不加会 `llvm_unreachable`。DataLayout 为 `"E-m:e-p:64:64-i64:64-i128:128-n32:64-S128"`（大端、64位指针、ELF）。
- **`get32BitArchVariant()`/`get64BitArchVariant()` 需要新增 dadao case**：否则 `-Wswitch` 警告。
- **`getLittleEndianArchVariant()` 需要新增 dadao case**：dadao 是大端（`isLittleEndian()==false`），若不加 case 会落入 `default: llvm_unreachable`。解法：归入 `setArch(UnknownArch)` 组（dadao 无小端变体）。0628 同思路。
- **空 `MCRegisterInfo` 存根必需**：`llvm-mc --triple=dadao-unknown-elf` 在 `LookupTarget` 路径要求 `RegisterMCRegInfo` 已调用，否则触发 `Assertion 'MRI && "Unable to create target register info!"'`。解法：注册一个 `new MCRegisterInfo()` 空对象（无实际寄存器定义）。
- **`EM_DADAO` 值来自 `contract-elf.md §1.1`（`0x0DA0`）**：以本地 `static constexpr` 定义并注释来源，未硬编码无来源数字。
- **无 `.td` 方案可行**：最小 target 骨架不依赖 tablegen，`add_llvm_target(DADAOCodeGen ...)` 仅编译 `DADAOTargetMachine.cpp`（纯 C++，无 `.inc` 依赖）。
- **lit 测试 `config.llvm_build_dir` 不存在**：lit 的 `TestingConfig` 没有 `llvm_build_dir` 属性。改用 `config.llvm_tools_dir`（site config 提供）+ 环境变量 `LLVM_TOOLS_DIR` fallback + 自动推导。
- **lit `test_exec_root` 必须指向 build 树**：若指向源码树（`tests/lit/…/Output`），lit 产物（`.lit_test_times.txt`、`*.tmp.out`）会污染 git 仓库。解法：从 `tools_dir` 推导 build root（`os.path.dirname(tools_dir)`），将 exec_root 设为 `<build>/test-output/DADAO-MC`。`.work/` 已 gitignore，故零污染。

**遗留问题**：
- `DADAOELFObjectWriter::getRelocType()` 返回 `0`（stub），M2 引入重定义时需替换为真实重定位类型映射（`contract-elf.md §2`）。
- **F3 deferred**：ELF writer 存根是死代码（`createDadaoELFObjectWriter` 未注册、`createDadaoAsmBackend`/`createDadaoMCCodeEmitter` 只声明未定义未注册）→ 归后续 ELF/汇编器任务。已登记 `.tao/knowledge/deferred.md`。
- **F4 deferred**：`e_flags` 未设置（`contract-elf.md §1.1` 要求 `0x00000001`）→ 归后续 ELF/汇编器任务。已登记 `.tao/knowledge/deferred.md`。

## 审阅记录

### 第 1 轮自审后返工（patch 命名 + llvm-lit + lit.cfg）

**返工时间**：2026-09-17

**问题 1（patch 文件名与任务书不符）**：
- **现象**：`git format-patch` 默认命名 `0001-DADAO-Register-dadao-triple-and-add-to-LLVM_ALL_TARG.patch`（截断）+ `0002-DADAO-Add-minimal-target-skeleton-with-MC-support.patch`，与任务书要求的 `0001-dadao-triple-registration.patch`、`0002-dadao-target-skeleton.patch` 不符。
- **处置**：重命名两个 patch 文件 + 更新 `series`。
- **复验**：`cat series` 与 `ls` 一致，`make prepare` 干净重放 PASS。

**问题 2（Makefile `ninja llvm-lit` 目标不存在）**：
- **现象**：`make build-mc` 在 `ninja -C $(LLVM_BUILD) llvm-mc llvm-objdump llvm-lit FileCheck` 处失败（`ninja: error: unknown target 'llvm-lit'`）。
- **根因**：`bin/llvm-lit` 是 CMake configure 阶段 `configure_file` 生成的 Python 脚本，无对应 ninja target。
- **处置**：`Makefile:84` 去掉 `llvm-lit`，改为 `ninja -C $(LLVM_BUILD) llvm-mc llvm-objdump FileCheck`。
- **复验**：`make build-mc` exit=0，`build-mc: PASS`。

**问题 3（LLVM-002t 任务书补记）**：
- **处置**：在 `LLVM-002t` 完成区「遗留问题」后追加「补记（2026-09-17，用户裁定 + LLVM-003t）」，说明 `llvm-lit` 非 ninja 目标、`Makefile` 已在 LLVM-003t 中修正。

**额外修复（lit.cfg.py）**：
- **现象**：`config.llvm_build_dir` 不存在（`AttributeError`）。
- **处置**：改用 `config.llvm_tools_dir`（site config 提供）+ `LLVM_TOOLS_DIR` 环境变量 fallback + 自动从文件位置推导 build dir。
- **复验**：`llvm-lit tests/lit/MC/Dadao/triple-smoke.s -v` → PASS。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| patch 文件名不符任务书 | ✅已修 | 重命名 2 个 patch 文件 + 更新 series | `cat series` + `ls` 一致；`make prepare` PASS |
| Makefile ninja llvm-lit 不存在 | ✅已修 | `Makefile:84` 去掉 `llvm-lit` | `make build-mc` exit=0 |
| LLVM-002t 需补记 | ✅已修 | 追加补记段落 | 读取文件确认 |
| lit.cfg.py 引用不存在的属性 | ✅已修 | 改用 `llvm_tools_dir` + fallback | `llvm-lit` PASS |

### 第 2 轮返工（lit exec_root 污染）

**返工时间**：2026-09-17

**问题**：`test_exec_root` 指向源码树（`tests/lit/MC/Dadao/Output`），lit 产物（`.lit_test_times.txt`、`*.tmp.out`）污染 git 仓库。

**处置**：将 `test_exec_root` 改为从 `tools_dir`（`<build>/bin`）推导的 build 树路径（`<build>/test-output/DADAO-MC`）。`.work/` 已 gitignore，产物零污染。同时删除已产生的 `tests/lit/MC/Dadao/Output/` 目录，并增加 `tools_dir` 解析失败时的清晰报错。

**复验证据**：

| 验证项 | 结果 |
|--------|------|
| `llvm-lit tests/lit/MC/Dadao/ -v` | PASS（exit=0），1 test passed |
| `git status --short tests/` | `?? tests/lit/`（仅两个源文件，无 Output） |
| `find tests/lit/ -type f` | 仅 `triple-smoke.s` + `lit.cfg.py` |
| `ls .work/build/llvm/test-output/DADAO-MC/` | `.lit_test_times.txt` + `Output/`（产物在 build 树） |
| `find . -path ./.work -prune -o -name "*.tmp.out" -print` | 无命中（仓库内无 tmp.out） |
| `make manifest-check` | PASS（exit=0） |
| `make build-mc` | PASS（exit=0，`ninja: no work to do.` + `build-mc: PASS`） |

### 第 3 轮返工（reviewer F1/F2/F5/F6）

**返工时间**：2026-09-17

**F1（`getLittleEndianArchVariant` 缺 dadao case）**：
- **现象**：dadao 是大端（`isLittleEndian()==false`），进入 `getLittleEndianArchVariant()` 的 switch，未命中任何 case，落入 `default: llvm_unreachable` → 调用即崩溃。
- **处置**：在 `Triple.cpp` 的 `getLittleEndianArchVariant()` 中加入 `case Triple::dadao:` 到 `setArch(UnknownArch)` 组（dadao 无小端变体）。归入 commit 1 (0001)。
- **复验**：`git diff HEAD~2 HEAD~1 -- llvm/lib/TargetParser/Triple.cpp` 确认 `getLittleEndianArchVariant` 区域含 `+  case Triple::dadao:`。

**F2（`llvm-mc --triple=dadao-unknown-elf` 缺 MCRegInfo 而 abort）**：
- **现象**：`Assertion 'MRI && "Unable to create target register info!"' failed`（SIGABRT / exit 141）。
- **处置**：在 `DADAOMCTargetDesc.cpp` 中新增 `createDadaoMCRegInfo` 函数（返回 `new MCRegisterInfo()` 空对象），并在 `LLVMInitializeDADAOTargetMC()` 中注册。归入 commit 2 (0002)。
- **复验**：`echo "" | .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null` → `error: unable to create subtarget info`（exit 1，正常错误，不再 SIGABRT）。

**F5（完成区错值）**：
- **0001 文件归属**：`TargetDataLayout.cpp` 实际属 0002（`git diff HEAD~1 HEAD` 确认），非 0001。已修正。
- **文件计数**：0001 = 3 files changed（全修改）；0002 = 15 files changed（13 新建 + 2 修改）。已修正。
- **patch `From` sha**：`git format-patch` 的 `From` 行 sha 与 worktree commit sha 一致（因从同一 worktree 生成），已如实说明。

**F6（Makefile 过时注释）**：
- **现象**：`Makefile:72-73` 写「Until LLVM-003t lands that patch, cmake configure will fail.」——LLVM-003t 已落地，后半句过时。
- **处置**：去掉「Until LLVM-003t … will fail」，只保留 ADR-0007 指引。
- **复验**：`grep "Until LLVM-003t" Makefile` 无命中。

**F3/F4（deferred）**：
- **F3**：ELF writer 存根是死代码（`createDadaoELFObjectWriter` 未注册、`createDadaoAsmBackend`/`createDadaoMCCodeEmitter` 只声明未定义未注册）。已登记 `.tao/knowledge/deferred.md`，归后续 ELF/汇编器任务。
- **F4**：`e_flags` 未设置（`contract-elf.md §1.1` 要求 `0x00000001`）。已登记 `.tao/knowledge/deferred.md`，归后续 ELF/汇编器任务。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 getLittleEndianArchVariant 缺 dadao | ✅已修 | `Triple.cpp` 加 `case Triple::dadao:` 归 UnknownArch 组 | `git diff HEAD~2 HEAD~1` 确认含该 case |
| F2 llvm-mc --triple abort | ✅已修 | `DADAOMCTargetDesc.cpp` 加 `createDadaoMCRegInfo` 空存根并注册 | `llvm-mc --triple=dadao-unknown-elf` → `error: unable to create subtarget info`（exit 1，不再 SIGABRT） |
| F5 完成区错值 | ✅已修 | 文件归属/计数/sha 说明全部按 `git diff --stat` 实际输出修正 | 读取完成区确认 |
| F6 Makefile 过时注释 | ✅已修 | 去掉「Until LLVM-003t … will fail」 | `grep` 无命中 |
| F3 ELF writer 死代码 | ⏸deferred | 不改代码，登记 `.tao/knowledge/deferred.md` | 读取 deferred.md 确认 |
| F4 e_flags 未设置 | ⏸deferred | 不改代码，登记 `.tao/knowledge/deferred.md` | 读取 deferred.md 确认 |

### 第 1 轮 reviewer 验收

**验收者**：reviewer
**时间**：2026-09-17
**判决**：**Accepted**（5/5 条验收标准满足）

**独立重跑**：`make manifest-check` exit=0；patch 命名/`series` 顺序正确；0001 含 `LLVM_ALL_TARGETS` 增项（应用后 `llvm/CMakeLists.txt` 出现 `DADAO`）；0002 无 `.td`；`EM_DADAO = 0x0DA0` 有来源注释（对照 `contract-elf.md §1.1`，**无无来源魔数**）；大端（`IsLittleEndian=false`、DataLayout 首字符 `E`）；干净重放 `make prepare` exit=0；`make build-mc` exit=0（`-- Targeting DADAO`、`[858/858]`）；`llvm-mc --version` 含 `dadao - DADAO SimRISC`；`ninja llvm-lit` 确为 `unknown target`（故 `Makefile` 去 `llvm-lit` 正确）；`llvm-lit tests/lit/MC/Dadao/` PASS；无仓库污染；`make check` PASS；与 0628 补丁逐段 diff 确认**未照抄正文**。

**新发现（非阻塞）**：F1 `getLittleEndianArchVariant()` 缺 `case Triple::dadao`（潜在 `llvm_unreachable`）；F2 `llvm-mc --triple=dadao-unknown-elf` 实测 SIGABRT（缺 MCRegInfo）；F3 ELF writer 存根未接线（死代码）；F4 `e_flags` 未设置（`contract-elf.md §1.1` 要求 `0x00000001`）；F5 完成区文件归属/计数/patch sha 表述不准；F6 `Makefile` 注释过时。

### 第 3 轮返工（reviewer F1/F2/F5/F6）

**返工者**：engineer
**时间**：2026-09-17

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 | ✅已修 | 0001 中 `Triple.cpp` 的 `getLittleEndianArchVariant()` 加 `case Triple::dadao:`（归 `setArch(UnknownArch)` 组） | patch 内容核对 + 重新干净重放 |
| F2 | ✅已修 | 0002 中新增 `createDadaoMCRegInfo`（空 `new MCRegisterInfo()`）并在 `LLVMInitializeDADAOTargetMC()` 注册 | `llvm-mc --triple=dadao-unknown-elf` 由 SIGABRT(141) 变为 `error: unable to create subtarget info`、exit=1（**如实记录**，不伪装成功） |
| F5 | ✅已修 | 完成区按 `git show --stat` 实际输出修正（0001 = 3 文件全修改；0002 = 13 新建 + 2 修改；patch `From` sha 与 worktree commit sha 一致并说明来源） | 与 `git diff --stat` 对照 |
| F6 | ✅已修 | `Makefile:72-73` 去掉「Until LLVM-003t lands that patch, cmake configure will fail」 | `grep "Until LLVM-003t" Makefile` 无命中 |
| F3/F4 | ⏸deferred | 登记 `.tao/knowledge/deferred.md`（`## llvm / qemu / integ`），归属后续 ELF/汇编器任务（`LLVM-006t` 起） | 读取 deferred.md 确认 |

**复验**：`make manifest-check` exit=0；干净重放 `make prepare` exit=0；`make build-mc` exit=0（`build-mc: PASS`）；`llvm-mc --version` 含 `dadao - DADAO SimRISC`；`llvm-lit tests/lit/MC/Dadao/` PASS、无仓库污染；patch 命名/`series` 符合任务书。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-17
**判决**：**确认 Accepted**（无过度宽松；无需新增 ADR）。

**独立核对**：5 条验收标准均有真实命令输出；F1–F6 处置完整；`F5` 的文件计数与 patch `From` sha 与 `git show --stat` 一致；跨模块（`build-qemu`/`build-gem5`、qemu/integ/testcases）未被破坏。

**ADR-0007 终审**：其 D1 有效性已由真实构建流水线验证（0001 加入 `LLVM_ALL_TARGETS` + `cmake -DLLVM_TARGETS_TO_BUILD=DADAO` configure 成功 + `llvm-mc --version` 含 dadao）→ 由主会话升 `Accepted`。

**新发现（非阻塞）**：
- **N1**：`LLVM-002t` 正文 5 处（第 41/100/116/167/184 行）仍写 `ninja … llvm-lit FileCheck`；**不改**（已有「补记」兜底，属已 `Verified` 任务的历史正文）。
- **N2**：`changelog.md` 缺 `LLVM-003t` 条目 → 收尾时补。

### 收尾

- `adr-0007-dadao-target-registration.md` 升 **`Accepted`**（2026-09-17）。
- `**状态**` 置 `已验证`（2026-09-17）。
- `MEMORY.md`（llvm 行）、`changelog.md` 已同步；F3/F4 已登记 `deferred.md`。

---

### 补记（LLVM-004t 第 2 轮返工发现，2026-09-18）

`LLVM-003t` 交付的 `DADAOTargetMachine.{h,cpp}` 使用 `LLVMTargetMachine` 基类，但 LLVM 23.1.1 已将该类改名为 `CodeGenTargetMachineImpl`。此问题被 `build-mc` 的门禁盲区掩盖：`Makefile` 的 `build-mc` 只构建 `llvm-mc`/`llvm-objdump`/`FileCheck`，从不构建 `LLVMDADAOCodeGen`（含 `DADAOTargetMachine.cpp`），因此 CodeGen C++ 自始未被编译。

基类修复落在 `LLVM-004t` 的 `0003` 补丁中（不改写已交付的 `0002`）。`Makefile` 的 `build-mc` 目标列表已增加 `LLVMDADAOCodeGen`，后续任务的门禁将真实覆盖 CodeGen 编译。
