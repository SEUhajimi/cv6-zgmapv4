"""
重算战国七雄地图（Zhanguo_V4/ZhanguoV4.lua）的开局距离表 START_DIST 和各人数的开局组合 SPREAD_SETS。

距离按陆路算（山、雪山、水面都过不去），没有陆路时（比如隔着长江）用直线格数。
开局组合：对每个人数 N，枚举 N 个出生点的所有组合，每块陆地归离它陆路最近的出生点（沙漠按 0.3 格算），
取各家土地最平均的那些组合（和最平均的相差不超过 5%），并要求最近的两个出生点陆路至少相隔 MIN_GAP 格。
长江以南的出生点（和会稽陆路相通的）一组里要么不选，要么至少选两个，且不超过一半，免得一家独占南方。

改了地形（尤其是山、水、关口）后运行一次，START_DIST 和 SPREAD_SETS 才和新地形一致。

用法：python tools/start_sets.py [地图脚本] [--write]
默认读 Zhanguo_V4/ZhanguoV4.lua；不带 --write 只打印结果，带 --write 写回地图脚本。需要 numpy。
"""
import collections
import itertools
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
LUA = args[0] if args else os.path.join(ROOT, "Zhanguo_V4", "ZhanguoV4.lua")
WRITE = "--write" in sys.argv

MIN_GAP = None  # 一组里最近的两个出生点，陆路至少相隔这么多格（V3 巨型地图 9 格，其他尺寸按宽度换算）
TOL = 1.05   # 保留和最平均的组合相差 5% 以内的组合
REACH = 10  # 只算离出生点这么多格以内的陆地（前期能拿到的地，边远地区不算）；None 表示全图
MAX_NEAR = None  # 每个出生点离最近的另一个出生点不超过这么多格，免得有人独占一角安心发育（按宽度换算 30 格）

s = open(LUA, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
blk = lambda n: re.findall(r'"([^"]+)"', re.search(r"local " + n + r" = \{(.*?)\r?\n\}", s, re.S).group(1))
T = blk("TERRAIN_ROWS")
H, W = len(T), len(T[0])
MIN_GAP = MIN_GAP or round(9 * W / 106)
MAX_NEAR = MAX_NEAR or round(30 * W / 106)
t = lambda x, y: T[H - 1 - y][x]
pos = {n: (int(x), int(y)) for n, x, y in re.findall(r'name = "(\w+)", x = (\d+), y = (\d+)', s.split("local LEADER_BIND")[0])}
names = list(pos)


def nbrs(x, y):
    # 奇数行右移半格（游戏的排布）
    d = [(1, 0), (-1, 0), (0, 1), (1, 1), (0, -1), (1, -1)] if y & 1 else [(1, 0), (-1, 0), (-1, 1), (0, 1), (-1, -1), (0, -1)]
    for dx, dy in d:
        nx, ny = x + dx, y + dy
        if 0 <= nx < W and 0 <= ny < H:
            yield nx, ny


land = lambda x, y: t(x, y) not in "~cMS"
tiles = [(x, y) for y in range(H) for x in range(W) if land(x, y)]
idx = {c: i for i, c in enumerate(tiles)}
weight = np.array([0.3 if t(x, y) in "dD" else 1.0 for x, y in tiles])
INF = 10 ** 6
# dist[k, i]：第 k 个出生点到第 i 块陆地的陆路格数
dist = np.full((len(names), len(tiles)), INF, dtype=np.int32)
for k, n in enumerate(names):
    D = {pos[n]: 0}
    q = collections.deque([pos[n]])
    while q:
        u = q.popleft()
        for v in nbrs(*u):
            if v not in D and land(*v):
                D[v] = D[u] + 1
                q.append(v)
    for c, d in D.items():
        dist[k, idx[c]] = d


def cube(x, y):
    return x - (y - (y & 1)) // 2, y


def hd(a, b):
    """两格之间的直线格数。"""
    q1, r1 = cube(*a)
    q2, r2 = cube(*b)
    dq, dr = q2 - q1, r2 - r1
    return max(abs(dq), abs(dr), abs(dq + dr))


# 出生点两两之间的距离：有陆路用陆路，没有就用直线（即 START_DIST）
P = {a: {b: (0 if a == b else (int(dist[names.index(a), idx[pos[b]]]) if dist[names.index(a), idx[pos[b]]] < INF else hd(pos[a], pos[b]))) for b in names} for a in names}


def shares(combo):
    """一组出生点各自分到的土地（每块陆地归陆路最近的出生点）。"""
    ks = [names.index(n) for n in combo]
    sub = dist[ks]
    owner = sub.argmin(axis=0)
    reach = sub.min(axis=0) < (INF if REACH is None else REACH + 1)
    return np.bincount(owner[reach], weights=weight[reach], minlength=len(ks))


south = [n for n in names if dist[names.index("Kuaiji"), idx[pos[n]]] < INF]
print("south starts:", south)
result = {}
for n in range(2, len(names)):
    scored = []
    for combo in itertools.combinations(names, n):
        ns = sum(1 for c in combo if c in south)
        if ns == 1 or ns * 2 > n:  # 南方不能只有一家，也不能超过一半
            continue
        gap = min(P[a][b] for a, b in itertools.combinations(combo, 2))
        if gap < MIN_GAP:
            continue
        if max(min(P[a][b] for b in combo if b != a) for a in combo) > MAX_NEAR:
            continue
        sh = shares(combo)
        scored.append((sh.max() / max(sh.min(), 1), gap, combo, sh))
    if not scored:
        continue
    best = min(r[0] for r in scored)
    keep = [r for r in scored if r[0] <= best * TOL]
    keep.sort(key=lambda r: (r[0], -r[1]))
    result[n] = keep
    r = keep[0]
    print(f"{n:2d} players: {len(keep):3d} groups, best max/min land {r[0]:.2f}, closest pair {r[1]}")
    print("     ", " ".join(f"{c}{int(v)}" for c, v in sorted(zip(r[2], r[3]), key=lambda kv: -kv[1])))

if WRITE:
    m = re.search(r"local START_DIST = \{.*?\n\}", s, re.S)
    rows = ['\t["%s"] = { %s }' % (a, ", ".join('["%s"] = %d' % (b, P[a][b]) for b in names)) for a in names]
    s = s[:m.start()] + "local START_DIST = {" + nl + ("," + nl).join(rows) + nl + "}" + s[m.end():]
    m = re.search(r"local SPREAD_SETS = \{.*?\n\}", s, re.S)
    lines = ["\t[%d] = { %s }" % (n, ", ".join("{ " + ", ".join('"%s"' % x for x in r[2]) + " }" for r in result[n])) for n in sorted(result)]
    s = s[:m.start()] + "local SPREAD_SETS = {" + nl + ("," + nl).join(lines) + nl + "}" + s[m.end():]
    open(LUA, "w", encoding="utf-8", newline="").write(s)
    print("written")
