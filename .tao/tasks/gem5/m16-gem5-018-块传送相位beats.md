# m16-gem5-018: 块传送 `beats` 按起始相位算（N19，用户 2026-11-19 裁定改）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-016`（改同一份 `docs/core-wuming-cycle-model.md` 与生成表 `contracts/wuming-cycles.yaml`）⇒ **必须等 016 收尾再派**
**可并行分片**：否
**预估**：3–4 h
**档位**：中改
**状态**：待开始

## 背景（N19，`m16-chipyard-004` 实测发现）

现行 `components/gem5/patches/src/arch/dadao/wuming_latency.hh` 的 `multiElementCycles()`：

```cpp
const unsigned bytes = elements * row.elemWidth;
const unsigned beats = (bytes + 7u) / 8u;          // 只看元素总字节
```

即「元素不跨 8 B 拍」。**chipyard 实测要求把起始相位算进去**：

```
beats = ⌈(addr % 8 + N·w) / 8⌉
```

非 8 B 相位起址时每组恰多 8 拍——`ldm.ub` N=8、起址相位 2 ⇒ **24 拍**，而当前模型给 16。影响：**所有非 8 B 对齐起址的 `ldm`/`stm` 都被低估**（`ldm.ub` N=8 = 16 只是 8 B 相位上的值，不能外推）。

**用户裁定（2026-11-19）**：改模型。「相位」是**运行期**量（`addr % 8`），**不新增表格维度**；表里的 `perElement`/`perBeat` 仍是标定出来的系数。

> 附：另有两个 N=1 地址特例（SRAM 尾拍 +11、`.text` 内 off-queue 取指 −1），是既有实测例外，**本任务不解释、不改**（仅记录，避免被当成公式的一部分）。

## 要做

1. **把起始有效地址传进模型**：
   - `wuming::DynamicState` 加起始 EA 字段（块传送基址）；
   - `fillDynamicState()` 的 `dyn == "N"` / `"beats"` 分支填充它（`ldm`/`stm` 的基址寄存器 + 偏移；**hook 时点拿不到 EA 就换到能拿到的时点**——在任务书里写清你选了哪个时点、为什么，以及是否影响 `simInsts` 口径）；
2. **改公式**：`multiElementCycles(row, elements, addr)` 用 `beats = (addr%8 + N·w + 7) / 8`；
3. **重算 `nBase`**（若有影响）：`nBase` 是 §5 实测表的残差，来自 8 B 相位的点。改公式后必须**逐项复核**：8 B 相位下所有既有实测点（`ldm.ub` N=8 = 16、`ldm.o` N=8 = 72、`stm` 类等）**结果一分不差**；若 `nBase` 需变，说明为什么、并把新值写进生成器/表（**不得**为了让旧点凑绿而给公式加特例）；
4. **文档**：在 `docs/core-wuming-cycle-model.md` 的 D 类说明处写清 beats 含起始相位（`beats = ⌈(addr%8 + N·w)/8⌉`），并注明「N=8 = 16 是 8 B 相位值」；**改了文档就必须重跑** `python3 tools/gem5/gen_wuming_cycles.py`，`make check-wuming-cycles` rc=0（门控绑文档 sha256）；
5. **不动** `blockCopyCycles`（D′ 寄存器复制无内存拍）。

## 验收（逐条贴真实 rc）

1. **8 B 相位零回归**：所有既有实测点逐项不变（列表 + 旧值/新值）；同一 ELF 在 8 B 对齐场景下 `numCycles` 与改前**完全相等**；
2. **相位正确**：`ldm.ub` N=8 相位 2 ⇒ **24 拍**（改前 16）、N=1 各相位、`stm` 同式；给 gem5 `--debug-flags=Exec` 的逐指令拍差实测；
3. **与 chipyard 对照**：用 `m16-chipyard-004` 的实测点（若数据仍可用）核方向与数值；若不可用，说明替代证据；
4. **可达 FAIL**：把公式改回 `(N·w+7)/8` ⇒ 相位用例红（`cp`+md5 还原 + 重建）；
5. `check-wuming-cycles`/`check-gem5-decode`/`check-index-blobs` rc=0；`check-patch-tree` gem5 段 0 问题；合并态（`Process-07 §5a`）。

## 完成区

（待填）
