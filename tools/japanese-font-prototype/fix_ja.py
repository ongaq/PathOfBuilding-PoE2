"""ja.lua 内の壊れたエントリを削除"""
import re

ja_path = 'e:/Projects/PathOfBuilding-PoE2/src/Data/Lang/ja.lua'
with open(ja_path, 'r', encoding='utf-8') as f:
    ja = f.read()

# 厳密な行パターン: ["KEY"] = "VALUE",
entry_re = re.compile(r'^\s*\[("(?:[^"\\]|\\.)*")\]\s*=\s*("(?:[^"\\]|\\.)*")\s*,?\s*(?:--.*)?$')

new_lines = []
removed = 0
removed_samples = []
for line in ja.split('\n'):
    stripped = line.strip()
    if stripped.startswith('['):
        if not entry_re.match(line):
            removed += 1
            if len(removed_samples) < 10:
                removed_samples.append(line[:120])
            continue
    new_lines.append(line)

new_ja = '\n'.join(new_lines)
with open(ja_path, 'w', encoding='utf-8') as f:
    f.write(new_ja)

print(f'Removed broken entries: {removed}')
print(f'Final size: {len(new_ja):,} bytes')
print('Samples of removed lines:')
for s in removed_samples:
    print(f'  {s}')
