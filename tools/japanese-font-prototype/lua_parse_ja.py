"""実 Lua インタプリタで ja.lua をロードしてエラーを検出"""
import lupa
from pathlib import Path

ja_path = Path('e:/Projects/PathOfBuilding-PoE2/src/Data/Lang/ja.lua')
content = ja_path.read_text(encoding='utf-8')

# Lua 5.1 (LuaJIT 互換) で実行
lua = lupa.LuaRuntime()
try:
    result = lua.execute(content)
    if result is None:
        print('Loaded but returned nil')
    elif lupa.lua_type(result) == 'table':
        count = sum(1 for _ in result)
        print(f'OK: returned table with {count} entries')
    else:
        print(f'Returned: {type(result)} = {result}')
except lupa.LuaError as e:
    print(f'Lua error: {e}')
except Exception as e:
    print(f'Unexpected: {type(e).__name__}: {e}')
