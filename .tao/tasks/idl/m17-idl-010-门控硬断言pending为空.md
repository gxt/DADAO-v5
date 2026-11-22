# m17-idl-010: 门控硬断言——收口后 `pending` 必须为空

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-009`
**可并行分片**：否
**预估**：30–60 min
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（`m17-idl-009` 复核发现）

`tools/idl/check_four_way.py` 的集合断言是 `主清单 == 现场派生 − pending`。因此「把一条主清单镜像一致地移进 `pending`」仍然 rc=0（主清单 221 / pending 1 / 派生 222，实测）。阶段一已收口（222 例全绿、`pending`=0）；若日后有人把红例移进 `pending`，L2 仍绿，**覆盖会静默缩水**——这正是本任务要堵的口子。

## 要做

1. `tools/idl/check_four_way.py`：在清单断言之后加一条硬断言——`[[pending]]` **必须为空**（段不存在或空数组）；非空 ⇒ rc=2，文案写明「阶段一已收口：能力缺口另立任务，不得用 pending 静默降覆盖」。
2. `docs/idl-four-way.md` §4 与 `idl/README.md` 同步该口径（删掉「一致地暂缓一条允许」的表述）。
3. 保留现成的 `pending` 解析代码，只加断言，不重构。

## 不做

- 不改任何 instruction 语义、不改 `idl/idl_exec_cases.toml` 的 222 条主清单；
- 不改 `tests/inst`、`.idl` 源、`spec/`、`contracts/`、QEMU/gem5/RTL。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动上述 3 个文件 + 本任务书；计数现场派生；完成区 ≤30 行。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl` rc=0（222/222）；
2. **可达 FAIL**：临时给 `idl/idl_exec_cases.toml` 加一条 `[[pending]]`（引用一条已在主清单的镜像的**另一条**合法镜像）⇒ rc=2 且文案含「pending 必须为空」；`cp`+md5 还原后 rc=0；
3. `check-idl-parse`/`check-idl-sync` rc=0；
4. 确认断言**不吃**正常路径：无 pending 时 222/222 仍绿、耗时无明显变化。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
