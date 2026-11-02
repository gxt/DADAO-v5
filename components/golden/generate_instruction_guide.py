#!/usr/bin/env python3
"""Generate the Chinese scalar instruction reference from normative metadata.

Prose below is authored from contract-isa/SimRISC, not execution code. Only
identity/encoding/field layout comes from opcodes.yaml. No model import.
--check verifies the checked-in document is reproducible, not ISA correctness.
"""
import argparse
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'components/golden/INSTRUCTION_REFERENCE.md'
_FP_SPEC = yaml.safe_load((ROOT / 'contracts/fp_semantics.yaml').read_text())
FP_FAMILY = {x['id']: x['family'] for x in _FP_SPEC['instructions']}
FP_ANCHOR = {'convert_ff': 2, 'convert_f2i': 3, 'convert_i2f': 4, 'arith': 5,
             'root': 6, 'sign': 7, 'compare': 8, 'classify': 9, 'cs_rf': 10,
             'rf_mem': 11, 'rf_move': 12, 'set_w_rf': 13, 'roundint': 18,
             'minmax': 19, 'fma': 20}
MASK64 = 2**64 - 1


def hx(n):
    return f'0x{n & MASK64:016X}'


def scalar(r):
    # User scope: original integer/memory/transfer/control families, plus the
    # current integer RB-RB subtraction. Never derive scope from model code.
    return ((r['scope'] == 'm1' and not r['format'].startswith('c')) or
            r['id'] == 'sub.o_orrr_dbb' or r['scope'] == 'fp')


def spec_link(cite):
    number = cite.split(':', 1)[0].strip() if ':' in cite else cite.split()[0]
    files = sorted((ROOT / 'spec').glob(number + '-*.md'))
    if len(files) != 1:
        raise ValueError(f'cannot resolve spec source {cite}')
    return f'[{cite}](../../spec/{files[0].name})'


def body(r):
    """Return category, meaning, operands, steps, faults, example, source."""
    mn, fmt, iid = r['mnemonic'], r['format'], r['id']
    fields = [f['name'] for f in r['fields']]
    base = mn.split('.')[0]
    normal = '本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。'
    destfault = '目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。'
    if base in ('ld','ldm','st','stm'):
        load = base in ('ld','ldm'); multi = base in ('ldm','stm')
        bank = iid.rsplit('_',1)[1]; reg=bank+'ha'
        suffix=mn.split('.')[1]; size={'b':1,'w':2,'t':4,'o':8}[suffix[-1]]
        sign=suffix.startswith('s') and load; bits=size*8
        meaning=f'{"连续" if multi else "单次"}{"读取" if load else "存储"}{bits}位数据，{"写入" if load else "读出"}{bank.upper()}寄存器。'
        operands=f'`{reg}` 是{"第一个" if multi else ""}{"目的" if load else "源"}寄存器，`rbhb` 是地址基址；'+('`rdhc` 是字节偏移，`immu6` 是寄存器个数。' if multi else '`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。')
        address='EA[i] = (旧RB[hb] + 旧RD[hc] + i×'+str(size)+') mod 2^48，i=0…immu6−1' if multi else 'EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48'
        steps=[f'计算地址：`{address}`。'+('基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。' if multi else ''),f'每个元素占{size}字节，地址低处存高字节（大端）。']
        if load:
            steps.append(f'按地址读取{bits}位，'+('将其最高位作为符号位，符号扩展到64位' if sign else '零扩展到64位' if bits<64 else '保留完整64位位模式')+f'，写入 `{bank.upper()}[ha'+('+i' if multi else '')+']`，覆盖旧值。')
        else:steps.append(f'从 `{bank.upper()}[ha'+('+i' if multi else '')+f']` 读取原值，仅将低{bits}位写入对应的{size}个内存字节，其余内存不改。源寄存器不改。')
        if bank=='ra' and load:steps.append('若目的包含 ra0，只写 RACNT[53:48] 和 MRPTR[47:0]，SBZ[63:54] 不写入；其他RA条目保留完整64位。')
        steps.append(normal)
        faults=[]
        if load and bank in ('rd','rb'):faults.append(f'目的起点 `{reg}` 不可为 `{bank}0`，否则 ILLI。')
        elif not load and bank in ('rd','rb'):faults.append(f'源 `{bank}0` 合法，读出'+('0。' if bank=='rd' else '本条执行前的完整rb0值。'))
        else:faults.append('ra0 作为源或目的均合法；它的写屏蔽规则仍有效。')
        if multi:faults.append(f'`immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。')
        faults.append(f'有效地址必须是{size}的整数倍，否则 MALIGN。' if size>1 else 'byte访问不要求额外对齐。')
        if load:
            value=(1<<bits)-1; expected=MASK64 if sign else value
            example=f'基址0x1000、偏移0，'+('个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1='+hx(expected)+'、寄存器2=1。' if multi else f'内存该{size}字节全为FF；目的选寄存器1，结果 `{hx(expected)}`。')
        else:
            example=f'基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `{((0x1122334455667788) % (1<<bits)).to_bytes(size,"big").hex(" ").upper()}`。'+(f'个数2时，寄存器2=1还会在 `0x{0x1000+size:X}` 写入{size}字节的值1。' if multi else '')
        return '访存',meaning,operands,steps,' '.join(faults),example,'§3.1–3.3、§1.3.4'
    if mn in ('rd2rd','rb2rd','rd2rb','rb2rb','rd2ra','ra2rd'):
        src,dst=mn[:2],mn[-2:]; same=src==dst
        steps=[f'先检查两个寄存器区间，再按 i=0…n−1 将旧的 `{src.upper()}[hc+i]` 复制到 `{dst.upper()}[hb+i]`；每个元素64位，不做符号转换或48位截断。']
        if dst=='ra':steps.append('目的包含ra0时，丢弃写入值的SBZ[63:54]，只写其余54位。')
        steps.append(normal)
        faults=f'`n=immu6` 必须为1–63，`hb+n<=64` 且 `hc+n<=64`；否则 ILLI。'
        if dst in ('rd','rb'):faults+=f' 目的起点不可为 `{dst}0`。'
        if same:faults+=' 两区间有任何交集（包括完全相同）即 ILLI。'
        else:faults+=' 不同寄存器组的同号区间不构成重叠；源可包含0号寄存器。'
        return '寄存器传送',f'把{src.upper()}连续寄存器复制到{dst.upper()}。',f'`{dst}hb` 是目的起点，`{src}hc` 是源起点，`immu6` 是个数。',steps,faults,f'源寄存器1=5、2=9，目的起点10、个数2；执行后 `{dst}10=5`、`{dst}11=9`，其他显式寄存器不变。','§4、§3.3.3'
    if fmt=='rwii':
        bank=fields[0][:2]; reg=fields[0]; op=mn.split('.')[0]
        effect={'set':'','or':'将目标16位与立即数逐位或，其余48位保留。','andn':'将目标16位与立即数的16位按位取反值逐位与，其余48位保留。'}
        if mn=='set.zw':rule='把目标16位置为immu16，其余48位全部清零。';ex='旧值全1、wp1、immu16=0x1234，结果 `0x0000000012340000`。'
        elif mn=='set.ow':rule='把目标16位置为immu16，其余48位全部置一。';ex='旧值0、wp1、immu16=0x1234，结果 `0xFFFFFFFF1234FFFF`。'
        elif op=='or':rule=effect[op];ex='旧值 `0x00000000000F0001`、wp1、immu16=0x00F0，结果 `0x0000000000FF0001`。'
        else:rule=effect[op];ex='旧值全1、wp1、immu16=0x00F0，结果 `0xFFFFFFFFFF0FFFFF`。'
        return '立即数设置',f'用16位立即数修改{bank.upper()}寄存器。',f'`{reg}` 是目的'+('兼源（读改写）' if op in ('or','andn') else '')+'，`wpN` 选择16位段，`immu16` 范围0–65535。',[ 'wp0、wp1、wp2、wp3分别选 bits[15:0]、[31:16]、[47:32]、[63:48]。',rule,normal],f'目的 `{bank}0` 为 ILLI。立即数/段号超出编码范围属于输入/汇编错误，不应静默截断。',ex,'§5、§2.4'
    if fmt=='rrrr' and base in ('add','sub','mul'):
        signed='.so' in mn; op={'add':'+','sub':'−','mul':'×'}[base]
        steps=[f'一次读取旧RD[hc]和旧RD[hd]，按64位'+('有符号补码' if signed else '无符号整数')+f'解释，计算数学结果 `R=A{op}B`。', '将R取模2^128，高64位写RD[ha]、低64位写RD[hb]；两个源先读取，目的覆盖源不会改变本次计算。',normal]
        example={'add':('A=−1、B=1，高=0、低=0。' if signed else 'A=0xFFFFFFFFFFFFFFFF、B=1，高=1、低=0。'),'sub':('A=0、B=1，高和低均为0xFFFFFFFFFFFFFFFF。' if signed else 'A=0、B=1，借位=1、低=0xFFFFFFFFFFFFFFFF；A=9、B=4，借位=0、低=5。'),'mul':('A=−2、B=3，高=0xFFFFFFFFFFFFFFFF、低=0xFFFFFFFFFFFFFFFA。' if signed else 'A=0xFFFFFFFFFFFFFFFF、B=2，高=1、低=0xFFFFFFFFFFFFFFFE。')}[base]
        if mn=='sub.uo':
            steps[1]='无借位时 rdHA=0、rdHB=(A−B) mod 2^64；有借位（A<B）时 rdHA=1、rdHB=(A−B) mod 2^64（ADR-0049）。低 64 位始终是差，不写 128 位结果的全 1 高半。'
            return ('双目的整数运算', '64位无符号减法：rdHB 为差，rdHA 为借位。',
                    '`rdha` 为借位目的，`rdhb` 为低64位差目的，`rdhc/rdhd` 为源。',
                    steps, '两个目的同时为rd0或为同一个非零寄存器，触发ILLI。允许一个目的为rd0（丢弃该半）；源可为rd0。借位按 ADR-0049 写 0/1，不触发异常。',
                    'A=0、B=1，借位=1、低=0xFFFFFFFFFFFFFFFF；A=9、B=4，借位=0、低=5。',
                    '§6.1.1')
        return '双目的整数运算',f'64位{"有符号" if signed else "无符号"}{ {"add":"加法","sub":"减法","mul":"乘法"}[base]}，产生高、低两个结果。','`rdha` 为高结果目的，`rdhb` 为低结果目的，`rdhc/rdhd` 为源。',steps,'两个目的同时为rd0或为同一个非零寄存器，触发ILLI。允许一个目的为rd0（丢弃该半）；源可为rd0。普通进位/溢出不触发异常。',example,'§6.1.1、§6.1.4'
    if mn=='add.si':
        bank=fields[0][:2]
        return '地址与立即数算术','将有符号立即数加到原寄存器上。',f'`{fields[0]}` 同时为源和目的，imms18范围−131072至131071。',[f'读取旧{bank.upper()}[ha]，将imms18符号扩展到64位；`结果=(旧值+立即数) mod 2^64`，写满64位。','溢出回绕，不保留旧高位，也不设置额外整数标志寄存器。',normal],f'目的 `{bank}0` 为ILLI。', '旧值0、立即数−1，结果0xFFFFFFFFFFFFFFFF。','§6.1.3、§7.2'
    if mn in ('cmp.si','cmp.ui'):
        sign=mn=='cmp.si';imm='imms12' if sign else 'immu12'
        return '整数比较','将寄存器与立即数比较，返回−1/0/+1。',f'rdha为目的，rdhb为源，{imm}为12位'+('有符号立即数（−2048…2047）。' if sign else '无符号立即数（0…4095）。'),['将RD[hb]按64位'+('有符号补码' if sign else '无符号整数')+'解释，与立即数数值比较。','小于写0xFFFFFFFFFFFFFFFF，相等写0，大于写1；完整覆盖RD[ha]。',normal],destfault,'RD[hb]=5、立即数7，RD[ha]=0xFFFFFFFFFFFFFFFF；立即数5时为0、3时为1。','§6.2.1'
    if iid.endswith(('_bbd','_dbb')):
        compare=base=='cmp'; bbd=iid.endswith('_bbd')
        dst='RB[hb]' if bbd else 'RD[hb]';right='RD[hd]' if bbd else 'RB[hd]'
        rule='按完整64位无符号比较A、B，小于/等于/大于分别写全64位−1/0/+1。' if compare else f'`{dst}=(A'+('+' if base=='add' else '−')+'B) mod 2^64`，不截到48位。'
        return '地址与立即数算术','比较完整地址寄存器值。' if compare else '进行完整64位地址加减。',f'目的为{dst}，源A=旧RB[hc]，源B=旧{right}。',[rule,'源先读再写；高16位也参与运算。只在后续访存/取指时截到48位。',normal],f'目的 {"rb0" if bbd else "rd0"} 为ILLI；0号源合法。',('A=0x0001000000000005、B=6，结果1。' if compare else 'A=0x0001000000000005、B=7，结果'+('0x000100000000000C。' if base=='add' else '0x0000FFFFFFFFFFFE。')),'§7.1、§7.3'
    if iid == 'aip.si_riii_rb':
        return '地址与立即数算术','将当前指令地址加上4KiB单位的有符号偏移写入RB。','`rbha` 是目的；`imms18` 是编码层有符号4KiB块偏移。',['读取执行前的完整 `rb0`（IP）。','计算 `RB[ha] = (旧rb0 + (imms18 << 12)) mod 2^64`。','只有后续访存使用该结果的低48位；本条写回保留完整64位。',normal],'目的为rb0时ILLI；偏移须由编码提供，源rb0取本条当前地址。','旧rb0=0x1000、imms18=1，则rb1=0x2000。','SimRISC-05 §3.4'
    if base in ('add','sub','mul','div','rem','cmp','and','or','xor','xnor','shl','shr','ext'):
        suffix=mn.split('.')[1];w={'b':8,'w':16,'t':32,'o':64}[suffix[-1]];sign=suffix.startswith('s');m=(1<<w)-1
        if base in ('and','or','xor','xnor'):
            rules={'and':'两位都为1才得1。','or':'至少一位为1就得1。','xor':'两位不同得1。','xnor':'两位相同得1（异或后按64位取反）。'}
            ex={'and':8,'or':14,'xor':6,'xnor':MASK64^6}[base]
            return '逻辑运算','逐位计算两个64位源。','RD[hb]为目的，RD[hc]/RD[hd]为源。',[rules[base],'对全部64位运算并写满目的，不保留目的旧位。',normal],destfault,f'A=0xC、B=0xA，结果 `{hx(ex)}`。','§6.3'
        if base in ('shl','shr','ext'):
            amt='k=immu6' if fmt=='orri' else 'k=旧RD[hd] & 0x3F'
            opdesc=('从第k位向高位扩展。' if base=='ext' else '左移，低位补0。' if base=='shl' else '算术右移，高位补源的符号位。' if sign else '逻辑右移，高位补0。')
            steps=[f'计算 `{amt}`；'+('这是最后保留的位编号，不是位数。' if base=='ext' else f'源只取低{w}位。')]
            if base=='ext':steps.append('保留源bits[k:0]，其余高位'+('用源bit[k]填充，形成64位符号扩展结果。' if sign else '清零，形成64位零扩展结果。'))
            else:steps.extend([opdesc,f'结果只保留低{w}位，再'+('符号' if sign else '零')+'扩展到64位写回；目的旧高位被覆盖。'])
            steps.append(normal)
            if base=='ext':example='源0x180、k=7，结果'+('0xFFFFFFFFFFFFFF80。' if sign else '0x0000000000000080。')
            elif base=='shl':example=f'源 `{hx(1<<(w-1))}`、k=1，移出有效宽度后结果0。'
            else:example=f'源低{w}位全1、k=1，结果 `{hx(MASK64 if sign else m>>1)}`。'
            return '移位与扩展',f'{w}位'+opdesc,'RD[hb]为目的、RD[hc]为源；'+('immu6直接给出k。' if fmt=='orri' else 'RD[hd]给出k，仅读其低6位。'),steps,destfault+f' k>{w-1}时ILLI；检查之前不能再按{w}取模。'+('本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。' if w==64 else ''),example,'§6.4、§10.4、§11.4、§12.4'
        steps=[f'取两个源的低{w}位，按'+('有符号补码' if sign else '无符号整数')+'解释为A、B。']
        descriptions={'add':'相加','sub':'相减','mul':'相乘','div':'求商','rem':'求余数','cmp':'比较'}
        if base in ('add','sub','mul'):steps.append(f'计算 `R=A{ {"add":"+","sub":"−","mul":"×"}[base]}B`，保留低'+str(w)+'位；超出位宽的部分丢弃。')
        elif base=='cmp':steps.append('A小于B时R=−1，相等时R=0，大于时R=1；结果写满64位，不按操作宽度零扩展。')
        else:
            steps.append('正常除法得到Q='+('向零截断(A/B)' if sign else 'floor(A/B)')+'，余数T=A−Q×B；'+('非零余数与A同号。' if sign else '余数在0至B−1之间。')+('本指令返回Q。' if base=='div' else '本指令返回T。'))
            steps.append('B按位宽截断后为0时，'+('返回该宽度的全1。' if base=='div' else '返回A。')+' 不触发ILLI。')
            if sign:steps.append(f'A=−2^{w-1}且B=−1时，'+(f'返回−2^{w-1}。' if base=='div' else '返回0。')+' 不触发ILLI。')
        if base=='cmp':
            steps.extend(['R写满RD[hb]的64位，不保留旧高位。',normal])
        else:
            steps.extend([f'R的低{w}位按'+('符号' if sign else '零')+'扩展写满RD[hb]的64位，不保留旧高位。',normal])
        if base=='cmp':example=f'A=1、B=2，结果 `{hx(MASK64)}`；A=B时为0，A>B时为1。'
        elif base in ('div','rem'):
            example=('A=−7、B=3，结果 '+(hx(-2) if base=='div' else hx(-1))+'。') if sign else 'A=7、B=3，结果'+('2。' if base=='div' else '1。')
        else:
            ex={'add':(1<<(w-1))-1+1,'sub':0-1,'mul':3*5}[base]&m
            val=ex-(1<<w) if sign and ex&(1<<(w-1)) else ex
            example=({'add':f'A=2^{w-1}−1、B=1','sub':'A=0、B=1','mul':'A=3、B=5'}[base])+f'，结果 `{hx(val)}`。'
        return '定宽整数运算',f'{w}位{"有符号" if sign else "无符号"}{descriptions[base]}。','RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。',steps,destfault,example,'§6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2'
    if base=='cs':
        kind=mn.split('.')[1];dual=kind in ('eq','ne')
        cond={'n':'按64位补码为负数（bit63=1）','z':'全部64位为0','p':'bit63=0且值不为0','eq':'RD[ha]与RD[hb]的完整64位相等','ne':'RD[ha]与RD[hb]的完整64位不同'}[kind]
        steps=['在任何写入前读取条件和所需源值。',('若'+cond+'，将旧RD[hd]写入RD[hc]；否则保留RD[hc]旧值。' if dual else '若旧RD[ha]'+cond+'，RD[hb]=旧RD[hc]；否则RD[hb]=旧RD[hd]。'),'赋值写满64位；条件不成立并不豁免非法目的检查。',normal]
        ex=('两个比较源'+('相等' if kind=='eq' else '不同')+'、旧RD[hd]=9时，目的变9；相反条件下目的旧值保持。') if dual else '旧RD[ha]='+{'n':'−1','z':'0','p':'1'}[kind]+'、RD[hc]=7、RD[hd]=9时，目的得7；旧RD[ha]='+{'n':'0','z':'1','p':'0'}[kind]+'时得9。'
        return '条件赋值','根据条件选择或保留寄存器值。',('RD[ha]/RD[hb]为比较源，RD[hc]为目的，RD[hd]为赋值源。' if dual else 'RD[ha]为条件源，RD[hb]为目的，RD[hc]/RD[hd]为两个候选源。'),steps,f'目的 {"rdhc" if dual else "rdhb"}=rd0时ILLI；源可为rd0。所有别名读取执行前值。',ex,'§6.5'
    if base in ('br','jump','call','ret'):
        control='计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。'
        if base=='br':
            kind=mn.split('.')[1];bank='rb' if iid.endswith('_rb') else 'rd';dual=kind in ('eq','ne')
            condition={'n':'RD[ha]的bit63=1','nn':'RD[ha]的bit63=0','z':bank.upper()+'[ha]的全部64位为0','nz':bank.upper()+'[ha]的64位值不等于0','p':'RD[ha]的bit63=0且值非0','np':'RD[ha]的bit63=1或值为0','eq':'RD[ha]与RD[hb]的64位值相等','ne':'RD[ha]与RD[hb]的64位值不同'}[kind]
            imm='imms12' if dual else 'imms18'
            return '控制流',f'当{condition}时跳转。',f'条件源为{bank.upper()}[ha]'+('和RD[hb]' if dual else '')+f'；{imm}为有符号指令偏移（单位4字节）。',[f'判断旧状态的条件：{condition}。',f'成立：目标=(旧rb0 + ({imm}<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。',control],'源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。','旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。','§8.1–8.2'
        if base in ('jump','call'):
            relative=fmt=='iiii';target='(旧rb0 + (imms24<<2)) mod 2^64' if relative else '(旧RB[ha] + 旧RD[hb] + (imms12<<2)) mod 2^64'
            steps=[f'先用旧状态计算目标 `{target}`；立即数是有符号数、单位4字节。']
            if base=='call':steps.append('将 `(旧rb0+4) mod 2^48` 作为返回地址，执行本文“共同规则：call压栈”的完整流程；新条目递归计数为1。同址且未饱和时递归折叠。栈更新成功后才提交跳转。')
            steps.append(control)
            faults='源可为rd0/rb0。目标低两位非0时，本条完成跳转；下一条取指才报IALIGN。'
            if base=='call':faults+=' 返回栈满且未启用MemRAS时RASOF；MemRAS溢出写地址未8字节对齐时MALIGN；异常时返回栈、内存、PC全部不变。'
            ex='旧rb0=0x1000，'+('imms24=3' if relative else 'RB[ha]=0x2000、RD[hb]=8、imms12=−1')+'，下一地址'+('0x100C。' if relative else '0x2004。')
            if base=='call':ex+=' 若RACNT原为0，ra63变为0x0001000000001004，RACNT变1。'
            return '控制流',('调用函数并保存返回地址。' if base=='call' else '无条件跳转。'),('imms24是24位有符号指令偏移。' if relative else 'RB[ha]为基址源、RD[hb]为字节偏移源、imms12为有符号指令偏移。'),steps,faults,ex,'§8.3–8.6'
        return '控制流','弹出返回地址，并可同时设置整数返回值。','RD[ha]为返回值目的，imms18为18位有符号返回值；地址来自RAS而非立即数。',['先检查ret rd0的立即数限制，再执行本文“共同规则：ret弹栈”完整流程，取得返回地址。','把imms18符号扩展写入RD[ha]；合法rd0形式丢弃写入。','把弹出的48位返回地址零扩展写入rb0；pc和pc_next为该取指地址。'],'rdha=rd0且imms18非0为ILLI；有效栈顶计数0、空栈且无MemRAS、MemRAS条目计数0为RASUF；读取MemRAS地址未8字节对齐为MALIGN。所有异常都不改变原状态。','RACNT=1、ra63=0x0001000000002000，ret rd1,−1后RD1=0xFFFFFFFFFFFFFFFF、RACNT=0、下一地址0x2000。','§8.5–8.6'
    if mn=='swym':
        return '其他标量指令','空操作/延时提示；单步golden只观察架构效果。','immu18为18位无符号提示值0…262143。',['不修改数据寄存器、RA、RF和内存。',normal,'不模拟周期；非零参数也不能被当成非法指令。'],'本条无额外操作数异常；共同的取指IALIGN检查仍适用。','旧rb0=0x1000，无论immu18=0还是1，下一地址0x1004，其他架构状态不变。','§13.1'
    raise ValueError(f'no normative prose for {iid}')


def pseudocode(r):
    """Return code-like, identity-specific execution steps.

    The generated blocks deliberately use expressions rather than explanatory
    prose. ``S`` is the complete pre-instruction snapshot and ``D`` is the
    tentative post-state; no destination is committed until all checks pass.
    """
    mn, fmt, iid = r['mnemonic'], r['format'], r['id']
    base = mn.split('.')[0]
    MASK64 = '(1 << 64) - 1'
    MASK48 = '(1 << 48) - 1'

    if r['scope'] == 'fp':
        fp = yaml.safe_load((ROOT / 'contracts/fp_semantics.yaml').read_text())
        family = {x['id']: x['family'] for x in fp['instructions']}[iid]
        fmt_bits = 32 if mn.startswith('ft') else 64
        fmt_name = 'binary32' if fmt_bits == 32 else 'binary64'
        if family == 'arith':
            op = {'ftadd':'add','foadd':'add','ftsub':'sub','fosub':'sub',
                  'ftmul':'mul','fomul':'mul','ftdiv':'div','fodiv':'div',
                  'ftrem':'remainder','forem':'remainder',
                  'ftsclb':'scaleB','fosclb':'scaleB'}[mn]
            return [
                'S = snapshot(state)',
                f'A = decode_fp(S.RF[hc], format={fmt_name})',
                f'B = decode_fp(S.RF[hd], format={fmt_name})',
                f'(R, F) = fp_{op}(A, B, rounding=S.RF[0][33:32])',
                f'D.RF[hb] = encode_fp(R, format={fmt_name})',
                'D.RF[0][4:0] = S.RF[0][4:0] | F',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'commit(D)']
        if family in ('convert_ff', 'convert_f2i', 'convert_i2f', 'classify', 'rf_move'):
            src = 'RD' if family == 'convert_i2f' or iid == 'rd2rf_orri_rf' else 'RF'
            dst = 'RD' if family in ('convert_f2i', 'classify') or iid == 'rf2rd_orri_rf' else 'RF'
            if family == 'convert_ff':
                src_fmt = 'binary32' if mn.startswith('ft') else 'binary64'
                dst_fmt = 'binary32' if mn.endswith('ft') else 'binary64'
                action = f'convert_fp(src[i], {src_fmt}, {dst_fmt}, rounding)'
            elif family == 'convert_f2i':
                target = mn[-2:]
                action = f'fp_to_int(src[i], {"signed" if target.startswith("i") else "unsigned"}, {32 if target.endswith("t") else 64}, rounding, saturate=True)'
            elif family == 'convert_i2f':
                source = mn[:2]
                action = f'int_to_fp(src[i], {"signed" if source.startswith("i") else "unsigned"}, {32 if source.endswith("t") else 64}, {"binary32" if mn.endswith("ft") else "binary64"}, rounding)'
            elif family == 'classify': action = 'classify_fp(src[i]) & 0x3ff'
            else: action = 'src[i]'
            lines = [
                'S = snapshot(state)',
                'N = immu6',
                'assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64',
                f'src[i] = S.{src}[hc + i] for i in range(N)',
                'rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]',
            ]
            if family in ('convert_ff', 'convert_f2i', 'convert_i2f'):
                lines.append(f'for i in range(N): val[i], flg[i] = {action}')
                lines.append(f'D.{dst}[hb:hb + N] = val[0:N]')
                lines.append('D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)')
            else:
                lines.append(f'for i in range(N): val[i] = {action}')
                lines.append(f'D.{dst}[hb:hb + N] = val[0:N]')
            lines += ['D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
            return lines
        if family == 'root':
            return [
                'S = snapshot(state)',
                'assert immu6 == 2',
                f'X = decode_fp(S.RF[hc], format={fmt_name})',
                'assert not (is_negative_zero(X))  # SPECIFICATION-GAP otherwise',
                'R, F = fp_sqrt(X, rounding=S.RF[0][33:32])',
                f'D.RF[hb] = encode_fp(R, format={fmt_name})',
                'D.RF[0][4:0] = S.RF[0][4:0] | F',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'commit(D)']
        if family == 'sign':
            sign_expr = 'sign(S.RF[hd])' if mn.endswith('sgnj') else '1 ^ sign(S.RF[hd])'
            return [
                'S = snapshot(state)',
                f'A = S.RF[hc] & ((1 << {fmt_bits}) - 1)',
                f's = {sign_expr}',
                f'D.RF[hb] = (A & ((1 << ({fmt_bits} - 1)) - 1)) | (s << {fmt_bits - 1})',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'commit(D)']
        if family == 'compare':
            nan_result = 'positive_snan' if mn.endswith('scmp') else 'positive_qnan'
            return [
                'S = snapshot(state)',
                f'A = decode_fp(S.RF[hc], format={fmt_name})',
                f'B = decode_fp(S.RF[hd], format={fmt_name})',
                f'R = {nan_result} if (is_nan(A) or is_nan(B)) else (-1 if A < B else (0 if A == B else 1))',
                'D.RD[hb] = R & ((1 << 64) - 1)',
                'D.RF[0][4:0] = S.RF[0][4:0] | (NV if has_signaling_nan(A, B) else 0)',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'commit(D)']
        if family == 'roundint':
            return [
                'S = snapshot(state)',
                f'A = decode_fp(S.RF[hc], format={fmt_name})',
                'assert immu6 in {0x01, 0x02, 0x04, 0x08, 0x10, 0x20}',
                'R, F = round_to_integral(A, selector=immu6, rounding=S.RF[0][33:32])',
                f'D.RF[hb] = encode_fp(R, format={fmt_name})',
                'D.RF[0][4:0] = S.RF[0][4:0] | F',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'commit(D)']
        if family == 'minmax':
            fn = 'fp_minimumNumber' if mn.endswith('min') else 'fp_maximumNumber'
            return [
                'S = snapshot(state)',
                f'A = decode_fp(S.RF[hc], format={fmt_name})',
                f'B = decode_fp(S.RF[hd], format={fmt_name})',
                f'R, F = {fn}(A, B)',
                f'D.RF[hb] = encode_fp(R, format={fmt_name})',
                'D.RF[0][4:0] = S.RF[0][4:0] | F',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'commit(D)']
        if family == 'fma':
            return [
                'S = snapshot(state)',
                f'A = decode_fp(S.RF[hb], format={fmt_name})',
                f'B = decode_fp(S.RF[hc], format={fmt_name})',
                f'C = decode_fp(S.RF[hd], format={fmt_name})',
                'R, F = fp_fusedMultiplyAdd(A, B, C, rounding=S.RF[0][33:32])',
                f'D.RF[ha] = encode_fp(R, format={fmt_name})',
                'D.RF[0][4:0] = S.RF[0][4:0] | F',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'commit(D)']
        if family == 'cs_rf':
            cond = {'cs.n':'((S.RD[ha] >> 63) & 1) == 1', 'cs.z':'S.RD[ha] == 0',
                    'cs.p':'(((S.RD[ha] >> 63) & 1) == 0 and S.RD[ha] != 0)', 'cs.eq':'S.RD[ha] == S.RD[hb]',
                    'cs.ne':'S.RD[ha] != S.RD[hb]'}[mn]
            if mn in ('cs.n', 'cs.z', 'cs.p'):
                return [
                    'S = snapshot(state)',
                    f'D.RF[hb] = S.RF[hc] if ({cond}) else S.RF[hd]',
                    'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                    'commit(D)']
            return [
                'S = snapshot(state)',
                f'D.RF[hc] = S.RF[hd] if ({cond}) else S.RF[hc]',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'commit(D)']
        if family == 'rf_mem':
            width = 4 if mn.endswith('.t') else 8
            off = 'S.RD[hc]' if fmt == 'rrri' else 'sext(imms12, 12)'
            lines = ['S = snapshot(state)', 'N = immu6' if fmt == 'rrri' else 'N = 1']
            if fmt == 'rrri':
                lines.append('assert 1 <= N <= 63 and ha + N <= 64')
            lines += [f'EA[i] = (S.RB[hb] + {off} + i * {width}) & ({MASK48}) for i in range(N)',
                      f'assert all(EA[i] % {width} == 0 for i in range(N))']
            if mn.startswith('ld'):
                lines += [f'v[i] = be_load(S.mem, EA[i], {width}) for i in range(N)',
                          f'R[i] = ((S.RF[ha + i] & 0xffffffff00000000) | v[i]) if {width} == 4 else v[i] for i in range(N)',
                          'D.RF[ha + i] = ((S.RF[ha + i] & ~FCSR_WRITE_MASK) | (R[i] & FCSR_WRITE_MASK)) if ha + i == 0 else R[i] for i in range(N)']
            else:
                lines += [f'v[i] = S.RF[ha + i] & ((1 << {width * 8}) - 1) for i in range(N)',
                          f'D.mem[(EA[i] + j) & ({MASK48})] = be_bytes(v[i], {width})[j] for i in range(N) for j in range({width})']
            lines += ['D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
            return lines
        if family == 'set_w_rf':
            return [
                'S = snapshot(state)',
                'shift = 16 * wpN',
                'mask = 0xffff << shift',
                'R = (S.RF[ha] & ~mask) | (immu16 << shift)',
                'FCSR_WRITE_MASK = (0x3 << 32) | 0x1f',
                'D.RF[ha] = (S.RF[ha] & ~(mask & FCSR_WRITE_MASK)) | (R & mask & FCSR_WRITE_MASK) if ha == 0 else R',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'commit(D)']

    # Scalar instruction families.
    if base in ('ld', 'ldm', 'st', 'stm'):
        load = base in ('ld', 'ldm')
        multi = base in ('ldm', 'stm')
        bank = iid.rsplit('_', 1)[1]
        suffix = mn.split('.')[1]
        size = {'b': 1, 'w': 2, 't': 4, 'o': 8}[suffix[-1]]
        bits = size * 8
        off = 'S.RD[hc]' if multi else 'sext(imms12, 12)'
        lines = ['S = snapshot(state)', f'N = immu6' if multi else 'N = 1']
        if multi:
            lines.append('assert 1 <= N <= 63 and ha + N <= 64')
        lines += [f'EA[i] = (S.RB[hb] + {off} + i * {size}) & ({MASK48}) for i in range(N)',
                  f'assert all(EA[i] % {size} == 0 for i in range(N))']
        if load:
            extend = 'sext(v[i], {bits})' if suffix.startswith('s') else 'zext(v[i], {bits})'
            if bits == 64: extend = 'v[i]'
            lines += [f'v[i] = be_load(S.mem, EA[i], {size}) for i in range(N)',
                      f'D.{bank.upper()}[ha + i] = {extend.format(bits=bits)} for i in range(N)']
            if bank == 'ra':
                lines += ['D.RA[0] = (D.RA[0] & 0x003fffffffffffff) | (S.RA[0] & 0xffc0000000000000)']
        else:
            lines += [f'v[i] = S.{bank.upper()}[ha + i] & ((1 << {bits}) - 1) for i in range(N)',
                      f'D.mem[EA[i]:EA[i] + {size}] = be_bytes(v[i], {size}) for i in range(N)']
        lines += ['D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
        return lines
    if fmt == 'rwii':
        bank = r['fields'][0]['name'][:2].upper()
        dst = r['fields'][0]['name']
        result = {
            'or': '(old | (imm << shift))',
            'andn': '(old & ~(imm << shift))',
            'set': '(imm << shift)',
        }[base]
        if mn == 'set.ow': result = '((~mask) & ((1 << 64) - 1)) | (imm << shift)'
        return ['S = snapshot(state)', 'shift = 16 * wpN', 'mask = 0xffff << shift',
                'old = S.%s[%s] & ((1 << 64) - 1)' % (bank, dst[2:]),
                'imm = immu16 & 0xffff',
                'D.%s[%s] = %s' % (bank, dst[2:], result),
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if mn in ('rd2rd', 'rb2rd', 'rd2rb', 'rb2rb', 'rd2ra', 'ra2rd'):
        src, dst = mn[:2].upper(), mn[-2:].upper()
        src_field, dst_field = r['fields'][1]['name'], r['fields'][0]['name']
        return ['S = snapshot(state)', 'N = immu6', 'assert 1 <= N <= 63',
                f'assert {dst_field[2:]} + N <= 64 and {src_field[2:]} + N <= 64',
                f'assert not ("{src}" == "{dst}" and overlap([{src_field[2:]}, {src_field[2:]} + N), [{dst_field[2:]}, {dst_field[2:]} + N)))',
                f'tmp[i] = S.{src}[{src_field[2:]} + i] for i in range(N)',
                f'D.{dst}[{dst_field[2:]} + i] = tmp[i] for i in range(N)',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if fmt == 'rrrr' and base in ('add', 'sub', 'mul'):
        signed = mn.endswith('.so')
        op = {'add': '+', 'sub': '-', 'mul': '*'}[base]
        cast = 'sint' if signed else 'uint'
        if mn == 'sub.uo':
            return ['S = snapshot(state)', 'A = uint(S.RD[hc], 64)', 'B = uint(S.RD[hd], 64)',
                    'D.RD[hb] = (A - B) & ((1 << 64) - 1)',
                    'D.RD[ha] = 1 if A < B else 0',
                    'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
        return ['S = snapshot(state)', f'A = {cast}(S.RD[hc], 64)', f'B = {cast}(S.RD[hd], 64)',
                f'R = A {op} B', 'U = R & ((1 << 128) - 1)',
                'D.RD[ha] = (U >> 64) & ((1 << 64) - 1)',
                'D.RD[hb] = U & ((1 << 64) - 1)',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if mn == 'add.si':
        return ['S = snapshot(state)', 'D.%s[ha] = (S.%s[ha] + sext(imms18, 18)) & ((1 << 64) - 1)' %
                (r['fields'][0]['name'][:2].upper(), r['fields'][0]['name'][:2].upper()),
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if mn in ('cmp.si', 'cmp.ui'):
        signed = mn.endswith('.si')
        cast = 'sint' if signed else 'uint'
        imm = 'sext(imms12, 12)' if signed else 'immu12'
        return ['S = snapshot(state)', f'A = {cast}(S.RD[hb], 64)', f'B = {imm}',
                'R = -1 if A < B else (0 if A == B else 1)',
                'D.RD[ha] = R & ((1 << 64) - 1)',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if iid == 'aip.si_riii_rb':
        return ['S = snapshot(state)', 'D.RB[ha] = (S.RB[0] + (sext(imms18, 18) << 12)) & ((1 << 64) - 1)',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if iid.endswith(('_bbd', '_dbb')):
        dst = 'RB[hb]' if iid.endswith('_bbd') else 'RD[hb]'
        a = 'S.RB[hc]'; b = 'S.RD[hd]' if iid.endswith('_bbd') else 'S.RB[hd]'
        if base == 'cmp':
            expr = f'-1 if {a} < {b} else (0 if {a} == {b} else 1)'
        else:
            expr = f'({a} {"+" if base == "add" else "-"} {b}) & ((1 << 64) - 1)'
        return ['S = snapshot(state)', f'D.{dst} = {expr}',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if base in ('and', 'or', 'xor', 'xnor'):
        op = {'and': '&', 'or': '|', 'xor': '^', 'xnor': '^'}[base]
        tail = ['R = (A %s B) & ((1 << 64) - 1)' % op]
        if base == 'xnor': tail.append('R ^= ((1 << 64) - 1)')
        return ['S = snapshot(state)', 'A = S.RD[hc]', 'B = S.RD[hd]'] + tail + [
            'D.RD[hb] = R', 'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if base in ('shl', 'shr', 'ext'):
        suffix = mn.split('.')[1]
        width = {'b': 8, 'w': 16, 't': 32, 'o': 64}[suffix[-1]]
        signed = suffix.startswith('s')
        amount = 'immu6' if fmt == 'orri' else '(S.RD[hd] & 0x3f)'
        if base == 'ext':
            op = 'sext' if signed else 'zext'
            result = f'{op}(S.RD[hc] & ((1 << (k + 1)) - 1), k + 1)'
            check = f'assert 0 <= k < {width}'
        elif base == 'shl':
            result = f'(S.RD[hc] & ((1 << {width}) - 1)) << k'
            check = f'assert 0 <= k < {width}'
        elif signed:
            result = f'sint(S.RD[hc] & ((1 << {width}) - 1), {width}) >> k'
            check = f'assert 0 <= k < {width}'
        else:
            result = f'(S.RD[hc] & ((1 << {width}) - 1)) >> k'
            check = f'assert 0 <= k < {width}'
        return ['S = snapshot(state)', f'k = {amount}', check, f'R = {result} & ((1 << {width}) - 1)',
                f'D.RD[hb] = {"sext" if signed else "zext"}(R, {width})',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if base in ('div', 'rem', 'add', 'sub', 'mul', 'cmp'):
        suffix = mn.split('.')[1]
        width = {'b': 8, 'w': 16, 't': 32, 'o': 64}[suffix[-1]]
        signed = suffix.startswith('s')
        cast = 'sint' if signed else 'uint'
        lines = ['S = snapshot(state)', f'A = {cast}(S.RD[hc] & ((1 << {width}) - 1), {width})',
                 f'B = {cast}(S.RD[hd] & ((1 << {width}) - 1), {width})']
        if base == 'cmp': lines += ['R = -1 if A < B else (0 if A == B else 1)']
        elif base in ('add', 'sub', 'mul'): lines += [f'R = (A { {"add":"+", "sub":"-", "mul":"*"}[base] } B) & ((1 << {width}) - 1)']
        else:
            if base == 'div':
                zero = f'((1 << {width}) - 1) if not {signed} else -1'
                result = 'Q'
            else:
                zero = 'A'
                result = 'T'
            lines += [f'Q = trunc0(A / B) if B != 0 else {zero}',
                      f'Q = -((1 << ({width} - 1))) if ({signed} and A == -(1 << ({width} - 1)) and B == -1) else Q',
                      'T = A - Q * B', f'R = {result}']
        lines += [f'D.RD[hb] = {"sext" if signed else "zext"}(R & ((1 << %d) - 1), %d)' % (width, width),
                  'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
        return lines
    if base == 'cs':
        kind = mn.split('.')[1]
        cond = {'n':'(S.RD[ha] >> 63) == 1', 'z':'S.RD[ha] == 0', 'p':'(S.RD[ha] >> 63) == 0 and S.RD[ha] != 0',
                'eq':'S.RD[ha] == S.RD[hb]', 'ne':'S.RD[ha] != S.RD[hb]'}[kind]
        if kind in ('eq', 'ne'):
            target = 'RD[hc]'; yes = 'S.RD[hd]'; no = 'S.RD[hc]'
        else:
            target = 'RD[hb]'; yes = 'S.RD[hc]'; no = 'S.RD[hd]'
        return ['S = snapshot(state)', f'D.{target} = {yes} if ({cond}) else {no}',
                'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)', 'commit(D)']
    if base == 'br':
        kind = mn.split('.')[1]
        if kind in ('eq', 'ne'): cond = f'S.RD[ha] {"==" if kind == "eq" else "!="} S.RD[hb]'; imm = 'imms12'
        else:
            source = 'S.RB[ha]' if iid.endswith('_rb') else 'S.RD[ha]'
            cond = {'n':f'{source} >> 63 == 1', 'nn':f'{source} >> 63 == 0', 'z':f'{source} == 0',
                    'nz':f'{source} != 0', 'p':f'({source} >> 63 == 0) and ({source} != 0)',
                    'np':f'({source} >> 63 == 1) or ({source} == 0)'}[kind]
            imm = 'imms18'
        return ['S = snapshot(state)', f'taken = bool({cond})',
                f'target = (S.RB[0] + (sext({imm}, {12 if imm == "imms12" else 18}) << 2)) & ((1 << 64) - 1)',
                'D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))',
                'D.pc = D.RB[0] & ((1 << 48) - 1)', 'commit(D)']
    if base in ('jump', 'call'):
        target = '(S.RB[0] + (sext(imms24, 24) << 2))' if fmt == 'iiii' else '(S.RB[ha] + S.RD[hb] + (sext(imms12, 12) << 2))'
        lines = ['S = snapshot(state)', f'target = ({target}) & ((1 << 64) - 1)']
        if base == 'call': lines += ['return_pc = (S.RB[0] + 4) & ((1 << 48) - 1)', '(D, ok) = ras_push(S, return_pc)', 'assert ok']
        lines += ['D.RB[0] = target', 'D.pc = target & ((1 << 48) - 1)', 'commit(D)']
        return lines
    if base == 'ret':
        return ['S = snapshot(state)', 'assert not (rdha == 0 and imms18 != 0)',
                '(return_pc, D.RAS, D.mem, ok) = ras_pop(S)', 'assert ok',
                'D.RD[ha] = sext(imms18, 18) & ((1 << 64) - 1) if ha != 0 else S.RD[0]',
                'D.RB[0] = return_pc & ((1 << 48) - 1)', 'D.pc = D.RB[0]', 'commit(D)']
    if mn == 'swym':
        return ['S = snapshot(state)', 'D = S', 'D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)',
                'D.pc = D.RB[0] & ((1 << 48) - 1)', 'commit(D)']
    raise ValueError(f'no pseudocode for {iid}')


HEADER='''# M1 与 FP 指令逐条 golden 判定说明

本文件为每个标量**指令身份**单列一节，描述“给定执行前状态，应得到什么结果”。同名指令的不同格式、位宽、寄存器组均分开说明。本文是当前规范的可读投影，不是新增ISA规范；若与规范正文冲突，应报告并裁定，不能以本文覆盖规范。

**使用范围**：原有整数、RD/RB/RA访存与传送、地址运算、控制流、swym，以及合约中 66 条 RF/浮点指令。后来新增的特权指令、原子指令和 fence 仍未实现。浮点转整数的 NX、`rootn(-0,2)`及部分 remainder/scaleB 边界仍待规范裁定；不能据此声称完整符合所有输入。

**阅读顺序**：先读共同规则，再按目录查指令。每条包含独立的操作数解释、编码字段、计算步骤、异常/边界、例子和依据。例子仅用于解释，不代表穷尽测试。

**维护方式**：语义文字在 `generate_instruction_guide.py` 中按规范编写，编码身份/位域来自 `contracts/opcodes.yaml`；生成器不导入解释器，不从LLVM/QEMU计算期望。运行 `python3 -B ./components/golden/generate_instruction_guide.py` 更新，`--check` 检查产物一致；一致不等于语义证明。

## 共同规则

这一节解释后文反复使用的概念。阅读某条指令时，应将这里的共同约定与该条指令的具体规则一起使用。例如，条目中写“结果写入目的寄存器”，默认还包括本节说明的旧值读取、PC推进和异常时不提交修改等要求。

这里需要区分三种信息：**架构规范规定的行为**、**golden为了运行测试采用的模型约定**，以及**当前模型尚不能给出答案的情况**。下面会分别说明，避免把模型的简化当成硬件必须遵守的规则。

### 1. golden的一步执行，输入和输出分别是什么

本模型一次执行一条32位机器指令。输入除了指令字，还包括执行前的寄存器值、内存内容和当前指令地址。golden根据这些输入计算本条指令的效果，返回执行后的状态，或者返回本条指令触发的架构异常。

例如，执行一条加法时，需要知道两个源寄存器的旧值；执行一次加载时，还需要知道基址寄存器、偏移量和相应内存位置的内容。因此，只给出“执行add”不足以确定正确答案，必须同时明确操作数和执行前状态。

模型中的 `run()` 不会自动从内存取下一条指令。需要连续执行时，由调用者提供下一条机器指令，并把上一步返回的状态作为新的输入。执行成功后，返回状态中的PC已经指向下一条指令；执行失败时，本条指令的修改不会提交。

后文中的算例只列出与解释有关的输入。正式编写测试时，还应给出需要检查的结果；没有写进断言的寄存器或内存，不能视为已经验证。

### 2. 如何读寄存器名和操作数字段

DADAO有RD、RB、RA、RF四组寄存器，每组64个，每个寄存器64位。RD主要用于整数数据，RB用于基址和地址运算，RA用于返回地址栈，RF用于浮点。本次golden执行前三组相关的标量指令与 RF 浮点指令；浮点有限值由独立整数/有理数 oracle 计算，不使用宿主浮点结果。

`rd1` 是一个具体寄存器名，而 `rdha` 是指令格式中的占位名称，表示“由ha字段指定的RD寄存器”。例如，ha字段的值为3时，`RD[ha]` 就是 `rd3`。`RB[hb]`、`RA[hc]` 等写法也按这个方法理解。

本文计算式右侧出现的寄存器值，除非明确说明为中间结果，均指**本条指令执行前的值**。这样才能正确处理源和目的使用同一寄存器的情况。例如，一条运算同时读取并写入rd3，计算时使用的是旧rd3，不能先写入结果再把新值当作源。双目的运算也必须先取得两个源值，再写高、低两个结果。

多寄存器加载同样需要保存原始地址。例如，加载范围恰好覆盖了用作索引的RD寄存器，后续元素仍按最初的基址和索引计算地址，不能因前一次加载改写了索引而改变地址。

### 3. 零号寄存器不能一概视为普通寄存器

`rd0` 固定读出0。它可以作为整数运算和存数的源，但通常不能作为目的：这种非法目的应触发ILLI，不能只把写入丢掉就算执行成功。当前范围中的两个例外是：双目的加减乘允许其中一个目的为rd0，用于丢弃对应半结果；`ret rd0, 0` 允许只返回、不设置返回值。双目的同时为rd0，或者 `ret rd0, 非零立即数`，仍然非法。

`rb0` 保存当前控制流值。指令读取它时，得到的是**本条指令执行前**的值，而不是自动加4后的值。它可以作为基址或存数源，但不能作为普通指令的显式目的；成功执行后对rb0的推进或跳转更新，由控制流规则完成。

`ra0` 与rd0不同，它不是常数零，而是可读写的返回栈管理寄存器。对它的写入要遵守后文的字段限制。RF组的rf0是FCSR，其读写规则及其余浮点寄存器语义见浮点逐条说明。

因此，判断0号操作数是否合法时，必须同时看**寄存器组、源/目的角色和具体指令**。尤其要注意：从rd0存数表示存入0，从rb0存数表示存入当前rb0值，两者在现行规范下都是合法的。

### 4. 位宽、有符号数和结果写回

寄存器虽然都是64位，一条指令实际参与运算的数据却可能只有8、16、32或64位。后缀b、w、t、o分别表示这四种宽度。本文用W表示当前运算宽度。

`x mod 2^W` 表示只保留x的低W位。例如，在8位范围内，`0x1234` 只保留为 `0x34`；255加1后保留低8位，结果是0。这种截断是定宽运算的一部分，不自动等于触发溢出异常。

同一串位如何解释，取决于指令的有符号或无符号属性。例如，8位的 `0xFF` 按无符号数解释是255，按有符号补码解释是−1。有符号运算应以**当前运算宽度的最高位**判断符号，不能直接拿原64位寄存器的bit63代替8位运算的bit7。

将窄结果写回64位寄存器时，主要有两种扩展方式：

| 写回方式 | 做法 | 8位结果0x80写回64位的例子 |
| --- | --- | --- |
| 零扩展 | 结果放在低位，新增高位全部填0 | `0x0000000000000080` |
| 符号扩展 | 结果放在低位，新增高位复制窄结果的符号位 | `0xFFFFFFFFFFFFFF80` |

当前定宽算术、比较和移位按各自后缀扩展，**写满目的寄存器的64位**。目的寄存器旧高位不会被保留。与此不同，`or.w`、`andn.w` 这类16位段操作只改指定段，其他段保留旧值；应以每条指令的写回说明为准。

比较产生−1、0或1后，也要应用相应的扩展规则。例如，8位无符号比较中“小于”的结果是 `0x00000000000000FF`；8位有符号比较中“小于”的结果是 `0xFFFFFFFFFFFFFFFF`。不要把两者都写成同一个64位−1。

有符号除法采用向零截断：−7除以3的商为−2，余数为−1。计算golden时不能直接用Python对负数的向下取整除法替代。除零和最小负数除以−1在现行整数规范中有明确的定值结果，详见各条除余指令；它们不再一律触发ILLI。

本架构不通过一个额外的整数条件码寄存器保存这类运算结果。后续分支通常读取数据寄存器的值来判断条件。

### 5. PC、rb0和下一条指令地址的关系

需要同时保留两个概念：**参与地址计算的完整64位控制流值**，以及**实际用于取指的低48位地址**。模型用 `rb0` 保存前者，用 `pc` 保存后者。两者的低48位应当一致。

对于成功执行的普通指令，完整控制流值按64位加4；对于分支、jump、call和ret，则按相应条目计算新值。新的完整值写入rb0，再取其低48位作为下一条取指地址。模型返回成功状态时，`pc` 和 `pc_next` 都表示这个下一取指地址；`pc_next` 是模型接口字段，不是额外的硬件寄存器。

例如，当前rb0为 `0x0000FFFFFFFFFFFC`，顺序执行一条指令后，rb0变为 `0x0001000000000000`，而下一取指地址为0。这个例子说明：不能先把rb0截成48位并丢弃进位，再声称完整控制流值已经正确更新。

相对跳转的基准是当前rb0。例如，当前地址为0x1000，分支立即数为2且条件成立时，目标为 `0x1000 + 2×4 = 0x1008`，不是0x100C。偏移立即数的单位是指令字，即4字节；访存指令的字节偏移则不能套用这个乘4规则。

如果jump产生了一个低两位非0的目标，本条jump先完成；下一次尝试从该地址取指时才报告IALIGN。不要把下一次取指的异常提前当成本条jump自身的失败。

默认测试入口 `0xFC0000000000` 来自当前向量约定。它不是本模型对芯片硬件复位地址的规定，调用者可以提供其他起始地址。

### 6. 内存中的字节顺序和地址范围

内存按字节寻址，数据采用大端顺序，即一个多字节数的高字节放在较低地址。例如，把32位值 `0x12345678` 存到0x1000后，0x1000、0x1001、0x1002、0x1003四个地址依次存放12、34、56、78这四个十六进制字节。

实际访存使用计算结果的低48位。RB中的高16位在普通寄存器运算中仍然有效，不能因为它以后可能被用作地址，就在此前的算术、比较或传送中一律清掉。

2、4、8字节访问分别要求地址是2、4、8的整数倍，否则触发MALIGN；1字节访问没有额外对齐要求。一次多寄存器访存还要检查整个寄存器区间是否合法，并按元素宽度依次计算地址。

测试向量中的内存预置值也要结合访问宽度理解。例如，byte访问的预置项 `value=0x1234` 按宽度写入低1字节，因此该地址得到的是0x34，不是把一个64位数写入后再从第一个字节读取。具体预置格式由向量schema规定，不能用它替代指令本身的访存语义。

当前golden用稀疏字节表表示内存，没有预置的字节读作0。**这是为了让单步测试可运行而采用的模型约定，不是硬件保证所有未初始化内存都为0。** 模型不模拟地址映射、访问权限、MMU、ROM或设备，因此不能用它判断UNMAPPED、CFXMEM等机器层异常是否正确。

### 7. 译码成功、执行成功和模型有能力判断，是三件事

译码先回答“这个32位字属于哪条指令”。本文件每条提供的mask/value表示匹配条件：`(word & mask) == value`。字段表随后说明，剩余位如何组成寄存器编号和立即数。

匹配到某个身份，不代表操作数一定合法。例如，一个字可以成功译码为加法，但其目的寄存器组合可能被规范禁止。因此，译码之后仍需做合法性检查。反过来，一个已删除指令的旧机器字如果被当前编码表重新分配，应按当前身份解释；只有当前表未定义的编码才按保留编码处理。

本模型区分以下结果：

| 结果 | 含义 | 测试中应如何理解 |
| --- | --- | --- |
| 执行成功 | 指令属于本模型范围，输入可判定，并完成了规定效果 | 继续比较寄存器、内存和PC断言 |
| ILLI、UNDI、IALIGN、MALIGN、RASOF、RASUF | 本模型覆盖的架构异常 | 核对异常类型，并检查执行前状态未被破坏 |
| `Unsupported` | 编码有定义，但本模型尚未实现，例如原子、fence 或特权指令 | 不能当成该指令在完整机器上必然非法 |
| `SpecificationGap` | 当前规范的文字不足以唯一确定结果 | 需要裁定，不能选一个实现的输出当标准 |
| `ValueError`等输入错误 | 调用参数或测试数据格式无效，例如指令字超过32位 | 先修正测试输入，不能作为ISA异常来验收 |

`sub.uo` 的借位高半已由 `ADR-0049` 裁定为 0/1（`rdHC < rdHD` 时 1，否则 0），不再报 `SpecificationGap`；详见下文“规范口径与验证边界”§1。

### 8. 异常发生时，为什么必须保留执行前状态

“精确异常”在本模型中的要求是：如果本条指令失败，就像它尚未提交任何架构修改一样。目的寄存器不能只写了一半，内存不能只存入前几个元素，call/ret也不能先改栈再报错；PC应仍停在失败的这条指令，而不是正常推进到下一条。

例如，一条ret在读取返回栈时发现无有效返回地址，应报告RASUF。此时既不能修改返回值寄存器，也不能推进MRPTR或改变RACNT。只检查“报了RASUF”而不检查这些状态，仍可能漏掉实现错误。

解释器在状态副本上执行，成功后才返回新状态；发生架构异常则返回执行前状态。这是实现精确异常的一种软件办法，不要求真实硬件也必须复制整份状态。验证器检查的是最终可见行为，而不是硬件内部采用什么实现方法。

当前模型不执行异常处理程序，也不模拟特权异常入口。文档中的“异常后状态不变”，指失败指令自身没有提交副作用，不应被理解为完整系统的异常处理过程永远不会修改任何状态。

### 9. 返回地址栈中究竟保存了什么

call需要记住“函数返回后从哪里继续执行”，ret随后按后入先出的顺序取回这个地址。DADAO为此设置了返回地址栈RAS，其中一部分放在寄存器中，称为RegRAS；寄存器容纳不下时，可使用内存中的MemRAS。

RegRAS使用ra1到ra63，共63个槽位，ra63始终表示栈顶。每个有效条目的低48位是返回地址，高16位是递归计数。计数表示这个条目合并保存了多少次相同返回地址；它与有效槽位数不是同一个概念。

ra0用于管理栈，其字段如下：

| 字段 | 位置 | 含义 |
| --- | --- | --- |
| MRPTR | bits[47:0] | MemRAS中下一个待弹出条目的地址；0表示未启用MemRAS |
| RACNT | bits[53:48] | RegRAS当前有效条目数，范围0–63 |
| SBZ | bits[63:54] | 保留为零，写入这些位无效 |

判断栈内哪些寄存器有效，必须看RACNT。例如RACNT=2时，只有ra63和ra62属于有效栈，ra61即使残留一个非零数也不算条目。无效槽位的内容不能用来推断栈深，也不应成为规范测试的固定期望值。

递归计数的作用可以用一个例子理解：第一次压入返回地址0x1004时，栈顶记录为“计数1、地址0x1004”。如果再次压入的仍是0x1004，而且计数尚未饱和，可以直接把计数改为2，不必再占用一个寄存器槽位。之后两次ret分别将计数减1和真正移除该条目。

下面两个流程是所有call/ret条目共同定义的一部分。表述中的“移动条目”描述的是软件可见的RA寄存器状态；硬件可以采用其他内部结构实现相同效果。

### 共同规则：call压栈

call先根据执行前的rb0计算返回地址：`(旧rb0 + 4) mod 2^48`。要压入的是**调用指令之后的地址**，而不是函数入口地址。函数入口由call自身的跳转操作数另行计算。

随后依次判断以下情况，前面的情况满足后就不再继续选择后面的分支：

1. **寄存器返回栈为空。** 当RACNT=0时，在ra63放入新返回地址，递归计数设为1，RACNT改为1。旧ra63中即使有残留数据，也不能把它当作有效旧栈顶。
2. **可以合并同一个返回地址。** 当RACNT>0、新返回地址与栈顶地址相同，而且栈顶计数小于65535时，只把计数加1，RACNT不变。这一步优先于满栈处理，因此RACNT已经是63也仍可能成功call，不需要访问MemRAS。
3. **需要新条目，而且寄存器栈还有空位。** 如果不能合并，但RACNT<63，就把现有有效条目向较低编号移动一个位置，新条目放ra63，计数为1，RACNT加1。例如原来只有ra63有效，插入后原栈顶移到ra62。即使返回地址相同，只要递归计数已经饱和，也需要走这个分支或下一分支。
4. **需要新条目，但寄存器栈已满。** 此时RACNT=63。若MRPTR=0，表示没有可用的MemRAS，报告RASOF，原状态不变。否则，计算待写地址 `(MRPTR−8) mod 2^48`，检查8字节对齐，将最旧的条目ra1写入该地址，并把MRPTR更新到这里；原ra2至ra63向较低编号移一格，再把新条目放到ra63。这样移出一个、加入一个，RACNT仍为63。

例如，满栈时MRPTR原为0x2000，需要溢出的条目会写到0x1FF8，新的MRPTR也是0x1FF8。这里的“指针减8”来自一个返回栈条目占8字节，不是调用指令的长度。

MemRAS是否有足够的已分配空间由系统管理；本模型不检查OS分配边界。它会检查本次访问是否对齐，并保证失败时RA、内存和PC都保持原状。只有压栈成功，call的跳转结果才一并提交。

### 共同规则：ret弹栈

ret先检查自己的显式操作数是否合法，例如 `ret rd0, 非零立即数` 必须报ILLI。通过后，再从RAS取得返回地址。不能总是假定返回地址直接来自ra63，因为寄存器栈为空时可能需要读取MemRAS。

**当RACNT>0时，栈顶在ra63：**

1. 栈顶递归计数为0，说明有效条目无法提供一次合法返回，报告RASUF，状态不变。
2. 栈顶递归计数大于1，取它的低48位作为返回地址，只把计数减1。这个条目还要供后续ret使用，因此RACNT不变。
3. 栈顶递归计数等于1，取出返回地址并移除这个条目。下层有效条目向较高编号移动一个位置，新的栈顶仍在ra63，RACNT减1。退出有效区的槽位以后不再参与栈语义，不要求它具有某个固定值。

**当RACNT=0时，需要检查MemRAS：**

1. MRPTR=0，表示寄存器栈为空且未启用MemRAS，报告RASUF。即使某个RA槽位还残留非零值，也不能据此返回。
2. MRPTR非0，先检查8字节对齐，再读取该地址的一个8字节条目。此时先不要修改指针，要先检查条目计数。
3. 读出的计数为0，报告RASUF，MRPTR和所有其他状态均不变。
4. 读出的计数为1，使用条目的低48位作为返回地址；该条目本次就消耗完，MRPTR按48位加8，RACNT仍为0。
5. 读出的计数大于1，本次返回消耗其中一次。把“计数减1、地址不变”的剩余记录放到ra63，RACNT设为1，同时MRPTR按48位加8。后续ret就可以从寄存器栈继续返回。

例如，RACNT=0、MRPTR=0x2000，内存条目保存“计数3、地址0x1004”。一次ret之后，下一取指地址是0x1004，ra63保留“计数2、地址0x1004”，RACNT变为1，MRPTR变为0x2008。

弹栈成功后，ret还会按照自身的立即数设置返回值寄存器，并将取得的48位返回地址零扩展写入rb0。若任一检查失败，这些写回都不能发生。返回目标是否4字节对齐，则在下一次取指时检查。

### 10. 伪代码中使用的函数、常量与记号

本节把后文伪代码用到的所有函数和记号先集中声明，避免出现没有解释的名字。伪代码采用 Python 风格语法：`for`、`in`、`if/else`、`range()`、`all()`、`bool()`、`and/or/not` 只表示控制流，不是架构函数；`True/False` 是布尔常量。其余函数都是本文定义的抽象操作，**不是 Python 标准库**，实际实现位置见表。各条中的局部变量（`A`、`B`、`R`、`tmp`、`val`、`flg` 等）由该指令节当场赋值。

#### 10.1 状态、异常与位模式约定

- `state`：调用者传入的完整架构状态。`S = snapshot(state)` 是执行前快照；`S.RD[i]`、`S.RB[i]`、`S.RA[i]`、`S.RF[i]` 是四组寄存器第 i 项，`S.mem` 是稀疏大端内存，`S.pc` 是当前指令地址，`S.RAS` 是返回地址栈。
- `D`：暂定的执行后状态。伪代码先写 `D`，只有末尾 `commit(D)` 才整体生效；任何 `assert` 失败、架构异常或 `SPECIFICATION-GAP` 都不会提交 `D`，返回执行前状态。
- `assert 条件`：条件不成立时，按该条“合法性、异常与边界”报 ILLI（或文中明确的其他异常/`SPECIFICATION-GAP`），并丢弃 `D`。这里的 `assert` 是“检查失败即架构异常”的简写，不是宿主 Python 的断言。
- `EA`：访存有效地址；`EA[i]` 是多寄存器/块访问第 i 个元素的地址。
- `mod 2^64`、`& ((1 << 64) - 1)`：保留低 64 位；`(1 << n) - 1` 是低 n 位全 1 掩码。`X[a:b]` 是左闭右开区间。
- `NV`/`DZ`/`OF`/`UF`/`NX`：FCSR 累积标志，数值 1/2/4/8/16，用按位或合并。`RNE`/`RTZ`/`RDN`/`RUP`：`rf0[33:32]` 的四种舍入方向。
- `FCSR_WRITE_MASK`：写 `rf0` 时允许修改的位 `[33:32]` 与 `[4:0]`，其余位保持。
- `SPECIFICATION-GAP`：规范未给唯一答案，模型拒绝输出；它不是 ISA 异常，也不计作执行通过。
- `positive_qnan` / `positive_snan`：当前格式下符号位为 0 的规范 quiet/signaling NaN 位模式；`ft*` 为 binary32，`fo*` 为 binary64。

#### 10.2 通用与整数函数

| 伪代码写法 | 输入 → 输出 | 含义 | 实际实现 |
| --- | --- | --- | --- |
| `snapshot(state)` | state → S | 深拷贝执行前状态，后续只读 | `dadao_interp_v5.run` 中的复制 |
| `commit(D)` | D → 新状态 | 全部检查通过后一次性提交，返回 D | `run` 末尾替换工作状态 |
| `sext(value, bits)` | 整数、位宽 → 有符号整数 | 取低 `bits` 位按补码解释 | `_sext` |
| `sint(value, width)` | 整数、位宽 → 有符号整数 | 同上；用于完整寄存器/内存值的低 `width` 位 | `_sext` |
| `uint(value, width)` | 整数、位宽 → 无符号整数 | 取低 `width` 位按无符号解释 | 掩码 `& ((1 << width) - 1)` |
| `zext(value, bits)` | 整数、位宽 → 整数 | 取低 `bits` 位并零扩展到 64 位 | 掩码后写回 |
| `trunc0(ratio)` | 有理数 → 整数 | 向零截断（丢弃小数部分） | `div`/`rem` 的整数商实现 |
| `overlap([a,b), [c,d))` | 两个半开区间 → 布尔 | 两个寄存器区间是否有交集；空区间不算 | `_check_blockcopy` 的区间判断 |
| `or_flags(flg)` | 标志列表 → 整数 | 把所有标志按位或合并 | `_fp_flags` 的累积方式 |
| `be_load(mem, addr, size)` | 内存、地址、字节数 → 无符号整数 | 从 `addr` 读 `size` 字节，大端拼成整数；未预置字节按 0（测试模型约定） | `State.load_mem` |
| `be_bytes(value, size)` | 整数、字节数 → 字节列表 | 把低 `size×8` 位按大端拆成 `size` 个字节 | `int.to_bytes(size, "big")` |
| `ras_push(S, addr)` | 快照、返回地址 → (D, ok) | 按共同规则压栈并更新复制的 RAS/内存；`ok=False` 表示 RASOF/MALIGN | `_ras_push` |
| `ras_pop(S)` | 快照 → (return_pc, D.RAS, D.mem, ok) | 按共同规则弹栈；`ok=False` 表示 RASUF/MALIGN | `_ras_pop` |

#### 10.3 浮点编解码与转换函数

| 伪代码写法 | 输入 → 输出 | 含义 | 实际实现 |
| --- | --- | --- | --- |
| `decode_fp(bits, format=...)` | 位模式 → (sign, kind, value, payload) | 解码符号位、类别（finite/zero/inf/nan）、精确有理数值、NaN payload | `fp_ref.decode` |
| `encode_fp(decoded, format=...)` | 解码值 → 位模式 | 把运算结果按格式编码；NaN 使用规范 quiet 位型 | `fp_ref.encode_fraction` 与特殊值路径 |
| `classify_fp(bits)` | 位模式 → 整数 | 返回 10 位分类掩码，伪代码再 `& 0x3ff` | `fp_ref.classify` |
| `convert_fp(bits, src, dst, rounding)` | 位模式、源/目标格式、舍入 → (bits, flags) | 浮点格式转换 | `fp_ref.convert_float` |
| `fp_to_int(bits, signed, width, rounding, saturate=True)` | 位模式、符号、宽度、舍入 → (整数, flags) | 浮点转整数；NaN/Inf/越界饱和并置 NV | `fp_ref.convert_to_int` |
| `int_to_fp(value, signed, width, dst, rounding)` | 整数、符号、宽度、目标格式、舍入 → (bits, flags) | 整数转浮点 | `fp_ref.convert_int` |
| `is_nan(X)` | 解码值 → 布尔 | 是否为 NaN | `fp_ref.decode(...)[1] == "nan"` |
| `has_signaling_nan(A, B)` | 两个解码值 → 布尔 | 任一为 signaling NaN；quiet NaN 返回假 | payload 的 quiet 位判断 |
| `is_negative_zero(X)` | 解码值 → 布尔 | 是否为 `−0` | 符号位与数值判断 |
| `sign(X)` | 解码值 → 0/1 | 符号位 | 解码结果第 0 项 |
| `positive_qnan` / `positive_snan` | 常量 | 符号位 0 的规范 quiet/signaling NaN 位模式 | `Format.canonical_qnan/snan` |

#### 10.4 浮点运算函数

| 伪代码写法 | 输入 → 输出 | 含义 | 实际实现 |
| --- | --- | --- | --- |
| `fp_add(A,B,rounding=...)` | 两个解码值、舍入 → (bits, flags) | 加法 | `fp_ref.arithmetic("add", ...)` |
| `fp_sub(...)` | 同上 | 减法 | `arithmetic("sub", ...)` |
| `fp_mul(...)` | 同上 | 乘法 | `arithmetic("mul", ...)` |
| `fp_div(...)` | 同上 | 除法 | `arithmetic("div", ...)` |
| `fp_remainder(...)` | 同上 | IEEE 754 remainder（平局取偶） | `arithmetic("rem", ...)` |
| `fp_scaleB(...)` | 同上 | scaleB 指数缩放 | `arithmetic("scalb", ...)` |
| `fp_sqrt(X, rounding=...)` | 解码值、舍入 → (bits, flags) | 平方根；`rootn(-0,2)` 报 `SPECIFICATION-GAP` | `fp_ref.sqrt` |
| `fp_minimumNumber(A,B)` / `fp_maximumNumber(A,B)` | 两个解码值 → (bits, flags) | IEEE 754-2019 §9.6 严格版最小/最大值 | `fp_ref.minmax("min"/"max", ...)` |
| `round_to_integral(A, selector, rounding)` | 解码值、one-hot selector、舍入 → (bits, flags) | 六档取整；仅 selector=0x20 读取舍入并可置 NX | `fp_ref.round_to_integral` |
| `fp_fusedMultiplyAdd(A,B,C,rounding)` | 三个解码值、舍入 → (bits, flags) | 精确积加加数后单次舍入 | `fp_ref.fma` |

返回 `(bits, flags)` 或 `(value, flags)` 的函数，`flags` 只含本条产生的 NV/DZ/OF/UF/NX，调用方再累积到 `rf0[4:0]`。`fp_to_int` 的精度损失是否置 NX 仍是开放点（见 §16）；模型对未裁定的输入报 `SPECIFICATION-GAP`，不自行补答案。

共同规则的规范依据：[ISA合约](../../.tao/contracts/contract-isa.md) §1–3、§6、§8、§10–15；[浮点合约](../../.tao/contracts/contract-fp.md)；[SimRISC-00](../../spec/SimRISC-00-指令系统设计.md)。测试输入与内存预置约定见 [向量schema](../../tests/vectors/schema.md)。模型接口和范围限制见 [设计说明](DESIGN.md)。

## 指令目录

'''


def generate():
    records=yaml.safe_load((ROOT/'contracts/opcodes.yaml').read_text())
    selected=[r for r in records if scalar(r)]
    omitted=[r for r in records if not scalar(r)]
    scalar_count = sum(1 for r in selected if r['scope'] != 'fp')
    fp_count = sum(1 for r in selected if r['scope'] == 'fp')
    content=HEADER+f'本次编码表现场统计：详细条目 **{len(selected)}** 个（scalar={scalar_count}，fp={fp_count}）；范围外身份 **{len(omitted)}** 个。下表按规范编码表顺序排列。\n\n| 序号 | 指令身份（点击查看） | 类别 |\n| --- | --- | --- |\n'
    sections=[]
    for i,r in enumerate(selected,1):
        if r['scope'] == 'fp':
            category = '浮点/FCSR'
            family = FP_FAMILY[r['id']]
            meaning = f"按浮点合约执行 `{r['mnemonic']}`，格式和寄存器字段以编码表为准。"
            operands = '源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。'
            faults = '目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。'
            example = '例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。'
            if family == 'roundint':
                meaning = '按 one-hot selector 指定的方向把浮点值取整，结果仍为同格式浮点。'
                operands = '`rfhb` 是目的，`rfhc` 是源，`immu6` 是 one-hot 取整 selector（0x01…0x20），不是寄存器个数。'
                faults = '目的rf0、`immu6` 非 one-hot（含0x00）均为ILLI；仅 0x20 读取 rf0 方向且仅当结果≠输入时置 NX。'
                example = '源 1.5：0x01/0x02/0x08 得 2.0，0x04/0x10 得 1.0；0x20 按 rf0 方向并可置 NX；trunc(−0.5) 得 −0。'
            elif family == 'minmax':
                meaning = '按 IEEE 754-2019 minimumNumber/maximumNumber 选取较小/较大值。'
                operands = '`rfhb` 是目的，`rfhc`/`rfhd` 是两个同格式源；先读后写，源与目的可重叠。'
                faults = '目的rf0为ILLI；单 NaN 返回那个数、双 NaN 返回 canonical qNaN、sNaN 置 NV；±0 按 −0<+0 比较。'
                example = 'min(+0,−0)=−0、max(+0,−0)=+0；min(1.0,qNaN)=1.0；双 NaN 返回规范 qNaN。'
            elif family == 'fma':
                meaning = '计算 rfHB×rfHC+rfHD，精确积与加数求和后只舍入一次。'
                operands = '`rfha` 是目的，`rfhb`/`rfhc` 是乘数，`rfhd` 是加数；三个源先读后写，均可与目的重叠。'
                faults = '目的rf0为ILLI；0×Inf、Inf 与异号 Inf 相加置 NV 并返回 qNaN；OF/UF/NX 按单次舍入累积。'
                example = '(1+2⁻²³)×(1−2⁻²³)−1 得 −2⁻⁴⁶（0xA8800000）；先 ftmul 再 ftadd 会把积舍入成 +0。'
            steps = pseudocode(r)
            cite = f"contract-fp §{FP_ANCHOR[family]} ({family})" 
        else:
            category,meaning,operands,steps,faults,example,cite=body(r)
        content+=f'| {i} | [{r["id"]}](#insn-{i:03d}) | {category} |\n'
        fields=', '.join(f['name'] for f in r['fields'])
        if r['format']=='rrrr' and r['mnemonic'].split('.')[0] in ('add','sub','mul'):
            fields='{rdha, rdhb}, rdhc, rdhd'
        section=f'\n<a id="insn-{i:03d}"></a>\n\n## {i}. `{r["id"]}`\n\n**用途**：{meaning}\n\n**操作数形式**：`{r["mnemonic"]} {fields}`（{r["format"]}；表内scope={r["scope"]}）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。\n\n**输入与目的**：{operands}\n\n**编码**：mask=`{r["mask"]}`，value=`{r["value"]}`。\n\n| 字段 | 指令字位域 | 含义 |\n| --- | --- | --- |\n'
        for f in r['fields']:
            role='有符号立即数' if f.get('signed') else '无符号立即数' if f.get('role')=='imm' else f.get('bank','')+'字段'
            if f['name']=='wpN':role='16位段编号0…3'
            section+=f'| `{f["name"]}` | `{f["bits"]}` | {role} |\n'
        section+='\n**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：\n\n```text\n'+''.join(f'{s}\n' for s in pseudocode(r))+"```\n\n**标准计算与写回**：\n\n"+''.join(f'{j}. {s}\n' for j,s in enumerate(steps,1))
        refs = f'{spec_link(r["spec_cite"])}；[指令合约](../../.tao/contracts/contract-isa.md)'
        if r['scope'] == 'fp':
            refs += f'；[浮点合约](../../.tao/contracts/contract-fp.md) {cite}'
        else:
            refs += f' {cite}'
        section+=f'\n**合法性、异常与边界**：{faults}\n\n**算例**：{example} 算例中未特别指定的目的均选择合法非零寄存器。\n\n**依据**：{refs}。\n'
        sections.append(section)
    content+=''.join(sections)
    content+='\n## 范围外指令身份清单\n\n以下身份有定义，但本次没有为它们建立执行golden；调用当前解释器应得到 `Unsupported`。这不是它们在完整DADAO机器上的语义，也不将“机器暂定decode ILLI”混同为模型已经实现。\n\n| 指令身份 | scope | 本次状态 |\n| --- | --- | --- |\n'
    for r in omitted:content+=f'| `{r["id"]}` | {r["scope"]} | 暂不支持 |\n'
    content+='''
## 规范口径与验证边界

这一节说明当前golden在哪些地方可以提供参考答案，哪些地方仍然需要规范裁定、数据修正或额外验证。阅读前面的逐条说明时，也必须保留这些限制：**一条指令有了详细文字定义，不等于它的所有输入已经验证，更不等于完整DADAO系统已经通过验收。**

这里把问题分开记录，是因为它们的解决方式不同。规范歧义需要先确定正确行为；旧向量需要按已确定的规范修正；模型范围外的能力需要另行实现；环境缺失则需要补齐工具后重新执行检查。不能把这些情况统一写成“测试暂时没过”，也不能统一改成SKIP来消除失败。

### 1. sub.uo：借位高半已裁定为 0/1

`sub.uo {rdHA, rdHB}, rdHC, rdHD` 的语义已由 `ADR-0049` 冻结：

- `rdHB = (rdHC − rdHD) mod 2^64`
- `rdHA = 1` 当且仅当 `rdHC < rdHD`，否则 `0`
- 不写 128 位结果的全 1 高半；需要 128 位有符号高半时用 `sub.so`

原先 `SimRISC-04` 总述句的“高 64 位”与 `.uo` 变体句的“借位 0/1”冲突，已按变体句修正。QEMU 原本已按借位实现；向量生成器/审计与 golden 已对齐，并新增 `0−1`、`5−7` 借位向量。

### 2. 仓库存数向量已按现行零号源规则同步

合并远端 `origin/master` 后，原先把 `rd0/rb0` 存数源判为 ILLI 的 10 条旧向量已按现行规则更新：从 `rd0` 存入 0、从 `rb0` 存入执行前控制流值均合法。本次全量回放 710 条，FAIL=0、退出码 0，这组分歧不再存在。

若后续重新引入同类旧数据，应依据规范重写预期内存内容、源寄存器保持和 PC 推进等断言；不能把模型改回“零号源非法”，也不能无条件跳过。

### 3. 已有验证证据分别能证明什么

以下是本次实现审查的记录，不是每次生成文档都会重新运行的测试结果。后续代码、规范或向量有变化时，应重新执行对应检查，不能一直引用旧数字作为最新结论。

| 证据 | 本次记录 | 可以支持的结论 | 不能由此推出的结论 |
| --- | --- | --- | --- |
| 模型和验证器直接测试 | 46项测试通过 | 已编写的正常、边界及错误检测用例满足断言 | 所有机器字和操作数组合都正确 |
| 独立算术与移位矩阵 | 3402组算术、360组移位检查 | 所选位宽、符号和边界组合与独立计算一致 | 这些组合已经穷尽全部64位输入 |
| 仓库输入逐条独立重算 | 159条适用算术/比较输入、84条移位/扩展输入 | 本次选定类别中全部适用输入都已重算，而非只抽样 | 其他指令族也完成了相同方式的全量重算 |
| 仓库向量回放 | 710条：171条编码通过、490条执行通过、0条失败、49条跳过；退出码0 | 当前仓库向量与模型一致 | 全量回归已经通过 |
| 反例注入 | 修改计算或断言后失败，恢复后通过 | 检查器至少能检出这些实际注入的错误 | 检查器能检出任何可能的错误 |
| 文档范围和生成一致性检查 | 指令身份、链接及生成内容核对通过 | 文档条目与当前清单对齐，生成结果可复现 | 文档中的每一个语义判断都已被机械证明 |

完整审查记录和限制见 [本次任务书](../../.tao/tasks/golden/GOLDEN-001t-M1模型校正与设计说明.md)。可复现命令见 [README](README.md)。这里的“独立重算”是指期望值依据规范、使用独立计算推导，不从LLVM或QEMU的执行结果取答案。

#### 编码通过不能替代执行通过

`PASS-encoding` 检查机器字是否解码成向量声明的指令，以及静态操作数是否合法。它没有执行运算，因此不能证明乘法结果、加载的数据、返回地址栈变化或分支目标正确。汇报时应把171条编码检查与490条执行检查分开说明，不能把两者合并称为“661条语义全部正确”。

`PASS-execution` 也只证明本条向量实际断言的内容成立。例如，成功用例只检查rd1，就不能据此声称所有其他寄存器均未误改。当前异常用例会额外检查整份状态不变，swym的无副作用用例也有整体状态检查；这不等于每一个成功用例都穷尽了全部副作用。

#### 独立性也有具体边界

模型和测试的语义期望不依赖LLVM/QEMU，但编码身份和字段位置都使用仓库的 `contracts/opcodes.yaml`。如果这张共享编码表自身写错，模型和向量可能同时使用同一个错误编码并彼此一致。要独立证明编码正确，还需要把表中编码与规范正文的QFC/子表逐项核对，不能只依靠模型与向量相互比对。

同样，生成器的 `--check` 只是重新生成文字后比对文件。即使生成器中的某段解释本身有误，只要产物与它相同，一致性检查仍会通过。因此，文字语义还需要对照规范审查；本文件不能成为自己正确性的唯一证据。

### 4. 跳过的用例没有得到执行正确性的证明

本次回放中的49条跳过包括5条已标deferred的用例和44条机器层异常用例。它们没有计入执行通过数，也不能在汇报时视为“没有问题”。本次回放没有 FP 向量；FP 由 `test_fp_v5.py` 的专项测试覆盖，另有逐身份 66 条冒烟检查，整套单测共 46 项。

- **SKIP-deferred**：向量已明确暂缓，通常意味着其期望或验证前提尚未确定。本模型本次没有对它作出通过结论；后续需解决具体暂缓原因，再转为可执行的有效断言。
- **SKIP-machine**：用例期待UNMAPPED、CFXMEM等地址映射或权限结果，而当前单步模型没有这些机器机制。需要在具备相应地址图、权限配置和异常机制的环境中验证。
- **SKIP-scope**：被测指令在本模型实现范围外。当前 710 条 ISA 回放中这个计数为 0；特权、原子和 fence 仍在范围外，只说明本组向量没有相应项目。

即使一批测试的失败数为0，只要仍有跳过项，也应同时给出原因和范围。当前运行器对空输入或全部用例都跳过的情况返回非零，防止“什么都没有验证”被当成成功。

### 5. 当前模型明确不验证的能力

浮点 66 条 RF 指令现在纳入本模型范围；其有限值运算使用独立整数/有理数 oracle，舍入模式和累积标志按浮点合约处理。`rootn(-0,2)`、浮点转整数精度损失的NX，以及 remainder/scaleB的合约开放边界仍报告 `SPECIFICATION-GAP`，不能据此宣称所有输入都已裁定或完整符合 IEEE 754-2019。后来新增的特权指令、trap/escape、原子指令和fence仍在范围外。

内存模型只提供指令所需的字节读写、端序、地址截取和对齐检查，没有完整系统的页表、权限、地址映射、ROM或设备行为。模型中某个地址可以读写，不代表真实机器在该地址也一定可访问；未预置内存读0同样只是测试模型约定。

模型也不提供周期、流水线、缓存一致性或多核并发内存序的答案。`swym` 在架构状态上不改数据，并不表示已经验证其真实等待周期；未实现fence，也不能用顺序执行的单步结果证明屏障语义正确。

返回栈方面，本模型检查RACNT、递归计数、MemRAS指针与对齐等已覆盖行为，但不判断OS实际分配了多少MemRAS空间。有效区以外的RA槽位内容由规范视为未定义，测试也不能把当前Python实现恰好留下的值固化成硬件必须遵守的结果。

### 6. 当前已知不足与 L2 状态

**f2i 尚未收口。** `convert_to_int` 对任何 inexact 输入直接抛 `FPGap`（如 `1.5 → int` 没有答案），但规范只把 NX 列为未定，整数值本身可确定；舍入方向（golden 用 `rf0`，QEMU softfloat 对 f2i 用 toward-zero）以及 NaN/Inf/负无符号的饱和值也没有可机械判的口径，且缺少对应测试。

**FP 没有共享向量。** `tests/vectors` 目前只有标量；66 条 FP 由单测、逐身份冒烟和一次性 oracle 差分覆盖，差分脚本尚未入库。

**golden 未接入 make/CI。** 单测、710 条回放和本文件 `--check` 目前靠手工执行；没有 `check-golden` 目标，回归不会被项目门控自动拦住。`009t-audit.py` 对 `ctrl-br`、`ldm.o`、`shl.*` 仍有既存偏差（与本次 B 方案无关）。

**L2 尚未跑通。** 依赖已安装、组件已拉取并打补丁，LLVM/LLD/QEMU 正在构建；L2 的 `check-lit`、`check-qemu-smoke` 和 FP 探针需要完整工具链。构建完成后运行 `make check-modules JOBS=2` 并保留真实输出；在跑通前不能写“L2 通过”。

### 7. 伪指令、旧指令和范围变化应怎样理解

本文件以**当前编码表里的机器指令身份**为单位。`set.rd`等汇编伪指令可能展开成多条机器指令，因此这里不会再给它们建立一个独立的单步机器语义。验证伪指令时，需要另外检查汇编展开序列及整个序列的效果，不能只查看其中一条机器指令。

旧版本中的rela.si、专门的illi指令等，也不能按旧名字继续套用旧行为。对实际机器字，应先查当前编码表：若当前已分配给另一身份，就按新身份执行；只有未定义的编码才报UNDI。这里“illi指令已删除”也不表示ILLI异常被删除，非法操作数仍可能触发ILLI。

当前仓库的 `scope: m1` 标签还包含后来加入的特权能力，而本次用户确认的是原有标量范围。因此，文档详细条目数、编码表m1数量和完整项目已实现数量不必相同；汇报覆盖范围时应列明采用的是哪一份清单。

### 8. 当前结论与下一步应如何表述

本模型已按当前规范校正确认范围内的整数、访存、寄存器传送、控制流和 66 条 FP，并通过直接测试、独立重算及反例检查；仍保留 f2i 等开放语义、FP 共享向量缺口、golden 未入门控和系统能力边界。

要进一步完成验收，需要分别推进：

1. （已完成）`sub.uo` 借位高半已由 ADR-0049 裁定为 0/1，并同步规范、合约、golden 与向量。
2. （已完成）十条旧存数向量已随远端合并按现行零号源规则更新；回放 710 条、FAIL=0。
3. 裁定 f2i 的舍入/饱和/NX 口径并补向量；把 FP oracle 差分和 `check-golden` 纳入仓库门控。
4. （进行中）项目工具环境已配置，LLVM/LLD/QEMU 构建中；完成后运行 L2 并更新验收记录。

这些后续动作有不同的授权范围。本文把它们列为待办说明，不意味着已经修改共享规范、测试数据、ADR或系统环境；也不以文字补充代替实际执行证据。
'''
    return content


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    content=generate()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text()!=content:
            print('FAIL: instruction reference missing or differs from generator')
            return 1
        print('PASS: instruction reference reproducible (not a semantic proof)')
    else:
        OUTPUT.write_text(content)
        print(f'WROTE {OUTPUT.relative_to(ROOT)} ({len(content.splitlines())} lines)')
    return 0


if __name__=='__main__':
    sys.exit(main())
