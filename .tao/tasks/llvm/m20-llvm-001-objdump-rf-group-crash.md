# m20-llvm-001: `llvm-objdump` 对 rf 寄存器组越界崩溃（ISS-468）

**模块**：llvm
**项目里程碑**：M20
**依赖**：无（`m14-llvm-007`、`m15-spec-003` 已合入）
**可并行分片**：否（单组件补丁 + 单 lit 面）
**预估**：2–4 h
**档位**：大改（组件补丁；复核 ≤60 min）
**状态**：待验收

## 背景（M20 分诊，2026-11-25）

`ISS-468` 记录 9 个 `tests/inst/**/*_rf.S` 镜像无法生成 IP→助记符表：
组装后用 `llvm-objdump -d` 反汇编即断言崩溃。现场复核 9/9 仍复现：

```
Assertion `RegNo && RegNo < 258 && "Invalid register number!"' failed
```

定位到的触发点是测试故意构造的非法 `ldm` 原始字 `0x3EDC304A`
（`tests/inst/01-load-store/ldm.o_rrri_rf.S` 第 116 行，`rf55 + immu6=10 > 64`）。
MC 解码器接受该字并给出 `rf55`、`count=10`，打印机 `printRegGroupRange`
用 `Start.id() + Count - 1` 算结束寄存器，得到 258（越出 rf bank），撞断言。
合法用例（如 `{rf1:rf63}`、`{rf32:rf47}`）不触发。

## 目标

1. `llvm-objdump -d` 对**非法/越界组编码**不得崩溃：按 MC 层判据拒绝该编码并由
   objdump 输出可见的未知/非法指令形式，或在打印机层做不改合法输出的防御。
   具体分支在任务书「待裁定」中给出并由 reviewer 复核，不得静默截断成合法组。
2. 合法 rf 组（含 rf63 边界、`{rf32:rf47}`、`{rf1:rf63}`）反汇编输出逐字不变。
3. 9 个 `_rf.S` 镜像全部可生成反汇编；不得通过修改测试用例里的非法原始字来绕过
   （该字是合法性用例的一部分）。

## 验收（逐条贴真实 rc）

1. 9/9 `_rf.S` 组装 + `llvm-objdump -d` 全部 rc=0；崩溃数为 0；对 `0x3EDC304A`
   给出稳定、可重复的非法编码输出（记录原文）。
2. 合法 rf 组反汇编抽样 3 例（`{rf63:rf63}`、`{rf32:rf47}`、`{rf1:rf63}`）与改动前
   逐字节 `diff` 为空。
3. 新增/扩展 lit 用例：覆盖非法 `0x3EDC304A`、合法 rf63 边界和至少一个合法组；
   证明非法分支可达（注入前红/后绿），且不是恒真断言。
4. 按 `docs/Process-01` 更新 `components/llvm-project` 补丁序列并重导；`check-lit`、
   `check-patch-tree` 的 **llvm 段 0 problem**、`check-instrinfo` 真 rc。
5. 重建/安装按仓库纪律执行；完成区记录 `llvm-objdump` 与安装根 md5，证明安装根
   与构建树一致；若 `install-host` 与在途 QEMU 窗口冲突，须串行等待或按规程
   记录并补装。

## 约束

独立 `git worktree`（分支 = `m20-llvm-001`）；不提交 git；只改
`components/llvm-project/**`、对应 lit 用例与本任务书；不改 `spec/`、契约、
`Makefile`；不新增测试之外的文档。任务书不写构建树/安装树/临时目录的具体路径；
证据落在「运行期证据目录内的 `run.sh`」。
术语：`rf` 是**寄存器组**，不写「银行」。

## 实现决策（任务书要求记录：修在 MC 解码器，而非打印机）

**选择：在 `DADAODisassembler::getInstruction` 解码成功后拒绝非法组编码（返回
`MCDisassembler::Fail`），打印机一行未改。**

1. **判据属 MC 层**：`contract-isa.md §15.1` / `contract-fp.md §15` 把
   `immu6 == 0`（`mreg_zero`）与 `起始 + immu6 > 64`（`mreg_range_overflow`）定义为
   **ILLI**；`llvm-objdump` 对 `Fail` 的既有行为就是打印 `<unknown>`（`0xFFFFFFFF`
   实测同形），即「可见的未知/非法指令形式」，所有消费方（`llvm-objdump`、
   `llvm-mc -disassemble`、C disassembler API）行为一致。
2. **打印机防御不能修正确性**：pre-fix 实测 RD/RB/RA 组越界不崩溃而是**静默跨
   bank**——`ldm.o` op 0x38/0x3A/0x3C 的 `起始 61 + 4` 打印成 `{rd61:rf0}` /
   `{rb61:rd0}` / `{ra61:rb0}`。只在打印机防越界，要么继续打印这些假组，要么复制
   同一套判据；放在解码器一次判完更小、也更完整。
3. **合法输出零改动**：校验只读解码后的操作数、不重写 MCInst；`{rf63}`、
   `{rf1:rf63}`、`{rf60:rf63}`、`{rf32:rf47}`、`rf2rf`、`ftcls` 与 pre-fix 快照
   逐字节 `diff` 为空。
4. **不误伤**：按 opcode 白名单触发（19 条 rrri `ldm.*`/`stm.*` + 11 条 orri：9 条
   块复制 + `ftcls`/`focls`），`ext.so` 等以 immu6 作移位量/阶/舍入码的 orri 不参与
   （用例钉住 `ext.so rd61, rd61, 10`）。
5. **范围**：`mreg_range_overlap`（区间重叠）不是崩溃源、不影响可打印性，本次不在
   解码期拒绝（仍由汇编期/运行期规则承担），避免扩大行为变更面。

## 完成区

**测试结果**：`make check-lit` 183/183 PASS（rc=0，MC+CodeGen+E2E）；本任务新增/扩展 lit 2 文件全绿；证据脚本 11 项全绿（`fails=0 skips=0`，rc=0）。pre-fix 快照跑同一新用例 ⇒ rc=1（崩溃），修复后 ⇒ PASS（注入红→还原回绿）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/Disassembler/DADAODisassembler.cpp.patch`（+100/−3，`series` 99 不变）；`components/llvm-project/changelog.md`（M20 一条）；`tests/unit/llvm/lit/MC/DADAO/rf-group-range.s`（新增）；`tests/unit/llvm/lit/MC/DADAO/ra.s`（两处期望订正）；本任务书。
**验收结果**：
- 65/65 `tests/inst/**/*_rf.S`：`llvm-mc` + `llvm-objdump -d` rc=0、断言/abort 0 次（含 ISS-468 的 9 例；计数现场派生）。
- `0x3EDC304A` 输出原文 `3e dc 30 4a  \t<unknown>`，连跑 3 次逐字节相同；`0x3EFC3042`/`0x3E143040`/RD·RB·RA 越界/classify 双窗口同形。
- 合法组 3 例（`{rf63:rf63}` 打印为 `{rf63}`、`{rf32:rf47}`、`{rf1:rf63}`）与 pre-fix 快照 `diff` 为空（0 diff 行；双二进制对照亦为空）。
- `check-patch-tree`：`llvm-project: 99 patch(es)`，llvm 段 0 problem；整库 rc=1 由 qemu/linux/musl 的 23 行 KNOWN-RED 组成（在途任务推进共享源树，ISS-463，与本任务无关）。
- `check-instrinfo` rc=0（10 PASS / 0 errors）。
- 安装根与构建树 `llvm-objdump` md5 同为 `7893b3086f305947bf0afb1ce029f985`（`llvm-mc` 同为 `ebaad000b2267ce3b794342b837c308b`）；clang build-id 指向本任务补丁 commit `b6caceed2`。
- `make build-mc`（rc=0）与 `make install-host`（rc=0）均经 Makefile 的 `gate.lock` + `writer_guard`（日志无「等待他人释放」记录，未插队在途任务；install-host 的嵌套 llvm/qemu 注册为其自身 ancestry）。
- 证据：运行期证据目录内 `run.sh`。
**新发现/坑**：
1. RD/RB/RA 组越界**不崩溃而是静默跨 bank**：寄存器枚举 ra→rb→rd→rf 相邻，`start.id()+count-1` 会读下一 bank 的合法寄存器（`{rd61:rf0}` 等）——只修 rf 断言会留下更危险的假组，故按 MC 层判据统一拒绝。
2. **汇编器仍接受跨 bank 文本组**：`ra2rd {rd63:rf61}, {ra63:rb61}` 被接受并编码为 `0x40BBFFFF`（immu6=63），AsmParser 的 count 推导按寄存器 id 差值跨了 bank、`mreg_range_overflow` 未拦住；属既有汇编期漏洞（非本任务崩溃源），建议另立 issue。
3. `ra.s` 原把上述非法编码的跨 bank 打印当作 expected（`OBJ:` 钉 `{rd63:rf61}, {ra63:rb61}`），属把 bug 固化为期望；随本修复订正为 `<unknown>`（原始字未改）。
4. `{rf63:rf63}` 打印形态是 `{rf63}`（`Count>1` 才加 `:`）；验收抽样按打印原文比对。
**遗留问题**：无（「新发现 2」建议另立任务/issue，不在本任务范围）。

## 审阅记录

#### 第 1 轮 engineer 自审

**结论**：改动集中在解码器单点（`getInstruction` 的 post-decode 校验），逻辑、边界与
失败路径均已复核；所有 finding 已处置，状态可置「待验收」。

逐行审查要点（无 finding）：
- `hasInvalidRegGroup` 的 `GroupInvalid` 对 `isReg`/`isImm` 先判类型（解码失败/异常
  形态不会 `getReg()` 误取），`Count` 6 位字段值 0..63 显式窄化；`default: false`
  覆盖其余全部 opcode，非组窗口 orri 不受影响（`ext.so` 用例）。
- `getEncodingValue` 用 HWEncoding（每 bank 0–63）而非枚举 id，避免「枚举相邻 bank
  混读」；判据 `count == 0 || enc + count > 64` 与 spec 两条规则一一对应，不环绕、
  不截断。
- 返回 `Fail` 前不重写 MCInst（合法路径完全不变）；`Size=4` 已在前面设置，objdump
  按 4 字节步进，无死循环/错位。
- 19 条 rrri 与 11 条 orri 的操作数下标逐条核对 def 的 `OutOperandList++InOperandList`
  （rrri: 组首=0、count=3；orri: 组首=0/1、count=2）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 RD/RB/RA 组越界不崩溃、静默打印成 `{rd61:rf0}`/`{rb61:rd0}`/`{ra61:rb0}`（任务只提 rf，属同类根因） | ✅已修 | 解码器判据覆盖全部组 opcode（非只 rf） | lit 三个原始字 → `<unknown>`；pre-fix 快照旧输出即上述假组 |
| F2 `ra.s` 把非法编码（`0x40BBFFFF`，63+63>64）的跨 bank 打印钉成 expected ⇒ `check-lit` 红 | ✅已修 | 两处 `OBJ:` 期望改 `<unknown>`（`0x3C000000` count=0、`0x40BBFFFF`），原始字未动 | `llvm-lit …/MC/DADAO` 90/90；`make check-lit` 183/183 |
| F3 证据脚本把 check-patch-tree 的成功行也算进 llvm problem | ✅已修 | bad 计数过滤 ` patch(es)$` | run2 `llvm_bad=0 llvm_ok_report=1` |
| F4 合法组基线比对因 objdump 头行绝对/相对路径差异假红 | ✅已修 | 以 `cwd=$WORK` + 相对文件名运行 | `legal_groups_vs_pre_fix_golden` 0 diff 行 |
| F5 opcode 白名单漂移（将来新增组指令漏加） | ⏸延后 | 代码注释写明新增组指令须同步；本次白名单与 spec `mreg_zero` 清单逐条一致 | 19 rrri + 11 orri = spec 清单；`check-instrinfo` 0 error |
| F6 是否连带拒绝 `immu6 == 0`（任务只要求越界） | ✅已做 | `Count == 0` 一并拒绝（spec 同为 ILLI） | `ra.s` `0x3C000000` → `<unknown>`；合法输出无变化 |
| F7 其它消费方一致性（`llvm-mc -disassemble`） | ✅已验证 | 无额外代码 | 非法字 → `warning: invalid instruction encoding`（rc=0，不崩溃）；count=9 对照正常打印 |

#### 第 1 轮 reviewer 验收

**判决：Accepted**（以下全部为我自己的重跑输出，不采信完成区转述）

**重跑记录（均在仓库根执行）**
1. `bash 运行期证据目录内的 run.sh` → `RUNSH_RC=0`，`fails=0 skips=0`；11 项逐项 rc=0：`install_md5_vs_build`（两侧同 `7893b308…`/`ebaad000…`）、`mirror_rf_disasm_rc0`（65/65 ok、0 bad）、`illegal_word_0x3EDC304A`（stable=0、unknown_missing=0）、`legal_groups_vs_pre_fix_golden`（0 diff 行）、`legal_groups_prefix_vs_new_binary`（diff 空）、`lit_new_test_green`（1 PASS）、`inject_prefix_binary_must_fail`（lit rc=1）、`inject_expectation_fail_then_restore`（mut=1/restored=0/md5_eq=yes）、`check_patch_tree_llvm_segment`（llvm_bad=0）、`check_instrinfo`（10 PASS/0 errors）、`make_check_lit`（183 Passed）。
2. 我另写独立循环遍历全部 `tests/inst/**/*_rf.S`（不复用脚本）：`total=65 new_bad=0`；同一批 .o 换 **pre-fix 快照**反汇编 → 恰 **9** 例断言崩溃（`RegNo && RegNo < 258`）= ldm.o/ldm.t/stm.o/stm.t_rrri_rf + rd2rf/rf2rd/rf2rf_orri_rf + focls/ftcls_orri_rf，与 ISS-468 的 9 例逐一对上。
3. 非法字 `0x3EDC304A`/`0x3EFC3042`/`0x3E143040`/`0x38F434C4`/`0x44014F44` 连跑 3 次 `cmp` 全同、stderr 0 字节、rc=0，输出逐字稳定（`3e dc 30 4a  \t<unknown>` 等 5 行）。
4. 合法组夹具（`{rf63}`、`{rf1:rf63}`、`{rf60:rf63}`、`{rf32:rf47}`、`rf2rf`、`ftcls`、`ext.so`）：pre-fix 快照 vs 新二进制 `diff` rc=0（0 行）；另核 golden 与 pre-fix 快照输出逐字相同（基线非同源自比）。
5. `make check-lit` → `Passed: 183 (100.00%)`，`CHECKLIT_RC=0`；`make check-instrinfo` → `Result: 0 errors` rc=0；`check-patch-tree` → `llvm-project: 99 patch(es)`、llvm 段 0 problem、`pt_rc=1`，21 problem 全在 qemu(7)/linux(12)/musl(2)，本任务 5 文件 diff 与这些组件无关 ⇒ 按分段披露为在途共享源树漂移（ISS-463 同族）。
6. `series` = 99 行；安装根与构建树 `llvm-objdump`/`llvm-mc` md5 各自一致，我重建两次后 md5 复原同值（重建确定性 ⇒ 未重跑 `install-host`，此项按 md5 证据采信、未亲跑）。

**独立注入（可达 FAIL；`cp`+md5 还原，未用 git checkout）**：备份源文件（md5 `198fccde…`）→ 把 `isInvalidRegGroup` 判据改成 `return false` → 构建树增量重建 → 非法字回到崩溃 `objdump_rc=134`（断言 `RegNo && RegNo < 258`）；同一二进制跑新 lit → `FAIL: DADAO-MC :: rf-group-range.s`、`lit_rc=1`。`cp` 还原后 md5 相等、无注入标记 → 重建 → 两二进制 md5 回 `7893b308…`/`ebaad000…`，`make check-lit` 183/183 回绿。

**实现核验（确在 MC 解码器，非打印机防御）**：改动只有 `DADAODisassembler.cpp.patch` 一份（`git diff --name-only`），打印机补丁未动；`case DADAO::` 共 30 = 19 rrri + 11 orri，与两份 `.td` 中**全部**组窗口指令集合相等（M1 15 rrri + 6 orri、FP 4 rrri + 5 orri），无漏无多；两侧判据 `Count == 0` 与 `getEncodingValue(Start) + Count > 64` 都在，`GroupInvalid` 先验 `isReg`/`isImm`；`ext.so rd61, rd61, 10` 等非组 orri 走 `default`（lit 与我的夹具均原样打印）。

**约束核验**：变更集 = 5 文件（任务书 / changelog / 解码器补丁 / `ra.s` / 新增 `rf-group-range.s`），未触 `spec/`、`.tao/contracts/`、`Makefile`；任务书无运行期/临时/宿主绝对路径；`ra.s` 只改两处 `OBJ:` 与注释，原始字 `0x3c000000`、`0x40BBFFFF` 及 `ASM:` 行未动；`rf-group-range.s` 覆盖 5 非法字 + 4 合法边界 + count=9 对照 + classify 双窗口 + `ext.so` 对照，注入证明确非恒真断言。

**非阻断 finding（交 architect 收尾）**：① 完成区「23 行 KNOWN-RED」我这轮实测 21 problem / 24 行（在途漂移随时间变，非门控期望值）；② 「clang build-id 指向 commit b6caceed2」措辞不准（clang 内嵌 git 哈希与源树 HEAD 确为 `b6caceed2`，build-id 另是一串）；③ 汇编器仍接受跨 bank 文本组 `ra2rd {rd63:rf61}, {ra63:rb61}`（我实测 asm rc=0 → `0x40BBFFFF`），属独立 AsmParser 缺陷、非本任务崩溃源，任务书「新发现 2」已登记但 `issues-m20.yaml` 无对应条目 ⇒ 请立 issue；④ `ISS-468` 条目仍写「修 `getRegisterName` 映射」且 `status: open`，与实际 MC 层修法不一致，收尾时更新。
**待裁定**：无（③④ 由 architect 收尾处置，不阻断本任务）。
