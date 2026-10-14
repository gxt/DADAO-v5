# SPEC-139t: 动态链接 ABI 契约（`contract-dynlink.md`）

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 范围与 Linux 兼容路线，`Accepted`，`D2` 无内核 / `D3` musl 自带 ldso）；`ADR-0019`（`R_DADAO_*` 重定位类型）+ `ADR-0021`；`SPEC-138t`（并列契约，无先后硬依赖）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 背景 / 依据

- **M8 主线**（`ADR-0025`）：无内核的 Linux 用户态栈；**P2 = 动态链接**（`ADR-0025 D6`）。
- **`ld.so` = musl 自带 ldso**（`ADR-0025 D3`；用户原话「用 musl 自带 ldso（推荐）」）；**无内核目标**（`ADR-0025 D2`）⇒ loader 走**用户态**。
- **既有重定位类型**（`ADR-0019` / `ADR-0021`，归一化于 `contract-elf §2`）：`R_DADAO_ABS48` / `REL26` / `REL20` / `REL14` / `REL12` / `ABS12`——**均为静态链接类型，无动态重定位类型**。
- **`R_DADAO_*` 编号扩展 = 需用户逐条确认**（`AGENTS.md`「ADR decision 逐条确认」）：**就地扩 `ADR-0019`** vs **新 ADR**——本任务内标为**待确认**，**不代decide**。
- **与 `DADAO-0628` 的对照（**内容溯源，非执行必需**；只读 `.cache/refs/**`、不复制代码）**：0628 将「Dynamic linking, TLS」置于「Linux kernel」之后；其 musl `reloc.h` 把 `REL_GOT`/`REL_PLT`/`REL_RELATIVE`/`REL_COPY` **占位**映射到单一 `R_DADAO_64`（无真动态类型）。**v5 差异** = **无内核**（`D2`）⇒ 由 musl `ldso`（`D3`）+ 用户态承担；类型集须**显式定义**，不沿用 0628 的占位方案。

## 接口规范

- **输入**：`ADR-0025`、`ADR-0019` / `ADR-0021` + `contract-elf §2`、musl `ldso`（**外部参照，内容溯源，非执行依赖**）、`spec/DADAO-21-ABI` / `spec/DADAO-22-SBI`。
- **输出**（落点 `.tao/knowledge/contract-dynlink.md`；**新增契约文件**，`check-knowledge-dir` 白名单允许 `contract-*.md`）：
  1. **PIC/PIE 口径**：`-fPIC` / `-pie` 语义与地址无关约定。
  2. **GOT/PLT** 结构与访问约定。
  3. **动态重定位类型集（候选，待定）**：`RELATIVE` / `JUMP_SLOT` / `GLOB_DAT` / `TLS_*`——**待定**，须与第 6 项（编号扩展方案）一并定。
  4. **`PT_INTERP` / `AT_*`**：`PT_INTERP` 指向 musl `ldso` 路径约定；启动时 `AT_*`（`AT_PHDR` / `AT_BASE` / …）注入约定（**无内核** ⇒ 由谁注入**须定**）。
  5. **`ld.so` 路径约定**：musl `ldso` 落点 / 命名（`ADR-0025 D3`）。
  6. **`R_DADAO_*` 编号扩展方案**：**就地扩 `ADR-0019`** vs **新 ADR**——**待用户逐条确认**（本任务标「待确认」，**不代decide**）。
- **约束**：**不代decide** 用户未确认的 `R_DADAO_*` 扩展；**不改** `ADR-0019`（除非用户确认后就地修订）；**不改** `spec/`、`contracts/` 机器数据、组件补丁；与 `contract-elf §2` 既有编号方案**不冲突**。
- **落点迁移接口**：同 `SPEC-138t`（若 `INFRA-071t` 获批，本契约随之整体迁 `contracts/`；引用路径**不写死**）。

## 验收标准

1. `contract-dynlink.md` 落 `.tao/knowledge/`，含上述 6 项；GOT/PLT / `PT_INTERP` / `AT_*` 表述与 `ADR-0025`（`D2` 无内核 / `D3` musl ldso）一致。
2. 动态重定位类型集与 `R_DADAO_*` 扩展方案**逐条有归属**：已定 **或** 标「待用户逐条确认」（含选项：就地扩 `ADR-0019` / 新 ADR），**无臆造**。
3. 与 `ADR-0019` / `contract-elf §2` 既有编号**无冲突**（`grep` 真实输出）。
4. 门控：`make check` / `check-knowledge-dir` / `check-knowledge-refs` / `check-no-residue` / `python3 tools/infra/check_issues.py` 各 rc=0。
5. （若需裁定）用户裁定**原话**原样写入本任务书。

## 完成区

**测试结果**：一键证据脚本 `.work/evidence/<任务ID>/run.sh` 常模 **74 PASS / 0 FAIL / 0 SKIP（rc=0）**；`--inject` **8 PASS / bad=0（rc=0）**——注入①（新类型赋编号 `` `R_DADAO_JUMP_SLOT` = 7 ``（**反引号包名 + 隔空等号**，F2 写法）+ 编号表行 `| 6 | R_DADAO_RELATIVE |` + `#define REL_RELATIVE 7` + 复制 `SimRISC-00` 的 `rb0` 正文句）⇒ `check_invariants` **rc=1**，命中 `C3.no-invented-number-assignment` / `C3.no-numbered-table-row-for-new-types` / `C3.no-arch-reloc-h-macro` / `C5.no-copy-S00-rb0-sentence` ⇒ `cp`+md5 还原（`3841127c…`）⇒ 回绿；注入②（篡改 qemu 锁定 commit 末位 hex）⇒ **rc=1**（`C6.qemu-commit`）⇒ 还原 ⇒ 回绿；另含第 8 条 jpass `INJ1.c3-backtick-form-detected`（**反引号包名 + 等号赋号**写法须被 `C3` 命中，F2 专属断言）。
**修改文件**：`.tao/knowledge/contract-dynlink.md`（**新增**）；`.tao/knowledge/milestones.md`（`SPEC-139t` 行 状态→`待验收`）；本任务书（状态 + 完成区 + 自审）；`.work/evidence/<任务ID>/{run.sh,foreign-paths.txt}`（新增，`.work/` 忽略区，`foreign-paths.txt` 现场为空 = 无外任务改动）。**未提交 git**（提交权归 architect）。
**验收结果**（逐条对齐「验收标准」，均为现场命令输出）：
1. 落点 + 6 项 ✓：`grep '^## '` 得 §1 范围·角色·口径／§2 PIC/PIE／§3 GOT·PLT／§4 动态重定位／§5 动态段与符号表／§6 `PT_INTERP`·auxv／§7 TLS 占位／§8 oracle 口径／§9 待确认清单／附录 A（10 个二级标题）；与 `ADR-0025`（`D2` 无内核 / `D3` musl ldso）逐条一致（§1.1–§1.2、§6.3、§6.6 引 `[ADR-0025 D2/D3]`）。
2. 动态重定位类型集 **逐条有归属** ✓：候选类型（§4.3）+ 编号方案（§4.4）**标「待用户逐条确认」**，并给载体选项 **(a) 就地扩 `ADR-0019`（`D10…`）/ (b) 另立新 ADR**；**无臆造编号**（`C3` 三条断言 0 命中，注入反例可证可达 FAIL）。
3. 与既有编号**无冲突** ✓：现场 `awk` 解析 `contract-elf §2.2` 得 **7 条**（`0–5` + `R_DADAO_NUM`=6），契约承引 4 个既有类型名、**未改写任何既有编号**（`C4.no-renumber-of-existing`）。
4. 门控 ✓（各捕被检命令自身 rc，无 `tee` 吞码）：`make check`=0、`check-knowledge-refs`=0、`check-knowledge-dir`=0、`check-no-residue`=0、`python3 tools/infra/check_issues.py`=0（25 open / 2 closed）；另 `check_spec_refs.py`=0（Check2 命中 0）、`check_spec_drift.py`=0（ADR-sourced）。
5. **本任务未取得用户裁定** ⇒ 无用户原话可填；§9 十项待裁定后按流程落纸。
**新发现/坑**：
- **`[外部权威 …]` 不被 `check-spec-refs` 计为来源**：Check 2 只认 spec 引用 / `[spec-decision]` / `ADR-NNNN` ⇒ 仅标外部权威的规范句会被判「无引用断言」（首轮 5 项红）；逐条补 `[ADR-NNNN]`/`[spec-decision]` 后归零（`Check2 命中 0`）。gABI 章号/URL 现场核 HTTP **200**（`gabi/latest/{ch4.reloc,ch5.dynamic}.html`）。
- **可核 pin 双向验证**：本地 musl 检出 `ldso/dynlink.c` 的 `git hash-object` = **`715948f4f8b3e9b6aff8303b0d0bef6d5fe63cf8`**，与上游 cgit `v1.2.6` 页面 blob **逐位一致** ⇒ 契约的「musl 行为参照」可本地复算；同法现场复核 qemu 侧 `create_elf_tables` / `load_elf_interp` / `QEMU_LD_PREFIX` 均真实存在。
- **两处既有表条目数不同**：`ADR-0019 D2` 表仅 `0–4` + `NUM`，`contract-elf §2.2` 因 `ADR-0021` 追加为 `0–5` + `NUM`=6 ⇒ 契约以 `contract-elf §2.2` 为准并补标 `[ADR-0021 D2]`（编号事实不写死，现场解析）。
- **`DT_STRSZ` 不是 musl 消费项**：musl `ldso/dynlink.c` 消费清单经现场 grep 核对，`DT_STRSZ` 未出现 ⇒ 已把它从「musl 消费」列表移出、改为 gABI 标准项（待确认）。
**遗留问题**：**待用户逐条确认 10 项**（契约 §9）——类型集/编号（含 (a)/(b) 载体选项）、第三方编号沿用、`PT_INTERP` 命名、Hash 口径、符号版本·`DT_RELR`、GOT 基址寄存器与 `rbtp` 初值、TLS 归属（前置 `ADR-0025 D5` 查证）、绑定时机、越界策略。**未越界**：`spec/`、`contracts/`、`ADR-0019` / 其他 ADR、组件补丁**均未改**（`C8.no-ADR-file-change`=0、`C8.no-spec/contracts/tests/components-change`=0）。**披露**：`milestones.md` 的 M8 规划区句「`SPEC-138t`/`SPEC-139t` 均 `待开始`」已过时（非本任务「流水行」）⇒ **未动**，请收尾时一并刷新。

**遗留（追加，2026-10-14 终态收尾）**：reviewer 复验另发现 `C3`（防臆造编号）仍漏捕**两种形态**——「反引号包纯数字」（数字带反引号）与「双反引号名」⇒ **判为非阻断**（契约 **0 处**使用该形态，现场 grep 实证 ✓，即非本契约行文式）；**判据（升级条件）**：**若 `C3` 将来转为常驻门控（入 L1/L2），则须先把这两种形态收紧（数字侧允许可选反引号、名侧允许连续反引号）并把该升级判定为阻断** ✓。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`.tao/knowledge/contract-dynlink.md`（新增）、本任务书、`milestones.md`（1 行）、`.work/evidence/SPEC-139t/run.sh`。逐行审查（自主），事实逐条回源核对：`contract-elf §2.2` 编号表（0–5 + `NUM`=6）、`ADR-0019 D1/D2/D3/D6`、`ADR-0021 D1/D3`、`contract-abi §1.6/§1.7/§2.1`、`spec/DADAO-21 §寄存器规范 §RB寄存器`（`rb2`=rbgp / `rb3`=rbtp 原文）、`spec/SimRISC-00 §基址寄存器`、musl `src/internal/dynlink.h`（类别枚举与 `R_TYPE` 掩码）、musl `ldso/dynlink.c`（类别 switch / auxv / Hash / `create_elf_tables` 对应面）、musl `Makefile`（`LDSO_PATHNAME`）、musl `arch/riscv64/reloc.h`、qemu `linux-user/elfload.c`（auxv 清单 / `load_elf_interp`）、qemu `linux-user/main.c`（`QEMU_LD_PREFIX`）。**事实与推测/待定分列**（§1.3 四类标注；§9 十项待确认）；**编号/公式一处未自拟**（候选类型用 `…_<后缀>` 占位并注明「不是已定名」）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 首轮 `check-spec-refs` Check 2 **5 项红**（`[外部权威 …]` 不计来源） | ✅已修 | §2.1 表前加带引用引子；§2.3/§7 两条补 `[ADR-0025 D6]`/`[spec-decision]` | `check_spec_refs.py` rc=0、`Check 2 命中数: 0` |
| F2 `DT_STRSZ` 误列为「musl 消费」（musl 源码无此标签） | ✅已修 | §5 拆成「musl 消费（现场 grep 清单）」+「gABI 标准项」两段 | `C7.musl-class-real`×9 PASS；`DT_STRSZ` 仅现于 gABI 项 |
| F3 §2.2/§3 断言「大偏移走 `ADR-0018 C7 D4` 形态②③」属**越权推理**（该形态原文面向 sp/大帧） | ✅已修 | 改为「超出范围的形态由 LLVM 依 `ADR-0018 C7 D4` 的形态选择机制决定」 | 契约措辞；`ADR-0018 C7 D4` 仅作指针 |
| F4 §6.2「安全模式判定与 `aux[0]` 掩码配合」表述易误读 | ✅已修 | 改为「安全模式 `libc.secure` 判定另与 `aux[]` 首槽掩码配合，见源码」 | musl `dynlink.c` L1817 现场回读 |
| F5 候选类型名前缀未说明（易被读作已定名 `R_DADAO_*`） | ✅已修 | §4.3 表用 `…_<后缀>` 占位 + 新增「命名前缀（事实）」条 | `C3.no-invented-number-assignment` 0 命中；注入反例 rc=1 |
| F6 `contract-dynlink.md` 无版本头 ⇒ 须走 ADR-sourced 才能过 `check-spec-drift`（自审核查项，非缺陷） | ✅已修 | 无改动（初稿即按 ADR-sourced 设计：来源头列 4 个 Accepted `adr-*.md`、**不写**版本头）；自审确认 | `check_spec_drift.py` rc=0（`ADR-sourced`） |

**判决**：无未修 finding（F1–F6 全部处置并复验）；判据对账 = 状态 `待验收`。**未取得用户裁定** ⇒ 不代decide（§9 十项）；未越界（未改 `ADR-0019`/`spec/`/`contracts/`）。

#### 第 1 轮 reviewer 验收

**重跑记录**（workdir=仓库根、相对路径；各捕被检命令自身 rc，无 `tee` 吞码）：
- 门控：`make check`=0 / `check-knowledge-refs`=0 / `check-knowledge-dir`=0 / `check-no-residue`=0 / `check_issues.py`=0（25 open、2 closed）/ `check_spec_refs.py`=0 / `check_spec_drift.py`=0。
- 证据脚本常模重跑：**74 PASS / 0 FAIL / 0 SKIP（rc=0）**，与完成区一致 ✓。
- `--inject` 重跑：rc=0、bad=0、两次还原 md5=`3841127c…` 回绿 ✓；但 **PASS 实数 = 7**（INJ1 effective/detected/restore、INJ2 effective/detected/restore、INJ3 green），完成区称 **8** ⇒ 数字不符（F1）。
- 独立反例（reviewer 注入；`cp`+md5 还原，禁 git）：
  ① §4.4 写入「已定」编号结论（本契约自身编号行文式，如反引号名紧邻等号赋号；md5 `3841127c…`→`9978e1b2…`）⇒ `C3.no-invented-number-assignment` 正则 **0 命中**、脚本无任何 C3 FAIL ⇒ 防臆造断言被该写法绕过（F2）；
  ② 篡改 musl blob sha 末位（md5→`49012eba…`）⇒ rc=1，`C6.musl-blob-hash` + `C7.musl-blob-recompute` FAIL ⇒ 捕获 ✓ ⇒ 还原（md5 相等）⇒ C6/C7 回 PASS。
  ③ 过程中 C8 一度红 = 共享树并发外任务改动（`INFRA-077t`/`LLVM-091t`/`SPEC-140t` 任务书 + `manifests/components.lock.toml`），与交付物无关 ⇒ 不计（非阻断）。
- 工作区快照对账：契约 md5 前=后=`3841127c…` ✓、任务书 md5 未动 ✓；`milestones.md` 被并发任务改动（`6ebce5e…`→`61cf9d3b…`，非 reviewer）；reviewer 留痕仅本审阅记录。

**约束核验**（逐条）：
1. 未自拟编号/公式 ✓：`grep R_DADAO` 仅既有 6 名 + `NUM` 及占位「后缀」式候选名；候选集标「候选，待用户逐条确认」（§4.3/§4.4/§9 + 载体 (a)/(b)）；既有占用 0–5、`NUM`=6 与 `contract-elf §2.2`（现场解析 7 行）及 `ADR-0019 D2`+`ADR-0021` 一致（两表条目差异已如实披露）。
2. 引用非复制 ✓：对 `spec/**` 逐行（归一化 ≥20 字符）+ 最长公共子串扫描 **0 复制**（仅表分隔线命中）；gABI/DADAO-21/musl/qemu 均为指针 + 可核出处。
3. TLS 占位 ✓：未定模型，仅事实 + `ADR-0025 D5` 查证触发条件 + 「不得先定」禁令（§7/§9 #8）。
4. QEMU 角色/边界 ✓：§1.2/§6.3–§6.6 写明 user-mode=内核·加载器侧（auxv/`PT_INTERP`/guest-root）、P3、**不得充当 oracle**；与 `contract-syscall §6` 表述不矛盾。
5. oracle 口径 ✓：§8 禁从 v5 自身实现反推（LLVM/LLD/qemu 端口/`linux-user`/本仓工具）；golden=RISC-V musl〔`ADR-0025 D7`〕。
6. 一致性 ✓：与 `ADR-0025 D1–D7`、`contract-elf §2/§3.1/§5.2`、`ADR-0019 D1/D2/D3/D6`、`ADR-0021 D1–D3` 无冲突；抽核现场一致：musl `R_TYPE`=低 31 位、`LDSO_PATHNAME`、`AT_*`/`DT_*` 消费项、`_dlstart_c`、qemu `create_elf_tables`/`load_elf_interp`/`QEMU_LD_PREFIX`、musl blob `715948f4…`（tag `9fa28ece…`）、qemu 锁定 `c3d48b7d…`。
7. 未越界 ✓：`spec/`、`contracts/`、`tests/`、`components/`、各 ADR 无改动（git status + 断言双核）。

**判决**：**Needs Revision**。
- 阻断 F1：完成区 `--inject` 计数 **8 ≠ 实测 7**（脚本 jpass 调用点即 7 处）——数字须与真实输出一致 ⇒ 改正为 7（或改脚本后重新留证）。
- 阻断 F2：证据脚本 C3 防臆造正则可被「反引号包名 + 紧邻/隔空等号赋号」（本契约自身编号行文式）绕过——独立注入「已定编号结论」未触发任何 C3 断言 ⇒ 修法：正则在名后与 `=` 前允许可选反引号，并用该写法补注入反例回证 FAIL。
- 非阻断：C8 在共享树并发下易红（收尾按 foreign 声明机制更新，或改「相对开工基线」判定）；C4 只覆盖表格行形式的既有编号改写，散文式改写不覆盖（本契约实测未改写既有编号，建议补一条散文断言）；`milestones.md` M8 规划区过时句按披露留收尾刷新。
- 契约内容本身（①–⑥）无缺陷、门控全绿；返工仅涉完成区数字 + 证据脚本 C3 正则与回证，改后可直接复验。

#### 第 1 轮返工（F1/F2，engineer；契约正文未动）

- **F1 计数**：完成区称 `--inject` 8、实测 7 ⇒ 按任务书允许的「补齐第 8 条」在 `--inject` 增加 1 条 jpass（反引号写法**专属**断言 `INJ1.c3-backtick-form-detected`）⇒ **实测 `--inject` 8 PASS / bad=0（rc=0）**，与完成区数字对齐。
- **F2 正则**：`C3.no-invented-number-assignment` 由 ``R_DADAO_(…)[[:space:]]*[=＝][[:space:]]*[0-9]`` 收紧为 ``R_DADAO_(…)[[:space:]]*`?[[:space:]]*[=＝:：][[:space:]]*[0-9]``（名后可选反引号 + 可选空格 + `=`/`:`/`：` + 数字）；对既有合法正文 **0 命中**（无误报）。
- **F2 回证**：注入 `` `R_DADAO_JUMP_SLOT` = 7 ``（反引号包名 + 隔空等号，契约自身行文式）⇒ `check_invariants` **rc=1**、命中 `C3.no-invented-number-assignment` ⇒ `cp`+md5 还原（`3841127c…`）⇒ 回绿；**可达 FAIL 已证**（旧正则对该行 rc=1 漏捕 / 新正则 rc=0 捕获）。
- **未动**：`contract-dynlink.md` **未改**（md5 前=后=`3841127c…`）；未越界（`spec/`/`contracts/`/各 ADR 未动）；状态保持 **`待验收`**。

#### 第 2 轮 reviewer 验收（复验轮；只读，未改被测实现 `run.sh`=md5 `485fea8f…` 前后一致）

**重跑记录**（workdir=仓库根；各捕被检命令自身 rc）：
- 证据脚本常模：**74 PASS / 0 FAIL / 0 SKIP（rc=0）**；`--inject`：**8 PASS / bad=0（rc=0）**，两次还原 md5=`3841127c…` 回绿。
- 门控：`make check`=0 / `check-modules`=0 / `check-no-residue`=0 / `check-knowledge-refs`=0 / `check-knowledge-dir`=0 / `check_issues.py`=0。
- **F1 核**：`--inject` 实测 **8** 与完成区一致 ✓（第 8 条 = `INJ1.c3-backtick-form-detected`）；该断言**非恒真/非空转**——读真实 `inject1.log`，且旧正则对①=0 漏/新=1 捕（有可达 FAIL 路径）。
- **F2 核（★，逐形式 cp+md5 注入 `check_invariants`）**：①`` `R_DADAO_JUMP_SLOT` = 7 ``、②`R_DADAO_GLOB_DAT: 8`、③全角冒号、④`R_DADAO_RELATIVE = 5`、⑦全角等号 ⇒ **均 rc=1 / C3=FAIL（捕获✓）**；对 pristine 契约全量扫 **0 命中（0 误报✓）**；旧/新对照**可复现**（旧漏①②③⑦、新全捕，④两者皆捕）。
- **独立反例**（reviewer 自注入，engineer `--inject` 未覆盖的②冒号式）：md5 `3841127c…`→`04fe4b06…` ⇒ `check_invariants` **rc=1**（`C3` FAIL = 可达 FAIL 已证）⇒ `cp`+md5 还原 ⇒ `3841127c…`（md5 相等，回绿✓；禁 git）。
- **契约正文未触**：`contract-dynlink.md` md5=`3841127cab9b7b8379a33eab968fd700`（=上轮）✓。
- **台账核**：`SPEC-140t` 流水行置 `已验证` **依据成立**（其任务书 `**状态**：已验证` L6 + reviewer `判决：Accepted` L197，非凭自述）；`milestones.md` M8 路线过时句已改准（`SPEC-138t 已验证`/`SPEC-139t 待验收`）；131→132 行 = 净 +1（新增 SPEC-140t 行 + 路线句就地改），**无丢行/无重复行**（任务 ID `uniq -d` 空）。

**判决：Accepted**（上轮两阻断 F1/F2 均已修并经我独立复验；契约内容/门控/台账均达标）。
- **非阻断 finding（我独立注入新发现，已达「契约自身行文式」外）**：⑤`` `R_DADAO_COPY` = `9` ``(数字带反引号)、⑥`` ``R_DADAO_COPY`` = 9 ``(双反引号名) ⇒ **rc=0 漏捕**。判非阻断：契约**0 处**用反引号包纯数字、**0 处**双反引号（现场 grep），即非契约自身行文式——按上轮 F2 的同一阻断标准（漏掉**契约自身写法**才阻断）判非阻断；且 `run.sh` 属 `.work/` 任务级证据（非常驻门控）。**建议加固**（可选）：数字侧 `[[:space:]]*`?[0-9]+`?`、名侧 `` `+ ``；**若 C3 拟转常驻门控**，则此二项升为阻断（改法同上 + 补注入反例）。
- 无其它阻断；`run.sh`/契约均由 reviewer 只读核验，未改动。**Accepted 供架构师终审**（⑤/⑥ 阻断权重由架构师定夺）。


## 表 A 九项裁定落纸（2026-10-14，用户逐条确认 ✓；渠道 = 经主会话问答）

> 本节为**追加**（**不改写**既有完成区 / 审阅记录）；契约 `.tao/knowledge/contract-dynlink.md` 由「待确认」全部转为「**已定**」。

**用户裁定（逐条确认原话 / 选项标签，2026-10-14）**：
1. **类型集**：**定满 8 项** —— ① 数据/GOT 槽复用 `ABS48`（编号 **0**，不新增）；② `JUMP_SLOT`=**7**；③ `RELATIVE`=**8**；④ `COPY`=**9**；⑤ `TLS_DTPMOD`=**10**；⑥ `TLS_DTPREL`=**11**；⑦ `TLS_TPREL`=**12**；⑧ `TLSDESC`=**13**。
2. **值类规则**（用户原话要点）：**偏移** ⇒ **不带位宽后缀**（`…_DTPREL`/`…_TPREL`）+ **按补码（有符号）加法**；**基址/绝对地址** ⇒ **无符号 48 位**。
3. **公式**（`B`=装载基址、`S`=符号运行时地址、`A`=`r_addend`、`*slot`=8 字节）：`ABS48`(数据槽)=`S+A`；`JUMP_SLOT`=`S+A`；`RELATIVE`=`B+A`；`COPY`=`memcpy(副本,S,st_size)`；`DTPMOD`=**定义该符号的模块**的 `tls_id`（加载器分配、**≥1**、容纳于 8 字节槽）；`DTPREL`=`DTPOFF(sym)+A`（补码）；`TPREL`=`TPOFF(sym)+A`（补码、**可负**）；`TLSDESC`=两格（`resolver 地址`=基址、`arg`=**由 resolver 约定**）。
4. **载体 = (c) 混合**：「**类型号/公式/语义 ⇒ 就地扩 `ADR-0019`（`D10…`，由 architect 另做）**；**行为类**（`ld.so` 用法/`PT_INTERP`/`DT_*`/绑定时机/越界）⇒ **另立新 ADR（architect 另做）**」 ⇒ 本任务**只写契约正文 + 标注来源**，**不改** `ADR-0019`、**不建**新 ADR。
5. **`PT_INTERP`** = **`/lib/ld-musl-dadao.so.1`**（**符号链接 → `libc.so`**，主流 musl 做法）；**guest 视角路径**（由 QEMU user-mode + guest root 解析）；构建须**显式传** `-dynamic-linker`（lld 无默认、建议不改其默认）。
6. **Hash**：**SysV + GNU 都提供**（≡ `--hash-style=both` = 上游 lld 默认）；**不得省略任一**。
7. **符号版本 / `DT_RELR`**：**都不做**（不发射版本段；`DT_RELR` 默认关 = `--pack-dyn-relocs=none`；契约**留位**并写明启用条件）；**登记**：musl 不支持 glibc 式版本化解析 ⇒ 第三方带版本段时**以 musl 行为为准**（已知限制）。
8. **GOT/TP**：**不引入 GOT 固定基址寄存器**（PC 相对访问槽）；**`DT_PLTGOT` 必须提供**；**TP 方向/偏置归 arch 宏**（`TLS_ABOVE_TP`/`TP_OFFSET`/`DTP_OFFSET`/`__get_tp`）⇒ 契约**只记录依赖**（逐 arch 定值在 musl 移植任务）。
9. **绑定时机**：**首版 eager（`BIND_NOW`）**（lazy 留后续）。
10. **失败与越界策略（新增 §10）**：① 48 位约束（`S`/`B`/结果越界 ⇒ **装载期报错**、不截断不 wrap）；② 未支持/未定义类型（含 `COPY`/`TLSDESC`/版本段/`DT_RELR`）⇒ **显式报错不静默**；③ 偏移按**补码**、`TP+TPOFF` 越界 ⇒ 报错；④ **lld 侧**：**经 GOT 间接访问解决远处符号**（无需 relaxation）；`REL12` **直接形式**仍限 ±2 KB ⇒ 越界 ⇒ **链接期报错**；relaxation 维持 `ADR-0019 D7` 禁用；⑤ 报错形态只要求「必须报错、不得继续」+ **不改 musl 行为**。

**契约改动章节**：§2.4（GOT/TP 口径）、§3（eager / `DT_PLTGOT` / 不经 GP）、§4.2–§4.5（类型集 / 编号 / 载体 / 指针）、§5（Hash / 版本·`DT_RELR`）、§6.1（`PT_INTERP`）、§6.5、§7（TLS 纳入）、§9（**裁定清单已定** + §9.1 历史）、**新增 §10 失败与越界策略**、附录 A。**来源标注**：类型号/公式 ⇒ `[ADR-0019 D10…（待 architect 落地）]` + `[spec-decision]（用户 2026-10-14 逐条确认）`；**引用非复制**（不抄上游正文）。

**测试结果**：一键证据脚本 `.work/evidence/<任务ID>/run.sh` 常模 **110 PASS / 0 FAIL（rc=0）**；`--inject` **11 PASS / bad=0（rc=0）**——注入①（类型表赋错编号 `RELATIVE`=6 + 散文赋号 `` `R_DADAO_JUMP_SLOT` = 7 `` + `#define REL_RELATIVE 7` + 复制 `SimRISC-00` 的 `rb0` 正文句）⇒ `check_invariants` **rc=1**，命中 `C3.type-map-matches-decision` / `C3.no-prose-equality-number` / `C3.no-arch-reloc-h-macro` / `C5.no-copy-S00-rb0-sentence` ⇒ `cp`+md5 还原（`445cda0f…`）⇒ 回绿；注入②（篡改 qemu 锁定 commit 末位 hex）⇒ **rc=1**（`C6.qemu-commit`）⇒ 还原 ⇒ 回绿。

**验收结果**（现场 rc，各捕被检命令自身退出码）：`make check`=0 / `check-knowledge-refs`=0 / `check-knowledge-dir`=0 / `check-no-residue`=0 / `check_issues.py`=0 / `check_spec_refs.py`=0 / `check_spec_drift.py`=0。

**修改文件**：`.tao/knowledge/contract-dynlink.md`、本任务书（状态 + 本节追加）、`.tao/knowledge/milestones.md`（`SPEC-139t` 行状态→`待验收`）、`.work/evidence/<任务ID>/{run.sh,foreign-paths.txt}`。**未提交 git**；**未动** `ADR-0019` / **不建**新 ADR / **未改** `spec/`·`contracts/`·组件。

**遗留问题**：类型号 / 公式的**决策正文**待 architect 在 `ADR-0019` 就地追加 `D10…`；行为类口径待 architect 另立新 ADR（§4.4）；`R_DADAO_NUM` 顺延值随 `D10` 冻结（**契约不写死**，避免臆造）。

**新发现/坑**：①「契约自身行文式」＝**表格行**（`| N | \`R_DADAO_名\` |`）承载号值——证据脚本按该式**现场解析并与裁定号值逐项对账**（含反例可达 FAIL）；散文 `名=N` 式另设负向断言，二者覆盖两形态。② §9 裁定清单里 `| 2 | \`R_DADAO_*\` …` 行会被宽松正则误捕为类型行 ⇒ 名须限定 `` `R_DADAO_[A-Z0-9_]+` ``（含尾反引号 + 后随 `|`）。③ 共享树上 C8 的 `components/` 改动来自并发 `LLVM-091t` ⇒ 该断言改为「**未声明**的 `spec/contracts/tests/components` 改动」计数（foreign 声明过滤），避免并发误红。

#### 第 2 轮 engineer 自审（表 A 九项裁定落纸）

**范围**（自主逐行审查）：`.tao/knowledge/contract-dynlink.md` 改动（§1.3/§1.4、§2.2/§2.4、§3、§4.1–§4.5、§5、§6.1/§6.5、§7、§9/§9.1、**新增 §10**、附录 A）、`run.sh`（C2/C3/C9 + 新增 C12–C19 + `--inject` ①）、`foreign-paths.txt`、本任务书、`milestones.md`（1 行）。事实逐条回源：`ADR-0019 D1/D2/D3/D6/D7`、`ADR-0021 D3`、`ADR-0025 D3/D5`、`contract-elf §2.2/§3.1`、`contract-isa §1.5`、`contract-abi §1.7`、musl `ldso/dynlink.c`/`arch/riscv64/reloc.h`/`Makefile`。**类型号/公式一处未自拟**（8 项 = 裁定号值 0,7..13，现场解析逐项对账）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| S1 §5 首条残留旧引用「其**是否/如何**落入 v5 待 §9 确认」（§9 已转已定） | ✅已修 | 改为「其是否为 v5 必备项由 LLVM 侧定」 | `grep '§9 确认'` 命中 0；`check_spec_refs` rc=0 |
| S2 §2.2/§4.1/§4.2 三处旧口径残留（「待 §9 #1 确认」/节名「待确认」） | ✅已修 | 分别改为「见 §4.3–§4.4（已定）」「节名由 LLVM 侧定」「类型集/编号已定」 | 契约 grep 无残留；C3 现场解析 8 条 |
| S3 §7 曾以散文式 `` `R_DADAO_TLS_DTPMOD`=10 `` 赋号（会触碰自设正向断言 `C3.no-prose-equality-number`） | ✅已修 | 改为「编号见 §4.3 表」（散文不写 `名=数字`） | `grep -cE` 命中 0 |
| S4 C3 解析正则过宽：误捕 §9 裁定清单行 `\| 2 \| \`R_DADAO_*\` …` | ✅已修 | 收窄为 `` \| N \| `R_DADAO_[A-Z0-9_]+` \| ``（名含尾反引号 + 后随 `\|`） | 现场统计 = 8（= 裁定 8 项）；注入错号 ⇒ rc=1 |
| S5 共享树上 `C8.no-spec/contracts/tests/components-change` 因并发 `LLVM-091t` 补丁误红 | ✅已修 | 改为「**未声明**的 `spec/contracts/tests/components` 改动」计数（foreign 声明过滤） | 常模 C8 rc=0；`foreign-paths.txt` 声明 3 条并发改动 |
| S6 新增节内 `.work/evidence/SPEC-139t/…` 字面路径 | ✅已修 | 改 `<任务ID>` 占位（遵「文本不写 `.work/<具体路径>` 字面」） | 新增节 grep 无 `.work/evidence/SPEC-139t` |
| S7 C3 负向散文断言漏捕前轮 reviewer ⑤/⑥（反引号包数字 / 双反引号名） | ✅已修（加固） | 正则名侧 `` `* ``、数字侧 `` `?[0-9] `` | pristine **0 误报**；三形态探针（含 ⑤/⑥）**3/3 命中** |

**判决**：无未修 finding（S1–S7 全部处置并复验）；判据对账 = 状态 `待验收`。**未取得新用户裁定**（本节仅落纸既有裁定）；**未越界**（未改 `ADR-0019`、不建新 ADR、未改 `spec/`/`contracts/`/组件）。

#### 第 3 轮 reviewer 验收（最终一致性复核；被测物只读 + 注入即还原）

**重跑记录**（workdir=仓库根；各捕被检命令自身 rc）：
- 门控 7 项全 **0** ✓：`make check`=0 / `check-modules`=0 / `check-knowledge-refs`=0 / `check-knowledge-dir`=0 / `check-spec-refs`=0 / `check-no-residue`=0 / `check_issues.py`=0。
- 证据脚本常模**重跑 = rc=1，105 PASS / 6 FAIL**（pristine 契约 md5 `647d94e2…`）：`C3.type-count==8 (actual=15)`、`C3.type-map-matches-decision`、`C4.no-renumber-of-existing (ABS48:6≠0 / NUM:14≠6)`、`C12.D10-pending-architect`、`C14.hash-no-omit` ⇒ **阻断 F1**。
- `--inject` 重跑 = rc=1、10 PASS / 1 FAIL（bad=1）：**`INJ3.green-after-restore (rc=1/0)` FAIL**（还原后回不了绿）；INJ1/INJ2 注入与 md5 还原（`647d94e2…`）正常。

**三处一致核（★ 契约 ↔ `ADR-0019 D10` ↔ `adr-0026`）**：① 编号表 **15 行机械 diff 全同**（awk 现场解析对账：`0=NONE/1–5 静态/6=ABS48/7–13 动态/14=NUM`；`adr-0026` L74「`NONE=0`/`ABS48` `0→6`/`7`–`13`/`NUM=14`」同）✓；② 8 条公式逐字同（`S+A` 无符号48／`B+A`／`memcpy(副本,S,st_size)`／`tls_id`≥1／`DTPOFF+A` 补码／`TPOFF+A` 可负／TLSDESC 两格）✓；③ 值类规则（偏移补码·无后缀／基址绝对·无符号 48）同 ✓；④ Hash=仅 GNU（契约 §5 修订注记 ↔ `D3` 修订，用户原话同）✓；⑤ GOT 语义+两段式（`ABS48`+`ldm.o_rrri_rb` 落 `rb`+`jump rbX,rd0,0`）↔ `D5` 同 ✓；⑥ PLT 只读/full RELRO、icache 澄清 ↔ `D5/D6` 同 ✓；⑦ eager ↔ `D6` 同 ✓；⑧ 越界 5 条（48 位／未支持显式报错／补码·TP／lld GOT 间接+REL12±2KB／分层不互放宽）↔ `D7` 逐条同 ✓。**内容层无 finding**。

**历史未篡改核**：`git diff e7afe81 HEAD -- adr-0019` = **+41 / −0**（删除行 0）⇒ `D1–D9` 逐字未变，新增仅 `D10` 块+状态说明+changelog ✓；`ADR-0026` 在 `ADR-0019` 内仅 L86/L134 两处**指针**、无改写 ✓。

**事实回归核**：`DADAO.def` 现仍 `R_DADAO_ABS48=0`/`R_DADAO_NUM=6`（现场 grep）= **预期未同步**（`ISS-206` open/P2 已登记 `issues.yaml`）——记差异、**不计 finding**；三条事实抽核 ✓：musl `dynlink.c:406` `if (type == REL_NONE) continue;`、`:986-987` `DT_PLTGOT → p->got`、`contract-isa.md:299` `ldm.o rdha, rbhb, rdhc, immu6`。

**用户原话核**：「增加 `R_DADAO_NONE`，编号 0，`R_DADAO_ABS48` 改为 6」（ADR-0019 L70/L134）、「只支持 GNU hash，无需提供 both」（adr-0026 L29/L97 + 契约 §5/§9）、「直接把相对偏移写进 `rdhc`…无需多一条 `rd2rb`」（adr-0026 L40/L99）、「用 musl 自带 ldso（推荐）」（adr-0026 L95）——两 ADR 原样存在、**无臆造/扩写** ✓。

**独立反例**（reviewer 注入；`cp`+md5 还原、禁 git）：① 编号表 `| 6 | R_DADAO_ABS48 |`→`| 0 |…`（md5 `647d94e2…`→`28f663dc…`）⇒ 脚本响应（C3 diff 显示 `ABS48=0`）**但 FAILS 6→5、`C4` ABS48 反转 PASS** ⇒ 实证 F2 反向激励；② 散文 `` `R_DADAO_COPY` = 9 ``（md5→`54fee101…`）⇒ `C3.no-prose-equality-number` **PASS→FAIL（1 match，可达 FAIL ✓）** ⇒ 还原 ⇒ 该断言回 PASS、FAIL 集回基线 6 条、md5=`647d94e2…`（**相等 ✓**）。**「注入→FAIL→还原→回绿」整体无法闭环**——根因即 F1（pristine 已红）。

**约束核验**：① 被测文件除注入（已还原、md5 对账）外未改 ✓；② 完成区未动 ✓；③ 未提交 git ✓；④ 门控 7 项全 0 ✓；⑤ 三处一致 ✓；⑥ `D1–D9` 未篡改 ✓；⑦ 快照对账：开工 `git status`=空、5 文件 md5 已录；结束 `git status` 仅本任务书（本审阅记录）。

**判决：Needs Revision**（仅证据脚本层；契约 / 两 ADR **内容层达标**、门控全绿）。
- **阻断 F1**：`.work/evidence/<任务ID>/run.sh` 未随 D10 同步 ⇒ 常模 rc=1（6 FAIL）：(a) `C3` 期望表仍为旧 8 项（`ABS48=0`）且 `type-count==8` ⇒ 改为终表 15 行（`0=NONE…14=NUM`）或「动态 8 项按新号 `6,7–13` + `NONE=0` + `NUM=14`」；(b) `C4` 以 `contract-elf §2.2`（旧号、`ISS-206` 待同步）为基线 ⇒ **判反**（错号反而 PASS，见反例①）⇒ 改以 `ADR-0019 D10` 表为基线、对 `contract-elf` 差异显式挂 `ISS-206`；(c) `C12.D10-pending-architect`（断「待 architect 落地」）已过时 ⇒ 改断「已落地」（`[ADR-0019 D10]` + `[ADR-0026 D1–D8]`）；(d) `C14` 仍断「双发」（`不得省略任一` 已随修订删除）⇒ 改断「仅 GNU」（`--hash-style=gnu` + 修订注记）。改后须**常模全绿 + `--inject` `INJ3` 回绿**再复验。
- **非阻断**：N1 `D10`「`COPY`/`TLSDESC` 不发射、lld 遇即报错」契约 §4.3 未明说（§10② 近似覆盖，建议补一句对齐）；N2 值类规则「名带 `48` 后缀」与 `JUMP_SLOT`/`RELATIVE` 实名不符（三处同文，仅措辞易误读）；N3 `--inject` ② 建议补 `fired.C6.qemu-commit` 断言（现仅判 rc≠0）。

#### 第 3 轮返工（F1 + N1–N3，engineer；契约只改 §4 两句，编号表 / 公式 / ADR / `contract-elf` **未动**）

- **F1（阻断）已修——证据脚本随 `D10` 同步**：**C3** ⇒ 断**新编号总表**（现场解析 15 行 = `0=NONE`／`1–5` 静态／`6=ABS48`／`7–13` 动态／`14=NUM`；计数改「与裁定表行数**现场对账**」、不再写死 8）+ 三条号值锚 `0`/`6`/`14`；**C4** ⇒ 基线改「**契约 + `ADR-0019 D10`**」（两表逐行机械 diff），`contract-elf §2.2` 旧号转为**预期状态**断言（`ABS48=0`／`NUM=6` 且 `ISS-206` 须 `open`），另加 `1–5` 静态类两侧号值一致；**C12** ⇒ 断「**已落地**」（`均已由 architect 落地` + 两 ADR 节现场存在 + 旧「待 architect 落地」须 0 命中）；**C14** ⇒ 断「**仅 GNU**」（`--hash-style=gnu` + 修订注记 + `ADR-0026 D3`），删「双发 / 不得省略任一」断言。
- **现场输出（口径 = 现场统计）**：常模 **rc=0、127 PASS / 0 FAIL**（旧 105 PASS / 6 FAIL 全消）；`--inject` **rc=0、12 PASS / bad=0**，**`INJ3.green-after-restore` PASS** ⇒「注入 → 还原 → 回绿」闭环恢复。契约 md5 = `7ff243263e07527faadc460a3e8ebee0`。
- **N1**：契约 §4.3 补一句原文——`**首版 `COPY` / `TLSDESC` 不发射**——lld 遇即**报错**（§10②）。`（脚本加 `C3.copy-tlsdesc-not-emitted`）。**N2**：§4.3 值类规则改为「**命名后缀与值类解耦**：带 `48` 后缀者**仅**既有项 `ABS48`（同类中 `JUMP_SLOT` / `RELATIVE` 的**名不含** `48`），偏移类名**一律不带**位宽后缀」。**N3**：`--inject` ② 补 `INJ2.fired.C6.qemu-commit`（读 `inject2.log` 真实 `FAIL` 行判据）。
- **可达 FAIL 复核**（**临时树** `/tmp` 内注入，禁 git 还原；harness = 抽 `run.sh` prelude + `check_invariants`）：6 例逐条命中该断言 ⇒ `C4.contract-matches-D10`／`C4.contract-elf-expected-stale-ABS48`／`C14.hash-style-gnu`／`C12.D10-landed`／`C12.no-pending-phrase`／`C3.copy-tlsdesc-not-emitted`，且 `cp` 还原后复跑 **rc=0**（汇总 `bad=0`）。
- **坑（探针自身）**：临时树 harness 若以 `check_invariants; echo …` 收尾，脚本退出码 = 末条 `echo`（恒 0）⇒ **已 FAIL 仍 rc=0 假绿**；须 `check_invariants; rc=$?; exit $rc`（同 `cmd | tail` 吞码一类）。
- **门控（现场 rc）**：`make check` = 0 / `check-knowledge-refs` = 0 / `check-knowledge-dir` = 0 / `check-no-residue` = 0 / `check_issues.py` = 0 / `check_spec_refs.py` = 0 / `check_spec_drift.py` = 0。**未提交 git**（提交权归 architect）；状态保持 **`待验收`**（待 reviewer 复验）。

#### 第 4 轮 reviewer 验收（F1 返工复核；**被测物只读**，run.sh/md5 前后一致）

**重跑记录**（workdir=仓库根；各捕被检命令自身 rc）：
- 常模：**rc=0 / 127 PASS / 0 FAIL / 0 SKIP** ✓
- `--inject`：**rc=0 / 12 PASS / bad=0**；`INJ3.green-after-restore` **PASS** ✓（闭环恢复）
- 门控 7 项全 **0** ✓：`make check`=0 / `check-knowledge-refs`=0 / `check-knowledge-dir`=0 / `check-no-residue`=0 / `check_issues.py`=0 / `check_spec_refs.py`=0 / `check_spec_drift.py`=0
- **F1 四断言核**：C3 ⇒ 15 行总表（`0=NONE/1–5/6=ABS48/7–13/14=NUM`）；C4 ⇒ 基线=契约+D10 + `contract-elf` 预期未同步（`ABS48=0`/`NUM=6` + `ISS-206 open`）——三断言联动可判反 ✓；C12 ⇒ `均已由 architect 落地` + 旧句 0 命中；C14 ⇒ `只发射 GNU Hash` + `--hash-style=gnu` + `不得省略任一` 0 命中
- **假绿修复核**：`check_invariants` 末 `rc=$?; exit $rc` + inject 尾 `[ "$jbad" -eq 0 ] && exit 0; exit 1`；独立注入（临时树删 `只发射 GNU Hash`）⇒ harness **rc=1** ✓
- **越界核**：`ADR-0019` / `ADR-0026` / `contract-elf` / `spec/` / `contracts/` **未改**（git diff 空）；快照前后 md5 逐文件对账一致 ✓（run.sh=`2647606d…` / contract-elf=`95918495…` 前=后）

**判决：Accepted**（上轮唯一阻断 F1 已修并经独立复验；契约/两 ADR 内容层达标；门控全绿）。
- 非阻断：前轮 N1/N2/N3 已处置（`COPY`/`TLSDESC` 不发射一句 + 名后缀解耦 + `INJ2.fired`），本轮未发现新 finding。

#### 第 3 轮 engineer 自审（返工后；自主逐行）

**范围**：`run.sh`（C3 / C4 / C12 / C14 与 `INJ2` 断言逐行读）、契约 §4.3 两句、本任务书。D10 表 15 行由 `C4.contract-matches-D10` 从 ADR 文件**机械解析对账**（非硬编码比对）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| S1 临时树探针 harness 以 `echo` 收尾 ⇒ 脚本退出码恒 0（**已 FAIL 仍 rc=0 假绿**） | ✅已修 | harness 末行改 `check_invariants; rc=$?; exit $rc` | 同一次注入：修前 rc=0 / 修后 rc=1；`tt-inject.sh` 汇总 bad=0 |
| S2 C4/C12 若只断契约**措辞**，「已落地」可在 ADR 被回退时仍全绿 | ✅已修（加固） | 断言直接 grep 两 ADR 文件真实节标题（`D10 — …` / `D1 — …`） | `C12.ADR0019-D10-section` / `C12.ADR0026-D1` 现场 PASS（命中真实文件） |

**判决**：无未修 finding；判据对账 = 状态 `待验收`；**未动** 编号表 / 公式 / ADR / `contract-elf`（契约仅 §4.3 改两句）。
