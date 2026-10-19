# LLVM-109t: 汇编注释符 `;`→`@@`（实现与迁移：`CommentString = "@@"` + `SeparatorString = ";"`）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`SPEC-147t`（规范面已冻结：`@@` 注释、`;` 语句分隔符；`spec/Toolchain-01` 0.5.3）、`.tao/contracts/contract-asm.md §2.2`（0.5.3）、`docs/Process-01`（组件补丁树）、`docs/Process-05`（TDD/可达 FAIL）、`ADR-0013 D9.1`（被用户 2026-10-19 裁定**部分取代**；ADR 处置待用户确认，本册不改 ADR）
**状态**：待验收

## 执行环境
**执行环境**：本地

## 用户授权（原话逐字，渠道 = 经主会话问答，2026-10-19）
> 「**很好，就改成 `@@` 了**」

`SPEC-147t` 已把规范改为「`@@` = 注释、`;` = 语句分隔符」；本册只做**实现 + 语料/工具迁移**，**不改 `spec/`**（`docs/Process-06` 授权只覆盖 `SPEC-147t` 的既有改动）。

## 问题根源

1. **当前实现**：`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch` 第 46 行 `CommentString = ";"`；`SeparatorString` 沿用 `MCAsmInfo` 默认 `";"`（`.work/source/llvm-project/llvm/include/llvm/MC/MCAsmInfo.h:133`）。`AsmLexer::LexToken` **先**判注释、**后**判语句分隔符（`AsmLexer.cpp:836-857`）⇒ 当前 `;` 永远被当注释，**一行多条语句不可达**。
2. **目标**：`CommentString = "@@"`、`SeparatorString = ";"`。单字符 `@` 不可用：clang 产出 `.type add,@function`、`.section ".note.GNU-stack","",@progbits`，单字符注释会误吞。
3. **LLVM 通用 MC 的 `@` 特例（关键坑）**：源码用 `CommentString.starts_with("@")` 判「ARM 式单 `@` 注释」，对 `@@` 也成立：
   - `llvm/lib/MC/MCParser/ELFAsmParser.cpp:721`：`if (!AllowAt && !getCommentString().starts_with("@")) setAllowAtInIdentifier(true);` ⇒ `@@` 下**不启用** `@` 标识符，`.type add,@function` 在 `:739-742` 报 `expected ...` **FAIL**。这是**功能必修点**，改成 `!= "@"`（仅单字符 `@` 触发 ARM 特例）。
   - `AsmLexer.cpp:113`（`AllowAtInIdentifier = !starts_with("@") && useAtForSpecifier()`）与 `ELFAsmParser.cpp:400`（错误文案分支）语义上是同一特例；DADAO `useAtForSpecifier()` 为 false、`:400` 只影响文案 ⇒ **最小改 `:721` 即可**，另两处**仅在探针证明需要时**改并记录理由。
   - `AsmParser.cpp:1651` 已是 `== "@"`，无需改。
4. **语料现状（现场实测，2026-10-19）**：`tests/**/*.s` 共 **99** 个文件、**3440** 行行首为 `;`、`;` 总出现 **3580** 次；`tests/llvm/lit/MC/DADAO/*.s` 的 **87** 条 `CHECK` 全为 `;` 前缀；`tests/llvm/lit/MC/DADAO-gen/*.s` 12 个文件由 `tools/testcases/generate_lit_vectors.py` 生成（**禁手改**）。
5. **直接翻 `CommentString` 的后果**：旧 `;` 注释行变成「空语句 + 若干标识符」⇒ 通常报 `unrecognized instruction mnemonic`，但若注释文本碰巧像指令则**可能静默编错**。因此迁移必须**先改语料、再翻常量**（同一提交内），让中间态**响亮失败**而不是静默错。

## 接口规范

### A. MC 配置（`DADAOMCAsmInfo.cpp`）

```cpp
// DADAO uses "@@" as the comment string and ";" as the statement separator.
CommentString = "@@";
SeparatorString = ";";   // 显式写出（默认已是 ";"；同时作为规范锚点）
```

- `AllowAdditionalComments = false` 不变。
- 变更须在 `.work/source/llvm-project` 改源码 → 按 `docs/Process-01` 用 `tools/infra/make_patch.py` 重新导出补丁；**禁**手工编辑 `.patch`。

### B. 迁移顺序（硬约束，同一提交）

1. **先**迁移语料与工具（`tests/**/*.s`、生成器、解析器）；
2. **再**改 `CommentString`；
3. **同一提交**内完成，**不得**分两次提交。中间态**不可运行**（先翻常量 ⇒ 旧注释当语句；先改语料 ⇒ `@@` 尚未成为注释），故 1/2 之间**不得**跑门控下结论。

### C. 语料迁移规则

- 逐文件：每行**第一个** `;`（**字符串字面量之外**）是注释引导符 ⇒ 改 `@@`；注释文本内后续 `;` **保留**（如 `0x11; the ...`）。
- 行首 `;`（含 `; RUN:`/`; CHECK:`/`; OBJ:`/`; ASM:`/`; @src`）⇒ `@@ ...`。
- `tests/llvm/lit/MC/DADAO-gen/*.s`：改 `tools/testcases/generate_lit_vectors.py` 的模板后**重生成**（`python3 tools/testcases/generate_lit_vectors.py`），**禁**手改生成物。
- **不动** `.ll`（LLVM IR 注释 `;` 与汇编无关）、不动 `.c/.h` 的 C 分号、不动 `tests/**` 外的上游源码。
- `.asciz/.string` 内的 `;` 若存在，**不得**改；迁移后须用 `grep` 复核无字符串被误改。

### D. 工具同步（现场 grep 命中，逐文件）

- `tools/testcases/generate_lit_vectors.py`：`; RUN:`/`; @src`/`; OBJ:`/`; ASM:`/`; UNREC:`/banner 模板 → `@@`。
- `tools/testcases/check_lit_gen.py`：`; @src` / `; OBJ:` 正则与 docstring。
- `tools/testcases/validate_mc_vectors.py`：`; OBJ:` / `; @src` 解析。
- `tools/llvm/check_lit_bytes.py`：`OBJ_RE` / `OBJ_LITERAL_RE`（`;` → `@@`）。
- `tools/llvm/test_encoding_oracle.py:447`：`' ; OBJ:'` 判定。
- `tools/integ/check_interface_alignment.py`：注释/调用面（按实际 grep 结果改）。
- `tools/llvm/gen_isa_coverage.py`：若解析 `;` 前缀则同步（现场核查；无命中则不改）。
- 验收：`grep -rn '; OBJ:\|; RUN:\|; CHECK\|; @src' tools/ tests/ --include='*.py' --include='*.s'` 应为 **0**（历史 changelog/`.tao/archive` 除外）。

### E. 组件补丁与台账

- 更新 `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch`（`CommentString`/`SeparatorString` 两行 + 注释）。
- 若 `:721` 通用修复必要：新增 `components/llvm-project/patches/llvm/lib/MC/MCParser/ELFAsmParser.cpp.patch`（一文件一补丁），加入 `series`（81 → 82，路径字典序），`check-patch-tree` 现场派生计数并记录。
- `components/llvm-project/changelog.md` 追加 `## M8` 条目（按任务一条，列表式）。

## 验收标准

1. **MC 配置**：`DADAOMCAsmInfo.cpp` 终态含 `CommentString = "@@"` 与**显式** `SeparatorString = ";"`；补丁树经 `make check-patch-tree` / `make check-source-state` rc=0。
2. **printer**：`clang --target=dadao-unknown-elf -S` 产物注释符为 `@@`（如 `@@ -- Begin function`、`@@ %bb.0:`），**无** `;` 注释。
3. **一行多条（端到端）**：
   ```bash
   printf 'add.si rb1, -8 ; add.uo {rd0, rd8}, rd17, rd16 ; ret rd0, 0\n' \
     | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /tmp/opencode/LLVM-109t/multi.o
   llvm-objdump -d --triple=dadao-unknown-elf /tmp/opencode/LLVM-109t/multi.o
   ```
   ⇒ 反汇编**恰 3 条**且顺序/字节正确；`-filetype=asm` 往返输出 3 行（可规范化分行）。
4. **`.type` / `@progbits` 不被误吞**：
   ```asm
   .text
   .globl add
   .type add,@function
   add:
     add.si rb1, -8
     ret rd0, 0
   .size add, .-add
   .section ".note.GNU-stack","",@progbits
   ```
   ⇒ `llvm-mc` rc=0；`llvm-readelf -s` 中 `add` 类型为 `FUNC`。修 `ELFAsmParser.cpp:721` 前应 FAIL（**可达 FAIL 证据**）。
5. **语料零残留**：`grep -rn -E '^[[:space:]]*;' tests/ --include='*.s'` = **0**；`grep -rn '; OBJ:\|; RUN:\|; CHECK\|; @src' tests/ --include='*.s'` = 0；迁移后 `lit` MC/DADAO **全部 PASS**、`check-lit-full`（DADAO-gen）PASS。
6. **工具/编码门控**：`check_lit_gen.py`、`check_lit_bytes.py`、`validate_mc_vectors.py`、`check-interface`（含 `check_interface_alignment`）rc=0；`make check`（L1）rc=0。
7. **安装根复验**：`make install-host` 后（`JOBS=8`、不并发、`ISS-210`；**先申报预计耗时**）用**安装根** `clang`/`llvm-mc` 重跑第 2–5 项（不得只凭 `.work/build` 树下结论）；L2 `make check-modules`、L3 `make check-full` 由主会话执行并如实记录。
8. **可达 FAIL（两处，均须注入→红→还原→绿）**：
   - ① 在临时副本 `.s` 加一行 `; note` ⇒ 汇编必须 FAIL（`;` 已是分隔符，`note` 非法）；还原用 `cp` + md5 对账。
   - ② 把 `CommentString` 临时改回 `";"` ⇒ 一行三条语句用例应只反汇编 1 条（后两条被吞）⇒ FAIL；还原回绿。
   - ③ 撤销 `:721` 修复 ⇒ `.type add,@function` 必须 FAIL；恢复后 PASS。
9. **证据**：`.work/evidence/<任务ID>/run.sh`（default + `--inject`）rc=0；日志落 `.work/log/llvm/LLVM-109t-*.log`；完成区贴真实输出/退出码。

## 不做项（显式）

- 不改 `.ll`、不改 C/C++ 源码注释。
- 不改上游 `spec/` 只读册（其 `;` 示例由上游另行生成新版）。
- 不把 `;` 重新定义为注释；不引入第三种注释符。
- 不改 ADR-0013 正文（处置待用户确认）。
- 不 `push`（提交后由主会话收尾）。

## 完成区

**测试结果**：证据脚本 default **31/31 PASS rc=0**；`--inject` **47/47 PASS rc=0**（I1/I2/I3 三注入均 RED→md5 还原→GREEN，I4 最终重链）。lit MC `DADAO` **68/68**、`DADAO-gen` **12/12**；`check_lit_gen` 64 checks、`check_lit_bytes` 185 patterns、`validate_mc_vectors` 78 向量/0 错、`validate_m5` 141、`validate_m6` 102、`validate_cfx` 14、`test_encoding_oracle` 125/125，均 rc=0。`make check`（L1）**rc=0**（首次 rc=2 因并发 libc-test 运行期空目录撞 `check-run-artifacts`，该目录随后被写满；重试 1 次 rc=0）。
**修改文件**：
- 源码（`.work/source/llvm-project`，已 E1 收敛为 base+1 单 commit）：`llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp`（`CommentString="@@";` + 显式 `SeparatorString=";"`）、`llvm/lib/MC/MCParser/ELFAsmParser.cpp`（`:721` `starts_with("@")`→`!= "@"`）
- 组件：`components/llvm-project/patches/.../DADAOMCAsmInfo.cpp.patch`（重导出）、**新增** `.../llvm/lib/MC/MCParser/ELFAsmParser.cpp.patch`、`components/llvm-project/series`（81→82）、`components/llvm-project/changelog.md`（M8 追加一条）
- 语料：`tests/**/*.s|*.S` **101 文件 / 3684 行**（e2e 187、m5 267、lit MC/DADAO 2261、DADAO-gen 823、scripts 146）；`tests/llvm/lit/MC/DADAO/validate_cfx_vectors.py`（解析器+docstring）
- 工具：`tools/testcases/{generate_lit_vectors,check_lit_gen,validate_mc_vectors,validate_m5_vectors,validate_m6_vectors}.py`、`tools/llvm/{check_lit_bytes,test_encoding_oracle,gen_isa_coverage,check_ret_canonical}.py`、`tools/integ/check_interface_alignment.py`
- 证据：`.work/evidence/LLVM-109t/{run.sh,check_corpus.py}`；日志 `.work/log/llvm/LLVM-109t-evidence-*.log`
**验收结果**：
- `clang -S` 产物注释为 `@@`（`@@ -- Begin function add`、` @@ %bb.0:`），无 `;` 注释行。
- 一行三条 `add.si rb1, -8 ; add.uo {rd0, rd8}, rd17, rd16 ; ret rd0, 0` ⇒ `llvm-mc` rc=0；`-filetype=asm` 回 3 行；`llvm-objdump -d` **恰 3 条**，字节 `5b07fff8 50008450 76000000`。
- `.type add,@function` ⇒ `llvm-readobj --symbols`：`Name: add / Type: Function (0x2)`。（注入撤销 `:721` 修复 ⇒ rc=1，可达 FAIL 已证。）
- `; note` ⇒ rc=1 `error: unrecognized instruction mnemonic`（不再静默吞）；`@@ note` ⇒ rc=0。
- 残留：`grep -rn -E '^[[:space:]]*;' tests/ --include='*.s'` = **0**；`.S` = 0；`; OBJ:`/`; RUN:`/`; CHECK`/`; @src` 于 `tools/`+`tests/` = 0；`.ll`/C/`.h`/`.yaml` 未动（`.yaml` 现场逐条判定：无汇编字符串命中）。
- 门控 rc：`check-asm-prose`/`check-asm-list`/`check-asm-list-drift`/`check-instrinfo`/`check-index-blobs`(131 new-file patch OK)/`check-source-state`(llvm-project clean, count=1)/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog` 全 **0**；`check-patch-tree` **181 patches OK rc=0**（180→181）。
**新发现/坑**：
1. `tests/**/*.S`（大写，bootrom 两册）同样由 `llvm-mc` 汇编，任务书按 `*.s` 统计会漏（现场统计 `.s` 99 文件/3440 前导注释行；`.s+.S` 101 文件/3684 总行）。`grep --include='*.s'` 大小写敏感。
2. 迁移不能只改行首：**行尾 `;` 注释**（m5/m4 约 244 行）若保留，翻 `CommentString` 后会被当语句分隔符而报错。
3. `check_ret_canonical.py` 内嵌汇编探针（`CONSUMER`）不在任务书 §D 清单，但不改则安装根/构建树跑该探针必失败；已同步。
4. `validate_cfx_vectors.py` 位于 `tests/llvm/lit/MC/DADAO/`（任务书 §D 未列），是 L1 cfx 向量的独立 oracle，必须同步。
5. `validate_m6_vectors.py` 同一文件内**两种语境**：L1 段解析 `.s`（改 `@@`）、IR 段解析 `.ll`（保持 `;`）——不可整文件替换。
6. `FileCheck` 前缀在行内任意位置命中，`; CHECK:`→`@@ CHECK:` 不需改 lit 配置；但注释**文本内**的 `;`（如 `wpn_err_wp4.s` 的 `invalid wyde-position; expected ...`）保留，仍能匹配诊断原文。
7. `make check` 的 `check-run-artifacts` 会与**并发**进行的测试运行竞态（空目录窗口内判 FAIL）；重试即恢复，非本笔引入。
**遗留问题**：
- `install-host` 未跑（按派单归主会话）；**安装根仍为旧 `;` 行为** ⇒ 在其完成前，任何用安装根工具跑 `tests/**/*.s` 的门控（`check-lit`/`check-lit-full`/e2e lit/`run_elf_e2e` 等）都会红。
- **install-host 后须复验**：① `make check-lit`（MC 68 + CodeGen + e2e）；② `check-lit-full`（DADAO-gen 12）；③ `tests/scripts/bootrom*.S` 与 `codegen_crt0.s` 的 QEMU E2E；④ `tools/llvm/check_ret_canonical.py`（内嵌汇编探针）在安装根 clang 下 default 全绿；⑤ L2 `check-modules`、L3 `check-full`。
- 未 `commit`/`push`（提交归 architect）；未改 `**状态**`（按派单）。

### 迁移漏项修复（`ISS-281`，2026-10-19，engineer）

**触发**：`LLVM-109t` 的迁移面未覆盖组件补丁里的 DADAO 手写汇编 ⇒ 新 `CommentString="@@"` 下旧 `;` 注释被当语句分隔符，`make build-musl` 报 `unrecognized instruction mnemonic`，`.work/source/musl/lib/{libc.a,crt1.o}` 缺失（现场 `/tmp/opencode/rebuild-m.log:66+`）。
**命中（改前，逐文件）**：musl `src/signal/dadao/sigsetjmp.s` **49** 行、`src/thread/dadao/syscall_cp.s` **86** 行、`src/thread/dadao/__set_thread_area.s` **25** 行（均行首 `;`）；picolibc `libos/semihost/machine/dadao/semihost-dadao.S` **3** 行（行尾注释）。判定依据：仅汇编语境；`src/setjmp/dadao/{setjmp,longjmp}.S` 与 picolibc `libc/machine/dadao/setjmp.S` 的 `;` 全在 C 块注释内，未改；C/伪代码/IR 未动。
**改法与补丁重导出**：改 `.work/source/{musl,picolibc}` → E1 收敛（`commit --amend`，HEAD=base+1、`clean=True`）→ `tools/infra/make_patch.py`：musl **3 written / 19 skipped**（`src/signal/dadao/sigsetjmp.s.patch`、`src/thread/dadao/{__set_thread_area,syscall_cp}.s.patch`），picolibc **1 written / 13 skipped**（`libos/semihost/machine/dadao/semihost-dadao.S.patch`）；`series` **22/14 不变**。
**重建真值**：`make build-musl JOBS=8` **rc=0**（11.0 s，10/10 ELF 检查）；`make build-musl-shared JOBS=8` **rc=0**（12.9 s）；`libc.a` **2735226 B** / `crt1.o` **1512 B** / `libc.so` **1112200 B** 均在；`check-musl-freshness` **PASS**（source stamp `d7641575…`、installed==build sha256 `1e2b0438…`）。
**回归**：`047t` 10 例小样本 **静态 10/10、动态 10/10**（`--json-out /tmp/opencode/FIX-AT-MUSL/...`）；`046t` 静态 `-O0` **19/19**。
**门控**：`check-patch-tree` **181 patches OK**（无新增补丁，计数与 `components/*/series` 总行数一致）、`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-component-changelog`/`make check`(L1) 均 **rc=0**。
**证据**：`.work/evidence/LLVM-109t-fixasm/run.sh` default **31/31 PASS rc=0**、`--inject` **39/39 PASS rc=0**（I1 注入 `;` ⇒ 汇编 rc=1，`cp`+md5 还原回绿；I2 补丁注入 `+;` ⇒ 检查转红，还原后回绿）。
**边界**：未 `install-host`/`build-qemu`/L2/L3；未 `commit`/`push`；未改 `tests/**` 与 `tools/testcases/run_llvm_ts_user.py`（后两者为他人改动）。
**补充（architect 提交前清理 stale）**：`arch/dadao/crt_arch.h` C 注释里的过期说明「`;` starts a comment」改为「`@@` starts a comment」（**仅注释文本，代码零改动**）；E1 收敛后 `make_patch.py musl` **1 written / 21 unchanged**，`crt_arch.h.patch` 同步（`series` 22 不变）。自审表该行「⏸延后」由本条取代。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-19）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 迁移脚本 `--check` 把已迁移行注释文本里的第二个 `;` 误判为“未迁移”（首轮 `--check` 报 187 行，实际仅注释文本） | ✅已修 | 扫描遇到 `@@` 即终止（其后为注释文本） | 重新 `--check` = `changed_lines=0` |
| 工具 grep 清单漏 `tests/.../validate_cfx_vectors.py`、`validate_m6_vectors.py` L1 段、`gen_isa_coverage.py:636`、`check_ret_canonical.py` 内嵌汇编 | ✅已修 | 逐文件改 `@@` 解析；`m6` 仅 L1 段（450/454 行 IR 段保持 `;`） | 各 oracle rc=0；`validate_cfx` 14 向量 0 错 |
| `check_ret_canonical.py` 一次性 `replace(';','@@')` 把注释文本第二个 `;` 也改成 `@@` | ✅已修 | 按行只改第一个 `;`，其余还原 | `grep -n '@@'` 仅 8 行注释引导符 |
| 证据脚本 C02b/C02d 用 `grep|wc -l` 后取 `$?`（恒 0 ⇒ 恒真） | ✅已修 | 先取计数再用 `[ n -eq 0 ]` 生成 rc | 脚本内 31/31 PASS；计数改动可达 FAIL（脚本逻辑） |
| 证据脚本引用 `/tmp/.../migrate_comments.py`（非自包含） | ✅已修 | 删除该行，语料自检用仓内 `check_corpus.py` | default 运行无 `/tmp` 依赖 |
| 语料行尾 `;` 注释（不止行首）可能漏迁移 | ✅已修 | 迁移按“行内第一个串外 `;`”统一处理 | `check_corpus.py`：`@@`=3684、代码位 `;`=0 |
| `m6-callconv.s` 注释内文档示例仍写 `; @enc`/`; @reloc`（旧语法示例） | ✅已修 | 改为 `@enc`/`@reloc` | 该文件 lit 1/1 PASS；`validate_m6` 102 checks PASS |
| `make check` 首次 rc=2（`check-run-artifacts` 报空目录）是否为回归 | ❌不修（非本笔） | 无（并发测试运行窗口） | 目录 08:12 创建、约 6 分钟后写满；重跑 `make check` rc=0、`[FAIL]` 计数 0 |


#### 提交（architect，2026-10-19）
- 档位：**WIP**（reviewer 尚未验收，状态 `待验收`）；分支 `LLVM-109t` → `master`（`merge --squash`），**未 push**。
- 文件集对账：staged **119** 项 = 本册声明（组件 5 / 语料 101 `.s|*.S` + 1 `.py` / 工具 10 / 本册 + `milestones` + `INTEG-036m`）；**不含** `tools/testcases/run_llvm_ts_user.py`（属 `TESTCASES-051t`，保持未暂存）。
- 门控：`make check` 因 `check-musl-freshness` FAIL（工具链戳 01:22 ≠ 08:18 安装根 clang，须 `build-musl-shared`）未全绿；其余 14 项单独 rc=0、`check-patch-tree` **181**。

### 迁移漏项修复：第 1 轮 engineer 自审（2026-10-19）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 迁移脚本按「行首 `;` / 首个串外 `;`」可能误改 `.S` 的 C 块注释 | ✅已修 | 脚本维护 `/* */` 状态，块注释内一行不动 | 结构化比对 4 文件 = 68/323/34/41 行、代码行差异 **0**；`.S` 未改 |
| 注释正文仍写「DADAO 用 `;` 注释」（sigsetjmp/syscall_cp/__set_thread_area 各 1 处） | ✅已修 | 注释正文 `;` → `@@`（引导符同批改） | 三文件重汇编 rc=0 |
| `crt_arch.h`（C 注释）仍写「`;` starts a comment」 | ⏸延后 | 未改（派单要求 C 代码/注释面不动） | 记为已知 stale 文档，非执行面 |
| 证据脚本 B1–B4 写死 49/86/25/3 | ✅已修 | 改为现场派生「源码 `@@` 行数 == 补丁 `+@@` 行数」，并要求 >0 | default 31/31 PASS |
| 证据脚本 B4 `grep '@@'` 误命中补丁 hunk 头 `@@ -0,0` | ✅已修 | 限定 `^+.*@@` | B4 src=3 patch=3 |
| 注入还原是否可能残留 | ✅已证 | `cp -p` 备份 + md5 对账，未用 `git checkout/restore/stash` | I1c/I2b md5 相同；I2d 源树干净 |

判决：无未修 finding；证据 default 31/31 rc=0、`--inject` 39/39 rc=0。
