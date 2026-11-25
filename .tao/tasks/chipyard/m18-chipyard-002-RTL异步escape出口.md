# m18-chipyard-002: RTL 实现异步 escape 出口（cg5 rc8–rc11、cg9 新布局）

**模块**：chipyard
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入）、`m18-llvm-002`（汇编/编码）、`m18-testcases-004`（向量）；**须等 M16 当前 chipyard 批次释放写者窗口**（同 `components/chipyard`）
**可并行分片**：否
**预估**：4–6 h（标定：同档 chipyard-026 2–3 h；本任务含跨 cfx mask 读写与 escape 重写，取 2×）
**档位**：大改（RTL 异常进入/退出）
**状态**：待开始
**执行环境**：本地（chipyard `WumingTiny/Vast`）

## 背景

`m18-spec-007`/`ADR-0061 R3` 把出口改为 `cg5 rc8`–`rc11` + `escape cfxHA`，`cg9` 重排（`rc0`–`rc4`、`rc14`/`rc15`），`cg0`–`cg3` 的 switch/vector 改 `rc14`/`rc15`。RTL 仍是 R2：`switchMode`/`vector` 在 `rc8`/`rc10`、`cg5 rc0/1/3` 可写、无出口意图字段、`escape` 带偏移。

## 目标

1. **寄存器面**：`cg5 rc0`–`rc3` 只读（写 ⇒ `CFXREG`）；`rc4/rc5` cause id/info；删 `pending`；`rc8`–`rc11` 出口意图（进入时硬件复制，`rc11` 复位全 1）；`cg9` `rc0`–`rc4` 只读、`rc5` pending、`rc14` switch、`rc15` vector；`cg0`–`cg3` 的 switch→`rc14`、vector→`rc15`，旧 `rc8`/`rc10` ⇒ `CFXREG`。
2. **进入**：同步（含 `trap`）写目标 cfx `cg5 rc0`–`rc5` + `rc8`–`rc11`；异步写 `cg9 rc0`–`rc4` + hart `cg5 rc8`–`rc11`（不写 hart `cg5 rc0`–`rc3`）。
3. **`escape`**：`imms18` 必须 0（非 0 ⇒ `ILLI`）；`cfxha` = 当前 cfx（否则 `CFXESC`）；目标模式不得升权（`CFXESC`）；目标 cfx 未实现/无 monitor ⇒ `CFXESC`；跳 `rc10`；`rc11` 整字写目标模式 monitor `cg8 rc1`，与切换/跳转同一状态转换；`escape_num` +1。
4. **跨 cfx 读写**：进入时读“被打断模式 monitor 的 `cg8 rc1`”填 `rc11`；`escape` 时写目标 monitor 的 `cg8 rc1`——新增 mux/写口，须给时序与资源评估。
5. **生成物/断言**：受 opcodes 影响的 decode 断言重生成；`check-qemu-forms`/`check-legality-drift` 一致；`expected-divergences` 只增删必要项。
6. **不做**：不改 QEMU/gem5/IDL/LLVM/内核/spec。

## 验收（逐条贴真实 rc）

1. `make verilog` + sim 构建 rc=0、`%Error`=0；sim md5 记录。
2. 向量（`m18-testcases-004`）在 Vast/Tiny 上可跑的条目通过；`rc11` 整字恢复、升权 `CFXESC`、非 0 `imms18` `ILLI`、未实现目标 `CFXESC`。
3. 与 QEMU 同 ELF 签名逐字节一致；不一致登记 `expected-divergences.yaml` 并说明。
4. **可达 FAIL ≥2 路**：`rc11` 增量写；恢复 `rc8` 当 switch；还原重建回绿。
5. 不回归：M16 cfx/cache 代表集、Tiny 基线；`check-patch-tree` chipyard 段 0 problem、`check-component-changelog` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/chipyard/patches/**`、`components/chipyard/changelog.md`、`tests/arch/**`、`tests/arch/expected-divergences.yaml`、本任务书。
3. 不改 QEMU/gem5/IDL/LLVM/内核/spec/契约/Makefile；不改版本号。
4. 组件补丁经 `make_patch.py chipyard` 重导；`cp`+md5 还原；还原后重建；等 M16 chipyard 写者窗口。

## 待裁定

无。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
