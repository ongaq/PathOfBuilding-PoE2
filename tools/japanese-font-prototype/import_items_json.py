"""temp/{en,ja}/items.json からアイテム名翻訳を抽出して ja.lua へマージ。

ペアリング戦略:
  items.json には id が無いため index ペアリングするが、カテゴリ内でユニーク/ベースを
  別グループに分け、en/ja の件数が一致するグループのみ安全にペアリングする。
  (en/ja は同じ「英語名アルファベット順」でソートされているため、各グループ内の
   順序が一致することを件数チェックで担保する)

ペアリング対象:
  - すべての UNIQUE (全 762 件、全カテゴリで件数完全一致)
  - 件数が完全一致する BASE カテゴリ (accessory/flask/gem/jewel/map/sanctum/wombgift)

スキップ:
  - 件数が一致しない BASE カテゴリ (armour: -7, currency: -1, weapon: +1)
    ドリフト位置を特定する手段が無いため。

抽出する翻訳キー:
  - `type`  : 基底アイテム名 (例: "Gold Ring" → "金の指輪")
  - `name`  : ユニークの固有名 (例: "Andvarius" → "アンドヴァリアス")
  - `text`  : フル表記 (例: "Andvarius Gold Ring" → "アンドヴァリアス 金の指輪")
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JA_LUA = ROOT / "src" / "Data" / "Lang" / "ja.lua"
EN_FILE = ROOT / "temp" / "en" / "items.json"
JA_FILE = ROOT / "temp" / "ja" / "items.json"


def split(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    uniq = [e for e in entries if e.get("flags", {}).get("unique")]
    base = [e for e in entries if not e.get("flags", {}).get("unique")]
    return uniq, base


def collect_pairs(en_entries: list[dict], ja_entries: list[dict], pairs: dict[str, str]) -> int:
    """en/ja を index ペアリングして type/name/text フィールドを翻訳辞書に追加。"""
    added = 0
    for ee, je in zip(en_entries, ja_entries):
        for k in ("type", "name", "text"):
            ev = ee.get(k)
            jv = je.get(k)
            if not isinstance(ev, str) or not isinstance(jv, str):
                continue
            if not ev or not jv or ev == jv:
                continue
            # 既出と矛盾しない限り採用 (先勝ち)
            if ev in pairs and pairs[ev] != jv:
                continue
            if ev not in pairs:
                added += 1
            pairs[ev] = jv
    return added


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

    pairs: dict[str, str] = {}
    paired_uniq = 0
    paired_base = 0
    skipped_drift: list[str] = []

    for ec, jc in zip(en["result"], ja["result"]):
        if ec["id"] != jc["id"]:
            continue
        eu, eb = split(ec["entries"])
        ju, jb = split(jc["entries"])

        # UNIQUE: 全カテゴリで件数一致 (検証済)。念のため再チェック。
        if len(eu) == len(ju):
            added = collect_pairs(eu, ju, pairs)
            paired_uniq += len(eu)
            # added 件は新規収集分のみカウント
        else:
            skipped_drift.append(f"{ec['id']}/unique({len(eu)}!={len(ju)})")

        # BASE: 件数一致のみ採用
        if len(eb) == len(jb):
            collect_pairs(eb, jb, pairs)
            paired_base += len(eb)
        else:
            skipped_drift.append(f"{ec['id']}/base({len(eb)}!={len(jb)})")

    print(f"ペアリング成功: unique {paired_uniq} 件, base {paired_base} 件")
    print(f"翻訳ペア (type/name/text 重複除去後): {len(pairs)} エントリ")
    if skipped_drift:
        print(f"件数不一致でスキップ: {skipped_drift}")

    # 既存 ja.lua とマージ
    lua_text = JA_LUA.read_text(encoding="utf-8")
    existing = parse_existing_keys(lua_text)
    new = {k: v for k, v in pairs.items() if k not in existing}
    print(f"\nja.lua 既存: {len(existing)}  新規追加: {len(new)}  既存と重複でスキップ: {len(pairs) - len(new)}")

    if not new:
        print("追加なし。終了。")
        return

    block = [
        "",
        "\t-- ============================================================",
        "\t-- items.json 由来 (temp/{en,ja}/items.json)",
        "\t-- 基底アイテム名 (type) / ユニーク名 (name) / フル表記 (text) の翻訳",
        "\t-- UNIQUE 全カテゴリ + BASE 件数一致カテゴリのみ採用",
        "\t-- ============================================================",
    ]
    for k in sorted(new):
        block.append(f'\t["{lua_escape(k)}"] = "{lua_escape(new[k])}",')
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


if __name__ == "__main__":
    main()
