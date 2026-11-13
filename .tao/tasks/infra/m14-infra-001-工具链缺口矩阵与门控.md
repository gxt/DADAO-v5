# m14-infra-001: 工具链缺口矩阵与门控（`make check-linux-toolchain`）

**模块**：infra
**项目里程碑**：M14
**依赖**：`m14-linux-001`（目标名与 Makefile 接线已由该任务声明；本任务不改 `Makefile`）
**可并行分片**：否（单一矩阵 + 单一门控；探针可并行执行但产出单份数据/报告）
**预估**：4–5 h
**状态**：待开始

## 背景

Linux 内核构建对工具链的要求比裸机测试更宽：归档/符号/剥符号工具（`llvm-ar`/`llvm-ranlib`/`llvm-strip`）、GNU C 扩展（`asm goto`）、栈保护、数据伪指令（`.quad/.long/.short/.byte`）、inline asm 约束、代码模型（`-mcmodel=kernel`）。当前安装根 `.dadao/cross-toolchain/bin` 只装 `HOST_LLVM_TOOLS`（`llvm-mc/llvm-objdump/llvm-objcopy/llvm-readobj/llvm-nm/llvm-dwarfdump/FileCheck/not/llc/clang` + 别名），**没有** `llvm-ar`/`llvm-ranlib`/`llvm-strip`（实测）；其余能力未系统测过。

M14 K0 的入口判据是「gaps 归零或有规避法 + 工具链就位」。本任务只**登记缺口与规避法**，**不修工具链**（安装根/构建树/LLVM 源码都不改）。

## 目标

1. 建 `tools/linux/toolchain_matrix.json`：逐项记录「探针 / 期望 / 实测 / K0 影响 / 规避法 / 归属任务」。
2. 建 `tools/linux/check_toolchain.py`：按矩阵**现场重跑探针**，断言「声明 == 实测」；提供 `--report` 从矩阵生成人读报告、`--inject` 自检（可达 FAIL）。
3. 产出 `docs/TestReports/M14-K0-toolchain-gaps.md`（四必备项：生成时间/数据来源/机器指纹/复现命令；无运行期绝对路径），并在 `docs/README.md` 索引补一行。
4. 在完成区给出 `check-linux-toolchain` 的 **L1 判据文本**（可机械判）；`docs/Process-07 §1.1` 的登记与 `Makefile` L1 成员接线**统一由 `m14-infra-003`** 完成（本任务不改 `Makefile`/`Process-07`）。
5. 给 `m14-linux-002` 输出**可直接消费**的工具选择：`CC/LD/AR/RANLIB/NM/OBJCOPY/OBJDUMP/STRIP` 各自的可执行来源与 fallback，不得只写「缺」。

## 矩阵行（至少覆盖；可增不可漏）

| 行 | 探针（必须指向 **DADAO target**，不得用 host x86 直测） | 判定 |
|---|---|---|
| `llvm-ar` | 安装根/构建树是否存在可执行 + `--version` | present/absent；内核 `AR` 选择 |
| `llvm-ranlib` | 同上 | present/absent；`.a` 索引 |
| `llvm-strip` | 同上 | present/absent；`STRIP`/`INSTALL` 行为 |
| `asm goto` | `clang --target=dadao -fsyntax-only` 编译带标签的 `asm goto`（内联 asm 跳到 C 标签） | 支持/不支持/错误码 |
| 栈保护 | `-fstack-protector-strong` +（若目标支持）`-mstack-protector-guard=…` 编译并检查生成物含 canary 访问 | 支持级别 |
| 数据伪指令 | 汇编 `.quad/.long/.short/.byte` 全组合，反汇编/读段核对字节与宽度 | 支持/错误 |
| inline asm 约束 | 内核常用约束（`"r"`, `"i"`, `"m"`, `"=&r"`, 内存 clobber）逐条编译 | 支持/错误码 |
| `-mcmodel=kernel` | 命令行接受性与实际 codegen（如 `.medlow/.small` 的替代） | 支持/需规避 |

- 每行必须给出**实测命令 + 原始输出摘要 + exit code**；禁止凭已知/文档填写。
- `missing` 行必须有**非空规避法**（如 `AR=<构建树 llvm-ar>`、`-mcmodel=medlow`、`-fno-stack-protector`）且写明对 K0 的影响（blocker / none）；`required` 行必须 present。
- 矩阵声明与探针结果**一一对应**；不允许「未知/未测」状态。

## 接口规范

**矩阵（JSON，字段名固定；值现场填写）**

```json
{
  "format": 1,
  "toolchain": {"target": "dadao-unknown-elf", "resolved_from": "tools/infra/paths.py"},
  "rows": [
    {"id": "llvm-ar", "required_for_k0": true, "declared": "absent",
     "probe": "<argv 形状，不含宿主绝对路径>", "measured": "absent",
     "workaround": "AR=<构建树>/llvm-ar（或 GNU ar）", "k0_impact": "none",
     "owner": "m14-linux-002"}
  ]
}
```

**门控判据（每条有可达 FAIL）**

1. 每一行 `declared == measured`；不一致 ⇒ FAIL（工具升级/降级后必须更新矩阵）。
2. 所有 `required_for_k0 == true` 的行 `measured == "present"`；否则 FAIL（K0 被阻塞）。
3. 所有 `declared == "absent"` 的行 `workaround` 非空；否则 FAIL。
4. 行集合覆盖上表；缺行/多未知行 ⇒ FAIL。
5. 报告与矩阵同源：报告由 `--report` 生成，正文数字与矩阵一致；改矩阵不重生成 ⇒ `--report --check` FAIL。
6. `--inject`：临时副本上翻转一行 `declared`、删一个 `workaround`、把 `required` 行标 `absent` ⇒ 三种各自 FAIL；还原（`cp`+md5）⇒ 回绿。

## 范围（改哪些文件）

- `tools/linux/toolchain_matrix.json`（新建）
- `tools/linux/check_toolchain.py`（新建）
- `docs/TestReports/M14-K0-toolchain-gaps.md`（新建，生成物）
- `docs/README.md`（索引一行）
- 本任务书

**不改**：`Makefile` 与 `docs/Process-07`（目标由 `m14-linux-001` 声明；L1 登记与成员接线由 `m14-infra-003`）、`manifests/`、LLVM/安装根/构建树内容、`components/`。

## 验收标准

1. `make check-linux-toolchain` rc=0，打印 `N/N 行一致`（N 现场统计）与 `gaps=K (blockers=0)`；`python3 tools/linux/check_toolchain.py --inject` rc=0（自检三例全 FAIL 后还原回绿）。
2. 八个矩阵行逐行有真实探针输出（完成区贴命令形状 + exit code；长输出留运行期日志目录）；**证明探针不是 host x86**（命令含 `--target=dadao` 或等价 target 选择，且失败/成功与 DADAO target 绑定）。
3. `llvm-ar`/`llvm-ranlib`/`llvm-strip` 的 present/absent 结论与安装根/构建树现场一致；若 absent，`workaround` 给出可执行来源与 `m14-linux-002` 的消费方式。
4. 报告 `docs/TestReports/M14-K0-toolchain-gaps.md`：四必备项齐全、无 `/tmp`/`/home`/具体 `.work` 路径；`make check-test-reports` rc=0；`docs/README.md` 索引有该文件。
5. 完成区给出可登记的 L1 判据文本（「声明==实测；required 全 present；absent 有规避法」）；`m14-infra-003` 负责在 `docs/Process-07 §1.1` 登记并接线（本任务不改 `Process-07`/`Makefile`）。
6. **不改工具链**：`git status` 无 `.dadao/**` 或 LLVM 源码改动；安装根二进制 mtime/sha 未变（现场核对）。
7. 回归：`make check` 其余目标 rc=0（新目标尚未接 L1，属预期；外部红逐条归属）。
8. 一键证据脚本（含注入）；完成区 ≤30 行、无运行期路径。

## 说明

- **为什么探针必须锁 target**：host clang 对 `asm goto`/`.quad`/`-mcmodel` 天然支持，用 host 测会得出「全绿」的假结论；所有探针必须经 target triple 或 `--target=…`，并在矩阵里记录 target。
- **为什么只登记不修**：安装根新增工具要走 `make install-host` + `HOST_LLVM_TOOLS`（跨任务、影响全仓），属独立决策；本任务给 `m14-linux-002` 可用的规避法即可。
- **报告文件名**按派单指定为 `docs/TestReports/M14-K0-toolchain-gaps.md`（英文主题）；`check-test-reports` 只校验 `<M>-<主题>.md` 形态与四项必备内容，不判语种。不得为「好看」改名或加日期。
- **`-mcmodel=kernel` 的语义**：DADAO 不一定有同名 code model；若 clang 拒绝，按实测选 `medlow`/`small`/默认，并把「内核链接地址 = 1 MiB」作为约束写进规避法（`m14-spec-001` 已冻结）。
- 参考实现只读：`.cache/refs/DADAO-0628` 的 K3 构建踩坑（`llvm-ar`/`strip`/`-O0`）只作**内容溯源，非执行必需**，不复制命令/补丁。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出留存运行期日志目录（`docs/Process-08`）。
10. 证据脚本的对照基线钉**派单前 commit 常量**或现场文件 md5，不得取 `HEAD`。

## 用户授权

（本任务不改 `spec/`/`docs/Process-*`/`Makefile`；如必须改，先停并登记「待裁定」。）

## 待裁定

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审（待填）

### 第 1 轮 reviewer 验收（待填）
