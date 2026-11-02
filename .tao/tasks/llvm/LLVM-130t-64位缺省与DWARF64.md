# LLVM-130t: 64 位缺省与 DWARF64

**模块**：llvm
**项目里程碑**：M10
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（LLVM 重建 `make install-host` 由主会话执行，属长任务）

## 接口规范

### 背景事实（实测，2026-10-25，ADR-0036 关联）
- `MCAsmInfo` 默认 `CodePointerSize = 4`、`CalleeSaveStackSlotSize = 4`（`llvm/include/llvm/MC/MCAsmInfo.h:89/93`）；DADAO 的 `DADAOMCAsmInfo.cpp` **两个都没设**（整份 patch 中零命中）。
- 后果 1：`clang --target=dadao-unknown-elf -g -c` 报
  `relocatable operand in '.dd.b08/.dd.w16/.dd.t32' is not supported`；实测 `-gdwarf64 -S` 输出里 `.debug_addr` 头为 `Address size = 4`，地址落 4 字节字段 ⇒ 3 处报错。
- 后果 2：`CalleeSaveStackSlotSize=4` 直接用于 `MCDwarf.cpp:1340 getDataAlignmentFactor()`（CFI 的 `data_alignment_factor`）；当前 `ExceptionsType=None` 无 CFI，属潜伏缺陷，本次一并修正。
- 对照：AArch64 / RISC-V 均显式设 `CodePointerSize = CalleeSaveStackSlotSize = 8`。
- 选项存在性：clang 已有 `-gdwarf64` 与 `-gdwarf32`（`clang/include/clang/Options/Options.td:5141/5145`）。

### 输入
- `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch`
- `components/llvm-project/patches/clang/lib/Driver/ToolChains/DADAO.cpp.patch`（若必须改共享文件，完成区须单列理由）

### 输出
1. `DADAOMCAsmInfo` 构造加 `CodePointerSize = CalleeSaveStackSlotSize = 8;`（注释指明 64 位原生 / ADR-0036）。
2. **DADAO 默认 DWARF64**：启用调试信息时驱动默认追加 `-gdwarf64`；用户显式 `-gdwarf32` ⇒ **明确报错**（DADAO 无 32 位重定位通道，不得静默降级）；用户显式 `-gdwarf64` 时保持。
3. 位宽探针 `tools/llvm/check-width-sizes.py` + Makefile 目标 `check-width-sizes`（L1）：
   - 静态断言编译：`sizeof(void*/long/size_t)==8`、`_Alignof(max_align_t)==16`、`sizeof(long double)==16`、`__BIGGEST_ALIGNMENT__==16`；
   - 产物：`llvm-readelf -h` Class=ELF64、`.rela` entsize=24、`.got` 项=8；
   - `-g` 产物：`llvm-dwarfdump --debug-info` 的 `Address Size: 8`；
   - 每条断言有**可达 FAIL** 路径。

### 约束
- 只动上述文件 + `tools/llvm/` 新脚本 + `Makefile` 一行目标；不改 `spec/`、不改数据指令、不改其它 target。
- 先留**失败现场**（修复前 `-g` 的真实报错），再改。

## 验收标准
1. `clang --target=dadao-unknown-elf -g -c` rc=0；`llvm-dwarfdump --debug-info` 显示 `Address Size: 8`，`DW_AT_low_pc` 与符号地址一致。
2. `clang -g` 链接产物可被 `llvm-dwarfdump` 正常解析（`.debug_info` / `.debug_line`）。
3. `make check-width-sizes` 绿；**反例注入**（改被检字段使断言 FAIL）→ 红 → `cp` 还原 → 绿（禁 `git checkout` 还原）。
4. `make install-host` 后 `make check` 绿；L2 代表集绿。
5. 完成区贴真实命令、退出码、日志路径。

## 完成区
**测试结果**：静态自检全绿；真实安装根上可执行验收全绿——`.work/evidence/LLVM-130t/run.sh --with-l1` **9/9 PASS，EVIDENCE_EXIT=0**（`.work/log/llvm/LLVM-130t-evidence.log`）：`make check-width-sizes` **15/15 PASS**、`make check`（L1）rc=0；`make check-modules`（L2）**PASS / EXIT=0**（`.work/log/llvm/LLVM-130t-check-modules.log`）。证据脚本在 L2 之后复跑仍 9/9。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch`、`components/llvm-project/patches/clang/lib/Driver/ToolChains/DADAO.cpp.patch`、`tools/llvm/check-width-sizes.py`（新）、`Makefile`（`check-width-sizes` 目标/help/phony/L1 依赖；`LLVM_MC_FULL_TARGETS` 与 `HOST_LLVM_TOOLS` 增 `llvm-dwarfdump`）、`.work/evidence/LLVM-130t/run.sh`（证据，非入库）。**本轮（返工）**只改 `check-width-sizes.py`（DWARF 断言移到链接产物 + self-test 注入）与 `run.sh`（负控制加 `--link-arg=-fuse-ld=lld`）。
**验收结果**：`make check-width-sizes` 15/15（`addr_sizes=[8]`、`formats=['DWARF64']`、RELA entsizes=[24]、`.got` 8 B/1 项）；32 位负控制 4/15 过、11 FAIL 且为**值级**红（ELF32、`REL` 非 `RELA`、无 `.got`、`addr_sizes=[4]`、`formats=['DWARF32']`）；linked 检查 `low_pc=0x0000000000020158 == sym main`；`--self-test` 10 类注入全 PASS（新增 g-compile / link / rela-missing）；patch 树 198 补丁、new-file blob 135 OK；`make check` rc=0（先 `make build-musl-shared JOBS=8`，22 s，`LLVM-130t-build-musl.log`）；`make check-modules` EXIT=0；L2 后 `check-musl-freshness`/`check-builtins-freshness` 仍 PASS。
**新发现/坑**：① **`llvm-dwarfdump` 对 `.o` 返回 rc=1**——libObject 不应用 DADAO ABS48 wyde 重定位（`warning: failed to compute relocation: R_DADAO_ABS48, Invalid data encountered while parsing the file`，并连带 `.debug_str_offsets` 报错），但 CU 头本身解析正确（`addr_size = 0x08` / `format = DWARF64`）⇒ 以 `rc == 0` 为条件的 DWARF 断言**必须**放在链接后的 `-g` 产物（`-nostdlib -Wl,-e,main`，rc=0）；`.o` 只保留 ELF/RELA/GOT 段表检查；② 本版 dwarfdump CU 头是 `addr_size = 0x08` / `format = DWARF64`，任务书的 `Address Size: 8` 不存在；③ 构建/安装集原本无 `llvm-dwarfdump`（`LLVM_MC_FULL_TARGETS`/`HOST_LLVM_TOOLS` 均缺）；④ `.debug_addr` address size 真源头是 `MCAsmInfo::CodePointerSize`（`DwarfUnit.cpp:2089`、`MCDwarf.cpp:1355`），DWARF64 只改 offset 宽度（`DwarfDebug.cpp:380`）；⑤ `addClangTargetOptions` 只覆盖 cc1；⑥ 负控制若链接失败会退化成「缺文件」红，须 `-fuse-ld=lld` 才落到值级；⑦ **工具链重建后 `check-musl-freshness` 必红**（toolchain/builtins stamp 变）⇒ `make check` 前须 `make build-musl-shared`。
**遗留问题**：① cc1as/`llvm-mc` 路径的 DWARF64 默认与 `-gdwarf32` 报错需改共享 `clang/lib/Driver/ToolChains/Clang.cpp`（按约束未动，建议另立任务）；② `components/llvm-project/changelog.md` 未加条目（任务书「改动范围」未列，建议 `/complete` 时按 Process-01 §10 补）；③ 工具链重建后 musl 需重编（本轮已执行 22 s，属流程事实，建议沉淀到知识库/门控提示）。

## 审阅记录

#### 第 1 轮 engineer 自审
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 任务书 `Address Size: 8` 与本版 dwarfdump 输出格式不符 | ✅已修 | 断言改为 `addr_size = 0x08`，并增加 `format = DWARF64` 断言 | `--self-test` 注入 addr/format 均红后回绿 |
| 安装根/构建目标集无 `llvm-dwarfdump`，验收 1/2/3 不可跑 | ✅已修 | Makefile `LLVM_MC_FULL_TARGETS` + `HOST_LLVM_TOOLS` 增项 | `make help` 含新目标；`make check-width-sizes` 报缺工具（真实） |
| 负控制仅判 rc≠0 会因缺工具假绿 | ✅已修 | run.sh 要求 5 个断言族 `[FAIL]` 且输出无 `missing tool` | 预构建复跑：负控制报 families-missing=5 ⇒ FAIL（未假绿） |
| CC1As/llvm-mc 路径未覆盖 DWARF64 默认与 `-gdwarf32` 报错 | ⏸延后 | 未改共享 `Clang.cpp`（任务约束） | 已记遗留② |
| `.got` 条数不可写死 | ✅已修 | 条数 = `.rela.got` size/自身 entsize（现场算）；`.got` 缺失 vacuous FAIL | self-test got-width / got-missing 注入均红 |
| 注释误称 DWARF32「无法重定位」 | ✅已修 | 改为「ABI 无 32 位地址重定位通道」 | `-fsyntax-only` rc=0 |
| 六个静态断言需独立可达 FAIL | ✅已修 | 每条属性单独编译一次（不互相掩盖） | self-test 注入 `sizeof(long)` 仅该条红 |


#### 第 2 轮 engineer 自审（返工）
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| DWARF 断言在 `.o` 上因 dwarfdump rc=1 假红（值本身正确） | ✅已修 | 新增 `-g` 链接步骤（`-nostdlib -Wl,-e,main`），DWARF 断言改读 `sizes.elf`；ELF/RELA/GOT 仍在 `.o` | `make check-width-sizes` 15/15（返工前 4/15）；`LLVM-130t-evidence.log` 03/05 |
| self-test 未覆盖新的链接产物检查 | ✅已修 | fake-clang 支持 `-c` 检测 + `FAKE_FAIL_LINK`；新增 g-compile / link / rela-missing 注入 | `--self-test` 10 类注入全 PASS（`LLVM-130t-selftest.log`） |
| 32 位负控制链接失败，DWARF 断言退化为「缺文件」红 | ✅已修 | 新增 `--link-arg`；run.sh 负控制加 `--link-arg=-fuse-ld=lld` | 负控制 4/15，`addr_sizes=[4]`、`formats=['DWARF32']`（值级红） |
| self-test 复用同一 work 目录可能读到上一轮产物 | ✅已修 | `check_objects` 起手删残留产物；fake readelf/dwarfdump 校验输入文件存在 | self-test link 注入只报目标断言 |
| 工具链重建使 `make check` 在 `check-musl-freshness` 红（与本任务无关） | ✅已处置 | `make build-musl-shared JOBS=8`（22 s） | `make check` rc=0（`LLVM-130t-check-L1.log`） |
| `milestones.md` 未登记活任务册（第 1 轮遗留⑤） | ✅已由主会话解决 | — | `make check` 中 `check-milestones-fresh` 通过 |

#### 第 1 轮 reviewer 验收

**重跑记录**（reviewer 亲自执行，日志 ` .work/log/llvm/LLVM-130t-reviewer-*.log`）：
- `run.sh --with-l1` 首跑 check 09 红（rc=2）：根因是 reviewer 自己的日志命名 `reviewer-*.log` 触发 `check-run-artifacts` A3 名字规则（环境干扰，非交付物缺陷）；改名 `LLVM-130t-reviewer-*.log` 后重跑 **9/9 PASS，EVIDENCE_EXIT=0**（run2/run3，`LLVM-130t-reviewer-evidence-run2/3.log`；run3 = L2 之后复跑，仍 9/9）。
- `make check-modules`（L2）：`CHECK_MODULES_EXIT=0`，`module checks (L2): PASS`（`LLVM-130t-reviewer-check-modules.log`）。
- 手工端到端（`LLVM-130t-reviewer-manual.log`）：`clang -g -c` rc=0；链接 `-g` 产物 `llvm-dwarfdump --debug-info` rc=0、CU `addr_size = 0x08`、`format = DWARF64`（对照 `-g -c` 产物 11 个 `.debug*` 段）；`-gdwarf32`（compile/link 三式）均 rc=1 `unsupported option`；`-g0` 无任何 `.debug*` 段（grep rc=1）。显式 `-gdwarf64` rc=0。
- `check-width-sizes` 15/15：`addr_sizes=[8]`、`formats=['DWARF64']`、entsizes=[24]、`.got` 8 B/1 项（restore 日志）。
- **独立反例注入**（非 self-test）：把真实链接 `-g` 产物 `.debug_info` 偏移 0x1F2 的 CU `addr_size` 字节 8→4（`cp` 副本 + md5，未动仓库文件）→ dwarfdump 输出 `addr_size = 0x04`（并 abort rc=134）→ 探针 `--dwarfdump` 指向该注入产物：**13/15、`[FAIL] DWARF CU addr_size`、PROBE_EXIT=1**；还原后回绿 **15/15、rc=0**（inject/restore 日志）。
- 32 位负控制独立复跑：rc=1，**4 PASS / 11 FAIL**，值级红（ELF32、entsizes=[]、无 `.got`、`addr_sizes=[4]`、`formats=['DWARF32']`）——与完成区一致。
- `check-patch-tree`：`198 patches OK` rc=0；`check-index-blobs` rc=0；`check-install-tools` PASS（48 项，含 `llvm-dwarfdump` 在安装集）。

**约束核验**：改动范围 = 完成区声明的 5 文件（`git diff master...HEAD` 另含主会话登记的 milestones.md/任务书本身）；Makefile 仅 L1 列表/help/`LLVM_MC_FULL_TARGETS`/`HOST_LLVM_TOOLS`/目标块；未动 `spec/`、其它 target。前后快照对账：`git status` 前后均 0 行、5 目标文件 md5 前后一致、注入物已清。

**判决：Accepted**。完成区数字（9/9、15/15、4/15、198、low_pc=0x20158）与 reviewer 重跑逐条相符；未发现阻断项。遗留②（changelog 条目）由 `/complete` 收尾时按 Process-01 §10 处理。
