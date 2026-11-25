# m20-testcases-003: `stm.t`/`stm.w` 补 `immu6=63` 边界 + rf0 源注释（ISS-m20-002）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m18-testcases-002`（同改 `tests/case-ledger.tsv` 与 `tests/data/inst-signature/expected.tsv`）合入后再派；或由主会话另行裁定串行窗口
**可并行分片**：否（共享 case-ledger/signature 生成物）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

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
