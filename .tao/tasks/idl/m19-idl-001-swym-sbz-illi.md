# m19-idl-001: IDL 执行器 swym 高位 SBZ 判 ILLI

**模块**：idl
**项目里程碑**：M19（swym 语义工作在本册；`m19-qemu-002` 已在此册）
**依赖**：无（单元级自足）；与 `m19-qemu-002`（QEMU swym ILLI，正在做）**并行、共享语义但不同组件**；用例复用 `m19-testcases-001`（已合入）
**可并行分片**：否（IDL 单写者）
**预估**：1–2 h
**档位**：小改（单点语义 + 复用既有用例，复核 ≤20 min）
**状态**：待验收

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

## 待裁定

1. `_install_bootrom` 的表偏移 0xE000→0x1F00 是让 IDL 能跑起来的**跨模块前置**（M19 8K BootROM 迁移未覆盖 IDL），本任务一并修：请裁定保留在本任务还是另立任务并重验。
2. 陈旧 `tests/data/inst-signature` 属 `m19-testcases-001` 应产出的生成物；建议该任务返工（`check_inst_sig.py --write`），本任务文件集不允许改。

## 完成区

**测试结果**：证据脚本 21/21 PASS（rc=0）。单方对照（补 BootROM 前置后、swym 修复前）：full=exit 12、CASE_N=12/13/14/15=12/13/14/15、合法字=0；修复后全部 exit 0（full 签名 88 B = 11 槽）。
**修改文件**：`idl/tools/idl_exec.py`（① `_op_swym` 增 `immu18[17:12] != 0 ⇒ Fault("Illegal")`；② `_install_bootrom` 表偏移 0xE000→0x1F00，见新发现①）。
**验收结果**：
- `check-idl-exec-anchor` rc=0（op 263/263、lib 1/1）；`check-idl-parse` rc=0；`check-idl-sync` rc=0；`check-knowledge-refs` rc=0；`idl_exec.py --self-test` 190/190 rc=0。
- `make check-idl` rc=2（264/274）：swym 唯一失败为**入库 expected.tsv 陈旧**（88 B ≠ 104 B），现场重生成后 `--only swym_oiii_imm` 四方一致（IDL 88 B/11 槽；QEMU 腿 PASS，安装根 qemu md5 `c5a46ef7…`）；其余 9 红（8 stm + cfx2rd）镜像无 swym，属既有 IDL 缺口。
- `check-idl-full` 未跑：nightly 274 例全四方，超出小改档位；swym 已由单例四方覆盖。
**新发现/坑**：
① M19 8K BootROM 迁移（`m19-testcases-003`）后 `_install_bootrom` 仍读旧 64K 表偏移 0xE000 ⇒ 任何 `--elf` 装载期 struct 异常、check-idl 基线全红；按 `spec/Kaiwu §6.2` 改为 0x1F00。
② `m19-testcases-001` 将 swym `.S` 从 13 检查点减为 11，但未重生成 `tests/data/inst-signature/{expected.tsv,inputs.sha256}` ⇒ swym 门控假红，与本改动无关。
③ `idl_qemu_trace.py` 同样残留 0xE000 表偏移（未改，不在本任务验收面）。
**遗留问题**：
① BootROM 修复归属待裁定（见上）。
② `tests/data/inst-signature` 需 `m19-testcases-001` 侧 `check_inst_sig.py --write` 重生成（本任务文件集外；已在证据脚本内临时重生成+`cp`/md5 还原验证 IDL 腿）。
③ 8 个 `stm.*` + `cfx2rd_crrr_cfx` 的 IDL 红为 8K 几何后既有缺口，需另立 IDL 任务。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行核对 `_op_swym`：`immu18` 为 18 位字段，`>> 12 & 0x3F` 精确取 `[17:12]`；非零先抛 `Illegal`（无副作用），合法 N 路径保持 no-op；风格与 `_fence`/`_lr` 的 `encode_sbz` 先例一致。`_install_bootrom`：0x1F00 取自 `spec/Kaiwu §6.2`，表头 16 B/表项 32 B 与 `build_tiny_bootrom.py` 一致。防造假：pre/post 均为真实命令原文；注入/还原 md5 见证据脚本输出。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 基线 `--elf` 全红（表偏移陈旧） | ✅已修 | `_install_bootrom` → 0x1F00（§6.2） | 修复前 struct 异常原文；修复后 264/274 可执行、证据 21/21 |
| F2 swym 门控假红（expected.tsv 陈旧） | ⏸延后（文件集外） | 无 | 临时重生成后 swym 四方 PASS，`cp`+md5 还原 |
| F3 `idl_qemu_trace.py` 同偏移 | ⏸延后（验收面外） | 无 | 同 F1 根因，已记新发现③ |
| F4 9 例 IDL 既有红 | ⏸延后（另立任务） | 无 | 对应镜像 grep `swym` = 0，与本改动无关 |

#### 第 1 轮 reviewer 验收

**判决：Accepted**（主改动、跨模块前置、证据脚本、约束均达标；QEMU 腿事实见 4）

1. **主改动**：`git diff` 仅 2 hunk——`_op_swym` 入口 `if (insn["immu18"] >> 12) & 0x3F: raise Fault("Illegal")`（取位 = bit17..12，`Fault("Illegal")` 为合法 cause，风格同 `_lr`/`_fence`）+ `_install_bootrom` 表偏移 `0xE000→0x1F00`；无夹带语义。判据源 `spec/SimRISC-12-其它指令.md §2`「`immu18[17:12]` 为 SBZ（非 0 ⇒ ILLI）」与 `contracts/opcodes.yaml` `legality: immu18[17:12] == 0`，非平台反推。
2. **修复前后对照（我自跑）**：修复后 full=exit 0 / 88 B（11 槽）、CASE_N=12/13/14/15 全 0、合法字 `0x47880000`/`0x47880FFF`=0；注入删判据后 full=12、CASE_N=12/13/14/15=12/13/14/15、合法字仍 0（即修复前行为）；`cp -p` 还原后 md5 回 `165119c0…`、mtime 复原、零残留。
3. **前置 hunk 判定**：① 支持——`spec/Kaiwu §6.2`（8 KiB、表 48 B@`0x1F00`）+ `discussing.md`（power 0x0000–0x07FF / hmon 0x0800–0x13FF / table 0x1F00）；我实测 8192 B 镜像在 `0x1F00` 读出 `DBOT`/v1/count1，`0xE000` 越界。② 必要——注入回 `0xE000` 后任意 `--elf` 在 `struct.unpack_from` 处 `struct.error`（需 57352 B / 实 8192 B），装载即死，swym 无法独立验证 ⇒ 接受为必要前置。③ 已在「待裁定 1」「新发现①」「完成区修改文件②」分列披露，未混入 swym 语义，归属留架构师裁定。④ `idl/tools/idl_qemu_trace.py` L201 仍 `0xE000`（我复核），与 `ISS-543` 描述一致（仅确认事实，未改）。
4. **门控（我自跑）**：`check-idl-exec-anchor`=0（op 263/263、lib 1/1）、`check-idl-parse`=0、`check-idl-sync`=0、`check-knowledge-refs`=0、`idl_exec.py --self-test`=0（190/190）。`make check-idl` rc=2、`264/274`，10 红 = 8 `stm.*` + `cfx2rd_crrr_cfx`（均无 swym）+ `swym_oiii_imm`（`槽 13 / rc {idl:0,qemu:0}`）。QEMU 腿我三次跑证据脚本均 `QEMU PASS`、`bytes {idl:88,qemu:88}`、`problems []`；事实是 `m19-qemu-002` 未合入（`components/qemu/patches/…/trans_ctrl.c.inc.patch` 仍写 `swym: NOP`，分支 `638ac7fc4` 待验收），绿灯来自共享源树该修复的在途本地 commit（10:14）与 10:31 构建的安装根 qemu ⇒ **不作本任务绿灯依据**，合入后需复验。`check-idl-full` 未跑（档位/耗时），与完成区声明一致。
5. **陈旧签名数据（我自跑）**：`check_inst_sig.py --data-only` rc=1，DATA-FAIL 恰 2 条且全属 `swym_oiii_imm`（`expected.tsv:4682`、`inputs.sha256:283`；我 `sha256sum` 现场 = `b3a13ccb…` ≠ 入库 `599b13c6…`）⇒ **除 swym 外 0 个镜像陈旧**。现场 `--write` 重生成后 `--only swym_oiii_imm` 双方 `rc {idl:0,qemu:0}`、11 槽/88 B、无 problems，随后 `cp`+md5 还原无残留 ⇒ 假红与实现无关；文件集只允许 `idl/`，修复已另立 `m19-testcases-007`（master `2e1064f59` 派单）。
6. **证据脚本**：重跑「运行期证据目录内的 `run.sh`」——第 1 次 rc=1（`writer-guard: REFUSED`，并发 qemu 构建 pid 3410742，环境干扰，重试 1/3）、第 2 次 rc=0 `21/21`、第 3 次（终态）rc=0 `21/21`；我独立注入删 SBZ 判据 → 同脚本 rc=1 `PASS=11 FAIL=10` → `cp -p` 还原 md5 回 `165119c0…` → 回绿 `21/21`。断言现场计数、捕被检命令 rc、注入点唯一命中、EXIT trap 兜底还原，脚本合格（不需返工）。
7. **约束核验**：分支 `m19-idl-001`、未提交 ✓；`git status -uall` 全程仅 `.tao/tasks/idl/m19-idl-001-swym-sbz-illi.md` + `idl/tools/idl_exec.py`，与完成区「修改文件」一致 ✓；未碰 `components/`、`spec/`、`contracts/`、`Makefile`、其它引擎 ✓；完成区 14 行 ≤30、全文无具体运行期/临时/家目录路径 ✓；注入还原全走 `cp`+md5（未用 checkout/restore/stash）✓。
8. **遗留（不阻断）**：前置归属裁定、`m19-testcases-007` 重生成签名数据、`ISS-543`（trace 工具同偏移）、8 `stm.*`+`cfx2rd` IDL 既有红另立任务。
