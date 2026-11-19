# m16-gem5-015: gem5 FS + Timing（tiny 与 vast 两种机型）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-006`（Timing 访存 + `--wuming-cycles`）、`m16-gem5-014`（Vast TLB）
**可并行分片**：否
**预估**：2–4 天
**档位**：大改
**状态**：待开始

## 背景（用户 2026-11-19 裁定）

「**`gem5` 的 `TimingSimpleCPU` 也要做 Vast**」。现状：

- `fs.py`（FS）**只有 Atomic**：`tiny → DadaoFsAtomicSimpleCPU`、`vast → DadaoNodeAtomicSimpleCPU`；
- `se_timing.py`（SE）才有 `DadaoTimingSimpleCPU`（`m16-gem5-006` 交付，含 `NoncoherentXBar` + `SimpleMemory` + `--wuming-cycles`）。

⇒ 缺的是 **FS 模式的 Timing 变体**，且要**两种机型都能跑**（Tiny 与 Vast 共用一套机制，几何由 profile 决定）。

## 目标

1. **新增 `configs/dadao/fs_timing.py`**：与 `fs.py` 同几何（`--profile {tiny,vast}`），CPU 换成 DADAO 的 `TimingSimpleCPU` 变体（`DadaoTimingSimpleCPU` 复用 `se_timing.py` 的类），挂 `NoncoherentXBar` + `SimpleMemory`；
2. **`translateTiming` 落地**：`fs_tlb.cc`（Tiny）与 `node_tlb.cc`（Vast）现在的 `translateTiming` 是 **stub/未实现**（忽略 `translation` 参数）；需按各 TLB 的解析逻辑实现，使 timed 访问能正确翻译并回填；
3. **`--wuming-cycles` 在 FS 下仍生效**（逐指令延迟钩子是 arch 侧，与 SE/FS 无关，确认即可）；
4. **Vast 的 TLB/PTW 时序口径**：若 TLB miss 的走查代价暂时不建模，必须在文件头**显式声明**（「PTW 走查按 0 延迟，由周期表另行记账」），并给出后续接入点；
5. **数据侧访存的既有折衷沿用**：`m16-gem5-006` 已声明「DADAO 执行核同步读内存 ⇒ 数据侧 functional、ld/st 由周期模型记账」；FS 侧同样处理，并在文档写清。

## 验收

1. `make build-gem5` rc=0；**Tiny**：`fs_timing.py --profile tiny` 跑 `tests/inst` 首册 + 至少一条 `k0` 镜像，退出码与 Atomic 一致；
2. **Vast**：`fs_timing.py --profile vast` 跑既有 Vast 冒烟（`run_m5_e2e.py --profile vast`），功能与 Atomic 一致；
3. **周期一致性**：同一 ELF 在 `fs_timing --profile tiny` 与 `se_timing` 下，**逐指令拍数一致**（同一 `--wuming-cycles` 表）；
4. **可达 FAIL**：把 `translateTiming` 改回 stub ⇒ 用例红（`cp`+md5 还原 + 重建）；
5. 不回归：`fs.py`（Atomic）与 `se_timing.py` 行为不变；`check-gem5-decode`/`check-index-blobs`/`check-patch-tree`（gem5 段）rc=0；合并态（`Process-07 §5a`）。

## 待裁定

- **PTW 走查的延迟**是否要建模（现在是 atomic/0）；若建模，需要先定「TLB miss 的拍数来源」（实测还是估算）——建议**先按 0 延迟并在文档声明**，等 RTL 实测再回填。

## 完成区

（待填）
