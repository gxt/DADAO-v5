# LLVM-141t: cfx 别名表 format=2 + stride 数组（cg7 `space_*[i]` 可汇编）

**模块**：llvm
**项目里程碑**：M10
**依赖**：`LLVM-135t`（cfx 别名运行时表，已验证）、`SPEC-179t`（cg7 stride 4 口径 + 投影，已验证）；`INTEG-049t` 仅登记本缺口（QEMU 侧，不阻塞）
**状态**：待开始

## 执行环境

**执行环境**：本地（仓库根，开工分支 `LLVM-141t`）；`.work/source/llvm-project`、`.work/build/llvm`、`.dadao/cross-toolchain` 均在场；临时目录 `/tmp/opencode/LLVM-141t/`；**不跑夜跑**。

## 背景与问题根源（预检实测）

1. **spec 已是 stride-4 数组**：`spec/DADAO-12 §3.8` 定义 cg7 每 4 个 rc 一个空间块（`rc = 4i+K`，`i=0..15`，K=0..3 为 desc/start/size/attr），`SPEC-179t` 已把它投影到契约与生成器（`.tao/contracts/contract-cfx-aliases.md` 的 rc 列即 `4i+0` 等）。
2. **运行时表 format=1 表达不了 stride**：`contracts/cfx-aliases.txt` 的 `reg` 语义是 `rc = rc-base + N`（stride 1），生成器只能把 cg7 展开成 **768 条** `reg cfx_<name>_space_*[n] ... <rc> 1 canonical`（名字里带字面下标、`rc-count=1`）。
3. **汇编端因此不可用（实测，rc=1）**：
   ```
   $ printf 'cfx2rd cfx_umon_space_desc[0], rd1\n' | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
   error: invalid operand for instruction
   ```
   `DADAOAsmParser` 先取 token `cfx_umon_space_desc` 查表，而表中登记名是 `cfx_umon_space_desc[0]` ⇒ 永不命中；`rc-count=1` 又使下标分支不被触发。
4. **打印端能出名字、往返却断裂（实测）**：`cfx2rd cfx0, cg7, rc20, rd1` 反汇编输出 `cfx2rd cfx_umon_space_desc[5], rd1`，但把该行再交给 `llvm-mc` 即上述 rc=1 ⇒ asm↔objdump 不能往返（工具链可用性缺陷）。
5. **连续数组正常，不能回归**：`cfx_umon_scratch_regs[3]`（`reg` count=64 stride=1）、`cfx_ptw_ptbr[3]`（专用 `reg` count=64）汇编/反汇编均正常。
6. **缺口已登记**：`SPEC-179t` 遗留 2、`INTEG-049t`「风险与已知缺口 5」均写明「运行时表 format=1 无 stride 字段，LLVM 汇编端暂不可拼写」。

## 用户授权（主会话下发原话，逐字摘录）

> - `contracts/cfx-aliases.txt` 升级 `format=2`，保留 `format=1` 读取兼容；
> - 新行 `array <name-base> <cfxha> <cg> <rc-base> <count> <stride> [canonical]`；
> - cg7 生成 48 条 array（12 cfx × 4 字段）：`cfx_<name>_space_desc/start/size/attr`，rc=4i+0/1/2/3，count=16，stride=4；
> - 连续数组继续用 `reg`；`regs` 统计仍按展开别名 1430；
> - `rc = rcBase + N*stride`；越界按 count；
> - LLVM 解析器支持 format=1/2；`RegAlias` 增加 stride；
> - `DADAOAsmParser` 数组下标按 stride；
> - `gen_cfx_alias_table.py`、`gen_cfx_aliases.py`（如需）、`validate_cfx_vectors.py`、`check-cfx-alias-table` 同步；
> - lit 覆盖 `space_desc[0]/[5]/[15]/[16]`、旧 format=1 兼容、连续数组不回归；
> - 不改 QEMU、不改 spec 语义。

（下发指令称此为「A 方案」；其内容以上述逐条设计为准，未另行展开。来源 = 主会话 2026-10-31 下发本任务书指令。）

## 目标

1. **表格式 v2**：`contracts/cfx-aliases.txt` 升级 `format=2`，新增 `array` 行；cg7 由 768 条字面下标 `reg` 收敛为 **48 条 array**；连续数组保持 `reg`；总展开别名数仍 **1430**。
2. **LLVM 端 stride**：表解析器同时接受 `format=1`（旧表原样可读）与 `format=2`；`RegAlias` 增 `stride`，`covers`/打印下标按 `rc = rcBase + N*stride`；汇编器下标按 stride 落 rc。
3. **可用性**：`llvm-mc` 能汇编 `cfx_<name>_space_{desc,start,size,attr}[N]`（N=0..15），`llvm-objdump` 打印同名并可往返；N=16 硬报错。
4. **同步与回归**：生成器、安装门控、lit 向量生成器同步到 format=2；连续数组、旧 format=1 表、既有 159 条 lit 全不回归。

## 接口规范

### 1. 表格式 `format=2`（`contracts/cfx-aliases.txt`，生成物）

头行与语法（`#` 注释、空行忽略；字段以空格分隔）：

```
# format=2
# Grammar: scalar <name> <cfxha> [canonical]
#          reg    <name> <cfxha> <cg> <rc-base> <rc-count> [canonical]
#          array  <name-base> <cfxha> <cg> <rc-base> <count> <stride> [canonical]
# scalars=12 regs=1430
```

- `scalar`：不变（`cfx_<cfxname>` ⇔ cfxha）。
- `reg`：不变，语义仍是 `rc = rc-base + N`（stride 1）；连续数组（`scratch_regs`、`cfx_pmem_{start,size,attr}`、`cfx_uart_uart*_regs`）继续用它。
- `array`：单下标 `name-base[N]` ⇔ `(cfxha, cg, rc = rc-base + N*stride)`，`N ∈ [0, count)`；`name-base` 不含方括号。
- `canonical` 语义不变。
- **计数口径**：`regs=` = **契约层展开别名数**（沿用 `gen_cfx_aliases.py::build_register_aliases` 的口径：cg7 每个元素各计 1、`[0..63]` 行计 1 条），即 `12 × 116 + 38 = 1430`；**不是**数据行数（行数应为 12 scalar + 662 reg + 48 array = 722 数据行）。生成器不得把 `regs` 改成行数。
- **cg7 的 48 条**（12 cfx × 4 字段；cfxha 按 `umon0/jmon1/smon2/hmon3/ptw4/cache5/hart15/llc16/pmem17/time18/uart62/power63`）：
  ```
  array cfx_umon_space_desc   0 7 0 16 4 canonical
  array cfx_umon_space_start  0 7 1 16 4 canonical
  array cfx_umon_space_size   0 7 2 16 4 canonical
  array cfx_umon_space_attr   0 7 3 16 4 canonical
  ...（其余 11 个 cfx 同形，cfxha 替换）
  ```
  即每 cfx 的 rc-base 分别为 0/1/2/3、count=16、stride=4；`[5]` ⇒ rc=20，`[15]` ⇒ rc=60。
- **行序**：`scalar` 在前；`reg`/`array` 统一按 `(cfxha, cg, rc-base, count, name)` 升序，保证 `--check` 幂等。
- **不再出现**：任何 `reg cfx_*_space_*[...]` 行（字面下标数组）。

### 2. LLVM 运行时表与汇编器（组件补丁）

改动文件（`.work/source/llvm-project` → `make_patch.py` 导出）：

- `MCTargetDesc/DADAOCfxAliasTable.h`
  - `lookupCfxRegAlias` 增加输出 `unsigned &RcStride`（数组步长；非数组为 1）；
  - 注释改为 `rc = rcBase + N*stride`，`RcCount>1` 即数组。
- `MCTargetDesc/DADAOCfxAliasTable.cpp`
  - `RegAlias` 增 `unsigned Stride = 1`；
  - `covers(Cg, Rc)`：`Cg` 相等、`Rc >= RcBase`、`(Rc-RcBase) % Stride == 0`、`(Rc-RcBase)/Stride < RcCount`；
  - `parseTable`：接受 `# format=1` 与 `# format=2`；`array` 仅 `format=2` 合法（format=1 中出现 ⇒ 该行报错 `'array' requires a '# format=2' header`）；`reg` 在两种格式下均按 stride=1；
  - `array` 校验：字段数 6/7；`count ∈ [1,64]`、`stride ∈ [1,64]`、`RcBase + (count-1)*stride <= 63`；名字以 `cfx_` 开头；跨 scalar/reg/array 查重（fail-closed，整表拒绝）；
  - **不得**因名字含 `[`/`]` 而拒绝：format=1 旧表含 `cfx_umon_space_desc[0]`、`cfx_umon_scratch_regs[0..N−1]` 等字面名，必须原样可读（旧表兼容）；
  - `getCfxRegName`：`RcCount>1` 时下标 = `(Rc-RcBase)/Stride`，输出 `name[index]`；
  - `parseTable` 末尾的缺头错误同时接受两种格式（报 `missing '# format=' header` 之类即可，不得只认 format=1）。
- `AsmParser/DADAOAsmParser.cpp`
  - 调用点取 `RcStride`；下标越界仍按 `RcCount` 判；rc = `RcBase + Sub*RcStride`；
  - 注释/诊断同步（`rcBase + N*stride`；范围文案 `[0, count-1]`）。

### 3. 生成器、门控与消费者同步

1. `tools/llvm/gen_cfx_alias_table.py`
   - 头注释/`FORMAT_LINE`/grammar 注释升级 `format=2`；
   - 直接用 `parse_register_tables` 的 `stride`/`expand_count`/`array_offset` 产出 `array` 行（**不要**用「展开后再按名字反推分组」的启发式）；
   - 非 stride 条目仍产 `reg`（含 `[0..63]` 行，count 由现有 `split_range` 得出）；
   - 断言改为 `RcBase + (count-1)*stride <= 63`（现 `base + count <= 64` 对 stride>1 是错的）；
   - 头行 `# scalars=… regs=…` 的 regs 取自投影器 `len(build_register_aliases(...))`（=1430），不得用行数；
   - `--check` 行为不变。
2. `tools/llvm/check_cfx_alias_install.py`
   - 源表头接受 `# format=1`/`# format=2`（`FORMAT_LINES`）；`--self-test` 增加一条 format=2 绿例（仍保留红例）。
3. `tools/testcases/generate_lit_vectors.py`
   - `_load_cfx_aliases` 增 `array` 解析（元组带 stride）；`_cfx_reg_name` 选择/下标按 stride（`(rc-base)//stride`，须整除）；
   - 生成物对现有用例必须**零变化**（`check_lit_gen.py` 与 `gen-fast.s`/`DADAO-gen/` 逐字节一致）。
4. `tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py`
   - 预期**无需改**（已按 `4i+K` 解析 stride）；仅当新向量暴露 stride 解析缺陷时做最小修正，并说明。
5. `tools/spec/gen_cfx_aliases.py` 与 `.tao/contracts/contract-cfx-aliases.md`
   - 预期**不改**（契约已含 `4i+K` 与 1430 统计）；`make check-cfx-aliases` 必须 byte-identical。仅在门控失败时最小修正。

### 4. lit 与独立向量

- 新增 `tests/unit/llvm/lit/MC/DADAO/cfx2-space-stride.s`（**文件名以 `cfx2-` 开头**，`validate_cfx_vectors.py` 才会纳入独立 oracle）：
  - 默认表：`cfx2rd cfx_umon_space_desc[0]`、`cfx_umon_space_desc[5]`、`cfx_umon_space_size[15]`、`cfx_umon_space_attr[15]` 汇编 rc=0；`objdump` 打印同名（证明 printer 用 stride 反算下标，而非 rc 原值）；行内 `@@ @enc` 由 oracle 派生（`[5]` ⇒ rc20、`[15]` ⇒ rc60），`@@ OBJ:` 字节双写。
  - 连续数组回归：`cfx_umon_scratch_regs[3]`、`cfx_ptw_ptbr[3]` 汇编/反汇编与现状一致。
  - **format=1 兼容**：临时写 `# format=1` + `reg cfx_bar 0 7 0 16` 表，`cfx2rd cfx_bar[5], rd1` 可汇编、反汇编打印 `cfx_bar[5]`（连续数组 stride=1 不变）。
  - **format=2 数据驱动**：临时写 `# format=2` + `array cfx_foo_bar 0 7 0 16 4 canonical`，`cfx2rd cfx_foo_bar[5], rd1` 可汇编、反汇编打印 `cfx_foo_bar[5]`（同一二进制、只换数据文件，不重建）。
- 新增 `tests/unit/llvm/lit/MC/DADAO/cfx2-space-stride-err.s`：`space_desc[16]` ⇒ 非零 + `out of range`；`cfx_umon_space_desc` 无下标 ⇒ `single subscript is required`。
- 既有 `cfx-alias-runtime.s` 不改（其自带 `# format=1` 表，作为旧格式兼容回归）。

## 修改文件范围

1. `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOCfxAliasTable.h.patch`
2. `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOCfxAliasTable.cpp.patch`
3. `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`
4. `components/llvm-project/changelog.md`（M10 节末追加 1 条）
5. `contracts/cfx-aliases.txt`（重新生成）
6. `tools/llvm/gen_cfx_alias_table.py`
7. `tools/llvm/check_cfx_alias_install.py`
8. `tools/testcases/generate_lit_vectors.py`
9. `tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py`（**如需**，最小修正）
10. `tests/unit/llvm/lit/MC/DADAO/cfx2-space-stride.s`（新增）
11. `tests/unit/llvm/lit/MC/DADAO/cfx2-space-stride-err.s`（新增）
12. `tests/unit/llvm/lit/MC/DADAO/README-m5.md`（索引追加两行）
13. `.tao/knowledge/milestones.md`（本任务流水行）
14. 本任务书（完成区 + 状态）

**明确不动**：`spec/**`、`.tao/adr/**`、`components/qemu/**`、`.tao/contracts/contract-cfx-aliases.md`（除非门控失败）、`contracts/opcodes.yaml`、`tests/inst/**`、`manifests/**`、`docs/**`（`docs/DDLN` 旧口径另立文档任务）、`Makefile`（无格式依赖）。

## 约束

1. **最小改动**：只做 format=2 + stride 语义；不改 ISA/权限/编码，不动 QEMU，不新增其它表字段。
2. **fail-closed**：表解析错误整表拒绝；汇编报错，反汇编仍裸回退 `cfx<HA>, cgN, rcN`（exit 0），与 LLVM-135t 一致。
3. **组件补丁纪律**（`docs/Process-01`）：只在 `.work/source/llvm-project` 改；E1 起点自检 → 改动 → 收敛为 base+1 单 commit → `python3 tools/infra/make_patch.py llvm-project` → `make check-patch-tree` → `make check-source-state`；**禁**手改补丁。
4. **重建与安装**：解析器变更必须重建。`make install-host` 为增量（预计 5–20 min；超过 10 min 用 `setsid nohup` + 日志 + `EXIT` 标记，不空等），完成后补 `make build-musl-shared`（clang build-id 变 ⇒ `check-musl-freshness` 需回绿）。**禁**手工 `cp` 二进制到安装根（`ISS-300`）。
5. **数据与二进制同步**：`make install-cfx-aliases`（或 `install-host` 前置）把新表同步到构建树与安装根；混合态（新二进制 + 旧表）只允许旧表格式=1 可读；旧二进制 + 新表会整表拒绝（裸回退），由安装门控兜底。
6. **证据**：`.work/evidence/<任务ID>/run.sh` 一键复跑，含 ≥1 项「注入 → FAIL → 还原 → PASS」（还原用 `cp` + md5，**禁** `git checkout/restore/stash/show`）。
7. **临时目录** `/tmp/opencode/LLVM-141t/`；日志 `.work/log/llvm/`；仓库内不得留临时文件/残留。
8. **不提交、不 push**：engineer 只改文件 + 填完成区；提交权归 architect。
9. **门控互斥**：构建/安装/门控一律经 `make`（自动 `flock` 排队）；不绕过、不 kill 他人任务；发现外部并行改动导致 L1 抖动时保留现场、重跑，不改外部任务书。

## 验收标准

1. **表格式与计数**：`head -1 contracts/cfx-aliases.txt` = `# format=2`；grammar 注释含 `array`；`grep -c '^array '` = **48**；`grep -c '^reg '` = **662**；`grep -c '^scalar '` = **12**；`grep -c '^reg .*_space_.*\['` = **0**；头行 `# scalars=12 regs=1430`。
2. **48 条 array 逐条**：每行形如 `array cfx_<name>_space_{desc,start,size,attr} <cfxha> 7 <K> 16 4 canonical`（K=0/1/2/3），cfxha 与 12 个 cfx 一一对应；用脚本逐行断言（不得抽样）。
3. **生成物最小 diff**：`git diff -U0 contracts/cfx-aliases.txt` 的删除行**全部**匹配 `^reg cfx_.*_space_(desc|start|size|attr)\[[0-9]+\]`（768 条），新增行为 48 条 array + 头/语法 2 行（`# format=2`、`array` 语法行；`# scalars=12 regs=1430` 不变）；其余行零变化。
4. **漂移门控**：`make check-cfx-alias-table` rc=0（`12 scalars, 1430 regs`）；`make check-cfx-aliases` rc=0（byte-identical，契约 md 未变）。
5. **安装门控**：`make install-cfx-aliases` 后 `make check-cfx-alias-install` rc=0（源表/构建树/安装根 sha256 一致，6+ checks），`--self-test` rc=0（新增 format=2 用例）。
6. **汇编/反汇编（默认表）**：`llvm-mc` 汇编 `cfx_umon_space_desc[0]`/`[5]`/`space_start[5]`/`space_size[15]`/`space_attr[15]` 全部 rc=0；`llvm-objdump -d` 输出同名；同一 `.o` 再汇编-反汇编往返一致（`cmp`）。
7. **独立编码 oracle**：`make check-cfx-vectors` rc=0，新向量计入（行内 `@enc` 由 `opcodes.yaml` + 契约 md 独立派生；`[5]`/`[15]` 必须分别等于 rc=20/60 的编码，**不得**从 llvm-mc 反推）。
8. **越界/缺下标**：`space_desc[16]` ⇒ rc≠0 且报 `out of range`；`cfx_umon_space_desc`（无下标）⇒ rc≠0 且报 `single subscript is required`（两例均在 lit err 文件中有可达 FAIL 断言）。
9. **格式兼容**：format=1 临时表（`reg` 连续数组）在新二进制下可汇编/反汇编；format=2 临时表（`array` 改名）可汇编/反汇编且打印新名 ⇒ 数据驱动、不重建；缺表行为与 LLVM-135t 一致（asm 用名硬报错、objdump 裸回退 rc=0）。
10. **连续数组不回归**：`cfx_umon_scratch_regs[3]`、`cfx_ptw_ptbr[3]` 的汇编/反汇编输出与改动前一致（记录改动前字节作对照）。
11. **门控**：`make check-lit` rc=0（基线 159 + 新增用例，全 PASS）；`make check` rc=0（L1）；`python3 tools/testcases/check_lit_gen.py --full-dir tests/unit/llvm/lit/MC/DADAO-gen --fast-file tests/unit/llvm/lit/MC/DADAO/gen-fast.s` rc=0 且生成物零变化；`make check-patch-tree`、`make check-source-state`、`make check-component-changelog`、`make check-tests-index` rc=0。
12. **证据与收尾**：`bash .work/evidence/<任务ID>/run.sh` rc=0；`--inject` 至少 1 项可达 FAIL（建议把某 array 的 stride 由 4 改 2，或把 `getCfxRegName` 的下标算法改回 `rc-rcBase`，验证后 `cp`+md5 还原）；完成区 ≤30 行、`**状态**` = `待验收`、`milestones.md` 流水行同步；`git status --porcelain -uall` 无仓库内临时残留。

## 下发前预检（5 项，architect 本轮实测）

1. **任务书内部一致**：目标 4 项 / 接口规范 4 节（表格式、LLVM、生成器与消费者、lit）/ 修改文件 14 项 / 验收 12 条逐条对应；48 条 array 的数量与 rc/stride 已由 spec `§3.8` 与 `SPEC-179t` 口径核对；依赖 `LLVM-135t`、`SPEC-179t` 均 `已验证`（`milestones.md` 流水行实测），`INTEG-049t` 仅作缺口登记。结论：**PASS**。
2. **验证手段前置实际可用（主仓 `38d616f0` 实测，日志 `.work/log/llvm/LLVM-141t-precheck-*.log`）**：`make check` 首次 rc=2 仅因**外部并行任务** `TESTCASES-085t` 的任务书瞬时进入索引、其 `.work/evidence/TESTCASES-085t/*` 尚未落盘（4 条悬空）；并行方改为未跟踪后 `make -k check` rc=0（83/83 PASS，含 `check-knowledge-refs` 0 悬空）；`make check-lit` rc=0（159/159，2.1 s）；`check-cfx-aliases`/`check-cfx-alias-table`/`check-cfx-vectors` rc=0；`check_cfx_alias_install.py` rc=0（6 checks）；`check_lit_gen.py` rc=0（62/62）；`.work/source/llvm-project` = base+1 且干净（HEAD `5632c0c5c`）、`.work/build/llvm` 与 `.dadao/cross-toolchain` 在场、`llvm-lit` 可执行；`.dadao/gate.lock` 空闲（`flock -n` 成功）。结论：**PASS**（注：主仓当时有外部并行任务在改 `milestones.md`，本任务在独立 worktree 提交，见风险 4）。
3. **验收逐条可跑性**：验收 1–12 **现在可跑**；唯一时间不确定项是 `make install-host` 增量重建（**估算 5–20 min**，须在任务内记录实测），不构成 BLOCKED。**不跑夜跑**（用户明示）。结论：**PASS（无 BLOCKED）**。
4. **与 `contracts/`、`tests/inst/` 一致**：`.tao/contracts/contract-cfx-aliases.md` 已含 cg7 `4i+K` 模板与 `1430` 统计；`validate_cfx_vectors.py::parse_rc` 已支持 `4i+K`；`tests/inst/**` 与 `tests/**` 无 `space_*` 别名引用（grep 0 命中）；当前唯一不一致正是本任务要修的：`contracts/cfx-aliases.txt`（format=1）无法表达 stride。结论：**PASS**。
5. **拟改文件 × `spec/` 清单**：命中 **0**（14 项全在 `spec/` 之外；用户明示「不改 spec 语义」）⇒ 不构成 BLOCKED。**ADR 提醒（未决）**：`ADR-0017 D10` 写的数组公式是 `rc = rc_base + N`（stride 1），本任务的 `rc = rcBase + N*stride` 是对它的扩展；本任务不改 ADR、不静默改写，若需固化请主会话先与用户**逐条确认**后另立 ADR（或在 D10 就地修订）。

## 风险与已知缺口

1. **重建成本与 build-id 连带**：改 `DADAOCfxAliasTable.{h,cpp}` + `DADAOAsmParser.cpp` ⇒ `make install-host` 必重建；clang build-id 变 ⇒ `check-musl-freshness` 需 `make build-musl-shared` 回绿（LLVM-135t 同款）。预计 5–20 min，超 10 min 走 `setsid nohup` + `EXIT` 标记。
2. **混合态**：旧二进制读新表 ⇒ 整表拒绝（名字汇编报错、反汇编裸回退）；新二进制读旧表 ⇒ 正常（format=1 兼容），但 cg7 名字仍不可汇编。安装门控（源/构建树/安装根 sha256 一致）用于卡住中间态；发布态必须三者同版本。
3. **格式解析放宽的风险**：`array` 仅在 format=2 允许、整表 fail-closed；format=1 旧表名字含 `[`/`]`，**禁止**加「名字不得含方括号」的校验，否则旧表兼容被破坏。
4. **外部并行**：主仓当时有 `TESTCASES-085t` 在改 `milestones.md`/任务书；本任务在独立 worktree（`/tmp/opencode/LLVM-141t/repo`，分支 `LLVM-141t`）规划与提交，执行阶段须在自己的分支/工作树内进行，避免把外部改动卷入。若 L1 因外部瞬时状态红，保留现场并重跑，不改外部文件。
5. **ADR/文档**：`ADR-0017 D10` 的 stride 扩展未固化（见预检 5）；`docs/DDLN` 等讲义若仍写旧 cg7/旧表格式，属文档漂移，不在本任务范围。
6. **`gen_cfx_aliases.py` 的 md 统计文案**（「12 cfxname × 56 模板」）与 1430 的展开口径表述不够直观，但数值正确且门控 byte-identical；本任务不动它，避免无关 diff。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
