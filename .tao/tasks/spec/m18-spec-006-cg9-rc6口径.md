# m18-spec-006: `cg9 rc6`（switch_run_mode）口径统一：复位 2、异步进入取 rc6

**模块**：spec
**项目里程碑**：M18
**依赖**：`m18-idl-002`（已合入，`cg9` 七槽执行器）、`m18-spec-004`/`m18-spec-005`（ADR-0061 R2 规格）
**可并行分片**：否
**预估**：1–2 h（标定：`m18-spec-005` 派单→合入 39 min；本任务含 IDL 初值/自检与 RTL 只读核对，取 1.5–2×）
**档位**：小改（单点口径澄清 + 1 行初值）
**状态**：待开始
**执行环境**：本地

## 背景

`m18-idl-002` reviewer 发现 `cg9 rc6` 口径不一致（`ISS-540`）：

- **spec/契约**：`DADAO-12 §4.7` 表给初始值 2，`§5.4` 伪码注「固定 supv」，`contract-see` 同句 ⇒ 读法是“rc6 不可写、恒 supv”。
- **实现**：QEMU `helper.c:3410` 写 `val & 0x3`、进入取 `switch_run_mode`（`helper.c:3209`）、复位 2（`cpu.c:348`）；IDL 执行器同样「接受 2 位、进入取 rc6」。
- **F2**：IDL `Cfx.__init__` 的 `cg9[6]` 初值为 0，与 spec/QEMU 的复位值 2 不一致。

**用户 2026-11-25 裁定**：选①——**改 spec 措辞**为「复位值 2、异步进入取 rc6」，QEMU/RTL/IDL 实现不动。

## 目标

1. `spec/DADAO-12-SEE-主管系统运行环境.md`：§4.7 `cg9 rc6` 行与 §5.4 伪码注，删「固定 supv」表述，改为「复位 2；异步进入按 rc6 切换运行模式」；语义与 ADR-0061 R2 其它条目一致。
2. `.tao/contracts/contract-see.md`：同步同一句（若契约中确有“固定”字样）。
3. `idl/tools/idl_exec.py`：`cg9[6]` 复位值改 2（与 spec/QEMU 一致）；自检补一条「复位值 = 2」。
4. **RTL 只读核对**：查 `components/chipyard/**` 对 `cg9 rc6` 的写入/读取处理，报告是否与「复位 2、进入取 rc6」一致；**发现不一致只登记，不改 RTL**（属 `m18-chipyard-001`/M16 范围）。
5. 版本号不变（内容澄清）；`spec/.manifests.toml` 的 sha 锁按仓库工具重算。

## 验收（逐条贴真实 rc）

1. `check-spec-codeblocks`、`check-spec-changelog`、`check-spec-purity`、`check-contracts-dir`、`check-contracts-pending`、`check-contract-relocs`、`check-manifests-guard`、`check-idl-sync`、`check-idl-parse` 全 rc=0。
2. `idl_exec --self-test` 全 PASS，含「cg9 rc6 复位 = 2」与「异步进入取 rc6」两条。
3. 全文扫描：`DADAO-12`/`contract-see` 无「固定 supv」残留；`cg9 rc6` 表述唯一。
4. **可达 FAIL ≥2 路**：① `idl_exec.py` 初值改回 0 ⇒ 自检红；② 删 spec 变更记录行 ⇒ `check-spec-changelog` 红；`cp`+md5 还原回绿。
5. `make check` 与基线逐行相同；版本号未变；`check-knowledge-refs` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree（分支 `m18-spec-006`）；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/.manifests.toml`、`.tao/contracts/contract-see.md`、`idl/tools/idl_exec.py`、`idl/data/exec_anchor.toml`（如需）、本任务书；**不改** QEMU/RTL/gem5/内核/LLVM/其它 spec 册。
3. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。
4. 门控有 flock：遇锁按 flock 等待，禁清锁/绕过；本任务不得起内核长跑批（`m18-linux-024` 正占用）。
5. 术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 待裁定

无（用户已裁定方案①）。

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
