# INTEG-041t: fence ciii 落地（编码/移册/汇编/测试）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0044（fence ciii）
**状态**：待开始

## 背景

ADR-0044 已定：`fence` 改为 `ciii`，`opc=0x79`，`cfxha` 选择资源域，`hb=0`，`hc=pred`，`hd=succ`；`pred/succ` 为 cr/cw/ci/co/mr/mw 六位掩码；`cfx0`/`cfx_umon` 表示 all cfx；`immu18` 整体书写、不拆三段；删除 `fm`/TSO；从 SimRISC-12「其它指令」移到 SimRISC-11「核芯功能扩展指令」。旧 `fence 0` 不再接受。

## 目标

1. **spec/文档**
   - SimRISC-11：加入 `fence` 的编码/语义/pred-succ 表；
   - SimRISC-12：删除 `fence`，同步索引；
   - DADAO-12/Toolchain-01：汇编语法、`cfx0`/`cfx_umon`=all、`fence 0` 拒绝；
   - 删除 `fm`/TSO 描述；`hb`/保留位明确 SBZ。
2. **contracts**
   - `contracts/opcodes.yaml`：旧 fence 记录替换为 `opc=0x79`、`ciii`、`cfxha/hb/hc/hd`；更新 legality/spec_cite；
   - 相关 alias/索引/生成物同步。
3. **LLVM**
   - MC 编码/解码、汇编器语法：`fence cfx0, immu18` / `fence cfx_umon, immu18`；
   - 拒绝 `fence 0`；`immu18` 为单个 18 位表达式；
   - 补 lit（正例/负例：hb!=0、reserved cfx、旧语法拒绝、pred/succ 组合）。
4. **QEMU**
   - 若当前有 fence 解码/trans：更新到 0x79/ciii；语义按“本 hart、资源域顺序”实现或明确 no-op hint；
   - 不改 DMA/TLB/cache 维护语义。
5. **测试**
   - 汇编接受 `cfx0`/`cfx_umon`/具体 cfx；
   - `immu18` 位映射、零掩码 no-op；
   - `hb!=0`/reserved cfx → ILLI；
   - 旧 `fence 0` 汇编失败；
   - 不改变现有访存/异常测试。

## 验收

- `make check`、`make check-lit`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state` rc=0；涉及 QEMU/LLVM 时补对应构建/定向测试。
- 证据 `.work/evidence/<任务号>/run.sh`：注入→FAIL→cp+md5 还原→PASS。
- 不改 `fence.vma`/`fence.i`/DMA 语义；不跑 full/夜跑。
- 完成区 ≤30 行；任务书与 `milestones.md` 置 `待验收`；临时 `/tmp/opencode/INTEG-041t/`。

## 约束

- 只做 ADR-0044 范围；不改 cfx 编号/cfx 权限。
- 不提交、不 push；重建先申报；失败保留现场。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
