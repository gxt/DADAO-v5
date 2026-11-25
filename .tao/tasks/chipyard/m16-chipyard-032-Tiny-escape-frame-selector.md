# m16-chipyard-032: Tiny 侧 `escape` frame selector（关闭 `DIV-11`）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-026`（cg9 捕获缓冲 R2）、`m16-chipyard-028`（cg9 rc6）
**可并行分片**：否（同 `components/chipyard` 写者）
**预估**：2–4 h
**档位**：中改（RTL 解码 + 探针）
**状态**：待开始

## 背景（`DIV-11`）

`ADR-0061 R2` 与 `spec/DADAO-12 §5.1` 规定 `escape` 的 `imms18 ∈ {0,1,2}`（汇编层 `imms20 ∈ {0,4,8}`）：`imms18[1]=1` 选 `cg9` 现场；`cg9` 是捕获缓冲、不是返回帧 ⇒ 目标为**当前 cfx** 的 `CFXESC`。

Tiny 无 `cfx_hart`（cfx15），`WumingDecoder` 的 `withHart` 门控保留旧 SBZ 规则（`imms18[17:1] ≠ 0 ⇒ ILLI`）⇒ `escape …, 8`（`imms18=2`）在 **Tiny** 上仍报 `ILLI`。`tests/arch/expected-divergences.yaml` 的 `DIV-11`（temporary）记录的正是这条；其 `close_when` = 「放开无 `cfx_hart` 门控，Tiny 按 §5.1 接受 `imms18=2`（因无 cg9 帧 ⇒ `CFXESC`），并补 Tiny 侧编码用例」。

M17 全四方当前 **273/274**，唯一红就是 `tests/inst/11-cfx/escape_ciii_cfx` 的 chipyard（Tiny）`rc=13`；本任务收口后应 274/274。

## 要做

1. `WumingDecoder`/escape 解码：**Tiny 也接受** `imms18 ∈ {0,1,2}`（不再按 `withHart` 拒绝 bit1）；`imms18=2` 时目标为 cg9 现场；Tiny 无 cg9 帧 ⇒ `CFXESC`（当前 cfx）；`imms18=3`/`[17:2] ≠ 0` 仍 `ILLI`；
2. 补 Tiny 侧编码用例（`tests/inst/11-cfx` 或 arch 探针）：`escape …, 8` 在 Tiny 上 ⇒ `CFXESC`（不是 ILLI）、`…, 12` ⇒ ILLI；
3. 关闭 `DIV-11`：删除 `expected-divergences.yaml` 的 `DIV-11` 条目（整条删除，非 skip）；
4. 重跑 M17 全四方（`make check-idl-full`）应 **274/274**；`11-cfx` 全绿；
5. 不改 Vast 的既有 escape 语义；不改 spec/契约；不改 QEMU/gem5/Linux。

## 不做

- 不引入 `cfx_hart` 到 Tiny（无 cfx15）；
- 不改 `cg9` 捕获缓冲的其它语义（归 026/028）。

## 约束

- 独立 `git worktree`；组件补丁按 `docs/Process-01`；不提交 git；
- 只动 chipyard 补丁/RTL、`tests/arch/expected-divergences.yaml`、必要 Tiny 探针、`components/chipyard/{README.md,changelog.md}`、本任务书；完成区 ≤30 行。

## 验证

1. `escape_ciii_cfx` 在 Tiny 上 guest rc=0（不再是 13）；全四方 274/274；
2. **可达 FAIL ≥2 路**：① 恢复 `withHart` 拒绝 bit1 ⇒ 该例红；② `imms18=2` 改成 `CFXESC` 之外的 cause ⇒ 红；`cp`+md5 还原并重建回绿；
3. `DIV-11` 删除后 `grep -c 'id: DIV-11'` = 0；
4. `check-patch-tree` chipyard 段 0 problem；Tiny/Vast 构建 rc=0；`check-component-changelog` rc=0。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
