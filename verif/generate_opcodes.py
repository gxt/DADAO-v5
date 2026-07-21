#!/usr/bin/env python3
"""从 SimRISC 0.5.3 规范生成 opcodes.yaml"""

import yaml

def create_record(mnemonic, fmt, op, ha=None, fields=None, legality=None, wiki_cite=""):
    """创建一条指令记录"""
    if fields is None:
        fields = []
    if legality is None:
        legality = []
    
    # 计算 mask 和 value
    if ha is not None:
        # MISC 子表指令：op[7:0] + ha[5:0] + 18位
        mask = 0xFFFC0000
        value = (op << 24) | (ha << 18)
    else:
        # 主表指令：op[7:0] + 24位
        mask = 0xFF000000
        value = (op << 24)
    
    record = {
        "mnemonic": mnemonic,
        "format": fmt,
        "op": f"0x{op:02X}",
        "mask": f"0x{mask:08X}",
        "value": f"0x{value:08X}",
        "fields": fields,
        "legality": legality,
        "wiki_cite": wiki_cite
    }
    
    if ha is not None:
        record["ha"] = f"0x{ha:02X}"
    
    return record

def create_field(name, bits, role, bank, signed=None):
    """创建一个字段定义"""
    return {
        "name": name,
        "bits": bits,
        "role": role,
        "bank": bank,
        "signed": signed
    }

def generate_rrrr_fields(dst_name="rdha", src1_name="rdhb", src2_name="rdhc", src3_name="rdhd"):
    """生成 rrrr 格式的字段"""
    return [
        create_field(dst_name, "[23:18]", "dst", "rd"),
        create_field(src1_name, "[17:12]", "src", "rd"),
        create_field(src2_name, "[11:6]", "src", "rd"),
        create_field(src3_name, "[5:0]", "src", "rd")
    ]

def generate_orrr_fields(dst_name="rdhb", src1_name="rdhc", src2_name="rdhd"):
    """生成 orrr 格式的字段"""
    return [
        create_field("ha", "[23:18]", "minor_op", "imm"),
        create_field(dst_name, "[17:12]", "dst", "rd"),
        create_field(src1_name, "[11:6]", "src", "rd"),
        create_field(src2_name, "[5:0]", "src", "rd")
    ]

def generate_orri_fields(dst_name="rdhb", src_name="rdhc", imm_name="immu6"):
    """生成 orri 格式的字段"""
    return [
        create_field("ha", "[23:18]", "minor_op", "imm"),
        create_field(dst_name, "[17:12]", "dst", "rd"),
        create_field(src_name, "[11:6]", "src", "rd"),
        create_field(imm_name, "[5:0]", "imm", "imm", signed=False)
    ]

def generate_rrii_fields(dst_name="rdha", src_name="rbhb", imm_name="imms12"):
    """生成 rrii 格式的字段"""
    return [
        create_field(dst_name, "[23:18]", "dst", "rd"),
        create_field(src_name, "[17:12]", "src", "rb"),
        create_field(f"{imm_name}_hi", "[11:6]", "imm", "imm"),
        create_field(f"{imm_name}_lo", "[5:0]", "imm", "imm")
    ]

def generate_riii_fields(dst_name="rdha", imm_name="imms18"):
    """生成 riii 格式的字段"""
    return [
        create_field(dst_name, "[23:18]", "dst", "rd"),
        create_field(f"{imm_name}_hi", "[17:12]", "imm", "imm"),
        create_field(f"{imm_name}_mid", "[11:6]", "imm", "imm"),
        create_field(f"{imm_name}_lo", "[5:0]", "imm", "imm")
    ]

def generate_iiii_fields(imm_name="imms24"):
    """生成 iiii 格式的字段"""
    return [
        create_field(f"{imm_name}_b23_18", "[23:18]", "imm", "imm"),
        create_field(f"{imm_name}_b17_12", "[17:12]", "imm", "imm"),
        create_field(f"{imm_name}_b11_6", "[11:6]", "imm", "imm"),
        create_field(f"{imm_name}_b5_0", "[5:0]", "imm", "imm")
    ]

def generate_rwii_fields(dst_name="rdha", wp_name="wpN", imm_name="immu16"):
    """生成 rwii 格式的字段"""
    return [
        create_field(dst_name, "[23:18]", "dst", "rd"),
        create_field(wp_name, "[17:16]", "wyde_pos", "imm"),
        create_field(f"{imm_name}_hi", "[15:12]", "imm", "imm"),
        create_field(f"{imm_name}_mid", "[11:6]", "imm", "imm"),
        create_field(f"{imm_name}_lo", "[5:0]", "imm", "imm")
    ]

def generate_oiii_fields(imm_name="immu18"):
    """生成 oiii 格式的字段"""
    return [
        create_field("ha", "[23:18]", "minor_op", "imm"),
        create_field(f"{imm_name}_hi", "[17:12]", "imm", "imm"),
        create_field(f"{imm_name}_mid", "[11:6]", "imm", "imm"),
        create_field(f"{imm_name}_lo", "[5:0]", "imm", "imm")
    ]

def generate_crrr_fields(cfx_name="cfxcode", cg_name="cghb", rc_name="rchc", rd_name="rdhd"):
    """生成 crrr 格式的字段"""
    return [
        create_field(cfx_name, "[23:18]", "cfxcode", "imm"),
        create_field(cg_name, "[17:12]", "cfx_cg", "imm"),
        create_field(rc_name, "[11:6]", "cfx_rc", "imm"),
        create_field(rd_name, "[5:0]", "dst", "rd")
    ]

def generate_crii_fields(rb_name="rbhb", imm_name="immu12"):
    """生成 crii 格式的字段"""
    return [
        create_field("cfxcode", "[23:18]", "cfxcode", "imm"),
        create_field(rb_name, "[17:12]", "src", "rb"),
        create_field(f"{imm_name}_hi", "[11:6]", "imm", "imm"),
        create_field(f"{imm_name}_lo", "[5:0]", "imm", "imm")
    ]

def generate_ciii_fields(imm_name="immu18"):
    """生成 ciii 格式的字段"""
    return [
        create_field("cfxcode", "[23:18]", "cfxcode", "imm"),
        create_field(f"{imm_name}_hi", "[17:12]", "imm", "imm"),
        create_field(f"{imm_name}_mid", "[11:6]", "imm", "imm"),
        create_field(f"{imm_name}_lo", "[5:0]", "imm", "imm")
    ]

def main():
    records = []
    
    # ======================================================================
    # 主 QFC 表指令
    # ======================================================================
    
    # 0001-0xxx: 存取类指令
    # ld.ub-rd-rrii, ld.uw-rd-rrii, ld.ut-rd-rrii, ld.sb-rd-rrii, ld.sw-rd-rrii, ld.st-rd-rrii, ld.t-rf-rrii, st.t-rf-rrii
    op = 0x10
    ld_rd_mnemonics = ["ld.ub-rd", "ld.uw-rd", "ld.ut-rd", "ld.sb-rd", "ld.sw-rd", "ld.st-rd"]
    for i, mnem in enumerate(ld_rd_mnemonics):
        records.append(create_record(
            mnem, "rrii", op + i,
            fields=generate_rrii_fields("rdha", "rbhb", "imms12"),
            legality=["rdha != rd0"],
            wiki_cite="SimRISC-01 §存取RD寄存器"
        ))
    
    # ld.t-rf-rrii, st.t-rf-rrii
    records.append(create_record("ld.t-rf", "rrii", 0x16,
        fields=generate_rrii_fields("rfha", "rbhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-03 §存取RF寄存器"
    ))
    records.append(create_record("st.t-rf", "rrii", 0x17,
        fields=generate_rrii_fields("rfha", "rbhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-03 §存取RF寄存器"
    ))
    
    # 0001-1xxx: st.b-rd-rrii, st.w-rd-rrii, st.t-rd-rrii
    st_rd_mnemonics = ["st.b-rd", "st.w-rd", "st.t-rd"]
    for i, mnem in enumerate(st_rd_mnemonics):
        records.append(create_record(
            mnem, "rrii", 0x18 + i,
            fields=generate_rrii_fields("rdha", "rbhb", "imms12"),
            legality=["rdha != rd0"],
            wiki_cite="SimRISC-01 §存取RD寄存器"
        ))
    
    # 0010-0xxx: ld.o-rd-rrii, st.o-rd-rrii, ld.o-rb-rrii, st.o-rb-rrii, ld.o-ra-rrii, st.o-ra-rrii, ld.o-rf-rrii, st.o-rf-rrii
    records.append(create_record("ld.o-rd", "rrii", 0x20,
        fields=generate_rrii_fields("rdha", "rbhb", "imms12"),
        legality=["rdha != rd0"],
        wiki_cite="SimRISC-01 §存取RD寄存器"
    ))
    records.append(create_record("st.o-rd", "rrii", 0x21,
        fields=generate_rrii_fields("rdha", "rbhb", "imms12"),
        legality=["rdha != rd0"],
        wiki_cite="SimRISC-01 §存取RD寄存器"
    ))
    records.append(create_record("ld.o-rb", "rrii", 0x22,
        fields=generate_rrii_fields("rbha", "rbhb", "imms12"),
        legality=["rbha != rb0"],
        wiki_cite="SimRISC-02 §存取RB寄存器"
    ))
    records.append(create_record("st.o-rb", "rrii", 0x23,
        fields=generate_rrii_fields("rbha", "rbhb", "imms12"),
        legality=["rbha != rb0"],
        wiki_cite="SimRISC-02 §存取RB寄存器"
    ))
    records.append(create_record("ld.o-ra", "rrii", 0x24,
        fields=generate_rrii_fields("raha", "rbhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-02 §存取RA寄存器"
    ))
    records.append(create_record("st.o-ra", "rrii", 0x25,
        fields=generate_rrii_fields("raha", "rbhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-02 §存取RA寄存器"
    ))
    records.append(create_record("ld.o-rf", "rrii", 0x26,
        fields=generate_rrii_fields("rfha", "rbhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-03 §存取RF寄存器"
    ))
    records.append(create_record("st.o-rf", "rrii", 0x27,
        fields=generate_rrii_fields("rfha", "rbhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-03 §存取RF寄存器"
    ))
    
    # 0010-1xxx: ldm.ub-rd-rrri, ldm.uw-rd-rrri, ldm.ut-rd-rrri, ldm.sb-rd-rrri, ldm.sw-rd-rrri, ldm.st-rd-rrri, ldm.t-rf-rrri, stm.t-rf-rrri
    ldm_rd_mnemonics = ["ldm.ub-rd", "ldm.uw-rd", "ldm.ut-rd", "ldm.sb-rd", "ldm.sw-rd", "ldm.st-rd"]
    for i, mnem in enumerate(ldm_rd_mnemonics):
        records.append(create_record(
            mnem, "rrri", 0x28 + i,
            fields=[
                create_field("rdha", "[23:18]", "dst", "rd"),
                create_field("rbhb", "[17:12]", "src", "rb"),
                create_field("rdhc", "[11:6]", "src", "rd"),
                create_field("immu6", "[5:0]", "imm", "imm", signed=False)
            ],
            legality=["rdha != rd0", "immu6 != 0", "rdha + immu6 <= 64"],
            wiki_cite="SimRISC-01 §存取RD寄存器"
        ))
    
    records.append(create_record("ldm.t-rf", "rrri", 0x2E,
        fields=[
            create_field("rfha", "[23:18]", "dst", "rf"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["immu6 != 0", "rfha + immu6 <= 64"],
        wiki_cite="SimRISC-03 §存取RF寄存器"
    ))
    records.append(create_record("stm.t-rf", "rrri", 0x2F,
        fields=[
            create_field("rfha", "[23:18]", "src", "rf"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["immu6 != 0", "rfha + immu6 <= 64"],
        wiki_cite="SimRISC-03 §存取RF寄存器"
    ))
    
    # 0011-0xxx: stm.b-rd-rrri, stm.w-rd-rrri, stm.t-rd-rrri
    stm_rd_mnemonics = ["stm.b-rd", "stm.w-rd", "stm.t-rd"]
    for i, mnem in enumerate(stm_rd_mnemonics):
        records.append(create_record(
            mnem, "rrri", 0x30 + i,
            fields=[
                create_field("rdha", "[23:18]", "src", "rd"),
                create_field("rbhb", "[17:12]", "src", "rb"),
                create_field("rdhc", "[11:6]", "src", "rd"),
                create_field("immu6", "[5:0]", "imm", "imm", signed=False)
            ],
            legality=["rdha != rd0", "immu6 != 0", "rdha + immu6 <= 64"],
            wiki_cite="SimRISC-01 §存取RD寄存器"
        ))
    
    # 0011-1xxx: ldm.o-rd-rrri, stm.o-rd-rrri, ldm.o-rb-rrri, stm.o-rb-rrri, ldm.o-ra-rrri, stm.o-ra-rrri, ldm.o-rf-rrri, stm.o-rf-rrri
    records.append(create_record("ldm.o-rd", "rrri", 0x38,
        fields=[
            create_field("rdha", "[23:18]", "dst", "rd"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["rdha != rd0", "immu6 != 0", "rdha + immu6 <= 64"],
        wiki_cite="SimRISC-01 §存取RD寄存器"
    ))
    records.append(create_record("stm.o-rd", "rrri", 0x39,
        fields=[
            create_field("rdha", "[23:18]", "src", "rd"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["rdha != rd0", "immu6 != 0", "rdha + immu6 <= 64"],
        wiki_cite="SimRISC-01 §存取RD寄存器"
    ))
    records.append(create_record("ldm.o-rb", "rrri", 0x3A,
        fields=[
            create_field("rbha", "[23:18]", "dst", "rb"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["rbha != rb0", "immu6 != 0", "rbha + immu6 <= 64"],
        wiki_cite="SimRISC-02 §存取RB寄存器"
    ))
    records.append(create_record("stm.o-rb", "rrri", 0x3B,
        fields=[
            create_field("rbha", "[23:18]", "src", "rb"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["rbha != rb0", "immu6 != 0", "rbha + immu6 <= 64"],
        wiki_cite="SimRISC-02 §存取RB寄存器"
    ))
    records.append(create_record("ldm.o-ra", "rrri", 0x3C,
        fields=[
            create_field("raha", "[23:18]", "dst", "ra"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["immu6 != 0", "raha + immu6 <= 64"],
        wiki_cite="SimRISC-02 §存取RA寄存器"
    ))
    records.append(create_record("stm.o-ra", "rrri", 0x3D,
        fields=[
            create_field("raha", "[23:18]", "src", "ra"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["immu6 != 0", "raha + immu6 <= 64"],
        wiki_cite="SimRISC-02 §存取RA寄存器"
    ))
    records.append(create_record("ldm.o-rf", "rrri", 0x3E,
        fields=[
            create_field("rfha", "[23:18]", "dst", "rf"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["immu6 != 0", "rfha + immu6 <= 64"],
        wiki_cite="SimRISC-03 §存取RF寄存器"
    ))
    records.append(create_record("stm.o-rf", "rrri", 0x3F,
        fields=[
            create_field("rfha", "[23:18]", "src", "rf"),
            create_field("rbhb", "[17:12]", "src", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["immu6 != 0", "rfha + immu6 <= 64"],
        wiki_cite="SimRISC-03 §存取RF寄存器"
    ))
    
    # 0100-0xxx: MISC-octa, MISC-tetra, MISC-wyde, MISC-byte, MISC-RF
    # 这些是子表的入口，不直接生成指令
    
    # 0100-1xxx: 立即数赋值指令
    records.append(create_record("or.w-rd", "rwii", 0x48,
        fields=generate_rwii_fields("rdha", "wpN", "immu16"),
        legality=[],
        wiki_cite="SimRISC-01 §立即数常数赋值"
    ))
    records.append(create_record("andn.w-rd", "rwii", 0x49,
        fields=generate_rwii_fields("rdha", "wpN", "immu16"),
        legality=[],
        wiki_cite="SimRISC-01 §立即数常数赋值"
    ))
    records.append(create_record("or.w-rb", "rwii", 0x4A,
        fields=generate_rwii_fields("rbha", "wpN", "immu16"),
        legality=[],
        wiki_cite="SimRISC-02 §立即数常数赋值"
    ))
    records.append(create_record("andn.w-rb", "rwii", 0x4B,
        fields=generate_rwii_fields("rbha", "wpN", "immu16"),
        legality=[],
        wiki_cite="SimRISC-02 §立即数常数赋值"
    ))
    records.append(create_record("set.zw-rd", "rwii", 0x4C,
        fields=generate_rwii_fields("rdha", "wpN", "immu16"),
        legality=[],
        wiki_cite="SimRISC-01 §立即数常数赋值"
    ))
    records.append(create_record("set.ow-rd", "rwii", 0x4D,
        fields=generate_rwii_fields("rdha", "wpN", "immu16"),
        legality=[],
        wiki_cite="SimRISC-01 §立即数常数赋值"
    ))
    records.append(create_record("set.zw-rb", "rwii", 0x4E,
        fields=generate_rwii_fields("rbha", "wpN", "immu16"),
        legality=[],
        wiki_cite="SimRISC-02 §立即数常数赋值"
    ))
    records.append(create_record("set.w-rf", "rwii", 0x4F,
        fields=generate_rwii_fields("rfha", "wpN", "immu16"),
        legality=[],
        wiki_cite="SimRISC-03 §立即数常数赋值"
    ))
    
    # 0101-0xxx: 算术运算指令
    records.append(create_record("add.uo-rd", "rrrr", 0x50,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["!(rdha == rd0 && rdhb == rd0)"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("add.so-rd", "rrrr", 0x51,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["!(rdha == rd0 && rdhb == rd0)"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("sub.uo-rd", "rrrr", 0x52,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["!(rdha == rd0 && rdhb == rd0)"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("sub.so-rd", "rrrr", 0x53,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["!(rdha == rd0 && rdhb == rd0)"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("mul.uo-rd", "rrrr", 0x54,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["!(rdha == rd0 && rdhb == rd0)"],
        wiki_cite="SimRISC-01 §乘除操作"
    ))
    records.append(create_record("mul.so-rd", "rrrr", 0x55,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["!(rdha == rd0 && rdhb == rd0)"],
        wiki_cite="SimRISC-01 §乘除操作"
    ))
    records.append(create_record("ftmadd", "rrrr", 0x56,
        fields=[
            create_field("rfha", "[23:18]", "dst", "rf"),
            create_field("rfhb", "[17:12]", "src", "rf"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rfha != rf0", "rfhb != rf0", "rfhc != rf0", "rfhd != rf0"],
        wiki_cite="SimRISC-03 §S3D1"
    ))
    records.append(create_record("fomadd", "rrrr", 0x57,
        fields=[
            create_field("rfha", "[23:18]", "dst", "rf"),
            create_field("rfhb", "[17:12]", "src", "rf"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rfha != rf0", "rfhb != rf0", "rfhc != rf0", "rfhd != rf0"],
        wiki_cite="SimRISC-03 §S3D1"
    ))
    
    # 0101-1xxx: 立即数加法、比较等
    # 0x58: 空
    records.append(create_record("add.si-rd", "riii", 0x59,
        fields=generate_riii_fields("rdha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-01 §自增自减"
    ))
    records.append(create_record("rela.si-rb", "riii", 0x5A,
        fields=generate_riii_fields("rbha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §PC相对寻址"
    ))
    records.append(create_record("add.si-rb", "riii", 0x5B,
        fields=generate_riii_fields("rbha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §自增自减"
    ))
    records.append(create_record("cmp.ui-rd", "rrii", 0x5C,
        fields=generate_rrii_fields("rdha", "rdhb", "immu12"),
        legality=["rdha != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    records.append(create_record("cmp.si-rd", "rrii", 0x5D,
        fields=generate_rrii_fields("rdha", "rdhb", "imms12"),
        legality=["rdha != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    records.append(create_record("cs.eq-rf", "rrrr", 0x5E,
        fields=[
            create_field("rdha", "[23:18]", "src", "rd"),
            create_field("rdhb", "[17:12]", "src", "rd"),
            create_field("rfhc", "[11:6]", "dst", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rfhc != rf0"],
        wiki_cite="SimRISC-03 §浮点条件赋值指令"
    ))
    records.append(create_record("cs.ne-rf", "rrrr", 0x5F,
        fields=[
            create_field("rdha", "[23:18]", "src", "rd"),
            create_field("rdhb", "[17:12]", "src", "rd"),
            create_field("rfhc", "[11:6]", "dst", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rfhc != rf0"],
        wiki_cite="SimRISC-03 §浮点条件赋值指令"
    ))
    
    # 0110-0xxx: 条件赋值指令
    records.append(create_record("cs.n-rd", "rrrr", 0x60,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §条件赋值"
    ))
    records.append(create_record("cs.n-rf", "rrrr", 0x61,
        fields=[
            create_field("rdha", "[23:18]", "src", "rd"),
            create_field("rfhb", "[17:12]", "dst", "rf"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rfhb != rf0"],
        wiki_cite="SimRISC-03 §浮点条件赋值指令"
    ))
    records.append(create_record("cs.z-rd", "rrrr", 0x62,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §条件赋值"
    ))
    records.append(create_record("cs.z-rf", "rrrr", 0x63,
        fields=[
            create_field("rdha", "[23:18]", "src", "rd"),
            create_field("rfhb", "[17:12]", "dst", "rf"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rfhb != rf0"],
        wiki_cite="SimRISC-03 §浮点条件赋值指令"
    ))
    records.append(create_record("cs.p-rd", "rrrr", 0x64,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §条件赋值"
    ))
    records.append(create_record("cs.p-rf", "rrrr", 0x65,
        fields=[
            create_field("rdha", "[23:18]", "src", "rd"),
            create_field("rfhb", "[17:12]", "dst", "rf"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rfhb != rf0"],
        wiki_cite="SimRISC-03 §浮点条件赋值指令"
    ))
    records.append(create_record("cs.eq-rd", "rrrr", 0x66,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["rdhc != rd0"],
        wiki_cite="SimRISC-01 §条件赋值"
    ))
    records.append(create_record("cs.ne-rd", "rrrr", 0x67,
        fields=generate_rrrr_fields("rdha", "rdhb", "rdhc", "rdhd"),
        legality=["rdhc != rd0"],
        wiki_cite="SimRISC-01 §条件赋值"
    ))
    
    # 0110-1xxx: 条件跳转指令
    records.append(create_record("br.n-rd", "riii", 0x68,
        fields=generate_riii_fields("rdha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    records.append(create_record("br.nn-rd", "riii", 0x69,
        fields=generate_riii_fields("rdha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    records.append(create_record("br.z-rd", "riii", 0x6A,
        fields=generate_riii_fields("rdha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    records.append(create_record("br.nz-rd", "riii", 0x6B,
        fields=generate_riii_fields("rdha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    records.append(create_record("br.p-rd", "riii", 0x6C,
        fields=generate_riii_fields("rdha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    records.append(create_record("br.np-rd", "riii", 0x6D,
        fields=generate_riii_fields("rdha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    records.append(create_record("br.eq-rd", "rrii", 0x6E,
        fields=generate_rrii_fields("rdha", "rdhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    records.append(create_record("br.ne-rd", "rrii", 0x6F,
        fields=generate_rrii_fields("rdha", "rdhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    
    # 0111-0xxx: 无条件跳转、函数调用等
    records.append(create_record("jump-iiii", "iiii", 0x70,
        fields=generate_iiii_fields("imms24"),
        legality=[],
        wiki_cite="SimRISC-02 §无条件跳转指令"
    ))
    records.append(create_record("jump-rrii", "rrii", 0x71,
        fields=generate_rrii_fields("rbha", "rdhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-02 §无条件跳转指令"
    ))
    records.append(create_record("br.z-rb", "riii", 0x72,
        fields=generate_riii_fields("rbha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    records.append(create_record("br.nz-rb", "riii", 0x73,
        fields=generate_riii_fields("rbha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §条件跳转指令"
    ))
    records.append(create_record("call-iiii", "iiii", 0x74,
        fields=generate_iiii_fields("imms24"),
        legality=[],
        wiki_cite="SimRISC-02 §函数调用"
    ))
    records.append(create_record("call-rrii", "rrii", 0x75,
        fields=generate_rrii_fields("rbha", "rdhb", "imms12"),
        legality=[],
        wiki_cite="SimRISC-02 §函数调用"
    ))
    records.append(create_record("ret-riii", "riii", 0x76,
        fields=generate_riii_fields("rdha", "imms18"),
        legality=[],
        wiki_cite="SimRISC-02 §函数返回"
    ))
    records.append(create_record("swym-iiii", "iiii", 0x77,
        fields=generate_iiii_fields("immu24"),
        legality=[],
        wiki_cite="SimRISC-04 §占位指令"
    ))
    
    # 0111-1xxx: 特权指令
    records.append(create_record("cfx2rd-crrr", "crrr", 0x7A,
        fields=generate_crrr_fields(),
        legality=[],
        wiki_cite="SimRISC-04 §寄存器传输指令"
    ))
    records.append(create_record("cfx2rc-crrr", "crrr", 0x7B,
        fields=generate_crrr_fields(),
        legality=[],
        wiki_cite="SimRISC-04 §寄存器传输指令"
    ))
    records.append(create_record("cfxld-crii", "crii", 0x7C,
        fields=generate_crii_fields(),
        legality=[],
        wiki_cite="SimRISC-04 §SRAM块传输指令"
    ))
    records.append(create_record("cfxst-crii", "crii", 0x7D,
        fields=generate_crii_fields(),
        legality=[],
        wiki_cite="SimRISC-04 §SRAM块传输指令"
    ))
    records.append(create_record("escape-ciii", "ciii", 0x7E,
        fields=generate_ciii_fields("imms18"),
        legality=[],
        wiki_cite="SimRISC-04 §退出指令"
    ))
    records.append(create_record("trap-ciii", "ciii", 0x7F,
        fields=generate_ciii_fields("immu18"),
        legality=[],
        wiki_cite="SimRISC-04 §陷入指令"
    ))
    
    # ======================================================================
    # MISC-AMO 子表 (op=0x00)
    # ======================================================================
    misc_amo_op = 0x00
    
    # illi-oiii
    records.append(create_record("illi", "oiii", misc_amo_op, ha=0x00,
        fields=generate_oiii_fields("immu18"),
        legality=[],
        wiki_cite="SimRISC-04 §非法指令"
    ))
    
    # fence-oiii
    records.append(create_record("fence", "oiii", misc_amo_op, ha=0x01,
        fields=generate_oiii_fields("immu18"),
        legality=[],
        wiki_cite="SimRISC-04 §fence指令"
    ))
    
    # lr_nn.o-orrr, lr_nr.o-orrr, lr_an.o-orrr, lr_ar.o-orrr
    lr_mnemonics = ["lr_nn.o", "lr_nr.o", "lr_an.o", "lr_ar.o"]
    for i, mnem in enumerate(lr_mnemonics):
        records.append(create_record(mnem, "orrr", misc_amo_op, ha=0x20 + i,
            fields=[
                create_field("ha", "[23:18]", "minor_op", "imm"),
                create_field("rdhb", "[17:12]", "dst", "rd"),
                create_field("rdhc", "[11:6]", "src", "rd"),
                create_field("rbhd", "[5:0]", "src", "rb")
            ],
            legality=["rdhb == rd0"],
            wiki_cite="SimRISC-04 §LR-SC指令"
        ))
    
    # sc_nn.o-orrr, sc_nr.o-orrr, sc_an.o-orrr, sc_ar.o-orrr
    sc_mnemonics = ["sc_nn.o", "sc_nr.o", "sc_an.o", "sc_ar.o"]
    for i, mnem in enumerate(sc_mnemonics):
        records.append(create_record(mnem, "orrr", misc_amo_op, ha=0x30 + i,
            fields=[
                create_field("ha", "[23:18]", "minor_op", "imm"),
                create_field("rdhb", "[17:12]", "dst", "rd"),
                create_field("rdhc", "[11:6]", "src", "rd"),
                create_field("rbhd", "[5:0]", "src", "rb")
            ],
            legality=[],
            wiki_cite="SimRISC-04 §LR-SC指令"
        ))
    
    # ======================================================================
    # MISC-octa 子表 (op=0x40)
    # ======================================================================
    misc_octa_op = 0x40
    
    # and.o-orrr, or.o-orrr, xor.o-orrr, xnor.o-orrr
    logic_octa_mnemonics = ["and.o", "or.o", "xor.o", "xnor.o"]
    for i, mnem in enumerate(logic_octa_mnemonics):
        records.append(create_record(mnem, "orrr", misc_octa_op, ha=0x08 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §逻辑运算"
        ))
    
    # ext.uo-orrr, ext.so-orrr, shr.uo-orrr, shr.so-orrr, shl.uo-orrr
    ext_octa_mnemonics = ["ext.uo", "ext.so", "shr.uo", "shr.so", "shl.uo"]
    for i, mnem in enumerate(ext_octa_mnemonics):
        records.append(create_record(mnem, "orrr", misc_octa_op, ha=0x10 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §位操作"
        ))
    
    # ext.uo-orri, ext.so-orri, shr.uo-orri, shr.so-orri, shl.uo-orri
    for i, mnem in enumerate(ext_octa_mnemonics):
        records.append(create_record(mnem, "orri", misc_octa_op, ha=0x18 + i,
            fields=generate_orri_fields("rdhb", "rdhc", "immu6"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §位操作"
        ))
    
    # add.so-rb-orrr
    records.append(create_record("add.so-rb", "orrr", misc_octa_op, ha=0x20,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rbhb", "[17:12]", "dst", "rb"),
            create_field("rbhc", "[11:6]", "src", "rb"),
            create_field("rdhd", "[5:0]", "src", "rd")
        ],
        legality=["rbhb != rb0"],
        wiki_cite="SimRISC-02 §加减操作"
    ))
    
    # sub.so-rb-orrr, cmp.uo-rb-orrr, cmp.uo-orrr, cmp.so-orrr
    records.append(create_record("sub.so-rb", "orrr", misc_octa_op, ha=0x28,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rbhb", "[17:12]", "dst", "rb"),
            create_field("rbhc", "[11:6]", "src", "rb"),
            create_field("rdhd", "[5:0]", "src", "rd")
        ],
        legality=["rbhb != rb0"],
        wiki_cite="SimRISC-02 §加减操作"
    ))
    records.append(create_record("cmp.uo-rb", "orrr", misc_octa_op, ha=0x29,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rdhb", "[17:12]", "dst", "rd"),
            create_field("rbhc", "[11:6]", "src", "rb"),
            create_field("rbhd", "[5:0]", "src", "rb")
        ],
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-02 §比较操作"
    ))
    records.append(create_record("cmp.uo", "orrr", misc_octa_op, ha=0x2A,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    records.append(create_record("cmp.so", "orrr", misc_octa_op, ha=0x2B,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    
    # rd2rd-orri, rd2ra-orri, ra2rd-orri
    records.append(create_record("rd2rd", "orri", misc_octa_op, ha=0x2C,
        fields=generate_orri_fields("rdhb", "rdhc", "immu6"),
        legality=["rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64", "rdhc + immu6 <= 64"],
        wiki_cite="SimRISC-01 §寄存器组之间块赋值"
    ))
    records.append(create_record("rd2ra", "orri", misc_octa_op, ha=0x2D,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rahb", "[17:12]", "dst", "ra"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["immu6 != 0", "rahb + immu6 <= 64", "rdhc + immu6 <= 64"],
        wiki_cite="SimRISC-02 §寄存器组之间块赋值"
    ))
    records.append(create_record("ra2rd", "orri", misc_octa_op, ha=0x2E,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rdhb", "[17:12]", "dst", "rd"),
            create_field("rahc", "[11:6]", "src", "ra"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64", "rahc + immu6 <= 64"],
        wiki_cite="SimRISC-02 §寄存器组之间块赋值"
    ))
    
    # rb2rb-orri, rd2rb-orri, rb2rd-orri
    records.append(create_record("rb2rb", "orri", misc_octa_op, ha=0x34,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rbhb", "[17:12]", "dst", "rb"),
            create_field("rbhc", "[11:6]", "src", "rb"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["rbhb != rb0", "immu6 != 0", "rbhb + immu6 <= 64", "rbhc + immu6 <= 64"],
        wiki_cite="SimRISC-02 §寄存器组之间块赋值"
    ))
    records.append(create_record("rd2rb", "orri", misc_octa_op, ha=0x35,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rbhb", "[17:12]", "dst", "rb"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["rbhb != rb0", "immu6 != 0", "rbhb + immu6 <= 64", "rdhc + immu6 <= 64"],
        wiki_cite="SimRISC-02 §寄存器组之间块赋值"
    ))
    records.append(create_record("rb2rd", "orri", misc_octa_op, ha=0x36,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rdhb", "[17:12]", "dst", "rd"),
            create_field("rbhc", "[11:6]", "src", "rb"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64", "rbhc + immu6 <= 64"],
        wiki_cite="SimRISC-02 §寄存器组之间块赋值"
    ))
    
    # div.uo-orrr, div.so-orrr, rem.uo-orrr, rem.so-orrr
    div_octa_mnemonics = ["div.uo", "div.so", "rem.uo", "rem.so"]
    for i, mnem in enumerate(div_octa_mnemonics):
        records.append(create_record(mnem, "orrr", misc_octa_op, ha=0x38 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0", "rdhd != rd0"],
            wiki_cite="SimRISC-01 §乘除操作"
        ))
    
    # rd2rf-orri, rf2rd-orri
    records.append(create_record("rd2rf", "orri", misc_octa_op, ha=0x3E,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rfhb", "[17:12]", "dst", "rf"),
            create_field("rdhc", "[11:6]", "src", "rd"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["immu6 != 0", "rfhb + immu6 <= 64", "rdhc + immu6 <= 64"],
        wiki_cite="SimRISC-03 §寄存器组之间块赋值"
    ))
    records.append(create_record("rf2rd", "orri", misc_octa_op, ha=0x3F,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rdhb", "[17:12]", "dst", "rd"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("immu6", "[5:0]", "imm", "imm", signed=False)
        ],
        legality=["rdhb != rd0", "immu6 != 0", "rdhb + immu6 <= 64", "rfhc + immu6 <= 64"],
        wiki_cite="SimRISC-03 §寄存器组之间块赋值"
    ))
    
    # ======================================================================
    # MISC-tetra 子表 (op=0x41)
    # ======================================================================
    misc_tetra_op = 0x41
    
    # and.t-orrr, or.t-orrr, xor.t-orrr, xnor.t-orrr
    logic_tetra_mnemonics = ["and.t", "or.t", "xor.t", "xnor.t"]
    for i, mnem in enumerate(logic_tetra_mnemonics):
        records.append(create_record(mnem, "orrr", misc_tetra_op, ha=0x08 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §逻辑运算"
        ))
    
    # ext.ut-orrr, ext.st-orrr, shr.ut-orrr, shr.st-orrr, shl.ut-orrr
    ext_tetra_mnemonics = ["ext.ut", "ext.st", "shr.ut", "shr.st", "shl.ut"]
    for i, mnem in enumerate(ext_tetra_mnemonics):
        records.append(create_record(mnem, "orrr", misc_tetra_op, ha=0x10 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §位操作"
        ))
    
    # ext.ut-orri, ext.st-orri, shr.ut-orri, shr.st-orri, shl.ut-orri
    for i, mnem in enumerate(ext_tetra_mnemonics):
        records.append(create_record(mnem, "orri", misc_tetra_op, ha=0x18 + i,
            fields=generate_orri_fields("rdhb", "rdhc", "immu6"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §位操作"
        ))
    
    # add.ut-orrr, add.st-orrr
    records.append(create_record("add.ut", "orrr", misc_tetra_op, ha=0x20,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("add.st", "orrr", misc_tetra_op, ha=0x21,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    
    # sub.ut-orrr, sub.st-orrr, cmp.ut-orrr, cmp.st-orrr
    records.append(create_record("sub.ut", "orrr", misc_tetra_op, ha=0x28,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("sub.st", "orrr", misc_tetra_op, ha=0x29,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("cmp.ut", "orrr", misc_tetra_op, ha=0x2A,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    records.append(create_record("cmp.st", "orrr", misc_tetra_op, ha=0x2B,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    
    # mul.ut-orrr, mul.st-orrr
    records.append(create_record("mul.ut", "orrr", misc_tetra_op, ha=0x30,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §乘除操作"
    ))
    records.append(create_record("mul.st", "orrr", misc_tetra_op, ha=0x31,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §乘除操作"
    ))
    
    # div.ut-orrr, div.st-orrr, rem.ut-orrr, rem.st-orrr
    div_tetra_mnemonics = ["div.ut", "div.st", "rem.ut", "rem.st"]
    for i, mnem in enumerate(div_tetra_mnemonics):
        records.append(create_record(mnem, "orrr", misc_tetra_op, ha=0x38 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0", "rdhd != rd0"],
            wiki_cite="SimRISC-01 §乘除操作"
        ))
    
    # ======================================================================
    # MISC-wyde 子表 (op=0x42)
    # ======================================================================
    misc_wyde_op = 0x42
    
    # and.w-orrr, or.w-orrr, xor.w-orrr, xnor.w-orrr
    logic_wyde_mnemonics = ["and.w", "or.w", "xor.w", "xnor.w"]
    for i, mnem in enumerate(logic_wyde_mnemonics):
        records.append(create_record(mnem, "orrr", misc_wyde_op, ha=0x08 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §逻辑运算"
        ))
    
    # ext.uw-orrr, ext.sw-orrr, shr.uw-orrr, shr.sw-orrr, shl.uw-orrr
    ext_wyde_mnemonics = ["ext.uw", "ext.sw", "shr.uw", "shr.sw", "shl.uw"]
    for i, mnem in enumerate(ext_wyde_mnemonics):
        records.append(create_record(mnem, "orrr", misc_wyde_op, ha=0x10 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §位操作"
        ))
    
    # ext.uw-orri, ext.sw-orri, shr.uw-orri, shr.sw-orri, shl.uw-orri
    for i, mnem in enumerate(ext_wyde_mnemonics):
        records.append(create_record(mnem, "orri", misc_wyde_op, ha=0x18 + i,
            fields=generate_orri_fields("rdhb", "rdhc", "immu6"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §位操作"
        ))
    
    # add.uw-orrr, add.sw-orrr
    records.append(create_record("add.uw", "orrr", misc_wyde_op, ha=0x20,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("add.sw", "orrr", misc_wyde_op, ha=0x21,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    
    # sub.uw-orrr, sub.sw-orrr, cmp.uw-orrr, cmp.sw-orrr
    records.append(create_record("sub.uw", "orrr", misc_wyde_op, ha=0x28,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("sub.sw", "orrr", misc_wyde_op, ha=0x29,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("cmp.uw", "orrr", misc_wyde_op, ha=0x2A,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    records.append(create_record("cmp.sw", "orrr", misc_wyde_op, ha=0x2B,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    
    # mul.uw-orrr, mul.sw-orrr
    records.append(create_record("mul.uw", "orrr", misc_wyde_op, ha=0x30,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §乘除操作"
    ))
    records.append(create_record("mul.sw", "orrr", misc_wyde_op, ha=0x31,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §乘除操作"
    ))
    
    # div.uw-orrr, div.sw-orrr, rem.uw-orrr, rem.sw-orrr
    div_wyde_mnemonics = ["div.uw", "div.sw", "rem.uw", "rem.sw"]
    for i, mnem in enumerate(div_wyde_mnemonics):
        records.append(create_record(mnem, "orrr", misc_wyde_op, ha=0x38 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0", "rdhd != rd0"],
            wiki_cite="SimRISC-01 §乘除操作"
        ))
    
    # ======================================================================
    # MISC-byte 子表 (op=0x43)
    # ======================================================================
    misc_byte_op = 0x43
    
    # and.b-orrr, or.b-orrr, xor.b-orrr, xnor.b-orrr
    logic_byte_mnemonics = ["and.b", "or.b", "xor.b", "xnor.b"]
    for i, mnem in enumerate(logic_byte_mnemonics):
        records.append(create_record(mnem, "orrr", misc_byte_op, ha=0x08 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §逻辑运算"
        ))
    
    # ext.ub-orrr, ext.sb-orrr, shr.ub-orrr, shr.sb-orrr, shl.ub-orrr
    ext_byte_mnemonics = ["ext.ub", "ext.sb", "shr.ub", "shr.sb", "shl.ub"]
    for i, mnem in enumerate(ext_byte_mnemonics):
        records.append(create_record(mnem, "orrr", misc_byte_op, ha=0x10 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §位操作"
        ))
    
    # ext.ub-orri, ext.sb-orri, shr.ub-orri, shr.sb-orri, shl.ub-orri
    for i, mnem in enumerate(ext_byte_mnemonics):
        records.append(create_record(mnem, "orri", misc_byte_op, ha=0x18 + i,
            fields=generate_orri_fields("rdhb", "rdhc", "immu6"),
            legality=["rdhb != rd0"],
            wiki_cite="SimRISC-01 §位操作"
        ))
    
    # add.ub-orrr, add.sb-orrr
    records.append(create_record("add.ub", "orrr", misc_byte_op, ha=0x20,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("add.sb", "orrr", misc_byte_op, ha=0x21,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    
    # sub.ub-orrr, sub.sb-orrr, cmp.ub-orrr, cmp.sb-orrr
    records.append(create_record("sub.ub", "orrr", misc_byte_op, ha=0x28,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("sub.sb", "orrr", misc_byte_op, ha=0x29,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §加减操作"
    ))
    records.append(create_record("cmp.ub", "orrr", misc_byte_op, ha=0x2A,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    records.append(create_record("cmp.sb", "orrr", misc_byte_op, ha=0x2B,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §比较操作"
    ))
    
    # mul.ub-orrr, mul.sb-orrr
    records.append(create_record("mul.ub", "orrr", misc_byte_op, ha=0x30,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §乘除操作"
    ))
    records.append(create_record("mul.sb", "orrr", misc_byte_op, ha=0x31,
        fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-01 §乘除操作"
    ))
    
    # div.ub-orrr, div.sb-orrr, rem.ub-orrr, rem.sb-orrr
    div_byte_mnemonics = ["div.ub", "div.sb", "rem.ub", "rem.sb"]
    for i, mnem in enumerate(div_byte_mnemonics):
        records.append(create_record(mnem, "orrr", misc_byte_op, ha=0x38 + i,
            fields=generate_orrr_fields("rdhb", "rdhc", "rdhd"),
            legality=["rdhb != rd0", "rdhd != rd0"],
            wiki_cite="SimRISC-01 §乘除操作"
        ))
    
    # ======================================================================
    # MISC-RF 子表 (op=0x44)
    # ======================================================================
    misc_rf_op = 0x44
    
    # ftcls-orri, ft2fo-orri, ft2ft-orri
    records.append(create_record("ftcls", "orri", misc_rf_op, ha=0x00,
        fields=generate_orri_fields("rdhb", "rfhc", "immu6"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-03 §浮点分类指令"
    ))
    records.append(create_record("ft2fo", "orri", misc_rf_op, ha=0x01,
        fields=generate_orri_fields("rfhb", "rfhc", "immu6"),
        legality=[],
        wiki_cite="SimRISC-03 §格式转换指令"
    ))
    records.append(create_record("ft2ft", "orri", misc_rf_op, ha=0x02,
        fields=generate_orri_fields("rfhb", "rfhc", "immu6"),
        legality=[],
        wiki_cite="SimRISC-03 §格式转换指令"
    ))
    
    # ftroot-orri, ftlog-orri
    records.append(create_record("ftroot", "orri", misc_rf_op, ha=0x06,
        fields=generate_orri_fields("rfhb", "rfhc", "immu6"),
        legality=[],
        wiki_cite="SimRISC-03 §S1D1"
    ))
    records.append(create_record("ftlog", "orri", misc_rf_op, ha=0x07,
        fields=generate_orri_fields("rfhb", "rfhc", "immu6"),
        legality=[],
        wiki_cite="SimRISC-03 §S1D1"
    ))
    
    # focls-orri, fo2ft-orri, fo2fo-orri
    records.append(create_record("focls", "orri", misc_rf_op, ha=0x08,
        fields=generate_orri_fields("rdhb", "rfhc", "immu6"),
        legality=["rdhb != rd0"],
        wiki_cite="SimRISC-03 §浮点分类指令"
    ))
    records.append(create_record("fo2ft", "orri", misc_rf_op, ha=0x09,
        fields=generate_orri_fields("rfhb", "rfhc", "immu6"),
        legality=[],
        wiki_cite="SimRISC-03 §格式转换指令"
    ))
    records.append(create_record("fo2fo", "orri", misc_rf_op, ha=0x0A,
        fields=generate_orri_fields("rfhb", "rfhc", "immu6"),
        legality=[],
        wiki_cite="SimRISC-03 §格式转换指令"
    ))
    
    # foroot-orri, folog-orri
    records.append(create_record("foroot", "orri", misc_rf_op, ha=0x0E,
        fields=generate_orri_fields("rfhb", "rfhc", "immu6"),
        legality=[],
        wiki_cite="SimRISC-03 §S1D1"
    ))
    records.append(create_record("folog", "orri", misc_rf_op, ha=0x0F,
        fields=generate_orri_fields("rfhb", "rfhc", "immu6"),
        legality=[],
        wiki_cite="SimRISC-03 §S1D1"
    ))
    
    # ftadd-orrr, ftsub-orrr, ftmul-orrr, ftdiv-orrr, ftrem-orrr, ftsclb-orrr, ftsgnn-orrr, ftsgnj-orrr
    ft_ops = ["ftadd", "ftsub", "ftmul", "ftdiv", "ftrem", "ftsclb", "ftsgnn", "ftsgnj"]
    for i, mnem in enumerate(ft_ops):
        records.append(create_record(mnem, "orrr", misc_rf_op, ha=0x10 + i,
            fields=generate_orrr_fields("rfhb", "rfhc", "rfhd"),
            legality=["rfhb != rf0", "rfhc != rf0", "rfhd != rf0"],
            wiki_cite="SimRISC-03 §S2D1" if i < 6 else "SimRISC-03 §浮点符号位操作指令"
        ))
    
    # foadd-orrr, fosub-orrr, fomul-orrr, fodiv-orrr, forem-orrr, fosclb-orrr, fosgnn-orrr, fosgnj-orrr
    fo_ops = ["foadd", "fosub", "fomul", "fodiv", "forem", "fosclb", "fosgnn", "fosgnj"]
    for i, mnem in enumerate(fo_ops):
        records.append(create_record(mnem, "orrr", misc_rf_op, ha=0x18 + i,
            fields=generate_orrr_fields("rfhb", "rfhc", "rfhd"),
            legality=["rfhb != rf0", "rfhc != rf0", "rfhd != rf0"],
            wiki_cite="SimRISC-03 §S2D1" if i < 6 else "SimRISC-03 §浮点符号位操作指令"
        ))
    
    # ftqcmp-orrr, ftscmp-orrr
    records.append(create_record("ftqcmp", "orrr", misc_rf_op, ha=0x20,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rdhb", "[17:12]", "dst", "rd"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rdhb != rd0", "rfhc != rf0", "rfhd != rf0"],
        wiki_cite="SimRISC-03 §浮点比较指令"
    ))
    records.append(create_record("ftscmp", "orrr", misc_rf_op, ha=0x21,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rdhb", "[17:12]", "dst", "rd"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rdhb != rd0", "rfhc != rf0", "rfhd != rf0"],
        wiki_cite="SimRISC-03 §浮点比较指令"
    ))
    
    # foqcmp-orrr, foscmp-orrr
    records.append(create_record("foqcmp", "orrr", misc_rf_op, ha=0x28,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rdhb", "[17:12]", "dst", "rd"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rdhb != rd0", "rfhc != rf0", "rfhd != rf0"],
        wiki_cite="SimRISC-03 §浮点比较指令"
    ))
    records.append(create_record("foscmp", "orrr", misc_rf_op, ha=0x29,
        fields=[
            create_field("ha", "[23:18]", "minor_op", "imm"),
            create_field("rdhb", "[17:12]", "dst", "rd"),
            create_field("rfhc", "[11:6]", "src", "rf"),
            create_field("rfhd", "[5:0]", "src", "rf")
        ],
        legality=["rdhb != rd0", "rfhc != rf0", "rfhd != rf0"],
        wiki_cite="SimRISC-03 §浮点比较指令"
    ))
    
    # ft2it-orri, ft2io-orri, ft2ut-orri, ft2uo-orri, it2ft-orri, io2ft-orri, ut2ft-orri, uo2ft-orri
    ft2it_ops = ["ft2it", "ft2io", "ft2ut", "ft2uo", "it2ft", "io2ft", "ut2ft", "uo2ft"]
    for i, mnem in enumerate(ft2it_ops):
        if i < 4:
            # ft2xx: rf -> rd
            records.append(create_record(mnem, "orri", misc_rf_op, ha=0x30 + i,
                fields=generate_orri_fields("rdhb", "rfhc", "immu6"),
                legality=["rdhb != rd0", "rfhc != rf0"],
                wiki_cite="SimRISC-03 §格式转换指令"
            ))
        else:
            # xx2ft: rd -> rf
            records.append(create_record(mnem, "orri", misc_rf_op, ha=0x30 + i,
                fields=generate_orri_fields("rfhb", "rdhc", "immu6"),
                legality=["rfhb != rf0"],
                wiki_cite="SimRISC-03 §格式转换指令"
            ))
    
    # fo2it-orri, fo2io-orri, fo2ut-orri, fo2uo-orri, it2fo-orri, io2fo-orri, ut2fo-orri, uo2fo-orri
    fo2it_ops = ["fo2it", "fo2io", "fo2ut", "fo2uo", "it2fo", "io2fo", "ut2fo", "uo2fo"]
    for i, mnem in enumerate(fo2it_ops):
        if i < 4:
            # fo2xx: rf -> rd
            records.append(create_record(mnem, "orri", misc_rf_op, ha=0x38 + i,
                fields=generate_orri_fields("rdhb", "rfhc", "immu6"),
                legality=["rdhb != rd0", "rfhc != rf0"],
                wiki_cite="SimRISC-03 §格式转换指令"
            ))
        else:
            # xx2fo: rd -> rf
            records.append(create_record(mnem, "orri", misc_rf_op, ha=0x38 + i,
                fields=generate_orri_fields("rfhb", "rdhc", "immu6"),
                legality=["rfhb != rf0"],
                wiki_cite="SimRISC-03 §格式转换指令"
            ))
    
    # 输出 YAML
    with open("verif/opcodes.yaml", "w", encoding="utf-8") as f:
        f.write("# SimRISC 0.5.3 指令编码表\n")
        f.write("# 自动生成自 wiki 规范文档\n")
        f.write(f"# 共 {len(records)} 条指令\n\n")
        yaml.dump(records, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"生成完成：{len(records)} 条指令")

if __name__ == "__main__":
    main()