# m16-testcases-015: `tests/arch` 运行模式环境（hmon/smon/umon）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-006`（骨架）、`m16-testcases-005`（签名）已合入
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景（用户 2026-11-22）

`tests/arch` 现在每个载体自己决定运行模式：`umon/*.s` 有的经 SEE bootrom 进 user、有的 body 在 hypv；`ptw` 的 body 固定 hmon；`cache` 的 RTL 探针固定 hmon。用户要求：**增加 hmon/smon/umon 的构建环境，让多数测试能在不同运行模式下运行**。

目标是把「测试 body」与「运行模式环境」分离：body 一份，env 负责进入指定模式、设栈、装异常向量、退出与签名区；`run_arch.py --mode hmon|smon|umon` 选择环境。

## 要做

1. **env 目录**：`tests/arch/common/env/{hmon,smon,umon}/`，每个含：
   - 启动/进入：从 BootROM 或 prelude 进入目标模式（`switch_run_mode`/`trap`）；
   - 链接布局与栈；
   - 异常向量/回落槽；
   - 退出：semihosting `SYS_EXIT`；
   - 签名区：复用 `tests/shared/signature.inc`。
2. **驱动**：`run_arch.py` 增加 `--mode hmon|smon|umon`；默认 `hmon`；不支持的组合 fail-closed。
3. **用例元数据**：`tests/arch.yaml` 或用例旁增加 `modes: [hmon,smon,umon]`（每用例允许集）；不能在该模式运行的用例显式标注原因（如 cfx0 的 user 进入本身依赖 U-mode）。
4. **代表迁移**：选 1 个不依赖特定模式的用例（建议 ptw 的寄存器面或 cache 寄存器面）迁移为「body + env」，在 hmon/smon/umon 三模式各跑一次；签名一致（或按权限差异登记）。
5. **未覆盖登记**：列出仍需逐件迁移的用例清单；本任务不迁全部。

## 不做

- 不迁移全部用例（后续逐件）；
- 不改测试语义/期望；
- 不改 QEMU/gem5/RTL 实现。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `tests/arch/**`、`tests/arch.yaml`、`tests/arch/README.md`、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 代表用例在 hmon/smon/umon 三模式各跑一次，签名逐槽一致；若某模式因权限不可用，必须显式 fail-closed 并写明原因，不得静默跳过；
2. `modes` 元数据现场校验（缺项/非法模式 ⇒ 红）；
3. **可达 FAIL**：注入「env 模式写错」⇒ 进入错误模式/签名红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路；
5. 未迁移用例清单存在且可读。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
