# `tests/parity/` — M11 跨引擎同模式一致性矩阵（入库快照）

本目录**不是**新的测试用例/向量体系，也不拥有任何期望值（`ADR-0048 D3`）。

- 全部 case 复用现有清单/驱动派生：`tests/inst/**`、`tests/arch/umon/expected.yaml`、
  `Makefile::ARCH_CFX_PROBES` + `min_rom_probe_046t` 的 `--list`、Embench 源树、
  picolibc Meson 清单。
- 驱动：`tools/testcases/parity/run_parity.py`（用法/case ID/退出码/例外见其
  `README.md`）。
- `matrix-M11.md` 是**现场生成的快照**：由重生成该快照的任务证据脚本（当前快照对应
  `TESTCASES-098t`）从全量矩阵 `cp` 而来，计数与差异逐项来自证据 JSON，**不手改**。

## 矩阵口径

| profile | inst | arch | embench | picolibc |
| --- | --- | --- | --- | --- |
| tiny | 适用全集（universal + explicit tiny） | `N/A`（`machine-profiles.yaml` `tiny.arch=false`） | 全 benchmark × O0/O2 | 旁证（`--stage fast`，不参与硬门） |
| node | 适用全集（universal + explicit node） | 10 smoke + 13 probes + `046t` | N/A（**历史**；M11 Node 不跑 embench） | 不跑（`node.picolibc=false`） |

- **Node embench = 历史，不计入 M11 Node 验收**：`GEM5-016t`/`QEMU-080t` 的 Node
  `inst`/`embench` 结果仅作历史参考；M11 起 `node/embench` 不再生成。

- 硬门：`QEMU PASS ⊆ gem5 PASS`，且同 case 的 exit/架构可见结果一致；
  `GEM5_ONLY_FAIL == 0`。
- `QEMU_ONLY_FAIL` 逐条列名，交主会话另立 QEMU 调试任务；不阻断本矩阵。
- `BLOCKED`/`N/A` 逐条给根因（QEMU `-icount` 无 atomic 对应、gem5 侧缺陷登记、
  picolibc B7 等），不得静默通过或改写成 PASS。
- 只比较 status/exit/架构可见结果；**不比较**时序、性能、PC/日志格式
  （`ADR-0048 D1/D2`）。

## 重新生成

```sh
python3 tools/testcases/parity/run_parity.py --profiles tiny,node \
  --scopes inst,arch,embench,picolibc --jobs 8 --timeout 600 \
  --work-dir /tmp/opencode/qemu-gem5-parity/run \
  --json /tmp/opencode/qemu-gem5-parity/matrix.json \
  --markdown /tmp/opencode/qemu-gem5-parity/matrix.md
```

入库快照只允许 `cp` 现场 Markdown；不要手改数字。
