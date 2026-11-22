# m17-idl-014: 全四方进 `night-run`（gem5/chipyard 常驻门控）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-013`（门控翻到 272/272、`idl/tools/` 新布局）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定 B）

`make check-idl` 在 L2 只跑 IDL+QEMU；全四方（IDL/QEMU/gem5/chipyard）目前没有任何常驻门控，只在任务收口由证据脚本人工跑一次 ⇒ gem5/RTL 侧漂移无人守。裁定 B：**全四方进 `night-run`**，L1/L2/L3 不变（L2 仍两方）。

现状（现场）：`night_run.py` 的 `DEFAULT_MEMBERS` = `tset:libc-test`/`llvm-ts`/`embench` + `arch:cfx` + 3 个 `tset:gem5-se-*` + `arch:gem5-fs`；`check_night_report.py` 的 `REQUIRED_MEMBERS` 是同一组 8 个；night-run 用独立锁 `.dadao/night.lock`，**不占** `gate.lock`。

## 要做

1. `Makefile` 新增目标 `check-idl-full`（**不进** `GATE_LOCKED_TARGETS`）：
   - `$(PYTHON) idl/tools/idl_four_way.py --platforms qemu,gem5,chipyard --jobs $(TEST_JOBS)`；
   - 日志落运行期日志目录内的 `check-idl-full.log`；缺任一引擎/固件 ⇒ rc=2（可见，不静默跳过）；
   - help 行注明「nightly 成员；全四方」。
2. `tools/testcases/night_run.py`：`DEFAULT_MEMBERS` 追加 `idl:four-way=make check-idl-full`；`MEMBER_TIMEOUTS` 加 `("idl","four-way"): 1800`；模块 docstring 的成员清单同步。
3. `tools/testcases/check_night_report.py`：`REQUIRED_MEMBERS` 加 `("idl","four-way")`；docstring 的「四 scope / 八成员」改为现场口径（不写死数）。
4. `docs/Process-07`：登记 `check-idl-full` = **nightly 成员**（不进 L1/L2/L3），并注明 L2 `check-idl` 仅 IDL+QEMU。
5. 不改 013 的语义、清单与门控口径。

## 不做

- 不改 `check-idl`（L2）的平台集；不改 272 条清单；不改 `.idl`/执行器；
- 不把 nightly 成员升成提交前门控。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动上述 4 个文件 + 本任务书；完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl-full` rc=0（贴 272/272、耗时、四方 md5）；
2. `NIGHT_DRY_RUN=1 make night-run` 打印的成员清单含 `idl:four-way`（现场统计条数）；
3. `check-night-report`：用一份**构造的** night 报告（含新成员）判 PASS；删掉 `idl:four-way` 行 ⇒ FAIL（可达）；
4. **可达 FAIL ≥2 路**：① `--platforms qemu,gem5`（少 chipyard）⇒ rc=2「缺引擎」，证明不会静默跳过；② 把 `REQUIRED_MEMBERS` 的 `idl:four-way` 去掉后用同一报告 ⇒ 覆盖断言失效（反向证明新增项确实被核）；
5. `make check-idl`（L2 两方）仍 rc=0，未被改动。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
