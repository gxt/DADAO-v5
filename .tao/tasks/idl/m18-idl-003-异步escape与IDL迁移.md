# m18-idl-003: IDL 执行器与 IDL-ISA 迁移到异步 escape（任务链第 3 环）

**模块**：idl
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入，F3 留下的 IDL 散文/渲染块由本任务补）、`m18-testcases-004`（向量）
**可并行分片**：否
**预估**：3–4 h（标定：同档 idl-002 2–3 h；本任务含 cg5/cg9 重排 + escape 重写 + IDL-ISA 散文与渲染，取 1.2–1.5×）
**档位**：中改（IDL 语义）
**状态**：待开始
**执行环境**：本地

## 背景

`m18-spec-007` 已改规范与契约，但 `idl/tools/idl_exec.py`、`idl/SimRISC-11.idl`、`spec/IDL-ISA §4.6` 散文及 `SimRISC-11` 的 IDL 渲染块仍是 R2/0.5.7 语义（seven-slot cg9、`imms18[1]` 恒 `CFXESC`、`cg5` 无出口意图）。`check-idl-sync` 之所以绿，是因为两边都旧；这会让 IDL 四方比对失去约束。

## 目标

1. **`idl/tools/idl_exec.py`**：
   - `cg5` 新布局（`rc0`–`rc3` 只读、`rc4/rc5`、`rc8`–`rc11`，`rc11` 复位全 1）；
   - `cg9` 新布局（`rc0`–`rc4`、`rc5` pending、`rc14` switch、`rc15` vector，`rc6`–`rc13` reserved）；
   - `cg0`–`cg3` switch/vector → `rc14`/`rc15`；
   - 进入自动填（同步/异步的写入集合不同，hart `cg5 rc0`–`rc3` 不写）；
   - `escape cfxHA`：`imms18=0`（非 0 `ILLI`）、`cfxha`=当前、不得升权、目标未实现/无 monitor ⇒ `CFXESC`、跳 `rc10`、`rc11` 整字写目标 monitor `cg8 rc1`、`escape_num` +1；
   - 删除旧的 cg9 七槽/`src_frame` 角色/`imms18[1]` 语义。
2. **`idl/SimRISC-11.idl` + 渲染块 + `spec/IDL-ISA §4.6` 散文**：同步新语义并重渲染（修 spec-007 的 F3）。
3. **`idl/data/exec_anchor.toml`/manifest** 重算；`check-idl-sync/-parse/-exec-anchor` rc=0。
4. 与 `m18-testcases-004` 向量交叉验证；`check-idl` 四方比对按新语义。
5. 不做：不改 QEMU/RTL/gem5/LLVM/内核。

## 验收（逐条贴真实 rc）

1. `idl_exec --self-test` 覆盖：cg5/cg9 槽位与权限、`rc11` 复位、进入写入集合、escape 五类判据、`rc11` 整字、`escape_num`；全 PASS。
2. `check-idl-sync`/`-parse`/`-exec-anchor`、`check-spec-codeblocks`、`check-manifests-guard` rc=0；`check-idl` 与 QEMU/RTL（可用者）一致，divergence 显式登记。
3. 可达 FAIL ≥2 路（旧 `imms18[1]`、`rc11` 增量），`cp`+md5 还原回绿。
4. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`idl/tools/idl_exec.py`、`idl/SimRISC-11.idl`、`idl/data/**`、`idl/.manifests.toml`、`spec/IDL-ISA-语义描述语言与语义库.md`、`spec/SimRISC-11-核芯功能扩展指令.md`（渲染块）、`spec/.manifests.toml`、本任务书。
3. 不改实现组件/契约（契约随 spec-007 已改）/`Makefile`；不改版本号；生成物用仓库工具重算；`cp`+md5 还原。

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
