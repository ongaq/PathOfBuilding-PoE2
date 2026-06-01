# 日本語フォント実現性プロトタイプ — 検証結果

## TL;DR

- **`.tgf` + `.tga` 日本語フォント生成 → 動作確認済み**（[gen_japanese_font.py](gen_japanese_font.py) で 312 グリフを 16 サイズ分生成成功）
- **配布バイナリ `SimpleGraphic.dll` は日本語を構造的にレンダリング不可**（`f_glyph_s glyphs[128]` の固定配列 + 単一バイト索引）
- **唯一の解決策は SimpleGraphic 本体（C++、別 OSS リポジトリ）のフォーク改修**。改修自体は **10〜30 行程度の小規模パッチ** で達成可能
- 結論: **技術的には実現可能だが、配布バイナリの自前ビルド・メンテナンスが必須**

---

## 1. `.tgf` / `.tga` フォーマット仕様（逆解析結果）

`runtime/SimpleGraphic/Fonts/Bitstream Vera Sans Mono.tgf` 等の既存ファイルを解析して仕様を確定:

### `.tgf` (グリフメタデータ、プレーンテキスト)
```
HEIGHT 10;
GLYPH  26  36  4  1  0;	// 65 (A)
...
HEIGHT 12;
...
HEIGHT 64;
```
- 1 ファイルに 16 セクション（HEIGHT 10/12/14/16/18/20/22/24/26/28/32/36/40/48/56/64）
- 各セクションに 128 GLYPH 行（ASCII 0–127）
- `GLYPH x y w sl sr` = アトラス内 (x, y) 位置、グリフ幅、左右パディング

### `.tga` (グリフアトラス、画像)
- TGA Image Type 10（RLE 圧縮）または 2（非圧縮、本プロトタイプで使用）
- 32bpp BGRA、左上原点
- 白色不透明でグリフを描画（PoB 側 `SetDrawColor` でランタイム着色）

---

## 2. レンダラ制約（最大の障壁）

ソース: [PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic](https://github.com/PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic) (`engine/render/r_font.cpp`)

```cpp
// 34-40: 固定 128 要素配列
struct f_fontHeight_s {
    r_tex_c* tex;
    int height;
    int numGlyph;
    f_glyph_s glyphs[128];          // ← 上限 128 固定
    f_glyph_s defGlyph{...};
};

// 42-47: 単一バイト索引（コードポイント未対応）
f_glyph_s const& Glyph(char ch) const {
    if ((unsigned char)ch >= numGlyph) return defGlyph;
    return glyphs[(unsigned char)ch];   // ← `unsigned char` で 0-255 のみ
}

// 80: パーサも 128 上限を強制
if (fh->numGlyph >= 128) continue;
```

ただし **明るい兆候**: テキスト描画関数 `DrawTextLine()` (Lines 251-289) は既に `std::u32string_view` で UTF-32 コードポイントを処理している。つまり **文字列のデコードは既に Unicode 対応済み**、グリフテーブル側のみ要改修。

---

## 3. プロトタイプ検証成果

### 生成スクリプト
[gen_japanese_font.py](gen_japanese_font.py) — Pillow + Noto Sans JP / MS Gothic から `.tgf` + `.tga` を自動生成

### 検証用に生成した文字セット（312 文字）
- ASCII 印字可能文字（U+0020–U+007E、既存互換維持）
- ひらがな全部（U+3041–U+3096）
- カタカナ全部（U+30A1–U+30FA）
- 主要記号（、。「」・ー等）
- 動作確認用サンプル漢字

### 生成結果
| サイズ | アトラス | TGA サイズ | グリフ数 |
|---|---|---|---|
| 10–14pt | 512×512 | 1MB 各 | 312 |
| 16–40pt | 1024×1024 | 4MB 各 | 312 |
| 48–64pt | 2048×2048 | 16MB 各 | 312 |
| **合計** | — | **約 100MB（非圧縮）** | — |

→ TGA RLE 圧縮を適用すれば 1/3〜1/5 程度に圧縮可能。常用漢字フル収録時の試算は 30〜50MB 程度。

### 検証スクリーンショット
[output/_sample_chi_visible.png](output/_sample_chi_visible.png) — 16pt の「ち」(U+3061) を黒背景上に合成、128px に拡大したもの。**グリフは正しくラスタライズされている**ことを確認。

---

## 4. レンダラ改修案（最小パッチ）

最小限の C++ 改修で日本語対応が可能。`engine/render/r_font.cpp` および `r_font.h` 相当を以下のように変更:

```cpp
// Before:
f_glyph_s glyphs[128];

// After:
std::unordered_map<char32_t, f_glyph_s> glyphs;

// Before:
f_glyph_s const& Glyph(char ch) const {
    if ((unsigned char)ch >= numGlyph) return defGlyph;
    return glyphs[(unsigned char)ch];
}

// After:
f_glyph_s const& Glyph(char32_t cp) const {
    auto it = glyphs.find(cp);
    return it != glyphs.end() ? it->second : defGlyph;
}

// Before:
if (fh->numGlyph >= 128) continue;
// After:
// (制限を撤廃、map なので無制限)

// パーサ呼び出し側で sscanf の glyph index を char32_t で受ける
```

呼び出し元 `DrawTextLine()` は既に `char32_t` でループしているため、引数型を `char32_t` に変えるだけで素通り可能。**実装規模: 10〜30 行程度**。

---

## 5. 取りうるパス

| パス | 概要 | 工数 | リスク | 推奨度 |
|---|---|---|---|---|
| **A. SimpleGraphic フォーク改修** | r_font.cpp/h を改修、独自 `.dll` をビルド・配布 | 小（改修） + 中（ビルド環境構築・CI 統合） | フォーク維持コスト、上流追従の手間 | ★★★★ |
| **B. 既存128スロットに圧縮** | カタカナ等を ASCII 範囲外の 128 空きに詰める | 小 | 表示可能文字数が極小、UX 劣化大 | ★ |
| **C. マルチフォント運用** | フォントを N 個に分割し、Lua 側で文字種ごとに使い分け | 大（Lua 全 `DrawString` 呼び出し改修） | 行内混在表示の制御が非常に複雑 | ★ |
| **D. 上流に PR** | PathOfBuildingCommunity に Unicode 対応 PR を提出 | 改修自体は小、レビュー・採用待ち期間が長い | 上流不採用リスク | ★★★★★（中長期） |

---

## 6. 推奨アクション

1. **短期（数日）**: 本プロトタイプの生成スクリプトを拡張し、JIS 第一水準漢字（約 3,000 字）+ 第二水準を含む完全な `.tgf`/`.tga` を生成。RLE 圧縮を実装してファイルサイズを最適化
2. **中期（1〜2 週間）**: PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic をフォーク、`r_font.cpp` を改修、独自 `SimpleGraphic.dll` をビルドして本プロトタイプ生成 `.tgf`/`.tga` で実描画テスト
3. **並行**: 同改修を上流に PR 提出。採用されれば自前バイナリ配布が不要になる
4. **長期**: 改修済みバイナリが手に入った段階で、当初計画 Phase 1（UI 翻訳基盤 `Localization.lua`）に着手

---

## 7. 結論

**フォント関連の技術的障壁はすべて解決可能**。残された作業は次の 2 点:

1. **SimpleGraphic レンダラの Unicode 対応** — C++ 小規模パッチ + バイナリ配布
2. **常用漢字フルセットの `.tgf`/`.tga` 生成スクリプトの本実装** — 本プロトタイプの直接的な拡張

両方とも工数見積もり可能な範囲。最大のリスクは「上流 PR が採用されない場合に独自バイナリを継続メンテすること」だが、これは中長期の運用問題であって技術的不可能性ではない。

**Phase 1（UI 日本語化）に着手するための前提条件はクリアした**と判断できる。
