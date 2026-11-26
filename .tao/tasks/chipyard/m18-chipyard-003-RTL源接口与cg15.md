# m18-chipyard-003: RTL 每源 pending/mask/ack（cg15/cg16）

**模块**：chipyard
**项目里程碑**：M18
**依赖**：`m18-spec-008`、`m18-testcases-005`；等 M16 chipyard 写者窗口
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（RTL 异步源）
**状态**：待开始

## 目标

按 `m18-spec-008`：异步捕获 `cg9`→`cg15`；monitor mask `cg8 rc1`→`cg15 rc3`；timer `cfx_hart cg16 rc0/rc1/rc16/17/18`；DMA `cfx_pmem cg16 rc16/17/18`、删除 `IRQ_EN`；pending ack 才清；进入判定按源 + monitor mask + ENABLE；`cg15 rc4/rc5` 聚合；`escape rc11` 写 `cg15 rc3`。

## 验收

1. `make verilog` + sim rc=0；`m18-testcases-005` 可跑项在 Vast 上通过；与 QEMU 同 ELF 签名一致（不一致登记 `expected-divergences.yaml`）。
2. 可达 FAIL ≥2（恢复 cg9 / pending 进入即清），`cp`+md5 还原重建回绿。
3. 不回归 M16 cfx/cache 代表集；`check-patch-tree` chipyard 段 0 problem；`check-component-changelog` rc=0。
4. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

独立 worktree；不提交 git；只动 `components/chipyard/**`、`tests/arch/**`、`expected-divergences.yaml`、本任务书；不改其它实现/spec/契约/Makefile；`make_patch.py chipyard`；`cp`+md5。
