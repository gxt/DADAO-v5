# m16-testcases-020: tests/arch 收尾（cfx5 I+D 同选 + 失败形态时限/日志）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-009` 合入；`m16-testcases-012` 已合入
**可并行分片**：否（共享 `tests/arch/cache/`、`common/`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

- `ISS-517`：`m16-chipyard-017` 的 cfx5 维护探针缺「I+D 同选 + 合法操作」用例（`CTRL_ID_*` 只有 none/非法）⇒ `CACHE-21` 的"先 I 后 D"只有静态核验；`m16-testcases-009` 已补三方 cache 用例，但同选项仍缺。
- `ISS-522`：`tests/arch` 的 smon/umon 异常路径失败形态过重——载体未装载当前模式监视器时只能等 60 s 超时，且 carrier 开 `-d cpu`，实测单次失败写约 11.7 GB 日志（tmpfs 16 G 被打满）。

## 要做

1. **I+D 同选用例**：在 `tests/arch/cache/` 增加 `cache_ctrl` 的 I+D 同选 + 合法操作组合（至少 `I|invalidate` + `D|clean`、`I|clean` + `D|invalidate` 各一），三方逐槽或登记差异；映射到 `CACHE-21` 并更新 `vast-arch-inventory.md`。
2. **失败形态收紧**：`tests/arch` 的 carrier/`run_case` 增加"短 timeout"（默认 ≤10 s，可用环境变量放宽）与"失败时关闭/截断 `-d cpu` dump"；确保异常路径判红的形态不再写满磁盘（可注入"未装载监视器"复现）。
3. **不回归**：fence/power/ptw/pmem/time/cache 代表集；`run_arch --self-test`。

## 不做

- 不改模拟器/内核实现；
- 不改用例语义（只补用例与失败路径参数）。

## 约束

- 独立 `git worktree`；**不提交 git**；变更集限 `tests/arch/**`、`tools/testcases/arch/**`、本任务书；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. I+D 同选用例三方（或登记差异）通过，映射 `CACHE-21`；
2. 失败路径：超时 ≤10 s 且日志 ≤ 数百 MB（注入"未装载监视器"实测，贴实际大小）；
3. **可达 FAIL ≥2**：注入"删同选用例"、"把 timeout 改回 60 s/dump 全开" ⇒ 红/可观测；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
