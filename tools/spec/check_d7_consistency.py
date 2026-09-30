#!/usr/bin/env python3
"""D7 一致性对照器：校验 ADR-0012 D7 ↔ 三载体（SimRISC-00/06、contract-isa）的 9 分支与位域/判据。

用法：
  python3 tools/spec/check_d7_consistency.py           # 默认以仓库根为 cwd
  python3 tools/spec/check_d7_consistency.py /path/to/repo

退出码：0 = PASS，1 = FAIL（输出不符项列表）
"""
import sys, os, re

root = sys.argv[1] if len(sys.argv) > 1 else '.'

def load(rel):
    with open(os.path.join(root, rel), encoding='utf-8') as f:
        return f.read()

def norm(s):
    """归一化：去 Markdown 标记，统一减号，合并空白"""
    s = s.replace('*', '').replace('`', '')
    s = s.replace('\u2212', '-')  # U+2212 MINUS SIGN
    s = s.replace('\u2013', '-')  # U+2013 EN DASH
    s = re.sub(r'\s+', ' ', s)
    return s

files = {
    's00': 'spec/SimRISC-00-指令系统设计.md',
    's06': 'spec/SimRISC-06-控制流.md',
    'cis': '.tao/knowledge/contract-isa.md',
}

raw = {}
txt = {}
for k, rel in files.items():
    try:
        raw[k] = load(rel)
    except FileNotFoundError:
        print(f'FAIL: 文件不存在 {rel}')
        sys.exit(1)
    txt[k] = norm(raw[k])

fails = []

def need(key, needle, label):
    """断言 needle ∈ txt[key]，否则记 FAIL"""
    if needle not in txt[key]:
        fails.append(f'[{key}] 缺少/不符: {label}  (needle={needle!r})')

def forbid(key, bad, label):
    """断言 bad ∉ txt[key]，否则记 FAIL（残留旧语义）"""
    if bad in txt[key]:
        fails.append(f'[{key}] 残留旧语义: {label}  (found={bad!r})')

# ═══════════════════════════════════════════════════
# §1/§2 位域表 + 有效性判据（SimRISC-00 与 contract-isa 双载体）
# ═══════════════════════════════════════════════════
for k in ('s00', 'cis'):
    need(k, '[63:54] = SBZ', 'ra0[63:54]=SBZ')
    need(k, '[53:48] = RACNT', 'ra0[53:48]=RACNT')
    need(k, 'MRPTR：MemRAS 下一个待弹出条目（栈顶）的字节地址', 'ra0[47:0]=MRPTR')
    need(k, '有效性判据 = RACNT（不看条目自身的值）', '§2 判据=RACNT')
    need(k, '有效条目 = 自 ra63 起向下连续 RACNT 个', '§2 有效条目定义')

# 不得出现旧语义
for k in ('s00', 's06', 'cis'):
    forbid(k, '引用计数', '引用计数')
    forbid(k, '条目自身高16', '条目自身高16')
    forbid(k, '条目自身高 16', '条目自身高 16')

# ═══════════════════════════════════════════════════
# §3 压栈 C1–C3b（SimRISC-00 与 contract-isa）
# ═══════════════════════════════════════════════════
for k in ('s00', 'cis'):
    need(k, 'C1 RACNT == 0 → 压入新条目（递归计数 = 1、返回地址），RACNT = 1', 'C1')
    need(k, 'C2 RACNT > 0 且 返回地址 == ra63[47:0]', 'C2 条件')
    need(k, 'ra63[63:48] < 0xFFFF', 'C2 计数上界')
    need(k, '递归折叠优先', 'C2 折叠优先')
    need(k, 'C3a RACNT < 63 → 压入新条目（递归计数 = 1），RACNT += 1', 'C3a')
    need(k, 'C3b RACNT == 63', 'C3b 条件')
    need(k, 'MRPTR -= 8', 'C3b MRPTR-=8')
    need(k, 'RACNT 保持 63', 'C3b RACNT 保持 63')

# ═══════════════════════════════════════════════════
# §4 弹栈 D1–D4b（SimRISC-00 与 contract-isa）
# ═══════════════════════════════════════════════════
for k in ('s00', 'cis'):
    need(k, 'D1 RACNT > 0 且 ra63[63:48] == 0 → RASUF', 'D1')
    need(k, 'D2 RACNT > 0 且 ra63[63:48] > 1 → 计数 -1，RACNT 不变', 'D2')
    need(k, 'D3 RACNT > 0 且 ra63[63:48] == 1 → 弹出栈顶，RACNT - 1', 'D3')
    need(k, 'D4 RACNT == 0', 'D4 条件')
    need(k, 'D4a MRPTR == 0 → RASUF', 'D4a')
    need(k, '递归计数 = 0 → RASUF', 'D4b 计数=0')
    need(k, '= 1 → 返回地址 = 条目低 48 且 MRPTR += 8', 'D4b 计数=1')
    need(k, '> 1 → 该条目压入成为栈顶（计数 -1）且 MRPTR += 8、RACNT = 1', 'D4b 计数>1')

# ═══════════════════════════════════════════════════
# §5 实现注 / §6 精确异常 / §7 影响
# ═══════════════════════════════════════════════════
need('s00', '环形缓冲 + 隐藏基准索引', '§5 实现注')
need('s00', '非架构语义', '§5 非架构标注')
for k in ('s00', 'cis'):
    need(k, '先完成全部 RASOF/RASUF 判定', '§6 先判定')
    need(k, 'RASOF 仅由「需溢出且 MRPTR == 0」触发', '§7 RASOF 条件')
    need(k, 'MemRAS 越界（容量耗尽）不由硬件检测（交 OS）', '§7 MemRAS 交 OS')

# ═══════════════════════════════════════════════════
# SimRISC-06 L99/L122（指向 + 递归计数表述）
# ═══════════════════════════════════════════════════
need('s06', '递归计数（首次压栈设为 1，递归调用递增）', '06 call 递归计数')
need('s06', '见 SimRISC-00 §返回地址栈', '06 call 指向')
need('s06', '[63:48] 为递归计数', '06 ret 递归计数')
need('s06', '见 SimRISC-00 §返回地址栈', '06 ret 指向')

# ═══════════════════════════════════════════════════
# 异常表（contract-isa）
# ═══════════════════════════════════════════════════
need('cis', 'RASOF | RegRAS 满栈（RACNT == 63）且需溢出到 MemRAS 但 MRPTR == 0', '异常表 RASOF')
need('cis', 'RASUF', '异常表 RASUF')

# ═══════════════════════════════════════════════════
# 输出
# ═══════════════════════════════════════════════════
if fails:
    print(f'FAIL: {len(fails)} 项不符')
    for f in fails:
        print('  - ' + f)
    sys.exit(1)

print('PASS: 全部 D7 对照项通过')
sys.exit(0)
