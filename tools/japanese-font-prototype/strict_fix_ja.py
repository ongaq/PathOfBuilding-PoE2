"""ja.lua の全行を Lua パーサで検証し、エラーを起こす行を除去する。"""
import lupa
import re
from pathlib import Path

ja_path = Path('e:/Projects/PathOfBuilding-PoE2/src/Data/Lang/ja.lua')
content = ja_path.read_text(encoding='utf-8')
lines = content.split('\n')

lua = lupa.LuaRuntime()
bad_lines: list[tuple[int, str, str]] = []
good_lines: list[str] = []

for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if not stripped.startswith('['):
        # エントリ行以外はそのまま残す
        good_lines.append(line)
        continue
    # 単独行で lua として評価できるか
    # 末尾カンマがあると単独評価できないので table 内で評価
    snippet = f'local t = {{ {line.rstrip(",").strip()} }}'
    try:
        lua.execute(snippet)
        good_lines.append(line)
    except lupa.LuaError as e:
        bad_lines.append((i, line[:120], str(e)[:80]))

print(f'Bad lines removed: {len(bad_lines)}')
for ln, l, err in bad_lines:
    print(f'  L{ln}: {l}')
    print(f'         err: {err}')

ja_path.write_text('\n'.join(good_lines), encoding='utf-8')

# 最終検証
try:
    result = lua.execute('\n'.join(good_lines))
    if lupa.lua_type(result) == 'table':
        count = sum(1 for _ in result)
        print(f'\nFinal: OK, {count} entries')
    else:
        print(f'\nFinal: returned {type(result)}')
except lupa.LuaError as e:
    print(f'\nFinal: still errors: {e}')
