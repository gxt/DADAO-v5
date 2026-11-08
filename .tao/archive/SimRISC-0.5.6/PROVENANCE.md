# SimRISC 0.5.6 归档来源

- 版本：`0.5.6`
- 来源仓库：本仓
- 快照提交：`9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1`（SPEC-196t: 合入 SimRISC 0.5.6 发布（已验证））
- 首次标记提交：`9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1`（2026-11-09）
- 文件数：13
- 版本组合 sha256：`95f166af8d4a87d999fd01bdfc7fe60f11db5d205994fd1699e1317383bd6317`

## 逐文件 sha256

```
ab73f39345c4fe210aa0a059937b1bbad60b5f99019f1edb73190432820642d1  SimRISC-00-指令系统设计.md
edf6b85bf1138d11cdd6055fb25c2c69003acf8c5c9a467365bad5d82fd98a27  SimRISC-01-取数存数.md
d98644be70274bc4041ea69c316391cb09dfcad1d1edb381899b18e96e5e166a  SimRISC-02-寄存器复制.md
6c541a4ff147cd6b7e92baffce66d9c5744c90b82f166711b1d50af0047c9ddb  SimRISC-03-16位立即数操作.md
2b2f5eba1e6b78f7ebbc958f356ba57df0ab27b9cc369e78126ed75be818ef98  SimRISC-04-64位数据运算.md
a8d60c9f452be5c34ac44cdbce906872243b4f327dda5e69611f59df2444bd60  SimRISC-05-64位地址运算.md
c24b0577fc1307b8b9aa912bc6e6a54f1ba95ae6f8232028d29d8b711bf40ffb  SimRISC-06-控制流.md
24ef3c324adbd212d906fe829b97b11673ea88f0ced0aaf8b3aeb3a2520ba70e  SimRISC-07-浮点运算.md
96b8e4050b6eb3c97fc74e54ab09aa9f0949fe482ab460524a5cfbc6c0ef3b7f  SimRISC-08-32位数据运算.md
8bbc712b0cbff5e94cb65ae32d0ec5f3aa874f4a963fdc7d0b962281801a28b7  SimRISC-09-16位数据运算.md
2a4d83b1402f72f7739c0fa9c3c70ba7ff7330f6a645b45cdae9d9fd07ea5b3d  SimRISC-10-8位数据运算.md
b5b1fa8f2442ee90e5c51902de695cd2c4d6fc8c058f70d79d49c0eaef3a8746  SimRISC-11-核芯功能扩展指令.md
2657e237bcfd4b5572aa20b1434d9cbaf2a4f97fbb8bd4bb3cb802c0c8e65f13  SimRISC-12-其它指令.md
```

## 提取命令

```sh
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-00-指令系统设计.md > .tao/archive/SimRISC-0.5.6/SimRISC-00-指令系统设计.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-01-取数存数.md > .tao/archive/SimRISC-0.5.6/SimRISC-01-取数存数.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-02-寄存器复制.md > .tao/archive/SimRISC-0.5.6/SimRISC-02-寄存器复制.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-03-16位立即数操作.md > .tao/archive/SimRISC-0.5.6/SimRISC-03-16位立即数操作.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-04-64位数据运算.md > .tao/archive/SimRISC-0.5.6/SimRISC-04-64位数据运算.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-05-64位地址运算.md > .tao/archive/SimRISC-0.5.6/SimRISC-05-64位地址运算.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-06-控制流.md > .tao/archive/SimRISC-0.5.6/SimRISC-06-控制流.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-07-浮点运算.md > .tao/archive/SimRISC-0.5.6/SimRISC-07-浮点运算.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-08-32位数据运算.md > .tao/archive/SimRISC-0.5.6/SimRISC-08-32位数据运算.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-09-16位数据运算.md > .tao/archive/SimRISC-0.5.6/SimRISC-09-16位数据运算.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-10-8位数据运算.md > .tao/archive/SimRISC-0.5.6/SimRISC-10-8位数据运算.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-11-核芯功能扩展指令.md > .tao/archive/SimRISC-0.5.6/SimRISC-11-核芯功能扩展指令.md
git show 9e9a9c3d38cf2d2fb028196f8cf6bc91794298d1:spec/SimRISC-12-其它指令.md > .tao/archive/SimRISC-0.5.6/SimRISC-12-其它指令.md
```

> 归档为**只读历史快照**：不参与 `spec/` 门控扫描；引用方须指向本目录，不得改写内容。
