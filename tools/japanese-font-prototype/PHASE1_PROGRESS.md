# Phase 1 (UI翻訳基盤) + SimpleGraphic フォーク 進捗

## 完了済み

### (B) SimpleGraphic フォーク + Unicode 対応パッチ

**ロケーション**: [tools/simplegraphic-fork/](../simplegraphic-fork/)

| ファイル | 変更内容 |
|---|---|
| [engine/render/r_font.cpp](../simplegraphic-fork/engine/render/r_font.cpp) | `glyphs[128]` → `unordered_map<char32_t, f_glyph_s>` / `Glyph(char)` → `Glyph(char32_t)` / 6パラメータ拡張形式 `.tgf` パーサ追加（後方互換） |
| [engine/render/r_font.h](../simplegraphic-fork/engine/render/r_font.h) | 変更なし（公開APIは不変） |
| [JAPANESE_PATCH.md](../simplegraphic-fork/JAPANESE_PATCH.md) | パッチ詳細・ビルド手順書 |

**残作業**:
- `git submodule update --init --recursive` でサブモジュール（vcpkg等）取得
- `cmake -B build -S . -A x64 -G "Visual Studio 17 2022" --toolchain "vcpkg\scripts\buildsystems\vcpkg.cmake"`
- VS2022で SimpleGraphic.dll をビルド + INSTALL ターゲット実行
- ビルドされた DLL を `runtime/SimpleGraphic.dll` に配置して動作確認
- 上流 [PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic](https://github.com/PathOfBuildingCommunity/PathOfBuilding-SimpleGraphic) への PR 提出を検討

### (C) Phase 1: UI翻訳基盤の構築

#### 新規ファイル
- [src/Modules/Localization.lua](../../src/Modules/Localization.lua) — i18n モジュール本体。`T()` グローバル関数、`localization:SetLanguage()`、言語別テーブルのキャッシュロード
- [src/Data/Lang/ja.lua](../../src/Data/Lang/ja.lua) — 日本語翻訳テーブル（初期 ~40 エントリ）

#### 変更済みファイル
- [src/Modules/Main.lua](../../src/Modules/Main.lua):
  - L19: `LoadModule("Modules/Localization")` 追加
  - L56-57: `main:Init` で初期化
  - L574-577: `LoadSettings` で `Misc.language` 属性を読み込み
  - L772: `SaveSettings` で `Misc.language` 属性を保存
  - L893-894: `OpenOptionsPopup` の `savedState` に `language` 追加
  - L982-994: 言語切替ドロップダウン追加
  - L1247-1249: Cancel ハンドラで言語を元に戻す処理追加
- [src/Modules/Build.lua](../../src/Modules/Build.lua):
  - L106, L113, L119: 上部バー「Back / Save / Save As」を `T()` 化
  - L318-353: モードボタン12個（Import/Export Build, Notes, Configuration, Tree, Skills, Items, Calcs, Party, Compare）を `T()` 化

## 動作（フォント未対応バイナリでの想定挙動）

現状の `SimpleGraphic.dll` のまま PoB を起動した場合:

1. ✅ Lua 側は問題なく動作（`T()` は文字列を返すだけなので副作用なし）
2. ✅ 言語ドロップダウンで「English」選択時は完全に従来通り
3. ⚠️ 言語ドロップダウンで「日本語」選択 + 訳語が存在する場合 → **`[U+xxxx]` 形式の tofu プレースホルダーが表示される**（描画は壊れないが文字は読めない）
4. ✅ 設定は `Settings.xml` の `Misc.language` 属性に永続化される
5. ✅ アイテム/スキル/mod パース処理は完全に英語のままで動作（影響なし）

## 検証方法

### Docker でテスト実行（Docker Desktop 要起動）
```bash
docker compose run --rm busted-tests
```

### 手動動作確認（フォント対応 DLL ビルド後）
1. パッチ済み `SimpleGraphic.dll` を `runtime/` に配置
2. 拡張形式の日本語 `.tgf` + `.tga` を `runtime/SimpleGraphic/Fonts/` に配置（[gen_japanese_font.py](gen_japanese_font.py) で生成可能）
3. `runtime/lua/Launch.lua` でフォント名を新しい日本語フォントに差し替え（`SetMainFont` 相当の場所、要調査）
4. PoB 起動 → Options → Language を「日本語」に設定
5. ビルドを開いて以下のラベルが日本語化されることを確認:
   - 「<< 戻る」「保存」「別名で保存」（上部バー）
   - 「ビルドの入出力」「メモ」「設定」「ツリー」「スキル」「アイテム」「計算」「パーティ」「比較」（モードボタン）
   - Options ダイアログの「言語」ラベル

## 次のステップ候補

1. **SimpleGraphic ビルド検証** — 実際にDLLをビルドして動作確認（ビルドにVS2022 + 数十分必要）
2. **翻訳カバレッジ拡大** — Build.lua以外の主要UI（CalcsTab、ItemsTab、SkillsTab、ConfigTab）を `T()` 化
3. **動的言語切替対応** — `label = function() return T("...") end` 形式に切り替え、再起動なしで切替可能にする
4. **Phase 2 着手** — `string.format` パターンとツールチップの翻訳
5. **フォント切替UI** — 言語選択に応じて自動的に対応フォント (`Bitstream Vera Sans Mono` ↔ `NotoSansJP`) を選ぶ仕組み
