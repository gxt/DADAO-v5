# m18-spec-003: escape frame selector 编码真源同步（SimRISC-11/IDL/Toolchain-01/contract-asm）

**模块**：spec
**项目里程碑**：M18
**依赖**：`m18-spec-002`（`DADAO-12`/`contract-see` 已改 hart-first/cg9 + selector）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务跨 4 处编码真源 + IDL 渲染，取 1.5–2× 中位）
**档位**：中改（编码/IDL/工具链规范）
**状态**：待开始
**执行环境**：本地

## 背景

`m18-spec-002` 只在 `DADAO-12 §5.1/§5.3`、`contract-see`、`contract-isa` 落了 `escape` 的 **frame selector bit1**（0=cg5，1=cg9；`imms18 ∈ {0,1,2}`、`3 ⇒ ILLI`；`imms18[17:2]` SBZ；cg9 仅偏移 0）。以下**编码真源仍未同步**，会导致工具链/IDL/QEMU/RTL/gem5 按旧编码实现：

- `spec/SimRISC-11-其它.md` 正文与 263 个 IDL 渲染块中的 `escape` 编码/合法立即数；
- `idl/SimRISC-11.idl` 的 `escape` 语义/约束；
- `spec/Toolchain-01 §2.4/§5`（汇编 `imms20` 合法值）；
- `.tao/contracts/contract-asm.md §5`。

## 目标

1. `spec/SimRISC-11`：`escape` 编码层 `imms18` 增 `bit1 = frame`（0=cg5/1=cg9）；合法 `imms18 ∈ {0,1,2}`，`3 ⇒ ILLI`；`imms18[17:2]` SBZ；汇编层 `imms20 ∈ {0,4,8}`，8=cg9/偏移 0；cg9 只允许偏移 0。
2. `idl/SimRISC-11.idl`：同步 `escape` 的编码/约束；重新渲染受影响的 `SimRISC-11` 块（只改 `escape` 相关块，其它块逐字节不变）。
3. `spec/Toolchain-01`：汇编器接受 `imms20 ∈ {0,4,8}`、拒绝其它；`8` 对应 cg9。
4. `.tao/contracts/contract-asm.md §5`：同步该编码口径。
5. `spec/.manifests.toml` 重算 `SimRISC-11` 与 `Toolchain-01` 的 sha256；版本仍 `0.8.0-rc`。

## 验收（逐条贴真实 rc）

1. `make check-spec-refs`/`check-spec-drift`/`check-spec-purity`/`check-spec-changelog`/`check-spec-numbering`/`check-spec-codeblocks`/`check-asm-list`/`check-contracts-*`/`check-idl-sync`/`check-idl-parse` 全 rc=0（按实际目标）。
2. `grep` 活文档中 `escape` 的旧约束 `imms18[17:1] SBZ`、`imms20 ∈ {0,4}` 已不再作为唯一合法集；新的 `{0,1,2}`/`{0,4,8}` 明文。
3. IDL 渲染：只 `escape` 相关块变化，其它 262 块逐字节相同（`git diff` 逐块核；渲染工具可复现）。
4. 锁哈希与文件一致；`DADAO-12` 不改（spec-002 已改）。
5. 不回归：`make check` 与基线逐行相同；`check-knowledge-refs` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`spec/SimRISC-11-其它.md`、`idl/SimRISC-11.idl`、`spec/Toolchain-01-*.md`、`.tao/contracts/contract-asm.md`、`spec/.manifests.toml`、本任务书；不改实现/QEMU/RTL/gem5/LLVM 代码。
3. 不改版本号；不复制 spec 正文；IDL 渲染必须用仓库工具，不手改生成块。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；术语「bank = 寄存器组」。

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
