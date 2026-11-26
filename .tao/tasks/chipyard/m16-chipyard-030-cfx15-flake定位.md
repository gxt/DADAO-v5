# m16-chipyard-030: `cfx15.S` 偶发挂死（flake）定位

**模块**：chipyard
**项目里程碑**：M16
**依赖**：无。`m18-chipyard-002/003` 已合入（`cfx15.S` 按 spec-007 重写、cg9/cg5/escape 新布局），`m16-chipyard-033` 已合入（RegRAS 环形缓冲）；chipyard 源树 `7b1d785`、Vast sim `0ead2519…`、Tiny sim `71cbed98…`，安装根 QEMU `e470dc56…`
**可并行分片**：否（共享 `components/chipyard` / `tests/arch/hart`）
**预估**：2–4 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景（`ISS-m16-011`）

`m16-chipyard-029` 复核两次 `+verbose` 实测：`cfx15.S` 偶发 **1/3 次在 99607 cycle 挂死**（其余 104765 cycle 正常完成、80 槽）；`m16-chipyard-028` 复核对约 10 次 RTL 运行 **0 次**挂死。原因未定位，与 `+verbose` 无确定相关。它会让 RTL 三方/收口结果偶发假红。

## 要做

1. **量化**：同一构建、同一 ELF、同一命令跑 **≥20 次**（hmon/smon/umon 各一轮），记录每次 cycle/退出码/槽数；统计挂死频率与是否与模式/时序相关。
2. **定位**：挂死时 dump `+verbose` 尾部与 `_start`/中断/`escape` 痕迹；判断卡在 boot、异步投递、`escape`、还是仿真器（Verilator/harness）；与 `ISS-m16-008` 的"旧 ELF"区别开（本任务是**当期 ELF**）。
3. **修复或收敛**：若是 RTL/探针竞态，修并补可复现用例；若是仿真器/harness 的偶发（如 `+max-cycles` 边界、随机种子、内存模型），给证据并登记为已知 flake（`expected-divergences` 不适用，走 issue 的 GAP）。
4. **回归**：修复后 20 次全绿；代表集不回归（槽数以现场派生为准：当前 `arch-hart-001` 124 槽、`arch-hart-002` S/U 各 38 槽、`arch-pmem-001` 48 槽；`time`/`cache`/`ptw` 代表集按 `tests/arch.yaml` 现取）。

## 不做

- 不改 spec/契约；
- 不做 `cg9 rc6`（028 已完成）；
- 不改 ADWBFAIL（023）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；
- 共享源树被占用时用隔离树；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. ≥20 次重复的 cycle/退出码/槽数表（现场生成，不手写）；
2. 若修复：20/20 全绿 + 代表集不回归；若登记 flake：给出频率、条件、影响与复评条件；
3. **可达 FAIL**：注入"恢复挂死条件"（若能确定）⇒ 复现；`cp`+md5 还原回绿；
4. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
