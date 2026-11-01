"""
把网页地图编辑器（tools/build_editor.py 生成）里的改动写回地图脚本。

输入是一个 JSON 文件：编辑器数据库 edits 集合导出的文档列表，或者编辑器「复制改动清单」得到的
{"base": ..., "edits": [...]}。每条改动有 x、y、t（地形字符）、f（地貌字符）、bt/bf（改之前）、note（备注）。
- 地图脚本里这格已经不是 bt/bf（别处改过）时提示，仍以网页上的 t/f 为准。
- 出生点只能是平地（g/p），山和水上不能有地貌，沼泽只能在平地上；不合规的改动跳过并列出。
- 只有备注、没改地形的条目只打印出来，由 Claude 按备注手动处理。
写回后照常依次运行 open_pockets、connect_rivers、balance_starts、start_sets、render_map、build_editor。

用法：python tools/apply_edits.py edits.json [地图脚本] [--write]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    sys.exit(__doc__)
EDITS = args[0]
LUA = args[1] if len(args) > 1 else os.path.join(ROOT, "Zhanguo_V4", "ZhanguoV4.lua")
WRITE = "--write" in sys.argv

raw = json.load(open(EDITS, encoding="utf-8"))
if isinstance(raw, dict):
    raw = raw.get("edits") or raw.get("documents") or raw.get("docs") or []
items = [d.get("data", d) for d in raw]

s = open(LUA, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
blk = lambda n: re.search(r"local " + n + r" = \{(.*?)\r?\n\}", s, re.S)
T = [list(r) for r in re.findall(r'"([^"]+)"', blk("TERRAIN_ROWS").group(1))]
F = [list(r) for r in re.findall(r'"([^"]+)"', blk("FEATURE_ROWS").group(1))]
H, W = len(T), len(T[0])
starts = {(int(x), int(y)): n for n, x, y in re.findall(r'name = "(\w+)", x = (\d+), y = (\d+)', blk("START_POSITIONS").group(1))}

done, skipped, notes, drift = [], [], [], []
for e in sorted(items, key=lambda e: (e["y"], e["x"])):
    x, y, t, f = e["x"], e["y"], e["t"], e["f"]
    if not (0 <= x < W and 0 <= y < H) or t not in "~cgGpPdDMS" or f not in ".fjm":
        skipped.append((x, y, "坐标或字符不对"))
        continue
    cur_t, cur_f = T[H - 1 - y][x], F[H - 1 - y][x]
    if (e.get("note") or "").strip():
        notes.append((x, y, e["note"].strip()))
    if (t, f) == (cur_t, cur_f):
        continue
    if (cur_t, cur_f) != (e.get("bt", cur_t), e.get("bf", cur_f)):
        drift.append((x, y, e.get("bt"), e.get("bf"), cur_t, cur_f))
    if (x, y) in starts and t not in "gp":
        skipped.append((x, y, f"{starts[(x, y)]} 的出生点必须是平地"))
        continue
    if f != "." and t in "~cMS":
        skipped.append((x, y, "山和水上不能有地貌"))
        continue
    if f == "m" and t not in "gp":
        skipped.append((x, y, "沼泽只能在平地上"))
        continue
    T[H - 1 - y][x], F[H - 1 - y][x] = t, f
    done.append((x, y, cur_t + cur_f, t + f))

print(f"改动 {len(done)} 格，跳过 {len(skipped)} 格，备注 {len(notes)} 条")
for x, y, a, b in done:
    print(f"  ({x},{y}) {a} -> {b}")
for x, y, why in skipped:
    print(f"  跳过 ({x},{y})：{why}")
for x, y, bt, bf, ct, cf in drift:
    print(f"  注意 ({x},{y})：网页上的原样是 {bt}{bf}，脚本里现在是 {ct}{cf}")
for x, y, n in notes:
    print(f"  备注 ({x},{y})：{n}")

# 改过的格子上的资源：水生资源（和石油）落到陆地上、或者陆地资源落到山和水上时，挪到 4 格内最近的空的合适格子
WATER_RES = {"FISH", "TURTLES", "CRABS", "PEARLS", "WHALES"}
changed = {(x, y) for x, y, _, _ in done}
used = set()
for name in ("SITE_RESOURCES", "GUAR_RESOURCES", "SCATTER_RESOURCES"):
    used |= {(int(x), int(y)) for x, y in re.findall(r"x = (\d+), y = (\d+)", blk(name).group(1))}
tt = lambda x, y: T[H - 1 - y][x]


def nbrs(x, y):
    d = [(1, 0), (-1, 0), (0, 1), (1, 1), (0, -1), (1, -1)] if y & 1 else [(1, 0), (-1, 0), (-1, 1), (0, 1), (-1, -1), (0, -1)]
    for dx, dy in d:
        if 0 <= x + dx < W and 0 <= y + dy < H:
            yield x + dx, y + dy


def move_res(m):
    x, y, r = int(m.group(1)), int(m.group(2)), m.group(3)
    if (x, y) not in changed:
        return m.group(0)
    want_water = r in WATER_RES or (r == "OIL" and tt(x, y) not in "dD~c")
    ok = (lambda c: tt(*c) == "c") if want_water else (lambda c: tt(*c) not in "~cMS")
    if ok((x, y)):
        return m.group(0)
    D = {(x, y): 0}
    q = [(x, y)]
    while q:
        u = q.pop(0)
        if ok(u) and u not in used:
            used.add(u)
            print(f"  资源 {r} ({x},{y}) 挪到 {u}")
            return m.group(0).replace(f"x = {x}, y = {y}", f"x = {u[0]}, y = {u[1]}")
        if D[u] < 4:
            for v in nbrs(*u):
                if v not in D:
                    D[v] = D[u] + 1
                    q.append(v)
    print(f"  资源 {r} ({x},{y}) 4 格内没有合适的格子，去掉")
    return "\x00"


if WRITE and done:
    def put(src, name, rows):
        m = re.search(r"local " + name + r" = \{(.*?)\r?\n\}", src, re.S)
        body = nl + ("," + nl).join('\t"' + "".join(r) + '"' for r in rows)
        return src[:m.start(1)] + body + src[m.end(1):]
    s = put(s, "TERRAIN_ROWS", T)
    s = put(s, "FEATURE_ROWS", F)
    s = re.sub(r'\{ x = (\d+), y = (\d+), res = "(\w+)" \}', move_res, s)
    s = re.sub(r"[^\n]*\x00[^\n]*\n", "", s)
    open(LUA, "w", encoding="utf-8", newline="").write(s)
    print("已写回")
