"""
调平战国七雄地图各出生点周围的地形，PvP 时各家开局差不多。

对每个出生点统计 3 格内（不含出生点本格）：
  陆地  可用陆地格数（水面按半格算，山地不算）
  粮食、生产力  地形和地貌的基础产出之和（草原 2/0、平原 1/1、丘陵 +1 生产力、森林 +1 生产力、雨林/沼泽 +1 粮食、水面 1/0）
  丘陵  丘陵格数
低于下限的，按顺序改地形补上：
  粮食不够  沙漠→平原，山地→草原丘陵（条件同下），平原→草原丘陵（2~3 环），平原→草原（生产力有富余时）
  生产力不够  平地→丘陵（2~3 环）或者平地加森林
  陆地不够  山地→丘陵：这格周围的陆地邻居不经过它也能在 4 格内互通（不会开出新的关口），并且至少留 3 座山（学院相邻加成）
  丘陵不够  平地→丘陵
不动出生点本格和写了资源的格子（SITE/GUAR/SCATTER_RESOURCES）；资源平衡由地图脚本在生成时完成（GenerateMap 5b、5c）。
可重复运行：都达标后不再改动。不带 --write 只打印，不写回。

用法：python tools/balance_starts.py [地图脚本] [--write]
"""
import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
LUA = args[0] if args else os.path.join(ROOT, "Zhanguo_V4", "ZhanguoV4.lua")
WRITE = "--write" in sys.argv

MIN_LAND, MIN_FOOD, MIN_PROD, MIN_HILL = 24, 42, 30, 7
KEEP_MTN = 3
R = 3

s = open(LUA, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
blk = lambda n: re.search(r"local " + n + r" = \{(.*?)\r?\n\}", s, re.S)
T = [list(r) for r in re.findall(r'"([^"]+)"', blk("TERRAIN_ROWS").group(1))]
F = [list(r) for r in re.findall(r'"([^"]+)"', blk("FEATURE_ROWS").group(1))]
H, W = len(T), len(T[0])
t = lambda x, y: T[H - 1 - y][x]
f = lambda x, y: F[H - 1 - y][x]


def sett(x, y, c):
    T[H - 1 - y][x] = c


def setf(x, y, c):
    F[H - 1 - y][x] = c


pos = [(n, int(x), int(y)) for n, x, y in re.findall(r'name = "(\w+)", x = (\d+), y = (\d+)', blk("START_POSITIONS").group(1))]
fixed = set()
for name in ("SITE_RESOURCES", "GUAR_RESOURCES", "SCATTER_RESOURCES"):
    fixed |= {(int(x), int(y)) for x, y in re.findall(r"x = (\d+), y = (\d+)", blk(name).group(1))}
fixed |= {(x, y) for _, x, y in pos}


def nbrs(x, y):
    d = [(1, 0), (-1, 0), (0, 1), (1, 1), (0, -1), (1, -1)] if y & 1 else [(1, 0), (-1, 0), (-1, 1), (0, 1), (-1, -1), (0, -1)]
    for dx, dy in d:
        if 0 <= x + dx < W and 0 <= y + dy < H:
            yield x + dx, y + dy


def area(x, y, r):
    D = {(x, y): 0}
    q = collections.deque([(x, y)])
    while q:
        u = q.popleft()
        if D[u] == r:
            continue
        for v in nbrs(*u):
            if v not in D:
                D[v] = D[u] + 1
                q.append(v)
    return D


YIELD = {"g": (2, 0), "p": (1, 1), "d": (0, 0), "G": (2, 1), "P": (1, 2), "D": (0, 1), "c": (1, 0), "~": (1, 0), "M": (0, 0), "S": (0, 0)}
land = lambda x, y: t(x, y) not in "~cMS"


def stats(x, y):
    D = area(x, y, R)
    cells = [c for c in D if c != (x, y)]
    ld = sum(1 for c in cells if land(*c)) + 0.5 * sum(1 for c in cells if t(*c) in "~c")
    fo = pr = 0
    for c in cells:
        a, b = YIELD[t(*c)]
        if f(*c) == "f":
            b += 1
        if f(*c) in "jm":
            a += 1
        fo, pr = fo + a, pr + b
    hill = sum(1 for c in cells if t(*c) in "GPD")
    mtn = sum(1 for c in cells if t(*c) in "MS")
    return ld, fo, pr, hill, mtn, D


def mtn_safe(c):
    """山改丘陵后，它周围的陆地邻居不经过它也能在 4 格内互通，不会开出新通道"""
    ln = [n for n in nbrs(*c) if land(*n)]
    if not ln:
        return False
    D = {ln[0]: 0}
    q = collections.deque([ln[0]])
    while q:
        u = q.popleft()
        if D[u] >= 4:
            continue
        for v in nbrs(*u):
            if v not in D and v != c and land(*v):
                D[v] = D[u] + 1
                q.append(v)
    return all(n in D for n in ln)


log = []
for name, x, y in pos:
    for _ in range(60):
        ld, fo, pr, hill, mtn, D = stats(x, y)
        # 外环优先改，1 环尽量保持原样
        cand = sorted((c for c in D if c not in fixed and D[c] >= 1), key=lambda c: (-D[c], c))
        changed = None
        if ld < MIN_LAND and mtn > KEEP_MTN:
            for c in cand:
                if t(*c) == "M" and mtn_safe(c):
                    sett(*c, "P" if pr < MIN_PROD + 4 else "G")
                    changed = (c, "山地→丘陵（补陆地）")
                    break
        if changed is None and fo < MIN_FOOD:
            for c in cand:
                if t(*c) in "dD":
                    sett(*c, {"d": "p", "D": "P"}[t(*c)])
                    changed = (c, "沙漠→平原（补粮食）")
                    break
            if changed is None and mtn > KEEP_MTN:
                for c in cand:
                    if t(*c) == "M" and mtn_safe(c):
                        sett(*c, "G")
                        changed = (c, "山地→草原丘陵（补粮食）")
                        break
            if changed is None:
                # 平原 1/1 → 草原丘陵 2/1：加粮食，生产力不变
                for c in cand:
                    if t(*c) == "p" and f(*c) in ".f" and D[c] >= 2:
                        sett(*c, "G")
                        changed = (c, "平原→草原丘陵（补粮食）")
                        break
            if changed is None and pr > MIN_PROD:
                for c in cand:
                    if t(*c) in "pP" and f(*c) == ".":
                        sett(*c, {"p": "g", "P": "G"}[t(*c)])
                        changed = (c, "平原→草原（补粮食）")
                        break
        if changed is None and (pr < MIN_PROD or hill < MIN_HILL):
            for c in cand:
                if t(*c) in "gp" and f(*c) == "." and D[c] >= 2:
                    sett(*c, t(*c).upper())
                    changed = (c, "平地→丘陵（补生产力）")
                    break
            if changed is None and pr < MIN_PROD:
                for c in cand:
                    if t(*c) in "gpGP" and f(*c) == ".":
                        setf(*c, "f")
                        changed = (c, "加森林（补生产力）")
                        break
        if changed is None:
            break
        log.append((name, *changed))

print(f"{'出生点':8s}  陆地  粮食 生产力 丘陵 山")
for name, x, y in pos:
    ld, fo, pr, hill, mtn, _ = stats(x, y)
    flag = "" if ld >= MIN_LAND and fo >= MIN_FOOD and pr >= MIN_PROD and hill >= MIN_HILL else "  ← 未达标"
    print(f"{name:10s} {ld:5.1f} {fo:5d} {pr:5d} {hill:4d} {mtn:3d}{flag}")
cnt = collections.Counter((n, what) for n, _, what in log)
for (n, what), k in sorted(cnt.items()):
    print(f"  {n}: {what} ×{k}")

if WRITE and log:
    def put(src, name, rows):
        m = re.search(r"local " + name + r" = \{(.*?)\r?\n\}", src, re.S)
        body = nl + ("," + nl).join('\t"' + "".join(r) + '"' for r in rows)
        return src[:m.start(1)] + body + src[m.end(1):]
    s = put(s, "TERRAIN_ROWS", T)
    s = put(s, "FEATURE_ROWS", F)
    open(LUA, "w", encoding="utf-8", newline="").write(s)
    print(f"已写回 {len(log)} 处改动")
