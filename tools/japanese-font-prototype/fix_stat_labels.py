"""BuildDisplayStats.lua のラベル群を手動訳で ja.lua に上書きする。

translate_ui.py が自動生成した低品質訳 (例: '効果ive ヒット Pool', 'Phys Max ヒット')
を、差分ツールチップで読みやすい統一訳に差し替える。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JA_LUA = ROOT / "src" / "Data" / "Lang" / "ja.lua"

# キー = BuildDisplayStats.lua の英語ラベル, 値 = 訳語
LABELS: dict[str, str] = {
    # 攻撃 / ヒット
    "Average Hit": "平均ヒット",
    "PvP Average Hit": "PvP平均ヒット",
    "Average Damage": "平均ダメージ",
    "Average Burst Damage": "平均バーストダメージ",
    "PvP Average Damage": "PvP平均ダメージ",
    "Hit Chance": "ヒット率",
    "Uncap. Hit Chance": "ヒット率(上限なし)",
    "Hit Rate": "ヒットレート",
    "Hit DPS": "ヒットDPS",
    "PvP Hit DPS": "PvPヒットDPS",
    "Skill DPS": "スキルDPS",
    "Combined DPS": "合計DPS",
    "Combined Total Damage": "総合ダメージ",
    "Damage inc. Impale": "ダメージ(インペイル込)",
    "Full DPS": "総合DPS(フル)",
    "Total DPS inc. Bleed": "総合DPS(出血込)",
    "Total DPS inc. DoT": "総合DPS(DoT込)",
    "Total DPS inc. Ignite": "総合DPS(発火込)",
    "Total DPS inc. Impale": "総合DPS(インペイル込)",
    "Total DPS inc. Poison": "総合DPS(毒込)",
    # 速度
    "Attack Rate": "攻撃レート",
    "Cast Rate": "詠唱レート",
    "Attack/Cast Rate": "攻撃/詠唱レート",
    "Effective Trigger Rate": "実効トリガーレート",
    "Cast Time": "詠唱時間",
    "Channel Time": "チャネル時間",
    "Firing Rate": "射出レート",
    "Reload Time": "リロード時間",
    "Skill Cooldown": "スキルクールダウン",
    "Skill Duration": "スキル持続時間",
    "Secondary Duration": "サブ持続時間",
    "Aura Duration": "オーラ持続時間",
    "Movement Speed Modifier": "移動スピード補正",
    "Skill Movement Speed": "スキル移動速度",
    "Proj. Speed Mod": "射出物速度補正",
    # クリティカル
    "Crit Chance": "クリティカル率",
    "Effective Crit Chance": "実効クリティカル率",
    "Crit Multiplier": "クリティカル倍率",
    "Crit Bifurcate Chance": "クリティカル分岐確率",
    # AoE
    "AoE Radius": "範囲半径",
    "Presence Radius": "プレゼンス範囲",
    "Attachment Range": "アタッチメント距離",
    # DoT
    "Ignite DPS": "発火DPS",
    "Bleed DPS": "出血DPS",
    "Poison DPS": "毒DPS",
    "Impale DPS": "インペイルDPS",
    "Impale Damage": "インペイルダメージ",
    "DoT DPS": "DoT DPS",
    "Total DoT DPS": "合計DoT DPS",
    "Full Dot DPS": "総合DoT DPS",
    "Decay DPS": "ディケイDPS",
    "Caustic Ground DPS": "腐食大地DPS",
    "Burning Ground DPS": "灼熱大地DPS",
    "Corrupting Blood DPS": "腐敗血DPS",
    "Culling DPS": "カリングDPS",
    "Mirage Caustic Ground DPS": "ミラージュ腐食大地DPS",
    "Mirage Burning Ground DPS": "ミラージュ灼熱大地DPS",
    "Total Mirage DPS": "ミラージュ総合DPS",
    "Total Wisp DPS": "ウィスプ総合DPS",
    "Total Damage per Bleed": "出血ごとの総ダメージ",
    "Total Damage per Ignite": "発火ごとの総ダメージ",
    "Total Damage per Poison": "毒ごとの総ダメージ",
    "Total Degen": "総ディジェネ",
    "Reservation DPS": "リザーブDPS",
    # 防御 - ヒットプール
    "Effective Hit Pool": "有効ヒットプール",
    "Enemy Life Equivalent": "敵ライフ換算",
    "Phys Max Hit": "物理最大ヒット",
    "Fire Max Hit": "火炎最大ヒット",
    "Cold Max Hit": "冷気最大ヒット",
    "Lightning Max Hit": "雷最大ヒット",
    "Chaos Max Hit": "混沌最大ヒット",
    "Elemental Max Hit": "属性最大ヒット",
    "PvP Hit Taken": "PvP被ヒット",
    # 防御 - ライフ/マナ/ES
    "Total Life": "総ライフ",
    "Unreserved Life": "未リザーブライフ",
    "Life Regen": "ライフリジェン",
    "Life Recovery": "ライフ回復",
    "Net Life Recovery": "正味ライフ回復",
    "Life Recoverable": "回復可能ライフ",
    "Life Leech/Gain per Hit": "ヒット毎ライフリーチ/獲得",
    "Life Leech/On Hit Rate": "ヒット時ライフリーチ レート",
    "Life Cost": "ライフコスト",
    "Life Cost per second": "毎秒ライフコスト",
    "Total Mana": "総マナ",
    "Unreserved Mana": "未リザーブマナ",
    "Mana Regen": "マナリジェン",
    "Mana Recovery": "マナ回復",
    "Net Mana Recovery": "正味マナ回復",
    "Mana Leech/Gain per Hit": "ヒット毎マナリーチ/獲得",
    "Mana Leech/On Hit Rate": "ヒット時マナリーチ レート",
    "Mana Cost": "マナコスト",
    "Mana Cost per second": "毎秒マナコスト",
    "Energy Shield": "エナジーシールド",
    "Recoverable ES": "回復可能ES",
    "ES Regen": "ESリジェン",
    "ES Recovery": "ES回復",
    "Net ES Recovery": "正味ES回復",
    "ES Leech/Gain per Hit": "ヒット毎ESリーチ/獲得",
    "ES Leech/On Hit Rate": "ヒット時ESリーチ レート",
    "ES Cost per second": "毎秒ESコスト",
    "Energy Shield Cost": "エナジーシールドコスト",
    "Total Net Recovery": "正味回復合計",
    # スピリット / レイジ / ダークネス / ソウル
    "Total Spirit": "総スピリット",
    "Unreserved Spirit": "未リザーブスピリット",
    "Rage": "レイジ",
    "Rage Cost": "レイジコスト",
    "Rage Cost per second": "毎秒レイジコスト",
    "Rage Regen": "レイジリジェン",
    "Reserved Darkness": "リザーブされたダークネス",
    "Total Darkness": "総ダークネス",
    "Soul Cost": "ソウルコスト",
    "Soul Gain Prevent.": "ソウル獲得阻害",
    # アーマー / 回避 / 受け流し
    "Armour": "アーマー",
    "Evasion Rating": "回避レーティング",
    "Evade Chance": "回避確率",
    "Melee Evade Chance": "近接回避確率",
    "Projectile Evade Chance": "射出物回避確率",
    "Spell Evade Chance": "スペル回避確率",
    "Spell Proj. Evade Chance": "スペル射出物回避確率",
    "Attack Dodge Chance": "アタックドッジ確率",
    "Spell Dodge Chance": "スペルドッジ確率",
    "Block Chance": "ブロック率",
    "Spell Block Chance": "スペルブロック率",
    "Spell Suppression Chance": "スペル抑制確率",
    "Deflect Chance": "受け流し確率",
    "Deflection Rating": "受け流しレーティング",
    "Phys. Damage Reduction": "物理ダメージ減衰",
    # 耐性
    "Fire Resistance": "火炎耐性",
    "Cold Resistance": "冷気耐性",
    "Lightning Resistance": "雷耐性",
    "Chaos Resistance": "混沌耐性",
    "Fire Res. Over Max": "火炎耐性(最大超過)",
    "Cold Res. Over Max": "冷気耐性(最大超過)",
    "Lightning Res. Over Max": "雷耐性(最大超過)",
    "Chaos Res. Over Max": "混沌耐性(最大超過)",
    # ツリー由来
    "%Inc Armour from Tree": "ツリー由来のアーマーの増加%",
    "%Inc ES from Tree": "ツリー由来のESの増加%",
    "%Inc Evasion from Tree": "ツリー由来の回避の増加%",
    "%Inc Life": "ライフの増加%",
    "%Inc Mana from Tree": "ツリー由来のマナの増加%",
    # 能力値
    "Strength": "筋力",
    "Dexterity": "器用さ",
    "Intelligence": "知性",
    "Strength Required": "必要筋力",
    "Dexterity Required": "必要器用さ",
    "Intelligence Required": "必要知性",
    "Devotion": "献身",
    # ミニオン / ウォーリアー / トーテム / トラップ / マイン
    "Active Minion Limit": "アクティブミニオン上限",
    "Totem Placement Time": "トーテム設置時間",
    "Trap Cooldown": "トラップクールダウン",
    "Trap Throwing Time": "トラップ投擲時間",
    "Avg. Traps per Throw": "投擲ごとの平均トラップ数",
    "Mine Throwing Time": "マイン投擲時間",
    "Avg. Mines per Throw": "投擲ごとの平均マイン数",
    "MH Accuracy": "メインハンド命中力",
    "OH Accuracy": "オフハンド命中力",
    # ブランド / シール / ウォークライ
    "Activations per Brand": "ブランドごとの起動数",
    "Max Number of Seals": "シール最大数",
    "Seal Gain Frequency": "シール獲得頻度",
    "Time to Gain Max Seals": "シール最大化までの時間",
    "Sustainable Trauma": "持続可能トラウマ",
    "WarcryCastTime": "ウォークライ詠唱時間",  # 念のため
    # 射出物
    "Projectile Count": "射出物数",
    "Proj, Split Count": "射出物分裂回数",
    "Pierce Count": "貫通回数",
    "Fork Count": "フォーク回数",
    "Max Chain Count": "最大チェイン回数",
    "Bounces Count": "跳ね返り回数",
    "Stored Uses": "蓄積使用回数",
    # オーラ / カース
    "Aura Effect Mod": "オーラ効果補正",
    "Curse Effect Mod": "カース効果補正",
    "Reserve Duration": "リザーブ持続",
    # クォンティティ / レアリティ
    "Item Quantity": "アイテムクォンティティ",
    "Item Rarity": "アイテムレアリティ",
    "Quantity Multiplier": "クォンティティ倍率",
    "Total Explode Chance": "爆発確率合計",
    "Tribute": "トリビュート",
    # その他
    "Warcry Cast Time": "ウォークライ詠唱時間",
    "Channel Time to Trigger": "トリガーまでのチャネル時間",
}


def lua_escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', r"\"")
        .replace("\n", r"\n")
        .replace("\r", r"\r")
        .replace("\t", r"\t")
    )


def main() -> None:
    lua_text = JA_LUA.read_text(encoding="utf-8")
    updated = 0
    appended = 0
    new_lines: list[str] = lua_text.splitlines(keepends=True)

    # 各行を走査してキーが LABELS にあれば値を差し替える
    re_kv = re.compile(r'^(\s*\[")((?:[^"\\]|\\.)+)("\]\s*=\s*")((?:[^"\\]|\\.)*)("\s*,.*)$')
    replaced_keys: set[str] = set()
    for i, ln in enumerate(new_lines):
        m = re_kv.match(ln)
        if not m:
            continue
        k = m.group(2).replace(r"\"", '"')
        if k in LABELS and k not in replaced_keys:
            new_val = lua_escape(LABELS[k])
            new_lines[i] = f"{m.group(1)}{m.group(2)}{m.group(3)}{new_val}{m.group(5)}\n"
            replaced_keys.add(k)
            updated += 1

    # 既存に無いキーは末尾 `}` 直前に追記
    missing = [k for k in LABELS if k not in replaced_keys]
    if missing:
        for i in range(len(new_lines) - 1, -1, -1):
            if new_lines[i].rstrip() == "}":
                insert_at = i
                break
        else:
            raise SystemExit("末尾 } 未検出")
        block = ["\n", "\t-- BuildDisplayStats 統一訳 (fix_stat_labels.py 追加)\n"]
        for k in missing:
            block.append(f'\t["{lua_escape(k)}"] = "{lua_escape(LABELS[k])}",\n')
            appended += 1
        new_lines = new_lines[:insert_at] + block + new_lines[insert_at:]

    final = "".join(new_lines)

    # Lua 構文検証
    try:
        import lupa
        lua = lupa.LuaRuntime()
        t = lua.execute(final)
        count = sum(1 for _ in t) if lupa.lua_type(t) == "table" else 0
        print(f"ja.lua 構文 OK: 全 {count} エントリ")
    except ImportError:
        print("[WARN] lupa 無しで検証スキップ")
    except Exception as e:
        print(f"[ERR] Lua 構文エラー: {e}")
        raise SystemExit(1)

    JA_LUA.write_text(final, encoding="utf-8")
    print(f"updated 既存上書き: {updated} 件")
    print(f"appended 新規追加: {appended} 件")


if __name__ == "__main__":
    main()
