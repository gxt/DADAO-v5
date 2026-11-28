# m19-testcases-006: hmon 数据槽消费者迁移（0xD8–0xF8 → 0xC00 页）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-testcases-005`、`m19-testcases-004`、`m19-testcases-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

`m19-testcases-005` 已把固件 hmon 的数据槽从 `HMON_BASE + 0xD8/0xE0/0xE8/0xF0/0xF8` 迁到 spec §6.2 的 `0xC00` 数据页：

- `+0x00` cause_id、`+0x08` cause_ip、`+0x10` cause_info、`+0x18` 返回地址、`+0x20` 保存 rd63、`+0x28` 保存 rb63。

但所有**消费者**仍按旧槽读：`tests/inst` 宏与部分用例、`tests/arch/{ptw,umon,time,power}`、`tools/chipyard/excp/*`、`tools/testcases/arch/min_rom_probe_integ007t.py`。不迁会让这些用例读到全零（或读到代码区），`check-arch` 的 `integ007t` 等会转红。

## 目标

1. 统一槽位常量：优先收敛到一处（`tests/shared/asm/machine-tiny.inc` 或等价头），消费者引用常量而不是硬写 `0xE0/0xE8/0xF0/0xF8/0xD8`。
2. 迁 `tests/inst`（宏 `inst_test.inc` 与所有读 hmon 帧的用例）、`tests/arch/**`、`tools/chipyard/excp/**`、`tools/testcases/arch/min_rom_probe_integ007t.py`。
3. 地址按 `HMON_BASE + 0xC00 + 页内偏移`；注意 `rb0` 相对寻址的 `imms12` 限制（必要时用第二基址寄存器或先算地址）。
4. 运行验证：新固件 8 KiB 镜像下，至少覆盖 `ptw`、`umon`、`time`、`inst` 各 1 个用例在 QEMU（与 gem5，若可用）跑通；`check-arch` 的 `integ007t` 不再因槽位失败。

## 验收（逐条贴真实 rc）

1. 全仓 `grep` 不再有「hmon 帧槽」形式的旧偏移（`HMON_BASE + 0xD8/0xE0/0xE8/0xF0/0xF8`）；若有历史说明性引用，须逐条列出并说明不动的原因。
2. 代表用例：`tests/inst` 2 个、`tests/arch` 4 个（ptw/umon/time/power 各 1）在 QEMU 下 rc=0，签名/退出码与期望一致。
3. `make check-arch`（或分模块子集）+ `check-inst-asm` 真实 rc；基线红逐行对照，`integ007t` 的失败若消失须给出前后对照。
4. **可达 FAIL ≥2 路**：① 把某消费者槽位写回 `0xE0` ⇒ 该用例读错、红；② 把固件 `HMON_SLOT_CAUSE_ID` 改 `+0x08` ⇒ 消费者红；均 `cp`+md5 还原回绿。
5. 不改 QEMU/gem5/chipyard 源码；不接板；版本号未升。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/**`、`tools/chipyard/excp/**`、`tools/testcases/arch/min_rom_probe_integ007t.py` 与必要索引；完成区不写具体 `.work/**` 路径。
