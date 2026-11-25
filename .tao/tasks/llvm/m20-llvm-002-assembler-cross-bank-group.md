# m20-llvm-002: LLVM 汇编器拒绝跨 bank 文本寄存器组（ISS-m20-001）

**模块**：llvm
**项目里程碑**：M20
**依赖**：`m20-llvm-001`（MC 层拒绝越界组）已合入；同改 `components/llvm-project`，须串行
**可并行分片**：否（单组件补丁 + AsmParser）
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（`m20-llvm-001` 复核新发现，2026-11-25）

`m20-llvm-001` 已在 MC **反汇编层**拒绝越界组编码（`immu6==0` 或
`起始+immu6>64` ⇒ `<unknown>`），但**汇编期**仍接受跨 bank 的文本组：

```
ra2rd {rd63:rf61}, {ra63:rb61}
```

实测 `llvm-mc` rc=0，编码为 `0x40BBFFFF`（immu6=63）；起始 63 + 63 > 64，按
`contract-isa.md §15.1` / `contract-fp.md §15` 应判
`mreg_range_overflow`（ILLI），汇编器不应生成该字。根因：AsmParser 的 count
由寄存器**枚举 id 差值**推导，rd→rf / ra→rb 枚举相邻，差值跨了 bank，绕过了
`mreg_range_overflow`；该路径与反汇编崩溃源（`m20-llvm-001`）不同。

## 目标

1. AsmParser 按组文本解析出**起始寄存器所在 bank** 与个数，按同一 bank 判
   `起始 + 个数 > 64`（不环绕、不截断）和 `个数 == 0`（若文本可表达）；不得使用
   跨 bank 的枚举 id 差值。
2. 非法组在汇编期硬报错（诊断含 `mreg_zero` / `mreg_range_overflow` 语义），
   不得生成 `.o`；合法组（`{rf63:rf63}`、`{rf1:rf63}`、`{rf32:rf47}`、
   `{rd63:rd63}` 等）编码与修复前逐字节一致。
3. 不修改 `m20-llvm-001` 的 MC 反汇编判据；若发现反汇编判据需要同步，写入
   「待裁定」并说明，不自行扩大。

## 验收（逐条贴真实 rc）

1. `llvm-mc` 对 `ra2rd {rd63:rf61}, {ra63:rb61}` 及 RD/RB/RA/RF 各一组跨 bank
   构造均 rc≠0，诊断可读；修复前同命令 rc=0（给出对照）。
2. 合法组 round-trip 抽样 5 例：`llvm-mc` → `llvm-objdump` 输出与 pre-fix 快照
   逐字节一致。
3. 新增/扩展 lit 负例，覆盖跨 bank、起始+count 越界、合法边界；证明可达 FAIL
   （放宽 AsmParser 判据 ⇒ 负例回红；`cp`+md5 还原后回绿）。
4. `make check-lit`、`check-instrinfo`、`check-patch-tree` 的 llvm 段 0 problem；
   按 `docs/Process-01` 重导补丁序列，`series` 数按实际（不得为过门控改数）。
5. 重建/安装按仓库纪律执行；记录 `llvm-mc` 与安装根 md5 一致；不写具体构建/临时路径。

## 约束

独立 `git worktree`（分支 = `m20-llvm-002`）；不提交 git；只改
`components/llvm-project/**`、对应 lit 用例与本任务书；不改 `spec/`、契约、
`Makefile`。证据落在「运行期证据目录内的 `run.sh`」。术语：bank = **寄存器组**。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
