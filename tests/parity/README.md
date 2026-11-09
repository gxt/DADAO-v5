# `tests/parity/` — M11 跨引擎同模式一致性矩阵（入库快照）

本目录**不是**新的测试用例/向量体系，也不拥有任何期望值（`ADR-0048 D3`）。

- 全部 case 复用现有清单/驱动派生：`tests/inst/**`、`tests/arch/umon/expected.yaml`、
  `Makefile::ARCH_CFX_PROBES` + `min_rom_probe_046t` 的 `--list`、Embench 源树、
  picolibc Meson 清单。
- 驱动：`tools/testcases/parity/run_parity.py`（用法/case ID/退出码/例外见其
  `README.md`）；SE user 模式（static + dynamic）的 tset 对账段由
  `tools/testcases/parity/se_tset_matrix.py` 汇总。
- `matrix-M11.md` 是**现场生成的快照**：FS 段由 `run_parity.py` 输出、末尾「SE
  tset matrix」段由 `se_tset_matrix.py` 输出，两段由收口任务的证据脚本
  `cat` 拼接后 `cp` 入库，计数逐项来自证据 JSON，**不手改**。

## 矩阵口径

| profile | inst | arch | embench | picolibc |
| --- | --- | --- | --- | --- |
| tiny | 适用全集（universal + explicit tiny） | `N/A`（`machine-profiles.yaml` `tiny.arch=false`） | 全 benchmark × O0/O2 | 旁证（`--stage fast`，不参与硬门） |
| vast | 适用全集（universal + explicit vast） | 10 smoke + 13 probes + `046t` | N/A（**历史**；M11 Vast 不跑 embench） | 不跑（`vast.picolibc=false`） |

- **Vast embench = 历史，不计入 M11 Vast 验收**：`GEM5-016t`/`QEMU-080t` 的 Vast
  `inst`/`embench` 结果仅作历史参考；M11 起 `vast/embench` 不再生成。

- 硬门：`QEMU PASS ⊆ gem5 PASS`，且同 case 的 exit/架构可见结果一致；
  `GEM5_ONLY_FAIL == 0`。
- `QEMU_ONLY_FAIL` 逐条列名，交主会话另立 QEMU 调试任务；不阻断本矩阵。
- `BLOCKED`/`N/A` 逐条给根因（真实能力缺口、gem5 侧缺陷登记、
  picolibc B7 等），不得静默通过或改写成 PASS。
- 只比较 status/exit/架构可见结果；**不比较**时序、性能、PC/日志格式
  （`ADR-0048 D1/D2`）。

## 重新生成

```sh
# 1) FS 段：QEMU system ↔ gem5 FS 全量矩阵
python3 tools/testcases/parity/run_parity.py --profiles tiny,vast \
  --scopes inst,arch,picolibc --jobs 16 --timeout 600 \
  --work-dir <运行期目录>/run \
  --json <运行期目录>/matrix.json \
  --markdown <运行期目录>/matrix.md

# 2) SE 段：gem5 SE ↔ QEMU user 的 tset 双档对账（读已入库基线）
python3 tools/testcases/parity/se_tset_matrix.py \
  --json-out <运行期目录>/se-parity.json \
  --markdown-out <运行期目录>/se-parity.md \
  --matrix-section-out <运行期目录>/matrix-M11-SE.md

# 3) 拼接入库（FS 段 + picolibc 承接段 + SE 段；承接段不手改，见下）
python3 tools/testcases/parity/se_tset_matrix.py \
  --compose-out <运行期目录>/matrix-M11.md \
  --fs-matrix <运行期目录>/matrix.md \
  --carry-from tests/parity/matrix-M11.md
cp <运行期目录>/matrix-M11.md tests/parity/matrix-M11.md
```

`--carry-from` 读取上一版快照的 `tiny/picolibc` 行原样承接（`math_test` B7 登记
不变：现引擎复测为 0 errors，但按任务约束不改写为 PASS，裁定待定）。

`se_tset_matrix.py` 的 per-case 归因与 static/dynamic 对照见
`.tao/knowledge/refs/INTEG-059t-se-parity-summary.md`。入库快照只允许 `cp`/脚本
输出；不要手改数字。
