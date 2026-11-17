# m14-spec-008: 把 DADAO-13 的第 1、2 章正文并入 DADAO-12（DADAO-13 只留引用）

**模块**：spec
**项目里程碑**：M14
**依赖**：无（纯文档重组；`DADAO-13` 0.1.4-rc / `DADAO-12` 0.7.3-rc 当前态）
**可并行分片**：否（同改两册 + 锁）
**预估**：1–1.5 h
**档位**：中改（spec 两册结构 + 锁哈希 + 引用；复核 ≥2 路注入）
**状态**：待开始

## 背景（用户 2026-11-17 原话）

> 「这部分 spec 内容在 DADAO-13 中，你的疑问确实是个事，请把 DADAO-13 的第一章第二章移动至 DADAO-12，DADAO-13 只保留个引用就行。」

起因：`DADAO-12 §3.4 cg3` 正文只有一句「H-mode 寄存器（cg=3）定义见 HEE」，而 `cg3 rc0–rc3` 的四类同步 mask 实际定义在 `DADAO-13 §1`；`DADAO-13 §2` 的 cfx_hmon 异常原因表同样只在 HEE 册。两册割裂导致实现方（chipyard）把四类 mask 合并成一份而未被正文拦住。

## 目标

1. **`DADAO-12 §3.4 cg3 - hypv mode 寄存器`**：用 `DADAO-13 §1` 的**全文**替换现有「定义见 HEE」占位——即寄存器表（rc0–rc12）+ 「`rc0`–`rc3` 四类同步 mask」段 + 「`rc10` 初值与写入」段，逐字搬运，不改语义。
2. **`DADAO-12 §4.4 cfx_hmon - hypervisor monitor`**：迁入 `DADAO-13 §2` 的 **hmon 说明段**（「hmon 为 hypv 下的同步异常处理核芯功能扩展…否则触发 CFXREG」）；异常原因表**不重复贴**，改为「与 `cfx_umon` 一致（表见 §4.1）；`CFXMEM`/`CFXPERM` 的 `cause_info` 与子原因见 §3.6」——避免制造第二真源。删除「详细定义见 HEE」。
3. **`DADAO-13`**：`## 1. cg3 - hypv mode 寄存器` 与 `## 2. cfx_hmon - hypervisor monitor` 两节**只保留标题 + 一行引用**（分别指向 `DADAO-12 §3.4`、`§4.4/§4.1`），章节编号保留作锚点（历史任务书/ADR 的 `DADAO-13 §1/§2` 引用仍可解析）。`## 3. 启动与引导移交`（详见 HBI）与附录不动。
4. **版本与锁**：两册各加一条变更记录（`DADAO-12` → `0.7.4-rc`、`DADAO-13` → `0.1.5-rc`，写明「章节并入」并给用户原话来源）；按 `docs/Process-06 §5` 重算两册锁哈希（`spec/README.md` 索引若含 sha256 同笔更新）。
5. **活跃引用同步**：只改 `spec/README.md` 与 `.tao/contracts/**` 中指向 `DADAO-13 §1/§2` 的**活跃**引用（改成新位置）；**历史任务书/ADR/refs 不改**（锚点仍在，且历史记录不该回写）。

## 验收（逐条贴真实 rc）

1. **内容无丢失**：逐行对照——`DADAO-13 §1` 的表格行数 + 两段说明、`§2` 的说明段，全部出现在 `DADAO-12 §3.4/§4.4`（行数与文字逐条比对，给 diff/命令输出）。
2. `DADAO-13 §1/§2` 只剩标题 + 引用行（`grep -c` 表格行 = 0）。
3. `make check-spec-drift check-spec-changelog check-spec-purity check-spec-cite-targets check-spec-refs check-spec-readonly check-spec-codeblocks` 全 rc=0；两册锁哈希与 `spec/README.md` 一致。
4. **≥2 路注入**（`cp`+md5 还原）：① 把 `DADAO-12 §3.4` 的 `rc0` 行删掉 ⇒ 内容对照/检查红；② 把 `DADAO-13 §1` 重新贴回表格 ⇒ 「只留引用」断言红。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **只动**：`spec/DADAO-12-*`、`spec/DADAO-13-*`、`spec/README.md`（如需）、`.tao/contracts/**` 的活跃引用、本任务书、锁文件。**不动** `spec/SimRISC-*`、`spec/Kaiwu-*`、`tests/`、`components/`、`Makefile` 门控集合。
3. **语义零变更**：不改任何寄存器初始值/位索引/异常语义；只做搬运与引用改写。
4. 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash/show`、禁 `reset --hard`）。

## 待裁定

（无）

## 审阅记录

（待填）
