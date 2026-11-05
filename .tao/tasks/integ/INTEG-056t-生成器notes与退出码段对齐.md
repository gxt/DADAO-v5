# INTEG-056t: 生成器 notes 与 §7.1 对齐（generator-sync 回绿）

**模块**：integ
**项目里程碑**：M11
**依赖**：`INTEG-055t`（已验证；退出码三段式迁移）
**状态**：待开始

## 执行环境
本地；只改生成器内的 notes 文本并重渲染，不改向量语义/期望值/判据。

## 现状

`INTEG-055t` 把 `tests/inst/base/ctrl-{jump,call,ret}.yaml` 的 notes 里旧退出码（`0x81`/`0x88`/`0x8A`/`0x8B`）删掉或改为「monitor」，但**手工改 yaml**、未同步生成器 `tools/testcases/generate_ctrl_jump_call_ret.py` 里的同名字符串。

L2 `make check-modules` 因此在 `check-generator-sync` 红：

```
FAIL: tests/inst/base/ctrl-jump.yaml 与重渲染结果不一致
FAIL: tests/inst/base/ctrl-call.yaml 与重渲染结果不一致
FAIL: tests/inst/base/ctrl-ret.yaml 与重渲染结果不一致
generate_ctrl_jump_call_ret --check: FAIL
```

## 目标

1. 以**已入库 yaml 为期望**，把生成器里对应的 notes 字符串改成同一文本（共 10 处，diff 见 `git show` 的 `INTEG-055t` 提交：`ctrl-jump` 2 处、`ctrl-call` 3 处、`ctrl-ret` 5 处）。
2. 重跑生成器渲染，确认三册 yaml **byte-identical**（无内容变化）。
3. 不改 `expected_fault`/`expected_state`/`expected_pc`/编码字/`spec_cite`/用例集。
4. 若发现 yaml 与生成器差异不止 notes（语义字段也被手工改），停止并报告，不得擅自改语义。

## 范围 / 非范围

**在范围内**：`tools/testcases/generate_ctrl_jump_call_ret.py`（仅 notes 字面量）、本任务书、`milestones.md`。

**不在范围内**：`tests/inst/base/*.yaml`（期望保持现入库内容不变）、`spec/**`、ADR、`contracts/**`、QEMU/gem5 源树与补丁。

## 验收标准

1. `python3 tools/testcases/generate_ctrl_jump_call_ret.py --check` rc=0（3 册 byte-identical）。
2. `git status --porcelain -uall` 不出现 `tests/inst/base/ctrl-*.yaml`（yaml 未变）。
3. `make check-modules JOBS=32` rc=0（或若仍有其它失败，逐条给出真实 rc 与归属，区分环境红）。
4. `make check`（L1）rc=0。
5. 反例：把生成器某条 notes 改回旧码（如 `0x81`）⇒ `--check` rc=1；`cp`+`md5sum -c` 还原回绿（禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 修复方向是**生成器对齐产物**，不是产物对齐生成器：yaml 里的 notes 已按 `Machine-v5 §7.1` 更新，生成器是滞后的一侧。
- 只动字面量文本；不得为了过门控而放宽 `--check` 判据。
