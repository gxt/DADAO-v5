# LLVM-081t: ISA↔后端覆盖矩阵（生成式，两层分列）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-079t`、`LLVM-080t`（矩阵第 2 层需已构建后端；同模块 ⇒ 串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #5`）：**「ISA↔后端覆盖矩阵」立即立项**——生成式；以 **`contracts/opcodes.yaml` 全量**记录为**真源**；**两层分列**：① **汇编器可受理？** ② **ISel 是否用得上？**（**现有 lit 只证第①层**）。
  - 真源：`contracts/opcodes.yaml`（`scope` 分 `m1`/`fp`/`excluded`/`m3`；每指令 mnemonic/format/op/mask/value/fields/legality/spec_cite）。现有工具 `tools/llvm/{gen_asm_list.py,validate_instrinfo.py,check_lit_bytes.py,...}`（复用优先，DRY）。
  - 后端能力来源：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOInstrInfo.td`/ISel）。
- **输出**：
  1. 生成式工具（落 **`tools/llvm/**`**，**入库**、**非易失**）：由 `contracts/opcodes.yaml` **全量**遍历，输出覆盖矩阵（机器可读 + 人类可读，如 TSV/Markdown），**两层分列**：
     - 第①层「汇编器可受理」：逐指令（各合法 shape）喂 `llvm-mc`/`llc`，记录受理/拒绝（**复用现有 lit 能力**）。
     - 第②层「ISel 用得上」：记录该 ISA 指令**是否有 ISel 模式引用**（由 TableGen/ISel 机械提取，**非人工判读**）。
  2. 一页**缺口汇总**（未被 ISel 使用的指令清单 = 候补优化面，供后续里程碑参考）。
- **约束**：
  - **以 `contracts/opcodes.yaml` 全量为真源，禁手工挑拣**（不得只挑已知指令）。
  - **生成式**：矩阵由脚本产出；**计数不写死**（现场统计）；脚本随产物入库（`AGENTS.md`「生成器/脚本随产物保留」）。
  - **不改** `contracts/opcodes.yaml`；**只读**它。
  - 只动任务范围（`tools/llvm/**` + 本文书 + 必要的测试），越界须披露。

## 验收标准

1. **全量覆盖**：矩阵行/指令数 = `contracts/opcodes.yaml` 中指令条数（**现场统计**，脚本从 yaml 数出，不写死）；`grep`/脚本真实输出证明**每条指令都有两层取值**。
2. **两层分列**：输出含独立两列（第①层、第②层），且**第①层与现有 lit 口径一致**（抽查若干指令与 lit 结果一致）。
3. **生成式**：脚本可从真源**幂等重跑**（两次运行结果一致）；`--check` 模式可对「矩阵与真源不一致」报 FAIL（**反例门控**：注入一条虚构指令或篡改 yaml 副本 ⇒ FAIL ⇒ 还原 ⇒ 回绿）。
4. **缺口汇总**：输出「未被 ISel 使用的指令」清单（现场统计条数）。
5. **门控**：`make check`（若新工具纳入门控则全绿）；`check-no-residue` EXIT=0。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：一键证据 `.work/evidence/<任务ID>/run.sh` **24/24 PASS（rc=0）**；工具 `--check` PASS；`make check` rc=0；`make check-no-residue` rc=0。
**修改文件**：新增 `tools/llvm/gen_isa_coverage.py`；新增 `.tao/knowledge/llvm-isa-backend-matrix.tsv` + `.md`；本任务书；`.tao/knowledge/milestones.md` 流水一行；证据脚本 `.work/evidence/<任务ID>/`（`.work` 内，非入库）。
**验收结果**（计数一律现场统计、脚本从 yaml 数出）：
1. **全量覆盖**：TSV 数据行 = 真源 **227** 条（`m1` 155/`fp` 60/`excluded` 11/`m3` 1）；每行两层取值齐备（①∈{accept,reject}、②∈{yes,no}）。
2. **两层分列**：① `accept` **217**/`reject` **10**（excluded 由汇编器显式拒绝）；受理行编码复核 `(word&mask)==value` 唯一命中 + == 真源 word，**mismatch 0**。② `yes` **86**/`no` **141**；证据 **110** 条（`pat` 87/`pat-args` 8/`isel-cpp` 15），外部 `sed` 独立复核 **110/110**（含 `--inject` 能失败自检）。
3. **口径一致**：形态复用 `tools/testcases/generate_lit_vectors.py::build_case`（= lit 全量档同一行文本），逐条命中 `tests/llvm/lit/MC/DADAO-gen/gen-*.s` **217/217**；`check_lit_bytes.py --lit-dir tests/llvm/lit/MC/DADAO-gen` rc=0。抽查：`and.o_orrr_rd`→`DADAOCodeGen.td.patch:333`；`call_iiii_ra`→`DADAOISelDAGToDAG.cpp.patch:381`；`fosgnj_orrr_rf`→`:551`。
4. **幂等**：两次重跑 MD5 一致且 == 已入库（tsv `ca0d08a5…`、md `cbef8932…`）。
5. **反例门控**：A 真源副本 + 虚构指令 ⇒ FAIL ⇒ 回绿；B 篡改已入库 TSV ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿；C 篡改已入库 MD 同；D 抽走 lit 全量档一个 format 文件 ⇒ 「①层与 lit 口径一致」断言 FAIL（命中 84 条）⇒ `cp`+md5 还原 ⇒ 回绿。
6. **缺口汇总**（141 条 `no`，四类）：候补优化面 **101** ｜ 汇编层/特权族 5（`crrr`/`ciii`/`crii`+`fence`/`swym`，机械判据）｜ 仅 post-ISel 24 ｜ `excluded` 11。候补优化面前若干：`add.{sb,so,st,sw,ub,ut,uw}_*`、`cmp.{sb,st,sw,ub,ut,uw}_orrr_rd`、`div.*`、`shr./shl.{ub,sb,uw,sw,ut,st}_*`、`ldm./stm.*`、`cs.eq/ne`（与 `ISS-187` 口径一致）。
7. **无残留**：`git status --porcelain -uall` 仅本任务改动 + 他任务既有 `??`；无 `*_tmp*`/`*.orig`/`*.rej`。
**新发现/坑**：① `validate_instrinfo.parse_td_defs` 用 `[^}]*` 截 def 体 ⇒ 注释含花括号的 def（`ft2fo`）op/ha 为 `None`；且 `check-instrinfo` **只**校验 `DADAOInstrInfo.td`（不含 FP 档）⇒ 60 条 FP def 的该缺陷长期无门控（本工具改「整行 `}` 收尾」）。② FP 记录**无** `ha` 字段，须由 `value` bits[23:18] 反推；`jump`/`tailjmp` 两 def 同编码 ⇒ 一条记录多 def（按集合处理）。③ bash `read -ra` 以 tab 为 IFS 会按「空白」折叠连续分隔符/去尾 ⇒ 空列被吞、列号错位（须 python `csv` 或 `awk -F'\t'`）。④ `^\s*def` 在 `re.M` 下会从前一行空行起匹配（`\s` 含 `\n`）⇒ 证据行号偏移（须 `^[ \t]*def`）。⑤ lit 全量档 `gen-excluded.s` 的反例只以注释存放 ⇒ 跨产物行文本比对仅对**正例**成立。
**遗留问题**：① 第②层为**静态**提取（不读 `.inc`/不跑构建）；经 pseudo 展开才落地的指令归 post-ISel、不计第②层——已在矩阵 MD §1「提取方法的局限」披露。② **未纳入 `make check`**（本任务范围不含 `Makefile`）⇒ `--check` 需手动/经证据脚本触发；纳门控须另行立项。③ 生成物与 `llvm-mc` 版本绑定（第①层为现场运行结果），换工具链须重跑，否则 `--check` 会红（设计如此）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`tools/llvm/gen_isa_coverage.py`（新增，~490 行）+ 生成物 + 证据脚本。逐行审查：解析/提取/渲染/check 四段；重点核对「赋值来源是否可独立复核」「计数是否现场统计」「断言是否有可达 FAIL 路径」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 def 体按 `[^}]*` 解析会截断（复用 `validate_instrinfo` 时发现 FP def op/ha 为 None） | ✅已修 | 自写 `parse_instr_defs`，体按整行 `}` 收尾 | 219/219 def 取到 op；217 条记录建到 def 映射（余 10 = `excluded` 无 def） |
| F2 证据行号取 `Pat<`/语句**起始**行 ⇒ 跨行体上该行不含 def 名，无法复核 | ✅已修 | 改为 def 名 **token 所在行** | `--check` 证据行复核 110/110；证据脚本 sed 独立复核 110/110 |
| F3 `^\s*def` 在 re.M 下从前一行空行起匹配 ⇒ 行号偏移 | ✅已修 | 改 `^[ \t]*def`／`^[ \t]*defm` | 偏差消失（`--check` 由 FAIL 20 项 → 0 项） |
| F4 `pat` 与 `pat-args` 对同一 `def : Pat<…>` 行**重复**计证据（且 `pat-args` 未真正覆盖 defm 实参） | ✅已修 | `pat-args` 改为「语句内**不在** `Pat<…>` 体的 `<...>` 组」+ defm 全语句 | 证据条数 87+87+15 → **87+8+15**；8 条恰为 `defm FPSelCC_*` 实参 |
| F5 证据列不含 def 名，无法定位是哪条 def 被引用 | ✅已修 | 证据格式 `kind:文件:行:def名`；`_ev_def` 反查死代码删除 | TSV/MD 证据列含 def；`--check` 按 def 名复核行 |
| F6 `run_check … true` 使前两项检查恒真（无可达 FAIL） | ✅已修 | 改为 heredoc 喂 python 检查本体给 `run_check` | 证据脚本 24 项均带期望 rc；`--inject` 自检证明证据检查能 FAIL |
| F7 证据脚本用 `git status \| tee`（吞码风险）+ `grep -oP` 依赖 PCRE | ✅已修 | 改 `> file; cat file`；改 `sed -n 's/…/\1/p'` | 脚本 `bash -n` 通过；run.sh rc=0 |
| F8 `rec_ha` 硬编码 `mask == 0xFFFC0000` | ✅已修 | 改判据 `(mask & 0xFC0000) == 0xFC0000`（ha 位域） | 生成物 MD5 不变（等价） |
| F9 `_post`/`L1_stderr` 为未使用字段（死数据） | ✅已修 | 删除两键 | `--check` PASS；产物 MD5 不变 |
| F10 第②层「真缺口」混入 `cfx2rd`/`escape`/`swym` 等汇编层/特权族，噪声影响候补优化面可用性 | ✅已修 | 以**机械判据**（`format∈{crrr,ciii,crii}` 或助记符∈{fence,swym}）拆出 3.2 类 | 缺口 101+5+24+11=141（现场统计） |
| F11 反例注入若中断可能留在仓库 | ✅已修 | run.sh 加 `trap restore_all EXIT`（`cp` 备份还原，禁 git 还原） | 反例 B/C 还原后 md5 与注入前一致 |
| F12 「第①层与 lit 口径一致」断言的 FAIL 路径未实测 | ✅已修 | 证据脚本加反例 D（抽走 `gen-orrr.s`） | 抽走后 `--check` rc=1 并命中 **84** 条不一致；`cp` 还原后 md5 一致（`a113970e…`）⇒ 回绿 |

**判决**：12 项 finding **全部 ✅已修**（含 F12 补测反例 D）；证据脚本 **28/28 PASS**、`--check` PASS、`make check` rc=0 ⇒ 可标 **待验收**。

### 第 2 轮 reviewer 验收

**环境**：分支 `LLVM-081t`，`llvm-mc` v23.1.1（`.dadao/cross-toolchain/bin/`）。
**重跑记录**：
- `make check` rc=0；`make check-no-residue` rc=0；`make check-knowledge-refs` rc=0
- TSV 227 行，yaml 227 条，id 集合一致；L1 `accept` 217/`reject` 10，L2 `yes` 86/`no` 141，evidence 110 条（pat 87/pat-args 8/isel-cpp 15）
- ①层抽验：6 条 accept llvm-mc rc=0，3 条 reject rc=1；`(word&mask)==value` 手算 and.o（0x4020824A）+ fosgnj（0x447C824A）均唯一命中
- ②层抽验：6 条 yes `sed -n` 行号全命中（and.o:333、fosgnj:549/551、cs.n:599/602、add.o:142/327、call:381）；4 条 no 检索 Pat/DADAO:: 均无命中
- lit 抽查 4 条（and.o/call/fosgnj/ldm.o）gen-*.s 均存在；`check_lit_bytes rc=0`
- 幂等：重跑 diff 空，tsv `ca0d08a5…`、md `cbef8932…`
- 独立注入：TSV 第 1 行 `yes→no` ⇒ `--check` rc=1（diff 显示篡改行）；`cp`+md5 还原后回绿 rc=0
- 越界：`git diff --stat -- contracts/` 无改动；`_tmp*/orig/rej` 无残留
**约束核验**：真源全量 227 条无挑拣 ✓；生成式现场统计 ✓；不改 contracts/ ✓；只动 tools/llvm/** + 2 产物 + 任务书 + milestones.md ✓
**遗留判定**：`--check` 未纳入 `make check`（任务书明确不含 Makefile），属**建议整改**非阻断；现有 drift 门控均不扫描本产物，无误扫风险。
**非阻断 note**：完成区「测试结果」写 24/24 而工程师自审终态 28/28，属记录时序差异。
**判决**：**Accepted**（6 条验收标准全部通过，无阻断项）。

