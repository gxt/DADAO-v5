# Embench-iot 组件变更记录

> 粒度：**按任务一条**，追加式。补丁集的生成/应用/校验规范见 `spec/Process-01-组件补丁组织与构建编排.md`。

| 日期 | 任务 | 变更 |
|---|---|---|
| 2026-10-09 | `INFRA-051t` | **组件接入骨架**：`manifests/components.lock.toml` 翻 `enabled=true` + 精确 commit `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`（`ADR-0022 D2`）；建 `components/embench-iot/{patches,series,changelog}`；首个补丁 = 新增 `examples/dadao/README.md`（占位，声明无行为；board shim/最小运行时归 `TESTCASES-039t`）。 |
| 2026-10-10 | `TESTCASES-039t` | **DADAO 板级接入**：新增 `examples/dadao/boardsupport.{c,h}`（board shim 3 函数 `initialise_board`/`start_trigger`/`stop_trigger`，经 semihosting `SYS_WRITE0` 打点，证明被 `support/main.c` 调用）；改 `src/md5sum/md5.c`（**大端适配**：`uint32_t*` 重解释 ⇒ 显式小端字序组装 `w[16]` + 小端写长度字段，使 `md5sum` 在大端 DADAO 结果正确）。最小运行时（`mem*`/`str*`/`ctype`/`sqrt`）不在本组件内，落 `tests/scripts/{dadao_mem_runtime.ll（复用）,embench_runtime.c,embench_include/}`。 |
