"""ja.lua をより厳密に検証 - 全エントリのパース可否を確認"""
import re

ja_path = 'e:/Projects/PathOfBuilding-PoE2/src/Data/Lang/ja.lua'
with open(ja_path, 'r', encoding='utf-8') as f:
    ja = f.read()

# 厳密な Lua 文字列リテラル: " (非\非") | (\任意) "
lua_string = r'"(?:[^"\\]|\\.)*"'
entry_pattern = re.compile(rf'^\s*\[\s*({lua_string})\s*\]\s*=\s*({lua_string})\s*,?\s*(?:--.*)?$')

lines = ja.split('\n')
bad_lines = []
keys_seen = {}
duplicate_keys = []
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if not stripped or stripped.startswith('--') or stripped in ('{', '}', 'return {'):
        continue
    m = entry_pattern.match(line)
    if not m:
        bad_lines.append((i, line))
        continue
    key = m.group(1)
    if key in keys_seen:
        duplicate_keys.append((i, keys_seen[key], key))
    else:
        keys_seen[key] = i

print(f'Total lines: {len(lines)}')
print(f'Entries parsed OK: {len(keys_seen)}')
print(f'Bad lines: {len(bad_lines)}')
for ln, l in bad_lines[:20]:
    print(f'  L{ln}: {l[:120]}')

print(f'Duplicate keys: {len(duplicate_keys)}')
for ln, first_ln, key in duplicate_keys[:5]:
    print(f'  L{ln} (first at L{first_ln}): {key[:80]}')

# 全体構造チェック
print()
opens = ja.count('{')
closes = ja.count('}')
print(f'Braces: {opens} open, {closes} close')

# return { ... } の最後の }の位置
last_brace = ja.rfind('}')
after = ja[last_brace+1:].strip()
print(f'After last {{}}: {repr(after[:60])}')
