# m18-idl-001: escape 帧选择位在 IDL 执行器/语义库/向量同步

**模块**：idl
**项目里程碑**：M18
**依赖**：`m18-spec-003`（SimRISC-11/IDL/Toolchain-01/contract-asm 编码真源）
**可并行分片**：否
**预估**：3–5 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务跨 IDL 执行器/语义库/向量，取 2–3× 中位）
**档位**：中改（IDL 执行语义 + 向量）
**状态**：待开始
**执行环境**：本地

## 背景

`m18-spec-003` 已把 `escape` 的编码真源改成：

- `imms18` bit1 = frame selector（0=cg5，1=cg9）；
- 合法 `imms18 ∈ {0,1,2}`，`3 ⇒ ILLI`；
- `imms20 ∈ {0,4,8}`（8=cg9/偏移 0），cg9 只允许偏移 0。

但以下消费方仍旧口径，导致 L2/向量不一致：

- `idl/tools/idl_exec.py::_op_escape` 仍只处理 cg5/旧立即数；
- `spec/IDL-ISA语义描述语言与语义库.md §4.6` 的 `cfx_escape_enter` 未含帧选择；
- `tests/inst/11-cfx/escape_ciii_cfx.S` case 13/14 仍把 `imms18=2` 当 ILLI；
- `idl/data/exec_anchor.toml` / `idl/.manifests.toml` 需随 IDL/执行器重算。

## 目标

1. `idl/tools/idl_exec.py::_op_escape`：按 `imms18` bit1 选 cg5/cg9；cg5 偏移 0/+4，cg9 仅 0；`3 ⇒ ILLI`；cg9 帧有效判据 `cfx_hart cg9 rc3 != 0`、返回 `prev_run_mode/prev_cfx_code/cause_ip` 并恢复 saved global mask（与 `DADAO-12 §5.3` 一致）；无 cg9 帧 ⇒ `CFXESC`。
2. `spec/IDL-ISA-… §4.6` `cfx_escape_enter` 签名/语义增加 frame selector；IDL 语义库版本/变更记录按需（不升 spec 版本，内容同步）。
3. `tests/inst/11-cfx/escape_ciii_cfx.S`：case 13/14 改为合法 `imms18=2` 的 cg9 路径（另加 `3 ⇒ ILLI` 新用例）；`tests/inst.yaml` 索引同步。
4. 重算 `idl/data/exec_anchor.toml`、`idl/.manifests.toml`；IDL 渲染/锚点门控回绿。

## 验收（逐条贴真实 rc）

1. `check-idl-sync`/`check-idl-parse`/`check-idl-exec-anchor`/`check-spec-codeblocks`/`check-asm-list`/`check-legality-drift`/`check-inst-macro-scope`/`check-tests-index` 全 rc=0。
2. `idl_exec` 对 `imms18=0/1/2/3` 的行为与 spec 一致：0/1 走 cg5、2 走 cg9、3 为 ILLI；cg9 帧无效/有效、返回寄存器/mask 恢复逐条覆盖。
3. `make check-inst-asm` 中 `escape` 向量全绿；新增 `3 ⇒ ILLI` 用例；`check-inst-sig`（如适用）与基线一致。
4. **可达 FAIL ≥2 路**：① 执行器仍把 2 当 ILLI ⇒ 新用例红；② cg9 帧不恢复 mask ⇒ 探针红；`cp`+md5 还原后回绿。
5. 不回归：`check-idl`/L2 相关、`make check` 与基线逐行相同；`check-knowledge-refs` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`idl/tools/idl_exec.py`、`idl/SimRISC-11.idl`（如需）、`spec/IDL-ISA-语义描述语言与语义库.md`、`idl/data/exec_anchor.toml`、`idl/.manifests.toml`、`tests/inst/11-cfx/**`、`tests/inst.yaml`、本任务书。
3. 不改 QEMU/RTL/gem5/LLVM/内核；不改版本号；IDL/生成锁用仓库工具重算。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；术语「bank = 寄存器组」。
5. 若发现 spec/契约与实现冲突，按 spec 改实现并写「待裁定」，不得反向改 spec。

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
