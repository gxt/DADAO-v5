# m17-idl-005: 四方差分驱动与 `check-idl` 门控

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-004`（trace，仅红后归因用）、`m17-testcases-002`（签名槽 4528）
**可并行分片**：否（与 `006`–`008` 同改 `idl/idl_exec.py`，须串行）
**预估**：2–3 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景（用户 2026-11-22 定口径）

M17 的四方差分底座 = `tests/inst` 272 个 `.S` 镜像（Kaiwu-Tiny）；**不含** Linux、`ee-user`（musl）、`ee-vast`/arch probes。判据 = **签名槽 + 退出码**四方一致；逐指令 trace 只在红后归因。

现状（现场事实）：
- 三平台已同 ELF 逐字节比对：`tests/ee-tiny/run_inst_tiny.py --platforms chipyard,qemu,gem5`；签名流机制 `tests/shared/asm/signature.inc`，host 侧解析 `tests/shared/signature.py`；
- 槽级期望 `tests/data/inst-signature/expected.tsv`（`m17-testcases-001/002` 从 `.S` 内联常量派生）；
- IDL 侧只有末态差分 `tools/idl/check_exec_parity.py`（28 例，比寄存器/退出码/`SYS_WRITEC` 字节流）与 trace 差分 `check_trace_parity.py`；
- `idl/idl_exec.py` 只实现 `SYS_WRITEC/CLOCK/EXIT/EXIT_EXTENDED`；签名流在 QEMU/gem5 走 `SYS_WRITEC` 回退、chipyard 走 `SYS_WRITE` 块写（`ISS-481`）。

## 要做

1. **四方驱动**（新增 `tools/idl/check_four_way.py`）：同一 ELF 取 IDL/QEMU/gem5/chipyard 的**签名槽流 + 退出码**并四方比对；平台启动与装载复用 `run_inst_tiny.py` 的既有路径，签名取流/解析复用 `tests/shared/signature.py`，不新建第二套。
2. **IDL 侧签名流**：`SYS_WRITE` 按「未实现 ⇒ 不可用」处理，使 guest 走 `SYS_WRITEC` 回退，与 QEMU/gem5 实测路径一致；字节写进既有 `output` 观测面。口径写 `docs/idl-four-way.md`。
3. **用例清单机制**：`idl/idl_exec_cases.toml` 扩为「镜像 → 类别」清单并新增 `pending` 段；门控断言 **主清单集合 == 现场派生集合（`tests/inst` 去掉 `07-floating-point`）减去 `pending`**；`pending` 每条写镜像名 + 原因。
4. **门控**：新增 `check-idl` 进 L2（`GATE_LOCKED_TARGETS` + `_locked-check-modules`）；L2 默认平台集 = **IDL + QEMU**（主控机可跑，不依赖 gem5/Verilator 构建），`--platforms gem5,chipyard` 由节点/收口调用；缺 QEMU 安装根或 bootrom 即 ERROR，不静默跳过；帮助行与 L2 注释同步。
5. 本任务只用**现有 28 例**跑通四方（`pending` = 其余非 FP 镜像），不扩语义。

## 不做

- 不补未注册 id 的语义（归 `006`–`008`）；
- 不改 `tests/inst` 载体、`tests/data/inst-signature/` 期望、QEMU/gem5/RTL、`.idl` 源；
- 不碰 FP（`07-floating-point`，归阶段二）。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 期望槽只来自 `.S` 内联常量 / `expected.tsv`；IDL 侧只提供实测槽，禁反向填期望；
- 计数现场派生（禁写死 272/222/28）；完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. 四方 28 例签名槽 + 退出码一致，真实 rc=0；逐例打印槽数；
2. **可达 FAIL ≥3 路**：① 少 dump 一槽 ⇒ 槽数不符红；② 改 IDL 一条写回值 ⇒ 槽值差异红（`cp`+md5 还原）；③ 从主清单删一条镜像但仍在现场派生集 ⇒ 集合断言红；
3. `make check-idl` 在 L2 真跑（贴 rc 与耗时）；`check-idl-parse`/`check-idl-sync`/`check-knowledge-refs` rc=0；
4. 不自比：随机抽 1 例，人工核对 IDL 槽值 vs `.S` 内联期望。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-22）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 同一 workdir 重跑时，`run_inst_tiny.json` / IDL `--state-out`/`--image-out` 可能是上次残留（崩溃时假绿） | ✅已修 | `run_platforms` 与 `run_idl` 起跑前 `unlink` 三件输出 | 驱动重跑 28 例仍 rc=0；注入①靠长度断言变红 |
| `expected.tsv` 无行的 0 检查点镜像（`undi_reserved.S`）会 KeyError/误判 | ✅已修 | nslots=0 时用 `run_inst_tiny` 现场 `expected` 对账；主清单 0 槽允许空流 | 代码路径审查；`--only` 主清单 28 例不受影响 |
| `check_exec_parity.py` 读新 schema 缺 `id` 会退出 | ✅已修 | `image` 存在时 `id = Path(image).stem`（兼容旧 id） | `--only ld.o_rrii_rd` rc=0；全量 28/28 rc=0 |
| 四方从复位跑暴露 `rf0` 复位值错（只读 qNaN 位为 0）；`check_exec_parity --init` 曾掩盖 | ✅已修 | `idl_exec` 按 `spec/SimRISC-00 §2.3.1` 置 `RF0_RESET=0x7FF800007FC00000`，自检加断言 | `rf2rf_orri_rf` 四方绿；self-test 30/30 |
| 注入②首版改 `ld.o` 写回 ⇒ guest 断言先退出（不是槽值差） | ✅已修 | 改为 IDL `SYS_WRITEC` 输出字节 `^1`，只动观测面 | 注入②红因「槽 1 idl=… ≠ qemu=…」；还原回绿 |
| 任务背景的 `tools/testcases/lib/signature.py` 已是旧路径 | ✅已核 | 实际复用 `tests/shared/signature.py`（`m16-testcases-005` 起唯一一份） | `docs/idl-four-way.md` 注明；驱动 import 该校验 |

**判决**：finding 全部已修/已核，无未修项 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 复核（2026-11-22）

**重跑记录（全部本人执行，不采信完成区）**
- 运行期证据目录内的 `run.sh`：**rc=0，PASS 33 / FAIL 0**，227.6 s；四方/清单/抽例/三路注入全过；
- `make check-idl`：**rc=0，17 s**，`28/28 例四方一致（parties=idl,qemu；主清单 28 / pending 194 / 现场派生 222）`；`check-idl-parse`=0、`check-idl-sync`=0、`check-knowledge-refs`=0、`check-no-residue`=0、`check-dirs`=0；
- 自跑全四方 `--platforms qemu,gem5,chipyard`：**rc=0，42 s，28/28**；镜像/二进制 = `qemu-system-dadao a9ca4aec…`、`bootrom_tiny.bin a5d78816…`、`gem5.opt ac0613c8…`、`simulator-chipyard…WumingTinyConfig 6d699cc3…`（writer-guard 启动=结束 md5 相同）；
- 集合现场复算：`tests/inst` 去 FP 册 = **222**，主清单 28 + pending 194 = 222，集合相等、主/pending 无交集、pending 194/194 均带 `reason`；
- 不自比：抽 `rd2rd_orri_rd` 人工核对 `.S` 内联常量（行 21/25/29/34/41/53/58/66/70/76/82）⇒ IDL **11/11 槽**逐槽相等，且 IDL 与 QEMU 字节流 88 B 逐字节相等；`idl_exec.py` **0 处**读 `expected.tsv`（只由驱动作 parse 计数 + oracle 比对，方向 = 期望→实测），期望真源 = `inst_expected.py` 从 `.S` 内联常量/WDATA 派生（m17-testcases-001）；
- **独立注入 4 路**（均 `cp` 备份 + md5 相等还原 → 回绿，未用 git 还原）：① `expected.tsv` 槽 11 期望翻 1 位 ⇒ **rc=1**（idl/qemu 双红「期望 0x…abcdff 实际 0x…abcdef」）；② 主清单追加重复 image ⇒ **rc=2**（「主清单有重复 image（29 条 / 28 唯一）」）；③ IDL `exit_code`+1 ⇒ **rc=1**（「退出码不一致 {idl:1,qemu:0}」）；④ rf0 复位归 0 ⇒ **rc=1**（`rf2rf_orri_rf` 槽 11 idl=0 ≠ qemu=0x7ff800007fc00000）。
- 基线红：`make check-run-artifacts` **rc=2**，**560** 条非法名全落 chipyard(471)/linux(58)/arch(17)/llvm(6)/ansibench(7)/infra(3) 历史日志，逐条 grep 本任务门控日志与 `check-idl`/four-way 条目 = **0**；门控代码本任务未改。

**约束核验**：门控接线（`check-idl` ∈ PHONY 列表、`GATE_LOCKED_TARGETS`、`_locked-check-modules`；`--platforms` 默认 `qemu` ⇒ L2 只 IDL+QEMU，不依赖 gem5/Verilator；缺 QEMU/bootrom 即 ERROR；帮助行与 L2 注释已同步）✅；`SYS_WRITE` 返回「未写字节数」+ `rd8_defined=true` 与 `contract-semihosting §3/§4` 一致，guest 据此走 `SYS_WRITEC` 回退 ✅；rf0 `0x7FF800007FC00000` 与 `spec/SimRISC-00 §2.3.1` 位域（[63:51]/[31:22] 只读 qNaN、其余 SBZ=0）逐位相符，属任务书 5 项之外改动但完成区+自审表**已披露**，且注入④证明其确实影响 28 例之一 ✅；`docs/idl-four-way.md` 路径（`tests/shared/signature.py`/`signature.inc`）与实现一致、无 `.work/**` 引用、`docs/README.md` 已加索引 ✅；`git status -uall` 复核前后各 8 行**逐行一致** = 完成区 7 项 + 任务书自身，无越界 ✅。

**发现（均不阻断，交 architect 收尾）**：F1 完成区写「561 条」，实测 **560**（数字笔误，非判据值）；F2 pending 194 条 `reason` 为同一条通用文案（有 reason，但无逐镜像差异）；F3 本轮 gem5 快照 `ac0613c8…` ≠ 完成区 `d6bc7508…`（并行任务 16:53 重建 `gem5.opt` 的环境差异；qemu/bootrom/chipyard 与完成区一致，四方仍 28/28）；F4 完成区「测试结果」写了具体临时目录证据路径，按「任务书不写运行期路径」应改为「运行期证据目录内的 `run.sh`」措辞（`check-knowledge-refs` rc=0，非门控项）。

**剩余风险**：L2 取流依赖共享安装根与并行重建窗口（writer-guard 已登记，极端时 rc=75）；全四方依赖 gem5/chipyard 构建在位。

**判决：Accepted**（本人重跑全绿 + 4 路独立注入均可达 FAIL 并还原回绿 + 约束无违反；F1–F3 交 architect 收尾修正/知悉）

## 完成区

**测试结果**：一键证据（运行期证据目录内的 `run.sh`）= **rc=0 / EVIDENCE: PASS（33 项，0 失败）**；全四方 28/28（IDL+QEMU+gem5+chipyard），L2 两方 28/28；注入 3 路各自红并 `cp`+md5 还原回绿；随机抽例 17/17 槽 IDL == `.S` 内联期望。
**修改文件**：`tools/idl/check_four_way.py`（新）、`docs/idl-four-way.md`（新）、`idl/idl_exec.py`、`idl/idl_exec_cases.toml`、`tools/idl/check_exec_parity.py`、`Makefile`、`docs/README.md`。
**验收结果**（真实 rc）：`make check-idl`=0（17 s，L2，28/28）；`check-idl-parse`=0、`check-idl-sync`=0、`check-knowledge-refs`=0；`check_exec_parity` 全量 28/28=0；`check-writer-guards`/`check-dirs`/`check-no-residue`/`check-manifests-guard`/`check-asm-list-drift`/`check-case-ledger` 均 0。四方快照 md5：qemu `a9ca4aec…`、gem5 `d6bc7508…`、chipyard `6d699cc3…`（启动=结束）。
**新发现/坑**：① 任务背景的 `tools/testcases/lib/signature.py` 已迁到 `tests/shared/signature.py`（`m16-testcases-005`）；② 四方从**复位**跑（不灌 QEMU 入口态）暴露 `rf0` 只读 qNaN 复位值缺失，已按 `spec/SimRISC-00 §2.3.1` 修（`006`–`008` 扩例前必须保持）；③ 并行任务反复重建 `install-host`/gem5/chipyard，writer-guard 曾拒绝（rc=75）并两次检出「二进制被替换」（重试 3 次：等写者结束后重跑；最终用启动时 md5 快照跑全四方）；④ `check-run-artifacts` 基线红 rc=2（560 条历史运行期日志非法名，均属 linux/旧任务，无 `idl` 条目）。
**遗留问题**：无（`pending` 194 例按任务边界留 `006`–`008`/`009`；FP 50 例归阶段二）。
