# TESTCASES-080t: llvm-ts 零 known-fail（obsequi/ft/8b10b）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-077t、TESTCASES-078t
**状态**：待开始

## 背景（自包含，2026-10-27 全量实测）
用户 2026-10-27 裁定：**全绿 = 没有 known-fail**。当前 `check-tset-llvm-full` 仍有 3 条逐例 known-fail（门控 rc=0，但不是 pass）：

1. `MultiSource/Applications/obsequi`（ISS-265）：oracle 不匹配，输出 4444 B vs 期望 4445 B（sha256 `5de6a8bb…` 起）；已按 ISS-265 逐例 known-fail。
2. `MultiSource/Benchmarks/Ptrdist/ft`（ISS-265）：oracle 不匹配，md5(output+exit)=`3dd953c9…` vs 参考 `63acb35e…`；已 known-fail。
3. `MultiSource/Benchmarks/VersaBench/8b10b`（ISS-266）：输入 `input.txt` 是**小端 u32 词流**，DADAO 目标为**大端**；首词 `38000000` 大端解释下 index 越界，guest SIGSEGV；已 known-fail（语料数据端序，非后端缺陷）。

这 3 条与 077/078/079 的架构/UB/ musl 问题不同：它们是**oracle 或输入端序**问题；必须逐条消除 known-fail，不能靠基线。

## 目标
1. **obsequi**：核对输出差异（4444 vs 4445 B）是确定性/格式/尾部字节/参考陈旧中的哪一种；用宿主可复现构建与上游输入重算，决定修 oracle 还是修测试胶水；不得改成模糊比较。
2. **ft**：核对 md5 差异来源（输出内容/exit/参考版本）；按同口径修复。
3. **8b10b**：处理输入端序：在测试胶水中做**显式、可审计的大端转换**（或按上游输入语义选择正确字节序），不得改 DADAO 目标端序；确认 65536 词索引在界内且输出与参考一致。
4. 三条均转为 **pass**；`known-fail` 计数 = 0；不得把适用用例改成 excluded/blocked 来「消红」。

## 验收
- 定向（static+dynamic）：`obsequi`、`ft`、`8b10b` 均 pass（输出+exit 与经论证的 oracle 一致）。
- `make check-tset-llvm-full`（static+dynamic）rc=0 且 **known-fail=0 / fail=0 / blocked=0**（与 077/078/079 合并后）。
- `ISS-265`、`ISS-266` 按实际更新/关闭；参考/端序处置留证据（命令、输入、哈希）。
- `make check` rc=0；证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-080t/`。

## 约束
- 只改本任务范围内的 `tests/tset/llvm-ts/`、`tools/testcases/tset/llvm-ts/`、测试胶水/参考、索引/ledger、任务书/milestones；不改 spec/qemu/LLVM 语义。
- 不改上游源码树本体；参考/输入转换必须可复现、可审计；不得放宽比较或静默跳过。
- **不提交、不 push**；长跑申报耗时；不跑无关全量。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
