# `tools/testcases/riscv_tests/` — riscv-tests 移植与差分驱动

任务 `m13-integ-004`。语料与框架在 `tests/riscv-tests/`，本目录只放代码。

| 脚本 | 作用 |
| --- | --- |
| `extract.py` | 从锁定的 riscv-tests 检出分类 114 个 RV64 文件、抽取 `port` 用例，写 `upstream-index.yaml` / `inventory.yaml` / `cases/**`；`--check` 防漂移（需要上游检出） |
| `gen.py` | 把一份 case YAML 生成为 DADAO 汇编（框架宏 + 签名区 + `tohost` 等价退出）；未知助记符显式失败 |
| `verify_cases.py` | 不 import 生成器的独立结构检查 + RISC-V 语义 oracle；`--inject` 证明检查可失败 |
| `run_riscv_tests.py` | 汇编、装载 Tiny raw image，在 QEMU system 与 gem5 FS 上比对退出码 + 签名区；`--inject guest|host` 为证据脚本反例 |

## 判定

- 每个 `port` 文件两条引擎都要求 `exit 0` 且签名区（逐条实际值）与 case YAML 期望完全一致。
- 两平台都通过且签名一致 ⇒ `AGREE_PASS`；两平台产生相同错误 ⇒ `AGREE_FAIL`；否则 `DIFF`（证据脚本按 `AGREE_PASS` 才绿）。
- 期望值来自上游 riscv-tests 用例（已由 `verify_cases.py` 用独立语义模型复核），不从任一引擎反推。
- chipyard 列本任务 `N/A`（核未就绪）；本驱动不尝试连接 chipyard。

## 约定

- 临时/运行期产物只写 `--work-dir`（默认 `/tmp/opencode/m13-integ-004/run`），不写仓库。
- 机器几何从 `tests/shared/machine-profiles.yaml` 派生（Tiny：入口 / 退出块）；不写死其它地址。
