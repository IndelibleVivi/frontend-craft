# Font material continuation / 字体材料接续

This is a technical font specimen and a real production derivative. It is not a
showcase, a recommended visual style, or evidence of autonomous design quality.
Open [the specimen](index.html) through the root's local HTTP server to inspect
Chinese, punctuation, mixed scripts and the retained weight axis.

这是实际字体产物与技术样张。它覆盖固定样本文字；新文案必须从准确原字体重建，
不能在旧 subset 上补不存在的字。它不代表已认可风格或自主 FC 制作效果。

- [ASSETS.json](ASSETS.json) identifies the pinned original, its SHA-256, output,
  text input and tested fontTools version. The original is deliberately not
  bundled; obtain it from the linked official Google Fonts revision when needed.
- [specimen.txt](specimen.txt) is the complete UTF-8 subset input.
- [noto-sans-sc-specimen.woff2](noto-sans-sc-specimen.woff2) retains the `wght`
  axis (100–900) and only this specimen's Unicode coverage.
- The font retains its [SIL Open Font License](OFL-NotoSansSC.txt); FC's code and
  documentation terms do not replace it.

The [catalog](catalog.json) records the original and derivative separately.
From the FC package root:

```bash
python3 scripts/fc_catalog.py query --catalog examples/materials/catalog.json --role material --language zh-CN
python3 scripts/fc_catalog.py resolve --catalog examples/materials/catalog.json --id noto-sans-sc-specimen --root fc-material-samples:package=.
```

The WOFF2/text/recipe/license are local. The original reports `remote-only`;
resolution never downloads it. The `package` root names the helper's source,
so a moved checkout can explicitly rebind that root without changing identity.

To reproduce or extend, save the linked original as `/work/materials/title.ttf`,
copy/edit the text input in the project, and run the
[font helper](../../references/material-production.md#fonts-inspect-subset-and-rebuild-when-text-changes)
into a fresh output directory. Check the original digest against `ASSETS.json`
before claiming this exact derivation. Keep the helper's manifest with that
project's source and register source/output separately in its catalog. The
packaged asset record omits machine-specific paths from the local manifest.

核对原物、修改字符输入、生成新版本、实际浏览器检查后，再更新项目采用项。登记和
解析操作见 [catalog runbook](../../references/catalog-operations.md)。字体文件可读与
加载成功不等于审美成立，样张也不证明复杂文字塑形或所有浏览器兼容性。
