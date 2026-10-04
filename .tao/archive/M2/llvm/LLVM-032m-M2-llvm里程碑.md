# LLVM-032m: M2 llvm 里程碑

**模块**：llvm
**项目里程碑**：M2
**状态**：里程碑
**目标**：LLVM MC 层随 M2 收口——双目的/多寄存器指令渲染、新汇编语法与立即数字节化、注释符 `;`（`#` 非法）；`ret rd0`、`mreg_range_overlap`、FP 编码层（60 条）、FP 汇编期静态合法性（`dst_rf0`/`mreg_range_overlap`/`mreg_range_overflow`/`encode_fp_root_n`）与 `dst_rd0@FP` 静态检查落地；`check-lit` 全绿、`check_lit_bytes`/`test_encoding_oracle` 通过。
**关联任务**：`LLVM-017t`、`LLVM-018t`、`LLVM-019t`、`LLVM-020t`、`LLVM-021t`、`LLVM-022t`、`LLVM-023t`、`LLVM-024t`、`LLVM-025t`、`LLVM-026t`、`LLVM-027t`、`LLVM-028t`、`LLVM-029t`、`LLVM-030t`、`LLVM-031t`（15 个）

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出是否存在：`components/llvm-project/patches/**`（现 69 = llvm 37 + qemu 32）、`tests/lit/MC/Dadao/*.s`、`tools/llvm/{check_lit_bytes,test_encoding_oracle}.py`
- `check-lit`（MC+E2E）全绿；`check_lit_bytes` / `test_encoding_oracle` 通过

## 核验记录（2026-10-04，architect 核验）

**关联任务**：`LLVM-017t`~`LLVM-031t`（15/15）全部 `已验证`。

**命令核验（真实输出，2026-10-04）**：
```
$ make check   → `check-lit`: Total Discovered Tests 31 / Passed 31 (100.00%)；EXIT=0
                 （含 fp-encoding.s、fp-legality.s、fp-dst-rd0-legality.s、ret-rd0-legality.s、overlap-legality.s）

$ python3 tools/llvm/check_lit_bytes.py ; echo rc=$?
check_lit_bytes: 113 patterns OK
rc=0

$ python3 tools/llvm/test_encoding_oracle.py
Results: 121 passed, 0 failed out of 121 tests
Cross-check OK: oracle tests (121) >= lit OBJ lines (113)
```
（`check-lit` 为 `make check` 成员；`check_lit_bytes`/`test_encoding_oracle` 为 llvm 侧证据。完整 `make check` 输出见 `.work/log/integ/M2-milestone-make-check.log`。）

**跨模块影响**：FP 编码/合法性由 spec 合约（`contract-fp.md`/`contracts/fp_semantics.yaml`）投影，`check-fp-contract`/`check-scope`/`check-rule-refs` 全绿；与 qemu 运行期半边（`QEMU-038t`）配套闭合 ⇒ 无未处置项。

**结论**：核验通过，置 `里程碑`。
