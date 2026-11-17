# m15-testcases-014: `inst-tiny.lds` 移入 `tests/ee-tiny/`

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-011`（ee-tiny 资产集中，已验证）
**可并行分片**：否（单文件 + 引用）
**预估**：30–60 min
**档位**：小改
**状态**：待开始

## 背景（用户 2026-11-18）

`m15-testcases-011` 把 tiny 的 bootrom/lds 集中到 `tests/ee-tiny/`，但把 `tests/inst/linker/inst-tiny.lds` 作为「inst 测试集布局」排除。用户指出它本质是 **tiny 专属 lds**，应一并集中。

## 目标

1. `git mv tests/inst/linker/inst-tiny.lds tests/ee-tiny/inst-tiny.lds`；`tests/inst/linker/` 若空则删除。
2. 更新引用：`tools/testcases/inst/run_asm_suite.py`（默认 `--lds`/`lds_map`）、`tests/inst/README.md`、`tests/inst/**` 中 `-T`/路径引用、其它 grep 到的调用方。
3. 测试集内容不动（`.S` 不变）。

## 验收（逐条贴真实 rc）

1. 旧路径不存在、新路径存在；md5 一致。
2. `check-inst-asm` **272/272**；`check-tests-index`、`check-dirs`、`check-no-residue` 全 rc=0。
3. `run_asm_suite.py --help` 可运行；1 路注入（引用改回旧路径 ⇒ 红，`cp`+md5 还原回绿）。
4. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：该 lds、调用方/文档、本任务书；**不动**测试集 `.S` 内容、`spec/`、`.tao/contracts/`。
3. **不改版本号**；不提交 git；`cp`+md5 还原。

## 待裁定

（无）

## 审阅记录

（待填）
