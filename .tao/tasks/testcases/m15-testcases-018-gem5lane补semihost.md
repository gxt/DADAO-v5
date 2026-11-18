# m15-testcases-018: `run_inst_tiny.py` 的 gem5 lane 补 `--semihost on`

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m16-gem5-011`（`fs.py` 的 `--semihost` 默认改 `off`）
**可并行分片**：否
**预估**：0.5–1 h
**档位**：小改
**状态**：待开始

## 背景（`m16-gem5-013` 复核发现）

`m16-gem5-011` 已把 `configs/dadao/fs.py` 的 `--semihost` 默认改为 **`off`**（显式开），但 `tests/ee-tiny/run_inst_tiny.py` 的 gem5 lane **没有同步补 `--semihost on`**：

```python
cmd = [gem5, "--outdir=…", config, "--profile", "tiny",
       "--bootrom", …, "--kernel", …, "--console-out", …]
# 缺 --semihost on
```

后果：`--platforms gem5` 时载体跑不出 semihosting 输出 ⇒ **必然超时/判红**，与实现无关。

## 目标

1. `tests/ee-tiny/run_inst_tiny.py` 的 `run_gem5()` 命令补 `--semihost on`（位置与其它参数同风格）。
2. 全仓核查同类消费者是否也漏（`grep -rn "configs/dadao/fs.py"` / 调用 `fs.py` 的脚本），逐条列出并处置（补参数或说明为何不需要）。
3. 若 `--semihost` 还有配套参数（`--semihost-argv`/`--semihost-system`）在载体链路中必需，一并确认；不需要则在完成区说明。

## 验收（逐条贴真实 rc）

1. `python3 tests/ee-tiny/run_inst_tiny.py --platforms gem5 --only <一个载体 id>`（或等价最小调用）⇒ **不再超时**，输出与 QEMU lane 一致（同一 id）。
2. **可达 FAIL**：把 `--semihost on` 临时去掉 ⇒ 该调用**超时/失败**；还原 ⇒ 通过（`cp`+md5）。
3. 全仓 grep 结论：列出所有调用 `fs.py` 的脚本，逐个标「已带/不需要/需补」。
4. `check-tests-index`、`check-dirs`、`check-no-residue` rc=0。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. 只动 `tests/ee-tiny/run_inst_tiny.py`（+ 同批发现的同类消费者）+ 本任务书。
3. 不改 gem5 组件（`--semihost` 默认 `off` 是既有裁定，不动）。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（无）

## 审阅记录

（待填）
