# m16-chipyard-029: Vast 当期构建 `cfx15.S` 不收敛（启动链）根因与修复

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-027`、`m17-chipyard-001` 已合入（两者都在当期共享树里）
**可并行分片**：否（`components/chipyard` 单写者 / 共享源树）
**预估**：2–4 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景（`m16-gem5-026` 复核发现）

- 共享 `.work/source/chipyard` 当期构建（13ef828，11-25 10:10，Vast sim md5 `53c367f6…`）上，`tests/arch/hart/cfx15.S` 在驱动固定 `+max-cycles=8000000` 内**不收敛**：`$stop`、0 槽；直接 `+max-cycles=1000000` 也在 1.05M cycle 内 **`_start` 重启 881 次**。
- 11-24 17:50 的旧构建（`f39a0c6`，补丁集 024/025/026/022-WIP，**缺 023/027/m17-chipyard-001**）同一 ELF <300k cycle 完成、80 槽过 oracle ⇒ 问题在**新补丁集**（023/027/m17-chipyard-001 的组合）而非探针本身。
- 影响：gem5-026 的 F2（当期构建复跑三方）、`m16-gem5-025/028/022/023` 的 RTL 腿、M16 `check-arch-vast` 与收口报告都不可信。

## 要做

1. **复现与定位**：在共享树上确认 `_start` 重启；用 `+verbose`/boot 信号或最小镜像判断是 power stub 未交付、BootROM 镜像布局、还是 hmon 进入即异常。
2. **二分**：以 master 补丁集为基准，按 023 → 027 → m17-chipyard-001 的补丁范围做最小裁剪（隔离树，不动共享树直到结论），找出引入点；若为组合效应，给出两者交互的证据。
3. **修复**：按根因修 RTL/镜像/参数（不改 spec；若确为 spec 与实现的冲突，登记 issue 并停）。
4. **回归**：修复后 Vast 重建，`cfx15.S`/`pmem`/`ptw`/`time`/`cache` 代表集在当期构建上跑通；`arch-hart-001`（80/40 槽）、`arch-pmem-001`（55 槽）。
5. **登记**：根因、引入点、修复面写进 issue（`ISS-m16-008` 已开）；若属 m17-chipyard-001 的回归，同步 M17 台账。

## 不做

- 不改 spec/契约；
- 不借机改 023/027/m17 的既有语义（除非根因就是它们）；
- 不在本任务做 `cg9 rc6`（028）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py chipyard` 幂等；
- 共享源树被他人占用时用隔离树（`rsync`/`git worktree` 副本），不得抢写；
- 失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 当期构建上 `cfx15.S` 在 `8e6` cycle 内完成、80/40 槽过 oracle；`_start` 不重启；
2. 代表集（pmem/ptw/time/cache）RTL 腿不回归；
3. **可达 FAIL**：注入"恢复被判定为引入点的改动" ⇒ 重启/挂死复现；`cp`+md5 还原并重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test` 记录 rc；
5. Vast 重建耗时与 sim md5 记录（ISS-453）。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
