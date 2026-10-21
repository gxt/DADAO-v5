# SimRISC 0.5.5-rc 归档来源

- 版本：`0.5.5-rc`
- 来源仓库：本仓
- 快照提交：`a04d34ee5247492c649dc14bbc6b60cfc5912795`（SPEC-153t 验收收尾（reviewer 两轮 Accepted）：原子指令 §3 整章 94 行迁入 SimRISC-11 §6，S12 删除重编号；计数 30/2、excluded 27；生成器 classify() 收窄；指针 12 处 + 锁 sha；证据脚本基线钉 4cbafbfc（含 C0 反例保证）；tests/** 陈旧引用 162 处登记 ISS-316）
- 首次标记提交：`0f7691004f98e64bd00651ca51d3f313a7e9e9d4`（2026-10-12）
- 文件数：13
- 版本组合 sha256：`a0a27cbc2b0a14b3448512b2bc94714c3e7ce60e1e8211cfe987cf8dd1611817`

## 逐文件 sha256

```
0255349e9a414f8c8288ea7dd71515ccc3342d77bb07e0e7a266da7066f73ad6  SimRISC-00-指令系统设计.md
0b142635e462c2bc774630434d54da578e06d3965fb8009d88cc308f0fa54f1f  SimRISC-01-取数存数.md
ecce63bea40283e9067b4dde7de89b29cbc436ca056c54668e42641e4d29b1d2  SimRISC-02-寄存器复制.md
c03444f87b91329eefaaff358cf239c89d02ca9eed254ca61d6f93f545214784  SimRISC-03-16位立即数操作.md
b32ba9e9122d1efda85aa67c56716618b80cfa6115fd5308cf818028c9c64ba7  SimRISC-04-64位数据运算.md
20c240bf30f7d396d4c0e0181ca3cd0cac7e49f1230887a489dce2e98543c80b  SimRISC-05-64位地址运算.md
a26f50d753b454f1c8c58b680a1531e675fcc5fe3cbce3950503baccea14ed3b  SimRISC-06-控制流.md
bd405979d2bd484d861e914a4f9fe0a67fb3c405f7026dc443f361b1110843fa  SimRISC-07-浮点运算.md
1ad7782728fbd3066dbf4ed791a3e0996bf768fcc614dac966ea29110a959cff  SimRISC-08-32位数据运算.md
61c01aaeab8acd3b678379f86266af8c2d56d3f3033ff91bc870f9db25bbf8da  SimRISC-09-16位数据运算.md
13c7b6df5958be43661a59154296f0c2bf33013133da770b42e109fd9c37e593  SimRISC-10-8位数据运算.md
db889e3e53af1fbf5ac6b719b945dca885723f199f782a7ec218801d31539dd6  SimRISC-11-其它.md
f36c77523c877a21c74448e9693e2b6f6d690e50dc406cddd94437ed13be1ddd  SimRISC-12-待定.md
```

## 提取命令

```sh
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-00-指令系统设计.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-00-指令系统设计.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-01-取数存数.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-01-取数存数.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-02-寄存器复制.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-02-寄存器复制.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-03-16位立即数操作.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-03-16位立即数操作.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-04-64位数据运算.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-04-64位数据运算.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-05-64位地址运算.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-05-64位地址运算.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-06-控制流.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-06-控制流.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-07-浮点运算.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-07-浮点运算.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-08-32位数据运算.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-08-32位数据运算.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-09-16位数据运算.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-09-16位数据运算.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-10-8位数据运算.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-10-8位数据运算.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-11-其它.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-11-其它.md
git show a04d34ee5247492c649dc14bbc6b60cfc5912795:spec/SimRISC-12-待定.md > .tao/archive/SimRISC-0.5.5-rc/SimRISC-12-待定.md
```

> 归档为**只读历史快照**：不参与 `spec/` 门控扫描；引用方须指向本目录，不得改写内容。
