import re, sys
sys.stdout.reconfigure(encoding='utf-8')
content = open('src/Modules/BuildDisplayStats.lua', encoding='utf-8').read()
labels = sorted(set(re.findall(r'label\s*=\s*"([^"]+)"', content)))
ja_content = open('src/Data/Lang/ja.lua', encoding='utf-8').read()
existing = set()
for m in re.finditer(r'\["((?:[^"\\]|\\.)+)"\]\s*=', ja_content):
    existing.add(m.group(1).replace(r'\"', '"').replace(r'\\', '\\'))
already = [l for l in labels if l in existing]
missing = [l for l in labels if l not in existing]
print(f'BuildDisplayStats labels: total={len(labels)} already={len(already)} missing={len(missing)}')
for l in missing:
    print(f'  MISSING: {l!r}')
