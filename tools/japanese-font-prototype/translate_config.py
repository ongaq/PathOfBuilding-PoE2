"""
ConfigOptions.lua の label を一括日本語化するスクリプト。

ja.lua に追記するための Lua テーブル形式の出力を生成する。
パターンベースの翻訳 + ゲーム用語辞書で処理。
"""
from __future__ import annotations

import re
from pathlib import Path

# ============================================================
# ゲーム用語辞書 (英→日)
# 単語境界で置換するため、長い語から登録する
# ============================================================
TERMS: dict[str, str] = {
    # ダメージタイプ・属性
    "Lightning": "雷",
    "Cold": "冷気",
    "Fire": "炎",
    "Chaos": "混沌",
    "Physical": "物理",
    "Elemental": "属性",
    "Energy Shield": "エナジーシールド",
    "Mana": "マナ",
    "Life": "ライフ",
    "Spirit": "スピリット",
    "Rage": "レイジ",
    "Soul": "ソウル",

    # 状態
    "Frozen": "凍結",
    "Chilled": "冷却",
    "Brittle": "脆性",
    "Burning": "炎上",
    "Ignited": "発火",
    "Scorched": "灼熱",
    "Shocked": "感電",
    "Sapped": "弱体",
    "Bleeding": "出血",
    "Poisoned": "毒",
    "Blinded": "盲目",
    "Dazed": "目眩",
    "Maimed": "切傷",
    "Pinned": "拘束",
    "Intimidated": "威圧",
    "Crushed": "粉砕",
    "Unnerved": "動揺",
    "Stunned": "気絶",
    "Cursed": "呪い",
    "Fortified": "強化",
    "Onslaught": "猛攻",
    "Adrenaline": "アドレナリン",
    "Channelling": "チャネリング",
    "Sprinting": "全力疾走",
    "Leeching": "吸収",
    "Sacrificing": "犠牲",
    "Elusive": "回避",
    "Focused": "集中",
    "Unbound": "解放",
    "Insane": "発狂",
    "Recently": "最近",
    "Recent": "最近の",
    "Immune": "免疫",

    # チャージ・スタック
    "Power Charge": "パワーチャージ",
    "Frenzy Charge": "フレンジーチャージ",
    "Endurance Charge": "エンデュランスチャージ",
    "Inspiration Charge": "インスピレーションチャージ",
    "Siphoning Charge": "サイフォニングチャージ",
    "Blitz Charge": "ブリッツチャージ",
    "Blood Charge": "ブラッドチャージ",
    "Challenger Charge": "チャレンジャーチャージ",
    "Spirit Charge": "スピリットチャージ",
    "Charges": "チャージ",
    "Charge": "チャージ",
    "Stacks": "スタック",
    "Stack": "スタック",

    # 敵関連
    "the enemy": "敵",
    "enemy": "敵",
    "Enemy": "敵",
    "Boss": "ボス",
    "Allies": "味方",
    "Minions": "ミニオン",
    "Minion": "ミニオン",
    "Totems": "トーテム",
    "Totem": "トーテム",
    "Spectres": "霊体",
    "Spectre": "霊体",
    "Enemies": "敵",

    # スキル系
    "Skill": "スキル",
    "Spell": "呪文",
    "Attack": "攻撃",
    "Critical": "クリティカル",
    "Hits": "ヒット",
    "Hit": "ヒット",
    "Cast": "詠唱",
    "Trigger": "トリガー",
    "Aura": "オーラ",
    "Curse": "呪い",
    "Banner": "バナー",
    "Brand": "ブランド",
    "Trap": "トラップ",
    "Mine": "マイン",
    "Warcry": "戦吼",

    # その他
    "Damage": "ダメージ",
    "Resistance": "耐性",
    "Penetration": "貫通",
    "Pen.": "貫通",
    "Multiplier": "倍率",
    "Chance": "確率",
    "Rating": "レーティング",
    "Reduction": "軽減",
    "Speed": "速度",
    "Duration": "持続時間",
    "Cooldown": "クールダウン",
    "Reload": "リロード",
    "Distance": "距離",
    "Nearby": "近くの",
    "nearby": "近くの",
    "Active": "アクティブ",
    "active": "アクティブ",
    "Number": "数",
    "Effect": "効果",
    "Bonus": "ボーナス",
    "Always": "常時",
    "always": "常時",
    "Full": "満タン",
    "Low": "低い",
    "always on Full": "常に満タンの",
    "always on Low": "常に低い",
    "moving": "移動中",
    "Maximum": "最大",
    "maximum": "最大",
    "Minimum": "最小",
    "minimum": "最小",
    "average": "平均",
    "Average": "平均",
    # screenshot で見えた追加語
    "Current": "現在の",
    "current": "現在の",
    "Recently": "最近",
    "recently": "最近",
    "Corpse": "死体",
    "Corpses": "死体",
    "Consumed": "消費した",
    "consumed": "消費した",
    "spent": "使用した",
    "Killed": "倒した",
    "applied": "付与した",
    "Discharge": "放出",
    "Companion": "コンパニオン",
    "Withered": "枯死",
    "Corrosion": "腐食",
    "Ensnare": "罠",
    "Tailwind": "追い風",
    "Fortification": "強化",
    "Adrenaline": "アドレナリン",
    "Phasing": "位相",
    "Chaotic Might": "混沌の力",
    "Unholy Might": "不浄の力",
    "Arcane Surge": "Arcane Surge",
    "Onslaught": "猛攻",
    "Quicksand Hourglass": "Quicksand Hourglass",
    "Alchemist's Genius": "Alchemist's Genius",
    "Skeleton": "スケルトン",
    "linked": "リンクされた",
    "linked Targets": "リンク対象",
    "Targets": "対象",
    "Bleeds": "出血",
    "Poisons": "毒",
    "Ignites": "発火",
    "stacks": "スタック",
    "Stacks": "スタック",
    "Spider's Web": "蜘蛛の巣",
    "Soul Eater": "ソウルイーター",
    "Power of Culled": "間引かれた力",
    "Power of": "の力",
    "wait for Max Seals": "最大シールを待つ",
    "Crab Barriers": "カニの障壁",
    "Rampage Kills": "ランページキル",
    "Rampage": "ランページ",
    "Higher than Player": "プレイヤーより高い",
    "higher than Player": "プレイヤーより高い",
    "if not": "でない場合",
    "attached to": "に付属する",
    "attached": "付属",
    "Brands attached to": "に付属するブランド",
    "in past": "過去の",
    "in the past": "過去の",
    "in the last": "過去の",
    "past": "過去",
    "seconds": "秒",
    "second": "秒",
    "Hazard": "ハザード",
    "Hazards": "ハザード",
    "affected by": "影響を受けた",
    "affected": "影響を受けた",
    "exited Presence": "Presenceから出た",
    "entered Presence": "Presenceに入った",
    "Presence": "Presence",
    "Hindered": "妨害",
    "Taunted": "挑発",
    "Debilitated": "衰弱",
    "Immobilised": "拘束",
    "Pacified": "鎮静",
    "Electrocuted": "感電中",
    "Heavy 気絶": "重気絶",
    "Heavy Stun": "重気絶",
    "Armour Broken": "アーマー破壊",
    "of Rupture": "Rupture",
    "Rupture": "Rupture",
    "blade count": "刃数",
    "Avatar": "Avatar",
    "Planted": "設置",
    "Valour": "勇気",
    "Hits Suppressed": "軽減ヒット",
    "Suppressed": "軽減",
    "Suppress": "軽減",
    "Banner": "バナー",
    "Have you": "あなたは",
    "have you": "あなたは",
    "Have your": "あなたの",
    "have your": "あなたの",
    "your minions": "あなたのミニオン",
    "Have your minions been created": "ミニオンが作成された",
    "skill has": "スキルが",
    "Skill has": "スキルが",
    "Forked": "分岐した",
    "Chained": "連鎖した",
    "Pierced": "貫通した",
    "different": "異なる",
    "Targeting": "ターゲット",
    "targeting": "ターゲット",
    "spent in past": "過去で使用した",
    "spent Recently": "最近使用した",
    "Roll Range": "ロール範囲",
    "Higher": "高い",
    "higher": "高い",
    "at Close Range": "近距離で",
    "Close Range": "近距離",
    "Heavy": "重",
    "% higher than Player": "% プレイヤーより高い",
    "Player": "プレイヤー",
    "applied Recently": "最近付与した",
    "Hits": "ヒット",
    "Ascendancy": "アセンダンシー",
    "Charm": "チャーム",
    "Charm active": "チャームが有効",
    "Flask": "フラスコ",
    "Flask active": "フラスコが有効",
    "Flask uses": "フラスコの使用回数",
    "Flame Walls": "Flame Walls",
    "% of": "の%",
    "% of Curse": "呪いの%",
    "Curse Expired": "呪い 持続時間 Expired",
    "Curse Duration Expired": "呪い 持続時間 Expired",
    "Expired": "持続時間切れ",
    "expired": "持続時間切れ",
    "in Your Presence": "あなたの Presence 内に",
    "in your Presence": "あなたの Presence 内に",
    "Your Presence": "あなたの Presence",
    "your Presence": "あなたの Presence",
}

# ============================================================
# 完全一致の決め打ち訳 (パターンマッチでは綺麗にいかないもの)
# ============================================================
EXACT: dict[str, str] = {
    # セクションヘッダ・基本UI
    "General": "一般",
    "Skill Options": "スキル設定",
    "When In Combat": "戦闘中",
    "For Effective DPS": "実効DPS用",
    "Enemy Stats": "敵ステータス",
    "Custom Modifiers": "カスタムmod",
    "Quest Rewards": "クエスト報酬",
    "Show All Configurations": "全設定を表示",
    "Config set:": "設定セット:",
    "Default": "既定",
    "Average": "平均",
    "Base": "基本",
    "None": "なし",
    "Nothing": "なし",
    "All": "全て",
    "Cold": "冷気",
    "Hot": "炎",

    # 各計算モード
    "Elemental Resistance penalty:": "属性耐性ペナルティ:",
    "Ailment calculation mode:": "状態異常計算モード:",
    "Cooldown calculation mode:": "クールダウン計算モード:",
    "Armour calculation mode:": "アーマー計算モード:",
    "Chance To Ignore PDR Mode:": "物理軽減無視確率モード:",
    "EHP calc unlucky:": "EHP計算 不運モード:",
    "Boosted calc mode:": "強化計算モード:",
    "Ignore Jewel Limits": "ジュエル上限を無視",
    "Endgame (-60%)": "エンドゲーム (-60%)",

    # 敵ステータス
    "Enemy Level:": "敵レベル:",
    "Is the enemy a Boss?": "敵はボスですか？",
    "Delirious Effect:": "せん妄効果:",
    "Enemy Phys. Damage Reduction:": "敵の物理ダメージ軽減:",
    "Enemy Lightning Resistance:": "敵の雷耐性:",
    "Enemy Cold Resistance:": "敵の冷気耐性:",
    "Enemy Fire Resistance:": "敵の炎耐性:",
    "Enemy Chaos Resistance:": "敵の混沌耐性:",
    "Enemy Max Resistance is always 75%": "敵の最大耐性は常に75%",
    "Enemy Block Chance:": "敵のブロック率:",
    "Enemy Base Evasion:": "敵の基本回避:",
    "Enemy Base Armour:": "敵の基本アーマー:",
    "Boss Skill Preset": "ボススキルプリセット",
    "Enemy Damage Type:": "敵のダメージタイプ:",
    "Enemy attack / cast time in ms:": "敵の攻撃/詠唱時間 (ミリ秒):",
    "Enemy critical strike chance:": "敵のクリティカル率:",
    "Enemy critical strike multiplier:": "敵のクリティカル倍率:",
    "Enemy Skill Physical Damage:": "敵スキルの物理ダメージ:",
    "Enemy Skill Physical Overwhelm:": "敵スキルの物理オーバーホエルム:",
    "Enemy Skill Lightning Damage:": "敵スキルの雷ダメージ:",
    "Enemy Skill Lightning Pen:": "敵スキルの雷貫通:",
    "Enemy Skill Cold Damage:": "敵スキルの冷気ダメージ:",
    "Enemy Skill Cold Pen:": "敵スキルの冷気貫通:",
    "Enemy Skill Fire Damage:": "敵スキルの炎ダメージ:",
    "Enemy Skill Fire Pen:": "敵スキルの炎貫通:",
    "Enemy Skill Chaos Damage:": "敵スキルの混沌ダメージ:",
    "Enemy Skill Chaos Pen:": "敵スキルの混沌貫通:",
    "Distance to enemy:": "敵までの距離:",
    "Guardian/Pinnacle": "ガーディアン/頂点",

    # For Effective DPS の Is the enemy X
    "Is the enemy Dazed?": "敵は目眩状態ですか？",
    "Is the enemy Maimed?": "敵は切傷状態ですか？",
    "Is the enemy Blinded?": "敵は盲目状態ですか？",
    "Is the enemy Pinned?": "敵は拘束状態ですか？",
    "Is the enemy Intimidated?": "敵は威圧状態ですか？",
    "Is the enemy Crushed?": "敵は粉砕状態ですか？",
    "Is the enemy Unnerved?": "敵は動揺状態ですか？",
    "Is the enemy covered in Ash?": "敵は灰塗れですか？",
    "Is the enemy covered in Frost?": "敵は霜塗れですか？",
    "Is the enemy on Low Life?": "敵は低ライフですか？",

    # When In Combat の Are you / Do you
    "Are you always moving?": "あなたは常に移動中ですか？",
    "Are you Channelling Cyclone?": "サイクロンをチャネリング中ですか？",
    "Are you Channelling?": "チャネリング中ですか？",
    "Are you in dodge roll?": "回避ロール中ですか？",
    "Are you in Demon Form?": "デーモンフォーム中ですか？",
    "Are you in Her Embrace?": "「彼女の抱擁」中ですか？",
    "Are you in a Bloodstorm?": "ブラッドストーム中ですか？",
    "Are you in a Sandstorm?": "サンドストーム中ですか？",
    "Are you on Caustic Ground?": "腐食地形上にいますか？",
    "Are you on Consecrated Ground?": "聖別地形上にいますか？",
    "Are you on Fungal Ground?": "菌類地形上にいますか？",
    "Are you out of Life Flask uses?": "ライフフラスコの使用回数を使い切りましたか？",
    "Are you surrounded?": "囲まれていますか？",
    "Are you animating Lingering Blades?": "残留ブレードを動かしていますか？",
    "Are you Immune to Curses?": "呪いに対して免疫ですか？",
    "Currently Shapeshifted?": "現在シェイプシフト中ですか？",
    "Bypass CD?": "クールダウンを無視しますか？",
    "Count Skill Reservation towards eHP?": "スキル予約をeHPに含めますか？",
    "Have you been Stunned Recently?": "最近気絶しましたか？",
    "Infusion consumed recently?": "最近Infusionを消費しましたか？",
    "Channeling for # seconds:": "Nチャネリング秒数:",

    # 残り少数の非スキル系
    "Don't disable items": "アイテムを無効化しない",
    "Multi-part area skills:": "複数パーツ範囲スキル:",
    "Time spent stationary": "静止していた時間",
    "Highest damage type Override:": "最大ダメージタイプの上書き:",
    "Overkill damage:": "オーバーキルダメージ:",
    "Stages:": "段階:",
    "Stance:": "スタンス:",
    "State:": "状態:",
    "Hex:": "ヘックス:",
    "Steel Shards consumed:": "消費したスチールシャード:",
    "Spear older than 0.5s?": "槍が0.5秒以上経過？",
    "Purple Flames collected:": "収集した紫の炎:",
    "Projectile Travelled through?": "投射物が通過した？",
    "Seconds building Stoicism:": "ストイシズム構築秒数:",
    "Source rate for Intuitive Link": "Intuitive Linkのソースレート",
    "Total Resonance Count:": "総共鳴数:",
    "Total life pool of Sentinel of Radiance": "Sentinel of Radianceの総ライフプール",
    "Do your minions have Chaotic Might?": "ミニオンは混沌の力を持っていますか？",
    "Do your minions have Unholy Might?": "ミニオンは不浄の力を持っていますか？",
    "PvP Tvalue override (ms):": "PvP T値上書き (ms):",
    "Reserved Darkness:": "予約された闇:",
    "Changed Stance in the last 1s?": "過去1秒でスタンス変更しましたか？",
    "Is Slipstream active?:": "スリップストリームは有効ですか？:",
    "Whirlwind Buffs:": "ウィワインドバフ:",
    "Whirlwind Stages:": "ウィワインド段階:",
    "Blade Vortex blade count:": "ブレイドボルテックスの刃数:",
    "Augyre rotating buff:": "Augyre 回転バフ:",
    "Steel Wards:": "スチールウォード:",
    "Combo:": "コンボ:",
    "Trauma:": "トラウマ:",
    "Cruelty:": "残虐:",
    "Infusion:": "Infusion:",
    "Doom on Hex:": "ヘックスのドゥーム:",
    "Drain Ailments:": "状態異常を吸収:",
    "Eldritch Empowerment:": "Eldritch Empowerment:",
    "Embrace Madness:": "狂気を受け入れる:",
    "Conflux Buff:": "コンフラックスバフ:",
    "Fresh Meat:": "Fresh Meat:",
    "Hex:": "ヘックス:",
    "Plague Bearer:": "Plague Bearer:",
    "Predator:": "Predator:",
    "Pride:": "誇り:",
    "Intensify:": "強化:",
    "Into the Breach:": "突入:",
    "Meat Shield:": "肉の盾:",
    "Momentum:": "勢い:",
    "Parry:": "受け流し:",
    "Stoicism:": "ストイシズム:",
    "Unhinge:": "Unhinge:",
    "Trinity:": "三位一体:",
    "Absolution: Count skill damage once": "アブソリューション: スキルダメージを1回のみカウント",
    "^1Nothing^7": "^1なし^7",
}

# 色エスケープ（^xRRGGBB / ^N）を一旦剥がして翻訳 → 戻す
COLOR_RE = re.compile(r"\^(?:x[0-9A-Fa-f]{6}|[0-9])")


def translate_term(text: str) -> str:
    """テキスト中の単語を辞書置換 (長い語優先、大小区別)"""
    # 長い key から順に
    for key in sorted(TERMS.keys(), key=len, reverse=True):
        text = text.replace(key, TERMS[key])
    return text


def translate_label(label: str) -> str | None:
    """ラベルを訳す。EXACT 優先、なければパターンマッチ。"""
    # 完全一致
    if label in EXACT:
        return EXACT[label]

    # 色エスケープは保持したまま中身だけ訳す
    # シンプルにラベル全体を辞書置換 → パターン整形
    translated = translate_term(label)

    # パターン整形
    # "Are you X?" → "あなたはXですか？"
    m = re.match(r"^Are you (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"あなたは{inner}ですか？"

    # "Do you have X?" → "Xを持っていますか？"
    m = re.match(r"^Do you have (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}を持っていますか？"

    # "Do you use X?" → "Xを使用しますか？"
    m = re.match(r"^Do you use (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}を使用しますか？"

    # "Do you X?" → "Xしますか？"
    m = re.match(r"^Do you (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}しますか？"

    # "Have you been X Recently?" → "最近Xしましたか？"
    m = re.match(r"^Have you been (.+) Recently\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"最近{inner}しましたか？"

    # "Have you X recently?" → "最近Xしましたか？"
    m = re.match(r"^Have you (.+) [Rr]ecently\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"最近{inner}しましたか？"

    # "Is the enemy X?" → "敵はXですか？"
    m = re.match(r"^Is the enemy (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"敵は{inner}ですか？"

    # "Is enemy X?" → "敵はXですか？"
    m = re.match(r"^Is enemy (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"敵は{inner}ですか？"

    # "# of X (if not maximum):" → "Xの数 (最大でない場合):"
    m = re.match(r"^# of (.+) \(if not maximum\):$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}の数 (最大でない場合):"

    # "# of X (if not average):" → "Xの数 (平均でない場合):"
    m = re.match(r"^# of (.+) \(if not average\):$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}の数 (平均でない場合):"

    # "# of X:" → "Xの数:"
    m = re.match(r"^# of (.+):$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}の数:"

    # "# X" → "Xの数"
    m = re.match(r"^# (.+)$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}の数"

    # "% of X:" → "Xの%:"
    m = re.match(r"^% (.+):$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}の%:"

    # "Have you X in the past Ys?" → "過去YでXしましたか？"
    m = re.match(r"^Have you (.+) in the (?:past|last) (.+)\?$", label)
    if m:
        action = translate_term(m.group(1))
        period = translate_term(m.group(2))
        return f"過去{period}で{action}しましたか？"

    # "Have you X?" → "Xしましたか？"
    m = re.match(r"^Have you (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}しましたか？"

    # "Is X active?" → "Xは有効ですか？"
    m = re.match(r"^Is (.+) active\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}は有効ですか？"

    # "Is X?" 汎用 → "Xですか？"
    m = re.match(r"^Is (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}ですか？"

    # "Has X consumed Y?" → "XはYを消費しましたか？"
    m = re.match(r"^Has (.+) consumed (.+)\?$", label)
    if m:
        subj = translate_term(m.group(1))
        obj = translate_term(m.group(2))
        return f"{subj}は{obj}を消費しましたか？"

    # "Did you X yourself?" → "自分にXしましたか？"
    m = re.match(r"^Did you (.+) yourself\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"自分に{inner}しましたか？"

    # "Did you X?" → "Xしましたか？"
    m = re.match(r"^Did you (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}しましたか？"

    # "How many X?" → "いくつのX？"
    m = re.match(r"^How many (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"いくつの{inner}？"

    # "X recently?" → "最近X？"
    m = re.match(r"^(.+) recently\?$", label, re.IGNORECASE)
    if m:
        inner = translate_term(m.group(1))
        return f"最近{inner}？"

    # "Summoned X in past Y Seconds?" → "過去Y秒以内にXを召喚しましたか？"
    m = re.match(r"^Summoned (.+) in past (\d+) Seconds\?$", label)
    if m:
        what = translate_term(m.group(1))
        sec = m.group(2)
        return f"過去{sec}秒以内に{what}を召喚しましたか？"

    # "Consumed X?" → "Xを消費しましたか？"
    m = re.match(r"^Consumed (.+)\?$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}を消費しましたか？"

    # "Consumed X" → "Xを消費"
    m = re.match(r"^Consumed (.+)$", label)
    if m:
        inner = translate_term(m.group(1))
        return f"{inner}を消費"

    # "X past Ns?" / "X past N seconds?"
    m = re.match(r"^(.+) past (.+)\?$", label)
    if m:
        action = translate_term(m.group(1))
        period = translate_term(m.group(2))
        return f"過去{period}で{action}？"

    # "Enable X" / "Disable X" → "Xを有効化" / "Xを無効化"
    m = re.match(r"^Enable (.+)$", label)
    if m:
        return f"{translate_term(m.group(1))}を有効化"
    m = re.match(r"^Disable (.+)$", label)
    if m:
        return f"{translate_term(m.group(1))}を無効化"

    # "X mode:" / "X Mode:" → "Xモード:"
    m = re.match(r"^(.+) [Mm]ode:$", label)
    if m:
        return f"{translate_term(m.group(1))}モード:"

    # "Last N% of attached duration?" → "付属持続時間の最後のN%？"
    m = re.match(r"^Last (\d+)% of attached duration\?$", label)
    if m:
        return f"付属持続時間の最後の{m.group(1)}%？"

    # 翻訳でテキストが変わったなら採用
    if translated != label:
        return translated

    return None  # 翻訳できなかった


def main() -> None:
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "src" / "Modules" / "ConfigOptions.lua"
    text = config_path.read_text(encoding="utf-8")
    labels = sorted(set(re.findall(r'label = "([^"]+)"', text)))

    out_lines = [
        "",
        "\t-- ============================================================",
        "\t-- ConfigOptions.lua 自動翻訳 (translate_config.py で生成)",
        "\t-- ============================================================",
    ]
    translated = 0
    untranslated: list[str] = []
    for label in labels:
        ja = translate_label(label)
        if ja is None or ja == label:
            untranslated.append(label)
            continue
        # Lua 文字列エスケープ
        key = label.replace("\\", "\\\\").replace('"', '\\"')
        val = ja.replace("\\", "\\\\").replace('"', '\\"')
        out_lines.append(f'\t["{key}"] = "{val}",')
        translated += 1

    out_path = Path(__file__).parent / "config_translations.lua"
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    untrans_path = Path(__file__).parent / "config_untranslated.txt"
    untrans_path.write_text("\n".join(untranslated) + "\n", encoding="utf-8")

    print(f"Total labels:    {len(labels)}")
    print(f"Translated:      {translated}")
    print(f"Untranslated:    {len(untranslated)}")
    print(f"Output:          {out_path}")
    print(f"Untranslated to: {untrans_path}")


if __name__ == "__main__":
    main()
