# INFRA-114t: check-sync-nonmaskable 白名单补 PMEM_DMA（M10 收尾门控）

**模块**：infra
**项目里程碑**：M10
**依赖**：`INTEG-042t`（`spec/DADAO-12` 异常原因表引入 `PMEM_DMA` 行）、`INTEG-047t`（`cfx_pmem` DMA 的 SBI 契约）——均为已 `已验证`，仅作溯源，非阻塞
**状态**：待开始

## 执行环境

**执行环境**：本地

## 背景（现场事实）

- `make check-milestone` 现 **rc=2**：`check-spec-archive` / `check-spec-archive-verify` 通过后停在
  `check-sync-nonmaskable`，报
  `DADAO-12-SEE-主管系统运行环境.md:662: 同步异常原因 PMEM_DMA 被标为可屏蔽（仅异步源可屏蔽）`。
- 事实两面：`spec/DADAO-12` 的 `PMEM_DMA`（`1 << 8`）**确实是异步源**（`dma_ctrl.IRQ_EN=1` 时 DONE/ERROR 置位；
  被掩码时置 `cfx_pmem_excp_pending`），标「可」**语义正确**；而 `tools/spec/check_sync_nonmaskable.py`
  的异步白名单 `ASYNC_NAME_RE = ^(?:IPI|TIMER|UART\d*|\.\.\.)$` **漏了 `PMEM_DMA`**。
- 该缺口自 `INTEG-042t` 引入（`git log -S` 命中 `145b07c3`），此前门控无此 cause 故未暴露。
- 连带：`--self-test` 的第 1 步「基线副本必须 PASS」现在也**必然 FAIL**（基线含 `PMEM_DMA`），
  即 self-test 目前整体非零 —— 修白名单后两者同时回绿。
- 已登记于 `INTEG-052m`（M10 核验册）「遗留」与「核验」两节。

## 接口规范

- 输入：`spec/DADAO-12-SEE-主管系统运行环境.md` / `DADAO-22` / `DADAO-23` 的「异常原因表」（列 `是否可屏蔽`）。
- 输出：`check_sync_nonmaskable.py` 的退出码（0 = PASS / 1 = 有同步 cause 被标可屏蔽 / 2 = 源缺失或空跑）。
- 约束：
  - **只放宽已知异步源**：白名单加入 `PMEM_DMA`（与 `IPI`/`TIMER`/`UART<n>` 同类），
    **不得**退化为「任意 cause 均放行」（如删掉 `ASYNC_NAME_RE` 判定、改成 `.*`、加 `\S+` 之类通配）；
  - **不改** `spec/DADAO-12`（`PMEM_DMA` 仍「可」）、不改 `TARGETS`、不改其它门控脚本；
  - 改后同步 **docstring 规则描述**（现文「`IPI`、`TIMER`、`UART<n>` 或占位行 `...`」）与
    **成功文案**（现 `check-sync-nonmaskable: PASS（仅异步源（IPI/TIMER/UART*/…）可屏蔽）`），三处口径一致。

## 验收标准

1. `python3 tools/spec/check_sync_nonmaskable.py` **rc=0**，且 stdout 含现场计数
   （`files=3 tables=… rows=… maskable_rows=…`）与 PASS 文案，PASS 文案列出 `PMEM_DMA`；
2. `python3 tools/spec/check_sync_nonmaskable.py --self-test` **rc=0**（基线 PASS / 注入同步 cause=可 → FAIL /
   还原 PASS / 异步源 PASS / 最终 PASS 全成立）；
3. **self-test 新增可达断言**：`PMEM_DMA=可` 明确验为「白名单命中 ⇒ 不报错」——不得**只**改正则而不加断言
   （现行第 1 步「基线副本必须 PASS」已隐式覆盖，须额外给出**显式**断言或独立注入步，
   且证明该断言**能失败**：把 `PMEM_DMA` 从白名单临时移除 ⇒ 该步必须 RED，`cp` 还原 + md5 对账后回绿）；
4. `make check-milestone` **rc=0**；若仍有其它门控红，**分开报告**（逐项 rc / 首行错误），不合并成一条；
5. L1 `make check` **rc=0**；
6. 无残留：`git status --untracked-files=all` 干净（自检临时树落 `/tmp/opencode/INFRA-114t/`，用完即清）；
7. 完成区贴真实命令输出与退出码（禁转述），并逐条对齐本清单。

## 完成区

**测试结果**：（待填写）
**修改文件**：（待填写）
**验收结果**：（待填写）
**新发现/坑**：（待填写）
**遗留问题**：（待填写）

## 审阅记录
