# m15-testcases-021: 测试资产伪指令收口（`LOAD_ADDR`→`set.rb`、`LD64`→`set.rd`）

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m16-testcases-002`（签名机制）、`m15-testcases-006`（载体装载改用规范伪指令）
**可并行分片**：否（改 `tests/` 共享头与 100 个载体）
**预估**：6–8 h
**档位**：大改（机械替换面大，语义必须零变化）
**状态**：待开始

## 背景（用户 2026-11-20 指出）

测试资产里还留着两个**手写伪指令替代物**，规范伪指令早就能覆盖它们：

1. `tests/shared/asm/machine.inc` 的**唯一内容**是 `LOAD_ADDR rb, addr`——`set.zw` + 3×`or.w` 的固定 4 条，等价于规范伪指令 **`set.rb rb, imm64`**（常量为最少指令数；符号/可重定位地址为固定 3 片 + `R_DADAO_ABS48`）。
2. `tests/ee-tiny/common_tiny.inc` 的**唯一内容**是 `LD64 rd, w0..w3`——等价于 **`set.rd rd, imm64`**（实测：同值、同指令数，仅编码顺序不同）。

持有量（实测）：`LOAD_ADDR` **100 个文件 / 533 处**；`LD64` 2 个文件（`tests/ee-tiny/power_tiny.S` 4 处、`tools/chipyard/excp/app.S`）。

## 目标

1. **`LOAD_ADDR` → `set.rb`**：533 处逐一替换（操作数是 `.equ` 常量表达式的走常量路径；若有裸标签/跨段符号，走 `R_DADAO_ABS48`——先用 `ld.lld` 实测通过再继续）；
2. **`LD64` → `set.rd`**：`power_tiny.S` 4 处、`excp/app.S`；
3. **删除两个文件**：`tests/shared/asm/machine.inc`、`tests/ee-tiny/common_tiny.inc`，并清掉 `.include`（含 `machine-{tiny,vast}.inc` 里对 `machine.inc` 的引用与 `tests/README.md` 的登记）；
4. **重生成**：`tests/data/inst-signature/inputs.sha256`（输入 `.S` 变了）、`case-ledger` 若需要；Tiny bootrom 重建。

## 验收（逐条贴真实 rc）

1. **零残留**：全仓 `grep -rn "LOAD_ADDR\|LD64"`（排 `.tao/archive`）**0 命中**；两个文件已删、`git ls-files` 无它们；
2. **语义零变化**：`check-inst-asm` **272/272**、`check-arch`、`check-inst-sig` 全绿；**签名槽与期望值不变**（代码字节可变，执行结果不可变）；
3. **Tiny bootrom**：`make build-bootrom` 成功；bootrom 的字节会变 ⇒ 更新其 md5 基线并**在完成区写明新旧值**；
4. **符号路径**：若存在 `LOAD_ADDR <label>` 形式，必须证明 `set.rb` + `R_DADAO_ABS48` 在 `ld.lld` 下解析正确（贴链接后反汇编/符号值）；不存在则说明「全部为常量表达式」并给统计；
5. **可达 FAIL ≥2 路**（`cp`+md5）：① 把一处 `set.rb` 的常量改错 ⇒ 对应用例红；② 删 `machine-*.inc` 一条 `.equ` ⇒ 构建或 `check-tests-index` 红；
6. 门控：`check-tests-index`（含 `ASM HEADER DRIFT`）、`check-inst-macro-scope`、`check-case-ledger`、`check-index-blobs`、`check-knowledge-refs`、`check-dirs`。

## 完成区必须写

**需重测周期的镜像清单**：所有指令流变化的镜像（`LOAD_ADDR` 4 条 → `set.rb` 1–4 条）；按指令类的周期表不受影响，但「实测总拍数」记录作废。

## 约束

独立 `git worktree`；不提交 git；**只做等价替换**，不顺带改语义/期望值；不改 `spec/` 与契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
