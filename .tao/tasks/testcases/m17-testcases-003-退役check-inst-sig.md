# m17-testcases-003: 退役 `check-inst-sig`（`check-idl` 为超集）

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-idl-013`（`check-idl` 覆盖 272 例后才退役）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定 A）

`check-inst-sig`（L2，QEMU 单平台，272 镜像逐槽 vs `tests/data/inst-signature/expected.tsv`）与 `check-idl`（L2，013 后 272 例，对每一方都比同一份 `expected.tsv` 再四方互比）**在同一层重复判同一件事**。`Process-07 §4` 要求「一个检查只在一层」。裁定 A = 退役 `check-inst-sig`。

保留：`expected.tsv` 派生（`make inst-signature-data`）、`tests/shared/signature.py`、`.S` 内联期望——它们都是 `check-idl` 的输入。

## 要做

1. `Makefile`：
   - 从 `_locked-check-modules`（L2 列表）删除 `check-inst-sig`；从 `GATE_LOCKED_TARGETS` 删除；
   - 删除 `_locked-check-inst-sig` 目标与 `INST_SIG_LOG`（确认无其它使用者）；
   - 删除 help 里的 `make check-inst-sig` 行 / PHONY 项；
   - **保留** `inst-signature-data`（它调 `check_inst_sig.py --write`）。
2. `tools/testcases/inst/check_inst_sig.py`：保留脚本与 `--write`（生成 `expected.tsv`、`inputs.sha256`）；usage/docstring 改为「期望值生成器；执行门控已退役，槽级判据在 `check-idl`」，避免误导。
3. `docs/Process-07`：
   - L2 表行删除 `check-inst-sig`，写明「签名区槽级判据已并入 `check-idl`（`m17-testcases-003`）」；
   - §7 表删除该行（或标「已退役」并指向 `check-idl`）。
4. `tools/testcases/README.md` 与 `tests/data/inst-signature/README.md` 中指向 `make check-inst-sig` 的 operational 说法改为「生成用 `make inst-signature-data`；执行判据见 `check-idl`」。
5. 不改 `expected.tsv`、`signature.py`、`tests/inst` 载体、`check-idl` 本身。

## 不做

- 不删 `check_inst_sig.py`（`--write` 仍是 `expected.tsv` 的唯一生成入口）；
- 不改历史任务书 / `.tao/archive/**`。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动 `Makefile`、`tools/testcases/inst/check_inst_sig.py`（docstring/usage）、`docs/Process-07`、`tools/testcases/README.md`、`tests/data/inst-signature/README.md`、本任务书；
- 完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl` rc=0（272/272）；`make check-inst-asm` rc=0（未被影响）；
2. **L2 成员断言（现场派生）**：`_locked-check-modules` 的前置列表里不含 `check-inst-sig`（从 Makefile 文本现场解析，不写死）；`GATE_LOCKED_TARGETS` 同样不含；
3. `python3 tools/testcases/inst/check_inst_sig.py --help` 可运行；`make inst-signature-data` 目标仍在（**不执行 `--write`**，避免重写期望；只断言目标存在且脚本可解析）；
4. **可达 FAIL 2 路**：① 把 `check-inst-sig` 加回 `_locked-check-modules` 前置 ⇒ 成员断言红；② 在 `docs/Process-07` 的 L2 行加回该名 ⇒ 文档一致性断言（grep 口径）红；均 `cp`+md5 还原后回绿；
5. `check-manifests-guard`/`check-dirs` rc=0。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
