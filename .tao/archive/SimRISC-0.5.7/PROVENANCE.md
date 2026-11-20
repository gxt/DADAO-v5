# SimRISC 0.5.7 归档来源

- 版本：`0.5.7`
- 来源仓库：本仓
- 快照提交：`7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f`（台账：m15-spec-009 移入进行中（派单））
- 首次标记提交：`00cccbe0db6173889a5c6017431ce745b582741c`（2026-11-20）
- 文件数：13
- 版本组合 sha256：`7932333220c14214cacd478754385ce525cccb5fd72b641123d20b11e1005baa`

## 逐文件 sha256

```
5668be5b7c810b18dc7a5b00a932bc1a79d1cc5f57a9e2e8ebc3933e190b7659  SimRISC-00-指令系统设计.md
cfdd2142123d6dc3880e86ae7f950bdfa20d78b4c22c9f3b1b3537cf876b54ea  SimRISC-01-取数存数.md
9b6be17e88ffbd3473495635d4444ab89195889dd0d90e6be0b34092b5562e15  SimRISC-02-寄存器复制.md
5262c935f7f9b4781f6bed8ec22dba72be0e1d61e419e4ad7344ad3cead7a775  SimRISC-03-16位立即数操作.md
202682455b840b11ea465b89383723a9fca5065e8bf8b73d5bff2df9d8e0911a  SimRISC-04-64位数据运算.md
c0b5fc2275c7eb829a302ff7df4b7f0f9f2259f7c48279bc72b4b5e62057bab9  SimRISC-05-64位地址运算.md
e1ee3485efc9f500f5afeeb004bfab6eef8e884d2ef774bfbcb2d88da9f0d1f3  SimRISC-06-控制流.md
68ff5c7a996fe2e71441a73ac84b027f8b331ccb8dc4c4dc8e1ad07a2877b101  SimRISC-07-浮点运算.md
1790fbf45c35414fddce95c2fc719f975ae7533b880f219e103ee60b567eab89  SimRISC-08-32位数据运算.md
95f61b72fabdca5beccfbdade94bb69c8e893c23711e975e2631f621815d9754  SimRISC-09-16位数据运算.md
f803d3b4539179e339e1639ebd41d377d975c826b609bf6ebc962f19d9cc4d33  SimRISC-10-8位数据运算.md
61b848ed33bcd02ecfee70e181a198959106a945a2a804cfb4d461a1f6c2783a  SimRISC-11-核芯功能扩展指令.md
631a992df50dae1d13eac81ab1d20c7dcd84cc4c5dcb692f1a0b28e8ebf36fa4  SimRISC-12-其它指令.md
```

## 提取命令

```sh
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-00-指令系统设计.md > .tao/archive/SimRISC-0.5.7/SimRISC-00-指令系统设计.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-01-取数存数.md > .tao/archive/SimRISC-0.5.7/SimRISC-01-取数存数.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-02-寄存器复制.md > .tao/archive/SimRISC-0.5.7/SimRISC-02-寄存器复制.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-03-16位立即数操作.md > .tao/archive/SimRISC-0.5.7/SimRISC-03-16位立即数操作.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-04-64位数据运算.md > .tao/archive/SimRISC-0.5.7/SimRISC-04-64位数据运算.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-05-64位地址运算.md > .tao/archive/SimRISC-0.5.7/SimRISC-05-64位地址运算.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-06-控制流.md > .tao/archive/SimRISC-0.5.7/SimRISC-06-控制流.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-07-浮点运算.md > .tao/archive/SimRISC-0.5.7/SimRISC-07-浮点运算.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-08-32位数据运算.md > .tao/archive/SimRISC-0.5.7/SimRISC-08-32位数据运算.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-09-16位数据运算.md > .tao/archive/SimRISC-0.5.7/SimRISC-09-16位数据运算.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-10-8位数据运算.md > .tao/archive/SimRISC-0.5.7/SimRISC-10-8位数据运算.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-11-核芯功能扩展指令.md > .tao/archive/SimRISC-0.5.7/SimRISC-11-核芯功能扩展指令.md
git show 7bf88240ae9d89eacfadc2f680c46df8fc3fcd5f:spec/SimRISC-12-其它指令.md > .tao/archive/SimRISC-0.5.7/SimRISC-12-其它指令.md
```

> 归档为**只读历史快照**：不参与 `spec/` 门控扫描；引用方须指向本目录，不得改写内容。
