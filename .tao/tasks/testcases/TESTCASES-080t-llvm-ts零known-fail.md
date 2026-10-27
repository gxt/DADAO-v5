# TESTCASES-080t: llvm-ts 零 known-fail（obsequi/ft/8b10b）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-077t、TESTCASES-078t
**状态**：待验收

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

**状态**：待验收
**测试结果**：定向两档（`--only obsequi$ / ft$ / 8b10b$`）= 每档 `pass 3 / fail 0 / known-fail 0 / blocked 0`；证据脚本 10/10；`make check` rc=0；`make check-tset-llvm-smoke` rc=0。**llvm-ts 全量未跑**（用户 2026-10-27：全量+夜跑不下发）⇒ 全量验收待用户回来。
**根因（逐条实测）**：① `obsequi`/`ft` 的参考**不是陈旧**——未改语料的宿主 `gcc -O2` 构建逐字节复现两份参考（obsequi 4445 B sha256 `daaf7e2c…`、ft md5 `63acb35e…`，日志 `.work/log/testcases/TESTCASES-080t-host-*.log`）；差异只在 `random()`（C 未规定该算法，上游参考钉死 glibc，musl 实现不同）⇒ 修胶水。② `8b10b` 差异 = 语料 `input.txt` 为**小端** u32 词流、目标**大端**（ADR-0003 D1）⇒ 修胶水（不改目标端序）。
**修改文件**：`tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`（新增 `CASE_PRNG_GLUE`/`CASE_LE32_INPUTS` 与施加/校验；删 `ISS265_ADMISSION` 两条 prng 行与 `ISS-266` 全套证据/常量；positive 索引界校验 `b10b_converted_index_check`）、新增 `tests/tset/llvm-ts/patches/README.md` 与 `patches/glue/{glibc_prng.c,le32_to_be32.py,verify_glibc_prng.py}`、`tests/tset/llvm-ts/README.md`（口径）、`.tao/knowledge/issues.yaml`（`ISS-266` 注）、`.tao/knowledge/milestones.md`、本任务书。
**验收结果**（真实输出）
- `run_llvm_ts_user.py --link-mode static|dynamic --only …`：`PASS obsequi exit=0 (output+exit … matched (byte-exact))`、`PASS ft exit=0 (md5(output+exit) == 63acb35e9d086e032ff07f8fdbe9d00a)`、`PASS 8b10b exit=0 (…matched (byte-exact))`；汇总 `total=3 pass=3 fail=0 known-fail=0 blocked=0`。
- `patches/glue/verify_glibc_prng.py`：`PASS (8 sequences, 100 draws each)`（默认态 + 7 种子，对宿主 glibc 逐字节相同）。
- 输入：`input.txt rewritten 65536 u32 words little-endian -> big-endian (sha256 067f1e24… -> 19e553fc…)`；`65536 big-endian words, all in range -- worst index5=63 < lookupTable5B[64], worst index3=15 < lookupTable3B[16]`。
- `.work/evidence/TESTCASES-080t/run.sh`：`PASS (10/10 checks)`，含三次注入（错 oracle → fail；删 glibc 310 抽预热 → ft fail；未转换输入 → guest SIGSEGV `returncode=-11`）与 `cp`+md5 还原后回绿（还原前后 md5 一致 `e2603586…`）。
- `make check` rc=0（`repository checks (L1): PASS`）；`make check-tset-llvm-smoke` rc=0。
**新发现/坑**：glibc `srandom(s)` 播种后**额外丢弃 310 抽**（`kc*=10`），只按教科书 16807 播种会得到另一条序列（首值 811325037 而非 1804289383）；glibc 未播种态 == `srandom(1)`；`8b10b` 的 `testbench.c:59` 按 `sizeof(unsigned int)` 读词（非逐字节），故端序必须显式处理。
**遗留问题**：① **llvm-ts 全量（两档）未跑**（用户限制），`known-fail=0` 的全量确认待用户回来；② `ISS-265` 在 `issues.yaml` 无独立条目（M8 已归档、M9 `issues-closed.md` 有行），本任务只删驱动内该两行、未新增/重开条目；③ 胶水只实现 `random()/srandom()`（两例未用 `initstate/setstate`；若将来有用例使用需扩展）。

## 审阅记录

### 第 1 轮 engineer 自审

判决：**实现完成，所有 self-review finding 已修**；改动逐行复核（diff 561 行 = 文档 + 删 265 行旧 known-fail 机制 + 增 130 行 positive 校验/胶水施加），定向两档与证据脚本均实测通过。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本 `report` 的 rc 合成写成「恒为 1」 | ✅已修 | 改为 `is1 "$drc" && both0 0 "$jrc"`（两条独立断言） | 注入跑 `inject.wrong-oracle`/`inject.glue.ft` 均 rc=0 且真实红过 |
| F2 8b10b 端序探针把 `2000` 当 int 传 subprocess / 用 bash 判 SIGSEGV | ✅已修 | 改 `"2000"`、断言 `returncode == -11` | 手工复跑：`returncode=-11 (SIGSEGV)  prc=0` |
| F3 胶水无 `#include <stdlib.h>`，签名不受 libc 原型校验 | ✅已修 | 加入 stdlib.h | 目标 `clang -Wall -Wextra` 无警告 + host 核对 8/8 |
| F4 文档行号与语料不符（`testbench.c:71/83`、`calc.c:173-174`、`graph.c:40`） | ✅已修 | 按实测改为 `59`/`72`、`170-173`、`43`（ft 播种在 `ft.c:86`） | `grep -n` 语料实测 |
| F5 删 prng 证据后 `import ctypes` 成孤儿 | ✅已修 | 删除 import | `grep -c ctypes` = 0；两档跑通 |
| F6 `iss265_evidence` 签名收敛后调用点需同步 | ✅已修 | `run_round` ×2 + `iss265_admission_selfcheck` | 两档 rc=0；selfcheck 在轮内执行且无 problem |
| F7 删行后是否残留死分支/恒真断言 | ✅已修 | 删 `ISS-266` 全套；selfcheck 增「不同尺寸不得判 interleave」可达 FAIL 分支 | `grep ISS266` = 0；selfcheck 三探针均拒绝 |
