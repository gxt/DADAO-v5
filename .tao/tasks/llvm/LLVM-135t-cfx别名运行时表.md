# LLVM-135t: cfx 别名运行时表（源码/反汇编共用；数据更新不重建 LLVM）

**模块**：llvm
**项目里程碑**：M10
**依赖**：SPEC-175t（`cfx_time` 改名）、`contract-cfx-aliases.md`（生成契约）
**状态**：已验证

## 执行环境
本地（LLVM 组件补丁 + 生成器 + Makefile + lit；需重建一次 LLVM）

## 接口规范

### 背景（用户 2026-10-26 裁定）
- 源码要用 **`cfx_<name>` / `cfx_<name>_<reg>`**；反汇编也要**名字**，不是 `cfx15, cg8, rc2`。
- `cfx_<name>` 与寄存器号**会经常变**；不允许「改一个号就重建 LLVM」。
- `cfx<HA>` 形式**保留**为裸/回退（reserved cfx、未知编码、表缺失时反汇编回退），不作为源码主风格。
- 表落点（已确认）：
  - 源：`contracts/cfx-aliases.txt`（提交、生成、门控）；
  - 构建树：`.work/build/llvm/share/dadao/cfx-aliases.txt`；
  - 安装根：`.dadao/cross-toolchain/share/dadao/cfx-aliases.txt`；
  - 查找：显式参数 → `DADAO_CFX_ALIAS_FILE` → `<可执行文件目录>/../share/dadao/cfx-aliases.txt`。

### 目标
1. **删除编译期表**：`DADAOCfxAlias.inc` 不再 `#include` 进 AsmParser；改为运行时加载文本表（**双向**）。
2. **AsmParser**：`trap/escape/cfxld/cfxst/cfx2rd/cfx2rc` 的 cfxha 与寄存器别名从表解析；`cfx<HA>` 语法保留。
3. **MCInstPrinter**：`cfx2rd/cfx2rc/cfxld/cfxst/trap/escape` 优先打印名字（含 `cfx_ptw_ptbr[3]` 数组形式）；无名字回退 `cfx<HA>, cgN, rcN`。
4. **生成器**：扩展 `tools/llvm/gen_cfx_alias_table.py`（或新增 `gen_cfx_alias_file.py`），从 spec 投影生成 `contracts/cfx-aliases.txt`（标量/寄存器/数组；含 canonical 标记）。
5. **安装**：`make install-host` 安装表；新增 `make install-cfx-aliases`（只拷贝、不重建）；构建树复制到 `.work/build/llvm/share/dadao/`。
6. **门控**：`gen --check`（源表 ↔ spec）、`check-cfx-alias-install`（安装表 ↔ 源表）；`llvm-mc`/`objdump` 缺表行为可判。
7. **修 `cfx_time` 回归**：表中包含 `cfx_time_freq`/`cfx_time_value`/`cfx_hart_timer_cmp`/`cfx_hart_timer_ctrl`；lit 向量改回名字（预期重新可汇编/反汇编为名字）。

### 表格式（建议，文本）
```
# format=1
scalar  cfx_umon   0   canonical
scalar  cfx_hmon   3   canonical
reg     cfx_hart_cycle_lo  15  8  2   1   canonical
reg     cfx_ptw_ptbr       4   9  0   64  canonical
```
（`scalar` = cfxha；`reg` = cfxha, cg, rc_base, count；`canonical` 用于同编码多名的反汇编选择。）

### 关键约束
- 只改 LLVM 组件补丁 + 生成器 + Makefile + lit + `contracts/cfx-aliases.txt` + 任务书/`milestones.md`；**不改** spec/契约正文（表由 spec 生成）。
- 组件补丁按 `docs/Process-01`（一文件一补丁、`series`、`check-patch-tree`）；LLVM 重建按 AGENTS 规则（`make install-host`，申报耗时）。
- `cfx<HA>` 保留；不删除裸形式。
- 反汇编缺表**不报错**（裸回退）；汇编缺表且用了名字 ⇒ **报错**。
- 临时目录 `/tmp/opencode/LLVM-135t/`；不提交。

## 验收标准
1. **名字汇编**：`llvm-mc` 用 `cfx_hart_cycle_lo` / `cfx_ptw_ptbr[3]` / `cfx_time_value` / `trap cfx_umon` 汇编成功。
2. **名字反汇编**：`llvm-objdump -d` 输出 `cfx_hart_cycle_lo`、`cfx_ptw_ptbr[3]`、`cfx_umon`；reserved/未知 cfx 回退 `cfx<HA>, cgN, rcN`。
3. **缺表**：汇编用名字 ⇒ 非零退出并报错；objdump ⇒ 裸回退（exit 0）。
4. **不重建证明**（关键）：LLVM 安装完成后，用 `DADAO_CFX_ALIAS_FILE` 指向一份临时改名的表（如 `cfx_hart`→`cfx_hartx`），`llvm-mc`/`llvm-objdump` 立即反映新名，**不重建 LLVM**；还原后回绿。
5. 门控：`gen --check`、`check-cfx-alias-install`、`check-patch-tree`、`check-lit`、`make check` 全 rc=0。
6. `make install-host` 后 `.dadao/cross-toolchain/share/dadao/cfx-aliases.txt` 存在且与源表一致；build-tree 同名文件存在。
7. 证据脚本 `.work/evidence/LLVM-135t/run.sh`（含注入→FAIL→还原→PASS）；完成区 ≤30 行。

## 完成区

**状态**：已验证

**测试结果**：证据脚本 49/49（含注入→FAIL→`cp`+md5 还原→PASS）；`make check` rc=0；`check-lit` 154/154；
`check-patch-tree` 5 组件/203 补丁 OK；`check-musl-freshness` rc=0；`check-cfx-vectors` 16/16。

**修改文件**：
- 组件补丁（`.work/source/llvm-project` → `components/llvm-project/patches`+`series`）：`MCTargetDesc/DADAOCfxAliasTable.{h,cpp}`（新）、`DADAOMCInstPrinter.cpp`、`MCTargetDesc/CMakeLists.txt`、`AsmParser/DADAOAsmParser.cpp`、`AsmParser/CMakeLists.txt`；删除 `AsmParser/DADAOCfxAlias.inc`（补丁同删）。
- 生成/门控：`contracts/cfx-aliases.txt`（新）、`tools/llvm/gen_cfx_alias_table.py`（改产 txt + `--check`）、`tools/llvm/check_cfx_alias_install.py`（新）、`Makefile`（`install-cfx-aliases`/3 门控/install-host 收尾）、`tools/infra/check_contracts_dir.py`、`tools/infra/build_musl.py`、`tools/testcases/generate_lit_vectors.py`。
- lit/台账：`cfx2-trap-escape.s`、`cfx-alias-runtime.s`（新）、`gen-fast.s`、`DADAO-gen/gen-{ciii,crrr}.s`、`tests/case-ledger.tsv`（`--write`）、`README-m5.md`、`components/llvm-project/changelog.md`、`.tao/knowledge/milestones.md`、本任务书。
- 证据：`.work/evidence/LLVM-135t/run.sh`；日志 `.work/log/llvm/LLVM-135t-*.log`。

**验收结果**：
- 名字汇编（`llvm-mc` rc=0）：`cfx2rd cfx_hart_cycle_lo, rd1` / `cfx2rd cfx_ptw_ptbr[3], rd2` / `cfx2rd cfx_time_value, rd3` / `trap cfx_umon, 0` → `7a 3c 80 81` / `7a 10 90 c2` / `7a 48 a2 03` / `7f 00 00 00`。
- `llvm-objdump -d` 打印同样**名字**；reserved/未知回退 `trap cfx20, 0`、`cfx2rd cfx0, cg8, rc1, rd2`。
- 缺表（`DADAO_CFX_ALIAS_FILE` 指向不存在文件）：汇编用名字 rc=1 + `error: cannot resolve 'cfx_umon': cannot read cfx alias table '…' No such file`；objdump rc=0 且裸回退。`cfx0` 无表仍可汇编（rc=0）。
- 不重建证明：`DADAO_CFX_ALIAS_FILE` → 改名表（`cfx_hart`→`cfx_hartx`）后同一 `llvm-objdump` 立刻打印 `cfx_hartx_cycle_lo`、汇编接受新名/拒绝旧名；`clang -mllvm -dadao-cfx-alias=`（cc1as）同样生效；`llvm-mc`/`llvm-objdump` md5 前后不变；默认表回绿。
- 表落点：`contracts/cfx-aliases.txt`（13 标量 + 894 寄存器）、`.work/build/llvm/share/dadao/`、`.dadao/cross-toolchain/share/dadao/` 三处 md5 一致（`ab91f025…`）。
- `make install-host` PASS（重建 LLVM/工具链，clang build-id `17e7f104…`）；`make install-cfx-aliases` 只拷贝；L2 `make check-modules` rc=0。

**新发现/坑**：
- cc1 的 I/O sandbox（`LLVM_ENABLE_IO_SANDBOX`）会拦运行期读表 ⇒ `clang -c x.S`（cc1as）用 cfx 名字即 `IO sandbox violation` fatal；读表须 `sys::sandbox::scopedDisable()`（表是辅助数据、非编译输入）。
- 打印名字后，所有"裸形式"文本断言都要改：`build_musl.py` 的 `trap cfx0, 0` 检查（现接受 `cfx_umon`）、`generate_lit_vectors.py` 的 ASM 期望（改为按 `contracts/cfx-aliases.txt` 派生）、`tests/case-ledger.tsv` 需 `--write` 重生成。
- 任何 LLVM 重建都会换 clang build-id ⇒ `check-musl-freshness` 红，须补 `make build-musl-shared`。
- `GATE_LOCKED_TARGETS` 成员只能写 `_locked-<name>` 目标体；直接写同名 recipe 会覆盖锁包装规则（make 警告 + 丢锁）。

**遗留问题**：无。（`cfxld`/`cfxst` 无 MC def，printer 无打印路径；缺表时反汇编静默回退，未加 stderr 警告——按需求。）

## 审阅记录

#### 第 1 轮 engineer 自审

**方式**：自主逐行审查（`subagent_depth=1`）+ 真实构建/运行反证（编译错误、cc1as、musl 构建、`make check*`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `DADAOCfxAliasTable.h` 被放在 AsmParser 的匿名 namespace 内 ⇒ 声明成内部链接、`llvm::DADAO::lookup…` 找不到 | ✅已修 | 头文件 include 移到文件顶部 include 块 | `ninja LLVMDADAOAsmParser` rc=0；补丁第 25 行为 include |
| F2 `std::string` 无 `starts_with`；`if (std::string Err=…)` 不能隐式转 bool | ✅已修 | `StringRef(A.Name).starts_with("cfx_")`；`Err.empty()` | `ninja LLVMDADAODesc` rc=0 |
| F3 cc1 I/O sandbox 拦运行期读表 ⇒ `clang -c x.S`（cc1as）用 cfx 名字即 `IO sandbox violation` fatal | ✅已修 | 读表处 `sys::sandbox::scopedDisable()`（表为辅助数据、非编译输入） | `clang --target=dadao -c t.S` rc=0 + objdump 名字；`build-musl-shared` PASS |
| F4 打印名字破坏既有"裸形式"文本断言（`build_musl.py`、`generate_lit_vectors.py`、`case-ledger.tsv`） | ✅已修 | 接受 `cfx0`/`cfx_umon` 两写法；ASM 期望改由 `contracts/cfx-aliases.txt` 派生；ledger `--write` | build-musl 10/10、`check-lit` 154/154、`check-case-ledger` PASS |
| F5 `install-cfx-aliases` 直接写 recipe 覆盖了 `GATE_LOCKED_TARGETS` 生成的锁包装（make "overriding recipe" 警告 ⇒ 丢锁） | ✅已修 | 改名为 `_locked-install-cfx-aliases`，由锁包装调用 | `make install-cfx-aliases` PASS 无警告 |
| F6 `.work/log/**.EXIT` 违反 `check-run-artifacts` A3 命名（AGENTS 的 `XXX_EXIT=$rc` 与之冲突） | ✅已处置 | 删 `.EXIT`，退出码以 `[exit marker] … rc=N` 追加进同名 `.log` | `check-run-artifacts` PASS（0 illegal）；`make check` rc=0 |
| F7 LLVM 重建 ⇒ clang build-id 变 ⇒ `check-musl-freshness` 必红（既有耦合） | ✅已处置 | 每次重建后补 `make build-musl-shared` | 最终 `check-musl-freshness` PASS |
| F8 生成器重复了 printer 的 canonical 名字选择规则（漂移风险） | ⏸接受 | 不新增共享代码（Python vs C++） | lit ASM 期望即交叉校验：不一致 ⇒ `check-lit` 红 |
| F9 反例可达性：注入必须能真红 | ✅已证 | 注入改 install 根表（`cfx_umon`→`cfx_umonx`） | `check-cfx-alias-install` rc=1 + objdump 打出 `cfx_umonx`；`cp`+md5 还原后 rc=0 |

**判决**：finding 全部处置（F8 说明为由 lit 自证的可接受重复），状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**方式**：本人真实重跑（不采信完成区转述）+ 独立不重建证明 + 独立注入反例（reg 名，异于 engineer 的 scalar 注入）。

**重跑记录（真实 rc）**：
- `check-cfx-alias-table` / `check-cfx-alias-install` / `check-cfx-vectors` / `check-patch-tree` / `check-musl-freshness`：**rc=0**（本人逐条实跑）。
- `make check` **rc=0**、`make check-lit` **rc=0**（本人后台实跑）；`make check-modules` rc=0 + lit `Passed: 154 (100.00%)`（architect 日志 modules.log，本人抽查核对）；`run.sh` 全量 **49/49 PASS**（architect evidence.log）+ 本人两轮 `--quick` 交叉验证（见下）。
- 三处表 md5 一致 `ab91f025…`（contracts / build 树 / 安装根）。

**独立不重建证明**：`cp` 源表到 /tmp、sed 改一条 **reg**（`cfx_hart_cycle_lo`→`cfx_hartx_cycle_lo`）→ `DADAO_CFX_ALIAS_FILE` 指向它：objdump 同一二进制立即打 `cfx_hartx_cycle_lo`；`llvm-mc` 新名 rc=0、旧名 rc=1（`invalid operand`）；`llvm-mc`/`llvm-objdump` md5 前后一致（`d00051c5…`/`35bd0b84…`，未重建）。默认路径：异 cwd 无环境变量仍打名字（`<exe>/../share/dadao/` 生效）。

**缺表行为**：名字汇编 rc=1 + `cannot resolve 'cfx_hart_cycle_lo': … No such file`；objdump rc=0 裸回退 `cfx15, cg8, rc2, rd1`/`trap cfx0, 0`；`cfx0` 无表可汇编 rc=0。名字覆盖 `cfx_hart_cycle_lo`/`cfx_ptw_ptbr[3]`/`cfx_time_value`/`trap cfx_umon` 编码与契约逐字节相符；reserved `trap cfx20, 0`、未知 `cfx2rd cfx0, cg8, rc1, rd2` 回退正确。

**独立注入→FAIL→还原→回绿**：安装根表 sed 注入 `reg cfx_hart_cycle_lo`→`cfx_hartx_cycle_lo` → `check-cfx-alias-install` **rc=2**（sha256 漂移 FAIL）；`run.sh --quick` **rc=1、22 条 [FAIL]、RESULT: FAIL**；objdump 默认路径打出注入名（数据驱动实证）。`cp` 备份还原，md5 复归 `ab91f025…`、注入残留 0 行 → 门控 rc=0、`run.sh --quick` PASS rc=0。

**约束核验**：① `check-cfx-alias-install` 不在 L1（Makefile:835 依赖表核对，0 命中）；② 补丁树合规：旧 `DADAOCfxAlias.inc.patch` 已删、新 `DADAOCfxAliasTable.{h,cpp}.patch` 入、series 两行新增一致，`check-patch-tree` rc=0；③ 生成器 `--check` 从 spec D12/D13 投影（非从 LLVM/实现反推）；④ `build_musl.py`/`generate_lit_vectors.py`/`check_contracts_dir.py` 改动为名字化必要适配（期望由 `contracts/cfx-aliases.txt` 派生、断言未删未弱化）；⑤ 提交范围与完成区「修改文件」一致，未越界改 spec/契约正文；⑥ 快照对账：验收前后 `git status -uall` 均 0 行，工具二进制 md5 未变，注入仅 /tmp + 安装根副本且已还原。

**判决**：**Accepted**（验收标准 1–7 全部经本人重跑/独立反证成立；文档级无发现）。
