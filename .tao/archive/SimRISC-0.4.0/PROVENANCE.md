# SimRISC 0.4.0 归档来源

- 版本：`0.4.0`
- 来源仓库：.cache/refs/DADAO.wiki
- 快照提交：`c8861ecb1155fa9ddc84c8724abcae4a3d0a3de8`（set_ptbr_perm跳转表偏移×4→×8）
- 首次标记提交：`85ba32a3b4fb0093c15741f33e6a0d9d60e70536`（2026-06-27）
- wiki 锚点：`9f378f4426e131903d60a208766086ae74a53c89`
- 文件数：5
- 版本组合 sha256：`549f5ba963403380879d2ecba19a786fbd9cb324116968a8783d4cd10eb497a2`
- 文件名规范化：U+2010（`‐`）→ ASCII `-`，共 5 个

## 逐文件 sha256

```
5fda2be4ac3689146d84a1de949f4f3d0246b194d80f7c55540a6e825a652d3e  SimRISC-00-指令系统设计.md
84c0a1be547c1ad4ef1d442c525a0ceecd2da02646990b1424cc648ffcf874b9  SimRISC-01-数据类指令.md
434edb95200c76548b3aa462ac09bb34234548f70e50cb76800cd6fea33815f8  SimRISC-02-地址类指令.md
c91ccf63f2c8a11426586b5a56611d25ac22f6196541a50b747eab803d9bf478  SimRISC-03-浮点类指令.md
2fe22cf7ba9e14a7551cf81d31ab5adce18b3c2742a971d50386c3888450d78e  SimRISC-04-系统类指令.md
```

## 提取命令

```sh
git -C .cache/refs/DADAO.wiki show c8861ecb1155fa9ddc84c8724abcae4a3d0a3de8:SimRISC‐00‐指令系统设计.md > .tao/archive/SimRISC-0.4.0/SimRISC-00-指令系统设计.md
git -C .cache/refs/DADAO.wiki show c8861ecb1155fa9ddc84c8724abcae4a3d0a3de8:SimRISC‐01‐数据类指令.md > .tao/archive/SimRISC-0.4.0/SimRISC-01-数据类指令.md
git -C .cache/refs/DADAO.wiki show c8861ecb1155fa9ddc84c8724abcae4a3d0a3de8:SimRISC‐02‐地址类指令.md > .tao/archive/SimRISC-0.4.0/SimRISC-02-地址类指令.md
git -C .cache/refs/DADAO.wiki show c8861ecb1155fa9ddc84c8724abcae4a3d0a3de8:SimRISC‐03‐浮点类指令.md > .tao/archive/SimRISC-0.4.0/SimRISC-03-浮点类指令.md
git -C .cache/refs/DADAO.wiki show c8861ecb1155fa9ddc84c8724abcae4a3d0a3de8:SimRISC‐04‐系统类指令.md > .tao/archive/SimRISC-0.4.0/SimRISC-04-系统类指令.md
```

> 归档为**只读历史快照**：不参与 `spec/` 门控扫描；引用方须指向本目录，不得改写内容。
