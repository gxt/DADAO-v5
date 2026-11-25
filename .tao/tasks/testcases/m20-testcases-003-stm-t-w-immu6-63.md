# m20-testcases-003: `stm.t`/`stm.w` 补 `immu6=63` 边界 + rf0 源注释（ISS-m20-002）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m18-testcases-002`（同改 `tests/case-ledger.tsv` 与 `tests/data/inst-signature/expected.tsv`）合入后再派；或由主会话另行裁定串行窗口
**可并行分片**：否（共享 case-ledger/signature 生成物）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（用户 2026-11-25 指出，M20 分诊）

1. `stm.t`/`stm.w` 的 `immu6=63` 边界缺失。现场统计：
   - `stm.b_rrri_rd`、`stm.o_rrri_{rd,rf,ra,rb}` 已有 `immu6=63`（`m17-testcases-006`）；
   - `stm.t_rrri_rd`、`stm.t_rrri_rf`、`stm.w_rrri_rd` 均无 63 例。
2. `stm.t_rrri_rf.S` 的 rf0 源注释只说 FCSR 字段，未明确“读出完整 64 位”；按
   `SimRISC-01` 的 rf0 源注（“rf0 作源读出完整 64 位”）和 `stm.t` 只存低 32 位，
   注释应同时写清“源读 64 位 / 本指令存低 32 位”。
3. RD 注释“读出 0/当前指令地址”已在 `m17-testcases-006`（`b69347fc`）修正为
   “读出 0”，当前 master 不再有该错误；本任务只需复核、不重复改。

## 目标

1. 三个文件各补 **1 个 `immu6=63` 链例**：
   - `stm.t_rrri_rd.S`：源组 `{rd1:rd63}`，从 `MUNI` 预装（`ldm.ut`），
     `stm.t` 落 `MSTORE`；检查首 / 中 / 尾数据单元，以及下一数据单元未被写。
   - `stm.t_rrri_rf.S`：源组 `{rf1:rf63}`，从 `MUNI` 预装（`ldm.t`），
     `stm.t` 落 `MSTORE`；同样检查首 / 中 / 尾 + 下一单元。
   - `stm.w_rrri_rd.S`：源组 `{rd1:rd63}`，从 `MUNI` 预装（`ldm.uw`），
     `stm.w` 落 `MSTORE`；按 16 位元素布局检查首 / 中 / 尾 + 下一单元。
   - 期望值必须由 `MUNI` 字面量（`0x0F1E2D3C4B5A6978`）和 `ldm`/`stm` 宽度
     独立派生，不得从 QEMU/gem5 实测反推。
2. 修正 `stm.t_rrri_rf.S` 第 5 行注释为「rf0 作源读出完整 64 位 FCSR 值（列出位域），
   本指令只存低 32 位」；如 `stm.o_rrri_rf.S` 同句也需同步，按最小一致性处理。
3. 更新链例点号、`tests/case-ledger.tsv` 与 `tests/data/inst-signature/expected.tsv`
   （及 `inputs.sha256`）必须由生成器产出，禁手改；`check-case-ledger`/`check-inst-asm`
   必须全绿。

## 验收（逐条贴真实 rc）

1. 三个文件各出现恰 1 个 `immu6=63` 链例；链例点号连续，故障例点号随之后移且连续。
2. 63 例的首/中/尾与“下一单元未写”检查均可达 FAIL（至少注入 1 处期望错误回红，`cp`+md5 还原后回绿）。
3. `make check-inst-asm`（镜像数不变、链例数增加）、`check-case-ledger`、`check-tests-index`
   真 rc；签名期望由生成器同步，diff 可解释。
4. `grep` 复核三个文件不再有“0/当前指令地址”旧注释；rf0 注释明确“完整 64 位 / 只存低 32 位”。
5. `check-patch-tree` 若总 rc 受在途任务影响，按「本任务未触碰组件补丁」披露。

## 约束

独立 `git worktree`（分支 = `m20-testcases-003`）；不提交 git；只改上述三个 `.S`、
生成的 ledger/signature 数据与本任务书；不改 `spec/`、契约、`components/**`、`Makefile`。
证据落在「运行期证据目录内的 `run.sh`」；不写具体构建/临时路径。
注意：`m18-testcases-002` 正在改同一组 ledger/signature 文件，**必须等其合入**或由主会话
明确分配串行窗口后再动，禁止并行写。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` ⇒ ALL PASS（rc=0，含 4 路注入红→`cp`+md5 还原→回绿）。`make check-inst-asm` 274/274 镜像 rc=0（632 例）；`make check-idl` 274/274 四方一致 rc=0；`check-case-ledger` rc=0（现场 5750 条）；`check-tests-index` rc=0（504 条）；签名 `--data-only` rc=0（274 镜像 / 4576 槽）。
**修改文件**：`tests/inst/01-load-store/stm.t_rrri_rd.S`、`stm.t_rrri_rf.S`、`stm.w_rrri_rd.S`（各 +4 检查点）；生成物 `tests/case-ledger.tsv`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`（生成器重写）；本任务书。
**验收结果**：链例点号 21→25 / 14→18 / 18→22，故障例顺延 22-28→26-32 / 15-22→19-26 / 19-25→23-29，全链 1..N 连续（扫描器 `pts_ok`）；槽数 4564→4576（+12），镜像仍 274。注入：错期望 ⇒ 点 24 红；63→62 ⇒ 点 24 红；模拟第 64 元素被写 ⇒ 点 25 红；点号跳号 ⇒ 结构检查红；均 md5 还原后回绿。三文件无「0/当前指令地址」旧说法；rf0 注释含「完整 64 位」+「只存低 32 位」。
**新发现/坑**：① MUNI 的 32 位元素在数据单元内 0x0F1E2D3C/0x4B5A6978 交替，63 例首/中单元整单元同 MUNI 值，尾单元只覆盖半/前 6 B（t: 高 4 B、w: 前 6 B），下一单元保持 MSTORE 模式。② 基线 `check-case-ledger` 与签名 `inputs.sha256` 在 HEAD 即为红（lit 缺 13/多 1；11-cfx 两文件哈希陈旧，均由既有 M20 提交遗留），本次生成器重写顺带修正 —— 已在证据脚本单列披露。③ `check-patch-tree` rc=2，24 problem 全在 gem5/musl 的在途组件树，本任务变更集不含 `components/`、`manifests/`。
**遗留问题**：`stm.o_rrri_rf.S` 的「完整 64 位」可读性同步未做（任务约束/派单只允许三个 `.S`；该行现有「读出 FCSR」无宽度错误表述）——如需统一措辞另立任务。`check-patch-tree` 红由在途组件任务处置。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 63 例覆盖面（首/中/尾/下一单元）与期望值正确性 | ✅已修 | 每文件 4 检查点，期望由 MUNI 字面量 + 宽度独立重算 | 结构检查 PASS；QEMU 三镜像 PASS；injA/B/D 各自点红 |
| 63 例覆盖 MSTORE 前序已写区、尾单元依赖前序状态 | ✅不修（确认无害） | 尾单元 0x0F8/0x078 与下一单元 0x100/0x080 前序均未写过；检查点顺序执行且签名先记 | 独立推导 + 274/274 QEMU 绿 |
| 草稿注释「半数据单元」「最后一个已写元素所在的 6 B」语义含糊 | ✅已修 | 改为「高 4 B = 第 63 个元素」「前 6 B = 3 个元素」 | 文件 diff 复核 |
| `stm.o_rrri_rf.S` 同句未同步「完整 64 位」 | ❌不修 | 约束与派单只允许三个 `.S`；该句无宽度错误 | 变更集范围检查 PASS（仅允许清单） |
| 生成物基线漂移（lit 模式 + 11-cfx 哈希） | ✅已修（生成器） | 重跑两个生成器，不手改 | 基线 pristine 复现红；重生成后 `check-case-ledger`/`--data-only` rc=0 |
| `check-patch-tree` rc=2 | ⏸延后 | 非本任务；变更集未触碰组件/清单 | `git diff --name-only HEAD` ∩ `components/|manifests/` = 0 |

#### 第 1 轮 reviewer 验收

**重跑记录**（全部由 reviewer 在任务 worktree 亲自执行，rc = 真实退出码）：
- `make check-case-ledger` ⇒ **rc=0**，现场身份 5750 条（asm 5208 / lit 542）。
- `make check-tests-index` ⇒ **rc=0**，PASS（504 条）。
- `python3 tools/testcases/inst/check_inst_sig.py --data-only` ⇒ **rc=0**，274 镜像 / 4576 槽。
- `make check-inst-asm` ⇒ **rc=0**，274/274 镜像通过（链例+故障链 632 例，0 FAIL）；三镜像 PASS 且检查点 25 / 18 / 22。
- `make check-idl` ⇒ **rc=0**，274/274 四方一致（parties=idl,qemu）。
- 运行期证据目录内 `run.sh` ⇒ **rc=0，ALL PASS**（32 条 PASS，含其 4 路注入红→还原→回绿）。
- `make check-patch-tree` ⇒ **rc=2**，24 problem 全在 gem5/musl 组件源树（在途组件任务）；本任务变更集与 `components/`、`manifests/` 交集现场计数 = 0 ⇒ 按任务书披露，非本任务阻断。

**生成物 diff 归因**：两个生成器各重跑一次 `--write`，三个生成物 md5 逐字节不变 ⇒ 确为生成器产出、非手改。case-ledger 除本任务 12 个新槽外的附带 diff 逐条核对为「生成器对 HEAD 既有状态的同步」：
① `ra.s` 行 `40bbffff` 删除 —— 该非法字在 HEAD 的 `ra.s` 已不存在（现场 grep rc=1），系 m20-llvm-001/002（均为 HEAD 祖先）移出；HEAD 账本仍有该行 1 处。
② `reg-group-bank.s` / `rf-group-range.s` 共 13 条 lit 新行 —— 两文件为上述两提交合入的新用例，HEAD 账本 0 命中；词表由 `@@ OBJ:` 字节派生。
③ `inputs.sha256` 两处 11-cfx 哈希 —— 现场 `sha256sum` 与新值逐字节相等（旧值为 HEAD 陈旧项）。
上述语料文件本任务均未改（变更集恰 7 文件）⇒ 属同步、非手改/漂移。

**独立注入**（禁 `git checkout`，`cp` 备份 + md5 对账）：
- `stm.w_rrri_rd.S` 尾期望 `…00AF`→`…00AE` ⇒ 单镜像 rc=1、FAIL 点 21；还原 md5 一致，重跑 rc=0 PASS。
- `stm.t_rrri_rf.S` `stm.t {rf1:rf63}`→`{rf1:rf62}` ⇒ rc=1、FAIL 点 17；还原 md5 一致，重跑 rc=0 PASS。
- `stm.t_rrri_rd.S` 在 63 例后额外写 `MSTORE+0x100` ⇒ rc=1、FAIL 点 25（下一单元被写可达）；还原 md5 一致，重跑 rc=0 PASS。

**结构/注释（本人重跑）**：三文件 `immu6=63` 段各 1；点号 1..32 / 1..26 / 1..29 连续无重号（现场扫描），故障例顺延 26–32 / 19–26 / 23–29（7/8/7 条）。首/中/尾+下一单元期望由 `MUNI=0x0F1E2D3C4B5A6978` 与 4/2 B 元素宽度独立重算（大端落盘、MSTORE = `0xC0DE0000000000A0+i`）：t 尾 `0x0F1E2D3C000000BF`、下一单元 `…C0`；w 尾 `0x0F1E2D3C4B5A00AF`、下一单元 `…B0` —— 与文件逐值一致，非实测反推。三文件 grep `0/当前指令地址` 命中 0（rc=1）；`stm.t_rrri_rf.S` 第 5 行含「完整 64 位」+「只存低 32 位」。

**快照对账**：验收前后 `git status --porcelain -uall` 同为 7 行（三 `.S` + 三生成物 + 本任务书），六个交付文件 md5 前后逐一相等；未提交 git、未改实现。

**判决：Accepted**（验收命令块在我本人重跑下全绿、约束无违反；最终接受由架构师终审）。

**遗留/finding（非阻断）**：① 三文件注释「0x100 / 0x080 = 第 64 个元素」编号口径不一（该处实为 i=64 即第 65 个元素；第 64 个元素 i=63 落在尾单元内、其「未写」已由尾单元低半检查覆盖）—— 文档级措辞，断言值本身正确，请架构师收尾时顺手改；② `stm.o_rrri_rf.S`「完整 64 位」措辞同步未做（派单只允许三个 `.S`）；③ `check-patch-tree` rc=2 由在途组件任务处置。
