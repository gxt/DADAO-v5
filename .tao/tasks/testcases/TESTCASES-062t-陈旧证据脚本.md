# TESTCASES-062t: 陈旧证据脚本收口（`ISS-237`/`ISS-238`/`ISS-282③`）

**模块**：testcases
**项目里程碑**：M9（用户 2026-10-24 裁定「M9 内做」）
**依赖**：无
**状态**：待开始

## 立项来源

- `ISS-237`：`QEMU-061t` 的 `smoke_derive.py` L2 派生逻辑过时（`GATE_VECTORS` 已含 `aip-si.yaml`，再"追加"无增量）
- `ISS-238`：`SPEC-145t` 证据脚本因 `rela`→`aip` 改名后有 **14 项 stale 断言**
- `ISS-282③`：`llvm-ts-user-*` 命名遗留（`INFRA-093t` 验收第 3 项）

## 目标

1. 237：按现行 `GATE_VECTORS` 重写派生断言（"追加"改为"集合包含"），并给"改前恒真/改后可达 FAIL"的证据。
2. 238：14 项 stale 断言逐条改指/删除；保留语义断言。
3. 282③：把 `llvm-ts-user-*` 的豁免/命名按 `Process-08` 收口（或明确"保留 + 记录判据"，不进门控），使 `ISS-282` 可关。

## 验收

1. 各脚本真实重跑 rc=0；`ISS-238` 的 14 项 **0 残留**（grep 证据）。
2. **可达 FAIL ≥2**：① 237 把"集合包含"改回"追加" ⇒ 注入即失败；② 238 改坏一条断言 ⇒ 红。
3. `make check`(L1) rc=0；`check-run-artifacts` rc=0。
4. 证据 `.work/evidence/<任务ID>/run.sh`。

## 约束

- 不改 QEMU/LLVM 实现；不 commit/push；临时目录 `/tmp/opencode/TESTCASES-062t/`。
