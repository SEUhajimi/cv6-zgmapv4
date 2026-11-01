"""
把战国七雄地图（Zhanguo_V4/ZhanguoV4.lua）里不通水面的淡水河边接到最近的水面上。

游戏里的河必须流进水里：一组河边（RIVER_PAIRS 和 YELLOW_EDGE_CELLS）如果哪头都不挨着水面，
游戏会在它的末端画出一个小水坑。这个工具找出所有这样的河段，沿陆地之间的格边找一条最短的路
（尽量不贴着山）接到水面或已经通水的河上，把新加的河边追加到 RIVER_PAIRS 末尾。
流向由地图脚本在生成时自动计算（流向沿河最近的水面），这里不用管。

可以重复运行：所有河段都通水以后不会再加任何东西。
用法：python tools/connect_rivers.py [地图脚本]
"""
import heapq
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "Zhanguo_V4", "ZhanguoV4.lua")
src = open(LUA, encoding="utf-8").read()


def block(name):
    return re.search(r"local " + name + r" = \{(.*?)\r?\n\}", src, re.S).group(1)


T = re.findall(r'"([^"]+)"', block("TERRAIN_ROWS"))
H, W = len(T), len(T[0])
inside = lambda x, y: 0 <= x < W and 0 <= y < H
terr = lambda x, y: T[H - 1 - y][x] if inside(x, y) else "M"
is_water = lambda t: inside(*t) and terr(*t) in "~c"  # 地图外不算水面
pairs = [tuple(map(int, m)) for m in re.findall(r"\{ (\d+), (\d+), (\d+), (\d+) \}", block("RIVER_PAIRS"))]
yellow = [(int(x), int(y)) for x, y in re.findall(r"x = (\d+), y = (\d+)", block("YELLOW_EDGE_CELLS"))]


def neighbors(x, y):
    # 奇数行右移半格（游戏的排布）
    if y & 1:
        d = {"E": (1, 0), "W": (-1, 0), "NE": (1, 1), "NW": (0, 1), "SE": (1, -1), "SW": (0, -1)}
    else:
        d = {"E": (1, 0), "W": (-1, 0), "NE": (0, 1), "NW": (-1, 1), "SE": (0, -1), "SW": (-1, -1)}
    return {k: (x + dx, y + dy) for k, (dx, dy) in d.items()}


# 顶点用整数格点表示：格子中心 (2x + 奇偶, 3y)，六个角在 (0,±2) 和 (±1,±1)
def corners(x, y):
    cx, cy = 2 * x + (y & 1), 3 * y
    return {(cx + dx, cy + dy) for dx, dy in ((0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1))}


def edge(a, b):
    s = corners(*a) & corners(*b)
    assert len(s) == 2, (a, b)
    return tuple(sorted(s))


vtiles = defaultdict(set)  # 顶点 -> 周围三个格子
for y in range(-1, H + 1):
    for x in range(-1, W + 1):
        for v in corners(x, y):
            vtiles[v].add((x, y))
wet = {v for v, ts in vtiles.items() if any(is_water(t) for t in ts)}

edges = {}  # 河边 -> 两侧格子
for x, y, x2, y2 in pairs:
    edges[edge((x, y), (x2, y2))] = ((x, y), (x2, y2))
for x, y in yellow:
    n = neighbors(x, y)
    for k in ("SE", "SW"):
        edges[edge((x, y), n[k])] = ((x, y), n[k])

adj = defaultdict(set)
for e in edges:
    for v in e:
        adj[v].add(e)


def components():
    seen, out = set(), []
    for e in edges:
        if e in seen:
            continue
        stack, comp = [e], []
        seen.add(e)
        while stack:
            f = stack.pop()
            comp.append(f)
            for v in f:
                for g in adj[v]:
                    if g not in seen:
                        seen.add(g)
                        stack.append(g)
        out.append(comp)
    return out


def land_edges(v):
    # 顶点周围两侧都是陆地的格边
    ts = sorted(vtiles[v])
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            a, b = ts[i], ts[j]
            if b in neighbors(*a).values() and inside(*a) and inside(*b) and not is_water(a) and not is_water(b):
                yield edge(a, b), (a, b)


def cost(a, b):
    # 贴着山的格边代价高，路线尽量走平地
    return 1 + 3 * sum(terr(*t) in "MS" for t in (a, b))


comps = components()
reach = set(wet)
for c in comps:
    vs = {v for e in c for v in e}
    if vs & wet:
        reach |= vs
dry = [c for c in comps if not ({v for e in c for v in e} & reach)]

added = []
for c in sorted(dry, key=len, reverse=True):
    start = {v for e in c for v in e}
    if start & reach:  # 前面接通的河已经连到了这一段
        continue
    dist, prev, heap = {v: 0 for v in start}, {}, [(0, v) for v in start]
    heapq.heapify(heap)
    goal = None
    while heap:
        d, v = heapq.heappop(heap)
        if d > dist[v]:
            continue
        if v in reach:
            goal = v
            break
        for e, (a, b) in land_edges(v):
            w = e[1] if e[0] == v else e[0]
            nd = d + cost(a, b)
            if nd < dist.get(w, 1e9):
                dist[w], prev[w] = nd, (v, e, (a, b))
                heapq.heappush(heap, (nd, w))
    if goal is None:
        print("找不到通往水面的路：", sorted(edges[e] for e in c)[:3])
        continue
    v = goal
    while v not in start:
        u, e, (a, b) = prev[v]
        if e not in edges:
            edges[e] = (a, b)
            added.append((a, b))
        reach.add(v)
        v = u
    reach |= start

print(f"不通水面的河段 {len(dry)} 组，新加河边 {len(added)} 条")
if added:
    lines = "".join(f"\n\t{{ {a[0]}, {a[1]}, {b[0]}, {b[1]} }}," for a, b in added)
    body = block("RIVER_PAIRS")
    if "-- 内陆河段通往水面的连接段" not in body:
        lines = "\n\t-- 内陆河段通往水面的连接段（tools/connect_rivers.py 生成）" + lines
    new_body = body.rstrip().rstrip(",") + "," + lines.rstrip(",")
    out = src.replace("local RIVER_PAIRS = {" + body, "local RIVER_PAIRS = {" + new_body, 1)
    open(LUA, "w", encoding="utf-8", newline="").write(out)
