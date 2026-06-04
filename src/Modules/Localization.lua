-- Path of Building
--
-- Module: Localization
-- UI多言語化基盤。SimpleGraphic の DrawString 系グローバル関数を透過的にフックし、
-- 翻訳テーブルにキーがあれば訳語に置き換える。
--
-- 設計方針:
--   call site (`label = "Items"` 等) は一切改変しない。上流リポジトリとのマージコンフリクトを
--   最小化するため、Lua/C++ の描画 API レイヤーで一括変換する。
--
-- 動作:
--   T("Items") → "アイテム" (ja.lua にキーがあれば訳語)
--   T("Items") → "Items"   (キーが無ければ原文をそのまま返す = 英語フォールバック)
--   T() は自動でカラーエスケープ (^7 等) を考慮し、prefix 付き/無し両方を試行する
--
-- 翻訳テーブル:
--   src/Data/Lang/<lang>.lua       : exact match (キー = 英語、値 = 訳語)
--   src/Data/Lang/<lang>_stats.lua : `#` プレースホルダ入りパターン (任意)
--
local localization = {
	currentLang = "en",
	available = {
		{ code = "en", display = "English" },
		{ code = "ja", display = "日本語" },
	},
	tables = {},
	-- パターン (# 入りスタット) は言語ごとに lazy ロード
	-- patterns[lang] = { { pat = "^...$", fmt = "...", argc = N }, ... }
	patterns = {},
	-- パターン照合結果のメモ化 (テキスト → 訳語 or false 訳語なし)
	-- memo[lang][text] = string | false
	memo = {},
	hooked = false,
}

-- 英語スタットを Lua パターンに変換: 非英数記号をエスケープし、`#` を数値キャプチャに置換
-- 数値書式は PoE 表示に合わせる: 任意符号 + (整数 or 小数) + 桁区切りカンマ可
-- gsub 置換文字列に `%` を含めると解釈エラーになるため、関数形式で組み立てる
-- `+15`, `-3`, `200`, `1.5`, `1,000` を捕捉。PoB は正の数値に `+` を付けて描画するため、
-- API 側パターンが `#%` であっても `+15%` を受けられるよう符号を任意受理する。
local PATTERN_NUM = "([%+%-]?[%d,]+%.?%d*)"
local function compilePattern(en)
	local pat = en:gsub("([%^%$%(%)%%%.%[%]%*%+%-%?])", function(c)
		return "%" .. c
	end)
	pat = pat:gsub("#", function() return PATTERN_NUM end)
	return "^" .. pat .. "$"
end

-- 訳文 ja の `#` を順番に %1, %2, ... プレースホルダに変換
local function compileFormat(ja)
	local n = 0
	return (ja:gsub("#", function()
		n = n + 1
		return "\0" .. tostring(n) .. "\0"
	end)), n
end

local function applyFormat(fmt, caps)
	return (fmt:gsub("%z(%d+)%z", function(i)
		return caps[tonumber(i)] or ""
	end))
end

function localization:LoadLanguage(lang)
	if self.tables[lang] then
		return self.tables[lang]
	end
	self.memo[lang] = {}
	if lang == "en" then
		self.tables.en = {}
		self.patterns.en = {}
		return self.tables.en
	end
	local ok, tbl = pcall(LoadModule, "Data/Lang/" .. lang)
	if ok and type(tbl) == "table" then
		self.tables[lang] = tbl
	else
		ConPrintf("Localization: 翻訳テーブル '%s' を読み込めませんでした: %s",
			lang, tostring(tbl))
		self.tables[lang] = {}
	end
	-- 追加でスタットパターン (任意) をロード
	local okp, patTbl = pcall(LoadModule, "Data/Lang/" .. lang .. "_stats")
	if okp and type(patTbl) == "table" then
		local compiled = {}
		for _, e in ipairs(patTbl) do
			if type(e.en) == "string" and type(e.ja) == "string" then
				local fmt, argc = compileFormat(e.ja)
				compiled[#compiled + 1] = {
					pat = compilePattern(e.en),
					fmt = fmt,
					argc = argc,
				}
			end
		end
		self.patterns[lang] = compiled
		ConPrintf("Localization: '%s_stats' から %d パターンをロード", lang, #compiled)
	else
		self.patterns[lang] = {}
	end
	return self.tables[lang]
end

function localization:SetLanguage(lang)
	if not lang or lang == "" then
		lang = "en"
	end
	self.currentLang = lang
	self:LoadLanguage(lang)
end

function localization:GetLanguage()
	return self.currentLang
end

-- 翻訳ルックアップの本体
-- 1. 完全一致を試す
-- 2. カラーエスケープ (^[0-9] または ^x[0-9A-F]{6}) を剥がして再試行
-- 3. 数字を含むテキストに限り、スタットパターンを順に照合 (結果は memo にキャッシュ)
local function lookup(text)
	local lang = localization.currentLang
	local tbl = localization.tables[lang]
	if not tbl or type(text) ~= "string" then
		return text
	end
	local hit = tbl[text]
	if hit then
		return hit
	end
	-- カラーエスケープを剥がして再試行
	-- 形式: ^N (Nは0-9) または ^xRRGGBB (RGBは16進6桁)
	local prefix, rest = text:match("^(%^x%x%x%x%x%x%x)(.*)$")
	if not prefix then
		prefix, rest = text:match("^(%^%d)(.*)$")
	end
	if prefix then
		hit = tbl[rest]
		if hit then
			return prefix .. hit
		end
	end

	-- スタットパターン照合: 数字を含むテキストのみ対象 (UI ラベル等は即スキップ)
	local pats = localization.patterns[lang]
	if pats and #pats > 0 and text:find("%d") then
		local memo = localization.memo[lang]
		local m = memo[text]
		if m ~= nil then
			return m or text
		end
		-- カラーエスケープを剥がした形でマッチさせ、ヒットしたら prefix を戻す
		local target = prefix and rest or text
		for i = 1, #pats do
			local p = pats[i]
			if p.argc == 1 then
				local a = target:match(p.pat)
				if a then
					local result = applyFormat(p.fmt, { a })
					if prefix then result = prefix .. result end
					memo[text] = result
					return result
				end
			else
				-- 多引数: gmatch ではなく match で複数キャプチャを受け取る
				local caps = { target:match(p.pat) }
				if caps[1] then
					local result = applyFormat(p.fmt, caps)
					if prefix then result = prefix .. result end
					memo[text] = result
					return result
				end
			end
		end
		-- ノーヒット記録: 次回以降同じ text で全パターンを走査しないよう false を残す
		memo[text] = false
	end
	return text
end

-- グローバル翻訳関数（フォーマット文字列等で明示的に呼ぶ用）
function T(key)
	if key == nil then
		return ""
	end
	return lookup(key)
end

-- DrawString 系グローバル関数をフック
-- 静的ラベルは call site 改変なしで自動翻訳される
function localization:InstallDrawStringHooks()
	if self.hooked then
		return
	end
	self.hooked = true

	-- DrawString(x, y, align, size, font, text, ...)
	if type(DrawString) == "function" then
		local _DrawString = DrawString
		DrawString = function(x, y, align, size, font, text, ...)
			return _DrawString(x, y, align, size, font, lookup(text), ...)
		end
	end

	-- DrawStringWidth(size, font, text)
	-- 訳語と原文で文字列幅が変わるため、フックして整合性を保つ
	if type(DrawStringWidth) == "function" then
		local _DrawStringWidth = DrawStringWidth
		DrawStringWidth = function(size, font, text, ...)
			return _DrawStringWidth(size, font, lookup(text), ...)
		end
	end

	-- DrawStringCursorIndex(size, font, text, curX, curY)
	-- テキスト入力フィールドでカーソル位置を計算する関数。翻訳対象は通常ユーザー入力なので
	-- フックしても lookup ヒットしないが、念のため整合性のため通す
	if type(DrawStringCursorIndex) == "function" then
		local _DrawStringCursorIndex = DrawStringCursorIndex
		DrawStringCursorIndex = function(size, font, text, curX, curY, ...)
			return _DrawStringCursorIndex(size, font, lookup(text), curX, curY, ...)
		end
	end
end

function localization:Init()
	self:LoadLanguage("en")
	self:InstallDrawStringHooks()
end

return localization
