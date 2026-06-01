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
--   src/Data/Lang/<lang>.lua (Luaファイルが table を return する形式)
--
local localization = {
	currentLang = "en",
	available = {
		{ code = "en", display = "English" },
		{ code = "ja", display = "日本語" },
	},
	tables = {},
	hooked = false,
}

function localization:LoadLanguage(lang)
	if self.tables[lang] then
		return self.tables[lang]
	end
	if lang == "en" then
		self.tables.en = {}
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
-- 2. カラーエスケープ (^[0-9] または ^x[0-9A-F]{6}) を剥がして再試行、ヒットすればプレフィックスを復元
local function lookup(text)
	local tbl = localization.tables[localization.currentLang]
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
