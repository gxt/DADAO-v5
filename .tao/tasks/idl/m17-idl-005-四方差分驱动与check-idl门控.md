# m17-idl-005: 四方差分驱动与 `check-idl` 门控

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-004`（trace，仅红后归因用）、`m17-testcases-002`（签名槽 4528）
**可并行分片**：否（与 `006`–`008` 同改 `idl/idl_exec.py`，须串行）
**预估**：2–3 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

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

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
