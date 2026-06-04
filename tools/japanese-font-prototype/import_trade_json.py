"""temp/{en,ja}/static.json + filter.json から id ペアで翻訳を抽出し、
既存 ja.lua にマージする。

- static.json: カレンシー / エッセンス / Soul Core / オムニ等の固有名 (約 757 件)
- filter.json: トレード/フィルタの UI ラベル (約 156 件)
- items.json は en/ja の並び順が異なり id も無いため対象外
- stats.json は `#` プレースホルダ問題のため対象外
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JA_LUA = ROOT / "src" / "Data" / "Lang" / "ja.lua"
EN_DIR = ROOT / "temp" / "en"
JA_DIR = ROOT / "temp" / "ja"


def collect(obj, acc):
    """id をキーに text / label を回収。"""
    if isinstance(obj, dict):
        if "id" in obj and "text" in obj and isinstance(obj["text"], str):
            acc[("text", obj["id"])] = obj["text"]
        if "id" in obj and "label" in obj and isinstance(obj["label"], str):
            acc[("label", obj["id"])] = obj["label"]
        for v in obj.values():
            collect(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            collect(v, acc)


def load_pairs(filename: str) -> dict[str, str]:
    en = json.loads((EN_DIR / filename).read_text(encoding="utf-8"))
    ja = json.loads((JA_DIR / filename).read_text(encoding="utf-8"))
    em, jm = {}, {}
    collect(en, em)
    collect(ja, jm)
    pairs: dict[str, str] = {}
    for k in set(em) & set(jm):
        e, j = em[k], jm[k]
        if not e or not j or e == j:
            continue
        # 既存の値と矛盾するキーは後勝ち (filter.json 優先したい場合の余地)
        pairs[e] = j
    return pairs


def parse_existing_keys(lua_text: str) -> set[str]:
    """ja.lua 既存キーを抽出。["..."] = "..." 形式のみ。"""
    keys: set[str] = set()
    pat = re.compile(r'\["((?:[^"\\]|\\.)*)"\]\s*=')
    for m in pat.finditer(lua_text):
        # Unescape \" → "
        k = m.group(1).replace(r"\"", '"').replace(r"\\", "\\")
        keys.add(k)
    return keys


def lua_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', r"\"")


def main() -> None:
    static_pairs = load_pairs("static.json")
    filter_pairs = load_pairs("filter.json")

    print(f"static.json: {len(static_pairs)} 翻訳ペア")
    print(f"filter.json: {len(filter_pairs)} 翻訳ペア")

    # filter > static の順で merge (filter のほうが UI 直結なので優先)
    all_pairs: dict[str, str] = {}
    all_pairs.update(static_pairs)
    all_pairs.update(filter_pairs)
    print(f"  合計ユニーク: {len(all_pairs)}")

    lua_text = JA_LUA.read_text(encoding="utf-8")
    existing = parse_existing_keys(lua_text)
    print(f"ja.lua 既存キー: {len(existing)}")

    new_entries = {k: v for k, v in all_pairs.items() if k not in existing}
    skipped = len(all_pairs) - len(new_entries)
    print(f"  新規追加: {len(new_entries)}  既存と重複でスキップ: {skipped}")

    if not new_entries:
        print("追加なし。終了。")
        return

    # Lua snippet 生成
    block_lines = [
        "",
        "\t-- ============================================================",
        "\t-- トレード/静的データ由来 (temp/{en,ja}/static.json + filter.json)",
        "\t-- カレンシー、エッセンス、Soul Core、フィルタ UI ラベル等",
        "\t-- ============================================================",
    ]
    for k in sorted(new_entries):
        v = new_entries[k]
        block_lines.append(f'\t["{lua_escape(k)}"] = "{lua_escape(v)}",')

    block = "\n".join(block_lines) + "\n"

    # 末尾の "}" 直前に挿入
    closing = "\n}\n"
    if not lua_text.endswith(closing):
        # 末尾改行/空白を許容
        idx = lua_text.rfind("\n}")
        if idx < 0:
            raise SystemExit("ja.lua の閉じカッコ `}` が見つからない")
        new_lua = lua_text[:idx] + block + lua_text[idx:]
    else:
        new_lua = lua_text[: -len(closing)] + block + closing

    # Lua 構文チェック (lupa)
    try:
        import lupa  # type: ignore

        lua = lupa.LuaRuntime()
        result = lua.execute(new_lua)
        if lupa.lua_type(result) == "table":
            count = sum(1 for _ in result)
            print(f"Lua 構文 OK: 全 {count} エントリ")
        else:
            print(f"Lua 構文: 戻り値が table でない ({type(result)})")
    except ImportError:
        print("[WARN] lupa が無いので Lua 構文チェックをスキップ")
    except Exception as e:
        print(f"[ERR] Lua 構文エラー: {e}")
        raise SystemExit(1)

    JA_LUA.write_text(new_lua, encoding="utf-8")
    print(f"書き込み完了: {JA_LUA}")


if __name__ == "__main__":
    main()
