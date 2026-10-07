# TESTCASES-035m: M5 testcases 里程碑

**模块**：testcases
**项目里程碑**：M5
**状态**：待开始
**目标**：测试向量支持 M5——① **SEE/HEE + semihosting 向量**（L1 MC：`trap`/`escape`/`cfx2rc`/`cfx2rd` 编码/往返，`UNSUPPORTED:` 分阶段；L3 执行：semihosting 服务/权限反例/一般 trap+escape），**独立 oracle**（禁从 LLVM/QEMU 反填）；② **exit-port → `SYS_EXIT` 迁移**（范围 = **全部**：M1–M4 所有依赖 exit-port 的向量/harness/oracle；期望值同步；迁移后全量重跑逐项不回归；`ISS-147` 随迁处置/结案）。
**关联任务**：`TESTCASES-033t`、`TESTCASES-034t`（2 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tests/llvm/lit/MC/DADAO/m5-*.s`（+ `README-m5.md`）、`tests/llvm/codegen/m5/`（+ `expected.yaml`）、oracle（`validate_*.py`）；迁移后的向量/harness/oracle
- 独立 oracle EXIT=0；oracle 无 `subprocess`/`os.system`/`Popen`（`grep` rc=1）
- L3 执行经 m5 驱动跑通（逐例「名字/期望/实际/退出码」）
- 迁移覆盖：`grep` 显示无残留依赖 exit-port 的测试侧（或仅披露例外）；期望退出码全落 `0x00–0x7F`（`ISS-147`）
- 不回归：`test-codegen` 15/15、`test-elf` 5/5、`check-lit`、`check-qemu-semantics` 逐项相等
- 反例门控：改期望字节/服务号/退出码 ⇒ 非零 ⇒ 还原回绿
- `make check`/`check-no-residue` EXIT=0

## 核验记录（主会话）

（核验命令、输出与退出码；结论）
