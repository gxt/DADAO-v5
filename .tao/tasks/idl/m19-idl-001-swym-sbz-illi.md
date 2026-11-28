# m19-idl-001: IDL 执行器 swym 高位 SBZ 判 ILLI

**模块**：idl
**项目里程碑**：M19（swym 语义工作在本册；`m19-qemu-002` 已在此册）
**依赖**：无（单元级自足）；与 `m19-qemu-002`（QEMU swym ILLI，正在做）**并行、共享语义但不同组件**；用例复用 `m19-testcases-001`（已合入）
**可并行分片**：否（IDL 单写者）
**预估**：1–2 h
**档位**：小改（单点语义 + 复用既有用例，复核 ≤20 min）
**状态**：待开始

## 目标

`idl/tools/idl_exec.py` 的 `@sem("swym_oiii_imm") def _op_swym(m, insn)`（约 L2507）当前只做 no-op，**无 SBZ 判据**。修复：执行体前判 `immu18[17:12] != 0 ⇒ Fault("Illegal")`（照 `_lr` L2451 的 `rdhb != 0 ⇒ ILLI` 风格）；合法 `N = immu18[11:0]`（0..4095）行为不变（no-op，IP 自增由 `Machine.step` 负责）。

不改 `.idl` 正文（`idl/SimRISC-12.idl` swym 条已含「`immu18[17:12]` SBZ ⇒ ILLI」注释）、不改 spec/契约/opcodes/其它引擎。

## 已核实事实（落地前可复验）

- 语义源：`spec/SimRISC-12-其它指令.md §2`（`immu18[17:12]` SBZ 非 0 ⇒ ILLI）；`contracts/opcodes.yaml` `swym_oiii_imm`：`legality: immu18[17:12] == 0`、`rule_refs: encode_sbz`。
- `Insn.decode()`（约 L297）只按 mask/value 匹配、不做 legality ⇒ 修复前 `0x47881000` 被当合法 `swym` 执行。
- 先例：`_lr`（L2451）`if insn["rdhb"] != 0: raise Fault("Illegal")`；`Fault` 构造（L132）校验 cause 名，`"Illegal"` 合法。
- **锚点无需更新**（纠正「可能需同步锚点」的预判）：`idl_check_anchor.py` 只锁 `.idl` 正文 sha256 + `impl` 函数名 + `idl/lib/*.idl` sha，**不锁 impl 函数体**；本任务只改 `_op_swym` 函数体、`.idl` 不动 ⇒ `check-idl-exec-anchor` 应保持 rc=0。若实际漂移（不应发生）才 `--update` 并在评审说明。

## 用例

`m19-testcases-001` 已合入 `tests/inst/12-misc/swym_oiii_imm.S`，含 4 条高位 ILLI 故障例（`TEST_FAULT_ENC` 12/13/14/15：`0x47881000`/`0x478A0000`/`0x478BFFFF`/`0x478A0007`）与 N=0/1/42/7/4095 合法例；`idl/data/idl_exec_cases.toml` 已登记该镜像（category arith）。**勿重复造用例**，直接复用。

对照点：
- `0x47881000`（H=0x1）、`0x478BFFFF`（H=0x3F）⇒ `Fault("Illegal")`；
- `0x47880000`（swym 0）、`0x47880FFF`（N=4095）⇒ 正常 no-op。

## 验收

1. 修复前后 `idl_exec.py --elf <swym 镜像 ELF>`（或 `idl_four_way.py --only swym_oiii_imm` 的 IDL 侧）真实 rc/输出对照：修复前高位字不抛异常、修复后抛 `Illegal`；合法字行为不变。
2. 门控真 rc：`make check-idl-exec-anchor`、`check-idl-parse`、`check-idl-sync`、`check-knowledge-refs` 全 rc=0。
3. `make check-idl`（IDL+QEMU 两方）：IDL 侧应转绿；QEMU 侧依赖 `m19-qemu-002` 合入——若未合入，如实报告 IDL/QEMU 差分（QEMU 仍按 NOP 执行高位字），不视为本任务失败；若已合入应全绿。`make check-idl-full` 若耗时可控则跑（gem5/chipyard 侧已由 m19-gem5-001/m19-chipyard-003 落实 ILLI，应绿）；否则说明原因。
4. 证据脚本落运行期证据目录内 `run.sh`：含「注入（临时去掉 SBZ 判据）→ FAIL → `cp`+md5 还原 → 回绿」真实输出；断言捕被检命令退出码，禁 `tee` 吞码。
5. 完成区 ≤30 行；改 `.idl` 须 `--update` 锚点并说明（本任务预期不改）。

## 硬约束

独立 worktree（分支 = `m19-idl-001`）；不提交 git；只动 `idl/tools/idl_exec.py`（+ 若锚点漂移则 `idl/data/exec_anchor.toml`）；不改 `components/**`、`spec/`、`contracts/`、`contracts/opcodes.yaml`、`Makefile`、其它引擎；`cp`+md5 还原（禁 `git checkout`/`restore`/`stash`）。

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
