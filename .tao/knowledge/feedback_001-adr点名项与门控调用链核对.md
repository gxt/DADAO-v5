# feedback_001：ADR 点名项须逐字落地核对 + 门控来源须沿调用链核对

> 操作规范（"应该这样做 / 不该那样做"）。来源：`INFRA-047t`（install 落地，2026-10-07）第 1 轮验收后由 architect 范围修正、重开一轮才闭合。

## 背景（触发事件）

`INFRA-047t` 的目标之一是「**门控/执行器改从 install 根取可执行**」（`ADR-0016 D9`）。第 1 轮实现与验收（判 `Accepted`）时，`make check` 的子门控 `check-qemu-semantics` 仍经 `tests/scripts/run_qemu_test.py` 从 `.work/build` 取 QEMU——**未被发现**：任务书把 `D9` 点名清单**改述**为「`Makefile` 路径变量 + `tools/integ/run_{codegen,elf}_e2e.py` + `tests/**/lit.cfg.py`」，漏掉 `D9` **原文点名**的 `run_qemu_test.py`；下发前预检又把验收 grep 范围收窄到 `Makefile`+`tools/infra`+`tools/integ`，使该缺口在验收中**不可见**。reviewer 在 B 节已瞄到，但因「超出任务界定」未阻塞判决。

## 规律（应固化）

1. **ADR/规范逐个点名一类产物时，任务界定与验收范围须「逐字列出、逐项核到底」**，不得以概括措辞替代点名清单。
   - 反例：`D9` 原文「门控/执行器（**`run_qemu_test.py`**、lit、各 `check_*`）改从 install 根取可执行」；改述后漏掉点名脚本。
   - 做法：把点名项**原样抄进**任务书「范围」与「验收 grep 范围」，逐项给「已落地 / 不适用 / out-of-scope（附证据）」的结论。

2. **核对「门控可执行来源」须从 `make check` 依赖表出发，沿门控→脚本→可执行/子脚本的调用链逐跳追**，不能只 grep 工具目录（`tools/`）。
   - `make check` 的子门控常经**脚本间接**取可执行：`check-qemu-semantics` → `tests/scripts/run_qemu_test.py`；`check-interface` → `tools/integ/check_interface_alignment.py` → `tools/llvm/check_lit_bytes.py` + `tools/qemu/check_qemu_trans.py`。
   - 因此 grep 范围须覆盖**全部被调脚本所在目录**（含 `tests/scripts/`）；只 grep `Makefile`+`tools/**` 会漏 `tests/scripts/` 下的门控执行器。

3. **「是不是门控/执行器」须用调用链证据判定，不能因「同款写法」或「同目录」类推。**
   - 反例：`tests/scripts/verify_harness_dump.py` 与 `run_qemu_test.py` **同款**硬编码 `.work/build`，但经全仓 grep（含 `import` / `subprocess` / 动态遍历）确认**无任何门控调用它** ⇒ 判 **out-of-scope（保留）**，而非「顺带一起改」。
   - 做法：判定 out-of-scope 须给出**调用链反证**（全仓 grep 该脚本名 + 门控脚本对其的 import/subprocess 均无命中），并登记为可另立任务的遗留。
