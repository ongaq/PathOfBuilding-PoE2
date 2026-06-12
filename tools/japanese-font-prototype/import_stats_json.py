"""temp/{en,ja}/stats.json から id ペアでスタット翻訳を抽出。

- `#` プレースホルダが無いエントリ → ja.lua に exact match として追加
- `#` プレースホルダ有りで en/ja の `#` 数が一致 → ja_stats.lua にパターンとして書き出し
- `#` 数が一致しないものは破棄 (翻訳精度を担保できない)

ja_stats.lua の形式 (Localization.lua がロードして使う):
    return {
      { en = "+#% to Cold Resistance", ja = "+#% 冷気耐性" },
      ...
    }
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JA_LUA = ROOT / "src" / "Data" / "Lang" / "ja.lua"
JA_STATS = ROOT / "src" / "Data" / "Lang" / "ja_stats.lua"
EN_FILE = ROOT / "temp" / "en" / "stats.json"
JA_FILE = ROOT / "temp" / "ja" / "stats.json"


def walk(obj, acc):
    if isinstance(obj, dict):
        if "id" in obj and "text" in obj and isinstance(obj["text"], str):
            acc[obj["id"]] = obj["text"]
        for v in obj.values():
            walk(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, acc)


def lua_escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', r"\"")
        .replace("\n", r"\n")
        .replace("\r", r"\r")
        .replace("\t", r"\t")
    )


def parse_existing_keys(lua_text: str) -> set[str]:
    keys: set[str] = set()
    pat = re.compile(r'\["((?:[^"\\]|\\.)*)"\]\s*=')
    for m in pat.finditer(lua_text):
        keys.add(m.group(1).replace(r"\"", '"').replace(r"\\", "\\"))
    return keys


def main() -> None:
    en = json.loads(EN_FILE.read_text(encoding="utf-8"))
    ja = json.loads(JA_FILE.read_text(encoding="utf-8"))
    em, jm = {}, {}
    walk(en, em)
    walk(ja, jm)
    common = set(em) & set(jm)
    print(f"stats.json id 共通ペア: {len(common)}")

    exact: dict[str, str] = {}
    patterns: list[tuple[str, str]] = []
    skip_identical = 0
    skip_hash_mismatch = 0
    for k in common:
        e, j = em[k], jm[k]
        if e == j:
            skip_identical += 1
            continue
        if e.count("#") != j.count("#"):
            skip_hash_mismatch += 1
            continue
        if "#" in e:
            patterns.append((e, j))
        else:
            exact[e] = j
    print(f"  exact (# 無し): {len(exact)}")
    print(f"  patterns (# 有り): {len(patterns)}")
    print(f"  同一でスキップ: {skip_identical}")
    print(f"  # 数不一致でスキップ: {skip_hash_mismatch}")

    # --- ja.lua へ exact をマージ ---
    lua_text = JA_LUA.read_text(encoding="utf-8")
    existing = parse_existing_keys(lua_text)
    new_exact = {k: v for k, v in exact.items() if k not in existing}
    print(f"\nja.lua 既存: {len(existing)}  exact 新規: {len(new_exact)}")

    if new_exact:
        block = ["", "\t-- ============================================================",
                 "\t-- スタット由来 exact (temp/{en,ja}/stats.json, # 無し)",
                 "\t-- ============================================================"]
        for k in sorted(new_exact):
            block.append(f'\t["{lua_escape(k)}"] = "{lua_escape(new_exact[k])}",')
        block_str = "\n".join(block) + "\n"
        closing = "\n}\n"
        if lua_text.endswith(closing):
            new_lua = lua_text[: -len(closing)] + block_str + closing
        else:
            idx = lua_text.rfind("\n}")
            new_lua = lua_text[:idx] + block_str + lua_text[idx:]
        try:
            import lupa
            lua = lupa.LuaRuntime()
            t = lua.execute(new_lua)
            count = sum(1 for _ in t) if lupa.lua_type(t) == "table" else 0
            print(f"  ja.lua 構文 OK: 全 {count} エントリ")
        except ImportError:
            print("  [WARN] lupa 無しで構文検証スキップ")
        except Exception as e:
            print(f"  [ERR] Lua 構文エラー: {e}")
            raise SystemExit(1)
        JA_LUA.write_text(new_lua, encoding="utf-8")
        print(f"  → 書き込み: {JA_LUA}")

    # --- ja_stats.lua をパターン用に書き出し ---
    lines = [
        "-- Path of Building",
        "--",
        "-- Data: Lang/ja_stats",
        "-- スタットの # プレースホルダ入り翻訳パターン (PoE2 公式トレード API stats.json 由来)",
        "--",
        "-- Localization.lua がロードし、exact 検索ミス時にパターン照合する。",
        "-- 各エントリ: { en = 英語原文, ja = 訳文 } (# が引数プレースホルダ、順序対応)",
        "--",
        "return {",
    ]
    # ソートで再現性確保
    for e, j in sorted(patterns):
        lines.append(f'\t{{ en = "{lua_escape(e)}", ja = "{lua_escape(j)}" }},')
    lines.append("}")
    lines.append("")
    ja_stats_content = "\n".join(lines)

    try:
        import lupa
        lua = lupa.LuaRuntime()
        t = lua.execute(ja_stats_content)
        count = sum(1 for _ in t) if lupa.lua_type(t) == "table" else 0
        print(f"\nja_stats.lua 構文 OK: {count} パターン")
    except ImportError:
        print("\n[WARN] lupa 無しで ja_stats.lua 構文検証スキップ")
    except Exception as e:
        print(f"\n[ERR] ja_stats.lua 構文エラー: {e}")
        raise SystemExit(1)

    JA_STATS.write_text(ja_stats_content, encoding="utf-8")
    print(f"→ 書き込み: {JA_STATS}")


if __name__ == "__main__":
    main()
