# m12-spec-001: 机器命名定稿 `Tiny` / `Vast`（spec + contracts + docs）

**模块**：spec
**项目里程碑**：M12
**类型**：task
**状态**：待开始

## 用户裁定（原话）

- 「同意用dadao-tiny/dadao-node」→ 后续修正为：「dadao-vast，B」
- 「ADR可以不改」「可以，授权」（spec 改名 + 同笔更新锁）「可以」（契约命令行示例）

## 目标（范围 B：profile 与机器名一次改到位）

把 `Node` 统一改名为 **`Vast`**，机器名为 `dadao-tiny` / `dadao-vast`：

1. `spec/Machine-v5-测试机运行环境.md`
   - `profile` 概念 `Tiny`/`Node` → `Tiny`/`Vast`（约 22 处，含 §1.1 表与正文）
   - 定位行里的机器名 `dadao-m1` → `dadao-tiny` / `dadao-vast`
   - 文末附录**新开 `0.4.1-rc（未发布）` 段**，条目只写「profile 与机器命名：Node→Vast、dadao-m1→dadao-tiny/dadao-vast（语义不变）」；册头状态行版本同步 `0.4.1-rc`
   - 同笔更新 `manifests/spec-readonly.lock.toml` 的 sha256
2. `.tao/contracts/contract-elf.md`（7 处）、`contract-see.md`（5 处）、`contract-syscall.md`（1 处 + 命令行示例）：`Node`→`Vast`、`-M dadao-m1`→`-M dadao-tiny`；`contract-elf` 两处 `-machine dadao-m1` 示例改 `dadao-tiny`
3. `spec/README.md`（索引措辞）、`docs/Machine-00-执行环境分层-Draft.md`（2 处）
4. **不改**：`.tao/adr/**`（历史，用户裁定不改）、历史任务书、组件 changelog、`components/**`

## 范围 / 非范围

**在范围内**：上述 spec/contracts/docs + 锁文件 + 本任务书 + `milestones-m12.md`。

**不在范围**：qemu 代码与测试（`m12-qemu-00x`）、`tests/shared/machine-profiles.yaml` 与生成 `.inc`（属 qemu-002）。

## 验收标准

1. `make check-spec-readonly` rc=0（锁与新内容一致，其余 20 册哈希不变）
2. `make check-spec-changelog` rc=0（`0.4.1-rc` 段在首、册头一致、逆序）
3. `make check-spec-drift` rc=0
4. `grep -rn 'Node' spec/Machine-v5-测试机运行环境.md` 在 profile 语境下 **0 命中**（"node" 其它语义如节点机需人工确认）
5. `grep -rn 'dadao-m1' spec/ .tao/contracts/ docs/` 为 0
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 说明

- 这是**规范文字变更**（命名），不改变 Tiny/Vast 的几何或语义
- 只读册纪律：改册 + 锁必须同笔；授权原话已在本任务书顶部
