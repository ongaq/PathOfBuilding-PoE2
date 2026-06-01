"""ja.lua の構文チェック"""
import re

with open('e:/Projects/PathOfBuilding-PoE2/src/Data/Lang/ja.lua', 'r', encoding='utf-8') as f:
    ja = f.read()

print(f'Size: {len(ja):,} bytes')
print(f'BOM: {repr(ja[:3])}')

# Control characters (除く \t \n)
ctrl = re.findall(r'[\x00-\x08\x0b-\x1f]', ja)
print(f'Control chars: {len(ctrl)}')

# キーごとに [..] = ".." 形式が成立しているか個別検査
# 各 ["KEY"] = "VALUE", 行を厳密に確認
entry_re = re.compile(r'^\s*\[("(?:[^"\\]|\\.)*")\]\s*=\s*("(?:[^"\\]|\\.)*")\s*,?\s*(?:--.*)?$')

lines = ja.split('\n')
total_entry_like = 0
bad_lines = []
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if not stripped or stripped.startswith('--') or stripped in ('{', '}', 'return {'):
        continue
    if stripped.startswith('['):
        total_entry_like += 1
        if not entry_re.match(line):
            bad_lines.append((i, line[:120]))

print(f'Entry-like lines: {total_entry_like}')
print(f'Bad entries: {len(bad_lines)}')
for ln, l in bad_lines[:15]:
    print(f'  L{ln}: {l}')
