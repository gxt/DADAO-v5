# m16-gem5-022: I 侧自修改实证 + monitor 脏行修复

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-021`（cfx5 命令）合入
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定）

`m16-gem5-021` 报“I 侧 invalidate 后取指仍执行旧字”，但检查发现：

- gem5 `DadaoL1DCache` 是**写回**；现有 `cfx5_selfmod.s` 是 base probe（无 cfx5、无 `D|clean`），不能证明 cfx5 I 侧不可用；
- RTL `WumingCache` 是 **VIPT**，但索引在 64 KiB 页内（`PA[15:0]==VA[15:0]`，无别名）⇒ 用 PA 索引/标签正确，021 的 `Request::PHYSICAL` 不是错。

用户选 B（修 gem5 自修改支持），但采纳“先证伪”的拆法：本任务先补**正确构造**的 I 侧用例；只有它仍失败，才立 `m16-gem5-023` 改取指侧模型。同时修 021 发现的 020 接线隐患。

## 要做

1. **正确 I 侧自修改用例**（落 `tests/arch/cache/` 或运行期证据）：
   - 写新指令到代码行；
   - `cfx5 cache_ctrl = D | clean | 单行`（必要时区间）把脏行写回内存；
   - `cfx5 cache_ctrl = I | invalidate | 同一 PA`（单行/区间）；
   - 跳转到该地址取指，断言执行**新指令**。
   - 单行与区间各至少 1 例；同一 ELF 在 `cache-model=on` 下跑。
2. **判定**：
   - 若用例 PASS ⇒ 记录“021 不缺命令层，只是缺正确用例”，不立 023；
   - 若用例 FAIL（已 clean D）⇒ 保留现场、写清证据，交给 `m16-gem5-023`（改 `src/cpu/simple/**` 或取指缓冲），本任务不改模型。
3. **修 020 的 monitor 脏行隐患**：`cache-model=on` 的 Vast BootROM 把 monitor 段经 D-Cache 拷入且不写回；`D|invalidate|all`（或对 monitor 行单行 invalidate）会打掉 monitor，下一次异常进入即 `UNDI` 死循环。修法二选一：
   - monitor/BootROM 段写入走直连/写穿（不进 D-Cache）；
   - 或启动移交后对 monitor 行 `D|clean`（写回），并在文档写明。
   验收：`D|invalidate|all` 后触发一次异常，monitor 仍能处理（不死循环）。
4. **不回归**：021 的 D 侧语义（clean/invalidate/flush、范围/使能/异常）、`off` 下 01 册 38/38 与 `run_m5_e2e --profile vast` 10/10。

## 不做

- 不改 `src/cpu/simple/**`（留给 023，仅当本任务证伪失败）；
- 不改 cfx5 寄存器/命令语义（021）；
- 不改 QEMU/chipyard。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py gem5` 幂等；
- 不写运行期路径；术语「寄存器组」；
- 证据脚本记录重建耗时与环境。

## 验证

运行期证据目录内的 `run.sh`：

1. 新 I 侧用例（单行、区间）在 `on` 下 PASS；若 FAIL，给出“已 clean D 仍旧字”的完整现场并标记 023；
2. `D|invalidate|all` 后异常进入 monitor 不死循环（修复前复现、修复后通过）；
3. `off` 下 01 册 38/38、vast 10/10；021 的 D 侧用例不回归；
4. **可达 FAIL**：注入「不 clean D」⇒ 新用例应按预期失败（证明用例确实依赖 clean）；注入「monitor 段仍走 D-Cache」⇒ invalidate 后死循环复现；`cp`+md5 还原并重建回绿；
5. `check-gem5-decode`、`check-patch-tree` gem5 段、`check-index-blobs`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
