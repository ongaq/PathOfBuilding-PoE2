"""
日本語ビットマップフォント生成プロトタイプ

PoB の SimpleGraphic ランタイムが使用する .tgf + .tga フォーマット仕様で
日本語グリフを含むフォントを生成する。

ファイル仕様（既存フォントから逆解析）:
  .tgf: テキスト形式、複数 HEIGHT セクション (HEIGHT 10/12/14/16/18/20/22/24/26/28/32/36/40/48/56/64)
        各セクション内に `GLYPH x y w sl sr; // index (char)` 行
  .tga: 32bpp RGBA、image_type 10 (RLE) または 2 (uncompressed)、白色グリフ

注意:
  現状の SimpleGraphic.dll は glyphs[128] の固定配列で 7-bit ASCII 範囲のみ対応。
  本スクリプトが生成する Unicode コードポイントを使う .tgf は、
  レンダラ側 (engine/render/r_font.cpp) を改修した SimpleGraphic.dll でのみ使用可能。
  詳細は FINDINGS.md を参照。
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# SimpleGraphic の既存フォントが備えるサイズ群
FONT_SIZES = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32, 36, 40, 48, 56, 64]

# 必ず含めるベース文字セット (ASCII + ひらがな + カタカナ + 主要記号)
BASE_CHARSET = (
    "".join(chr(i) for i in range(32, 127))     # ASCII印字可能
    + "".join(chr(i) for i in range(0x3041, 0x3097))  # ひらがな
    + "".join(chr(i) for i in range(0x30A1, 0x30FB))  # カタカナ
    + "、。「」『』・ー※→←↑↓〜"                       # 主要記号
)


def collect_chars_from_lang_files(lang_dir: Path) -> set[str]:
    """src/Data/Lang/*.lua から使われている全 CJK 文字を抽出する。

    翻訳テーブルの値（日本語）に登場する全ての非 ASCII 文字を集めることで、
    既存翻訳に必要なグリフを過不足なくフォントに含める。
    """
    chars: set[str] = set()
    if not lang_dir.exists():
        return chars
    for lua_file in lang_dir.glob("*.lua"):
        text = lua_file.read_text(encoding="utf-8")
        for ch in text:
            cp = ord(ch)
            # ASCII以外、かつ制御文字以外
            if cp > 0x7F and cp != 0xFEFF:
                chars.add(ch)
    return chars


def measure_glyph(font: ImageFont.FreeTypeFont, ch: str) -> tuple[int, int, int, int]:
    """グリフの (描画幅, 左余白, 右余白, advance) を取得。"""
    bbox = font.getbbox(ch)
    left, top, right, bottom = bbox
    width = max(right - left, 1)
    advance = int(font.getlength(ch))
    sl = max(left, 0)
    sr = max(advance - right, 0)
    return width, sl, sr, advance


def pack_glyphs(
    chars: str, font: ImageFont.FreeTypeFont, pixel_height: int, atlas_size: int,
    y_offset: int = 0
) -> tuple[Image.Image, list[dict]]:
    """グリフをアトラスにシェルフ詰めで配置。

    y_offset: 行頂上からのオフセット (TTFサイズが小さい時、行内で中央寄せするのに使う)
    """
    row_height = pixel_height + 2  # 既存フォント観察値: 行間 +2px
    atlas = Image.new("RGBA", (atlas_size, atlas_size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(atlas)

    placements: list[dict] = []
    cur_x = 0
    cur_y = 0
    for ch in chars:
        w, sl, sr, _adv = measure_glyph(font, ch)
        if cur_x + w + 1 > atlas_size:
            cur_x = 0
            cur_y += row_height
            if cur_y + pixel_height > atlas_size:
                # アトラスからあふれた分はスキップ（プロトタイプではログのみ）
                print(f"  [WARN] atlas full at U+{ord(ch):04X}, skipping rest")
                break

        # 白色不透明でグリフを描画 (PoB は SetDrawColor で着色する想定)
        # y_offset で行内位置を調整 (TTFサイズを縮めた場合の中央寄せ用)
        draw.text((cur_x, cur_y + y_offset), ch, font=font, fill=(255, 255, 255, 255))
        placements.append(
            {
                "codepoint": ord(ch),
                "char": ch,
                "x": cur_x,
                "y": cur_y,
                "w": w,
                "sl": sl,
                "sr": sr,
            }
        )
        cur_x += w + 1
    return atlas, placements


def write_tga_uncompressed(image: Image.Image, path: Path) -> None:
    """Type 2 (非圧縮) 32bpp RGBA TGA を書き出す。"""
    # Pillow の TGA セーバは type 10 (RLE) を出すが、より単純な type 2 で出力する
    # → stb_image / 一般的 TGA リーダの両方で読める
    width, height = image.size
    pixels = image.tobytes("raw", "BGRA")  # TGA は BGRA バイト順
    header = bytes(
        [
            0,  # ID length
            0,  # ColorMap type
            2,  # ImageType: uncompressed truecolor
            0, 0, 0, 0, 0,  # ColorMap spec (unused)
            0, 0,  # X origin
            0, 0,  # Y origin
            width & 0xFF, (width >> 8) & 0xFF,
            height & 0xFF, (height >> 8) & 0xFF,
            32,  # Pixel depth
            0x28,  # Image descriptor: bits 0-3 alpha=8, bit5 top-left origin
        ]
    )
    path.write_bytes(header + pixels)


def write_tgf(
    sections: list[tuple[int, list[dict]]], path: Path, *, by_codepoint: bool
) -> None:
    """.tgf を書き出す。

    by_codepoint=True: 拡張形式 (GLYPH cp x y w sl sr) でコードポイント明示。
                       パッチ済み SimpleGraphic (codepoint-keyed map) が必須。
    by_codepoint=False: 旧形式 (GLYPH x y w sl sr) で出現順=コードポイント。
                        ASCII 範囲 (0-127) のみ対応の既存バイナリ互換。
    """
    lines: list[str] = []
    if by_codepoint:
        lines.append("# Extended TGF: each GLYPH starts with Unicode codepoint")
        lines.append("# Format: GLYPH codepoint x y width spacingLeft spacingRight;")
        lines.append("# Requires patched SimpleGraphic.dll (codepoint-keyed glyph map)")
        lines.append("")
    for height, placements in sections:
        lines.append(f"HEIGHT {height};")
        for p in placements:
            cp = p["codepoint"]
            ch_repr = p["char"] if 0x20 <= cp < 0x7F else f"U+{cp:04X}"
            if by_codepoint:
                lines.append(
                    f"GLYPH {cp:5d} {p['x']:4d} {p['y']:4d} {p['w']:3d} {p['sl']:2d} {p['sr']:2d}; "
                    f"// {ch_repr}"
                )
            else:
                lines.append(
                    f"GLYPH {p['x']:4d} {p['y']:4d} {p['w']:3d} {p['sl']:2d} {p['sr']:2d}; "
                    f"// {cp} ({ch_repr})"
                )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="日本語ビットマップフォント生成")
    parser.add_argument("--name", default="NotoSansJP",
                        help="出力ファイル名のプレフィックス。例: 'Liberation Sans' で既存フォントを置換可能")
    parser.add_argument("--ttf", default="C:/Windows/Fonts/NotoSansJP-VF.ttf",
                        help="入力TTFパス（存在しなければ msgothic.ttc にフォールバック）")
    parser.add_argument("--lang-dir", default="../../src/Data/Lang",
                        help="翻訳ファイル群のディレクトリ。ここから使用文字を自動抽出")
    parser.add_argument("--ttf-size-offset", type=int, default=2,
                        help="TTF描画サイズを HEIGHT より N ピクセル小さく描く (日本語が大きく見えるのを補正)")
    parser.add_argument("--all-fonts", action="store_true",
                        help="PoB が使う全7フォント (Liberation Sans / Liberation Sans Bold / "
                             "Bitstream Vera Sans Mono / Fontin / Fontin Italic / Fontin SmallCaps / "
                             "Fontin SmallCaps Italic) を一括生成。--name は無視される")
    args = parser.parse_args()

    ttf_path = Path(args.ttf)
    if not ttf_path.exists():
        ttf_path = Path("C:/Windows/Fonts/msgothic.ttc")
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)

    # 翻訳ファイルから使用文字を抽出
    lang_dir = (Path(__file__).parent / args.lang_dir).resolve()
    lang_chars = collect_chars_from_lang_files(lang_dir)

    # 重複排除しつつ ASCII ベース → 翻訳由来文字 の順で連結
    seen: set[str] = set()
    combined: list[str] = []
    for ch in BASE_CHARSET:
        if ch not in seen:
            seen.add(ch)
            combined.append(ch)
    # 翻訳由来でベース未収録の文字を追加（コードポイント順で安定化）
    for ch in sorted(lang_chars, key=ord):
        if ch not in seen:
            seen.add(ch)
            combined.append(ch)
    charset = "".join(combined)

    print(f"日本語フォント生成プロトタイプ")
    print(f"  出力名: {args.name}")
    print(f"  TTF: {ttf_path}")
    print(f"  ベース文字数: {len(BASE_CHARSET)}")
    print(f"  翻訳由来追加文字: {len(lang_chars - set(BASE_CHARSET))} ({lang_dir})")
    print(f"  合計文字数: {len(charset)}")
    print()

    sections: list[tuple[int, list[dict]]] = []
    for height in FONT_SIZES:
        # アトラスサイズ: 1500 グリフ規模を想定して各サイズで十分余裕を取る
        # 経験則:
        #   HEIGHT 10/12: 1500 グリフ × 約12px幅 → 18000px → 512px だと 35行 = 余裕
        #   HEIGHT 14: 14px幅で 1500 → 21000px → 512だと厳しい (実測 OOM) → 1024
        #   HEIGHT 16-28: 1024 で十分か中サイズ境界。28 でも OOM 報告あり → 2048
        #   HEIGHT 32-: 2048 必須
        #   HEIGHT 56/64: 2048 でも溢れる場合あり → 4096 (GL_MAX_TEXTURE_SIZE 要確認)
        if height >= 56:
            atlas_size = 4096
        elif height >= 26:
            atlas_size = 2048
        elif height >= 14:
            atlas_size = 1024
        else:
            atlas_size = 512
        # 日本語フォントは Latin フォントより視覚的に大きく見えるため、TTF サイズを少し縮める
        ttf_size = max(height - args.ttf_size_offset, 6)
        y_offset = (height - ttf_size) // 2  # 行内中央寄せ
        font = ImageFont.truetype(str(ttf_path), ttf_size)
        atlas, placements = pack_glyphs(charset, font, height, atlas_size, y_offset=y_offset)

        tga_path = out_dir / f"{args.name}.{height}.tga"
        write_tga_uncompressed(atlas, tga_path)
        sections.append((height, placements))
        print(
            f"  HEIGHT {height:2d}: {len(placements):4d}グリフ → "
            f"{tga_path.name} ({tga_path.stat().st_size // 1024}KB, {atlas_size}x{atlas_size})"
        )

    tgf_path = out_dir / f"{args.name}.tgf"
    write_tgf(sections, tgf_path, by_codepoint=True)

    # --all-fonts 指定時、生成済みの .tgf/.tga を全フォント名にコピー
    # 視覚的差別化（Bold/Italic/SmallCaps）は失われるが、tofu は完全に消える
    if args.all_fonts:
        import shutil
        all_font_names = [
            "Liberation Sans",
            "Liberation Sans Bold",
            "Bitstream Vera Sans Mono",
            "Fontin",
            "Fontin Italic",
            "Fontin SmallCaps",
            "Fontin SmallCaps Italic",
        ]
        print()
        print(f"  --all-fonts: '{args.name}' を全7フォント名にコピー")
        for other_name in all_font_names:
            if other_name == args.name:
                continue
            # tgf
            shutil.copy(tgf_path, out_dir / f"{other_name}.tgf")
            # 全サイズのtga
            for height in FONT_SIZES:
                src_tga = out_dir / f"{args.name}.{height}.tga"
                dst_tga = out_dir / f"{other_name}.{height}.tga"
                shutil.copy(src_tga, dst_tga)
            print(f"    → {other_name}.tgf + 16 tga ファイル")
    print()
    print(f"  メタデータ: {tgf_path.name} ({tgf_path.stat().st_size // 1024}KB)")
    print()
    print("生成完了。FINDINGS.md でレンダラ改修案を確認のこと。")


if __name__ == "__main__":
    main()
