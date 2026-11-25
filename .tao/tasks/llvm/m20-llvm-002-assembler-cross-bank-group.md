# m20-llvm-002: LLVM 汇编器拒绝跨 bank 文本寄存器组（ISS-m20-001）

**模块**：llvm
**项目里程碑**：M20
**依赖**：`m20-llvm-001`（MC 层拒绝越界组）已合入；同改 `components/llvm-project`，须串行
**可并行分片**：否（单组件补丁 + AsmParser）
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（`m20-llvm-001` 复核新发现，2026-11-25）

`m20-llvm-001` 已在 MC **反汇编层**拒绝越界组编码（`immu6==0` 或
`起始+immu6>64` ⇒ `<unknown>`），但**汇编期**仍接受跨 bank 的文本组：

```
ra2rd {rd63:rf61}, {ra63:rb61}
```

实测 `llvm-mc` rc=0，编码为 `0x40BBFFFF`（immu6=63）；起始 63 + 63 > 64，按
`contract-isa.md §15.1` / `contract-fp.md §15` 应判
`mreg_range_overflow`（ILLI），汇编器不应生成该字。根因：AsmParser 的 count
由寄存器**枚举 id 差值**推导，rd→rf / ra→rb 枚举相邻，差值跨了 bank，绕过了
`mreg_range_overflow`；该路径与反汇编崩溃源（`m20-llvm-001`）不同。

## 目标

1. AsmParser 按组文本解析出**起始寄存器所在 bank** 与个数，按同一 bank 判
   `起始 + 个数 > 64`（不环绕、不截断）和 `个数 == 0`（若文本可表达）；不得使用
   跨 bank 的枚举 id 差值。
2. 非法组在汇编期硬报错（诊断含 `mreg_zero` / `mreg_range_overflow` 语义），
   不得生成 `.o`；合法组（`{rf63:rf63}`、`{rf1:rf63}`、`{rf32:rf47}`、
   `{rd63:rd63}` 等）编码与修复前逐字节一致。
3. 不修改 `m20-llvm-001` 的 MC 反汇编判据；若发现反汇编判据需要同步，写入
   「待裁定」并说明，不自行扩大。
4. 订正 `tools/llvm/test_encoding_oracle.py`：移除把非法跨 bank 文本
   `ra2rd {rd63:rf61}, {ra63:rb61}` 当合法编码的用例（非法原始字只在 lit 用
   `.dd.t32` 钉住，不得由非法文本反推编码），并保持独立 oracle 合法组覆盖不减。

## 验收（逐条贴真实 rc）

1. `llvm-mc` 对 `ra2rd {rd63:rf61}, {ra63:rb61}` 及 RD/RB/RA/RF 各一组跨 bank
   构造均 rc≠0，诊断可读；修复前同命令 rc=0（给出对照）。
2. 合法组 round-trip 抽样 5 例：`llvm-mc` → `llvm-objdump` 输出与 pre-fix 快照
   逐字节一致。
3. 新增/扩展 lit 负例，覆盖跨 bank、起始+count 越界、合法边界；证明可达 FAIL
   （放宽 AsmParser 判据 ⇒ 负例回红；`cp`+md5 还原后回绿）。
4. `make check-lit`、`check-instrinfo`、`check-patch-tree` 的 llvm 段 0 problem；
   按 `docs/Process-01` 重导补丁序列，`series` 数按实际（不得为过门控改数）。
5. 重建/安装按仓库纪律执行；记录 `llvm-mc` 与安装根 md5 一致；不写具体构建/临时路径。
6. `python3 tools/llvm/test_encoding_oracle.py` rc=0 且 `passed == total`；合法组
   覆盖计数现场统计、不低于订正前（124）；期望值注入 ⇒ FAIL、`cp`+md5 还原 ⇒ 回绿。

## 约束

独立 `git worktree`（分支 = `m20-llvm-002`）；不提交 git；只改
`components/llvm-project/**`、对应 lit 用例、`tools/llvm/test_encoding_oracle.py`
（主会话 2026-11-25 裁定纳入）与本任务书；不改 `spec/`、契约、`Makefile`。
证据落在「运行期证据目录内的 `run.sh`」。术语：bank = **寄存器组**。

## 完成区

**测试结果**：`make check-lit` 184/184 PASS（rc=0，含新增 lit）；`check-instrinfo` 10 PASS/0 errors（rc=0）；`test_encoding_oracle.py` 124/124 passed、0 failed（rc=0）；证据脚本默认模式 `fails=0 skips=1`（rc=0）、`--inject` 模式 `fails=0 skips=0`（rc=0）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（重导出，+62/−24 行补丁文本，`series` 99 不变）；`components/llvm-project/changelog.md`（M20 一条）；`tests/unit/llvm/lit/MC/DADAO/reg-group-bank.s`（新增）；`tests/unit/llvm/lit/MC/DADAO/ra.s`（`0x40BBFFFF` 改用 `.dd.t32` 钉住）；`tools/llvm/test_encoding_oracle.py`（非法文本用例改为合法边界；另订正 5 个 M1 后失效用例；124/124）；本任务书。
**验收结果**：
1. pre-fix 快照 3/3 接受（`ra2rd {rd63:rf61}, {ra63:rb61}`→`0x40BBFFFF`、`ldm.o {rd63:rf61}`→`0x38FC103F`、`ldm.o {ra63:rb61}`→`0x3CFC103F`，rc=0，bug 复现）；新汇编器对 RD/RF/RB/RA 起始的 5 条跨 bank 构造 5/5 rc≠0、诊断含 `mreg_range_overflow`、不生成 `.o`；`{rd0:rd63}`（count 64）与 `end < start` 仍拒。
2. 合法组抽样（fixture 6 组：`{rf63}`、`{rf1:rf63}`、`{rf32:rf47}`、`ra2rd`、`rd2ra`、`rf2rf`；lit 另含 `{rd0:rd62}`）：产物与 pre-fix `.o` `cmp` 相同（0 差异），`llvm-objdump` 反汇编 diff 0 行。
3. 新 lit 负例覆盖跨 bank 5 组、count 64 两组、`end < start` 与合法边界 5 组。可达 FAIL：pre-fix 快照跑新 lit ⇒ rc=1；放宽判据（恢复旧枚举差值 + `Count > 64`）重建 ⇒ 合法组仍过、首个跨 bank 负例被接受 ⇒ lit rc=1；`cp`+md5 还原（md5 相等）+ 重建 ⇒ lit rc=0。
4. `check-patch-tree` llvm 段 `99 patch(es)`、0 problem（整库 rc=1 = 其它组件 KNOWN-RED，在途任务，本轮 19–21 行漂移）；`--source-state` llvm OK（HEAD=033d3cffa、count=1、clean）。
5. 安装根与构建树 `llvm-mc` md5 同为 `9394cd5f36db37461ba2d6320e5da0ac`、`llvm-objdump` 同为 `f833779cfe97172ce8016694010dfd09`；`make build-mc`/`make install-host` rc=0（`install-host` 等待 gate 锁后串行完成）。
6. `tools/llvm/test_encoding_oracle.py`：124 passed / 0 failed（rc=0，计数 = 订正前 124，未减）；非法文本条改为合法边界 `ra2rd {rd0:rd62}, {ra1:ra63}`（双侧 count 63，期望 `0x40B8007F` 由 opcodes 字段独立算出）；期望值注入（`ha 0x2E→0x2F`）⇒ rc=1 且 `FAIL: ra2rd …` 命中，`cp`+md5 还原 ⇒ md5 相等、rc=0。
证据：运行期证据目录内 `run.sh`（默认/`--inject`），日志与注入 diff 在运行期日志目录。
**新发现/坑**：
1. 枚举顺序为 rd,rf,ra,rb；修复前只有「rd→rf」「ra→rb」方向的跨 bank 文本组被静默接受（计数 `65+(end−start)`），rb/rf 起始的跨 bank 文本碰巧报 `end<start`/`too large`，两者都不是 bank 判据。
2. oracle 不止本修复一条失效：`ext.uo ...` 的 `ha` 已由 0x18 改为 0x28；`cs.eq/cs.ne` 的 `_rrrr_rf` 形式已从 ISA 删除（改用 RD 形式 0x66/0x67）；`ftsclb`/`fosclb` 的第三操作数是 RD 不是 RF。均按 `contracts/opcodes.yaml` 独立派生订正，未从 llvm-mc 反读期望。
3. `make_patch.py`/`check_patch_tree.py` 的 ROOT 取 `__file__`：必须以本 worktree 相对路径调用，绝对路径会读到主工作树（本轮一次误读，已按相对路径复跑）。
4. `count == 0` 文本不可表达（单寄存器=1、range 要求 end≥start）⇒ `mreg_zero` 仍只在解码侧判（`m20-llvm-001` 未改）。
5. oracle 末尾的 lit 覆盖 cross-check 仍指向 M1 布局 `tests/lit/MC/Dadao`（现为 0），判据空转；不在本任务裁定范围，保留未改。
**遗留问题**：oracle 的 lit 覆盖 cross-check 路径过期（空转），建议另立小任务按 `tests/unit/llvm/lit/MC/DADAO` 重定义或删除。未跑 L2 `check-modules`（任务验收未要求）。
**已裁定（主会话 2026-11-25）**：允许把 `tools/llvm/test_encoding_oracle.py` 纳入本任务同一变更（已订正，rc=0）。

## 审阅记录

#### 第 1 轮 engineer 自审

**结论**：改动集中在 `parseRegGroup` 的组计数判据（bank 判据 + bank 内编码计数），所有 finding 已处置，状态可置「待验收」。

逐行审查要点（无 finding）：`regGroupBank` 只认四个 bank 的枚举区间；`getEncodingValue` 每个 bank 返回 0..63（与 `m20-llvm-001` 解码侧同一取法）；跨 bank 判据在计数之前返回，`end < start` 保留；`Count == 0` 文本不可达已在注释与任务书说明；移动的 4 个 bank 谓词是纯移动，伪指令展开与 `m20-llvm-001` 判据未受影响（本任务变更集里只有 `AsmParser.cpp.patch` 被重写，`Disassembler.cpp.patch` 未出现在 `git status`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本临时目录用 `${TMPDIR:-/tmp}`，违反 AGENTS §8 | ✅已修 | 改用 `/tmp/opencode/m20-llvm-002/ev.*` | `--inject` 两轮 rc=0，残留目录 0 |
| F2 合法组反汇编比对因两侧文件名不同（`legal_pre_fix.o` vs `legal.o`）假红 | ✅已修 | 基线改用同名 `legal.o` 重生成；对象 `cmp` 保留为主证据 | 默认/注入两轮 `obj=0 dis=0` |
| F3 注入最初只放宽 bank 判据、未恢复旧 `Count>64` ⇒ 合法组也被拒，红因不纯 | ✅已修 | 注入同时恢复枚举差值与 `Count > 64` | 注入 lit：合法组 RUN 过、首个跨 bank 负例被接受 ⇒ rc=1 |
| F4 `StartIdx + Count > 64` 对同 bank 的 6 位编码不可达 | ⏸保留（防御） | 作为合同字面判据保留；count 64 的真实拦截在既有 mnemonics 级检查 | ERR-CNT 两例通过；注入改回 `Count>64` 后 count64 仍拒 |
| F5 `tools/llvm/test_encoding_oracle.py` 失效（范围外） | ⏸延后 | 未改 | 记入「新发现 2」/待裁定 |
| F6 移动 4 个 bank 谓词可能影响伪指令展开 | ✅已做 | 纯移动，两处共用 | 编译通过、`make check-lit` 184/184 |

#### 第 2 轮 engineer 自审（oracle 纳入同一变更；主会话 2026-11-25 裁定）

**结论**：第 1 轮 F5 由裁定转为「已修」；oracle 124/124 rc=0，注入可达 FAIL 且还原回绿；
状态保持「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| G1 第 1 轮 F5：oracle 把非法文本当合法编码 | ✅已修（按裁定纳入） | 该条改为合法边界 `ra2rd {rd0:rd62}, {ra1:ra63}`（双侧 count 63），期望 `0x40B8007F` 由 opcodes 字段独立算出；非法字只在 lit 用 `.dd.t32` 钉住 | oracle `124 passed, 0 failed`（rc=0）；lit `ra.s`/`reg-group-bank.s` |
| G2 oracle 另有 5 个 M1 后失效用例（不订正则 rc≠0） | ✅已修 | `ext.uo` ha 0x18→0x28；`cs.eq`/`cs.ne` 改 RD 形式（0x66/0x67，rf 形式已删）；`ftsclb`/`fosclb` 第三操作数 rf8→rd8（opcodes 为 rdhd） | 5 条单测均 OK；总 `124/124` |
| G3 非法文本反推编码（禁用做法） | ✅已修 | 已移除；oracle 只从 spec/opcodes 派生期望 | 注入期望值仍能 FAIL（见 G4），非恒真 |
| G4 oracle 可达 FAIL | ✅已验证 | `--inject` 注入 `ha 0x2E→0x2F` | oracle rc=1 且 `FAIL: ra2rd …` 命中；`cp`+md5 还原 ⇒ md5 相等、rc=0 |
| G5 oracle 末尾 lit 覆盖 cross-check 路径仍是 M1 布局（空转） | ⏸延后 | 未改（不在裁定范围，改动会牵出判据重定义） | 记入「遗留问题」 |

#### 第 1 轮 reviewer 验收（2026-11-25，reviewer 独立重跑）

**判决：Accepted**（验收命令块全部由我重跑通过；硬约束逐条核验无违反；未改任何实现）

**重跑记录（均在仓库根、相对路径执行，贴真实 rc）**
1. 运行期证据目录内 `run.sh --inject` → **rc=0，`fails=0 skips=0`**：安装根/构建树 `llvm-mc` md5 `9394cd5f…`=`9394cd5f…`、`llvm-objdump` `f833779c…`=`f833779c…`；pre-fix 快照 3/3 接受（`0x40BBFFFF`/`0x38FC103F`/`0x3CFC103F`）；跨 bank 5/5 `rc≠0 + mreg_range_overflow + 无 .o`；count64 `rc=1`；`end<start` `rc=1`；合法组 `obj cmp=0 dis=0`；新 lit PASS；oracle `124 passed, 0 failed`；pre-fix 二进制跑新 lit `rc=1`；脚本注入 `build=0 lit=1` → 还原 md5 相等 `lit=0`；oracle 注入 `rc=1` → 还原 `rc=0`；`check-instrinfo` `0 errors`；`check-patch-tree` llvm `99 patch(es)` 0 problem（整库 `rc=1`，14 problem 全在 linux/musl，他任务 KNOWN-RED）；`make check-lit` `184/184 rc=0`。
2. 我独立复现 pre-fix：证据目录 pre-fix `llvm-mc` 对 `ra2rd {rd63:rf61}, {ra63:rb61}` / `ldm.o {rd63:rf61}` / `ldm.o {ra63:rb61}` **rc=0** 且编码同上；现行 `llvm-mc` 三条 **rc=1**、诊断含 `mreg_range_overflow`、`-o x.o` 后**无 `.o` 文件**；RB/RF 起始跨组（`{rb63:ra61}`、`{rf63:ra0}`）由旧的 `end < start`/`range too large` 统一为 bank 诊断；`{rd0:rd63}`（count 64）`rc=1`（mnemonic 级 `mreg_range_overflow`）；`{rd5:rd3}` `rc=1 end < start`。
3. 合法组：fixture 6 组 + 我追加 5 组（`{rd0:rd62}`、`{rd63:rd63}`、`{ra0:ra62}`、`{rb31:rb32}`、`{rf0:rf1}`）pre-fix 与现行 `.o` md5 同为 `4396ee46…`（逐字节一致），`llvm-objdump` 仅输出文件名行不同。
4. 门控我本人重跑：`make check-lit` `rc=0` `Total 184 / Passed 184`；`make check-instrinfo` `rc=0` `Result: 0 errors`；`tools/infra/check_patch_tree.py` llvm 段 0 problem；`python3 tools/llvm/test_encoding_oracle.py` `rc=0` `124 passed, 0 failed`；`make check-knowledge-refs` `rc=0 PASS`。

**补丁与订正核验**
- `DADAOAsmParser.cpp.patch`：`regGroupBank` 判起止同组，`MRI->getEncodingValue` 取组内 0..63 计 count，判 `StartIdx + Count > 64`；已应用源树中无 `First.id() - DADAO::rd0` 差值路径（grep 0 命中）；`Disassembler.cpp.patch` 不在变更集 ⇒ `m20-llvm-001` MC 反汇编判据未改。
- oracle 5 处订正**逐条对 `contracts/opcodes.yaml` 独立核对**（非 llvm-mc 反读）：`ext.uo_orri_rd` ha `0x28`（value `0x40A00000`）；`cs.eq_rrrr_rd`/`cs.ne_rrrr_rd` opc `0x66`/`0x67` 且 yaml 中无 `_rf` 记录；`ftsclb_orrr_rf`/`fosclb_orrr_rf` 第三字段 `rdhd`（bank rd）⇒ 第三操作数 `rd8`。
- 覆盖未减：HEAD 与工作树 `TESTS` 均 **124 条、组语法 48 条**（现场统计）；非法文本用例已删，改合法边界 `ra2rd {rd0:rd62}, {ra1:ra63}`，期望 `0x40B8007F` 由 `ra2rd_orri_ra`（value `0x40B80000`）字段独立算出。

**独立注入（我设计；`cp`+md5 还原，未用 git checkout）**
- 注入 A（放宽 AsmParser）：bank 判据改 `StartBank / 2 != EndBank / 2`（rd≡rf、ra≡rb）+ 计数回退枚举差值 + `Count > 64`，重建 10 s 后三条跨 bank 文本 **rc=0** 并复现 `0x40BBFFFF`/`0x38FC103F`/`0x3CFC103F`，新 lit `reg-group-bank.s` **rc=1 FAILED**；`cp` 还原后源文件 md5 `0feb1613…` 相等、重建 lit **rc=0**、安装根/构建树 md5 复归 `9394cd5f…`/`f833779c…`。
- 注入 B（改 oracle 期望）：`ext.uo` ha `0x28→0x27` ⇒ **rc=1**、`FAIL: ext.uo rd8, rd0, 1`、`123/124`；`cp` 还原 md5 `acdb5f3c…` 相等 ⇒ **rc=0 `124/124`**。

**范围核验**：验收前后 `git status --porcelain -uall` 快照一致，仅任务书、`components/llvm-project/{changelog.md,patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch}`、`tests/unit/llvm/lit/MC/DADAO/{ra.s,reg-group-bank.s}`、`tools/llvm/test_encoding_oracle.py`；`spec/`、契约、`Makefile` 改动 0；`components/llvm-project/series` 99 行未改；五个跟踪文件 md5 前后不变（`2d7ba3e7…`/`bc006925…`/`fdee777e…`/`acdb5f3c…`）。注入只作用于运行期源树，`cp`+md5 对账还原相等。

**遗留（不阻断）**：① oracle 末尾 lit 覆盖 cross-check 仍指向旧布局（现场计数 0、判据空转），建议另立小任务按 `tests/unit/llvm/lit/MC/DADAO` 重定义或删除；② `check-patch-tree` 整库 rc=1 为 linux/musl 14 处他任务漂移（KNOWN-RED）；③ 未跑 L2 `check-modules`（验收未要求）。无「待裁定」项。
