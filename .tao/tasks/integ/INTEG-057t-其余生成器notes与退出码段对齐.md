# INTEG-057t: 其余向量生成器 notes 与退出码段对齐

**模块**：integ
**项目里程碑**：M11
**依赖**：`INTEG-055t`（已验证；退出码三段式迁移）、`INTEG-056t`（生成器 `ctrl-jump/call/ret` 对齐）
**状态**：待开始

## 执行环境
本地；只改生成器内的 notes 文本/渲染格式并重渲染，不改向量语义、期望值、判据。

## 现状

`INTEG-055t` 手工改了 `tests/inst/base/*.yaml` 的 notes（删旧退出码、把 `0x81` 改「monitor」），但只同步了部分生成器。`INTEG-056t` 修完 `generate_ctrl_jump_call_ret.py` 后，L2 `check-generator-sync` 仍红在这三个：

```
generate_ctrl_br --check: FAIL          （tests/inst/base/ctrl-br.yaml）
generate_mem_vectors --check: FAIL      （tests/inst/base/mem-ra.yaml / mem-rb.yaml / mem-rd.yaml）
generate_misc --check: FAIL             （tests/inst/base/misc.yaml，纯渲染格式/换行）
generate_isa_vectors / generate_bitcnt_vectors --check: PASS
```

## 目标

1. 逐个生成器比对「重渲染结果」与「已入库 yaml」，把差异**逐条归类**：notes 文本 / 纯格式（引号、折行、空行）/ 语义字段（`expected_fault`/`expected_state`/`expected_pc`/`encoding.word`/`spec_cite`/用例集）。
2. 对 **notes 与纯格式**差异：以已入库 yaml 为准，改生成器使其重渲染 byte-identical。
3. 对 **语义字段**差异：停止并报告（列出字段、用例、两侧值），不得擅自改 yaml 或生成器期望值等待裁定。
4. 三册（`ctrl-br`、`mem-*`、`misc`）全部 `--check` rc=0；yaml 零改动。

## 范围 / 非范围

**在范围内**：`tools/testcases/generate_ctrl_br.py`、`tools/testcases/generate_mem_vectors.py`、`tools/testcases/generate_misc.py`（仅 notes 字面量 / 渲染格式）、本任务书、`milestones.md`。

**不在范围内**：`tests/inst/base/*.yaml` 内容、`spec/**`、ADR、`contracts/**`、QEMU/gem5 源树与补丁、`generate_ctrl_jump_call_ret.py`（`INTEG-056t` 已修）。

## 验收标准

1. 三个生成器 `--check` 均 rc=0（逐册 byte-identical）。
2. `git status --porcelain -uall` 不含 `tests/inst/base/*.yaml`。
3. `make check-generator-sync` rc=0（6 个生成器全绿）。
4. `make check`（L1）rc=0；`make check-modules JOBS=32` rc=0（若有其它失败，逐条给归属并区分环境红）。
5. 反例：任一生成器 notes 改回旧退出码（如 `0x81`/`0xFA`）⇒ 该 `--check` rc=1；`cp`+`md5sum -c` 还原回绿（禁 git 还原）。
6. 差异归类清单写入完成区（每个文件一行：差异类型 + 处数）。
7. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 方向同 `INTEG-056t`：生成器对齐产物，不是产物对齐生成器。
- 若 `misc.yaml` 差异纯属 PyYAML 版本渲染差异（同一版本下重渲染仍不等），需给出最小复现与版本信息，再决定是否改渲染实现；不得放宽 `--check`。
