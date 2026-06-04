# 翻訳手順

```bash
cd tools/japanese-font-prototype
```

## 1. 辞書を編集した場合のみ: 翻訳再生成 + ja.lua マージ

```bash
.venv/Scripts/python.exe translate_ui.py
```

 (マージは前回コマンドの inline Python を再実行)

## 2. 必須: フォント再生成（ja.lua から新文字を自動抽出）

```bash
cd ../../
PYTHONIOENCODING=utf-8 python tools/japanese-font-prototype/gen_japanese_font.py --name "Liberation Sans" --all-fonts
```

## 3. PoB を閉じてフォント配置

```bash
cp -f tools/japanese-font-prototype/output/* runtime/SimpleGraphic/Fonts/
```
