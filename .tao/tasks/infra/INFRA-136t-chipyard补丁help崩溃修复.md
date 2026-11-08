# INFRA-136t: chipyard 补丁集（`--help` / 非法参数不再崩溃）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-133t`（节点 chipyard 环境已就绪）
**状态**：待开始

## 背景与事实

`sims/verilator` 的仿真器在执行 `--help`（以及任何非法参数）时崩溃：

```
$ ./simulator-chipyard.harness-RocketConfig --help
[打印 Usage: … EMULATOR OPTIONS …]
terminate called after throwing an instance of 'std::invalid_argument'
  what():  User queried htif_t help text
rc=255
```

gdb `catch throw` 的调用链（实测）：

```
#1 htif_t::parse_arguments        fesvr/htif.cc:337   ← throw
#2 htif_t::htif_t                 fesvr/htif.cc:61
#3 tsi_t::tsi_t                   fesvr/tsi.cc:16
#4 testchip_tsi_t::testchip_tsi_t
#5 tsi_tick()                     SimTSI.cc           ← DPI 回调
#6 VTestDriver___…tsi_tick        （仿真模型求值中）
#11 VTestDriver::eval_step()
#12 main()                        Verilator --main 自动生成，无 try/catch
```

根因：`SimTSI.cc::tsi_tick()` 在**第一个时钟 tick** 里才 `new testchip_tsi_t(info.argc, info.argv, true)`，构造函数链走到 `htif_t::parse_arguments`；`-h` 分支先 `usage()` 再 `throw`，而自动生成的 `main()` 没有 catch ⇒ `std::terminate`。`--disk` 等非法参数同样崩溃。

用户裁定（2026-11-08）：「A」——**修**，不是记为已知缺陷。

## 目标

1. 在 `generators/testchipip/src/main/resources/testchipip/csrc/SimTSI.cc` 的 `tsi_tick()` 中，把首次构造包进 `try/catch`：
   - `-h`（`invalid_argument("User queried htif_t help text")`）⇒ 打印信息后 `std::exit(0)`（usage 已由 fesvr 打印）；
   - 其它 `std::exception` ⇒ 打印 `what()` 后 `std::exit(1)`，不再 `terminate`。
2. 把 `components/chipyard` 从 **patchless** 转为**受补丁组件**：`manifests/components.lock.toml` 用 `patch_dir`/`patch_series` 取代 `patchless = true`；新增 `components/chipyard/{patches/…,series,changelog.md}`。
3. 不改 chipyard 的其它行为；补丁必须最小（只动 `SimTSI.cc`）。

## 范围 / 非范围

**在范围内**：`.work/source/chipyard` 的该文件、`components/chipyard/**`、`manifests/components.lock.toml`（仅 chipyard 条目）、本任务书、`milestones.md`。

**不在范围**：`SimTSI.cc` 以外任何 chipyard 文件、Verilator 版本、`INFRA-133t` 的任务书（其判据由 architect 在合并后统一改）、其它组件。

## 验收标准

1. **补丁最小**：`git -C .work/source/chipyard diff --stat` 只有 `SimTSI.cc` 一个文件；`components/chipyard/patches/**` 非空、`series` 列全。
2. `check-patch-tree` rc=0（chipyard 已按受补丁组件校验）；`check-source-state` rc=0（源树 clean 且 base+1 与补丁一致）。
3. `make apply-series` 幂等：再跑一次判定「already applied」并 rc=0。
4. **行为验证**（在节点上由 architect 执行，本任务需提供可复现命令）：重建后 `--help` ⇒ **rc=0**、输出含 `Usage:`；非法参数（如 `--disk`）⇒ rc≠0 且**无** `terminate called`。
5. L1 rc=0（`check-patch-tree` 转受补丁后不得引入红）。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- 这是本仓库**第一个 chipyard 补丁**，`components/chipyard/changelog.md` 须写明动机（上游 help 崩溃）、影响面（仅参数解析失败路径）与回退方式。
- 补丁从源树导出，遵循 `docs/Process-01`（树形补丁集、一文件一补丁、`git apply` 应用），不要手写 patch 文件。
- 重建与真机验证由主会话在节点执行（长任务），本任务负责补丁与清单正确性。
